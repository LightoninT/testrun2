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
```

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
