#!/usr/bin/env python3
"""Validate language HTML pages for common correctness issues.

Run from repo root:
    python3 scripts/validate_syntax_html.py

Exit code 0 = OK, 1 = problems found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("python", "rust", "cpp", "csharp")

# Patterns that strongly suggest stripped or broken generics
BROKEN_PATTERNS = [
    (r"\bVec\s*>", "Rust: Vec> looks like stripped generic"),
    (r"\bOption\s*>", "Rust: Option> looks like stripped generic"),
    (r"\bResult\s*>", "Rust: Result> looks like stripped generic"),
    (r"\bHashMap\s*>", "Rust: HashMap> looks like stripped generic"),
    (r"\bBox\s*>", "Rust: Box> looks like stripped generic"),
    (r"\bList\s*>", "C#: List> looks like stripped generic"),
    (r"\bIEnumerable\s*>", "C#: IEnumerable> looks like stripped generic"),
    (r"\bTask\s*>", "C#: Task> looks like stripped generic"),
    (r"\bDictionary\s*>", "C#: Dictionary> looks like stripped generic"),
    (r"parse::\(\)", "Rust: parse::() missing type argument"),
    (r"collect::\(\)", "Rust: collect::() missing type argument"),
    (r"make_unique\s*\(\s*\d", "C++: make_unique(42) should be make_unique<T>(42)"),
    (r"dynamic_cast\s*\(\s*\w", "C++: dynamic_cast(ptr) should include type argument"),
    (r"template\s*\n\s*T\s+\w+\s*\(", "C++: template parameter list appears stripped"),
    (r"class Box\s+where\b", "C#: Box<T> type parameter appears stripped"),
]


def decode_entities(s: str) -> str:
    return (
        s.replace("<", "<")
        .replace(">", ">")
        .replace("&", "&")
        .replace(""", '"')
        .replace("&#39;", "'")
    )


def code_blocks(html: str) -> list[str]:
    return re.findall(r"<pre><code>(.*?)</code></pre>", html, flags=re.S)


def find_raw_angles(block: str) -> list[str]:
    """Return contexts of raw < or > that are not HTML entities."""
    issues = []
    for m in re.finditer(r"<|>", block):
        start = m.start()
        before = block[max(0, start - 4) : start + 1]
        if before.endswith("<") or before.endswith(">") or before.endswith("&"):
            continue
        ch = m.group(0)
        after = block[start : start + 12]
        if ch == "<" and re.match(r"<[A-Za-z_/!]", after):
            issues.append(after.split("\n")[0][:40])
        elif ch == "<":
            ctx = block[max(0, start - 8) : start + 8].replace("\n", " ")
            issues.append(f"unescaped < near: {ctx!r}")
    return issues


def expected_generics_present(lang: str, html: str) -> list[str]:
    """Ensure languages that need generics actually contain escaped examples."""
    missing = []
    checks = {
        "cpp": [r"template<typename T>", r"make_unique<", r"vector<", r"static_cast<"],
        "rust": [r"Vec<", r"Option<", r"<i32>", r"parse::<"],
        "csharp": [r"List<", r"<T>", r"IEnumerable<"],
        "python": [r"list\[int\]", r"TypeVar", r"Sequence\["],
    }
    for pat in checks.get(lang, []):
        if not re.search(pat, html):
            missing.append(pat)
    return missing


def validate_lang(lang: str) -> list[str]:
    path = ROOT / lang / "index.html"
    errors: list[str] = []
    if not path.exists():
        return [f"{lang}/index.html missing"]

    html = path.read_text(encoding="utf-8")
    blocks = code_blocks(html)
    if not blocks:
        errors.append(f"{lang}: no <pre><code> blocks found")

    for i, block in enumerate(blocks):
        plain = decode_entities(block)
        for pat, msg in BROKEN_PATTERNS:
            if re.search(pat, plain):
                errors.append(f"{lang} block {i}: {msg}")

        for ctx in find_raw_angles(block):
            errors.append(f"{lang} block {i}: raw angle bracket — {ctx}")

    for pat in expected_generics_present(lang, html):
        errors.append(f"{lang}: expected pattern not found: {pat}")

    if not re.search(r'class="lang-tag', html):
        errors.append(f"{lang}: missing lang-tag version badge")

    return errors


def main() -> int:
    all_errors: list[str] = []
    for lang in LANGS:
        errs = validate_lang(lang)
        if errs:
            print(f"FAIL {lang}:")
            for e in errs:
                print(f"  - {e}")
            all_errors.extend(errs)
        else:
            print(f"OK   {lang}")

    if all_errors:
        print(f"\n{len(all_errors)} problem(s) found")
        return 1
    print("\nAll language pages passed validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
