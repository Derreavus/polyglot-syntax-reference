"""Tests for scripts/check/check_csharp_examples.py, the checker that compares the C#, .NET and .NET Framework version
history with the real C# compiler. Each compiler test hands the real script deliberately wrong data and requires a
specific complaint, so a checker that quietly stopped checking would fail here.

The tests of the parsing, coverage rules, compatibility-note wording, the no-SDK behaviour and the CI setup run
everywhere. The tests that compile need a .NET SDK 10 with the .NET 8 and .NET 10 reference packs and Mono's
reference assemblies; they are skipped without them, and CI runs the whole checker on the real data.
"""
from __future__ import annotations

import contextlib
import copy
import io
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "renderer"))
sys.path.insert(0, str(ROOT / "scripts" / "check"))

import check_csharp_examples as checker
from load_data import load_data

TC = checker.discover(None, None)
HAS_COMPILER = (TC is not None and "14.0" in TC.supported and all(TC.packs.get(k) for k in ("net8.0", "net10.0", "netstandard2.1"))
                and all(TC.mono_refs(v) for v in checker.FRAMEWORK_ORDER))


def only(data: dict, *slugs: str) -> dict:
    """The data reduced to the named C# features, so a compiler test checks only what it needs."""
    reduced = copy.deepcopy(data)
    reduced["features"] = [f for f in reduced["features"] if f["language"] == "csharp" and f["slug"] in slugs]
    return reduced


def feature(data: dict, slug: str) -> dict:
    return next(f for f in data["features"] if f["language"] == "csharp" and f["slug"] == slug)


def run(check, data: dict, *args) -> list[str]:
    report = checker.Report()
    with ThreadPoolExecutor(max_workers=2) as pool:
        check(TC, data, report, pool, *args)
    return report.problems


def only_compat(*slugs: str):
    """Limit the compatibility probes to the named features, so a test compiles 9 targets for each of them and no more."""
    return mock.patch.dict(checker.COMPAT_PROBES, {k: v for k, v in checker.COMPAT_PROBES.items() if k in slugs}, clear=True)


def row(**results: tuple[bool, str]) -> dict:
    base = {f"net{t}": (True, "") for t in checker.FRAMEWORK_TARGETS}
    base.update({"netstandard2.1": (True, ""), "net8.0": (True, ""), "net10.0": (True, "")})
    base.update(results)
    return base


class CheckerParsingTests(unittest.TestCase):
    def test_the_highest_sdk_is_picked_from_the_list(self) -> None:
        text = "8.0.132 [/usr/lib/dotnet/sdk]\n10.0.113 [/usr/lib/dotnet/sdk]\n9.0.300 [/usr/lib/dotnet/sdk]\n"
        self.assertEqual(checker.parse_sdk_list(text), ("10.0.113", "/usr/lib/dotnet/sdk"))
        self.assertEqual(checker.parse_sdk_list("10.0.100-preview.1 [/x/sdk]\n9.0.300 [/y/sdk]"), ("10.0.100-preview.1", "/x/sdk"))
        self.assertIsNone(checker.parse_sdk_list("The command could not be loaded"))

    def test_only_numbered_language_versions_are_taken_from_the_compiler_list(self) -> None:
        text = "Supported language versions:\ndefault\n1\n2\n7.0\n7.3\n8.0\n14.0 (default)\nlatestmajor\npreview\nlatest\n"
        self.assertEqual(checker.parse_langversions(text), ["1", "2", "7.0", "7.3", "8.0", "14.0"])

    def test_version_ids_map_to_the_compilers_language_version_names(self) -> None:
        self.assertEqual([checker.langversion(v) for v in ("cs1.0", "cs2.0", "cs6.0", "cs7.0", "cs7.3", "cs8.0", "cs14.0")],
                         ["1", "2", "6", "7.0", "7.3", "8.0", "14.0"])

    def test_the_previous_language_version_is_the_one_before_it_in_the_compilers_own_list(self) -> None:
        supported = ["1", "2", "3", "7.0", "7.1", "8.0"]
        self.assertEqual(checker.previous_langversion("8.0", supported), "7.1")
        self.assertEqual(checker.previous_langversion("7.0", supported), "3")
        self.assertIsNone(checker.previous_langversion("1", supported))
        self.assertIsNone(checker.previous_langversion("9.0", supported), "a version the compiler does not know has no previous")

    def test_framework_releases_are_compared_with_the_release_before_them_and_4_5_with_4_0(self) -> None:
        self.assertEqual(checker.previous_framework("4.5"), "4.0")
        self.assertEqual(checker.previous_framework("4.7.2"), "4.7.1")
        self.assertEqual(checker.previous_framework("4.8"), "4.7.2")
        self.assertEqual(checker.framework_version("fx4.6.2"), "4.6.2")

    def test_dotnet_core_releases_count_as_before_net_8(self) -> None:
        self.assertEqual([checker.dotnet_major(v) for v in ("core1.0", "core3.1", "net5.0", "net8.0", "net10.0")], [0, 0, 5, 8, 10])

    def test_error_codes_are_read_from_the_compiler_message(self) -> None:
        self.assertEqual(checker.error_code("a.cs(1,2): error CS8701: Target runtime doesn't support it"), "CS8701")
        self.assertEqual(checker.error_code("warning only"), "")


