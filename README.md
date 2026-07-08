# ToolForge MCP

ToolForge MCP is a governed registry of reusable Python tools for AI agents.
It lets agents search approved tools by intent, run approved tools with JSON
input, register newly generated scripts as drafts, and manage tool lifecycle
through approval, updates, deprecation, and rollback.

The MVP is MCP-only. It runs over stdio by default and does not include a web UI
or HTTP server.

## Features

- Register Python scripts as draft reusable tools
- Approve reviewed tool versions for execution
- Search approved tools by semantic-style intent with keyword/tag fallback
- Run approved tools through a subprocess JSON contract
- Log every run to SQLite
- Seed safe default tools on first startup
- Update, deprecate, and rollback tool versions

## Runtime Paths

By default, ToolForge stores metadata and runtime tool files locally:

```text
data/toolforge.db
tools/
```

Override these paths with:

```bash
export TOOLFORGE_DB_PATH=/path/to/toolforge.db
export TOOLFORGE_TOOLS_DIR=/path/to/tools
export TOOLFORGE_WORK_DIR=/path/to/work
```

## MCP Server

Run the server with:

```bash
uv run toolforge-mcp
```

or:

```bash
python3 server.py
```

## Connect MCP Clients

ToolForge MCP is a local stdio MCP server. The MCP client starts the process,
then discovers the server instructions and available tools at connection time.

Use absolute paths in client configuration so the server can start from any
working directory. Replace `/absolute/path/to/toolforge-mcp` with your local
checkout path.

### Recommended Setup

Install runtime dependencies before connecting a client:

```bash
cd /absolute/path/to/toolforge-mcp
uv sync --extra dev
```

The `--extra dev` option installs test dependencies and optional libraries used
by the default seed tools, such as PDF and image helpers. Local semantic
embeddings are optional because they pull a larger ML dependency stack. To enable
them, run:

```bash
uv sync --extra dev --extra semantic
```

If you do not use `uv`, create a Python environment and install the package
dependencies from `pyproject.toml`.

### Codex

Codex reads MCP servers from `~/.codex/config.toml`, or from a project-scoped
`.codex/config.toml` in trusted projects. The Codex CLI and IDE extension share
this configuration.

CLI setup:

```bash
codex mcp add toolforge --env TOOLFORGE_DB_PATH=/absolute/path/to/toolforge-mcp/data/toolforge.db --env TOOLFORGE_TOOLS_DIR=/absolute/path/to/toolforge-mcp/tools --env TOOLFORGE_WORK_DIR=/absolute/path/to/toolforge-mcp/work -- uv --directory /absolute/path/to/toolforge-mcp run toolforge-mcp
```

Equivalent `~/.codex/config.toml` entry:

```toml
[mcp_servers.toolforge]
command = "uv"
args = ["--directory", "/absolute/path/to/toolforge-mcp", "run", "toolforge-mcp"]
startup_timeout_sec = 20
tool_timeout_sec = 120

[mcp_servers.toolforge.env]
TOOLFORGE_DB_PATH = "/absolute/path/to/toolforge-mcp/data/toolforge.db"
TOOLFORGE_TOOLS_DIR = "/absolute/path/to/toolforge-mcp/tools"
TOOLFORGE_WORK_DIR = "/absolute/path/to/toolforge-mcp/work"
```

In the Codex TUI, run `/mcp` to confirm that `toolforge` is connected.

### Claude Code

Claude Code can add local stdio MCP servers with `claude mcp add`. The `--`
separator is important: everything after it is the command used to start the MCP
server.

CLI setup:

```bash
claude mcp add \
  --env TOOLFORGE_DB_PATH=/absolute/path/to/toolforge-mcp/data/toolforge.db \
  --env TOOLFORGE_TOOLS_DIR=/absolute/path/to/toolforge-mcp/tools \
  --env TOOLFORGE_WORK_DIR=/absolute/path/to/toolforge-mcp/work \
  --transport stdio \
  toolforge \
  -- uv --directory /absolute/path/to/toolforge-mcp run toolforge-mcp
```

Project-scoped `.mcp.json` example:

