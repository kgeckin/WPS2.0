from __future__ import annotations

import pytest
from itsdangerous import URLSafeTimedSerializer

from wps_lab import storage, tokens
from wps_lab.settings import initialize_secret, secret_for


def test_initialize_is_idempotent(tmp_path):
    path = tmp_path / "lab.sqlite3"
    storage.initialize(path)
    storage.initialize(path)
    assert storage.overview(path) == {
        "campaigns": 2, "active": 1, "consented_participants": 9,
        "acknowledgements": 0, "origin": "synthetic local demo",
        "credential_collection": False
    }


def test_only_consenting_active_aliases_are_eligible(tmp_path):
    path = tmp_path / "lab.sqlite3"
    storage.initialize(path)
    assert storage.eligible(path, 1, 1)
    assert not storage.eligible(path, 1, 8)
    assert not storage.eligible(path, 2, 8)
    assert not storage.eligible(path, 999, 1)
    assert storage.acknowledge(path, 1, 1)
    assert storage.acknowledge(path, 1, 1)  # unique, idempotent
    assert storage.overview(path)["acknowledgements"] == 1


def test_token_validates_signature_and_positive_identifiers():
    secret = "strong-secret-" + "T" * 60
    token = tokens.create(secret, 1, 1)
    assert tokens.verify(secret, token) == (1, 1)
    assert tokens.verify(secret, token + "tampered") is None
    assert tokens.verify("different-secret-" + "T" * 60, token) is None
    assert tokens.verify(secret, "bad-token") is None
    with pytest.raises(ValueError):
        tokens.create(secret, 0, 1)
    with pytest.raises(ValueError):
        tokens.create(secret, 1, -2)


def test_secret_generation_is_private_and_reusable(tmp_path, monkeypatch):
    monkeypatch.delenv("WPS_SECRET_KEY", raising=False)
    path = initialize_secret(tmp_path)
    first = secret_for(tmp_path)
    initialize_secret(tmp_path)
    assert first == secret_for(tmp_path)
    assert len(first) >= 40
    assert first not in path.name
    assert path.name == "secret.key"


def test_missing_secret_is_fatal(tmp_path, monkeypatch):
    monkeypatch.delenv("WPS_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="init"):
        secret_for(tmp_path)