class CompatibilityNoteWordingTests(unittest.TestCase):
    def test_a_feature_that_compiles_everywhere_has_no_note(self) -> None:
        self.assertIsNone(checker.expected_compat_note(row(), None, False))

    def test_a_feature_no_framework_release_accepts(self) -> None:
        fail = (False, "a.cs(1,1): error CS8701: x")
        note = checker.expected_compat_note(row(**{f"net{t}": fail for t in checker.FRAMEWORK_TARGETS}), None, False)
        self.assertEqual(note, "Needs library or runtime support. It does not compile against any .NET Framework 4.5 to 4.8 reference assembly "
                               "(CS8701); netstandard 2.1 accepts it; .NET 8 and .NET 10 accept it.")

    def test_a_feature_the_framework_accepts_from_a_release_on(self) -> None:
        fail = (False, "error CS8179: x")
        note = checker.expected_compat_note(row(**{"net4.5": fail, "net4.6.2": fail}), None, False)
        self.assertIn("compiles against .NET Framework from 4.7 but not before (CS8179)", note)

    def test_netstandard_rejection_and_the_polyfill_hint(self) -> None:
        fail = (False, "error CS0518: x")
        r = row(**{**{f"net{t}": fail for t in checker.FRAMEWORK_TARGETS}, "netstandard2.1": fail})
        with_hint = checker.expected_compat_note(r, "records+init", True)
        self.assertIn("netstandard 2.1 rejects it (CS0518)", with_hint)
        self.assertTrue(with_hint.endswith("Defining System.Runtime.CompilerServices.IsExternalInit in your own code makes it compile there; "
                                           "this was checked at compile time only."))
        self.assertNotIn("Defining", checker.expected_compat_note(r, "records+init", False), "no hint unless the polyfill compiled")
        self.assertNotIn("Defining", checker.expected_compat_note(r, None, True))

    def test_a_modern_target_that_rejects_it_is_flagged_rather_than_described(self) -> None:
        r = row(**{"net4.5": (False, "error CS1: x"), "net8.0": (False, "error CS2: x")})
        self.assertIn("check .NET 8 and .NET 10 results", checker.expected_compat_note(r, None, False))


