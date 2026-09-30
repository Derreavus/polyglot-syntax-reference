# Adding a New Language

Language pages are generated from [`data/site_data.json`](data/site_data.json).
You do not create an `index.html`, and you do not edit any navigation: the
header dropdown, homepage cards, compare picker, and search all read the
language list at runtime.

**Before you start:** read the [Contributing](README.md#contributing) section of
the README. Priorities in order: correctness, clarity, practical usefulness,
consistency with the existing reference, current language standards.

---

## Checklist before opening a PR

- [ ] Language entry added to `languages` (version/edition in `version_label`)
- [ ] `sections` and `topics` added for the language, following the outline below
- [ ] Every topic has a unique `slug` within the language (it becomes the anchor ID)
- [ ] Code examples are copy-pasteable *real syntax*, not pseudocode
- [ ] `<`, `>` and `&` inside code blocks are written as `&lt;`, `&gt;` and `&amp;`
- [ ] No Unicode stand-ins for syntax (`⟨ ⟩ ≤ ≥ → ⇒`); use the real ASCII operators
- [ ] At least one `★ Default` callout and one `Common mistake` callout, where
      genuinely applicable — don't force it if the language has no strong idiomatic
      default or classic footgun in that section
- [ ] `concepts` mappings added for every concept the language has a topic for
- [ ] A value for the new language added to **every** row in `compare`
- [ ] `python renderer/build_site.py` succeeds and the checks in the
      [Verify](#verify) section pass
- [ ] Reviewed the built site locally (`python scripts/serve_staging.py`)

---

## 1. Add the language

In `languages`:

```json
{
  "slug": "go",
  "name": "Go",
  "status": "available",
  "order": 6,
  "description": "One-line description shown on the homepage card.",
  "version_label": "Go 1.22+ · statically typed, compiled"
}
```

`slug` becomes the folder and URL (`/go/`), and `order` controls dropdown and
card order. The `version_label` is the badge shown under the page title, so state
the version or edition there.

## 2. Add sections

In `sections`, one entry per sidebar heading:

```json
{ "language": "go", "slug": "basics", "title": "Basics", "sort_order": 1 }
```

## 3. Add topics

In `topics`, one entry per topic. The body is trusted HTML in `content_html`:

```json
{
  "language": "go",
  "section": "basics",
  "slug": "variables",
  "title": "Variables & Assignment",
  "concept": "variables",
  "sort_order": 2,
  "content_html": "<pre><code>x := 42</code></pre>",
  "search_keywords": "declare assign short declaration const var"
}
```

- `concept` links the topic to a cross-language concept (see step 4). Use `null`
  when there is no equivalent elsewhere.
- `search_keywords` is optional. Without it, search falls back to the text of the
  topic body. `search_title` is also optional.

### Content conventions

- Code goes in `<pre><code>…</code></pre>`. Copy buttons are added automatically.
- Inline code: `<code class="inline">…</code>`.
- Callouts:

  ```html
  <div class="callout callout-default"><strong>★ Default</strong> The idiomatic choice.</div>
  <div class="callout callout-mistake"><strong>Common mistake</strong> The classic footgun.</div>
  <div class="callout callout-use"><strong>When to use</strong> Guidance on when this fits.</div>
  ```

- Tables (for example the standard library) use plain `<table>` markup, matching
  the existing pages.
- Show bad and good side by side where possible.

### Suggested outline

Match the depth of the existing pages. Topic slugs can vary where the language
demands it (Rust has `ownership`, C++ has `templates`), but keep the order of
ideas consistent so readers can find things across languages.

| Group | Topics |
| --- | --- |
| Basics | data types, variables and assignment, operators, control flow, functions |
| Data modeling | classes and OOP, lightweight data structures (structs, records, dataclasses), typing and generics |
| Collections | core collection types with common operations, comprehensions or the closest functional chain, iterators and generators |
| Advanced | exceptions or the language's error model, resource management (`with`, `using`, RAII, `defer`), async, key standard library, packaging |
| Expansion | gotchas, ecosystem and tooling |

If the language has no equivalent for a topic, say so briefly and show the
closest idiomatic pattern instead of omitting it silently.

## 4. Map cross-language concepts

In `concepts`, add the new topic slug under each concept it belongs to:

```json
{
  "slug": "variables",
  "title": "Variables & Assignment",
  "topics": { "python": "variables", "go": "variables" }
}
```

This drives the "Also in" links on topic pages. Every mapped topic must exist for
that language, or the build fails.

## 5. Add compare values

Every object in `compare` needs a value for the new language key:

```json
{ "concept": "variables", "label": "Mutable value", "go": "x := 42" }
```

(Keep the existing language keys in the row; the example shows only the new one.)
Compare cells are rendered as inline code, so `<` and `>` are escaped for you
here, unlike in `content_html`.

---

## Verify

```bash
python renderer/build_site.py
python -m unittest discover -s tests
python scripts/validate_staging_parity.py
python scripts/validate_syntax_html.py
python scripts/validate_links.py
python scripts/validate_html_smoke.py
```

`validate_syntax_html.py` checks every language page for missing structure, raw
`<`/`>` in code blocks, and forbidden Unicode substitutes. It also carries a
small list of generic-syntax patterns that must appear on the C++, Rust, C#, and
Python pages. A new language gets the general checks automatically; add its
own expected patterns to that script if it has syntax that is easy to corrupt.

CI runs the same steps, so a PR that skips them will fail.
