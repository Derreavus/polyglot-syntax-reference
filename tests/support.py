"""Helpers shared by several test files."""
from __future__ import annotations


def add_made_up_language(data: dict, slug: str = "zig", versions: bool = True) -> dict:
    """A complete extra language, defined purely as data.

    With versions=False it has no version history, which is how the tests get a language that has none:
    every real language is gaining version history, so none can stand in for that case.
    """
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
    if not versions:
        return language
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
