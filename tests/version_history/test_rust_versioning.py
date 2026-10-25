"""Tests for the Rust version history: the two tracks, which releases are listed, the editions, the lifecycles
of retired features, and how the version pages render them.

These guard rules the data has to keep (and facts checked against Rust's own release notes and Edition Guide)
rather than repeating every entry. The general rules for any language live in test_versioning.py.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "renderer"))

from load_data import load_data
from render_language import render_language_page
from render_versions import render_versions_page
from versioning import lifecycle_state, primary_track, tracks_for, version_orders, versions_for

LANG = "rust"
RELEASES, EDITIONS = "rust", "edition"

# Release dates from Rust's release notes (RELEASES.md in rust-lang/rust). Only releases that introduced
# something this reference tracks are listed, so most of the 100 releases from 1.0 to 1.99 are absent.
RELEASE_DATES = {
    "1.0": "2015-05-15", "1.13": "2016-11-10", "1.15": "2017-02-02", "1.20": "2017-08-31", "1.22": "2017-11-22",
    "1.26": "2018-05-10", "1.27": "2018-06-21", "1.28": "2018-08-02", "1.30": "2018-10-25", "1.31": "2018-12-06",
    "1.33": "2019-02-28", "1.36": "2019-07-04", "1.37": "2019-08-15", "1.39": "2019-11-07", "1.42": "2020-03-12",
    "1.50": "2021-02-11", "1.51": "2021-03-25", "1.52": "2021-05-06", "1.53": "2021-06-17", "1.58": "2022-01-13",
    "1.61": "2022-05-19", "1.62": "2022-06-30", "1.63": "2022-08-11", "1.64": "2022-09-22", "1.65": "2022-11-03",
    "1.68": "2023-03-09", "1.70": "2023-06-01", "1.74": "2023-11-16", "1.75": "2023-12-28", "1.77": "2024-03-21",
    "1.79": "2024-06-13", "1.80": "2024-07-25", "1.81": "2024-09-05", "1.82": "2024-10-17", "1.84": "2025-01-09",
    "1.85": "2025-02-20", "1.86": "2025-04-03", "1.88": "2025-06-26", "1.95": "2026-04-16",
}
EDITION_DATES = {"2015": "2015-05-15", "2018": "2018-12-06", "2021": "2021-10-21", "2024": "2025-02-20"}

# What each edition changes or removes (additions are listed separately), from the Edition Guide.
EDITION_CHANGES = {
    "2018": {"anonymous-trait-params", "module-paths", "reserved-keywords"},
    "2021": {"array-into-iter", "bare-trait-objects", "cargo-resolver", "disjoint-closure-capture", "ellipsis-range-patterns",
             "or-patterns-in-macros", "panic-macro-consistency", "prelude-additions", "reserved-prefixes"},
    "2024": {"box-slice-into-iter", "cargo-resolver", "if-let-temporary-scope", "macro-fragment-specifiers",
             "match-ergonomics-reservations", "newly-unsafe-functions", "prelude-additions", "reserved-keywords",
             "rpit-lifetime-capture", "static-mut-references", "tail-expression-temporary-scope", "unsafe-attributes",
             "unsafe-extern", "unsafe-op-in-unsafe-fn"},
}
EDITION_ADDITIONS = {"2018": {"async-await"}, "2021": {"c-string-literals"}, "2024": {"let-chains"}}

# Features Rust retired, and the release that deprecated each (from the release notes).
DEPRECATED_IN = {
    "anonymous-trait-params": 30, "trim-left-right": 33, "bare-trait-objects": 37, "try-macro": 39,
    "mem-uninitialized": 39, "error-description": 42, "atomic-compare-and-swap": 50,
}
KNOWN_REPLACEMENTS = {
    "try-macro": ["question-mark"], "bare-trait-objects": ["dyn-trait"],
    "ellipsis-range-patterns": ["inclusive-ranges"], "mem-uninitialized": ["maybe-uninit"],
}


def minor(version_id: str) -> int:
    return int(version_id.rsplit(".", 1)[1])


def history_for(feature: dict, track: str) -> list[dict]:
    """A feature's events in one track; a Rust feature may belong to only one of the two."""
    return feature["history"].get(track, [])


def events(feature: dict, track: str, kind: str) -> list[dict]:
    return [e for e in history_for(feature, track) if e["kind"] == kind]


class RustVersionDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.tracks = {t["id"]: t for t in tracks_for(self.data, LANG)}
        self.releases = versions_for(self.data, LANG, RELEASES)
        self.editions = versions_for(self.data, LANG, EDITIONS)
        self.features = [f for f in self.data["features"] if f["language"] == LANG]
        self.by_slug = {f["slug"]: f for f in self.features}

    def test_rust_has_a_release_track_first_and_an_edition_track_second(self) -> None:
        self.assertEqual([t["id"] for t in tracks_for(self.data, LANG)], [RELEASES, EDITIONS])
        self.assertEqual(primary_track(self.data, LANG)["id"], RELEASES)
        self.assertEqual((self.tracks[RELEASES]["kind"], self.tracks[RELEASES]["version_noun"]), ("implementation", "release"))
        self.assertEqual(self.tracks[EDITIONS]["kind"], "standard")
        for track in self.tracks.values():
            for link in track["changelog_links"]:
                self.assertTrue(link["url"].startswith("https://"), link)

    def test_only_releases_with_a_tracked_change_are_listed(self) -> None:
        # The owner's rule: a version is listed only if it has a meaningful tracked feature to show.
        for track, versions in ((RELEASES, self.releases), (EDITIONS, self.editions)):
            used = {e["version"] for f in self.features for e in history_for(f, track)}
            for version in versions:
                self.assertIn(version["id"], used, f"{version['id']} has no tracked change, so it should not be listed")

    def test_the_listed_releases_and_their_dates_match_rusts_release_notes(self) -> None:
        listed = {v["id"].split("-", 1)[1]: v["released"] for v in self.releases}
        self.assertEqual(listed, RELEASE_DATES)
        self.assertEqual([v["order"] for v in self.releases], list(range(1, len(self.releases) + 1)))
        minors = [minor(v["id"]) for v in self.releases]
        self.assertEqual(minors, sorted(minors))
        self.assertEqual(self.releases[0]["id"], "rust-1.0")
        self.assertIn("baseline", self.releases[0]["label"])
        self.assertEqual({v["status"] for v in self.releases}, {"released"})

    def test_rust_releases_have_no_end_of_life_because_only_the_latest_is_supported(self) -> None:
        for version in self.releases + self.editions:
            self.assertNotIn("end_of_life", version, version["id"])

    def test_the_two_edition_releases_are_noted_on_the_releases_that_stabilised_them(self) -> None:
        by_id = {v["id"]: v for v in self.releases}
        self.assertIn("2018 edition", by_id["rust-1.31"]["note"])
        self.assertIn("2024 edition", by_id["rust-1.85"]["note"])

    def test_the_editions_and_their_dates(self) -> None:
        self.assertEqual({v["id"][2:]: v["released"] for v in self.editions}, EDITION_DATES)
        self.assertEqual([v["id"] for v in self.editions], ["ed2015", "ed2018", "ed2021", "ed2024"])
        self.assertIn("baseline", self.editions[0]["label"])

    def test_each_edition_changes_exactly_what_the_edition_guide_says(self) -> None:
        for edition, expected in EDITION_CHANGES.items():
            actual = {f["slug"] for f in self.features for e in history_for(f, EDITIONS)
                      if e["version"] == f"ed{edition}" and e["kind"] in ("changed", "removed")}
            self.assertEqual(actual, expected, f"edition {edition}")
        for edition, expected in EDITION_ADDITIONS.items():
            actual = {f["slug"] for f in self.features for e in history_for(f, EDITIONS)
                      if e["version"] == f"ed{edition}" and e["kind"] == "added"}
            self.assertEqual(actual, expected, f"edition {edition} additions")

    def test_changes_that_can_break_existing_code_are_flagged_as_breaking(self) -> None:
        for slug in ("reserved-keywords", "module-paths", "array-into-iter", "panic-macro-consistency", "prelude-additions"):
            for event in history_for(self.by_slug[slug], EDITIONS):
                if event["kind"] == "changed":
                    self.assertTrue(event.get("breaking"), f"{slug} {event['version']}")

    def test_retired_features_were_deprecated_in_the_releases_the_notes_name(self) -> None:
        actual = {f["slug"]: minor(e["version"]) for f in self.features for e in events(f, RELEASES, "deprecated")}
        self.assertEqual(actual, DEPRECATED_IN)

    def test_replaced_by_names_a_live_replacement_that_existed_when_the_old_feature_was_retired(self) -> None:
        for slug, replacements in KNOWN_REPLACEMENTS.items():
            self.assertEqual(self.by_slug[slug].get("replaced_by"), replacements, slug)
        orders = version_orders(self.releases)
        latest = max(orders.values())
        for feature in self.features:
            retired = [minor(e["version"]) for e in events(feature, RELEASES, "deprecated")]
            for target_slug in feature.get("replaced_by", []):
                target = self.by_slug[target_slug]
                self.assertEqual(lifecycle_state(target, RELEASES, orders, latest), "available", f"{target_slug} should be live")
                if retired:
                    self.assertLessEqual(minor(events(target, RELEASES, "added")[0]["version"]), min(retired),
                                         f"{target_slug} arrived after {feature['slug']} was deprecated")

    def test_features_present_in_both_tracks_agree_on_their_first_appearance_order(self) -> None:
        # a feature added to the release track and gated by an edition: the data must give both tracks an `added`
        for feature in self.features:
            for track in (RELEASES, EDITIONS):
                if history_for(feature, track):
                    self.assertEqual(history_for(feature, track)[0]["kind"], "added", f"{feature['slug']} in {track}")


class RustVersionPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.language = next(l for l in self.data["languages"] if l["slug"] == LANG)
        self.tracks = {t["id"]: t for t in tracks_for(self.data, LANG)}
        self.features = [f for f in self.data["features"] if f["language"] == LANG]
        self.pages = {
            RELEASES: render_versions_page(self.language, self.tracks[RELEASES], self.data, page_rel="rust/versions/index.html"),
            EDITIONS: render_versions_page(self.language, self.tracks[EDITIONS], self.data, page_rel="rust/versions/edition/index.html"),
        }

    def block(self, track: str, version_id: str) -> str:
        match = re.search(rf'<section class="version-block" id="v-{re.escape(version_id)}".*?</section>', self.pages[track], re.S)
        self.assertIsNotNone(match, f"no block for {version_id}")
        return match.group(0)

    def test_each_page_names_its_versions_correctly(self) -> None:
        self.assertIn("between Rust releases.", self.pages[RELEASES])
        self.assertIn("in each Rust release for Rust", self.pages[RELEASES])
        self.assertIn("between Rust editions.", self.pages[EDITIONS])
        self.assertIn("in each edition for Rust", self.pages[EDITIONS])
        for text in ("editions editions", "edition edition", "releases releases"):
            for page in self.pages.values():
                self.assertNotIn(text, page)

    def test_every_version_has_a_block_and_every_feature_appears_once_on_each_page_it_belongs_to(self) -> None:
        for track in (RELEASES, EDITIONS):
            for version in versions_for(self.data, LANG, track):
                self.assertIn(f'id="v-{version["id"]}" data-order="{version["order"]}" data-status="released"', self.pages[track])
            for feature in self.features:
                expected = 1 if history_for(feature, track) else 0
                self.assertEqual(self.pages[track].count(f'id="feature-{feature["slug"]}"'), expected, f"{feature['slug']} on {track}")

    def test_no_release_block_is_empty(self) -> None:
        for version in versions_for(self.data, LANG, RELEASES):
            self.assertIn("kind-", self.block(RELEASES, version["id"]), f"{version['id']} shows nothing")

    def test_the_2021_edition_block_lists_its_two_removals(self) -> None:
        block = self.block(EDITIONS, "ed2021")
        self.assertEqual(block.count("kind-removed"), 2 * 2, "bare trait objects and ... patterns, each with a list item and a badge")

    def test_the_two_tracks_are_linked_with_tabs_and_the_other_track_page_exists(self) -> None:
        self.assertIn("Rust editions", self.pages[RELEASES])
        self.assertIn("track-tab", self.pages[EDITIONS])

    def test_topic_pages_show_both_kinds_of_availability_chip(self) -> None:
        page = render_language_page(self.language, self.data, page_rel="rust/index.html")
        self.assertRegex(page, r"Rust 1\.\d+\+")
        self.assertIn("Since Rust 2018", page)
        self.assertIn('class="version-notes"', page)


if __name__ == "__main__":
    unittest.main()
