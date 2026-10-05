"""Version history pages for a language: one page per track (for example ECMAScript and Node.js)."""

from __future__ import annotations

import html
from typing import Any

from render_language import relative_asset_path
from versioning import (
    KIND_LABELS,
    STATES,
    features_for,
    history_for,
    is_breaking,
    lifecycle_facts,
    release_text,
    short_label,
    track_page_rel,
    tracks_for,
    version_orders,
    versions_for,
)

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
KIND_ORDER = ("removed", "deprecated", "changed", "added")
STATE_LABELS = {
    "available": "Available",
    "deprecated": "Deprecated",
    "restricted": "Restricted",
    "removed": "Removed",
    "not-yet": "Not yet",
}
KIND_NOUN = {"language": "edition", "runtime": "release"}
TRACK_KIND_LABEL = {"language": "Language standard", "runtime": "Runtime"}


def format_date(value: str) -> str:
    parts = value.split("-")
    if len(parts) >= 2:
        month = MONTHS[int(parts[1]) - 1]
        return f"{month} {parts[2].lstrip('0')}, {parts[0]}" if len(parts) == 3 else f"{month} {parts[0]}"
    return value


def format_month(value: str) -> str:
    parts = value.split("-")
    return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}" if len(parts) >= 2 else value


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _feature_link(ctx: "TrackContext", feature: dict[str, Any]) -> str:
    """Link to where the feature is explained: its topic on the reference page, if it has one."""
    title = _esc(feature["title"])
    topic = feature.get("topic")
    if topic:
        return f'<a class="change-title" href="{_esc(ctx.language_href)}#{_esc(topic)}">{title}</a>'
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


def _replaced_by_html(feature: dict[str, Any], features_by_slug: dict[str, dict[str, Any]], prefix: str) -> str:
    targets = feature.get("replaced_by", [])
    if not targets:
        return ""
    links = ", ".join(
        f'<a href="#{prefix}{_esc(slug)}">{_esc(features_by_slug[slug]["title"])}</a>'
        for slug in targets
        if slug in features_by_slug
    )
    return f'<p class="change-replaced">Use instead: {links}</p>' if links else ""


class TrackContext:
    """Everything the page needs to know about one track of one language."""

    def __init__(self, data: dict[str, Any], language: dict[str, Any], track: dict[str, Any]) -> None:
        self.data = data
        self.language = language
        self.slug = language["slug"]
        self.track = track
        self.versions = versions_for(data, self.slug, track["id"])
        self.orders = version_orders(self.versions)
        self.version_by_id = {v["id"]: v for v in self.versions}
        self.features = features_for(data, self.slug, track["id"])
        self.features_by_slug = {f["slug"]: f for f in self.features}
        self.page_rel = track_page_rel(data, self.slug, track["id"])
        self.language_href = relative_asset_path(self.page_rel, f"{self.slug}/index.html")

    def history(self, feature: dict[str, Any]) -> list[dict[str, Any]]:
        return history_for(feature, self.track["id"])

    def added_order(self, feature: dict[str, Any]) -> int:
        return self.orders[self.history(feature)[0]["version"]]

    def other_tracks_html(self, feature: dict[str, Any]) -> str:
        """Where else the feature is tracked, for example the ECMAScript edition behind a Node.js entry."""
        parts: list[str] = []
        for other in tracks_for(self.data, self.slug):
            if other["id"] == self.track["id"] or other["id"] not in feature["history"]:
                continue
            other_versions = {v["id"]: v for v in versions_for(self.data, self.slug, other["id"])}
            first = feature["history"][other["id"]][0]
            label = release_text(other_versions[first["version"]], first)
            target = relative_asset_path(self.page_rel, track_page_rel(self.data, self.slug, other["id"]))
            plus = "+" if other["kind"] == "runtime" else ""
            parts.append(
                f'<a href="{_esc(target)}#feature-{_esc(feature["slug"])}">{_esc(other["label"])}: {_esc(label)}{plus}</a>'
            )
        return f'<p class="change-tracks">Also tracked on {" · ".join(parts)}</p>' if parts else ""


