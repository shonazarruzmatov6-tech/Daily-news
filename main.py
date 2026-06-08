#!/usr/bin/env python3
"""
Uzbek financial-news digest bot.

Pipeline (runs once a day from GitHub Actions):
  1. Pull recent items from the RSS feeds in sources.py
  2. Keep only finance/economy items (and drop ones already summarized)
  3. Ask Google Gemini (free tier) for a one-page executive summary
  4. Send it to you on Telegram

No server, no recurring cost. Network libraries are imported lazily so the
pure logic stays importable/testable even if a dependency is missing.

Required environment variables (set as GitHub Actions secrets):
  GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

import os
import re
import sys
import json
import time
import html
import calendar
import datetime as dt

from sources import SOURCES, FINANCE_KEYWORDS

# ----------------------------- Config -----------------------------
LOOKBACK_HOURS   = int(os.getenv("LOOKBACK_HOURS", "26"))    # what counts as "recent"
MAX_ITEMS_TO_LLM = int(os.getenv("MAX_ITEMS_TO_LLM", "60"))  # cap items sent to the model
DIGEST_LANGUAGE  = os.getenv("DIGEST_LANGUAGE", "English")   # output language of the brief
SEEN_PATH        = os.getenv("SEEN_PATH", "seen.json")
REQUEST_TIMEOUT  = 25

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Tried in order; protects against a model being renamed/retired.
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"]
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "").strip()

_TAG_RE = re.compile(r"<[^>]+>")


def log(msg):
    print(f"[{dt.datetime.utcnow():%Y-%m-%d %H:%M:%S}Z] {msg}", flush=True)


# ----------------------------- Pure helpers -----------------------------
def strip_html(s):
    """Turn an RSS HTML snippet into clean plain text."""
    s = _TAG_RE.sub(" ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def is_financial(item):
    """General feeds are keyword-filtered; dedicated economy feeds pass through."""
    if item["financial_only"]:
        return True
    blob = (item["title"] + " " + item["summary"]).lower()
    return any(k in blob for k in FINANCE_KEYWORDS)


def split_text(text, limit):
    """Split into <=limit-char chunks on line boundaries (Telegram caps at 4096)."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:                 # pathological single long line
            if current:
                chunks.append(current); current = ""
            chunks.append(line[:limit]); line = line[limit:]
        if len(current) + len(line) + 1 > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)
    return chunks


def extract_gemini_text(data):
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except Exception:
        raise RuntimeError("Unexpected Gemini response: " + json.dumps(data)[:300])


# ----------------------------- State (de-dup) -----------------------------
def load_seen():
    try:
        with open(SEEN_PATH, "r", encoding="utf-8") as f:
            return list(json.load(f).get("links", []))
    except Exception:
        return []


def save_seen(links):
    try:
        with open(SEEN_PATH, "w", encoding="utf-8") as f:
            json.dump({"links": links, "updated": dt.datetime.utcnow().isoformat()},
                      f, ensure_ascii=False)
    except Exception as e:
        log(f"Could not write {SEEN_PATH}: {e}")


def item_key(it):
    return it["link"] or (it["source"] + "|" + it["title"])


