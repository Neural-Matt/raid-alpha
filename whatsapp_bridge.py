"""WhatsApp Business Cloud API — official Meta API for sending messages.

Setup (one-time, ~10 minutes):
  1. developers.facebook.com -> create a Meta App -> add the "WhatsApp" product.
  2. Under WhatsApp -> API Setup: note the **Phone Number ID**, and generate a
     permanent access token (Business Settings -> System Users -> generate
     token with whatsapp_business_messaging permission — the 24h test token
     shown by default will expire and need replacing otherwise).
  3. While the app is in Development mode you can only message numbers added
     as verified testers; move the app to Live (needs Meta Business
     verification) to message any number.
  4. Paste the Phone Number ID and access token into Settings -> WhatsApp.

Important Meta policy (not a limitation of this code): outbound messages
only deliver freely within 24 hours of the recipient last messaging you.
Outside that window Meta requires a pre-approved message *template* — a
plain free-text message like the rest of this CRM sends will be rejected.
This module sends free-text only; if you need first-contact outreach via
WhatsApp, set up an approved template in Meta Business Manager and this
function will need a small follow-up change to use it.

Unlike the wa.me links used elsewhere in the CRM (which just open WhatsApp
for you to send manually), this sends directly from your business number
via the API — no human has to click send.
"""
import requests

import db

API_VERSION = "v20.0"


def configured() -> bool:
    return bool(db.get_setting("whatsapp_token") and db.get_setting("whatsapp_phone_id"))


def send_message(lead_id: str, to: str, body: str) -> dict:
    token = db.get_setting("whatsapp_token")
    phone_id = db.get_setting("whatsapp_phone_id")
    if not token or not phone_id:
        raise RuntimeError("Add your WhatsApp Business API token and Phone Number ID in Settings first.")
    digits = "".join(ch for ch in (to or "") if ch.isdigit())
    if len(digits) < 8:
        raise RuntimeError("No valid phone number for this lead.")

    resp = requests.post(
        f"https://graph.facebook.com/{API_VERSION}/{phone_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={"messaging_product": "whatsapp", "to": digits, "type": "text",
              "text": {"body": body, "preview_url": False}},
        timeout=20,
    )
    if not resp.ok:
        detail = ""
        try:
            detail = resp.json().get("error", {}).get("message", "")
        except Exception:
            pass
        raise RuntimeError(f"WhatsApp send failed ({resp.status_code}): {detail or resp.text[:200]}")

    data = resp.json()
    msg_id = (data.get("messages") or [{}])[0].get("id", "")
    db.record_email(lead_id, "", msg_id or db.uid(), "out", "WhatsApp message", body[:200], db.now())
    return data
