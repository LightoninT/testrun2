# Meta App Review — application pack for this tracker (100% free tier)

Official Meta APIs cost $0, but the price is paperwork. This pack maps each tracker
feature to the exact permission/scope to request, plus the artifacts reviewers ask for.
Expect 1–2 weeks end-to-end (Business verification is the slow part).

## 0. What you are applying for

| Tracker feature | Product to add | Permissions / scopes | Notes |
|---|---|---|---|
| IG hashtag discovery (`ig_hashtag_search`, `recent_media`) | Instagram Graph API | `instagram_basic` | Needs an IG **Business/Creator** account linked to a FB Page |
| IG owned mentions/tags (`mentions`, `tags`) | Instagram Graph API | `instagram_basic` | Real-time via webhooks |
| IG comment read/hide/reply on watchlist | Instagram Graph API | `instagram_basic` + `instagram_manage_comments` | Justify moderation use-case |
| FB Page posts + `feed` webhook (posts **and comments**) | Facebook Login + Pages API | `pages_show_list`, `pages_read_engagement`, `pages_read_user_content`, `pages_manage_posts` (only if replying) | Admin role on the hotel Page |
| Threads mentions/replies | Threads API | `threads_basic`, `threads_manage_replies` | Youngest API — keep the request narrow |
| Login for hotel staff | Facebook Login for Business | standard | System-user token for cron (never expires if configured) |

Request the **minimum** set first (basic + read). Add `manage_*` in a second review round —
narrow requests pass faster.

## 1. Step-by-step

1. **developers.facebook.com → Create App** (type: Business). Note the App ID.
2. **Add products:** Instagram (Graph API), Facebook Login for Business, Threads.
3. **Link assets:** Meta Business Suite — verify the business (utility bill / business
   registration for the hotel; 3–10 days). Connect the IG Business account to the FB Page.
4. **Settings → Basic:** fill Privacy Policy URL (use `meta-app-review/PRIVACY_POLICY.md`
   content hosted anywhere public, e.g. this repo's GitHub Pages or the hotel site),
   App Icon (1024×1024), Category (Business), and **Data Deletion Callback URL**
   (host `deletion_callback.py` on your always-on box; reviewers ping it).
5. **Roles → Test Users:** create 2 test users (one Page admin, one commenter) so the
   reviewer can reproduce without touching the real hotel page.
6. **Record the screencast (2–4 min, required per permission):**
   - 0:00 log in with a test user, show granted scopes on the consent screen;
   - 0:30 run `python3 tracker.py --once` → show a mention/comment arriving;
   - 1:30 trigger a keyword match → show it landing at the top of the webpage
     dashboard (📊 Latest updates, NEW highlight);
   - 2:30 open `dashboard.html`, show only public snippet + permalink stored
     (say out loud: "we store the minimum; authors can request deletion").
7. **App Review → Requests:** one request per permission with the use-case text:
   > "Hospitality reputation monitoring for [Hotel]. We read public mentions, tags and
   > comments on our own Business assets to detect guest feedback containing tracked
   > service keywords, and notify duty staff. We store only the public snippet,
   > permalink and timestamp for 30–90 days; no ads, no resale, deletion on request
   > via the Data Deletion callback."
8. **Token hygiene for cron:** exchange the short-lived token for a 60-day token, then a
   never-expiring **system user token** (Business Settings → System Users) and put it in
   `.tracker-env` — never in git. Set a calendar reminder to rotate yearly.

## 2. Common rejection reasons (and fixes)

- "Unclear use" → re-record the screencast showing the *hotel* context, not generic API calls.
- Missing Privacy Policy / deletion callback → both are in this folder; host them first.
- Asking for `manage_*` + `read_*` together → split into two rounds.
- Test credentials missing → always attach the test-user login in the request notes.

## 3. After approval

- Keep the app in **Live mode**; monitor **App Dashboard → Alerts** for rate-limit
  warnings (our `rate_limits.graph_calls_per_hour: 200` SQLite bucket keeps you inside).
- Any new permission = new review round. Design keyword/matching changes to need none.
