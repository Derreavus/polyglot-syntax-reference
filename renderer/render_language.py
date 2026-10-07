from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Any

from theme import language_theme_style

from versioning import features_for, has_versioning, lifecycle_facts, release_text, short_label, track_page_rel, tracks_for, version_orders, versions_for


TABLE_PATTERN = re.compile(r"<table\b.*?</table>", re.DOTALL)


def wrap_tables(body_html: str) -> str:
    """Give each content table its own horizontal scroller so wide tables never widen the page."""
    return TABLE_PATTERN.sub(lambda match: f'<div class="table-scroll scroll-fade">{match.group(0)}</div>', body_html)


def _since_text(track: dict[str, Any], version: dict[str, Any], event: dict[str, Any]) -> str:
    label = release_text(version, event)
    if track["kind"] != "standard":
        return f"{label}+"
    return f"Draft in {label}" if version["status"] == "draft" else f"Since {label}"


def version_notes_html(topic_slug: str, features: list[dict[str, Any]], tracks: list[dict[str, Any]], versions: dict[str, dict[str, dict[str, Any]]], orders: dict[str, dict[str, int]], href_for) -> str:
    """A collapsed "Version notes" list for the features that belong to a topic, across every track."""
    items = [f for f in features if f.get("topic") == topic_slug]
    if not items:
        return ""
    primary = tracks[0]["id"]

    def sort_key(feature: dict[str, Any]) -> tuple[int, int, str]:
        for rank, track in enumerate(tracks):
            if track["id"] in feature["history"]:
                first = feature["history"][track["id"]][0]["version"]
                return (rank, orders[track["id"]][first], feature["title"].lower())
        return (len(tracks), 0, feature["title"].lower())

    items.sort(key=sort_key)
    rows: list[str] = []
    legacy = 0
    for feature in items:
        chips: list[str] = []
        flagged = False
        for track in tracks:
            if track["id"] not in feature["history"]:
                continue
            facts = lifecycle_facts(feature, track["id"], versions[track["id"]])
            added = facts["added"]
            draft = " vn-draft" if added["status"] == "draft" else ""
            runtime = " vn-runtime" if track["kind"] != "standard" else ""
            target = f'{href_for(track["id"])}#feature-{html.escape(feature["slug"])}'
            chips.append(f'<a class="vn-since{draft}{runtime}" href="{target}">{html.escape(_since_text(track, added, facts["added_event"]))}</a>')
            prefix = f'{track["label"]}: ' if track["id"] != primary else ""
            if facts["deprecated"] is not None:
                flagged = True
                if facts["deprecated_version"] is None:
                    text = "Legacy"
                else:
                    text = f'Deprecated in {short_label(facts["deprecated_version"])}'
                chips.append(f'<span class="vn-status vn-deprecated">{html.escape(prefix + text)}</span>')
            if facts["removed"] is not None:
                flagged = True
                scope = facts["removed"].get("scope")
                where = f" ({scope})" if scope else ""
                word = "Restricted" if scope else "Removed"
                removed_label = short_label(facts["removed_version"])
                text = f"{prefix}{word} in {removed_label}{where}"
                chips.append(f'<span class="vn-status vn-removed">{html.escape(text)}</span>')
            if facts["changed_versions"]:
                names = ", ".join(short_label(v) for v in facts["changed_versions"])
                text = f"{prefix}Changed in {names}"
                chips.append(f'<span class="vn-status vn-changed">{html.escape(text)}</span>')
        legacy += 1 if flagged else 0
        first_track = next(track["id"] for track in tracks if track["id"] in feature["history"])
        rows.append(
            f'<li><a href="{href_for(first_track)}#feature-{html.escape(feature["slug"])}">{html.escape(feature["title"])}</a>'
            f'<span class="vn-chips">{"".join(chips)}</span></li>'
        )
    primary_items = [f for f in items if primary in f["history"]]
    if primary_items:
        firsts = [f["history"][primary][0]["version"] for f in primary_items]
        lo = min(firsts, key=lambda v: orders[primary][v])
        hi = max(firsts, key=lambda v: orders[primary][v])
        span = short_label(versions[primary][lo]) if lo == hi else f"{short_label(versions[primary][lo])} to {short_label(versions[primary][hi])}"
    else:
        span = ""
    flag = f' <span class="vn-flag">{legacy} legacy</span>' if legacy else ""
    count = f"{len(items)} feature" + ("" if len(items) == 1 else "s")
    meta = f"{count}, {html.escape(span)}" if span else count
    return (
        '<details class="version-notes"><summary>Version notes '
        f'<span class="vn-meta">{meta}</span>{flag}</summary>'
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

    history_link_html = ""
    if has_versioning(data, language["slug"]):
        names = " and ".join(track["label"] for track in tracks_for(data, language["slug"]))
        history_link_html = (
            f'<a class="version-history-link" href="versions/index.html">Version history: {html.escape(names)} \u2192</a>'
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
    language_tracks = tracks_for(data, language["slug"]) if versioned else []
    track_versions = {
        track["id"]: {v["id"]: v for v in versions_for(data, language["slug"], track["id"])} for track in language_tracks
    }
    track_orders = {
        track["id"]: version_orders(versions_for(data, language["slug"], track["id"])) for track in language_tracks
    }
    language_features = features_for(data, language["slug"]) if versioned else []

    def href_for(track_id: str) -> str:
        return relative_asset_path(page_rel, track_page_rel(data, language["slug"], track_id))

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
            f'{version_notes_html(topic.get("slug", ""), language_features, language_tracks, track_versions, track_orders, href_for) if versioned else ""}'
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
  {language_theme_style(data)}
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
