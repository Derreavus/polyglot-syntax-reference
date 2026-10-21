"""Tests for scripts/check/check_python_examples.py, the checker that compares the Python version history with
Python itself. Each test hands the real script deliberately wrong data and requires a specific complaint,
so a checker that quietly stopped checking would fail here.

The probes are written for Python 3.12 (the version CI runs), so the tests that run the whole checker are
skipped on any other Python. The tests of the coverage rules and of the CI setup run everywhere.
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

import check_python_examples as checker
from load_data import load_data

ON_PROBED_PYTHON = sys.version_info[:2] == checker.PROBED


def feature(data: dict, slug: str) -> dict:
    return next(f for f in data["features"] if f["language"] == "python" and f["slug"] == slug)


def event(data: dict, slug: str, kind: str) -> dict:
    return next(e for e in feature(data, slug)["history"]["python"] if e["kind"] == kind)


def new_feature(slug: str, category: str) -> dict:
    return {"language": "python", "slug": slug, "title": slug, "category": category, "summary": "x",
            "history": {"python": [{"version": "py3.10", "kind": "added"}]}}


class CheckerSetupTests(unittest.TestCase):
    """Rules that do not depend on which Python runs the tests."""

    def setUp(self) -> None:
        self.data = load_data()
        self.features = [f for f in self.data["features"] if f["language"] == "python"]

    def test_every_python_feature_has_an_example_or_a_probe(self) -> None:
        problems: list[str] = []
        checker.check_coverage(self.features, problems)
        self.assertEqual(problems, [])

    def test_a_new_library_feature_without_a_probe_is_reported(self) -> None:
        problems: list[str] = []
        checker.check_coverage(self.features + [new_feature("brand-new-lib", "library")], problems)
        self.assertEqual(len(problems), 1)
        self.assertIn("brand-new-lib: no probe", problems[0])

    def test_a_new_syntax_feature_without_an_example_is_reported(self) -> None:
        problems: list[str] = []
        checker.check_coverage(self.features + [new_feature("brand-new-syntax", "syntax")], problems)
        self.assertEqual(len(problems), 1)
        self.assertIn("brand-new-syntax: a syntax feature with no before/after example", problems[0])

    def test_a_probe_or_example_for_a_feature_that_is_not_in_the_data_is_reported(self) -> None:
        problems: list[str] = []
        with mock.patch.dict(checker.SYNTAX_EXAMPLES, {"no-such-feature": "x = 1\n"}):
            checker.check_coverage(self.features, problems)
        self.assertEqual(len(problems), 1)
        self.assertIn("no-such-feature", problems[0])

    def test_a_feature_cannot_be_both_probed_and_exempt(self) -> None:
        problems: list[str] = []
        with mock.patch.dict(checker.NOT_PROBEABLE, {"pathlib": "reason"}):
            checker.check_coverage(self.features, problems)
        self.assertEqual(len(problems), 1)
        self.assertIn("pathlib: is both probed and listed as not probeable", problems[0])

    def test_the_probed_interpreter_matches_a_version_in_the_data(self) -> None:
        self.assertEqual(checker.PROBED_ID, f"py{checker.PROBED[0]}.{checker.PROBED[1]}")
        self.assertIn(checker.PROBED_ID, {v["id"] for v in self.data["versions"] if v["language"] == "python"})

    def test_ci_runs_the_checker_in_strict_mode_on_the_python_the_probes_are_written_for(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        python = re.search(r'python-version:\s*"?([\d.]+)"?', workflow)
        self.assertIsNotNone(python, "ci.yml no longer pins a Python version")
        self.assertEqual(python.group(1), f"{checker.PROBED[0]}.{checker.PROBED[1]}",
                         "CI uses a different Python from the one the probes are written for; update PROBED and the probes together")
        self.assertIn("python3 scripts/check/check_python_examples.py --strict", workflow)


@unittest.skipUnless(ON_PROBED_PYTHON, "the checker's probes are written for Python 3.12, which CI runs")
class CheckerCatchesWrongDataTests(unittest.TestCase):
    def run_checker(self, mutate=None, argv=("--strict",), running=None) -> tuple[int, str]:
        data = copy.deepcopy(load_data())
        if mutate:
            mutate(data)
        patches = [mock.patch.object(checker, "load_data", lambda: data),
                   mock.patch.object(sys, "argv", ["check_python_examples.py", *argv])]
        if running:
            patches.append(mock.patch.object(checker, "running_version", lambda: running))
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            with contextlib.redirect_stdout(output):
                code = checker.main()
        return code, output.getvalue()

    def assert_reports(self, mutate, *phrases: str) -> None:
        code, output = self.run_checker(mutate)
        self.assertEqual(code, 1, output)
        for phrase in phrases:
            self.assertIn(phrase, output)

    def test_the_real_data_passes(self) -> None:
        code, output = self.run_checker()
        self.assertEqual(code, 0, output)
        self.assertIn("OK   python examples", output)

    def test_a_removal_dated_too_late_is_reported(self) -> None:
        self.assert_reports(lambda d: event(d, "time-clock", "removed").update(version="py3.13"),
                            "time-clock: the data says deprecated in Python 3.12, but time.clock does not exist")

    def test_a_removal_that_has_not_happened_is_reported(self) -> None:
        def remove_utcnow(d: dict) -> None:
            history = feature(d, "datetime-utcnow")["history"]["python"]
            history.remove(event(d, "datetime-utcnow", "deprecated"))
            history.append({"version": "py3.12", "kind": "removed", "note": "x"})

        self.assert_reports(remove_utcnow, "datetime-utcnow: the data says removed in Python 3.12, but datetime.datetime.utcnow exists")

    def test_a_library_feature_dated_after_it_exists_is_reported(self) -> None:
        self.assert_reports(lambda d: event(d, "itertools-batched", "added").update(version="py3.13"),
                            "itertools-batched: the data says not-yet in Python 3.12, but itertools.batched exists")

    def test_a_library_feature_dated_before_it_exists_is_reported(self) -> None:
        self.assert_reports(lambda d: event(d, "frozendict", "added").update(version="py3.12"),
                            "frozendict: the data says available in Python 3.12, but builtin frozendict does not exist")

    def test_syntax_dated_after_the_parser_accepts_it_is_reported(self) -> None:
        self.assert_reports(lambda d: event(d, "structural-pattern-matching", "added").update(version="py3.13"),
                            "structural-pattern-matching: the data says Python 3.13 added this syntax, but the snippet parses in Python 3.12")

    def test_syntax_dated_before_it_existed_is_reported(self) -> None:
        self.assert_reports(lambda d: event(d, "assignment-expressions", "added").update(version="py3.7"),
                            "assignment-expressions: the 'after' snippet is rejected as Python 3.7 syntax")

    def test_syntax_claimed_for_a_version_that_cannot_parse_it_is_reported(self) -> None:
        self.assert_reports(lambda d: event(d, "lazy-imports", "added").update(version="py3.12"),
                            "lazy-imports: the 'after' snippet does not parse")

    def test_a_broken_after_snippet_is_reported(self) -> None:
        self.assert_reports(lambda d: feature(d, "pathlib")["migration"].update(modern="path = Path(base) / / 'x'"),
                            "pathlib: the 'after' snippet does not parse")

    def test_a_broken_before_snippet_is_reported(self) -> None:
        self.assert_reports(lambda d: feature(d, "nonlocal-statement")["migration"].update(legacy="def f(:"),
                            "nonlocal-statement: the 'before' snippet does not parse")

    def test_python_2_syntax_that_python_3_accepts_is_reported(self) -> None:
        self.assert_reports(lambda d: feature(d, "print-statement")["migration"].update(legacy='print("x")'),
                            "print-statement: the 'before' snippet is Python 2 syntax but parses in Python 3")

    def test_a_feature_that_exists_but_is_marked_removed_is_reported(self) -> None:
        self.assert_reports(lambda d: feature(d, "pathlib")["history"]["python"].append({"version": "py3.5", "kind": "removed", "note": "x"}),
                            "pathlib: the data says removed in Python 3.12, but module pathlib exists")

    def test_a_feature_with_nothing_to_check_it_is_reported(self) -> None:
        self.assert_reports(lambda d: d["features"].append(new_feature("brand-new-lib", "library")), "brand-new-lib: no probe")

    def test_another_python_is_an_error_when_strict(self) -> None:
        code, output = self.run_checker(running=(3, 13))
        self.assertEqual(code, 1)
        self.assertIn("probes are written for Python 3.12, this is Python 3.13 (--strict)", output)

    def test_another_python_skips_the_probes_with_a_note_when_not_strict(self) -> None:
        code, output = self.run_checker(argv=(), running=(3, 13))
        self.assertEqual(code, 0, output)
        self.assertIn("so they were skipped", output)
        self.assertNotIn("probes passed", output)


if __name__ == "__main__":
    unittest.main()
