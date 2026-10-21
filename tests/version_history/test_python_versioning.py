"""Tests for the Python version history: the track, its versions and dates, the Python 2 to 3 changes,
the replaced_by links, and how the version page renders them.

These guard rules the data has to keep (and a few facts that were checked against Python's own sources),
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
from versioning import features_for, history_for, lifecycle_state, tracks_for, version_orders, versions_for

LANG = "python"
TRACK = "python"

# Release and end-of-life dates from Python's release-cycle data (https://peps.python.org/api/release-cycle.json),
# checked on 2026-10-15. "py2" is dated at the Python 2.6 release so that it sorts before 3.0, and its end of
# life is the one for Python 2 as a whole. Versions that are still supported only have a month for their end
# of life; the test accepts that being refined to a day.
ENDED = {
    "py2": ("2008-10-01", "2020-01-01"),
    "py3.0": ("2008-12-03", "2009-06-27"),
    "py3.1": ("2009-06-27", "2012-04-09"),
    "py3.2": ("2011-02-20", "2016-02-20"),
    "py3.3": ("2012-09-29", "2017-09-29"),
    "py3.4": ("2014-03-16", "2019-03-18"),
    "py3.5": ("2015-09-13", "2020-09-30"),
    "py3.6": ("2016-12-23", "2021-12-23"),
    "py3.7": ("2018-06-27", "2023-06-27"),
    "py3.8": ("2019-10-14", "2024-10-07"),
    "py3.9": ("2020-10-05", "2025-10-31"),
    "py3.10": ("2021-10-04", "2026-10-01"),
}
SUPPORTED = {
    "py3.11": ("2022-10-24", "2027-10"),
    "py3.12": ("2023-10-02", "2028-10"),
    "py3.13": ("2024-10-07", "2029-10"),
    "py3.14": ("2025-10-07", "2030-10"),
    "py3.15": ("2026-10-09", "2031-10"),
}

# Python 2 features that Python 3.0 removed outright, and the two it changed in a way that breaks old code.
REMOVED_IN_3_0 = {
    "print-statement", "unicode-type", "dict-has-key", "xrange", "raw-input", "except-comma", "exec-statement",
    "backtick-repr", "diamond-not-equal", "long-type", "classic-classes", "dict-iter-methods", "cmp-and-ordering",
    "implicit-relative-imports",
}
CHANGED_IN_3_0 = {"true-division", "stdlib-renames"}

# Old feature -> its replacement. The direction matters: replaced_by sits on the feature being retired.
KNOWN_REPLACEMENTS = {
    "print-statement": ["print-function"],
    "unicode-type": ["text-and-bytes"],
    "typing-collection-aliases": ["builtin-generics"],
    "postponed-annotations": ["deferred-annotations"],
    "asyncio-coroutine-decorator": ["async-await"],
    "asyncore-asynchat-smtpd": ["asyncio-module"],
}


def version_key(version_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"py(\d+)(?:\.(\d+))?", version_id)
    assert match, version_id
    return int(match.group(1)), int(match.group(2) or 0)


def events(feature: dict, kind: str) -> list[dict]:
    return [e for e in history_for(feature, TRACK) if e["kind"] == kind]


class PythonVersionDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.track = tracks_for(self.data, LANG)[0]
        self.versions = versions_for(self.data, LANG, TRACK)
        self.features = features_for(self.data, LANG, TRACK)
        self.by_slug = {f["slug"]: f for f in self.features}
        self.orders = version_orders(self.versions)

    def test_python_has_one_standard_track_whose_releases_are_called_versions(self) -> None:
        self.assertEqual([t["id"] for t in tracks_for(self.data, LANG)], [TRACK])
        self.assertEqual(self.track["kind"], "standard")
        self.assertEqual(self.track["label"], "Python")
        self.assertEqual(self.track["version_noun"], "version")
        self.assertTrue(self.track["changelog_links"])
        for link in self.track["changelog_links"]:
            self.assertTrue(link["url"].startswith("https://"), link)

    def test_versions_run_from_the_python_2_baseline_through_python_3_without_gaps(self) -> None:
        ids = [v["id"] for v in self.versions]
        self.assertEqual(ids[:2], ["py2", "py3.0"])
        minors = [version_key(i)[1] for i in ids[1:]]
        self.assertEqual(minors, list(range(len(minors))), "Python 3 versions must be consecutive from 3.0")
        self.assertEqual([v["order"] for v in self.versions], list(range(1, len(ids) + 1)))
        released = [v["released"] for v in self.versions]
        self.assertEqual(released, sorted(released), "versions must be in release order")
        self.assertEqual(len(set(released)), len(released))

    def test_every_listed_version_is_released_so_nothing_unreleased_is_presented_as_available(self) -> None:
        self.assertEqual({v["status"] for v in self.versions}, {"released"})

    def test_the_python_2_baseline_sorts_before_python_3_and_only_holds_added_events(self) -> None:
        baseline, first = self.versions[0], self.versions[1]
        self.assertEqual(baseline["id"], "py2")
        self.assertIn("baseline", baseline["label"])
        self.assertLess(baseline["released"], first["released"])
        for feature in self.features:
            for event in history_for(feature, TRACK):
                if event["version"] == "py2":
                    self.assertEqual(event["kind"], "added", f"{feature['slug']}: the baseline can only introduce features")

    def test_release_and_end_of_life_dates_match_the_official_release_cycle(self) -> None:
        by_id = {v["id"]: v for v in self.versions}
        for version_id, (released, end_of_life) in ENDED.items():
            self.assertEqual((by_id[version_id]["released"], by_id[version_id]["end_of_life"]), (released, end_of_life), version_id)
        for version_id, (released, month) in SUPPORTED.items():
            self.assertEqual(by_id[version_id]["released"], released, version_id)
            self.assertTrue(by_id[version_id]["end_of_life"].startswith(month), f"{version_id}: {by_id[version_id]['end_of_life']}")

    def test_every_end_of_life_is_a_valid_date_after_the_release(self) -> None:
        for version in self.versions:
            end = version["end_of_life"]
            self.assertRegex(end, r"^\d{4}-\d{2}(-\d{2})?$", version["id"])
            self.assertGreater(end, version["released"], version["id"])

    def test_python_2_to_3_changes_are_pinned_and_all_start_from_the_baseline(self) -> None:
        removed = {f["slug"] for f in self.features if any(e["version"] == "py3.0" for e in events(f, "removed"))}
        changed = {f["slug"] for f in self.features if any(e["version"] == "py3.0" for e in events(f, "changed"))}
        self.assertEqual(removed, REMOVED_IN_3_0)
        self.assertEqual(changed, CHANGED_IN_3_0)
        for slug in REMOVED_IN_3_0 | CHANGED_IN_3_0:
            self.assertEqual([e["version"] for e in events(self.by_slug[slug], "added")], ["py2"], f"{slug} must come from the Python 2 baseline")

    def test_changes_that_break_python_2_code_are_flagged_as_breaking(self) -> None:
        for slug in CHANGED_IN_3_0:
            change = next(e for e in events(self.by_slug[slug], "changed") if e["version"] == "py3.0")
            self.assertTrue(change.get("breaking"), slug)

    def test_every_python_2_removal_tells_the_reader_what_to_do_instead(self) -> None:
        for slug in REMOVED_IN_3_0:
            feature = self.by_slug[slug]
            self.assertTrue(feature.get("migration") or feature.get("replaced_by"), f"{slug} has no migration and no replacement")

    def test_replaced_by_covers_the_known_replacements(self) -> None:
        for slug, replacements in KNOWN_REPLACEMENTS.items():
            self.assertEqual(self.by_slug[slug].get("replaced_by"), replacements, slug)

    def test_a_replacement_already_existed_when_the_old_feature_was_retired_and_still_works(self) -> None:
        latest = max(self.orders.values())
        for feature in self.features:
            for target_slug in feature.get("replaced_by", []):
                self.assertIn(target_slug, self.by_slug, f"{feature['slug']} -> {target_slug}")
                target = self.by_slug[target_slug]
                retired = [e for e in history_for(feature, TRACK) if e["kind"] in ("deprecated", "removed")]
                self.assertTrue(retired, f"{feature['slug']} names a replacement but is neither deprecated nor removed")
                first_retirement = min(version_key(e["version"]) for e in retired)
                target_added = version_key(events(target, "added")[0]["version"])
                self.assertLessEqual(target_added, first_retirement, f"{target_slug} arrived after {feature['slug']} was retired")
                self.assertEqual(lifecycle_state(target, TRACK, self.orders, latest), "available", f"{target_slug} should be live")


class PythonVersionPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.language = next(l for l in self.data["languages"] if l["slug"] == LANG)
        self.track = tracks_for(self.data, LANG)[0]
        self.versions = versions_for(self.data, LANG, TRACK)
        self.features = features_for(self.data, LANG, TRACK)
        self.page = render_versions_page(self.language, self.track, self.data, page_rel="python/versions/index.html")

    def block(self, version_id: str) -> str:
        match = re.search(rf'<section class="version-block" id="v-{re.escape(version_id)}".*?</section>', self.page, re.S)
        self.assertIsNotNone(match, f"no block for {version_id}")
        return match.group(0)

    def test_the_page_says_versions_never_editions(self) -> None:
        self.assertIn("between Python versions.", self.page)
        self.assertNotIn("edition", self.page.lower())

    def test_every_version_has_a_block_and_every_feature_appears_once(self) -> None:
        for version in self.versions:
            self.assertIn(f'id="v-{version["id"]}" data-order="{version["order"]}" data-status="released"', self.page)
            self.assertIn(f'<option value="{version["id"]}"', self.page)
        for feature in self.features:
            self.assertEqual(self.page.count(f'id="feature-{feature["slug"]}"'), 1, feature["slug"])

    def test_the_python_3_0_block_lists_the_removals_and_breaking_changes(self) -> None:
        block = self.block("py3.0")
        self.assertEqual(block.count("kind-removed"), 2 * len(REMOVED_IN_3_0), "each removal has a list item and a badge")
        self.assertEqual(block.count('data-breaking="true"'), len(REMOVED_IN_3_0) + len(CHANGED_IN_3_0))

    def test_month_only_end_of_life_dates_render_as_months(self) -> None:
        self.assertIn('data-eol="2027-10" data-eol-text="October 2027"', self.page)
        self.assertIn("Support ends October 2031", self.page)

    def test_the_baseline_is_labelled_as_such(self) -> None:
        self.assertIn("<h2>Python 2.7 (baseline)</h2>", self.page)

    def test_topic_pages_show_the_python_2_removals_as_version_notes(self) -> None:
        page = render_language_page(self.language, self.data, page_rel="python/index.html")
        self.assertIn('class="version-notes"', page)
        self.assertIn("Removed in Python 3.0", page)
        self.assertIn("Since Python 2.7", page)


if __name__ == "__main__":
    unittest.main()
