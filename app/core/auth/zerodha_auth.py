"""Zerodha OAuth helper — handles login URL, session creation, encrypted token storage."""

import json
import os
import ssl
import certifi
from datetime import datetime
from typing import Any

from app.config import settings

# Fix SSL certificate verification for kiteconnect
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

_TOKEN_FILE = ".tokens"


def generate_login_url() -> str:
    """Return the Zerodha OAuth URL for user to visit."""
    api_key = settings.zerodha_api_key
    return f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"


def generate_session(request_token: str) -> dict[str, Any] | None:
    """Exchange request_token for access_token using Kite Connect."""
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=settings.zerodha_api_key)
        data = kite.generate_session(request_token, api_secret=settings.zerodha_api_secret)
        access_token = data["access_token"]
        _store_token(access_token)
        return {
            "access_token": access_token,
            "user": data.get("user_name", ""),
            "user_id": data.get("user_id", ""),
        }
    except Exception as e:
        print(f"[ZerodhaAuth] Session generation failed: {e}")
        return None


def load_token() -> str | None:
    """Load and decrypt stored access token if valid (today's token)."""
    if not os.path.exists(_TOKEN_FILE):
        return None
    try:
        with open(_TOKEN_FILE, "r") as f:
            data = json.load(f)

        stored_date = data.get("date", "")
        encrypted_token = data.get("encrypted_token", "")
        plain_token = data.get("access_token", "")  # Fallback for unencrypted

        # Tokens expire at 6 AM IST next day — check if stored today
        if stored_date != datetime.now().strftime("%Y-%m-%d"):
            return None

        # Try decryption
        if encrypted_token and settings.token_encryption_key:
            try:
                from cryptography.fernet import Fernet
                f = Fernet(settings.token_encryption_key.encode())
                return f.decrypt(encrypted_token.encode()).decode()
            except Exception:
                pass

        # Fallback to plain token
        return plain_token if plain_token else None
    except Exception:
        return None


def is_token_valid() -> bool:
    """Check if we have a valid (today's) token."""
    return load_token() is not None


def _store_token(access_token: str) -> None:
    """Encrypt and store token with today's date."""
    data: dict[str, Any] = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "stored_at": datetime.now().isoformat(),
    }

    # Encrypt if key available
    if settings.token_encryption_key:
        try:
            from cryptography.fernet import Fernet
            f = Fernet(settings.token_encryption_key.encode())
            data["encrypted_token"] = f.encrypt(access_token.encode()).decode()
        except Exception:
            data["access_token"] = access_token
    else:
        data["access_token"] = access_token

    with open(_TOKEN_FILE, "w") as f:
        json.dump(data, f)
