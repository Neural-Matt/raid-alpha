"""Postgres storage for Racuda Alpha.

Connects via POSTGRES_URL (Vercel Postgres convention) or DATABASE_URL.
Works the same locally (point it at any Postgres instance) and once deployed.
"""
import os
import uuid
import datetime

import psycopg2
import psycopg2.extras
import psycopg2.errors

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    org TEXT NOT NULL,
    contact TEXT DEFAULT '',
    role TEXT DEFAULT '',
    email TEXT DEFAULT '',
    country TEXT DEFAULT '',
    segment TEXT DEFAULT '',
    source TEXT DEFAULT '',
    stage TEXT DEFAULT 'New',
    score INTEGER DEFAULT 0,
    tentative_value INTEGER DEFAULT 0,
    trigger TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    url TEXT DEFAULT '',
    follow_up TEXT DEFAULT '',
    dedupe_key TEXT UNIQUE,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    lead_id TEXT,
    date TEXT,
    text TEXT
);
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT,
    body TEXT
);
CREATE TABLE IF NOT EXISTS todos (
    id TEXT PRIMARY KEY,
    lead_id TEXT,
    text TEXT,
    due TEXT DEFAULT '',
    done INTEGER DEFAULT 0,
    origin TEXT DEFAULT 'manual',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    lead_id TEXT,
    thread_id TEXT,
    msg_id TEXT UNIQUE,
    direction TEXT,
    subject TEXT,
    snippet TEXT,
    date TEXT
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

DEFAULT_TEMPLATES = [
    (
        "Donor / NGO — M&E & data collection",
        "Subject: Local data collection & M&E partner for {{org}}\n\n"
        "Dear {{first_name}},\n\n"
        "I noticed {{trigger}} — congratulations. I'm reaching out from Neural Cloud "
        "Enterprise, a Lusaka-based data consultancy specialising in survey design, digital "
        "data collection (KoboToolbox, ODK, SurveyCTO) and full M&E cycles including "
        "baseline/endline studies.\n\n"
        "We work as a local implementing partner for donor-funded programmes across the "
        "region, handling enumeration, field management and analysis with rigorous data "
        "quality controls.\n\n"
        "Would you be open to a short call to see whether we could support {{org}}'s "
        "upcoming data needs?\n\n"
        "Best regards,\n{{sender_name}}\nNeural Cloud Enterprise",
    ),
    (
        "Corporate — BI & reporting automation",
        "Subject: Cutting reporting time for {{org}}\n\n"
        "Hi {{first_name}},\n\n"
        "{{trigger}} — which usually means the reporting workload on your team is growing "
        "too. Neural Cloud Enterprise builds executive dashboards and automated reporting "
        "pipelines (Power BI, SQL, Python) that replace manual month-end spreadsheet work "
        "with live, self-service views.\n\n"
        "Would a 20-minute call next week be worthwhile to explore what this could look "
        "like for {{org}}?\n\n"
        "Best regards,\n{{sender_name}}\nNeural Cloud Enterprise",
    ),
    (
        "Follow-up — no reply",
        "Subject: Re: {{org}} — quick follow-up\n\n"
        "Hi {{first_name}},\n\n"
        "Just floating this back to the top of your inbox. If data and reporting support "
        "isn't relevant right now, a one-line \"not now\" is completely fine and I'll close "
        "the loop.\n\n"
        "Best regards,\n{{sender_name}}",
    ),
]


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def today() -> str:
    return datetime.date.today().isoformat()


def uid() -> str:
    return uuid.uuid4().hex[:12]


def connect():
    dsn = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "POSTGRES_URL (or DATABASE_URL) environment variable is not set. "
            "Attach a Postgres database (e.g. Vercel Postgres) and set the connection string.")
    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)


def init() -> None:
    con = connect()
    cur = con.cursor()
    cur.execute(SCHEMA)
    cur.execute("SELECT COUNT(*) AS c FROM templates")
    if cur.fetchone()["c"] == 0:
        for name, body in DEFAULT_TEMPLATES:
            cur.execute(
                "INSERT INTO templates (id, name, body) VALUES (%s,%s,%s)",
                (uid(), name, body),
            )
    con.commit()
    cur.close()
    con.close()


# ---------------- leads ----------------

def list_leads():
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM leads ORDER BY score DESC, created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def get_lead(lead_id):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM leads WHERE id=%s", (lead_id,))
    row = cur.fetchone()
    lead = dict(row) if row else None
    if lead:
        cur.execute("SELECT * FROM activities WHERE lead_id=%s ORDER BY date DESC", (lead_id,))
        lead["activities"] = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM emails WHERE lead_id=%s ORDER BY date DESC", (lead_id,))
        lead["emails"] = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM todos WHERE lead_id=%s AND done=0 ORDER BY due", (lead_id,))
        lead["todos"] = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return lead


LEAD_FIELDS = ["org", "contact", "role", "email", "country", "segment", "source",
               "stage", "score", "tentative_value", "trigger", "notes", "url", "follow_up"]


