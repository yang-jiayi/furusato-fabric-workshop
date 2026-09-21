"""Assemble the complete single-file HTML page around the rendered document."""

from __future__ import annotations

import json
from typing import Any

from furusato_docs.typography import ascii_parentheses
from furusato_docs.context import UNIFIED_DOCUMENT_EDITION

from .model import Document, Section, Text
from .render import ICONS, RenderContext, esc, plain_bilingual, render_section, render_toc


def _head(ctx: RenderContext) -> str:
    description = ctx.ui["meta.description"]["ja"] + " / " + ctx.ui["meta.description"]["en"]
    title = ctx.ui["app.title"]["ja"]
    publication = (
        '<meta name="publication-mode" content="public-documents-only">'
        if ctx.stats.get("public_documents_only") else ""
    )
    return (
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        '<meta name="color-scheme" content="light">'
        f'<meta name="description" content="{esc(description)}">'
        f'<meta name="generator" content="tools/html/build_html.py {esc(ctx.fingerprint)}">'
        f'<meta name="dcterms.rightsHolder" content="Microsoft">'
        f'<meta name="classification" content="General">'
        f"{publication}"
        f"<title>{esc(title)} — v{esc(ctx.version)}</title>"
        f"<style>{ctx.stats['css']}</style>"
        "</head>"
    )


def _header(ctx: RenderContext) -> str:
    return (
        '<header class="app-header no-print" role="banner">'
        '<div class="spectrum" aria-hidden="true"><i></i><i></i><i></i></div>'
        '<div class="app-bar">'
        '<div class="brand">'
        f'<span class="brand__mark"><img src="{ctx.assets.logo}" alt="Microsoft Fabric IQ" width="40" height="40"></span>'
        '<span class="brand__text">'
        f'<strong>{plain_bilingual(ctx.ui_text("app.title"))}</strong>'
        f'<span id="current-section" data-current-section></span>'
        "</span></div>"
        '<div class="app-bar__center">'
        f'<button type="button" class="pill nav-toggle" id="toc-toggle" aria-expanded="false" '
        f'aria-controls="toc" data-i18n-label="nav.toggle.open" '
        f'aria-label="{esc(ctx.ui["nav.toggle.open"]["ja"])}">{ICONS["menu"]}</button>'
        '<div class="search" role="search">'
        f'{ICONS["search"]}'
        f'<input id="search-input" class="search__input" type="search" autocomplete="off" '
        f'role="combobox" aria-expanded="false" aria-controls="search-results" aria-autocomplete="list" '
        f'data-i18n-label="search.label" aria-label="{esc(ctx.ui["search.label"]["ja"])}" '
        f'data-i18n-placeholder="search.placeholder" placeholder="{esc(ctx.ui["search.placeholder"]["ja"])}">'
        f'<button type="button" class="search__clear" id="search-clear" data-i18n-label="search.clear" '
        f'aria-label="{esc(ctx.ui["search.clear"]["ja"])}">✕</button>'
        '<div class="search__panel" id="search-panel" hidden>'
        '<div class="search__meta">'
        f'<span id="search-count" aria-live="polite"></span>'
        f'<span>{plain_bilingual(ctx.ui_text("search.hint"))}</span>'
        "</div>"
        '<ul class="search__list" id="search-results" role="listbox" '
        f'aria-label="{esc(ctx.ui["search.results"]["ja"])}" data-i18n-label="search.results"></ul>'
        "</div></div></div>"
        '<div class="app-actions">'
        f'<span class="progress-chip" id="progress-chip" role="meter" aria-valuemin="0" aria-valuenow="0" '
        f'data-i18n-label="checklist.summary" aria-label="{esc(ctx.ui["checklist.summary"]["ja"])}">'
        f'<span class="progress-chip__track" aria-hidden="true"><span class="progress-chip__fill" id="progress-fill"></span></span>'
        '<span id="progress-text">0 / 0 (0%)</span></span>'
        f'<div class="lang-switch" role="group" data-i18n-label="lang.label" '
        f'aria-label="{esc(ctx.ui["lang.label"]["ja"])}">'
        '<button type="button" class="lang-switch__btn" data-set-lang="ja" aria-pressed="true" lang="ja">日本語</button>'
        '<button type="button" class="lang-switch__btn" data-set-lang="en" aria-pressed="false" lang="en">English</button>'
        "</div>"
        f'<button type="button" class="pill" id="print-guide" data-i18n-label="print.aria" '
        f'aria-label="{esc(ctx.ui["print.aria"]["ja"])}">{ICONS["print"]}'
        f'<span data-i18n="print.label">{esc(ctx.ui["print.label"]["ja"])}</span></button>'
        "</div></div></header>"
    )


