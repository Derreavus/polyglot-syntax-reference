(function () {
  "use strict";

  window.POLYGLOT_LANGUAGES = [
    {"name":"Python","slug":"python","status":"available","order":1,"description":"Readable and versatile. Explore types, collections, async, typing, and the standard library."},
    {"name":"Rust","slug":"rust","status":"available","order":2,"description":"Ownership, borrowing, traits, and zero-cost abstractions. Safe systems programming without a GC."},
    {"name":"C++","slug":"cpp","status":"available","order":3,"description":"Modern C++ from fundamentals through templates, RAII, the STL, and C++20/23 features."},
    {"name":"C#","slug":"csharp","status":"available","order":4,"description":"Expressive and powerful. Explore LINQ, async/await, generics, records, and the .NET libraries."}
  ];

  window.POLYGLOT_LANGUAGES.sort(function (a, b) {
    return Number(a.order || 0) - Number(b.order || 0);
  });

  window.POLYGLOT_LANG_MAP = Object.fromEntries(
    window.POLYGLOT_LANGUAGES.map(function (lang) {
      return [lang.slug, lang];
    })
  );

  window.POLYGLOT = window.POLYGLOT || {};
  window.POLYGLOT.languages = window.POLYGLOT_LANGUAGES;
})();
