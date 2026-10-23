"""Persistent, append-only run tracing for agent execution."""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from app.core.auth import DATABASE_PATH


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialise_trace_store() -> None:
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                request TEXT NOT NULL,
                status TEXT NOT NULL,
                document_path TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                event_type TEXT NOT NULL,
                model TEXT,
                attempt INTEGER,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                tools TEXT NOT NULL DEFAULT '[]',
                details TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES agent_runs(run_id)
            );
            """
        )


class RunTracer:
    def start(self, run_id: str, user_id: int, request: str) -> None:
        with _connection() as connection:
            connection.execute(
                "INSERT INTO agent_runs (run_id, user_id, request, status, created_at) VALUES (?, ?, ?, 'running', ?)",
                (run_id, user_id, request, datetime.now(UTC).isoformat()),
            )

    def event(self, run_id: str, agent: str, event_type: str, *, model: str | None = None,
              attempt: int | None = None, prompt_tokens: int | None = None,
              completion_tokens: int | None = None, tools: list[str] | None = None,
              details: dict[str, Any] | None = None) -> None:
        with _connection() as connection:
            connection.execute(
                """INSERT INTO run_events
                (run_id, agent, event_type, model, attempt, prompt_tokens, completion_tokens, tools, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, agent, event_type, model, attempt, prompt_tokens, completion_tokens,
                 json.dumps(tools or []), json.dumps(details or {}), datetime.now(UTC).isoformat()),
            )

    def finish(self, run_id: str, document_path: str) -> None:
        with _connection() as connection:
            connection.execute(
                "UPDATE agent_runs SET status='succeeded', document_path=?, completed_at=? WHERE run_id=?",
                (document_path, datetime.now(UTC).isoformat(), run_id),
            )

    def fail(self, run_id: str, error: str) -> None:
        with _connection() as connection:
            connection.execute(
                "UPDATE agent_runs SET status='failed', error=?, completed_at=? WHERE run_id=?",
                (error[:1000], datetime.now(UTC).isoformat(), run_id),
            )

    def get(self, run_id: str, user_id: int) -> dict | None:
        with _connection() as connection:
            run = connection.execute("SELECT * FROM agent_runs WHERE run_id=? AND user_id=?", (run_id, user_id)).fetchone()
            if run is None:
                return None
            events = connection.execute("SELECT * FROM run_events WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        result = dict(run)
        result["events"] = [
            {**dict(event), "tools": json.loads(event["tools"]), "details": json.loads(event["details"])}
            for event in events
        ]
        return result
