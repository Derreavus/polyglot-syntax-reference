"""Per-language colors, generated from the data so no stylesheet has to name a language.

Every language in the data has a ``color`` (and optionally a ``color_text``, a lighter variant that is
readable as text on a dark background). The rules below are written once and emitted for each language.
"""

from __future__ import annotations

from typing import Any


def _channel(value: int) -> float:
    unit = value / 255
    return unit / 12.92 if unit <= 0.03928 else ((unit + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    red, green, blue = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def readable_on(hex_color: str) -> str:
    """Text color that stays readable on top of a solid language color."""
    return "#1a1a1a" if luminance(hex_color) > 0.4 else "#ffffff"


RULES = """\
.language-option.{slug}:hover, .language-option.{slug}[aria-current="page"] {{ color: {text}; }}
.lang-btn.{slug}:hover, .lang-btn.{slug}.active {{ color: {on}; background: {color}; }}
.hero-card.{slug} h2 {{ color: {text}; }}
.lang-tag.{slug} {{ background: color-mix(in srgb, {color} 25%, transparent); color: {text}; }}
.xlang-link.{slug}:hover {{ background: {color}; border-color: {color}; color: {on}; }}
.cmd-hit-lang.{slug} {{ background: color-mix(in srgb, {color} 25%, transparent); color: {text}; }}
.quad-card-header.{slug} {{ color: {text}; background: color-mix(in srgb, {color} 12%, transparent); }}
"""


def language_theme_css(data: dict[str, Any]) -> str:
    blocks: list[str] = []
    for language in sorted(data["languages"], key=lambda l: int(l["order"])):
        color = language["color"]
        # Without an explicit text color, blend with the page text color so it adapts to either theme.
        text = language.get("color_text") or f"color-mix(in srgb, {color} 60%, var(--text))"
        blocks.append(RULES.format(slug=language["slug"], color=color, text=text, on=readable_on(color)))
    return "".join(blocks)


def language_theme_style(data: dict[str, Any]) -> str:
    return f'<style id="language-theme">\n{language_theme_css(data)}</style>'
