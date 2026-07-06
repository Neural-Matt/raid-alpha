"""Racuda Alpha — lead command center server.

Run:  python app.py     then open http://127.0.0.1:8765
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import db
import enrich
import gmail_bridge
from sources import REGISTRY, describe

db.init()
app = FastAPI(title="Racuda Alpha")
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


@app.post("/api/sources/{key}/run")
def api_run_source(key: str):
    mod = REGISTRY.get(key)
    if not mod:
        return JSONResponse({"error": "unknown source"}, status_code=404)
    settings = db.all_settings()
    try:
        raw_leads = mod.pull(settings)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    added, skipped = 0, 0
    for raw in raw_leads:
        lead = enrich.score_lead(raw)
        if db.insert_lead(lead, f"Pulled from {lead.get('source', key)}"):
            added += 1
        else:
            skipped += 1
    return {"added": added, "duplicates_skipped": skipped, "fetched": len(raw_leads)}


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
    print("\n  Racuda Alpha -> http://127.0.0.1:8765\n")
    uvicorn.run(app, host="127.0.0.1", port=8765)
