from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ToolStatus = Literal["draft", "testing", "approved", "deprecated", "blocked"]


class RegisterToolInput(BaseModel):
    name: str = Field(description="Lowercase snake_case name for the reusable tool.")
    description: str = Field(description="Clear capability description for LLM search and selection.")
    language: Literal["python"] = Field(default="python", description="Tool language. MVP supports Python only.")
    code: str = Field(description="Python script source code that reads JSON from stdin and writes JSON to stdout.")
    tags: list[str] = Field(default_factory=list, description="Capability tags used for browsing and search.")
    version: str = Field(default="1.0.0", description="Semantic version for this tool version.")


class ListToolsInput(BaseModel):
    status: ToolStatus | None = Field(default=None, description="Optional lifecycle status filter.")
    tag: str | None = Field(default=None, description="Optional tag filter.")
    language: Literal["python"] | None = Field(default=None, description="Optional language filter.")
    name: str | None = Field(default=None, description="Optional case-insensitive partial name filter.")


class GetToolInput(BaseModel):
    tool_id: int = Field(description="ToolForge tool id to inspect.")


class ApproveToolInput(BaseModel):
    tool_id: int = Field(description="Tool id containing the version to approve.")
    version: str = Field(description="Semantic version to approve.")
    approved_by: str = Field(description="Human or workflow identity approving the tool.")
    notes: str = Field(default="", description="Approval notes explaining why this version is approved.")


class SearchToolsInput(BaseModel):
    query: str = Field(description="Intent, task description, name, tag, or capability to search for.")
    limit: int = Field(default=5, ge=1, le=25, description="Maximum number of matching tools to return.")
    include_deprecated: bool = Field(default=False, description="Include deprecated tools in results.")


class RunToolInput(BaseModel):
    tool_id: int = Field(description="Approved ToolForge tool id to execute.")
    input_json: dict[str, Any] = Field(description="JSON object passed to the tool on stdin.")


class UpdateToolInput(BaseModel):
    tool_id: int = Field(description="Existing tool id to version.")
    new_code: str = Field(description="Updated Python script source code.")
    version: str = Field(description="New semantic version to create as draft.")
    changelog: str = Field(description="Human-readable summary of the change.")


class DeprecateToolInput(BaseModel):
    tool_id: int = Field(description="Tool id to deprecate.")
    reason: str = Field(description="Reason the tool is obsolete or no longer preferred.")


class RollbackToolInput(BaseModel):
    tool_id: int = Field(description="Tool id to roll back.")
    target_version: str = Field(description="Earlier approved semantic version to make active.")
