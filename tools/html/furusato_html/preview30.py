"""Accessible, offline bilingual renderer for the complete shared v3 course."""

from __future__ import annotations

import html
import hashlib
import json

from furusato_docs.preview30_content import HTML_NAME, VERSION, WORD_NAME
from furusato_docs import preview30_release as release
from .assets import build_library, encode_screenshot, screenshot_size
from .mirror import load_ui_strings
from .model import Text
from .render import RenderContext, esc, plain_bilingual, render_block


# Keep the two final MCP references with the preceding content, not on a URL-only page.
RELEASE_PRINT_CSS = """
@media print {
 html[data-lang="en"] #ch-20-10 > .callout:last-of-type { margin-bottom:2mm; }
 html[data-lang="en"] #ch-20-10 > p:nth-last-child(-n+2) { margin-block:0; }
}
"""


def register_reviewed_captures(assets, captures):
    canonical_captures = {}
    capture_aliases = {}
    for ident, entry in captures.items():
        blob = entry["path"].read_bytes()
        if hashlib.sha256(blob).hexdigest() != entry["sha256"]:
            raise ValueError("Reviewed capture changed before HTML rendering: " + ident)
        canonical = canonical_captures.get(entry["sha256"])
        if canonical is None:
            assets.register_digest("reviewed-capture:" + ident, blob)
            assets.screenshots[ident] = encode_screenshot(blob)
            assets.screenshot_sizes[ident] = screenshot_size(blob)
            canonical_captures[entry["sha256"]] = ident
        else:
            capture_aliases[ident] = canonical
            assets.screenshots[ident] = assets.screenshots[canonical]
            assets.screenshot_sizes[ident] = assets.screenshot_sizes[canonical]
    return capture_aliases


def render(
    document, context, facts, carrier, evidence, metadata, word_sha, root, *,
    release_profile=release.PREVIEW,
):
    profile = release.require_metadata_profile(metadata, release_profile)
    diagram_keys = sorted({b["source_key"] for b in document.figures if b["source_kind"] == "diagram"})
    assets = build_library(context, carrier, diagram_keys, [])
    capture_aliases = register_reviewed_captures(assets, evidence["captures"])
    ctx = RenderContext(
        ui=load_ui_strings(public_documents_only=True, context=context), assets=assets,
        version=profile.version, fingerprint=metadata["contentSha256"][:16], runtime_fingerprint="",
        facts=facts, context=context, stats={},
    )
    counter = {"code": 0}

    def block_markup(block):
        if block.kind == "prompt":
            counter["code"] += 1
            index = counter["code"]
            pieces = []
            for lang in ("ja", "en"):
                ident = f"prompt-{index}-{lang}"
                pieces.append(
                    f'<div class="codeblock" data-l="{lang}" lang="{lang}">'
                    f'<button type="button" data-copy-target="{ident}">{"コピー" if lang == "ja" else "Copy"}</button>'
                    f'<pre><code id="{ident}">{esc(block["text"].get(lang))}</code></pre></div>'
                )
            return "".join(pieces)
        return render_block(block, ctx, counter)

    def section_markup(section):
        heading = "h" + str(min(6, section.level + 1))
        content = "".join(block_markup(block) for block in section.blocks)
        children = "".join(section_markup(child) for child in section.children)
        text = plain_bilingual(section.title)
        if "-legacy-" in section.ident and section.level == 2:
            return (
                f'<details class="legacy" id="{section.ident}"><summary>{text}</summary>'
                f'<div class="legacy-body">{content}{children}</div></details>'
            )
        check = ""
        if section.checklist_id:
            check = (
                '<label class="step-check"><input type="checkbox" '
                f'data-step="{section.checklist_id}"> '
                + plain_bilingual(Text("実施記録済み (合格判定とは別)", "Recorded (not a pass judgment)")) + "</label>"
            )
        return (
            f'<section id="{section.ident}" class="{"chapter" if section.level == 1 else "section"}" '
            f'data-section-id="{section.ident}">'
            f'<{heading}>{text}</{heading}>{check}{content}{children}</section>'
        )

    toc = "".join(f'<li><a href="#{s.ident}">{plain_bilingual(s.title)}</a></li>' for s in document.sections)
    content = "".join(section_markup(s) for s in document.sections)
    notice = release.presentation(metadata, profile)
    state = Text(notice["ja"], notice["en"])
    public_metadata = {
        **metadata, "wordFilename": profile.word_name, "wordSha256": word_sha,
        "htmlFilename": profile.html_name,
        "captureDigests": {ident: entry["sha256"] for ident, entry in evidence["captures"].items()},
        "captureResourceAliases": capture_aliases,
        "languages": ["ja", "en"],
    }
    encoded_metadata = json.dumps(public_metadata, ensure_ascii=False).replace("<", "\\u003c")
    css = (root / "tools" / "html" / "assets" / "preview30.css").read_text(encoding="utf-8")
    if profile.is_release:
        css += RELEASE_PRINT_CSS
    js = (root / "tools" / "html" / "assets" / "preview30.js").read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="ja" data-lang="ja">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Complete 24-chapter bilingual {profile.title}; honest per-lab evidence status.">
