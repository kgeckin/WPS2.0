"""Authenticated short-lived, non-PII training links."""
from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TTL_SECONDS = 900
SALT = "wps-awareness-lab-training-v3"


def create(secret: str, campaign_id: int, participant_id: int) -> str:
    if campaign_id <= 0 or participant_id <= 0:
        raise ValueError("Identifiers must be positive")
    return URLSafeTimedSerializer(secret, salt=SALT).dumps(
        {"campaign": int(campaign_id), "participant": int(participant_id)})


def verify(secret: str, token: str) -> tuple[int, int] | None:
    if len(token) > 4096:
        return None
    try:
        value = URLSafeTimedSerializer(secret, salt=SALT).loads(
            token, max_age=TTL_SECONDS)
        if not isinstance(value, dict):
            return None
        campaign_id = value.get("campaign")
        participant_id = value.get("participant")
        if type(campaign_id) is not int or type(participant_id) is not int:
            return None
        if campaign_id <= 0 or participant_id <= 0:
            return None
        return campaign_id, participant_id
    except (BadSignature, SignatureExpired, ValueError, TypeError, OverflowError):
        return None
