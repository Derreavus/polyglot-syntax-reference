"""Tests for scripts/check/check_rust_examples.py, the checker that compares the Rust version history with a real
Rust compiler. Each test hands the real script deliberately wrong data and requires a specific complaint, so a
checker that quietly stopped checking would fail here.

The checker adapts to the compiler it is given, so these tests do not depend on which Rust version is installed.
The tests that compile need a rustc that knows the 2021 edition; they are skipped without one. The tests of the
coverage rules, the no-compiler behaviour and the CI setup run everywhere.
"""
from __future__ import annotations

import contextlib
import copy
import io
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "renderer"))
sys.path.insert(0, str(ROOT / "scripts" / "check"))

import check_rust_examples as checker
from load_data import load_data

MINOR = checker.rustc_minor(["rustc"])
HAS_COMPILER = MINOR is not None and MINOR >= checker.EDITION_MIN_RUSTC["2021"]
# The real data has been checked on compilers up to this release. A newer compiler may legitimately disagree, and
# CI runs the pinned toolchains for that, so the test that runs the whole real data is skipped beyond it.
REAL_DATA_CHECKED_UP_TO = 95


def new_feature(slug: str, rust=None, edition=None, migration=None) -> dict:
    history = {}
    if rust:
        history["rust"] = [{"version": v, "kind": k, **({"note": "x"} if k in ("changed", "removed") else {})} for v, k in rust]
    if edition:
        history["edition"] = [{"version": v, "kind": k, **({"note": "x"} if k in ("changed", "removed") else {})} for v, k in edition]
    feature = {"language": "rust", "slug": slug, "title": slug, "category": "syntax", "summary": "x", "history": history}
    if migration:
        feature["migration"] = {"legacy": migration[0], "modern": migration[1]}
    return feature


def add_release(data: dict, minor: int) -> None:
    orders = [v["order"] for v in data["versions"] if v["language"] == "rust" and v["track"] == "rust"]
    data["versions"].append({"language": "rust", "track": "rust", "id": f"rust-1.{minor}", "label": f"Rust 1.{minor}",
                             "released": "2099-01-01", "order": max(orders) + 1, "status": "released"})


