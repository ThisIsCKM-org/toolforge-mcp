from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from .registry import ToolForgeRegistry
from .versioning import checksum_file


class ToolRunner:
    def __init__(self, registry: ToolForgeRegistry):
        self.registry = registry

    def run_tool(self, tool_id: int, input_json: dict) -> dict:
        started = time.monotonic()
        version_id = None
        try:
            _tool, version = self.registry.active_version(tool_id)
            version_id = version["id"]
            tool_path = Path(version["file_path"])
            actual_checksum = checksum_file(tool_path)
            if actual_checksum != version["checksum"]:
                raise ValueError("Checksum mismatch; refusing to execute tool.")
            completed = subprocess.run(
                [sys.executable, str(tool_path)],
                input=json.dumps(input_json),
                text=True,
                capture_output=True,
                cwd=self.registry.config.work_dir,
                timeout=self.registry.config.timeout_seconds,
                check=False,
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            if completed.returncode != 0:
                error = completed.stderr.strip() or f"Tool exited with code {completed.returncode}."
                self.registry.log_run(tool_id, version_id, input_json, None, "failed", error, duration_ms)
                return {"status": "failed", "error": error, "duration_ms": duration_ms}
            try:
                output = json.loads(completed.stdout or "{}")
            except json.JSONDecodeError as exc:
                error = f"Tool returned invalid JSON: {exc}"
                self.registry.log_run(tool_id, version_id, input_json, None, "failed", error, duration_ms)
                return {"status": "failed", "error": error, "duration_ms": duration_ms}
            self.registry.log_run(tool_id, version_id, input_json, output, "success", None, duration_ms)
            return {"status": "success", "output_json": output, "duration_ms": duration_ms}
        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - started) * 1000)
            error = "Tool execution timed out."
            self.registry.log_run(tool_id, version_id, input_json, None, "failed", error, duration_ms)
            return {"status": "failed", "error": error, "duration_ms": duration_ms}
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            self.registry.log_run(tool_id, version_id, input_json, None, "failed", str(exc), duration_ms)
            return {"status": "failed", "error": str(exc), "duration_ms": duration_ms}
