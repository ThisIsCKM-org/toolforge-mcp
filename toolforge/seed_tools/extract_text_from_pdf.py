import json
import sys
from pathlib import Path


try:
    from pypdf import PdfReader
except ImportError:
    print(json.dumps({"error": "pypdf is required for extract_text_from_pdf."}))
    raise SystemExit(1)


payload = json.load(sys.stdin)
input_path = Path(payload["input_path"])
page_level = bool(payload.get("page_level", False))
reader = PdfReader(str(input_path))
pages = [{"page": index + 1, "text": page.extract_text() or ""} for index, page in enumerate(reader.pages)]

if page_level:
    print(json.dumps({"pages": pages, "page_count": len(pages)}))
else:
    print(json.dumps({"text": "\n".join(page["text"] for page in pages), "page_count": len(pages)}))