def _cover(ctx: RenderContext, document: Document) -> str:
    stats = ctx.stats
    cards = [
        (stats["entity_types"], "entities"),
        (stats["relationship_types"], "relationships"),
        (stats["metadata_objects"], "metadata"),
        (stats["tests"], "tests"),
    ]
    stat_labels = {
        "entities": Text("Entity Type", "Entity Types"),
        "relationships": Text("Relationship Type", "Relationship Types"),
        "metadata": Text("Notebook 02 メタデータ", "Notebook 02 metadata objects"),
        "tests": Text("held-out テスト", "held-out tests"),
    }
    stat_html = "".join(
        f'<div class="stat"><b>{value}</b>{plain_bilingual(stat_labels[key])}</div>'
        for value, key in cards
    )
    download_items = [("cover.download.guide", stats["download_guide"])]
    if not stats.get("public_documents_only"):
        download_items.extend((
            ("cover.download.tests", stats["download_tests"]),
            ("cover.download.workbook", stats["download_workbook"]),
        ))
    downloads = "".join(
        f'<a class="pill" href="{esc(href)}" download>{plain_bilingual(ctx.ui_text(key))}</a>'
        for key, href in download_items
    )
    edition = (
        f'<span class="badge">{plain_bilingual(Text("文書版", "Document edition"))}: '
        f'{esc(stats["edition"])}</span>'
        if stats.get("edition")
        else ""
    )
    core_badge = (
        Text("1 Agent・3 ソース・CI", "1 Agent, 3 sources, CI")
        if stats.get("edition") == UNIFIED_DOCUMENT_EDITION
        else Text("Core: Notebook 01 / 02", "Core: Notebook 01 / 02")
    )
    return (
        '<section class="cover" id="cover" aria-labelledby="cover-title">'
        f'<p class="cover__kicker">{plain_bilingual(ctx.ui_text("app.brand"))}</p>'
        f'<h1 id="cover-title">{plain_bilingual(ctx.ui_text("app.title"))}</h1>'
        f'<p class="cover__sub">{plain_bilingual(ctx.ui_text("cover.tagline"))}</p>'
        '<p class="cover__badges">'
        f'<span class="badge badge--solid">v{esc(ctx.version)}</span>'
        f'<span class="badge">{plain_bilingual(Text(f"データセット契約 {stats['dataset_version']}", f"Dataset contract {stats['dataset_version']}"))}</span>'
        f'<span class="badge">{plain_bilingual(ctx.ui_text("cover.classification"))}</span>'
        f'<span class="badge">{plain_bilingual(core_badge)}</span>'
        f"{edition}"
        "</p>"
        f'<div class="cover__grid">{stat_html}</div>'
        f'<p class="cover__kicker no-print">{plain_bilingual(ctx.ui_text("cover.downloads"))}</p>'
        f'<div class="downloads no-print">{downloads}'
        f'<p class="downloads__note">{plain_bilingual(ctx.ui_text("cover.download.note"))}</p></div>'
        "</section>"
    )


