#!/usr/bin/env python3
"""Validate language HTML pages for common correctness issues.

Run from repo root:
    python3 scripts/validate_syntax_html.py

Exit code 0 = OK, 1 = problems found.
"""

from __future__ import annotations

import html as html_lib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("python", "rust", "cpp", "csharp")

UNICODE_SUBSTITUTES = {
    "\u27e8": "<",  # ⟨
    "\u27e9": ">",  # ⟩
    "\uff1c": "<",  # ＜
    "\uff1e": ">",  # ＞
    "≤": "<=",
    "≥": ">=",
    "→": "->",
    "⇒": "=>",
    "⇐": "<=",
}

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
    (r"\bstd::vector\s*>", "C++: vector> looks like stripped generic"),
    (r"\bstd::optional\s*>", "C++: optional> looks like stripped generic"),
    (r"\bstd::variant\s*>", "C++: variant> looks like stripped generic"),
    (r"\bstd::expected\s*>", "C++: expected> looks like stripped generic"),
    (r"\bstd::span\s*>", "C++: span> looks like stripped generic"),
    (r"parse::\(\)", "Rust: parse::() missing type argument"),
    (r"collect::\(\)", "Rust: collect::() missing type argument"),
    (r"make_unique\s*\(\s*\d", "C++: make_unique(42) should include type argument"),
    (r"dynamic_cast\s*\(\s*\w", "C++: dynamic_cast(ptr) should include type argument"),
    (r"template\s*\n\s*T\s+\w+\s*\(", "C++: template parameter list appears stripped"),
    (r"class Box\s+where\b", "C#: Box<T> type parameter appears stripped"),
]


def decode_entities(s: str) -> str:
    out = html_lib.unescape(s)
    for bad, good in UNICODE_SUBSTITUTES.items():
        out = out.replace(bad, good)
    return out


def code_blocks(html_text: str) -> list[str]:
    return re.findall(r"<pre\s*>\s*<code[^>]*>(.*?)</code>\s*</pre>", html_text, flags=re.S)


def find_raw_angles(block: str) -> list[str]:
    """Return raw angle bracket fragments that would be interpreted as HTML tags."""
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


def has_escaped_generic(html_text: str, *needles: str) -> bool:
    for n in needles:
        if n in html_text:
            return True
        ent = html_lib.escape(n, quote=False)
        if ent in html_text:
            return True
        for bad, good in UNICODE_SUBSTITUTES.items():
            math = n.replace("<", bad).replace(">", good if bad in ("\u27e8", "\u27e9") else ">")
            if math in html_text:
                return True
    return False


def expected_generics_present(lang: str, html_text: str) -> list[str]:
    checks = {
        "cpp": [
            "template<typename T>",
            "make_unique<",
            "vector<",
            "static_cast<",
        ],
        "rust": [
            "Vec<",
            "Option<",
            "Result<",
        ],
        "csharp": [
            "List<",
            "<T>",
        ],
        "python": [
            "list[int]",
            "TypeVar",
        ],
    }
    missing = []
    for needle in checks.get(lang, []):
        if needle not in html_text and html_lib.escape(needle, quote=False) not in html_text:
            missing.append(needle)
    return missing


def validate_structure(lang: str, html_text: str) -> list[str]:
    errors = []
    if not re.search(r'class="lang-tag', html_text):
        errors.append(f"{lang}: missing lang-tag version badge")
    if not re.search(r'class="sidebar"', html_text):
        errors.append(f"{lang}: missing sidebar")
    if not re.search(r"<h1>", html_text):
        errors.append(f"{lang}: missing h1")
    topics = re.findall(r'class="topic"', html_text)
    if len(topics) < 5:
        errors.append(f"{lang}: fewer than 5 topic sections ({len(topics)})")
    return errors


def validate_lang(lang: str) -> list[str]:
    path = ROOT / lang / "index.html"
    errors: list[str] = []
    if not path.exists():
        return [f"{lang}/index.html missing"]

    html_text = path.read_text(encoding="utf-8")
    blocks = code_blocks(html_text)
    if not blocks:
        errors.append(f"{lang}: no <pre><code> blocks found")

    for i, block in enumerate(blocks):
        decoded = decode_entities(block)
        for pat, msg in BROKEN_PATTERNS:
            if re.search(pat, decoded):
                errors.append(f"{lang} block {i}: {msg}")
        if any(ch in decoded for ch in UNICODE_SUBSTITUTES):
            for ch in UNICODE_SUBSTITUTES:
                if ch in decoded:
                    errors.append(f"{lang} block {i}: forbidden Unicode syntax substitute detected: {ch!r}")
        for ctx in find_raw_angles(block):
            errors.append(f"{lang} block {i}: raw angle bracket tag — {ctx}")
        if re.search(r"(?<!&)<|>", block):
            errors.append(f"{lang} block {i}: raw < or > found in code block; use HTML entities")

    for pat in expected_generics_present(lang, html_text):
        errors.append(f"{lang}: expected generic pattern not found: {pat}")

    errors.extend(validate_structure(lang, html_text))
    return errors


def validate_compare() -> list[str]:
    path = ROOT / "compare" / "index.html"
    if not path.exists():
        return ["compare/index.html missing"]
    html_text = path.read_text(encoding="utf-8")
    errors = []
    for sec in ("basics", "collections", "oop", "ownership", "errors", "async"):
        if f'id="{sec}"' not in html_text:
            errors.append(f"compare: missing section #{sec}")
    if re.search(r"<code>Vec<T></code>", html_text):
        errors.append("compare: raw Vec<T> will be stripped by browsers")
    if re.search(r"<code><T></code>", html_text):
        errors.append("compare: raw <T> will be stripped by browsers")
    if re.search(r"<code>List<T></code>", html_text):
        errors.append("compare: raw List<T> will be stripped by browsers")
    for ch in ("\u27e8", "\u27e9", "\uff1c", "\uff1e", "≤", "≥", "→", "⇒", "⇐"):
        if ch in html_text:
            errors.append(f"compare: forbidden Unicode syntax substitute present: {ch!r}")
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
