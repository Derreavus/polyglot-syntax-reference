# New Language Page Template

Use this as the structural blueprint for adding a new language to Polyglot Syntax
Reference. Copy this file, rename it, and fill in each section with real, working
syntax for your language — matching the depth and structure of the existing
Python / Rust / C++ / C# pages.

**Before you start:** read the [Contributing](../README.md#contributing) section
of the README. Priorities in order: correctness, clarity, practical usefulness,
consistency with the existing reference, current language standards.

---

## Checklist before opening a PR

- [ ] Page follows the folder convention: `/<language>/index.html`
- [ ] Nav bar updated across **all** existing language pages (and homepage) to
      link to the new language
- [ ] Every section below is present with a matching anchor ID
- [ ] Version/edition stated up top (e.g. "Go 1.22+", "Java 21+")
- [ ] Code examples are copy-pasteable *real syntax*, not pseudocode
- [ ] At least one `★ Default` callout and one `Common mistake` callout, where
      genuinely applicable — don't force it if the language doesn't have a
      strong idiomatic default or a classic footgun in that section
- [ ] Ran the repo's validation scripts (HTML validity, internal links, syntax
      formatting, Unicode substitution check)
- [ ] Added an entry to the Compare page for any concepts that already exist
      there for other languages

---

## Page header

```
# <Language> Syntax Reference

<Version/edition> · <one-line descriptor, e.g. "statically typed, compiled">
```

---

## Basics

### Data Types `#types`
<!-- Scalars, literals (including numeric literal formats), primitive collection
     types if relevant here vs. in Collections. Show declaration syntax with
     and without explicit typing if the language supports both. -->

### Variables & Assignment `#variables`
<!-- Declaration, mutability (const/mut/readonly/final — whatever the language's
     equivalent is), multiple assignment, destructuring/unpacking if supported,
     compound assignment operators. -->

### Operators `#operators`
<!-- Arithmetic, comparison, logical, bitwise, identity vs. equality if the
     language distinguishes them, any range/chaining operators. -->

### Control Flow `#control`
<!-- if/else, pattern matching or switch, loops, ternary/conditional expression
     if one exists. -->

### Functions `#functions`
<!-- Declaration syntax, default/optional params, variadic params, positional-
     vs-keyword-only if applicable, anonymous functions/closures, decorators
     or attributes if the language has an equivalent. -->

---

## Data Modeling

### Classes & OOP `#classes`
<!-- Class declaration, constructors, inheritance, interfaces/traits/protocols,
     method overriding, visibility/access modifiers. -->

### Dataclasses & Named Tuples `#dataclasses`
<!-- The language's equivalent for lightweight structured data (structs,
     records, dataclasses, named tuples — whatever fits). If the language has
     no direct equivalent, say so briefly and show the closest idiomatic
     pattern instead of leaving this blank. -->

**★ Default data bag** <!-- state the idiomatic choice for simple field
containers in this language -->

### Type Hints `#typing`
<!-- Static typing syntax, generics/type parameters, union/optional types,
     structural typing (protocols/interfaces) if relevant. Skip or adapt this
     section heading if the language is dynamically typed with no annotation
     system — note that explicitly rather than omitting silently. -->

---

## Collections

### Collections `#collections`
<!-- The core built-in collection types (list/array, map/dict, set, etc.) with
     common operations (add, get-with-default, iterate). -->

**★ Defaults** <!-- name the collection types most idiomatic to reach for -->

### Comprehensions `#comprehensions`
<!-- List/dict/set comprehensions or the closest equivalent (LINQ, iterator
     chains, etc.). If the language has no comprehension syntax, show the
     idiomatic functional-chain alternative instead. -->

### Iterators & Generators `#iterators`
<!-- Custom iteration protocol, generator/yield syntax if present, common
     lazy-iteration standard library helpers. -->

---

## Advanced

### Exceptions `#exceptions`
<!-- Try/catch/finally or the language's error-handling model (including
     Result/Option-style approaches if that's idiomatic instead of exceptions —
     adapt the heading content accordingly, note the paradigm shift explicitly). -->

### Context Managers `#context`
<!-- Resource-management syntax: with-statements, using-statements, RAII,
     defer, try-with-resources — whatever the language's idiom is. -->

### Async / Await `#async`
<!-- Async function declaration, awaiting, concurrent execution of multiple
     async operations, running the async runtime/entry point. -->

### Key Standard Library `#stdlib`
<!-- Table format, matching existing pages:

| Module/Package | Import | Use for |
| --- | --- | --- |
| ... | ... | ... |

List the 8-10 most commonly reached-for standard library modules. -->

### Packaging `#packaging`
<!-- Environment/dependency management, install commands, the current
     recommended tooling (not just what's oldest/most common historically). -->

---

## Expansion

### Gotchas `#gotchas`
<!-- The classic footguns for this language — mutable default args, integer
     overflow behavior, off-by-one traps, whatever is genuinely well-known to
     bite people. Show bad vs. good side by side where possible. -->

**Common mistake** <!-- one-line summary of the single most important gotcha
to internalize -->

### Ecosystem & Tooling `#ecosystem`
<!-- Environment setup, install/add-dependency commands, lint/format/type-check/
     test tool commands, a single "run this file" command. -->

**★ Defaults** <!-- name the modern go-to toolchain, not every option that
exists -->

---

## Footer

```
[GitHub](https://github.com/Derreavus/polyglot-syntax-reference) · <Language> reference
```
