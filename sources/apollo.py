"""Apollo.io — official People Search API (requires your Apollo API key).

Apollo is a licensed B2B contact-data provider; using their API with your own
account is the legitimate route to decision-maker contacts (vs. scraping
LinkedIn, which violates its terms). Configure titles/keywords in Settings.
Free tier includes limited credits.
"""
import requests

NAME = "Apollo.io decision-makers"
DESCRIPTION = ("Apollo People Search API — pulls named decision-makers (with emails "
               "where available) matching your target titles and industries. "
               "Requires an Apollo API key.")
NEEDS = ["apollo_api_key"]

API = "https://api.apollo.io/api/v1/mixed_people/search"
DEFAULT_TITLES = ["Head of Monitoring and Evaluation", "M&E Manager", "Chief Operating Officer",
                  "Head of Data", "IT Director", "Country Director"]
DEFAULT_LOCATIONS = ["Zambia", "Kenya", "Tanzania", "South Africa", "Uganda"]


def pull(settings: dict) -> list[dict]:
    key = settings.get("apollo_api_key", "").strip()
    if not key:
        raise RuntimeError("Add your Apollo API key in Settings first.")
    titles = [t.strip() for t in
              (settings.get("apollo_titles") or ", ".join(DEFAULT_TITLES)).split(",") if t.strip()]
    locations = [l.strip() for l in
                 (settings.get("apollo_locations") or ", ".join(DEFAULT_LOCATIONS)).split(",") if l.strip()]

    resp = requests.post(API, headers={
        "Content-Type": "application/json",
        "X-Api-Key": key,
    }, json={
        "person_titles": titles[:10],
        "person_locations": locations[:10],
        "page": 1,
        "per_page": 25,
    }, timeout=30)
    resp.raise_for_status()
    people = resp.json().get("people", []) or []

    leads = []
    for p in people:
        org = (p.get("organization") or {}).get("name", "") or p.get("organization_name", "")
        if not org:
            continue
        name = p.get("name", "")
        phones = p.get("phone_numbers") or []
        phone = phones[0].get("raw_number", "") if phones and isinstance(phones[0], dict) else ""
        leads.append({
            "org": org,
            "contact": name,
            "role": p.get("title", ""),
            "email": p.get("email", "") if p.get("email") and "not_unlocked" not in str(p.get("email")) else "",
            "phone": phone,
            "country": p.get("country", "") or "",
            "trigger": "",
            "notes": f"Apollo match. LinkedIn: {p.get('linkedin_url','')}",
            "url": p.get("linkedin_url", ""),
            "source": "Apollo",
            "dedupe_key": f"apollo|{p.get('id', name + org)}",
        })
    return leads
