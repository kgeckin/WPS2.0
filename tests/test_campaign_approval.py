"""Offline policy checks for real, institutionally authorized awareness recipients.

No Selenium session, MySQL connection, message dispatch or external account is used.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from campaign_approval import CampaignApproval, ScopeError, approved_batch, record_audit


NOW = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)
CLIENTS = [
    {"user_id": 11, "phone": "+12025550111", "is_active": 1},
    {"user_id": 12, "phone": "+12025550112", "is_active": 1},
    {"user_id": 13, "phone": "+12025550113", "is_active": 1},
]


@pytest.fixture
def approval_file(tmp_path):
    path = tmp_path / "local-approval.json"
    policy = {
        "campaign_id": 4,
        "approved_by": "Example Security Owner",
        "authorization_reference": "EXAMPLE-CHANGE-123",
        "valid_from": (NOW - timedelta(hours=1)).isoformat(),
        "valid_until": (NOW + timedelta(hours=3)).isoformat(),
        "recipient_user_ids": [11, 12],
        "recipient_phone_numbers": ["+12025550111", "+12025550112"],
        "max_recipients": 2,
    }
    path.write_text(json.dumps(policy), encoding="utf-8")
    return path


def test_selected_approved_recipients_are_preserved_in_order(approval_file):
    policy = CampaignApproval.from_file(approval_file)
    rows = policy.validate(campaign_id=4, selected_user_ids=[12, 11],
                           active_users=CLIENTS, now=NOW)
    assert [x["user_id"] for x in rows] == [12, 11]


@pytest.mark.parametrize("ids", [None, [], [13], [11, 13], [11, 11]])
def test_preflight_rejects_unapproved_or_ambiguous_selection(approval_file, ids):
    policy = CampaignApproval.from_file(approval_file)
    with pytest.raises(ScopeError):
        policy.validate(campaign_id=4, selected_user_ids=ids,
                        active_users=CLIENTS, now=NOW)


def test_approval_rejects_wrong_campaign_window_or_modified_number(approval_file):
    policy = CampaignApproval.from_file(approval_file)
    with pytest.raises(ScopeError):
        policy.validate(campaign_id=5, selected_user_ids=[11],
                        active_users=CLIENTS, now=NOW)
    with pytest.raises(ScopeError):
        policy.validate(campaign_id=4, selected_user_ids=[11],
                        active_users=CLIENTS, now=NOW + timedelta(days=1))
    modified = [dict(CLIENTS[0], phone="+12025550199"), CLIENTS[1]]
    with pytest.raises(ScopeError):
        policy.validate(campaign_id=4, selected_user_ids=[11],
                        active_users=modified, now=NOW)


def test_approval_refuses_duplicate_phone_and_unchecked_ids(approval_file):
    policy = CampaignApproval.from_file(approval_file)
    bad = [CLIENTS[0], dict(CLIENTS[1], phone=CLIENTS[0]["phone"])]
    with pytest.raises(ScopeError):
        policy.validate(campaign_id=4, selected_user_ids=[11, 12],
                        active_users=bad, now=NOW)
    with pytest.raises(ScopeError):
        policy.validate(campaign_id=4, selected_user_ids=[11],
                        active_users=[CLIENTS[1]], now=NOW)


def test_invalid_scope_and_unknown_policy_are_denied(tmp_path, approval_file, monkeypatch):
    monkeypatch.delenv("WPS_CAMPAIGN_APPROVAL_FILE", raising=False)
    with pytest.raises(ScopeError):
        approved_batch(4, [11], CLIENTS)
    with pytest.raises(ScopeError):
        CampaignApproval.from_file(tmp_path / "missing.json")
    data = json.loads(approval_file.read_text())
    data["authorization_reference"] = ""
    approval_file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ScopeError):
        CampaignApproval.from_file(approval_file)


def test_approval_limit_never_silently_truncates(tmp_path, approval_file):
    data = json.loads(approval_file.read_text())
    data["max_recipients"] = 1
    approval_file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ScopeError):
        CampaignApproval.from_file(approval_file)


def test_audit_contains_no_phone_or_personal_contact_data(tmp_path, approval_file):
    policy = CampaignApproval.from_file(approval_file)
    record_audit("preview", 4, policy, 2, directory=tmp_path)
    text = (tmp_path / "campaign-audit.jsonl").read_text(encoding="utf-8")
    assert "EXAMPLE-CHANGE-123" in text
    assert "+1202555" not in text
    assert "Example Security Owner" not in text
    assert '"recipient_count": 2' in text