```json
{
  "mcpServers": {
    "toolforge": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/toolforge-mcp", "run", "toolforge-mcp"],
      "env": {
        "TOOLFORGE_DB_PATH": "/absolute/path/to/toolforge-mcp/data/toolforge.db",
        "TOOLFORGE_TOOLS_DIR": "/absolute/path/to/toolforge-mcp/tools",
        "TOOLFORGE_WORK_DIR": "/absolute/path/to/toolforge-mcp/work"
      },
      "timeout": 120000
    }
  }
}
```

Inside Claude Code, use `/mcp` to inspect server status. Project-scoped MCP
servers may require workspace trust approval before they become active.

### Cursor

Cursor reads MCP servers from JSON configuration. Use a project-scoped
`.cursor/mcp.json` when ToolForge should be available only for this repository,
or a user-level MCP configuration when you want it available across projects.

Project-scoped `.cursor/mcp.json` example:

```json
{
  "mcpServers": {
    "toolforge": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/toolforge-mcp", "run", "toolforge-mcp"],
      "env": {
        "TOOLFORGE_DB_PATH": "/absolute/path/to/toolforge-mcp/data/toolforge.db",
        "TOOLFORGE_TOOLS_DIR": "/absolute/path/to/toolforge-mcp/tools",
        "TOOLFORGE_WORK_DIR": "/absolute/path/to/toolforge-mcp/work"
      }
    }
  }
}
```

After editing Cursor MCP settings, reload Cursor or restart the agent session,
then confirm that the ToolForge tools appear in Cursor's MCP/tools panel.

### Without `uv`

If `uv` is not available, install the project into a virtual environment and use
that environment's Python directly:

```bash
cd /absolute/path/to/toolforge-mcp
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[dev]"
# Optional semantic embeddings:
# python3 -m pip install -e ".[dev,semantic]"
```

Then replace the MCP command with:

```json
{
  "command": "/absolute/path/to/toolforge-mcp/.venv/bin/python",
  "args": ["/absolute/path/to/toolforge-mcp/server.py"]
}
```

## Agent Governance Pack

ToolForge includes copy-ready governance examples for teams that want Codex,
Claude Code, and Cursor to consistently reuse MCP tools instead of creating
throwaway scripts.

See [`governance/`](governance/) for:

- Codex `AGENTS.md` guidance and `config.toml` MCP example
- Claude Code `CLAUDE.md` guidance and `.mcp.json` example
- Cursor `.mdc` rule and `.cursor/mcp.json` example

The shared policy is:

1. Search ToolForge before creating utility scripts.
2. Run an approved tool when one exists.
3. Register newly generated reusable utility scripts as draft tools.
4. Approve tools only after human or authorized workflow review.

### Setup Script

Use the setup script to install project-scoped governance and MCP config for
Codex, Claude Code, and Cursor. Running the script without arguments prints
help and does not write files:

```bash
python3 scripts/setup_agent_governance.py
```

Pass explicit options to install governance/config files:

```bash
python3 scripts/setup_agent_governance.py \
  --agents all \
  --target-project /path/to/your/project \
  --toolforge-dir /absolute/path/to/toolforge-mcp
```

Preview changes without writing files:

```bash
python3 scripts/setup_agent_governance.py --agents all --target-project /path/to/your/project --dry-run
```

Configure one agent at a time:

```bash
python3 scripts/setup_agent_governance.py --agents codex --target-project /path/to/your/project
python3 scripts/setup_agent_governance.py --agents claude --target-project /path/to/your/project
python3 scripts/setup_agent_governance.py --agents cursor --target-project /path/to/your/project
```

The script updates managed ToolForge sections idempotently and preserves other
MCP servers in JSON config files.

## Stored Tool Contract

Stored scripts must:

- read one JSON object from stdin
- write one JSON object to stdout
- exit nonzero on failure

## Default Seed Tools

On first startup, ToolForge seeds these approved tools:

- `validate_json_schema`
- `clean_csv_file`
- `generate_markdown_report`
- `resize_image`
- `extract_text_from_pdf`

The seed operation is idempotent and recorded in SQLite.

## License

Apache License 2.0
