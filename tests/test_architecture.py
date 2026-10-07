"""Architecture tests: the roadmap's "sixth language" rule.

Adding a language must take data and content, not renderer, script or stylesheet changes. These tests add a
made-up language through data alone and check that everything still builds, and they scan the code for any
reference to a specific language.
"""

from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_site import render_site_data_js
from load_data import get_languages, load_data
from render_compare import render_compare_page
from render_home import render_home_page
from render_language import render_language_page
from render_versions import render_versions_page
from theme import language_theme_css, readable_on
from validate_data import validate_data_model
from versioning import TRACK_KINDS, tracks_for, versions_for

CODE_FILES = (
    sorted((ROOT / "renderer").glob("*.py"))
    + [ROOT / "src" / "static" / "js" / "main.js", ROOT / "src" / "static" / "css" / "style.css"]
)


def add_made_up_language(data: dict, slug: str = "zig") -> dict:
    """A complete sixth language, defined purely as data."""
    language = {
        "slug": slug, "name": "Zig", "status": "available", "order": 6, "category": "programming",
        "color": "#f7a41d", "description": "A made-up language used by the architecture test.",
        "version_label": "Zig 0.13 · systems",
    }
    data["languages"].append(language)
    data["sections"].append({"language": slug, "slug": "basics", "title": "Basics", "sort_order": 1})
    data["topics"].append({
        "language": slug, "section": "basics", "slug": "variables", "title": "Variables", "concept": "variables",
        "sort_order": 1, "content_html": "<pre><code>const x: u32 = 1;</code></pre>", "search_keywords": "const var",
    })
    for concept in data["concepts"]:
        if concept["slug"] == "variables":
            concept["topics"][slug] = "variables"
    for row in data["compare"]:
        row[slug] = "const x = 1;"
    data["tracks"].append({
        "language": slug, "id": slug, "label": "Zig", "kind": "standard", "order": 1,
        "description": "Releases of the Zig language.",
        "changelog_links": [{"title": "Release notes", "url": "https://ziglang.org/download/"}],
    })
    data["versions"] += [
        {"language": slug, "track": slug, "id": "zig-0.12", "label": "Zig 0.12", "released": "2024-04", "order": 1, "status": "released"},
        {"language": slug, "track": slug, "id": "zig-0.13", "label": "Zig 0.13", "released": "2024-06", "order": 2, "status": "released"},
    ]
    data["features"].append({
        "language": slug, "slug": "comptime-vars", "title": "comptime variables", "category": "syntax",
        "summary": "Variables evaluated at compile time.", "topic": "variables",
        "history": {slug: [{"version": "zig-0.13", "kind": "added"}]},
        "migration": {"legacy": "var x = 1;", "modern": "comptime var x = 1;"},
    })
    return language


class SixthLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.language = add_made_up_language(self.data)

    def test_a_language_defined_only_in_data_validates(self) -> None:
        validate_data_model(copy.deepcopy(self.data))

    def test_every_page_type_renders_the_new_language(self) -> None:
        language = next(l for l in get_languages(self.data) if l["slug"] == "zig")
        page = render_language_page(language, self.data, page_rel="zig/index.html")
        self.assertIn("const x: u32 = 1;", page)
        self.assertIn('class="lang-tag zig"', page)
        self.assertIn("Version history: Zig", page)
        self.assertIn('"slug":"zig"', render_site_data_js(self.data))
        self.assertIn('data-language="zig"', render_compare_page(self.data))
        self.assertIn("zig", render_home_page(self.data))

    def test_the_new_language_gets_a_version_page_and_its_colors_from_data(self) -> None:
        track = tracks_for(self.data, "zig")[0]
        page = render_versions_page(self.language, track, self.data, page_rel="zig/versions/index.html")
        self.assertIn('id="feature-comptime-vars"', page)
        self.assertEqual([v["id"] for v in versions_for(self.data, "zig", "zig")], ["zig-0.12", "zig-0.13"])
        css = language_theme_css(self.data)
        self.assertIn(".lang-tag.zig { background: color-mix(in srgb, #f7a41d 25%, transparent);", css)
        self.assertIn("color-mix(in srgb, #f7a41d 60%, var(--text))", css)

    def test_every_language_gets_the_same_set_of_color_rules(self) -> None:
        css = language_theme_css(self.data)
        rules = [line.split(" {")[0].replace(".", "|", 1).split("|")[0] for line in css.splitlines()]
        for language in self.data["languages"]:
            count = sum(1 for line in css.splitlines() if f".{language['slug']}" in line)
            self.assertEqual(count, 7, language["slug"])
        self.assertTrue(rules)

    def test_javascript_is_themed_like_the_other_languages(self) -> None:
        self.assertIn(".lang-tag.javascript {", language_theme_css(load_data()))

    def test_text_on_a_language_color_stays_readable(self) -> None:
        self.assertEqual(readable_on("#f7df1e"), "#1a1a1a")   # yellow
        self.assertEqual(readable_on("#dea584"), "#1a1a1a")   # rust
        self.assertEqual(readable_on("#3776ab"), "#ffffff")   # python blue
        self.assertEqual(readable_on("#00599c"), "#ffffff")

    def test_slugs_must_be_safe_to_use_as_css_classes(self) -> None:
        for bad in ("1zig", "Zig", "z ig", "z_g"):
            data = load_data()
            add_made_up_language(data, slug="zig")
            data["languages"][-1]["slug"] = bad
            with self.assertRaisesRegex(ValueError, "must start with a letter"):
                validate_data_model(data)

    def test_a_new_language_must_name_a_category_and_a_color(self) -> None:
        data = load_data()
        add_made_up_language(data)
        data["languages"][-1]["category"] = "databases"
        with self.assertRaisesRegex(ValueError, "unknown category 'databases'"):
            validate_data_model(data)


