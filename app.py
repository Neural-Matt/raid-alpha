"""Raid Alpha — lead command center server.

Run:  python app.py     then open http://127.0.0.1:8765
"""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import bot
import db
import enrich
import gmail_bridge
from sources import REGISTRY, describe

db.init()
app = FastAPI(title="Raid Alpha")
STATIC = Path(__file__).parent / "static"


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


# ---------------- leads ----------------

@app.get("/api/leads")
def api_leads():
    return db.list_leads()


@app.get("/api/leads/{lead_id}")
def api_lead(lead_id: str):
    lead = db.get_lead(lead_id)
    return lead or JSONResponse({"error": "not found"}, status_code=404)


@app.post("/api/leads")
async def api_add_lead(req: Request):
    data = await req.json()
    data["source"] = data.get("source") or "Manual"
    lead = enrich.score_lead(data)
    # manual adds should never be silently dropped as dupes
    lead["dedupe_key"] = f"manual|{db.uid()}"
    lid = db.insert_lead(lead, "Lead added manually")

    if bot.configured() and lid:
        services = db.list_services()
        if services:
            try:
                matches = bot.match_leads([db.get_lead(lid)], services)
            except Exception:
                matches = {}
            m = matches.get(0)
            if m:
                db.update_lead(lid, {
                    "matched_service": m["service_name"],
                    "match_score": m["score"],
                    "match_reasoning": m["reasoning"],
                })

    return {"id": lid}


@app.patch("/api/leads/{lead_id}")
async def api_update_lead(lead_id: str, req: Request):
    body = await req.json()
    db.update_lead(lead_id, body.get("patch", {}), body.get("log"))
    return {"ok": True}


@app.delete("/api/leads/{lead_id}")
def api_delete_lead(lead_id: str):
    db.delete_lead(lead_id)
    return {"ok": True}


# ---------------- sources ----------------

@app.get("/api/sources")
def api_sources():
    return describe()


def _run_source(key: str) -> dict:
    """Pull + score + match one source. Returns a plain dict (never a Response)
    so it can be reused by both the interactive endpoint and the cron job."""
    mod = REGISTRY.get(key)
    if not mod:
        return {"error": "unknown source"}
    settings = db.all_settings()
    try:
        raw_leads = mod.pull(settings)
    except Exception as e:
        return {"error": str(e)}

    added, skipped = 0, 0
    new_lead_ids = []
    for raw in raw_leads:
        lead = enrich.score_lead(raw)
        lid = db.insert_lead(lead, f"Pulled from {lead.get('source', key)}")
        if lid:
            added += 1
            new_lead_ids.append(lid)
        else:
            skipped += 1

    if bot.configured() and new_lead_ids:
        services = db.list_services()
        new_leads = [db.get_lead(lid) for lid in new_lead_ids]
        try:
            matches = bot.match_leads(new_leads, services)
        except Exception:
            matches = {}
        for i, lid in enumerate(new_lead_ids):
            m = matches.get(i)
            if m:
                db.update_lead(lid, {
                    "matched_service": m["service_name"],
                    "match_score": m["score"],
                    "match_reasoning": m["reasoning"],
                })

    return {"added": added, "duplicates_skipped": skipped, "fetched": len(raw_leads)}


@app.post("/api/sources/{key}/run")
def api_run_source(key: str):
    if key not in REGISTRY:
        return JSONResponse({"error": "unknown source"}, status_code=404)
    result = _run_source(key)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return result


@app.get("/api/cron/run-all")
def api_cron_run_all(request: Request):
    """Scheduled entrypoint for Vercel Cron: runs every source + a Gmail sync.

    Vercel automatically sends `Authorization: Bearer <CRON_SECRET>` on
    cron-triggered requests when an env var named exactly CRON_SECRET is set
    — set one to stop this (otherwise-public) endpoint being triggerable by
    anyone who finds the URL.
    """
    secret = os.environ.get("CRON_SECRET")
    if secret and request.headers.get("authorization") != f"Bearer {secret}":
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    results = {key: _run_source(key) for key in REGISTRY}
    try:
        gmail_result = gmail_bridge.sync()
    except Exception as e:
        gmail_result = {"error": str(e)}
    return {"sources": results, "gmail": gmail_result}


# ---------------- services ----------------

@app.get("/api/services")
def api_services():
    return db.list_services()


@app.post("/api/services")
async def api_save_service(req: Request):
    s = await req.json()
    sid = db.save_service(s.get("id"), s.get("name", "Service"), s.get("description", ""))
    return {"id": sid}


@app.delete("/api/services/{sid}")
def api_delete_service(sid: str):
    db.delete_service(sid)
    return {"ok": True}


@app.get("/api/bot/status")
def api_bot_status():
    return {"configured": bot.configured()}


