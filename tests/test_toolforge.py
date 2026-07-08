import json
import sqlite3
import textwrap
from pathlib import Path

from toolforge.bootstrap import seed_default_tools
from toolforge.config import ToolForgeConfig
from toolforge.mcp_server import SERVER_DESCRIPTION
from toolforge.registry import ToolForgeRegistry
from toolforge.runner import ToolRunner


def make_registry(tmp_path: Path) -> ToolForgeRegistry:
    return ToolForgeRegistry(
        ToolForgeConfig(
            db_path=tmp_path / "data" / "toolforge.db",
            tools_dir=tmp_path / "tools",
            work_dir=tmp_path / "work",
            timeout_seconds=1,
        )
    )


def test_server_description_mentions_governed_registry():
    assert "governed registry" in SERVER_DESCRIPTION
    assert "reusable Python tools" in SERVER_DESCRIPTION


def test_bootstrap_seeds_default_tools_once(tmp_path):
    registry = make_registry(tmp_path)
    first = seed_default_tools(registry)
    second = seed_default_tools(registry)

    assert first["seeded"] is True
    assert second["seeded"] is False
    tools = registry.list_tools(status="approved")
    assert {tool["name"] for tool in tools} >= {
        "validate_json_schema",
        "clean_csv_file",
        "generate_markdown_report",
        "resize_image",
        "extract_text_from_pdf",
    }


def test_register_rejects_duplicate_names(tmp_path):
    registry = make_registry(tmp_path)
    code = "import json, sys\nprint(json.dumps({'ok': True}))\n"
    registry.register_tool("sample_tool", "Sample tool", "python", code, ["sample"])

    try:
        registry.register_tool("sample_tool", "Sample tool", "python", code, ["sample"])
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("Expected duplicate tool name to fail")


def test_approved_tool_runs_and_logs_success(tmp_path):
    registry = make_registry(tmp_path)
    runner = ToolRunner(registry)
    code = textwrap.dedent(
        """
        import json
        import sys

        payload = json.load(sys.stdin)
        print(json.dumps({"echo": payload["value"]}))
        """
    )
    created = registry.register_tool("echo_tool", "Echo a value", "python", code, ["echo"])
    registry.approve_tool(created["tool_id"], "1.0.0", "tester", "safe")

    result = runner.run_tool(created["tool_id"], {"value": "hello"})

    assert result["status"] == "success"
    assert result["output_json"] == {"echo": "hello"}
    assert registry.get_tool(created["tool_id"])["recent_runs"][0]["status"] == "success"


def test_draft_tool_cannot_run(tmp_path):
    registry = make_registry(tmp_path)
    runner = ToolRunner(registry)
    created = registry.register_tool(
        "draft_tool",
        "Draft only",
        "python",
        "import json\nprint(json.dumps({'ok': True}))\n",
        ["draft"],
    )

    result = runner.run_tool(created["tool_id"], {})

    assert result["status"] == "failed"
    assert "Only approved tools can run" in result["error"]


def test_checksum_mismatch_blocks_execution(tmp_path):
    registry = make_registry(tmp_path)
    runner = ToolRunner(registry)
    created = registry.register_tool(
        "checksum_tool",
        "Checksum test",
        "python",
        "import json\nprint(json.dumps({'ok': True}))\n",
        ["checksum"],
    )
    registry.approve_tool(created["tool_id"], "1.0.0", "tester", "safe")
    version = registry.get_tool(created["tool_id"])["versions"][0]
    Path(version["file_path"]).write_text("print('tampered')\n", encoding="utf-8")

    result = runner.run_tool(created["tool_id"], {})

    assert result["status"] == "failed"
    assert "Checksum mismatch" in result["error"]


def test_timeout_is_enforced(tmp_path):
    registry = make_registry(tmp_path)
    runner = ToolRunner(registry)
    code = "import time\ntime.sleep(5)\n"
    created = registry.register_tool("slow_tool", "Slow tool", "python", code, ["slow"])
    registry.approve_tool(created["tool_id"], "1.0.0", "tester", "safe")

    result = runner.run_tool(created["tool_id"], {})

    assert result["status"] == "failed"
    assert "timed out" in result["error"]


def test_invalid_json_output_is_failure(tmp_path):
    registry = make_registry(tmp_path)
    runner = ToolRunner(registry)
    created = registry.register_tool(
        "bad_json_tool",
        "Bad JSON",
        "python",
        "print('not json')\n",
        ["json"],
    )
    registry.approve_tool(created["tool_id"], "1.0.0", "tester", "safe")

    result = runner.run_tool(created["tool_id"], {})

    assert result["status"] == "failed"
    assert "invalid JSON" in result["error"]


def test_search_finds_approved_tool_and_ignores_draft(tmp_path):
    registry = make_registry(tmp_path)
    code = "import json\nprint(json.dumps({'ok': True}))\n"
    approved = registry.register_tool("clean_orders_csv", "Clean order CSV files", "python", code, ["csv"])
    registry.approve_tool(approved["tool_id"], "1.0.0", "tester", "safe")
    registry.register_tool("draft_csv_tool", "Clean CSV draft", "python", code, ["csv"])

    results = registry.search_tools("clean csv file", limit=5)

    assert [result["name"] for result in results] == ["clean_orders_csv"]


def test_update_rollback_and_deprecate(tmp_path):
    registry = make_registry(tmp_path)
    original = "import json\nprint(json.dumps({'version': 1}))\n"
    updated = "import json\nprint(json.dumps({'version': 2}))\n"
    created = registry.register_tool("versioned_tool", "Versioned", "python", original, ["version"])
    registry.approve_tool(created["tool_id"], "1.0.0", "tester", "safe")
    registry.update_tool(created["tool_id"], updated, "1.1.0", "return v2")
    registry.approve_tool(created["tool_id"], "1.1.0", "tester", "safe")

    rollback = registry.rollback_tool(created["tool_id"], "1.0.0")
    deprecated = registry.deprecate_tool(created["tool_id"], "Replaced")

    assert rollback["active_version"] == "1.0.0"
    assert deprecated["status"] == "deprecated"


def test_seeded_schema_tool_runs(tmp_path):
    registry = make_registry(tmp_path)
    seed_default_tools(registry)
    tool = next(tool for tool in registry.list_tools() if tool["name"] == "validate_json_schema")
    result = ToolRunner(registry).run_tool(
        tool["id"],
        {
            "data": {"name": "Ada"},
            "schema": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}},
        },
    )

    assert result["status"] == "success"
    assert result["output_json"] == {"valid": True, "errors": []}
