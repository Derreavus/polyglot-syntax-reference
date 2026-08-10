#!/usr/bin/env python3
"""Lightweight HTML smoke checks (no external deps).

- every .html file has <html, <head, <body
- no PLACEHOLDER pages
- balanced-ish critical tags
- charset declared

Run from repo root:
    python3 scripts/validate_html_smoke.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_file(path: Path) -> list[str]:
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8", errors="replace")
    errors = []

    if "PLACEHOLDER" in text and path.name == "index.html":
        errors.append(f"{rel}: contains PLACEHOLDER")

    low = text.lower()
    for tag in ("<!doctype html", "<html", "<head", "<body"):
        if tag not in low:
            errors.append(f"{rel}: missing {tag}")

    if "charset" not in low:
        errors.append(f"{rel}: missing charset declaration")

    for tag in ("div", "section", "table", "tr", "td", "ul", "ol", "li"):
        opens = len(re.findall(rf"<{tag}\b", low))
        closes = len(re.findall(rf"</{tag}>", low))
        if opens != closes and opens > 0:
            errors.append(f"{rel}: unbalanced <{tag}> ({opens} open / {closes} close)")

    return errors


def main() -> int:
    errors: list[str] = []
    pages = sorted(ROOT.rglob("*.html"))
    if not pages:
        print("FAIL: no HTML files found")
        return 1

    for p in pages:
        errors.extend(check_file(p))

    if errors:
        print("FAIL html smoke:")
        for e in errors:
            print(f"  - {e}")
        print(f"\n{len(errors)} problem(s) found")
        return 1

    print(f"OK   html smoke ({len(pages)} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
