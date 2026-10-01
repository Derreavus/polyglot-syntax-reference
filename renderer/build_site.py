from __future__ import annotations

import html
import json
import re
import shutil

from load_data import ROOT, get_languages, load_data
from render_compare import render_compare_page
from render_home import render_home_page
from render_language import render_language_page, wrap_tables
from validate_data import validate_data_model


OUTPUT_ROOT = ROOT / "dist"
STATIC_ROOT = ROOT / "src" / "static"


def clean_output_dir() -> None:
    """Start every build from an empty dist/ so removed pages never linger."""
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)


def ensure_output_dirs() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for lang in get_languages(load_data()):
        (OUTPUT_ROOT / lang["slug"]).mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "compare").mkdir(parents=True, exist_ok=True)


def render_site_data_js(data: dict) -> str:
    languages = get_languages(data)
    concepts = {
        concept["slug"]: concept.get("topics", {})
        for concept in data.get("concepts", [])
    }
    search_index = [
        {
            "lang": topic["language"],
            "id": topic["slug"],
            "title": topic.get("search_title", topic["title"]),
            "keywords": topic.get(
                "search_keywords",
                re.sub(
                    r"\s+",
                    " ",
                    html.unescape(re.sub(r"<[^>]*>", " ", topic["content_html"])),
                ).strip(),
            ),
        }
        for topic in data["topics"]
    ]
    languages_payload = json.dumps(languages, ensure_ascii=True, separators=(",", ":"))
    concepts_payload = json.dumps(concepts, ensure_ascii=True, separators=(",", ":"))
    search_payload = json.dumps(search_index, ensure_ascii=True, separators=(",", ":"))
    js = (
        "(function () {\n"
        "  'use strict';\n"
        f"  window.POLYGLOT_LANGUAGES = {languages_payload};\n"
        "  window.POLYGLOT_LANGUAGES.sort(function (a, b) {\n"
        "    return Number(a.order || 0) - Number(b.order || 0);\n"
        "  });\n"
        f"  window.POLYGLOT_CONCEPTS = {concepts_payload};\n"
        f"  window.POLYGLOT_SEARCH_INDEX = {search_payload};\n"
        "  window.POLYGLOT_LANG_MAP = Object.fromEntries(\n"
        "    window.POLYGLOT_LANGUAGES.map(function (lang) {\n"
        "      return [lang.slug, lang];\n"
        "    })\n"
        "  );\n"
        "  window.POLYGLOT = window.POLYGLOT || {};\n"
        "  window.POLYGLOT.languages = window.POLYGLOT_LANGUAGES;\n"
        "  window.POLYGLOT.concepts = window.POLYGLOT_CONCEPTS;\n"
        "  window.POLYGLOT.searchIndex = window.POLYGLOT_SEARCH_INDEX;\n"
        "})();\n"
    )
    return js


def generate_site_data_js(data: dict) -> None:
    target = OUTPUT_ROOT / "js" / "site-data.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_site_data_js(data), encoding="utf-8", newline="\n")


def copy_static_assets() -> None:
    """Copy every hand-authored file under src/static/ into dist/."""
    for source in sorted(STATIC_ROOT.rglob("*")):
        if not source.is_file():
            continue
        target = OUTPUT_ROOT / source.relative_to(STATIC_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def build_homepage(data: dict) -> None:
    page = render_home_page(data, page_rel="index.html")
    (OUTPUT_ROOT / "index.html").write_text(page, encoding="utf-8", newline="\n")


def build_compare_page(data: dict) -> None:
    page = render_compare_page(data, page_rel="compare/index.html")
    (OUTPUT_ROOT / "compare" / "index.html").write_text(page, encoding="utf-8", newline="\n")


def build_language_pages(data: dict) -> None:
    for language in get_languages(data):
        slug = language["slug"]
        page_path = OUTPUT_ROOT / slug / "index.html"
        page = render_language_page(language, data, page_rel=f"{slug}/index.html")
        page_path.write_text(page, encoding="utf-8", newline="\n")


def validate_generated_site(data: dict) -> None:
    languages = get_languages(data)
    required = {"index.html", "compare/index.html"}
    required.update(f"{lang['slug']}/index.html" for lang in languages)

    missing = [path for path in sorted(required) if not (OUTPUT_ROOT / path).exists()]
    if missing:
        raise FileNotFoundError(f"Missing generated pages: {', '.join(missing)}")

    for lang in languages:
        slug = lang["slug"]
        page_path = OUTPUT_ROOT / slug / "index.html"
        text = page_path.read_text(encoding="utf-8")
        expected_topics = [topic for topic in data["topics"] if topic["language"] == slug]
        expected_ids = {topic["slug"] for topic in expected_topics}
        rendered_ids = set(re.findall(r'<section class="topic" id="([^"]+)"', text))
        if rendered_ids != expected_ids:
            missing_topics = sorted(expected_ids - rendered_ids)
            extra_topics = sorted(rendered_ids - expected_ids)
            raise ValueError(
                f"{slug}: generated topic mismatch; missing={missing_topics}, extra={extra_topics}"
            )
        for topic in expected_topics:
            if wrap_tables(topic["content_html"]) not in text:
                raise ValueError(f"{slug}#{topic['slug']}: full topic content was not rendered")
        if f'id="{slug}"' not in text and f'class="lang-tag {slug}"' not in text:
            raise ValueError(f"{slug}: missing language token in generated page")

    compare_text = (OUTPUT_ROOT / "compare" / "index.html").read_text(encoding="utf-8")
    required_sections = [section["slug"] for section in data["compare_sections"]]
    missing_sections = [section for section in required_sections if f'id="{section}"' not in compare_text]
    if missing_sections:
        raise ValueError(f"compare: missing expected sections: {', '.join(missing_sections)}")

    link_count = len(re.findall(r'href=["\'][^"\']+["\']', compare_text))
    if link_count < 5:
        raise ValueError("compare: page appears incomplete; too few links found")

    js_text = (OUTPUT_ROOT / "js" / "main.js").read_text(encoding="utf-8")
    required_runtime_markers = [
        'const themeBtn = document.getElementById("theme-toggle")',
        'document.getElementById("back-to-top")',
        'document.querySelectorAll("pre")',
        'section.topic[id]',
        "window.POLYGLOT_SEARCH_INDEX",
    ]
    missing_markers = [marker for marker in required_runtime_markers if marker not in js_text]
    if missing_markers:
        raise ValueError(f"runtime parity markers missing from dist JS: {', '.join(missing_markers)}")

    print("OK   built output validation")


def main() -> int:
    data = load_data()
    validate_data_model(data)
    clean_output_dir()
    ensure_output_dirs()
    generate_site_data_js(data)
    copy_static_assets()
    build_homepage(data)
    build_compare_page(data)
    build_language_pages(data)
    validate_generated_site(data)
    print(f"Generated site at {OUTPUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
