from __future__ import annotations

from typing import Any


REQUIRED_LANGUAGE_KEYS = {"slug", "name", "order"}
REQUIRED_TOPIC_KEYS = {"language", "section", "slug", "title", "concept"}
REQUIRED_SECTION_KEYS = {"language", "slug", "title"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_data_model(data: dict[str, Any]) -> None:
    languages = data.get("languages", [])
    sections = data.get("sections", [])
    topics = data.get("topics", [])
    concepts = data.get("concepts", [])
    compare_sections = data.get("compare_sections", [])
    site = data.get("site", {})

    _require(isinstance(languages, list), "data.languages must be a list")
    _require(isinstance(sections, list), "data.sections must be a list")
    _require(isinstance(topics, list), "data.topics must be a list")
    _require(isinstance(concepts, list), "data.concepts must be a list")
    _require(isinstance(compare_sections, list), "data.compare_sections must be a list")
    _require(isinstance(site, dict), "data.site must be an object")
    _require(len(languages) > 0, "data.languages is empty")
    required_site_keys = {
        "brand",
        "brand_short",
        "home_meta_description",
        "home_heading_lines",
        "home_description",
        "footer",
        "compare_title",
        "compare_description",
        "compare_heading",
        "compare_intro",
    }
    _require(
        required_site_keys <= set(site),
        f"data.site missing keys: {', '.join(sorted(required_site_keys - set(site)))}",
    )
    _require(
        isinstance(site["home_heading_lines"], list)
        and all(isinstance(line, str) and line.strip() for line in site["home_heading_lines"]),
        "data.site.home_heading_lines must contain non-empty strings",
    )
    for key in required_site_keys - {"home_heading_lines"}:
        _require(isinstance(site[key], str) and site[key].strip(), f"data.site.{key} must be a non-empty string")

    language_slugs = set()
    for index, language in enumerate(languages):
        _require(isinstance(language, dict), f"languages[{index}] must be an object")
        missing = sorted(REQUIRED_LANGUAGE_KEYS - set(language.keys()))
        _require(not missing, f"languages[{index}] missing keys: {', '.join(missing)}")
        slug = language["slug"]
        _require(isinstance(slug, str) and slug.strip(), f"languages[{index}].slug must be a non-empty string")
        _require(slug not in language_slugs, f"duplicate language slug: {slug}")
        language_slugs.add(slug)

    concept_slugs = set()
    for index, concept in enumerate(concepts):
        _require(isinstance(concept, dict), f"concepts[{index}] must be an object")
        slug = concept.get("slug")
        _require(isinstance(slug, str) and slug.strip(), f"concepts[{index}].slug must be non-empty")
        _require(slug not in concept_slugs, f"duplicate concept slug: {slug}")
        concept_slugs.add(slug)

    section_keys = set()
    for index, section in enumerate(sections):
        _require(isinstance(section, dict), f"sections[{index}] must be an object")
        missing = sorted(REQUIRED_SECTION_KEYS - set(section.keys()))
        _require(not missing, f"sections[{index}] missing keys: {', '.join(missing)}")
        language = section["language"]
        _require(language in language_slugs, f"sections[{index}] references unknown language: {language}")
        slug = section["slug"]
        _require(isinstance(slug, str) and slug.strip(), f"sections[{index}].slug must be non-empty")
        section_key = (language, slug)
        _require(section_key not in section_keys, f"duplicate section '{slug}' for language '{language}'")
        section_keys.add(section_key)

    for index, topic in enumerate(topics):
        _require(isinstance(topic, dict), f"topics[{index}] must be an object")
        missing = sorted(REQUIRED_TOPIC_KEYS - set(topic.keys()))
        _require(not missing, f"topics[{index}] missing keys: {', '.join(missing)}")
        language = topic["language"]
        section = topic["section"]
        _require(language in language_slugs, f"topics[{index}] references unknown language: {language}")
        _require(any(s.get("language") == language and s.get("slug") == section for s in sections), f"topics[{index}] references unknown section '{section}' for language '{language}'")
        slug = topic["slug"]
        _require(isinstance(slug, str) and slug.strip(), f"topics[{index}].slug must be non-empty")
        content_html = topic.get("content_html")
        _require(
            isinstance(content_html, str) and content_html.strip(),
            f"topics[{index}].content_html must contain the full topic content",
        )

    for language in languages:
        slug = language["slug"]
        lang_sections = [s for s in sections if s.get("language") == slug]
        lang_topics = [t for t in topics if t.get("language") == slug]
        _require(lang_sections, f"language '{slug}' has no sections")
        _require(lang_topics, f"language '{slug}' has no topics")

        section_slugs = {s.get("slug") for s in lang_sections}
        topic_slugs = [topic.get("slug") for topic in lang_topics]
        _require(
            len(topic_slugs) == len(set(topic_slugs)),
            f"language '{slug}' has duplicate topic slugs",
        )
        for topic in lang_topics:
            _require(topic.get("section") in section_slugs, f"topic '{topic.get('slug')}' is not assigned to a valid section for '{slug}'")
            concept = topic.get("concept")
            _require(
                concept is None or concept in concept_slugs,
                f"topic '{topic.get('slug')}' references unknown concept '{concept}'",
            )

    topic_ids_by_language = {
        language: {topic["slug"] for topic in topics if topic["language"] == language}
        for language in language_slugs
    }
    for concept in concepts:
        mappings = concept.get("topics", {})
        _require(isinstance(mappings, dict), f"concept '{concept['slug']}'.topics must be an object")
        for language, topic_slug in mappings.items():
            _require(language in language_slugs, f"concept '{concept['slug']}' references unknown language '{language}'")
            _require(
                topic_slug in topic_ids_by_language[language],
                f"concept '{concept['slug']}' references missing topic '{language}#{topic_slug}'",
            )

    compare_section_slugs = set()
    for index, section in enumerate(compare_sections):
        _require(isinstance(section, dict), f"compare_sections[{index}] must be an object")
        slug = section.get("slug")
        title = section.get("title")
        _require(isinstance(slug, str) and slug.strip(), f"compare_sections[{index}].slug must be non-empty")
        _require(isinstance(title, str) and title.strip(), f"compare_sections[{index}].title must be non-empty")
        _require(slug not in compare_section_slugs, f"duplicate compare section slug: {slug}")
        compare_section_slugs.add(slug)
        filters = section.get("concepts")
        _require(
            filters is None or isinstance(filters, list),
            f"compare section '{slug}'.concepts must be a list or null",
        )
        for concept_slug in filters or []:
            _require(
                concept_slug in concept_slugs,
                f"compare section '{slug}' references unknown concept '{concept_slug}'",
            )

    compare_rows = data.get("compare", [])
    _require(isinstance(compare_rows, list), "data.compare must be a list")
    for index, row in enumerate(compare_rows):
        _require(isinstance(row, dict), f"compare[{index}] must be an object")
        _require(any(key in row for key in ("label", "concept")), f"compare[{index}] must include a label or concept")

    print("OK   staged data validation")
