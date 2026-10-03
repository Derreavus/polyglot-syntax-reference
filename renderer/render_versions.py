"""Version history page for a language: what was added, changed, deprecated and removed."""

from __future__ import annotations

import html
from typing import Any

from render_language import relative_asset_path
from versioning import (
    KIND_LABELS,
    features_for,
    is_breaking,
    version_orders,
    versions_for,
)

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
KIND_ORDER = ("removed", "deprecated", "changed", "added")


def format_release(released: str) -> str:
    parts = released.split("-")
    if len(parts) >= 2:
        return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}"
    return released


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _feature_link(feature: dict[str, Any], language_slug: str, from_versions_page: bool = True) -> str:
    """Link to where the feature is explained: its topic on the reference page, if it has one."""
    title = _esc(feature["title"])
    topic = feature.get("topic")
    if topic:
        return f'<a class="change-title" href="../index.html#{_esc(topic)}">{title}</a>'
    return f'<span class="change-title">{title}</span>'


def _migration_html(feature: dict[str, Any]) -> str:
    migration = feature.get("migration")
    if not migration:
        return ""
    note = f'<p class="migration-note">{_esc(migration["note"])}</p>' if migration.get("note") else ""
    return (
        '<details class="migration"><summary>Before and after</summary>'
        '<div class="migration-pair">'
        f'<figure><figcaption>Older code</figcaption><pre><code>{_esc(migration["legacy"])}</code></pre></figure>'
        f'<figure><figcaption>Newer code</figcaption><pre><code>{_esc(migration["modern"])}</code></pre></figure>'
        f"</div>{note}</details>"
    )


def _replaced_by_html(feature: dict[str, Any], features_by_slug: dict[str, dict[str, Any]]) -> str:
    targets = feature.get("replaced_by", [])
    if not targets:
        return ""
    links = ", ".join(
        f'<a href="#feature-{_esc(slug)}">{_esc(features_by_slug[slug]["title"])}</a>' for slug in targets
    )
    return f'<p class="change-replaced">Use instead: {links}</p>'


def _event_html(
    feature: dict[str, Any],
    event: dict[str, Any],
    order: int | None,
    added_order: int,
    features_by_slug: dict[str, dict[str, Any]],
    language_slug: str,
) -> str:
    kind = event["kind"]
    breaking = is_breaking(event)
    classes = f"change kind-{kind}"
    attrs = (
        f'data-kind="{kind}" data-breaking="{"true" if breaking else "false"}" '
        f'data-added-order="{added_order}"'
    )
    anchor = f' id="feature-{_esc(feature["slug"])}"' if kind == "added" else ""
    scope = f' <span class="change-scope">{_esc(event["scope"])}</span>' if event.get("scope") else ""
    breaking_badge = '<span class="breaking-badge">Breaking</span>' if breaking else ""
    note = f'<p class="change-note">{_esc(event["note"])}</p>' if event.get("note") else ""
    extras = _migration_html(feature) if kind == "added" else _replaced_by_html(feature, features_by_slug)
    if kind != "added":
        see = f'<a class="change-origin" href="#feature-{_esc(feature["slug"])}">Where it was added</a>'
    else:
        see = ""
    return (
        f'<li class="{classes}"{anchor} {attrs}>'
        f'<div class="change-head"><span class="kind-badge kind-{kind}">{KIND_LABELS[kind]}</span>'
        f'{_feature_link(feature, language_slug)}'
        f'<span class="category-tag">{_esc(feature["category"])}</span>{breaking_badge}{scope}</div>'
        f'<p class="change-summary">{_esc(feature["summary"])}</p>{note}{extras}{see}'
        "</li>"
    )


