"""Tests for scripts/check/check_cpp_examples.py, the checker that compares the C++ version history with real GCC and Clang toolchains.

The tests of the version markers, the coverage rules, the argument handling and the CI setup run everywhere. The tests that compile need all
18 toolchain configurations that the checker lists (GCC 9 to 16, Clang 14 to 23, each with its own library); they are skipped without them, and CI
runs the whole checker on the real data. Each compiler test hands the real script deliberately wrong data and requires a specific complaint,
so a checker that quietly stopped checking would fail here.
"""
from __future__ import annotations

import contextlib
import copy
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "renderer"))
sys.path.insert(0, str(ROOT / "scripts" / "check"))

import check_cpp_examples as checker
from load_data import load_data

CFGS = checker.discover()
HAVE_ALL = len(CFGS) == len(checker.GCC_VERSIONS) + len(checker.CLANG_VERSIONS)
NEEDS_ALL = unittest.skipUnless(HAVE_ALL, "needs all 18 toolchain configurations (see scripts/ci/setup_cpp_toolchains.sh)")


def only(data: dict, *slugs: str) -> dict:
    """The data reduced to the named C++ features so a compiler test checks only what it needs."""
    reduced = copy.deepcopy(data)
    reduced["features"] = [f for f in reduced["features"] if f["language"] == "cpp" and f["slug"] in slugs]
    return reduced


def feature(data: dict, slug: str) -> dict:
    return next(f for f in data["features"] if f["language"] == "cpp" and f["slug"] == slug)


def run(check, data: dict, *args) -> list[str]:
    report = checker.Report()
    if check in (checker.check_markers, checker.check_coverage):
        check(data, report)
    else:
        check(data, CFGS, report, *args)
    return report.problems


@contextlib.contextmanager
def tables(leakage: dict | None = None, lifecycle: dict | None = None):
    """Replace the leakage and lifecycle tables with the part a reduced-data test needs, so entries for other features are not reported as stale."""
    with mock.patch.dict(checker.STANDARD_LEAKAGE, leakage or {}, clear=True), mock.patch.dict(checker.LIFECYCLE_PROBES, lifecycle or {}, clear=True):
        yield


@contextlib.contextmanager
def lib_tables(evidence: tuple[str, ...] = (), leakage: dict | None = None):
    """Limit the library evidence and leakage tables to the named features, so a reduced-data test is not told the others are missing."""
    with mock.patch.dict(checker.LIBRARY_EVIDENCE, {k: v for k, v in checker.LIBRARY_EVIDENCE.items() if k in evidence}, clear=True), \
         mock.patch.dict(checker.LIBRARY_LEAKAGE, leakage or {}, clear=True):
        yield


