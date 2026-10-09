"""Build a separately dated, field-free Word/bilingual HTML report from public sources.

Inputs are the counts-only result-20261010.json and the two shared Markdown files.
The report uses condition denominators, preserves phase/native limitations, and
never reinterprets conditions as question cohorts. No cloud calls are made.
Run with a fresh external staging directory. A successful build is artifact
validation, not independent judgment verification or answer-quality acceptance.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import hashlib
import html
import json
import os
import re
import sys
import zipfile
from lxml import etree
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from furusato_docs.docx_kit import DocumentBuilder
from furusato_docs.oox import StyleCarrier, apply_japanese_typography, normalise_package_metadata

ROOT=Path(__file__).resolve().parents[2]
SOURCES=('README.md','calibration-and-proofreading.md','result-20261010.json')
VERDICTS=('PASS','FAIL','UNCLEAR','NA')


def assert_public_text(text):
    """Reject live identifiers/private evaluation payload markers, including JSON escapes."""
    patterns=(r'/workspace/',r'/var/tmp/',r'\b(?:T|B|Q)\d{2}\b',r'\b(?:HA|HB)\b',
              r'(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
              r'(?i)bearer\s+[A-Za-z0-9_.-]{20,}',r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')
    if any(re.search(p,text) for p in patterns):
        raise ValueError('Public source contains a private path, live identifier or evaluation marker.')


def validate_summary(study):
    if study.get('schema')!='furusato-measured-contract-summary/v1':
        raise ValueError('Unsupported measured summary schema.')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',study.get('date','')):
        raise ValueError('A separately dated report is required.')
    assert_public_text(json.dumps(study,ensure_ascii=False))
    method=study['method']
    for key in ('independentHumanSignoff','strictNativeAcceptanceAssigned','strictGradersChanged',
                'favorableRetrySelection','causalEffectIsolatedFromCaptureAvailability','latestFull51Retested'):
        if method[key] is not False:
            raise ValueError('Measured-summary boundary changed: '+key)
    if method['originalVerdictsPreserved'] is not True:
        raise ValueError('Original verdicts must be retained.')
    groups=[study['original']['baseline'],study['original']['R8'],study['regression']['baseline'],
            study['regression']['R8'],study['disjointUnusedSets']['baseline'],study['disjointUnusedSets']['R8'],
            study['qualitySupplement']['baseline'],study['qualitySupplement']['R8'],
            *(v['conditions'] for v in study['latestTargetedChecks'])]
    for group in groups:
        if any(type(group[k]) is not int or group[k]<0 for k in VERDICTS):
            raise ValueError('Verdict counts must be explicit nonnegative integers.')
        if sum(group[k] for k in VERDICTS)!=group['registeredConditions']:
            raise ValueError('Condition denominator changed.')
        n=group['registeredConditions']-group['NA']
        if n<=0 or group['applicableConditions']!=n or group['passPercent']!=round(group['PASS']/n*100,2):
            raise ValueError('Applicable-condition percentage is inconsistent.')
    original=study['original']
    for phase in ('baseline','R8'):
        if original[phase]['registeredConditions']!=original['conditionsPerRepetition']*original['repetitions']:
            raise ValueError('Original repetitions do not match the registered conditions.')
    matched=study['matchedOriginal'];n=matched['conditions']
    for phase in ('baseline','R8'):
        g=matched[phase]
        if g['PASS']+g['FAIL']!=n or g['passPercent']!=round(g['PASS']/n*100,2):
            raise ValueError('Matched denominator is inconsistent.')
    if matched['deltaPercentagePoints']!=round((matched['R8']['PASS']-matched['baseline']['PASS'])/n*100,2):
        raise ValueError('Matched percentage-point change is inconsistent.')
    if n+sum(matched['exclusionsFromBothPhases'].values())!=original['baseline']['registeredConditions']:
        raise ValueError('Matched exclusions do not preserve the original denominator.')
    if matched['original252JudgmentsModified'] is not False:
        raise ValueError('Historical condition judgments must be retained.')
    for phase in study['latestTargetedChecks']:
        if phase['full51Retested'] is not False or phase['questionPOSTs']!=phase['questions'] or phase['knownTerminalResponses']!=phase['questions']:
            raise ValueError('Targeted phase must not be promoted into a full retest.')
        if sum(phase['captureStatuses'].values())!=phase['questions']:
            raise ValueError('Targeted capture denominator is inconsistent.')
    if type(study['artifactSourceDateEpoch']) is not int or study['artifactSourceDateEpoch']<315532800:
        raise ValueError('A valid reproducible artifact epoch is required.')
    for ref in study['privateEvidenceDigests']:
        if not re.fullmatch('[a-f0-9]{64}',ref['sha256']):
            raise ValueError('Immutable evidence references need exact SHA256 digests.')
    return study


INLINE=re.compile(r'\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`')
def tokens(text):
 pos=0
 for m in INLINE.finditer(text):
  if m.start()>pos:yield 'plain',text[pos:m.start()],None
  if m.group(1) is not None:yield 'link',m.group(1),m.group(2)
  elif m.group(3) is not None:yield 'bold',m.group(3),None
  else:yield 'code',m.group(4),None
  pos=m.end()
 if pos<len(text):yield 'plain',text[pos:],None
def plain(text):return ''.join(t for kind,t,target in tokens(text))
def html_inline(text):
 out=[]
 for kind,t,target in tokens(text):
  t=html.escape(t)
  out.append('<a href="'+html.escape(target,quote=True)+'">'+t+'</a>' if kind=='link' else '<strong>'+t+'</strong>' if kind=='bold' else '<code>'+t+'</code>' if kind=='code' else t)
 return ''.join(out)
def parse(text):
 lines=text.splitlines(); i=0; blocks=[]
 while i<len(lines):
  line=lines[i]
  if not line.strip():i+=1;continue
  if line.startswith('```'):
   lang=line[3:].strip();i+=1;code=[]
   while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
   blocks.append({'kind':'code','language':lang,'text':'\n'.join(code)});i+=1;continue
  m=re.match(r'^(#{1,4}) (.+)$',line)
  if m:blocks.append({'kind':'heading','level':len(m.group(1)),'text':m.group(2)});i+=1;continue
  if line.startswith('|'):
   table=[]
   while i<len(lines) and lines[i].startswith('|'):
    table.append([s.strip() for s in lines[i].strip().strip('|').split('|')]);i+=1
   assert len(table)>=2 and all(re.fullmatch(r':?-+:?',c) for c in table[1]),table[1]
   blocks.append({'kind':'table','headers':table[0],'rows':table[2:]});continue
  m=re.match(r'^(\d+\. |\- )(.+)$',line)
  if m:blocks.append({'kind':'step' if m.group(1)[0].isdigit() else 'bullet','prefix':m.group(1),'text':m.group(2)});i+=1;continue
  para=[line];i+=1
  while i<len(lines) and lines[i].strip() and not re.match(r'^(#{1,4} |```|\||\- |\d+\. )',lines[i]):para.append(lines[i]);i+=1
  blocks.append({'kind':'paragraph','text':' '.join(para)})
 return blocks
def word_inline(paragraph,text,input_dir):
 for kind,t,target in tokens(text):
  if kind=='link':
   resolved=(input_dir/target).resolve()
   url='https://github.com/yang-jiayi/furusato-fabric-workshop/blob/main/'+resolved.relative_to(ROOT).as_posix() if not target.startswith('http') else target
   rid=paragraph.part.relate_to(url,RT.HYPERLINK,is_external=True)
   hyperlink=OxmlElement('w:hyperlink');hyperlink.set(qn('r:id'),rid)
   run=OxmlElement('w:r');pr=OxmlElement('w:rPr');style=OxmlElement('w:rStyle');style.set(qn('w:val'),'Hyperlink');pr.append(style);run.append(pr)
   node=OxmlElement('w:t');node.text=t;run.append(node);hyperlink.append(run);paragraph._p.append(hyperlink)
  else:
   run=paragraph.add_run(t);run.bold=kind=='bold'
   if kind=='code':run.font.name='Consolas';run.font.size=Pt(9)
   elif kind=='plain':run.font.size=Pt(10)

def canonical(text):return re.sub(r'\s+','',text).translate(str.maketrans({'（':'(', '）':')'}))
def build(input_dir,output):
    input_dir=Path(input_dir).resolve()
    output=Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Use a fresh output directory; preserve earlier rendered evidence.')
    source_hashes={name:hashlib.sha256((input_dir/name).read_bytes()).hexdigest() for name in SOURCES}
    study=validate_summary(json.loads((input_dir/SOURCES[2]).read_text(encoding='utf-8')))
    for name in SOURCES[:2]:
        assert_public_text((input_dir/name).read_text(encoding='utf-8'))
    os.environ.setdefault('SOURCE_DATE_EPOCH',str(study['artifactSourceDateEpoch']))
    input_sha=hashlib.sha256(json.dumps(source_hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    sections=[parse((input_dir/name).read_text(encoding='utf-8')) for name in SOURCES[:2]]
    all_blocks=[b for section in sections for b in section]
    output.mkdir(parents=True,exist_ok=True)
    stage=output
    stem="furusato-data-agent-tuning-"+study["date"].replace("-", "")
    word=stage/(stem+".docx");web=stage/(stem+".html")
    builder=DocumentBuilder(StyleCarrier.resolve(ROOT),stage/'shell.docx')
    doc=builder.document
    for section in doc.sections:
     for part in [section.header,section.footer,section.first_page_header,section.first_page_footer]:
      element=part._element
      for child in list(element):element.remove(child)
      element.append(OxmlElement('w:p'))
    settings=doc.settings.element
    for field in list(settings.findall(qn('w:updateFields'))):settings.remove(field)
    builder.paragraph('Data Agent 実測改善・校正手順',style='Title')
    builder.paragraph('Measured improvements, calibration and proofreading',size=14)
    builder.paragraph(study['date']+' · Furusato Workshop 3.0.0 · Separate dated report')
    for si,blocks in enumerate(sections):
     for b in blocks:
      kind=b['kind']
      if kind=='heading':
       heading=builder.heading(plain(b['text']),min(b['level'],3),new_page=False)
       if b['text'].startswith('測定結果'):
        heading.paragraph_format.page_break_before=True
      elif kind=='table':builder.table([plain(h) for h in b['headers']],[[plain(c) for c in row] for row in b['rows']],caption='測定・手順 / Measurements and procedure',widths=([2.7,1.8,2.1,3.0] if len(b['headers'])==4 else [2.7,6.9]),font_size=8.5,header_size=8.5)
      elif kind=='code':builder.code_block(b['text'],language=b['language'],keep_together=True)
      else:
       p=builder.paragraph(space_after=7);word_inline(p,b.get('prefix','')+b['text'],input_dir)
    builder.paragraph('Source manifest SHA-256: '+input_sha,size=8)
    doc.core_properties.title='Furusato Data Agent measured improvements and calibration — '+study['date']
    doc.core_properties.subject='Bounded content measurements and workshop proofreading procedure'
    # Explicit CJK fonts prevent mixed Japanese/Latin table runs losing glyphs
    # through a Linux substitute for Yu Gothic UI. Office layout stays unverified.
    for style in doc.styles:
        if not hasattr(style,'font'):
            continue
        style.font.name='Noto Sans CJK JP'
        properties=style.element.get_or_add_rPr()
        fonts=properties.find(qn('w:rFonts'))
        if fonts is None:
            fonts=OxmlElement('w:rFonts');properties.append(fonts)
        for attribute in ('w:ascii','w:hAnsi','w:eastAsia','w:cs'):
            fonts.set(qn(attribute),'Noto Sans CJK JP')
    for run in doc.element.iter(qn('w:r')):
        properties=run.find(qn('w:rPr'))
        if properties is None:
            properties=OxmlElement('w:rPr');run.insert(0,properties)
        fonts=properties.find(qn('w:rFonts'))
        mono=fonts is not None and fonts.get(qn('w:ascii'))=='Consolas'
        if fonts is None:
            fonts=OxmlElement('w:rFonts');properties.append(fonts)
        family='Noto Sans Mono CJK JP' if mono else 'Noto Sans CJK JP'
        for attribute in ('w:ascii','w:hAnsi','w:eastAsia','w:cs'):
            fonts.set(qn(attribute),family)
    builder.save(word);apply_japanese_typography(word);normalise_package_metadata(word)
    with zipfile.ZipFile(word) as archive:parts={n:archive.read(n) for n in archive.namelist()}
    for name,blob in parts.items():
     if name.startswith('word/') and name.endswith('.xml'):
      assert b'fldChar' not in blob and b'instrText' not in blob,(name,'dynamic field')
    assert not re.search(rb'<(?:\w+:)?Pages\b',parts['docProps/app.xml'])
    word_xml=etree.fromstring(parts['word/document.xml']);ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    word_text=''.join(word_xml.xpath('//w:t/text()',namespaces=ns))
    for b in all_blocks:
     expected=([*b['headers'],*[cell for row in b['rows'] for cell in row]] if b['kind']=='table' else [b['text']])
     for text in expected:assert canonical(plain(text)) in canonical(word_text),(b['kind'],plain(text)[:70])
    word_sha=hashlib.sha256(word.read_bytes()).hexdigest()
    body=[];toc=[];idx=0
    for blocks in sections:
     for b in blocks:
      lang='ja' if re.search(r'[\u3040-\u30ff\u3400-\u9fff]',b.get('text','')) else 'en'
      kind=b['kind'];attr=f' lang="{lang}"'
      if kind=='heading':
       idx+=1;hid=f'section-{idx}';lvl=min(b['level']+1,4);body.append(f'<h{lvl} id="{hid}">{html_inline(b["text"])}</h{lvl}>');toc.append(f'<a href="#{hid}">{html.escape(plain(b["text"]))}</a>')
      elif kind=='table':
       body.append('<div class="scroll"><table><thead><tr>'+''.join('<th scope="col">'+html_inline(v)+'</th>' for v in b['headers'])+'</tr></thead><tbody>')
       body.extend('<tr>'+''.join('<td>'+html_inline(v)+'</td>' for v in row)+'</tr>' for row in b['rows']);body.append('</tbody></table></div>')
      elif kind=='code':body.append('<pre><code>'+html.escape(b['text'])+'</code></pre>')
      else:body.append('<p'+attr+(' class="step"' if kind in ['step','bullet'] else '')+'>'+html.escape(b.get('prefix',''))+html_inline(b['text'])+'</p>')
    html_text='''<!doctype html>
    <html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Furusato Data Agent 実測改善・校正手順 — REPORT_DATE</title><link rel="icon" href="data:,">
    <meta name="source-manifest-sha256" content="INPUT"><meta name="paired-word-sha256" content="WORD">
    <style>
    :root{font-family:"Yu Gothic UI","Noto Sans CJK JP","Segoe UI",sans-serif;color:#203048;background:#eef3f9;line-height:1.75}*{box-sizing:border-box}body{max-width:1120px;margin:0 auto;padding:28px}header,main,nav{background:#fff;border-radius:10px;padding:26px;margin-bottom:20px}header{border-top:7px solid #174c88}h1{font-size:1.85rem;margin:0 0 8px}h2{font-size:1.55rem;color:#174c88;margin-top:30px}h3{font-size:1.24rem;color:#174c88;border-top:1px solid #dce5ee;padding-top:20px;margin-top:30px}p{margin:12px 0}nav{display:grid;gap:5px;font-size:.9rem}a{color:#175c9b;text-decoration-thickness:1px;text-underline-offset:3px}a:focus-visible{outline:3px solid #0f6cbd;outline-offset:3px}.scroll{overflow-x:auto;margin:20px 0}table{border-collapse:collapse;width:100%;min-width:660px;font-size:.87rem;line-height:1.6}th,td{border:1px solid #d6dfea;padding:11px;vertical-align:top;text-align:left}th{background:#174c88;color:#fff}tbody tr:nth-child(even){background:#eef3f9}code{font-family:Consolas,"Noto Sans Mono",monospace;background:#f1f5fa;padding:1px 3px;overflow-wrap:anywhere}pre{padding:16px;background:#f1f5fa;border-left:4px solid #0f6cbd;overflow:auto}pre code{padding:0;overflow-wrap:normal}.step{padding-left:12px;border-left:3px solid #dce5ee}footer{font-size:.8rem;overflow-wrap:anywhere;color:#52667f}button{font:inherit;background:#174c88;color:#fff;border:0;border-radius:5px;padding:7px 12px;cursor:pointer}@media(max-width:600px){body{padding:12px}header,main,nav{padding:18px}h1{font-size:1.45rem}h2{font-size:1.3rem}}@media print{body{max-width:none;padding:0;background:#fff}nav,.print{display:none}header,main{padding:0;margin:0;border-radius:0}h2,h3{break-after:avoid}tr,pre{break-inside:avoid}table{min-width:0}a{color:inherit}header{border-top:0}}
    </style></head><body><header><h1>Data Agent 実測改善・校正手順</h1><p lang="en">Measured improvements, calibration and proofreading — Furusato Workshop 3.0.0</p><p>REPORT_DATE · 別日付レポート / Separate dated report</p><button class="print" onclick="window.print()">印刷 / Print</button></header>
    <nav aria-label="目次 / Contents">TOC</nav><main>BODY</main><footer>Source manifest SHA-256: INPUT<br>Paired Word SHA-256: WORD</footer></body></html>
    '''.replace('REPORT_DATE',study['date']).replace('INPUT',input_sha).replace('WORD',word_sha).replace('TOC',''.join(toc)).replace('BODY','\n'.join(body))
    web.write_text(html_text,encoding='utf-8')
    from lxml import html as lh
    parsed=lh.fromstring(html_text);rendered=''.join(parsed.xpath('//main//text()'))
    for b in all_blocks:
     expected=([*b['headers'],*[cell for row in b['rows'] for cell in row]] if b['kind']=='table' else [b['text']])
     for text in expected:assert canonical(plain(text)) in canonical(rendered),(b['kind'],plain(text)[:70])
    for text in [word_text,rendered]:
     for bad in [r'/workspace/',r'/var/tmp/',r'\b(?:T|B|Q)\d{2}\b',r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b']:
      assert not re.search(bad,text),bad
    assert b'General' in parts['docProps/custom.xml']
    validation={'schema':'furusato-measured-report-artifact-validation/v1','date':study['date'],'sourceFilesSha256':source_hashes,'sourceDateEpoch':int(os.environ['SOURCE_DATE_EPOCH']),'sourceManifestSha256':input_sha,'contentBlockCount':len(all_blocks),'markdownToWordContentParity':True,'markdownToHtmlContentParity':True,'conditionDenominatorsValidated':True,'publicTextLeakageChecksPassed':True,'generalClassificationNormalized':True,'dynamicWordFields':0,'fakeOfficePageCountPresent':False,'microsoftWordRenderChecked':False,'htmlBrowserChecked':False,'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [word,web]}}
    (stage/'artifact-validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    (stage/'shell.docx').unlink()
    return validation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True,help='Reviewed public summary and shared Markdown directory.')
    parser.add_argument('--out',type=Path,required=True,help='Fresh external staging directory.')
    args=parser.parse_args()
    print(json.dumps(build(args.input_dir,args.out),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
