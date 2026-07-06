"""Lead source registry.

Each source module exposes:
    NAME        - display name
    DESCRIPTION - one-liner shown in the UI
    NEEDS       - list of setting keys it requires (empty if none)
    pull(settings: dict) -> list[dict]   raw leads

A raw lead dict can contain: org, contact, role, email, country, trigger,
notes, url, source, posted_date, segment, dedupe_key.
"""
from . import reliefweb, worldbank, rss_feeds, apollo, hunter, zppa

REGISTRY = {
    "reliefweb": reliefweb,
    "worldbank": worldbank,
    "zppa": zppa,
    "rss": rss_feeds,
    "apollo": apollo,
    "hunter": hunter,
}


def describe():
    return [
        {
            "key": key,
            "name": mod.NAME,
            "description": mod.DESCRIPTION,
            "needs": mod.NEEDS,
        }
        for key, mod in REGISTRY.items()
    ]
