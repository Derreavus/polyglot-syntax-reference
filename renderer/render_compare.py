from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any


def relative_asset_path(page_rel: str, target_rel: str) -> str:
    return os.path.relpath(target_rel, start=str(Path(page_rel).parent)).replace('\\', '/')


def render_compare_page(data: dict[str, Any], page_rel: str = "compare/index.html") -> str:
    languages = sorted(data.get("languages", []), key=lambda item: int(item.get("order", 0)))
    rows = data.get("compare", [])
    compare_sections = data["compare_sections"]
    site = data["site"]
    max_lanes = int(site.get("compare_max_languages", 4))
    css_path = relative_asset_path(page_rel, "css/style.css")
    js_path = relative_asset_path(page_rel, "js/site-data.js")
    main_js_path = relative_asset_path(page_rel, "js/main.js")

    def render_rows(section_rows: list[dict[str, Any]]) -> str:
        return "\n".join(
            '<tr role="row">'
            + f'<td class="concept" role="rowheader">{html.escape(row.get("label", ""))}</td>'
            + "".join(
                f'<td role="cell" data-language="{html.escape(lang["slug"], quote=True)}" hidden>'
                f'<code>{html.escape(row.get(lang["slug"], ""))}</code></td>'
                for lang in languages
            )
            + '</tr>'
            for row in section_rows
        )

    def matching_rows(section: dict[str, Any]) -> list[dict[str, Any]]:
        concept_filter = section.get("concepts")
        if concept_filter is None:
            return rows
        return [row for row in rows if row.get("concept") in set(concept_filter)]

    sections_html = "\n".join(
        f'<section class="compare-section" id="{html.escape(section["slug"])}" hidden>'
        + f'<h2>{html.escape(section["title"])}</h2>'
        + f'<table class="compare-table" role="table" aria-label="{html.escape(section["title"], quote=True)}">'
        + '<thead class="sr-only" role="rowgroup"><tr role="row"><th role="columnheader">Concept</th>'
        + "".join(
            f'<th role="columnheader" data-language="{html.escape(lang["slug"], quote=True)}" hidden>'
            f'{html.escape(lang["name"])}</th>'
            for lang in languages
        )
        + '</tr></thead>'
        + f'<tbody role="rowgroup">{render_rows(matching_rows(section))}</tbody></table></section>'
        for section in compare_sections
    )

    toc_html = "\n".join(
        f'<a href="#{html.escape(section["slug"])}">{html.escape(section["title"])}</a>'
        for section in compare_sections
    )
    page_title = site["compare_title"]
    page_description = site["compare_description"]

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(page_title)} — {html.escape(site["brand"])}</title>
  <meta name="description" content="{html.escape(page_description, quote=True)}">
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
            <span>Languages</span><span class="language-menu-chevron" aria-hidden="true"></span>
          </summary>
          <div class="language-menu-panel" aria-label="Available languages"></div>
        </details>
      </nav>
      <a href="{relative_asset_path(page_rel, 'index.html')}" class="lang-btn" style="color: var(--accent); border: 1px solid var(--accent);">Home</a>
      <button id="theme-toggle" class="theme-btn" aria-label="Toggle theme">☾</button>
    </div>
  </header>

  <main class="container compare-main">
    <div class="compare-hero">
      <h1>{html.escape(site["compare_heading"])}</h1>
      <p id="compare-language-summary">{html.escape(site["compare_intro"])}</p>
    </div>

    <nav class="compare-toc" aria-label="Comparison sections">
      {toc_html}
    </nav>

    <div class="compare-board" id="compare-board" data-max-lanes="{max_lanes}" style="--lanes: 1;">
      <div class="compare-board-inner">
        <div class="lane-bar" id="lane-bar" role="group" aria-label="Languages being compared">
          <div class="lane-add-wrap">
            <button type="button" id="lane-add" class="lane-add" aria-haspopup="menu" aria-expanded="false" aria-controls="lane-menu">
              <span class="lane-add-icon" aria-hidden="true">+</span>
              <span id="lane-add-label">Add language</span>
            </button>
            <div id="lane-menu" class="lane-menu" role="menu" aria-label="Available languages" hidden></div>
          </div>
        </div>

        <p id="compare-empty-state" class="compare-empty-state">Use <strong>Add language</strong> to pick up to {max_lanes} languages and compare them side by side.</p>
        <noscript><p class="compare-empty-state">The comparison view needs JavaScript to choose languages.</p></noscript>

        {sections_html}
      </div>
    </div>
    <p id="compare-status" class="sr-only" role="status" aria-live="polite"></p>
  </main>

  <script src="{js_path}"></script>
  <script src="{main_js_path}"></script>
</body>
</html>
'''
