# droppd

Your daily dose of useful tech discoveries!

Get one handpicked recommendation every day, from interesting GitHub
repositories and productivity apps to powerful browser extensions and
developer tools.

Discover something useful. Learn something new. Build smarter, every day.

## How it works

Every morning at 10:00 India time, droppd:

1. Fetches the freshest candidates from GitHub's public API: real
   repositories, pushed within the last 90 days, rotating daily through a
   set of focus areas (note-taking, clipboard, window management, backups,
   terminal tools, ...).
2. Asks Gemini to pick the ONE that best matches your personal spec in
   `profile.md`, and to explain why it fits you.
3. Sends it to your Telegram and records it in `history.txt`, so no pick
   ever repeats.

Zero cost, zero paid APIs. Everything runs on the Python standard
library: no `pip install`, no server, no database.

## Setup (first time, about 5 minutes)

What you need: Python 3, a Telegram account, a free Google account.

1. Check Python:

       python3 --version

   On macOS, if that fails, run `xcode-select --install` first.

2. Collect your two free keys:
   - Telegram bot token: message [@BotFather](https://t.me/BotFather) on
     Telegram, send `/newbot`, and copy the token it gives you.
   - Gemini API key: create one free at
     <https://aistudio.google.com/apikey>.

3. Create your local config from the template:

       cp .env.example .env

   Open `.env` and paste in your bot token and Gemini key. Leave
   `TELEGRAM_CHAT_ID` empty for now. `.env` is gitignored, so your secrets
   never leave your machine.

4. Find your chat id: open Telegram, send `/start` to your new bot, then:

       python3 bot.py setup

   It prints your chat id. Put it into `.env` as `TELEGRAM_CHAT_ID=...`.

5. Get your first drop:

       python3 bot.py

   Your phone should buzz within about 15 seconds.

## Run it every day

**Option A, GitHub Actions (free, runs even when your computer is off).**
Push this folder to a private GitHub repo and add three repository secrets
under Settings > Secrets and variables > Actions:

   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`

The included workflow (`.github/workflows/daily.yml`) then runs every day
at 10:00 India time (04:30 UTC) and commits `history.txt` back to the repo
after each run, so the no-repeats memory survives. Test it any time from
the repo's Actions tab with the "Run workflow" button.

**Option B, your own computer.** Any scheduler that runs `python3 bot.py`
once a day works: cron, launchd on macOS, or Task Scheduler on Windows.
On a Mac, a launchd agent with a daily `StartCalendarInterval` at 10:00 is
the native way; log output to a file so failures are visible.

## Share your drops

To deliver the same daily pick to other people, create a Telegram channel
and add your bot as its admin with permission to post. Post any message in
the channel, run `python3 bot.py setup` once to read out the channel's
chat id, and put that id into `TELEGRAM_CHAT_ID`. Everyone in the channel
then receives the drop: a private channel means only people you invite, a
public channel means anyone with the link.

## Notes

- Cost: zero. Gemini's free tier covers one model call a day, and
  GitHub's public search API needs no key and allows far more. The bot
  deliberately avoids Gemini's paid search-grounding feature; the live
  data comes from GitHub directly.
- `profile.md` is your taste, written in plain English. Edit it whenever
  you like; the next morning's drop follows it.
- `history.txt` is the memory. If a run ever fails, the log shows the
  exact server response.
- On GitHub Actions, scheduled workflows pause after 60 days with no repo
  activity. The daily `history.txt` commit keeps the repo active by
  itself, but an occasional push never hurts.
- Your `.env` holds your bot token and API key. It is gitignored on
  purpose: never commit it, never paste it anywhere.
