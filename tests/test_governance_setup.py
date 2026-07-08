import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "setup_agent_governance.py"
spec = importlib.util.spec_from_file_location("setup_agent_governance", SCRIPT_PATH)
setup = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = setup
spec.loader.exec_module(setup)


def run_setup(tmp_path: Path, agents: str = "all") -> None:
    setup.main(
        [
            "--agents",
            agents,
            "--target-project",
            str(tmp_path / "target"),
            "--toolforge-dir",
            str(tmp_path / "toolforge"),
        ]
    )


def test_setup_installs_all_agent_governance_files(tmp_path):
    run_setup(tmp_path)
    target = tmp_path / "target"

    assert (target / ".codex" / "AGENTS.md").exists()
    assert (target / ".codex" / "config.toml").exists()
    assert (target / "CLAUDE.md").exists()
    assert (target / ".mcp.json").exists()
    assert (target / ".cursor" / "rules" / "toolforge.mdc").exists()
    assert (target / ".cursor" / "mcp.json").exists()

    codex_guidance = (target / ".codex" / "AGENTS.md").read_text()
    assert "Before creating a utility script" in codex_guidance
    assert "TOOLFORGE_CODEX_GOVERNANCE_START" in codex_guidance

    codex_config = (target / ".codex" / "config.toml").read_text()
    assert "[mcp_servers.toolforge]" in codex_config
    assert str(tmp_path / "toolforge") in codex_config


def test_setup_is_idempotent_for_managed_sections(tmp_path):
    run_setup(tmp_path)
    run_setup(tmp_path)
    target = tmp_path / "target"

    codex_guidance = (target / ".codex" / "AGENTS.md").read_text()
    codex_config = (target / ".codex" / "config.toml").read_text()
    claude_guidance = (target / "CLAUDE.md").read_text()

    assert codex_guidance.count("TOOLFORGE_CODEX_GOVERNANCE_START") == 1
    assert codex_config.count("TOOLFORGE_CODEX_MCP_START") == 1
    assert claude_guidance.count("TOOLFORGE_CLAUDE_GOVERNANCE_START") == 1


def test_setup_preserves_existing_json_mcp_servers(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    existing = {"mcpServers": {"other": {"command": "echo", "args": ["ok"]}}}
    (target / ".mcp.json").write_text(json.dumps(existing))

    run_setup(tmp_path, agents="claude")

    data = json.loads((target / ".mcp.json").read_text())
    assert data["mcpServers"]["other"] == {"command": "echo", "args": ["ok"]}
    assert data["mcpServers"]["toolforge"]["command"] == "uv"
    assert data["mcpServers"]["toolforge"]["timeout"] == 120000


def test_dry_run_does_not_write_files(tmp_path, capsys):
    target = tmp_path / "target"
    result = setup.main(
        [
            "--agents",
            "codex",
            "--target-project",
            str(target),
            "--toolforge-dir",
            str(tmp_path / "toolforge"),
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "Would write" in captured.out
    assert not (target / ".codex" / "AGENTS.md").exists()
