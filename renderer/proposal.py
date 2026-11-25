"""What a language proposal consists of: its limits, the fields of the proposal form and what the site data asks for.

One definition used twice: ``scripts/lib/language_spec.py`` generates the GitHub issue form and parses issues from it, and
``render_propose.py`` shows the same fields on the "Propose a language" page. They cannot drift apart because neither
holds its own copy. Everything here is derived from the site data (the Compare rows, the concepts, the categories), so
adding a Compare row to the data changes the form and the page with no other edit.

Language-neutral: nothing here names a language.
"""

from __future__ import annotations

from typing import Any

LIMITS = {
    "name": 40, "slug": 24, "description": 160, "version_label": 60, "compare_value": 200,
    "url": 300, "docs": 10, "section_title": 60, "sections": 10, "body": 60_000,
}

MANDATORY = ("name", "slug", "category", "description", "docs", "compare", "concepts")
OPTIONAL = ("version_label", "color", "release_notes", "extra_sections")

# The GitHub issue form: labels a proposal carries and the one a reviewer adds.
FORM_TEMPLATE = "add-language.yml"  # the file name under .github/ISSUE_TEMPLATE, and the ?template= value in the form address
FORM_TITLE_PREFIX = "Propose language: "
FORM_LABELS = ("language-proposal", "needs-verification")
VERIFIED_LABEL = "verified"
NO_RESPONSE = "_No response_"  # what GitHub writes for an optional field left empty

REVIEW_CHECKLIST = (
    "The documentation links are official",
    "It is a real general-purpose language",
    "Every Compare value matches the documentation",
    "The name and slug are free",
    "Examples compile where a toolchain exists",
)
ATTESTATION = "The documentation links are official, and every value above comes from them."


def form_url(repository: str) -> str:
    """The address that opens the proposal form in ``OWNER/REPO``. ``data.site.propose_form_url`` has to equal this."""
    return f"https://github.com/{repository}/issues/new?template={FORM_TEMPLATE}"


def compare_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    return data["compare"]


def concept_titles(data: dict[str, Any]) -> dict[str, str]:
    return {concept["slug"]: concept["title"] for concept in data["concepts"]}


def requirements(data: dict[str, Any]) -> dict[str, Any]:
    """Everything a proposal has to provide, read from the data. The proposal page and the issue form both use it."""
    titles = concept_titles(data)
    return {
        "mandatory": MANDATORY,
        "optional": OPTIONAL,
        "categories": [(c["slug"], c["name"]) for c in sorted(data["categories"], key=lambda c: c["order"])],
        "compare": [(row["label"], titles.get(row["concept"], row["concept"])) for row in compare_rows(data)],
        "concepts": list(titles.items()),
        "limits": LIMITS,
    }


def form_fields(data: dict[str, Any]) -> list[dict[str, Any]]:
    """The fields of the issue form, in order. ``key`` says where a field lands in the spec; the form and the parser share this."""
    titles = concept_titles(data)
    fields: list[dict[str, Any]] = [
        {"key": "name", "label": "Language name", "type": "input", "required": True, "description": f"As the language writes it. Up to {LIMITS['name']} characters.", "placeholder": "Example Language"},
        {"key": "slug", "label": "Suggested slug", "type": "input", "required": True, "description": f"Lowercase letters, digits and '-', starting with a letter. Up to {LIMITS['slug']} characters. It becomes the address of the language's pages.", "placeholder": "example-language"},
        {"key": "category", "label": "Category", "type": "dropdown", "required": True, "options": [c["name"] for c in sorted(data["categories"], key=lambda c: c["order"])]},
        {"key": "description", "label": "One-line description", "type": "input", "required": True, "description": f"Shown on the home page card. Up to {LIMITS['description']} characters."},
        {"key": "docs", "label": "Official documentation addresses", "type": "textarea", "required": True, "description": f"One https address per line (up to {LIMITS['docs']}). A reviewer checks the proposal against these pages."},
        {"key": "version_label", "label": "Version label", "type": "input", "required": False, "description": "Optional. Shown on the home page card, for example the current version and a short tag."},
        {"key": "color", "label": "Suggested colour", "type": "input", "required": False, "description": "Optional, like #1a2b3c. A maintainer may change it."},
        {"key": "release_notes", "label": "Release notes address", "type": "input", "required": False, "description": "Optional https address of the official release notes, if the language should get version history."},
    ]
    for row in compare_rows(data):
        fields.append({"key": ("compare", row["label"]), "label": f"Compare: {row['label']}", "type": "input", "required": True,
                       "description": f"One line of code in this language for: {titles.get(row['concept'], row['concept'])}. Up to {LIMITS['compare_value']} characters."})
    fields += [
        {"key": "concepts", "label": "Concepts this language has", "type": "checkboxes", "required": False,
         "options": [{"label": title, "required": False} for title in titles.values()],
         "description": "Tick every shared concept the language has. At least one is needed."},
        {"key": "extra_sections", "label": "Language-specific sections", "type": "textarea", "required": False,
         "description": f"Optional. Sections that only this language has, one title per line (up to {LIMITS['sections']})."},
        {"key": "_attestation", "label": "Confirmation", "type": "checkboxes", "required": True, "options": [{"label": ATTESTATION, "required": True}]},
        {"key": "_review", "label": "Reviewer checklist (maintainers only)", "type": "checkboxes", "required": False,
         "options": [{"label": item, "required": False} for item in REVIEW_CHECKLIST], "description": "Leave this unticked. A reviewer ticks it, then adds the 'verified' label."},
    ]
    return fields
