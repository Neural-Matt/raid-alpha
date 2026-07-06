"""Hunter.io — official Domain Search API (requires your Hunter API key).

Given target-company domains (Settings → one per line), returns publicly
listed professional email addresses and roles at those organisations.
Hunter's free tier includes 25 searches/month.
"""
import requests

NAME = "Hunter.io contacts by domain"
DESCRIPTION = ("Hunter Domain Search API — finds published professional emails at "
               "the target-company domains you list in Settings. Requires a Hunter API key.")
NEEDS = ["hunter_api_key", "hunter_domains"]

API = "https://api.hunter.io/v2/domain-search"


def pull(settings: dict) -> list[dict]:
    key = settings.get("hunter_api_key", "").strip()
    if not key:
        raise RuntimeError("Add your Hunter API key in Settings first.")
    domains = [d.strip() for d in (settings.get("hunter_domains") or "").splitlines() if d.strip()]
    if not domains:
        raise RuntimeError("Add target domains (one per line) in Settings first.")

    leads = []
    for domain in domains[:10]:
        try:
            resp = requests.get(API, params={
                "domain": domain, "api_key": key, "limit": 10, "type": "personal",
            }, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("data", {}) or {}
        except Exception:
            continue
        org = data.get("organization") or domain
        country = data.get("country") or ""
        for e in data.get("emails", [])[:10]:
            name = " ".join(x for x in [e.get("first_name"), e.get("last_name")] if x)
            leads.append({
                "org": org,
                "contact": name,
                "role": e.get("position", "") or "",
                "email": e.get("value", ""),
                "country": country,
                "notes": f"Hunter domain search ({domain}). Confidence: {e.get('confidence','?')}%",
                "url": f"https://{domain}",
                "source": "Hunter",
                "dedupe_key": f"hunter|{e.get('value','')}",
            })
    return leads
