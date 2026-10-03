# Polyglot Syntax Reference

A quick reference for anyone who works with multiple programming languages.

Polyglot Syntax Reference makes it easier to switch between programming languages by organizing equivalent syntax, concepts, patterns, and common gotchas into a consistent reference format.

## Website

**[Open Polyglot Syntax Reference](https://derreavus.github.io/polyglot-syntax-reference/)**

The website is the primary way to use the reference.

---

## What Is Polyglot Syntax Reference?

Polyglot Syntax Reference is designed for programmers who already know one or more programming languages and need a quick way to remember how familiar concepts are expressed in another language.

Instead of searching through full language documentation for something like:

- “How do I make a dictionary in Rust?”
- “What's the C++ equivalent of this Python pattern?”
- “How does C# handle async?”
- “What's the syntax for generics in Rust again?”

Polyglot provides a concise reference organized around the concepts and syntax you're likely to need.

It is a **quick reference and comparison tool**, not a replacement for official language documentation.

---

## Why “Polyglot”?

The same programming concept can look very different between languages.

| Language | Common type |
| --- | --- |
| Python | `dict` |
| Rust | `HashMap<K, V>` |
| C++ | `std::unordered_map<K, V>` |
| C# | `Dictionary<TKey, TValue>` |

Polyglot Syntax Reference presents these concepts in a consistent format so you can quickly translate what you already know into another language.

---

## Languages

Currently covered:

- **C++**
- **C#**
- **JavaScript**
- **Python**
- **Rust**

JavaScript has a full reference (19 topics) and is the first language with version history. New languages can be added through the JSON source without editing the shared page templates.

---

## Features

### Consistent language pages

Each language follows a similar organizational structure, so once you know where to find something in one language, you can find the equivalent information in another.

### Quick syntax reference

Concise examples for common language features, syntax, operators, collections, control flow, functions, types, and other frequently referenced concepts.

### Cross-language comparisons

Compare how different languages approach the same programming concept without searching each language's documentation separately.

### Search and keyboard navigation

Use the site's search to quickly find syntax and concepts across the reference. Press `Ctrl+K` to access search without manually browsing the site.

### Copyable examples

Code examples are designed to be copied directly and use the actual syntax of the language rather than visual substitutes.

### Version information

Languages that have version data get a **Version history** page (for example `javascript/versions/`). It lists what was added, changed, deprecated and removed in each version, with before-and-after examples, so you can work out what old code was doing and how to move it to a newer version. The page has two views. **Upgrade changes** lists everything between the version you are upgrading from and the one you are moving to. **What can I use?** shows, for one version, which features are available, deprecated, restricted, removed or not yet available, with the older way to write each missing one. Each topic on the language page also has a collapsed **Version notes** list that links into the history. See [Version history](#version-history).

### Practical guidance

Where useful, reference entries include:

- When to use something
- When to avoid it
- Common mistakes
- Recommended defaults
- Language-specific gotchas

---

## How It Is Organized

The reference is organized around the things programmers commonly need to look up rather than attempting to reproduce complete language documentation.

Typical sections include:

- Basics
- Variables and types
- Operators
- Control flow
- Functions
- Collections
- Generics / templates
- Error handling
- Object-oriented programming
- Asynchronous programming
- Common patterns
- Standard libraries
- Language-specific gotchas

The exact organization varies where a language's design requires it, but the overall goal is to keep concepts easy to locate across languages.

---

## Who Is It For?

Polyglot Syntax Reference is useful for anyone who switches between programming languages, including:

- Developers working with multiple languages
- Developers learning a new language
- Students studying multiple languages
- Hobbyist programmers
- Developers returning to a language they have not used recently
- Anyone who occasionally forgets the exact syntax for something

You do not need to be an expert in every language covered. The reference is intended to help bridge the gap between what you already know and the syntax you need to remember.

---

## Structured Content and Local Build

The canonical authored content and site configuration live in [data/site_data.json](data/site_data.json). The HTML pages and browser-facing data files are generated from that file by [renderer/build_site.py](renderer/build_site.py); do not edit generated HTML or `js/site-data.js` by hand. Hand-authored static assets (`css/style.css`, `js/main.js`) live in [src/static](src/static) and are copied into the build unchanged.

The build writes the complete site to `dist/`, which is gitignored and rebuilt from scratch on every run. Running the build changes local files only; it does not publish or push anything.

> **Transitional note:** the pages, `css/` and `js/` at the repository root are the last generated copy, kept only so GitHub Pages keeps serving the site until it is switched to Actions-based deployment. They are no longer updated by the build and are removed after the switch. Edit `data/site_data.json` and `src/static/` instead.

### Content model

The JSON source contains:

- language metadata and the homepage content
- language navigation populated from the available-language registry
- language-specific sections and complete topic bodies, including examples, notes, and callouts
- concept mappings for cross-language navigation
- search titles and keywords
- comparison rows and their section/group configuration

Each topic stores its complete authored body as `content_html`. The build validates that every topic and body is rendered, and parity validation checks the expected coverage and browser data. Treat `content_html` as trusted, authored repository content. The one-time importer [scripts/import_legacy_content.py](scripts/import_legacy_content.py) accepts an explicit Git revision to import topic content from an existing set of pages.

The header language dropdown is populated at runtime from the generated language registry. Each menu item shows only the language name, in a compact card-style panel that matches the site's colors and borders. Adding a language entry makes it appear in the dropdown; no per-language header link needs to be added to the page templates.

The comparison page uses the same registry to build its **Add language** menu. It starts with no languages selected. Each language you add becomes a vertical lane, up to four at a time (`site.compare_max_languages` in the data file changes the limit). The selection is kept in the URL (`?lang=python,rust`), so a comparison can be bookmarked or shared.

### Local preview

To preview the built site locally:

```bash
python scripts/serve_staging.py
```

This builds the site, serves `dist/`, and rebuilds automatically when you save a change under `data/`, `src/` or `renderer/`. Refresh the browser after the "Rebuilt" message. Responses are sent uncached, so a refresh always shows the latest build. Options: `--port 8123` to change the port, `--no-watch` to disable auto-rebuild, `--no-build` to serve existing output.

Then open:

- http://127.0.0.1:8000/

Preview only through this script (or by opening files inside `dist/`). A server started at the repository root, such as an editor's "Go Live" button or `python -m http.server`, serves the frozen legacy pages at the root, not the current build. If the script reports that the port is already in use, an older preview server is still running; stop it or pick another port.

Run the checks separately with `python -m unittest discover -s tests` and the scripts in `scripts/validate_*.py`.

This is a local-only workflow. The remote deployment remains unchanged until you explicitly choose to publish.

### Version history

Version data lives in [data/site_data.json](data/site_data.json) next to the rest of the content and is validated on every build. It is language-neutral, so the same model is used for every language. JavaScript is the first language to use it.

- **`versions`**: the ordered releases of a language. Each has an `id`, a `label`, a release date, an `order` number and a `status` of `released` or `draft`. For JavaScript a version is an **ECMAScript edition** (ES5, ES2015 and so on), not a browser or Node.js release.
- **`features`**: things you can recognise in code, such as `let` and `const` or `Array.prototype.includes()`. Each has a `history` of events: `added`, `changed`, `deprecated` and `removed`. A feature can link to the reference `topic` that explains it, name what replaced it (`replaced_by`), and carry a `migration` pair with an older and a newer way to write the same thing.
- **`changelog_links`** on the language: links to the official changelogs. The page shows these as its sources instead of citing a source for every event.

How the model behaves:

- `added: V` means available in V. `removed: V` means not available in V. A removal with a `scope` (for example strict mode only) means the feature still works elsewhere and is shown as restricted.
- A deprecation may have no version. JavaScript marks many legacy features this way without any edition deprecating them, so they appear in their own "no removal planned" section.
- Every comparison uses the integer `order`, never the label. The page shows changes with `from < version <= to`.
- History is stored as changes, never copied per version. A fact stays true until a later event changes it, so the reference pages stay current and the version tools annotate them.

The build rejects data that breaks the rules: duplicate or out-of-order versions, a first event that is not `added`, events out of order or after a removal, a removal in the same version as its deprecation, unknown versions, topics or replacements, replacement cycles, and a language with versions but no changelog links.

For JavaScript, `node scripts/check_js_examples.js` (after `npm install --no-save acorn`) also checks the before-and-after snippets by parsing them in the edition they belong to, and parses every code block in the JavaScript reference topics. It is optional and not part of CI.

A feature with a `topic` appears in that topic's **Version notes**. The **What can I use?** view computes each feature's state in the browser with the same rules as `lifecycle_state()` in `renderer/versioning.py`, and the tests keep the two in step.

### Adding a new language

To add a future language:

1. Add the language, its sections, and complete topics to [data/site_data.json](data/site_data.json).
2. Add or update its comparison values and concept mappings in the same file.
3. Rebuild with [renderer/build_site.py](renderer/build_site.py).
4. Validate and review the `dist/` build. Never author changes directly in generated HTML.

This keeps the architecture static-site friendly while making the content source easier to maintain and validate offline.

## Project Philosophy

### Familiar concepts first

The reference focuses on concepts programmers are likely to already understand and shows how those concepts are expressed in each language.

### Concise over comprehensive

The goal is not to document every feature of every language. It is to provide the information most useful when you need a quick answer.

### Practical over academic

Examples should demonstrate how syntax is actually used rather than only showing isolated grammar rules.

### Consistent where possible

Similar concepts should be presented in similar ways across languages, making cross-language comparison easier.

### Accurate over clever

Examples should use valid, current syntax and avoid misleading shortcuts or language-specific tricks unless they are clearly identified.

---

## Project Status

Polyglot Syntax Reference currently covers C++, C#, JavaScript, Python, and Rust. JavaScript also has version history; the other languages do not yet.

The project continues to evolve, with a focus on content accuracy, practical guidance, validated examples, accessibility, and cross-language navigation.

---

## Contributing

Contributions are welcome.

Useful contributions include:

- Correcting inaccurate information
- Fixing outdated syntax
- Improving examples
- Adding useful gotchas
- Improving cross-language comparisons
- Improving accessibility
- Fixing bugs
- Improving the site's tooling and validation
- Proposing useful additions to the reference

When adding or changing examples, prioritize:

1. Correctness
2. Clarity
3. Practical usefulness
4. Consistency with the existing reference
5. Current language standards and conventions

Avoid adding content solely to increase the size of the reference.

---

## Development

The project is a static website.

To work on the project locally:

```bash
git clone https://github.com/Derreavus/polyglot-syntax-reference.git
cd polyglot-syntax-reference
```

Then follow the project's existing development and build instructions.

Before submitting changes, run the available validation and CI checks to ensure that:

- HTML remains valid
- Internal links work
- Syntax content remains correctly formatted
- Code examples have not been corrupted
- Unsupported Unicode syntax substitutions have not been introduced

---

## License

Polyglot Syntax Reference is licensed under the MIT License.

See [`LICENSE`](LICENSE) for the full license text.

---

## Repository

**GitHub:** [Derreavus/polyglot-syntax-reference](https://github.com/Derreavus/polyglot-syntax-reference)

**Website:** [derreavus.github.io/polyglot-syntax-reference](https://derreavus.github.io/polyglot-syntax-reference/)