class CheckerSetupTests(unittest.TestCase):
    """Rules that need no compiler."""

    def setUp(self) -> None:
        self.data = load_data()

    def coverage(self, data: dict) -> list[str]:
        report = checker.Report()
        checker.check_coverage(data, report)
        return report.problems

    def test_every_event_on_the_three_tracks_is_checked_by_something(self) -> None:
        self.assertEqual(self.coverage(self.data), [])

    def test_a_new_event_with_nothing_checking_it_is_reported(self) -> None:
        data = copy.deepcopy(self.data)
        feature(data, "records")["history"]["csharp"].append({"version": "cs14.0", "kind": "changed", "note": "x"})
        problems = self.coverage(data)
        self.assertEqual(len(problems), 1)
        self.assertIn("csharp event records@cs14.0 has no probe and no NOT_PROBEABLE reason", problems[0])

    def test_a_probe_for_an_event_that_is_not_in_the_data_is_reported(self) -> None:
        with mock.patch.dict(checker.LANGUAGE_PROBES, {"no-such-feature@cs7.0": ("class C{}", ())}):
            problems = self.coverage(self.data)
        self.assertEqual(len(problems), 1)
        self.assertIn("LANGUAGE_PROBES has no-such-feature@cs7.0, which is not an event in the data", problems[0])

    def test_an_event_cannot_be_both_probed_and_exempt(self) -> None:
        with mock.patch.dict(checker.NOT_PROBEABLE, {"records@cs9.0": "reason"}):
            problems = self.coverage(self.data)
        self.assertEqual(len(problems), 1)
        self.assertIn("records@cs9.0 has both a probe and a NOT_PROBEABLE reason", problems[0])

    def test_every_exemption_gives_a_reason(self) -> None:
        for key, reason in checker.NOT_PROBEABLE.items():
            self.assertGreater(len(reason), 20, key)

    def test_the_probe_tables_cover_the_documented_numbers(self) -> None:
        self.assertEqual((len(checker.LANGUAGE_PROBES), len(checker.FRAMEWORK_PROBES), len(checker.RUNTIME_API_PROBES),
                          len(checker.COMPAT_PROBES), len(checker.POLYFILLS)), (129, 26, 28, 17, 3))

    def test_a_missing_sdk_is_an_error_when_strict(self) -> None:
        with mock.patch.object(sys, "argv", ["x", "--strict", "--dotnet", "no-such-dotnet-binary"]), contextlib.redirect_stdout(io.StringIO()) as out:
            code = checker.main(["--strict", "--dotnet", "no-such-dotnet-binary"])
        self.assertEqual(code, 1)
        self.assertIn("no .NET SDK with Roslyn found", out.getvalue())

    def test_a_missing_sdk_is_skipped_with_a_note_when_not_strict(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = checker.main(["--dotnet", "no-such-dotnet-binary"])
        self.assertEqual(code, 0)
        self.assertIn("SKIP csharp examples", out.getvalue())

    def test_ci_runs_the_checker_strictly_with_the_sdks_and_mono_it_needs(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("check_csharp_examples.py --strict", workflow)
        self.assertIn("actions/setup-dotnet", workflow)
        for version in ("10.0.x", "8.0.x"):
            self.assertIn(version, workflow)
        self.assertIn("mono-devel", workflow)


@unittest.skipUnless(HAS_COMPILER, "needs .NET SDK 10, the .NET 8 and 10 reference packs, netstandard 2.1 and Mono's reference assemblies")
class CheckerCompilerTests(unittest.TestCase):
    """Wrong data must be rejected by the real compiler."""

    def setUp(self) -> None:
        self.data = load_data()

    def test_the_real_data_for_a_few_representative_features_passes(self) -> None:
        data = only(self.data, "records", "tuples", "generics", "pattern-matching")
        self.assertEqual(run(checker.check_language, data), [])

    def test_a_language_version_set_too_early_is_reported(self) -> None:
        data = only(self.data, "records")
        with mock.patch.dict(checker.LANGUAGE_PROBES, {"records@cs8.0": checker.LANGUAGE_PROBES["records@cs9.0"]}):
            feature(data, "records")["history"]["csharp"][0]["version"] = "cs8.0"
            problems = run(checker.check_language, data)
        self.assertEqual(len(problems), 1)
        self.assertIn("records@cs8.0: does not compile at -langversion 8.0", problems[0])

    def test_a_probe_whose_feature_is_dated_too_late_is_reported(self) -> None:
        data = only(self.data, "generics")
        with mock.patch.dict(checker.LANGUAGE_PROBES, {"generics@cs3.0": checker.LANGUAGE_PROBES["generics@cs2.0"]}):
            feature(data, "generics")["history"]["csharp"][0]["version"] = "cs3.0"
            problems = run(checker.check_language, data)
        self.assertEqual(len(problems), 1)
        self.assertIn("also compiles at -langversion 2, so 3 is too late", problems[0])

    def test_a_probe_dated_too_early_is_reported(self) -> None:
        data = only(self.data, "generics")
        with mock.patch.dict(checker.LANGUAGE_PROBES, {"generics@cs1.0": checker.LANGUAGE_PROBES["generics@cs2.0"]}):
            feature(data, "generics")["history"]["csharp"][0]["version"] = "cs1.0"
            problems = run(checker.check_language, data)
        self.assertEqual(len(problems), 1)
        self.assertIn("does not compile at -langversion 1", problems[0])

    def test_a_framework_release_dated_too_late_or_too_early_is_reported(self) -> None:
        data = only(self.data, "hashset-trygetvalue")
        late = copy.deepcopy(data)
        with mock.patch.dict(checker.FRAMEWORK_PROBES, {"hashset-trygetvalue@fx4.8": checker.FRAMEWORK_PROBES["hashset-trygetvalue@fx4.7.2"]}):
            feature(late, "hashset-trygetvalue")["history"]["netfx"][0]["version"] = "fx4.8"
            problems = run(checker.check_framework, late, True)
        self.assertEqual(len(problems), 1)
        self.assertIn("also compiles against 4.7.2, so 4.8 is too late", problems[0])
        early = copy.deepcopy(data)
        with mock.patch.dict(checker.FRAMEWORK_PROBES, {"hashset-trygetvalue@fx4.7.1": checker.FRAMEWORK_PROBES["hashset-trygetvalue@fx4.7.2"]}):
            feature(early, "hashset-trygetvalue")["history"]["netfx"][0]["version"] = "fx4.7.1"
            problems = run(checker.check_framework, early, True)
        self.assertEqual(len(problems), 1)
        self.assertIn("does not compile against the 4.7.1 reference assemblies", problems[0])

    def test_an_api_dated_after_net_8_that_the_net_8_pack_already_has_is_reported(self) -> None:
        data = only(self.data, "priority-queue")
        with mock.patch.dict(checker.RUNTIME_API_PROBES, {"priority-queue@net9.0": checker.RUNTIME_API_PROBES["priority-queue@net6.0"]}):
            feature(data, "priority-queue")["history"]["dotnet"][0]["version"] = "net9.0"
            problems = run(checker.check_runtime_apis, data, True)
        self.assertEqual(len(problems), 1)
        self.assertIn("already in the .NET 8 reference pack, so listing it at .NET 9 is too late", problems[0])

    def test_an_api_dated_up_to_net_8_that_the_net_8_pack_lacks_is_reported(self) -> None:
        data = only(self.data, "ordered-dictionary")
        with mock.patch.dict(checker.RUNTIME_API_PROBES, {"ordered-dictionary@net8.0": checker.RUNTIME_API_PROBES["ordered-dictionary@net9.0"]}):
            feature(data, "ordered-dictionary")["history"]["dotnet"][0]["version"] = "net8.0"
            problems = run(checker.check_runtime_apis, data, True)
        self.assertEqual(len(problems), 1)
        self.assertIn("expected in the .NET 8 reference pack but missing", problems[0])

    def test_a_compatibility_note_that_disagrees_with_the_compiler_is_reported(self) -> None:
        data = only(self.data, "default-interface-members")
        feature(data, "default-interface-members")["history"]["csharp"][0]["note"] = feature(data, "default-interface-members")["history"]["csharp"][0]["note"].replace("accepts it", "rejects it (CS0000)", 1)
        with only_compat("default-interface-members"):
            problems = run(checker.check_compat, data, True)
        self.assertTrue(any("compatibility note differs from the compile results" in p for p in problems), problems)

    def test_a_compatibility_note_on_a_feature_that_compiles_everywhere_is_reported(self) -> None:
        data = only(self.data, "ref-struct")
        feature(data, "ref-struct")["history"]["csharp"][0]["note"] = "Needs library or runtime support. invented."
        with only_compat("ref-struct"):
            problems = run(checker.check_compat, data, True)
        self.assertTrue(any("ref-struct: compiles against every target, but the data has a compatibility note" in p for p in problems), problems)

    def test_a_missing_compatibility_note_is_reported(self) -> None:
        data = only(self.data, "records")
        feature(data, "records")["history"]["csharp"][0].pop("note")
        with only_compat("records"):
            problems = run(checker.check_compat, data, True)
        self.assertTrue(any("records: compatibility note differs" in p for p in problems), problems)

    def test_a_wrong_default_csharp_version_on_a_dotnet_release_is_reported(self) -> None:
        data = copy.deepcopy(self.data)
        next(v for v in data["versions"] if v["language"] == "csharp" and v["id"] == "net8.0")["note"] = "Default C# version: 11."
        report = checker.Report()
        checker.check_defaults(TC, data, report, True)
        self.assertEqual(len(report.problems), 1)
        self.assertIn("net8.0: the SDK defaults to C# 12.0", report.problems[0])


if __name__ == "__main__":
    unittest.main()
