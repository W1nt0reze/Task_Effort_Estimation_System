from __future__ import annotations

import sqlite3

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "app.db"

META_LAST_RETRAINED_THROUGH_ID = "last_retrained_through_task_id"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                priority TEXT NOT NULL,
                type TEXT NOT NULL,
                team TEXT NOT NULL DEFAULT 'other',
                story_points REAL NOT NULL DEFAULT 0,
                actual_hours REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        if not _column_exists(conn, "tasks", "team"):
            conn.execute("ALTER TABLE tasks ADD COLUMN team TEXT NOT NULL DEFAULT 'other'")

        if _column_exists(conn, "tasks", "tags"):
            conn.execute(
                """
                UPDATE tasks
                SET team = COALESCE(NULLIF(team, ''), tags, 'other')
                """
            )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        row = conn.execute(
            "SELECT value FROM app_meta WHERE key = ?",
            (META_LAST_RETRAINED_THROUGH_ID,),
        ).fetchone()

        if row is None:
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM tasks").fetchone()[0]
            conn.execute(
                "INSERT INTO app_meta (key, value) VALUES (?, ?)",
                (META_LAST_RETRAINED_THROUGH_ID, str(int(max_id))),
            )

        conn.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


@dataclass
class TaskRow:
    id: int
    title: str
    priority: str
    type: str
    team: str
    story_points: float
    actual_hours: float
    created_at: str


def get_last_retrained_through_task_id() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM app_meta WHERE key = ?",
            (META_LAST_RETRAINED_THROUGH_ID,),
        ).fetchone()
        return int(row["value"]) if row else 0


def set_last_retrained_through_task_id(task_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_meta (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (META_LAST_RETRAINED_THROUGH_ID, str(int(task_id))),
        )
        conn.commit()


def count_tasks_after_id(after_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM tasks WHERE id > ?",
            (int(after_id),),
        ).fetchone()
        return int(row["c"])


def max_task_id() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COALESCE(MAX(id), 0) AS m FROM tasks").fetchone()
        return int(row["m"])


def insert_task(
    title: str,
    priority: str,
    type: str,
    team: str,
    story_points: float,
    actual_hours: float,
    created_at: datetime,
) -> int:
    created_iso = created_at.isoformat(timespec="seconds")

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO tasks (
                title,
                priority,
                type,
                team,
                story_points,
                actual_hours,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, priority, type, team, story_points, actual_hours, created_iso),
        )
        conn.commit()
        return int(cur.lastrowid)


def fetch_all_tasks() -> list[TaskRow]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                title,
                priority,
                type,
                team,
                story_points,
                actual_hours,
                created_at
            FROM tasks
            ORDER BY id
            """
        ).fetchall()

        return [
            TaskRow(
                id=int(r["id"]),
                title=r["title"],
                priority=r["priority"],
                type=r["type"],
                team=r["team"] or "other",
                story_points=float(r["story_points"]),
                actual_hours=float(r["actual_hours"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]