def insert_lead(data: dict, log: str = "Lead created"):
    """Insert a lead. Returns id, or None if it's a duplicate (dedupe_key clash)."""
    con = connect()
    cur = con.cursor()
    lid = uid()
    dedupe = data.get("dedupe_key") or f"{data.get('org','').lower().strip()}|{data.get('trigger','').lower().strip()[:80]}"
    values = {f: data.get(f, "") for f in LEAD_FIELDS}
    values["score"] = int(data.get("score") or 0)
    values["tentative_value"] = int(data.get("tentative_value") or 0)
    values["stage"] = data.get("stage") or "New"
    try:
        cur.execute(
            f"INSERT INTO leads (id,{','.join(LEAD_FIELDS)},dedupe_key,created_at,updated_at) "
            f"VALUES (%s,{','.join('%s' for _ in LEAD_FIELDS)},%s,%s,%s)",
            [lid] + [values[f] for f in LEAD_FIELDS] + [dedupe, now(), now()],
        )
    except psycopg2.errors.UniqueViolation:
        con.rollback()
        cur.close()
        con.close()
        return None
    cur.execute("INSERT INTO activities (id, lead_id, date, text) VALUES (%s,%s,%s,%s)",
                (uid(), lid, today(), log))
    con.commit()
    cur.close()
    con.close()
    return lid


def update_lead(lead_id, patch: dict, log: str | None = None):
    fields = [f for f in LEAD_FIELDS if f in patch]
    if not fields and not log:
        return
    con = connect()
    cur = con.cursor()
    if fields:
        sets = ", ".join(f"{f}=%s" for f in fields)
        cur.execute(f"UPDATE leads SET {sets}, updated_at=%s WHERE id=%s",
                    [patch[f] for f in fields] + [now(), lead_id])
    if log:
        cur.execute("INSERT INTO activities (id, lead_id, date, text) VALUES (%s,%s,%s,%s)",
                    (uid(), lead_id, today(), log))
    con.commit()
    cur.close()
    con.close()


def delete_lead(lead_id):
    con = connect()
    cur = con.cursor()
    for table in ("leads", "activities", "emails"):
        cur.execute(f"DELETE FROM {table} WHERE {'id' if table=='leads' else 'lead_id'}=%s", (lead_id,))
    cur.execute("DELETE FROM todos WHERE lead_id=%s", (lead_id,))
    con.commit()
    cur.close()
    con.close()


def find_lead_by_email(email: str):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM leads WHERE lower(email)=lower(%s)", (email,))
    row = cur.fetchone()
    cur.close()
    con.close()
    return dict(row) if row else None


# ---------------- templates ----------------

def list_templates():
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM templates")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def save_template(tid, name, body):
    con = connect()
    cur = con.cursor()
    if tid:
        cur.execute("UPDATE templates SET name=%s, body=%s WHERE id=%s", (name, body, tid))
    else:
        tid = uid()
        cur.execute("INSERT INTO templates (id, name, body) VALUES (%s,%s,%s)", (tid, name, body))
    con.commit()
    cur.close()
    con.close()
    return tid


def delete_template(tid):
    con = connect()
    cur = con.cursor()
    cur.execute("DELETE FROM templates WHERE id=%s", (tid,))
    con.commit()
    cur.close()
    con.close()


# ---------------- todos ----------------

def list_todos(include_done=False):
    con = connect()
    cur = con.cursor()
    q = ("SELECT t.*, l.org AS lead_org FROM todos t LEFT JOIN leads l ON l.id=t.lead_id "
         + ("" if include_done else "WHERE t.done=0 ")
         + "ORDER BY t.done, CASE WHEN t.due='' THEN 1 ELSE 0 END, t.due")
    cur.execute(q)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def add_todo(text, lead_id=None, due="", origin="manual"):
    con = connect()
    cur = con.cursor()
    # avoid duplicate auto-generated todos
    if origin != "manual":
        cur.execute("SELECT 1 FROM todos WHERE text=%s AND done=0", (text,))
        dup = cur.fetchone()
        if dup:
            cur.close()
            con.close()
            return None
    tid = uid()
    cur.execute("INSERT INTO todos (id, lead_id, text, due, origin, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                (tid, lead_id, text, due, origin, now()))
    con.commit()
    cur.close()
    con.close()
    return tid


def set_todo(tid, done=None, text=None, due=None):
    con = connect()
    cur = con.cursor()
    if done is not None:
        cur.execute("UPDATE todos SET done=%s WHERE id=%s", (1 if done else 0, tid))
    if text is not None:
        cur.execute("UPDATE todos SET text=%s WHERE id=%s", (text, tid))
    if due is not None:
        cur.execute("UPDATE todos SET due=%s WHERE id=%s", (due, tid))
    con.commit()
    cur.close()
    con.close()


# ---------------- emails ----------------

def record_email(lead_id, thread_id, msg_id, direction, subject, snippet, date):
    con = connect()
    cur = con.cursor()
    try:
        cur.execute(
            "INSERT INTO emails (id, lead_id, thread_id, msg_id, direction, subject, snippet, date) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (uid(), lead_id, thread_id, msg_id, direction, subject, snippet, date))
        con.commit()
        new = True
    except psycopg2.errors.UniqueViolation:
        con.rollback()
        new = False
    cur.close()
    con.close()
    return new


# ---------------- settings ----------------

def get_setting(key, default=""):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT value FROM settings WHERE key=%s", (key,))
    row = cur.fetchone()
    cur.close()
    con.close()
    return row["value"] if row else default


def set_setting(key, value):
    con = connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO settings (key, value) VALUES (%s,%s) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (key, value))
    con.commit()
    cur.close()
    con.close()


def all_settings():
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM settings")
    rows = {r["key"]: r["value"] for r in cur.fetchall()}
    cur.close()
    con.close()
    return rows
