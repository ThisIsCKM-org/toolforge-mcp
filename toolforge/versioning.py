from __future__ import annotations

import hashlib
import re
from pathlib import Path


VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,80}$")


def validate_tool_name(name: str) -> None:
    if not TOOL_NAME_RE.match(name):
        raise ValueError("Tool name must be lowercase snake_case and start with a letter.")


def validate_version(version: str) -> None:
    if not VERSION_RE.match(version):
        raise ValueError("Version must use semantic format X.Y.Z.")


def version_dir_name(version: str) -> str:
    validate_version(version)
    return "v" + version.replace(".", "_")


def checksum_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def checksum_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tool_file_path(tools_dir: Path, status: str, name: str, version: str) -> Path:
    return tools_dir / status / name / version_dir_name(version) / "tool.py"
