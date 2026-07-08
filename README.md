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
