"""World Bank Projects & Operations — official open-data API.

Active, funded projects in data/statistics/health/education sectors are
budgeted programmes that routinely subcontract local data collection, M&E
and analytics work. The implementing agency is the lead.
"""
import requests

NAME = "World Bank active projects"
DESCRIPTION = ("World Bank open-data Projects API — active funded projects "
               "(statistics, health, education, governance) in Southern & Eastern "
               "Africa that subcontract data and M&E work.")
NEEDS = []

API = "https://search.worldbank.org/api/v2/projects"
COUNTRIES = ["ZM", "MW", "TZ", "ZW", "KE", "UG", "RW", "MZ", "BW", "NA"]
DEFAULT_TERMS = ["statistics", "health systems", "monitoring", "digital", "education data"]


def pull(settings: dict) -> list[dict]:
    terms = [t.strip() for t in
             (settings.get("worldbank_terms") or ",".join(DEFAULT_TERMS)).split(",")
             if t.strip()]
    leads, seen = [], set()
    for term in terms[:6]:
        try:
            resp = requests.get(API, params={
                "format": "json",
                "qterm": term,
                "status": "Active",
                "rows": 20,
                "fl": "id,project_name,countryshortname,impagency,boardapprovaldate,url,totalamt",
            }, timeout=30)
            resp.raise_for_status()
            projects = resp.json().get("projects", {}) or {}
        except Exception:
            continue
        for pid, p in projects.items():
            if pid in seen or not isinstance(p, dict):
                continue
            seen.add(pid)
            country = p.get("countryshortname", "")
            if isinstance(country, list):
                country = country[0] if country else ""
            if country and not any(country.lower().startswith(c) for c in
                                   ["zambia", "malawi", "tanzania", "zimbabwe", "kenya",
                                    "uganda", "rwanda", "mozambique", "botswana", "namibia",
                                    "africa", "eastern", "southern"]):
                continue
            agency = p.get("impagency", "") or f"World Bank project ({country})"
            if isinstance(agency, list):
                agency = agency[0] if agency else ""
            name = p.get("project_name", "")
            leads.append({
                "org": str(agency)[:120],
                "country": str(country),
                "trigger": f"the active World Bank-funded project \"{name}\"",
                "notes": f"WB project: {name}. Approved: {str(p.get('boardapprovaldate',''))[:10]}. "
                         f"Total: {p.get('totalamt','?')}",
                "url": p.get("url", "") or f"https://projects.worldbank.org/en/projects-operations/project-detail/{pid}",
                "source": "World Bank",
                "posted_date": str(p.get("boardapprovaldate", ""))[:10],
                "segment": "Public sector",
                "dedupe_key": f"wb|{pid}",
            })
    return leads
