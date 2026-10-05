"""Validation for the versioning model (versions, features, lifecycle events, changelog links)."""

from __future__ import annotations

import re
from typing import Any

from versioning import CATEGORIES, EVENT_KINDS, TRACK_KINDS, VERSION_STATUSES

TRACK_KEYS = {"language", "id", "label", "kind", "order", "description", "changelog_links"}
VERSION_KEYS = {
    "language", "track", "id", "label", "aliases", "released", "order", "status", "note",
    "codename", "lts_from", "end_of_life", "engine",
}
REQUIRED_VERSION_KEYS = {"language", "track", "id", "label", "released", "order", "status"}
FEATURE_KEYS = {
    "language", "slug", "title", "category", "summary", "topic", "history", "replaced_by", "migration",
}
REQUIRED_FEATURE_KEYS = {"language", "slug", "title", "category", "summary", "history"}
EVENT_KEYS = {"version", "kind", "release", "note", "scope", "breaking"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?$")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_versioning(data: dict[str, Any]) -> None:
    tracks = data.get("tracks", [])
    versions = data.get("versions", [])
    features = data.get("features", [])
    _require(isinstance(tracks, list), "data.tracks must be a list")
    _require(isinstance(versions, list), "data.versions must be a list")
    _require(isinstance(features, list), "data.features must be a list")

    languages = {language["slug"]: language for language in data.get("languages", [])}
    for slug, language in languages.items():
        _require(
            "changelog_links" not in language,
            f"language '{slug}': move changelog_links onto its track",
        )
    topic_slugs = {(t["language"], t["slug"]) for t in data.get("topics", [])}

    track_ids = _validate_tracks(tracks, languages)
    orders = _validate_versions(versions, languages, track_ids)
    for language, ids in track_ids.items():
        for track_id in ids:
            _require(
                (language, track_id) in orders,
                f"track '{language}/{track_id}' has no versions",
            )
    _validate_features(features, languages, track_ids, orders, topic_slugs)


def _validate_links(label: str, links: Any) -> None:
    _require(isinstance(links, list) and bool(links), f"{label}.changelog_links must be a non-empty list")
    for index, link in enumerate(links):
        where = f"{label}.changelog_links[{index}]"
        _require(isinstance(link, dict), f"{where} must be an object")
        _require(_non_empty_str(link.get("title")), f"{where}.title must be a non-empty string")
        url = link.get("url")
        _require(isinstance(url, str) and url.startswith("https://"), f"{where}.url must be an https:// URL")


def _validate_tracks(tracks: list[Any], languages: dict[str, Any]) -> dict[str, set[str]]:
    by_language: dict[str, list[dict[str, Any]]] = {}
    for index, track in enumerate(tracks):
        label = f"tracks[{index}]"
        _require(isinstance(track, dict), f"{label} must be an object")
        missing = sorted(TRACK_KEYS - set(track))
        _require(not missing, f"{label} missing keys: {', '.join(missing)}")
        unknown = sorted(set(track) - TRACK_KEYS)
        _require(not unknown, f"{label} has unknown keys: {', '.join(unknown)}")
        language = track["language"]
        _require(language in languages, f"{label} references unknown language '{language}'")
        _require(
            isinstance(track["id"], str) and ID_PATTERN.match(track["id"]) is not None,
            f"{label}: id must be lowercase letters, digits, '.', '_' or '-'",
        )
        label = f"track '{language}/{track['id']}'"
        _require(_non_empty_str(track["label"]), f"{label}: label must be a non-empty string")
        _require(track["kind"] in TRACK_KINDS, f"{label}: kind must be one of {', '.join(TRACK_KINDS)}")
        _require(
            isinstance(track["order"], int) and not isinstance(track["order"], bool) and track["order"] >= 1,
            f"{label}: order must be a positive integer",
        )
        _require(_non_empty_str(track["description"]), f"{label}: description must be a non-empty string")
        _validate_links(label, track["changelog_links"])
        by_language.setdefault(language, []).append(track)

    ids: dict[str, set[str]] = {}
    for language, items in by_language.items():
        names = [t["id"] for t in items]
        _require(len(names) == len(set(names)), f"{language}: duplicate track ids")
        orders = [t["order"] for t in items]
        _require(len(orders) == len(set(orders)), f"{language}: duplicate track order numbers")
        ids[language] = set(names)
    return ids


def _validate_versions(
    versions: list[Any], languages: dict[str, Any], track_ids: dict[str, set[str]]
) -> dict[tuple[str, str], dict[str, int]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for index, version in enumerate(versions):
        label = f"versions[{index}]"
        _require(isinstance(version, dict), f"{label} must be an object")
        missing = sorted(REQUIRED_VERSION_KEYS - set(version))
        _require(not missing, f"{label} missing keys: {', '.join(missing)}")
        unknown = sorted(set(version) - VERSION_KEYS)
        _require(not unknown, f"{label} has unknown keys: {', '.join(unknown)}")
        language, track = version["language"], version["track"]
        _require(language in languages, f"{label} references unknown language '{language}'")
        _require(track in track_ids.get(language, set()), f"{label} references unknown track '{language}/{track}'")
        label = f"version '{language}/{track}#{version['id']}'"
        _require(
            isinstance(version["id"], str) and ID_PATTERN.match(version["id"]) is not None,
            f"{label}: id must be lowercase letters, digits, '.', '_' or '-'",
        )
        _require(_non_empty_str(version["label"]), f"{label}: label must be a non-empty string")
        _require(
            isinstance(version["order"], int) and not isinstance(version["order"], bool) and version["order"] >= 1,
            f"{label}: order must be a positive integer",
        )
        for key in ("released", "lts_from", "end_of_life"):
            if key in version:
                _require(
                    isinstance(version[key], str) and DATE_PATTERN.match(version[key]) is not None,
                    f"{label}: {key} must look like YYYY-MM or YYYY-MM-DD",
                )
        _require(version["status"] in VERSION_STATUSES, f"{label}: status must be one of {', '.join(VERSION_STATUSES)}")
        aliases = version.get("aliases", [])
        _require(
            isinstance(aliases, list) and all(_non_empty_str(a) for a in aliases),
            f"{label}: aliases must be a list of non-empty strings",
        )
        for key in ("note", "codename", "engine"):
            _require(
                key not in version or _non_empty_str(version[key]),
                f"{label}: {key} must be a non-empty string when present",
            )
        if "end_of_life" in version:
            _require(version["end_of_life"] >= version["released"], f"{label}: end_of_life is before released")
        if "lts_from" in version:
            _require(version["lts_from"] >= version["released"], f"{label}: lts_from is before released")
            if "end_of_life" in version:
                _require(version["lts_from"] <= version["end_of_life"], f"{label}: lts_from is after end_of_life")
        grouped.setdefault((language, track), []).append(version)

    orders_by_track: dict[tuple[str, str], dict[str, int]] = {}
    for (language, track), items in grouped.items():
        where = f"{language}/{track}"
        ids = [v["id"] for v in items]
        _require(len(ids) == len(set(ids)), f"{where}: duplicate version ids")
        order_values = [v["order"] for v in items]
        _require(len(order_values) == len(set(order_values)), f"{where}: duplicate version order numbers")
        ordered = sorted(items, key=lambda v: v["order"])
        for earlier, later in zip(ordered, ordered[1:]):
            _require(
                earlier["released"] <= later["released"],
                f"{where}: version '{later['id']}' is dated before '{earlier['id']}' but has a later order",
            )
            _require(
                not (earlier["status"] == "draft" and later["status"] == "released"),
                f"{where}: released version '{later['id']}' comes after draft version '{earlier['id']}'",
            )
        orders_by_track[(language, track)] = {v["id"]: v["order"] for v in items}
    return orders_by_track


def _validate_features(
    features: list[Any],
    languages: dict[str, Any],
    track_ids: dict[str, set[str]],
    orders: dict[tuple[str, str], dict[str, int]],
    topic_slugs: set[tuple[str, str]],
) -> None:
    seen: set[tuple[str, str]] = set()
    by_language: dict[str, dict[str, dict[str, Any]]] = {}
    for index, feature in enumerate(features):
        label = f"features[{index}]"
        _require(isinstance(feature, dict), f"{label} must be an object")
        missing = sorted(REQUIRED_FEATURE_KEYS - set(feature))
        _require(not missing, f"{label} missing keys: {', '.join(missing)}")
        unknown = sorted(set(feature) - FEATURE_KEYS)
        _require(not unknown, f"{label} has unknown keys: {', '.join(unknown)}")
        language = feature["language"]
        _require(language in languages, f"{label} references unknown language '{language}'")
        _require(
            language in track_ids,
            f"{label}: language '{language}' has features but no versions",
        )
        slug = feature["slug"]
        _require(
            isinstance(slug, str) and SLUG_PATTERN.match(slug) is not None,
            f"{label}: slug must be lowercase letters, digits and '-'",
        )
        label = f"feature '{language}#{slug}'"
        _require((language, slug) not in seen, f"duplicate feature slug: {language}#{slug}")
        seen.add((language, slug))
        _require(_non_empty_str(feature["title"]), f"{label}: title must be a non-empty string")
        _require(
            feature["category"] in CATEGORIES,
            f"{label}: category must be one of {', '.join(CATEGORIES)}",
        )
        _require(_non_empty_str(feature["summary"]), f"{label}: summary must be a non-empty string")

        topic = feature.get("topic")
        _require(
            topic is None or (language, topic) in topic_slugs,
            f"{label}: topic '{topic}' does not exist for {language}",
        )
        history = feature["history"]
        _require(isinstance(history, dict) and bool(history), f"{label}: history must map track ids to event lists")
        for track_id, events in history.items():
            _require(
                track_id in track_ids[language],
                f"{label}: history refers to unknown track '{track_id}'",
            )
            _validate_history(f"{label} [{track_id}]", events, orders[(language, track_id)])
        _validate_migration(label, feature.get("migration"))
        by_language.setdefault(language, {})[slug] = feature

    for language, items in by_language.items():
        for slug, feature in items.items():
            label = f"feature '{language}#{slug}'"
            replaced_by = feature.get("replaced_by", [])
            _require(
                isinstance(replaced_by, list) and all(isinstance(r, str) for r in replaced_by),
                f"{label}: replaced_by must be a list of feature slugs",
            )
            kinds = {event["kind"] for events in feature["history"].values() for event in events}
            _require(
                not replaced_by or kinds & {"deprecated", "removed"},
                f"{label}: replaced_by only makes sense on a deprecated or removed feature",
            )
            for target in replaced_by:
                _require(target != slug, f"{label}: replaced_by cannot point at itself")
                _require(target in items, f"{label}: replaced_by references unknown feature '{target}'")
        _require_acyclic(language, items)


def _require_acyclic(language: str, items: dict[str, dict[str, Any]]) -> None:
    state: dict[str, int] = {}

    def visit(slug: str, trail: list[str]) -> None:
        if state.get(slug) == 2:
            return
        _require(state.get(slug) != 1, f"{language}: replaced_by cycle: {' -> '.join(trail + [slug])}")
        state[slug] = 1
        for target in items[slug].get("replaced_by", []):
            visit(target, trail + [slug])
        state[slug] = 2

    for slug in items:
        visit(slug, [])


def _validate_history(label: str, history: Any, orders: dict[str, int]) -> None:
    _require(isinstance(history, list) and history, f"{label}: history must be a non-empty list")
    for position, event in enumerate(history):
        where = f"{label} history[{position}]"
        _require(isinstance(event, dict), f"{where} must be an object")
        unknown = sorted(set(event) - EVENT_KEYS)
        _require(not unknown, f"{where} has unknown keys: {', '.join(unknown)}")
        kind = event.get("kind")
        _require(kind in EVENT_KINDS, f"{where}: kind must be one of {', '.join(EVENT_KINDS)}")
        _require("version" in event, f"{where}: missing version (use null only for an undated deprecation)")
        version = event["version"]
        if version is None:
            _require(kind == "deprecated", f"{where}: only a deprecation can omit its version")
            _require(_non_empty_str(event.get("note")), f"{where}: an undated deprecation needs a note")
        else:
            _require(version in orders, f"{where}: unknown version '{version}'")
        for key in ("note", "scope", "release"):
            _require(
                key not in event or _non_empty_str(event[key]),
                f"{where}: {key} must be a non-empty string when present",
            )
        _require(
            "release" not in event or version is not None,
            f"{where}: release needs a dated event",
        )
        if "breaking" in event:
            _require(isinstance(event["breaking"], bool), f"{where}: breaking must be true or false")
            _require(kind in ("changed", "removed"), f"{where}: breaking only applies to changed or removed events")
        if kind in ("changed", "removed"):
            _require(_non_empty_str(event.get("note")), f"{where}: a {kind} event needs a note")

    kinds = [event["kind"] for event in history]
    _require(kinds[0] == "added", f"{label}: the first event must be 'added'")
    _require(kinds.count("added") == 1, f"{label}: exactly one 'added' event is allowed")
    _require(kinds.count("deprecated") <= 1, f"{label}: at most one 'deprecated' event is allowed")
    _require(kinds.count("removed") <= 1, f"{label}: at most one 'removed' event is allowed")
    if "removed" in kinds:
        _require(kinds[-1] == "removed", f"{label}: 'removed' must be the last event")
        if "deprecated" in kinds:
            _require(
                kinds.index("deprecated") < kinds.index("removed"),
                f"{label}: 'deprecated' must come before 'removed'",
            )

    added_order = orders[history[0]["version"]]
    previous = added_order
    for position, event in enumerate(history[1:], start=1):
        if event["version"] is None:
            continue
        order = orders[event["version"]]
        where = f"{label} history[{position}]"
        _require(order > added_order, f"{where}: must come after the version it was added in")
        _require(order >= previous, f"{where}: events must be in version order")
        previous = order
    if "deprecated" in kinds and "removed" in kinds:
        deprecated = history[kinds.index("deprecated")]["version"]
        removed = history[kinds.index("removed")]["version"]
        if deprecated is not None:
            _require(
                orders[removed] > orders[deprecated],
                f"{label}: a feature must be removed in a later version than it was deprecated",
            )


def _validate_migration(label: str, migration: Any) -> None:
    if migration is None:
        return
    _require(isinstance(migration, dict), f"{label}: migration must be an object")
    _require(
        set(migration) <= {"legacy", "modern", "note"},
        f"{label}: migration may only contain legacy, modern and note",
    )
    for key in ("legacy", "modern"):
        _require(_non_empty_str(migration.get(key)), f"{label}: migration.{key} must be non-empty code")
    _require(
        "note" not in migration or _non_empty_str(migration["note"]),
        f"{label}: migration.note must be a non-empty string when present",
    )