def render_versions_page(
    language: dict[str, Any], data: dict[str, Any], page_rel: str
) -> str:
    site = data["site"]
    slug = language["slug"]
    versions = versions_for(data, slug)
    orders = version_orders(versions)
    features = features_for(data, slug)
    features_by_slug = {feature["slug"]: feature for feature in features}
    version_by_id = {version["id"]: version for version in versions}

    events_by_version: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {v["id"]: [] for v in versions}
    undated: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for feature in features:
        for event in feature["history"]:
            if event["version"] is None:
                undated.append((feature, event))
            else:
                events_by_version[event["version"]].append((feature, event))

    def sort_key(item: tuple[dict[str, Any], dict[str, Any]]) -> tuple[int, str]:
        feature, event = item
        return (KIND_ORDER.index(event["kind"]), feature["title"].lower())

    blocks: list[str] = []
    for version in reversed(versions):
        items = sorted(events_by_version[version["id"]], key=sort_key)
        if not items:
            continue
        added_order = lambda feature: orders[feature["history"][0]["version"]]  # noqa: E731
        draft = '<span class="draft-badge">Draft</span>' if version["status"] == "draft" else ""
        aliases = f' <span class="version-aliases">also {_esc(", ".join(version["aliases"]))}</span>' if version.get("aliases") else ""
        note = f'<p class="version-note">{_esc(version["note"])}</p>' if version.get("note") else ""
        list_html = "\n".join(
            _event_html(feature, event, orders[version["id"]], added_order(feature), features_by_slug, slug)
            for feature, event in items
        )
        blocks.append(
            f'<section class="version-block" id="v-{_esc(version["id"])}" data-order="{version["order"]}" '
            f'data-status="{version["status"]}">'
            f'<h2>{_esc(version["label"])}{draft}</h2>'
            f'<p class="version-date">{_esc(format_release(version["released"]))}{aliases}</p>{note}'
            f'<ul class="change-list">{list_html}</ul></section>'
        )

    if undated:
        undated.sort(key=sort_key)
        added_of = lambda feature: orders[feature["history"][0]["version"]]  # noqa: E731
        list_html = "\n".join(
            _event_html(feature, event, None, added_of(feature), features_by_slug, slug)
            for feature, event in undated
        )
        blocks.append(
            '<section class="version-block version-undated" id="v-undated" data-order="">'
            '<h2>Deprecated, with no removal planned</h2>'
            '<p class="version-note">These are discouraged but still work. No edition has deprecated or removed them, so they are not tied to a version.</p>'
            f'<ul class="change-list">{list_html}</ul></section>'
        )

    def option(version: dict[str, Any], selected: bool) -> str:
        draft = " (draft)" if version["status"] == "draft" else ""
        return (
            f'<option value="{_esc(version["id"])}" data-order="{version["order"]}"'
            f'{" selected" if selected else ""}>{_esc(version["label"])}{draft}</option>'
        )

    released = [v for v in versions if v["status"] == "released"]
    default_to = released[-1]["id"] if released else versions[-1]["id"]
    from_options = '<option value="" data-order="0">Beginning</option>' + "".join(
        option(v, False) for v in versions
    )
    to_options = "".join(option(v, v["id"] == default_to) for v in versions)

    kind_buttons = "".join(
        f'<button type="button" class="kind-filter kind-{kind}" data-kind="{kind}" aria-pressed="true">{KIND_LABELS[kind]}</button>'
        for kind in ("added", "changed", "deprecated", "removed")
    )

    links_html = "".join(
        f'<li><a href="{_esc(link["url"])}" rel="noopener">{_esc(link["title"])}</a></li>'
        for link in language.get("changelog_links", [])
    )

    css_path = relative_asset_path(page_rel, "css/style.css")
    js_path = relative_asset_path(page_rel, "js/site-data.js")
    main_js_path = relative_asset_path(page_rel, "js/main.js")
    home_path = relative_asset_path(page_rel, "index.html")
    compare_path = relative_asset_path(page_rel, "compare/index.html")
    language_path = relative_asset_path(page_rel, f"{slug}/index.html")
    name = html.escape(language["name"])

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} version history — {html.escape(site["brand"])}</title>
  <meta name="description" content="What was added, changed, deprecated and removed in each {name} version, with before-and-after examples for upgrading old code.">
  <script>document.documentElement.classList.add("js");</script>
  <link rel="stylesheet" href="{css_path}">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a href="{home_path}" class="logo"><span class="logo-mark">{{ }}</span><span class="logo-text">{html.escape(site["brand_short"])}</span></a>
      <nav class="lang-nav" aria-label="Language navigation">
        <details class="language-menu">
          <summary class="language-menu-toggle" aria-label="Choose a language">
            <span>{name}</span><span class="language-menu-chevron" aria-hidden="true"></span>
          </summary>
          <div class="language-menu-panel" aria-label="Available languages"></div>
        </details>
      </nav>
      <a href="{compare_path}" class="lang-btn" style="color: var(--accent); border: 1px solid var(--accent);">Compare</a>
      <button id="theme-toggle" class="theme-btn" aria-label="Toggle theme">☾</button>
    </div>
  </header>

  <main class="container versions-main">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="{home_path}">Home</a> / <a href="{language_path}">{name}</a> / <span>Version history</span></nav>
    <h1>{name} version history</h1>
    <p class="versions-intro">What was added, changed, deprecated and removed between {name} versions. Choose the version your code was written for and the one you are moving to, and the list shows everything in between.</p>

    <section class="version-controls" aria-label="Choose versions">
      <div class="version-selects">
        <label>Upgrading from<select id="version-from">{from_options}</select></label>
        <label>to<select id="version-to">{to_options}</select></label>
      </div>
      <div class="kind-filters" role="group" aria-label="Types of change to show">{kind_buttons}</div>
      <label class="breaking-only"><input type="checkbox" id="breaking-only"> Breaking changes only</label>
      <p id="version-summary" class="version-summary" role="status" aria-live="polite"></p>
    </section>

    <div id="version-list" data-language="{html.escape(slug)}">
      {"".join(blocks)}
    </div>
    <p id="version-empty" class="version-empty" hidden>No changes match these choices.</p>

    <section class="version-sources">
      <h2>Official changelogs</h2>
      <p>This history is a summary. The official sources below are the reference for exact wording and dates.</p>
      <ul>{links_html}</ul>
    </section>
  </main>

  <script src="{js_path}"></script>
  <script src="{main_js_path}"></script>
</body>
</html>
'''
