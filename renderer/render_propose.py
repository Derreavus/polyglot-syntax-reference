"""The "Propose a language" page: what a proposal needs, generated from the same definition as the proposal form.

The fields, the comparison rows and the concepts come from ``proposal.py`` and the site data, so the page cannot disagree
with the GitHub issue form. All wording lives in ``data["site"]``. The page is plain HTML with no script of its own.
"""

from __future__ import annotations

import html
from typing import Any

from chrome import render_footer, render_head, render_header
from proposal import REVIEW_CHECKLIST, compare_rows, concept_titles, form_fields

# Fields shown in the "what you fill in" list. The comparison rows and the concepts have their own sections.
OWN_SECTION = {"concepts"}


def _tag(site: dict[str, Any], required: bool) -> str:
    kind, key = ("required", "propose_required_label") if required else ("optional", "propose_optional_label")
    return f'<span class="propose-tag propose-{kind}">{html.escape(site[key])}</span>'


def render_propose_page(data: dict[str, Any], page_rel: str = "propose/index.html") -> str:
    site = data["site"]
    titles = concept_titles(data)
    general = [f for f in form_fields(data) if isinstance(f["key"], str) and not f["key"].startswith("_") and f["key"] not in OWN_SECTION]

    def describe(field: dict[str, Any]) -> str:
        if field.get("description"):
            return html.escape(field["description"])
        return html.escape(f'{site["propose_options_prefix"]} ' + ", ".join(field.get("options", [])))

    fields_html = "\n".join(
        f'<dt>{html.escape(field["label"])} {_tag(site, bool(field["required"]))}</dt><dd>{describe(field)}</dd>' for field in general
    )
    compare_html = "\n".join(
        f'<li><strong>{html.escape(row["label"])}</strong> <span>{html.escape(titles.get(row["concept"], row["concept"]))}</span></li>'
        for row in compare_rows(data)
    )
    concepts_html = "\n".join(f"<li>{html.escape(title)}</li>" for title in titles.values())
    steps_html = "\n".join(f"<li>{html.escape(step)}</li>" for step in site["propose_steps"])
    review_html = "\n".join(f"<li>{html.escape(item)}</li>" for item in REVIEW_CHECKLIST)
    head_title = f'{site["propose_title"]} — {site["brand"]}'
    return f'''<!DOCTYPE html>
<html lang="en">
{render_head(data, page_rel, head_title, site["propose_description"])}
<body>
  {render_header(data, page_rel, action="home")}

  <main class="container compare-main propose-main">
    <div class="compare-hero">
      <h1>{html.escape(site["propose_heading"])}</h1>
      <p>{html.escape(site["propose_intro"])}</p>
      <p><a class="propose-button" href="{html.escape(site["propose_form_url"], quote=True)}" rel="noopener">{html.escape(site["propose_button"])}</a></p>
    </div>

    <section class="propose-section" id="how-it-works">
      <h2>{html.escape(site["propose_steps_heading"])}</h2>
      <ol class="propose-steps">
{steps_html}
      </ol>
    </section>

    <section class="propose-section" id="fields">
      <h2>{html.escape(site["propose_fields_heading"])}</h2>
      <p>{html.escape(site["propose_fields_intro"])}</p>
      <dl class="propose-fields">
{fields_html}
      </dl>
    </section>

    <section class="propose-section" id="comparison-rows">
      <h2>{html.escape(site["propose_compare_heading"])}</h2>
      <p>{html.escape(site["propose_compare_intro"])}</p>
      <ul class="propose-list">
{compare_html}
      </ul>
    </section>

    <section class="propose-section" id="concepts">
      <h2>{html.escape(site["propose_concepts_heading"])}</h2>
      <p>{html.escape(site["propose_concepts_intro"])}</p>
      <ul class="propose-list">
{concepts_html}
      </ul>
    </section>

    <section class="propose-section" id="review">
      <h2>{html.escape(site["propose_review_heading"])}</h2>
      <ul class="propose-list">
{review_html}
      </ul>
    </section>
  </main>

  {render_footer(site, page_rel)}
</body>
</html>
'''
