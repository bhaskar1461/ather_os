"""
Password hashing and verification using the bcrypt library directly.
Avoids passlib compatibility issues with modern bcrypt releases.
"""

import bcrypt


def hash_password(password: str) -> str:
    """
    Generate a bcrypt hash of the given password.

    Args:
        password: Plain-text password.

    Returns:
        Hashed password string.
    """
    # bcrypt expects bytes for hashing
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.

    Args:
        plain_password: The password to check.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False
