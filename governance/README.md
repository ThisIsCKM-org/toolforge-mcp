# ToolForge Agent Governance Pack

This directory contains copy-ready governance examples for agents that should use
ToolForge MCP as the reusable utility registry.

The goal is consistent behavior across Codex, Claude Code, and Cursor:

1. Search ToolForge before creating utility scripts.
2. Run an approved ToolForge tool when one matches the task.
3. Register newly generated reusable utility scripts as draft tools.
4. Require human or authorized workflow approval before new tools become approved.

Replace `/absolute/path/to/toolforge-mcp` in config examples with your local
ToolForge checkout path.

## Files

- `codex/AGENTS.md`: global or project Codex guidance.
- `codex/config.toml.example`: Codex MCP server config.
- `claude/CLAUDE.md`: global or project Claude Code guidance.
- `claude/mcp.json.example`: Claude Code project MCP config.
- `cursor/toolforge.mdc`: Cursor project rule.
- `cursor/mcp.json.example`: Cursor project MCP config.

## Recommended Rollout

1. Install and test ToolForge MCP locally.
2. Add the matching MCP config for each agent.
3. Add the matching guidance/rules file for each agent.
4. Start a new agent session so guidance and MCP config are reloaded.
5. Test with a utility task, such as PDF generation or CSV cleanup.
