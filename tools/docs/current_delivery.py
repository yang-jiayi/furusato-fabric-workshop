"""Build, verify and package the current standalone HTML and GitHub Lab guide.

The historical paired-document pipeline remains separate. This pipeline never
creates an Office document or claims live Fabric validation.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import tempfile
import zipfile
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/docs'), str(ROOT / 'tools/html'), str(ROOT / 'tools/provisioning')]
from furusato_docs.lab import load_model, write_lab, validate_lab
from furusato_docs.preview30_content import verify_artifact_manifest
from furusato_docs.current_publication import current_publication
from furusato_docs.typography import ascii_parentheses
from furusato_html.preview30 import render
from furusato_html.model import Text
from lxml import html as html_parser
import preview30_runtime as runtime
import v3_artifacts

PUBLICATION = current_publication(ROOT)
HTML_NAME = PUBLICATION.html_name
PACKAGE_NAME = PUBLICATION.package_name
SOURCE_MANIFEST = 'SOURCE_ARTIFACT_SET.json'
NEW_AUTHORING_FILES = {
    'tools/docs/current_delivery.py', 'tools/docs/CURRENT_HTML_LAB.md',
    'tools/docs/build_lab.py', 'tools/docs/furusato_docs/lab.py',
    'tools/docs/furusato_docs/lab_clients.py', 'tools/docs/tests/test_lab.py',
    'tools/docs/tests/test_current_delivery.py',
    'tools/docs/furusato_docs/current_publication.py',
}
DOC_SOURCE_SUFFIXES = {'.py','.json','.ps1','.md','.txt','.zip','.css','.js','.png','.svg','.pdf'}
PRIVATE_NAMES = {'storage-state.json','cookies.json','credentials.json','msal_token_cache.json','msal_token_cache.bin'}


def digest(value):
    return sha256(value).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def normalized(value):
    return re.sub(r'\s+', ' ', ascii_parentheses(value.replace('`', ''))).strip()


def source_revision(root, binding):
    observed = subprocess.run(['git','-C',str(root),'status','--porcelain'],text=True,capture_output=True)
    return {'baseCommit':binding['sourceCommit'],
            'workingTreeMatchesCommit':not bool(observed.stdout.strip()) if observed.returncode == 0 else None,
            'gitMetadataAvailable':observed.returncode == 0,
            'sourceTreeSha256':binding['sourceTreeSha256']}


def approved_doc_files(root, tracked):
    names=set()
    for directory in ('tools/docs','tools/html','docs/assets'):
        for path in (root/directory).rglob('*'):
            if path.is_symlink():
                raise ValueError('Source package refuses symbolic links: ' + str(path.relative_to(root)))
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            relative=path.relative_to(root).as_posix()
            if path.name.startswith('.env') or path.name.lower() in PRIVATE_NAMES:
                raise ValueError('Private configuration is not a publication input: ' + relative)
            if path.suffix in {'.pyc','.docx'}:
                continue
            if path.suffix not in DOC_SOURCE_SUFFIXES or relative not in tracked | NEW_AUTHORING_FILES:
                raise ValueError('Unapproved authoring source file: ' + relative)
            names.add(relative)
    return names


def current_source_manifest(root):
    """Freeze a bounded actual source inventory before composing either guide."""
    manifest=v3_artifacts.snapshot()
    tracked=set(subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().split('\0'))
    names={name for name in manifest['files'] if not name.startswith('docs/') and not name.endswith('.docx')}
    names.update(runtime.RUNTIME_INPUT_FILES)
    names.add('workshop/v3.0.0-preview/provisioning/baseline-hashes.json')
    names.add('tools/provisioning/unified_agent.py')
    # Public CLI helpers load adjacent schemas, SQL and evaluation resources.
    # Only reviewed, tracked files in these two tool trees are publication inputs.
    for name in tracked:
        candidate=Path(name)
        if (name.startswith(('tools/data-agent/','tools/provisioning/'))
                and candidate.suffix in {'.py','.json','.sql','.txt','.md','.kql','.ps1'}
                and not {'private','.private','qa'} & set(candidate.parts)
                and not candidate.name.startswith('.env') and candidate.name.lower() not in PRIVATE_NAMES):
            names.add(name)
    if names - (tracked | NEW_AUTHORING_FILES):
        raise ValueError('Unapproved runtime source files: ' + ', '.join(sorted(names - (tracked | NEW_AUTHORING_FILES))))
    names.update(approved_doc_files(root,tracked))
    manifest['files']={name:digest((root/name).read_bytes()) for name in sorted(names)}
    manifest['sourceTreeSha256']=runtime.digest(manifest['files'])
    manifest['documentationBinding']={'deliveryMode':'html-lab','guide':'guide/'+HTML_NAME,'lab':'Lab/README.md'}
    manifest['documentationSourceRevision']=source_revision(root,manifest)
    return manifest


def checked_lab_files(lab, expected):
    actual=set()
    for path in lab.rglob('*'):
        if path.is_symlink():
            raise ValueError('Lab must not contain symbolic links')
        if path.is_file():actual.add(path.relative_to(lab).as_posix())
    if actual != set(expected):
        raise ValueError('Lab file inventory differs from generated content: ' + ', '.join(sorted(actual ^ set(expected))))
    if isinstance(expected,dict):
        for name,blob in expected.items():
            if (lab/name).read_bytes() != blob:
                raise ValueError('Lab bytes differ from generated content: '+name)
    return sorted(actual)


def validate_source_manifest_paths(root, manifest, *, require_git=False):
    observed=subprocess.run(['git','-C',str(root),'ls-files','-z'],capture_output=True)
    if require_git and observed.returncode != 0:
        raise ValueError('Publication packaging requires a Git source inventory')
    tracked=set(observed.stdout.decode().split('\0')) if observed.returncode == 0 else None
    for name in manifest.get('files',{}):
        path=Path(name)
        if (path.is_absolute() or '..' in path.parts or '\\' in name
                or {'private','.private','qa'} & set(path.parts)
                or path.name.startswith('.env') or path.name.lower() in PRIVATE_NAMES
                or path.suffix.lower() in {'.pem','.key','.pfx','.token','.secret'}):
            raise ValueError('Private or unsafe publication input: '+name)
        if tracked is not None and name not in tracked | NEW_AUTHORING_FILES:
            raise ValueError('Unapproved publication input: '+name)


def markdown_links(lab):
    for path in sorted(lab.rglob('*.md')):
        for value in re.findall(r'\[[^\]\n]*\]\(([^)\s]+)\)',path.read_text(encoding='utf-8')):
            parsed=urlsplit(value)
            if not parsed.scheme and parsed.path:
                yield path,unquote(parsed.path)


def add_lab_aliases(files, root, lab, source_files, html_blob):
    """Keep GitHub-relative Lab links valid in the portable package too."""
    root = Path(root).resolve()
    lab = Path(lab).resolve()
    for page,target in markdown_links(lab):
        virtual_lab=(root/'Lab').resolve()
        destination=(virtual_lab/page.relative_to(lab).parent/target).resolve()
        if destination.is_relative_to(virtual_lab):continue
        if not destination.is_relative_to(root.resolve()):
            raise ValueError('Lab link escapes the source tree')
        name=destination.relative_to(root).as_posix()
        if name=='docs/'+HTML_NAME:
            files[name]=html_blob
        elif name in source_files:
            files[name]=files['source/'+name]
        elif destination.is_dir():
            matching=[item for item in source_files if item.startswith(name+'/')]
            if not matching:raise ValueError('Lab directory link is absent from the source inventory: '+name)
            for item in matching:files[item]=files['source/'+item]
        else:
            raise ValueError('Lab link is absent from the publication inventory: '+name)


def validate_packaged_links(extracted):
    checked=0
    for page,target in markdown_links(extracted/'Lab'):
        destination=(page.parent/target).resolve()
        if not destination.is_relative_to(extracted.resolve()) or not destination.exists():
            raise ValueError('Broken packaged Lab link: '+page.relative_to(extracted).as_posix()+' -> '+target)
        checked+=1
    return checked


def text_values(value):
    if isinstance(value, Text):
        yield value.ja
        yield value.en
    elif isinstance(value, dict):
        for child in value.values():
            yield from text_values(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from text_values(child)


def inspect_html(path, document, metadata):
    raw = path.read_bytes()
    tree = html_parser.fromstring(raw)
    provenance = json.loads(tree.get_element_by_id('preview30-provenance').text)
    if (provenance.get('deliveryMode') != 'html-lab'
            or provenance.get('contentSha256') != metadata['contentSha256']
            or provenance.get('currentArtifactSet') != metadata['currentArtifactSet']
            or any(key in provenance for key in ('wordSha256', 'wordFilename', 'documentRelease'))):
        raise ValueError('The HTML does not bind the current standalone participant model')
    main = tree.get_element_by_id('main')
    body = tree.find('body')
    if re.search(r'\bWord\b|\.docx', body.text_content(), re.I) or tree.xpath('//*[@id="word-download"]'):
        raise ValueError('Retired guide references remain in the current participant HTML')
    sections = list(document.walk())
    if len(main.xpath('./section')) != 29:
        raise ValueError('The guide must contain 24 chapters and five appendices')
    actual_sections = main.xpath('.//section[@data-section-id]')
    if [s.get('id') for s in actual_sections] != [s.ident for s in sections]:
        raise ValueError('HTML section order or coverage differs from the model')
    values_checked = code_checked = 0
    all_code = [node.text_content() for node in main.xpath('.//pre/code')]
    for section in sections:
        target = tree.get_element_by_id(section.ident)
        visible = normalized(target.text_content())
        for value in (section.title.ja, section.title.en):
            if normalized(value) not in visible:
                raise ValueError('Missing section title: ' + section.ident)
        for block in section.blocks:
            for value in text_values(block.payload):
                if normalized(value) and normalized(value) not in visible:
                    # Alternate text is an image accessibility attribute.
                    alts = ' '.join(target.xpath('.//@aria-label | .//@alt'))
                    if normalized(value) not in normalized(alts):
                        raise ValueError('Missing bilingual model text: ' + section.ident + ': ' + value[:90])
                values_checked += 1
            if block.kind == 'code':
                expected = block['text'] if block.get('canonicalLiteral') else ascii_parentheses(block['text'])
                if expected not in all_code:
                    raise ValueError('Code literal differs from its source: ' + section.ident)
                code_checked += 1
            if block.kind == 'prompt':
                for lang in ('ja', 'en'):
                    expected = block['text'].get(lang)
                    if not block.get('canonicalLiteral'):
                        expected = ascii_parentheses(expected)
                    if expected not in all_code:
                        raise ValueError('Prompt literal differs from its source: ' + section.ident)
                    code_checked += 1
    if len(main.xpath('.//figure')) != len(document.figures):
        raise ValueError('Figure coverage differs from the model')
    for node in tree.xpath('//*[@src] | //link[@href] | //script[@src]'):
        uri = node.get('src') or node.get('href')
        if not uri.startswith(('data:', '#')):
            raise ValueError('HTML requires an external resource: ' + uri)
    ids = tree.xpath('//@id')
    if len(ids) != len(set(ids)):
        raise ValueError('HTML contains duplicate anchor IDs')
    for link in tree.xpath('//a[starts-with(@href,"#")]/@href'):
        if link[1:] not in ids:
            raise ValueError('HTML contains a broken anchor: ' + link)
    return {'passed': True, 'chaptersAndAppendices': 29, 'sections': len(sections),
            'modelBlocks': sum(len(s.blocks) for s in sections), 'bilingualValuesChecked': values_checked,
            'literalCodeAndPromptsChecked': code_checked, 'figures': len(document.figures),
            'standaloneResources': True, 'retiredGuideReferences': 0, 'htmlSha256': digest(raw)}


def build(root, out, artifact_manifest=None):
    if out.exists():
        raise ValueError('Choose a new output directory; existing artifacts are preserved')
    out.mkdir(parents=True)
    manifest_path=out/SOURCE_MANIFEST
    manifest_path.write_bytes(Path(artifact_manifest).read_bytes() if artifact_manifest else json_bytes(current_source_manifest(root)))
    validate_source_manifest_paths(root,json.loads(manifest_path.read_bytes()))
    document, context, facts, carrier, evidence, metadata = load_model(root, manifest_path)
    metadata = {k: v for k, v in metadata.items() if k not in {'retiredWordDeliveryChanges', 'currentDeliveryChanges'}}
    metadata.update(deliveryMode='html-lab')
    metadata['sourceRevision'] = source_revision(root, metadata['currentArtifactSet'])
    text = render(document, context, facts, carrier, evidence, metadata, None, root,
                  release_profile=None, delivery_mode='html-lab')
    path = out / HTML_NAME
    path.write_text(text, encoding='utf-8', newline='\n')
    receipt = {'schemaVersion': 'furusato-current-html-lab-validation/v1', 'deliveryMode': 'html-lab',
               'contentSha256': metadata['contentSha256'], 'static': inspect_html(path, document, metadata),
               'sourceRevision': metadata['sourceRevision'],
               'currentArtifactSet':metadata['currentArtifactSet'],
               'browser': {'passed': False, 'performed': False}, 'liveFabricValidationClaimed': False}
    (out / 'DOCUMENT_VALIDATION.json').write_bytes(json_bytes(receipt))
    return receipt


def select_browser_executable(chromium, executable=None):
    if executable is not None:
        selected = Path(executable)
        if not selected.is_file():
            raise FileNotFoundError('Browser executable must be an existing file: ' + str(selected))
        return selected.resolve()
    system = Path('/usr/bin/chromium')
    if sys.platform.startswith('linux') and system.is_file():
        return system
    selected = Path(chromium.executable_path)
    if not selected.is_file():
        raise FileNotFoundError(
            'Playwright Chromium is not installed. Run "python -m playwright install chromium" '
            'with this Python environment, or use --browser-executable with an existing browser file.')
    return selected


def browser_check(path, out, executable=None):
    """Exercise the standalone guide; serve only its exact HTML bytes locally."""
    from playwright.sync_api import sync_playwright
    from pypdf import PdfReader
    raw = path.read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split('?')[0] not in ('/', '/' + path.name):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = 'http://127.0.0.1:' + str(server.server_port)
    checks, print_pages, errors, external = [], {}, [], []
    try:
        with sync_playwright() as p:
            selected = select_browser_executable(p.chromium, executable)
            browser = p.chromium.launch(executable_path=str(selected), headless=True, args=['--no-sandbox'])
            version = browser.version
            context = browser.new_context(viewport={'width':1440,'height':1000})
            def route_request(route):
                if route.request.url.startswith(origin + '/'):
                    route.continue_()
                else:
                    external.append(route.request.url)
                    route.abort()
            context.route('http://**/*', route_request)
            context.route('https://**/*', route_request)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(origin + '/' + path.name, wait_until='load')
            page.wait_for_selector('html[data-ready=true]')
            assert page.locator('main > section').count() == 29
            checks.append('all29chaptersAndAppendices')
            for lang in ('ja', 'en'):
                page.locator(f'button[data-language="{lang}"]').click()
                assert page.locator('html').get_attribute('data-lang') == lang
                page.reload(wait_until='load')
                assert page.locator('html').get_attribute('data-lang') == lang
                page.locator('#search').fill('Donation')
                assert page.locator('main > section:not([hidden])').count() > 0
                page.locator('#search-clear').click()
                assert page.locator('main > section:not([hidden])').count() == 29
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                page.set_viewport_size({'width':1440,'height':1000})
                checks.extend([f'{lang}.languagePersists', f'{lang}.searchAndReset', f'{lang}.mobile390'])
                page.emulate_media(media='print')
                pdf = out / f'html-{lang}.pdf'
                page.pdf(path=str(pdf), print_background=True, prefer_css_page_size=True)
                print_pages[lang] = len(PdfReader(pdf).pages)
                assert print_pages[lang] > 0
                page.emulate_media(media='screen')
                checks.append(f'{lang}.printPdf')
            checkbox = page.locator('input[data-step]').first
            checkbox.check()
            page.reload(wait_until='load')
            assert page.locator('input[data-step]').first.is_checked()
            page.locator('#progress-reset').click()
            assert not page.locator('input[data-step]:checked').count()
            checks.append('progressPersistsAndResets')
            link = page.locator('.toc a').last
            target = link.get_attribute('href')
            link.click()
            assert page.evaluate('location.hash') == target
            checks.append('tocNavigation')
            page.locator('[data-copy-target]').first.click()
            page.wait_for_function("document.getElementById('copy-status').textContent.length > 0")
            checks.append('copyFeedback')
            page.locator('[data-lightbox]').first.click()
            assert page.locator('#lightbox').is_visible()
            page.locator('#lightbox-close').click()
            assert not page.locator('#lightbox').is_visible()
            checks.append('figureZoom')
            page.evaluate('window.print=()=>{window.__printInvoked=true}')
            page.locator('#print').click()
            assert page.evaluate('window.__printInvoked === true')
            checks.append('printButton')
            assert not errors, errors
            assert not external, external
            checks.extend(['noScriptErrors','noExternalRequests'])
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return {'passed':True, 'performed':True, 'browserVersion':version, 'htmlSha256':digest(raw),
            'checks':checks, 'printedPages':print_pages, 'allPrintedPagesVisuallyReviewed':False}


def require_validated(path, receipt):
    if (receipt.get('schemaVersion') != 'furusato-current-html-lab-validation/v1'
            or receipt.get('deliveryMode') != 'html-lab'
            or receipt.get('static',{}).get('passed') is not True
            or receipt.get('browser',{}).get('passed') is not True
            or receipt['static']['htmlSha256'] != digest(path.read_bytes())
            or receipt['browser']['htmlSha256'] != digest(path.read_bytes())):
        raise ValueError('Current HTML requires matching static and real browser validation')


def package(root, path, lab, receipt_path, output):
    if output.exists():
        raise ValueError('Refusing to overwrite an existing package')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    require_validated(path, receipt)
    if not (lab / 'README.md').is_file():
        raise ValueError('The complete Lab guide is required')
    manifest_path=receipt_path.parent/SOURCE_MANIFEST
    validate_source_manifest_paths(root,json.loads(manifest_path.read_bytes()),require_git=True)
    manifest,binding=verify_artifact_manifest(root,manifest_path)
    if binding != receipt.get('currentArtifactSet'):
        raise ValueError('The packaged artifact manifest differs from the validated HTML binding')
    model = load_model(root,manifest_path)
    if model[-1]['contentSha256'] != receipt['contentSha256']:
        raise ValueError('The participant model changed after HTML validation')
    inspect_html(path,model[0],model[-1])
    with tempfile.TemporaryDirectory(prefix='furusato-package-lab-') as temp:
        coverage=write_lab(root,Path(temp)/'Lab',model=model)
        lab_validation=validate_lab(root,lab,coverage,model=model)
        expected={p.relative_to(Path(temp)/'Lab').as_posix():p.read_bytes() for p in (Path(temp)/'Lab').rglob('*') if p.is_file()}
        lab_names=checked_lab_files(lab,expected)
    files = {'guide/' + path.name:path.read_bytes(), 'DOCUMENT_VALIDATION.json':json_bytes(receipt)}
    files['LAB_VALIDATION.json']=json_bytes(lab_validation)
    attachment_root=root/'workshop/v3.0.0-preview/attachments'
    attachment_manifest=json.loads((attachment_root/'manifest.json').read_text(encoding='utf-8'))
    for name in ('business-requirements.pdf','data-dictionary.txt','domain-model.png',
                 'revision-requirements.txt','manifest.json','SHA256SUMS.txt'):
        blob=(attachment_root/name).read_bytes()
        if name in attachment_manifest['files']:
            if digest(blob) != attachment_manifest['files'][name]['sha256']:
                raise ValueError('Attachment changed: ' + name)
        files['attachments/'+name]=blob
    for name in lab_names:files['Lab/'+name]=(lab/name).read_bytes()
    source_files = manifest['files']
    for name, expected in source_files.items():
        blob = (root/name).read_bytes()
        if digest(blob) != expected:
            raise ValueError('Source changed during packaging: ' + name)
        files['source/' + name] = blob
    files['source/artifact-set.json'] = manifest_path.read_bytes()
    add_lab_aliases(files,root,lab,source_files,path.read_bytes())
    files['START_HERE.txt'] = (
        PUBLICATION.title + '\n\n' +
        'guide/ の日英HTML、または Lab/README.md の全手順を開き、第4章の準備から進めます。\n'
        'Open the standalone bilingual HTML in guide/ or the complete Lab/README.md; start with Chapter 4.\n'
        'source/ からNotebook・データ・配置ツールを実行します。\n'
        'Run Notebooks, data and deployment tools from source/.\n'
        '第17章でAgentを設定・公開し、第19章と付録Cで評価・改善します。\n'
        'Chapter 17 configures and publishes the Agent; Chapter 19 and Appendix C cover evaluation and improvement.\n'
        'SHA256SUMS.txtでファイルの整合を確認します。\n'
        'Check file integrity with SHA256SUMS.txt.\n'
    ).encode('utf-8')
    files['PACKAGE_MANIFEST.json'] = json_bytes({'schemaVersion':'furusato-current-html-lab-package/v1',
        'deliveryMode':'html-lab','workshopVersion':PUBLICATION.version,
        'files':{name:digest(blob) for name,blob in sorted(files.items())},
        'liveFabricValidationClaimed':False})
    files['SHA256SUMS.txt'] = ''.join(digest(blob)+'  '+name+'\n' for name,blob in sorted(files.items())).encode()
    if any(name.endswith('.docx') for name in files):
        raise ValueError('The current participant package must not contain a retired guide')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,blob in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,31,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,blob)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('Package CRC verification failed')
        for name,blob in files.items():
            if archive.read(name) != blob:
                raise ValueError('Packaged bytes differ: ' + name)
        with tempfile.TemporaryDirectory(prefix='furusato-package-links-') as temp:
            archive.extractall(temp)
            links=validate_packaged_links(Path(temp))
    return {'entries':len(files),'sha256':digest(output.read_bytes()),'deliveryMode':'html-lab','packagedLabLinksChecked':links}


def parse_args(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('build');p.add_argument('--out',type=Path,required=True);p.add_argument('--artifact-manifest',type=Path)
    p=sub.add_parser('validate');p.add_argument('--out',type=Path,required=True);p.add_argument('--browser',action='store_true');p.add_argument('--artifact-manifest',type=Path)
    p.add_argument('--browser-executable',type=Path,help='Existing Chromium executable (requires --browser); otherwise use Linux system Chromium or Playwright Chromium')
    p=sub.add_parser('package');p.add_argument('--out',type=Path,required=True);p.add_argument('--lab',type=Path,default=ROOT/'Lab');p.add_argument('--package',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.command=='validate' and args.browser_executable is not None:
        if not args.browser:
            parser.error('--browser-executable requires --browser')
        if not args.browser_executable.is_file():
            parser.error('--browser-executable must be an existing file')
    return args


def main():
    args=parse_args()
    if args.command=='build':
        result=build(ROOT,args.out,args.artifact_manifest)
    elif args.command=='validate':
        manifest_path=args.artifact_manifest or args.out/SOURCE_MANIFEST
        document,_,_,_,_,metadata=load_model(ROOT,manifest_path)
        metadata.update(deliveryMode='html-lab')
        receipt_path=args.out/'DOCUMENT_VALIDATION.json'
        result=json.loads(receipt_path.read_text())
        result['static']=inspect_html(args.out/HTML_NAME,document,metadata)
        result['sourceRevision']=source_revision(ROOT, metadata['currentArtifactSet'])
        if args.browser:
            result['browser']=browser_check(args.out/HTML_NAME,args.out,args.browser_executable)
        receipt_path.write_bytes(json_bytes(result))
    else:
        result=package(ROOT,args.out/HTML_NAME,args.lab,args.out/'DOCUMENT_VALIDATION.json',args.package)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
