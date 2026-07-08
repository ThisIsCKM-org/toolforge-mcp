from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .config import ToolForgeConfig
from .database import connect, initialize, rows_to_dicts
from .search import embedding_text, encode_embedding, rank_tools, serialize_embedding
from .security import scan_code
from .versioning import (
    checksum_file,
    checksum_text,
    tool_file_path,
    validate_tool_name,
    validate_version,
)


class ToolForgeRegistry:
    def __init__(self, config: ToolForgeConfig):
        self.config = config
        self.config.ensure_dirs()
        initialize(self.config.db_path)

    def register_tool(
        self,
        name: str,
        description: str,
        language: str,
        code: str,
        tags: list[str],
        version: str = "1.0.0",
        status: str = "draft",
        approved: bool = False,
        changelog: str | None = None,
    ) -> dict:
        if language != "python":
            raise ValueError("ToolForge MVP supports Python tools only.")
        validate_tool_name(name)
        validate_version(version)
        scan = scan_code(code)
        file_path = tool_file_path(self.config.tools_dir, status, name, version)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(code, encoding="utf-8")
        checksum = checksum_text(code)

        with connect(self.config.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO tools (name, description, language, tags, status, risk_level)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, description, language, json.dumps(tags), status, scan["risk_level"]),
            )
            tool_id = int(cursor.lastrowid)
            version_cursor = conn.execute(
                """
                INSERT INTO tool_versions (tool_id, version, file_path, checksum, approved, changelog)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tool_id, version, str(file_path), checksum, int(approved), changelog),
            )
            version_id = int(version_cursor.lastrowid)
            if approved:
                conn.execute(
                    "UPDATE tools SET active_version_id = ?, status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (version_id, tool_id),
                )
                self._upsert_embedding(conn, tool_id)
        return {
            "tool_id": tool_id,
            "version_id": version_id,
            "status": "approved" if approved else status,
            "risk_level": scan["risk_level"],
            "security_findings": scan["findings"],
            "message": "Tool registered successfully",
        }

    def list_tools(
        self,
        status: str | None = None,
        tag: str | None = None,
        language: str | None = None,
        name: str | None = None,
    ) -> list[dict]:
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if language:
            clauses.append("language = ?")
            params.append(language)
        if name:
            clauses.append("LOWER(name) LIKE ?")
            params.append(f"%{name.lower()}%")
        sql = "SELECT * FROM tools"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY name"
        with connect(self.config.db_path) as conn:
            tools = rows_to_dicts(conn.execute(sql, params).fetchall())
        decoded = [self._decode_tool(tool) for tool in tools]
        if tag:
            decoded = [tool for tool in decoded if tag in tool["tags"]]
        return decoded

    def get_tool(self, tool_id: int) -> dict:
        with connect(self.config.db_path) as conn:
            tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
            if tool is None:
                raise ValueError(f"Tool {tool_id} not found.")
            versions = rows_to_dicts(
                conn.execute(
                    "SELECT * FROM tool_versions WHERE tool_id = ? ORDER BY created_at, id",
                    (tool_id,),
                ).fetchall()
            )
            approvals = rows_to_dicts(
                conn.execute(
                    "SELECT * FROM approvals WHERE tool_id = ? ORDER BY approved_at, id",
                    (tool_id,),
                ).fetchall()
            )
            runs = rows_to_dicts(
                conn.execute(
                    "SELECT id, status, error, duration_ms, created_at FROM tool_runs WHERE tool_id = ? ORDER BY id DESC LIMIT 10",
                    (tool_id,),
                ).fetchall()
            )
        result = self._decode_tool(dict(tool))
        result["versions"] = versions
        result["approvals"] = approvals
        result["recent_runs"] = runs
        return result

    def approve_tool(self, tool_id: int, version: str, approved_by: str, notes: str = "") -> dict:
        validate_version(version)
        with connect(self.config.db_path) as conn:
            tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
            version_row = conn.execute(
                "SELECT * FROM tool_versions WHERE tool_id = ? AND version = ?",
                (tool_id, version),
            ).fetchone()
            if tool is None or version_row is None:
                raise ValueError("Tool or version not found.")
            source = Path(version_row["file_path"])
            target = tool_file_path(self.config.tools_dir, "approved", tool["name"], version)
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            checksum = checksum_file(target)
            conn.execute(
                "UPDATE tool_versions SET file_path = ?, checksum = ?, approved = 1 WHERE id = ?",
                (str(target), checksum, version_row["id"]),
            )
            conn.execute(
                "UPDATE tools SET status = 'approved', active_version_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (version_row["id"], tool_id),
            )
            conn.execute(
                "INSERT INTO approvals (tool_id, version_id, approved_by, approval_notes) VALUES (?, ?, ?, ?)",
                (tool_id, version_row["id"], approved_by, notes),
            )
            self._upsert_embedding(conn, tool_id)
        return {"tool_id": tool_id, "version": version, "status": "approved"}

    def update_tool(self, tool_id: int, new_code: str, version: str, changelog: str) -> dict:
        validate_version(version)
        scan = scan_code(new_code)
        with connect(self.config.db_path) as conn:
            tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
            if tool is None:
                raise ValueError(f"Tool {tool_id} not found.")
            file_path = tool_file_path(self.config.tools_dir, "draft", tool["name"], version)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(new_code, encoding="utf-8")
            cursor = conn.execute(
                """
                INSERT INTO tool_versions (tool_id, version, file_path, checksum, approved, changelog)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (tool_id, version, str(file_path), checksum_text(new_code), changelog),
            )
            conn.execute(
                "UPDATE tools SET status = CASE WHEN status = 'approved' THEN status ELSE 'draft' END, risk_level = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (scan["risk_level"], tool_id),
            )
        return {
            "tool_id": tool_id,
            "version_id": int(cursor.lastrowid),
            "version": version,
            "status": "draft",
            "risk_level": scan["risk_level"],
            "security_findings": scan["findings"],
        }

    def deprecate_tool(self, tool_id: int, reason: str) -> dict:
        with connect(self.config.db_path) as conn:
            tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
            if tool is None:
                raise ValueError(f"Tool {tool_id} not found.")
            conn.execute(
                "UPDATE tools SET status = 'deprecated', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (tool_id,),
            )
            conn.execute(
                """
                INSERT INTO tool_runs (tool_id, version_id, input_json, output_json, status, error, duration_ms)
                VALUES (?, ?, ?, ?, 'deprecated', ?, 0)
                """,
                (tool_id, tool["active_version_id"], "{}", "{}", reason),
            )
        return {"tool_id": tool_id, "status": "deprecated", "reason": reason}

    def rollback_tool(self, tool_id: int, target_version: str) -> dict:
        validate_version(target_version)
        with connect(self.config.db_path) as conn:
            version = conn.execute(
                """
                SELECT * FROM tool_versions
                WHERE tool_id = ? AND version = ? AND approved = 1
                """,
                (tool_id, target_version),
            ).fetchone()
            if version is None:
                raise ValueError("Target version is not an approved version.")
            conn.execute(
                "UPDATE tools SET active_version_id = ?, status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (version["id"], tool_id),
            )
        return {"tool_id": tool_id, "active_version": target_version, "status": "approved"}

    def search_tools(self, query: str, limit: int = 5, include_deprecated: bool = False) -> list[dict]:
        with connect(self.config.db_path) as conn:
            clauses = ["tools.status = 'approved'"]
            if include_deprecated:
                clauses = ["tools.status IN ('approved', 'deprecated')"]
            rows = rows_to_dicts(
                conn.execute(
                    f"""
                    SELECT tools.*, tool_embeddings.embedding, tool_embeddings.embedding_text
                    FROM tools
                    LEFT JOIN tool_embeddings ON tools.id = tool_embeddings.tool_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY tools.name
                    """
                ).fetchall()
            )
        decoded = [self._decode_tool(row) for row in rows]
        return [
            {
                "tool_id": tool["id"],
                "name": tool["name"],
                "description": tool["description"],
                "status": tool["status"],
                "version": self._active_version_label(tool["active_version_id"]),
                "tags": tool["tags"],
                "score": tool["score"],
            }
            for tool in rank_tools(query, decoded, limit)
        ]

    def active_version(self, tool_id: int) -> tuple[dict, dict]:
        with connect(self.config.db_path) as conn:
            tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
            if tool is None:
                raise ValueError(f"Tool {tool_id} not found.")
            if tool["status"] != "approved":
                raise ValueError("Only approved tools can run.")
            if tool["active_version_id"] is None:
                raise ValueError("Approved tool has no active version.")
            version = conn.execute(
                "SELECT * FROM tool_versions WHERE id = ?",
                (tool["active_version_id"],),
            ).fetchone()
            if version is None or not version["approved"]:
                raise ValueError("Active version is not approved.")
        return dict(tool), dict(version)

    def log_run(
        self,
        tool_id: int,
        version_id: int | None,
        input_json: dict,
        output_json: dict | None,
        status: str,
        error: str | None,
        duration_ms: int,
    ) -> None:
        with connect(self.config.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tool_runs
                (tool_id, version_id, input_json, output_json, status, error, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tool_id,
                    version_id,
                    json.dumps(input_json),
                    json.dumps(output_json or {}),
                    status,
                    error,
                    duration_ms,
                ),
            )

    def _upsert_embedding(self, conn, tool_id: int) -> None:
        tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
        if tool is None:
            return
        text = embedding_text(self._decode_tool(dict(tool)))
        embedding = serialize_embedding(encode_embedding(text))
        conn.execute(
            """
            INSERT INTO tool_embeddings (tool_id, embedding, embedding_text)
            VALUES (?, ?, ?)
            ON CONFLICT(tool_id) DO UPDATE SET
                embedding = excluded.embedding,
                embedding_text = excluded.embedding_text,
                created_at = CURRENT_TIMESTAMP
            """,
            (tool_id, embedding, text),
        )

    def _active_version_label(self, version_id: int | None) -> str | None:
        if version_id is None:
            return None
        with connect(self.config.db_path) as conn:
            row = conn.execute("SELECT version FROM tool_versions WHERE id = ?", (version_id,)).fetchone()
        return None if row is None else row["version"]

    @staticmethod
    def _decode_tool(tool: dict) -> dict:
        decoded = dict(tool)
        try:
            decoded["tags"] = json.loads(decoded.get("tags") or "[]")
        except json.JSONDecodeError:
            decoded["tags"] = []
        return decoded
