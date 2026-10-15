from __future__ import annotations

import html
from typing import Any

from chrome import relative_asset_path, render_footer, render_head, render_header
from versioning import has_versioning

SEARCH_ICON = (
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
    'aria-hidden="true"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/></svg>'
)


def render_home_page(data: dict[str, Any], page_rel: str = "index.html") -> str:
    site = data["site"]
    languages = sorted(data.get("languages", []), key=lambda item: int(item.get("order", 0)))
    categories = sorted(data.get("categories", []), key=lambda item: int(item.get("order", 0)))
    js_path = relative_asset_path(page_rel, "js/site-data.js")
    main_js_path = relative_asset_path(page_rel, "js/main.js")
    topic_counts: dict[str, int] = {}
    for topic in data.get("topics", []):
        topic_counts[topic["language"]] = topic_counts.get(topic["language"], 0) + 1

    def card_for(lang: dict[str, Any]) -> str:
        slug = lang["slug"]
        href = relative_asset_path(page_rel, f"{slug}/index.html")
        count = topic_counts.get(slug, 0)
        facts = [f"{count} topic" + ("" if count == 1 else "s")]
        if has_versioning(data, slug):
            facts.append(site["card_version_history"])
        return (
            f'<a href="{href}" class="hero-card {html.escape(slug)}">'
            f'<h2>{html.escape(lang["name"])}</h2>'
            f'<p>{html.escape(lang.get("description", ""))}</p>'
            f'<p class="card-meta">{html.escape(" · ".join(facts))}</p>'
            f"</a>"
        )

    sections: list[str] = []
    for category in categories:
        members = [lang for lang in languages if lang["category"] == category["slug"]]
        if not members:
            continue
        heading_id = f'category-{html.escape(category["slug"])}'
        sections.append(
            f'<section class="home-section" aria-labelledby="{heading_id}">'
            f'<div class="container"><h2 id="{heading_id}">{html.escape(category["name"])}</h2>'
            f'<p class="home-section-sub">{html.escape(category["description"])}</p>'
            f'<div class="hero-cards">{"".join(card_for(lang) for lang in members)}</div></div></section>'
        )

    compare_href = relative_asset_path(page_rel, "compare/index.html")
    tools = (
        '<section class="home-section" aria-labelledby="tools-heading">'
        f'<div class="container"><h2 id="tools-heading">{html.escape(site["home_tools_heading"])}</h2>'
        '<div class="hero-cards">'
        f'<a href="{compare_href}" class="hero-card tool-card"><h2>{html.escape(site["home_compare_title"])}</h2>'
        f'<p>{html.escape(site["home_compare_description"])}</p></a>'
        "</div></div></section>"
    )

    heading = "<br>".join(html.escape(line) for line in site["home_heading_lines"])
    return f'''<!DOCTYPE html>
<html lang="en">
{render_head(data, page_rel, site["brand"], site["home_meta_description"])}
<body>
  {render_header(data, page_rel)}

  <main>
    <section class="hero">
      <div class="container">
        <h1>{heading}</h1>
        <p class="hero-sub">{html.escape(site["home_description"])}</p>
        <button type="button" class="hero-search" id="hero-search" aria-label="{html.escape(site["home_search_label"], quote=True)}">
          {SEARCH_ICON}<span>{html.escape(site["home_search_prompt"])}</span><kbd>/</kbd>
        </button>
      </div>
    </section>
    <h2 class="sr-only">{html.escape(site["home_browse_heading"])}</h2>
    {"".join(sections)}
    {tools}
  </main>

  {render_footer(site)}

  <script src="{js_path}"></script>
  <script src="{main_js_path}"></script>
</body>
</html>
'''
