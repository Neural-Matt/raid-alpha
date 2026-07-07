"""ZPPA — Zambia Public Procurement Authority official OCDS bulk tender data.

ZPPA publishes structured Open Contracting Data Standard (OCDS) "record
packages" at zppa.org.zm — one JSON file per month, covering every public
tender across Zambian government. It is a bulk-data feed, not a live query
API, so this module downloads the most recent month(s), streams the records
(without loading the whole ~150-200MB file into memory at once), and keeps
only tenders that are still open and match the configured keywords —
otherwise every run would surface thousands of unrelated tenders (food,
construction, vehicles, etc.) alongside the handful relevant to NCE.
"""
import io
import json
import zipfile

import requests

try:
    import ijson
except ImportError:
    ijson = None

NAME = "ZPPA (Zambia public tenders)"
DESCRIPTION = ("Official ZPPA OCDS bulk tender data (zppa.org.zm) — recent open "
               "government tenders across Zambia, filtered to M&E / data / IT keywords.")
NEEDS = []

LIST_URL = "https://www.zppa.org.zm/ocds/services/recordpackage/getrecordpackagelist"
DEFAULT_QUERY = (
    "monitoring and evaluation,baseline survey,endline survey,data collection,"
    "household survey,impact assessment,survey firm,database system,"
    "management information system,business intelligence,power bi,dashboard,"
    "data analyst,data analytics,statistics office,census,information system,"
    "software development,web application,erp system,system integration,"
    "capacity building training,data literacy"
)
OPEN_STATUSES = {"planned", "active", "pending"}
MAX_LEADS = 50
MONTHS_BACK = 1


def _latest_month_urls(n: int) -> list[str]:
    resp = requests.get(LIST_URL, timeout=30)
    resp.raise_for_status()
    urls = resp.json().get("packagesPerMonth", [])
    return urls[-n:] if n > 0 else urls


def _latest_release(releases: list[dict]) -> dict:
    return max(releases, key=lambda r: r.get("date", ""))


def _iter_records(fh):
    if ijson is not None:
        yield from ijson.items(fh, "records.item")
    else:
        yield from json.load(fh).get("records", [])


def pull(settings: dict) -> list[dict]:
    query = settings.get("zppa_query") or DEFAULT_QUERY
    keywords = [k.strip().lower() for k in query.split(",") if k.strip()]
    months = int(settings.get("zppa_months_back") or MONTHS_BACK)

    leads = []
    for month_url in _latest_month_urls(months):
        resp = requests.get(month_url, timeout=60)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            with zf.open(zf.namelist()[0]) as fh:
                for rec in _iter_records(fh):
                    releases = rec.get("releases") or []
                    if not releases:
                        continue
                    release = _latest_release(releases)
                    tender = release.get("tender") or {}
                    status = (tender.get("status") or "").lower()
                    if status not in OPEN_STATUSES:
                        continue
                    title = tender.get("title", "")
                    desc = tender.get("description", "")
                    blob = f"{title} {desc}".lower()
                    if keywords and not any(kw in blob for kw in keywords):
                        continue
                    entity = tender.get("procuringEntity") or {}
                    org = entity.get("name") or (entity.get("identifier") or {}).get("legalName", "")
                    if not org:
                        continue
                    address = entity.get("address") or {}
                    contact = entity.get("contactPoint") or {}
                    deadline = (tender.get("tenderPeriod") or {}).get("endDate", "")[:10]
                    submission = tender.get("submissionMethodDetails", "")
                    eligibility = (tender.get("eligibilityCriteria") or "")[:800]
                    how_to_apply = "\n".join(filter(None, [
                        f"Submission method: {submission}" if submission else "",
                        f"Eligibility / requirements: {eligibility}" if eligibility else "",
                    ]))
                    leads.append({
                        "org": org,
                        "email": contact.get("email", ""),
                        "role": "Procurement contact" if contact.get("email") else "",
                        "country": address.get("countryName") or "Zambia",
                        "trigger": f"their open tender: \"{title}\"",
                        "notes": f"ZPPA tender: {title}. {desc}"[:400],
                        "how_to_apply": how_to_apply[:2000],
                        "deadline": deadline,
                        "url": "https://www.zppa.org.zm/records",
                        "source": "ZPPA",
                        "posted_date": (release.get("date") or "")[:10],
                        "dedupe_key": f"zppa|{rec.get('ocid')}",
                    })
                    if len(leads) >= MAX_LEADS:
                        return leads
    return leads
