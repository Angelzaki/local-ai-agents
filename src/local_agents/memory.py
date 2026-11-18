from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class SessionMemory:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    meta TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add(self, session_id: str, role: str, content: str, meta: dict | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO turns(session_id, role, content, meta) VALUES (?, ?, ?, ?)",
                (session_id, role, content, json.dumps(meta or {}, ensure_ascii=False)),
            )

    def history(self, session_id: str, limit: int = 12) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, meta
                FROM turns
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        items = [
            {"role": role, "content": content, "meta": json.loads(meta or "{}")}
            for role, content, meta in rows
        ]
        items.reverse()
        return items
