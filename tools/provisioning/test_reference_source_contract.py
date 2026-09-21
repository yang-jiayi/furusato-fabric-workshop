"""Offline regression coverage for the maintained source-contract inputs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import reference_assets

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/data-agent/source-contract"
BUNDLE = ROOT / "workshop/v2.7.0/provisioning/bundle"


class ReferenceSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((SOURCE / "contract.json").read_text("utf-8"))
        cls.generated = reference_assets.build_assets(ROOT)
        cls.template = json.loads(cls.generated["ai-reference/ontology-template.json"])
        cls.metadata = json.loads(cls.generated["ai-reference/source-metadata.json"])

    def patched_contract(self, contract):
        read_text = Path.read_text

        def read(path, *args, **kwargs):
            if path == SOURCE / "contract.json":
                return json.dumps(contract)
            return read_text(path, *args, **kwargs)

        return patch.object(Path, "read_text", read)

    def test_every_generated_asset_is_byte_identical_to_the_packaged_runtime(self):
        independently_frozen = {
            "ai-reference/global-instructions.txt",
            "ai-reference/global-profile.json",
        }
        packaged = {
            path.relative_to(BUNDLE).as_posix()
            for path in (BUNDLE / "ai-reference").rglob("*")
            if path.is_file()
        }
        self.assertEqual(set(self.generated), packaged - independently_frozen)
        for name, text in self.generated.items():
            with self.subTest(asset=name):
                self.assertEqual(text.encode("utf-8"), (BUNDLE / name).read_bytes())
        self.assertEqual(self.generated, reference_assets.build_assets(ROOT))

    def test_source_metadata_reads_only_the_maintained_contract_inputs(self):
        reads = set()
        read_text, read_bytes = Path.read_text, Path.read_bytes

        def text(path, *args, **kwargs):
            reads.add(path)
            return read_text(path, *args, **kwargs)

        def raw(path):
            reads.add(path)
            return read_bytes(path)

        with patch.object(Path, "read_text", text), patch.object(Path, "read_bytes", raw):
            actual = reference_assets.source_metadata(ROOT, self.template)
        self.assertEqual(actual, self.metadata)
        self.assertEqual(
            {path.name for path in reads if path.parent == SOURCE},
            {
                "contract.json", "entrypoint-schema.json", "field-descriptions.json",
                "trace-and-operational-descriptions.json",
                "lakehouse-instructions.txt", "kusto-instructions.txt",
            },
        )
        self.assertFalse(any("profiles" in path.parts for path in reads))

    def test_contract_has_no_global_baseline_or_candidate_identity_dependency(self):
        self.assertEqual(
            set(self.contract),
            {"schemaVersion", "instructions", "sourceDescriptions", "objectDescriptions"},
        )
        self.assertEqual(self.contract["schemaVersion"], reference_assets.SOURCE_CONTRACT_SCHEMA)
        self.assertEqual(set(self.contract["instructions"]), {"lakehouse", "kusto"})
        self.assertEqual(
            set(self.contract["sourceDescriptions"]), {"lakehouse_tables", "kusto", "ontology"}
        )
        self.assertEqual(
            set(self.contract["objectDescriptions"]), {"MunicipalityStatic", "MunicipalityById"}
        )

    def test_source_instruction_bytes_and_hashes_match_runtime_metadata(self):
        for source, key in (("lakehouse_tables", "lakehouse"), ("kusto", "kusto")):
            record = self.contract["instructions"][key]
            raw = (SOURCE / record["file"]).read_bytes()
            with self.subTest(source=source):
                self.assertEqual(set(record), {"file", "sha256"})
                self.assertEqual(reference_assets.digest(raw), record["sha256"])
                self.assertEqual(raw, self.metadata[source]["instructions"].encode("utf-8"))

    def test_three_source_claim_requires_completed_same_id_instance_queries(self):
        text = (BUNDLE / "ai-reference/global-instructions.txt").read_text("utf-8")
        section = text.split("CROSS-SOURCE LEADER OVERRIDE\n", 1)[1].split(
            "\nROUTE BEFORE TOOLS", 1
        )[0]
        self.assertIn(
            "After all three current-turn same-ID queries succeed, including an Ontology instance path",
            section,
        )
        self.assertIn(
            "Missing/unused/failed source or field=incomplete: omit success heading; never impute.",
            section,
        )
        fields = section.split("Then one presentation table (not SQL JOIN/formatter): ", 1)[1]
        fields = fields.split(". Four metrics mandatory", 1)[0].split(", ")
        self.assertEqual(fields, [
            "MunicipalityId", "MunicipalityName", "RawObservationCount",
            "RawObservedAmountYen", "MunicipalityStaticCount", "MunicipalityStaticTotalYen",
            "MunicipalityStoredNationwideAmountRank", "PrefectureId", "PrefectureName",
            "EventhouseSource", "LakehouseSource", "OntologySource", "EventhouseScope",
            "LakehouseScope", "RawDuplicateCaveat",
        ])

    def test_purely_static_routing_never_suppresses_cross_source_ontology(self):
        text = self.metadata["lakehouse_tables"]["instructions"]
        self.assertIn("For purely static place metrics", text)
        self.assertIn("This never suppresses a required Ontology step in cross-source operational reconciliation", text)
        self.assertIn("let the root obtain current Ontology instance-path proof", text)
        self.assertIn("their SQL presence never claims that Eventhouse or Ontology executed", text)

    def test_reference_presentation_and_refusal_rules_stay_hash_pinned_and_bounded(self):
        raw = (BUNDLE / "ai-reference/global-instructions.txt").read_bytes()
        text = raw.decode("utf-8")
        profile = json.loads((BUNDLE / "ai-reference/global-profile.json").read_text("utf-8"))
        self.assertEqual(reference_assets.digest(raw), profile["sha256"])
        self.assertLessEqual(len(text), 15000)
        self.assertNotIn(b"\r", raw)
        self.assertIn("Caption each table: actual Source, scope, grain, units.", text)
        self.assertIn(
            "Offer only cumulative donation amount and rank in an explicitly named Static 2025 UTC scope; "
            "do not broaden this alternative.",
            text,
        )
        self.assertIn("A platform error is not a normal refusal; do not bypass it.", text)

    def test_changed_instruction_hash_is_rejected_without_fallback(self):
        for key in ("lakehouse", "kusto"):
            contract = copy.deepcopy(self.contract)
            contract["instructions"][key]["sha256"] = "0" * 64
            with self.subTest(source=key), self.patched_contract(contract):
                with self.assertRaisesRegex(ValueError, "Unpinned structural source instructions"):
                    reference_assets.source_metadata(ROOT, self.template)

    def test_missing_instruction_is_rejected_without_using_a_historical_profile(self):
        read_bytes = Path.read_bytes
        for key in ("lakehouse", "kusto"):
            missing = SOURCE / self.contract["instructions"][key]["file"]

            def read(path):
                if path == missing:
                    raise FileNotFoundError(path)
                return read_bytes(path)

            with self.subTest(source=key), patch.object(Path, "read_bytes", read):
                with self.assertRaises(FileNotFoundError):
                    reference_assets.source_metadata(ROOT, self.template)

    def test_unknown_source_contract_schema_is_rejected(self):
        contract = {**self.contract, "schemaVersion": "unsupported"}
        with self.patched_contract(contract):
            with self.assertRaisesRegex(ValueError, "Unsupported structural source contract"):
                reference_assets.source_metadata(ROOT, self.template)

    def test_schema_describes_interfaces_without_overriding_runtime_selection(self):
        schema = json.loads((SOURCE / "entrypoint-schema.json").read_text("utf-8"))
        self.assertTrue(all("selected" not in obj for obj in schema["objects"].values()))
        self.assertEqual(
            set(self.metadata["lakehouse_tables"]["referenceObjects"]),
            set(reference_assets.SQL_SELECTED),
        )
        trace = self.metadata["lakehouse_tables"]["referenceObjects"]["DonationTraceById"]
        self.assertEqual(len(trace["fields"]), 30)
        self.assertIn("non-additive", trace["fieldDescriptions"]["DonationAmountYen"])


if __name__ == "__main__":
    unittest.main()
