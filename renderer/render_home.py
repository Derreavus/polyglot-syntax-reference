from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any

from theme import language_theme_style


def relative_asset_path(page_rel: str, target_rel: str) -> str:
    return os.path.relpath(target_rel, start=str(Path(page_rel).parent)).replace('\\', '/')


def render_home_page(data: dict[str, Any], page_rel: str = "index.html") -> str:
    languages = sorted(data.get("languages", []), key=lambda item: int(item.get("order", 0)))
    site = data["site"]
    css_path = relative_asset_path(page_rel, "css/style.css")
    js_path = relative_asset_path(page_rel, "js/site-data.js")
    main_js_path = relative_asset_path(page_rel, "js/main.js")

    def card_for(lang: dict[str, Any]) -> str:
        slug = lang["slug"]
        href = relative_asset_path(page_rel, f"{slug}/index.html")
        return (
            f'<a href="{href}" class="hero-card {html.escape(slug)}">'
            f'<h2>{html.escape(lang["name"])}</h2>'
            f'<p>{html.escape(lang.get("description", ""))}</p>'
            f'</a>'
        )

    cards_html = "\n".join(card_for(lang) for lang in languages)

    compare_href = relative_asset_path(page_rel, "compare/index.html")

    brand = site["brand"]
    brand_short = site["brand_short"]
    home_heading = "<br>".join(
        html.escape(line) for line in site["home_heading_lines"]
    )
    home_description = site["home_description"]

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(brand)}</title>
  <meta name="description" content="{html.escape(site["home_meta_description"], quote=True)}">
  <script>document.documentElement.classList.add("js");</script>
  <link rel="stylesheet" href="{css_path}">
  {language_theme_style(data)}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a href="{relative_asset_path(page_rel, 'index.html')}" class="logo">
        <span class="logo-mark">{{ }}</span>
        <span class="logo-text">{html.escape(brand_short)}</span>
      </a>
      <nav class="lang-nav" aria-label="Language navigation">
        <details class="language-menu">
          <summary class="language-menu-toggle" aria-label="Choose a language">
            <span>Languages</span><span class="language-menu-chevron" aria-hidden="true"></span>
          </summary>
          <div class="language-menu-panel" aria-label="Available languages"></div>
        </details>
      </nav>
      <a href="{compare_href}" class="lang-btn" style="color: var(--accent); border: 1px solid var(--accent);">Compare</a>
      <button id="theme-toggle" class="theme-btn" aria-label="Toggle theme">☾</button>
    </div>
  </header>

  <main>
    <section class="hero">
      <div class="container">
        <h1>{home_heading}</h1>
        <p class="hero-sub">{html.escape(home_description)}</p>
        <div class="hero-cards" aria-label="Language cards">{cards_html}</div>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>{html.escape(site["footer"])}</p>
    </div>
  </footer>

  <script src="{js_path}"></script>
  <script src="{main_js_path}"></script>
</body>
</html>
'''
