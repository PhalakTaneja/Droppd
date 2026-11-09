#!/usr/bin/env python3
"""
Daily App Bot
=============
Every morning this script fetches a batch of real, freshly-maintained
candidates from GitHub's free public API, asks Google Gemini to pick the ONE
that best matches your spec in profile.md, then sends it to your Telegram.

It uses ONLY the Python standard library and ONLY free, keyless services --
you never need to pip-install anything or pay for search grounding.

Usage:
    python3 bot.py setup     # first time: find your Telegram chat id
    python3 bot.py           # normal run: pick one app, send it to you
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# File locations -- everything lives next to this script, so you can run it
# from anywhere.
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROFILE_FILE = BASE_DIR / "profile.md"   # your spec, written in plain English
HISTORY_FILE = BASE_DIR / "history.txt"  # apps already sent, one per line
ENV_FILE = BASE_DIR / ".env"             # your secrets, never committed to git


TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# GitHub's search API is free, needs no key, and gives the spec's core
# requirements (open-source, actively maintained) as hard facts.
GITHUB_SEARCH_API = "https://api.github.com/search/repositories"

# One focus area per day, rotating, so the candidate pool never goes stale.
SEARCH_TOPICS = [
    "productivity", "note-taking", "clipboard", "screenshot",
    "window-manager", "terminal", "automation", "backup",
    "time-tracking", "todo",
]


def load_env_file():
    """Copy KEY=VALUE pairs from the .env file into the environment.

    A .env file only exists on YOUR computer (it's in .gitignore).
    On GitHub Actions there is no .env file, but the secrets are set as
    real environment variables -- and real environment variables always
    win here, so the same code works in both places.
    """
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue  # skip blank lines and comments
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name):
    """Return an environment variable, or quit with a helpful message."""
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: {name} is not set.")
        print(f"  - Running locally?  Put {name}=... in your .env file")
        print("   (create a .env file in this folder and fill it in).")
        print("  - Running on GitHub Actions?  Add it under Settings > Secrets")
        print("    and variables > Actions > New repository secret.")
        sys.exit(1)
    return value


# ---------------------------------------------------------------------------
# One tiny helper for talking to any JSON API over HTTPS
# ---------------------------------------------------------------------------
def post_json(url, payload, headers=None):
    """Send a POST request with a JSON body, return the parsed response.

    If anything goes wrong, quit with the server's actual error message so
    you can see exactly what the problem was.
    """
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")[:600]
        print(f"ERROR: the server rejected the request (HTTP {err.code}).")
        print(f"Server said: {body}")
        sys.exit(1)
    except urllib.error.URLError as err:
        print(f"ERROR: could not reach the server ({err.reason}).")
        print("Check your internet connection and try again.")
        sys.exit(1)


def get_json(url, headers=None, timeout=30):
    """GET a URL and return the parsed JSON, or None if anything goes wrong.

    Used for GitHub's public API, which needs no key -- just a User-Agent
    header identifying the caller.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": "daily-app-bot", **(headers or {})}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as err:  # network errors and bad JSON
        print(f"WARNING: could not reach {url} ({err}).")
        return None


# ---------------------------------------------------------------------------
# Finding candidates: GitHub's free public search
# ---------------------------------------------------------------------------
def fetch_live_candidates():
    """Fetch real, currently-maintained repos from GitHub's public API.

    Rotates through the focus areas above (one per day) and asks for repos
    pushed within the last 90 days, sorted by stars. Returns digest lines
    for the prompt -- every link comes straight from GitHub, so it is
    guaranteed to be real.
    """
    topic = SEARCH_TOPICS[date.today().timetuple().tm_yday % len(SEARCH_TOPICS)]
    pushed_since = (date.today() - timedelta(days=90)).isoformat()
    url = (
        f"{GITHUB_SEARCH_API}?q=topic:{topic}+pushed:>{pushed_since}"
        "&sort=stars&order=desc&per_page=20"
    )
    data = get_json(url, headers={"Accept": "application/vnd.github+json"})
    repos = (data or {}).get("items") or []
    lines = []
    for repo in repos:
        license_id = (repo.get("license") or {}).get("spdx_id") or "none"
        topics = ", ".join((repo.get("topics") or [])[:4]) or "none"
        pushed = (repo.get("pushed_at") or "")[:10]
        lines.append(
            f"- {repo.get('full_name', '?')} "
            f"(stars: {repo.get('stargazers_count', '?')}, "
            f"language: {repo.get('language') or 'n/a'}, "
            f"license: {license_id}, last push: {pushed}, topics: {topics})\n"
            f"  {repo.get('description') or '(no description)'}\n"
            f"  {repo.get('html_url', '')}"
        )
    return lines


# ---------------------------------------------------------------------------
# Telegram helpers
# ---------------------------------------------------------------------------
def find_chat_id(token):
    """Discover your chat id from the last message your bot received.

    Bots on Telegram cannot message someone out of the blue -- you have to
    talk to the bot first. That first message is what tells Telegram "this
    human is allowed to hear from my bot", and it is how we learn your id.
    """
    result = post_json(TELEGRAM_API.format(token=token, method="getUpdates"), {})
    updates = result.get("result", [])
    # Updates arrive oldest-first, so we walk backwards to find the newest.
    for update in reversed(updates):
        chat = (update.get("message") or {}).get("chat") or \
               (update.get("channel_post") or {}).get("chat")
        if chat:
            return chat["id"], chat.get("first_name") or chat.get("username", "")
    print("No messages found yet.")
    print("Open Telegram, send /start to your bot, then run this again:")
    print("    python3 bot.py setup")
    sys.exit(1)


def send_telegram(token, chat_id, text):
    """Send a plain-text message. Plain text means no formatting errors."""
    # Telegram rejects messages longer than 4096 characters, so trim first.
    text = text[:4000]
    result = post_json(
        TELEGRAM_API.format(token=token, method="sendMessage"),
        {"chat_id": chat_id, "text": text},
    )
    if not result.get("ok"):
        print(f"ERROR: Telegram said not-ok: {result}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# The brain: ask Gemini (with live web search) for today's recommendation
# ---------------------------------------------------------------------------
def ask_gemini(api_key, prompt):
    """Send the prompt to Gemini and return the answer.

    The live research already happened before this call: real candidate
    data is baked into the prompt, so no paid search tool is needed.
    """
    model = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    result = post_json(url, payload, headers={"x-goog-api-key": api_key})

    candidates = result.get("candidates", [])
    if not candidates:
        print("ERROR: Gemini returned no answer. Full response:")
        print(json.dumps(result, indent=2)[:600])
        sys.exit(1)

    # The answer may be split across several "parts"; glue them together.
    parts = candidates[0].get("content", {}).get("parts", [])
    answer = "".join(part.get("text", "") for part in parts).strip()
    if not answer:
        print("ERROR: Gemini's answer was empty. Full response:")
        print(json.dumps(result, indent=2)[:600])
        sys.exit(1)
    return answer


# ---------------------------------------------------------------------------
# Building the prompt from your files
# ---------------------------------------------------------------------------
def build_prompt(candidates):
    """Combine the live candidates, your spec and your history into one prompt."""
    profile = PROFILE_FILE.read_text() if PROFILE_FILE.exists() else \
        "No profile.md found -- recommend a generally useful productivity app."
    if HISTORY_FILE.exists() and HISTORY_FILE.read_text().strip():
        history = HISTORY_FILE.read_text().strip()
    else:
        history = "(nothing yet -- this is the very first recommendation)"

    if candidates:
        live = (
            "TODAY'S LIVE CANDIDATES FROM GITHUB (fetched minutes ago: every\n"
            "entry is a real repository with a working link, updated within the\n"
            "last 90 days):\n" + "\n".join(candidates)
        )
        pick_rule = (
            "- Choose ONLY from the live candidates above. The LINK must be the\n"
            "  repository URL shown there -- never invent or guess a link."
        )
    else:
        live = (
            "NO LIVE DATA: GitHub could not be reached today, so there is no\n"
            "candidate list. Only recommend something you are GENUINELY certain\n"
            "is real and currently maintained, and admit in WHY ME that today's\n"
            "pick comes without live verification."
        )
        pick_rule = (
            "- With no live list, only recommend what you are certain is real\n"
            "  and maintained. If nothing qualifies, say so instead of guessing."
        )

    return f"""Today is {date.today().isoformat()}.
You are my personal software-recommendation agent.

Find ONE genuinely useful, currently maintained app, extension, or open-source
tool that would improve my productivity and that matches my specification
below.

{live}

MY SPECIFICATION:
---
{profile}
---

APPS ALREADY RECOMMENDED TO ME (do NOT repeat any of these):
{history}

RULES:
- Pick exactly ONE item, and it must NOT be on the history list.
{pick_rule}
- Prefer free and open-source. If it costs money, it must have a genuinely
  usable free tier -- no subscription-only tools.
- Skip famous obvious picks (Chrome, VS Code, Notion, Spotify, 1Password...)
  unless the entry has a specific lesser-known feature or trick worth teaching me.

Answer in EXACTLY this plain-text format (no markdown, no asterisks):

APP: <name>
WHAT IT IS: <one sentence>
PLATFORM: <Windows / macOS / Linux / Web / browser extension>
WHY ME: <two or three sentences tying it specifically to my specification>
PRICE: <what is free, what a paid tier adds>
LINK: <official download or repository page>"""


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------
def main():
    load_env_file()
    token = require_env("TELEGRAM_BOT_TOKEN")

    # -- setup mode: just print the chat id and stop ------------------------
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        chat_id, who = find_chat_id(token)
        print(f"Hello {who}! Your chat id is: {chat_id}")
        print(f"Now open your .env file and set:")
        print(f"    TELEGRAM_CHAT_ID={chat_id}")
        return

    # -- normal mode: pick an app and send it ------------------------------
    chat_id = require_env("TELEGRAM_CHAT_ID")
    gemini_key = require_env("GEMINI_API_KEY")

    print("Fetching live candidates from GitHub...")
    candidates = fetch_live_candidates()
    if candidates:
        print(f"Got {len(candidates)} real, maintained candidates.")
    else:
        print("WARNING: no live candidates; asking Gemini to be careful.")

    print("Asking Gemini to pick today's recommendation...")
    answer = ask_gemini(gemini_key, build_prompt(candidates))

    print("Sending it to Telegram...")
    send_telegram(token, chat_id, answer)

    # Remember what we sent so the same app is never recommended twice.
    app_line = next(
        (line for line in answer.splitlines() if line.strip().startswith("APP:")),
        answer.splitlines()[0] if answer else "unknown",
    )
    app_name = app_line.split(":", 1)[-1].strip() if ":" in app_line else app_line
    with HISTORY_FILE.open("a", encoding="utf-8") as history:
        history.write(f"{date.today().isoformat()}  {app_name}\n")

    print(f"Done! Today's pick was: {app_name}")


if __name__ == "__main__":
    main()