# ----------------------------- Network -----------------------------
def fetch_source(src):
    """Return (items, error_or_None) for one feed. Never raises."""
    import requests
    import feedparser
    try:
        r = requests.get(src["url"], headers={"User-Agent": USER_AGENT},
                         timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return [], f"HTTP {r.status_code}"
        feed = feedparser.parse(r.content)
        if feed.bozo and not feed.entries:
            return [], "not a valid RSS feed"

        cutoff = dt.datetime.utcnow() - dt.timedelta(hours=LOOKBACK_HOURS)
        items = []
        for e in feed.entries:
            title = (e.get("title") or "").strip()
            if not title:
                continue
            published = e.get("published_parsed") or e.get("updated_parsed")
            if published:
                pub_dt = dt.datetime.utcfromtimestamp(calendar.timegm(published))
                if pub_dt < cutoff:
                    continue
                pub_iso = pub_dt.isoformat()
            else:
                pub_iso = ""  # undated: keep it; de-dup stops repeats
            items.append({
                "source": src["name"],
                "title": title,
                "summary": strip_html(e.get("summary", "") or e.get("description", ""))[:400],
                "link": (e.get("link") or "").strip(),
                "published": pub_iso,
                "financial_only": src.get("financial_only", False),
            })
        return items, None
    except Exception as ex:
        return [], str(ex)[:200]


def telegram_send(text):
    import requests
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        log("Telegram not configured; printing instead:\n" + text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chunk in split_text(text, 4000):
        try:
            r = requests.post(url, data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "disable_web_page_preview": True,
            }, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                log(f"Telegram error {r.status_code}: {r.text[:300]}")
        except Exception as e:
            log(f"Telegram send failed: {e}")
        time.sleep(0.4)


def gemini_summarize(items):
    import requests
    today_str = (dt.datetime.utcnow() + dt.timedelta(hours=5)).strftime("%d %B %Y")  # Tashkent

    system = (
        "You are a financial-news editor briefing a treasury professional in Uzbekistan. "
        "You receive raw headlines and snippets (Uzbek, Russian, or English) from Uzbek "
        "news outlets. Produce a concise one-page EXECUTIVE SUMMARY of the financial and "
        "economic news only. Ignore sport, culture, crime, accidents, weather and anything "
        "not economically relevant. Summarize and paraphrase in your own words; never copy "
        "article sentences. Merge the same story when several outlets report it. If a detail "
        "is unclear or unverifiable, omit it rather than guess."
    )

    instructions = f"""Write the brief in {DIGEST_LANGUAGE}.

Format exactly like this — plain text only, no markdown symbols (#, *, _):

UZBEK FINANCIAL BRIEF — {today_str}

TOP STORIES
- <one-line takeaway> - <why it matters, <=12 words> [Source]
(3 to 6 lines, most important first)

BY THEME
(Include only the themes that actually have news. Use these section headers:)
MONETARY & CENTRAL BANK
BANKING & FINANCE
CURRENCY & MARKETS
FISCAL, TAX & BUDGET
TRADE & INVESTMENT
CORPORATE & BUSINESS
- <short bullet with concrete numbers/names/figures> [Source]

Rules: keep the whole brief under 3500 characters; neutral, factual tone;
prefer specific figures over vague phrasing; no opinions or closing commentary.

Items (JSON):
"""
    payload = [{"source": it["source"], "title": it["title"], "summary": it["summary"]}
               for it in items]
    prompt = instructions + json.dumps(payload, ensure_ascii=False)

    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}

    last_err = ""
    for model in GEMINI_MODELS:
        url = GEMINI_URL.format(model=model)
        for attempt in range(2):
            try:
                r = requests.post(url, headers=headers, json=body, timeout=90)
                if r.status_code == 200:
                    return extract_gemini_text(r.json())
                if r.status_code in (429, 500, 503):           # transient: retry
                    last_err = f"{model}: HTTP {r.status_code}"
                    time.sleep(5 * (attempt + 1)); continue
                if r.status_code == 404:                        # bad model name: next model
                    last_err = f"{model}: 404 (model name?)"; break
                last_err = f"{model}: HTTP {r.status_code}: {r.text[:200]}"; break
            except Exception as e:
                last_err = f"{model}: {e}"; time.sleep(3)
    raise RuntimeError("Gemini call failed. Last error: " + last_err)


# ----------------------------- Orchestration -----------------------------
def main():
    missing = [n for n, v in [("GEMINI_API_KEY", GEMINI_API_KEY),
                              ("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
                              ("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)] if not v]
    if missing:
        log("Missing required secrets: " + ", ".join(missing))
        sys.exit(1)

    seen_list = load_seen()
    seen_set = set(seen_list)

    all_items, failures = [], []
    for src in SOURCES:
        items, err = fetch_source(src)
        if err:
            failures.append(f"{src['name']}: {err}")
            log(f"FAIL {src['name']}: {err}")
        else:
            log(f"OK   {src['name']}: {len(items)} recent items")
            all_items.extend(items)

    seen_this_run, filtered = set(), []
    for it in all_items:
        if not is_financial(it):
            continue
        k = item_key(it)
        if k in seen_set or k in seen_this_run:
            continue
        seen_this_run.add(k)
        filtered.append(it)

    filtered.sort(key=lambda x: x["published"], reverse=True)   # newest first
    filtered = filtered[:MAX_ITEMS_TO_LLM]
    log(f"{len(filtered)} financial items after filtering/de-dup")

    footer = ""
    if failures:
        footer = ("\n\n----------\nSources skipped today (edit sources.py):\n"
                  + "\n".join("- " + f for f in failures))

    if not filtered:
        telegram_send(f"UZBEK FINANCIAL BRIEF\n\nNo major new financial news in the "
                      f"last {LOOKBACK_HOURS} hours." + footer)
        save_seen(seen_list)            # keepalive commit, no new links
        return

    try:
        summary = gemini_summarize(filtered)
    except Exception as e:
        telegram_send("UZBEK FINANCIAL BRIEF\n\nCould not generate today's summary.\n"
                      f"Reason: {e}" + footer)
        save_seen(seen_list)
        sys.exit(1)

    telegram_send(summary + footer)

    # mark the items we just summarized as seen; keep newest ~2000, preserve order
    merged, s = [], set()
    for k in seen_list + [item_key(it) for it in filtered]:
        if k not in s:
            s.add(k); merged.append(k)
    save_seen(merged[-2000:])
    log("Done.")


if __name__ == "__main__":
    main()