class CheckerSetupTests(unittest.TestCase):
    """Rules that need no compiler."""

    def setUp(self) -> None:
        self.data = load_data()
        self.features = [f for f in self.data["features"] if f["language"] == "rust"]

    def test_every_rust_feature_is_checked_by_something(self) -> None:
        problems: list[str] = []
        checker.check_coverage(self.features, problems)
        self.assertEqual(problems, [])

    def test_a_new_feature_with_nothing_checking_it_is_reported(self) -> None:
        problems: list[str] = []
        checker.check_coverage(self.features + [new_feature("brand-new", rust=[("rust-1.13", "added")])], problems)
        self.assertEqual(len(problems), 1)
        self.assertIn("brand-new: nothing checks this feature", problems[0])

    def test_a_probe_for_a_feature_that_is_not_in_the_data_is_reported(self) -> None:
        problems: list[str] = []
        with mock.patch.dict(checker.PROBES, {"no-such-feature": [checker.P("pub fn f() {}")]}):
            checker.check_coverage(self.features, problems)
        self.assertEqual(len(problems), 1)
        self.assertIn("no-such-feature", problems[0])

    def test_a_feature_cannot_be_both_probed_and_exempt(self) -> None:
        problems: list[str] = []
        with mock.patch.dict(checker.NOT_PROBEABLE, {"thread-scope": "reason"}):
            checker.check_coverage(self.features, problems)
        self.assertEqual(len(problems), 1)
        self.assertIn("thread-scope: is both probed and listed as not probeable", problems[0])

    def test_every_edition_named_by_a_probe_is_a_known_edition(self) -> None:
        for slug, probes in checker.EDITION_PROBES.items():
            for probe in probes:
                self.assertIn(probe.ok_in, checker.EDITION_MIN_RUSTC, slug)
                self.assertIn(probe.fails_in, checker.EDITION_MIN_RUSTC, slug)
        for slug, probes in checker.PROBES.items():
            for probe in probes:
                self.assertIn(probe.edition, checker.EDITION_MIN_RUSTC, slug)

    def test_a_missing_compiler_is_an_error_when_strict(self) -> None:
        with mock.patch.object(sys, "argv", ["x", "--strict", "--rustc", "no-such-rustc-binary"]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = checker.main()
        self.assertEqual(code, 1)
        self.assertIn("no working compiler", out.getvalue())

    def test_a_missing_compiler_is_skipped_with_a_note_when_not_strict(self) -> None:
        with mock.patch.object(sys, "argv", ["x", "--rustc", "no-such-rustc-binary"]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = checker.main()
        self.assertEqual(code, 0)
        self.assertIn("SKIP rust examples", out.getvalue())

    def test_ci_checks_the_data_on_an_old_and_a_new_toolchain_that_covers_the_newest_release(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        toolchains = re.findall(r'--strict --rustc "rustup run (1\.\d+\.\d+) rustc"', workflow)
        self.assertGreaterEqual(len(toolchains), 2, "CI should run the checker on an old and a new toolchain")
        minors = sorted(int(t.split(".")[1]) for t in toolchains)
        newest_release = max(int(v["id"].rsplit(".", 1)[1]) for v in self.data["versions"] if v["language"] == "rust" and v["track"] == "rust")
        self.assertGreaterEqual(minors[-1], newest_release, "the newest CI toolchain must know every release the data lists")
        for toolchain in toolchains:
            self.assertIn(toolchain, re.search(r"rustup toolchain install ([^\n]+)", workflow).group(1))


@unittest.skipUnless(HAS_COMPILER, "needs a rustc that knows the 2021 edition")
class CheckerCatchesWrongDataTests(unittest.TestCase):
    def run_checker(self, mutate=None, probes=None, edition_probes=None, whole_data=False) -> tuple[int, str]:
        """Run the real checker. By default only the made-up zz- features are checked, with the real probe tables
        swapped out, so a test compiles a handful of snippets instead of the whole dataset."""
        data = copy.deepcopy(load_data())
        if mutate:
            mutate(data)
        if not whole_data:
            data["features"] = [f for f in data["features"] if f["language"] != "rust" or f["slug"].startswith("zz-")]
        tables = {} if whole_data else {"clear": True}
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(checker, "load_data", lambda: data))
            stack.enter_context(mock.patch.object(sys, "argv", ["check_rust_examples.py", "--strict"]))
            stack.enter_context(mock.patch.dict(checker.PROBES, probes or {}, **tables))
            stack.enter_context(mock.patch.dict(checker.EDITION_PROBES, edition_probes or {}, **tables))
            if not whole_data:
                stack.enter_context(mock.patch.dict(checker.NOT_PROBEABLE, {}, clear=True))
                stack.enter_context(mock.patch.dict(checker.EXAMPLE_EDITIONS, {}, clear=True))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = checker.main()
        return code, output.getvalue()

    def assert_reports(self, phrase: str, mutate=None, probes=None, edition_probes=None) -> None:
        code, output = self.run_checker(mutate, probes, edition_probes)
        self.assertEqual(code, 1, output)
        self.assertIn(phrase, output)

    @unittest.skipIf(MINOR is not None and MINOR > REAL_DATA_CHECKED_UP_TO, "the real data has not been checked on a compiler this new")
    def test_the_real_data_passes(self) -> None:
        code, output = self.run_checker(whole_data=True)
        self.assertEqual(code, 0, output)
        self.assertIn("OK   rust examples", output)

    def test_a_probe_that_compiles_for_a_feature_the_data_says_is_newer_is_reported(self) -> None:
        def mutate(d: dict) -> None:
            add_release(d, MINOR + 1)
            d["features"].append(new_feature("zz-newer", rust=[(f"rust-1.{MINOR + 1}", "added")]))
        self.assert_reports("zz-newer: the data says not-yet", mutate, {"zz-newer": [checker.P("pub fn f() {}")]})

    def test_a_probe_that_fails_for_a_feature_the_data_says_exists_is_reported(self) -> None:
        self.assert_reports("zz-exists: the data says available",
                            lambda d: d["features"].append(new_feature("zz-exists", rust=[("rust-1.0", "added")])),
                            {"zz-exists": [checker.P("this is not rust")]})

    def test_a_deprecation_that_the_compiler_does_not_see_is_reported(self) -> None:
        def mutate(d: dict) -> None:
            d["features"].append(new_feature("zz-deprecated", rust=[("rust-1.0", "added"), ("rust-1.13", "deprecated")]))
        self.assert_reports("zz-deprecated: the data says deprecated", mutate,
                            {"zz-deprecated": [checker.P("pub fn f() {}", flags=checker.DENY_DEPRECATED, deprecation=True)]})

    def test_a_broken_after_snippet_is_reported(self) -> None:
        self.assert_reports("zz-after: the 'after' snippet does not compile",
                            lambda d: d["features"].append(new_feature("zz-after", rust=[("rust-1.0", "added")], migration=("pub fn f() {}", "this is not rust"))),
                            {"zz-after": [checker.P("pub fn f() {}")]})

    def test_a_broken_before_snippet_is_reported(self) -> None:
        self.assert_reports("zz-before: the 'before' snippet does not compile",
                            lambda d: d["features"].append(new_feature("zz-before", rust=[("rust-1.0", "added")], migration=("this is not rust", "pub fn f() {}"))),
                            {"zz-before": [checker.P("pub fn f() {}")]})

    def test_an_after_snippet_that_compiles_before_the_release_the_data_names_is_reported(self) -> None:
        def mutate(d: dict) -> None:
            add_release(d, MINOR + 1)
            d["features"].append(new_feature("zz-early", rust=[(f"rust-1.{MINOR + 1}", "added")], migration=("pub fn f() {}", "pub fn f() {}")))
        self.assert_reports(f"zz-early: the data says this arrived in 1.{MINOR + 1}, but the 'after' snippet compiles", mutate,
                            {"zz-early": [checker.P("this is not rust")]})

    def test_an_edition_probe_that_compiles_where_it_should_fail_is_reported(self) -> None:
        self.assert_reports("zz-edition: the edition probe should fail on 2021 but compiles",
                            lambda d: d["features"].append(new_feature("zz-edition", edition=[("ed2015", "added"), ("ed2021", "changed")])),
                            edition_probes={"zz-edition": [checker.EditionProbe("pub fn f() {}", "2018", "2021")]})

    def test_an_edition_probe_that_disagrees_with_the_data_is_reported(self) -> None:
        self.assert_reports("zz-boundary: the probe differs between editions 2018 and 2021, but the data has no edition event at 2021",
                            lambda d: d["features"].append(new_feature("zz-boundary", edition=[("ed2015", "added"), ("ed2018", "changed")])),
                            edition_probes={"zz-boundary": [checker.EditionProbe("pub fn f() { let a = [1u8]; let _: u8 = a.into_iter().next().unwrap(); }", "2021", "2018")]})

    def test_a_feature_with_nothing_checking_it_is_reported(self) -> None:
        self.assert_reports("zz-unchecked: nothing checks this feature",
                            lambda d: d["features"].append(new_feature("zz-unchecked", rust=[("rust-1.13", "added")])))


if __name__ == "__main__":
    unittest.main()
