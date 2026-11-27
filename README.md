# CodeReference

A quick reference for technical details you need while working.

CodeReference brings syntax, concepts, practical patterns, common pitfalls and version history together in one place. It began as the Polyglot Syntax Reference and is expanding from programming languages to other technical references.

## Website

**[Open CodeReference](https://derreavus.github.io/polyglot-syntax-reference/)**

The website is the primary way to use the reference.

---

## What Is CodeReference?

CodeReference is for people who know their way around code but need to check a detail: how another language handles a familiar idea, what changed between releases, or how to use a tool they don't work with every day.

Instead of searching through full documentation for something like:

- “How do I make a dictionary in Rust?”
- “What's the C++ equivalent of this Python pattern?”
- “How does C# handle async?”
- “What did this code do in the version it was written for, and what replaced it?”

It organizes concise answers around the concepts and syntax people commonly look up.

It is a **quick reference**, not a replacement for official documentation. Comparing languages side by side is one of its tools, not its identity.

## How it is organized

- **References** are grouped into categories. Programming languages are the first category.
- **Search** finds a concept, a piece of syntax or a feature across every reference.
- **Version history** shows what was added, changed, deprecated and removed between versions, so old code can be understood and moved forward.
- **Compare** puts the same concept in several languages side by side.

For example, a dictionary has a different name in each of these languages:

| Language | Common type |
| --- | --- |
| Python | `dict` |
| Rust | `HashMap<K, V>` |
| C++ | `std::unordered_map<K, V>` |
| C# | `Dictionary<TKey, TValue>` |

The shared format makes it easier to find the equivalent in a language you know less well.

---

## Languages

Currently covered:

- **C++**
- **C#**
- **JavaScript**
- **Python**
- **Rust**

All five have a version history page. This is what each one tracks:

| Language | Version history tracks |
| --- | --- |
| C++ | The C++ standard, GCC, Clang and MSVC |
| C# | C# language versions, .NET and .NET Framework |
| JavaScript | ECMAScript editions and Node.js |
| Python | Python versions |
| Rust | Rust releases and Rust editions |

Version history is optional. A language can be added without it; language pages and navigation are generated from the shared data rather than maintained as separate templates.

---

## Features

### What you'll find

Language pages use a familiar structure for syntax and common concepts, with examples written in the language's real syntax. Search works across references, and `Ctrl+K` opens it from anywhere. Compare pages put equivalent concepts side by side.

Entries focus on useful examples and practical details: when a pattern fits, common mistakes, recommended defaults and language-specific pitfalls. They are concise references, not complete language manuals.

### Version information

All five current language references include version history (for example, `/rust/versions/`). **Upgrade changes** shows what changed between two versions; **What can I use?** shows the status of features in a selected version. Topic pages link to relevant version notes. The [version history section](#version-history) describes how this information is represented in the project data.

---

## Who Is It For?

It is especially useful when switching languages, reading older code, learning a language, or returning to one you have not used in a while. You don't need to know every language already; the examples connect familiar concepts to the syntax you're looking for.

---

## Structured Content and Local Build

The authored content and site configuration live in [data/site_data.json](data/site_data.json). [renderer/build_site.py](renderer/build_site.py) generates the HTML pages and browser data from it. Edit that source and the hand-authored assets in [src/static](src/static); generated HTML and `js/site-data.js` are build output.

The build writes the complete site to `dist/`, which is gitignored and rebuilt from scratch on every run. Running the build changes local files only; it does not publish or push anything.

> **Transitional note:** the pages, `css/` and `js/` at the repository root are the last generated copy, kept only so GitHub Pages keeps serving the site until it is switched to Actions-based deployment. They are no longer updated by the build and are removed after the switch. Edit `data/site_data.json` and `src/static/` instead.

### Content model

The JSON holds language metadata, homepage content, sections and topic bodies (`content_html`), concept mappings, search terms, comparison rows and version history. The build checks that topics are rendered; parity validation checks page coverage and browser data. `content_html` is authored repository content and treated as trusted HTML. The one-time importer [scripts/content/import_legacy_content.py](scripts/content/import_legacy_content.py) can import topic content from a specified Git revision.

The generated language registry supplies the header menu, homepage cards, search and comparison picker. Adding a language to the data updates these automatically; no language-specific navigation links are needed.

The comparison page starts with no languages selected. Add up to four vertical lanes (`site.compare_max_languages` sets the limit); selections appear in the URL, for example `?lang=python,rust`, so comparisons can be bookmarked or shared.

### Local preview

To preview the built site locally:

```bash
python scripts/dev/serve_staging.py
```

This builds the site, serves `dist/`, and rebuilds when you save a change under `data/`, `src/` or `renderer/`. Refresh after the "Rebuilt" message. Use `--port 8123` to change the port, `--no-watch` to disable rebuilding on save, or `--no-build` to serve existing output.

Then open:

- http://127.0.0.1:8000/

Use this script or open files inside `dist/` to preview current output. A server started at the repository root (for example, an editor's "Go Live" or `python -m http.server`) serves the frozen legacy pages instead. If the port is already in use, stop the other preview server or choose another port.

Run checks with `python -m unittest discover -s tests` and the scripts in `scripts/validate/`.

This is a local-only workflow. The remote deployment remains unchanged until you explicitly choose to publish.

### Version history

Version data lives in [data/site_data.json](data/site_data.json) next to the rest of the content, and every build validates it. The model knows nothing about any one language. All five languages use it.

A language has one or more tracks. A track is an ordered list of versions with its own release data, and a feature keeps a separate history on each track it appears on. These are the tracks today.

| Language | Track | Kind |
| --- | --- | --- |
| C++ | C++ standards | standard |
| C++ | GCC | implementation |
| C++ | Clang | implementation |
| C++ | MSVC | implementation |
| C# | C# language versions | standard |
| C# | .NET (Core and 5+) | runtime |
| C# | .NET Framework | runtime |
| JavaScript | ECMAScript | standard |
| JavaScript | Node.js | runtime |
| Python | Python | standard |
| Rust | Rust | implementation |
| Rust | Rust editions | standard |

The first track of a language is its main one and gets the short address, `/cpp/versions/`. The others get `/cpp/versions/gcc/` and so on.

Tracks are kept apart on purpose. A language feature is only usable once the runtime's engine supports it, so `Array.prototype.at()` was added in ES2022 but first ran in Node.js 16.6. Some features exist on one track only. `crypto.createCipher()` is Node.js only, and `Math.sumPrecise()` has no Node.js entry until a release supports it.

The data has three parts.

- `tracks` have an `id`, a `label`, a `kind` (`standard`, `runtime`, `implementation` or `environment`), an `order`, a `description` and `changelog_links` to the official changelogs. The page shows those links as its sources, so individual events don't each cite one. A track can also set `version_noun`, the word the page uses for one version, such as `edition`, `release` or `version`. Without it the page uses a word that fits the kind, edition for a standard and release for a runtime or an implementation.
- `versions` each belong to a `track` and have an `id`, a `label`, a release date, an `order` number that counts separately for each track, and a `status`. `released` means published. `complete` means the specification is finished but not formally published yet, which is where C++26 sits today. `draft` means it is still being written. A track keeps its versions in that order. Runtime versions can also carry `codename`, `lts_from`, `end_of_life` and `engine`.
- `features` are things you can recognise in code, such as `let` and `const` or `fs.promises`. Each has a `history` that maps a track id to a list of events: `added`, `changed`, `deprecated` and `removed`. An event can name the exact `release` inside a version, like `16.6.0`. A feature can link to the reference `topic` that explains it, name what replaced it with `replaced_by`, which can point at a feature on another track, and carry a `migration` pair with an older and a newer way to write it.

How the model behaves:

- `added: V` means available in V. `removed: V` means not available in V. A removal with a `scope`, such as strict mode only, means the feature still works elsewhere and is shown as restricted.
- A deprecation may have no version. JavaScript marks many legacy features this way without any edition deprecating them, so they appear in their own "no removal planned" section.
- Every comparison uses the integer `order` within one track, never the label. The page shows changes with `from < version <= to`.
- History is stored as changes and never copied per version. A fact stays true until a later event changes it, so the reference pages stay current and the version tools annotate them.
- Each track is validated on its own. Events are never compared across tracks, because a runtime can ship a feature before the standard publishes it.

Each track has its own page with the two views described above. On the Node.js page, support labels update in the browser when an end-of-life date passes.

Where the data comes from differs by language. Every track lists its official changelogs, and its page shows them. Beyond that, the scripts in `scripts/check/` compare the data with real tools where one exists: a Python interpreter, a Rust compiler, GCC and Clang, the C# compiler and a JavaScript parser. [scripts/README.md](scripts/README.md#the-per-language-checkers) says what each one checks.

For JavaScript, the Node.js availability of language features comes from [MDN's browser compatibility data](https://github.com/mdn/browser-compat-data), using the first release with full, unflagged support. Release dates, support windows and end-of-life dates come from the [nodejs/Release schedule](https://github.com/nodejs/Release). Node.js-only APIs were checked against the history recorded in the Node.js type definitions, and the removal of `crypto.createCipher()` in Node.js 22 against the Node.js project's own notes. It is a snapshot, so refresh it when a new Node.js version ships.

The build rejects data that breaks the rules: duplicate or out-of-order versions within a track, versions whose statuses are out of order, a track with no versions or no https changelog links, a history that names an unknown track, a first event that is not `added`, events out of order or after a removal, a removal in the same version as its deprecation, unknown versions, topics or replacements, replacement cycles, and support dates in the wrong order.

`node scripts/check/check_js_examples.js` (after `npm install --no-save acorn`) also checks the JavaScript before-and-after snippets by parsing them in the edition they belong to, and parses every code block in the JavaScript reference topics. It is optional and not part of CI.

A feature with a `topic` appears in that topic's "Version notes". The "What can I use?" view computes each feature's state in the browser with the same rules as `lifecycle_state()` in `renderer/versioning.py`, and the tests keep the two in step.

### Choosing tracks

The model can describe every dimension: the language standard or edition, a runtime, and an implementation such as one compiler. That doesn't mean every language gets a track for each. A track exists only when it tells readers something the other tracks don't, and the data decides that, not habit. Each extra track is another page to read and more data to keep right.

Here is how that worked out.

- JavaScript has ECMAScript and Node.js. A feature can sit in the standard for years before an engine runs it.
- C++ has the standard as its main timeline, plus GCC, Clang and MSVC. Each compiler supports a standard on its own schedule.
- C# has its language versions, .NET and .NET Framework. Framework got its own track once the compatibility checks showed it was worth separating.
- Rust has compiler releases and editions. An edition is a setting you opt into for each crate, so it has its own timeline next to the releases.
- Python has one track.

A version is listed in a track only if something we track happens in it.

### Categories and the language-neutral rule

Every language belongs to a **category** (`categories` in the data file). Today there is one, programming languages, so the site looks the same, but the data is ready for databases, spreadsheets, shells and other kinds of reference without renaming anything.

Adding a language takes data and content only. Nothing in the renderers, scripts or stylesheet may name a particular language: colors are generated from each language's `color`, and the checks for generics or topic counts come from the data. `tests/core/test_architecture.py` enforces this. It builds a made-up sixth language from data alone, and scans the code for any reference to a real language.

### Adding a new language

To propose a language, use **Propose a language** in the home page footer. A maintainer checks the submission against its documentation and can scaffold placeholder topics. The workflow is in [scripts/README.md](scripts/README.md#proposing-and-adding-a-language). To write a language reference, use the [language template](TEMPLATE.md), which covers the data, comparisons, concept links, optional version history and checks.

## Project Status

CodeReference currently covers C++, C#, JavaScript, Python and Rust, each with version history. Ongoing work focuses on accuracy, checking examples against real tools, accessibility and making it easier to move between references.

---

## Contributing

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

For examples, prioritize correctness, clarity and practical value. Keep them consistent with the reference and current language conventions. Add material because it helps answer a question, not just to make a page longer.

---

## Development

The project is a static website.

To work on the project locally:

```bash
git clone https://github.com/Derreavus/polyglot-syntax-reference.git
cd polyglot-syntax-reference
```

For local preview and build instructions, see [Local preview](#local-preview). Before submitting, run the checks listed in [TEMPLATE.md](TEMPLATE.md#verify) or the relevant CI checks. They cover HTML, links, syntax formatting, and accidental changes to code examples.

---

## License

CodeReference is licensed under the MIT License.

See [`LICENSE`](LICENSE) for the full license text.

---

## Repository

**GitHub:** [Derreavus/polyglot-syntax-reference](https://github.com/Derreavus/polyglot-syntax-reference)

**Website:** [derreavus.github.io/polyglot-syntax-reference](https://derreavus.github.io/polyglot-syntax-reference/)
