"""Postgres storage for Raid Alpha.

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
    phone TEXT DEFAULT '',
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
    matched_service TEXT DEFAULT '',
    match_score INTEGER DEFAULT 0,
    match_reasoning TEXT DEFAULT '',
    score_breakdown TEXT DEFAULT '[]',
    value_note TEXT DEFAULT '',
    deadline TEXT DEFAULT '',
    how_to_apply TEXT DEFAULT '',
    alignment_pct INTEGER DEFAULT 0,
    snoozed_until TEXT DEFAULT '',
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS services (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT
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
    body TEXT,
    segment TEXT DEFAULT ''
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
    # migrations for columns added after the table already existed in production
    cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS matched_service TEXT DEFAULT ''")
    cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS match_score INTEGER DEFAULT 0")
    cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS match_reasoning TEXT DEFAULT ''")
    cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS score_breakdown TEXT DEFAULT '[]'")
    cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS value_note TEXT DEFAULT ''")
    cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS deadline TEXT DEFAULT ''")
    cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS how_to_apply TEXT DEFAULT ''")
    cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS phone TEXT DEFAULT ''")
    cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS alignment_pct INTEGER DEFAULT 0")
    cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS snoozed_until TEXT DEFAULT ''")
    cur.execute("ALTER TABLE templates ADD COLUMN IF NOT EXISTS segment TEXT DEFAULT ''")
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


LEAD_FIELDS = ["org", "contact", "role", "email", "phone", "country", "segment", "source",
               "stage", "score", "tentative_value", "trigger", "notes", "url", "follow_up",
               "matched_service", "match_score", "match_reasoning",
               "score_breakdown", "value_note", "deadline", "how_to_apply", "alignment_pct",
               "snoozed_until"]


def is_past_deadline(deadline: str) -> bool:
    if not deadline:
        return False
    try:
        return datetime.date.fromisoformat(str(deadline)[:10]) < datetime.date.today()
    except ValueError:
        return False


def insert_lead(data: dict, log: str = "Lead created"):
    """Insert a lead. Returns id, or None if it's a duplicate (dedupe_key clash)
    or its application deadline has already passed — a lead you can no longer
    act on has no place cluttering an active pipeline."""
    if is_past_deadline(data.get("deadline")):
        return None
    con = connect()
    cur = con.cursor()
    lid = uid()
    dedupe = data.get("dedupe_key") or f"{data.get('org','').lower().strip()}|{data.get('trigger','').lower().strip()[:80]}"
    values = {f: data.get(f, "") for f in LEAD_FIELDS}
    values["score"] = int(data.get("score") or 0)
    values["tentative_value"] = int(data.get("tentative_value") or 0)
    values["match_score"] = int(data.get("match_score") or 0)
    values["alignment_pct"] = int(data.get("alignment_pct") or 0)
    values["score_breakdown"] = data.get("score_breakdown") or "[]"
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


def delete_expired_leads() -> int:
    """Remove active-pipeline leads whose application deadline has passed.

    Won/Lost leads are left alone even if their deadline has passed — those
    are resolved outcomes, not dead weight sitting in an active pipeline.
    """
    con = connect()
    cur = con.cursor()
    cur.execute(
        "SELECT id FROM leads WHERE deadline <> '' AND deadline < %s "
        "AND stage NOT IN ('Won','Lost')", (today(),))
    ids = [r["id"] for r in cur.fetchall()]
    for lid in ids:
        for table in ("activities", "emails", "todos"):
            cur.execute(f"DELETE FROM {table} WHERE lead_id=%s", (lid,))
        cur.execute("DELETE FROM leads WHERE id=%s", (lid,))
    con.commit()
    cur.close()
    con.close()
    return len(ids)


def list_all_activities(limit: int = 300) -> list[dict]:
    """Global audit trail across every lead, most recent first."""
    con = connect()
    cur = con.cursor()
    cur.execute("""
        SELECT a.id, a.lead_id, a.date, a.text, l.org AS lead_org
        FROM activities a LEFT JOIN leads l ON l.id = a.lead_id
        ORDER BY a.date DESC LIMIT %s
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def bulk_update_stage(ids: list[str], stage: str) -> int:
    if not ids:
        return 0
    con = connect()
    cur = con.cursor()
    cur.execute(f"UPDATE leads SET stage=%s, updated_at=%s WHERE id IN ({','.join(['%s']*len(ids))})",
                [stage, now()] + ids)
    for lid in ids:
        cur.execute("INSERT INTO activities (id, lead_id, date, text) VALUES (%s,%s,%s,%s)",
                    (uid(), lid, today(), f"Stage → {stage} (bulk action)"))
    con.commit()
    cur.close()
    con.close()
    return len(ids)


def bulk_delete(ids: list[str]) -> int:
    if not ids:
        return 0
    con = connect()
    cur = con.cursor()
    ph = ",".join(["%s"] * len(ids))
    for table in ("activities", "emails", "todos"):
        cur.execute(f"DELETE FROM {table} WHERE lead_id IN ({ph})", ids)
    cur.execute(f"DELETE FROM leads WHERE id IN ({ph})", ids)
    con.commit()
    cur.close()
    con.close()
    return len(ids)


