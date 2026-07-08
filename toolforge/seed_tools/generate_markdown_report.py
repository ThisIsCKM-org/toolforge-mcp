import json
import sys


payload = json.load(sys.stdin)
lines = [f"# {payload.get('title', 'Report')}", ""]

summary = payload.get("summary")
if summary:
    lines.extend([str(summary), ""])

for section in payload.get("sections", []):
    lines.extend([f"## {section.get('heading', 'Section')}", ""])
    if section.get("content"):
        lines.extend([str(section["content"]), ""])
    for item in section.get("bullets", []):
        lines.append(f"- {item}")
    if section.get("bullets"):
        lines.append("")
    for table in section.get("tables", []):
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        if headers:
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in rows:
                lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
            lines.append("")

markdown = "\n".join(lines).rstrip() + "\n"
print(json.dumps({"markdown": markdown}))
