"use strict";
(() => {
  const root = document.documentElement;
  const key = "furusato-preview30-learning-v1";
  const search = document.getElementById("search");
  let language = "ja", records = {};
  try { records = JSON.parse(localStorage.getItem(key) || "{}"); } catch (_) { records = {}; }
  if (!records || typeof records !== "object" || Array.isArray(records)) records = {};
  const text = (ja,en) => language === "ja" ? ja : en;
  const save = () => { try { localStorage.setItem(key,JSON.stringify(records)); } catch (_) {} };
  const steps = [...document.querySelectorAll("input[data-step]")];
  function progress() {
    const count = steps.filter(input => input.checked).length;
    document.getElementById("progress").textContent = text(
      `${count}/${steps.length} 操作を記録。これは実環境の合格証明ではありません。`,
      `${count}/${steps.length} procedures recorded. This is not evidence of live execution passing.`);
  }
  steps.forEach(input => {
    input.checked = records[input.dataset.step] === true;
    input.addEventListener("change",() => { records[input.dataset.step] = input.checked; save(); progress(); });
  });
  function performSearch() {
    const query = search.value.trim().toLocaleLowerCase();
    let found = 0;
    document.querySelectorAll("main > .chapter").forEach(section => {
      const parts = [...section.querySelectorAll(`[data-l="${language}"],pre code:not([data-l])`)];
      const content = parts.map(element => element.textContent).join("\n").toLocaleLowerCase();
      const matches = !query || content.includes(query);
      section.hidden = !matches;
      if(matches) found++;
      if(query && matches) section.querySelectorAll("details.legacy").forEach(d => { d.open = true; });
    });
    document.getElementById("search-status").textContent = query
      ? text(`${found} 章・付録に一致`,`${found} chapters/appendices match`) : "";
  }
  function setLanguage(value) {
    language = value === "en" ? "en" : "ja";
    root.lang = root.dataset.lang = language;
    document.querySelectorAll("button[data-language]").forEach(b => b.setAttribute("aria-pressed",String(b.dataset.language === language)));
    document.querySelectorAll("[data-i18n-label]").forEach(button => {
      if(button.hasAttribute("data-copy-target")) button.setAttribute("aria-label",text("コードをコピー","Copy code"));
      if(button.hasAttribute("data-lightbox")) button.setAttribute("aria-label",text("図を拡大","Enlarge figure"));
    });
    document.querySelectorAll("[data-copy-label]").forEach(label => { label.textContent=text("コピー","Copy"); });
    document.querySelectorAll(".table-scroll").forEach(table => {
      const labels=[...table.querySelectorAll(`caption [data-l="${language}"]`)];
      table.setAttribute("aria-label",labels.map(label => label.textContent).join(" "));
    });
    progress(); performSearch();
    const url = new URL(location.href); url.searchParams.set("lang",language);
    try { history.replaceState(null,"",url); } catch (_) {}
  }
  document.querySelectorAll("[data-language]").forEach(button => button.addEventListener("click",() => setLanguage(button.dataset.language)));
  search.addEventListener("input",performSearch);
  document.getElementById("search-clear").addEventListener("click",() => { search.value=""; performSearch(); search.focus(); });
  document.getElementById("progress-reset").addEventListener("click",() => {
    records={}; steps.forEach(input => { input.checked=false; }); save(); progress();
  });
  const legacyToggle=document.getElementById("legacy-toggle");
  if(legacyToggle) legacyToggle.addEventListener("click",() => {
    const details=[...document.querySelectorAll("details.legacy")], open=details.some(d => !d.open);
    details.forEach(d => { d.open=open; });
  });
  document.querySelectorAll("a[href^='#']").forEach(link => link.addEventListener("click",() => {
    const target=document.getElementById(link.hash.slice(1));
    if(target) {
      search.value=""; performSearch();
      let node=target.parentElement;
      while(node) { if(node.tagName === "DETAILS") node.open=true; node=node.parentElement; }
    }
  }));
  document.querySelectorAll("[data-copy-target]").forEach(button => button.addEventListener("click",async () => {
    const target=document.getElementById(button.dataset.copyTarget);
    try {
      await navigator.clipboard.writeText(target.textContent);
      document.getElementById("copy-status").textContent=text("コピーしました","Copied");
    } catch (_) {
      const selection=getSelection(), range=document.createRange(); range.selectNodeContents(target);
      selection.removeAllRanges(); selection.addRange(range);
      document.getElementById("copy-status").textContent=text("テキストを選択しました。Ctrl+Cでコピーしてください。","Text selected. Press Ctrl+C to copy.");
    }
  }));
  const dialog=document.getElementById("lightbox"), dialogContent=document.getElementById("lightbox-content");
  document.querySelectorAll("[data-lightbox]").forEach(button => button.addEventListener("click",() => {
    dialogContent.replaceChildren();
    const clone=button.cloneNode(true); clone.removeAttribute("data-lightbox"); clone.removeAttribute("type");
    const renamed=new Map([...clone.querySelectorAll("[id]")].map(e => [e.id,"zoom-"+e.id]));
    clone.querySelectorAll("*").forEach(element => {
      [...element.attributes].forEach(attribute => {
        let value=attribute.value;
        if(attribute.name === "id") value=renamed.get(value) || value;
        else if(attribute.name.startsWith("aria-")) value=value.split(" ").map(id => renamed.get(id) || id).join(" ");
        else renamed.forEach((replacement,id) => { value=value.split("#"+id).join("#"+replacement); });
        element.setAttribute(attribute.name,value);
      });
    });
    while(clone.firstChild) dialogContent.append(clone.firstChild);
    dialog.showModal();
  }));
  document.getElementById("lightbox-close").addEventListener("click",() => dialog.close());
  let printState=[];
  window.addEventListener("beforeprint",() => {
    printState=[...document.querySelectorAll("details")].map(d => [d,d.open]);
    printState.forEach(([d]) => { d.open=true; });
    document.querySelectorAll("main > .chapter").forEach(s => { s.hidden=false; });
  });
  window.addEventListener("afterprint",() => { printState.forEach(([d,open]) => {d.open=open;}); performSearch(); });
  document.getElementById("print").addEventListener("click",() => window.print());
  setLanguage(new URL(location.href).searchParams.get("lang") || "ja");
  root.dataset.ready="true";
})();
