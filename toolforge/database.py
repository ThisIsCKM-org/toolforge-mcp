from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


SCHEMA: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS tools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL,
        language TEXT NOT NULL,
        tags TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'draft',
        risk_level TEXT NOT NULL DEFAULT 'medium',
        active_version_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(active_version_id) REFERENCES tool_versions(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_id INTEGER NOT NULL,
        version TEXT NOT NULL,
        file_path TEXT NOT NULL,
        checksum TEXT NOT NULL,
        approved INTEGER NOT NULL DEFAULT 0,
        changelog TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tool_id, version),
        FOREIGN KEY(tool_id) REFERENCES tools(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_id INTEGER NOT NULL,
        version_id INTEGER,
        input_json TEXT,
        output_json TEXT,
        status TEXT NOT NULL,
        error TEXT,
        duration_ms INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tool_id) REFERENCES tools(id),
        FOREIGN KEY(version_id) REFERENCES tool_versions(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS approvals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_id INTEGER NOT NULL,
        version_id INTEGER NOT NULL,
        approved_by TEXT NOT NULL,
        approval_notes TEXT,
        approved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tool_id) REFERENCES tools(id),
        FOREIGN KEY(version_id) REFERENCES tool_versions(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_embeddings (
        tool_id INTEGER PRIMARY KEY,
        embedding BLOB,
        embedding_text TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tool_id) REFERENCES tools(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bootstrap_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
)


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize(db_path: Path) -> None:
    with connect(db_path) as conn:
        for statement in SCHEMA:
            conn.execute(statement)


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]
