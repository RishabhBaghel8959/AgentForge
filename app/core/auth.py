"""Local SQLite user storage and minimal HS256 JWT helpers."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, status
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")
DATABASE_PATH = PROJECT_DIR / "agentforge.db"
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-development-secret-before-deploying")
JWT_ALGORITHM = "HS256"
TOKEN_LIFETIME_HOURS = 24


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialise_database() -> None:
    with _connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return f"pbkdf2_sha256$600000${_encode(salt)}${_encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, rounds, salt, digest = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _decode(salt), int(rounds)
        )
        return hmac.compare_digest(candidate, _decode(digest))
    except (ValueError, TypeError):
        return False


def create_user(email: str, password: str) -> dict:
    try:
        with _connection() as connection:
            cursor = connection.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email.lower(), hash_password(password), datetime.now(UTC).isoformat()),
            )
            return {"id": cursor.lastrowid, "email": email.lower()}
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from error


def find_user(email: str) -> sqlite3.Row | None:
    with _connection() as connection:
        return connection.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?", (email.lower(),)
        ).fetchone()


def create_access_token(user: dict) -> str:
    header = _encode(json.dumps({"alg": JWT_ALGORITHM, "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _encode(
        json.dumps(
            {
                "sub": str(user["id"]),
                "email": user["email"],
                "exp": int((datetime.now(UTC) + timedelta(hours=TOKEN_LIFETIME_HOURS)).timestamp()),
            },
            separators=(",", ":"),
        ).encode()
    )
    signature = _encode(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        expected = _encode(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        claims = json.loads(_decode(payload))
        if int(claims["exp"]) < int(datetime.now(UTC).timestamp()):
            raise ValueError("Expired token")
        return claims
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
