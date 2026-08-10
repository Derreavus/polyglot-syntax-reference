#!/usr/bin/env python3
"""Shared language registry access for the static site validation scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "js" / "site-data.js"


def load_languages() -> list[dict[str, object]]:
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    match = re.search(r"window\.POLYGLOT_LANGUAGES\s*=\s*(\[[\s\S]*?\])\s*;", text)
    if match is None:
        raise ValueError(f"Language registry not found in {REGISTRY_PATH}")
    payload = match.group(1)
    languages = json.loads(payload)
    return sorted(languages, key=lambda lang: int(lang["order"]))


def language_slugs() -> list[str]:
    return [str(lang["slug"]) for lang in load_languages()]
