"""Integrity boundaries for the explicit standalone current delivery route."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools/docs'),str(ROOT/'tools/html')]
import current_delivery as delivery
from furusato_html.preview30 import render
from furusato_docs import preview30_release as release


class CurrentDeliveryTests(unittest.TestCase):
    def test_paired_renderer_still_requires_original_release_binding(self):
        with self.assertRaises(ValueError):
            render(None,None,None,None,None,{'version':'3.0.0'},'a'*64,ROOT,release_profile=release.V300)

    def test_standalone_renderer_rejects_paired_digest_or_unbound_model(self):
        for metadata, word_sha in [
            ({'version':'3.0.0','participantEdition':True,'deliveryMode':'html-lab'},None),
            ({'version':'3.0.0','participantEdition':True,'deliveryMode':'html-lab','currentArtifactSet':{'sourceCommit':'a'*40}},'b'*64),
        ]:
            with self.subTest(metadata=metadata,word_sha=word_sha),self.assertRaises(ValueError):
                render(None,None,None,None,None,metadata,word_sha,ROOT,release_profile=release.V300,delivery_mode='html-lab')

    def test_packaging_requires_completed_browser_checks_on_exact_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/delivery.HTML_NAME
            path.write_text('first html')
            sha=sha256(path.read_bytes()).hexdigest()
            receipt={'schemaVersion':'furusato-current-html-lab-validation/v1','deliveryMode':'html-lab',
                     'static':{'passed':True,'htmlSha256':sha},'browser':{'passed':False,'htmlSha256':sha}}
            with self.assertRaises(ValueError):delivery.require_validated(path,receipt)
            receipt['browser']['passed']=True
            delivery.require_validated(path,receipt)
            path.write_text('modified html')
            with self.assertRaises(ValueError):delivery.require_validated(path,receipt)

    def test_unexpected_private_lab_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'README.md').write_text('Expected guide')
            delivery.checked_lab_files(root,{'README.md'})
            for name in ('.env','storage-state.json','extra.md'):
                path=root/name
                path.write_text('private test fixture')
                with self.subTest(name=name),self.assertRaises(ValueError):
                    delivery.checked_lab_files(root,{'README.md'})
                path.unlink()

    def test_unapproved_private_authoring_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            directory=root/'tools/docs';directory.mkdir(parents=True)
            (directory/'current_delivery.py').write_text('# known authoring source')
            self.assertEqual(delivery.approved_doc_files(root,set()),{'tools/docs/current_delivery.py'})
            for name in ('.env','storage-state.json','unreviewed-helper.py'):
                path=directory/name
                path.write_text('private test fixture')
                with self.subTest(name=name),self.assertRaises(ValueError):
                    delivery.approved_doc_files(root,set())
                path.unlink()

    def test_expected_lab_filename_cannot_hide_appended_private_content(self):
        with tempfile.TemporaryDirectory() as temp:
            lab=Path(temp);path=lab/'README.md';expected=b'Generated current index\n'
            path.write_bytes(expected)
            delivery.checked_lab_files(lab,{'README.md':expected})
            path.write_bytes(expected+b'PRIVATE TEST FIXTURE\n')
            with self.assertRaises(ValueError):delivery.checked_lab_files(lab,{'README.md':expected})

    def test_supplied_manifest_cannot_bypass_private_path_guard(self):
        for name in ('tools/docs/.env','tools/data-agent/private/answer.json','tools/docs/storage-state.json'):
            with self.subTest(name=name),self.assertRaises(ValueError):
                delivery.validate_source_manifest_paths(ROOT,{'files':{name:'0'*64}})

    def test_external_staged_lab_links_use_the_virtual_repository_layout(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'repo';root.mkdir();(root/'workshop/v3.0.0-preview').mkdir(parents=True)
            lab=Path(temp)/'stage/Lab';lab.mkdir(parents=True)
            (lab/'README.md').write_text('[HTML](../docs/'+delivery.HTML_NAME+')\n[Source](../workshop/v3.0.0-preview)')
            source='workshop/v3.0.0-preview/notebook.txt'
            files={'source/'+source:b'test public source'}
            delivery.add_lab_aliases(files,root,lab,{source:'0'*64},b'validated html')
            self.assertEqual(files['docs/'+delivery.HTML_NAME],b'validated html')
            self.assertEqual(files[source],b'test public source')

    def test_extracted_lab_links_must_resolve_inside_actual_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            lab=root/'Lab';lab.mkdir()
            (lab/'README.md').write_text('[Guide](../docs/guide.html)')
            with self.assertRaises(ValueError):delivery.validate_packaged_links(root)
            (root/'docs').mkdir();(root/'docs/guide.html').write_text('actual html')
            self.assertEqual(delivery.validate_packaged_links(root),1)


if __name__=='__main__':unittest.main()
