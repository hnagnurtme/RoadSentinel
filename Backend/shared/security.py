"""
shared/security.py
---------------------
Helper functions for password hashing and verification.
"""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    pw_bytes = password.encode("utf-8")
    hash_bytes = password_hash.encode("utf-8")
    return bcrypt.checkpw(pw_bytes, hash_bytes)
