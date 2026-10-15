"""The CodeReference identity: search first, browse by category, tools, one shared header."""

from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))

from build_site import render_site_data_js
from chrome import render_header
from load_data import get_languages, load_data
from render_compare import render_compare_page
from render_home import render_home_page
from render_language import render_language_page
from render_versions import render_versions_page
from validate_data import validate_data_model
from versioning import tracks_for


def header_of(page: str) -> str:
    return re.search(r'<header class="site-header">.*?</header>', page, re.S).group(0)


class HomePageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.home = render_home_page(self.data)

    def test_brand_and_wording_come_from_the_data(self) -> None:
        site = self.data["site"]
        self.assertEqual(site["brand"], "CodeReference")
        self.assertIn(f"<title>{site['brand']}</title>", self.home)
        self.assertIn(site["home_heading_lines"][0], self.home)
        self.assertIn(site["footer"], self.home)

    def test_search_comes_first_and_opens_the_palette(self) -> None:
        self.assertIn('id="hero-search"', self.home)
        self.assertIn(self.data["site"]["home_search_prompt"], self.home)
        self.assertLess(self.home.index('id="hero-search"'), self.home.index('class="home-section"'))
        runtime = (ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8")
        self.assertIn('document.getElementById("hero-search")', runtime)

    def test_references_are_browsed_by_category(self) -> None:
        self.assertIn('id="category-programming"', self.home)
        self.assertIn("Programming languages", self.home)
        for language in get_languages(self.data):
            self.assertIn(f'href="{language["slug"]}/index.html" class="hero-card {language["slug"]}"', self.home)

    def test_compare_is_a_tool_not_a_reference_card(self) -> None:
        self.assertIn('id="tools-heading"', self.home)
        self.assertLess(self.home.index('id="category-programming"'), self.home.index('id="tools-heading"'))
        tools = self.home[self.home.index('id="tools-heading"'):]
        self.assertIn('href="compare/index.html" class="hero-card tool-card"', tools)
        self.assertNotIn("compare/index.html", self.home[:self.home.index('id="tools-heading"')].split("</header>")[1])

    def test_cards_show_topic_counts_and_version_history_only_where_it_exists(self) -> None:
        javascript = re.search(r'<a href="javascript/index.html".*?</a>', self.home, re.S).group(0)
        python = re.search(r'<a href="python/index.html".*?</a>', self.home, re.S).group(0)
        self.assertRegex(javascript, r"\d+ topics · Version history")
        self.assertIn("topics</p>", python)
        self.assertNotIn("Version history", python)

    def test_categories_are_rendered_in_order_and_empty_ones_are_skipped(self) -> None:
        data = copy.deepcopy(self.data)
        data["categories"] = [
            {"slug": "databases", "name": "Databases", "order": 2, "description": "Query languages."},
            {"slug": "empty", "name": "Empty", "order": 3, "description": "Nothing here yet."},
            data["categories"][0],
        ]
        data["languages"].append({
            "slug": "sql", "name": "SQL", "status": "available", "order": 6, "category": "databases",
            "color": "#e38c00", "description": "Query language.",
        })
        validate_data_model(self._with_sql(data))
        page = render_home_page(data)
        self.assertLess(page.index('id="category-programming"'), page.index('id="category-databases"'))
        self.assertNotIn('id="category-empty"', page)

    def _with_sql(self, data: dict) -> dict:
        data["sections"].append({"language": "sql", "slug": "basics", "title": "Basics", "sort_order": 1})
        data["topics"].append({
            "language": "sql", "section": "basics", "slug": "select", "title": "SELECT", "concept": None,
            "sort_order": 1, "content_html": "<pre><code>SELECT 1;</code></pre>", "search_keywords": "select",
        })
        for row in data["compare"]:
            row["sql"] = "SELECT 1"
        return data

    def test_the_old_name_is_gone_from_every_page(self) -> None:
        javascript = next(l for l in get_languages(self.data) if l["slug"] == "javascript")
        pages = [
            self.home,
            render_compare_page(self.data),
            render_language_page(javascript, self.data, page_rel="javascript/index.html"),
        ]
        pages += [
            render_versions_page(javascript, track, self.data, page_rel="javascript/versions/index.html")
            for track in tracks_for(self.data, "javascript")
        ]
        for page in pages:
            self.assertNotIn("Polyglot", page)

    def test_new_wording_keys_are_required(self) -> None:
        for key in ("home_search_prompt", "nav_references_label", "card_version_history"):
            data = copy.deepcopy(self.data)
            del data["site"][key]
            with self.assertRaisesRegex(ValueError, key):
                validate_data_model(data)


class SharedChromeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()
        self.javascript = next(l for l in get_languages(self.data) if l["slug"] == "javascript")

    def test_every_page_type_uses_the_one_header(self) -> None:
        home = render_home_page(self.data)
        language = render_language_page(self.javascript, self.data, page_rel="javascript/index.html")
        compare = render_compare_page(self.data)
        track = tracks_for(self.data, "javascript")[0]
        versions = render_versions_page(self.javascript, track, self.data, page_rel="javascript/versions/index.html")
        self.assertEqual(header_of(home), render_header(self.data, "index.html"))
        self.assertEqual(header_of(language), render_header(self.data, "javascript/index.html", "JavaScript"))
        self.assertEqual(header_of(compare), render_header(self.data, "compare/index.html", action="home"))
        self.assertEqual(header_of(versions), render_header(self.data, "javascript/versions/index.html", "JavaScript"))

    def test_the_menu_names_the_current_reference_or_says_references(self) -> None:
        home = header_of(render_home_page(self.data))
        language = header_of(render_language_page(self.javascript, self.data, page_rel="javascript/index.html"))
        self.assertIn("<span>References</span>", home)
        self.assertIn("<span>JavaScript</span>", language)
        self.assertIn('aria-label="Choose a reference"', home)

    def test_the_action_button_differs_only_where_it_should(self) -> None:
        self.assertIn(">Compare</a>", header_of(render_home_page(self.data)))
        compare = header_of(render_compare_page(self.data))
        self.assertIn(">Home</a>", compare)
        self.assertNotIn(">Compare</a>", compare)

    def test_header_links_follow_the_page_depth(self) -> None:
        self.assertIn('href="../../../index.html" class="logo"', render_header(self.data, "javascript/versions/node/index.html"))
        self.assertIn('href="../../compare/index.html"', render_header(self.data, "javascript/versions/index.html"))

    def test_script_gets_the_brand_from_the_site_data(self) -> None:
        payload = render_site_data_js(self.data)
        self.assertIn('window.POLYGLOT_SITE = {"brand":"CodeReference","brand_short":"CodeReference"};', payload)
        runtime = (ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8")
        self.assertNotIn("Polyglot", runtime)
        self.assertIn("siteInfo.brand", runtime)
        self.assertNotIn("renderHomepageCards", runtime)


if __name__ == "__main__":
    unittest.main()
