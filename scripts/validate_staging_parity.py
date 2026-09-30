#!/usr/bin/env python3
"""Validate that the generated staging pages include the expected browser runtime hooks.

This is a parity check for the local preview build: the live pages rely on JS to
inject navigation/search/theme/copy/back-to-top UI at runtime, so the generated
staging output must still ship the required hooks and runtime markers.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "staging"
DATA_PATH = ROOT / "data" / "site_data.json"
MINIMUM_TOPIC_COUNTS = {
    "python": 18,
    "rust": 20,
    "cpp": 21,
    "csharp": 20,
    "javascript": 10,
}

RUNTIME_MARKERS = {
    "theme": [
        'const themeBtn = document.getElementById("theme-toggle")',
        'localStorage.getItem("theme")',
    ],
    "language_navigation": [
        'nav.querySelector(".language-menu")',
        'link.className = "language-option hero-card "',
        'registry.forEach(function (lang)',
    ],
    "search": [
        'injectSearchTrigger(openPalette)',
        'const SEARCH_INDEX = window.POLYGLOT_SEARCH_INDEX || [];',
        'openPalette()',
        'cmd-overlay',
    ],
    "copy": [
        'document.querySelectorAll("pre")',
        'copy-btn',
        'navigator.clipboard',
    ],
    "xlang": [
        'section.topic[id]',
        'xlang-bar',
        'Also in',
    ],
    "back_to_top": [
        'document.getElementById("back-to-top")',
        'window.scrollTo({ top: 0, behavior: "smooth" })',
    ],
}


def ensure_runtime_marker_set(file_path: Path, markers: list[str], label: str) -> list[str]:
    text = file_path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in text]
    if missing:
        return [f"{label}: missing runtime markers -> {', '.join(missing)}"]
    return []


def main() -> int:
    errors: list[str] = []
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    for language in data["languages"]:
        slug = language["slug"]
        page = OUT / slug / "index.html"
        if not page.exists():
            errors.append(f"{slug}: missing generated page")
            continue

        text = page.read_text(encoding="utf-8")
        if 'class="language-menu"' not in text or 'class="language-menu-panel"' not in text:
            errors.append(f"{slug}: missing language dropdown markup")
        expected_topics = {
            topic["slug"] for topic in data["topics"] if topic["language"] == slug
        }
        minimum_count = MINIMUM_TOPIC_COUNTS.get(slug, 1)
        if len(expected_topics) < minimum_count:
            errors.append(
                f"{slug}: only {len(expected_topics)} topics; expected at least {minimum_count}"
            )
        rendered_topics = set(
            re.findall(r'<section class="topic" id="([^"]+)"', text)
        )
        if rendered_topics != expected_topics:
            missing = sorted(expected_topics - rendered_topics)
            extra = sorted(rendered_topics - expected_topics)
            errors.append(
                f"{slug}: topic mismatch (missing: {', '.join(missing) or 'none'}; "
                f"extra: {', '.join(extra) or 'none'})"
            )

        for topic in data["topics"]:
            if topic["language"] != slug:
                continue
            content_html = topic.get("content_html")
            if not isinstance(content_html, str) or not content_html.strip():
                errors.append(f"{slug}#{topic['slug']}: missing full topic content")
            elif content_html not in text:
                errors.append(f"{slug}#{topic['slug']}: full topic content not rendered")

    runtime_js = OUT / "js" / "main.js"
    site_data_js = OUT / "js" / "site-data.js"
    if not runtime_js.exists():
        errors.append("missing generated runtime JS")
    if not site_data_js.exists():
        errors.append("missing generated site data JS")

    if runtime_js.exists():
        errors.extend(ensure_runtime_marker_set(runtime_js, RUNTIME_MARKERS["theme"], "theme"))
        errors.extend(ensure_runtime_marker_set(runtime_js, RUNTIME_MARKERS["language_navigation"], "language_navigation"))
        errors.extend(ensure_runtime_marker_set(runtime_js, RUNTIME_MARKERS["search"], "search"))
        errors.extend(ensure_runtime_marker_set(runtime_js, RUNTIME_MARKERS["copy"], "copy"))
        errors.extend(ensure_runtime_marker_set(runtime_js, RUNTIME_MARKERS["xlang"], "xlang"))
        errors.extend(ensure_runtime_marker_set(runtime_js, RUNTIME_MARKERS["back_to_top"], "back_to_top"))
        runtime_text = runtime_js.read_text(encoding="utf-8")
        if "const CONCEPTS = {" in runtime_text or "const SEARCH_INDEX = [" in runtime_text:
            errors.append("runtime JS still contains hardcoded topic metadata")

    if site_data_js.exists():
        site_data_text = site_data_js.read_text(encoding="utf-8")
        for marker in ("window.POLYGLOT_CONCEPTS =", "window.POLYGLOT_SEARCH_INDEX ="):
            if marker not in site_data_text:
                errors.append(f"generated site data JS missing {marker}")
        if len(data["topics"]) and "window.POLYGLOT_SEARCH_INDEX = [" not in site_data_text:
            errors.append("generated search index is empty")

    for label, page in {"home": OUT / "index.html", "compare": OUT / "compare" / "index.html"}.items():
        if not page.exists():
            errors.append(f"{label}: missing generated page")
            continue
        text = page.read_text(encoding="utf-8")
        if 'id="theme-toggle"' not in text:
            errors.append(f"{label}: missing theme toggle markup")
        if 'class="language-menu"' not in text:
            errors.append(f"{label}: missing language dropdown markup")
        if label == "compare" and 'compare-toc' not in text:
            errors.append("compare: missing compare TOC markup")

    if errors:
        print("FAIL parity validation")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("OK   staging parity validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
