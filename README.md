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
- **Python**
- **Rust**

The project is intentionally focused on building a strong reference for the currently supported languages before expanding into additional languages.

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

## Language Registry

The site now uses a single authoritative language registry in [js/site-data.js](js/site-data.js). The registry defines the currently supported languages and their display order:

- Python
- Rust
- C++
- C#

Each entry includes:

- `name` — displayed name
- `slug` — URL segment and page folder
- `status` — support state for the site
- `order` — display order in navigation and cards

Navigation and homepage cards are generated from that registry, and validation scripts read the same source so the site does not maintain a second hard-coded language list.

### Adding a new language

To add a future language:

1. Add the language entry to the registry.
2. Create the language page under its slug folder, keeping the same static HTML structure.
3. Add the language-specific content and any required section IDs.
4. Ensure the page is referenced by the registry-driven navigation and homepage generation.
5. Run the validation scripts to confirm the site still passes.

This keeps the architecture static-site friendly and avoids introducing a framework.

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
