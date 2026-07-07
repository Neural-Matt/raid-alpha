"""GoZambiaJobs — lightweight, respectful scraper (no official API exists).

Verified before building: robots.txt only disallows /rss/ and sets a
Crawl-delay of 1s (no blanket disallow, no bot-specific block); no
scraping/automated-access prohibition found in their published terms
(gozambiajobs.com/jobs/legal). We identify ourselves honestly via User-Agent
rather than spoofing a browser, and only fetch the public job-listing page.

This is a *hiring-signal* source, not a tender/opportunity source: a company
posting for a Data/M&E/IT role is either building that capacity in-house or
may want complementary consultancy support for overflow/specialised work —
a weaker but still legitimate buying signal, scored accordingly.

If GoZambiaJobs changes its markup this will need a corresponding update —
it depends on the site's current page structure, unlike the API-based
sources elsewhere in sources/.
"""
import datetime
import re

import requests
from bs4 import BeautifulSoup

NAME = "GoZambiaJobs (hiring signals)"
DESCRIPTION = ("Zambia's largest job board — flags companies hiring for data/M&E/IT "
               "roles as a complementary-support lead signal. Lightweight public-page "
               "scraper (no official API), identifies itself honestly, respects "
               "the site's crawl-delay.")
NEEDS = []

BASE = "https://gozambiajobs.com"
HEADERS = {"User-Agent": "RaidAlphaLeadBot/1.0 (+https://github.com/Neural-Matt/raid-alpha)"}
DEFAULT_KEYWORDS = ("data analy,data collection,data management,monitoring and evaluation,"
                    "m&e officer,software developer,database administrator,digital transformation,"
                    "geographic information system,management information system,"
                    "information communication technology,business intelligence,"
                    "power bi,survey,statistician")
MAX_LEADS = 20


def _relative_to_date(text: str) -> str:
    text = (text or "").strip().lower()
    m = re.match(r"(\d+)\s*d", text)
    if m:
        return (datetime.date.today() - datetime.timedelta(days=int(m.group(1)))).isoformat()
    if "h" in text or "m" in text and "mo" not in text:
        return datetime.date.today().isoformat()
    m = re.match(r"(\d+)\s*mo", text)
    if m:
        return (datetime.date.today() - datetime.timedelta(days=int(m.group(1)) * 30)).isoformat()
    return ""


def pull(settings: dict) -> list[dict]:
    query = settings.get("gozambiajobs_query") or DEFAULT_KEYWORDS
    keywords = [k.strip().lower() for k in query.split(",") if k.strip()]

    resp = requests.get(f"{BASE}/jobs", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    leads = []
    for item in soup.select("[data-jobid]"):
        title_a = item.select_one("a.job-details-link")
        if not title_a:
            continue
        title = title_a.get_text(strip=True)
        company_a = item.find("a", href=re.compile(r"^/companies/"))
        location_a = item.find("a", href=re.compile(r"^/jobs/in-"))
        tags = [t.get_text(strip=True) for t in item.select("a.job-tag")]
        blob = f"{title} {' '.join(tags)}".lower()
        if keywords and not any(kw in blob for kw in keywords):
            continue
        org = company_a.get_text(strip=True) if company_a else ""
        if not org:
            continue
        job_id = item.get("data-jobid", "")
        posted_span = item.select_one(".job-posted-date")
        leads.append({
            "org": org[:160],
            "country": (location_a.get_text(strip=True) if location_a else "") or "Zambia",
            "trigger": f"they're hiring: \"{title}\"",
            "notes": f"GoZambiaJobs posting: {title}" +
                     (f" ({', '.join(tags[:4])})" if tags else ""),
            "url": f"{BASE}{title_a['href']}",
            "source": "GoZambiaJobs",
            "posted_date": _relative_to_date(posted_span.get_text() if posted_span else ""),
            "dedupe_key": f"gzj|{job_id}",
        })
        if len(leads) >= MAX_LEADS:
            break
    return leads