def _howto(ctx: RenderContext) -> str:
    items = [
        "howto.item.lang",
        "howto.item.search",
        "howto.item.checklist",
        "howto.item.figures",
        "howto.item.copy",
        "howto.item.print",
    ]
    list_html = "".join(f"<li>{plain_bilingual(ctx.ui_text(key))}</li>" for key in items)
    return (
        '<section class="panel" id="how-to-use" aria-labelledby="how-to-use-title" data-section-id="how-to-use">'
        f'<h2 id="how-to-use-title" data-section-title>{plain_bilingual(ctx.ui_text("howto.title"))}</h2>'
        f'<p class="lead" data-search-block>{plain_bilingual(ctx.ui_text("howto.lead"))}</p>'
        f'<ul class="panel__list" data-search-block>{list_html}</ul>'
        f'<h3>{plain_bilingual(ctx.ui_text("howto.scope.title"))}</h3>'
        f'<ul class="panel__list" data-search-block>'
        f'<li>{plain_bilingual(ctx.ui_text("howto.scope.core"))}</li>'
        f'<li>{plain_bilingual(ctx.ui_text("howto.scope.optional"))}</li>'
        "</ul>"
        '<p class="chip-row no-print">'
        f'<button type="button" class="pill" id="expand-all" aria-expanded="false">'
        f'<span data-expand-label data-i18n="details.expand">'
        f'{esc(ctx.ui["details.expand"]["ja"])}</span></button>'
        f'<button type="button" class="pill" id="reset-progress" data-i18n-label="checklist.reset" '
        f'aria-label="{esc(ctx.ui["checklist.reset"]["ja"])}">'
        f'<span>{plain_bilingual(ctx.ui_text("checklist.reset"))}</span></button>'
        f'<span class="badge">{plain_bilingual(ctx.ui_text("checklist.saved"))}</span>'
        "</p>"
        "</section>"
    )


def _contents_panel(ctx: RenderContext, document: Document) -> str:
    rows: list[str] = []
    for section in document.sections:
        subs = [child for child in section.children if child.level == 2]
        sub_text = " · ".join(child.number for child in subs) if subs else "—"
        rows.append(
            "<tr>"
            f'<th scope="row"><a href="#{section.ident}">{esc(section.number)}</a></th>'
            f"<td>{plain_bilingual(section.title_without_number())}</td>"
            f"<td>{esc(sub_text)}</td>"
            "</tr>"
        )
    headers = [
        Text("番号", "No."),
        Text("章 / 付録", "Chapter / appendix"),
        Text("節", "Sections"),
    ]
    head = "".join(f'<th scope="col">{plain_bilingual(header)}</th>' for header in headers)
    caption = Text(
        f"全 {len(document.sections)} 章・付録の一覧（Word 版と同じ番号）",
        f"All {len(document.sections)} chapters and appendices (same numbering as the Word edition)",
    )
    return (
        '<section class="panel" id="contents" aria-labelledby="contents-title" data-section-id="contents">'
        f'<h2 id="contents-title" data-section-title>{plain_bilingual(ctx.ui_text("toc.title"))}</h2>'
        f'<p data-search-block>{plain_bilingual(ctx.ui_text("toc.lead"))}</p>'
        '<div class="table-wrap"><div class="table-scroll" tabindex="0" role="region" '
        f'aria-label="{esc(caption.ja)}"><table>'
        f"<caption>{plain_bilingual(caption)}</caption>"
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>"
        "</section>"
    )


def _office_line(name: str, entry) -> str:
    """One provenance line per Office deliverable.

    ``entry`` is either a bare digest or a ``{release, observed}`` pair. They differ
    only for a layout-only reissue, where the DOCX was repaginated without changing
    text, tables or runtime; both digests are then shown so nothing is concealed.
    """
    if isinstance(entry, str):
        release = observed = entry
    else:
        release = entry.get("release", "")
        observed = entry.get("observed", release)
    line = (
        f'<p class="fingerprint" data-office-source="{esc(name)}"'
        f' data-office-release="{esc(release)}"'
        f' data-office-observed="{esc(observed)}">'
        f"{esc(name)} · sha256 {esc(release)}"
    )
    if observed and observed != release:
        line += (
            f'<span class="fingerprint__note"> · '
            f"<span data-l=\"ja\" lang=\"ja\">レイアウトのみの再発行。ビルド時にディスク上にあったのは "
            f"sha256 {esc(observed[:16])}… で、本文・表・ランタイムは同一です。</span>"
            f"<span data-l=\"en\" lang=\"en\">Layout-only reissue. The copy on disk at build time was "
            f"sha256 {esc(observed[:16])}…; text, tables and runtime are identical.</span></span>"
        )
    return line + "</p>"