def find_duplicate_groups() -> list[list[dict]]:
    """Group leads that look like the same organisation: same normalized org
    name, or same non-empty email. Returns only groups with 2+ members, most
    recently-touched group first."""
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM leads ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()

    by_org: dict[str, list[dict]] = {}
    by_email: dict[str, list[dict]] = {}
    for r in rows:
        key = (r.get("org") or "").strip().lower()
        if key:
            by_org.setdefault(key, []).append(r)
        email = (r.get("email") or "").strip().lower()
        if email:
            by_email.setdefault(email, []).append(r)

    groups, seen_ids = [], set()
    for bucket in (by_email, by_org):
        for members in bucket.values():
            if len(members) < 2:
                continue
            ids = tuple(sorted(m["id"] for m in members))
            if ids in seen_ids:
                continue
            seen_ids.add(ids)
            groups.append(members)
    return groups


def merge_leads(keep_id: str, remove_id: str) -> bool:
    """Fold remove_id's activities/emails/todos into keep_id, then delete remove_id."""
    if keep_id == remove_id:
        return False
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM leads WHERE id=%s", (keep_id,))
    if not cur.fetchone():
        cur.close()
        con.close()
        return False
    for table in ("activities", "emails", "todos"):
        cur.execute(f"UPDATE {table} SET lead_id=%s WHERE lead_id=%s", (keep_id, remove_id))
    cur.execute("INSERT INTO activities (id, lead_id, date, text) VALUES (%s,%s,%s,%s)",
                (uid(), keep_id, today(), f"Merged duplicate lead {remove_id} into this one"))
    cur.execute("DELETE FROM leads WHERE id=%s", (remove_id,))
    con.commit()
    cur.close()
    con.close()
    return True


def stats_by_source() -> list[dict]:
    con = connect()
    cur = con.cursor()
    cur.execute("""
        SELECT source,
               COUNT(*) AS total,
               SUM(CASE WHEN stage='Won' THEN 1 ELSE 0 END) AS won,
               SUM(CASE WHEN stage='Won' THEN tentative_value ELSE 0 END) AS won_value,
               SUM(CASE WHEN stage NOT IN ('Won','Lost') THEN 1 ELSE 0 END) AS active
        FROM leads GROUP BY source ORDER BY won_value DESC, total DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def stats_by_segment() -> list[dict]:
    con = connect()
    cur = con.cursor()
    cur.execute("""
        SELECT segment,
               COUNT(*) AS total,
               SUM(CASE WHEN stage NOT IN ('Won','Lost') THEN 1 ELSE 0 END) AS active,
               SUM(CASE WHEN stage NOT IN ('Won','Lost') THEN tentative_value ELSE 0 END) AS active_value,
               SUM(CASE WHEN stage='Won' THEN 1 ELSE 0 END) AS won,
               SUM(CASE WHEN stage='Won' THEN tentative_value ELSE 0 END) AS won_value,
               AVG(score) AS avg_score, AVG(alignment_pct) AS avg_alignment
        FROM leads GROUP BY segment ORDER BY active_value DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def stats_trend(days: int = 30) -> list[dict]:
    """Average fit score & alignment of leads *created* on each of the last N
    days — an approximation of "is lead quality improving", since we don't
    keep historical score snapshots, only the score a lead was given at
    creation time."""
    con = connect()
    cur = con.cursor()
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    cur.execute("""
        SELECT substr(created_at,1,10) AS day,
               COUNT(*) AS n, AVG(score) AS avg_score, AVG(alignment_pct) AS avg_alignment
        FROM leads WHERE substr(created_at,1,10) >= %s
        GROUP BY day ORDER BY day
    """, (since,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def find_lead_by_email(email: str):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM leads WHERE lower(email)=lower(%s)", (email,))
    row = cur.fetchone()
    cur.close()
    con.close()
    return dict(row) if row else None


# ---------------- services ----------------

def list_services():
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM services ORDER BY created_at")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def save_service(sid, name, description):
    con = connect()
    cur = con.cursor()
    if sid:
        cur.execute("UPDATE services SET name=%s, description=%s WHERE id=%s", (name, description, sid))
    else:
        sid = uid()
        cur.execute("INSERT INTO services (id, name, description, created_at) VALUES (%s,%s,%s,%s)",
                    (sid, name, description, now()))
    con.commit()
    cur.close()
    con.close()
    return sid


def delete_service(sid):
    con = connect()
    cur = con.cursor()
    cur.execute("DELETE FROM services WHERE id=%s", (sid,))
    con.commit()
    cur.close()
    con.close()


# ---------------- templates ----------------

def list_templates():
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM templates")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def save_template(tid, name, body, segment=""):
    con = connect()
    cur = con.cursor()
    if tid:
        cur.execute("UPDATE templates SET name=%s, body=%s, segment=%s WHERE id=%s", (name, body, segment, tid))
    else:
        tid = uid()
        cur.execute("INSERT INTO templates (id, name, body, segment) VALUES (%s,%s,%s,%s)",
                    (tid, name, body, segment))
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
