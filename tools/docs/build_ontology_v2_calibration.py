"""Build standalone bilingual calibration Word/HTML from one public Markdown source.

This procedure renderer neither reads nor invents evaluation results. Relative
links resolve under the explicitly declared public source path, never a private
staging path. Rendering performs no network or cloud operations.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import urlparse
import zipfile

from build_ontology_v2_report import public_text, private_output, canonical

REPO = next((p for p in Path(__file__).resolve().parents
             if (p / 'WORKSHOP_VERSION').is_file() and (p / 'tools/docs').is_dir()), Path.cwd())
SCHEMA = 'furusato-ontology-v2-calibration-artifacts/v1'
DEFAULT_PUBLIC_SOURCE = 'docs/v3.0.0/tuning-20261015/calibration-and-proofreading.md'


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def link_target(target, public_source):
    """Only reviewed public repository links and ordinary HTTPS links are allowed."""
    parsed = urlparse(target)
    if parsed.scheme:
        if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError('Only public HTTPS links are supported.')
        # The report prose guard rejects Windows-drive-like substrings, including
        # the final "s:/" in https://. Validate the scheme explicitly here, then
        # apply its identity/token/private-path checks to the remaining URL.
        public_text(target[len('https://'):])
        return target
    if target.startswith(('/', '\\', '//')) or '\\' in target or parsed.netloc or parsed.query:
        raise ValueError('A public relative repository path is required.')
    parts = list(PurePosixPath(public_source).parent.parts)
    for part in PurePosixPath(parsed.path).parts:
        if part == '..':
            if not parts:
                raise ValueError('A link escapes the public repository.')
            parts.pop()
        elif part != '.':
            parts.append(part)
    return 'https://github.com/yang-jiayi/furusato-fabric-workshop/blob/main/' + '/'.join(parts) + ('#' + parsed.fragment if parsed.fragment else '')


def prepare(source, public_source, repo):
    source = Path(source).resolve()
    relative = PurePosixPath(public_source)
    if relative.is_absolute() or '..' in relative.parts or not public_source.startswith('docs/') or relative.suffix != '.md':
        raise ValueError('Public source must be a repository-relative Markdown path under docs/.')
    raw = source.read_bytes()
    text = raw.decode('utf-8')
    public_text(text)
    # The aggregate guard serializes input as JSON; scanning individual source
    # lines also preserves identifier word boundaries after literal newlines.
    for line in text.splitlines():
        public_text(line)
    if re.search(r'PRIVATE DRAFT|NOT PUBLISHABLE|FINAL AGGREGATES REQUIRED|FINAL CAPABILITY VERDICTS REQUIRED', text):
        raise ValueError('An unfinished private draft cannot become a public procedure.')
    sys.path.insert(0, str(Path(repo) / 'tools/docs'))
    import build_measured_tuning_report as markdown
    blocks = markdown.parse(text)
    if not blocks or blocks[0]['kind'] != 'heading' or blocks[0]['level'] != 1:
        raise ValueError('A shared bilingual Markdown title is required.')
    if not re.search(r'[\u3040-\u30ff\u3400-\u9fff]', text) or 'Calibration and proofreading' not in text:
        raise ValueError('Japanese and English procedure content are required.')
    links = {}
    for block in blocks:
        cells = [*block['headers'], *(cell for row in block['rows'] for cell in row)] if block['kind'] == 'table' else [block['text']]
        for cell in cells:
            for kind, label, target in markdown.tokens(cell):
                if kind == 'link':
                    links[target] = link_target(target, public_source)
        if block['kind'] == 'table':
            width = len(block['headers'])
            if width not in (2, 4) or any(len(row) != width for row in block['rows']):
                raise ValueError('Procedure tables must preserve two or four columns.')
    return raw, blocks, links, markdown


def build(source, output, *, report_date, source_date_epoch, public_source=DEFAULT_PUBLIC_SOURCE, repo=REPO):
    repo = Path(repo).resolve()
    if date.fromisoformat(report_date).isoformat() != report_date or type(source_date_epoch) is not int or source_date_epoch < 315532800:
        raise ValueError('An exact date and reproducible artifact epoch are required.')
    raw, blocks, links, markdown = prepare(source, public_source, repo)
    output = private_output(output, repo)
    from furusato_docs.docx_kit import DocumentBuilder
    from furusato_docs.oox import StyleCarrier, apply_japanese_typography, normalise_package_metadata
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt
    from lxml import etree, html as lhtml

    output.mkdir(parents=True, mode=0o700)
    os.chmod(output, 0o700)
    word, web = (output / ('calibration-and-proofreading.' + suffix) for suffix in ('docx', 'html'))
    source_sha = digest(raw)
    shared_sha = digest(json.dumps(blocks, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
    prior_epoch = os.environ.get('SOURCE_DATE_EPOCH')
    os.environ['SOURCE_DATE_EPOCH'] = str(source_date_epoch)
    try:
        builder = DocumentBuilder(StyleCarrier.resolve(repo), output / 'shell.docx')
        doc = builder.document
        for section in doc.sections:
            for part in (section.header, section.footer, section.first_page_header, section.first_page_footer):
                for node in list(part._element):
                    part._element.remove(node)
                part._element.append(OxmlElement('w:p'))
        for node in list(doc.settings.element.findall(qn('w:updateFields'))):
            doc.settings.element.remove(node)
        for block in blocks:
            kind = block['kind']
            if kind == 'heading':
                if block['level'] == 1:
                    builder.paragraph(markdown.plain(block['text']), style='Title')
                    builder.paragraph(report_date + ' · Furusato Workshop 3.0.0 · Procedure', size=10)
                else:
                    builder.heading(markdown.plain(block['text']), min(block['level'] - 1, 3), new_page=False)
            elif kind == 'table':
                widths = [2.6, 7.0] if len(block['headers']) == 2 else [2.6, 1.7, 1.7, 3.6]
                builder.table([markdown.plain(x) for x in block['headers']], [[markdown.plain(x) for x in row] for row in block['rows']],
                              caption='校正手順 / Calibration procedure', widths=widths, font_size=8.5, header_size=8.5)
            elif kind == 'code':
                builder.code_block(block['text'], language=block['language'], keep_together=True)
            else:
                paragraph = builder.paragraph(space_after=7)
                for token_kind, text, target in markdown.tokens(block.get('prefix', '') + block['text']):
                    if token_kind == 'link':
                        rid = paragraph.part.relate_to(links[target], RT.HYPERLINK, is_external=True)
                        link = OxmlElement('w:hyperlink'); link.set(qn('r:id'), rid)
                        run = OxmlElement('w:r'); pr = OxmlElement('w:rPr')
                        style = OxmlElement('w:rStyle'); style.set(qn('w:val'), 'Hyperlink'); pr.append(style); run.append(pr)
                        node = OxmlElement('w:t'); node.text = text; run.append(node); link.append(run); paragraph._p.append(link)
                    else:
                        run = paragraph.add_run(text); run.bold = token_kind == 'bold'; run.font.size = Pt(10)
        builder.paragraph('Source Markdown SHA-256: ' + source_sha, size=8)
        builder.paragraph('Shared content SHA-256: ' + shared_sha, size=8)
        doc.core_properties.title = 'Furusato Workshop — Calibration and proofreading — ' + report_date
        doc.core_properties.subject = 'Reusable procedure; actual evaluation results remain in the separate dated report'
        for style in doc.styles:
            if hasattr(style, 'font'):
                style.font.name = 'Noto Sans CJK JP'
                props = style.element.get_or_add_rPr()
                fonts = props.find(qn('w:rFonts'))
                if fonts is None:
                    fonts = OxmlElement('w:rFonts'); props.append(fonts)
                for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
                    fonts.set(qn(attr), 'Noto Sans CJK JP')
        for run in doc.element.iter(qn('w:r')):
            props = run.find(qn('w:rPr'))
            if props is None:
                props = OxmlElement('w:rPr'); run.insert(0, props)
            fonts = props.find(qn('w:rFonts'))
            if fonts is None:
                fonts = OxmlElement('w:rFonts'); props.append(fonts)
            for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
                fonts.set(qn(attr), 'Noto Sans CJK JP')
        builder.save(word); apply_japanese_typography(word); normalise_package_metadata(word)
    finally:
        if prior_epoch is None:
            os.environ.pop('SOURCE_DATE_EPOCH', None)
        else:
            os.environ['SOURCE_DATE_EPOCH'] = prior_epoch

    with zipfile.ZipFile(word) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    if any(b'fldChar' in blob or b'instrText' in blob for name, blob in parts.items() if name.startswith('word/') and name.endswith('.xml')):
        raise ValueError('Dynamic Word fields are not permitted.')
    if re.search(rb'<(?:\w+:)?Pages\b', parts['docProps/app.xml']) or b'General' not in parts['docProps/custom.xml']:
        raise ValueError('Office page-count or classification boundary changed.')
    word_text = ''.join(etree.fromstring(parts['word/document.xml']).xpath('//w:t/text()', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}))
    word_sha = digest(word.read_bytes())
    body, toc = [], []
    def inline(text):
        result = []
        for kind, value, target in markdown.tokens(text):
            escaped = html.escape(value)
            result.append('<a href="' + html.escape(links[target], quote=True) + '">' + escaped + '</a>' if kind == 'link' else '<strong>' + escaped + '</strong>' if kind == 'bold' else '<code>' + escaped + '</code>' if kind == 'code' else escaped)
        return ''.join(result)
    for block in blocks:
        kind = block['kind']
        if kind == 'heading':
            anchor = 'section-' + str(len(toc) + 1)
            level = min(block['level'], 4)
            body.append(f'<h{level} id="{anchor}">' + inline(block['text']) + f'</h{level}>')
            toc.append('<a href="#' + anchor + '">' + html.escape(markdown.plain(block['text'])) + '</a>')
        elif kind == 'table':
            body.append('<div class="table-wrap"><table><thead><tr>' + ''.join('<th scope="col">' + inline(x) + '</th>' for x in block['headers']) + '</tr></thead><tbody>')
            body.extend('<tr>' + ''.join('<td>' + inline(x) + '</td>' for x in row) + '</tr>' for row in block['rows'])
            body.append('</tbody></table></div>')
        elif kind == 'code':
            body.append('<pre><code>' + html.escape(block['text']) + '</code></pre>')
        else:
            language = 'ja' if re.search(r'[\u3040-\u30ff\u3400-\u9fff]', block['text']) else 'en'
            body.append('<p lang="' + language + '">' + inline(block.get('prefix', '') + block['text']) + '</p>')
    css = ":root{font-family:'Noto Sans CJK JP',sans-serif;line-height:1.75;color:#203048;background:#eef3f9}*{box-sizing:border-box}body{max-width:1100px;margin:auto;padding:24px}main,nav,header{background:white;padding:28px;margin-bottom:20px;border-radius:10px}h1{font-size:1.8rem}h2{font-size:1.35rem;color:#174c88;margin-top:32px}nav{display:grid;gap:6px}p,td,code{overflow-wrap:anywhere}a{color:#175c9b}.table-wrap{overflow-x:auto}table{width:100%;min-width:640px;border-collapse:collapse;font-size:.85rem}th,td{border:1px solid #d6dfea;padding:9px;text-align:left;vertical-align:top}th{background:#174c88;color:white}tr:nth-child(even){background:#eef3f9}footer{font-size:.75rem;overflow-wrap:anywhere}button{font:inherit;padding:8px 12px;background:#174c88;color:white;border:0;border-radius:5px}@media(max-width:600px){body{padding:10px}main,nav,header{padding:16px}}@media print{@page{size:A4;margin:16mm}body{padding:0;background:white;max-width:none}nav,button{display:none}header,main{padding:0;margin:0}h1,h2{break-after:avoid}tr{break-inside:avoid}table{min-width:0;font-size:8pt}.table-wrap{overflow:visible}th,td{padding:5px}}"
    document = '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>校正・資料整合の手順 / Calibration and proofreading</title><link rel="icon" href="data:,"><meta name="source-markdown-sha256" content="' + source_sha + '"><meta name="shared-content-sha256" content="' + shared_sha + '"><meta name="paired-word-sha256" content="' + word_sha + '"><style>' + css + '</style></head><body><header><p>' + report_date + ' · Furusato Workshop 3.0.0 · Procedure</p><button onclick="window.print()">印刷 / Print</button></header><nav aria-label="目次 / Contents">' + ''.join(toc) + '</nav><main>' + ''.join(body) + '</main><footer>Source Markdown SHA-256: ' + source_sha + '<br>Shared content SHA-256: ' + shared_sha + '<br>Paired Word SHA-256: ' + word_sha + '</footer></body></html>'
    web.write_text(document, encoding='utf-8')
    html_text = ''.join(lhtml.fromstring(document).xpath('//main//text()'))
    for block in blocks:
        values = [*block['headers'], *(cell for row in block['rows'] for cell in row)] if block['kind'] == 'table' else [block['text']]
        for value in values:
            expected = canonical(markdown.plain(value))
            if expected not in canonical(word_text) or expected not in canonical(html_text):
                raise ValueError('Shared Markdown content is missing from a rendered format.')
    public_text(word_text); public_text(html_text)
    receipt = {'schema': SCHEMA, 'date': report_date, 'sourceDateEpoch': source_date_epoch,
               'rendererSha256': digest(Path(__file__).read_bytes()),
               'publicSourcePath': public_source, 'sourceMarkdownSha256': source_sha, 'sharedContentSha256': shared_sha,
               'contentBlocks': len(blocks), 'markdownWordHtmlParity': True, 'sourceLinks': links,
               'generalClassificationNormalized': True, 'dynamicWordFields': 0, 'fakeOfficePageCountPresent': False,
               'publicTextLeakageChecksPassed': True, 'procedureIsEvaluationEvidence': False,
               'microsoftWordRenderChecked': False, 'libreOfficeRenderChecked': False, 'htmlBrowserChecked': False,
               'outputs': {p.name: digest(p.read_bytes()) for p in (word, web)}}
    public_text({key: value for key, value in receipt.items() if key != 'sourceLinks'})
    for original, resolved in links.items():
        public_text(original[len('https://'):] if original.startswith('https://') else original)
        public_text(resolved[len('https://'):])
    (output / 'calibration-artifact-validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    (output / 'calibration-shared-content.json').write_text(json.dumps(blocks, ensure_ascii=False, indent=2) + '\n')
    (output / 'shell.docx').unlink(missing_ok=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--date', required=True)
    parser.add_argument('--source-date-epoch', required=True, type=int)
    parser.add_argument('--public-source', default=DEFAULT_PUBLIC_SOURCE)
    parser.add_argument('--repo', type=Path, default=REPO)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.out, report_date=args.date, source_date_epoch=args.source_date_epoch,
                           public_source=args.public_source, repo=args.repo), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
