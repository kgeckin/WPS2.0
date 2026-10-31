"""Time limited Fernet tokens for authorized training links."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()
_secret_key = os.getenv("SECRET_KEY", "")
if not _secret_key:
    raise RuntimeError("SECRET_KEY is missing. Run generate_key.py during local setup.")

fernet = Fernet(_secret_key.encode("utf-8"))
TOKEN_VALID_SEC = int(os.getenv("TOKEN_VALID_SEC", "300"))
if TOKEN_VALID_SEC < 1:
    raise ValueError("TOKEN_VALID_SEC must be a positive number.")


def generate_encrypted_token(user_id: int, campaign_id: int) -> str:
    """Create an encrypted, time limited training link token."""
    if user_id <= 0 or campaign_id <= 0:
        raise ValueError("Training identifiers must be positive.")
    return fernet.encrypt(f"{user_id}|{campaign_id}".encode()).decode()


def decrypt_token(token: str) -> tuple[int | None, int | None]:
    """Return two identifiers only when the token is authentic and unexpired."""
    try:
        raw = fernet.decrypt(token.encode(), ttl=TOKEN_VALID_SEC).decode()
        parts = raw.split("|")
        if len(parts) != 2:
            return None, None
        user_id, campaign_id = int(parts[0]), int(parts[1])
        if user_id <= 0 or campaign_id <= 0:
            return None, None
        return user_id, campaign_id
    except (InvalidToken, UnicodeError, ValueError, TypeError):
        return None, None
