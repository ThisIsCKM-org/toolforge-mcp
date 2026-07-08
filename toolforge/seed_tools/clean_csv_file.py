import csv
import json
import sys
from pathlib import Path


payload = json.load(sys.stdin)
input_path = Path(payload["input_path"])
output_path = Path(payload.get("output_path", input_path.with_name(input_path.stem + "_clean.csv")))

with input_path.open(newline="", encoding=payload.get("encoding", "utf-8")) as source:
    rows = list(csv.reader(source))

if not rows:
    output_path.write_text("", encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), "rows_written": 0}))
    raise SystemExit(0)

headers = [header.strip().lower().replace(" ", "_") for header in rows[0]]
cleaned = [headers]
for row in rows[1:]:
    normalized = [cell.strip() for cell in row]
    if any(normalized):
        cleaned.append(normalized)

with output_path.open("w", newline="", encoding="utf-8") as target:
    writer = csv.writer(target)
    writer.writerows(cleaned)

print(json.dumps({"output_path": str(output_path), "rows_written": max(0, len(cleaned) - 1)}))
