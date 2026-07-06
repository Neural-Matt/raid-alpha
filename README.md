# Racuda Alpha

A lead generation + outreach CRM for Neural Cloud Enterprise. Runs on Vercel
with Supabase as the database, GitHub as the staging/deploy pipeline — or
locally against any Postgres database (including your Supabase project).

What it does:

1. **Pull leads** at the press of a button from legal, official sources:
   - ReliefWeb API (live M&E / data-collection consultancy postings)
   - World Bank Projects API (active funded projects in your region)
   - ZPPA OCDS bulk data (open Zambian government tenders, filtered to your keywords)
   - Any RSS/Atom feeds you add (tender boards, Google Alerts = the widest net)
   - Apollo.io People Search (decision-maker contacts, your API key)
   - Hunter.io Domain Search (published emails at target companies, your API key)
2. **Auto-enrich & score** every lead: service segment, 0–100 fit score, and a
   tentative deal value — all pre-populated in the pipeline and fully editable.
3. **Gmail bridge**: draft from templates, send from your own Gmail, and scan
   your inbox — replies auto-bump lead stages and asks like "send a proposal"
   or "let's schedule a call" become to-dos automatically.
4. **Full tracking**: pipeline stages, follow-up dates, activity logs, to-dos,
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

## 2. First pull

Go to **Sources → Run all sources**. ReliefWeb, World Bank, and ZPPA need no
keys, so you'll have a scored pipeline within a minute.

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
  (defaults to M&E/data/IT terms — broaden it if you want wider coverage;
  ZPPA covers every sector, so an empty filter would flood your pipeline).

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

## 4. Daily workflow

1. **Sources → Run all** (pull + Gmail sync in one click).
2. **Pipeline**: work top-down — leads are sorted by fit score. Open a lead,
   add/verify the contact email, tweak the *trigger* line (this is what makes
   outreach feel personal), pick a template → Generate → **Send**.
3. Sending auto-moves the lead to *Contacted* and creates a follow-up to-do
   4 days out.
4. **To-dos** tab is your morning checklist: Gmail-extracted asks, auto
   follow-ups, and your own tasks, sorted by due date.

## 5. Staying compliant (important)

- All sources here are official APIs or licensed providers — keep it that way.
  Don't add scrapers for LinkedIn or other sites that prohibit it; accounts get
  banned and data quality is poor anyway.
- Cold B2B email is legal in most jurisdictions if you identify yourself,
  keep it relevant, and honour opt-outs immediately (mark the lead *Lost* and
  don't email again). For EU contacts, keep outreach strictly business-relevant.
- Send in modest daily volumes (10–30 well-personalised emails/day outperforms
  mass blasts and protects your Gmail sender reputation).

## Files

```
app.py            FastAPI server (run this)
db.py             Postgres storage (creates tables on first run)
enrich.py         Segment classification, fit scoring, tentative deal values
gmail_bridge.py   Gmail web OAuth flow, send, inbox scan → stages & to-dos
sources/          One module per lead source (add your own — see __init__.py)
static/index.html The CRM interface
api/index.py      Vercel entrypoint (re-exports the FastAPI app)
vercel.json       Vercel routing config
```

## Adding your own source

Create `sources/mysource.py` with `NAME`, `DESCRIPTION`, `NEEDS`, and a
`pull(settings) -> list[dict]` returning dicts with at least `org` plus any of
`contact, role, email, country, trigger, notes, url, posted_date, dedupe_key`.
Register it in `sources/__init__.py`. Scoring and dedup happen automatically.
