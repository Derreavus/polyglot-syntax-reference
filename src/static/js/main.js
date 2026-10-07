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

  // Everything below resolves URLs from this script's own location, so links stay correct on
  // /<language>/, /<language>/index.html, nested pages, GitHub project sites, and file:// previews alike.
  const scriptEl = document.currentScript || document.querySelector('script[src$="js/main.js"]');
  const siteRoot = scriptEl && scriptEl.src ? new URL("../", scriptEl.src).href : "";
  const path = location.pathname;
  const registry = Array.isArray(window.POLYGLOT_LANGUAGES) ? window.POLYGLOT_LANGUAGES.slice() : [];

  // Marks a scrollable element with data-fade="start|end|both|none" so CSS can fade the edge
  // that has more content. Used instead of visible scrollbars on menus and lists.
  function bindScrollFade(el, axis) {
    if (!el || el.getAttribute("data-fade-bound")) return;
    el.setAttribute("data-fade-bound", "1");
    const horizontal = axis === "x";
    el.setAttribute("data-fade-axis", horizontal ? "x" : "y");
    function refresh() {
      const size = horizontal ? el.clientWidth : el.clientHeight;
      const total = horizontal ? el.scrollWidth : el.scrollHeight;
      const pos = Math.abs(horizontal ? el.scrollLeft : el.scrollTop);
      let state = "none";
      if (total > size + 1) {
        const atStart = pos <= 1;
        const atEnd = pos + size >= total - 1;
        state = atStart ? "end" : atEnd ? "start" : "both";
      }
      if (el.getAttribute("data-fade") !== state) el.setAttribute("data-fade", state);
    }
    el.addEventListener("scroll", refresh, { passive: true });
    window.addEventListener("resize", refresh);
    if (window.ResizeObserver) new ResizeObserver(refresh).observe(el);
    if (window.MutationObserver) new MutationObserver(refresh).observe(el, { childList: true, subtree: true });
    refresh();
  }

  function getPageInfo() {
    const rootPath = siteRoot ? new URL(siteRoot).pathname : "/";
    const relative = path.indexOf(rootPath) === 0 ? path.slice(rootPath.length) : path;
    const segments = relative.split("/").filter(function (part) { return part && part !== "index.html"; });
    const first = segments[0] || "";
    const isLanguage = registry.some(function (lang) { return lang.slug === first; });
    return {
      segments: segments,
      lang: isLanguage ? first : null,
      isCompare: first === "compare",
      isVersions: isLanguage && segments[1] === "versions",
    };
  }

  function getCurrentLang() {
    return getPageInfo().lang;
  }

  let currentLang = getCurrentLang();

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
    return siteRoot + slug + "/index.html";
  }

  function renderLanguageNavigation() {
    const navs = document.querySelectorAll(".lang-nav");
    if (!navs.length) return;

    navs.forEach(function (nav) {
      const languageMenu = nav.querySelector(".language-menu");
      const menuPanel = languageMenu && languageMenu.querySelector(".language-menu-panel");
      if (!languageMenu || !menuPanel) return;

      const menuList = document.createElement("div");
      menuList.className = "language-menu-list scroll-fade";
      menuPanel.appendChild(menuList);
      bindScrollFade(menuList, "y");

      registry.forEach(function (lang) {
        const link = document.createElement("a");
        link.href = navPathFor(lang.slug);
        link.className = "language-option hero-card " + lang.slug;
        link.textContent = lang.name;
        if (currentLang === lang.slug) link.setAttribute("aria-current", "page");

        link.addEventListener("click", function () {
          languageMenu.open = false;
        });
        menuList.appendChild(link);
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

    homepageCards.innerHTML = "";
    registry.forEach(function (lang) {
      const card = document.createElement("a");
      card.href = siteRoot + lang.slug + "/index.html";
      card.className = "hero-card " + lang.slug;
      card.innerHTML = "<h2>" + escapeHtml(lang.name) + "</h2><p>" + escapeHtml(lang.description || "") + "</p>";
      homepageCards.appendChild(card);
    });

    const compareCard = document.createElement("a");
    compareCard.href = siteRoot + "compare/index.html";
    compareCard.className = "hero-card";
    compareCard.style.borderColor = "var(--accent)";
    compareCard.innerHTML = '<h2 style="color:var(--accent);">Compare</h2><p>Same concept, different language — compare syntax and approaches across languages.</p>';
    homepageCards.appendChild(compareCard);
  }

  // ---- Support end dates: say "ended" once the date has passed, using the reader's clock ----
  function initSupportDates() {
    const now = Date.now();
    document.querySelectorAll(".eol[data-eol]").forEach(function (node) {
      const text = node.getAttribute("data-eol-text") || node.getAttribute("data-eol");
      const end = Date.parse(node.getAttribute("data-eol") + "T23:59:59Z");
      if (!isNaN(end) && end < now) {
        node.classList.add("eol-past");
        node.textContent = "Support ended " + text;
      }
    });
  }

  // ---- Version history page: upgrade changes between two versions, or what one version can use ----
  function initVersionsPage() {
    const list = document.getElementById("version-list");
    const fromSelect = document.getElementById("version-from");
    const toSelect = document.getElementById("version-to");
    const atSelect = document.getElementById("available-at");
    if (!list || !fromSelect || !toSelect || !atSelect) return;

    const breakingBox = document.getElementById("breaking-only");
    const summary = document.getElementById("version-summary");
    const emptyMessage = document.getElementById("version-empty");
    const kindButtons = Array.from(document.querySelectorAll(".kind-filter"));
    const stateButtons = Array.from(document.querySelectorAll(".state-filter"));
    const viewTabs = Array.from(document.querySelectorAll(".view-tab"));
    const panels = { changes: document.getElementById("panel-changes"), available: document.getElementById("panel-available") };
    const blocks = Array.from(list.querySelectorAll(".version-block"));
    const cards = Array.from(document.querySelectorAll(".feature-card"));
    const searchBox = document.getElementById("feature-search");
    const availableSummary = document.getElementById("available-summary");
    const availableEmpty = document.getElementById("available-empty");

    const orderOf = {};
    const labelOf = {};
    Array.from(fromSelect.options).concat(Array.from(toSelect.options), Array.from(atSelect.options)).forEach(function (option) {
      orderOf[option.value] = parseInt(option.getAttribute("data-order"), 10);
      labelOf[option.value] = option.textContent.replace(/ \(draft\)$/, "");
    });
    const allKinds = kindButtons.map(function (button) { return button.getAttribute("data-kind"); });
    const allStates = stateButtons.map(function (button) { return button.getAttribute("data-state"); });
    const defaults = { from: "", to: toSelect.value, at: atSelect.value };

    function pickList(raw, allowed) {
      const chosen = raw ? raw.split(",").filter(function (item) { return allowed.indexOf(item) !== -1; }) : [];
      return chosen.length ? chosen : allowed.slice();
    }
    const params = new URLSearchParams(location.search);
    const validId = function (id) { return id !== null && orderOf[id] !== undefined; };
    const state = {
      view: params.get("view") === "available" ? "available" : "changes",
      from: validId(params.get("from")) ? params.get("from") : defaults.from,
      to: params.get("to") && validId(params.get("to")) ? params.get("to") : defaults.to,
      kinds: pickList(params.get("kinds"), allKinds),
      breaking: params.get("breaking") === "1",
      at: params.get("at") && validId(params.get("at")) ? params.get("at") : defaults.at,
      states: pickList(params.get("states"), allStates),
      q: params.get("q") || "",
    };

    function writeUrl() {
      const query = [];
      if (state.view !== "changes") query.push("view=" + state.view);
      if (state.from !== defaults.from) query.push("from=" + encodeURIComponent(state.from));
      if (state.to !== defaults.to) query.push("to=" + encodeURIComponent(state.to));
      if (state.kinds.length !== allKinds.length) query.push("kinds=" + state.kinds.join(","));
      if (state.breaking) query.push("breaking=1");
      if (state.at !== defaults.at) query.push("at=" + encodeURIComponent(state.at));
      if (state.states.length !== allStates.length) query.push("states=" + state.states.join(","));
      if (state.q) query.push("q=" + encodeURIComponent(state.q));
      try {
        history.replaceState(null, "", location.pathname + (query.length ? "?" + query.join("&") : "") + location.hash);
      } catch (err) { /* URL sync is a convenience only */ }
    }

    function toggle(listOfValues, value) {
      const index = listOfValues.indexOf(value);
      if (index === -1) listOfValues.push(value);
      else if (listOfValues.length > 1) listOfValues.splice(index, 1);
    }

    // ---- upgrade changes
    function applyChanges() {
      const fromOrder = orderOf[state.from] || 0;
      const toOrder = orderOf[state.to];
      const validRange = fromOrder < toOrder;
      let shown = 0;
      blocks.forEach(function (block) {
        const blockOrder = block.getAttribute("data-order");
        let visible = 0;
        block.querySelectorAll(".change").forEach(function (item) {
          let inRange;
          if (blockOrder === "") {
            // Undated entries (deprecations with no edition) apply to any version that has the feature.
            inRange = parseInt(item.getAttribute("data-added-order"), 10) <= toOrder;
          } else {
            inRange = parseInt(blockOrder, 10) > fromOrder && parseInt(blockOrder, 10) <= toOrder;
          }
          const show = validRange && inRange &&
            state.kinds.indexOf(item.getAttribute("data-kind")) !== -1 &&
            (!state.breaking || item.getAttribute("data-breaking") === "true");
          item.hidden = !show;
          if (show) visible += 1;
        });
        block.hidden = visible === 0;
        shown += visible;
      });
      fromSelect.value = state.from;
      toSelect.value = state.to;
      kindButtons.forEach(function (button) {
        button.setAttribute("aria-pressed", state.kinds.indexOf(button.getAttribute("data-kind")) !== -1 ? "true" : "false");
      });
      if (breakingBox) breakingBox.checked = state.breaking;
      emptyMessage.hidden = shown > 0;
      if (!validRange) {
        summary.textContent = "Choose a starting version that is older than the version you are moving to.";
      } else {
        const noun = shown === 1 ? " change" : " changes";
        summary.textContent = state.from === ""
          ? shown + noun + " up to " + labelOf[state.to] + "."
          : shown + noun + " between " + labelOf[state.from] + " and " + labelOf[state.to] + ".";
      }
    }

    // ---- what can I use in one version
    const STATE_TEXT = { available: "Available", deprecated: "Deprecated", restricted: "Restricted", removed: "Removed", "not-yet": "Not yet" };

    // Mirrors lifecycle_state() in renderer/versioning.py: added: V is available in V, removed: V is not.
    function stateAt(card, at) {
      if (at < parseInt(card.getAttribute("data-added"), 10)) return "not-yet";
      let result = "available";
      const deprecated = card.getAttribute("data-deprecated");
      if (deprecated === "any" || (deprecated !== "" && at >= parseInt(deprecated, 10))) result = "deprecated";
      const removed = card.getAttribute("data-removed");
      if (removed !== "" && at >= parseInt(removed, 10)) {
        return card.getAttribute("data-removed-scope") ? "restricted" : "removed";
      }
      return result;
    }

    function applyAvailable() {
      const at = orderOf[state.at];
      const query = state.q.trim().toLowerCase();
      const counts = { available: 0, deprecated: 0, restricted: 0, removed: 0, "not-yet": 0 };
      let shown = 0;
      cards.forEach(function (card) {
        const cardState = stateAt(card, at);
        card.setAttribute("data-state", cardState);
        const badge = card.querySelector("[data-state-badge]");
        badge.textContent = STATE_TEXT[cardState];
        badge.className = "state-badge state-" + cardState;
        card.querySelectorAll(".migration").forEach(function (block) {
          block.hidden = block.getAttribute("data-show-when").split(" ").indexOf(cardState) === -1;
        });
        const matches = !query || card.getAttribute("data-search").indexOf(query) !== -1;
        if (matches) counts[cardState] += 1;
        const show = matches && state.states.indexOf(cardState) !== -1;
        card.hidden = !show;
        if (show) shown += 1;
      });
      atSelect.value = state.at;
      if (searchBox && searchBox.value !== state.q) searchBox.value = state.q;
      stateButtons.forEach(function (button) {
        const kind = button.getAttribute("data-state");
        button.setAttribute("aria-pressed", state.states.indexOf(kind) !== -1 ? "true" : "false");
      });
      availableEmpty.hidden = shown > 0;
      availableSummary.textContent =
        "In " + labelOf[state.at] + ": " + counts.available + " available, " + counts.deprecated + " deprecated, " +
        counts.restricted + " restricted, " + counts.removed + " removed, " + counts["not-yet"] + " not yet available. Showing " + shown + ".";
    }

    function applyView() {
      Object.keys(panels).forEach(function (name) { panels[name].hidden = name !== state.view; });
      viewTabs.forEach(function (tab) {
        tab.setAttribute("aria-pressed", tab.getAttribute("data-view") === state.view ? "true" : "false");
      });
    }

    function apply() {
      applyView();
      applyChanges();
      applyAvailable();
      writeUrl();
    }

    function revealHash() {
      const id = decodeURIComponent(location.hash.slice(1));
      const target = id ? document.getElementById(id) : null;
      if (!target) return;
      const inChanges = panels.changes.contains(target);
      state.view = inChanges ? "changes" : "available";
      if (inChanges) {
        const block = target.closest(".version-block");
        state.from = "";
        state.kinds = allKinds.slice();
        state.breaking = false;
        const blockOrder = block ? parseInt(block.getAttribute("data-order"), 10) : NaN;
        if (!isNaN(blockOrder) && blockOrder > orderOf[state.to]) state.to = block.id.replace(/^v-/, "");
      } else {
        state.states = allStates.slice();
        state.q = "";
      }
      apply();
      target.scrollIntoView();
    }

    viewTabs.forEach(function (tab) {
      tab.addEventListener("click", function () { state.view = tab.getAttribute("data-view"); apply(); });
    });
    fromSelect.addEventListener("change", function () { state.from = fromSelect.value; apply(); });
    toSelect.addEventListener("change", function () { state.to = toSelect.value; apply(); });
    atSelect.addEventListener("change", function () { state.at = atSelect.value; apply(); });
    if (breakingBox) breakingBox.addEventListener("change", function () { state.breaking = breakingBox.checked; apply(); });
    kindButtons.forEach(function (button) {
      button.addEventListener("click", function () { toggle(state.kinds, button.getAttribute("data-kind")); apply(); });
    });
    stateButtons.forEach(function (button) {
      button.addEventListener("click", function () { toggle(state.states, button.getAttribute("data-state")); apply(); });
    });
    if (searchBox) searchBox.addEventListener("input", function () { state.q = searchBox.value; apply(); });
    window.addEventListener("hashchange", revealHash);

    apply();
    revealHash();
  }

  function initCompareBoard() {
    const layout = document.getElementById("compare-layout");
    const board = document.getElementById("compare-board");
    const barViewport = document.getElementById("lane-bar-viewport");
    const bar = document.getElementById("lane-bar");
    const addBtn = document.getElementById("lane-add");
    const addLabel = document.getElementById("lane-add-label");
    const menuBox = document.getElementById("lane-menu");
    const menuBackdrop = document.getElementById("lane-menu-backdrop");
    const sheetMode = window.matchMedia("(max-width: 700px)");
    const menu = document.getElementById("lane-menu-list");
    const emptyState = document.getElementById("compare-empty-state");
    const status = document.getElementById("compare-status");
    if (!layout || !barViewport || !board || !bar || !addBtn || !addLabel || !menuBox || !menu || !emptyState) return;
    bindScrollFade(board, "x");
    bindScrollFade(menu, "y");

    const maxLanes = parseInt(board.getAttribute("data-max-lanes"), 10) || 4;
    const bySlug = {};
    registry.forEach(function (lang) { bySlug[lang.slug] = lang; });

    function laneColor(lang) {
      return lang && /^#[0-9a-f]{6}$/i.test(lang.color || "") ? lang.color : "";
    }

    function readSelectionFromUrl() {
      const raw = new URLSearchParams(location.search).get("lang") || "";
      const seen = {};
      return raw.split(",").filter(function (slug) {
        if (!bySlug[slug] || seen[slug]) return false;
        seen[slug] = true;
        return true;
      }).slice(0, maxLanes);
    }

    let selected = readSelectionFromUrl();

    function writeSelectionToUrl() {
      const query = selected.length ? "?lang=" + selected.map(encodeURIComponent).join(",") : "";
      try {
        history.replaceState(null, "", location.pathname + query + location.hash);
      } catch (err) { /* URL sync is a convenience only */ }
    }

    function availableLanguages() {
      return registry.filter(function (lang) { return selected.indexOf(lang.slug) === -1; });
    }

    function announce(message) {
      if (status) status.textContent = message;
    }

    function renderLanes() {
      bar.querySelectorAll(".lane").forEach(function (node) { node.remove(); });
      selected.forEach(function (slug) {
        const lang = bySlug[slug];
        const lane = document.createElement("div");
        lane.className = "lane";
        lane.setAttribute("data-language", slug);
        const color = laneColor(lang);
        if (color) lane.style.setProperty("--lane-color", color);

        const link = document.createElement("a");
        link.className = "lane-name";
        link.href = siteRoot + encodeURIComponent(slug) + "/index.html";
        link.title = "Open the " + lang.name + " reference";
        link.textContent = lang.name;

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "lane-remove";
        remove.setAttribute("aria-label", "Remove " + lang.name + " from the comparison");
        remove.textContent = "\u00d7";
        remove.addEventListener("click", function () { removeLanguage(slug); });

        lane.appendChild(link);
        lane.appendChild(remove);
        bar.appendChild(lane);
      });
    }

    function renderCells() {
      // repeat() needs at least one track, so an empty board still reserves one lane column
      layout.style.setProperty("--lanes", String(Math.max(selected.length, 1)));
      document.querySelectorAll(".compare-table [data-language]").forEach(function (cell) {
        const slug = cell.getAttribute("data-language");
        const index = selected.indexOf(slug);
        cell.hidden = index === -1;
        if (index === -1) {
          cell.style.removeProperty("order");
          cell.style.removeProperty("--lane-color");
          return;
        }
        cell.style.order = String(index + 1);
        const color = laneColor(bySlug[slug]);
        if (color) cell.style.setProperty("--lane-color", color);
        else cell.style.removeProperty("--lane-color");
      });
      document.querySelectorAll(".compare-section").forEach(function (section) {
        section.hidden = selected.length === 0;
      });
      emptyState.hidden = selected.length > 0;
    }

    function renderAddButton() {
      const full = selected.length >= maxLanes;
      const exhausted = availableLanguages().length === 0;
      addBtn.disabled = full || exhausted;
      addLabel.textContent = full ? selected.length + " of " + maxLanes + " added"
        : exhausted ? "All added"
        : "Add language";
      if (addBtn.disabled) closeMenu(false);
    }

    function renderMenu() {
      menu.textContent = "";
      availableLanguages().forEach(function (lang) {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "lane-menu-item";
        item.setAttribute("role", "menuitem");
        item.setAttribute("data-language", lang.slug);

        const dot = document.createElement("span");
        dot.className = "lane-menu-dot";
        dot.setAttribute("aria-hidden", "true");
        const color = laneColor(lang);
        if (color) dot.style.background = color;

        const name = document.createElement("span");
        name.textContent = lang.name;

        item.appendChild(dot);
        item.appendChild(name);
        item.addEventListener("click", function () { addLanguage(lang.slug); });
        menu.appendChild(item);
      });
    }

    function menuItems() {
      return Array.from(menu.querySelectorAll(".lane-menu-item"));
    }

    // Wide screens anchor the menu under the Add button; on phones CSS turns it into a bottom sheet.
    function positionMenu() {
      if (sheetMode.matches) {
        menuBox.style.removeProperty("--menu-top");
        menuBox.style.removeProperty("--menu-left");
        menuBox.style.removeProperty("--menu-width");
        menu.style.removeProperty("max-height");
        return;
      }
      const rect = addBtn.getBoundingClientRect();
      const width = Math.min(Math.max(rect.width, 224), window.innerWidth - 16);
      const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
      menuBox.style.setProperty("--menu-top", Math.round(rect.bottom + 6) + "px");
      menuBox.style.setProperty("--menu-left", Math.round(left) + "px");
      menuBox.style.setProperty("--menu-width", Math.round(width) + "px");
      menu.style.maxHeight = Math.max(160, Math.min(288, window.innerHeight - rect.bottom - 24)) + "px";
    }

    function openMenu() {
      if (addBtn.disabled) return;
      renderMenu();
      positionMenu();
      menuBox.hidden = false;
      if (menuBackdrop) menuBackdrop.hidden = !sheetMode.matches;
      document.body.classList.add("menu-open");
      addBtn.setAttribute("aria-expanded", "true");
      const items = menuItems();
      if (items.length) items[0].focus();
    }

    function closeMenu(returnFocus) {
      if (menuBox.hidden) return;
      menuBox.hidden = true;
      if (menuBackdrop) menuBackdrop.hidden = true;
      document.body.classList.remove("menu-open");
      addBtn.setAttribute("aria-expanded", "false");
      if (returnFocus) addBtn.focus();
    }

    // The lane bar sits outside the board so it can stay pinned while the page scrolls. Keep the
    // two scrolled to the same sideways position, whichever one the user swipes.
    function syncScroll(from, to) {
      if (Math.abs(to.scrollLeft - from.scrollLeft) > 0.5) to.scrollLeft = from.scrollLeft;
      layout.setAttribute("data-scrolled", from.scrollLeft > 1 ? "true" : "false");
    }
    board.addEventListener("scroll", function () { syncScroll(board, barViewport); }, { passive: true });
    barViewport.addEventListener("scroll", function () { syncScroll(barViewport, board); }, { passive: true });

    function update() {
      renderLanes();
      renderCells();
      renderAddButton();
      writeSelectionToUrl();
      syncScroll(board, barViewport);
    }

    function addLanguage(slug) {
      if (!bySlug[slug] || selected.indexOf(slug) !== -1 || selected.length >= maxLanes) return;
      selected.push(slug);
      closeMenu(false);
      update();
      announce(bySlug[slug].name + " added. " + selected.length + " of " + maxLanes + " languages.");
      if (addBtn.disabled) {
        const removeBtn = bar.querySelector('.lane[data-language="' + slug + '"] .lane-remove');
        if (removeBtn) removeBtn.focus();
      } else {
        addBtn.focus();
      }
    }

    function removeLanguage(slug) {
      if (selected.indexOf(slug) === -1) return;
      selected = selected.filter(function (item) { return item !== slug; });
      update();
      announce(bySlug[slug].name + " removed. " + selected.length + " of " + maxLanes + " languages.");
      addBtn.focus();
    }

    addBtn.addEventListener("click", function () {
      if (menuBox.hidden) openMenu(); else closeMenu(true);
    });
    addBtn.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" && menuBox.hidden) { e.preventDefault(); openMenu(); }
    });
    menu.addEventListener("keydown", function (e) {
      const items = menuItems();
      const index = items.indexOf(document.activeElement);
      if (e.key === "ArrowDown") { e.preventDefault(); items[(index + 1) % items.length].focus(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); items[(index - 1 + items.length) % items.length].focus(); }
      else if (e.key === "Home") { e.preventDefault(); items[0].focus(); }
      else if (e.key === "End") { e.preventDefault(); items[items.length - 1].focus(); }
      else if (e.key === "Escape") { e.preventDefault(); closeMenu(true); }
      else if (e.key === "Tab") { closeMenu(false); }
    });
    if (menuBackdrop) menuBackdrop.addEventListener("click", function () { closeMenu(true); });
    window.addEventListener("scroll", function () { if (!menuBox.hidden && !sheetMode.matches) closeMenu(false); }, { passive: true });
    window.addEventListener("resize", function () { if (!menuBox.hidden) { if (sheetMode.matches) positionMenu(); else closeMenu(false); } });
    document.addEventListener("click", function (e) {
      if (!menuBox.hidden && !e.target.closest(".lane-add-wrap") && !e.target.closest("#lane-menu")) closeMenu(false);
    });

    update();
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
    results.classList.add("scroll-fade");
    bindScrollFade(results, "y");
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
      return siteRoot + LANG_META[item.lang].path + "#" + item.id;
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
    btn.innerHTML =
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/></svg>' +
      '<span class="search-trigger-label">Search</span> <kbd>/</kbd>';
    btn.addEventListener("click", openFn);
    const theme = document.getElementById("theme-toggle");
    if (theme) headerInner.insertBefore(btn, theme); else headerInner.appendChild(btn);
    const old = document.querySelector(".search-wrap");
    if (old) old.remove();
  }

  renderLanguageNavigation();
  renderHomepageCards();
  initCompareBoard();
  initVersionsPage();
  initSupportDates();
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

  document.querySelectorAll(".table-scroll").forEach(function (el) { bindScrollFade(el, "x"); });

  // ---- Phone/tablet: sections become a slide-in drawer opened from a floating button ----
  let notifyActiveSection = function () {};

  function initSectionDrawer() {
    const drawer = document.querySelector(".sidebar");
    if (!drawer || !currentLang) return null;
    const scroller = drawer.querySelector(".sidebar-scroll");
    const closeBtn = drawer.querySelector(".drawer-close");
    if (!scroller || !closeBtn || !drawer.querySelector('a[href^="#"]')) return null;

    bindScrollFade(scroller, "y");

    const narrow = window.matchMedia("(max-width: 860px)");
    const backdrop = document.createElement("div");
    backdrop.id = "drawer-backdrop";
    backdrop.hidden = true;
    document.body.appendChild(backdrop);

    const fab = document.createElement("button");
    fab.id = "sections-fab";
    fab.type = "button";
    fab.setAttribute("aria-controls", drawer.id);
    fab.setAttribute("aria-expanded", "false");
    fab.innerHTML =
      '<span class="fab-icon" aria-hidden="true"><i></i><i></i><i></i></span>' +
      '<span class="fab-label">Sections</span>';
    document.body.appendChild(fab);
    const fabLabel = fab.querySelector(".fab-label");

    let currentTitle = "";
    let activeLink = null;
    let lastY = window.scrollY;

    function isOpen() { return drawer.classList.contains("is-open"); }

    function updateFab() {
      const atTop = window.scrollY < 120;
      const showTitle = !atTop && currentTitle;
      fabLabel.textContent = showTitle ? currentTitle : "Sections";
      fab.setAttribute(
        "aria-label",
        showTitle ? "Open sections menu. Current section: " + currentTitle : "Open sections menu"
      );
    }

    function open() {
      if (!narrow.matches || isOpen()) return;
      drawer.classList.add("is-open");
      drawer.setAttribute("role", "dialog");
      drawer.setAttribute("aria-modal", "true");
      backdrop.hidden = false;
      document.body.classList.add("drawer-open");
      fab.setAttribute("aria-expanded", "true");
      if (activeLink) scroller.scrollTop = Math.max(0, activeLink.offsetTop - scroller.clientHeight / 2);
      closeBtn.focus();
    }

    function close(returnFocus) {
      if (!isOpen()) return;
      drawer.classList.remove("is-open");
      backdrop.hidden = true;
      document.body.classList.remove("drawer-open");
      fab.setAttribute("aria-expanded", "false");
      if (returnFocus) fab.focus();
    }

    function applyMode() {
      if (narrow.matches) {
        drawer.setAttribute("aria-label", "Sections");
      } else {
        close(false);
        drawer.removeAttribute("role");
        drawer.removeAttribute("aria-modal");
      }
    }

    fab.addEventListener("click", open);
    closeBtn.addEventListener("click", function () { close(true); });
    backdrop.addEventListener("click", function () { close(true); });
    drawer.addEventListener("click", function (e) {
      if (e.target.closest && e.target.closest('a[href^="#"]')) close(false);
    });
    document.addEventListener("keydown", function (e) {
      if (!isOpen()) return;
      if (e.key === "Escape") { e.preventDefault(); close(true); return; }
      if (e.key !== "Tab") return;
      const focusable = Array.from(drawer.querySelectorAll('button, a[href]'));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });

    // The button shows its label at the top of the page, then shrinks to the icon while scrolling
    // down and returns with the current section's name when scrolling back up.
    let ticking = false;
    window.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        const y = window.scrollY;
        const delta = y - lastY;
        if (y < 120 || delta < -8) fab.classList.remove("is-compact");
        else if (delta > 8) fab.classList.add("is-compact");
        if (Math.abs(delta) > 8 || y < 120) lastY = y;
        updateFab();
        ticking = false;
      });
    }, { passive: true });

    if (narrow.addEventListener) narrow.addEventListener("change", applyMode);
    else if (narrow.addListener) narrow.addListener(applyMode);
    applyMode();
    updateFab();

    return {
      setActive: function (link) {
        activeLink = link;
        currentTitle = link.textContent.trim();
        updateFab();
      }
    };
  }

  const sectionDrawer = initSectionDrawer();
  if (sectionDrawer) notifyActiveSection = sectionDrawer.setActive;

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
            notifyActiveSection(link);
          }
        });
      },
      { rootMargin: "-20% 0px -70% 0px", threshold: 0 }
    );
    map.forEach(function (_link, el) { observer.observe(el); });
  }
})();
