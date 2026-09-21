"""Classification checks must reject private identifiers without publishing them."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))

import validate_docs
from furusato_docs import oox, validators


class LabelIdentifierPrivacyTests(unittest.TestCase):
    identifier = "12345678-9abc-4def-8123-0123456789ab"
    fingerprint = hashlib.sha256(identifier.encode("ascii")).hexdigest()

    def setUp(self):
        self.catalogue = patch.object(
            validators, "FORBIDDEN_LABEL_GUID_HASHES", frozenset({self.fingerprint})
        )
        self.catalogue.start()
        self.addCleanup(self.catalogue.stop)

    def test_case_braces_and_embedded_custom_property_names(self):
        for value in (
            self.identifier,
            self.identifier.upper(),
            "{" + self.identifier + "}",
            "MSIP_Label_" + self.identifier.upper() + "_SiteId",
            "f" + self.identifier + "e",
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    validators.forbidden_label_guid_fingerprints(value),
                    (self.fingerprint,),
                )

    def test_duplicates_are_reported_once(self):
        self.assertEqual(
            validators.forbidden_label_guid_fingerprints(
                self.identifier + " " + self.identifier.upper()
            ),
            (self.fingerprint,),
        )

    def test_approved_classification_and_unrelated_guids_are_not_rejected(self):
        text = validators.EXPECTED_LABEL_ID + validators.EXPECTED_SITE_ID
        text += " 00000000-0000-0000-0000-000000000000 "
        self.assertEqual(validators.forbidden_label_guid_fingerprints(text), ())

    def test_xml_and_relationship_failures_never_echo_the_identifier(self):
        report = validators.Report("synthetic package")
        validators.check_no_foreign_label_guids(
            {
                "docProps/custom.xml": self.identifier.upper().encode("ascii"),
                "_rels/.rels": self.identifier.encode("ascii"),
                "word/media/image.bin": self.identifier.encode("ascii"),
            },
            report,
            scope="fixture",
        )
        self.assertEqual([item.check for item in report.failures], ["fixture.foreignLabels"])
        message = report.failures[0].message
        self.assertIn("docProps/custom.xml:sha256:" + self.fingerprint, message)
        self.assertIn("_rels/.rels:sha256:" + self.fingerprint, message)
        self.assertNotIn(self.identifier, message.lower())
        self.assertNotIn("image.bin", message)

    def test_clean_package_still_passes(self):
        report = validators.Report("clean package")
        validators.check_no_foreign_label_guids(
            {"docProps/custom.xml": validators.EXPECTED_LABEL_ID.encode("ascii")},
            report,
            scope="fixture",
        )
        self.assertTrue(report.passed)
        self.assertEqual(report.findings[0].check, "fixture.foreignLabels")

    def test_carrier_reuses_the_same_redacted_check_including_json_parts(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "carrier.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("metadata.json", '{"id":"' + self.identifier.upper() + '"}')
                output.writestr(
                    "parts/docMetadata/LabelInfo.xml",
                    validators.EXPECTED_LABEL_ID + validators.EXPECTED_SITE_ID,
                )
                output.writestr("parts/docProps/custom.xml", oox.custom_properties_xml())
            report = validators.Report("synthetic carrier")
            validate_docs._check_carrier_labels(archive, report)
        failures = [item for item in report.failures if item.check == "toolchain.carrierLabels"]
        self.assertEqual(len(failures), 1)
        self.assertIn(self.fingerprint, failures[0].message)
        self.assertNotIn(self.identifier, failures[0].message.lower())


if __name__ == "__main__":
    unittest.main()