class CodeIsLanguageNeutralTests(unittest.TestCase):
    """No renderer, script or stylesheet may name a particular language."""

    def setUp(self) -> None:
        self.slugs = [l["slug"] for l in load_data()["languages"]]

    def test_no_code_file_mentions_a_language_slug(self) -> None:
        offenders = []
        for path in CODE_FILES:
            text = path.read_text(encoding="utf-8")
            for slug in self.slugs:
                pattern = rf'''["'`]{slug}["'`]|\.{slug}\b|--{slug}\b|/{slug}/'''
                for number, line in enumerate(text.splitlines(), start=1):
                    if re.search(pattern, line):
                        offenders.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()[:80]}")
        self.assertEqual(offenders, [])

    def test_validation_scripts_take_their_expectations_from_data(self) -> None:
        for name in ("validate_staging_parity.py", "validate_syntax_html.py", "validate_links.py", "validate_html_smoke.py", "language_registry.py"):
            text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            for slug in self.slugs:
                self.assertNotRegex(text, rf'''["']{slug}["']''', f"{name} names {slug}")


class CategoriesAndTrackKindsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()

    def test_categories_are_defined_and_validated(self) -> None:
        self.assertEqual([c["slug"] for c in self.data["categories"]], ["programming"])
        self.assertTrue(all(l["category"] == "programming" for l in self.data["languages"]))
        data = copy.deepcopy(self.data)
        data["categories"].append(dict(data["categories"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate category slug"):
            validate_data_model(data)
        data = copy.deepcopy(self.data)
        data["categories"] = []
        with self.assertRaisesRegex(ValueError, "non-empty list"):
            validate_data_model(data)

    def test_track_kinds_follow_the_roadmap(self) -> None:
        self.assertEqual(TRACK_KINDS, ("standard", "runtime", "implementation", "environment"))
        for kind in TRACK_KINDS:
            data = copy.deepcopy(self.data)
            data["tracks"][0]["kind"] = kind
            validate_data_model(data)
        data = copy.deepcopy(self.data)
        data["tracks"][0]["kind"] = "language"
        with self.assertRaisesRegex(ValueError, "kind must be one of"):
            validate_data_model(data)
        self.assertEqual({t["kind"] for t in self.data["tracks"]}, {"standard", "runtime"})

    def test_syntax_checks_are_validated(self) -> None:
        data = copy.deepcopy(self.data)
        data["languages"][0]["syntax_checks"] = {"every": ["x"]}
        with self.assertRaisesRegex(ValueError, "may only contain 'all' and 'any'"):
            validate_data_model(data)
        data["languages"][0]["syntax_checks"] = {"all": [""]}
        with self.assertRaisesRegex(ValueError, "non-empty strings"):
            validate_data_model(data)


if __name__ == "__main__":
    unittest.main()
