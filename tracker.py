#!/usr/bin/env python3
"""
1-hour Agile MVP: keyword tracker for Novotel Century / Le Cafe / AKI Hotel HK
across Instagram / Facebook / Threads (public surface, no API keys required).

How it works (honest coverage model):
  1. Google News RSS + Bing News RSS with keyword + site: operators
     -> captures public IG/FB/Threads posts indexed by search engines (2-60 min lag).
  2. Official Meta/Threads API adapters auto-activate if tokens present in env
     (META_IG_TOKEN, META_FB_PAGE_TOKEN, THREADS_TOKEN) -> owned mentions, real-time.
  3. Normalize -> keyword match -> SQLite dedup -> notify (console/Telegram/webhook)
     -> regenerate dashboard.html.

Usage:
  python3 tracker.py --once        # single poll (default)
  python3 tracker.py --watch       # loop every poll_interval_minutes
  python3 tracker.py --serve       # serve dashboard.html on :8000 + watch in bg thread
  python3 tracker.py --list        # show tracked keywords

Env (optional):
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MATCH_WEBHOOK_URL,
  META_IG_TOKEN (IG Business id via META_IG_USER_ID),
  META_FB_PAGE_TOKEN, META_FB_PAGE_ID, THREADS_TOKEN, THREADS_USER_ID

Stdlib only — no pip install.
"""
import argparse
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
KEYWORDS_PATH = os.path.join(ROOT, "keywords.json")
DB_PATH = os.path.join(ROOT, "matches.db")
DASH_PATH = os.path.join(ROOT, "dashboard.html")
STATE_PATH = os.path.join(ROOT, "state.json")

