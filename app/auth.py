from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any


PASSWORD_ITERATIONS = 390_000
PASSWORD_MIN_LENGTH = 4
PASSWORD_MAX_LENGTH = 128


def password_is_set(config: dict[str, Any]) -> bool:
    return bool(
        str(config.get("password_salt", "")).strip()
        and str(config.get("password_hash", "")).strip()
    )


def validate_new_password(password: str) -> str | None:
    if len(password) < PASSWORD_MIN_LENGTH:
        return (
            f"La password deve contenere almeno "
            f"{PASSWORD_MIN_LENGTH} caratteri."
        )

    if len(password) > PASSWORD_MAX_LENGTH:
        return (
            f"La password non può superare "
            f"{PASSWORD_MAX_LENGTH} caratteri."
        )

    return None


def create_password_record(password: str) -> dict[str, object]:
    error = validate_new_password(password)
    if error is not None:
        raise ValueError(error)

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )

    return {
        "password_salt": salt.hex(),
        "password_hash": digest.hex(),
        "password_iterations": PASSWORD_ITERATIONS,
    }


def verify_password(password: str, config: dict[str, Any]) -> bool:
    if not password_is_set(config):
        return False

    try:
        salt = bytes.fromhex(str(config.get("password_salt", "")))
        expected = bytes.fromhex(str(config.get("password_hash", "")))
        iterations = int(
            config.get(
                "password_iterations",
                PASSWORD_ITERATIONS,
            )
        )

        if iterations <= 0:
            return False

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
    except (TypeError, ValueError):
        return False

    return hmac.compare_digest(actual, expected)
