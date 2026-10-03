"""Language-agnostic helpers for the versioning model.

A language defines an ordered list of ``versions``. Each ``feature`` carries a ``history`` of
lifecycle events (added, changed, deprecated, removed) that refer to those versions. Nothing here
is specific to one language, and every comparison uses the integer ``order`` of a version, never
its label.
"""

from __future__ import annotations

from typing import Any

EVENT_KINDS = ("added", "changed", "deprecated", "removed")
CATEGORIES = ("syntax", "library", "behavior", "tooling")
VERSION_STATUSES = ("released", "draft")
STATES = ("not-yet", "available", "deprecated", "restricted", "removed")

KIND_LABELS = {
    "added": "Added",
    "changed": "Changed",
    "deprecated": "Deprecated",
    "removed": "Removed",
}


def versions_for(data: dict[str, Any], language_slug: str) -> list[dict[str, Any]]:
    versions = [v for v in data.get("versions", []) if v.get("language") == language_slug]
    return sorted(versions, key=lambda v: int(v["order"]))


def features_for(data: dict[str, Any], language_slug: str) -> list[dict[str, Any]]:
    return [f for f in data.get("features", []) if f.get("language") == language_slug]


def has_versioning(data: dict[str, Any], language_slug: str) -> bool:
    return bool(versions_for(data, language_slug))


def version_orders(versions: list[dict[str, Any]]) -> dict[str, int]:
    return {v["id"]: int(v["order"]) for v in versions}


def event_order(event: dict[str, Any], orders: dict[str, int]) -> int | None:
    """Order of the version an event refers to, or None for an undated event."""
    version = event.get("version")
    return None if version is None else orders[version]


def added_order(feature: dict[str, Any], orders: dict[str, int]) -> int:
    return orders[feature["history"][0]["version"]]


def lifecycle_state(feature: dict[str, Any], orders: dict[str, int], at_order: int) -> str:
    """State of a feature in the version with the given order.

    ``added: V`` means available in V. ``removed: V`` means not available in V, or "restricted"
    when the removal has a ``scope`` (for example strict mode only) and the feature still works
    elsewhere. A deprecation with no version applies to every version in which the feature exists.
    """
    if at_order < added_order(feature, orders):
        return "not-yet"
    state = "available"
    for event in feature["history"]:
        order = event_order(event, orders)
        kind = event["kind"]
        if kind == "deprecated" and (order is None or at_order >= order):
            state = "deprecated"
        elif kind == "removed" and at_order >= order:
            return "restricted" if event.get("scope") else "removed"
    return state


def changes_between(
    data: dict[str, Any], language_slug: str, from_order: int, to_order: int
) -> list[dict[str, Any]]:
    """Dated events with from_order < version order <= to_order, oldest first.

    Each item is ``{"feature": ..., "event": ..., "order": ...}``. Undated events are not included.
    """
    orders = version_orders(versions_for(data, language_slug))
    found: list[dict[str, Any]] = []
    for feature in features_for(data, language_slug):
        for event in feature["history"]:
            order = event_order(event, orders)
            if order is not None and from_order < order <= to_order:
                found.append({"feature": feature, "event": event, "order": order})
    found.sort(key=lambda item: (item["order"], item["feature"]["title"].lower()))
    return found


def is_breaking(event: dict[str, Any]) -> bool:
    return event["kind"] == "removed" or bool(event.get("breaking"))


def short_label(version: dict[str, Any]) -> str:
    """Label without a trailing qualifier such as "(baseline)"."""
    return version["label"].split(" (")[0]


def lifecycle_facts(feature: dict[str, Any], versions_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """What a reader wants to know about a feature at a glance."""
    history = feature["history"]
    deprecated = next((e for e in history if e["kind"] == "deprecated"), None)
    removed = next((e for e in history if e["kind"] == "removed"), None)
    return {
        "added": versions_by_id[history[0]["version"]],
        "deprecated": deprecated,
        "deprecated_version": versions_by_id[deprecated["version"]] if deprecated and deprecated["version"] else None,
        "removed": removed,
        "removed_version": versions_by_id[removed["version"]] if removed else None,
        "changed_versions": [versions_by_id[e["version"]] for e in history if e["kind"] == "changed"],
    }
