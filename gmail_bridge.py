"""Gmail bridge — send and receive email for leads directly from the CRM.

Uses a server-side OAuth 2.0 "web application" flow: visit /api/gmail/authorize,
approve access in Google's consent screen, and it redirects back to
/api/gmail/oauth/callback, which stores the resulting token in the settings
table (via db.py). This works the same whether the app is running locally or
deployed — there is no local-browser/localhost-only redirect involved.

Setup (one-time):
  1. console.cloud.google.com -> create project -> enable "Gmail API"
  2. OAuth consent screen -> External -> add your own Gmail as a test user
  3. Credentials -> Create OAuth client ID -> Application type: Web application
     -> Authorized redirect URIs, add both:
       http://127.0.0.1:8765/api/gmail/oauth/callback   (local dev)
       https://<your-vercel-domain>/api/gmail/oauth/callback  (deployed)
  4. Set env vars GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI
     (the exact redirect URI for whichever environment you're running in)
     wherever the app runs.
"""
from __future__ import annotations
import json
import os
import re
import datetime

import db

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# Phrases in an incoming reply that should become todos
TODO_PATTERNS = [
    (r"\b(demo|demonstration)\b", "Prepare & schedule a demo for {org}"),
    (r"\b(call|meeting|meet|chat|zoom|teams)\b", "Schedule a call with {contact} ({org})"),
    (r"\b(proposal|quote|quotation|pricing|costs?)\b", "Send proposal / pricing to {org}"),
    (r"\b(capability statement|profile|portfolio|references?)\b",
     "Send capability statement to {org}"),
    (r"\b(next week|next month|follow up|circle back|later)\b",
     "Follow up with {org} (they asked for later)"),
]


def _redirect_uri() -> str:
    uri = os.environ.get("GOOGLE_REDIRECT_URI")
    if not uri:
        raise RuntimeError("GOOGLE_REDIRECT_URI env var is not set.")
    if uri.startswith("http://"):
        # allow the plain-http localhost redirect used for local dev
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    return uri


def _client_config() -> dict:
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET env vars are not set. "
            "See the setup steps at the top of gmail_bridge.py / the README.")
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def authorize_url() -> str:
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=_redirect_uri())
    url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent")
    db.set_setting("gmail_oauth_state", state)
    # PKCE: the code_verifier flow.authorization_url() just generated must be
    # replayed on the *same* flow object at fetch_token() time, but the
    # callback is a separate request (a fresh Flow instance) — persist it
    # alongside state rather than relying on in-memory continuity.
    db.set_setting("gmail_oauth_code_verifier", flow.code_verifier or "")
    return url


def handle_oauth_callback(query_string: str, state: str) -> None:
    from google_auth_oauthlib.flow import Flow
    saved_state = db.get_setting("gmail_oauth_state")
    if not saved_state or state != saved_state:
        raise RuntimeError("OAuth state mismatch — please retry authorization from Settings.")
    code_verifier = db.get_setting("gmail_oauth_code_verifier") or None
    flow = Flow.from_client_config(
        _client_config(), scopes=SCOPES, redirect_uri=_redirect_uri(), state=state,
        code_verifier=code_verifier)
    authorization_response = f"{_redirect_uri()}?{query_string}"
    flow.fetch_token(authorization_response=authorization_response)
    db.set_setting("gmail_token", flow.credentials.to_json())
    db.set_setting("gmail_oauth_state", "")
    db.set_setting("gmail_oauth_code_verifier", "")


def _get_service():
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as e:
        raise RuntimeError(
            "Google libraries missing. Run: pip install -r requirements.txt") from e

    token_json = db.get_setting("gmail_token")
    if not token_json:
        raise RuntimeError("Gmail not connected yet. Go to Settings and click Connect Gmail.")
    creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            db.set_setting("gmail_token", creds.to_json())
        else:
            raise RuntimeError("Gmail authorization expired. Reconnect it from Settings.")
    return build("gmail", "v1", credentials=creds)


def status() -> dict:
    return {
        "client_configured": bool(
            os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")),
        "authorized": bool(db.get_setting("gmail_token")),
    }


def send_email(lead_id: str, to: str, subject: str, body: str) -> dict:
    from email.mime.text import MIMEText
    import base64
    service = _get_service()
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    db.record_email(lead_id, sent.get("threadId", ""), sent.get("id", ""),
                    "out", subject, body[:200], db.now())
    return {"id": sent.get("id"), "threadId": sent.get("threadId")}


def send_raw_email(to: str, subject: str, body: str) -> dict:
    """Send without recording against a lead — used for the daily digest."""
    from email.mime.text import MIMEText
    import base64
    service = _get_service()
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"id": sent.get("id"), "threadId": sent.get("threadId")}


def _header(payload: dict, name: str) -> str:
    for h in payload.get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def sync() -> dict:
    """Scan Gmail for conversations with pipeline leads.

    - records new incoming/outgoing messages against each lead
    - bumps stage to 'Replied' when a lead has written back
    - extracts todos (demo, call, proposal, follow-up) from reply text
    """
    service = _get_service()
    leads = [l for l in db.list_leads() if l.get("email")]
    new_msgs, new_todos, replied = 0, 0, 0

    for lead in leads[:80]:
        addr = lead["email"]
        try:
            res = service.users().messages().list(
                userId="me", q=f"(from:{addr} OR to:{addr}) newer_than:60d",
                maxResults=15).execute()
        except Exception:
            continue
        got_reply = False
        for m in res.get("messages", []):
            try:
                full = service.users().messages().get(
                    userId="me", id=m["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]).execute()
            except Exception:
                continue
            payload = full.get("payload", {})
            frm = _header(payload, "From")
            subject = _header(payload, "Subject")
            snippet = full.get("snippet", "")[:300]
            direction = "in" if addr.lower() in frm.lower() else "out"
            ts = int(full.get("internalDate", "0")) / 1000
            date = datetime.datetime.fromtimestamp(ts).isoformat(timespec="seconds") if ts else db.now()
            if db.record_email(lead["id"], full.get("threadId", ""), m["id"],
                               direction, subject, snippet, date):
                new_msgs += 1
                if direction == "in":
                    got_reply = True
                    # mine the snippet for actionable asks
                    blob = (subject + " " + snippet).lower()
                    for pattern, template in TODO_PATTERNS:
                        if re.search(pattern, blob):
                            text = template.format(
                                org=lead["org"], contact=lead.get("contact") or lead["org"])
                            due = (datetime.date.today() +
                                   datetime.timedelta(days=2)).isoformat()
                            if db.add_todo(text, lead_id=lead["id"], due=due,
                                           origin="gmail"):
                                new_todos += 1
                            break
        if got_reply and lead["stage"] in ("New", "Researched", "Contacted"):
            db.update_lead(lead["id"], {"stage": "Replied"},
                           "Reply detected in Gmail — stage → Replied")
            replied += 1

    return {"new_messages": new_msgs, "new_todos": new_todos,
            "stage_bumps": replied, "leads_checked": len(leads)}
