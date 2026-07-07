"""SADC (Southern African Development Community) procurement opportunities.

No official API exists. Verified before building: robots.txt (standard
Drupal defaults) does not disallow /procurement-opportunities, and no
legal-notice/terms page exists on the site to check for a scraping
prohibition (both return 404). SADC is an intergovernmental body publishing
these notices specifically to solicit bids from qualified firms — the same
public-interest basis as ZPPA and the World Bank sources. Scraper identifies
itself honestly via User-Agent and reads only the public listing + detail
pages (a handful of requests — the list is small, typically single digits
of open opportunities at any time).

If SADC changes its site markup this will need a corresponding update —
it depends on current page structure, unlike the API-based sources
elsewhere in sources/.
"""
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

NAME = "SADC procurement opportunities"
DESCRIPTION = ("Southern African Development Community — official regional "
               "procurement notices with deadlines, descriptions and named "
               "contacts. No API exists; a small, honestly-identified public-page "
               "reader (typically only a handful of notices are open at once).")
NEEDS = []

BASE = "https://www.sadc.int"
LIST_URL = f"{BASE}/procurement-opportunities?items_per_page=All"
HEADERS = {"User-Agent": "RaidAlphaLeadBot/1.0 (+https://github.com/Neural-Matt/raid-alpha)"}
MONTHS = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
          "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}


def _parse_closing_date(day: str, month_year: str) -> str:
    m = re.match(r"([A-Za-z]{3})\s*(\d{4})", (month_year or "").strip())
    if not m or not day.strip().isdigit():
        return ""
    mon = MONTHS.get(m.group(1))
    if not mon:
        return ""
    return f"{m.group(2)}-{mon}-{int(day.strip()):02d}"


def _fetch_detail(url: str) -> dict:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception:
        return {}
    soup = BeautifulSoup(resp.text, "html.parser")
    body = soup.select_one(".field--name-body")
    text = body.get_text("\n", strip=True) if body else ""
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
    phone_match = re.search(r"(?:Tel(?:ephone)?(?:\s*Number)?)\s*:?\s*([+\d][\d\s()./-]{6,}\d)", text)
    return {
        "description": text[:2200],
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(1).strip() if phone_match else "",
    }


def pull(settings: dict) -> list[dict]:
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for grid_item in soup.select(".grid-item"):
        title_a = grid_item.select_one(".views-field-title a")
        if not title_a:
            continue
        day = grid_item.select_one(".date-large")
        month_year = grid_item.select_one(".date-small")
        items.append({
            "title": title_a.get_text(strip=True),
            "url": BASE + title_a["href"],
            "deadline": _parse_closing_date(
                day.get_text() if day else "", month_year.get_text() if month_year else ""),
        })

    details = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_fetch_detail, it["url"]): it["url"] for it in items}
        for fut in as_completed(futures):
            details[futures[fut]] = fut.result()

    leads = []
    for it in items:
        d = details.get(it["url"], {})
        leads.append({
            "org": "SADC Secretariat",
            "email": d.get("email", ""),
            "phone": d.get("phone", ""),
            "role": "Procurement contact" if d.get("email") else "",
            "country": "Botswana (SADC Secretariat, regional scope)",
            "trigger": f"their open regional tender: \"{it['title'][:120]}\"",
            "notes": f"SADC procurement notice: {it['title']}",
            "how_to_apply": d.get("description", ""),
            "deadline": it["deadline"],
            "url": it["url"],
            "source": "SADC",
            "dedupe_key": f"sadc|{it['url']}",
        })
    return leads
