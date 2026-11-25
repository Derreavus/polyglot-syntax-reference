#!/usr/bin/env python3
"""Shared language registry access for the static site validation scripts.

Reads the canonical content source (data/site_data.json) rather than the
generated js/site-data.js, so the validators never depend on a build artifact.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "site_data.json"


def load_languages() -> list[dict[str, object]]:
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        languages = json.load(handle)["languages"]
    return sorted(languages, key=lambda lang: int(lang["order"]))


# The topic text the add_language script writes for a language whose topics a maintainer has not written yet.
PLACEHOLDER_TOPIC_HTML = "<p>This topic has not been written yet.</p>"


def placeholder_counts() -> dict[str, tuple[int, int]]:
    """Per language: how many of its topics are still the placeholder, and how many topics it has."""
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        topics = json.load(handle)["topics"]
    counts: dict[str, list[int]] = {}
    for topic in topics:
        pair = counts.setdefault(str(topic["language"]), [0, 0])
        pair[0] += topic["content_html"] == PLACEHOLDER_TOPIC_HTML
        pair[1] += 1
    return {slug: (pair[0], pair[1]) for slug, pair in counts.items()}


def language_slugs() -> list[str]:
    return [str(lang["slug"]) for lang in load_languages()]


def language_entry(slug: str) -> dict[str, object]:
    for language in load_languages():
        if language["slug"] == slug:
            return language
    raise KeyError(slug)
