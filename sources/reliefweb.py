"""ReliefWeb — official public API (https://apidoc.reliefweb.int/).

Pulls recent consultancy/job postings matching NCE's service keywords across
its 12 service lines. These postings are strong buying signals: an
organisation actively looking for that capacity right now. ReliefWeb's
audience skews NGO/UN/humanitarian, so the default query is a representative
subset (not the full 250-keyword catalog) weighted toward the services that
sector actually buys — data/M&E, health systems, digital transformation,
capacity building — while still covering software and cloud work.
"""
import requests

NAME = "ReliefWeb consultancies"
DESCRIPTION = ("Official ReliefWeb API — recent consultancy postings from NGOs and UN "
               "agencies across NCE's service lines (M&E/data, software, health "
               "systems, digital transformation, capacity building).")
NEEDS = []

API = "https://api.reliefweb.int/v2/jobs"
_DEFAULT_TERMS = [
    "monitoring and evaluation", "baseline survey", "data collection", "data analyst",
    "business intelligence", "dashboard", "software developer", "database administrator",
    "digital transformation", "capacity building", "cloud migration",
    "geographic information system", "management information system",
    "web application development", "health information system", "process automation",
]
DEFAULT_QUERY = " OR ".join(f'"{t}"' for t in _DEFAULT_TERMS)


def pull(settings: dict) -> list[dict]:
    query = settings.get("reliefweb_query") or DEFAULT_QUERY
    params = {
        "appname": settings.get("reliefweb_appname") or "nce-lead-crm",
        "query[value]": query,
        "query[operator]": "OR",
        "limit": 30,
        "sort[]": "date:desc",
        "fields[include][]": ["title", "source.name", "country.name",
                              "date.created", "date.closing", "url",
                              "career_categories.name", "body", "how_to_apply"],
    }
    resp = requests.get(API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    leads = []
    for item in data.get("data", []):
        f = item.get("fields", {})
        org = ""
        srcs = f.get("source") or []
        if isinstance(srcs, list) and srcs:
            org = srcs[0].get("name", "")
        elif isinstance(srcs, dict):
            org = srcs.get("name", "")
        countries = f.get("country") or []
        country = countries[0].get("name", "") if countries else ""
        title = f.get("title", "")
        posted = (f.get("date", {}) or {}).get("created", "")[:10]
        deadline = (f.get("date", {}) or {}).get("closing", "")[:10]
        if not org:
            continue
        leads.append({
            "org": org,
            "country": country,
            "trigger": f"your recent posting: \"{title}\"",
            "notes": (f.get("body") or f"ReliefWeb posting: {title}")[:1000],
            "how_to_apply": (f.get("how_to_apply") or "")[:2000],
            "deadline": deadline,
            "url": f.get("url", ""),
            "source": "ReliefWeb",
            "posted_date": posted,
            "dedupe_key": f"rw|{item.get('id')}",
        })
    return leads
