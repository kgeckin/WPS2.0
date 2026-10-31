"""Regression tests for minimal-data database and reporting paths."""

from __future__ import annotations

import db_utils
import report_exporter


class FakeCursor:
    def __init__(self):
        self.query = None
        self.parameters = None

    def execute(self, query, parameters):
        self.query = query
        self.parameters = parameters


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def close(self):
        pass


def test_legacy_log_arguments_are_discarded(monkeypatch):
    conn = FakeConnection()
    monkeypatch.setattr(db_utils, "get_connection", lambda: conn)
    assert db_utils.log_login_attempt(
        1, 2, "person@example.org", "never-store", "browser", "127.0.0.1"
    )
    assert conn.cursor_instance.parameters == (1, 2)
    assert "submitted_pass" not in conn.cursor_instance.query


def test_report_cannot_export_passwords():
    try:
        report_exporter.build_dataframes(include_passwords=True)
    except ValueError as error:
        assert "disabled" in str(error)
    else:
        raise AssertionError("Legacy password export must be rejected")


def test_report_strips_contact_data_and_escapes_formulas(monkeypatch):
    monkeypatch.setattr(report_exporter, "fetch_all_users", lambda: [
        {
            "user_id": 1,
            "company_name": "=1+1",
            "email": "person@example.org",
            "phone": "555",
        }
    ])
    monkeypatch.setattr(report_exporter, "fetch_all_campaigns", lambda: [])
    monkeypatch.setattr(report_exporter, "fetch_campaign_tracking", lambda: [])
    monkeypatch.setattr(report_exporter, "fetch_login_attempts", lambda: [
        {
            "attempt_id": 10,
            "user_id": 1,
            "campaign_id": 2,
            "timestamp": "2026-01-01",
            "submitted_pass": "old-secret",
        }
    ])

    frames = report_exporter.build_dataframes()
    assert "email" not in frames["users"].columns
    assert "phone" not in frames["users"].columns
    assert frames["users"].iloc[0]["company_name"] == "'=1+1"
    assert "submitted_pass" not in frames["attempts"].columns
    assert frames["attempts"].iloc[0]["attempt_id"] == 10
