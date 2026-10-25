"""Redis-backed cache for successful agent responses.

SQLite remains the durable source of truth for users and execution traces. Redis
only holds short-lived response copies, so losing the cache is safe.
"""

import hashlib
import json
import os
import socket
from typing import Any, Protocol
from urllib.parse import unquote, urlsplit


class RedisClient(Protocol):
    def ping(self) -> Any: ...
    def get(self, key: str) -> str | None: ...
    def setex(self, key: str, ttl: int, value: str) -> Any: ...


class RedisConnection:
    """Small Redis RESP client for the commands this service needs."""

    def __init__(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "redis" or not parsed.hostname:
            raise ValueError("REDIS_URL must use the redis://host:port/database format")
        self.host = parsed.hostname
        self.port = parsed.port or 6379
        self.password = unquote(parsed.password) if parsed.password else None
        self.database = int(parsed.path.lstrip("/") or "0")

    @staticmethod
    def _encode(*parts: str | int) -> bytes:
        encoded = [str(part).encode("utf-8") for part in parts]
        return b"*" + str(len(encoded)).encode() + b"\r\n" + b"".join(
            b"$" + str(len(part)).encode() + b"\r\n" + part + b"\r\n" for part in encoded
        )

    @staticmethod
    def _read_response(stream: Any) -> str | int | None:
        marker = stream.read(1)
        if not marker:
            raise ConnectionError("Redis closed the connection unexpectedly")
        line = stream.readline().rstrip(b"\r\n")
        if marker == b"+":
            return line.decode("utf-8")
        if marker == b"-":
            raise ConnectionError(f"Redis error: {line.decode('utf-8')}")
        if marker == b":":
            return int(line)
        if marker == b"$":
            size = int(line)
            if size == -1:
                return None
            value = stream.read(size)
            stream.read(2)
            return value.decode("utf-8")
        raise ConnectionError("Redis sent an unsupported response")

    def _command(self, *parts: str | int) -> str | int | None:
        with socket.create_connection((self.host, self.port), timeout=5) as connection:
            with connection.makefile("rwb") as stream:
                if self.password:
                    stream.write(self._encode("AUTH", self.password))
                    stream.flush()
                    self._read_response(stream)
                if self.database:
                    stream.write(self._encode("SELECT", self.database))
                    stream.flush()
                    self._read_response(stream)
                stream.write(self._encode(*parts))
                stream.flush()
                return self._read_response(stream)

    def ping(self) -> str | int | None:
        return self._command("PING")

    def get(self, key: str) -> str | None:
        result = self._command("GET", key)
        return result if isinstance(result, str) else None

    def setex(self, key: str, ttl: int, value: str) -> str | int | None:
        return self._command("SETEX", key, ttl, value)


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _ttl_seconds() -> int:
    try:
        return max(1, int(os.getenv("CACHE_TTL_SECONDS", "3600")))
    except ValueError:
        return 3600


class AgentResultCache:
    def __init__(self, client: RedisClient | None = None) -> None:
        self.client = client or RedisConnection(_redis_url())

    @staticmethod
    def _key(user_id: int, request: str) -> str:
        digest = hashlib.sha256(request.strip().encode("utf-8")).hexdigest()
        return f"agentforge:agent-result:{user_id}:{digest}"

    def healthcheck(self) -> None:
        self.client.ping()

    def get(self, user_id: int, request: str) -> dict[str, Any] | None:
        cached = self.client.get(self._key(user_id, request))
        return json.loads(cached) if cached else None

    def set(self, user_id: int, request: str, result: dict[str, Any]) -> None:
        self.client.setex(self._key(user_id, request), _ttl_seconds(), json.dumps(result))
