"""Lead source registry.

Each source module exposes:
    NAME        - display name
    DESCRIPTION - one-liner shown in the UI
    NEEDS       - list of setting keys it requires (empty if none)
    pull(settings: dict) -> list[dict]   raw leads

A raw lead dict can contain: org, contact, role, email, phone, country,
trigger, notes, url, source, posted_date, segment, dedupe_key, deadline,
how_to_apply.
"""
from . import (reliefweb, worldbank, wb_tenders, rss_feeds, apollo, hunter,
               zppa, grants_gov, ted_eu, sam_gov, gozambiajobs, sadc, etenders_sa)

REGISTRY = {
    "reliefweb": reliefweb,
    "worldbank": worldbank,
    "wb_tenders": wb_tenders,
    "zppa": zppa,
    "grants_gov": grants_gov,
    "ted_eu": ted_eu,
    "sam_gov": sam_gov,
    "sadc": sadc,
    "etenders_sa": etenders_sa,
    "gozambiajobs": gozambiajobs,
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
