"""A visitor proposes a language; a maintainer verifies it; a script scaffolds it. These tests guard every step.

The language used throughout is made up for the tests and appears nowhere in the code under test.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in ("renderer", "scripts/lib", "scripts/content"):
    sys.path.insert(0, str(ROOT / folder))

import add_language  # noqa: E402
import language_spec as ls  # noqa: E402
from load_data import get_languages, load_data  # noqa: E402
from render_compare import render_compare_page  # noqa: E402
from render_home import render_home_page  # noqa: E402
from render_language import render_language_page  # noqa: E402
from validate_data import validate_data_model  # noqa: E402

DATA = load_data()
SCRIPT = ROOT / "scripts" / "content" / "add_language.py"


def make_spec(data: dict = DATA, **overrides) -> dict:
    spec = {
        "name": "Quillscript", "slug": "quillscript", "category": data["categories"][0]["slug"],
        "description": "A small, embeddable scripting language.",
        "docs": ["https://docs.quillscript.example/manual/"],
        "compare": {row["label"]: f"value_{number} = 1" for number, row in enumerate(data["compare"])},
        "concepts": [concept["slug"] for concept in data["concepts"][:5]],
    }
    spec.update(overrides)
    return spec


def fill_form(spec: dict, data: dict = DATA, *, checked_confirmation: bool = True) -> str:
    """An issue body as GitHub writes it for a form filled in with this spec."""
    names = {c["slug"]: c["name"] for c in data["categories"]}
    titles = {c["slug"]: c["title"] for c in data["concepts"]}
    out = []
    for field in ls.form_fields(data):
        key, label = field["key"], field["label"]
        if key == "_review":
            value = "\n".join(f"- [ ] {o['label']}" for o in field["options"])
        elif key == "_attestation":
            value = f"- [{'x' if checked_confirmation else ' '}] {ls.ATTESTATION}"
        elif isinstance(key, tuple):
            value = spec.get("compare", {}).get(key[1], "")
        elif key == "concepts":
            value = "\n".join(f"- [{'x' if slug in spec.get('concepts', []) else ' '}] {title}" for slug, title in titles.items())
        elif key == "category":
            value = names.get(spec.get("category", ""), spec.get("category", ""))
        elif key in ("docs", "extra_sections"):
            value = "\n".join(spec.get(key, []))
        else:
            value = spec.get(key, "")
        out.append(f"### {label}\n\n{value or ls.NO_RESPONSE}")
    return "\n\n".join(out) + "\n"


def parse_yaml_subset(text: str):
    """Reads back exactly the YAML subset the form generator writes, so the test needs no YAML library."""
    lines = [(len(l) - len(l.lstrip(" ")), l.strip()) for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]

    def scalar(token: str):
        if token in ("true", "false"):
            return token == "true"
        if token in ("[]", "{}"):
            return json.loads(token)
        return json.loads(token) if token.startswith('"') else int(token)

    def block(i: int, indent: int):
        return listing(i, indent) if lines[i][1].startswith("- ") else mapping(i, indent)

    def mapping(i: int, indent: int):
        out = {}
        while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
            key, _, rest = lines[i][1].partition(":")
            rest = rest.strip()
            if rest:
                out[key], i = scalar(rest), i + 1
            else:
                out[key], i = block(i + 1, lines[i + 1][0])
        return out, i

    def listing(i: int, indent: int):
        out = []
        while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
            rest = lines[i][1][2:]
            if re.match(r"^[A-Za-z_][\w-]*:( |$)", rest):
                lines[i] = (indent + 2, rest)
                item, i = mapping(i, indent + 2)
            else:
                item, i = scalar(rest), i + 1
            out.append(item)
        return out, i

    value, end = block(0, lines[0][0])
    assert end == len(lines), f"unparsed YAML from line {end}"
    return value


class SpecValidationTests(unittest.TestCase):
    def problems(self, **overrides) -> list[str]:
        return ls.validate_spec(make_spec(**overrides), DATA)

    def test_a_complete_spec_is_valid(self) -> None:
        self.assertEqual(self.problems(), [])

    def test_each_mandatory_field_is_reported_by_name_when_missing(self) -> None:
        for key in ls.MANDATORY:
            spec = make_spec()
            del spec[key]
            self.assertIn(f"missing mandatory field: {key}", ls.validate_spec(spec, DATA), key)
        self.assertIn("missing mandatory field: name", self.problems(name="   "))

    def test_every_compare_row_is_mandatory_and_unknown_rows_are_rejected(self) -> None:
        compare = make_spec()["compare"]
        label = next(iter(compare))
        del compare[label]
        self.assertIn(f"compare: no value for '{label}'", ls.validate_spec(make_spec(compare=compare), DATA))
        self.assertIn("compare: unknown row 'Invented row'", self.problems(compare={**make_spec()["compare"], "Invented row": "x"}))
        self.assertIn(f"compare: no value for '{label}'", self.problems(compare={**make_spec()["compare"], label: " "}))

    def test_slug_rules(self) -> None:
        for bad in ("1quill", "Quillscript", "l_a", "l a", "-quill", "x" * 25):
            self.assertTrue(any(p.startswith("slug:") for p in self.problems(slug=bad)), bad)
        taken = DATA["languages"][0]["slug"]
        self.assertIn(f"slug: '{taken}' is already on the site", self.problems(slug=taken))
        self.assertIn("slug: 'compare' is reserved for a page of the site", self.problems(slug="compare"))

    def test_name_clash_ignores_case(self) -> None:
        taken = DATA["languages"][0]["name"]
        self.assertTrue(any("already on the site" in p for p in self.problems(name=taken.upper())))

    def test_category_and_concepts_must_exist(self) -> None:
        self.assertTrue(any(p.startswith("category:") for p in self.problems(category="nonsense")))
        self.assertIn("concepts: unknown concept 'nonsense'", self.problems(concepts=["nonsense"]))
        first = DATA["concepts"][0]["slug"]
        self.assertIn("concepts: a concept is listed twice", self.problems(concepts=[first, first]))

    def test_documentation_addresses_must_be_plain_https_websites(self) -> None:
        for bad in ("http://docs.quillscript.example/", "ftp://docs.quillscript.example/", "javascript:alert(1)", "https://user:pw@docs.quillscript.example/", "https://127.0.0.1/", "https://localhost/", "https://docs.quillscript.example/a b", "docs.quillscript.example"):
            self.assertTrue(any(p.startswith("docs[1]") for p in self.problems(docs=[bad])), bad)
        self.assertTrue(any("more than" in p for p in self.problems(docs=["https://docs.quillscript.example/"] * 11)))
        self.assertTrue(any(p.startswith("release_notes") for p in self.problems(release_notes="http://docs.quillscript.example/")))

    def test_control_and_invisible_characters_are_rejected_everywhere(self) -> None:
        for bad in ("a\u202eb", "a\u200bb", "a\x00b", "a\nb", "a\tb"):
            self.assertTrue(self.problems(name=bad), repr(bad))
            self.assertTrue(self.problems(description=bad), repr(bad))
            label = DATA["compare"][0]["label"]
            self.assertTrue(self.problems(compare={**make_spec()["compare"], label: bad}), repr(bad))

    def test_length_limits(self) -> None:
        self.assertTrue(self.problems(name="n" * 41))
        self.assertTrue(self.problems(description="d" * 161))
        self.assertTrue(self.problems(version_label="v" * 61))
        label = DATA["compare"][0]["label"]
        self.assertTrue(self.problems(compare={**make_spec()["compare"], label: "c" * 201}))

    def test_color_unknown_fields_and_shape(self) -> None:
        self.assertIn("color: must look like #1a2b3c", self.problems(color="red"))
        self.assertEqual(self.problems(color="#1A2B3C"), [])
        self.assertIn("unknown field: html", self.problems(html="<b>"))
        self.assertEqual(ls.validate_spec([], DATA), ["the spec must be a JSON object"])
        self.assertTrue(self.problems(docs="https://docs.quillscript.example/"))

    def test_the_requirements_come_from_the_data(self) -> None:
        wanted = ls.requirements(DATA)
        self.assertEqual([label for label, _ in wanted["compare"]], [row["label"] for row in DATA["compare"]])
        self.assertEqual([slug for slug, _ in wanted["concepts"]], [c["slug"] for c in DATA["concepts"]])


class ScaffoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.before = copy.deepcopy(DATA)
        self.spec = make_spec()
        self.after = ls.scaffold(self.spec, DATA)

    def test_the_input_is_not_changed_and_the_result_is_valid(self) -> None:
        self.assertEqual(DATA, self.before)
        validate_data_model(copy.deepcopy(self.after))

    def test_it_adds_exactly_the_language_its_placeholder_topics_and_its_values(self) -> None:
        self.assertEqual(len(self.after["languages"]), len(DATA["languages"]) + 1)
        self.assertEqual(len(self.after["sections"]), len(DATA["sections"]) + 1)
        self.assertEqual(len(self.after["topics"]), len(DATA["topics"]) + len(self.spec["concepts"]))
        for key in self.after:
            if key not in ("languages", "sections", "topics", "concepts", "compare"):
                self.assertEqual(self.after[key], DATA[key], key)
        for row, original in zip(self.after["compare"], DATA["compare"]):
            self.assertEqual({k: v for k, v in row.items() if k != "quillscript"}, original)
            self.assertEqual(row["quillscript"], self.spec["compare"][row["label"]])

    def test_topics_are_fixed_placeholders_that_carry_nothing_from_the_proposal(self) -> None:
        mine = [t for t in self.after["topics"] if t["language"] == "quillscript"]
        self.assertEqual({t["content_html"] for t in mine}, {ls.PLACEHOLDER_TOPIC_HTML})
        self.assertEqual([t["concept"] for t in mine], [c["slug"] for c in DATA["concepts"] if c["slug"] in self.spec["concepts"]])
        self.assertEqual([t["sort_order"] for t in mine], list(range(1, len(mine) + 1)))
        for concept in self.after["concepts"]:
            self.assertEqual(concept["topics"].get("quillscript"), concept["slug"] if concept["slug"] in self.spec["concepts"] else None)

    def test_order_and_colour(self) -> None:
        added = self.after["languages"][-1]
        self.assertEqual(added["order"], max(l["order"] for l in DATA["languages"]) + 1)
        self.assertNotIn(added["color"], {l["color"].lower() for l in DATA["languages"]})
        self.assertEqual(added["version_label"], "Quillscript")
        chosen = ls.scaffold(make_spec(color="#ABCDEF", version_label="Quillscript 2.1"), DATA)["languages"][-1]
        self.assertEqual((chosen["color"], chosen["version_label"]), ("#abcdef", "Quillscript 2.1"))

    def test_it_is_deterministic_and_refuses_the_same_language_twice(self) -> None:
        self.assertEqual(self.after, ls.scaffold(make_spec(), DATA))
        with self.assertRaisesRegex(ValueError, "already on the site"):
            ls.scaffold(self.spec, self.after)

    def test_it_refuses_a_bad_spec_and_names_every_problem(self) -> None:
        with self.assertRaises(ValueError) as caught:
            ls.scaffold(make_spec(slug="Bad Slug", docs=["http://x.org"]), DATA)
        self.assertIn("slug:", str(caught.exception))
        self.assertIn("docs[1]", str(caught.exception))

    def test_every_page_type_renders_the_new_language(self) -> None:
        language = next(l for l in get_languages(self.after) if l["slug"] == "quillscript")
        self.assertIn("Quillscript", render_language_page(language, self.after, page_rel="quillscript/index.html"))
        self.assertIn("Quillscript", render_home_page(self.after))
        self.assertIn("Quillscript", render_compare_page(self.after))

    def test_text_from_a_proposal_is_always_escaped(self) -> None:
        hostile = "<script>alert(1)</script>"
        spec = make_spec(name="<b>Quillscript</b>", description=hostile, version_label=hostile, compare={label: hostile for label in make_spec()["compare"]})
        data = ls.scaffold(spec, DATA)
        validate_data_model(copy.deepcopy(data))
        language = next(l for l in get_languages(data) if l["slug"] == "quillscript")
        pages = [render_language_page(language, data, page_rel="quillscript/index.html"), render_home_page(data), render_compare_page(data)]
        for page in pages:
            self.assertNotIn(hostile, page)
            self.assertNotIn("<b>Quillscript</b>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", pages[2])

    def test_follow_ups_list_what_the_scaffold_cannot_write(self) -> None:
        notes = ls.follow_ups(ls.normalise_spec(make_spec(release_notes="https://docs.quillscript.example/news", extra_sections=["Coroutines"])))
        joined = "\n".join(notes)
        for part in ("topics", "https://docs.quillscript.example/manual/", "https://docs.quillscript.example/news", "Coroutines"):
            self.assertIn(part, joined)


class IssueFormTests(unittest.TestCase):
    def test_the_form_asks_for_every_compare_row_and_every_concept(self) -> None:
        fields = ls.form_fields(DATA)
        compare = [f for f in fields if isinstance(f["key"], tuple)]
        self.assertEqual([f["key"][1] for f in compare], [row["label"] for row in DATA["compare"]])
        self.assertTrue(all(f["required"] for f in compare))
        concepts = next(f for f in fields if f["key"] == "concepts")
        self.assertEqual([o["label"] for o in concepts["options"]], [c["title"] for c in DATA["concepts"]])
        self.assertEqual(next(f for f in fields if f["key"] == "category")["options"], [c["name"] for c in sorted(DATA["categories"], key=lambda c: c["order"])])

    def test_every_mandatory_field_is_required_in_the_form(self) -> None:
        required = {f["key"] for f in ls.form_fields(DATA) if f["required"] and not isinstance(f["key"], tuple)}
        self.assertTrue({"name", "slug", "category", "description", "docs"} <= required)

    def test_the_form_follows_the_data(self) -> None:
        changed = copy.deepcopy(DATA)
        changed["compare"].append({"concept": changed["concepts"][0]["slug"], "label": "A brand new row", **{l["slug"]: "x" for l in changed["languages"]}})
        self.assertIn("Compare: A brand new row", [f["label"] for f in ls.form_fields(changed)])
        self.assertNotEqual(ls.issue_form_yaml(changed), ls.issue_form_yaml(DATA))

    def test_the_form_satisfies_the_github_issue_form_rules(self) -> None:
        form = parse_yaml_subset(ls.issue_form_yaml(DATA))
        self.assertEqual(set(form), {"name", "description", "title", "labels", "body"})
        self.assertEqual(form["labels"], list(ls.FORM_LABELS))
        self.assertEqual(form["body"][0]["type"], "markdown")
        elements = form["body"][1:]
        self.assertTrue({e["type"] for e in elements} <= {"input", "textarea", "dropdown", "checkboxes"})
        ids = [e["id"] for e in elements]
        labels = [e["attributes"]["label"] for e in elements]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(labels), len(set(labels)))
        self.assertTrue(all(re.fullmatch(r"[A-Za-z0-9_-]+", i) for i in ids))
        self.assertTrue(all(e["attributes"]["options"] for e in elements if e["type"] in ("dropdown", "checkboxes")))
        self.assertTrue(any(e.get("validations", {}).get("required") for e in elements))

    def test_the_generated_text_is_valid_yaml(self) -> None:
        try:
            import yaml
        except ImportError:
            if os.environ.get("CI"):
                self.fail("PyYAML is not installed on CI, so the generated issue form was not parsed by a real YAML parser")
            self.skipTest("PyYAML is not installed; the structure is checked by the other form tests")
        self.assertEqual(yaml.safe_load(ls.issue_form_yaml(DATA)), parse_yaml_subset(ls.issue_form_yaml(DATA)))
        self.assertEqual(yaml.safe_load(ls.issue_config_yaml()), {"blank_issues_enabled": True})

    def test_the_checked_in_form_matches_the_data(self) -> None:
        for name, render in add_language.FORM_FILES.items():
            self.assertEqual((ROOT / ".github" / "ISSUE_TEMPLATE" / name).read_text(encoding="utf-8"), render(DATA), name)


class IssueParsingTests(unittest.TestCase):
    def test_a_filled_form_parses_back_into_the_spec(self) -> None:
        spec = make_spec(version_label="Quillscript 2.1", color="#123abc", release_notes="https://docs.quillscript.example/news", extra_sections=["Coroutines", "Metatables"])
        parsed, problems = ls.parse_issue_body(fill_form(spec), DATA)
        self.assertEqual(problems, [])
        self.assertEqual(parsed, spec)
        self.assertEqual(ls.validate_spec(parsed, DATA), [])

    def test_empty_optional_fields_are_left_out(self) -> None:
        parsed, _ = ls.parse_issue_body(fill_form(make_spec()), DATA)
        self.assertEqual(set(parsed), set(ls.MANDATORY))

    def test_windows_line_endings_reordering_and_unknown_headings(self) -> None:
        body = fill_form(make_spec())
        blocks = body.strip().split("\n\n### ")
        shuffled = "### " + "\n\n### ".join(reversed([b.removeprefix("### ") for b in blocks])) + "\n\n### Something else\n\nignored\n"
        for text in (body.replace("\n", "\r\n"), shuffled):
            parsed, problems = ls.parse_issue_body(text, DATA)
            self.assertEqual((parsed, problems), (make_spec(), []))

    def test_an_unticked_confirmation_is_a_problem(self) -> None:
        _, problems = ls.parse_issue_body(fill_form(make_spec(), checked_confirmation=False), DATA)
        self.assertEqual(problems, ["the confirmation box is not ticked"])

    def test_missing_parts_are_caught_by_validation(self) -> None:
        body = fill_form(make_spec(docs=[], concepts=[]))
        parsed, _ = ls.parse_issue_body(body, DATA)
        problems = ls.validate_spec(parsed, DATA)
        self.assertIn("missing mandatory field: docs", problems)
        self.assertIn("missing mandatory field: concepts", problems)

    def test_markup_in_a_proposal_stays_plain_text(self) -> None:
        parsed, _ = ls.parse_issue_body(fill_form(make_spec(description="<img src=x onerror=alert(1)>")), DATA)
        self.assertEqual(parsed["description"], "<img src=x onerror=alert(1)>")

    def test_an_oversized_body_is_refused(self) -> None:
        huge = fill_form(make_spec()) + "\n" + "x" * ls.LIMITS["body"]  # valid apart from its size
        parsed, problems = ls.parse_issue_body(huge, DATA)
        self.assertEqual(parsed, {})
        self.assertTrue(any("longer than" in p for p in problems))
        self.assertEqual(ls.parse_issue_body(fill_form(make_spec()), DATA)[0], make_spec())

    def test_only_a_verified_issue_becomes_a_spec(self) -> None:
        body = fill_form(make_spec())
        for labels in ([], ["language-proposal"], ["language-proposal", "needs-verification"]):
            with self.assertRaisesRegex(ValueError, "not marked 'verified'"):
                ls.spec_from_issue(body, labels, DATA)
        self.assertEqual(ls.spec_from_issue(body, ["language-proposal", "verified"], DATA), make_spec())
        self.assertEqual(ls.labels_of({"labels": [{"name": "verified"}, "other"]}), ["verified", "other"])

    def test_a_verified_but_invalid_issue_is_still_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "slug:"):
            ls.spec_from_issue(fill_form(make_spec(slug="Bad Slug")), ["verified"], DATA)
        with self.assertRaisesRegex(ValueError, "confirmation"):
            ls.spec_from_issue(fill_form(make_spec(), checked_confirmation=False), ["verified"], DATA)


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = add_language.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        self.data = self.directory / "site_data.json"
        self.data.write_text(ls.data_text(DATA), encoding="utf-8", newline="\n")

    def write(self, name: str, value) -> str:
        path = self.directory / name
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
        return str(path)

    def test_validate_reports_problems_and_exit_codes(self) -> None:
        self.assertEqual(run_cli("--data", str(self.data), "validate", self.write("ok.json", make_spec()))[0], 0)
        code, _, err = run_cli("--data", str(self.data), "validate", self.write("bad.json", make_spec(slug="Bad Slug")))
        self.assertEqual(code, 1)
        self.assertIn("slug:", err)

    def test_scaffold_is_a_dry_run_unless_told_to_write(self) -> None:
        code, out, _ = run_cli("--data", str(self.data), "scaffold", self.write("spec.json", make_spec()))
        self.assertEqual(code, 0)
        self.assertIn("Dry run: nothing was written", out)
        self.assertIn('+      "slug": "quillscript"', out)
        self.assertIn("Still to do by hand", out)
        self.assertEqual(self.data.read_text(encoding="utf-8"), ls.data_text(DATA))

    def test_scaffold_writes_the_data_exactly_as_the_library_computes_it(self) -> None:
        code, _, _ = run_cli("--data", str(self.data), "scaffold", self.write("spec.json", make_spec()), "--write", "--no-checks")
        self.assertEqual(code, 0)
        self.assertEqual(self.data.read_text(encoding="utf-8"), ls.data_text(ls.scaffold(make_spec(), DATA)))
        self.assertEqual(list(self.directory.glob("*.tmp")), [])

    def test_scaffold_refuses_an_invalid_spec_without_touching_the_data(self) -> None:
        code, _, err = run_cli("--data", str(self.data), "scaffold", self.write("spec.json", make_spec(docs=["http://x.org"])), "--write", "--no-checks")
        self.assertEqual(code, 1)
        self.assertIn("docs[1]", err)
        self.assertEqual(self.data.read_text(encoding="utf-8"), ls.data_text(DATA))

    def test_from_issue_needs_the_verified_label(self) -> None:
        body = fill_form(make_spec())
        issue = {"body": body, "labels": [{"name": "language-proposal"}]}
        code, _, err = run_cli("--data", str(self.data), "from-issue", "--issue-json", self.write("issue.json", issue))
        self.assertEqual(code, 1)
        self.assertIn("not marked 'verified'", err)
        issue["labels"].append({"name": "verified"})
        out_path = self.directory / "spec.json"
        code, _, _ = run_cli("--data", str(self.data), "from-issue", "--issue-json", self.write("issue.json", issue), "--out", str(out_path))
        self.assertEqual((code, json.loads(out_path.read_text(encoding="utf-8"))), (0, make_spec()))

    def test_from_issue_accepts_a_body_file_with_labels_and_needs_some_input(self) -> None:
        body_file = self.write("body.md", fill_form(make_spec()))
        self.assertEqual(run_cli("--data", str(self.data), "from-issue", "--body-file", body_file, "--labels", "verified")[0], 0)
        self.assertEqual(run_cli("--data", str(self.data), "from-issue", "--body-file", body_file)[0], 1)
        self.assertEqual(run_cli("--data", str(self.data), "from-issue")[0], 2)

    def test_issue_template_writes_and_checks_the_form(self) -> None:
        form_dir = self.directory / "templates"
        self.assertEqual(run_cli("--data", str(self.data), "issue-template", "--form-dir", str(form_dir), "--check")[0], 1)
        self.assertEqual(run_cli("--data", str(self.data), "issue-template", "--form-dir", str(form_dir))[0], 0)
        self.assertEqual(run_cli("--data", str(self.data), "issue-template", "--form-dir", str(form_dir), "--check")[0], 0)
        (form_dir / "add-language.yml").write_text("# edited by hand\n", encoding="utf-8")
        code, _, err = run_cli("--data", str(self.data), "issue-template", "--form-dir", str(form_dir), "--check")
        self.assertEqual(code, 1)
        self.assertIn("out of date", err)

    def test_the_checked_in_form_passes_the_ci_check(self) -> None:
        self.assertEqual(run_cli("issue-template", "--check")[0], 0)

    def test_the_form_address_is_checked_against_the_repository(self) -> None:
        url = DATA["site"]["propose_form_url"]
        match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/issues/new\?template=(.+)", url)
        self.assertIsNotNone(match, url)
        self.assertEqual(match.group(2), ls.FORM_TEMPLATE)
        self.assertTrue((ROOT / ".github" / "ISSUE_TEMPLATE" / match.group(2)).is_file())
        self.assertEqual(run_cli("--data", str(self.data), "issue-template", "--check", "--repository", match.group(1))[0], 0)
        code, _, err = run_cli("--data", str(self.data), "issue-template", "--check", "--repository", "someone/else")
        self.assertEqual(code, 1)
        self.assertIn("someone/else", err)
        self.assertEqual(ls.form_url("a/b"), "https://github.com/a/b/issues/new?template=add-language.yml")


class EndToEndTests(unittest.TestCase):
    """A made-up language goes from a verified issue to a built site with no edit to any renderer."""

    def test_issue_to_built_site_in_a_copy_of_the_repository(self) -> None:
        copy_root = Path(tempfile.mkdtemp()) / "repo"
        self.addCleanup(shutil.rmtree, copy_root.parent, ignore_errors=True)
        ignore = shutil.ignore_patterns(".git", "dist", "output", "node_modules", ".venv", "graphify-out", "__pycache__", "*.pyc")
        shutil.copytree(ROOT, copy_root, ignore=ignore)
        renderer_before = {p.name: p.read_bytes() for p in (copy_root / "renderer").glob("*.py")}
        static_before = {p: p.read_bytes() for p in (copy_root / "src").rglob("*") if p.is_file()}

        issue = {"body": fill_form(make_spec(release_notes="https://docs.quillscript.example/news")), "labels": [{"name": "language-proposal"}, {"name": "verified"}]}
        (copy_root / "issue.json").write_text(json.dumps(issue), encoding="utf-8")
        python, script = sys.executable, str(copy_root / "scripts" / "content" / "add_language.py")
        step = subprocess.run([python, script, "from-issue", "--issue-json", "issue.json", "--out", "spec.json"], cwd=copy_root, capture_output=True, text=True)
        self.assertEqual(step.returncode, 0, step.stderr)
        step = subprocess.run([python, script, "scaffold", "spec.json", "--write", "--skip-tests"], cwd=copy_root, capture_output=True, text=True)
        self.assertEqual(step.returncode, 0, step.stdout[-1500:] + step.stderr[-1500:])
        self.assertIn("Build and validators passed", step.stdout)
        self.assertIn("SKIP quillscript: every topic is a placeholder", step.stdout)
        release = subprocess.run([python, str(copy_root / "scripts" / "validate" / "validate_syntax_html.py"), "--no-placeholders"], cwd=copy_root, capture_output=True, text=True)
        self.assertEqual(release.returncode, 1)
        self.assertIn("quillscript: 5 of 5 topics are still placeholders", release.stdout)

        self.assertTrue((copy_root / "dist" / "quillscript" / "index.html").is_file())
        self.assertTrue((copy_root / "dist" / "propose" / "index.html").is_file())
        compare = (copy_root / "dist" / "compare" / "index.html").read_text(encoding="utf-8")
        self.assertIn("value_0 = 1", compare)
        self.assertEqual({p.name: p.read_bytes() for p in (copy_root / "renderer").glob("*.py")}, renderer_before)
        self.assertEqual({p: p.read_bytes() for p in (copy_root / "src").rglob("*") if p.is_file()}, static_before)

        architecture = subprocess.run([python, "-m", "unittest", "discover", "-s", "tests/core"], cwd=copy_root, capture_output=True, text=True)
        self.assertEqual(architecture.returncode, 0, architecture.stderr[-1500:])


if __name__ == "__main__":
    unittest.main()
