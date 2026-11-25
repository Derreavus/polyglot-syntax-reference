#!/usr/bin/env python3
"""Add a language to the site from a proposal, and keep the proposal form in step with the data.

    add_language.py validate SPEC.json
    add_language.py scaffold SPEC.json [--write] [--no-checks] [--skip-tests]
    add_language.py from-issue (--issue-json FILE | --body-file FILE --labels a,b) [--out SPEC.json]
    add_language.py issue-template [--check] [--repository OWNER/REPO]

A SPEC is a small JSON file (see scripts/lib/language_spec.py). ``from-issue`` builds one from a GitHub issue filled in through
the proposal form, and only for an issue a reviewer has marked ``verified``. ``scaffold`` shows what adding the language does
to data/site_data.json; with ``--write`` it writes the data, then rebuilds the site and runs the validators and the tests, so
the result is a normal change for a pull request. Topics are placeholders: a maintainer writes them. Nothing here edits a renderer.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "renderer"))

import language_spec as spec_lib  # noqa: E402
from validate_data import validate_data_model  # noqa: E402

DATA_PATH = ROOT / "data" / "site_data.json"
FORM_DIR = ROOT / ".github" / "ISSUE_TEMPLATE"
FORM_FILES = {spec_lib.FORM_TEMPLATE: spec_lib.issue_form_yaml, "config.yml": lambda data: spec_lib.issue_config_yaml()}
VALIDATORS = ("validate_staging_parity.py", "validate_syntax_html.py", "validate_links.py", "validate_html_smoke.py")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _report(problems: list[str]) -> None:
    print(f"{len(problems)} problem(s):", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)


def _run(command: list[str]) -> int:
    print("$ " + " ".join(command[1:]))
    return subprocess.run(command, cwd=ROOT).returncode


def command_validate(args: argparse.Namespace) -> int:
    problems = spec_lib.validate_spec(_load(Path(args.spec)), _load(Path(args.data)))
    if problems:
        _report(problems)
        return 1
    print("The spec is valid.")
    return 0


def command_scaffold(args: argparse.Namespace) -> int:
    data_path, spec = Path(args.data), _load(Path(args.spec))
    data = _load(data_path)
    try:
        new = spec_lib.scaffold(spec, data)
        validate_data_model(new)
    except ValueError as error:
        _report(str(error).split("; "))
        return 1
    print(spec_lib.diff_text(data, new))
    print("\nStill to do by hand:")
    for note in spec_lib.follow_ups(spec_lib.normalise_spec(spec)):
        print(f"  - {note}")
    if not args.write:
        print("\nDry run: nothing was written. Add --write to write the data and run the checks.")
        return 0
    temporary = data_path.with_suffix(".json.tmp")
    temporary.write_text(spec_lib.data_text(new), encoding="utf-8", newline="\n")
    temporary.replace(data_path)
    print(f"\nWrote {data_path}.")
    if args.no_checks:
        return 0
    failed = [_run([sys.executable, str(ROOT / "renderer" / "build_site.py")])]
    failed += [_run([sys.executable, str(ROOT / "scripts" / "validate" / name)]) for name in VALIDATORS]
    if not args.skip_tests:
        failed.append(_run([sys.executable, "-m", "unittest", "discover", "-s", "tests"]))
    if any(failed):
        print("\nA check failed: the data is written, fix the problem or restore it with git before committing.", file=sys.stderr)
        return 1
    print(f"\n{'Build and validators' if args.skip_tests else 'Build, validators and tests'} passed. Review the diff, write the topics, then open a pull request.")
    return 0


def command_from_issue(args: argparse.Namespace) -> int:
    data = _load(Path(args.data))
    if args.issue_json:
        issue = _load(Path(args.issue_json))
        body, labels = issue.get("body", ""), spec_lib.labels_of(issue)
    elif args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
        labels = [label.strip() for label in (args.labels or "").split(",") if label.strip()]
    else:
        print("Give --issue-json, or --body-file with --labels.", file=sys.stderr)
        return 2
    try:
        spec = spec_lib.spec_from_issue(body, labels, data)
    except ValueError as error:
        _report(str(error).split("; "))
        return 1
    text = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {args.out}.")
    else:
        print(text, end="")
    return 0


def command_issue_template(args: argparse.Namespace) -> int:
    data, directory = _load(Path(args.data)), Path(args.form_dir)
    status = 0
    for name, render in FORM_FILES.items():
        text, path = render(data), directory / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                print(f"{path} is out of date: run scripts/content/add_language.py issue-template", file=sys.stderr)
                status = 1
        else:
            directory.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"Wrote {path}.")
    if args.repository:
        expected, actual = spec_lib.form_url(args.repository), data["site"]["propose_form_url"]
        if actual != expected:
            print(f"data.site.propose_form_url is {actual} but this repository's form is at {expected}", file=sys.stderr)
            status = 1
    if args.check and status == 0:
        print("The issue form matches the data" + (f" and the form address is right for {args.repository}." if args.repository else "."))
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default=str(DATA_PATH), help="site data file (default: data/site_data.json)")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="check a spec against the current data")
    validate.add_argument("spec")
    validate.set_defaults(run=command_validate)
    scaffold = commands.add_parser("scaffold", help="show, and with --write apply, what adding the language does to the data")
    scaffold.add_argument("spec")
    scaffold.add_argument("--write", action="store_true", help="write the data, then build and run the validators and tests")
    scaffold.add_argument("--no-checks", action="store_true", help="with --write: skip the build, validators and tests")
    scaffold.add_argument("--skip-tests", action="store_true", help="with --write: skip only the unit tests")
    scaffold.set_defaults(run=command_scaffold)
    from_issue = commands.add_parser("from-issue", help="turn a verified proposal issue into a spec")
    from_issue.add_argument("--issue-json", help="JSON from: gh issue view N --json body,labels")
    from_issue.add_argument("--body-file", help="the issue body as a text file")
    from_issue.add_argument("--labels", help="comma-separated label names (with --body-file)")
    from_issue.add_argument("--out", help="write the spec here instead of printing it")
    from_issue.set_defaults(run=command_from_issue)
    template = commands.add_parser("issue-template", help="write, or with --check verify, the generated GitHub issue form")
    template.add_argument("--check", action="store_true")
    template.add_argument("--repository", help="OWNER/REPO: also check that data.site.propose_form_url points at this repository's form (CI passes the current one)")
    template.add_argument("--form-dir", default=str(FORM_DIR))
    template.set_defaults(run=command_issue_template)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
