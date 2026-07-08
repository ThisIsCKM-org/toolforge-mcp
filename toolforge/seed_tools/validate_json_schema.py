import json
import sys


def _validate(value, schema, path="$"):
    errors = []
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            return [f"{path}: expected object"]
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: missing required property")
        for key, child_schema in schema.get("properties", {}).items():
            if key in value:
                errors.extend(_validate(value[key], child_schema, f"{path}.{key}"))
    elif expected == "array":
        if not isinstance(value, list):
            return [f"{path}: expected array"]
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                errors.extend(_validate(item, item_schema, f"{path}[{index}]"))
    elif expected == "string" and not isinstance(value, str):
        errors.append(f"{path}: expected string")
    elif expected == "number" and not isinstance(value, (int, float)):
        errors.append(f"{path}: expected number")
    elif expected == "integer" and not isinstance(value, int):
        errors.append(f"{path}: expected integer")
    elif expected == "boolean" and not isinstance(value, bool):
        errors.append(f"{path}: expected boolean")
    return errors


payload = json.load(sys.stdin)
data = payload.get("data")
schema = payload.get("schema", {})
errors = _validate(data, schema)
print(json.dumps({"valid": not errors, "errors": errors}))
