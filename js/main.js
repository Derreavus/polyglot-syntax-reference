(function () {
  // --- Theme toggle ---
  const root = document.documentElement;
  const btn = document.getElementById("theme-toggle");
  const stored = localStorage.getItem("theme");

  if (stored === "light") {
    root.setAttribute("data-theme", "light");
    if (btn) btn.textContent = "☀";
  }

  if (btn) {
    btn.addEventListener("click", () => {
      const isLight = root.getAttribute("data-theme") === "light";
      if (isLight) {
        root.removeAttribute("data-theme");
        localStorage.setItem("theme", "dark");
        btn.textContent = "☾";
      } else {
        root.setAttribute("data-theme", "light");
        localStorage.setItem("theme", "light");
        btn.textContent = "☀";
      }
    });
  }

  // --- Inject search box if missing ---
  if (!document.getElementById("site-search")) {
    const headerInner = document.querySelector(".header-inner");
    const themeBtn = document.getElementById("theme-toggle");
    if (headerInner && themeBtn) {
      const wrap = document.createElement("div");
      wrap.className = "search-wrap";
      wrap.innerHTML = '<input type="search" id="site-search" placeholder="Search topics…" autocomplete="off" aria-label="Search topics"><div id="search-results" hidden></div>';
      headerInner.insertBefore(wrap, themeBtn);
    }
  }

  // --- Detect current language from path ---
  const path = location.pathname;
  let currentLang = null;
  if (path.includes("/python")) currentLang = "python";
  else if (path.includes("/rust")) currentLang = "rust";
  else if (path.includes("/cpp")) currentLang = "cpp";
  else if (path.includes("/csharp")) currentLang = "csharp";

  // --- Cross-language concept map ---
  const CONCEPTS = {
    types: {
      label: "Data Types",
      python: { id: "types", path: "../python/index.html" },
      rust:   { id: "types", path: "../rust/index.html" },
      cpp:    { id: "types", path: "../cpp/index.html" },
      csharp: { id: "types", path: "../csharp/index.html" },
    },
    variables: {
      label: "Variables",
      python: { id: "variables", path: "../python/index.html" },
      rust:   { id: "variables", path: "../rust/index.html" },
      cpp:    { id: "variables", path: "../cpp/index.html" },
      csharp: { id: "variables", path: "../csharp/index.html" },
    },
    operators: {
      label: "Operators",
      python: { id: "operators", path: "../python/index.html" },
      cpp:    { id: "operators", path: "../cpp/index.html" },
      csharp: { id: "operators", path: "../csharp/index.html" },
    },
    control: {
      label: "Control Flow",
      python: { id: "control", path: "../python/index.html" },
      rust:   { id: "control", path: "../rust/index.html" },
      cpp:    { id: "control", path: "../cpp/index.html" },
      csharp: { id: "control", path: "../csharp/index.html" },
    },
    functions: {
      label: "Functions / Methods",
      python: { id: "functions", path: "../python/index.html" },
      rust:   { id: "functions", path: "../rust/index.html" },
      cpp:    { id: "functions", path: "../cpp/index.html" },
      csharp: { id: "methods", path: "../csharp/index.html" },
    },
    methods: {
      label: "Functions / Methods",
      python: { id: "functions", path: "../python/index.html" },
      rust:   { id: "functions", path: "../rust/index.html" },
      cpp:    { id: "functions", path: "../cpp/index.html" },
      csharp: { id: "methods", path: "../csharp/index.html" },
    },
    classes: {
      label: "Classes / Structs",
      python: { id: "classes", path: "../python/index.html" },
      rust:   { id: "structs", path: "../rust/index.html" },
      cpp:    { id: "classes", path: "../cpp/index.html" },
      csharp: { id: "classes", path: "../csharp/index.html" },
    },
    structs: {
      label: "Classes / Structs",
      python: { id: "classes", path: "../python/index.html" },
      rust:   { id: "structs", path: "../rust/index.html" },
      cpp:    { id: "classes", path: "../cpp/index.html" },
      csharp: { id: "classes", path: "../csharp/index.html" },
    },
    inheritance: {
      label: "Inheritance",
      cpp:    { id: "inheritance", path: "../cpp/index.html" },
      csharp: { id: "inheritance", path: "../csharp/index.html" },
    },
    templates: {
      label: "Generics / Templates",
      python: { id: "typing", path: "../python/index.html" },
      rust:   { id: "traits", path: "../rust/index.html" },
      cpp:    { id: "templates", path: "../cpp/index.html" },
      csharp: { id: "generics", path: "../csharp/index.html" },
    },
    traits: {
      label: "Generics / Templates / Traits",
      python: { id: "typing", path: "../python/index.html" },
      rust:   { id: "traits", path: "../rust/index.html" },
      cpp:    { id: "templates", path: "../cpp/index.html" },
      csharp: { id: "generics", path: "../csharp/index.html" },
    },
    typing: {
      label: "Type Hints / Generics",
      python: { id: "typing", path: "../python/index.html" },
      rust:   { id: "traits", path: "../rust/index.html" },
      cpp:    { id: "templates", path: "../cpp/index.html" },
      csharp: { id: "generics", path: "../csharp/index.html" },
    },
    generics: {
      label: "Generics / Templates",
      python: { id: "typing", path: "../python/index.html" },
      rust:   { id: "traits", path: "../rust/index.html" },
      cpp:    { id: "templates", path: "../cpp/index.html" },
      csharp: { id: "generics", path: "../csharp/index.html" },
    },
    collections: {
      label: "Collections / Containers",
      python: { id: "collections", path: "../python/index.html" },
      rust:   { id: "collections", path: "../rust/index.html" },
      cpp:    { id: "containers", path: "../cpp/index.html" },
      csharp: { id: "collections", path: "../csharp/index.html" },
    },
    containers: {
      label: "Collections / Containers",
      python: { id: "collections", path: "../python/index.html" },
      rust:   { id: "collections", path: "../rust/index.html" },
      cpp:    { id: "containers", path: "../cpp/index.html" },
      csharp: { id: "collections", path: "../csharp/index.html" },
    },
    iterators: {
      label: "Iterators / Algorithms",
      python: { id: "iterators", path: "../python/index.html" },
      rust:   { id: "iterators", path: "../rust/index.html" },
      cpp:    { id: "algorithms", path: "../cpp/index.html" },
    },
    algorithms: {
      label: "Iterators / Algorithms",
      python: { id: "iterators", path: "../python/index.html" },
      rust:   { id: "iterators", path: "../rust/index.html" },
      cpp:    { id: "algorithms", path: "../cpp/index.html" },
    },
    exceptions: {
      label: "Error Handling",
      python: { id: "exceptions", path: "../python/index.html" },
      rust:   { id: "error", path: "../rust/index.html" },
      cpp:    { id: "exceptions", path: "../cpp/index.html" },
      csharp: { id: "exceptions", path: "../csharp/index.html" },
    },
    error: {
      label: "Error Handling",
      python: { id: "exceptions", path: "../python/index.html" },
      rust:   { id: "error", path: "../rust/index.html" },
      cpp:    { id: "exceptions", path: "../cpp/index.html" },
      csharp: { id: "exceptions", path: "../csharp/index.html" },
    },
    concurrency: {
      label: "Concurrency / Async",
      python: { id: "async", path: "../python/index.html" },
      rust:   { id: "concurrency", path: "../rust/index.html" },
      cpp:    { id: "concurrency", path: "../cpp/index.html" },
      csharp: { id: "async", path: "../csharp/index.html" },
    },
    async: {
      label: "Concurrency / Async",
      python: { id: "async", path: "../python/index.html" },
      rust:   { id: "concurrency", path: "../rust/index.html" },
      cpp:    { id: "concurrency", path: "../cpp/index.html" },
      csharp: { id: "async", path: "../csharp/index.html" },
    },
    ownership: {
      label: "Memory / Ownership",
      rust:   { id: "ownership", path: "../rust/index.html" },
      cpp:    { id: "pointers", path: "../cpp/index.html" },
      csharp: { id: "memory", path: "../csharp/index.html" },
    },
    pointers: {
      label: "Memory / Ownership",
      rust:   { id: "ownership", path: "../rust/index.html" },
      cpp:    { id: "pointers", path: "../cpp/index.html" },
      csharp: { id: "memory", path: "../csharp/index.html" },
    },
    memory: {
      label: "Memory / Ownership",
      rust:   { id: "ownership", path: "../rust/index.html" },
      cpp:    { id: "pointers", path: "../cpp/index.html" },
      csharp: { id: "memory", path: "../csharp/index.html" },
    },
    pattern: {
      label: "Pattern Matching",
      python: { id: "control", path: "../python/index.html" },
      rust:   { id: "pattern", path: "../rust/index.html" },
      csharp: { id: "pattern", path: "../csharp/index.html" },
    },
    records: {
      label: "Records / Data Classes",
      python: { id: "dataclasses", path: "../python/index.html" },
      csharp: { id: "records", path: "../csharp/index.html" },
    },
    dataclasses: {
      label: "Records / Data Classes",
      python: { id: "dataclasses", path: "../python/index.html" },
      csharp: { id: "records", path: "../csharp/index.html" },
    },
  };

  const LANG_LABELS = { python: "Python", rust: "Rust", cpp: "C++", csharp: "C#" };

  // Inject "Also in" links under each matching section heading
  if (currentLang) {
    document.querySelectorAll("section.topic").forEach((section) => {
      const id = section.id;
      const concept = CONCEPTS[id];
      if (!concept) return;

      const others = Object.entries(concept)
        .filter(([lang]) => lang !== "label" && lang !== currentLang)
        .map(([lang, info]) => {
          const href = info.path + "#" + info.id;
          return `<a href="${href}" class="xlang-link ${lang}">${LANG_LABELS[lang]}</a>`;
        });

      if (others.length === 0) return;

      const h2 = section.querySelector("h2");
      if (!h2) return;

      const bar = document.createElement("div");
      bar.className = "xlang-bar";
      bar.innerHTML = `<span class="xlang-label">Also in</span> ${others.join("")}`;
      h2.insertAdjacentElement("afterend", bar);
    });
  }

  // --- Sidebar scroll spy ---
  const sections = document.querySelectorAll("section.topic");
  const links = document.querySelectorAll(".sidebar a");

  if (sections.length && links.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.id;
            links.forEach((a) => {
              a.classList.toggle("active", a.getAttribute("href") === "#" + id);
            });
          }
        });
      },
      { rootMargin: "-20% 0px -60% 0px" }
    );
    sections.forEach((s) => observer.observe(s));
  }

  // --- Search ---
  const searchInput = document.getElementById("site-search");
  const searchResults = document.getElementById("search-results");

  if (searchInput && searchResults) {
    const index = [];
    document.querySelectorAll("section.topic").forEach((sec) => {
      const title = (sec.querySelector("h2") || {}).textContent || "";
      const text = sec.textContent || "";
      index.push({ id: sec.id, title: title.trim(), text: text.toLowerCase(), el: sec });
    });

    function showResults(query) {
      searchResults.innerHTML = "";
      if (!query || query.length < 1) {
        searchResults.hidden = true;
        index.forEach((item) => { item.el.style.display = ""; });
        document.querySelectorAll(".xlang-bar").forEach((b) => { b.style.display = ""; });
        return;
      }

      const q = query.toLowerCase();
      const matches = index.filter(
        (item) => item.title.toLowerCase().includes(q) || item.text.includes(q)
      );

      index.forEach((item) => {
        const show = matches.includes(item);
        item.el.style.display = show ? "" : "none";
        const bar = item.el.querySelector(".xlang-bar");
        if (bar) bar.style.display = show ? "" : "none";
      });

      if (matches.length === 0) {
        searchResults.innerHTML = `<div class="search-empty">No matches for “${query}”</div>`;
        searchResults.hidden = false;
        return;
      }

      matches.slice(0, 12).forEach((item) => {
        const a = document.createElement("a");
        a.href = "#" + item.id;
        a.className = "search-hit";
        a.textContent = item.title;
        a.addEventListener("click", () => {
          searchResults.hidden = true;
          searchInput.value = "";
          setTimeout(() => {
            index.forEach((i) => { i.el.style.display = ""; });
            document.querySelectorAll(".xlang-bar").forEach((b) => { b.style.display = ""; });
          }, 100);
        });
        searchResults.appendChild(a);
      });
      searchResults.hidden = false;
    }

    let debounce;
    searchInput.addEventListener("input", () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => showResults(searchInput.value.trim()), 120);
    });

    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        searchInput.value = "";
        showResults("");
        searchInput.blur();
      }
    });

    document.addEventListener("click", (e) => {
      if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.hidden = true;
      }
    });
  }
})();
