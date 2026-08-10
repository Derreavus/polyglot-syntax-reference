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
├── js/main.js          # Theme toggle + scroll spy
├── python/index.html   # Python 3.12+ reference
├── rust/index.html     # Rust (Edition 2024) reference
├── cpp/index.html      # C++20/23 reference
└── csharp/index.html   # C# 12 / .NET 8+ reference
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

## License

MIT — feel free to fork and extend.
