from __future__ import annotations

import re

from wps_lab import storage, tokens


def test_dashboard_and_apis_only_expose_synthetic_data(client):
    page = client.get("/")
    assert page.status_code == 200
    assert b"TRAINING" in page.data or b"Training" in page.data
    assert b"password" not in page.data.lower() or b"no password" in page.data.lower()
    summary = client.get("/api/v1/summary").json
    assert summary["campaigns"] == 2
    assert summary["credential_collection"] is False
    assert len(client.get("/api/v1/campaigns").json) == 2
    assert client.get("/api/v1/events").json == []
    assert client.get("/health").json["mode"] == "local-demo"


def test_training_requires_valid_expiring_signed_link(client, lab):
    app, path = lab
    secret = app.config["SECRET_KEY"]
    link = "/practice/" + tokens.create(secret, 1, 1)
    assert client.get(link).status_code == 200
    assert client.get("/practice/invalid").status_code == 404
    assert client.get("/practice/" + tokens.create(secret, 2, 7)).status_code == 404


def test_explicit_acknowledgement_is_csrf_bound_and_one_use(client, lab):
    app, path = lab
    link = "/practice/" + tokens.create(app.config["SECRET_KEY"], 1, 1)
    assert client.post(link + "/acknowledge", data={"csrf": "guess"}).status_code == 403
    get = client.get(link)
    csrf = re.search(r'name="csrf" value="([^"]+)"', get.get_data(as_text=True)).group(1)
    assert client.post(link + "/acknowledge", data={"csrf": "wrong"}).status_code == 403
    assert storage.overview(path / "lab.sqlite3")["acknowledgements"] == 0
    get = client.get(link)
    csrf = re.search(r'name="csrf" value="([^"]+)"', get.get_data(as_text=True)).group(1)
    done = client.post(link + "/acknowledge", data={"csrf": csrf, "password": "NEVER_STORE_THIS"})
    assert done.status_code == 200
    assert storage.overview(path / "lab.sqlite3")["acknowledgements"] == 1
    assert client.post(link + "/acknowledge", data={"csrf": csrf}).status_code == 403
    stored = (path / "lab.sqlite3").read_bytes()
    assert b"NEVER_STORE_THIS" not in stored


def test_no_credential_collection_even_on_legacy_endpoint(client):
    assert client.get("/login").status_code == 410
    assert client.post("/login", data={"email": "not-logged@example.com", "password": "ignore"}).status_code == 410


def test_refuse_nonlocal_and_untrusted_host_requests(client):
    assert client.get("/api/v1/summary", environ_overrides={"REMOTE_ADDR": "203.0.113.44"}).status_code == 403
    assert client.get("/", headers={"Host": "malicious.example.com"}).status_code == 400


def test_response_headers_and_no_remote_assets(client):
    res = client.get("/")
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Cache-Control"] == "no-store"
    assert "default-src 'self'" in res.headers["Content-Security-Policy"]
    assert b"https://fonts.googleapis.com" not in res.data
    assert b"<script src=\"https://" not in res.data
