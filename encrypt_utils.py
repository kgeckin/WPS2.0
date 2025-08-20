"""
encrypt_utils.py
----------------
Provides encryption and decryption utilities for secure URL token handling.
Key must be present in .env as SECRET_KEY. No auto-generation!
"""

from cryptography.fernet import Fernet, InvalidToken
import os
from dotenv import load_dotenv

load_dotenv()
_SECRET_KEY = os.getenv("SECRET_KEY")

if not _SECRET_KEY:
    raise ValueError("SECRET_KEY not found in environment. Please set it in .env (use generate_key.py)!")

fernet = Fernet(_SECRET_KEY.encode())

def generate_encrypted_token(user_id: int, campaign_id: int) -> str:
    """Encrypts user_id and campaign_id as a token."""
    data = f"{user_id}|{campaign_id}".encode()
    token = fernet.encrypt(data)
    return token.decode()

def decrypt_token(token: str):
    """Decrypts the token to extract user_id and campaign_id."""
    try:
        decrypted = fernet.decrypt(token.encode()).decode()
        user_id_str, campaign_id_str = decrypted.split('|')
        return int(user_id_str), int(campaign_id_str)
    except (InvalidToken, ValueError) as e:
        print(f"[DECRYPTION ERROR] {e}")
        return None, None
