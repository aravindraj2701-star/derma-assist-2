"""
Hash Utilities — Secure password hashing and verification using PBKDF2 HMAC SHA-256.
Uses hashlib from the standard library (zero external dependencies).
"""

import hashlib
import os


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2 HMAC SHA-256."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its PBKDF2 hash."""
    if not hashed:
        return False
    try:
        salt_hex, key_hex = hashed.split(":")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return new_key == key
    except Exception:
        return False
