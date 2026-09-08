# ☕ Social Tracker for Le Cafe

Tracks public Instagram / Facebook / Threads mentions of **Le Cafe (Novotel Century, Wanchai)** —
plus Novotel Century context keywords — **dashboard-first: every update lands at the top of
the webpage** (`index.html` 📊 Latest updates panel). No push channels, no accounts, nothing to install.

Two ways to run, pick either (or both):

## A. Webpage — click to run (no install)

1. Push this repo to GitHub (commands below).
2. Repo **Settings → Pages → Deploy from a branch → `main` + `/ (root)` → Save**.
3. Open `https://<YOU>.github.io/<REPO>/` → top panel **📊 Latest updates** shows the feed;
   **▶ Run scan now** runs a live in-browser scan (Google News RSS with
   `site:instagram.com OR site:facebook.com OR site:threads.net` filters via CORS proxy,
   keyword match, `localStorage` dedup, 5/10/30-min watch mode) merged into the same top list.

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

## E. 🚨 PR-crisis runbook (5-minute posture)

Crisis mode = complaint keywords ON (`crisis-watch` group: food poisoning / 曱甴 / 食物中毒…)
+ dashboard shows ONLY content < 24h old at top (stale index resurfaces are stored, not surfaced).

| Option | How | Best for |
|---|---|---|
| **A. One-click scan** | Repo → **Actions → crisis-scan → Run workflow** (works from your phone) | "Check right now" |
| **B. Continuous 5-min** | Uncomment the `schedule: */5` block in `.github/workflows/crisis.yml`, push. Re-comment when over | Full crisis watch |
| **C. Local/VPS 5-min** | `python3 tracker.py --watch --interval 5 --crisis` (or `TRACKER_CRISIS=1`) | No Actions minutes burned |
| **D. Webpage** | Open `index.html` → interval **every 5 min (crisis)** → Watch | Desk monitoring |

To unlock comment bodies + owned mentions, set these repo **Secrets**
(Settings → Secrets → Actions) — both workflows pass them through, empty = gracefully skipped:

- `META_IG_TOKEN`/`META_IG_USER_ID`, `META_FB_PAGE_TOKEN`/`META_FB_PAGE_ID`,
  `THREADS_TOKEN`/`THREADS_USER_ID`

During a crisis, keep the dashboard open — it auto-refreshes the feed every 5 min,
and the ⏱ Watch mode re-scans live on the same cadence. New items get a green
**NEW** pill + **🚨 crisis** badge until you press **✓ Mark all seen**.

Stand down: flip `crisis_mode.enabled` back to false (or delete the env flag), re-comment the
`*/5` schedule, and switch local watch back to `--interval 10`.

Honest limits at 5-min cadence: RSS still carries search-index lag (days for social posts —
see README §delay note), Google tolerates ~20 reqs/cycle but may 429 under load (cycles degrade
gracefully — a skipped cycle just retries in 5 min), and Actions `schedule` can slip a few
minutes when GitHub is busy. True real-time on your own accounts needs the Meta-token-fed
paths (owned mentions via official APIs, watchlist comment crawl).

## D. 💬 Comment tracking (Phase 1)

No Meta API searches *all* public comments by keyword — so comments work in two circles:

- **Watchlist posts** (`watchlist.json`): paste public IG/FB post URLs (e.g. a viral Le Cafe review).
  Each run, the tracker crawls **new comments** on those posts, matches keywords locally,
  and surfaces them with parent-post context (`↳ on: <post>`). Beyond 3 matches/post/day,
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
```

## F. $0 production setup (official APIs + cron, no paid services)

| Layer | Free choice | In this repo |
|---|---|---|
| Meta/Threads API calls | $0 (standard Graph/Threads usage is free) | `tracker.py` official adapters — dormant until tokens set |
| Scheduler | $0 `cron`/systemd on existing PC, hotel server, or free tier (Oracle Always Free / AWS free) | `cron/crontab.example`, `cron/tracker.{service,timer}` |
| Updates surface | $0 webpage dashboard (top panel, auto-refresh) | `index.html` 📊 Latest updates fed by `docs/latest-matches.json`; secrets only for Meta API tokens via `.env.example` → `~/.tracker-env` (chmod 600) |
| Rate safety | 200 Graph calls/hr enforced in code | `rate_limits` in `config.json` + SQLite `api_budget` bucket — crawlers defer, never burn the token |

Real costs to budget instead: **time** — Meta App Review (Business verification + screencast,
1–2 weeks; everything prepared in `meta-app-review/`: permission checklist, privacy-policy
boilerplate, stdlib deletion-callback server), and **scope honesty** (official APIs cover
your own assets + hashtag discovery, not the whole internet — broad firehose stays a paid
vendor decision, documented in the plan).

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
| `index.html` | webpage dashboard — 📊 Latest updates top panel (feed + live scans, filters, NEW highlighting) |
| `tracker.py` | Python backend: RSS → match → SQLite dedup → console log → dashboard feed |
| `keywords.json` | Le Cafe-first keyword groups + exclusions (Hyderabad/India pre-excluded) |
| `.github/workflows/tracker.yml` | scheduled scan + on-demand run, commits JSON feed for the page |
| `docs/latest-matches.json` | feed the webpage reads for scheduled results |
| `config.json`, `run.sh` | backend config + runner |

Coverage note: Meta has no public global keyword API (CrowdTangle retired Aug 2024).
This repo covers the indexed public surface immediately; full firehose needs a licensed vendor.
