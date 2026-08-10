(function () {
  "use strict";

  const root = document.documentElement;
  const themeBtn = document.getElementById("theme-toggle");
  const storedTheme = localStorage.getItem("theme");

  if (storedTheme === "light") {
    root.setAttribute("data-theme", "light");
    if (themeBtn) themeBtn.textContent = "\u2600";
  }

  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const isLight = root.getAttribute("data-theme") === "light";
      if (isLight) {
        root.removeAttribute("data-theme");
        localStorage.setItem("theme", "dark");
        themeBtn.textContent = "\u263E";
      } else {
        root.setAttribute("data-theme", "light");
        localStorage.setItem("theme", "light");
        themeBtn.textContent = "\u2600";
      }
    });
  }

  const path = location.pathname;
  let currentLang = null;
  if (path.includes("/python")) currentLang = "python";
  else if (path.includes("/rust")) currentLang = "rust";
  else if (path.includes("/cpp")) currentLang = "cpp";
  else if (path.includes("/csharp")) currentLang = "csharp";

  const LANG_META = {
    python: { label: "Python", path: "python/index.html" },
    rust: { label: "Rust", path: "rust/index.html" },
    cpp: { label: "C++", path: "cpp/index.html" },
    csharp: { label: "C#", path: "csharp/index.html" },
  };
  const basePrefix = currentLang ? "../" : "";

  const CONCEPTS = {
    types: { python: { id: "types" }, rust: { id: "types" }, cpp: { id: "types" }, csharp: { id: "types" } },
    variables: { python: { id: "variables" }, rust: { id: "variables" }, cpp: { id: "variables" }, csharp: { id: "variables" } },
    operators: { python: { id: "operators" }, cpp: { id: "operators" }, csharp: { id: "operators" } },
    control: { python: { id: "control" }, rust: { id: "control" }, cpp: { id: "control" }, csharp: { id: "control" } },
    functions: { python: { id: "functions" }, rust: { id: "functions" }, cpp: { id: "functions" }, csharp: { id: "methods" } },
    classes: { python: { id: "classes" }, rust: { id: "structs" }, cpp: { id: "classes" }, csharp: { id: "classes" } },
    collections: { python: { id: "collections" }, rust: { id: "collections" }, cpp: { id: "containers" }, csharp: { id: "collections" } },
    exceptions: { python: { id: "exceptions" }, rust: { id: "error" }, cpp: { id: "exceptions" }, csharp: { id: "exceptions" } },
    async: { python: { id: "async" }, cpp: { id: "concurrency" }, csharp: { id: "async" } },
    iterators: { python: { id: "iterators" }, rust: { id: "iterators" }, cpp: { id: "algorithms" }, csharp: { id: "linq" } },
    generics: { python: { id: "typing" }, rust: { id: "traits" }, cpp: { id: "templates" }, csharp: { id: "generics" } },
    pattern: { python: { id: "control" }, rust: { id: "pattern" }, csharp: { id: "pattern" } },
  };

  if (currentLang) {
    document.querySelectorAll("section.topic[id]").forEach((section) => {
      const concept = CONCEPTS[section.id];
      if (!concept) return;
      const others = Object.keys(LANG_META).filter((l) => l !== currentLang && concept[l]);
      if (!others.length) return;
      const bar = document.createElement("div");
      bar.className = "xlang-bar";
      bar.innerHTML =
        '<span class="xlang-label">Also in</span> ' +
        others
          .map((l) => {
            const href = "../" + LANG_META[l].path + "#" + concept[l].id;
            return '<a class="xlang-link ' + l + '" href="' + href + '">' + LANG_META[l].label + "</a>";
          })
          .join(" ");
      const h2 = section.querySelector("h2");
      if (h2) h2.insertAdjacentElement("afterend", bar);
      else section.appendChild(bar);
    });
  }

  const SEARCH_INDEX = [
    { lang: "python", id: "types", title: "Data Types", keywords: "int float str bool list dict tuple set none" },
    { lang: "python", id: "variables", title: "Variables & Assignment", keywords: "unpack walrus swap binding" },
    { lang: "python", id: "operators", title: "Operators", keywords: "arithmetic comparison is in and or" },
    { lang: "python", id: "control", title: "Control Flow", keywords: "if elif else match case for while break" },
    { lang: "python", id: "functions", title: "Functions", keywords: "def lambda decorator args kwargs closure" },
    { lang: "python", id: "classes", title: "Classes & OOP", keywords: "class inheritance mro abc abstract" },
    { lang: "python", id: "dataclasses", title: "Dataclasses & Named Tuples", keywords: "dataclass frozen slots field namedtuple enum" },
    { lang: "python", id: "typing", title: "Type Hints", keywords: "typing TypeVar Generic Protocol Optional Union overload" },
    { lang: "python", id: "collections", title: "Collections", keywords: "list dict set deque Counter defaultdict" },
    { lang: "python", id: "comprehensions", title: "Comprehensions", keywords: "list dict set generator expression" },
    { lang: "python", id: "iterators", title: "Iterators & Generators", keywords: "yield iter next itertools functools" },
    { lang: "python", id: "exceptions", title: "Exceptions", keywords: "try except finally raise ExceptionGroup" },
    { lang: "python", id: "context", title: "Context Managers", keywords: "with enter exit contextmanager" },
    { lang: "python", id: "async", title: "Async / Await", keywords: "asyncio await gather TaskGroup coroutine" },
    { lang: "python", id: "stdlib", title: "Standard Library", keywords: "pathlib json re datetime sys os" },
    { lang: "python", id: "packaging", title: "Packaging & Tooling", keywords: "pip uv venv pyproject ruff mypy pytest" },
    { lang: "rust", id: "getting-started", title: "Getting Started", keywords: "cargo new build run rustc" },
    { lang: "rust", id: "types", title: "Data Types", keywords: "i32 u64 f64 bool char tuple array slice" },
    { lang: "rust", id: "variables", title: "Variables & Assignment", keywords: "let mut const static shadowing" },
    { lang: "rust", id: "strings", title: "Strings", keywords: "String str to_string format" },
    { lang: "rust", id: "control", title: "Control Flow", keywords: "if else loop while for break continue" },
    { lang: "rust", id: "functions", title: "Functions & Closures", keywords: "fn closure move Fn FnMut FnOnce" },
    { lang: "rust", id: "ownership", title: "Ownership & Borrowing", keywords: "move borrow reference mut clone drop" },
    { lang: "rust", id: "lifetimes", title: "Lifetimes", keywords: "lifetime static annotation" },
    { lang: "rust", id: "structs", title: "Structs & Enums", keywords: "struct enum impl Option Result" },
    { lang: "rust", id: "traits", title: "Traits & Generics", keywords: "trait impl where bound dyn derive" },
    { lang: "rust", id: "pattern", title: "Pattern Matching", keywords: "match if let while let destructure" },
    { lang: "rust", id: "collections", title: "Collections", keywords: "Vec HashMap HashSet BTreeMap VecDeque" },
    { lang: "rust", id: "iterators", title: "Iterators", keywords: "iter map filter collect fold zip" },
    { lang: "rust", id: "error", title: "Error Handling", keywords: "Result Option unwrap expect anyhow" },
    { lang: "rust", id: "modules", title: "Modules & Cargo", keywords: "mod pub use cargo.toml crate" },
    { lang: "rust", id: "io", title: "File I/O", keywords: "fs File read write BufReader" },
    { lang: "cpp", id: "types", title: "Data Types", keywords: "int bool char float auto decltype constexpr" },
    { lang: "cpp", id: "variables", title: "Variables & Literals", keywords: "initialization brace nullptr reference" },
    { lang: "cpp", id: "operators", title: "Operators", keywords: "cast sizeof new delete spaceship" },
    { lang: "cpp", id: "control", title: "Control Flow", keywords: "if switch for while range structured binding" },
    { lang: "cpp", id: "functions", title: "Functions", keywords: "overload default noexcept constexpr consteval" },
    { lang: "cpp", id: "pointers", title: "Pointers & Smart Pointers", keywords: "unique_ptr shared_ptr weak_ptr make_unique" },
    { lang: "cpp", id: "raii", title: "RAII & Special Members", keywords: "rule of zero five destructor move copy" },
    { lang: "cpp", id: "classes", title: "Structs & Classes", keywords: "class struct constructor initializer" },
    { lang: "cpp", id: "inheritance", title: "Inheritance & Polymorphism", keywords: "virtual override abstract dynamic_cast" },
    { lang: "cpp", id: "templates", title: "Templates", keywords: "template typename concept requires SFINAE" },
    { lang: "cpp", id: "lambdas", title: "Lambda Expressions", keywords: "capture mutable generic lambda" },
    { lang: "cpp", id: "modern", title: "Modern C++", keywords: "optional variant span ranges expected format" },
    { lang: "cpp", id: "containers", title: "STL Containers", keywords: "vector map unordered_map array deque set" },
    { lang: "cpp", id: "algorithms", title: "Iterators & Algorithms", keywords: "sort find transform ranges views" },
    { lang: "cpp", id: "complexity", title: "Complexity Tables", keywords: "big-O access insert erase amortized" },
    { lang: "cpp", id: "exceptions", title: "Exception Handling", keywords: "try catch throw noexcept exception" },
    { lang: "cpp", id: "concurrency", title: "Concurrency", keywords: "thread mutex lock_guard atomic async future jthread" },
    { lang: "cpp", id: "headers", title: "Key Headers", keywords: "iostream vector memory algorithm string" },
    { lang: "csharp", id: "types", title: "Data Types", keywords: "int string bool decimal nullable nint" },
    { lang: "csharp", id: "variables", title: "Variables & Literals", keywords: "var const readonly string interpolation" },
    { lang: "csharp", id: "operators", title: "Operators", keywords: "null-coalescing ranges indices" },
    { lang: "csharp", id: "control", title: "Control Flow", keywords: "if switch foreach using" },
    { lang: "csharp", id: "methods", title: "Methods", keywords: "ref out in params extension local function" },
    { lang: "csharp", id: "classes", title: "Classes & Structs", keywords: "class struct primary constructor" },
    { lang: "csharp", id: "records", title: "Records", keywords: "record with expression init immutable" },
    { lang: "csharp", id: "inheritance", title: "Inheritance & Interfaces", keywords: "interface abstract override virtual" },
    { lang: "csharp", id: "properties", title: "Properties, Indexers & Events", keywords: "get set init required event" },
    { lang: "csharp", id: "linq", title: "LINQ", keywords: "Where Select OrderBy GroupBy deferred ToList" },
    { lang: "csharp", id: "async", title: "Async / Await", keywords: "Task ValueTask await WhenAll CancellationToken" },
    { lang: "csharp", id: "pattern", title: "Pattern Matching", keywords: "is switch property list relational patterns" },
    { lang: "csharp", id: "generics", title: "Generics", keywords: "where constraints covariance INumber" },
    { lang: "csharp", id: "collections", title: "Collections", keywords: "List Dictionary HashSet Span collection expression" },
    { lang: "csharp", id: "exceptions", title: "Exceptions", keywords: "try catch finally when throw" },
    { lang: "csharp", id: "memory", title: "Spans & Memory", keywords: "Span Memory ArrayPool stackalloc" },
    { lang: "csharp", id: "dotnet", title: ".NET Highlights", keywords: "DI ASP.NET HttpClient JsonSerializer" },
  ];

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "\u0026amp;")
      .replace(/</g, "\u0026lt;")
      .replace(/>/g, "\u0026gt;")
      .replace(/"/g, "\u0026quot;");
  }

  function ensurePalette() {
    if (document.getElementById("cmd-palette")) return;
    const overlay = document.createElement("div");
    overlay.id = "cmd-overlay";
    overlay.hidden = true;
    overlay.innerHTML =
      '<div id="cmd-palette" role="dialog" aria-label="Search Polyglot" aria-modal="true">' +
      '<div class="cmd-header">' +
      '<input type="search" id="cmd-input" placeholder="Search all languages\u2026" autocomplete="off" aria-label="Search" />' +
      '<kbd class="cmd-hint">esc</kbd></div>' +
      '<div id="cmd-results" role="listbox"></div>' +
      '<div class="cmd-footer">' +
      "<span><kbd>\u2191</kbd><kbd>\u2193</kbd> navigate</span>" +
      "<span><kbd>\u21B5</kbd> open</span>" +
      "<span><kbd>esc</kbd> close</span></div></div>";
    document.body.appendChild(overlay);

    const input = document.getElementById("cmd-input");
    const results = document.getElementById("cmd-results");
    let activeIndex = 0;
    let currentHits = [];

    function score(item, q) {
      const title = item.title.toLowerCase();
      const kw = item.keywords.toLowerCase();
      if (title === q) return 100;
      if (title.startsWith(q)) return 80;
      if (title.includes(q)) return 60;
      if (kw.includes(q)) return 40;
      if (item.lang.includes(q)) return 20;
      const tokens = q.split(/\s+/).filter(Boolean);
      if (tokens.length && tokens.every((t) => title.includes(t) || kw.includes(t) || item.lang.includes(t))) return 30;
      return 0;
    }

    function itemHref(item) {
      if (item.lang === currentLang) return "#" + item.id;
      return basePrefix + LANG_META[item.lang].path + "#" + item.id;
    }

    function render(q) {
      results.innerHTML = "";
      activeIndex = 0;
      if (!q) {
        currentHits = SEARCH_INDEX.filter((i) => !currentLang || i.lang === currentLang).slice(0, 8);
      } else {
        currentHits = SEARCH_INDEX.map((item) => ({ item: item, s: score(item, q) }))
          .filter((x) => x.s > 0)
          .sort((a, b) => b.s - a.s || a.item.title.localeCompare(b.item.title))
          .slice(0, 12)
          .map((x) => x.item);
      }
      if (!currentHits.length) {
        results.innerHTML = '<div class="cmd-empty">No matches</div>';
        return;
      }
      currentHits.forEach((item, idx) => {
        const a = document.createElement("a");
        a.href = itemHref(item);
        a.className = "cmd-hit" + (idx === 0 ? " active" : "");
        a.setAttribute("role", "option");
        a.innerHTML =
          '<span class="cmd-hit-lang ' + item.lang + '">' + LANG_META[item.lang].label + "</span>" +
          '<span class="cmd-hit-title">' + escapeHtml(item.title) + "</span>" +
          (item.lang === currentLang ? '<span class="cmd-hit-here">this page</span>' : "");
        a.addEventListener("mouseenter", function () { setActive(idx); });
        a.addEventListener("click", function () { closePalette(); });
        results.appendChild(a);
      });
    }

    function setActive(idx) {
      activeIndex = idx;
      results.querySelectorAll(".cmd-hit").forEach(function (el, i) {
        el.classList.toggle("active", i === idx);
      });
      const active = results.querySelector(".cmd-hit.active");
      if (active) active.scrollIntoView({ block: "nearest" });
    }

    function openPalette() {
      overlay.hidden = false;
      document.body.classList.add("palette-open");
      input.value = "";
      render("");
      requestAnimationFrame(function () { input.focus(); });
    }

    function closePalette() {
      overlay.hidden = true;
      document.body.classList.remove("palette-open");
    }

    function goActive() {
      const hit = currentHits[activeIndex];
      if (!hit) return;
      closePalette();
      location.href = itemHref(hit);
    }

    input.addEventListener("input", function () { render(input.value.trim().toLowerCase()); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); setActive(Math.min(activeIndex + 1, currentHits.length - 1)); }
      else if (e.key === "ArrowUp") { e.preventDefault(); setActive(Math.max(activeIndex - 1, 0)); }
      else if (e.key === "Enter") { e.preventDefault(); goActive(); }
      else if (e.key === "Escape") { e.preventDefault(); closePalette(); }
    });
    overlay.addEventListener("click", function (e) { if (e.target === overlay) closePalette(); });

    document.addEventListener("keydown", function (e) {
      const isK = e.key === "k" || e.key === "K" || e.code === "KeyK";
      const mod = e.metaKey || e.ctrlKey;
      if (mod && isK) {
        e.preventDefault();
        e.stopPropagation();
        if (typeof e.stopImmediatePropagation === "function") e.stopImmediatePropagation();
        if (overlay.hidden) openPalette();
        else closePalette();
        return;
      }
      if (mod && e.shiftKey && (e.key === "p" || e.key === "P" || e.code === "KeyP")) {
        e.preventDefault();
        e.stopPropagation();
        if (overlay.hidden) openPalette();
        else closePalette();
        return;
      }
      if (e.key === "/" && !mod && !e.altKey) {
        const tag = (e.target && e.target.tagName) || "";
        if (tag !== "INPUT" && tag !== "TEXTAREA" && !(e.target && e.target.isContentEditable)) {
          e.preventDefault();
          openPalette();
        }
      }
    }, true);

    injectSearchTrigger(openPalette);
  }

  function injectSearchTrigger(openFn) {
    const headerInner = document.querySelector(".header-inner");
    if (!headerInner || document.getElementById("search-trigger")) return;
    const btn = document.createElement("button");
    btn.id = "search-trigger";
    btn.className = "search-trigger";
    btn.type = "button";
    btn.setAttribute("aria-label", "Search");
    btn.innerHTML = '<span class="search-trigger-label">Search</span> <kbd>/</kbd>';
    btn.addEventListener("click", openFn);
    const theme = document.getElementById("theme-toggle");
    if (theme) headerInner.insertBefore(btn, theme); else headerInner.appendChild(btn);
    const old = document.querySelector(".search-wrap");
    if (old) old.remove();
  }

  ensurePalette();

  function addCopyButtons() {
    document.querySelectorAll("pre").forEach(function (pre) {
      if (pre.querySelector(".copy-btn")) return;
      const code = pre.querySelector("code");
      if (!code) return;
      pre.classList.add("code-block");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "copy-btn";
      btn.textContent = "Copy";
      btn.setAttribute("aria-label", "Copy code");
      btn.addEventListener("click", function () {
        const text = code.innerText.replace(/\n$/, "");
        function ok() {
          btn.textContent = "Copied!";
          btn.classList.add("copied");
          setTimeout(function () { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 1500);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(ok).catch(function () { fallbackCopy(text, ok); });
        } else {
          fallbackCopy(text, ok);
        }
      });
      pre.appendChild(btn);
    });
  }

  function fallbackCopy(text, ok) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); ok(); } catch (e) {}
    document.body.removeChild(ta);
  }

  addCopyButtons();

  function ensureBackToTop() {
    if (document.getElementById("back-to-top")) return;
    const btn = document.createElement("button");
    btn.id = "back-to-top";
    btn.type = "button";
    btn.setAttribute("aria-label", "Back to top");
    btn.innerHTML = "\u2191";
    btn.hidden = true;
    btn.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
    document.body.appendChild(btn);
    var ticking = false;
    window.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { btn.hidden = window.scrollY < 400; ticking = false; });
    });
  }

  ensureBackToTop();

  function addPrevNext() {
    if (!currentLang) return;
    const sections = Array.from(document.querySelectorAll("section.topic[id]"));
    if (sections.length < 2) return;
    sections.forEach(function (section, i) {
      const nav = document.createElement("nav");
      nav.className = "section-nav";
      nav.setAttribute("aria-label", "Section navigation");
      if (i > 0) {
        const prev = sections[i - 1];
        const a = document.createElement("a");
        a.href = "#" + prev.id;
        a.className = "section-nav-prev";
        const title = (prev.querySelector("h2") && prev.querySelector("h2").textContent) || prev.id;
        a.innerHTML = '<span class="section-nav-dir">\u2190 Previous</span><span class="section-nav-title">' + escapeHtml(title) + "</span>";
        nav.appendChild(a);
      } else {
        nav.appendChild(document.createElement("span"));
      }
      if (i < sections.length - 1) {
        const next = sections[i + 1];
        const a = document.createElement("a");
        a.href = "#" + next.id;
        a.className = "section-nav-next";
        const title = (next.querySelector("h2") && next.querySelector("h2").textContent) || next.id;
        a.innerHTML = '<span class="section-nav-dir">Next \u2192</span><span class="section-nav-title">' + escapeHtml(title) + "</span>";
        nav.appendChild(a);
      }
      section.appendChild(nav);
    });
  }

  addPrevNext();

  function addBreadcrumbs() {
    const article = document.querySelector("article.content");
    if (!article || !currentLang || article.querySelector(".breadcrumbs")) return;
    const h1 = article.querySelector("h1");
    if (!h1) return;
    const nav = document.createElement("nav");
    nav.className = "breadcrumbs";
    nav.setAttribute("aria-label", "Breadcrumb");
    nav.innerHTML =
      '<a href="../index.html">Polyglot</a><span class="bc-sep">/</span>' +
      '<span class="bc-current">' + LANG_META[currentLang].label + "</span>";
    article.insertBefore(nav, h1);
  }

  addBreadcrumbs();

  const sidebarLinks = document.querySelectorAll('.sidebar a[href^="#"]');
  if (sidebarLinks.length) {
    const map = new Map();
    sidebarLinks.forEach(function (a) {
      const id = a.getAttribute("href").slice(1);
      const el = document.getElementById(id);
      if (el) map.set(el, a);
    });
    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          const link = map.get(entry.target);
          if (!link) return;
          if (entry.isIntersecting) {
            sidebarLinks.forEach(function (l) { l.classList.remove("active"); });
            link.classList.add("active");
          }
        });
      },
      { rootMargin: "-20% 0px -70% 0px", threshold: 0 }
    );
    map.forEach(function (_link, el) { observer.observe(el); });
  }
})();
