# Adding a New Language

Language pages are generated from [`data/site_data.json`](data/site_data.json).
Add the language and its content there; the header menu, homepage cards,
comparison picker and search use the shared language registry.

Someone else proposed the language? Use the proposal workflow instead of
editing by hand: see [Proposing and adding a language](scripts/README.md#proposing-and-adding-a-language).
`scripts/content/add_language.py` scaffolds the language from a verified issue;
this guide then explains how to write what the script leaves as placeholders.

Before writing, read [Contributing](README.md#contributing) for the content
priorities: correctness, clarity, practical value and consistency with current
language conventions.

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
- [ ] If the language has version history: `tracks`, `versions` and `features` added
      (see [Version history](#6-version-history-optional))
- [ ] `python renderer/build_site.py` succeeds and the checks in the
      [Verify](#verify) section pass
- [ ] Reviewed the built site locally (`python scripts/dev/serve_staging.py`)

---

## 1. Add the language

In `languages`:

```json
{
  "slug": "go",
  "name": "Go",
  "status": "available",
  "order": 6,
  "category": "programming",
  "description": "One-line description shown on the homepage card.",
  "version_label": "Go 1.22+ · statically typed, compiled",
  "color": "#00add8",
  "color_text": "#5dc9e2",
  "syntax_checks": { "all": ["[]int", "func("] }
}
```

`slug` becomes the folder and URL (`/go/`) and a CSS class, so it must start with a letter and use only
lowercase letters, digits and `-`. `order` controls dropdown and card order. The `version_label` is the badge
shown under the page title, so state the version or edition there.

- `category` must match a `slug` in the top-level `categories` list.
- `color` is required (`#rrggbb`). The build turns it into the language's tag, card, button and search-result
  colors, and the lane color on the compare page. Nothing in the stylesheet names a language.
- `color_text` is optional. Use it when the main color is too dark to read as text on the dark theme. Without
  it, the text color is the main color blended with the page's text color, which adapts to both themes.
- `syntax_checks` is optional. Snippets under `all` must each appear on the language page, and at least one
  snippet under `any` must. Use it to protect syntax that is easy to corrupt in HTML, such as generics.

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

When a language has no direct equivalent, note that and show the closest
idiomatic approach where one exists.

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
The compare page picks up the new language in its **Add language** menu
automatically; no page or script changes are needed. Compare cells are rendered as inline code, so `<` and `>` are escaped for you
here, unlike in `content_html`.

## 6. Version history (optional)

A language gets version history pages once it has `tracks`. It is optional, and every language on the site
today has it. A track is one ordered list of versions.

**How many tracks.** Start with the language's own release timeline. Add a runtime or compiler track when its
releases have a separate schedule that affects feature availability, as with Node.js for JavaScript or GCC,
Clang and MSVC for C++. Each track needs a page and maintained release data, so include one only when it adds
information readers need. List a version only when something being tracked changes in it.

The five languages on the site today, for reference:

| Language | Tracks |
| --- | --- |
| JavaScript | `ecmascript` (standard), `node` (runtime) |
| Python | `python` (standard) |
| Rust | `rust` (implementation), `edition` (standard) |
| C# | `csharp` (standard), `dotnet` and `netfx` (runtime) |
| C++ | `cpp` (standard), `gcc`, `clang` and `msvc` (implementation) |

Add the pieces in this order.

**Tracks** (the first one, by `order`, gets the short address `/<language>/versions/`; the others get
`/<language>/versions/<track id>/`):

```json
{ "language": "go", "id": "go", "label": "Go", "kind": "standard", "order": 1,
  "description": "Releases of the Go language and toolchain.",
  "changelog_links": [
    { "title": "Official release notes", "url": "https://go.dev/doc/devel/release" }
  ] }
```

`kind` is `standard` (editions of a language standard), `runtime`, `implementation` (a particular compiler or
interpreter) or `environment` (where code runs, such as a browser). `changelog_links` are required, must use https, and are shown as the
page's sources, so there is no need to cite a source for each event.

`version_noun` is optional. It is the word the page uses for one version of the track. Leave it out and the
page picks a word from `kind`, which is edition for `standard`, release for `runtime` and `implementation`, and
version for `environment`. Set it when that reads wrong. Python is a `standard` track whose releases are
versions, so it sets `"version_noun": "version"`. If the track's `label` already ends in the noun, as in
`Rust editions`, the page doesn't say it twice.

**Versions** (one per release, oldest first, each naming its track):

```json
{ "language": "go", "track": "go", "id": "go1.21", "label": "Go 1.21", "aliases": [],
  "released": "2023-08", "order": 12, "status": "released" }
```

- `order` must be unique and increasing within a track, and dates must not go backwards. Use
  `status: "draft"` for a release that is not out yet. Use `status: "complete"` for one whose specification is finished but that has not been
  formally published yet (the version note should say what is still pending). Within a track the statuses must run `released`, then `complete`,
  then `draft`.
- The first version can be a baseline for features that have existed since the beginning.
- A runtime version can add `codename`, `lts_from`, `end_of_life` and `engine` (for example `"V8 12.4"`).
  The page shows them, and marks a version "support ended" once `end_of_life` has passed.

**Features** (things you can recognise in code). `history` maps a track id to that track's events, so a
feature can be on one track or on several:

```json
{
  "language": "go", "slug": "generics", "title": "Generics", "category": "syntax",
  "summary": "Type parameters on functions and types.",
  "topic": "generics",
  "history": {
    "go": [
      { "version": "go1.18", "kind": "added" },
      { "version": "go1.21", "kind": "changed", "note": "Type inference was extended." }
    ]
  },
  "migration": { "legacy": "func Max(a, b interface{}) ...", "modern": "func Max[T cmp.Ordered](a, b T) T ...",
                 "note": "Optional explanation." }
}
```

- `category` is `syntax`, `library`, `behavior` or `tooling`.
- Event kinds are `added`, `changed`, `deprecated` and `removed`. Each track's list has exactly one `added`
  event and it comes first. There is at most one `deprecated` and at most one `removed`, and `removed`
  comes last. `changed` and `removed` need a `note`. Add `"breaking": true` to a `changed` event that can
  break old code.
- Add `"release": "16.6.0"` to name the exact release inside a version where the change first appeared.
- A `deprecated` event may use `"version": null` (with a `note`) when no release deprecated it.
- `scope` limits an event, for example `"scope": "strict mode only"`.
- `replaced_by` lists the feature slugs that replace a deprecated or removed feature. They may be on a
  different track.
- A `migration` needs both snippets. Make the newer snippet valid in the version that added the feature.
- `topic` must be an existing topic slug for the same language, or left out.
- Each track is checked on its own. Do not try to keep tracks in step: a runtime can ship a feature before
  the language standard publishes it.

---

## Verify

```bash
python renderer/build_site.py
python -m unittest discover -s tests
python scripts/validate/validate_staging_parity.py
python scripts/validate/validate_syntax_html.py
python scripts/validate/validate_links.py
python scripts/validate/validate_html_smoke.py
```

`validate_syntax_html.py` checks every language page for missing structure, raw
`<`/`>` in code blocks, and forbidden Unicode substitutes. It also carries a
small list of generic-syntax patterns that must appear on the C++, Rust, C#, and
Python pages. A new language gets the general checks automatically; add its
own expected patterns to that script if it has syntax that is easy to corrupt.

If the language has version history, it also gets a checker in `scripts/check/` and a test in `tests/checkers/`,
like the other languages. [scripts/README.md](scripts/README.md#the-per-language-checkers) explains what the
existing checkers do.

CI runs the same steps, so a PR that skips them will fail. A language that came
from the proposal script starts with placeholder topics: replace every one, then
run `python scripts/validate/validate_syntax_html.py --no-placeholders`, which
fails while any placeholder is left.
