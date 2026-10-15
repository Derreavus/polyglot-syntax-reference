"""Page chrome shared by every page: the <head>, the site header and the footer.

One copy of each means the brand, the navigation and the interface wording change in a single place, and
a new kind of page cannot drift out of step with the others.
"""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any

from theme import language_theme_style

FONTS = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700"
    "&family=JetBrains+Mono:wght@400;500&display=swap"
)


def relative_asset_path(page_rel: str, target_rel: str) -> str:
    return os.path.relpath(target_rel, start=str(Path(page_rel).parent)).replace("\\", "/")


def render_head(data: dict[str, Any], page_rel: str, title: str, description: str | None = None) -> str:
    css_path = relative_asset_path(page_rel, "css/style.css")
    meta = (
        f'\n  <meta name="description" content="{html.escape(description, quote=True)}">' if description else ""
    )
    return f'''<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>{meta}
  <script>document.documentElement.classList.add("js");</script>
  <link rel="stylesheet" href="{css_path}">
  {language_theme_style(data)}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{FONTS}" rel="stylesheet">
</head>'''


def render_header(data: dict[str, Any], page_rel: str, menu_label: str | None = None, action: str = "compare") -> str:
    """The site header. ``menu_label`` is the name shown on the reference menu (the current reference on its own pages)."""
    site = data["site"]
    label = html.escape(menu_label if menu_label is not None else site["nav_references_label"])
    home = relative_asset_path(page_rel, "index.html")
    if action == "home":
        button_href, button_text = home, site["nav_home_label"]
    else:
        button_href, button_text = relative_asset_path(page_rel, "compare/index.html"), site["nav_compare_label"]
    return f'''<header class="site-header">
    <div class="container header-inner">
      <a href="{home}" class="logo"><span class="logo-mark">{{ }}</span><span class="logo-text">{html.escape(site["brand_short"])}</span></a>
      <nav class="lang-nav" aria-label="{html.escape(site["nav_references_aria"], quote=True)}">
        <details class="language-menu">
          <summary class="language-menu-toggle" aria-label="{html.escape(site["nav_references_choose"], quote=True)}">
            <span>{label}</span><span class="language-menu-chevron" aria-hidden="true"></span>
          </summary>
          <div class="language-menu-panel" aria-label="{html.escape(site["nav_references_available"], quote=True)}"></div>
        </details>
      </nav>
      <a href="{button_href}" class="lang-btn" style="color: var(--accent); border: 1px solid var(--accent);">{html.escape(button_text)}</a>
      <button id="theme-toggle" class="theme-btn" aria-label="{html.escape(site["theme_toggle_label"], quote=True)}">☾</button>
    </div>
  </header>'''


def render_footer(site: dict[str, Any]) -> str:
    return f'''<footer class="site-footer">
    <div class="container">
      <p>{html.escape(site["footer"])}</p>
    </div>
  </footer>'''