class CheckerSetupTests(unittest.TestCase):
    """Rules that need no compiler."""

    def setUp(self) -> None:
        self.data = load_data()

    def test_the_real_data_passes_the_marker_and_coverage_checks(self) -> None:
        self.assertEqual(run(checker.check_markers, self.data), [])
        self.assertEqual(run(checker.check_coverage, self.data), [])

    def test_a_version_marked_verified_without_a_configuration_is_reported(self) -> None:
        data = copy.deepcopy(self.data)
        next(v for v in data["versions"] if v["language"] == "cpp" and v["id"] == "gcc4.8")["note"] = "Verified here: g++-4.8"
        problems = run(checker.check_markers, data)
        self.assertEqual(len(problems), 1)
        self.assertIn("gcc gcc4.8: marked verified but the checker has no configuration for it", problems[0])

    def test_a_version_with_a_configuration_that_is_marked_not_verified_is_reported(self) -> None:
        data = copy.deepcopy(self.data)
        next(v for v in data["versions"] if v["language"] == "cpp" and v["id"] == "clang17")["note"] = "Not verified here: x"
        problems = run(checker.check_markers, data)
        self.assertEqual(len(problems), 1)
        self.assertIn("clang clang17: marked not verified but the checker has configuration for it", problems[0])

    def test_msvc_is_never_verified(self) -> None:
        data = copy.deepcopy(self.data)
        next(v for v in data["versions"] if v["language"] == "cpp" and v["id"] == "vs2015")["note"] = "Verified here: cl"
        self.assertEqual(len(run(checker.check_markers, data)), 1)

    def test_a_header_feature_without_a_probe_is_reported(self) -> None:
        data = copy.deepcopy(self.data)
        data["features"].append({"language": "cpp", "slug": "header-newthing", "title": "<newthing>", "category": "library", "summary": "x", "topic": "headers",
                                 "history": {"cpp": [{"version": "cpp26", "kind": "added"}]}})
        problems = run(checker.check_coverage, data)
        self.assertEqual(problems, ["header feature header-newthing has no probe"])

    def test_a_probe_table_entry_for_a_missing_feature_is_reported(self) -> None:
        with mock.patch.dict(checker.HEADER_PROBES, {"header-ghost": ("17", "int x;")}):
            problems = run(checker.check_coverage, self.data)
        self.assertEqual(problems, ["HEADER_PROBES has header-ghost, which is not a feature in the data"])
        with mock.patch.dict(checker.LANGUAGE_EVIDENCE, {"ghost-feature": {"std": "17", "macros": [], "probe": "int x;"}}):
            self.assertEqual(run(checker.check_coverage, self.data), ["LANGUAGE_EVIDENCE has ghost-feature, which is not a feature in the data"])

    def test_a_library_feature_without_an_evidence_entry_is_reported(self) -> None:
        data = copy.deepcopy(self.data)
        data["features"].append({"language": "cpp", "slug": "lib-newthing", "title": "x", "category": "library", "summary": "x", "topic": "headers",
                                 "history": {"cpp": [{"version": "cpp26", "kind": "added"}]}})
        self.assertEqual(run(checker.check_coverage, data), ["library feature lib-newthing has no evidence entry"])

    def test_a_library_evidence_entry_for_a_missing_feature_is_reported(self) -> None:
        with mock.patch.dict(checker.LIBRARY_EVIDENCE, {"lib-ghost": {"macro": "__cpp_lib_ghost", "std": "20"}}):
            self.assertEqual(run(checker.check_coverage, self.data), ["LIBRARY_EVIDENCE has lib-ghost, which is not a feature in the data"])

    def test_a_library_probe_for_a_missing_feature_is_reported(self) -> None:
        with mock.patch.dict(checker.LIBRARY_PROBES, {"lib-ghost": ("11", "int x;")}):
            self.assertEqual(run(checker.check_coverage, self.data), ["LIBRARY_PROBES has lib-ghost, which is not a feature in the data"])

    def test_a_feature_in_both_library_tables_is_reported(self) -> None:
        with mock.patch.dict(checker.LIBRARY_EVIDENCE, {"lib-unique-ptr": {"macro": "__cpp_lib_ghost", "std": "11"}}):
            self.assertEqual(run(checker.check_coverage, self.data), ["lib-unique-ptr is in both LIBRARY_EVIDENCE and LIBRARY_PROBES"])

    def test_the_probe_tables_have_the_documented_sizes(self) -> None:
        self.assertEqual((len(checker.LANGUAGE_EVIDENCE), len(checker.HEADER_PROBES), len(checker.LIFECYCLE_PROBES), len(checker.STANDARD_LEAKAGE), len(checker.LIBRARY_EVIDENCE), len(checker.LIBRARY_LEAKAGE), len(checker.LIBRARY_PROBES)), (141, 63, 20, 11, 208, 13, 68))
        self.assertEqual(sum(1 for e in checker.LANGUAGE_EVIDENCE.values() if e["probe"]), 76)
        self.assertEqual(sum(1 for e in checker.LANGUAGE_EVIDENCE.values() if e["macros"]), 65)

    def test_macro_specs_and_version_numbers_are_parsed(self) -> None:
        class Fake:
            def macros(self) -> dict[str, int]: return {"__cpp_concepts": 201907, "__cpp_lib_x": 5}
        self.assertTrue(checker.macro_ok(Fake(), "__cpp_concepts>=201907"))
        self.assertFalse(checker.macro_ok(Fake(), "__cpp_concepts>=202002"))
        self.assertFalse(checker.macro_ok(Fake(), "__cpp_missing>=1"))
        self.assertEqual([checker.major("gcc4.8", "gcc"), checker.major("clang23", "clang"), checker.major("gcc16", "gcc")], [4, 23, 16])

    def test_with_no_configuration_the_checker_skips_or_fails_when_strict(self) -> None:
        with mock.patch.object(checker, "discover", return_value={}):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code_soft = checker.main([])
            with contextlib.redirect_stdout(io.StringIO()) as out2:
                code_strict = checker.main(["--strict"])
        self.assertEqual(code_soft, 0)
        self.assertIn("SKIP cpp examples", out.getvalue())
        self.assertEqual(code_strict, 1)
        self.assertIn("FAIL cpp examples", out2.getvalue())

    def test_discovery_on_empty_roots_finds_no_conda_or_unpacked_libcxx_configurations(self) -> None:
        found = checker.discover("/nonexistent-envs", "/nonexistent-libcxx")
        self.assertTrue(all(track == "gcc" and v <= 14 for track, v in found), sorted(found))

    def test_ci_installs_the_toolchains_and_runs_the_checker_strictly(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("scripts/ci/setup_cpp_toolchains.sh", workflow)
        self.assertIn("check_cpp_examples.py --strict", workflow)
        job = workflow[workflow.index("  cpp-toolchains:"):]
        self.assertIn("runs-on: ubuntu-24.04", job.split("steps:")[0], "the C++ job must run on the Ubuntu release that has the pinned package versions, not ubuntu-latest")
        setup = (ROOT / "scripts" / "ci" / "setup_cpp_toolchains.sh").read_text(encoding="utf-8")
        self.assertIn('"${VERSION_ID:-}" != "24.04"', setup)
        for needle in ("g++-9", "g++-14", "clang-14", "clang-20", "libc++-$v-dev", "/opt/libcxx", "gxx_linux-64=$v", "clangxx=$v", "libcxx-devel=$v", "for v in 15 16", "for v in 21 22 23"):
            self.assertIn(needle, setup)


@NEEDS_ALL
class CheckerCompilerTests(unittest.TestCase):
    """Wrong data must be rejected by the real compilers."""

    def setUp(self) -> None:
        self.data = load_data()

    def test_the_real_data_for_a_few_representative_features_passes(self) -> None:
        data = only(self.data, "concepts", "deducing-this", "header-format", "lambda-expressions", "auto-ptr")
        self.assertEqual(run(checker.check_events, data, False), [])
        with tables(lifecycle={"auto-ptr": checker.LIFECYCLE_PROBES["auto-ptr"]}):
            self.assertEqual(run(checker.check_boundaries, data, False), [])
            self.assertEqual(run(checker.check_lifecycle, data, False), [])

    def test_a_version_the_evidence_does_not_support_is_reported(self) -> None:
        data = only(self.data, "concepts")
        feature(data, "concepts")["history"]["gcc"][0]["version"] = "gcc11"
        problems = run(checker.check_events, data, False)
        self.assertEqual(len(problems), 1)
        self.assertIn("gcc gcc11 concepts", problems[0])
        self.assertIn("evidence first supports [10]", problems[0])

    def test_an_event_the_evidence_confirms_must_not_say_it_is_documented_only(self) -> None:
        data = only(self.data, "deducing-this")
        feature(data, "deducing-this")["history"]["gcc"][0]["note"] = checker.DOCUMENTED
        problems = run(checker.check_events, data, False)
        self.assertEqual(len(problems), 1)
        self.assertIn("the evidence confirms this version but the event says it is documented only", problems[0])

    def test_an_event_the_evidence_does_not_confirm_must_say_it_is_documented_only(self) -> None:
        data = only(self.data, "reflection")
        feature(data, "reflection")["history"]["gcc"][0]["note"] = "Needs -freflection."
        problems = run(checker.check_events, data, False)
        self.assertEqual(len(problems), 1)
        self.assertIn("does not say it is documented only", problems[0])

    def test_a_header_added_in_the_wrong_standard_is_reported(self) -> None:
        data = only(self.data, "header-format")
        feature(data, "header-format")["history"]["cpp"][0]["version"] = "cpp23"
        with tables():
            problems = run(checker.check_boundaries, data, False)
        self.assertTrue(any("the data adds it in ['cpp23'] but its probe belongs to C++20" in p for p in problems), problems)

    def test_a_leakage_entry_that_a_strict_configuration_contradicts_is_reported(self) -> None:
        data = only(self.data, "header-format")
        with tables(leakage={"header-format": "claimed"}):
            problems = run(checker.check_boundaries, data, False)
        self.assertTrue(any("header-format: listed as leaking, but a strict configuration does confirm its boundary" in p for p in problems), problems)

    def test_a_boundary_no_strict_configuration_confirms_must_be_listed_as_leakage(self) -> None:
        data = only(self.data, "func-predefined-identifier")
        with tables():
            problems = run(checker.check_boundaries, data, False)
        self.assertTrue(any("func-predefined-identifier: no strict configuration compiles it at C++11 and rejects it at C++03" in p for p in problems), problems)

    def test_a_wrong_recorded_removal_behaviour_is_reported(self) -> None:
        data = only(self.data, "auto-ptr")
        impl = dict(checker.LIFECYCLE_PROBES["auto-ptr"]["impl"], libstdcxx="rejects")
        with tables(lifecycle={"auto-ptr": dict(checker.LIFECYCLE_PROBES["auto-ptr"], impl=impl)}):
            problems = run(checker.check_lifecycle, data, False)
        self.assertEqual(len(problems), 1)
        self.assertIn("auto-ptr: gcc 16 accepts at C++17, the data records rejects", problems[0])

    def test_library_events_and_boundaries_for_representative_features_pass(self) -> None:
        names = ("lib-constexpr-string", "lib-ranges-to-container", "lib-bit-cast", "lib-copyable-function")
        data = only(self.data, *names)
        self.assertEqual(run(checker.check_events, data, False), [])
        with lib_tables(names):
            self.assertEqual(run(checker.check_library_boundaries, data, False), [])

    def test_a_library_version_set_too_early_is_reported(self) -> None:
        data = only(self.data, "lib-constexpr-string")
        feature(data, "lib-constexpr-string")["history"]["gcc"][0]["version"] = "gcc8"
        problems = run(checker.check_events, data, False)
        self.assertEqual(len(problems), 0, "gcc8 is outside the verified range, so only documentation could support it")
        feature(data, "lib-constexpr-string")["history"]["gcc"][0]["version"] = "gcc11"
        problems = run(checker.check_events, data, False)
        self.assertEqual(len(problems), 1)
        self.assertIn("evidence first supports [12]", problems[0])

    def test_the_minimum_macro_value_matters_for_a_macro_that_was_first_defined_for_another_feature(self) -> None:
        with mock.patch.dict(checker.LIBRARY_EVIDENCE, {"lib-constexpr-string": {"macro": "__cpp_lib_constexpr_string", "std": "20"}}):
            data = only(self.data, "lib-constexpr-string")
            problems = run(checker.check_events, data, False)
        self.assertEqual(len(problems), 2, problems)
        self.assertTrue(any("evidence first supports [9]" in p for p in problems), problems)    # GCC defines the macro for char_traits from GCC 9
        self.assertTrue(any("evidence first supports [14]" in p for p in problems), problems)   # and libc++ from Clang 14

    def test_a_library_feature_added_in_the_wrong_standard_is_reported(self) -> None:
        data = only(self.data, "lib-bit-cast")
        feature(data, "lib-bit-cast")["history"]["cpp"][0]["version"] = "cpp23"
        with lib_tables(("lib-bit-cast",)):
            problems = run(checker.check_library_boundaries, data, False)
        self.assertTrue(any("the data adds it in ['cpp23'] but its macro evidence belongs to C++20" in p for p in problems), problems)

    def test_a_library_leakage_entry_that_a_strict_configuration_contradicts_is_reported(self) -> None:
        data = only(self.data, "lib-bit-cast")
        with lib_tables(("lib-bit-cast",), leakage={"lib-bit-cast": "claimed"}):
            problems = run(checker.check_library_boundaries, data, False)
        self.assertTrue(any("lib-bit-cast: listed as leaking, but a strict configuration does confirm its boundary" in p for p in problems), problems)

    def test_a_library_boundary_no_strict_configuration_confirms_must_be_listed(self) -> None:
        slug = sorted(checker.LIBRARY_LEAKAGE)[0]
        data = only(self.data, slug)
        with lib_tables((slug,)):
            problems = run(checker.check_library_boundaries, data, False)
        self.assertTrue(any(f"{slug}: no strict configuration defines" in p for p in problems), problems)

    def test_a_missing_configuration_is_an_error_when_strict_and_a_skip_otherwise(self) -> None:
        data = only(self.data, "concepts")
        partial = {k: v for k, v in CFGS.items() if k != ("gcc", 10)}
        report = checker.Report()
        checker.check_events(data, partial, report, True)
        self.assertEqual(len(report.problems), 1)
        self.assertIn("a configuration needed for this event was not found", report.problems[0])
        report = checker.Report()
        checker.check_events(data, partial, report, False)
        self.assertEqual(report.problems, [])
        self.assertEqual(len(report.skipped), 1)


if __name__ == "__main__":
    unittest.main()
