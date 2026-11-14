"""Staff passwords and session tokens. No extra packages."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

SESSION_DAYS = 14


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"pbkdf2${salt}${digest}"


def check_password(password, stored):
    try:
        kind, salt, digest = stored.split("$", 2)
    except (AttributeError, ValueError):
        return False
    if kind != "pbkdf2":
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return secrets.compare_digest(check, digest)


def new_token():
    return secrets.token_urlsafe(32)


def expiry():
    return datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
