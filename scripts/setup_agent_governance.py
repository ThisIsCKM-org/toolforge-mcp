#!/usr/bin/env python3
"""Install ToolForge MCP governance and MCP config for agent clients.

The setup is project-scoped by default. It writes or updates:
- Codex: .codex/AGENTS.md and .codex/config.toml
- Claude Code: CLAUDE.md and .mcp.json
- Cursor: .cursor/rules/toolforge.mdc and .cursor/mcp.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

AGENTS = {"codex", "claude", "cursor"}


@dataclass(frozen=True)
class SetupConfig:
    repo_root: Path
    target_project: Path
    toolforge_dir: Path
    dry_run: bool = False


@dataclass(frozen=True)
class PlannedWrite:
    path: Path
    content: str


def mcp_server_config(toolforge_dir: Path) -> dict:
    toolforge = str(toolforge_dir)
    return {
        "command": "uv",
        "args": ["--directory", toolforge, "run", "toolforge-mcp"],
        "env": {
            "TOOLFORGE_DB_PATH": str(toolforge_dir / "data" / "toolforge.db"),
            "TOOLFORGE_TOOLS_DIR": str(toolforge_dir / "tools"),
            "TOOLFORGE_WORK_DIR": str(toolforge_dir / "work"),
        },
    }


def codex_config_block(toolforge_dir: Path) -> str:
    server = mcp_server_config(toolforge_dir)
    env = server["env"]
    args = ", ".join(json.dumps(value) for value in server["args"])
    return "\n".join(
        [
            "[mcp_servers.toolforge]",
            'command = "uv"',
            f"args = [{args}]",
            "startup_timeout_sec = 20",
            "tool_timeout_sec = 120",
            "",
            "[mcp_servers.toolforge.env]",
            f'TOOLFORGE_DB_PATH = "{env["TOOLFORGE_DB_PATH"]}"',
            f'TOOLFORGE_TOOLS_DIR = "{env["TOOLFORGE_TOOLS_DIR"]}"',
            f'TOOLFORGE_WORK_DIR = "{env["TOOLFORGE_WORK_DIR"]}"',
            "",
        ]
    )


def read_template(repo_root: Path, relative_path: str) -> str:
    return (repo_root / relative_path).read_text(encoding="utf-8").strip() + "\n"


def managed_markdown(title: str, body: str) -> str:
    return (
        f"<!-- TOOLFORGE_{title}_START -->\n"
        f"{body.rstrip()}\n"
        f"<!-- TOOLFORGE_{title}_END -->\n"
    )


def managed_toml(title: str, body: str) -> str:
    return (
        f"# TOOLFORGE_{title}_START\n"
        f"{body.rstrip()}\n"
        f"# TOOLFORGE_{title}_END\n"
    )


def replace_managed_section(existing: str, start: str, end: str, replacement: str) -> str:
    if start in existing and end in existing:
        before = existing[: existing.index(start)]
        after = existing[existing.index(end) + len(end) :]
        return (before.rstrip() + "\n\n" + replacement.rstrip() + "\n" + after.lstrip()).rstrip() + "\n"
    if existing.strip():
        return existing.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return replacement.rstrip() + "\n"


def plan_managed_write(path: Path, replacement: str, start: str, end: str) -> PlannedWrite:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    return PlannedWrite(path, replace_managed_section(existing, start, end, replacement))


def load_json(path: Path) -> dict:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Cannot update invalid JSON file: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def plan_json_mcp_write(path: Path, toolforge_dir: Path, include_timeout: bool = False) -> PlannedWrite:
    data = load_json(path)
    data.setdefault("mcpServers", {})
    server = mcp_server_config(toolforge_dir)
    if include_timeout:
        server["timeout"] = 120000
    data["mcpServers"]["toolforge"] = server
    return PlannedWrite(path, json.dumps(data, indent=2) + "\n")


def write_plans(plans: Iterable[PlannedWrite], dry_run: bool) -> list[Path]:
    written = []
    for plan in plans:
        written.append(plan.path)
        if dry_run:
            continue
        plan.path.parent.mkdir(parents=True, exist_ok=True)
        plan.path.write_text(plan.content, encoding="utf-8")
    return written


def install_codex(config: SetupConfig) -> list[PlannedWrite]:
    body = read_template(config.repo_root, "governance/codex/AGENTS.md")
    guidance = managed_markdown("CODEX_GOVERNANCE", body)
    mcp = managed_toml("CODEX_MCP", codex_config_block(config.toolforge_dir))
    return [
        plan_managed_write(
            config.target_project / ".codex" / "AGENTS.md",
            guidance,
            "<!-- TOOLFORGE_CODEX_GOVERNANCE_START -->",
            "<!-- TOOLFORGE_CODEX_GOVERNANCE_END -->",
        ),
        plan_managed_write(
            config.target_project / ".codex" / "config.toml",
            mcp,
            "# TOOLFORGE_CODEX_MCP_START",
            "# TOOLFORGE_CODEX_MCP_END",
        ),
    ]


def install_claude(config: SetupConfig) -> list[PlannedWrite]:
    body = read_template(config.repo_root, "governance/claude/CLAUDE.md")
    guidance = managed_markdown("CLAUDE_GOVERNANCE", body)
    return [
        plan_managed_write(
            config.target_project / "CLAUDE.md",
            guidance,
            "<!-- TOOLFORGE_CLAUDE_GOVERNANCE_START -->",
            "<!-- TOOLFORGE_CLAUDE_GOVERNANCE_END -->",
        ),
        plan_json_mcp_write(config.target_project / ".mcp.json", config.toolforge_dir, include_timeout=True),
    ]


def install_cursor(config: SetupConfig) -> list[PlannedWrite]:
    rule = read_template(config.repo_root, "governance/cursor/toolforge.mdc")
    return [
        PlannedWrite(config.target_project / ".cursor" / "rules" / "toolforge.mdc", rule),
        plan_json_mcp_write(config.target_project / ".cursor" / "mcp.json", config.toolforge_dir),
    ]


def parse_agents(value: str) -> list[str]:
    requested = [item.strip().lower() for item in value.split(",") if item.strip()]
    if not requested or "all" in requested:
        return ["codex", "claude", "cursor"]
    unknown = sorted(set(requested) - AGENTS)
    if unknown:
        raise ValueError(f"Unknown agent(s): {', '.join(unknown)}")
    return requested


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install ToolForge MCP governance/config for agent clients.")
    parser.add_argument(
        "--agents",
        default="all",
        help="Comma-separated agents to configure: codex,claude,cursor,all. Default: all.",
    )
    parser.add_argument(
        "--target-project",
        type=Path,
        default=Path.cwd(),
        help="Project directory where agent guidance/config should be installed. Default: current directory.",
    )
    parser.add_argument(
        "--toolforge-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="ToolForge checkout used by MCP configs. Default: this repository.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned files without writing them.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        agents = parse_agents(args.agents)
    except ValueError as exc:
        parser.error(str(exc))

    config = SetupConfig(
        repo_root=Path(__file__).resolve().parents[1],
        target_project=args.target_project.resolve(),
        toolforge_dir=args.toolforge_dir.resolve(),
        dry_run=args.dry_run,
    )

    plans: list[PlannedWrite] = []
    for agent in agents:
        if agent == "codex":
            plans.extend(install_codex(config))
        elif agent == "claude":
            plans.extend(install_claude(config))
        elif agent == "cursor":
            plans.extend(install_cursor(config))

    written = write_plans(plans, config.dry_run)
    action = "Would write" if config.dry_run else "Wrote"
    for path in written:
        print(f"{action}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