UA = {"User-Agent": "Mozilla/5.0 (hospitality-keyword-tracker/1.0; +local MVP)"}


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def norm(s):
    s = (s or "").lower()
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def content_hash(text):
    return hashlib.sha256(norm(text).encode("utf-8")).hexdigest()[:16]


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS matches(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      group_id TEXT, phrase TEXT, platform TEXT,
      title TEXT, snippet TEXT, url TEXT UNIQUE,
      source TEXT, published TEXT, detected_at TEXT, hash TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS seen(
      url_hash TEXT PRIMARY KEY, first_seen TEXT)""")
    con.commit()
    return con


def all_phrases(kw):
    out = []
    for g in kw.get("groups", []):
        for p in g.get("phrases", []):
            out.append((g["id"], p))
    return out


def exclusions(kw):
    return [norm(e) for e in kw.get("exclusions", [])]


def rss_urls(phrase, cfg):
    q_general = f'"{phrase}"'
    q_social = f'"{phrase}" (site:instagram.com OR site:facebook.com OR site:threads.net OR site:threads.com)'
    urls = []
    if cfg.get("sources", {}).get("google_news_rss", True):
        for q in (q_general, q_social):
            urls.append(("google-news",
                         "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) +
                         f"&hl=en-US&gl={cfg.get('region','HK')}&ceid={cfg.get('region','HK')}:en"))
    if cfg.get("sources", {}).get("bing_news_rss", True):
        urls.append(("bing-news",
                     "https://www.bing.com/news/search?q=" + urllib.parse.quote(q_general) + "&format=rss"))
    return urls


def fetch(url, timeout):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_rss(xml_text):
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for it in root.iter("item"):
        def t(tag):
            el = it.find(tag)
            return (el.text or "") if el is not None else ""
        title = html.unescape(t("title") or "")
        # strip HTML tags
        title = re.sub(r"<[^>]+>", "", title)
        link = t("link") or ""
        desc = re.sub(r"<[^>]+>", "", html.unescape(t("description") or ""))
        pub = t("pubDate") or t("pubdate") or ""
        items.append({"title": title.strip(), "url": link.strip(),
                      "snippet": desc.strip()[:500], "published": pub.strip()})
    return items


def guess_platform(url, title, snippet):
    u = url.lower()
    if "instagram.com" in u:
        return "instagram"
    if "facebook.com" in u or "fb.watch" in u:
        return "facebook"
    if "threads." in u:
        return "threads"
    blob = (title + " " + snippet).lower()
    if "instagram" in blob[:120]:
        return "instagram?"
    if "facebook" in blob[:120]:
        return "facebook?"
    if "threads" in blob[:120]:
        return "threads?"
    return "web"


def match_phrase(text_norm, phrase_norm):
    # token-subset match: all significant tokens of phrase appear in order (allows cafe/café)
    def toks(s):
        s = s.replace("é", "e")
        return [w for w in re.findall(r"\w+", s) if len(w) > 1]
    pt, tt = toks(phrase_norm), toks(text_norm)
    if not pt:
        return False
    if phrase_norm in text_norm:
        return True
    # ordered subsequence of tokens
    i = 0
    for w in tt:
        if w == pt[i]:
            i += 1
            if i == len(pt):
                return True
    # short-phrase fallback: e.g. "AKI Hotel" needs both tokens adjacent-ish
    if len(pt) <= 2:
        return all(w in tt for w in pt)
    return False


def notify_telegram(text):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not tok or not chat:
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000]}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                     data=data, headers=UA)
        urllib.request.urlopen(req, timeout=10).read()
        return True
    except Exception as e:
        print(f"[telegram] failed: {e}")
        return False


def notify_webhook(payload):
    url = os.environ.get("MATCH_WEBHOOK_URL", "")
    cfg = load_json(CONFIG_PATH, {})
    if not url:
        url = cfg.get("notifications", {}).get("webhook", {}).get("url", "")
    if not url:
        return False
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json", **UA})
        urllib.request.urlopen(req, timeout=10).read()
        return True
    except Exception as e:
        print(f"[webhook] failed: {e}")
        return False


def poll_official_apis():
    """Stub adapters: activate only when tokens exist. Returns [] otherwise."""
    out = []
    # Instagram Graph: mentions of connected Business account
    ig_tok = os.environ.get("META_IG_TOKEN", "")
    ig_uid = os.environ.get("META_IG_USER_ID", "")
    if ig_tok and ig_uid:
        try:
            url = (f"https://graph.facebook.com/v21.0/{ig_uid}/mentions"
                   f"?fields=id,caption,like_count,timestamp,permalink&access_token={ig_tok}")
            raw = fetch(url, 15)
            for m in json.loads(raw).get("data", []):
                out.append({"title": (m.get("caption") or "")[:140], "url": m.get("permalink", ""),
                            "snippet": m.get("caption", "")[:500],
                            "published": m.get("timestamp", ""), "source": "instagram-graph"})
        except Exception as e:
            print(f"[ig-graph] skipped: {e}")
    # Facebook Page feed (owned pages)
    fb_tok = os.environ.get("META_FB_PAGE_TOKEN", "")
    fb_pid = os.environ.get("META_FB_PAGE_ID", "")
    if fb_tok and fb_pid:
        try:
            url = (f"https://graph.facebook.com/v21.0/{fb_pid}/feed"
                   f"?fields=message,created_time,permalink_url&limit=25&access_token={fb_tok}")
            raw = fetch(url, 15)
            for m in json.loads(raw).get("data", []):
                out.append({"title": (m.get("message") or "")[:140],
                            "url": m.get("permalink_url", ""),
                            "snippet": (m.get("message") or "")[:500],
                            "published": m.get("created_time", ""), "source": "facebook-graph"})
        except Exception as e:
            print(f"[fb-graph] skipped: {e}")
    # Threads mentions
    th_tok = os.environ.get("THREADS_TOKEN", "")
    th_uid = os.environ.get("THREADS_USER_ID", "")
    if th_tok and th_uid:
        try:
            url = (f"https://graph.threads.net/v1.0/{th_uid}/mentions"
                   f"?fields=id,text,permalink,timestamp&access_token={th_tok}")
            raw = fetch(url, 15)
            for m in json.loads(raw).get("data", []):
                out.append({"title": (m.get("text") or "")[:140], "url": m.get("permalink", ""),
                            "snippet": (m.get("text") or "")[:500],
                            "published": m.get("timestamp", ""), "source": "threads-graph"})
        except Exception as e:
            print(f"[threads-graph] skipped: {e}")
    return out


def run_once(verbose=True):
    cfg = load_json(CONFIG_PATH, {})
    kw = load_json(KEYWORDS_PATH, {})
    phrases = all_phrases(kw)
    excl = exclusions(kw)
    timeout = cfg.get("request_timeout_sec", 15)
    maxn = cfg.get("max_items_per_query", 20)
    con = init_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new_matches, checked = 0, 0

    for group_id, phrase in phrases:
        for source, url in rss_urls(phrase, cfg):
            try:
                items = parse_rss(fetch(url, timeout))[:maxn]
            except Exception as e:
                if verbose:
                    print(f"[fetch] {source} '{phrase}': {e}")
                continue
            for it in items:
                checked += 1
                blob = norm(it["title"] + " " + it["snippet"])
                if any(x in blob for x in excl):
                    continue
                if not match_phrase(blob, norm(phrase)):
                    continue
                uh = hashlib.sha256(it["url"].encode()).hexdigest()[:24]
                cur = con.execute("SELECT 1 FROM seen WHERE url_hash=?", (uh,)).fetchone()
                if cur:
                    continue
                plat = guess_platform(it["url"], it["title"], it["snippet"])
                try:
                    con.execute("INSERT INTO matches(group_id,phrase,platform,title,snippet,url,source,published,detected_at,hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                (group_id, phrase, plat, it["title"][:300], it["snippet"],
                                 it["url"], source, it["published"], now, content_hash(blob)))
                    con.execute("INSERT INTO seen(url_hash,first_seen) VALUES(?,?)", (uh, now))
                    con.commit()
                except sqlite3.IntegrityError:
                    con.execute("INSERT OR IGNORE INTO seen(url_hash,first_seen) VALUES(?,?)", (uh, now))
                    con.commit()
                    continue
                new_matches += 1
                msg = f"[{plat}] ({group_id} | '{phrase}') {it['title']}\n{it['url']}"
                print("NEW ▶ " + msg)
                notify_telegram("🔔 " + msg)
                notify_webhook({"group": group_id, "phrase": phrase, "platform": plat, **it})

    # official APIs (owned mentions — no-op without tokens)
    for it in poll_official_apis():
        blob = norm(it["title"] + " " + it["snippet"])
        for group_id, phrase in phrases:
            if match_phrase(blob, norm(phrase)):
                uh = hashlib.sha256(it["url"].encode()).hexdigest()[:24]
                if not con.execute("SELECT 1 FROM seen WHERE url_hash=?", (uh,)).fetchone():
                    plat = guess_platform(it["url"], it["title"], it["snippet"])
                    try:
                        con.execute("INSERT INTO matches(group_id,phrase,platform,title,snippet,url,source,published,detected_at,hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                    (group_id, phrase, plat, it["title"][:300], it["snippet"],
                                     it["url"], it.get("source", "official"), it["published"], now, content_hash(blob)))
                        con.execute("INSERT INTO seen(url_hash,first_seen) VALUES(?,?)", (uh, now))
                        con.commit()
                        new_matches += 1
                        print("NEW ▶ [official] " + it["title"] + "\n" + it["url"])
                    except sqlite3.IntegrityError:
                        pass

    total = con.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    con.close()
    # persist state
    state = load_json(STATE_PATH, {})
    state["last_run"] = now
    state["last_checked"] = checked
    state["last_new"] = new_matches
    state["total_matches"] = total
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    build_dashboard()
    if verbose:
        print(f"\nDone: checked={checked} new={new_matches} total={total} @ {now}")
    return new_matches, total


def build_dashboard():
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute("SELECT group_id,phrase,platform,title,snippet,url,source,published,detected_at FROM matches ORDER BY id DESC LIMIT 200").fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    state = load_json(STATE_PATH, {})
    kw = load_json(KEYWORDS_PATH, {})
    cards = ""
    for g, ph, plat, ti, sn, url, src, pub, det in rows:
        cards += f"""<div class="card"><div class="meta"><span class="plat">{html.escape(plat or '')}</span>
<span class="grp">{html.escape(g or '')}</span><span class="src">{html.escape(src or '')}</span></div>
<div class="title"><a href="{html.escape(url or '#')}" target="_blank" rel="noopener">{html.escape(ti or '(no title)')}</a></div>
<div class="sn">{html.escape(sn or '')}</div>
<div class="foot">match: <b>{html.escape(ph or '')}</b> · published: {html.escape(pub or '')} · detected: {html.escape(det or '')}</div></div>\n"""
    if not cards:
        cards = "<p class='empty'>No matches yet — run <code>python3 tracker.py --once</code>. RSS coverage has a search-engine indexing lag (minutes–hours); official API adapters activate when tokens are set (see README).</p>"
    groups = "".join(f"<li><b>{html.escape(g.get('id',''))}</b> — {', '.join(html.escape(p) for p in g.get('phrases',[]))}</li>" for g in kw.get("groups", []))
    html_doc = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hotel Keyword Tracker — Novotel Century / Le Cafe / AKI</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;background:#fafafa;color:#222}}
.card{{background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:12px 14px;margin:12px 0}}
.plat{{background:#111;color:#fff;border-radius:6px;padding:2px 8px;font-size:12px;margin-right:6px}}
.grp{{background:#eef;font-size:12px;border-radius:6px;padding:2px 8px;margin-right:6px}}
.src{{color:#888;font-size:12px}}.title{{font-weight:600;margin:8px 0}}.sn{{color:#444;font-size:14px}}.foot{{color:#777;font-size:12px;margin-top:6px}}
.top{{display:flex;justify-content:space-between;align-items:center}}.empty{{color:#666}}code{{background:#eee;padding:1px 5px;border-radius:4px}}</style></head>
<body><div class="top"><h2>🏨 Keyword Tracker — Wanchai Hotels</h2><span>last run: {html.escape(state.get('last_run','—'))} · total: {state.get('total_matches','?')}</span></div>
<p>Tracking Instagram / Facebook / Threads <i>public indexed surface</i> via News-RSS + official API adapters (activate with tokens). Poll every ~10 min: <code>python3 tracker.py --watch</code></p>
<h3>Keywords</h3><ul>{groups}</ul><h3>Latest matches ({len(rows)})</h3>{cards}
<p style="color:#888;font-size:12px">Coverage note: Meta offers no public global keyword API (CrowdTangle shut down Aug 2024). RSS catches indexed public posts; connect IG/FB/Threads tokens for real-time owned mentions; add a licensed vendor (Brandwatch/Meltwater) for full firehose.</p></body></html>"""
    with open(DASH_PATH, "w", encoding="utf-8") as f:
        f.write(html_doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="single poll")
    ap.add_argument("--watch", action="store_true", help="loop forever")
    ap.add_argument("--serve", action="store_true", help="watch + serve dashboard on :8000")
    ap.add_argument("--list", action="store_true", help="list keywords")
    ap.add_argument("--interval", type=float, default=None)
    a = ap.parse_args()
    if a.list:
        kw = load_json(KEYWORDS_PATH, {})
        for g in kw.get("groups", []):
            print(f"[{g['id']}] {g.get('label','')}")
            for p in g.get("phrases", []):
                print(f"   - {p}")
        return
    if a.serve:
        import threading
        from http.server import SimpleHTTPRequestHandler, HTTPServer
        cfg = load_json(CONFIG_PATH, {})
        iv = (a.interval or cfg.get("poll_interval_minutes", 10)) * 60
        def loop():
            while True:
                try:
                    run_once(verbose=True)
                except Exception as e:
                    print(f"[watch] error: {e}")
                time.sleep(iv)
        threading.Thread(target=loop, daemon=True).start()
        os.chdir(ROOT)
        print("Dashboard: http://localhost:8000/dashboard.html (watching…)")
        HTTPServer(("0.0.0.0", 8000), SimpleHTTPRequestHandler).serve_forever()
        return
    if a.watch:
        cfg = load_json(CONFIG_PATH, {})
        iv = (a.interval or cfg.get("poll_interval_minutes", 10)) * 60
        while True:
            try:
                run_once(verbose=True)
            except Exception as e:
                print(f"[watch] error: {e}")
            print(f"sleep {iv/60:.1f} min…")
            time.sleep(iv)
        return
    run_once(verbose=True)


if __name__ == "__main__":
    main()
