"""Daily digest — Slack webhook and/or email summary of pipeline activity.

Settings (all optional — digest is off unless digest_enabled is "true"):
  digest_enabled       "true" / "false"
  digest_channel       "email", "slack", or "both"
  digest_email         recipient address (email channel)
  slack_webhook_url    Slack Incoming Webhook URL (slack channel — create one
                        at api.slack.com/apps -> your app -> Incoming Webhooks)

Triggered once a day as part of the existing Vercel Cron run
(/api/cron/run-all), right after sources are pulled and expired leads are
cleaned up, so the numbers reflect the day's fresh pipeline state.
"""
import requests

import db
import gmail_bridge


def _build_text() -> str:
    leads = db.list_leads()
    active = [l for l in leads if l["stage"] not in ("Won", "Lost")]
    due = [l for l in active if l.get("follow_up") and l["follow_up"] <= db.today()]
    new_today = [l for l in leads if (l.get("created_at") or "")[:10] == db.today()]
    pipeline_value = sum(l["tentative_value"] for l in active)

    lines = [
        f"Raid Alpha daily digest — {db.today()}",
        f"Active leads: {len(active)} | Pipeline value: ${pipeline_value:,}",
        f"New today: {len(new_today)} | Follow-ups due: {len(due)}",
    ]
    if due:
        lines.append("\nFollow-ups due:")
        lines += [f"  - {l['org']} ({l['stage']})" for l in due[:10]]
    if new_today:
        lines.append("\nNew leads today:")
        lines += [f"  - {l['org']} — {l['segment']} — score {l['score']}, "
                   f"{l.get('alignment_pct', 0)}% aligned" for l in new_today[:10]]
    return "\n".join(lines)


def send() -> dict:
    if (db.get_setting("digest_enabled") or "").lower() != "true":
        return {"skipped": "digest not enabled in Settings"}

    text = _build_text()
    channel = db.get_setting("digest_channel") or "email"
    result = {}

    if channel in ("slack", "both"):
        webhook = db.get_setting("slack_webhook_url")
        if webhook:
            try:
                r = requests.post(webhook, json={"text": text}, timeout=15)
                result["slack"] = "sent" if r.ok else f"error {r.status_code}: {r.text[:150]}"
            except Exception as e:
                result["slack"] = f"error: {e}"
        else:
            result["slack"] = "no Slack webhook URL configured"

    if channel in ("email", "both"):
        to = db.get_setting("digest_email")
        if to:
            try:
                gmail_bridge.send_raw_email(to, f"Raid Alpha digest — {db.today()}", text)
                result["email"] = "sent"
            except Exception as e:
                result["email"] = f"error: {e}"
        else:
            result["email"] = "no digest recipient email configured"

    return result