def _event_html(ctx: TrackContext, feature: dict[str, Any], event: dict[str, Any], added_order: int) -> str:
    kind = event["kind"]
    breaking = is_breaking(event)
    attrs = (
        f'data-kind="{kind}" data-breaking="{"true" if breaking else "false"}" '
        f'data-added-order="{added_order}"'
    )
    anchor = f' id="feature-{_esc(feature["slug"])}"' if kind == "added" else ""
    scope = f' <span class="change-scope">{_esc(event["scope"])}</span>' if event.get("scope") else ""
    release = (
        f'<span class="release-tag">from {_esc(event["release"])}</span>' if event.get("release") else ""
    )
    breaking_badge = '<span class="breaking-badge">Breaking</span>' if breaking else ""
    note = f'<p class="change-note">{_esc(event["note"])}</p>' if event.get("note") else ""
    if kind == "added":
        extras = _migration_html(feature) + ctx.other_tracks_html(feature)
        see = ""
    else:
        extras = _replaced_by_html(feature, ctx.features_by_slug, "feature-")
        see = f'<a class="change-origin" href="#feature-{_esc(feature["slug"])}">Where it was added</a>'
    return (
        f'<li class="change kind-{kind}"{anchor} {attrs}>'
        f'<div class="change-head"><span class="kind-badge kind-{kind}">{KIND_LABELS[kind]}</span>'
        f'{_feature_link(ctx, feature)}'
        f'<span class="category-tag">{_esc(feature["category"])}</span>{release}{breaking_badge}{scope}</div>'
        f'<p class="change-summary">{_esc(feature["summary"])}</p>{note}{extras}{see}'
        "</li>"
    )


def _version_meta_html(version: dict[str, Any]) -> str:
    bits = [_esc(format_date(version["released"]))]
    if version.get("engine"):
        bits.append(_esc(version["engine"]))
    if version.get("lts_from"):
        bits.append(f'Long-term support from {_esc(format_month(version["lts_from"]))}')
    html_bits = " · ".join(bits)
    if version.get("end_of_life"):
        end = version["end_of_life"]
        html_bits += (
            f' · <span class="eol" data-eol="{_esc(end)}" data-eol-text="{_esc(format_month(end))}">'
            f'Support ends {_esc(format_month(end))}</span>'
        )
    if version.get("aliases"):
        html_bits += f' <span class="version-aliases">also {_esc(", ".join(version["aliases"]))}</span>'
    return html_bits


def _card_html(ctx: TrackContext, feature: dict[str, Any]) -> str:
    facts = lifecycle_facts(feature, ctx.track["id"], ctx.version_by_id)
    added, added_event = facts["added"], facts["added_event"]
    deprecated, removed = facts["deprecated"], facts["removed"]
    dep_value = "" if deprecated is None else ("any" if deprecated["version"] is None else str(ctx.orders[deprecated["version"]]))
    rem_value = "" if removed is None else str(ctx.orders[removed["version"]])
    scope = _esc(removed.get("scope", "")) if removed else ""
    timeline = [f"Added in {_esc(release_text(added, added_event))}"]
    for version in facts["changed_versions"]:
        timeline.append(f"changed in {_esc(short_label(version))}")
    if deprecated is not None:
        timeline.append(
            "deprecated, no removal planned" if facts["deprecated_version"] is None
            else f'deprecated in {_esc(short_label(facts["deprecated_version"]))}'
        )
    if removed is not None:
        timeline.append(
            ("restricted" if scope else "removed") + f' in {_esc(short_label(facts["removed_version"]))}'
            + (f" ({scope})" if scope else "")
        )
    migration = feature.get("migration")
    legacy_block = modern_block = ""
    if migration:
        legacy_block = (
            '<details class="migration" data-show-when="not-yet"><summary>What to write in this version instead</summary>'
            f'<pre><code>{_esc(migration["legacy"])}</code></pre>'
            + (f'<p class="migration-note">{_esc(migration["note"])}</p>' if migration.get("note") else "")
            + "</details>"
        )
        modern_block = (
            '<details class="migration" data-show-when="deprecated restricted removed"><summary>Newer way to write it</summary>'
            f'<pre><code>{_esc(migration["modern"])}</code></pre></details>'
        )
    replaced = _replaced_by_html(feature, ctx.features_by_slug, "index-")
    topic = feature.get("topic")
    title = (
        f'<a class="change-title" href="{_esc(ctx.language_href)}#{_esc(topic)}">{_esc(feature["title"])}</a>'
        if topic else f'<span class="change-title">{_esc(feature["title"])}</span>'
    )
    search = _esc(f'{feature["title"]} {feature["summary"]} {feature["category"]}'.lower())
    return (
        f'<li class="feature-card" id="index-{_esc(feature["slug"])}" data-added="{ctx.orders[added["id"]]}" '
        f'data-deprecated="{dep_value}" data-removed="{rem_value}" data-removed-scope="{scope}" '
        f'data-search="{search}" data-state="available">'
        f'<div class="change-head"><span class="state-badge" data-state-badge>Available</span>{title}'
        f'<span class="category-tag">{_esc(feature["category"])}</span></div>'
        f'<p class="change-summary">{_esc(feature["summary"])}</p>'
        f'<p class="feature-timeline">{" · ".join(timeline)}</p>'
        f'{legacy_block}{modern_block}{replaced}{ctx.other_tracks_html(feature)}</li>'
    )


