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

JavaScript is included as a starter reference. New languages can be added through the JSON source without editing the shared page templates.

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

Language features include version information where relevant, so you can identify when particular syntax or functionality was introduced.

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

The canonical authored content and site configuration live in [data/site_data.json](data/site_data.json). The HTML pages and browser-facing data files are generated from that file by [renderer/build_site.py](renderer/build_site.py); do not edit generated HTML or `js/site-data.js` by hand.

The build writes a preview to [output/staging](output/staging) and synchronizes the same generated pages to the repository root for GitHub Pages. Running the build changes local files only; it does not publish or push anything.

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

The comparison page uses the same registry to build its language selector. It starts with no languages selected and allows up to four at a time.

### Local preview

To preview the staged build locally:

```bash
python renderer/build_site.py
python -m unittest discover -s tests
python scripts/serve_staging.py --host 127.0.0.1 --port 8123 --directory output/staging
```

Then open:

- http://127.0.0.1:8123/

This is a local-only workflow. The remote deployment remains unchanged until you explicitly choose to publish.

### Adding a new language

To add a future language:

1. Add the language, its sections, and complete topics to [data/site_data.json](data/site_data.json).
2. Add or update its comparison values and concept mappings in the same file.
3. Regenerate both local outputs with [renderer/build_site.py](renderer/build_site.py).
4. Validate and review the staging site. Never author changes directly in generated HTML.

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

Polyglot Syntax Reference currently focuses on C++, C#, Python, and Rust.

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
