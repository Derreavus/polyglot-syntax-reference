from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))

from build_site import render_site_data_js
from load_data import get_languages, load_data
from render_compare import render_compare_page
from render_home import render_home_page
from render_language import render_language_page, wrap_tables
from validate_data import validate_data_model


class DataSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()

    def test_language_pages_render_topics_and_bodies_from_data(self) -> None:
        for language in get_languages(self.data):
            page = render_language_page(
                language,
                self.data,
                page_rel=f"{language['slug']}/index.html",
            )
            topics = [
                topic for topic in self.data["topics"]
                if topic["language"] == language["slug"]
            ]
            with self.subTest(language=language["slug"]):
                for topic in topics:
                    self.assertIn(f'id="{topic["slug"]}"', page)
                    self.assertIn(wrap_tables(topic["content_html"]), page)

    def test_compare_sections_and_navigation_come_from_data(self) -> None:
        data = copy.deepcopy(self.data)
        data["compare_sections"].append({
            "slug": "data-defined-section",
            "title": "Data-defined section",
            "concepts": [],
        })

        page = render_compare_page(data)

        self.assertIn('href="#data-defined-section">Data-defined section</a>', page)
        self.assertIn('id="data-defined-section"', page)

    def test_compare_starts_empty_and_offers_an_add_language_control(self) -> None:
        page = render_compare_page(self.data)

        self.assertIn('id="lane-add"', page)
        self.assertIn('id="lane-menu"', page)
        self.assertIn('data-max-lanes="4"', page)
        self.assertIn('id="compare-empty-state"', page)
        self.assertNotIn('type="checkbox"', page)
        self.assertNotIn("compare-language-options", page)
        self.assertRegex(page, r'<section class="compare-section" id="basics" hidden>')
        self.assertIn('<th role="columnheader" data-language="python" hidden>Python</th>', page)
        self.assertIn('<td role="cell" data-language="python" hidden>', page)
        runtime = (ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8")
        self.assertIn("function initCompareBoard()", runtime)
        self.assertIn('board.getAttribute("data-max-lanes")', runtime)

    def test_compare_lane_limit_comes_from_data(self) -> None:
        data = copy.deepcopy(self.data)
        data["site"]["compare_max_languages"] = 3

        page = render_compare_page(data)

        self.assertIn('data-max-lanes="3"', page)
        self.assertIn("pick up to 3 languages", page)

    def test_every_compare_row_gets_a_cell_per_language(self) -> None:
        data = copy.deepcopy(self.data)
        data["languages"].append(
            {"slug": "go", "name": "Go", "order": 99, "color": "#00add8"}
        )

        page = render_compare_page(data)

        row_count = page.count('<td class="concept" role="rowheader">')
        self.assertGreater(row_count, 0)
        self.assertEqual(page.count('<td role="cell" data-language="go" hidden>'), row_count)

    def test_language_color_is_optional_but_must_be_a_hex_color(self) -> None:
        data = copy.deepcopy(self.data)
        del data["languages"][0]["color"]
        validate_data_model(data)

        data["languages"][0]["color"] = "red"
        with self.assertRaisesRegex(ValueError, "color must be a #rrggbb"):
            validate_data_model(data)

    def test_language_page_has_section_drawer_and_scrolling_tables(self) -> None:
        language = self.data["languages"][0]
        page = render_language_page(language, self.data, page_rel=f"{language['slug']}/index.html")

        self.assertIn('document.documentElement.classList.add("js")', page)
        self.assertIn('<aside class="sidebar" id="sections-drawer"', page)
        self.assertIn('class="drawer-close"', page)
        self.assertIn('class="sidebar-scroll scroll-fade"', page)
        for lang in self.data["languages"]:
            rendered = render_language_page(lang, self.data, page_rel=f"{lang['slug']}/index.html")
            self.assertEqual(rendered.count("<table"), rendered.count('<div class="table-scroll scroll-fade"><table'))

    def test_scroll_cues_replace_visible_scrollbars_in_runtime_assets(self) -> None:
        runtime = (ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8")
        styles = (ROOT / "src" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("function bindScrollFade(", runtime)
        self.assertIn("function initSectionDrawer()", runtime)
        self.assertIn("scrollbar-width: none", styles)
        self.assertIn('.scroll-fade[data-fade="end"]', styles)

    def test_homepage_copy_comes_from_data(self) -> None:
        data = copy.deepcopy(self.data)
        data["site"]["home_description"] = "Unique source-driven homepage copy."

        page = render_home_page(data)

        self.assertIn("Unique source-driven homepage copy.", page)

    def test_language_navigation_is_a_runtime_populated_dropdown(self) -> None:
        pages = [
            render_home_page(self.data),
            render_compare_page(self.data),
            render_language_page(
                self.data["languages"][0],
                self.data,
                page_rel=f'{self.data["languages"][0]["slug"]}/index.html',
            ),
        ]

        for page in pages:
            with self.subTest(page=page[:80]):
                self.assertIn('class="language-menu"', page)
                self.assertIn('class="language-menu-panel"', page)
                self.assertNotIn('class="lang-btn python"', page)

        runtime = (ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8")
        self.assertIn('nav.querySelector(".language-menu")', runtime)
        self.assertIn("registry.forEach(function (lang)", runtime)
        self.assertIn('link.className = "language-option hero-card "', runtime)
        self.assertIn("link.textContent = lang.name", runtime)
        self.assertNotIn("language-option-version", runtime)
        self.assertIn('event.key !== "Escape"', runtime)

    def test_new_language_is_exported_for_dropdown_without_template_edits(self) -> None:
        data = copy.deepcopy(self.data)
        data["languages"].append({
            "slug": "go",
            "name": "Go",
            "status": "available",
            "order": 5,
            "description": "Go language reference.",
            "version_label": "Go 1.24+",
        })

        browser_data = render_site_data_js(data)
        template = render_home_page(data)

        self.assertIn('"slug":"go","name":"Go"', browser_data)
        self.assertIn('class="language-menu"', template)
        self.assertNotIn('class="lang-btn go"', template)

    def test_javascript_is_available_and_renders_a_reference_page(self) -> None:
        validate_data_model(self.data)
        javascript = next(
            language for language in get_languages(self.data)
            if language["slug"] == "javascript"
        )

        home_page = render_home_page(self.data)
        browser_data = render_site_data_js(self.data)
        javascript_page = render_language_page(
            javascript,
            self.data,
            page_rel="javascript/index.html",
        )
        compare_page = render_compare_page(self.data)

        self.assertIn('class="hero-card javascript"', home_page)
        self.assertIn('"slug":"javascript","name":"JavaScript"', browser_data)
        self.assertIn("JavaScript Syntax Reference", javascript_page)
        self.assertIn('id="operators"', javascript_page)
        self.assertIn("===", javascript_page)
        self.assertIn(
            '<th role="columnheader" data-language="javascript" hidden>JavaScript</th>',
            compare_page,
        )
        self.assertIn("<code>xs.map(x =&gt; f(x))</code>", compare_page)

    def test_browser_search_and_cross_language_maps_come_from_data(self) -> None:
        data = copy.deepcopy(self.data)
        data["topics"][0]["search_keywords"] = "json-owned-search-keyword"
        data["concepts"][0]["topics"]["python"] = "json-owned-topic"

        browser_data = render_site_data_js(data)

        self.assertIn("json-owned-search-keyword", browser_data)
        self.assertIn('"python":"json-owned-topic"', browser_data)
        self.assertNotIn("const SEARCH_INDEX = [", (ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8"))
        self.assertNotIn("const CONCEPTS = {", (ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