@app.post("/api/services/rematch")
def api_rematch():
    if not bot.configured():
        return JSONResponse({"error": "GEMINI_API_KEY not set"}, status_code=400)
    services = db.list_services()
    if not services:
        return JSONResponse({"error": "No services defined yet"}, status_code=400)
    leads = db.list_leads()
    matched = 0
    batch_size = 40
    for start in range(0, len(leads), batch_size):
        batch = leads[start:start + batch_size]
        try:
            matches = bot.match_leads(batch, services)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        for i, lead in enumerate(batch):
            m = matches.get(i)
            if m:
                db.update_lead(lead["id"], {
                    "matched_service": m["service_name"],
                    "match_score": m["score"],
                    "match_reasoning": m["reasoning"],
                })
                matched += 1
    return {"matched": matched, "total": len(leads)}


# ---------------- templates ----------------

@app.get("/api/templates")
def api_templates():
    return db.list_templates()


@app.post("/api/templates")
async def api_save_template(req: Request):
    t = await req.json()
    tid = db.save_template(t.get("id"), t.get("name", "Template"), t.get("body", ""))
    return {"id": tid}


@app.delete("/api/templates/{tid}")
def api_delete_template(tid: str):
    db.delete_template(tid)
    return {"ok": True}


# ---------------- todos ----------------

@app.get("/api/todos")
def api_todos(all: int = 0):
    return db.list_todos(include_done=bool(all))


@app.post("/api/todos")
async def api_add_todo(req: Request):
    t = await req.json()
    tid = db.add_todo(t.get("text", ""), t.get("lead_id"), t.get("due", ""))
    return {"id": tid}


@app.patch("/api/todos/{tid}")
async def api_set_todo(tid: str, req: Request):
    t = await req.json()
    db.set_todo(tid, done=t.get("done"), text=t.get("text"), due=t.get("due"))
    return {"ok": True}


# ---------------- gmail ----------------

@app.get("/api/gmail/status")
def api_gmail_status():
    return gmail_bridge.status()


@app.get("/api/gmail/authorize")
def api_gmail_authorize():
    try:
        url = gmail_bridge.authorize_url()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return RedirectResponse(url)


@app.get("/api/gmail/oauth/callback")
def api_gmail_oauth_callback(request: Request):
    try:
        gmail_bridge.handle_oauth_callback(
            str(request.url.query), request.query_params.get("state", ""))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return RedirectResponse("/#settings")


@app.post("/api/gmail/send")
async def api_gmail_send(req: Request):
    body = await req.json()
    lead_id = body.get("lead_id", "")
    try:
        result = gmail_bridge.send_email(
            lead_id, body["to"], body.get("subject", ""), body.get("body", ""))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    lead = db.get_lead(lead_id)
    if lead and lead["stage"] in ("New", "Researched"):
        db.update_lead(lead_id, {"stage": "Contacted"}, "Email sent via Gmail")
    else:
        db.update_lead(lead_id, {}, "Email sent via Gmail")
    # auto follow-up task in 4 days
    import datetime as _dt
    due = (_dt.date.today() + _dt.timedelta(days=4)).isoformat()
    if lead:
        db.add_todo(f"Follow up with {lead['org']} if no reply", lead_id, due, "auto")
    return result


@app.post("/api/gmail/sync")
def api_gmail_sync():
    try:
        return gmail_bridge.sync()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ---------------- settings & stats ----------------

@app.get("/api/settings")
def api_settings():
    return db.all_settings()


@app.post("/api/settings")
async def api_save_settings(req: Request):
    data = await req.json()
    for k, v in data.items():
        db.set_setting(k, str(v))
    return {"ok": True}


@app.get("/api/stats")
def api_stats():
    leads = db.list_leads()
    active = [l for l in leads if l["stage"] not in ("Won", "Lost")]
    contacted = [l for l in leads if l["stage"] not in ("New", "Researched")]
    replied = [l for l in leads if l["stage"] in ("Replied", "Meeting", "Proposal", "Won")]
    due = [l for l in active if l["follow_up"] and l["follow_up"] <= db.today()]
    return {
        "total": len(leads),
        "active": len(active),
        "pipeline_value": sum(l["tentative_value"] for l in active),
        "won": sum(1 for l in leads if l["stage"] == "Won"),
        "won_value": sum(l["tentative_value"] for l in leads if l["stage"] == "Won"),
        "reply_rate": round(100 * len(replied) / len(contacted)) if contacted else 0,
        "followups_due": len(due),
        "todos_open": len(db.list_todos()),
    }


app.mount("/static", StaticFiles(directory=STATIC), name="static")

if __name__ == "__main__":
    import uvicorn
    print("\n  Raid Alpha -> http://127.0.0.1:8765\n")
    uvicorn.run(app, host="127.0.0.1", port=8765)
