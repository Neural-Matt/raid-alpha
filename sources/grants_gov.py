"""Grants.gov — official US federal funding-opportunity API (grants.gov).

Free, public, no key required. Many notices are US-agency-funded programs
(State Department public diplomacy grants, USAID-adjacent programs, etc.)
that explicitly fund M&E, data collection and capacity-building work
internationally, open to non-US applicants. Each hit is enriched with a
detail-endpoint call for the actual contact person, deadline, funding
amount and eligibility text — the same "opportunity details + contact +
how to apply" depth as the other sources.
"""
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

NAME = "Grants.gov (US federal funding)"
DESCRIPTION = ("Official US government grants API — federal funding opportunities "
               "matching your keywords, enriched with contact details and deadlines.")
NEEDS = []

SEARCH_API = "https://api.grants.gov/v1/api/search2"
DETAIL_API = "https://api.grants.gov/v1/api/fetchOpportunity"
DEFAULT_QUERY = "monitoring and evaluation data collection capacity building"
MAX_LEADS = 12
DETAIL_TIMEOUT = 10
DETAIL_WORKERS = 6


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").replace("&nbsp;", " ").replace("&amp;", "&")


def _to_iso(date_str: str) -> str:
    """Grants.gov dates arrive as MM/DD/YYYY."""
    import datetime
    try:
        return datetime.datetime.strptime(date_str, "%m/%d/%Y").date().isoformat()
    except (ValueError, TypeError):
        return ""


def _fetch_detail(opp_id) -> dict:
    try:
        dresp = requests.post(DETAIL_API, json={"opportunityId": int(opp_id)}, timeout=DETAIL_TIMEOUT)
        dresp.raise_for_status()
        return (dresp.json().get("data") or {}).get("synopsis") or {}
    except Exception:
        return {}


def pull(settings: dict) -> list[dict]:
    query = settings.get("grants_gov_query") or DEFAULT_QUERY
    resp = requests.post(SEARCH_API, json={
        "rows": MAX_LEADS,
        "keyword": query,
        "oppStatuses": "posted",
    }, timeout=30)
    resp.raise_for_status()
    hits = (resp.json().get("data") or {}).get("oppHits", []) or []
    hits = [h for h in hits[:MAX_LEADS] if h.get("id")]

    # detail calls are independent HTTP round-trips — fetch concurrently so
    # a dozen opportunities don't mean a dozen sequential network waits
    details = {}
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
        futures = {pool.submit(_fetch_detail, h["id"]): h["id"] for h in hits}
        for fut in as_completed(futures):
            details[futures[fut]] = fut.result()

    leads = []
    for hit in hits:
        opp_id = hit["id"]
        detail = details.get(opp_id, {})
        title = hit.get("title", "")
        agency = hit.get("agency") or detail.get("agencyDetails", {}).get("agencyName", "")
        if not agency:
            continue
        eligibility = _strip_html(detail.get("applicantEligibilityDesc", ""))[:800]
        description = _strip_html(detail.get("synopsisDesc", ""))[:2000]
        how_to_apply = "\n".join(filter(None, [
            f"Eligibility: {eligibility}" if eligibility else "",
            description,
        ]))
        funding = detail.get("awardCeilingFormatted") or detail.get("estimatedFundingFormatted") or ""
        leads.append({
            "org": agency[:160],
            "contact": detail.get("agencyContactName", "").replace("\n", " ").strip(),
            "email": detail.get("agencyContactEmail", ""),
            "phone": detail.get("agencyContactPhone", ""),
            "role": "Grants contact",
            "country": "",
            "trigger": f"their open funding opportunity: \"{title}\"" +
                       (f" (up to {funding})" if funding else ""),
            "notes": f"Grants.gov opportunity {hit.get('number','')} from {agency} "
                     f"(US federal funder — check eligibility for international applicants).",
            "how_to_apply": how_to_apply[:2500],
            "deadline": _to_iso(hit.get("closeDate", "")),
            "url": f"https://www.grants.gov/search-results-detail/{opp_id}",
            "source": "Grants.gov",
            "posted_date": _to_iso(hit.get("openDate", "")),
            "dedupe_key": f"grantsgov|{opp_id}",
        })
    return leads
