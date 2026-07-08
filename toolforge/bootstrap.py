from __future__ import annotations

import importlib.resources

from .database import connect
from .registry import ToolForgeRegistry


DEFAULT_TOOLS = [
    {
        "name": "validate_json_schema",
        "description": "Validate a JSON object against a provided JSON Schema and return whether it is valid plus any validation errors.",
        "tags": ["json", "schema", "validation"],
        "file": "validate_json_schema.py",
    },
    {
        "name": "clean_csv_file",
        "description": "Clean a CSV file by normalizing headers, trimming whitespace, removing empty rows, and optionally writing a cleaned output file.",
        "tags": ["csv", "data-cleaning", "files"],
        "file": "clean_csv_file.py",
    },
    {
        "name": "generate_markdown_report",
        "description": "Generate a structured Markdown report from a title, sections, tables, bullet lists, and summary content.",
        "tags": ["markdown", "report", "documentation"],
        "file": "generate_markdown_report.py",
    },
    {
        "name": "resize_image",
        "description": "Resize an image to a target width and height while preserving format and optionally maintaining aspect ratio.",
        "tags": ["image", "resize", "media"],
        "file": "resize_image.py",
    },
    {
        "name": "extract_text_from_pdf",
        "description": "Extract readable text from a PDF file and return full-document text or page-level text.",
        "tags": ["pdf", "text-extraction", "documents"],
        "file": "extract_text_from_pdf.py",
    },
]


def seed_default_tools(registry: ToolForgeRegistry) -> dict:
    with connect(registry.config.db_path) as conn:
        marker = conn.execute(
            "SELECT value FROM bootstrap_state WHERE key = 'default_tools_seeded'"
        ).fetchone()
        if marker is not None:
            return {"seeded": False, "message": "Default tools already seeded."}

    seeded = []
    seed_root = importlib.resources.files("toolforge.seed_tools")
    for spec in DEFAULT_TOOLS:
        code = (seed_root / spec["file"]).read_text(encoding="utf-8")
        existing = registry.list_tools(name=spec["name"])
        if existing:
            continue
        result = registry.register_tool(
            name=spec["name"],
            description=spec["description"],
            language="python",
            code=code,
            tags=spec["tags"],
            version="1.0.0",
            status="approved",
            approved=True,
            changelog="Seeded default ToolForge tool.",
        )
        registry.approve_tool(result["tool_id"], "1.0.0", "system", "Auto-approved default seed tool.")
        seeded.append(spec["name"])

    with connect(registry.config.db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bootstrap_state (key, value) VALUES ('default_tools_seeded', 'true')"
        )
    return {"seeded": True, "tools": seeded}
