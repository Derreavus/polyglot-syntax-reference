"""Tests for the C++ version history: the standards timeline, the GCC, Clang and MSVC implementation tracks, which versions are marked verified,
the deprecation and removal history, the library headers and how the pages render them.

These guard the rules the data has to keep and facts checked against primary sources, not every entry. The general rules for any language live in
test_versioning.py. Sources of the pinned facts:
  - ISO standards: publication months from general knowledge (the ISO catalogue was not read); C++26 is technically complete but not yet published by ISO.
  - GCC release dates: gcc.gnu.org/releases.html. Clang: llvm.org news (2.9 to 6.0) and the dates of the llvm-project release tags, month precision.
  - MSVC: Visual Studio release dates (endoflife.date and Microsoft Learn); VS 2013 is month precision and not source-checked.
  - Deprecations and removals: Annex D and Annex C of the standard drafts n3337, n4140, n4659, n4861, n4950 and the C++26 working draft.
  - Verified markers and implementation notes: results of compiling with the toolchain configurations listed in scripts/check/check_cpp_examples.py.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "renderer"))

from load_data import load_data
from render_versions import render_versions_page
from versioning import primary_track, tracks_for, versions_for

LANG = "cpp"
STD, GCC, CLANG, MSVC = "cpp", "gcc", "clang", "msvc"

CPP_VERSIONS = {"cpp98": "1998-09", "cpp11": "2011-09", "cpp14": "2014-12", "cpp17": "2017-12", "cpp20": "2020-12", "cpp23": "2024-10", "cpp26": "2026-03"}
GCC_RELEASES = {
    "gcc3.0": "2001-06-18", "gcc3.3": "2003-05-13", "gcc4.3": "2008-03-05", "gcc4.4": "2009-04-21", "gcc4.5": "2010-04-14", "gcc4.6": "2011-03-25", "gcc4.7": "2012-03-22",
    "gcc4.8": "2013-03-22", "gcc4.9": "2014-04-22", "gcc5": "2015-04-22", "gcc6": "2016-04-27", "gcc7": "2017-05-02", "gcc8": "2018-05-02", "gcc9": "2019-05-03",
    "gcc10": "2020-05-07", "gcc11": "2021-04-27", "gcc12": "2022-05-06", "gcc13": "2023-04-26", "gcc14": "2024-05-07", "gcc15": "2025-04-25", "gcc16": "2026-04-30",
}
CLANG_RELEASES = {
    "clang2.9": "2011-04", "clang3.0": "2011-12", "clang3.1": "2012-05", "clang3.2": "2012-12", "clang3.3": "2013-06", "clang3.4": "2014-01", "clang3.5": "2014-09",
    "clang3.6": "2015-02", "clang3.9": "2016-09", "clang4": "2017-03", "clang5": "2017-09", "clang6": "2018-03", "clang7": "2018-09", "clang8": "2019-03",
    "clang9": "2019-09", "clang10": "2020-03", "clang11": "2020-10", "clang12": "2021-04", "clang13": "2021-09", "clang14": "2022-03", "clang15": "2022-09",
    "clang16": "2023-03", "clang17": "2023-09", "clang18": "2024-03", "clang19": "2024-09", "clang20": "2025-03", "clang21": "2025-08", "clang22": "2026-02", "clang23": "2026-08",
}
MSVC_DATES = {"vs2013": "2013-10", "vs2015": "2015-07-20", "vs2015.3": "2016-06-27", "vs2017-15.0": "2017-03-07", "vs2017-15.7": "2018-05-07", "vs2019-16.0": "2019-04-02",
              "vs2019-16.4": "2019-12-03", "vs2019-16.10": "2021-05-25", "vs2022-17.0": "2021-11-08", "vs2022-17.14": "2025-05-13"}
VERIFIED_GCC = set(range(9, 17))
VERIFIED_CLANG = set(range(14, 24))

# slug -> [(version id or None, kind)] on the standards track
LIFECYCLE = {
    "auto-ptr": [("cpp98", "added"), ("cpp11", "deprecated"), ("cpp17", "removed")],
    "unary-function-binary-function": [("cpp98", "added"), ("cpp11", "deprecated"), ("cpp17", "removed")],
    "bind1st-bind2nd": [("cpp98", "added"), ("cpp11", "deprecated"), ("cpp17", "removed")],
    "random-shuffle": [("cpp98", "added"), ("cpp14", "deprecated"), ("cpp17", "removed")],
    "register-storage-class": [("cpp98", "added"), ("cpp11", "deprecated"), ("cpp17", "removed")],
    "trigraphs": [("cpp98", "added"), ("cpp17", "removed")],
    "dynamic-exception-specifications": [("cpp98", "added"), ("cpp11", "deprecated"), ("cpp17", "removed")],
    "throw-empty-specification": [("cpp98", "added"), ("cpp11", "deprecated"), ("cpp20", "removed")],
    "result-of": [("cpp11", "added"), ("cpp17", "deprecated"), ("cpp20", "removed")],
    "shared-ptr-unique": [("cpp11", "added"), ("cpp17", "deprecated"), ("cpp20", "removed")],
    "uncaught-exception": [("cpp98", "added"), ("cpp17", "deprecated"), ("cpp20", "removed")],
    "get-temporary-buffer": [("cpp98", "added"), ("cpp17", "deprecated"), ("cpp20", "removed")],
    "codecvt-facilities": [("cpp11", "added"), ("cpp17", "deprecated"), ("cpp26", "removed")],
    "strstream": [("cpp98", "added"), (None, "deprecated"), ("cpp26", "removed")],
    "aligned-storage": [("cpp11", "added"), ("cpp23", "deprecated")],
    "is-pod": [("cpp11", "added"), ("cpp20", "deprecated")],
    "std-iterator": [("cpp98", "added"), ("cpp17", "deprecated")],
    "memory-order-consume": [("cpp11", "added"), ("cpp26", "deprecated")],
}
# first version of each implementation, from the data (language features and headers): None = the track has no entry
FIRST = {
    "concepts": {STD: "cpp20", GCC: "gcc10", CLANG: "clang10", MSVC: "vs2019-16.3"},
    "deducing-this": {STD: "cpp23", GCC: "gcc14", CLANG: "clang18", MSVC: "vs2022-17.13"},
    "constexpr-if-statements": {STD: "cpp17", GCC: "gcc7", CLANG: "clang3.9", MSVC: "vs2017-15.3"},
    "lambda-expressions": {STD: "cpp11", GCC: "gcc4.5", CLANG: "clang3.1", MSVC: None},
    "modules": {STD: "cpp20", GCC: "gcc11", CLANG: "clang11", MSVC: "vs2019-16.8"},
    "reflection": {STD: "cpp26", GCC: "gcc16", CLANG: None, MSVC: None},
    "header-expected": {STD: "cpp23", GCC: "gcc12", CLANG: "clang16", MSVC: None},
    "header-format": {STD: "cpp20", GCC: "gcc13", CLANG: "clang17", MSVC: None},
    "header-print": {STD: "cpp23", GCC: "gcc14", CLANG: "clang17", MSVC: None},
    "header-flat-map": {STD: "cpp23", GCC: "gcc15", CLANG: "clang20", MSVC: None},
    "header-optional": {STD: "cpp17", GCC: None, CLANG: None, MSVC: None},   # present from the oldest verified version, so no first release is claimed
    "lib-ranges-to-container": {STD: "cpp23", GCC: "gcc14", CLANG: "clang17", MSVC: None},
    "lib-constexpr-string": {STD: "cpp20", GCC: "gcc12", CLANG: "clang15", MSVC: None},   # the macro first existed for constexpr char_traits; std::string needs value 201907
    "lib-clamp": {STD: "cpp17", GCC: "gcc7", CLANG: None, MSVC: None},   # GCC 7 is libstdc++'s documented version, not confirmed here
    "lib-copyable-function": {STD: "cpp26", GCC: "gcc16", CLANG: None, MSVC: None},
    "lib-span-at": {STD: "cpp26", GCC: None, CLANG: "clang18", MSVC: None},
}


def history(feature: dict, track: str) -> list[dict]:
    return feature["history"].get(track, [])


class CppVersionDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.tracks = {t["id"]: t for t in tracks_for(self.data, LANG)}
        self.versions = {t: {v["id"]: v for v in versions_for(self.data, LANG, t)} for t in (STD, GCC, CLANG, MSVC)}
        self.features = {f["slug"]: f for f in self.data["features"] if f["language"] == LANG}

    def test_four_tracks_the_standard_first_then_three_implementations(self) -> None:
        self.assertEqual([t["id"] for t in tracks_for(self.data, LANG)], [STD, GCC, CLANG, MSVC])
        self.assertEqual(primary_track(self.data, LANG)["id"], STD)
        self.assertEqual([self.tracks[t]["kind"] for t in (STD, GCC, CLANG, MSVC)], ["standard", "implementation", "implementation", "implementation"])
        for track in self.tracks.values():
            for link in track["changelog_links"]:
                self.assertTrue(link["url"].startswith("https://"), link)

    def test_standard_versions_dates_and_the_cpp26_status(self) -> None:
        self.assertEqual({k: v["released"] for k, v in self.versions[STD].items()}, CPP_VERSIONS)
        self.assertEqual({k: v["status"] for k, v in self.versions[STD].items() if v["status"] != "released"}, {"cpp26": "complete"})
        self.assertEqual(self.versions[STD]["cpp26"]["label"], "C++26")
        self.assertIn("ISO", self.versions[STD]["cpp26"]["note"])
        self.assertIn("baseline", self.versions[STD]["cpp98"]["label"])
        self.assertIn("general knowledge", self.tracks[STD]["description"])

    def test_gcc_and_clang_versions_and_release_dates(self) -> None:
        self.assertEqual({k: v["released"] for k, v in self.versions[GCC].items()}, GCC_RELEASES)
        self.assertEqual({k: v["released"] for k, v in self.versions[CLANG].items()}, CLANG_RELEASES)

    def test_unreleased_compiler_versions_are_not_listed(self) -> None:
        for track, limit in ((GCC, 16), (CLANG, 23)):
            for vid in self.versions[track]:
                self.assertLessEqual(float(vid.removeprefix(track)), limit, vid)
        text = " ".join(str(f["history"]) for f in self.features.values())
        self.assertNotIn("gcc17", text)
        self.assertNotIn("clang24", text)

    def test_msvc_dates(self) -> None:
        listed = {k: v["released"] for k, v in self.versions[MSVC].items()}
        for vid, date in MSVC_DATES.items():
            self.assertEqual(listed[vid], date, vid)
        self.assertIn("month was not source-checked", self.versions[MSVC]["vs2013"]["note"])
        self.assertNotIn("not source-checked", self.versions[MSVC]["vs2015"]["note"])

    def test_verified_markers_follow_the_toolchain_configurations(self) -> None:
        for track, verified in ((GCC, VERIFIED_GCC), (CLANG, VERIFIED_CLANG)):
            for vid, v in self.versions[track].items():
                major = int(vid.removeprefix(track).split(".")[0])
                says_verified = v["note"].startswith("Verified here")
                self.assertEqual(says_verified, major in verified, vid)
                if not says_verified:
                    self.assertTrue(v["note"].startswith("Not verified here"), vid)
        self.assertIn("g++-12 with libstdc++ 12", self.versions[GCC]["gcc12"]["note"])
        self.assertIn("clang++-17 with libc++ 17", self.versions[CLANG]["clang17"]["note"])
        for vid, v in self.versions[MSVC].items():
            self.assertTrue(v["note"].startswith("Not verified here"), vid)
        self.assertIn("none of its versions is marked verified", self.tracks[MSVC]["description"])

    def test_every_feature_is_on_the_standards_timeline(self) -> None:
        self.assertTrue(all(history(f, STD) for f in self.features.values()))
        self.assertEqual({t: sum(1 for f in self.features.values() if history(f, t)) for t in (STD, GCC, CLANG, MSVC)}, {STD: 521, GCC: 352, CLANG: 226, MSVC: 81})

    def test_documented_only_notes_appear_only_inside_the_verified_range(self) -> None:
        marker = "Documented by the vendor; no probe here confirmed"
        for track, verified in ((GCC, VERIFIED_GCC), (CLANG, VERIFIED_CLANG), (MSVC, set())):
            for f in self.features.values():
                for e in history(f, track):
                    inside = int(e["version"].removeprefix(track).split(".")[0]) in verified if track != MSVC else False
                    if marker in e.get("note", ""):
                        self.assertTrue(inside, f"{f['slug']} {e['version']}")

    def test_first_versions_of_well_known_features(self) -> None:
        for slug, expected in FIRST.items():
            for track, version in expected.items():
                got = history(self.features[slug], track)
                self.assertEqual(got[0]["version"] if got else None, version, f"{slug} on {track}")

    def test_flags_a_feature_needs_are_recorded(self) -> None:
        self.assertIn("-freflection", history(self.features["reflection"], GCC)[0]["note"])
        self.assertIn("-fcontracts", history(self.features["contracts"], GCC)[0]["note"])
        self.assertIn("-fmodules", history(self.features["modules"], GCC)[0]["note"])
        self.assertIn("-fcoroutines", history(self.features["coroutines"], GCC)[0]["note"])

    def test_lifecycle_histories_from_annex_d_and_c(self) -> None:
        for slug, expected in LIFECYCLE.items():
            self.assertEqual([(e["version"], e["kind"]) for e in history(self.features[slug], STD)], expected, slug)

    def test_removals_say_how_the_implementations_behave(self) -> None:
        note = lambda s: history(self.features[s], STD)[-1]["note"]
        self.assertIn("libstdc++ still accepts it for compatibility", note("auto-ptr"))
        self.assertIn("libstdc++ still accepts it for compatibility", note("codecvt-facilities"))
        self.assertIn("both reject it from -std=c++17", note("register-storage-class"))
        self.assertIn("still accept it at -std=c++20", note("throw-empty-specification"))
        self.assertIn("stop replacing the sequences from -std=c++17", note("trigraphs"))

    def test_a_deprecation_in_the_standard_that_introduced_it_is_undated_with_a_note(self) -> None:
        event = history(self.features["strstream"], STD)[1]
        self.assertIsNone(event["version"])
        self.assertTrue(event["note"])

    def test_header_standards_and_the_two_documented_oddities(self) -> None:
        for slug, std in (("header-optional", "cpp17"), ("header-ranges", "cpp20"), ("header-flat-map", "cpp23"), ("header-inplace-vector", "cpp26"), ("header-charconv", "cpp17"),
                          ("header-array", "cpp11"), ("header-stacktrace", "cpp23"), ("header-hive", "cpp26")):
            self.assertEqual(history(self.features[slug], STD)[0]["version"], std, slug)
        self.assertIn("omits <charconv>", history(self.features["header-charconv"], STD)[0]["note"])
        self.assertIn("earlier modes", history(self.features["header-version"], STD)[0]["note"])
        self.assertEqual(sum(1 for s in self.features if s.startswith("header-")), 63)

    def test_headers_present_on_the_oldest_verified_compiler_claim_no_first_release(self) -> None:
        self.assertEqual(history(self.features["header-optional"], GCC), [])
        self.assertEqual(history(self.features["header-optional"], CLANG), [])
        for slug, f in self.features.items():
            if slug.startswith("header-"):
                for e in history(f, GCC): self.assertNotEqual(e["version"], "gcc9", slug)
                for e in history(f, CLANG): self.assertNotEqual(e["version"], "clang14", slug)

    def test_library_features_come_from_feature_test_macros(self) -> None:
        lib = {s: f for s, f in self.features.items() if s.startswith("lib-")}
        self.assertEqual(len(lib), 276)   # 208 placed by a feature-test macro, 68 with no macro placed by a standard-boundary probe
        self.assertTrue(all(f["category"] == "library" for f in lib.values()))
        from collections import Counter
        self.assertEqual(Counter(history(f, STD)[0]["version"] for f in lib.values()), {"cpp11": 67, "cpp14": 21, "cpp17": 40, "cpp20": 45, "cpp23": 48, "cpp26": 55})
        for slug, std in (("lib-make-unique", "cpp14"), ("lib-void-t", "cpp17"), ("lib-scoped-lock", "cpp17"), ("lib-bit-cast", "cpp20"), ("lib-erase-if", "cpp20"),
                          ("lib-string-contains", "cpp23"), ("lib-ranges-zip", "cpp23"), ("lib-saturation-arithmetic", "cpp26"), ("lib-function-ref", "cpp26")):
            self.assertEqual(history(self.features[slug], STD)[0]["version"], std, slug)

    def test_library_features_the_header_features_already_cover_are_not_repeated(self) -> None:
        for slug in ("lib-ranges", "lib-concepts", "lib-optional", "lib-format", "lib-span", "lib-gcd", "lib-lcm", "lib-char8-t", "lib-destroying-delete"):
            self.assertNotIn(slug, self.features, slug)

    def test_a_standard_placed_by_a_macro_value_says_so(self) -> None:
        placed = [s for s, f in self.features.items() if s.startswith("lib-") and "Placed in this standard by the value of its feature-test macro" in history(f, STD)[0].get("note", "")]
        self.assertEqual(len(placed), 96)
        self.assertIn("(__cpp_lib_to_string)", history(self.features["lib-to-string"], STD)[0].get("note", "") + "(__cpp_lib_to_string)")
        self.assertIn("std::string became constexpr in C++20", history(self.features["lib-constexpr-string"], STD)[0]["note"])

    def test_library_events_on_the_implementation_tracks(self) -> None:
        lib = [f for s, f in self.features.items() if s.startswith("lib-")]
        self.assertEqual((sum(1 for f in lib if history(f, GCC)), sum(1 for f in lib if history(f, CLANG)), sum(1 for f in lib if history(f, MSVC))), (174, 65, 0))
        self.assertNotIn("clang14", {e["version"] for f in lib for e in history(f, CLANG)}, "a library feature present at the oldest verified Clang claims no first release")
        self.assertEqual({e["version"] for f in lib for e in history(f, GCC) if e["version"] == "gcc9"} - {"gcc9"}, set())


class CppVersionPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.language = next(l for l in self.data["languages"] if l["slug"] == LANG)
        self.tracks = {t["id"]: t for t in tracks_for(self.data, LANG)}
        rels = {STD: "cpp/versions/index.html", GCC: "cpp/versions/gcc/index.html", CLANG: "cpp/versions/clang/index.html", MSVC: "cpp/versions/msvc/index.html"}
        self.pages = {t: render_versions_page(self.language, self.tracks[t], self.data, page_rel=rel) for t, rel in rels.items()}

    def test_the_pages_list_521_352_226_and_81_features(self) -> None:
        self.assertEqual({t: p.count('class="feature-card"') for t, p in self.pages.items()}, {STD: 521, GCC: 352, CLANG: 226, MSVC: 81})

    def test_every_version_has_a_block(self) -> None:
        for track, page in self.pages.items():
            for version in versions_for(self.data, LANG, track):
                self.assertIn(f'id="v-{version["id"]}" data-order="{version["order"]}"', page)

    def test_the_technically_complete_standard_and_the_verified_markers_are_visible(self) -> None:
        self.assertIn('data-status="complete"', self.pages[STD])
        self.assertIn('class="complete-badge">Technically complete', self.pages[STD])
        self.assertIn("C++26 (technically complete)</option>", self.pages[STD])
        self.assertNotIn("draft-badge", self.pages[STD])
        self.assertIn("Verified here: g++-12 with libstdc++ 12", self.pages[GCC])
        self.assertIn("Not verified here: this version could not be run", self.pages[GCC])
        self.assertIn("Verified here: clang++-17 with libc++ 17", self.pages[CLANG])
        self.assertNotIn("Verified here", self.pages[MSVC])
        self.assertIn("Documented by the vendor; no probe here confirmed", self.pages[GCC])

    def test_removal_notes_show_on_the_standards_page(self) -> None:
        self.assertIn("GCC&#x27;s libstdc++ still accepts it for compatibility", self.pages[STD].replace("'", "&#x27;"))
        self.assertIn("Dynamic exception specifications", self.pages[STD])

    def test_the_four_tracks_are_linked_from_every_page(self) -> None:
        for page in self.pages.values():
            for label in ("C++ standards", "GCC", "Clang", "MSVC"):
                self.assertIn(label, page)


if __name__ == "__main__":
    unittest.main()
