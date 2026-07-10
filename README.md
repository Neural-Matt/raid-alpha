# Raid Alpha

A lead generation + outreach CRM for Neural Cloud Enterprise. Runs on Vercel
with Supabase as the database, GitHub as the staging/deploy pipeline — or
locally against any Postgres database (including your Supabase project).

What it does:

0. **Classifies every lead into one of NCE's 12 official service lines**
   (Custom Software Development, AI Solutions & Intelligent Automation, Data
   Analytics/BI/Research, Cloud & Infrastructure, Call Center/VoIP,
   Healthcare & Pharmacy Tech, Insurance Tech, Business Process Automation,
   Web & Mobile App Development, UI/UX Design, Networking & Connectivity,
   Training & Capacity Building) — see **Settings → "Which services does
   Neural Cloud offer?"** to toggle which of the 12 are currently in scope.
   Unticking a service excludes it from classification (a lead can only ever
   land in a service you've left checked) and every keyword-driven source
   below defaults to searching across whichever services are active. The
   full keyword catalog for all 12 lives in `services_catalog.py` — it's the
   single source of truth every source module and the scorer both read from.
1. **Pull leads** at the press of a button from legal, official sources:
   - ReliefWeb API (consultancy postings from NGOs/UN agencies — a curated
     slice of NCE's 12 service lines weighted toward what that sector buys —
     with application deadline and how-to-apply text where the posting has it)
   - World Bank Projects API (active funded projects across statistics,
     health, education, digital and governance in your region)
   - World Bank Procurement Notices API (live open tenders across all 12
     service lines — real deadlines and named procurement contacts with
     email/phone, straight from the notice)
   - ZPPA OCDS bulk data (open Zambian government tenders, filtered to
     whichever of NCE's 12 service lines are active, with deadline +
     submission method where published)
   - Grants.gov (US federal funding opportunities — many open to international
     applicants — enriched with the actual grants contact, deadline, funding
     ceiling and eligibility text)
   - TED — Tenders Electronic Daily (official EU public procurement — live
     tenders from European Commission DGs, national ministries and
     development agencies, OR-matched across several service lines at once,
     with real deadlines)
   - SAM.gov (US federal contract solicitations, incl. USAID/State Dept
     procurements — requires your own free SAM.gov API key)
   - SADC procurement opportunities (official regional tenders from the SADC
     Secretariat — real deadlines and named procurement contacts with
     email/phone; a lightweight, transparently-identified public-page reader
     since no API exists — see "A note on scraping" below)
   - eTenders South Africa (National Treasury's tender portal — live open
     tenders nationwide across all 12 service lines, with named contacts,
     email, phone, bid documents and closing dates; reads the same public
     JSON the portal's own search page uses, no formal API exists — see
     "A note on scraping" below)
   - GoZambiaJobs (Zambia's largest job board — flags companies hiring across
     any of NCE's 12 service lines as a complementary-support signal; a
     lightweight, transparently-identified public-page reader since no API
     exists — see "A note on scraping" below)
   - Any RSS/Atom feeds you add (tender boards, Google Alerts = the widest net)
   - Apollo.io People Search (decision-maker contacts, your API key)
   - Hunter.io Domain Search (published emails at target companies, your API key)
2. **Auto-enrich & score** every lead: service segment, 0–100 fit score, a
   tentative deal value, application deadline and how-to-apply instructions
   where the source provides them — all pre-populated in the pipeline and
   fully editable.
3. **Intelligent service matching (free, optional)**: define the services your
   business offers in plain language, and a Gemini-powered bot scores every
   incoming lead against them with a fit score and short reasoning — no
   paid API required.
4. **Gmail bridge**: draft from templates, send from your own Gmail, and scan
   your inbox — replies auto-bump lead stages and asks like "send a proposal"
   or "let's schedule a call" become to-dos automatically.
5. **Full tracking**: pipeline stages, follow-up dates, activity logs, to-dos,
   templates, search/filter, and dashboard stats including total pipeline value.

---

## 1. Install & run locally (5 minutes)

You need Python 3.10+ (python.org) and a [Supabase](https://supabase.com)
project (free tier is fine — Project Settings → Database → Connection string,
use the **Transaction pooler** URI on port 6543). Then, in this folder:

```bash
pip install -r requirements.txt
export POSTGRES_URL="postgresql://postgres.xxxx:PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres"
python app.py
```

Open **http://127.0.0.1:8765** in your browser. That's the CRM.

The app binds to 127.0.0.1 only — nothing on your machine can reach it from
the network unless you deploy it. Outbound calls (source APIs, Gmail,
Supabase) work normally regardless, since that's independent of the bind
address.

## 1b. Deploy to Vercel + Supabase, with GitHub for staging

**Architecture:** GitHub hosts the code and drives two Vercel environments —
push to `staging` for a preview deployment to test against, merge to `main`
for production. Supabase is the database for both (use two separate Supabase
projects if you want staging data fully isolated from production).

1. **Supabase:** create a project (or two — one for staging, one for
   production) at supabase.com. Grab the **Transaction pooler** connection
   string (port 6543) from Project Settings → Database — this is your
   `POSTGRES_URL`.
2. **Push to GitHub** (already done for this repo — see below), then
   **import it in Vercel** (New Project → select the repo). Vercel
   auto-detects the Python app via `vercel.json` + `api/index.py`.
3. **Environment variables** (Project → Settings → Environment Variables —
   set separately per Vercel environment: Production / Preview):
   - `POSTGRES_URL` — your Supabase pooler connection string (production DB
     for the Production environment, staging DB for Preview if using two).
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` — only
     needed if you want the Gmail bridge live on the deployed site (see
     step 3 below).
   - `GEMINI_API_KEY` — only needed for the service-matching bot (see step 3b).
   - `CRON_SECRET` — any random string you generate yourself. Locks down the
     scheduled-run endpoint (see below) so only Vercel's own cron trigger can
     call it.
4. **Set the Production Branch to `main`** (Project → Settings → Git). Any
   push to `staging` (or any other branch) automatically gets its own Preview
   deployment URL — test there before merging to `main`.
5. Redeploy after adding env vars. First load creates tables automatically
   (same `db.init()` as local) in whichever Supabase project `POSTGRES_URL`
   points to.

Note the deployed app has no persistent local disk — everything (leads,
templates, settings, the Gmail token) lives in Supabase Postgres, which is
what makes it safe to redeploy or run across multiple serverless invocations.

### Working with staging

```bash
git checkout -b staging
git push -u origin staging      # Vercel creates a Preview deployment automatically
# ...make changes, push to staging, test on the preview URL...
git checkout main
git merge staging
git push                        # promotes to production
```

### Scheduled runs (Vercel Cron)

Once deployed, `vercel.json` schedules a daily run of every source + a Gmail
sync at 06:00 UTC via `GET /api/cron/run-all` — you don't have to press "Run
all sources" yourself every day. Set a `CRON_SECRET` env var (any random
string) so the endpoint only responds to Vercel's own scheduled trigger,
which automatically sends it as a Bearer token. Change the schedule by
editing the cron `schedule` (standard cron syntax) in `vercel.json`. Note:
Vercel's Hobby (free) plan limits cron jobs to once-daily triggers — this is
already within that limit.

## 2. First pull

First, check **Settings → "Which services does Neural Cloud offer?"** — all
12 are active by default. Untick anything you're not taking on right now;
every keyword-driven source below (and the scorer itself) respects this list.

Then go to **Sources → Run all sources**. ReliefWeb, World Bank (both projects
and tenders), ZPPA, and Grants.gov need no keys, so you'll have a scored
pipeline within a minute.

To widen the net:

- **Google Alerts trick (free, powerful):** at google.com/alerts create alerts
  like `"request for proposals" "monitoring and evaluation"` or
  `"data analytics" tender Zambia`, set *Deliver to: RSS feed*, and paste the
  feed URLs into **Settings → RSS feed URLs**. Now Google's index feeds your CRM.
  This is also the practical way to track broader international tender
  aggregators (e.g. dgMarket) — they block automated scraping/API access, but
  their listings are indexable, so a Google Alert on your target keywords
  picks them up anyway.
- **Apollo** (apollo.io → Settings → API): paste your API key, set target titles
  and locations in Settings, then run the Apollo source.
- **Hunter** (hunter.io → API): paste your key and list target-company domains.
- **ZPPA**: pulls the most recent month of Zambia's official government tender
  data and keeps only tenders matching **Settings → ZPPA keyword filter**
  (defaults to all active service lines' keywords — ZPPA covers every sector
  of government spending, so *some* filter is essential or it floods the
  pipeline with unrelated tenders like food and vehicle procurement).
- **World Bank open tenders**: live procurement notices with real deadlines
  and named contacts. Defaults to your priority African countries — flip
  **Settings → Limit WB tenders to your priority countries?** to "No" for
  worldwide coverage, and adjust **World Bank tender search terms** to widen
  or narrow the keyword match.
- **Grants.gov**: US federal funding opportunities, many explicitly open to
  international/non-US applicants (check each listing's eligibility text,
  captured under "How to apply" on the lead). Adjust **Grants.gov search
  keywords** in Settings.
- **TED (EU)**: no key needed. Searches EU procurement notice *descriptions*
  (not just titles, since titles are mostly generic category names) —
  adjust **TED (EU) search keywords** and **TED days back** in Settings.
- **SAM.gov**: needs your own free API key. Log into sam.gov (create an
  account if needed) → Account Details → request a public API key → paste
  it into **Settings → SAM.gov API key**. Note: this module is built to
  SAM.gov's documented API shape but hasn't been live-verified end-to-end
  (only the account holder can get a key to test with) — if a pull errors,
  the response shape may have drifted; tell your assistant and it can fix it.
- **SADC**: no key needed. Reads the SADC Secretariat's public procurement
  opportunities page directly — typically only a handful of notices are open
  at once, so there's no keyword filter to configure.
- **eTenders SA**: no key needed. Adjust **eTenders SA keyword filter** in
  Settings — pulls the full list of currently-open national tenders (~1,800
  at any time) and filters locally by keyword (defaults to all active
  service lines), since the portal's own search endpoint ignores the filter
  value it's sent (verified: it always returns every record regardless of
  what you search).
- **GoZambiaJobs**: no key needed. Adjust **GoZambiaJobs keyword filter** in
  Settings (defaults to all active service lines) — a general job board
  needs *some* filter or every accounting/sales/driving vacancy in Zambia
  floods the pipeline alongside the handful of relevant tech roles.

### A note on scraping

SADC, eTenders SA and GoZambiaJobs are the three sources above with no
formal, documented API — everything else is an official API, verified live
where a free tier exists. Before adding any of them, its `robots.txt` and
published terms were checked for any prohibition on automated access; none
was found for any of the three (SADC and eTenders SA have no legal-notice/
terms page at all; GoZambiaJobs's robots.txt only disallows its own `/rss/`
path and sets a polite 1-second crawl delay). eTenders SA is a slightly
different case from the other two — rather than parsing rendered HTML, it
calls the same unauthenticated JSON endpoint the portal's own search page
calls, which returns the identical data any visitor's browser receives. All
three identify themselves honestly via a descriptive `User-Agent` rather
than pretending to be a browser, and only read the public listing + detail
data needed.

Several other sites researched for this project were deliberately **not**
integrated: some actively block automated access (Cloudflare bot challenges),
one (comesa.int) explicitly disallows AI crawlers including Claude in its
`robots.txt`, and several job boards (BrighterMonday, Jobberman, Pnet) and
directories explicitly disallow crawling the exact pages needed in their
`robots.txt`. Those signals are respected — don't remove this check as a
"fix" if a future source addition seems to be failing for the same reason.

**Facebook is a hard no.** Its `robots.txt` opens with "Collection of data on
Facebook through automated means is prohibited unless you have express
written permission from Facebook," and separately, by name, disallows
`ClaudeBot` specifically — the exact tool that would be used to build this.
There's no compliant way to pull public posts, Marketplace listings, or
Group content as a lead source; Meta has also successfully sued scrapers
over this (Meta v. Bright Data and others) even where the data was
technically public. The Graph API doesn't help either — it only grants
access to Pages/ad accounts *you* administer, not to discovering other
companies' posts. If you want Facebook in the loop, the practical options
are: (1) keep using **Add lead** to manually drop in anything you spot
there yourself, or (2) if NCE runs its own Facebook Page and takes inbound
messages/Lead Ads through it, that could become a future *inbound* bridge
(like the Gmail one) using your own Page's official access token — a
different, compliant integration from "scrape other people's posts," and
not built here since it wasn't asked for.

## 3. Gmail bridge setup (one-time, ~5 minutes)

1. Go to https://console.cloud.google.com → create a project (any name).
2. *APIs & Services → Library* → search **Gmail API** → Enable.
3. *APIs & Services → OAuth consent screen* → External → fill the two required
   fields → add **your own Gmail address** as a Test user.
4. *APIs & Services → Credentials → Create credentials → OAuth client ID →
   Application type: Web application* → under **Authorized redirect URIs**
   add both (as applicable):
   - `http://127.0.0.1:8765/api/gmail/oauth/callback` (local dev)
   - `https://<your-vercel-domain>/api/gmail/oauth/callback` (deployed)
5. Set these as environment variables wherever the app runs (locally in your
   shell, or in Vercel → Settings → Environment Variables):
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI` — the exact redirect URI for that environment.

Go to **Settings** in the CRM and click **Connect Gmail** — approve access in
Google's consent screen and you're connected. The token is stored in Postgres
(via the `settings` table), so it survives redeploys and works the same
locally or once deployed.

**What the scan does:** for every lead with an email address, it finds your
Gmail conversations with them, attaches the thread to the lead card, marks
leads as **Replied** when they've written back, and creates to-dos when a reply
asks for a demo, call, proposal, or capability statement.

## 3b. Intelligent service matching (free bot, ~2 minutes)

Instead of a fixed keyword classifier, you can define the actual services
your business offers in plain language, and a small bot decides which one
each incoming lead best matches, with a fit score and a one-sentence reason.
It runs on **Google Gemini's free tier** — no credit card, no cost.

1. Go to https://aistudio.google.com/apikey → **Create API key** (any Google
   account works, no billing setup needed for the free tier).
2. Set it as an environment variable wherever the app runs:
   - `GEMINI_API_KEY` — locally in your shell, or in Vercel → Settings →
     Environment Variables (both Production and Preview).
3. Go to **Services** in the CRM and add one or more services — a name plus a
   description of what you offer. The more specific the description, the
   better the matching (e.g. *"Survey design, digital data collection
   (KoboToolbox/ODK), baseline/endline evaluations for donor-funded
   programmes"* rather than just *"M&E"*).

From then on, every new lead pulled from a source is automatically matched
against your services (one batched API call per pull — cheap and fast). Click
**↻ Re-match all leads against services** any time you add or edit a service
to re-score your existing pipeline. If `GEMINI_API_KEY` isn't set, or no
services are defined, this step is silently skipped — the CRM works fine
without it, falling back to the static keyword scoring described above.

## 4. Daily workflow

1. **Sources → Run all** (pull + Gmail sync in one click).
2. **Pipeline**: work top-down — leads are sorted by fit score. Open a lead,
   add/verify the contact email, tweak the *trigger* line (this is what makes
   outreach feel personal), pick a template → Generate → **Send**.
3. Sending auto-moves the lead to *Contacted* and creates a follow-up to-do
   4 days out.
4. **To-dos** tab is your morning checklist: Gmail-extracted asks, auto
   follow-ups, and your own tasks, sorted by due date.

## 4b. Pipeline power tools

**Views** — the Pipeline tab has a List / Board / Calendar switcher:
- **Board** is a Kanban view, one column per stage — drag a card to a new
  column to change its stage.
- **Calendar** shows every lead with an application deadline on a month grid
  (deadlines within 3 days are highlighted).

**Filters & saved presets** — filter by service, by time (created in the last
7/30/90 days), search, and stage (the chips). Click **💾 Save filter** to name
the current combination and recall it later from the **Saved filters**
dropdown.

**Bulk actions** — click **☑ Select** to enter multi-select mode, tick leads
on the list view, then bulk-change their stage or bulk-delete from the bar
that appears.

**Export & duplicates** — **⬇ Export CSV** downloads the current pipeline for
a board report or offline review. **⧉ Duplicates** groups leads that share an
email or organisation name and lets you pick which one to keep — its
activity/email/to-do history absorbs the others.

**Snooze** — from a lead's drawer, **💤 Snooze** hides it from the pipeline
until a date you choose, without changing its stage (tick **Show snoozed** in
the toolbar to see snoozed leads again).

**Insights tab** — pipeline value and lead count broken out by service line,
which sources actually convert to Won (not just volume), a 30-day trend of
average fit score & alignment %, and a global activity feed across every lead.

**Alignment %** — every lead shows a 🎯 badge separate from its 0–100 fit
score: purely how strongly its text matched the service it was classified
under (4+ matching phrases = 100%). The fit score also weighs source trust,
region and recency — alignment is the "does this actually sound like our
work" signal in isolation.

## 4c. Daily digest (Slack / email)

Settings → **Daily digest**: turn it on, pick email/Slack/both, and it sends
automatically once a day as part of the scheduled cron run — active leads,
pipeline value, new leads today, and follow-ups due.

- **Email**: uses your already-connected Gmail bridge (§3) — just set a
  recipient address.
- **Slack**: create an Incoming Webhook at api.slack.com/apps → your app →
  Incoming Webhooks, paste the URL in.

Use **Send a test digest now** to check it before waiting for the next
scheduled run.

## 4d. WhatsApp Business API (optional, needs your own Meta account)

Unlike the 💬 links elsewhere in the app (which just open WhatsApp for you to
send manually), Settings → **WhatsApp Business API** lets you send directly
from a lead's drawer, the same way Gmail sending works.

Setup (~10 minutes): developers.facebook.com → create a Meta App → add the
**WhatsApp** product → API Setup gives you a **Phone Number ID**; generate a
permanent access token under Business Settings → System Users (the default
24-hour test token will expire). Paste both into Settings.

Two things to know before relying on this:
- While your Meta app is in Development mode, you can only message numbers
  added as verified testers — Live mode needs Meta Business verification.
- Meta only allows free-text messages within 24 hours of the lead last
  messaging *you*. Outside that window, first-contact outreach needs a
  pre-approved message template — this integration sends free-text only, so
  it's best suited to following up with leads who've already replied.

This module is built to Meta's documented API shape; report back if it needs
adjusting once you're sending through a real account.

## 4e. Install as an app (PWA) & the capture bookmarklet

Raid Alpha is installable — open it in Chrome/Edge (desktop or Android) and
use "Install app" / "Add to Home Screen"; it'll open in its own window with
an icon, no browser chrome. A minimal service worker caches the app shell so
the UI still loads if your connection drops (API data itself always needs a
live connection).

**Capture bookmarklet** (Settings, bottom of the page): drag the **+ Add to
Raid Alpha** button to your bookmarks bar. On any page — a tender listing, a
job posting, a company site — click it to instantly add that page as a
manual lead (title and URL pre-filled), no need to switch tabs and fill in
the form yourself.

## 5. Staying compliant (important)

- Every source here is either an official API/licensed provider, or (in the
  three cases where no formal API exists — SADC, eTenders SA and
  GoZambiaJobs) a reader only added after checking `robots.txt` and terms of
  service found no prohibition, that identifies itself honestly and reads
  only public pages/data. Don't add scrapers
  for LinkedIn or other sites that prohibit it in their terms or `robots.txt`
  (including sites that disallow AI crawlers specifically) — accounts get
  banned, it can create real legal exposure, and data quality is poor anyway.
- Cold B2B email is legal in most jurisdictions if you identify yourself,
  keep it relevant, and honour opt-outs immediately (mark the lead *Lost* and
  don't email again). For EU contacts, keep outreach strictly business-relevant.
- Send in modest daily volumes (10–30 well-personalised emails/day outperforms
  mass blasts and protects your Gmail sender reputation).

## Files

```
app.py               FastAPI server (run this)
db.py                Postgres storage (creates tables on first run)
enrich.py            Fit scoring, alignment %, tentative deal values
services_catalog.py  NCE's 12 official service lines — keywords & value ranges
bot.py               Gemini-powered service matching (free tier, optional)
gmail_bridge.py      Gmail web OAuth flow, send, inbox scan → stages & to-dos
whatsapp_bridge.py   WhatsApp Business Cloud API send (needs your own Meta account)
digest.py            Daily Slack/email pipeline summary, sent via cron
sources/             One module per lead source (add your own — see __init__.py)
static/index.html    The CRM interface
static/manifest.json PWA manifest (installable app)
static/sw.js         Service worker (offline app-shell caching)
static/icons/        Generated PWA/favicon icons
api/index.py         Vercel entrypoint (re-exports the FastAPI app)
vercel.json          Vercel routing config
```

## Adding your own source

Create `sources/mysource.py` with `NAME`, `DESCRIPTION`, `NEEDS`, and a
`pull(settings) -> list[dict]` returning dicts with at least `org` plus any of
`contact, role, email, country, trigger, notes, url, posted_date, dedupe_key`.
Register it in `sources/__init__.py`. Scoring and dedup happen automatically.