def render_versions_page(
    language: dict[str, Any], track: dict[str, Any], data: dict[str, Any], page_rel: str
) -> str:
    site = data["site"]
    ctx = TrackContext(data, language, track)
    slug = ctx.slug
    noun = KIND_NOUN[track["kind"]]
    name = html.escape(language["name"])
    track_label = html.escape(track["label"])

    events_by_version: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {v["id"]: [] for v in ctx.versions}
    undated: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for feature in ctx.features:
        for event in ctx.history(feature):
            if event["version"] is None:
                undated.append((feature, event))
            else:
                events_by_version[event["version"]].append((feature, event))

    def sort_key(item: tuple[dict[str, Any], dict[str, Any]]) -> tuple[int, str]:
        feature, event = item
        return (KIND_ORDER.index(event["kind"]), feature["title"].lower())

    blocks: list[str] = []
    for version in reversed(ctx.versions):
        items = sorted(events_by_version[version["id"]], key=sort_key)
        if not items:
            continue
        draft = '<span class="draft-badge">Draft</span>' if version["status"] == "draft" else ""
        codename = (
            f'<span class="codename-badge">{_esc(version["codename"])}</span>' if version.get("codename") else ""
        )
        note = f'<p class="version-note">{_esc(version["note"])}</p>' if version.get("note") else ""
        list_html = "\n".join(
            _event_html(ctx, feature, event, ctx.added_order(feature)) for feature, event in items
        )
        blocks.append(
            f'<section class="version-block" id="v-{_esc(version["id"])}" data-order="{version["order"]}" '
            f'data-status="{version["status"]}">'
            f'<h2>{_esc(version["label"])}{codename}{draft}</h2>'
            f'<p class="version-date">{_version_meta_html(version)}</p>{note}'
            f'<ul class="change-list">{list_html}</ul></section>'
        )

    if undated:
        undated.sort(key=sort_key)
        list_html = "\n".join(
            _event_html(ctx, feature, event, ctx.added_order(feature)) for feature, event in undated
        )
        blocks.append(
            '<section class="version-block version-undated" id="v-undated" data-order="">'
            '<h2>Deprecated, with no removal planned</h2>'
            f'<p class="version-note">These are discouraged but still work. No {noun} has deprecated or removed them, so they are not tied to a version.</p>'
            f'<ul class="change-list">{list_html}</ul></section>'
        )

    ordered_features = sorted(ctx.features, key=lambda f: (ctx.added_order(f), f["title"].lower()))
    cards_html = "\n".join(_card_html(ctx, feature) for feature in ordered_features)
    state_buttons = "".join(
        f'<button type="button" class="state-filter state-{state}" data-state="{state}" aria-pressed="true">{STATE_LABELS[state]}</button>'
        for state in STATES
    )

    def option(version: dict[str, Any], selected: bool) -> str:
        draft = " (draft)" if version["status"] == "draft" else ""
        return (
            f'<option value="{_esc(version["id"])}" data-order="{version["order"]}"'
            f'{" selected" if selected else ""}>{_esc(version["label"])}{draft}</option>'
        )

    released = [v for v in ctx.versions if v["status"] == "released"]
    default_to = released[-1]["id"] if released else ctx.versions[-1]["id"]
    from_options = '<option value="" data-order="0">Beginning</option>' + "".join(option(v, False) for v in ctx.versions)
    to_options = "".join(option(v, v["id"] == default_to) for v in ctx.versions)
    at_options = to_options

    kind_buttons = "".join(
        f'<button type="button" class="kind-filter kind-{kind}" data-kind="{kind}" aria-pressed="true">{KIND_LABELS[kind]}</button>'
        for kind in ("added", "changed", "deprecated", "removed")
    )
    links_html = "".join(
        f'<li><a href="{_esc(link["url"])}" rel="noopener">{_esc(link["title"])}</a></li>'
        for link in track["changelog_links"]
    )

    all_tracks = tracks_for(data, slug)
    tabs = ""
    if len(all_tracks) > 1:
        tab_items = []
        for other in all_tracks:
            href = relative_asset_path(page_rel, track_page_rel(data, slug, other["id"]))
            current = ' aria-current="page"' if other["id"] == track["id"] else ""
            tab_items.append(
                f'<a class="track-tab" href="{_esc(href)}"{current}>'
                f'<span class="track-tab-name">{_esc(other["label"])}</span>'
                f'<span class="track-tab-kind">{TRACK_KIND_LABEL[other["kind"]]}</span></a>'
            )
        tabs = f'<nav class="track-tabs" aria-label="Version tracks">{"".join(tab_items)}</nav>'

    css_path = relative_asset_path(page_rel, "css/style.css")
    js_path = relative_asset_path(page_rel, "js/site-data.js")
    main_js_path = relative_asset_path(page_rel, "js/main.js")
    home_path = relative_asset_path(page_rel, "index.html")
    compare_path = relative_asset_path(page_rel, "compare/index.html")
    language_path = relative_asset_path(page_rel, f"{slug}/index.html")
    primary_page = relative_asset_path(page_rel, track_page_rel(data, slug, all_tracks[0]["id"]))
    is_primary = track["id"] == all_tracks[0]["id"]
    crumb_track = (
        f'<a href="{_esc(primary_page)}">Version history</a> / <span>{track_label}</span>'
        if not is_primary else "<span>Version history</span>"
    )
    title_suffix = "" if is_primary else f": {track['label']}"

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} version history{html.escape(title_suffix)} — {html.escape(site["brand"])}</title>
  <meta name="description" content="What was added, changed, deprecated and removed in each {track_label} {noun} for {name}, with before-and-after examples for upgrading old code.">
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
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="{home_path}">Home</a> / <a href="{language_path}">{name}</a> / {crumb_track}</nav>
    <h1>{name} version history</h1>
    {tabs}
    <p class="track-description"><strong>{track_label}.</strong> {html.escape(track["description"])}</p>
    <p class="versions-intro">What was added, changed, deprecated and removed between {track_label} {noun}s. See everything that changes between the {noun} your code was written for and the one you are moving to, or check what a particular {noun} can and cannot use.</p>

    <div class="view-switch" role="group" aria-label="Choose a view">
      <button type="button" class="view-tab" data-view="changes" aria-pressed="true">Upgrade changes</button>
      <button type="button" class="view-tab" data-view="available" aria-pressed="false">What can I use?</button>
    </div>

    <div id="panel-changes" class="version-panel">
      <section class="version-controls" aria-label="Choose versions">
        <div class="version-selects">
          <label>Upgrading from<select id="version-from">{from_options}</select></label>
          <label>to<select id="version-to">{to_options}</select></label>
        </div>
        <div class="kind-filters" role="group" aria-label="Types of change to show">{kind_buttons}</div>
        <label class="breaking-only"><input type="checkbox" id="breaking-only"> Breaking changes only</label>
        <p id="version-summary" class="version-summary" role="status" aria-live="polite"></p>
      </section>

      <div id="version-list" data-language="{html.escape(slug)}" data-track="{html.escape(track["id"])}">
        {"".join(blocks)}
      </div>
      <p id="version-empty" class="version-empty" hidden>No changes match these choices.</p>
    </div>

    <div id="panel-available" class="version-panel" hidden>
      <section class="version-controls" aria-label="Choose a version to check">
        <div class="version-selects">
          <label>My code runs on<select id="available-at">{at_options}</select></label>
          <label class="feature-search">Filter by name<input type="search" id="feature-search" placeholder="for example, optional chaining" autocomplete="off"></label>
        </div>
        <div class="state-filters" role="group" aria-label="States to show">{state_buttons}</div>
        <p id="available-summary" class="version-summary" role="status" aria-live="polite"></p>
      </section>
      <ul id="feature-index" class="feature-index">
        {cards_html}
      </ul>
      <p id="available-empty" class="version-empty" hidden>No features match these choices.</p>
    </div>

    <section class="version-sources">
      <h2>Official sources</h2>
      <p>This history is a summary. The sources below are the reference for exact wording and dates.</p>
      <ul>{links_html}</ul>
    </section>
  </main>

  <script src="{js_path}"></script>
  <script src="{main_js_path}"></script>
</body>
</html>
'''
