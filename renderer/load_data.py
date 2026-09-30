from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "site_data.json"


def load_data() -> dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_languages(data: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(data.get("languages", []), key=lambda item: int(item.get("order", 0)))


def get_sections(data: dict[str, Any], language_slug: str) -> list[dict[str, Any]]:
    sections = data.get("sections", [])
    return [section for section in sections if section.get("language") == language_slug]


def get_topics(data: dict[str, Any], language_slug: str) -> list[dict[str, Any]]:
    topics = data.get("topics", [])
    return [topic for topic in topics if topic.get("language") == language_slug]


def get_examples(data: dict[str, Any], language_slug: str, topic_slug: str) -> list[dict[str, Any]]:
    examples = data.get("examples", [])
    return [
        example
        for example in examples
        if example.get("language") == language_slug and example.get("topic") == topic_slug
    ]


def get_compare_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    return data.get("compare", [])
