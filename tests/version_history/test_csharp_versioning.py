"""Tests for the C# version history: the three tracks, which versions are listed and their dates, the features that
appear on more than one track, the compatibility differences between C# and each runtime, and how the pages render them.

These guard rules the data has to keep, and facts checked against primary sources, rather than repeating every entry.
The general rules for any language live in test_versioning.py. Sources of the pinned facts:
  - C# release months: "C# version history" (dotnet/docs).
  - .NET release dates, support type and end of life: dotnet/core release feed (releases.json for each channel).
  - .NET Framework lifecycle dates: Microsoft's lifecycle page for .NET Framework (Pacific Time dates).
  - Default C# version per runtime: Microsoft's "C# language versioning" page (net8.0, net10.0 and netstandard2.1 re-checked with the SDK).
  - Compatibility results: Roslyn from .NET SDK 10 against the reference assemblies of each target, at -langversion 14.
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

LANG = "csharp"
CSHARP, DOTNET, NETFX = "csharp", "dotnet", "netfx"

CSHARP_RELEASES = {
    "cs1.0": "2002-01", "cs1.2": "2003-04", "cs2.0": "2005-11", "cs3.0": "2007-11", "cs4.0": "2010-04", "cs5.0": "2012-08",
    "cs6.0": "2015-07", "cs7.0": "2017-03", "cs7.1": "2017-08", "cs7.2": "2017-11", "cs7.3": "2018-05", "cs8.0": "2019-09",
    "cs9.0": "2020-11", "cs10.0": "2021-11", "cs11.0": "2022-11", "cs12.0": "2023-11", "cs13.0": "2024-11", "cs14.0": "2025-11",
}
# id -> (general availability, support type, end of support). .NET Core 1.1 had no tracked change and is not listed.
DOTNET_RELEASES = {
    "core1.0": ("2016-06-27", "lts", "2019-06-27"), "core2.0": ("2017-08-14", "sts", "2018-10-01"),
    "core2.1": ("2018-05-30", "lts", "2021-08-21"), "core2.2": ("2018-12-04", "sts", "2019-12-23"),
    "core3.0": ("2019-09-23", "sts", "2020-03-03"), "core3.1": ("2019-12-03", "lts", "2022-12-13"),
    "net5.0": ("2020-11-10", "sts", "2022-05-10"), "net6.0": ("2021-11-08", "lts", "2024-11-12"),
    "net7.0": ("2022-11-08", "sts", "2024-05-14"), "net8.0": ("2023-11-14", "lts", "2026-11-10"),
    "net9.0": ("2024-12-03", "sts", "2026-11-10"), "net10.0": ("2025-11-11", "lts", "2028-11-14"),
}
# id -> (lifecycle start, lifecycle end or None). Microsoft publishes no end date for 4.7 and later.
NETFX_RELEASES = {
    "fx4.5": ("2012-10-09", "2016-01-12"), "fx4.5.1": ("2014-01-15", "2016-01-12"), "fx4.5.2": ("2014-05-05", "2022-04-26"),
    "fx4.6": ("2015-07-29", "2022-04-26"), "fx4.6.1": ("2015-11-30", "2022-04-26"), "fx4.6.2": ("2016-08-02", "2027-01-12"),
    "fx4.7": ("2017-04-11", None), "fx4.7.1": ("2017-10-17", None), "fx4.7.2": ("2018-04-30", None),
    "fx4.8": ("2019-04-18", None), "fx4.8.1": ("2022-08-09", None),
}
DEFAULT_CSHARP = {"core2.0": "7.3", "core2.1": "7.3", "core2.2": "7.3", "core3.0": "8.0", "core3.1": "8.0", "net5.0": "9.0",
                  "net6.0": "10", "net7.0": "11", "net8.0": "12", "net9.0": "13", "net10.0": "14"}

# Features that appear on more than one track, with the version each track first lists them.
SHARED = {
    "tuples": {CSHARP: "cs7.0", NETFX: "fx4.7"},
    "indices-ranges": {CSHARP: "cs8.0", DOTNET: "core3.0"},
    "async-streams": {CSHARP: "cs8.0", DOTNET: "core3.0"},
    "lock-type": {CSHARP: "cs13.0", DOTNET: "net9.0"},
    "netstandard-2-0": {DOTNET: "core2.0", NETFX: "fx4.7.1"},
}

# Language features the compiler rejects against some runtime's reference assemblies at -langversion 14, and the
# first compiler error. "framework_from" is the first .NET Framework release that accepts it (None = none does).
COMPAT = {
    "tuples": ("CS8179", "fx4.7", True),
    "indices-ranges": ("CS0518", None, True),
    "async-streams": ("CS0234", None, True),
    "default-interface-members": ("CS8701", None, True),
    "static-abstract-members": ("CS8919", None, False),
    "ref-fields": ("CS9064", None, False),
    "covariant-returns": ("CS8830", None, False),
    "records": ("CS0518", None, False),
    "init-setters": ("CS0518", None, False),
    "required-members": ("CS0656", None, False),
    "module-initializers": ("CS0234", None, False),
    "utf8-literals": ("CS0234", None, True),
    "inline-arrays": ("CS0234", None, False),
    "first-class-span": ("CS0234", None, True),
}
# Accepted everywhere the compiler was run, so they carry no compatibility note.
NO_COMPAT_NOTE = {"ref-struct", "in-parameters", "params-collections"}
# Compile once the missing type is defined in source (checked at compile time only).
POLYFILLABLE = {"records", "init-setters", "required-members", "module-initializers"}
COMPAT_PREFIX = "Needs library or runtime support."

# The docs' C# 7.2 list wrongly includes these; Roslyn and csharplang put them in 7.3.
SEVEN_THREE = {
    "generic-constraints-unmanaged-enum": "added", "stackalloc-initializers": "added", "fixed-buffers-no-pinning": "added",
    "custom-fixed": "added", "ref-locals-returns": "changed",
}

FIRST_LISTED = {
    CSHARP: {"generics": "cs2.0", "lambdas": "cs3.0", "async-await": "cs5.0", "string-interpolation": "cs6.0", "out-var": "cs7.0",
             "nullable-reference-types": "cs8.0", "records": "cs9.0", "file-scoped-namespaces": "cs10.0", "raw-string-literals": "cs11.0",
             "primary-constructors": "cs12.0", "params-collections": "cs13.0", "field-keyword": "cs14.0", "stackalloc-initializers": "cs7.3"},
    DOTNET: {"system-text-json": "core3.0", "span-memory": "core2.1", "priority-queue": "net6.0", "frozen-collections": "net8.0",
             "ordered-dictionary": "net9.0", "post-quantum-crypto": "net10.0", "native-aot": "net8.0"},
    NETFX: {"httpclient": "fx4.5", "rsacng": "fx4.6", "isreadonly-attribute": "fx4.7.1", "hashset-trygetvalue": "fx4.7.2",
            "wcf-service-health": "fx4.8", "arm64-native": "fx4.8.1"},
}


def history_for(feature: dict, track: str) -> list[dict]:
    return feature["history"].get(track, [])


class CSharpVersionDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.tracks = {t["id"]: t for t in tracks_for(self.data, LANG)}
        self.versions = {t: versions_for(self.data, LANG, t) for t in (CSHARP, DOTNET, NETFX)}
        self.features = [f for f in self.data["features"] if f["language"] == LANG]
        self.by_slug = {f["slug"]: f for f in self.features}

    def test_three_tracks_language_first_then_dotnet_then_dotnet_framework(self) -> None:
        self.assertEqual([t["id"] for t in tracks_for(self.data, LANG)], [CSHARP, DOTNET, NETFX])
        self.assertEqual(primary_track(self.data, LANG)["id"], CSHARP)
        self.assertEqual([self.tracks[t]["kind"] for t in (CSHARP, DOTNET, NETFX)], ["standard", "runtime", "runtime"])
        for track in self.tracks.values():
            for link in track["changelog_links"]:
                self.assertTrue(link["url"].startswith("https://"), link)

    def test_only_versions_with_a_tracked_change_are_listed(self) -> None:
        for track, versions in self.versions.items():
            used = {e["version"] for f in self.features for e in history_for(f, track)}
            self.assertEqual({v["id"] for v in versions}, used, track)

    def test_csharp_versions_and_their_release_months(self) -> None:
        self.assertEqual({v["id"]: v["released"] for v in self.versions[CSHARP]}, CSHARP_RELEASES)
        self.assertEqual([v["order"] for v in self.versions[CSHARP]], list(range(1, 19)))
        self.assertIn("baseline", self.versions[CSHARP][0]["label"])
        for version in self.versions[CSHARP]:
            self.assertNotIn("end_of_life", version, "a language version has no end of life of its own")

    def test_dotnet_releases_dates_support_type_and_end_of_life_match_the_release_feed(self) -> None:
        listed = {v["id"]: (v["released"], "lts" if "lts_from" in v else "sts", v["end_of_life"]) for v in self.versions[DOTNET]}
        self.assertEqual(listed, DOTNET_RELEASES)
        self.assertNotIn("core1.1", {v["id"] for v in self.versions[DOTNET]})
        for version in self.versions[DOTNET]:
            if "lts_from" in version:
                self.assertEqual(version["lts_from"], version["released"], version["id"])

    def test_dotnet_releases_show_the_default_csharp_version(self) -> None:
        for version in self.versions[DOTNET]:
            expected = DEFAULT_CSHARP.get(version["id"])
            if expected is None:
                self.assertNotIn("Default C# version", version.get("note", ""), version["id"])
            else:
                self.assertIn(f"Default C# version: {expected}.", version["note"], version["id"])

    def test_dotnet_framework_dates_come_from_the_lifecycle_page_and_47_onward_have_no_end_date(self) -> None:
        listed = {v["id"]: (v["released"], v.get("end_of_life")) for v in self.versions[NETFX]}
        self.assertEqual(listed, NETFX_RELEASES)
        for version in self.versions[NETFX]:
            if "end_of_life" not in version:
                self.assertIn("Component Lifecycle Policy", version["note"], version["id"])
        self.assertIn("start of Microsoft's support lifecycle", self.tracks[NETFX]["description"])

    def test_the_features_on_more_than_one_track_are_exactly_the_shared_ones(self) -> None:
        actual = {f["slug"]: {t: history_for(f, t)[0]["version"] for t in f["history"]} for f in self.features if len(f["history"]) > 1}
        self.assertEqual(actual, SHARED)

    def test_first_listing_of_well_known_features(self) -> None:
        for track, expected in FIRST_LISTED.items():
            for slug, version in expected.items():
                self.assertEqual(history_for(self.by_slug[slug], track)[0]["version"], version, f"{slug} on {track}")

    def test_the_five_items_the_docs_wrongly_place_in_72_are_listed_in_73(self) -> None:
        for slug, kind in SEVEN_THREE.items():
            events = [e for e in history_for(self.by_slug[slug], CSHARP) if e["kind"] == kind and e["version"] in ("cs7.2", "cs7.3")]
            self.assertTrue(any(e["version"] == "cs7.3" for e in events), slug)
        for slug in ("generic-constraints-unmanaged-enum", "stackalloc-initializers", "fixed-buffers-no-pinning", "custom-fixed"):
            self.assertEqual(history_for(self.by_slug[slug], CSHARP)[0]["version"], "cs7.3", slug)

    def test_foreach_variable_change_in_csharp_5_is_a_breaking_change(self) -> None:
        events = history_for(self.by_slug["foreach-loop-variable"], CSHARP)
        self.assertEqual([(e["kind"], e["version"]) for e in events], [("added", "cs1.0"), ("changed", "cs5.0")])
        self.assertTrue(events[1]["breaking"])

    def test_httpclienthandler_properties_were_added_in_471_and_only_implemented_in_472(self) -> None:
        events = history_for(self.by_slug["httpclienthandler-properties"], NETFX)
        self.assertEqual([(e["kind"], e["version"]) for e in events], [("added", "fx4.7.1"), ("changed", "fx4.7.2")])

    def test_each_runtime_dependent_language_feature_carries_a_compatibility_note(self) -> None:
        for slug, (code, framework_from, netstandard_ok) in COMPAT.items():
            note = history_for(self.by_slug[slug], CSHARP)[0].get("note", "")
            self.assertTrue(note.startswith(COMPAT_PREFIX), slug)
            self.assertIn(f"({code})", note, slug)
            self.assertIn(".NET 8 and .NET 10 accept it", note, slug)
            self.assertIn("netstandard 2.1 accepts it" if netstandard_ok else "netstandard 2.1 rejects it", note, slug)
            if framework_from is None:
                self.assertIn("does not compile against any .NET Framework 4.5 to 4.8 reference assembly", note, slug)
            else:
                self.assertIn(f"compiles against .NET Framework from {framework_from.removeprefix('fx')} but not before", note, slug)

    def test_features_the_compiler_accepted_everywhere_have_no_compatibility_note(self) -> None:
        for slug in NO_COMPAT_NOTE:
            for event in history_for(self.by_slug[slug], CSHARP):
                self.assertNotIn(COMPAT_PREFIX, event.get("note", ""), slug)
        with_note = {f["slug"] for f in self.features for e in history_for(f, CSHARP) if COMPAT_PREFIX in e.get("note", "")}
        self.assertEqual(with_note, set(COMPAT))

    def test_the_polyfill_hint_appears_only_where_it_was_verified_and_says_compile_time_only(self) -> None:
        for slug in COMPAT:
            note = history_for(self.by_slug[slug], CSHARP)[0]["note"]
            if slug in POLYFILLABLE:
                self.assertIn("in your own code makes it compile there; this was checked at compile time only", note, slug)
            else:
                self.assertNotIn("in your own code", note, slug)

    def test_runtime_pages_say_what_the_framework_cannot_compile(self) -> None:
        text = self.tracks[NETFX]["description"]
        for phrase in ("C# 7.3", "default interface members", "static abstract members", "ref fields", "records"):
            self.assertIn(phrase, text)
        self.assertIn("C# 12", self.tracks[CSHARP]["description"])

    def test_availability_follows_the_history_for_a_runtime_dependent_feature(self) -> None:
        orders = {t: version_orders(self.versions[t]) for t in self.versions}
        records = self.by_slug["records"]
        self.assertEqual(lifecycle_state(records, CSHARP, orders[CSHARP], orders[CSHARP]["cs8.0"]), "not-yet")
        self.assertEqual(lifecycle_state(records, CSHARP, orders[CSHARP], orders[CSHARP]["cs9.0"]), "available")
        self.assertNotIn(NETFX, records["history"], "records are never listed on the .NET Framework track")

    def test_the_language_label_names_the_current_versions_and_matches_the_source_page(self) -> None:
        language = next(l for l in self.data["languages"] if l["slug"] == LANG)
        self.assertEqual(language["version_label"], "C# 14 / .NET 10 · modern .NET")
        source = (ROOT / "csharp" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f'<span class="lang-tag csharp">{language["version_label"]}</span>', source)


class CSharpVersionPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.language = next(l for l in self.data["languages"] if l["slug"] == LANG)
        self.tracks = {t["id"]: t for t in tracks_for(self.data, LANG)}
        self.features = [f for f in self.data["features"] if f["language"] == LANG]
        rels = {CSHARP: "csharp/versions/index.html", DOTNET: "csharp/versions/dotnet/index.html", NETFX: "csharp/versions/netfx/index.html"}
        self.pages = {t: render_versions_page(self.language, self.tracks[t], self.data, page_rel=rel) for t, rel in rels.items()}

    def test_every_version_has_a_block_and_every_feature_appears_once_on_each_page_it_belongs_to(self) -> None:
        for track, page in self.pages.items():
            for version in versions_for(self.data, LANG, track):
                self.assertIn(f'id="v-{version["id"]}" data-order="{version["order"]}" data-status="released"', page)
            for feature in self.features:
                expected = 1 if feature["history"].get(track) else 0
                self.assertEqual(page.count(f'id="feature-{feature["slug"]}"'), expected, f"{feature['slug']} on {track}")

    def test_the_three_pages_list_141_67_and_44_features(self) -> None:
        self.assertEqual({t: p.count('class="feature-card"') for t, p in self.pages.items()}, {CSHARP: 141, DOTNET: 67, NETFX: 44})

    def test_the_records_card_shows_the_compatibility_note_and_the_framework_page_has_no_records_card(self) -> None:
        self.assertIn("Needs library or runtime support. It does not compile against any .NET Framework 4.5 to 4.8 reference assembly",
                      self.pages[CSHARP])
        self.assertNotIn('id="feature-records"', self.pages[NETFX])
        self.assertNotIn('id="feature-records"', self.pages[DOTNET])

    def test_shared_features_link_to_their_other_tracks(self) -> None:
        match = re.search(r'id="index-tuples".*?</li>', self.pages[CSHARP], re.S)
        self.assertIsNotNone(match)
        self.assertIn(".NET Framework", match.group(0))
        self.assertIn("4.7", match.group(0))

    def test_dotnet_page_shows_default_csharp_versions_and_support_dates(self) -> None:
        page = self.pages[DOTNET]
        self.assertIn("Default C# version: 14.", page)
        self.assertIn("Support ends November 2028", page)
        self.assertIn("Long-term support from", page)

    def test_the_pages_link_all_three_tracks(self) -> None:
        for page in self.pages.values():
            for label in ("C# language versions", ".NET (Core and 5+)", ".NET Framework"):
                self.assertIn(label, page)
            self.assertIn("track-tab", page)

    def test_topic_page_shows_the_new_label_and_availability_chips(self) -> None:
        page = render_language_page(self.language, self.data, page_rel="csharp/index.html")
        self.assertIn("C# 14 / .NET 10 · modern .NET", page)
        self.assertNotIn("C# 12 / .NET 8+", page)
        self.assertRegex(page, r"C# \d+(\.\d+)?\+")


if __name__ == "__main__":
    unittest.main()
