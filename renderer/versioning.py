"""Language-agnostic helpers for the versioning model.

A language has one or more ``tracks`` (for JavaScript: the ECMAScript editions and the Node.js
releases). Each track has its own ordered list of ``versions``. A ``feature`` keeps a separate
lifecycle ``history`` per track, made of events (added, changed, deprecated, removed) that refer
to that track's versions. Nothing here is specific to one language, and every comparison uses the
integer ``order`` of a version, never its label.
"""

from __future__ import annotations

from typing import Any

EVENT_KINDS = ("added", "changed", "deprecated", "removed")
CATEGORIES = ("syntax", "library", "behavior", "tooling")
VERSION_STATUSES = ("released", "draft")
TRACK_KINDS = ("standard", "runtime", "implementation", "environment")
STATES = ("not-yet", "available", "deprecated", "restricted", "removed")

KIND_LABELS = {
    "added": "Added",
    "changed": "Changed",
    "deprecated": "Deprecated",
    "removed": "Removed",
}


# ---------------------------------------------------------------- tracks and versions
def tracks_for(data: dict[str, Any], language_slug: str) -> list[dict[str, Any]]:
    tracks = [t for t in data.get("tracks", []) if t.get("language") == language_slug]
    return sorted(tracks, key=lambda t: int(t["order"]))


def has_versioning(data: dict[str, Any], language_slug: str) -> bool:
    return bool(tracks_for(data, language_slug))


def primary_track(data: dict[str, Any], language_slug: str) -> dict[str, Any]:
    return tracks_for(data, language_slug)[0]


def versions_for(data: dict[str, Any], language_slug: str, track_id: str) -> list[dict[str, Any]]:
    versions = [
        v for v in data.get("versions", [])
        if v.get("language") == language_slug and v.get("track") == track_id
    ]
    return sorted(versions, key=lambda v: int(v["order"]))


def version_orders(versions: list[dict[str, Any]]) -> dict[str, int]:
    return {v["id"]: int(v["order"]) for v in versions}


def track_page_rel(data: dict[str, Any], language_slug: str, track_id: str) -> str:
    """Path of a track's version page. The primary track keeps the short address."""
    if track_id == primary_track(data, language_slug)["id"]:
        return f"{language_slug}/versions/index.html"
    return f"{language_slug}/versions/{track_id}/index.html"


# ---------------------------------------------------------------- features
def features_for(data: dict[str, Any], language_slug: str, track_id: str | None = None) -> list[dict[str, Any]]:
    """Features of a language, or only those that have a history on the given track."""
    found = [f for f in data.get("features", []) if f.get("language") == language_slug]
    if track_id is None:
        return found
    return [f for f in found if track_id in f["history"]]


def history_for(feature: dict[str, Any], track_id: str) -> list[dict[str, Any]]:
    return feature["history"][track_id]


def event_order(event: dict[str, Any], orders: dict[str, int]) -> int | None:
    """Order of the version an event refers to, or None for an undated event."""
    version = event.get("version")
    return None if version is None else orders[version]


def added_order(feature: dict[str, Any], track_id: str, orders: dict[str, int]) -> int:
    return orders[history_for(feature, track_id)[0]["version"]]


def lifecycle_state(feature: dict[str, Any], track_id: str, orders: dict[str, int], at_order: int) -> str:
    """State of a feature in the version of a track with the given order.

    ``added: V`` means available in V. ``removed: V`` means not available in V, or "restricted"
    when the removal has a ``scope`` (for example strict mode only) and the feature still works
    elsewhere. A deprecation with no version applies to every version in which the feature exists.
    """
    if at_order < added_order(feature, track_id, orders):
        return "not-yet"
    state = "available"
    for event in history_for(feature, track_id):
        order = event_order(event, orders)
        kind = event["kind"]
        if kind == "deprecated" and (order is None or at_order >= order):
            state = "deprecated"
        elif kind == "removed" and at_order >= order:
            return "restricted" if event.get("scope") else "removed"
    return state


def changes_between(
    data: dict[str, Any], language_slug: str, track_id: str, from_order: int, to_order: int
) -> list[dict[str, Any]]:
    """Dated events with from_order < version order <= to_order, oldest first.

    Each item is ``{"feature": ..., "event": ..., "order": ...}``. Undated events are not included.
    """
    orders = version_orders(versions_for(data, language_slug, track_id))
    found: list[dict[str, Any]] = []
    for feature in features_for(data, language_slug, track_id):
        for event in history_for(feature, track_id):
            order = event_order(event, orders)
            if order is not None and from_order < order <= to_order:
                found.append({"feature": feature, "event": event, "order": order})
    found.sort(key=lambda item: (item["order"], item["feature"]["title"].lower()))
    return found


def is_breaking(event: dict[str, Any]) -> bool:
    return event["kind"] == "removed" or bool(event.get("breaking"))


# ---------------------------------------------------------------- presentation helpers
def short_label(version: dict[str, Any]) -> str:
    """Label without a trailing qualifier such as "(baseline)"."""
    return version["label"].split(" (")[0]


def release_text(version: dict[str, Any], event: dict[str, Any]) -> str:
    """Label of a version, narrowed to the exact release when the event names one (Node.js 16.6)."""
    label = short_label(version)
    release = event.get("release")
    if not release:
        return label
    prefix = label.rsplit(" ", 1)[0]
    parts = release.split(".")
    trimmed = ".".join(parts[:2]) if len(parts) >= 3 and parts[2] == "0" else release
    return f"{prefix} {trimmed}"


def lifecycle_facts(
    feature: dict[str, Any], track_id: str, versions_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """What a reader wants to know about a feature on one track at a glance."""
    history = history_for(feature, track_id)
    deprecated = next((e for e in history if e["kind"] == "deprecated"), None)
    removed = next((e for e in history if e["kind"] == "removed"), None)
    return {
        "added": versions_by_id[history[0]["version"]],
        "added_event": history[0],
        "deprecated": deprecated,
        "deprecated_version": versions_by_id[deprecated["version"]] if deprecated and deprecated["version"] else None,
        "removed": removed,
        "removed_version": versions_by_id[removed["version"]] if removed else None,
        "changed_versions": [versions_by_id[e["version"]] for e in history if e["kind"] == "changed"],
    }
