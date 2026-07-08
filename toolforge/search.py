from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from typing import Iterable


WORD_RE = re.compile(r"[a-z0-9_]+")


def embedding_text(tool: dict) -> str:
    tags = tool.get("tags", [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except json.JSONDecodeError:
            tags = [tags]
    return " ".join(
        [
            str(tool.get("name", "")),
            str(tool.get("description", "")),
            " ".join(str(tag) for tag in tags),
        ]
    ).strip()


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def lexical_score(query: str, text: str) -> float:
    query_terms = tokenize(query)
    text_terms = tokenize(text)
    if not query_terms or not text_terms:
        return 0.0
    query_counts = Counter(query_terms)
    text_counts = Counter(text_terms)
    overlap = sum(min(query_counts[t], text_counts[t]) for t in query_counts)
    coverage = overlap / len(query_terms)
    density = overlap / math.sqrt(len(text_terms))
    substring_boost = 0.15 if query.lower() in text.lower() else 0.0
    return min(1.0, coverage * 0.8 + density * 0.2 + substring_boost)


@lru_cache(maxsize=1)
def get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def encode_embedding(text: str) -> list[float] | None:
    model = get_embedding_model()
    if model is None:
        return None
    try:
        vector = model.encode(text, normalize_embeddings=True)
    except Exception:
        return None
    return [float(value) for value in vector]


def serialize_embedding(vector: list[float] | None) -> bytes | None:
    if vector is None:
        return None
    return json.dumps(vector).encode("utf-8")


def deserialize_embedding(blob: bytes | None) -> list[float] | None:
    if blob is None:
        return None
    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    try:
        return [float(value) for value in json.loads(blob.decode("utf-8"))]
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError, TypeError):
        return None


def cosine_score(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return max(0.0, sum(a * b for a, b in zip(left, right)))


def rank_tools(query: str, tools: Iterable[dict], limit: int) -> list[dict]:
    query_embedding = encode_embedding(query)
    ranked = []
    for tool in tools:
        text = tool.get("embedding_text") or embedding_text(tool)
        semantic = cosine_score(query_embedding, deserialize_embedding(tool.get("embedding")))
        lexical = lexical_score(query, text)
        score = semantic if semantic > 0 else lexical
        if score <= 0:
            continue
        item = dict(tool)
        item["score"] = round(score, 4)
        ranked.append(item)
    ranked.sort(key=lambda item: (item["status"] != "approved", -item["score"], item["name"]))
    return ranked[:limit]
