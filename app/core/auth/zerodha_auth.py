"""Zerodha OAuth helper — handles login URL generation, session creation, token storage."""

import json
import os
from datetime import datetime, time as dtime
from typing import Any

from app.config import settings

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
        return {"access_token": access_token, "user": data.get("user_name", "")}
    except ImportError:
        return None
    except Exception as e:
        print(f"[ZerodhaAuth] Session generation failed: {e}")
        return None


def load_token() -> str | None:
    """Load stored access token if valid (today's token)."""
    if not os.path.exists(_TOKEN_FILE):
        return None
    try:
        with open(_TOKEN_FILE, "r") as f:
            data = json.load(f)
        stored_date = data.get("date", "")
        token = data.get("access_token", "")
        # Tokens expire at 6 AM IST next day
        if stored_date == datetime.now().strftime("%Y-%m-%d") and token:
            return token
        return None
    except Exception:
        return None


def is_token_valid() -> bool:
    """Check if we have a valid (today's) token."""
    return load_token() is not None


def _store_token(access_token: str) -> None:
    """Store token with today's date."""
    data = {
        "access_token": access_token,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "stored_at": datetime.now().isoformat(),
    }
    with open(_TOKEN_FILE, "w") as f:
        json.dump(data, f)
