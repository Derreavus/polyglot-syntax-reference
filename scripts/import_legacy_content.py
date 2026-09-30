#!/usr/bin/env python3
"""Import full topic markup from a pre-migration site revision into site_data.json."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "site_data.json"
LANGUAGE_SLUGS = ("python", "rust", "cpp", "csharp")


def read_revision_page(revision: str, language: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{revision}:{language}/index.html"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )


def plain_text(markup: str) -> str:
    return html.unescape(re.sub(r"<[^>]*>", "", markup)).strip()


def section_groups(page: str, language: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    sidebar = re.search(r'<aside class="sidebar">(.*?)</aside>', page, re.DOTALL)
    if not sidebar:
        raise ValueError(f"{language}: legacy page has no sidebar")

    groups: list[dict[str, Any]] = []
    topic_sections: dict[str, str] = {}
    headings = list(re.finditer(r"<h3>(.*?)</h3>", sidebar.group(1), re.DOTALL))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(sidebar.group(1))
        title = plain_text(heading.group(1))
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        groups.append({
            "language": language,
            "slug": slug,
            "title": title,
            "sort_order": index + 1,
        })
        group_markup = sidebar.group(1)[heading.end():end]
        for topic_slug in re.findall(r'href="#([^"]+)"', group_markup):
            if topic_slug in topic_sections:
                raise ValueError(f"{language}: duplicate sidebar topic #{topic_slug}")
            topic_sections[topic_slug] = slug
    if not groups:
        raise ValueError(f"{language}: legacy page has no sidebar section headings")
    return groups, topic_sections


def extract_topics(page: str, language: str, topic_sections: dict[str, str],
                   previous_topics: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    topic_matches = list(re.finditer(
        r'<section class="topic" id="([^"]+)">(.*?)</section>',
        page,
        re.DOTALL,
    ))
    actual_topic_count = len(re.findall(r'<section class="topic" id="', page))
    if len(topic_matches) != actual_topic_count:
        raise ValueError(f"{language}: topic section extraction was incomplete")

    topics: list[dict[str, Any]] = []
    for order, match in enumerate(topic_matches, start=1):
        slug, inner_html = match.groups()
        section = topic_sections.get(slug)
        if section is None:
            raise ValueError(f"{language}#{slug}: topic is not listed in a sidebar section")
        heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", inner_html, re.DOTALL)
        if not heading:
            raise ValueError(f"{language}#{slug}: topic has no h2 title")
        title = plain_text(heading.group(1))
        content_html = inner_html[:heading.start()] + inner_html[heading.end():]
        content_html = content_html.strip()
        if not content_html:
            raise ValueError(f"{language}#{slug}: topic has no content")

        topic: dict[str, Any] = {
            "language": language,
            "section": section,
            "slug": slug,
            "title": title,
            "concept": None,
            "sort_order": order,
            "content_html": content_html,
        }
        previous = previous_topics.get((language, slug), {})
        if previous.get("concept") is not None:
            topic["concept"] = previous["concept"]
        for key in ("search_title", "search_keywords"):
            if key in previous:
                topic[key] = previous[key]
        topics.append(topic)
    if not topics:
        raise ValueError(f"{language}: legacy page has no topic sections")
    return topics


def import_content(revision: str) -> dict[str, Any]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    previous_topics = {
        (topic["language"], topic["slug"]): topic
        for topic in data.get("topics", [])
    }
    sections: list[dict[str, Any]] = []
    topics: list[dict[str, Any]] = []
    for language in LANGUAGE_SLUGS:
        page = read_revision_page(revision, language)
        language_sections, topic_section_map = section_groups(page, language)
        language_topics = extract_topics(page, language, topic_section_map, previous_topics)
        sections.extend(language_sections)
        topics.extend(language_topics)
        print(f"{language}: imported {len(language_topics)} topics across {len(language_sections)} sections")
    data["sections"] = sections
    data["topics"] = topics
    data["content_source_revision"] = revision
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-ref",
        required=True,
        help="Git revision containing the complete pre-migration language pages",
    )
    args = parser.parse_args()
    data = import_content(args.source_ref)
    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Updated {DATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
