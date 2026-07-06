"""Racuda Alpha's intelligent opportunity-matching bot.

Uses Google's Gemini API (free tier, no card required — get a key at
https://aistudio.google.com/apikey) to decide which of your defined
services (if any) best matches each incoming lead, with a fit score and a
short reason. Every lead from one source pull is batched into a single
Gemini call, since the services list only needs to be sent once.

If GEMINI_API_KEY isn't set, or no services are defined, matching is
skipped silently — the CRM works fine without it (the static keyword
scoring in enrich.py still runs regardless).
"""
from __future__ import annotations
import json
import os

import requests

GEMINI_MODEL = "gemini-flash-latest"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "lead_index": {"type": "integer"},
                    "service_name": {"type": "string"},
                    "score": {"type": "integer"},
                    "reasoning": {"type": "string"},
                },
                "required": ["lead_index", "service_name", "score", "reasoning"],
            },
        },
    },
    "required": ["matches"],
}


def configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def match_leads(leads: list[dict], services: list[dict]) -> dict[int, dict]:
    """Return {lead_index: {"service_name", "score", "reasoning"}} for each lead.

    `leads` items need at least "org", "trigger", "notes" keys. `services`
    items need "name" and "description". Returns {} if the bot isn't
    configured, there are no services, or no leads — callers should treat
    that as "skip, nothing changes".
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not services or not leads:
        return {}

    service_list = "\n".join(
        f"- {s['name']}: {s.get('description', '')}" for s in services)
    lead_list = "\n".join(
        f"{i}. {l.get('org', '')} — {l.get('trigger', '')} {l.get('notes', '')}"[:600]
        for i, l in enumerate(leads))

    prompt = (
        "You are helping a business classify incoming sales leads against the "
        "services it offers. For each lead below, decide which ONE service (if "
        "any) it best matches, a fit score from 0-100 (0 = no real fit), and a "
        "one-sentence reason. If a lead doesn't genuinely match any service, "
        "still name the closest one but give it a low score (under 30).\n\n"
        f"Services offered:\n{service_list}\n\n"
        f"Leads (index. org — description):\n{lead_list}\n\n"
        "Return a match for every lead index listed above, exactly once each."
    )

    resp = requests.post(
        f"{API_URL}?key={api_key}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
            },
        },
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)

    out = {}
    for m in parsed.get("matches", []):
        idx = m.get("lead_index")
        if idx is None:
            continue
        out[int(idx)] = {
            "service_name": m.get("service_name", ""),
            "score": int(m.get("score", 0)),
            "reasoning": m.get("reasoning", ""),
        }
    return out
