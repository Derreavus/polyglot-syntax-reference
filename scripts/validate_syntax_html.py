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

MATH_LT = "\u27e8"  # ⟨
MATH_GT = "\u27e9"  # ⟩
FULL_LT = "\uff1c"  # ＜
FULL_GT = "\uff1e"  # ＞

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
        .replace("&#60;", "<")
        .replace("&#62;", ">")
        .replace("&", "&")
        .replace(""", '"')
        .replace("&#39;", "'")
        .replace(MATH_LT, "<")
        .replace(MATH_GT, ">")
        .replace(FULL_LT, "<")
        .replace(FULL_GT, ">")
    )


def code_blocks(html: str) -> list[str]:
    return re.findall(r"<pre><code>(.*?)</code></pre>", html, flags=re.S)


def find_raw_angles(block: str) -> list[str]:
    """Return contexts of raw ASCII < that look like HTML tags (dangerous)."""
    issues = []
    for m in re.finditer(r"<", block):
        start = m.start()
        before = block[max(0, start - 6) : start + 1]
        if re.search(r"&(amp;|lt;|#60;)$", before):
            continue
        after = block[start : start + 16]
        if re.match(r"</?[A-Za-z_!]", after):
            issues.append(after.split("\n")[0][:40])
    return issues


def has_escaped_generic(html: str, *needles: str) -> bool:
    for n in needles:
        if n in html:
            return True
        ent = n.replace("<", "<").replace(">", ">")
        if ent in html:
            return True
        num = n.replace("<", "&#60;").replace(">", "&#62;")
        if num in html:
            return True
        math = n.replace("<", MATH_LT).replace(">", MATH_GT)
        if math in html:
            return True
        full = n.replace("<", FULL_LT).replace(">", FULL_GT)
        if full in html:
            return True
        sq = n.replace("<", "[").replace(">", "]")
        if sq in html and sq != n:
            return True
    return False


def expected_generics_present(lang: str, html: str) -> list[str]:
    missing = []
    checks = {
        "cpp": [
            ("template<typename T>", "template<typename T>"),
            ("make_unique<", "make_unique<"),
            ("vector<", "vector<"),
            ("static_cast<", "static_cast<"),
        ],
        "rust": [
            ("Vec<", "Vec<"),
            ("Option<", "Option<"),
            ("Result<", "Result<"),
        ],
        "csharp": [
            ("List<", "List<"),
            ("<T>", "<T>"),
        ],
        "python": [
            ("list[int]", "list[int]"),
            ("TypeVar", "TypeVar"),
        ],
    }
    for pair in checks.get(lang, []):
        if not has_escaped_generic(html, *pair):
            missing.append(pair[0])
    return missing


def validate_structure(lang: str, html: str) -> list[str]:
    errors = []
    if not re.search(r'class="lang-tag', html):
        errors.append(f"{lang}: missing lang-tag version badge")
    if not re.search(r'class="sidebar"', html):
        errors.append(f"{lang}: missing sidebar")
    if not re.search(r"<h1>", html):
        errors.append(f"{lang}: missing h1")
    topics = re.findall(r'class="topic"', html)
    if len(topics) < 5:
        errors.append(f"{lang}: fewer than 5 topic sections ({len(topics)})")
    return errors


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
            errors.append(f"{lang} block {i}: raw angle bracket tag — {ctx}")

    for pat in expected_generics_present(lang, html):
        errors.append(f"{lang}: expected generic pattern not found: {pat}")

    errors.extend(validate_structure(lang, html))
    return errors


def validate_compare() -> list[str]:
    path = ROOT / "compare" / "index.html"
    if not path.exists():
        return ["compare/index.html missing"]
    html = path.read_text(encoding="utf-8")
    errors = []
    for sec in ("basics", "collections", "oop", "ownership", "errors", "async"):
        if f'id="{sec}"' not in html:
            errors.append(f"compare: missing section #{sec}")
    if re.search(r"<code>Vec<T></code>", html):
        errors.append("compare: raw Vec<T> will be stripped by browsers")
    if re.search(r"<code><T></code>", html):
        errors.append("compare: raw <T> will be stripped by browsers")
    if re.search(r"<code>List<T></code>", html):
        errors.append("compare: raw List<T> will be stripped by browsers")
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

    cmp_errs = validate_compare()
    if cmp_errs:
        print("FAIL compare:")
        for e in cmp_errs:
            print(f"  - {e}")
        all_errors.extend(cmp_errs)
    else:
        print("OK   compare")

    if all_errors:
        print(f"\n{len(all_errors)} problem(s) found")
        return 1
    print("\nAll pages passed validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