<title>{profile.title}</title><style>{css}</style></head>
<body>
<a class="skip-link" href="#main">{plain_bilingual(Text("本文へ", "Skip to content"))}</a>
<header>
 <a href="#top" class="brand">Furusato / Fabric IQ · {profile.display_version}</a>
 <nav aria-label="Language"><button type="button" data-language="ja" aria-pressed="true">日本語</button>
 <button type="button" data-language="en" aria-pressed="false">English</button></nav>
 <button type="button" id="print">{plain_bilingual(Text("印刷", "Print"))}</button>
</header>
<div id="top" class="hero"><p class="eyebrow">MICROSOFT FABRIC · SYNTHETIC HANDS-ON WORKSHOP</p>
 <h1>Furusato Workshop<br>{profile.display_version}</h1>
 <p>{plain_bilingual(Text("24章・5付録／Wordと同じ共有原稿／全19章の旧教材も保持", "24 chapters · 5 appendices · shared Word source · complete 19-chapter baseline retained"))}</p>
 <p class="status" role="status">{plain_bilingual(state)}</p>
 <p><a download href="{profile.word_name}" id="word-download">{plain_bilingual(Text("対応するWordをダウンロード", "Download the matching Word guide"))}</a></p>
 <p class="digest">Word SHA-256: <code>{word_sha}</code></p>
</div>
<aside class="controls"><label for="search">{plain_bilingual(Text("この言語の全文を検索", "Search the full text in this language"))}</label>
 <input id="search" type="search" autocomplete="off"><button type="button" id="search-clear">{plain_bilingual(Text("検索解除", "Clear search"))}</button>
 <p id="search-status" role="status" aria-live="polite"></p>
 <button type="button" id="legacy-toggle">{plain_bilingual(Text("旧版参考をすべて開閉", "Toggle all baseline references"))}</button>
 <button type="button" id="progress-reset">{plain_bilingual(Text("学習記録をリセット", "Reset learning progress"))}</button>
 <p id="progress" role="status"></p>
</aside>
<nav class="toc" aria-label="Contents"><h2>{plain_bilingual(Text("目次", "Contents"))}</h2><ol>{toc}</ol></nav>
<main id="main">{content}</main>
<footer><p>{plain_bilingual(Text("Microsoft Learn確認日: 2026-09-29。Previewは段階展開。未実施を合格にしません。", "Microsoft Learn reviewed: 2026-09-29. Preview is rolling out. Unperformed is not passed."))}</p>
 <p>Furusato Fabric Workshop · Content SHA-256: <code>{metadata["contentSha256"]}</code></p></footer>
<dialog id="lightbox" aria-label="Figure"><button id="lightbox-close" type="button">{plain_bilingual(Text("閉じる", "Close"))}</button><div id="lightbox-content"></div></dialog>
<p class="sr-only" id="copy-status" aria-live="polite"></p>
<script type="application/json" id="preview30-provenance">{encoded_metadata}</script>
<script>{js}</script>
</body></html>
"""
