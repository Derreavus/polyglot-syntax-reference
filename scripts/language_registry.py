#!/usr/bin/env python3
"""Shared language registry access for the static site validation scripts.

Reads the canonical content source (data/site_data.json) rather than the
generated js/site-data.js, so the validators never depend on a build artifact.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "site_data.json"


def load_languages() -> list[dict[str, object]]:
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        languages = json.load(handle)["languages"]
    return sorted(languages, key=lambda lang: int(lang["order"]))


def language_slugs() -> list[str]:
    return [str(lang["slug"]) for lang in load_languages()]


def language_entry(slug: str) -> dict[str, object]:
    for language in load_languages():
        if language["slug"] == slug:
            return language
    raise KeyError(slug)