def _footer(ctx: RenderContext) -> str:
    office = ctx.stats.get("office") or {}
    office_lines = "".join(_office_line(name, entry) for name, entry in sorted(office.items()))
    return (
        '<footer class="app-footer" role="contentinfo">'
        '<div class="app-footer__inner">'
        f'<p><strong>{plain_bilingual(ctx.ui_text("footer.version"))}</strong></p>'
        f'<p>{plain_bilingual(ctx.ui_text("footer.classification"))}</p>'
        f'<p>{plain_bilingual(ctx.ui_text("footer.synthetic"))}</p>'
        f'<p>{plain_bilingual(ctx.ui_text("footer.legal"))}</p>'
        f'<p class="fingerprint">{plain_bilingual(ctx.ui_text("footer.fingerprint"))}: {esc(ctx.fingerprint)}</p>'
        f'<p class="fingerprint">{plain_bilingual(ctx.ui_text("footer.runtime"))}: {esc(ctx.runtime_fingerprint)}</p>'
        f'<p class="fingerprint">{plain_bilingual(ctx.ui_text("footer.source"))}: tools/html/build_html.py · '
        f'workshop/v{esc(ctx.version)}</p>'
        f'<p>{plain_bilingual(ctx.ui_text("footer.mirrored"))}</p>'
        f"{office_lines}"
        "</div></footer>"
    )


def _lightbox(ctx: RenderContext) -> str:
    return (
        '<div class="lightbox no-print" id="lightbox" role="dialog" aria-modal="true" '
        f'aria-labelledby="lightbox-title" hidden>'
        '<div class="lightbox__bar">'
        '<span class="lightbox__title" id="lightbox-title"></span>'
        f'<span class="lightbox__hint">{plain_bilingual(ctx.ui_text("lightbox.hint"))}</span>'
        f'<button type="button" class="lightbox__close" id="lightbox-close">'
        f'{plain_bilingual(ctx.ui_text("lightbox.close"))}</button>'
        "</div>"
        '<div class="lightbox__stage" id="lightbox-stage"></div>'
        "</div>"
    )


def render_page(document: Document, ctx: RenderContext) -> str:
    counter = {"code": 0}
    body_sections = "".join(render_section(section, ctx, counter) for section in document.sections)
    section_titles = [
        {"id": section.ident, "ja": ascii_parentheses(section.title.ja), "en": ascii_parentheses(section.title.en)}
        for section in document.sections
    ]
    display_ui = {
        key: {language: ascii_parentheses(value) for language, value in entry.items()}
        for key, entry in ctx.ui.items()
    }
    strings_json = json.dumps(display_ui, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    sections_json = json.dumps(section_titles, ensure_ascii=False, separators=(",", ":"))
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ja" data-lang="ja">'
        + _head(ctx)
        + "<body>"
        f'<a class="skip-link" href="#main">{plain_bilingual(ctx.ui_text("app.skip"))}</a>'
        f'<div class="reading-progress no-print" role="presentation">'
        f'<span class="reading-progress__value" id="reading-progress-value"></span></div>'
        + _header(ctx)
        + '<div class="toc-backdrop no-print" id="toc-backdrop" hidden></div>'
        '<div class="layout">'
        f'<nav class="toc no-print" id="toc" data-i18n-label="nav.label" '
        f'aria-label="{esc(ctx.ui["nav.label"]["ja"])}">'
        f'<p class="toc__title">{plain_bilingual(ctx.ui_text("nav.label"))}</p>'
        f'<p class="toc__hint">{plain_bilingual(ctx.ui_text("toc.lead"))}</p>'
        + render_toc(document, ctx)
        + "</nav>"
        '<main class="content" id="main" tabindex="-1">'
        + _cover(ctx, document)
        + _howto(ctx)
        + _contents_panel(ctx, document)
        + f"<article>{body_sections}</article>"
        + "</main></div>"
        + _footer(ctx)
        + f'<button type="button" class="to-top no-print" id="to-top" data-i18n-label="top.label" '
        f'data-i18n-title="top.label" title="{esc(ctx.ui["top.label"]["ja"])}" '
        f'aria-label="{esc(ctx.ui["top.label"]["ja"])}">{ICONS["top"]}'
        f'<span data-i18n="top.label">{esc(ctx.ui["top.label"]["ja"])}</span></button>'
        + _lightbox(ctx)
        + '<div id="live-status" class="sr-only" role="status" aria-live="polite" aria-atomic="true"></div>'
        + f"<script>window.__FURUSATO_STRINGS__={strings_json};"
        f"window.__FURUSATO_SECTIONS__={sections_json};</script>"
        + f"<script>{ctx.stats['js']}</script>"
        + "</body></html>\n"
    )
