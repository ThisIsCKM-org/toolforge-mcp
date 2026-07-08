from __future__ import annotations

from .bootstrap import seed_default_tools
from .config import ToolForgeConfig
from .registry import ToolForgeRegistry
from .runner import ToolRunner


SERVER_DESCRIPTION = (
    "ToolForge MCP provides a governed registry of reusable Python tools for AI agents. "
    "Use it to search approved tools by intent, run approved tools with JSON input, "
    "register newly generated scripts as draft tools, approve reviewed versions, and "
    "manage tool lifecycle through updates, deprecation, and rollback."
)


def create_services(config: ToolForgeConfig | None = None) -> tuple[ToolForgeRegistry, ToolRunner]:
    registry = ToolForgeRegistry(config or ToolForgeConfig.from_env())
    seed_default_tools(registry)
    return registry, ToolRunner(registry)


def create_mcp():
    try:
        from fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("fastmcp is required to run the MCP server. Install dependencies with uv sync.") from exc

    registry, runner = create_services()
    mcp = FastMCP("ToolForge MCP", instructions=SERVER_DESCRIPTION)

    @mcp.tool(
        description="Register a new reusable Python script as a draft ToolForge tool. Use this when an agent or user has created a useful script that should be saved for review, approval, versioning, and future reuse."
    )
    def register_tool(name: str, description: str, language: str, code: str, tags: list[str], version: str = "1.0.0") -> dict:
        return registry.register_tool(name, description, language, code, tags, version)

    @mcp.tool(
        description="List ToolForge tools with optional filters such as status, tag, language, or name. Use this to browse the registry, inspect available capabilities, or find tools before choosing one to view, approve, update, or run."
    )
    def list_tools(status: str | None = None, tag: str | None = None, language: str | None = None, name: str | None = None) -> list[dict]:
        return registry.list_tools(status=status, tag=tag, language=language, name=name)

    @mcp.tool(
        description="Get detailed metadata for a ToolForge tool, including description, tags, lifecycle status, versions, active approved version, checksum, approval state, and usage history. Use this before running, approving, updating, deprecating, or explaining a tool."
    )
    def get_tool(tool_id: int) -> dict:
        return registry.get_tool(tool_id)

    @mcp.tool(
        description="Approve a reviewed draft or tested tool version so it becomes available for search and execution. Use this only after a human or authorized approval workflow has confirmed the tool is safe and useful."
    )
    def approve_tool(tool_id: int, version: str, approved_by: str, notes: str = "") -> dict:
        return registry.approve_tool(tool_id, version, approved_by, notes)

    @mcp.tool(
        description="Search approved reusable ToolForge tools by intent, task description, name, tags, or capability. Uses semantic search with keyword and tag fallback. Use this before generating new code when an existing approved tool may already solve the task."
    )
    def search_tools(query: str, limit: int = 5, include_deprecated: bool = False) -> list[dict]:
        return registry.search_tools(query, limit, include_deprecated)

    @mcp.tool(
        description="Execute an approved ToolForge tool with JSON input and return JSON output. Use this when the correct approved tool has been selected and the task should be performed through a governed, logged execution."
    )
    def run_tool(tool_id: int, input_json: dict) -> dict:
        return runner.run_tool(tool_id, input_json)

    @mcp.tool(
        description="Create a new draft version of an existing ToolForge tool with updated code and a changelog. Use this when a tool needs a bug fix, improvement, new behavior, or compatibility update without replacing the current approved version immediately."
    )
    def update_tool(tool_id: int, new_code: str, version: str, changelog: str) -> dict:
        return registry.update_tool(tool_id, new_code, version, changelog)

    @mcp.tool(
        description="Mark a ToolForge tool as deprecated so it remains visible for history and audit purposes but is no longer recommended or used by default. Use this when a tool is obsolete, replaced, unsafe for normal use, or no longer preferred."
    )
    def deprecate_tool(tool_id: int, reason: str) -> dict:
        return registry.deprecate_tool(tool_id, reason)

    @mcp.tool(
        description="Restore an earlier approved version of a ToolForge tool as the active version. Use this when a newer approved version is broken, unsafe, or less reliable than a previous approved version."
    )
    def rollback_tool(tool_id: int, target_version: str) -> dict:
        return registry.rollback_tool(tool_id, target_version)

    return mcp


def main() -> None:
    create_mcp().run()
