# Uzbek Financial Digest Bot

Every morning at ~09:00 Tashkent time, this reads recent items from Uzbek news
feeds, keeps the finance/economy stories, has Google Gemini write a one-page
executive summary, and sends it to you on Telegram. Runs in the cloud on a
schedule. **Cost: $0.**

You do **not** write any code. The only thing left is a one-time setup
(~10 minutes) that I cannot do for you because it requires *your* accounts.

---

## The only part you must do: deploy once

You need three secret values — a Telegram bot token, your Telegram chat ID, and
a Gemini API key — then drop the files in a GitHub repo.

### 1. Telegram bot token
1. Open Telegram, search **@BotFather**, send `/newbot`.
2. Pick any name and a username ending in `bot`.
3. Copy the token it gives you (looks like `8123456789:AAH...`). → **TELEGRAM_BOT_TOKEN**

### 2. Your Telegram chat ID
1. Open the bot you just made and press **Start** (send it any message, e.g. "hi").
   *(A bot can only message you after you've started it — don't skip this.)*
2. In a browser, open:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   (paste your token in place of `<YOUR_TOKEN>`).
3. Find `"chat":{"id":123456789` — that number is your ID. → **TELEGRAM_CHAT_ID**

### 3. Gemini API key (free)
1. Go to **https://aistudio.google.com/apikey**, sign in with Google.
2. Click **Create API key**, copy it. → **GEMINI_API_KEY**
   - Free tier, no credit card. Plenty for one summary a day.
   - *If the page won't issue a key from your region:* create it once over a VPN —
     it works everywhere afterward, and the bot itself calls Gemini from GitHub's
     US servers, so daily runs are unaffected. (Or see "Swapping the model" below.)

### 4. Put it on GitHub
1. Create a free account at github.com if you don't have one.
2. **New repository** → name it anything → **Public** (public repos get unlimited
   free Actions minutes; your secrets stay hidden regardless).
3. Upload all files from this folder, keeping the structure — the
   `.github/workflows/daily.yml` path matters. (Easiest: "uploading an existing
   file" → drag the whole folder, or unzip and drag.)
4. In the repo: **Settings → Secrets and variables → Actions → New repository
   secret**. Add three secrets with these exact names:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`
5. Open the **Actions** tab, enable workflows if prompted, click **Uzbek
   financial digest → Run workflow**. Within a minute you should get a Telegram
   message. That's the test — if it arrives, you're done.

After this, it runs on its own every morning. You're not involved again unless
something breaks.

---

## Adjusting things (optional)

- **Time:** edit the `cron` line in `.github/workflows/daily.yml`.
  It's in UTC. `0 4 * * *` = 09:00 Tashkent. For 08:00, use `0 3 * * *`.
- **Language:** in the same file, set `DIGEST_LANGUAGE` to `Uzbek`, `Russian`,
  or `English`.
- **Sources:** add or remove one line in `sources.py`. Each is one RSS feed.
- **How far back it looks:** `LOOKBACK_HOURS` (default 26) covers a full day plus
  a margin so nothing slips through the gap between runs.

---

## When something breaks (it eventually will)

This is "runs by itself, with rare fixes," not "immortal." The bot is built to
fail loudly so you're never guessing:

- **A source stops working** (site changed its feed): the bot keeps going with
  the others and lists the broken one at the bottom of your daily message. Fix or
  delete that line in `sources.py`.
- **No message arrives at all:** check the **Actions** tab for a red run and read
  the log. Usual causes: a wrong secret, or you never pressed Start on the bot.
- **GitHub disables the schedule after long inactivity:** the bot commits
  `seen.json` daily, which keeps the repo active and the schedule alive. If it's
  ever disabled anyway, re-enabling is one click in the Actions tab.
- **Gemini quota / 429 errors:** one daily call won't hit the free limit; if you
  see persistent 429s, generate a fresh key.

### Swapping the model (only if Gemini is unavailable to you)
Groq also has a free tier and an OpenAI-style API. Replace the body of
`gemini_summarize()` with a single POST to
`https://api.groq.com/openai/v1/chat/completions` using header
`Authorization: Bearer <GROQ_KEY>`, a `messages` array (system + user), and a
model such as `llama-3.3-70b-versatile`; read the reply from
`data["choices"][0]["message"]["content"]`. Swap the secret name accordingly.

---

## Two honest limitations

1. **The "analysis" is automated Gemini calls billed to your free quota — not me
   in a chat.** I wrote the code; the daily intelligence is the model your bot
   calls each morning.
2. **It reads news *websites*, not Telegram channels.** Reading Telegram channels
   needs a phone-number login that expires and would pull you back in — exactly
   what you asked to avoid. If you later want a specific Telegram channel added,
   that's a different setup; tell me and I'll handle it.
