from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolForgeConfig:
    db_path: Path
    tools_dir: Path
    work_dir: Path
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "ToolForgeConfig":
        return cls(
            db_path=Path(os.getenv("TOOLFORGE_DB_PATH", "data/toolforge.db")),
            tools_dir=Path(os.getenv("TOOLFORGE_TOOLS_DIR", "tools")),
            work_dir=Path(os.getenv("TOOLFORGE_WORK_DIR", "work")),
            timeout_seconds=int(os.getenv("TOOLFORGE_TIMEOUT_SECONDS", "30")),
        )

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        for status in ("draft", "approved", "deprecated", "blocked"):
            (self.tools_dir / status).mkdir(parents=True, exist_ok=True)
