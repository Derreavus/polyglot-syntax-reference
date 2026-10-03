from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))

from load_data import load_data
from render_language import render_language_page
from render_versions import render_versions_page
from validate_data import validate_data_model
from versioning import (
    changes_between,
    features_for,
    has_versioning,
    is_breaking,
    lifecycle_state,
    version_orders,
    versions_for,
)


def feature(data: dict, slug: str) -> dict:
    return next(f for f in data["features"] if f["language"] == "javascript" and f["slug"] == slug)


class VersioningValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()

    def assert_invalid(self, pattern: str, mutate) -> None:
        data = copy.deepcopy(self.data)
        mutate(data)
        with self.assertRaisesRegex(ValueError, pattern):
            validate_data_model(data)

    def test_real_data_is_valid(self) -> None:
        validate_data_model(copy.deepcopy(self.data))

    # ---- versions
    def test_duplicate_version_id(self) -> None:
        self.assert_invalid("duplicate version ids", lambda d: d["versions"][1].update(id="es3"))

    def test_duplicate_version_order(self) -> None:
        self.assert_invalid("duplicate version order", lambda d: d["versions"][1].update(order=1))

    def test_dates_must_follow_order(self) -> None:
        self.assert_invalid("dated before", lambda d: d["versions"][3].update(released="2014-01"))

    def test_released_version_cannot_follow_a_draft(self) -> None:
        self.assert_invalid("comes after draft", lambda d: d["versions"][12].update(status="draft"))

    def test_status_and_date_format(self) -> None:
        self.assert_invalid("status must be", lambda d: d["versions"][0].update(status="beta"))
        self.assert_invalid("released must look like", lambda d: d["versions"][0].update(released="Dec 1999"))

    def test_unknown_keys_are_rejected(self) -> None:
        self.assert_invalid("unknown keys", lambda d: d["versions"][0].update(colour="red"))
        self.assert_invalid("unknown keys", lambda d: d["features"][0].update(since="es5"))
        self.assert_invalid("unknown keys", lambda d: d["features"][0]["history"][0].update(url="https://x.dev"))

    # ---- features
    def test_feature_language_must_exist_and_have_versions(self) -> None:
        self.assert_invalid("unknown language", lambda d: d["features"][0].update(language="cobol"))
        self.assert_invalid("has features but no versions", lambda d: d["features"][0].update(language="python"))

    def test_duplicate_feature_slug(self) -> None:
        self.assert_invalid("duplicate feature slug", lambda d: d["features"][1].update(slug=d["features"][0]["slug"]))

    def test_topic_must_exist(self) -> None:
        self.assert_invalid("does not exist for javascript", lambda d: feature(d, "let-const").update(topic="nope"))

    def test_first_event_must_be_added(self) -> None:
        def mutate(d: dict) -> None:
            feature(d, "array-includes")["history"] = [{"version": "es2017", "kind": "changed", "note": "x"}]
        self.assert_invalid("first event must be 'added'", mutate)

    def test_only_one_added_event(self) -> None:
        def mutate(d: dict) -> None:
            feature(d, "array-includes")["history"].append({"version": "es2018", "kind": "added"})
        self.assert_invalid("exactly one 'added'", mutate)

    def test_removed_must_be_last(self) -> None:
        def mutate(d: dict) -> None:
            feature(d, "with-statement")["history"].append({"version": "es2015", "kind": "changed", "note": "x"})
        self.assert_invalid("'removed' must be the last event", mutate)

    def test_removed_must_be_later_than_deprecated(self) -> None:
        def mutate(d: dict) -> None:
            feature(d, "array-includes")["history"] += [
                {"version": "es2018", "kind": "deprecated", "note": "x"},
                {"version": "es2018", "kind": "removed", "note": "x"},
            ]
        self.assert_invalid("removed in a later version", mutate)

    def test_deprecated_must_precede_removed(self) -> None:
        def mutate(d: dict) -> None:
            feature(d, "array-includes")["history"] += [
                {"version": "es2018", "kind": "removed", "note": "x"},
                {"version": None, "kind": "deprecated", "note": "x"},
            ]
        self.assert_invalid("'removed' must be the last event", mutate)

    def test_only_deprecation_may_be_undated(self) -> None:
        self.assert_invalid(
            "only a deprecation can omit its version",
            lambda d: feature(d, "let-const")["history"][0].update(version=None),
        )

    def test_undated_deprecation_needs_a_note(self) -> None:
        def mutate(d: dict) -> None:
            del feature(d, "string-substr")["history"][1]["note"]
        self.assert_invalid("undated deprecation needs a note", mutate)

    def test_unknown_version_reference(self) -> None:
        self.assert_invalid("unknown version", lambda d: feature(d, "let-const")["history"][0].update(version="es2099"))

    def test_events_must_be_in_version_order(self) -> None:
        def mutate(d: dict) -> None:
            feature(d, "array-includes")["history"] += [
                {"version": "es2020", "kind": "changed", "note": "x"},
                {"version": "es2018", "kind": "changed", "note": "x"},
            ]
        self.assert_invalid("events must be in version order", mutate)

    def test_events_must_come_after_added(self) -> None:
        def mutate(d: dict) -> None:
            feature(d, "array-includes")["history"].append({"version": "es2016", "kind": "changed", "note": "x"})
        self.assert_invalid("must come after the version it was added in", mutate)

    def test_changed_and_removed_need_notes_and_breaking_is_limited(self) -> None:
        def no_note(d: dict) -> None:
            del feature(d, "for-in-enumeration")["history"][1]["note"]
        self.assert_invalid("needs a note", no_note)
        self.assert_invalid(
            "breaking only applies",
            lambda d: feature(d, "let-const")["history"][0].update(breaking=True),
        )

    # ---- replaced_by
    def test_replaced_by_rules(self) -> None:
        self.assert_invalid("unknown feature", lambda d: feature(d, "octal-literals").update(replaced_by=["nope"]))
        self.assert_invalid("cannot point at itself", lambda d: feature(d, "octal-literals").update(replaced_by=["octal-literals"]))
        self.assert_invalid("only makes sense", lambda d: feature(d, "let-const").update(replaced_by=["arrow-functions"]))

    def test_replaced_by_cycle(self) -> None:
        def mutate(d: dict) -> None:
            feature(d, "binary-octal-literals")["history"].append(
                {"version": None, "kind": "deprecated", "note": "x"}
            )
            feature(d, "binary-octal-literals")["replaced_by"] = ["octal-literals"]
        self.assert_invalid("cycle", mutate)

    # ---- migration and changelog links
    def test_migration_needs_both_snippets(self) -> None:
        def mutate(d: dict) -> None:
            del feature(d, "let-const")["migration"]["legacy"]
        self.assert_invalid("migration.legacy", mutate)

    def test_changelog_links_are_required_and_https(self) -> None:
        def remove(d: dict) -> None:
            next(l for l in d["languages"] if l["slug"] == "javascript").pop("changelog_links")
        self.assert_invalid("no changelog_links", remove)

        def insecure(d: dict) -> None:
            next(l for l in d["languages"] if l["slug"] == "javascript")["changelog_links"][0]["url"] = "http://x.dev"
        self.assert_invalid("https://", insecure)


class VersioningLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.orders = version_orders(versions_for(self.data, "javascript"))

    def state(self, slug: str, version: str) -> str:
        return lifecycle_state(feature(self.data, slug), self.orders, self.orders[version])

    def test_only_languages_with_versions_have_versioning(self) -> None:
        self.assertTrue(has_versioning(self.data, "javascript"))
        self.assertFalse(has_versioning(self.data, "python"))

    def test_added_means_available_in_that_version(self) -> None:
        self.assertEqual(self.state("let-const", "es5"), "not-yet")
        self.assertEqual(self.state("let-const", "es2015"), "available")

    def test_scoped_removal_is_restricted_not_removed(self) -> None:
        self.assertEqual(self.state("with-statement", "es3"), "available")
        self.assertEqual(self.state("with-statement", "es5"), "restricted")
        self.assertEqual(self.state("with-statement", "es2026"), "restricted")

    def test_unscoped_removal_is_removed_from_that_version(self) -> None:
        synthetic = {
            "history": [
                {"version": "es2015", "kind": "added"},
                {"version": "es2017", "kind": "deprecated", "note": "x"},
                {"version": "es2020", "kind": "removed", "note": "x"},
            ]
        }
        states = [lifecycle_state(synthetic, self.orders, self.orders[v]) for v in ("es5", "es2015", "es2017", "es2019", "es2020", "es2026")]
        self.assertEqual(states, ["not-yet", "available", "deprecated", "deprecated", "removed", "removed"])

    def test_undated_deprecation_applies_wherever_the_feature_exists(self) -> None:
        self.assertEqual(self.state("string-substr", "es3"), "deprecated")
        self.assertEqual(self.state("string-substr", "es2026"), "deprecated")

    def test_draft_features_are_not_yet_available_in_released_editions(self) -> None:
        self.assertEqual(self.state("temporal", "es2026"), "not-yet")
        self.assertEqual(self.state("temporal", "es2027"), "available")

    def test_range_is_exclusive_of_from_and_inclusive_of_to(self) -> None:
        found = {(c["feature"]["slug"], c["event"]["kind"]) for c in changes_between(self.data, "javascript", self.orders["es5"], self.orders["es2015"])}
        self.assertIn(("let-const", "added"), found)
        self.assertIn(("strict-mode", "changed"), found)
        self.assertNotIn(("with-statement", "removed"), found)
        self.assertNotIn(("array-includes", "added"), found)

    def test_range_is_empty_when_from_is_not_older_than_to(self) -> None:
        self.assertEqual(changes_between(self.data, "javascript", self.orders["es2020"], self.orders["es2020"]), [])
        self.assertEqual(changes_between(self.data, "javascript", self.orders["es2020"], self.orders["es2015"]), [])

    def test_removed_and_flagged_changes_are_breaking(self) -> None:
        self.assertTrue(is_breaking({"kind": "removed"}))
        self.assertTrue(is_breaking({"kind": "changed", "breaking": True}))
        self.assertFalse(is_breaking({"kind": "changed"}))
        self.assertFalse(is_breaking({"kind": "added"}))


class VersionPageRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.language = next(l for l in self.data["languages"] if l["slug"] == "javascript")
        self.page = render_versions_page(self.language, self.data, page_rel="javascript/versions/index.html")

    def test_every_version_with_events_and_every_feature_is_present(self) -> None:
        for version in versions_for(self.data, "javascript"):
            self.assertIn(f'id="v-{version["id"]}"', self.page)
        for item in features_for(self.data, "javascript"):
            self.assertIn(f'id="feature-{item["slug"]}"', self.page)

    def test_newest_version_comes_first_and_drafts_are_labeled(self) -> None:
        self.assertLess(self.page.index('id="v-es2027"'), self.page.index('id="v-es2015"'))
        self.assertIn('class="draft-badge">Draft', self.page)
        self.assertIn('<option value="es2026" data-order="14" selected>', self.page)

    def test_undated_deprecations_have_their_own_section(self) -> None:
        self.assertIn('id="v-undated"', self.page)
        self.assertIn("Deprecated, with no removal planned", self.page)

    def test_removals_are_flagged_breaking_and_show_their_scope(self) -> None:
        self.assertIn('class="breaking-badge">Breaking', self.page)
        self.assertIn('class="change-scope">strict mode only', self.page)

    def test_changelog_links_are_rendered(self) -> None:
        for link in self.language["changelog_links"]:
            self.assertIn(link["url"], self.page)

    def test_code_and_text_are_escaped(self) -> None:
        data = copy.deepcopy(self.data)
        feature(data, "let-const")["migration"]["modern"] = "if (a < b && c > d) {}"
        feature(data, "let-const")["title"] = "let <b>"
        page = render_versions_page(self.language, data, page_rel="javascript/versions/index.html")
        self.assertIn("a &lt; b &amp;&amp; c &gt; d", page)
        self.assertIn("let &lt;b&gt;", page)
        self.assertNotIn("let <b>", page)

    def test_pages_use_depth_two_asset_paths(self) -> None:
        self.assertIn('href="../../css/style.css"', self.page)
        self.assertIn('src="../../js/main.js"', self.page)

    def test_only_versioned_languages_link_to_their_history(self) -> None:
        javascript_page = render_language_page(self.language, self.data, page_rel="javascript/index.html")
        python = next(l for l in self.data["languages"] if l["slug"] == "python")
        python_page = render_language_page(python, self.data, page_rel="python/index.html")
        self.assertIn('href="versions/index.html"', javascript_page)
        self.assertNotIn("version-history-link", python_page)

    def test_runtime_assets_support_the_page_and_resolve_urls_from_the_script(self) -> None:
        runtime = (ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8")
        styles = (ROOT / "src" / "static" / "css" / "style.css").read_text(encoding="utf-8")
        self.assertIn("function initVersionsPage()", runtime)
        self.assertIn("document.currentScript", runtime)
        self.assertNotIn("isNestedPage", runtime)
        self.assertIn(".kind-filter", styles)


class TopicNotesAndAvailabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.language = next(l for l in self.data["languages"] if l["slug"] == "javascript")
        self.language_page = render_language_page(self.language, self.data, page_rel="javascript/index.html")
        self.versions_page = render_versions_page(self.language, self.data, page_rel="javascript/versions/index.html")

    def topic_section(self, slug: str) -> str:
        start = self.language_page.index(f'<section class="topic" id="{slug}">')
        return self.language_page[start:self.language_page.index("</section>", start)]

    def test_topics_list_their_features_in_collapsed_version_notes(self) -> None:
        strings = self.topic_section("strings")
        self.assertIn('<details class="version-notes">', strings)
        self.assertNotIn("<details class=\"version-notes\" open", strings)
        self.assertIn('href="versions/index.html#feature-string-substr"', strings)
        expected = len([f for f in features_for(self.data, "javascript") if f.get("topic") == "strings"])
        self.assertEqual(strings.count("<li><a href="), expected)

    def test_version_notes_show_legacy_restricted_changed_and_draft_status(self) -> None:
        self.assertIn(">Legacy<", self.topic_section("strings"))
        self.assertIn("Restricted in ES5 (strict mode only)", self.topic_section("types"))
        self.assertIn("Changed in ES2018", self.topic_section("strings"))
        self.assertIn("Draft in ES2027", self.topic_section("dates"))

    def test_topics_without_features_and_other_languages_have_no_notes(self) -> None:
        python = next(l for l in self.data["languages"] if l["slug"] == "python")
        python_page = render_language_page(python, self.data, page_rel="python/index.html")
        self.assertNotIn("version-notes", python_page)
        linked = {f["topic"] for f in features_for(self.data, "javascript") if f.get("topic")}
        for slug in {t["slug"] for t in self.data["topics"] if t["language"] == "javascript"} - linked:
            self.assertNotIn("version-notes", self.topic_section(slug))

    def test_every_feature_has_a_card_with_the_data_the_browser_needs(self) -> None:
        for item in features_for(self.data, "javascript"):
            self.assertIn(f'id="index-{item["slug"]}"', self.versions_page)
        self.assertEqual(self.versions_page.count('class="feature-card"'), len(features_for(self.data, "javascript")))
        self.assertIn('data-deprecated="any"', self.versions_page)
        self.assertRegex(self.versions_page, r'data-removed="2" data-removed-scope="strict mode only"')

    def test_older_and_newer_code_are_shown_for_the_right_states(self) -> None:
        self.assertIn('data-show-when="not-yet"', self.versions_page)
        self.assertIn('data-show-when="deprecated restricted removed"', self.versions_page)

    def test_state_rules_are_mirrored_in_the_browser_script(self) -> None:
        runtime = (ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8")
        self.assertIn("function stateAt(", runtime)
        self.assertIn("lifecycle_state() in renderer/versioning.py", runtime)

    def test_javascript_reference_is_fully_linked_to_real_topics(self) -> None:
        topics = {t["slug"] for t in self.data["topics"] if t["language"] == "javascript"}
        self.assertGreaterEqual(len(topics), 19)
        for item in features_for(self.data, "javascript"):
            if item.get("topic"):
                self.assertIn(item["topic"], topics)


if __name__ == "__main__":
    unittest.main()
