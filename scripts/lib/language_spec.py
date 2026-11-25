#!/usr/bin/env python3
"""Language proposals as data.

A proposal is a *spec*: a small dict that a visitor's GitHub issue is parsed into. This module holds everything that
decides what a spec may contain and what adding it does to ``data/site_data.json``:

* ``validate_spec``  - every problem with a spec, by field name (mandatory fields first)
* ``scaffold``       - the site data with the language added (never mutates its input)
* ``form_fields``    - the fields of the GitHub issue form, generated from the current data so the mandatory
                       fields (the Compare rows, the concepts) always match the site
* ``parse_issue_body`` - the reverse: an issue body filled in through that form, back into a spec

Everything a visitor writes is untrusted. It is parsed as data, limited in length and checked for control and
invisible characters. It never becomes HTML here: topic pages are written by a maintainer after verification, so
the scaffold writes fixed placeholder text for them. The language's name, description and Compare values are
escaped by the renderers (a test proves it).

The module is language-neutral: it knows nothing about any particular language, only about the shape of the data.
"""

from __future__ import annotations

import copy
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "renderer"))
from validate_data import LANGUAGE_SLUG_PATTERN  # noqa: E402

from proposal import (  # noqa: E402,F401
    ATTESTATION, FORM_LABELS, FORM_TEMPLATE, FORM_TITLE_PREFIX, LIMITS, MANDATORY, NO_RESPONSE, OPTIONAL, REVIEW_CHECKLIST, VERIFIED_LABEL,
    compare_rows, concept_titles, form_fields, form_url, requirements,
)

sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from language_registry import PLACEHOLDER_TOPIC_HTML  # noqa: E402,F401  (the validators read the same text)

# What the scaffold writes for a language that has no written topics yet. Fixed text: nothing from a proposal.
PLACEHOLDER_SECTION = {"slug": "overview", "title": "Overview"}

# A suggested colour is optional. Without one the scaffold takes the first of these that no language uses yet.
PALETTE = ("#ef4444", "#f97316", "#10b981", "#06b6d4", "#6366f1", "#a855f7", "#ec4899", "#84cc16")

# Slugs that would collide with a generated page or a folder in the repository.
RESERVED_SLUGS = frozenset({"assets", "compare", "css", "data", "dist", "index", "js", "output", "propose", "src", "static", "versions"})

# ------------------------------------------------------------------ small checks


