# ☕ Social Tracker for Le Cafe

Tracks public Instagram / Facebook / Threads mentions of **Le Cafe (Novotel Century, Wanchai)** —
plus Novotel Century context keywords — and notifies you of new matches.

Two ways to run, pick either (or both):

## A. Webpage — click to run (no install)

1. Push this repo to GitHub (commands below).
2. Repo **Settings → Pages → Deploy from a branch → `main` + `/ (root)` → Save**.
3. Open `https://<YOU>.github.io/<REPO>/` → **▶ Run scan now**.
   - Runs fully in the browser: Google News RSS (with
     `site:instagram.com OR site:facebook.com OR site:threads.net` filters) via CORS proxy,
     keyword match, `localStorage` dedup, optional browser notifications, 10-min watch mode.
   - The page also shows the latest **scheduled-scan results** produced by GitHub Actions.

## B. GitHub Actions — scheduled background scans

- Workflow `.github/workflows/tracker.yml` runs `tracker.py --once` **every 30 min**
  and on demand via **Actions → tracker → Run workflow**.
- Each run commits fresh `docs/latest-matches.json` (+ `dashboard.html`), which the webpage displays.
- First enable the workflow: push, then open the Actions tab and click **“Run workflow”** once
  (scheduled runs activate after the first push).

## C. Local Python backend (real-time owned mentions)

```bash
./run.sh                 # single poll
python3 tracker.py --watch
python3 tracker.py --serve   # dashboard at http://localhost:8000/dashboard.html
python3 tracker.py --watchlist  # comment-watchlist status
```

## D. 💬 Comment tracking (Phase 1)

No Meta API searches *all* public comments by keyword — so comments work in two circles:

- **Watchlist posts** (`watchlist.json`): paste public IG/FB post URLs (e.g. a viral Le Cafe review).
  Each run, the tracker crawls **new comments** on those posts, matches keywords locally,
  and notifies with parent-post context (`↳ on: <post>`). Beyond 3 matches/post/day,
  extras are stored quietly as digest (see `comments.per_post_cap` in `config.json`).
- **What unlocks comment bodies:** `META_IG_TOKEN` (+ `media_id` on the entry) for Instagram,
  `META_FB_PAGE_TOKEN` (+ `post_id`) for Facebook. Without tokens the run honestly reports
  `⏳ … needs media_id/post_id or tokens` and only records lightweight title context.
- Webpage has a **📌 Track this post** panel (browser-side list — mirror URLs into
  `watchlist.json` for backend crawling). Dashboard shows 💬 comment cards with parent links.
- `matches.db` is committed by the Actions workflow so dedup state survives between
  scheduled runs (public post snippets only — fine for a private repo).

Optional real-time adapters activate with tokens (no code change):

```bash
export META_IG_TOKEN=... META_IG_USER_ID=...
export META_FB_PAGE_TOKEN=... META_FB_PAGE_ID=...
export THREADS_TOKEN=... THREADS_USER_ID=...
export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...   # instant alerts
```

## Push to GitHub (run these once)

```bash
cd "/root/social-tracker-for-le-cafe"
git init -b main
git add -A
git commit -m "Le Cafe social tracker + runnable webpage"
gh repo create <REPO> --public --source=. --push   # needs: gh auth login
# …or without gh CLI:
# git remote add origin https://github.com/<YOU>/<REPO>.git
# git push -u origin main
```

Then enable Pages (Settings → Pages → `main` / root) and run the workflow once from Actions.

## Files

| File | Purpose |
|---|---|
| `index.html` | runnable webpage (GitHub Pages) — client-side scan + results |
| `tracker.py` | Python backend: RSS → match → SQLite dedup → notify |
| `keywords.json` | Le Cafe-first keyword groups + exclusions (Hyderabad/India pre-excluded) |
| `.github/workflows/tracker.yml` | scheduled scan + on-demand run, commits JSON feed for the page |
| `docs/latest-matches.json` | feed the webpage reads for scheduled results |
| `config.json`, `run.sh` | backend config + runner |

Coverage note: Meta has no public global keyword API (CrowdTangle retired Aug 2024).
This repo covers the indexed public surface immediately; full firehose needs a licensed vendor.
