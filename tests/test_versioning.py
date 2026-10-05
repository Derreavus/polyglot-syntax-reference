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
    primary_track,
    release_text,
    track_page_rel,
    tracks_for,
    version_orders,
    versions_for,
)

ES = "ecmascript"
NODE = "node"


def feature(data: dict, slug: str) -> dict:
    return next(f for f in data["features"] if f["language"] == "javascript" and f["slug"] == slug)


def es_history(data: dict, slug: str) -> list:
    return feature(data, slug)["history"][ES]


def track(data: dict, track_id: str) -> dict:
    return next(t for t in data["tracks"] if t["language"] == "javascript" and t["id"] == track_id)


def js(data: dict) -> dict:
    return next(l for l in data["languages"] if l["slug"] == "javascript")


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

    # ---- tracks
    def test_duplicate_track_id_and_order(self) -> None:
        self.assert_invalid("duplicate track ids", lambda d: track(d, NODE).update(id=ES))
        self.assert_invalid("duplicate track order", lambda d: track(d, NODE).update(order=1))

    def test_track_kind_and_description(self) -> None:
        self.assert_invalid("kind must be one of", lambda d: track(d, NODE).update(kind="compiler"))
        self.assert_invalid("description must be a non-empty", lambda d: track(d, NODE).update(description=" "))

    def test_every_track_needs_versions_and_https_sources(self) -> None:
        def no_versions(d: dict) -> None:
            d["versions"] = [v for v in d["versions"] if v["track"] != NODE]
            for f in d["features"]:
                f["history"].pop(NODE, None)
            d["features"] = [f for f in d["features"] if f["history"]]
        self.assert_invalid("has no versions", no_versions)
        self.assert_invalid("changelog_links must be a non-empty list", lambda d: track(d, NODE).update(changelog_links=[]))
        self.assert_invalid("https://", lambda d: track(d, NODE)["changelog_links"][0].update(url="http://x.dev"))

    def test_language_level_changelog_links_are_no_longer_allowed(self) -> None:
        self.assert_invalid("move changelog_links onto its track", lambda d: js(d).update(changelog_links=[{"title": "x", "url": "https://x.dev"}]))

    # ---- versions
    def test_version_must_name_an_existing_track(self) -> None:
        self.assert_invalid("unknown track", lambda d: d["versions"][0].update(track="deno"))

    def test_version_ids_are_unique_per_track_not_per_language(self) -> None:
        def clash(d: dict) -> None:
            d["versions"][1].update(id=d["versions"][0]["id"])
        self.assert_invalid("duplicate version ids", clash)

        def same_id_other_track(d: dict) -> None:
            node_first = next(v for v in d["versions"] if v["track"] == NODE)
            node_first["id"] = "es5"
            for f in d["features"]:
                for e in f["history"].get(NODE, []):
                    if e["version"] == "node-0.10":
                        e["version"] = "es5"
        validate_data_model_ok = copy.deepcopy(self.data)
        same_id_other_track(validate_data_model_ok)
        validate_data_model(validate_data_model_ok)

    def test_order_is_independent_per_track(self) -> None:
        self.assertEqual(versions_for(self.data, "javascript", ES)[0]["order"], 1)
        self.assertEqual(versions_for(self.data, "javascript", NODE)[0]["order"], 1)

    def test_duplicate_order_and_date_rules_apply_within_a_track(self) -> None:
        self.assert_invalid("duplicate version order", lambda d: d["versions"][1].update(order=1))
        self.assert_invalid("dated before", lambda d: d["versions"][3].update(released="2014-01"))
        self.assert_invalid("comes after draft", lambda d: d["versions"][12].update(status="draft"))

    def test_status_and_date_format(self) -> None:
        self.assert_invalid("status must be", lambda d: d["versions"][0].update(status="beta"))
        self.assert_invalid("released must look like", lambda d: d["versions"][0].update(released="Dec 1999"))

    def test_support_metadata_is_validated(self) -> None:
        def node_version(d: dict, version_id: str) -> dict:
            return next(v for v in d["versions"] if v["track"] == NODE and v["id"] == version_id)
        self.assert_invalid("end_of_life must look like", lambda d: node_version(d, "node-18").update(end_of_life="April 2025"))
        self.assert_invalid("end_of_life is before released", lambda d: node_version(d, "node-18").update(end_of_life="2020-01-01"))
        self.assert_invalid("lts_from is before released", lambda d: node_version(d, "node-18").update(lts_from="2020-01-01"))
        self.assert_invalid("codename must be", lambda d: node_version(d, "node-18").update(codename=""))

    def test_unknown_keys_are_rejected(self) -> None:
        self.assert_invalid("unknown keys", lambda d: d["versions"][0].update(colour="red"))
        self.assert_invalid("unknown keys", lambda d: d["tracks"][0].update(colour="red"))
        self.assert_invalid("unknown keys", lambda d: d["features"][0].update(since="es5"))
        self.assert_invalid("unknown keys", lambda d: d["features"][0]["history"][ES][0].update(url="https://x.dev"))

    # ---- features and history
    def test_feature_language_must_exist_and_have_versions(self) -> None:
        self.assert_invalid("unknown language", lambda d: d["features"][0].update(language="cobol"))
        self.assert_invalid("has features but no versions", lambda d: d["features"][0].update(language="python"))

    def test_history_must_name_known_tracks(self) -> None:
        self.assert_invalid("unknown track", lambda d: feature(d, "let-const")["history"].update(deno=[{"version": "x", "kind": "added"}]))
        self.assert_invalid("history must map track ids", lambda d: feature(d, "let-const").update(history={}))
        self.assert_invalid("history must map track ids", lambda d: feature(d, "let-const").update(history=[]))

    def test_event_versions_must_belong_to_the_events_own_track(self) -> None:
        self.assert_invalid("unknown version", lambda d: es_history(d, "let-const")[0].update(version="node-18"))

    def test_duplicate_feature_slug_and_topic(self) -> None:
        self.assert_invalid("duplicate feature slug", lambda d: d["features"][1].update(slug=d["features"][0]["slug"]))
        self.assert_invalid("does not exist for javascript", lambda d: feature(d, "let-const").update(topic="nope"))

    def test_first_event_must_be_added(self) -> None:
        self.assert_invalid("first event must be 'added'", lambda d: feature(d, "array-includes")["history"].update({ES: [{"version": "es2017", "kind": "changed", "note": "x"}]}))

    def test_only_one_added_event(self) -> None:
        self.assert_invalid("exactly one 'added'", lambda d: es_history(d, "array-includes").append({"version": "es2018", "kind": "added"}))

    def test_removed_must_be_last_and_after_deprecated(self) -> None:
        self.assert_invalid("'removed' must be the last event", lambda d: es_history(d, "with-statement").append({"version": "es2015", "kind": "changed", "note": "x"}))

        def same_version(d: dict) -> None:
            es_history(d, "array-includes").extend([
                {"version": "es2018", "kind": "deprecated", "note": "x"},
                {"version": "es2018", "kind": "removed", "note": "x"},
            ])
        self.assert_invalid("removed in a later version", same_version)

        def wrong_order(d: dict) -> None:
            es_history(d, "array-includes").extend([
                {"version": "es2018", "kind": "removed", "note": "x"},
                {"version": None, "kind": "deprecated", "note": "x"},
            ])
        self.assert_invalid("'removed' must be the last event", wrong_order)

    def test_each_track_is_checked_on_its_own(self) -> None:
        def node_removed_before_added(d: dict) -> None:
            feature(d, "crypto-createcipher")["history"][NODE][2]["version"] = "node-0.12"
        self.assert_invalid("must come after the version it was added in|events must be in version order", node_removed_before_added)

        def node_first_not_added(d: dict) -> None:
            feature(d, "buffer-constructor")["history"][NODE].reverse()
        self.assert_invalid("first event must be 'added'", node_first_not_added)

    def test_only_deprecation_may_be_undated_and_needs_a_note(self) -> None:
        self.assert_invalid("only a deprecation can omit its version", lambda d: es_history(d, "let-const")[0].update(version=None))

        def no_note(d: dict) -> None:
            del es_history(d, "string-substr")[1]["note"]
        self.assert_invalid("undated deprecation needs a note", no_note)

    def test_unknown_version_and_event_order(self) -> None:
        self.assert_invalid("unknown version", lambda d: es_history(d, "let-const")[0].update(version="es2099"))

        def out_of_order(d: dict) -> None:
            es_history(d, "array-includes").extend([
                {"version": "es2020", "kind": "changed", "note": "x"},
                {"version": "es2018", "kind": "changed", "note": "x"},
            ])
        self.assert_invalid("events must be in version order", out_of_order)
        self.assert_invalid("must come after the version it was added in", lambda d: es_history(d, "array-includes").append({"version": "es2016", "kind": "changed", "note": "x"}))

    def test_notes_breaking_and_release_rules(self) -> None:
        def no_note(d: dict) -> None:
            del es_history(d, "for-in-enumeration")[1]["note"]
        self.assert_invalid("needs a note", no_note)
        self.assert_invalid("breaking only applies", lambda d: es_history(d, "let-const")[0].update(breaking=True))
        self.assert_invalid("release must be a non-empty", lambda d: feature(d, "array-at")["history"][NODE][0].update(release=""))
        self.assert_invalid("release needs a dated event", lambda d: es_history(d, "string-substr")[1].update(release="1.0"))

    # ---- replaced_by
    def test_replaced_by_rules(self) -> None:
        self.assert_invalid("unknown feature", lambda d: feature(d, "octal-literals").update(replaced_by=["nope"]))
        self.assert_invalid("cannot point at itself", lambda d: feature(d, "octal-literals").update(replaced_by=["octal-literals"]))
        self.assert_invalid("only makes sense", lambda d: feature(d, "let-const").update(replaced_by=["arrow-functions"]))

    def test_replaced_by_may_link_features_on_different_tracks(self) -> None:
        self.assertEqual(feature(self.data, "import-assertions")["replaced_by"], ["import-attributes"])
        self.assertIn(NODE, feature(self.data, "import-assertions")["history"])
        self.assertNotIn(ES, feature(self.data, "import-assertions")["history"])

    def test_replaced_by_cycle(self) -> None:
        def mutate(d: dict) -> None:
            feature(d, "binary-octal-literals")["history"][ES].append({"version": None, "kind": "deprecated", "note": "x"})
            feature(d, "binary-octal-literals")["replaced_by"] = ["octal-literals"]
        self.assert_invalid("cycle", mutate)

    def test_migration_needs_both_snippets(self) -> None:
        def mutate(d: dict) -> None:
            del feature(d, "let-const")["migration"]["legacy"]
        self.assert_invalid("migration.legacy", mutate)


class VersioningLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.es = version_orders(versions_for(self.data, "javascript", ES))
        self.node = version_orders(versions_for(self.data, "javascript", NODE))

    def state(self, slug: str, version: str, track_id: str = ES) -> str:
        orders = self.es if track_id == ES else self.node
        return lifecycle_state(feature(self.data, slug), track_id, orders, orders[version])

    def test_tracks_and_primary(self) -> None:
        self.assertEqual([t["id"] for t in tracks_for(self.data, "javascript")], [ES, NODE])
        self.assertEqual(primary_track(self.data, "javascript")["id"], ES)
        self.assertTrue(has_versioning(self.data, "javascript"))
        self.assertFalse(has_versioning(self.data, "python"))

    def test_page_paths(self) -> None:
        self.assertEqual(track_page_rel(self.data, "javascript", ES), "javascript/versions/index.html")
        self.assertEqual(track_page_rel(self.data, "javascript", NODE), "javascript/versions/node/index.html")

    def test_features_can_be_on_one_or_both_tracks(self) -> None:
        es_only = {f["slug"] for f in features_for(self.data, "javascript", ES)}
        node_only = {f["slug"] for f in features_for(self.data, "javascript", NODE)}
        self.assertIn("array-at", es_only & node_only)
        self.assertIn("crypto-createcipher", node_only - es_only)
        self.assertIn("math-sumprecise", es_only - node_only)

    def test_added_means_available_in_that_version(self) -> None:
        self.assertEqual(self.state("let-const", "es5"), "not-yet")
        self.assertEqual(self.state("let-const", "es2015"), "available")

    def test_scoped_removal_is_restricted_not_removed(self) -> None:
        self.assertEqual(self.state("with-statement", "es3"), "available")
        self.assertEqual(self.state("with-statement", "es5"), "restricted")
        self.assertEqual(self.state("with-statement", "es2026"), "restricted")

    def test_unscoped_removal_and_deprecation_ranges(self) -> None:
        synthetic = {"history": {ES: [
            {"version": "es2015", "kind": "added"},
            {"version": "es2017", "kind": "deprecated", "note": "x"},
            {"version": "es2020", "kind": "removed", "note": "x"},
        ]}}
        states = [lifecycle_state(synthetic, ES, self.es, self.es[v]) for v in ("es5", "es2015", "es2017", "es2019", "es2020", "es2026")]
        self.assertEqual(states, ["not-yet", "available", "deprecated", "deprecated", "removed", "removed"])

    def test_undated_deprecation_applies_wherever_the_feature_exists(self) -> None:
        self.assertEqual(self.state("string-substr", "es3"), "deprecated")
        self.assertEqual(self.state("string-substr", "es2026"), "deprecated")

    def test_draft_features_are_not_yet_available_in_released_editions(self) -> None:
        self.assertEqual(self.state("temporal", "es2026"), "not-yet")
        self.assertEqual(self.state("temporal", "es2027"), "available")

    def test_node_track_has_its_own_ordering_and_lifecycle(self) -> None:
        self.assertEqual(self.state("array-at", "node-14", NODE), "not-yet")
        self.assertEqual(self.state("array-at", "node-16", NODE), "available")
        self.assertEqual(self.state("crypto-createcipher", "node-8", NODE), "available")
        self.assertEqual(self.state("crypto-createcipher", "node-10", NODE), "deprecated")
        self.assertEqual(self.state("crypto-createcipher", "node-21", NODE), "deprecated")
        self.assertEqual(self.state("crypto-createcipher", "node-22", NODE), "removed")
        self.assertEqual(self.state("import-assertions", "node-15", NODE), "not-yet")
        self.assertEqual(self.state("import-assertions", "node-21", NODE), "available")
        self.assertEqual(self.state("import-assertions", "node-22", NODE), "removed")

    def test_the_same_feature_can_arrive_in_different_places_on_each_track(self) -> None:
        self.assertEqual(feature(self.data, "array-at")["history"][ES][0]["version"], "es2022")
        self.assertEqual(feature(self.data, "array-at")["history"][NODE][0]["version"], "node-16")
        self.assertEqual(feature(self.data, "array-at")["history"][NODE][0]["release"], "16.6.0")

    def test_range_is_exclusive_of_from_and_inclusive_of_to(self) -> None:
        found = {(c["feature"]["slug"], c["event"]["kind"]) for c in changes_between(self.data, "javascript", ES, self.es["es5"], self.es["es2015"])}
        self.assertIn(("let-const", "added"), found)
        self.assertIn(("strict-mode", "changed"), found)
        self.assertNotIn(("with-statement", "removed"), found)
        self.assertNotIn(("array-includes", "added"), found)

    def test_node_range_only_lists_node_events(self) -> None:
        found = {(c["feature"]["slug"], c["event"]["kind"]) for c in changes_between(self.data, "javascript", NODE, self.node["node-21"], self.node["node-22"])}
        self.assertIn(("crypto-createcipher", "removed"), found)
        self.assertIn(("import-assertions", "removed"), found)
        self.assertNotIn(("let-const", "added"), found)

    def test_range_is_empty_when_from_is_not_older_than_to(self) -> None:
        self.assertEqual(changes_between(self.data, "javascript", ES, self.es["es2020"], self.es["es2020"]), [])
        self.assertEqual(changes_between(self.data, "javascript", ES, self.es["es2020"], self.es["es2015"]), [])

    def test_removed_and_flagged_changes_are_breaking(self) -> None:
        self.assertTrue(is_breaking({"kind": "removed"}))
        self.assertTrue(is_breaking({"kind": "changed", "breaking": True}))
        self.assertFalse(is_breaking({"kind": "changed"}))
        self.assertFalse(is_breaking({"kind": "added"}))

    def test_release_text_narrows_a_version_to_the_exact_release(self) -> None:
        versions = {v["id"]: v for v in versions_for(self.data, "javascript", NODE)}
        self.assertEqual(release_text(versions["node-16"], {"release": "16.6.0"}), "Node.js 16.6")
        self.assertEqual(release_text(versions["node-16"], {"release": "16.14.2"}), "Node.js 16.14.2")
        self.assertEqual(release_text(versions["node-16"], {}), "Node.js 16")
        self.assertEqual(release_text(versions["node-0.10"], {}), "Node.js 0.10")

    def test_node_versions_carry_release_metadata(self) -> None:
        by_id = {v["id"]: v for v in versions_for(self.data, "javascript", NODE)}
        self.assertEqual(by_id["node-22"]["codename"], "Jod")
        self.assertEqual(by_id["node-22"]["engine"], "V8 12.4")
        self.assertEqual(by_id["node-18"]["end_of_life"], "2025-04-30")
        self.assertEqual(by_id["node-0.10"]["order"], 1)
        self.assertEqual([v["status"] for v in by_id.values()].count("released"), len(by_id))


class VersionPageRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.language = js(self.data)
        self.es_track = track(self.data, ES)
        self.node_track = track(self.data, NODE)
        self.page = render_versions_page(self.language, self.es_track, self.data, page_rel="javascript/versions/index.html")
        self.node_page = render_versions_page(self.language, self.node_track, self.data, page_rel="javascript/versions/node/index.html")

    def test_each_track_page_lists_only_its_own_versions_and_features(self) -> None:
        for version in versions_for(self.data, "javascript", ES):
            self.assertIn(f'<option value="{version["id"]}"', self.page)
            self.assertNotIn(f'<option value="{version["id"]}"', self.node_page)
        for item in features_for(self.data, "javascript", ES):
            self.assertIn(f'id="feature-{item["slug"]}"', self.page)
        self.assertNotIn('id="feature-crypto-createcipher"', self.page)
        self.assertIn('id="feature-crypto-createcipher"', self.node_page)
        self.assertNotIn('id="feature-math-sumprecise"', self.node_page)

    def test_track_tabs_link_the_pages_and_mark_the_current_one(self) -> None:
        self.assertIn('class="track-tab" href="index.html" aria-current="page"', self.page)
        self.assertIn('href="node/index.html"', self.page)
        self.assertIn('href="../index.html"', self.node_page)
        self.assertIn('href="index.html" aria-current="page"', self.node_page)

    def test_newest_version_comes_first_and_drafts_are_labeled(self) -> None:
        self.assertLess(self.page.index('id="v-es2027"'), self.page.index('id="v-es2015"'))
        self.assertIn('class="draft-badge">Draft', self.page)
        self.assertIn('<option value="es2026" data-order="14" selected>', self.page)
        self.assertNotIn("draft-badge", self.node_page)

    def test_node_release_metadata_is_shown(self) -> None:
        self.assertIn('class="codename-badge">Jod', self.node_page)
        self.assertIn("V8 12.4", self.node_page)
        self.assertIn("Long-term support from October 2024", self.node_page)
        self.assertIn('data-eol="2025-04-30" data-eol-text="April 2025">Support ends April 2025', self.node_page)
        self.assertIn('class="release-tag">from 16.14.0', self.node_page)

    def test_removals_are_flagged_breaking_and_show_their_scope(self) -> None:
        self.assertIn('class="breaking-badge">Breaking', self.page)
        self.assertIn('class="change-scope">strict mode only', self.page)

    def test_undated_deprecations_have_their_own_section(self) -> None:
        self.assertIn('id="v-undated"', self.page)
        self.assertIn("Deprecated, with no removal planned", self.page)
        self.assertIn("No edition has deprecated", self.page)
        self.assertNotIn('id="v-undated"', self.node_page)

    def test_each_page_shows_its_own_track_sources(self) -> None:
        for link in self.es_track["changelog_links"]:
            self.assertIn(link["url"], self.page)
            self.assertNotIn(link["url"], self.node_page)
        for link in self.node_track["changelog_links"]:
            self.assertIn(link["url"], self.node_page)

    def test_features_link_to_where_else_they_are_tracked(self) -> None:
        self.assertIn('Also tracked on <a href="node/index.html#feature-array-at">Node.js: Node.js 16.6+</a>', self.page)
        self.assertIn('href="../index.html#feature-array-at">ECMAScript: ES2022</a>', self.node_page)
        self.assertNotIn("Also tracked on", render_versions_page(
            self.language, self.es_track, _without_node_history(self.data, "array-at"), page_rel="javascript/versions/index.html"
        ).split('id="feature-array-at"')[1].split("</li>")[0])

    def test_topic_links_resolve_from_each_page_depth(self) -> None:
        self.assertIn('href="../index.html#variables"', self.page)
        self.assertIn('href="../../index.html#variables"', self.node_page)

    def test_code_and_text_are_escaped(self) -> None:
        data = copy.deepcopy(self.data)
        feature(data, "let-const")["migration"]["modern"] = "if (a < b && c > d) {}"
        feature(data, "let-const")["title"] = "let <b>"
        page = render_versions_page(self.language, self.es_track, data, page_rel="javascript/versions/index.html")
        self.assertIn("a &lt; b &amp;&amp; c &gt; d", page)
        self.assertIn("let &lt;b&gt;", page)
        self.assertNotIn("let <b>", page)

    def test_asset_paths_follow_page_depth(self) -> None:
        self.assertIn('href="../../css/style.css"', self.page)
        self.assertIn('href="../../../css/style.css"', self.node_page)
        self.assertIn('src="../../../js/main.js"', self.node_page)

    def test_only_versioned_languages_link_to_their_history(self) -> None:
        javascript_page = render_language_page(self.language, self.data, page_rel="javascript/index.html")
        python = next(l for l in self.data["languages"] if l["slug"] == "python")
        python_page = render_language_page(python, self.data, page_rel="python/index.html")
        self.assertIn('href="versions/index.html"', javascript_page)
        self.assertNotIn("version-history-link", python_page)

    def test_runtime_assets_support_the_pages_and_resolve_urls_from_the_script(self) -> None:
        runtime = (ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8")
        styles = (ROOT / "src" / "static" / "css" / "style.css").read_text(encoding="utf-8")
        self.assertIn("function initVersionsPage()", runtime)
        self.assertIn("function initSupportDates()", runtime)
        self.assertIn("document.currentScript", runtime)
        self.assertNotIn("isNestedPage", runtime)
        self.assertIn(".track-tab", styles)


def _without_node_history(data: dict, slug: str) -> dict:
    copied = copy.deepcopy(data)
    del feature(copied, slug)["history"][NODE]
    return copied


class TopicNotesAndAvailabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.language = js(self.data)
        self.language_page = render_language_page(self.language, self.data, page_rel="javascript/index.html")
        self.es_page = render_versions_page(self.language, track(self.data, ES), self.data, page_rel="javascript/versions/index.html")
        self.node_page = render_versions_page(self.language, track(self.data, NODE), self.data, page_rel="javascript/versions/node/index.html")

    def topic_section(self, slug: str) -> str:
        start = self.language_page.index(f'<section class="topic" id="{slug}">')
        return self.language_page[start:self.language_page.index("</section>", start)]

    def test_topics_list_their_features_in_collapsed_version_notes(self) -> None:
        strings = self.topic_section("strings")
        self.assertIn('<details class="version-notes">', strings)
        self.assertNotIn('<details class="version-notes" open', strings)
        self.assertIn('href="versions/index.html#feature-string-substr"', strings)
        expected = len([f for f in features_for(self.data, "javascript") if f.get("topic") == "strings"])
        self.assertEqual(strings.count("<li><a href="), expected)

    def test_version_notes_show_a_chip_for_each_track(self) -> None:
        collections = self.topic_section("collections")
        self.assertIn('href="versions/index.html#feature-array-at">Since ES2022</a>', collections)
        self.assertIn('href="versions/node/index.html#feature-array-at">Node.js 16.6+</a>', collections)
        self.assertIn("vn-runtime", collections)

    def test_node_only_features_link_to_the_node_page(self) -> None:
        modules = self.topic_section("modules")
        self.assertIn('<li><a href="versions/node/index.html#feature-commonjs-modules">', modules)
        self.assertNotIn('versions/index.html#feature-commonjs-modules', modules)

    def test_version_notes_show_legacy_restricted_changed_removed_and_draft_status(self) -> None:
        self.assertIn(">Legacy<", self.topic_section("strings"))
        self.assertIn("Restricted in ES5 (strict mode only)", self.topic_section("types"))
        self.assertIn("Changed in ES2018", self.topic_section("strings"))
        self.assertIn("Draft in ES2027", self.topic_section("dates"))
        modules = self.topic_section("modules")
        self.assertIn("Node.js: Removed in Node.js 22", modules)

    def test_topics_without_features_and_other_languages_have_no_notes(self) -> None:
        python = next(l for l in self.data["languages"] if l["slug"] == "python")
        python_page = render_language_page(python, self.data, page_rel="python/index.html")
        self.assertNotIn("version-notes", python_page)
        linked = {f["topic"] for f in features_for(self.data, "javascript") if f.get("topic")}
        for slug in {t["slug"] for t in self.data["topics"] if t["language"] == "javascript"} - linked:
            self.assertNotIn("version-notes", self.topic_section(slug))

    def test_every_feature_has_a_card_on_each_track_it_belongs_to(self) -> None:
        for item in features_for(self.data, "javascript", ES):
            self.assertIn(f'id="index-{item["slug"]}"', self.es_page)
        for item in features_for(self.data, "javascript", NODE):
            self.assertIn(f'id="index-{item["slug"]}"', self.node_page)
        self.assertEqual(self.es_page.count('class="feature-card"'), len(features_for(self.data, "javascript", ES)))
        self.assertEqual(self.node_page.count('class="feature-card"'), len(features_for(self.data, "javascript", NODE)))

    def test_cards_carry_the_data_the_browser_needs(self) -> None:
        self.assertIn('data-deprecated="any"', self.es_page)
        self.assertRegex(self.es_page, r'data-removed="2" data-removed-scope="strict mode only"')
        self.assertRegex(self.node_page, r'id="index-crypto-createcipher" data-added="1" data-deprecated="9" data-removed="21"')

    def test_older_and_newer_code_are_shown_for_the_right_states(self) -> None:
        self.assertIn('data-show-when="not-yet"', self.es_page)
        self.assertIn('data-show-when="deprecated restricted removed"', self.es_page)

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