def _bad_characters(text: str) -> bool:
    """Control, invisible (bidi overrides, zero-width) and unassigned characters. Tabs and newlines count as bad here."""
    return any(unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Co", "Cn"} for ch in text)


def _text_problem(value: Any, field: str, limit: int) -> str | None:
    if not isinstance(value, str):
        return f"{field}: must be text"
    if not value.strip():
        return f"{field}: must not be empty"
    if len(value.strip()) > limit:
        return f"{field}: longer than {limit} characters"
    if _bad_characters(value.strip()):
        return f"{field}: contains control or invisible characters"
    return None


def _url_problem(value: Any, field: str) -> str | None:
    problem = _text_problem(value, field, LIMITS["url"])
    if problem:
        return problem
    text = value.strip()
    if re.search(r"\s", text):
        return f"{field}: must not contain spaces"
    parts = urlsplit(text)
    host = parts.hostname or ""
    if parts.scheme != "https":
        return f"{field}: must be an https address"
    if "." not in host or re.fullmatch(r"[0-9.]+", host):
        return f"{field}: must name a website, not an address"
    if parts.username or parts.password:
        return f"{field}: must not contain a user name or password"
    return None


# ------------------------------------------------------------------ validation


def normalise_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """The same spec with surrounding spaces removed from every text value."""
    out: dict[str, Any] = {}
    for key, value in spec.items():
        if isinstance(value, str):
            out[key] = value.strip()
        elif isinstance(value, list):
            out[key] = [item.strip() if isinstance(item, str) else item for item in value]
        elif isinstance(value, dict):
            out[key] = {k: v.strip() if isinstance(v, str) else v for k, v in value.items()}
        else:
            out[key] = value
    return out


def _empty(value: Any) -> bool:
    return value is None or (hasattr(value, "__len__") and len(value) == 0) or (isinstance(value, str) and not value.strip())


def validate_spec(spec: Any, data: dict[str, Any]) -> list[str]:
    """Every problem with a spec, as plain sentences that name the field. An empty list means it can be scaffolded."""
    if not isinstance(spec, dict):
        return ["the spec must be a JSON object"]
    spec = normalise_spec(spec)
    problems = [f"missing mandatory field: {key}" for key in MANDATORY if key not in spec or _empty(spec[key])]
    problems += [f"unknown field: {key}" for key in sorted(set(spec) - set(MANDATORY) - set(OPTIONAL))]

    if "name" in spec and not _empty(spec["name"]):
        problem = _text_problem(spec["name"], "name", LIMITS["name"])
        if problem:
            problems.append(problem)
        elif spec["name"].casefold() in {l["name"].casefold() for l in data["languages"]}:
            problems.append(f"name: '{spec['name']}' is already on the site")

    if "slug" in spec and not _empty(spec["slug"]):
        slug = spec["slug"]
        if not isinstance(slug, str) or not LANGUAGE_SLUG_PATTERN.match(slug):
            problems.append("slug: must start with a letter and use only lowercase letters, digits and '-'")
        elif len(slug) > LIMITS["slug"]:
            problems.append(f"slug: longer than {LIMITS['slug']} characters")
        elif slug in {l["slug"] for l in data["languages"]}:
            problems.append(f"slug: '{slug}' is already on the site")
        elif slug in RESERVED_SLUGS:
            problems.append(f"slug: '{slug}' is reserved for a page of the site")

    if "category" in spec and not _empty(spec["category"]) and spec["category"] not in {c["slug"] for c in data["categories"]}:
        problems.append("category: must be one of " + ", ".join(sorted(c["slug"] for c in data["categories"])))

    if "description" in spec and not _empty(spec["description"]):
        problem = _text_problem(spec["description"], "description", LIMITS["description"])
        if problem:
            problems.append(problem)

    if spec.get("version_label"):
        problem = _text_problem(spec["version_label"], "version_label", LIMITS["version_label"])
        if problem:
            problems.append(problem)

    if spec.get("color") and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(spec["color"])):
        problems.append("color: must look like #1a2b3c")

    docs = spec.get("docs")
    if isinstance(docs, list) and docs:
        if len(docs) > LIMITS["docs"]:
            problems.append(f"docs: more than {LIMITS['docs']} addresses")
        problems += [p for i, url in enumerate(docs[: LIMITS["docs"]], start=1) if (p := _url_problem(url, f"docs[{i}]"))]
    elif "docs" in spec and not _empty(docs):
        problems.append("docs: must be a list of https addresses")

    if spec.get("release_notes"):
        problem = _url_problem(spec["release_notes"], "release_notes")
        if problem:
            problems.append(problem)

    row_labels = [row["label"] for row in compare_rows(data)]
    compare = spec.get("compare")
    if isinstance(compare, dict) and compare:
        problems += [f"compare: no value for '{label}'" for label in row_labels if _empty(compare.get(label))]
        problems += [f"compare: unknown row '{label}'" for label in compare if label not in row_labels]
        for label in row_labels:
            if not _empty(compare.get(label)):
                problem = _text_problem(compare[label], f"compare '{label}'", LIMITS["compare_value"])
                if problem:
                    problems.append(problem)
    elif "compare" in spec and not _empty(compare):
        problems.append("compare: must map each row label to a value")

    concepts = spec.get("concepts")
    known = concept_titles(data)
    if isinstance(concepts, list) and concepts:
        problems += [f"concepts: unknown concept '{c}'" for c in concepts if c not in known]
        if len(set(concepts)) != len(concepts):
            problems.append("concepts: a concept is listed twice")
    elif "concepts" in spec and not _empty(concepts):
        problems.append("concepts: must be a list of concept slugs")

    sections = spec.get("extra_sections", [])
    if sections:
        if not isinstance(sections, list) or len(sections) > LIMITS["sections"]:
            problems.append(f"extra_sections: must be a list of at most {LIMITS['sections']} titles")
        else:
            problems += [p for i, t in enumerate(sections, start=1) if (p := _text_problem(t, f"extra_sections[{i}]", LIMITS["section_title"]))]
    return problems


