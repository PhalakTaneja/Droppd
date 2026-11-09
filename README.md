# daily-app-bot

One productivity app recommendation in your Telegram, every morning at
10:00. The bot fetches real, freshly-maintained candidates from GitHub's
free public API, has Gemini pick the best match for your spec in
`profile.md`, and never repeats a past pick.

Zero cost, no pip installs, no server. Python 3 + Telegram + GitHub + Gemini.

## Setup (first time only)

1. **Check Python is available**

       python3 --version

   If that fails, run `xcode-select --install` first.

2. **Get a free Gemini API key** at <https://aistudio.google.com/apikey>
   (sign in with any Google account, "Create API key", copy it).

3. **Create your local config**

       cp .env.example .env

   Open `.env` and paste your BotFather token and the Gemini key.
   Leave `TELEGRAM_CHAT_ID` empty for now.

4. **Find your chat id**: open Telegram, send `/start` to your bot, then:

       python3 bot.py setup

   It prints your chat id -- put it into `.env` as `TELEGRAM_CHAT_ID=...`.

5. **Send your first recommendation:**

       python3 bot.py

   Your phone should buzz within ~15 seconds.

## Going live on GitHub Actions (free daily runs)

6. **Push this folder to a private GitHub repo**

       cd ~/daily-app-bot
       git init
       git add -A
       git commit -m "daily app bot v1"
   Then create an empty *private* repo on github.com and:

       git remote add origin git@github.com:YOUR-NAME/daily-app-bot.git
       git push -u origin main

   (Or use HTTPS: `git remote add origin https://github.com/YOUR-NAME/daily-app-bot.git`)

7. **Add three secrets** on GitHub: repo page > Settings > Secrets and
   variables > Actions > "New repository secret":

   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`

8. **Test it now**: repo page > Actions tab > "Daily app recommendation" >
   "Run workflow" > Run. A minute later, check Telegram.

Done. Every morning at 10:00 India time you get one fresh recommendation.

## Running it locally on a Mac instead

No GitHub needed: a launchd agent on this Mac runs the bot daily at 10:00.
The agent lives at `~/Library/LaunchAgents/com.faahh.daily-app-bot.plist`
and writes its output to `~/Library/Logs/daily-app-bot.log`.

       launchctl kickstart gui/$(id -u)/com.faahh.daily-app-bot   # run now
       launchctl bootout gui/$(id -u)/com.faahh.daily-app-bot     # stop it

If the Mac was asleep at 10:00, launchd simply runs the job when it wakes.

## Notes

- `profile.md` is your spec. Edit it in plain English any time; the next
  morning's recommendation follows it.
- `history.txt` lists everything already sent, so nothing repeats. The
  workflow commits it back to the repo after each run.
- GitHub disables scheduled workflows after 60 days of repo inactivity;
  push any commit to wake it up again.
- Cost: zero. Gemini's free tier covers one model call a day, and GitHub's
  public search API needs no key and allows 10 requests per minute. If a run
  ever fails, the log shows the exact error.
