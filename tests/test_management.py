from __future__ import annotations

import pytest

from wps_lab import storage
from wps_lab.cli import main


def test_manage_synthetic_scenarios_and_consent(tmp_path):
    db = tmp_path / "lab.sqlite3"
    storage.initialize(db)
    campaign = storage.create_campaign(db, "A safe local educational scenario")
    assert campaign > 2
    assert storage.create_alias(db, campaign, "train-010", consent=False) > 0
    assert not storage.eligible(db, campaign, storage.participants(db, campaign)[0]["id"])
    assert storage.change_campaign_state(db, campaign, "active")
    assert storage.set_alias_consent(db, campaign, "TRAIN-010", consent=True)
    person = storage.participants(db, campaign)[0]
    assert storage.eligible(db, campaign, person["id"])
    assert storage.acknowledge(db, campaign, person["id"])
    assert storage.set_alias_consent(db, campaign, "TRAIN-010", consent=False)
    assert not storage.eligible(db, campaign, person["id"])
    assert all(row["alias"] != "TRAIN-010" for row in storage.activity(db))
    assert storage.change_campaign_state(db, campaign, "closed")
    assert not storage.eligible(db, campaign, person["id"])


@pytest.mark.parametrize("alias", [
    "someone@example.com", "+905551234567", "TRAIN-999/../", "a user", ""
])
def test_alias_validation_blocks_personal_contacts(tmp_path, alias):
    db = tmp_path / "lab.sqlite3"
    storage.initialize(db)
    with pytest.raises(ValueError):
        storage.create_alias(db, 1, alias, consent=True)


def test_management_rejects_invalid_updates(tmp_path):
    db = tmp_path / "lab.sqlite3"
    storage.initialize(db)
    with pytest.raises(ValueError):
        storage.create_campaign(db, " ")
    with pytest.raises(ValueError):
        storage.create_campaign(db, "A\nInvalid")
    with pytest.raises(ValueError):
        storage.change_campaign_state(db, 1, "published")
    with pytest.raises(ValueError):
        storage.create_alias(db, 1, "TRAIN-001", consent=False)
    assert not storage.change_campaign_state(db, 999, "closed")
    assert not storage.set_alias_consent(db, 1, "TRAIN-404", consent=False)


def test_management_cli_keeps_data_local(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WPS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("WPS_SECRET_KEY", raising=False)
    assert main(["init"]) == 0
    assert main(["campaign-add", "--name", "A synthetic incident scenario"]) == 0
    assert main(["campaign-state", "--campaign", "3", "--state", "active"]) == 0
    assert main(["alias-add", "--campaign", "3", "--alias", "TRAIN-010"]) == 0
    assert main(["link", "--campaign", "3", "--participant", "10"]) == 1
    assert main(["alias-consent", "--campaign", "3", "--alias", "TRAIN-010", "--grant"]) == 0
    assert main(["link", "--campaign", "3", "--participant", "10"]) == 0
    assert main(["alias-consent", "--campaign", "3", "--alias", "TRAIN-010", "--revoke"]) == 0
    assert main(["link", "--campaign", "3", "--participant", "10"]) == 1
