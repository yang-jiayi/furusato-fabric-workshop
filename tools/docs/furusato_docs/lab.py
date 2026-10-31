"""Current participant Lab model and exhaustive GitHub Markdown renderer.

The model is shared with standalone HTML. Generation records content and image
integrity without claiming a deployment, new capture, or Word rendering.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
import html
import json
import re
import sys
from .context import load_context
from .facts import compute_facts
from .tests10 import build_tests
from .participant30 import compose, figure_path
from .participant30_text import CHAPTER_TITLES, APPENDIX_TITLES
from .preview30_public_evidence import load as load_evidence
from .preview30_content import verify_artifact_manifest
from .docx_kit import StyleCarrier
from furusato_html.model import Section, Text, Document

def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return sha256(raw).hexdigest()


def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')[:65] or 'section'


REPLACEMENTS = {
    'ja': [
        ('F12 → Network で /subfolders を絞り込み、ワークスペースのフォルダー一覧を再読み込みします。Request URL が /metadata/folders/<自分のWorkspace GUID>/subfolders の要求を選びます。',
         'F12 → Network を開いてワークスペースのフォルダー一覧を再読み込みし、実際のフォルダー一覧を返す要求を見つけます。環境によっては /powerbi/metadata/groupmetadata/?folderObjectId=<自分のWorkspace GUID> などの要求に含まれます。固定のパスだけを前提にせず、要求URLとResponseの内容を確認します。'),
        ('この Word または HTML と、', 'この Lab または HTML と、'),
        ('Word または HTML を操作手順書にして、', 'Lab または HTML を操作手順書にして、'),
        ('Word からコピーした場合も、保存後に改行や記号が変わっていないか確認します。',
         '保存後に改行や記号が変わっていないか確認します。'),
        ('手順書の校正は、同じ日英原稿から Word と HTML を生成し、',
         '手順書の校正は、同じ日英原稿から Lab と HTML を生成し、'),
        ('Word の目次リンクと図表', 'Lab の目次リンクと図表'),
        ('同じ版のWordまたはHTMLと参加者用ZIPを使います。',
         '同じ版のLabまたはHTMLと参加者用ZIPを使います。'),
    ],
    'en': [
        ("In F12 → Network, filter /subfolders and reload the workspace folder list. Choose the request whose path is /metadata/folders/<your workspace GUID>/subfolders.",
         "Open F12 → Network, reload the workspace folder list and find the actual request that returns the folders. Depending on the environment this may be /powerbi/metadata/groupmetadata/?folderObjectId=<your workspace GUID>. Inspect the request URL and Response rather than assuming one fixed endpoint."),
        ('Use this Word or HTML guide together', 'Use this Lab or HTML guide together'),
        ('Use Word or HTML as the procedure;', 'Use Lab or HTML as the procedure;'),
        ('after copying from Word, also check that line breaks and symbols survived saving.',
         'check that line breaks and symbols survived saving.'),
        ('generate Word and HTML from the same bilingual source',
         'generate Lab and HTML from the same bilingual source'),
        ('Word contents links and figures/tables', 'Lab contents links and figures/tables'),
        ('Use Word or HTML and the participant ZIP of the same version.',
         'Use Lab or HTML and the participant ZIP of the same version.'),
    ],
}


def current_text(value, language, block_id, changes=None):
    text = value.get(language) if isinstance(value, Text) else str(value)
    before = text
    for old, new in REPLACEMENTS[language]:
        text = text.replace(old, new)
    if text != before and changes is not None:
        changes.append({'block': block_id, 'language': language, 'before': before, 'after': text,
                        'reason': ('Use the actual native folder-list response.' if '/metadata/folders/' in before else 'Replace retired Word delivery with Lab while preserving the procedure.')})
    return text


def prose(value, language, block_id, *, table=False):
    text = current_text(value, language, block_id)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    if table:
        text = text.replace('|', '&#124;').replace('\n', '<br>')
    return text


def fence(value, language='text'):
    # Content can include triple backticks; select a strictly longer fence.
    runs = [len(m.group()) for m in re.finditer(r'`+', value)]
    ticks = '`' * max([3, *[n + 1 for n in runs]])
    return f'{ticks}{language}\n{value}\n{ticks}\n'




def load_model(root: Path, artifact_manifest_path: Path | None = None):
    """Return document/context/facts/carrier/evidence/metadata for current delivery.

    A supplied manifest is fully verified. Otherwise the existing source verifier
    fingerprints the current tree in memory, so docs edits do not reuse a stale
    committed artifact manifest. No release-approval record is manufactured.
    """
    root = Path(root).resolve()
    if artifact_manifest_path is None:
        sys.path.insert(0, str(root / "tools/provisioning"))
        import v3_artifacts
        if v3_artifacts.rt.REPO.resolve() != root:
            raise ValueError("Source verifier is bound to a different repository")
        manifest = v3_artifacts.snapshot()
        binding = {"manifestSha256": digest(manifest), "sourceCommit": manifest["sourceCommit"],
                   "sourceTreeSha256": manifest["sourceTreeSha256"], "workshopVersion": manifest["workshopVersion"],
                   "csvFiles": manifest["csvFiles"], "notebookCount": len(manifest["notebooks"]), "tempRequired": False}
    else:
        manifest, binding = verify_artifact_manifest(root, Path(artifact_manifest_path))
    context = load_context(root, document_edition="unified-20260923", source_version="2.7.0")
    facts = compute_facts(context)
    tests = build_tests(context, facts)
    evidence = load_evidence(root / "docs/assets/v3.0.0-evidence/manifest.json", root=root)
    roots = [Section(f"ch-{n}", 1, str(n), Text(f"{n}. {v[0]}", f"{n}. {v[1]}"), chapter=n)
             for n, v in CHAPTER_TITLES.items()]
    roots += [Section(f"appendix-{letter.lower()}", 1, letter,
                      Text(f"付録 {letter} {v[0]}", f"Appendix {letter} {v[1]}"), appendix=letter)
              for letter, v in APPENDIX_TITLES.items()]
    composition = compose(roots, root=root, context=context, facts=facts, tests=tests,
                          evidence=evidence, manifest=manifest, legacy_original={})
    from .lab_clients import append_sections
    append_sections(next(section for section in roots if section.chapter == 24))
    changes = []
    def normalize(value, block_id):
        if isinstance(value, Text):
            return Text(*(current_text(value, language, block_id, changes) for language in ("ja", "en")))
        if isinstance(value, list):
            return [normalize(item, block_id) for item in value]
        if isinstance(value, dict):
            return {key: normalize(item, block_id) for key, item in value.items()}
        if isinstance(value, str) and "Furusato_Workshop_v3.0.0_current-20261015.zip" in value:
            updated = value.replace("Furusato_Workshop_v3.0.0_current-20261015.zip", "Furusato_Workshop_v3.0.0_current.zip")
            changes.append({"block": block_id, "before": value, "after": updated,
                            "reason": "Use the current HTML+Lab package filename."})
            return updated
        return value
    figures, tables, checklist = [], [], []
    for chapter in roots:
        for section in chapter.walk():
            for index, block in enumerate(section.blocks):
                block.payload = normalize(block.payload, f"{section.ident}:{index}")
                if block.kind == "figure":
                    figures.append(block)
                    block.payload["number"] = len(figures)
                elif block.kind == "table":
                    tables.append(block)
                    block.payload["number"] = len(tables)
            if section.level == 2 and section.number.endswith(".2") and (section.chapter or 0) >= 4:
                section.checklist_id = section.ident
                checklist.append((section.ident, section))
    document = Document(roots, figures, tables, checklist)
    counts = {"chapters": 24, "appendices": 5, "headings": sum(1 for _ in document.walk()),
              "tables": len(tables), "figures": len(figures), "tests": len(tests),
              "conditions": sum(len(test.evidence) + len(test.pass_criteria) for test in tests)}
    if counts["conditions"] != 84:
        raise ValueError("Original evaluation conditions changed")
    metadata = {"version": (root / "WORKSHOP_VERSION").read_text().strip(), "counts": counts,
                "participantEdition": True, "delivery": "html-lab", "contentSha256": digest(asdict(document)),
                "participantFigures": composition["figures"], "participantEvaluation": composition["evaluation"],
                "currentArtifactSet": binding, "currentDeliveryChanges": changes,
                "retiredWordDeliveryChanges": [change for change in changes if "Word" in change["reason"]],
                "retainedLegacyChapters": 0, "retainedLegacyAppendices": 0,
                "newDeploymentReadinessCertified": False, "newDeploymentScreenshotsClaimed": False,
                "allFeaturesPassedClaimed": False, "aiAnswerQualityAccepted": False}
    return document, context, facts, StyleCarrier.resolve(root), evidence, metadata


class LabWriter:
    def __init__(self, root, out, context, evidence):
        self.root, self.out, self.context, self.evidence = root, out, context, evidence
        self.assets = {}

    def asset(self, block):
        key, kind = block['source_key'], block['source_kind']
        if kind == 'participant-capture':
            path = figure_path(key)
        elif kind == 'reviewed-capture':
            path = self.evidence['captures'][key]['path']
        elif kind == 'diagram':
            paths = self.context.diagrams[key]
            path = paths.get('svg') or paths['png']
        else:
            raise ValueError('Unreviewed image source: ' + kind)
        name = slug(key) + path.suffix.lower()
        raw = path.read_bytes()
        target = self.out / 'assets' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != raw:
            raise ValueError('Asset name collision: ' + name)
        target.write_bytes(raw)
        self.assets[key] = {'file': target.relative_to(self.out).as_posix(), 'kind': kind,
                       'source': path.relative_to(self.root).as_posix(), 'sha256': sha256(raw).hexdigest()}
        return '../assets/' + name


    def render_block(self, block, language, block_id):
        p = lambda v, **kw: prose(v, language, block_id, **kw)
        kind = block.kind
        if kind == 'paragraph':
            return p(block['text']) + '\n'
        if kind == 'list':
            start = block.get('start', 1)
            lines = []
            for i, item in enumerate(block['items']):
                prefix = f'{start + i}. ' if block['numbered'] else '- '
                text = p(item).replace('\n', '\n' + ' ' * len(prefix))
                lines.append(prefix + text)
            return '\n'.join(lines) + '\n'
        if kind == 'callout':
            title = p(block['title']) if block.get('title') else ''
            lines = (('**' + title + '**\n\n') if title else '') + p(block['text'])
            return '\n'.join('> ' + line for line in lines.splitlines()) + '\n'
        if kind == 'code':
            label = block.get('language')
            label = label.get(language) if isinstance(label, Text) else str(label or '')
            syntax = next((v for v in ('python', 'sql', 'kql', 'dax', 'json', 'powershell', 'bash', 'gql')
                           if v in label.lower()), 'text')
            return (('**' + html.escape(label) + '**\n\n') if label else '') + fence(block['text'], syntax)
        if kind == 'prompt':
            # Prompts are canonical literal source text: do not translate or rewrite.
            return fence(block['text'].get(language))
        if kind == 'table':
            headers = [p(value, table=True) for value in block['headers']]
            rows = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |']
            rows += ['| ' + ' | '.join(p(cell, table=True) for cell in row) + ' |' for row in block['rows']]
            return '**' + p(block['caption']) + '**\n\n' + '\n'.join(rows) + '\n'
        if kind == 'figure':
            image = self.asset(block)
            alt = p(block['alt']).replace('[', '\\[').replace(']', '\\]')
            return f'![{alt}]({image})\n\n' + p(block['caption']) + '\n'
        raise ValueError('Unknown participant model block: ' + kind)


def grouped(blocks):
    """Preserve model order and keep one screenshot/diagram per file."""
    segments, segment = [], []
    has_figure = False
    for index, block in enumerate(blocks):
        if segment and has_figure and (block.kind == 'figure' or
                block.kind == 'list' and block['numbered']):
            segments.append(segment)
            segment, has_figure = [], False
        segment.append((index, block))
        has_figure = has_figure or block.kind == 'figure'
    if segment:
        segments.append(segment)
    return segments or [[]]


def write_lab(root: Path, out: Path, *, model=None):
    root, out = Path(root).resolve(), Path(out).resolve()
    document, context, facts, carrier, evidence, metadata = model or load_model(root)
    writer = LabWriter(root, out, context, evidence)
    if out.exists():
        raise SystemExit('Refusing to overwrite existing staging Lab directory')
    out.mkdir()
    inventory, root_links, coverage, model_ids = [], [], [], []
    all_pages = []
    for chapter in document.sections:
        chapter_name = ('%02d' % chapter.chapter) if chapter.chapter else 'appendix-' + chapter.appendix.lower()
        folder = chapter_name + '-' + slug(chapter.title_without_number().en)
        chapter_dir = out / folder
        chapter_dir.mkdir()
        root_links.append((folder, chapter.title))
        section_links = []
        page_number = 0
        for section in chapter.walk():
            if section is chapter and not section.blocks:
                continue
            for part, segment in enumerate(grouped(section.blocks), 1):
                page_number += 1
                figure = next((b for _, b in segment if b.kind == 'figure'), None)
                suffix = slug(figure['source_key']) if figure else slug(section.title_without_number().en)
                filename = f'{page_number:02d}-{section.number.replace(".", "-").lower()}-{suffix}.md'
                page = chapter_dir / filename
                ids = [f'{section.ident}:{i}' for i, _ in segment]
                model_ids.extend(ids)
                title = section.title.ja + (f'（{part}）' if len(grouped(section.blocks)) > 1 else '')
                section_links.append((filename, title))
                ja = '\n'.join(writer.render_block(b, 'ja', ident) for ident, (_, b) in zip(ids, segment))
                en = '\n'.join(writer.render_block(b, 'en', ident) for ident, (_, b) in zip(ids, segment))
                body = f'# {title}\n\n[Lab 目次](../README.md) · [この章の目次](README.md)\n\n'
                body += ja + '\n<details>\n<summary>English</summary>\n\n'
                body += '## ' + section.title.en + '\n\n' + en + '\n</details>\n'
                page.write_text(body, encoding='utf-8', newline='\n')
                record = {'path': page.relative_to(out).as_posix(), 'section': section.ident,
                          'sourceBlockIds': ids, 'sourceBlockSha256': {ident: digest(asdict(b)) for ident, (_, b) in zip(ids, segment)},
                          'capture': figure['source_key'] if figure else None,
                          'codeBlocks': sum(b.kind == 'code' for _, b in segment),
                          'prompts': sum(b.kind == 'prompt' for _, b in segment),
                          'tables': sum(b.kind == 'table' for _, b in segment)}
                coverage.append(record)
                all_pages.append(page)
                if figure:
                    inventory.append({'id': figure['source_key'], 'page': record['path'],
                                      'captionJa': figure['caption'].ja, 'captionEn': figure['caption'].en})
        nav = f'# {chapter.title.ja}\n\n[Lab 目次](../README.md)\n\n{chapter.title.en}\n\n'
        nav += '\n'.join(f'- [{title}]({quote(path)})' for path, title in section_links) + '\n'
        (chapter_dir / 'README.md').write_text(nav, encoding='utf-8', newline='\n')
    expected_ids = [f'{s.ident}:{i}' for s in document.walk() for i, b in enumerate(s.blocks)]
    if model_ids != expected_ids:
        raise ValueError('Source block ordering, omission or duplication detected')
    index = '# Furusato Workshop Lab\n\n'
    index += ('Microsoft Fabric の Lakehouse・Eventhouse・Ontology・Semantic model・Data Agent を、合成データで順に構築して確かめます。'
              'この Lab と [HTML 手順書](../docs/furusato-workshop-v3-0-0-complete.html) は、最新版の操作手順を提供します。\n\n'
              '初回は **4章 → 24.4〜24.6 → 5〜8章の確認 → 24.7と9〜11章 → 24.8 → 17章 → 19章・付録C** の順で進めます。'
              '作成済みのデータやアイテムを重複して作成・取り込みしません。各章の目次から操作ページへ進み、完了条件を確認してください。\n\n'
              '各画面キャプチャは1つの操作ページにまとめ、キャプチャが不要な説明・コマンド・参照表も省略せずに収録しています。'
              '各ページ末尾の **English** を開くと同じ内容を英語で読めます。\n\n')
    index += '\n'.join(f'- [{title.ja}]({quote(folder)}/README.md)' for folder, title in root_links) + '\n\n'
    index += ('Notebook・CSV・モデル・Agent 設定は [`workshop/v3.0.0-preview/`](../workshop/v3.0.0-preview/) にあります。'
              'ローカルコマンドはリポジトリのルート、参加者用 ZIP では展開先の `source/` を起点に実行します。\n')
    (out / 'README.md').write_text(index, encoding='utf-8', newline='\n')
    counts = Counter(b.kind for s in document.walk() for b in s.blocks)
    receipt = {'schemaVersion': 'furusato-lab-source-coverage/v1', 'chapters': 24, 'appendices': 5,
               'sections': len(list(document.walk())), 'modelBlocks': sum(counts.values()), 'blocksByKind': dict(counts),
               'pages': len(coverage), 'capturePages': len(inventory), 'uniqueAssets': len(writer.assets),
               'allSourceBlocksPresentOnceInOrder': model_ids == expected_ids,
               'wordDeliveryChanges': metadata['retiredWordDeliveryChanges'], 'sourceTextChanges': metadata['currentDeliveryChanges'], 'pagesCoverage': coverage,
               'captures': inventory, 'assets': writer.assets,
               'newDeploymentScreenshotsClaimed': False}
    receipt["contentSha256"] = metadata["contentSha256"]
    receipt["currentArtifactSet"] = metadata["currentArtifactSet"]
    return receipt


def validate_lab(root: Path, out: Path, receipt: dict, *, model=None):
    """Check every literal/text/image/link and fail on content loss or tampering."""
    from urllib.parse import unquote, urlparse
    root, out = (Path(root).resolve(), Path(out).resolve())
    document, context, facts, carrier, evidence, metadata = model or load_model(root)
    source = {f'{section.ident}:{i}': block for section in document.walk() for i, block in enumerate(section.blocks)}
    actual_ids = []
    checked_texts = checked_literals = links = 0

    def same_space(value):
        return re.sub('\\s+', ' ', value).strip()

    def values(block):
        keys = {'paragraph': ['text'], 'list': ['items'], 'callout': ['text', 'title'], 'table': ['headers', 'rows', 'caption'], 'figure': ['alt', 'caption'], 'code': [], 'prompt': []}[block.kind]

        def walk(value):
            if isinstance(value, Text):
                yield value
            elif isinstance(value, (list, tuple)):
                for child in value:
                    yield from walk(child)
        for key in keys:
            yield from walk(block.get(key))
    for page in receipt['pagesCoverage']:
        path = (out / page['path']).resolve()
        if not path.is_relative_to(out):
            raise ValueError('Lab page path escapes output')
        text = path.read_text()
        if not text.count('<details>') == text.count('</details>') == 1:
            raise ValueError(path)
        if not len(re.findall('^#{1,2} ', text, re.M)) >= 2:
            raise ValueError(path)
        for ident in page['sourceBlockIds']:
            actual_ids.append(ident)
            block = source[ident]
            if not digest(asdict(block)) == page['sourceBlockSha256'][ident]:
                raise ValueError(ident)
            if block.kind == 'code':
                if not block['text'] in text:
                    raise ValueError((ident, 'canonical code changed'))
                checked_literals += 1
            elif block.kind == 'prompt':
                for lang in ('ja', 'en'):
                    if not block['text'].get(lang) in text:
                        raise ValueError((ident, lang, 'prompt changed'))
                checked_literals += 1
            for value in values(block):
                for lang in ('ja', 'en'):
                    wanted = prose(value, lang, ident, table=block.kind == 'table')
                    if block.kind == 'figure':
                        wanted = wanted.replace('[', '\\[').replace(']', '\\]')
                    if not same_space(wanted) in same_space(text):
                        raise ValueError((ident, lang, wanted[:90]))
                    checked_texts += 1
        if page['capture']:
            if not len(re.findall('^!\\[', text, re.M)) == 2:
                raise ValueError((path, 'one image per language required'))
    if not actual_ids == list(source):
        raise ValueError('Model block omission, duplication or ordering change')
    for ident, asset in receipt['assets'].items():
        local = out / asset['file']
        original = root / asset['source']
        if not sha256(local.read_bytes()).hexdigest() == asset['sha256']:
            raise ValueError('Lab validation failed')
        if not original.read_bytes() == local.read_bytes():
            raise ValueError(ident)
    for path in out.rglob('*.md'):
        text = path.read_text()
        if not not re.search('\\bWord\\b|\\.docx|76 PASS|48 PASS|\\bholdout\\b|\\bR8\\b', text, re.I):
            raise ValueError(path)
        in_fence = False
        fence_len = 0
        lines = []
        for line in text.splitlines():
            m = re.match('^(`{3,})', line)
            if m:
                if not in_fence:
                    in_fence = True
                    fence_len = len(m.group(1))
                elif len(m.group(1)) >= fence_len:
                    in_fence = False
                continue
            if not in_fence:
                lines.append(line)
        if not not in_fence:
            raise ValueError((path, 'unclosed code fence'))
        for target in re.findall('!?\\[[^\\n]*?\\]\\(([^\\s)]+)\\)', '\n'.join(lines)):
            if urlparse(target).scheme or target.startswith('#'):
                continue
            resolved = (path.parent / unquote(target.split('#')[0])).resolve()
            if resolved.is_relative_to(out):
                if not resolved.exists():
                    raise ValueError((path, target))
            elif resolved.is_relative_to(out.parent):
                mapped = root / resolved.relative_to(out.parent)
                if not mapped.exists():
                    raise ValueError((path, target, mapped))
            else:
                raise AssertionError((path, target, 'escaped staging/repository'))
            links += 1
    result = {'status': 'passed', 'chapters': 24, 'appendices': 5, 'sections': sum(1 for _ in document.walk()), 'sourceBlocksChecked': len(actual_ids), 'bilingualTextValuesChecked': checked_texts, 'canonicalCodeAndPromptBlocksChecked': checked_literals, 'imageFilesVerified': len(receipt['assets']), 'localLinksChecked': links, 'markdownFiles': len(list(out.rglob('*.md'))), 'currentParticipantWordReferences': 0, 'newDeploymentCaptureClaimed': False}
    return result