# ------------------------------------------------------------------ scaffold


def choose_color(data: dict[str, Any]) -> str:
    used = {str(l.get("color", "")).lower() for l in data["languages"]}
    return next((c for c in PALETTE if c not in used), PALETTE[len(data["languages"]) % len(PALETTE)])


def scaffold(spec: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """The site data with the proposed language added. Raises ValueError listing every problem with the spec.

    The language gets one section with a placeholder topic for each concept it has (fixed text, written by this
    function, never by the proposal). Its Compare values and concept mapping come from the spec. Tracks, versions and
    features are not scaffolded: version history is authored separately from release notes.
    """
    problems = validate_spec(spec, data)
    if problems:
        raise ValueError("; ".join(problems))
    spec = normalise_spec(spec)
    out = copy.deepcopy(data)
    slug = spec["slug"]
    titles = concept_titles(out)
    out["languages"].append({
        "slug": slug, "name": spec["name"], "status": "available",
        "order": max((int(l["order"]) for l in out["languages"]), default=0) + 1,
        "category": spec["category"], "description": spec["description"],
        "version_label": spec.get("version_label") or spec["name"],
        "color": (spec.get("color") or choose_color(out)).lower(),
    })
    out["sections"].append({"language": slug, "slug": PLACEHOLDER_SECTION["slug"], "title": PLACEHOLDER_SECTION["title"], "sort_order": 1})
    for number, concept in enumerate((c for c in out["concepts"] if c["slug"] in spec["concepts"]), start=1):
        out["topics"].append({
            "language": slug, "section": PLACEHOLDER_SECTION["slug"], "slug": concept["slug"], "title": titles[concept["slug"]],
            "concept": concept["slug"], "sort_order": number, "content_html": PLACEHOLDER_TOPIC_HTML, "search_keywords": "",
        })
        concept["topics"][slug] = concept["slug"]
    for row in compare_rows(out):
        row[slug] = spec["compare"][row["label"]]
    return out


def follow_ups(spec: dict[str, Any]) -> list[str]:
    """What a maintainer still has to do after the scaffold, from the parts of the spec the scaffold cannot write."""
    notes = ["write the topics (every topic is a placeholder)", "check the language's colour and its Compare values against the documentation"]
    notes += [f"documentation: {url}" for url in spec.get("docs", [])]
    if spec.get("release_notes"):
        notes.append(f"version history, from the release notes at {spec['release_notes']}")
    notes += [f"language-specific section to author: {title}" for title in spec.get("extra_sections", [])]
    return notes


def data_text(data: dict[str, Any]) -> str:
    """The data file exactly as the repository stores it."""
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def diff_text(before: dict[str, Any], after: dict[str, Any], limit: int = 400) -> str:
    lines = list(difflib.unified_diff(data_text(before).splitlines(), data_text(after).splitlines(), "site_data.json (before)", "site_data.json (after)", n=1, lineterm=""))
    if len(lines) > limit:
        lines = lines[:limit] + [f"... {len(lines) - limit} more lines"]
    return "\n".join(lines)


# ------------------------------------------------------------------ the issue form


def issue_form(data: dict[str, Any]) -> dict[str, Any]:
    """The GitHub issue form as a data structure (``issue_form_yaml`` writes it out)."""
    body: list[dict[str, Any]] = [{"type": "markdown", "attributes": {"value": (
        "Propose a language for the reference. Everything here is **reviewed by a maintainer against the documentation you supply** "
        "before anything reaches the site. Fields marked required must be filled in; the rest are optional. Plain text only: "
        "nothing you write is run or shown as page markup."
    )}}]
    for number, field in enumerate(form_fields(data), start=1):
        attributes: dict[str, Any] = {"label": field["label"]}
        if field.get("description"):
            attributes["description"] = field["description"]
        if field.get("placeholder"):
            attributes["placeholder"] = field["placeholder"]
        if field.get("options"):
            attributes["options"] = field["options"]
        element: dict[str, Any] = {"type": field["type"], "id": f"field-{number}", "attributes": attributes}
        if field["type"] != "checkboxes":
            element["validations"] = {"required": bool(field["required"])}
        body.append(element)
    return {"name": "Propose a language", "description": "Suggest a language to add to the reference", "title": FORM_TITLE_PREFIX, "labels": list(FORM_LABELS), "body": body}


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)  # a JSON string is a valid YAML double-quoted scalar


