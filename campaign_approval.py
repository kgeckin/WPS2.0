"""Explicit operator scope gate for authorized awareness campaign delivery.

No network calls, browser control, account secrets, or participant exports.
The private approval file is intentionally never committed.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping


class ScopeError(ValueError):
    """The campaign is outside the approved recipient/time scope."""


def canonical_phone(value: str, *, country_code: str = "90") -> str:
    """Convert common local recipient formats into an E.164-like canonical number."""
    source = re.sub(r"[\s()\-]", "", str(value or "").strip())
    if source.startswith("00"):
        source = "+" + source[2:]
    if source.startswith("+"):
        number = source
    elif re.fullmatch(r"\d{10}", source):
        number = "+" + country_code + source
    elif source.isdecimal():
        number = "+" + source
    else:
        number = ""
    if not re.fullmatch(r"\+[1-9]\d{7,14}", number):
        raise ScopeError("An approved recipient has an invalid phone number.")
    return number


def _date(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ScopeError(f"{field} must be a timestamp with timezone.")
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScopeError(f"{field} is not a valid timestamp.") from exc
    if date.tzinfo is None or date.utcoffset() is None:
        raise ScopeError(f"{field} needs a timezone.")
    return date.astimezone(timezone.utc)


@dataclass(frozen=True)
class CampaignApproval:
    campaign_id: int
    approved_by: str
    authorization_reference: str
    valid_from: datetime
    valid_until: datetime
    recipient_ids: frozenset[int]
    recipient_numbers: frozenset[str]
    max_recipients: int

    @classmethod
    def from_file(cls, file_path: str | os.PathLike[str]) -> "CampaignApproval":
        path = Path(file_path).expanduser()
        if not path.is_file():
            raise ScopeError("A private campaign approval file is required before delivery.")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ScopeError("Campaign approval file cannot be read.") from exc
        if not isinstance(payload, dict):
            raise ScopeError("Campaign approval must be a JSON object.")
        campaign_id = payload.get("campaign_id")
        maximum = payload.get("max_recipients")
        if type(campaign_id) is not int or campaign_id <= 0:
            raise ScopeError("An approved campaign ID is required.")
        if type(maximum) is not int or not 1 <= maximum <= 1000:
            raise ScopeError("max_recipients must be from 1 to 1000.")
        approved_by = payload.get("approved_by")
        reference = payload.get("authorization_reference")
        if not isinstance(approved_by, str) or not approved_by.strip():
            raise ScopeError("An approver is required.")
        if not isinstance(reference, str) or not reference.strip():
            raise ScopeError("An authorization reference is required.")
        from_time = _date(payload.get("valid_from"), "valid_from")
        until_time = _date(payload.get("valid_until"), "valid_until")
        if until_time <= from_time:
            raise ScopeError("The approval window must be chronological.")
        ids = payload.get("recipient_user_ids")
        phones = payload.get("recipient_phone_numbers")
        if (not isinstance(ids, list) or not ids
                or not all(type(x) is int and x > 0 for x in ids)
                or len(set(ids)) != len(ids)):
            raise ScopeError("List distinct approved recipient IDs.")
        if (not isinstance(phones, list) or not phones
                or not all(isinstance(x, str) for x in phones)):
            raise ScopeError("List approved phone numbers locally.")
        normalized = [canonical_phone(x) for x in phones]
        if len(set(normalized)) != len(normalized):
            raise ScopeError("Approved phone numbers must be distinct.")
        if len(ids) > maximum or len(phones) > maximum:
            raise ScopeError("Approved scope exceeds max_recipients.")
        return cls(campaign_id, approved_by.strip(), reference.strip(),
                   from_time, until_time, frozenset(ids), frozenset(normalized),
                   maximum)

    def validate(self, *, campaign_id: int,
                 selected_user_ids: Iterable[int] | None,
                 active_users: list[Mapping[str, object]],
                 country_code: str = "90",
                 now: datetime | None = None) -> list[Mapping[str, object]]:
        """Reject the entire batch if any identity, number, or approval is out of scope.

        Never silently expand the selected recipients to all active users.
        """
        timestamp = now or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ScopeError("Current time requires a timezone.")
        timestamp = timestamp.astimezone(timezone.utc)
        if not self.valid_from <= timestamp <= self.valid_until:
            raise ScopeError("Campaign is outside its authorized delivery window.")
        if type(campaign_id) is not int or campaign_id != self.campaign_id:
            raise ScopeError("This approval was issued for another campaign.")
        if selected_user_ids is None:
            raise ScopeError("An explicit filtered recipient selection is required.")
        selected = list(selected_user_ids)
        if (not selected or not all(type(x) is int and x > 0 for x in selected)
                or len(set(selected)) != len(selected)):
            raise ScopeError("Select one or more distinct recipient IDs.")
        if len(selected) > self.max_recipients:
            raise ScopeError("Selected recipient count exceeds approval.")
        if not set(selected).issubset(self.recipient_ids):
            raise ScopeError("Selected recipients exceed approved campaign scope.")
        users_by_id: dict[int, Mapping[str, object]] = {}
        for user in active_users:
            try:
                user_id = int(str(user["user_id"]))
            except (TypeError, ValueError, KeyError) as exc:
                raise ScopeError("Invalid user record in campaign data.") from exc
            if user_id in users_by_id:
                raise ScopeError("Duplicate recipient ID in the active list.")
            users_by_id[user_id] = user
        if not set(selected).issubset(users_by_id):
            raise ScopeError("One or more selected recipients are not active.")
        results: list[Mapping[str, object]] = []
        seen_phones: set[str] = set()
        for user_id in selected:
            user = users_by_id[user_id]
            phone = canonical_phone(str(user.get("phone") or ""),
                                    country_code=country_code)
            if phone not in self.recipient_numbers:
                raise ScopeError("A recipient number is not in the approved scope.")
            if phone in seen_phones:
                raise ScopeError("Duplicate phone number in the selected batch.")
            seen_phones.add(phone)
            results.append(user)
        return results


def approved_batch(campaign_id: int, selected_user_ids: Iterable[int] | None,
                   active_users: list[Mapping[str, object]],
                   country_code: str = "90",
                   file_path: str | None = None) -> tuple[CampaignApproval, list[Mapping[str, object]]]:
    """The one preflight used by GUI previews and actual deliveries."""
    source = file_path or os.environ.get("WPS_CAMPAIGN_APPROVAL_FILE")
    if not source:
        raise ScopeError("Set WPS_CAMPAIGN_APPROVAL_FILE to an authorized local approval JSON.")
    approval = CampaignApproval.from_file(source)
    recipients = approval.validate(campaign_id=campaign_id,
                                   selected_user_ids=selected_user_ids,
                                   active_users=active_users,
                                   country_code=country_code)
    return approval, recipients


def record_audit(event: str, campaign_id: int, approval: CampaignApproval,
                 recipient_count: int, detail: str = "",
                 *, directory: str | os.PathLike[str] | None = None) -> None:
    """Local-only audit with no recipient numbers, names or message bodies."""
    if event not in {"preview", "start", "complete", "denied", "failure"}:
        raise ValueError("Unknown audit event.")
    target = Path(directory or os.environ.get("WPS_AUDIT_DIR") or ".local").expanduser()
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = target / "campaign-audit.jsonl"
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "campaign_id": campaign_id,
        "approval_reference": approval.authorization_reference,
        "recipient_count": recipient_count,
        "detail": detail[:180],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
