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