def _yaml_lines(value: Any, indent: int) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key}:")
                lines += _yaml_lines(item, indent + 1)
            else:
                lines.append(f"{pad}{key}: {'[]' if item == [] else '{}' if item == {} else _scalar(item)}")
    else:
        for item in value:
            if isinstance(item, dict) and item:
                inner = _yaml_lines(item, indent + 1)
                lines.append(f"{pad}- {inner[0].lstrip()}")
                lines += inner[1:]
            elif isinstance(item, (dict, list)):
                lines.append(f"{pad}- {'[]' if item == [] else '{}'}")
            else:
                lines.append(f"{pad}- {_scalar(item)}")
    return lines


GENERATED_NOTE = "# Generated by scripts/content/add_language.py issue-template from data/site_data.json. Do not edit by hand."


def issue_form_yaml(data: dict[str, Any]) -> str:
    return GENERATED_NOTE + "\n" + "\n".join(_yaml_lines(issue_form(data), 0)) + "\n"


def issue_config_yaml() -> str:
    return GENERATED_NOTE + "\nblank_issues_enabled: true\n"


# ------------------------------------------------------------------ parsing an issue


def labels_of(issue: dict[str, Any]) -> list[str]:
    """Label names from the JSON that ``gh issue view --json body,labels`` prints (labels are objects or plain names)."""
    return [str(l["name"] if isinstance(l, dict) else l) for l in issue.get("labels", [])]


def require_verified(labels: list[str]) -> None:
    if VERIFIED_LABEL not in labels:
        raise ValueError(f"the issue is not marked '{VERIFIED_LABEL}': a reviewer has to check it against the documentation first")


def _parts(body: str) -> dict[str, str]:
    pieces = re.split(r"(?m)^### (.+?)[ \t]*$", body)
    return {pieces[i].strip(): pieces[i + 1].strip() for i in range(1, len(pieces) - 1, 2)}


def _checked(value: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"(?mi)^\s*[-*] \[x\] (.+?)\s*$", value)]


def parse_issue_body(body: str, data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """An issue body filled in through the form, parsed into a spec, plus problems found while reading it.

    The result still goes through ``validate_spec``. Reading is by heading text, so a renamed or reordered form keeps working.
    """
    if not isinstance(body, str) or len(body) > LIMITS["body"]:
        return {}, [f"the issue text is missing or longer than {LIMITS['body']} characters"]
    parts = _parts(body.replace("\r\n", "\n"))
    problems: list[str] = []
    spec: dict[str, Any] = {"compare": {}}
    categories = {c["name"]: c["slug"] for c in data["categories"]}
    titles = {title: slug for slug, title in concept_titles(data).items()}
    for field in form_fields(data):
        raw = parts.get(field["label"], "")
        raw = "" if raw == NO_RESPONSE else raw
        key = field["key"]
        if key == "_review":
            continue
        if key == "_attestation":
            if ATTESTATION not in _checked(raw):
                problems.append("the confirmation box is not ticked")
        elif isinstance(key, tuple):
            if raw:
                spec["compare"][key[1]] = raw
        elif key == "category":
            if raw:
                spec["category"] = categories.get(raw, raw)
        elif key in ("docs", "extra_sections"):
            items = [re.sub(r"^[-*]\s+", "", line.strip()) for line in raw.splitlines() if line.strip()]
            if items:
                spec[key] = items
        elif key == "concepts":
            chosen = [titles[t] for t in _checked(raw) if t in titles]
            if chosen:
                spec["concepts"] = chosen
        elif raw:
            spec[key] = raw
    if not spec["compare"]:
        del spec["compare"]
    return spec, problems


def spec_from_issue(body: str, labels: list[str], data: dict[str, Any]) -> dict[str, Any]:
    """The whole gate: refuse an issue that is not marked verified, then parse and validate it. Raises ValueError."""
    require_verified(labels)
    spec, problems = parse_issue_body(body, data)
    problems += validate_spec(spec, data)
    if problems:
        raise ValueError("; ".join(problems))
    return normalise_spec(spec)
