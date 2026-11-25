"""The "Propose a language" page shows what the proposal form asks for, from the same definition, and links to it."""

from __future__ import annotations

import copy
import html
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in ("renderer", "scripts/lib"):
    sys.path.insert(0, str(ROOT / folder))

import language_spec as ls  # noqa: E402
from chrome import render_footer  # noqa: E402
from load_data import load_data  # noqa: E402
from proposal import REVIEW_CHECKLIST, concept_titles, form_fields  # noqa: E402
from render_home import render_home_page  # noqa: E402
from render_propose import render_propose_page  # noqa: E402
from validate_data import validate_data_model  # noqa: E402

DATA = load_data()
PAGE = render_propose_page(DATA)


def invalid(change) -> str:
    data = copy.deepcopy(DATA)
    change(data)
    try:
        validate_data_model(data)
    except ValueError as error:
        return str(error)
    raise AssertionError("the change was accepted")


class ProposePageTests(unittest.TestCase):
    def test_it_lists_every_comparison_row_and_concept_from_the_data(self) -> None:
        for row in DATA["compare"]:
            self.assertIn(f"<strong>{html.escape(row['label'])}</strong>", PAGE)
        for title in concept_titles(DATA).values():
            self.assertIn(f"<li>{html.escape(title)}</li>", PAGE)

    def test_it_follows_the_data(self) -> None:
        data = copy.deepcopy(DATA)
        data["compare"].append({"concept": data["concepts"][0]["slug"], "label": "A brand new row", **{l["slug"]: "x" for l in data["languages"]}})
        data["concepts"].append({"slug": "brand-new", "title": "A brand new concept", "topics": {}})
        page = render_propose_page(data)
        self.assertIn("<strong>A brand new row</strong>", page)
        self.assertIn("<li>A brand new concept</li>", page)

    def test_it_shows_exactly_the_fields_the_form_asks_for(self) -> None:
        shown = re.findall(r"<dt>(.+?) <span", PAGE)
        asked = [f["label"] for f in form_fields(DATA) if isinstance(f["key"], str) and not f["key"].startswith("_") and f["key"] != "concepts"]
        self.assertEqual([html.unescape(label) for label in shown], asked)
        form_labels = {html.unescape(label) for label in re.findall(r'label: "(.+?)"', ls.issue_form_yaml(DATA))}
        self.assertTrue(set(asked) <= form_labels)

    def test_required_and_optional_fields_are_marked(self) -> None:
        required = sum(1 for f in form_fields(DATA) if isinstance(f["key"], str) and not f["key"].startswith("_") and f["key"] != "concepts" and f["required"])
        self.assertEqual(PAGE.count("propose-required"), required)
        self.assertIn("propose-optional", PAGE)

    def test_the_category_field_lists_its_options_and_the_review_checklist_is_shown(self) -> None:
        self.assertIn(html.escape(DATA["site"]["propose_options_prefix"]), PAGE)
        for category in DATA["categories"]:
            self.assertIn(html.escape(category["name"]), PAGE)
        for item in REVIEW_CHECKLIST:
            self.assertIn(f"<li>{html.escape(item)}</li>", PAGE)

    def test_the_button_goes_to_the_configured_form(self) -> None:
        url = DATA["site"]["propose_form_url"]
        self.assertIn(f'<a class="propose-button" href="{html.escape(url, quote=True)}" rel="noopener">', PAGE)
        self.assertTrue(url.startswith("https://"))

    def test_the_page_has_no_inline_script_and_no_event_handlers(self) -> None:
        body = PAGE.split("<body>", 1)[1]  # the shared <head> has the site's own theme script; the page itself adds none
        self.assertNotIn("<script", body)
        self.assertEqual(re.findall(r"\son\w+\s*=", PAGE), [])

    def test_wording_and_data_are_escaped(self) -> None:
        data = copy.deepcopy(DATA)
        hostile = "<script>alert(1)</script>"
        data["concepts"][0]["title"] = hostile
        data["compare"][0]["label"] = hostile
        data["site"]["propose_intro"] = hostile
        data["site"]["propose_steps"] = [hostile]
        page = render_propose_page(data)
        self.assertNotIn(hostile, page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_it_uses_the_shared_header_and_a_footer_without_a_link_to_itself(self) -> None:
        self.assertIn('class="site-header"', PAGE)
        self.assertIn('href="../index.html" class="logo"', PAGE)
        self.assertIn(DATA["site"]["footer"], PAGE)
        self.assertNotIn("<a ", PAGE.split("<footer", 1)[1])


class FooterLinkTests(unittest.TestCase):
    def test_the_home_page_footer_links_to_the_page(self) -> None:
        home = render_home_page(DATA)
        self.assertIn(f'<a href="propose/index.html">{html.escape(DATA["site"]["propose_nav_label"])}</a>', home)

    def test_the_link_is_relative_to_the_page_it_is_on(self) -> None:
        site = DATA["site"]
        self.assertIn('href="../propose/index.html"', render_footer(site, "compare/index.html"))
        self.assertIn('href="../../propose/index.html"', render_footer(site, "javascript/versions/index.html"))
        self.assertNotIn("propose", render_footer(site))
        self.assertNotIn("propose/index.html", render_footer(site, "propose/index.html"))


class SiteSettingsTests(unittest.TestCase):
    def test_the_wording_and_the_form_address_are_required_site_settings(self) -> None:
        for key in ("propose_nav_label", "propose_title", "propose_heading", "propose_intro", "propose_button", "propose_form_url", "propose_steps"):
            self.assertIn(f"data.site missing keys: {key}", invalid(lambda d, key=key: d["site"].pop(key)))
        self.assertIn("propose_intro must be a non-empty string", invalid(lambda d: d["site"].update(propose_intro="  ")))

    def test_the_steps_must_be_a_list_of_text(self) -> None:
        for bad in ([], [""], "one step", [1]):
            self.assertIn("propose_steps must contain non-empty strings", invalid(lambda d, bad=bad: d["site"].update(propose_steps=bad)))

    def test_the_form_address_must_be_https_without_spaces(self) -> None:
        for bad in ("http://github.com/x", "javascript:alert(1)", "https://github.com/a b", "github.com/x"):
            self.assertIn("propose_form_url must be an https address", invalid(lambda d, bad=bad: d["site"].update(propose_form_url=bad)))


if __name__ == "__main__":
    unittest.main()
