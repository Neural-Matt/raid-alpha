"""eTenders South Africa — National Treasury public tender portal.

No documented public API exists, but the portal's own opportunities page
(https://www.etenders.gov.za/Home/opportunities) is powered by an
unauthenticated JSON endpoint that returns exactly the data shown in its
public results table — the same category of "public data endpoint behind
a government portal" already used for ZPPA and SADC. robots.txt returns
404 (no restriction declared) and no terms/legal-notice page exists on the
site (/Home/TermsAndConditions, /terms, /Home/Terms all 404 as well).
This module self-identifies honestly via User-Agent and reads only the
same JSON the portal serves to any visitor's browser.

The endpoint ignores the DataTable's own global-search parameter (verified:
recordsFiltered always equals recordsTotal regardless of the value sent —
the portal's own JS even has its one real filtering call commented out), so
keyword filtering happens locally in Python after pulling the current list
of published/open tenders.
"""
import requests

NAME = "eTenders South Africa"
DESCRIPTION = ("South African National Treasury tender portal — live open "
               "tenders nationwide (government departments, municipalities, "
               "state-owned entities) with named contacts, email, phone and "
               "closing dates. No API exists; reads the same public JSON "
               "the portal's own search page uses.")
NEEDS = []

BASE = "https://www.etenders.gov.za"
LIST_URL = f"{BASE}/Home/PaginatedTenderOpportunities"
OPPORTUNITIES_URL = f"{BASE}/Home/opportunities"
HEADERS = {
    "User-Agent": "RaidAlphaLeadBot/1.0 (+https://github.com/Neural-Matt/raid-alpha)",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": OPPORTUNITIES_URL,
}
MAX_ROWS = 2500   # comfortably covers the ~1800 currently-open tenders
MAX_LEADS = 15

DEFAULT_KEYWORDS = (
    "monitoring and evaluation,m&e,data collection,data analysis,data management,"
    "baseline survey,endline survey,household survey,business intelligence,dashboard,"
    "database administrator,management information system,geographic information system,"
    "statistician,statistics,impact assessment,data capturing,digital transformation,"
    "power bi,survey firm,socio-economic survey"
)

_COLUMNS = ["0", "category", "description", "eSubmission", "date_Published", "closing_Date", "actions"]


def _params() -> list[tuple[str, str]]:
    params = [("draw", "1")]
    for i, data in enumerate(_COLUMNS):
        params.append((f"columns[{i}][data]", data))
        params.append((f"columns[{i}][name]", ""))
        params.append((f"columns[{i}][searchable]", "true"))
        params.append((f"columns[{i}][orderable]", "false" if data in ("0", "actions") else "true"))
        params.append((f"columns[{i}][search][value]", ""))
        params.append((f"columns[{i}][search][regex]", "false"))
    params += [
        ("order[0][column]", "4"), ("order[0][dir]", "desc"),
        ("start", "0"), ("length", str(MAX_ROWS)),
        ("search[value]", ""), ("search[regex]", "false"),
        ("status", "1"),  # 1 = Published / currently open
    ]
    return params


def pull(settings: dict) -> list[dict]:
    keywords = [k.strip().lower() for k in
                (settings.get("etenders_keywords") or DEFAULT_KEYWORDS).split(",") if k.strip()]

    resp = requests.get(LIST_URL, headers=HEADERS, params=_params(), timeout=30)
    resp.raise_for_status()
    rows = resp.json().get("data", [])

    leads = []
    for row in rows:
        blob = (row.get("description") or "").lower()
        if not any(kw in blob for kw in keywords):
            continue

        docs = row.get("supportDocument") or []
        doc_names = ", ".join(d.get("fileName", "") for d in docs if d.get("fileName"))
        briefing = ""
        if row.get("briefingSession"):
            venue = row.get("briefingVenue") or "venue TBC on the bid document"
            compulsory = "compulsory" if row.get("briefingCompulsory") else "optional"
            briefing = f" A briefing session applies ({compulsory}), at {venue}."

        tender_no = row.get("tender_No", "")
        how_to_apply = (
            f"Search tender number \"{tender_no}\" on {OPPORTUNITIES_URL} to download the "
            f"official bid documents{f' ({doc_names})' if doc_names else ''} and submit per "
            f"the instructions therein.{briefing} Delivery/site: {row.get('delivery') or 'see bid document'}."
        )

        leads.append({
            "org": row.get("department") or row.get("organ_of_State") or "South African government",
            "contact": row.get("contactPerson") or "",
            "role": "Procurement contact",
            "email": row.get("email") or "",
            "phone": row.get("telephone") or "",
            "country": f"South Africa ({row.get('province') or 'national'})",
            "trigger": f"their open tender \"{(row.get('description') or '')[:120].strip()}\"",
            "notes": f"eTenders SA notice {tender_no}: {(row.get('description') or '')[:400]}",
            "how_to_apply": how_to_apply,
            "deadline": (row.get("closing_Date") or "")[:10],
            "url": OPPORTUNITIES_URL,
            "source": "eTenders SA",
            "dedupe_key": f"etenders_sa|{row.get('id')}",
        })
        if len(leads) >= MAX_LEADS:
            break

    return leads
