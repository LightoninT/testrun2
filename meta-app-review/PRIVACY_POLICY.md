# Privacy Policy — [HOTEL NAME] Social Keyword Tracker

> Boilerplate for Meta App Review. Replace every `[BRACKET]` item, host this file at a
> public URL (hotel website or repo Pages), and paste the URL into the app's
> Settings → Basic → Privacy Policy URL field. Last updated: [DATE].

**1. What this app does.** The Tracker monitors public mentions, tags and comments on
[Hotel]'s own Instagram Business account, Facebook Page and Threads profile for
staff-defined service keywords (e.g. restaurant and stay-experience terms), so duty
staff can respond to guest feedback promptly.

**2. Data we collect (minimum necessary).** For each matching public item only: the
public text snippet, its permalink URL, the author's public handle, and the platform
timestamp. We do **not** collect private messages, follower lists, or any non-public
profile data.

**3. How we use it.** Internal service-recovery review by hotel staff on the tracker's
web dashboard. No advertising, no profiling, no sale or sharing with third parties.

**4. Retention.** Matches are kept 30–90 days (`dedup_ttl_days` in config), then deleted.
Aggregated counts without personal data may be kept for service-quality statistics.

**5. Your rights.** Authors may request correction or deletion of their data at any time
via [CONTACT EMAIL]. Platform deletion requests are honoured automatically through
Meta's Data Deletion Callback (`deletion_callback.py` in this repo): when Meta notifies
us that a user removed the app or deleted content, the matching rows are purged and a
confirmation code is returned.

**6. Security.** OAuth tokens are stored server-side only (never in source control),
transmitted over TLS, and rotated at least yearly. Access is limited to hotel duty staff.

**7. Contact.** Data controller: [HOTEL LEGAL NAME, ADDRESS]. Email: [CONTACT EMAIL].
