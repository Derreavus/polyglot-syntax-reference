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
    css_path = relative_asset_path(page_rel, "css/style.css")
    js_path = relative_asset_path(page_rel, "js/site-data.js")
    main_js_path = relative_asset_path(page_rel, "js/main.js")

    def render_rows(section_rows: list[dict[str, Any]]) -> str:
        return "\n".join(
            '<tr>'
            + f'<td class="concept">{html.escape(row.get("label", ""))}</td>'
            + "".join(
                f'<td data-language="{html.escape(lang["slug"], quote=True)}" hidden>'
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
        f'<section class="compare-section" id="{html.escape(section["slug"])}">'
        + f'<h2>{html.escape(section["title"])}</h2>'
        + '<table class="compare-table" hidden><thead><tr><th>Concept</th>'
        + "".join(
            f'<th class="lang-{html.escape(lang["slug"])}" '
            f'data-language="{html.escape(lang["slug"], quote=True)}" hidden>'
            f'{html.escape(lang["name"])}</th>'
            for lang in languages
        )
        + '</tr></thead>'
        + f'<tbody>{render_rows(matching_rows(section))}</tbody></table></section>'
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

  <main class="container" style="max-width:1100px;padding-bottom:4rem;">
    <div class="compare-hero">
      <h1>{html.escape(site["compare_heading"])}</h1>
      <p id="compare-language-summary">{html.escape(site["compare_intro"])}</p>
    </div>

    <section class="compare-picker" aria-labelledby="compare-picker-heading">
      <div class="compare-picker-heading">
        <h2 id="compare-picker-heading">Choose languages</h2>
        <p id="compare-language-count" aria-live="polite">0 of 4 selected</p>
      </div>
      <div id="compare-language-options" class="compare-language-options" role="group" aria-label="Languages to compare"></div>
      <p class="compare-picker-help">Select up to four languages. Comparison columns appear as you choose them.</p>
    </section>

    <p id="compare-empty-state" class="compare-empty-state">Choose at least one language to display the comparison tables.</p>

    <nav class="compare-toc">
      {toc_html}
    </nav>

    {sections_html}
  </main>

  <script src="{js_path}"></script>
  <script src="{main_js_path}"></script>
</body>
</html>
'''
