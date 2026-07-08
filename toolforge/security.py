from __future__ import annotations

import re


DANGEROUS_PATTERNS: tuple[tuple[str, str], ...] = (
    ("eval", r"\beval\s*\("),
    ("exec", r"\bexec\s*\("),
    ("os.system", r"\bos\.system\s*\("),
    ("subprocess", r"\bsubprocess\b"),
    ("socket", r"\bsocket\b"),
    ("requests", r"\brequests\b"),
    ("shutil.rmtree", r"\bshutil\.rmtree\s*\("),
    ("etc access", r"open\s*\(\s*['\"]/(etc|var|root)"),
    ("environment access", r"\bos\.environ\b|getenv\s*\("),
)


def scan_code(code: str) -> dict:
    findings = [
        label for label, pattern in DANGEROUS_PATTERNS if re.search(pattern, code)
    ]
    if not findings:
        risk_level = "low"
    elif len(findings) <= 2:
        risk_level = "medium"
    else:
        risk_level = "high"
    return {"risk_level": risk_level, "findings": findings}
