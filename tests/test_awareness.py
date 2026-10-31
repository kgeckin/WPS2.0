"""Isolated HTTP tests: no browser, database, or outbound messages."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet

# The import-time app requires a local Fernet key; no key is committed.
os.environ.setdefault("SECRET_KEY", Fernet.generate_key().decode())

from phishing_server.app import create_app


def test_health():
    app = create_app(lambda token: (1, 2), lambda *a, **kw: True)
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.text == "ok"


def test_invalid_link_is_rejected():
    app = create_app(lambda token: (None, None), lambda *a, **kw: True)
    response = app.test_client().get("/redirect?data=bad-token")
    assert response.status_code == 400


def test_training_link_records_event_only():
    events = []

    def record(*args, **kwargs):
        events.append((args, kwargs))
        return True

    app = create_app(lambda token: (5, 9), record)
    response = app.test_client().get("/r/test-token")
    assert response.status_code == 200
    assert b"No login, password" in response.data
    assert events == [((5, 9), {"clicked": True, "opened": True, "compromised": False})]
    assert response.headers["Cache-Control"] == "no-store"


def test_failed_tracking_is_not_reported_as_success():
    app = create_app(lambda token: (5, 9), lambda *a, **kw: False)
    assert app.test_client().get("/r/example").status_code == 503


def test_legacy_credential_post_is_retired():
    app = create_app(lambda token: (5, 9), lambda *a, **kw: True)
    response = app.test_client().post(
        "/login", data={"email": "test@example.org", "password": "not_collected"}
    )
    assert response.status_code == 410
