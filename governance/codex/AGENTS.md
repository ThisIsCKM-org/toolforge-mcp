# Codex ToolForge Governance

## ToolForge MCP Workflow

- Before creating a utility script, search ToolForge MCP for an approved reusable tool.
- If an approved matching tool exists, use `run_tool` instead of creating local throwaway utility code.
- If no matching approved tool exists and you create any utility script that could be reused for a similar future request, register it in ToolForge MCP as a draft tool using `register_tool`.
- Treat scripts for common file/document/data operations as reusable by default, including PDF generation, CSV cleanup, JSON validation, image conversion, report generation, document parsing, archive/file transforms, and format conversion.
- Do not skip registration only because the script was created for the current user request. Skip registration only when the script is clearly one-off, tightly project-specific, unsafe, contains secrets, or depends on private local paths/data that cannot be generalized.
- When registering a generated script, give it a generic capability name, clear description, useful tags, and code that reads JSON from stdin and writes JSON to stdout.
- After registering a draft tool, tell the user it needs review and approval before future agents can run it normally.
- Approve ToolForge tools only when the user explicitly asks for approval or an authorized approval workflow has confirmed the tool is safe and useful.
