from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Any

from versioning import features_for, has_versioning, lifecycle_facts, short_label, version_orders, versions_for


TABLE_PATTERN = re.compile(r"<table\b.*?</table>", re.DOTALL)


def wrap_tables(body_html: str) -> str:
    """Give each content table its own horizontal scroller so wide tables never widen the page."""
    return TABLE_PATTERN.sub(lambda match: f'<div class="table-scroll scroll-fade">{match.group(0)}</div>', body_html)


def version_notes_html(topic_slug: str, features: list[dict[str, Any]], versions_by_id: dict[str, dict[str, Any]], orders: dict[str, int]) -> str:
    """A collapsed "Version notes" list for the features that belong to a topic."""
    items = [f for f in features if f.get("topic") == topic_slug]
    if not items:
        return ""
    items.sort(key=lambda f: (orders[f["history"][0]["version"]], f["title"].lower()))
    rows: list[str] = []
    legacy = 0
    for feature in items:
        facts = lifecycle_facts(feature, versions_by_id)
        added = facts["added"]
        draft = " vn-draft" if added["status"] == "draft" else ""
        since = f"Draft in {short_label(added)}" if added["status"] == "draft" else f"Since {short_label(added)}"
        chips = [f'<span class="vn-since{draft}">{html.escape(since)}</span>']
        if facts["deprecated"] is not None:
            legacy += 1
            if facts["deprecated_version"] is None:
                chips.append('<span class="vn-status vn-deprecated">Legacy</span>')
            else:
                chips.append(f'<span class="vn-status vn-deprecated">Deprecated in {html.escape(short_label(facts["deprecated_version"]))}</span>')
        if facts["removed"] is not None:
            scope = facts["removed"].get("scope")
            where = f" ({html.escape(scope)})" if scope else ""
            word = "Restricted" if scope else "Removed"
            chips.append(f'<span class="vn-status vn-removed">{word} in {html.escape(short_label(facts["removed_version"]))}{where}</span>')
        if facts["changed_versions"]:
            names = ", ".join(short_label(v) for v in facts["changed_versions"])
            chips.append(f'<span class="vn-status vn-changed">Changed in {html.escape(names)}</span>')
        rows.append(
            f'<li><a href="versions/index.html#feature-{html.escape(feature["slug"])}">{html.escape(feature["title"])}</a>'
            f'<span class="vn-chips">{"".join(chips)}</span></li>'
        )
    first, last = items[0]["history"][0]["version"], max(items, key=lambda f: orders[f["history"][0]["version"]])["history"][0]["version"]
    span = short_label(versions_by_id[first]) if first == last else f"{short_label(versions_by_id[first])} to {short_label(versions_by_id[last])}"
    flag = f' <span class="vn-flag">{legacy} legacy</span>' if legacy else ""
    count = f"{len(items)} feature" + ("" if len(items) == 1 else "s")
    return (
        '<details class="version-notes"><summary>Version notes '
        f'<span class="vn-meta">{count}, {html.escape(span)}</span>{flag}</summary>'
        f'<ul class="vn-list">{"".join(rows)}</ul></details>'
    )


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

    versioned = has_versioning(data, language["slug"])
    all_versions = versions_for(data, language["slug"]) if versioned else []
    versions_by_id = {v["id"]: v for v in all_versions}
    version_order_map = version_orders(all_versions)
    language_features = features_for(data, language["slug"]) if versioned else []

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
            f'{version_notes_html(topic.get("slug", ""), language_features, versions_by_id, version_order_map) if versioned else ""}'
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
