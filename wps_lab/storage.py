"""Minimal, explicit SQLite schema for synthetic, consent-based demonstrations."""
from __future__ import annotations

import csv
import io
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def database(path: Path):
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with database(path) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('draft', 'active', 'closed')),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
            alias TEXT NOT NULL,
            consent INTEGER NOT NULL CHECK(consent IN (0, 1)),
            UNIQUE(campaign_id, alias)
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
            participant_id INTEGER NOT NULL REFERENCES participants(id),
            kind TEXT NOT NULL CHECK(kind = 'acknowledged'),
            created_at TEXT NOT NULL,
            UNIQUE(campaign_id, participant_id, kind)
        );
        CREATE INDEX IF NOT EXISTS idx_events_campaign ON events(campaign_id);
        """)
        con.execute("INSERT OR IGNORE INTO campaigns VALUES (1, ?, 'active', ?)",
                    ("Demo: Recognizing suspicious messages", _now()))
        con.execute("INSERT OR IGNORE INTO campaigns VALUES (2, ?, 'draft', ?)",
                    ("Demo: Reporting security concerns", _now()))
        for i in range(1, 7):
            con.execute("INSERT OR IGNORE INTO participants VALUES (?, 1, ?, 1)",
                        (i, f"TRAIN-{i:03d}"))
        for i in range(7, 10):
            con.execute("INSERT OR IGNORE INTO participants VALUES (?, 2, ?, 1)",
                        (i, f"TRAIN-{i:03d}"))


def overview(path: Path) -> dict:
    with database(path) as con:
        campaigns = con.execute("SELECT count(*) FROM campaigns").fetchone()[0]
        active = con.execute("SELECT count(*) FROM campaigns WHERE state='active'").fetchone()[0]
        participants = con.execute("SELECT count(*) FROM participants WHERE consent=1").fetchone()[0]
        acknowledged = con.execute("SELECT count(*) FROM events WHERE kind='acknowledged'").fetchone()[0]
    return {"campaigns": campaigns, "active": active,
            "consented_participants": participants, "acknowledgements": acknowledged,
            "origin": "synthetic local demo", "credential_collection": False}


def campaigns(path: Path) -> list[dict]:
    with database(path) as con:
        rows = con.execute("""
          SELECT c.id, c.name, c.state, c.created_at,
                 count(DISTINCT p.id) AS consented,
                 count(DISTINCT e.participant_id) AS acknowledged
          FROM campaigns c
          LEFT JOIN participants p ON p.campaign_id=c.id AND p.consent=1
          LEFT JOIN events e ON e.campaign_id=c.id AND e.kind='acknowledged'
          GROUP BY c.id ORDER BY c.id
        """).fetchall()
    return [dict(r) for r in rows]


def create_campaign(path: Path, name: str) -> int:
    """Create a draft scenario. No outbound campaign action is performed."""
    name = name.strip()
    if not 3 <= len(name) <= 100 or any(ord(ch) < 32 for ch in name):
        raise ValueError("Campaign name must contain 3 to 100 printable characters")
    with database(path) as con:
        cursor = con.execute(
            "INSERT INTO campaigns (name, state, created_at) VALUES (?, 'draft', ?)",
            (name, _now()))
        return int(cursor.lastrowid)


def change_campaign_state(path: Path, campaign_id: int, state: str) -> bool:
    """Transition a synthetic campaign; closed campaigns cannot issue new links."""
    if state not in ("draft", "active", "closed"):
        raise ValueError("Invalid campaign state")
    with database(path) as con:
        result = con.execute("UPDATE campaigns SET state=? WHERE id=?", (state, campaign_id))
        return bool(result.rowcount)


def create_alias(path: Path, campaign_id: int, alias: str, consent: bool = False) -> int:
    """Only fictional TRAIN- codes are accepted, never email or phone contacts."""
    import re

    alias = alias.strip().upper()
    if not re.fullmatch(r"TRAIN-[A-Z0-9]{3,8}", alias):
        raise ValueError("Use a synthetic participant code such as TRAIN-010")
    with database(path) as con:
        row = con.execute("SELECT 1 FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown campaign")
        try:
            result = con.execute(
                "INSERT INTO participants (campaign_id, alias, consent) VALUES (?,?,?)",
                (campaign_id, alias, int(consent)))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Synthetic alias already exists in the campaign") from exc
        return int(result.lastrowid)


def set_alias_consent(path: Path, campaign_id: int, alias: str, consent: bool) -> bool:
    """Revoking demo consent also deletes the alias's historic acknowledgements."""
    with database(path) as con:
        row = con.execute(
            "SELECT id FROM participants WHERE campaign_id=? AND alias=?",
            (campaign_id, alias.strip().upper())).fetchone()
        if row is None:
            return False
        con.execute("UPDATE participants SET consent=? WHERE id=?", (int(consent), row["id"]))
        if not consent:
            con.execute("DELETE FROM events WHERE participant_id=?", (row["id"],))
        return True


def participants(path: Path, campaign_id: int) -> list[dict]:
    with database(path) as con:
        rows = con.execute("SELECT id, alias, consent FROM participants WHERE campaign_id=? ORDER BY id",
                           (campaign_id,)).fetchall()
    return [dict(r) for r in rows]


def eligible(path: Path, campaign_id: int, participant_id: int) -> bool:
    with database(path) as con:
        row = con.execute("""
          SELECT 1 FROM participants p
          JOIN campaigns c ON c.id=p.campaign_id
          WHERE p.id=? AND p.campaign_id=? AND p.consent=1 AND c.state='active'
        """, (participant_id, campaign_id)).fetchone()
    return bool(row)


def acknowledge(path: Path, campaign_id: int, participant_id: int) -> bool:
    with database(path) as con:
        check = con.execute("""
          SELECT 1 FROM participants p JOIN campaigns c ON p.campaign_id=c.id
          WHERE p.id=? AND p.campaign_id=? AND p.consent=1 AND c.state='active'
        """, (participant_id, campaign_id)).fetchone()
        if check is None:
            return False
        con.execute("""
          INSERT OR IGNORE INTO events (campaign_id,participant_id,kind,created_at)
          VALUES (?,?,'acknowledged',?)
        """, (campaign_id, participant_id, _now()))
        return True


def activity(path: Path, limit: int = 30) -> list[dict]:
    with database(path) as con:
        rows = con.execute("""
          SELECT e.id,c.name AS campaign,p.alias,e.kind,e.created_at
          FROM events e JOIN campaigns c ON c.id=e.campaign_id
          JOIN participants p ON p.id=e.participant_id
          ORDER BY e.id DESC LIMIT ?
        """, (min(max(int(limit), 1), 100),)).fetchall()
    return [dict(r) for r in rows]


def _excel_safe(value: object) -> object:
    """Prevent spreadsheet formula evaluation in exported untrusted strings."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def export_csv(path: Path) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(("campaign", "participant_alias", "event", "timestamp_utc"))
    for row in activity(path, limit=100):
        writer.writerow([_excel_safe(row[key]) for key in
                         ("campaign", "alias", "kind", "created_at")])
    return buffer.getvalue()
