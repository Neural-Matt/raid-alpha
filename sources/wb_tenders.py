"""World Bank Procurement Notices — official open-data API.

Distinct from the "World Bank active projects" source (worldbank.py), which
surfaces funded projects as a general demand signal. This one pulls live,
individual open tenders/consulting-selection notices directly — each with a
real submission deadline and, very often, a named procurement contact
(name, email, phone, organisation), which is exactly the detail a lead needs
to be actionable rather than just informational.
"""
import re

import requests

NAME = "World Bank open tenders"
DESCRIPTION = ("Official World Bank Procurement Notices API — live open tenders and "
               "consulting-selection notices with real deadlines and named contacts.")
NEEDS = []

API = "https://search.worldbank.org/api/v2/procnotices"
DEFAULT_TERMS = ["monitoring and evaluation", "data collection", "survey", "statistics",
                 "digital", "database", "capacity building", "consulting services"]
PRIORITY_COUNTRIES = [
    "zambia", "zimbabwe", "malawi", "tanzania", "kenya", "uganda", "rwanda",
    "mozambique", "botswana", "namibia", "south africa", "congo", "ethiopia",
    "ghana", "nigeria",
]
MAX_LEADS = 40


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").replace("&nbsp;", " ").replace("&amp;", "&")


def pull(settings: dict) -> list[dict]:
    terms = [t.strip() for t in
             (settings.get("wb_tender_terms") or ",".join(DEFAULT_TERMS)).split(",")
             if t.strip()]
    country_filter = (settings.get("wb_tender_countries_only") or "true").lower() != "false"

    leads, seen = [], set()
    for term in terms[:8]:
        try:
            resp = requests.get(API, params={
                "format": "json",
                "qterm": term,
                "rows": 20,
            }, timeout=30)
            resp.raise_for_status()
            notices = resp.json().get("procnotices", []) or []
        except Exception:
            continue
        for n in notices:
            nid = n.get("id")
            if not nid or nid in seen:
                continue
            if (n.get("notice_status") or "").lower() != "published":
                continue
            country = n.get("project_ctry_name", "") or ""
            if country_filter and not any(c in country.lower() for c in PRIORITY_COUNTRIES):
                continue
            seen.add(nid)
            org = n.get("contact_organization") or n.get("project_name") or ""
            if not org:
                continue
            notice_text = _strip_html(n.get("notice_text", ""))[:2500]
            leads.append({
                "org": org[:160],
                "contact": n.get("contact_name", ""),
                "email": n.get("contact_email", ""),
                "role": "Procurement contact",
                "country": country,
                "trigger": f"their open tender: \"{n.get('bid_description','')[:120]}\"",
                "notes": f"WB {n.get('notice_type','notice')} for project \"{n.get('project_name','')}\" "
                         f"(ref {n.get('bid_reference_no','')}).",
                "how_to_apply": notice_text,
                "deadline": (n.get("submission_deadline_date") or "")[:10],
                "url": f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{nid}",
                "source": "World Bank Tenders",
                "posted_date": _parse_noticedate(n.get("noticedate", "")),
                "dedupe_key": f"wbtender|{nid}",
            })
            if len(leads) >= MAX_LEADS:
                return leads
    return leads


def _parse_noticedate(s: str) -> str:
    """noticedate arrives as '03-Jul-2026' — convert to ISO for recency scoring."""
    import datetime
    try:
        return datetime.datetime.strptime(s, "%d-%b-%Y").date().isoformat()
    except ValueError:
        return ""
