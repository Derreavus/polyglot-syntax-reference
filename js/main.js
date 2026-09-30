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
  const registry = Array.isArray(window.POLYGLOT_LANGUAGES) ? window.POLYGLOT_LANGUAGES.slice() : [];

  function getPageInfo() {
    const pageSegments = path.split("/").filter(Boolean);
    const lastSegment = pageSegments[pageSegments.length - 1] || "";
    const isIndexPage = lastSegment === "index.html" || pageSegments.length === 0;
    const parentSegment = isIndexPage && pageSegments.length > 1 ? pageSegments[pageSegments.length - 2] : null;
    const currentPageSegment = isIndexPage ? parentSegment : lastSegment;
    const isNestedPage = Boolean(parentSegment) && (parentSegment === "compare" || registry.some(function (lang) { return lang.slug === parentSegment; }));
    return {
      pageSegments: pageSegments,
      isIndexPage: isIndexPage,
      isNestedPage: isNestedPage,
      currentPageSegment: currentPageSegment,
    };
  }

  function getCurrentLang() {
    const pageInfo = getPageInfo();
    if (!pageInfo.currentPageSegment) return null;
    return registry.some(function (lang) { return lang.slug === pageInfo.currentPageSegment; }) ? pageInfo.currentPageSegment : null;
  }

  let currentLang = getCurrentLang();
  const basePrefix = getPageInfo().isNestedPage ? "../" : "";

  function buildLangMeta() {
    const meta = {};
    registry.forEach(function (lang) {
      meta[lang.slug] = {
        label: lang.name,
        path: lang.slug + "/index.html",
      };
    });
    return meta;
  }

  const LANG_META = buildLangMeta();

  const CONCEPTS = window.POLYGLOT_CONCEPTS || {};

  if (currentLang) {
    document.querySelectorAll("section.topic[id]").forEach((section) => {
      const concept = Object.values(CONCEPTS).find((topics) => topics[currentLang] === section.id);
      if (!concept) return;
      const others = Object.keys(LANG_META).filter((l) => l !== currentLang && concept[l]);
      if (!others.length) return;
      const bar = document.createElement("div");
      bar.className = "xlang-bar";
      bar.innerHTML =
        '<span class="xlang-label">Also in</span> ' +
        others
          .map((l) => {
            const href = "../" + LANG_META[l].path + "#" + concept[l];
            return '<a class="xlang-link ' + l + '" href="' + href + '">' + LANG_META[l].label + "</a>";
          })
          .join(" ");
      const h2 = section.querySelector("h2");
      if (h2) h2.insertAdjacentElement("afterend", bar);
      else section.appendChild(bar);
    });
  }

  const SEARCH_INDEX = window.POLYGLOT_SEARCH_INDEX || [];

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "\u0026amp;")
      .replace(/</g, "\u0026lt;")
      .replace(/>/g, "\u0026gt;")
      .replace(/"/g, "\u0026quot;");
  }

  function navPathFor(slug) {
    const isNestedPage = getPageInfo().isNestedPage;
    return (isNestedPage ? "../" : "") + slug + "/index.html";
  }

  function renderLanguageNavigation() {
    const navs = document.querySelectorAll(".lang-nav");
    if (!navs.length) return;

    navs.forEach(function (nav) {
      const languageMenu = nav.querySelector(".language-menu");
      const menuPanel = languageMenu && languageMenu.querySelector(".language-menu-panel");
      if (!languageMenu || !menuPanel) return;

      registry.forEach(function (lang) {
        const link = document.createElement("a");
        link.href = navPathFor(lang.slug);
        link.className = "language-option hero-card " + lang.slug;
        link.textContent = lang.name;
        if (currentLang === lang.slug) link.setAttribute("aria-current", "page");

        link.addEventListener("click", function () {
          languageMenu.open = false;
        });
        menuPanel.appendChild(link);
      });
    });

    document.addEventListener("click", function (event) {
      if (event.target instanceof Element && !event.target.closest(".language-menu")) {
        document.querySelectorAll(".language-menu[open]").forEach(function (menu) {
          menu.open = false;
        });
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      document.querySelectorAll(".language-menu[open]").forEach(function (menu) {
        menu.open = false;
        const summary = menu.querySelector("summary");
        if (summary) summary.focus();
      });
    });
  }

  function renderHomepageCards() {
    const homepageCards = document.querySelector(".hero-cards");
    if (!homepageCards) return;

    const isNestedPage = getPageInfo().isNestedPage;

    homepageCards.innerHTML = "";
    registry.forEach(function (lang) {
      const card = document.createElement("a");
      card.href = (isNestedPage ? "../" : "") + lang.slug + "/index.html";
      card.className = "hero-card " + lang.slug;
      card.innerHTML = "<h2>" + escapeHtml(lang.name) + "</h2><p>" + escapeHtml(lang.description || "") + "</p>";
      homepageCards.appendChild(card);
    });

    const compareCard = document.createElement("a");
    compareCard.href = (isNestedPage ? "../" : "") + "compare/index.html";
    compareCard.className = "hero-card";
    compareCard.style.borderColor = "var(--accent)";
    compareCard.innerHTML = '<h2 style="color:var(--accent);">Compare</h2><p>Same concept, different language — compare syntax and approaches across languages.</p>';
    homepageCards.appendChild(compareCard);
  }

  function renderCompareLanguagePicker() {
    const options = document.getElementById("compare-language-options");
    const count = document.getElementById("compare-language-count");
    const emptyState = document.getElementById("compare-empty-state");
    if (!options || !count || !emptyState) return;

    const maxLanguages = 4;
    registry.forEach(function (lang) {
      const label = document.createElement("label");
      label.className = "compare-language-option";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = lang.slug;
      checkbox.addEventListener("change", updateSelection);

      const name = document.createElement("span");
      name.textContent = lang.name;
      label.appendChild(checkbox);
      label.appendChild(name);
      options.appendChild(label);
    });

    function updateSelection() {
      const checkboxes = Array.from(options.querySelectorAll('input[type="checkbox"]'));
      const selected = new Set(
        checkboxes.filter(function (checkbox) { return checkbox.checked; })
          .map(function (checkbox) { return checkbox.value; })
      );

      count.textContent = selected.size + " of " + maxLanguages + " selected";
      emptyState.hidden = selected.size > 0;
      document.querySelectorAll(".compare-table").forEach(function (table) {
        table.hidden = selected.size === 0;
      });
      options.querySelectorAll(".compare-language-option").forEach(function (label) {
        const checkbox = label.querySelector('input[type="checkbox"]');
        if (!checkbox) return;
        label.classList.toggle("selected", checkbox.checked);
        checkbox.disabled = selected.size >= maxLanguages && !checkbox.checked;
        label.classList.toggle("disabled", checkbox.disabled);
      });

      document.querySelectorAll(".compare-table [data-language]").forEach(function (cell) {
        cell.hidden = !selected.has(cell.getAttribute("data-language"));
      });
    }

    updateSelection();
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

  renderLanguageNavigation();
  renderHomepageCards();
  renderCompareLanguagePicker();
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
