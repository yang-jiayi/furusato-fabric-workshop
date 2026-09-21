/* Furusato Fabric Workshop v2.7.0 — single-file guide behaviour.
   No dependencies, no network, no build step at runtime. */
(function () {
  "use strict";

  var STORE_KEY = "furusato-workshop-v2.7.0";
  var STORE_VERSION = 2;
  var LEGACY_LANG_KEY = "fiq-lang";
  var root = document.documentElement;
  var STRINGS = window.__FURUSATO_STRINGS__ || {};
  var CHAPTER_TITLES = window.__FURUSATO_SECTIONS__ || [];

  function t(key) {
    var entry = STRINGS[key];
    if (!entry) { return key; }
    return entry[currentLang()] || entry.ja || key;
  }

  function currentLang() {
    return root.getAttribute("data-lang") === "en" ? "en" : "ja";
  }

  /* ------------------------------------------------------------ storage */
  function readState() {
    var fallback = { version: STORE_VERSION, workshop: "2.7.0", lang: null, steps: [] };
    var raw;
    try { raw = window.localStorage.getItem(STORE_KEY); } catch (e) { return fallback; }
    if (!raw) {
      // The previous release's flow changed, so completed steps are never imported; only the
      // reader's language preference carries over.
      try {
        var legacy = window.localStorage.getItem(LEGACY_LANG_KEY);
        if (legacy === "ja" || legacy === "en") { fallback.lang = legacy; }
      } catch (e2) { /* ignore */ }
      return fallback;
    }
    try {
      var parsed = JSON.parse(raw);
      if (!parsed || parsed.version !== STORE_VERSION || parsed.workshop !== "2.7.0") { return fallback; }
      return {
        version: STORE_VERSION,
        workshop: "2.7.0",
        lang: parsed.lang === "en" || parsed.lang === "ja" ? parsed.lang : null,
        steps: Array.isArray(parsed.steps) ? parsed.steps.filter(function (s) { return typeof s === "string"; }) : []
      };
    } catch (e3) {
      return fallback;
    }
  }

  var state = readState();

  function persist() {
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify({
        version: STORE_VERSION,
        workshop: "2.7.0",
        lang: currentLang(),
        steps: Array.from(done)
      }));
    } catch (e) { /* private mode: progress simply is not persisted */ }
  }

  /* ---------------------------------------------------------- live region */
  var live = document.getElementById("live-status");
  function announce(message) {
    if (!live) { return; }
    live.textContent = "";
    window.setTimeout(function () { live.textContent = message; }, 30);
  }

  /* ------------------------------------------------------------ language */
  var langButtons = Array.prototype.slice.call(document.querySelectorAll("[data-set-lang]"));
  // Cached once: these node lists never change, and re-querying them on every
  // toggle is the difference between an instant switch and a visible stall.
  var i18nText = Array.prototype.slice.call(document.querySelectorAll("[data-i18n]"));
  var i18nLabel = Array.prototype.slice.call(document.querySelectorAll("[data-i18n-label]"));
  var i18nPlaceholder = Array.prototype.slice.call(document.querySelectorAll("[data-i18n-placeholder]"));
  var i18nTitle = Array.prototype.slice.call(document.querySelectorAll("[data-i18n-title]"));

  function applyLang(lang, announceChange) {
    root.setAttribute("data-lang", lang);
    root.setAttribute("lang", lang);
    langButtons.forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.getAttribute("data-set-lang") === lang));
    });
    i18nText.forEach(function (node) { node.textContent = t(node.getAttribute("data-i18n")); });
    i18nLabel.forEach(function (node) { node.setAttribute("aria-label", t(node.getAttribute("data-i18n-label"))); });
    i18nPlaceholder.forEach(function (node) { node.setAttribute("placeholder", t(node.getAttribute("data-i18n-placeholder"))); });
    i18nTitle.forEach(function (node) { node.setAttribute("title", t(node.getAttribute("data-i18n-title"))); });
    var titleNode = document.querySelector("title");
    if (titleNode) { titleNode.textContent = t("app.title") + " — v2.7.0"; }
    // The search index is language specific, but building it walks the whole
    // document, so defer that until a search actually needs it.
    indexDirty = true;
    if (searchInput && searchInput.value.trim()) { runSearch(searchInput.value); }
    updateCurrentSection();
    persist();
    if (announceChange) { announce(t("lang.switched." + lang)); }
  }

  langButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      applyLang(button.getAttribute("data-set-lang"), true);
    });
  });

  /* ----------------------------------------------------------- checklist */
  var done = new Set(state.steps);
  var stepInputs = Array.prototype.slice.call(document.querySelectorAll("[data-step-id]"));
  var progressFill = document.getElementById("progress-fill");
  var progressText = document.getElementById("progress-text");

  function refreshProgress() {
    var total = stepInputs.length;
    var count = 0;
    stepInputs.forEach(function (input) {
      var isDone = done.has(input.getAttribute("data-step-id"));
      input.checked = isDone;
      if (input.parentElement) { input.parentElement.classList.toggle("is-done", isDone); }
      if (isDone) { count += 1; }
      var link = document.querySelector('[data-toc-step="' + input.getAttribute("data-step-id") + '"]');
      if (link) { link.hidden = !isDone; }
    });
    var percent = total ? Math.round((count / total) * 100) : 0;
    if (progressFill) { progressFill.style.width = percent + "%"; }
    if (progressText) { progressText.textContent = count + " / " + total + " (" + percent + "%)"; }
    var meter = document.getElementById("progress-chip");
    if (meter) {
      meter.setAttribute("aria-valuenow", String(count));
      meter.setAttribute("aria-valuemax", String(total));
      meter.setAttribute("aria-valuetext", count + " / " + total + " (" + percent + "%)");
    }
  }

  stepInputs.forEach(function (input) {
    input.addEventListener("change", function () {
      var id = input.getAttribute("data-step-id");
      if (input.checked) { done.add(id); } else { done.delete(id); }
      refreshProgress();
      persist();
      announce(t(input.checked ? "checklist.announce.on" : "checklist.announce.off"));
    });
  });

  var resetButton = document.getElementById("reset-progress");
  if (resetButton) {
    resetButton.addEventListener("click", function () {
      if (!window.confirm(t("checklist.reset.confirm"))) { return; }
      done = new Set();
      refreshProgress();
      persist();
      announce(t("checklist.reset.done"));
    });
  }

  /* ---------------------------------------------------------------- copy */
  document.querySelectorAll("[data-copy-target]").forEach(function (button) {
    button.addEventListener("click", function () {
      var target = document.getElementById(button.getAttribute("data-copy-target"));
      if (!target) { return; }
      var text = target.textContent;
      var label = button.querySelector("[data-copy-label]");

      function feedback(ok) {
        button.classList.toggle("is-done", ok);
        button.classList.toggle("is-error", !ok);
        if (label) { label.textContent = t(ok ? "copy.done" : "copy.failed"); }
        announce(t(ok ? "copy.done" : "copy.failed"));
        window.setTimeout(function () {
          button.classList.remove("is-done", "is-error");
          if (label) { label.textContent = t("copy.label"); }
        }, 2000);
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { feedback(true); }, function () { feedback(legacyCopy(text)); });
      } else {
        feedback(legacyCopy(text));
      }
    });
  });

  function legacyCopy(text) {
    try {
      var area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "readonly");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(area);
      return ok;
    } catch (e) {
      return false;
    }
  }

  /* ------------------------------------------------------------- details */
  var expandAll = document.getElementById("expand-all");
  if (expandAll) {
    // data-i18n lives on the inner label, never on the button: applyLang assigns
    // textContent, which would otherwise delete the button's own subtree and make
    // every later click throw. The label is also the single source of truth for
    // which key is current, so language switching and clicking cannot disagree.
    var expandLabel = expandAll.querySelector("[data-expand-label]");
    var optionalDetails = Array.prototype.slice.call(
      document.querySelectorAll("details.optional-details")
    );

    var syncExpandAll = function () {
      if (!expandLabel) { return; }
      var allOpen = optionalDetails.length > 0 && optionalDetails.every(function (item) {
        return item.open;
      });
      var key = allOpen ? "details.collapse" : "details.expand";
      expandLabel.setAttribute("data-i18n", key);
      expandLabel.textContent = t(key);
      expandAll.setAttribute("aria-expanded", String(allOpen));
    };

    expandAll.addEventListener("click", function () {
      var shouldOpen = optionalDetails.some(function (item) { return !item.open; });
      optionalDetails.forEach(function (item) { item.open = shouldOpen; });
      syncExpandAll();
    });
    // Individual disclosure toggles must keep the summary control honest too.
    optionalDetails.forEach(function (item) {
      item.addEventListener("toggle", syncExpandAll);
    });
    syncExpandAll();
  }

  /* ------------------------------------------------------------ lightbox */
  var lightbox = document.getElementById("lightbox");
  var lightboxStage = document.getElementById("lightbox-stage");
  var lightboxTitle = document.getElementById("lightbox-title");
  var lightboxClose = document.getElementById("lightbox-close");
  var lastFocus = null;
  var lightboxSerial = 0;

  function cloneArtwork(source) {
    var clone = source.cloneNode(true);
    var nodes = [clone].concat(Array.prototype.slice.call(clone.querySelectorAll("*")));
    var ids = Object.create(null);
    var prefix = "lightbox-art-" + (++lightboxSerial) + "-";
    nodes.forEach(function (node) {
      if (node.id) {
        ids[node.id] = prefix + node.id;
        node.id = ids[node.id];
      }
    });
    // SVG arrowheads and accessible titles must resolve inside the clone, not
    // against the original artwork hidden behind the dialog or inactive language.
    function remapUrls(value) {
      return value.replace(/url\(#([^)]+)\)/g, function (match, id) {
        return ids[id] ? "url(#" + ids[id] + ")" : match;
      });
    }
    nodes.forEach(function (node) {
      Array.prototype.forEach.call(node.attributes, function (attribute) {
        var value = remapUrls(attribute.value);
        if ((attribute.name === "href" || attribute.name === "xlink:href") && value.charAt(0) === "#") {
          value = "#" + (ids[value.slice(1)] || value.slice(1));
        } else if (attribute.name === "aria-labelledby" || attribute.name === "aria-describedby") {
          value = value.split(/\s+/).map(function (id) { return ids[id] || id; }).join(" ");
        }
        attribute.value = value;
      });
      if (node.tagName.toLowerCase() === "style") { node.textContent = remapUrls(node.textContent); }
    });
    return clone;
  }

  function openLightbox(button) {
    if (!lightbox || !lightboxStage) { return; }
    var artwork = button.querySelector('.figure__art[data-l="' + currentLang() + '"]');
    var source = (artwork || button).querySelector("img, svg");
    if (!source) { return; }
    lastFocus = button;
    lightboxStage.innerHTML = "";
    lightboxStage.appendChild(cloneArtwork(source));
    var figure = button.closest("figure");
    var number = figure && figure.querySelector(".caption__num");
    var caption = number ? number.innerText.trim() : button.getAttribute("data-figure-label") || "";
    if (lightboxTitle) { lightboxTitle.textContent = caption; }
    lightbox.hidden = false;
    document.body.style.overflow = "hidden";
    if (lightboxClose) { lightboxClose.focus(); }
  }

  function closeLightbox() {
    if (!lightbox || lightbox.hidden) { return; }
    lightbox.hidden = true;
    if (lightboxStage) { lightboxStage.innerHTML = ""; }
    document.body.style.overflow = "";
    if (lastFocus) { lastFocus.focus(); }
  }

  document.querySelectorAll("[data-lightbox]").forEach(function (button) {
    button.addEventListener("click", function () { openLightbox(button); });
  });
  if (lightboxClose) { lightboxClose.addEventListener("click", closeLightbox); }
  if (lightbox) {
    lightbox.addEventListener("click", function (event) {
      if (event.target === lightbox || event.target === lightboxStage) { closeLightbox(); }
    });
    lightbox.addEventListener("keydown", function (event) {
      if (event.key !== "Tab") { return; }
      // Two focusable controls only; keep the focus ring inside the dialog.
      event.preventDefault();
      if (lightboxClose) { lightboxClose.focus(); }
    });
  }

  /* -------------------------------------------------------------- search */
  var searchInput = document.getElementById("search-input");
  var searchPanel = document.getElementById("search-panel");
  var searchList = document.getElementById("search-results");
  var searchCount = document.getElementById("search-count");
  var searchClear = document.getElementById("search-clear");
  var index = [];
  var indexDirty = true;
  var hits = [];
  var activeHit = -1;

  function buildIndex() {
    index = [];
    var lang = currentLang();
    var blocks = document.querySelectorAll("[data-search-block]");
    for (var i = 0; i < blocks.length; i += 1) {
      var block = blocks[i];
      var section = block.closest("[data-section-id]");
      if (!section) { continue; }
      var heading = section.querySelector("[data-section-title]");
      var text = textFor(block, lang);
      if (!text) { continue; }
      index.push({
        id: section.getAttribute("id"),
        title: heading ? textFor(heading, lang) : "",
        text: text,
        lower: text.toLowerCase()
      });
    }
    indexDirty = false;
  }

  function textFor(node, lang) {
    var parts = [];
    node.querySelectorAll('[data-l="' + lang + '"]').forEach(function (span) {
      parts.push(span.textContent);
    });
    if (!parts.length) { parts.push(node.textContent); }
    return parts.join(" ").replace(/\s+/g, " ").trim();
  }

  function escapeHtml(value) {
    return value.replace(/[&<>"']/g, function (character) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character];
    });
  }

  function excerpt(entry, needle) {
    var position = entry.lower.indexOf(needle);
    var start = Math.max(0, position - 48);
    var slice = entry.text.slice(start, start + 190);
    var prefix = start > 0 ? "… " : "";
    var suffix = start + 190 < entry.text.length ? " …" : "";
    var escaped = escapeHtml(prefix + slice + suffix);
    var escapedNeedle = escapeHtml(needle).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return escaped.replace(new RegExp(escapedNeedle, "gi"), function (match) { return "<mark>" + match + "</mark>"; });
  }

  function runSearch(rawQuery) {
    if (!searchPanel || !searchList) { return; }
    var query = rawQuery.trim().toLowerCase();
    searchList.innerHTML = "";
    activeHit = -1;
    if (searchInput) { searchInput.removeAttribute("aria-activedescendant"); }
    hits = [];
    if (query.length < 2) {
      closeSearch();
      if (searchCount) { searchCount.textContent = ""; }
      return;
    }
    if (indexDirty || !index.length) { buildIndex(); }
    var seen = {};
    index.forEach(function (entry) {
      if (hits.length >= 40) { return; }
      if (entry.lower.indexOf(query) === -1) { return; }
      var key = entry.id + "|" + entry.text.slice(0, 60);
      if (seen[key]) { return; }
      seen[key] = true;
      hits.push(entry);
    });
    if (searchCount) {
      searchCount.textContent = hits.length ? hits.length + " " + t("search.count.suffix") : t("search.none");
    }
    hits.forEach(function (entry, position) {
      var item = document.createElement("li");
      item.setAttribute("role", "presentation");
      var button = document.createElement("button");
      button.type = "button";
      button.id = "search-hit-" + position;
      button.tabIndex = -1;
      button.className = "search__hit";
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", "false");
      button.innerHTML = "<b>" + escapeHtml(entry.title) + "</b><small>" + excerpt(entry, query) + "</small>";
      button.addEventListener("click", function () { gotoHit(position); });
      item.appendChild(button);
      searchList.appendChild(item);
    });
    setSearchOpen(true);
    announce((hits.length ? hits.length : 0) + " " + t("search.count.suffix"));
  }

  function highlightHit(position) {
    var buttons = searchList ? searchList.querySelectorAll(".search__hit") : [];
    Array.prototype.forEach.call(buttons, function (button, buttonIndex) {
      var selected = buttonIndex === position;
      button.setAttribute("aria-selected", String(selected));
      if (selected) { button.scrollIntoView({ block: "nearest" }); }
    });
    if (searchInput) {
      if (buttons[position]) { searchInput.setAttribute("aria-activedescendant", buttons[position].id); }
      else { searchInput.removeAttribute("aria-activedescendant"); }
    }
    activeHit = position;
  }

  function gotoHit(position) {
    var entry = hits[position];
    if (!entry) { return; }
    var target = document.getElementById(entry.id);
    if (target) {
      target.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
        block: "start"
      });
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
    }
    closeSearch();
  }

  function setSearchOpen(open) {
    if (searchPanel) { searchPanel.hidden = !open; }
    if (searchInput) { searchInput.setAttribute("aria-expanded", String(open)); }
  }

  function closeSearch() {
    setSearchOpen(false);
    highlightHit(-1);
  }

  if (searchInput) {
    searchInput.addEventListener("input", function () { runSearch(searchInput.value); });
    searchInput.addEventListener("focus", function () {
      if (hits.length && searchInput.value.trim().length >= 2 && searchPanel) { setSearchOpen(true); }
    });
    searchInput.addEventListener("keydown", function (event) {
      if (event.key === "Escape") { searchInput.value = ""; runSearch(""); return; }
      if (!hits.length) { return; }
      if (event.key === "ArrowDown") { event.preventDefault(); highlightHit((activeHit + 1) % hits.length); }
      else if (event.key === "ArrowUp") {
        event.preventDefault();
        highlightHit(activeHit < 0 ? hits.length - 1 : (activeHit - 1 + hits.length) % hits.length);
      }
      else if (event.key === "Enter") { event.preventDefault(); gotoHit(activeHit >= 0 ? activeHit : 0); }
    });
  }
  if (searchClear) {
    searchClear.addEventListener("click", function () {
      if (searchInput) { searchInput.value = ""; searchInput.focus(); }
      runSearch("");
    });
  }

  document.addEventListener("click", function (event) {
    if (!searchPanel || searchPanel.hidden) { return; }
    if (event.target.closest && event.target.closest(".search")) { return; }
    closeSearch();
  });
  document.addEventListener("focusin", function (event) {
    if (searchPanel && !searchPanel.hidden && !event.target.closest(".search")) { closeSearch(); }
  });

  /* ------------------------------------------------------ nav / progress */
  var tocPanel = document.getElementById("toc");
  var tocToggle = document.getElementById("toc-toggle");
  var tocBackdrop = document.getElementById("toc-backdrop");
  var mobileToc = window.matchMedia("(max-width: 1024px)");

  function setToc(open, restoreFocus) {
    if (!tocPanel || !tocToggle) { return; }
    var wasOpen = tocPanel.classList.contains("is-open");
    tocPanel.classList.toggle("is-open", open);
    tocToggle.setAttribute("aria-expanded", String(open));
    tocToggle.setAttribute("data-i18n-label", open ? "nav.toggle.close" : "nav.toggle.open");
    tocToggle.setAttribute("aria-label", t(open ? "nav.toggle.close" : "nav.toggle.open"));
    if (tocBackdrop) { tocBackdrop.hidden = !open; }
    if (open) {
      var link = tocPanel.querySelector('.toc__link[aria-current="true"]') || tocPanel.querySelector("a");
      if (link) { link.focus(); }
    } else if (wasOpen && restoreFocus !== false) {
      tocToggle.focus({ preventScroll: true });
    }
  }

  if (tocToggle) {
    tocToggle.addEventListener("click", function () {
      setToc(!tocPanel.classList.contains("is-open"));
    });
  }
  if (tocBackdrop) { tocBackdrop.addEventListener("click", function () { setToc(false); }); }
  if (tocPanel) {
    tocPanel.addEventListener("click", function (event) {
      var link = event.target.closest("a");
      if (!link || !mobileToc.matches) { return; }
      setToc(false, false);
      var target = document.getElementById(link.hash.slice(1));
      if (target) {
        target.setAttribute("tabindex", "-1");
        target.focus({ preventScroll: true });
      }
    });
  }
  document.addEventListener("focusin", function (event) {
    if (tocPanel && tocPanel.classList.contains("is-open") &&
        !tocPanel.contains(event.target) && !tocToggle.contains(event.target)) {
      setToc(false, false);
    }
  });
  mobileToc.addEventListener("change", function () {
    if (!tocPanel) { return; }
    if (!mobileToc.matches) { setToc(false, false); }
    else if (!tocPanel.classList.contains("is-open") && tocPanel.contains(document.activeElement)) {
      tocToggle.focus({ preventScroll: true });
    }
  });

  var progressValue = document.getElementById("reading-progress-value");
  var currentLabel = document.getElementById("current-section");
  var toTop = document.getElementById("to-top");
  var chapters = Array.prototype.slice.call(document.querySelectorAll("[data-chapter-anchor]"));
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".toc__link"));

  function updateCurrentSection() {
    if (!chapters.length) { return; }
    // The "current" chapter is the last one whose top has passed an anchor line
    // a quarter of the way down the reading area, which matches what a reader
    // perceives after following a link or scrolling.
    var header = document.querySelector(".app-header");
    var headerHeight = header ? header.getBoundingClientRect().height : 0;
    var anchor = headerHeight + window.innerHeight * 0.25;
    var current = null;
    chapters.forEach(function (chapter) {
      var rect = chapter.getBoundingClientRect();
      if (rect.top <= anchor) { current = chapter; }
    });
    if (!current) {
      for (var i = 0; i < chapters.length; i += 1) {
        if (chapters[i].getBoundingClientRect().bottom > headerHeight) { current = chapters[i]; break; }
      }
    }
    var currentId = current ? current.id : chapters[0].id;
    tocLinks.forEach(function (link) {
      var isCurrent = link.getAttribute("href") === "#" + currentId;
      if (isCurrent) { link.setAttribute("aria-current", "true"); } else { link.removeAttribute("aria-current"); }
    });
    if (currentLabel) {
      var match = CHAPTER_TITLES.filter(function (entry) { return entry.id === currentId; })[0];
      currentLabel.textContent = match ? (match[currentLang()] || match.ja) : "";
    }
  }

  function onScroll() {
    var height = document.documentElement.scrollHeight - window.innerHeight;
    var ratio = height > 0 ? Math.min(1, Math.max(0, window.scrollY / height)) : 0;
    if (progressValue) { progressValue.style.width = (ratio * 100).toFixed(2) + "%"; }
    if (toTop) { toTop.classList.toggle("is-visible", window.scrollY > 640); }
    updateCurrentSection();
  }

  var ticking = false;
  window.addEventListener("scroll", function () {
    if (ticking) { return; }
    ticking = true;
    window.requestAnimationFrame(function () { onScroll(); ticking = false; });
  }, { passive: true });
  window.addEventListener("resize", onScroll);

  if (toTop) {
    toTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
      var skip = document.querySelector(".skip-link");
      if (skip) { skip.focus({ preventScroll: true }); }
    });
  }

  /* ---------------------------------------------------- wide table hints */
  function markScrollableTables() {
    document.querySelectorAll(".table-wrap").forEach(function (wrap) {
      var scroller = wrap.querySelector(".table-scroll");
      if (!scroller) { return; }
      wrap.classList.toggle("is-scrollable", scroller.scrollWidth > scroller.clientWidth + 2);
    });
  }
  window.addEventListener("resize", markScrollableTables);

  /* --------------------------------------------------------------- print */
  var printButton = document.getElementById("print-guide");

  // Every image is an inline data URI, so decoding is the only work left before
  // a figure can be painted. An image that has never been scrolled into view may
  // still be undecoded when the print pipeline snapshots the page, which would
  // silently drop the screenshot from the PDF. Force each one eager and wait for
  // its decode before handing control to window.print().
  function decodeAllImages() {
    var images = Array.prototype.slice.call(document.images);
    var pending = [];
    images.forEach(function (image) {
      if (image.loading === "lazy") { image.loading = "eager"; }
      if (image.complete && image.naturalWidth > 0) { return; }
      if (typeof image.decode === "function") {
        pending.push(image.decode().catch(function () { return null; }));
      }
    });
    return pending.length ? Promise.all(pending) : Promise.resolve();
  }

  if (printButton) {
    printButton.addEventListener("click", function () {
      decodeAllImages().then(function () { window.print(); });
    });
  }

  // Ctrl+P and the browser menu bypass the button, so the same guarantee is
  // applied from beforeprint as well. It cannot await a promise, but flipping the
  // attribute synchronously still starts the decode for anything left lazy.
  window.addEventListener("beforeprint", function () { decodeAllImages(); });

  // Printing must include collapsed Optional content; restore the reader's
  // choice afterwards so the screen view is untouched.
  var reopened = [];
  window.addEventListener("beforeprint", function () {
    reopened = [];
    document.querySelectorAll("details.optional-details").forEach(function (item) {
      if (!item.open) { reopened.push(item); item.open = true; }
    });
  });
  window.addEventListener("afterprint", function () {
    reopened.forEach(function (item) { item.open = false; });
    reopened = [];
  });

  /* ------------------------------------------------------------ shortcuts */
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      if (lightbox && !lightbox.hidden) { closeLightbox(); return; }
      if (tocPanel && tocPanel.classList.contains("is-open")) { setToc(false); return; }
      closeSearch();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (searchInput) { searchInput.focus(); searchInput.select(); }
    }
  });

  /* ----------------------------------------------------------------- boot */
  applyLang(state.lang || root.getAttribute("data-lang") || "ja", false);
  refreshProgress();
  markScrollableTables();
  onScroll();
  announce(t("status.ready"));
  root.setAttribute("data-ready", "true");
})();
