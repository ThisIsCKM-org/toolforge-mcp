import json
import sys
from pathlib import Path


try:
    from PIL import Image
except ImportError:
    print(json.dumps({"error": "Pillow is required for resize_image."}))
    raise SystemExit(1)


payload = json.load(sys.stdin)
input_path = Path(payload["input_path"])
output_path = Path(payload.get("output_path", input_path.with_name(input_path.stem + "_resized" + input_path.suffix)))
width = int(payload["width"])
height = int(payload["height"])
maintain_aspect_ratio = bool(payload.get("maintain_aspect_ratio", True))

with Image.open(input_path) as image:
    if maintain_aspect_ratio:
        image.thumbnail((width, height))
        resized = image.copy()
    else:
        resized = image.resize((width, height))
    resized.save(output_path)
    size = resized.size

print(json.dumps({"output_path": str(output_path), "width": size[0], "height": size[1]}))
