# Polyglot Syntax Reference

In-depth interactive syntax reference for **Python**, **Rust**, **C++**, and **C#**.

Designed for developers who learn by switching between languages. Each language page follows a consistent structure so you can jump from one language to another and immediately find the equivalent concept.

## Live Site

**https://derreavus.github.io/polyglot-syntax-reference/**

## Structure

```
├── index.html              # Landing page
├── css/style.css           # Shared dark/light theme
├── js/main.js              # Theme, search (Ctrl+K), copy buttons
├── python/index.html       # Python 3.12+ reference
├── rust/index.html         # Rust reference
├── cpp/index.html          # C++20/23 reference
├── csharp/index.html       # C# 12 / .NET 8+ reference
├── compare/index.html      # Cross-language concept matrices
├── scripts/
│   ├── validate_syntax_html.py
│   ├── validate_links.py
│   └── validate_html_smoke.py
└── .github/workflows/ci.yml
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

## Validation (Phase 5)

From the repo root:

```bash
python3 scripts/validate_syntax_html.py   # generics, structure, version badges
python3 scripts/validate_links.py         # internal links + fragments
python3 scripts/validate_html_smoke.py    # well-formed HTML smoke checks
```

GitHub Actions (`.github/workflows/ci.yml`) runs all three on every push and pull request to `main`.

### What the syntax linter catches

- Stripped generics (`Vec>`, `List>`, empty type args)
- Raw ASCII angle brackets inside code blocks that browsers treat as HTML tags
- Missing language version badges / sidebars / topic sections
- Compare-page raw `Vec<T>` / `<T>` that would disappear in the browser

### Correctness notes

Never put raw `<T>` in HTML — the browser treats it as a tag and strips it.

Safe forms that survive HTML parsing:

| Form | Example |
|------|---------|
| HTML entities | `Vec<T>` |
| Math brackets | `Vec⟨T⟩` |
| Fullwidth brackets | `Vec＜T＞` |
| Square brackets (compare page) | `Vec[T]` |

## License

MIT — feel free to fork and extend.
