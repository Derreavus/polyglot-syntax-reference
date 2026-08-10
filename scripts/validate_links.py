#!/usr/bin/env python3
"""Validate internal links across the static site.

Checks:
  - Every href that points to a local .html path resolves to a real file
  - Every fragment (#id) referenced on the same page (or target page) exists
  - Language nav links, compare links, and sidebar anchors

Run from repo root:
    python3 scripts/validate_links.py

Exit code 0 = OK, 1 = problems found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

from language_registry import language_slugs

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PAGES = ["index.html", "compare/index.html"] + [f"{slug}/index.html" for slug in language_slugs()]


def collect_html_files() -> list[Path]:
    return sorted(ROOT.rglob("*.html"))


def extract_ids(html: str) -> set[str]:
    ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', html))
    ids.update(re.findall(r'\bname=["\']([^"\']+)["\']', html))
    return ids


def extract_hrefs(html: str) -> list[str]:
    return re.findall(r'\bhref=["\']([^"\']+)["\']', html)


def resolve_target(page: Path, href: str) -> tuple[Path | None, str | None]:
    href = href.strip()
    if not href or href.startswith(("http://", "https://", "mailto:", "javascript:", "data:")):
        return None, None
    if href.startswith("//"):
        return None, None

    parsed = urlparse(href)
    frag = unquote(parsed.fragment) if parsed.fragment else None
    path = unquote(parsed.path)

    if not path:
        return page, frag

    target = (page.parent / path).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        return target, frag

    return target, frag


def main() -> int:
    errors: list[str] = []

    for req in REQUIRED_PAGES:
        if not (ROOT / req).exists():
            errors.append(f"required page missing: {req}")

    pages = collect_html_files()
    id_cache: dict[Path, set[str]] = {}

    for page in pages:
        html = page.read_text(encoding="utf-8")
        id_cache[page.resolve()] = extract_ids(html)

    for page in pages:
        rel = page.relative_to(ROOT)
        html = page.read_text(encoding="utf-8")
        for href in extract_hrefs(html):
            target, frag = resolve_target(page, href)
            if target is None and frag is None:
                continue

            if target is not None and target.is_dir():
                index = target / "index.html"
                if index.exists():
                    target = index
                else:
                    errors.append(f"{rel}: broken dir link href={href!r}")
                    continue

            if target is not None:
                if not target.exists():
                    errors.append(f"{rel}: broken file link href={href!r}")
                    continue

            if frag:
                key = (target or page).resolve()
                ids = id_cache.get(key)
                if ids is None and key.exists() and key.suffix.lower() in (".html", ".htm"):
                    ids = extract_ids(key.read_text(encoding="utf-8"))
                    id_cache[key] = ids
                if ids is not None and frag not in ids:
                    errors.append(f"{rel}: missing fragment #{frag} (from href={href!r})")

    for asset in ("css/style.css", "js/main.js"):
        if not (ROOT / asset).exists():
            errors.append(f"required asset missing: {asset}")

    if errors:
        print("FAIL links:")
        for e in errors:
            print(f"  - {e}")
        print(f"\n{len(errors)} problem(s) found")
        return 1

    print(f"OK   links ({len(pages)} HTML pages checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
