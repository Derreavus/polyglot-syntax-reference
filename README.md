# Polyglot Syntax Reference

In-depth interactive syntax reference for **Python**, **Rust**, **C++**, and **C#**.

Designed for developers who learn by switching between languages. Each language page follows a consistent structure so you can jump from one language to another and immediately find the equivalent concept.

## Live Site

Once GitHub Pages is enabled, the site will be available at:

**https://derreavus.github.io/polyglot-syntax-reference/**

## Structure

```
├── index.html          # Landing page
├── css/style.css       # Shared dark/light theme
├── js/main.js          # Theme toggle + scroll spy + search
├── python/index.html   # Python 3.12+ reference
├── rust/index.html     # Rust (Edition 2024) reference
├── cpp/index.html      # C++20/23 reference
├── csharp/index.html   # C# 12 / .NET 8+ reference
└── scripts/
    └── validate_syntax_html.py
```

## Topics Covered (per language)

- Data types & literals
- Variables, operators, control flow
- Functions / methods / closures
- Ownership / memory model (where relevant)
- Classes, structs, records, traits / interfaces
- Inheritance, polymorphism, generics
- Collections & algorithms
- Error handling
- Concurrency / async
- Key standard library highlights
- Modern language features

## Local Preview

Just open `index.html` in a browser, or serve the folder:

```bash
python -m http.server 8000
# then visit http://localhost:8000
```

## Validation

After editing language pages, run:

```bash
python3 scripts/validate_syntax_html.py
```

This checks for:

- stripped / broken generic syntax (`Vec>`, `template` without parameters, etc.)
- unescaped `<` / `>` inside code blocks
- presence of expected generic examples per language
- language version badge (`lang-tag`)

## Correctness notes (Phase 1)

Generic and template syntax in code blocks **must** be HTML-escaped:

| Write in HTML source | Browser shows |
|----------------------|---------------|
| `template<typename T>` | `template<typename T>` |
| `Vec<i32>` | `Vec<i32>` |
| `List<T>` | `List<T>` |
| `make_unique<int>(42)` | `make_unique<int>(42)` |

Never put raw `<T>` in HTML — the browser will treat it as a tag and strip it.

## License

MIT — feel free to fork and extend.
