from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Any

from versioning import has_versioning


TABLE_PATTERN = re.compile(r"<table\b.*?</table>", re.DOTALL)


def wrap_tables(body_html: str) -> str:
    """Give each content table its own horizontal scroller so wide tables never widen the page."""
    return TABLE_PATTERN.sub(lambda match: f'<div class="table-scroll scroll-fade">{match.group(0)}</div>', body_html)


def relative_asset_path(page_rel: str, target_rel: str) -> str:
    return os.path.relpath(target_rel, start=str(Path(page_rel).parent)).replace('\\', '/')


def render_language_page(language: dict[str, Any], data: dict[str, Any], page_rel: str) -> str:
    site = data["site"]
    sections = [
        section for section in data.get("sections", []) if section.get("language") == language["slug"]
    ]
    sections.sort(key=lambda item: int(item.get("sort_order", 0)))

    topics = [
        topic for topic in data.get("topics", []) if topic.get("language") == language["slug"]
    ]
    topics.sort(key=lambda item: int(item.get("sort_order", 0)))

    topics_by_section: dict[str, list[dict[str, Any]]] = {}
    for topic in topics:
        key = topic.get("section")
        topics_by_section.setdefault(key, []).append(topic)

    history_link_html = (
        '<a class="version-history-link" href="versions/index.html">Version history: what changed between releases \u2192</a>'
        if has_versioning(data, language["slug"])
        else ""
    )

    css_path = relative_asset_path(page_rel, "css/style.css")
    js_path = relative_asset_path(page_rel, "js/site-data.js")
    main_js_path = relative_asset_path(page_rel, "js/main.js")

    sidebar_parts: list[str] = []
    for section in sections:
        slug = section.get("slug")
        group = topics_by_section.get(slug, [])
        sidebar_parts.append(f'<h3>{html.escape(section.get("title", ""))}</h3>')
        for topic in group:
            href = f'#{topic.get("slug")}'
            sidebar_parts.append(f'<a href="{href}">{html.escape(topic.get("title", ""))}</a>')

    topic_html: list[str] = []
    for topic in topics:
        content_html = topic.get("content_html")
        if content_html:
            body_html = wrap_tables(content_html)
        else:
            examples = [
                example for example in data.get("examples", [])
                if example.get("language") == language["slug"] and example.get("topic") == topic.get("slug")
            ]
            code_blocks = "\n".join(
                f'<pre><code>{html.escape(example.get("code", ""))}</code></pre>'
                for example in examples
            )
            body_html = (
                f'<p>{html.escape(topic.get("summary", ""))}</p>'
                f'{code_blocks}'
            )
        topic_html.append(
            f'<section class="topic" id="{html.escape(topic.get("slug", ""))}">'
            f'<h2>{html.escape(topic.get("title", ""))}</h2>'
            f'{body_html}'
            f'</section>'
        )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(language["name"]) } — {html.escape(site["brand"])}</title>
  <script>document.documentElement.classList.add("js");</script>
  <link rel="stylesheet" href="{css_path}">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a href="{relative_asset_path(page_rel, 'index.html')}" class="logo"><span class="logo-mark">{{ }}</span><span class="logo-text">{html.escape(site["brand_short"])}</span></a>
      <nav class="lang-nav" aria-label="Language navigation">
        <details class="language-menu">
          <summary class="language-menu-toggle" aria-label="Choose a language">
            <span>{html.escape(language["name"])}</span><span class="language-menu-chevron" aria-hidden="true"></span>
          </summary>
          <div class="language-menu-panel" aria-label="Available languages"></div>
        </details>
      </nav>
      <a href="{relative_asset_path(page_rel, 'compare/index.html')}" class="lang-btn" style="color: var(--accent); border: 1px solid var(--accent);">Compare</a>
      <button id="theme-toggle" class="theme-btn" aria-label="Toggle theme">☾</button>
    </div>
  </header>

  <div class="lang-layout container">
    <aside class="sidebar" id="sections-drawer" aria-label="Sections">
      <div class="drawer-head">
        <h2 class="drawer-title">Sections</h2>
        <button type="button" class="drawer-close" aria-label="Close sections menu">&times;</button>
      </div>
      <div class="sidebar-scroll scroll-fade">
        {' '.join(sidebar_parts)}
      </div>
    </aside>

    <article class="content">
      <h1>{html.escape(language["name"]) } Syntax Reference</h1>
      <span class="lang-tag {html.escape(language["slug"])}">{html.escape(language.get("version_label", ""))}</span>
      {history_link_html}
      {' '.join(topic_html)}
    </article>
  </div>

  <script src="{js_path}"></script>
  <script src="{main_js_path}"></script>
</body>
</html>
'''
