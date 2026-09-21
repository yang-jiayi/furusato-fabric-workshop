"""Offline unified-profile contracts; service fixtures contain no cloud data."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import socket
from types import ModuleType
import unittest
from unittest.mock import patch

import reference_agent as agent
import reference_kql
import unified_agent as unified
import workshop_runtime as runtime
from test_reference_architecture import AgentServiceFixture

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "workshop" / "v2.7.0" / "provisioning" / "bundle"
CORE_PATH = (
    BUNDLE / "data-agent" / "Files" / "Config" / "published"
    / "ontology-{{name.ontology}}" / "datasource.json"
)


class UnifiedAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bundle = {
            path.relative_to(BUNDLE).as_posix(): path.read_bytes().decode("utf-8")
            for path in (BUNDLE / "ai-reference").rglob("*") if path.is_file()
        }
        stage = "data-agent/Files/Config/published/stage_config.json"
        bundle[stage] = BUNDLE.joinpath(*stage.split("/")).read_bytes().decode("utf-8")
        cls.reference = runtime.load_reference_assets({"bundle": bundle})
        cls.core = json.loads(CORE_PATH.read_bytes())
        cls.profile = unified.load_profile_files(ROOT)
        cls.assets = cls.build()

    @classmethod
    def build(cls, reference=None, core=None, profile=None):
        return unified.build_unified_assets(
            cls.reference if reference is None else reference,
            cls.core if core is None else core,
            profile_files=cls.profile if profile is None else profile,
        )

    def test_explicit_profile_structure_flags_lengths_and_hash_binding(self):
        report = unified.verify_unified_assets(self.assets)
        self.assertEqual(report["mode"], "unified")
        self.assertFalse(report["acceptanceClaimed"])
        self.assertLessEqual(report["globalCharacters"], 15_000)
        self.assertEqual(report["profileRevision"], 13)
        self.assertEqual(report["kustoFewShotCount"], 3)
        self.assertEqual(set(self.assets), unified.ASSET_FIELDS)
        self.assertEqual(set(unified.INSTRUCTION_FILES), {"global", "lakehouse_tables", "kusto"})
        self.assertEqual(set(self.profile), {
            "manifest.json", "global-instructions.txt", "lakehouse-instructions.txt",
            "kusto-instructions.txt", "kusto-fewshots.json",
        })
        contract = self.assets["contract"]
        self.assertEqual(contract["schemaVersion"], unified.SCHEMA)
        self.assertEqual(contract["agentTargetRole"], "existing-primary")
        self.assertEqual(contract["ontologyBindingRole"], "teachingOntology")
        self.assertEqual(contract["ontologyAction"], "reuse-only")
        self.assertEqual(contract["ontologyInstructionPolicy"], "preserve-null-use-global")
        self.assertFalse(contract["enabledByDefault"])
        self.assertEqual(self.assets["globalProfile"]["status"], "candidate")
        self.assertIs(self.assets["stageConfig"]["experimental"]["codeInterpreterEnabled"], True)
        self.assertIs(self.assets["stageConfig"]["experimental"]["enableExperimentalFeatures"], True)
        expected_stage = copy.deepcopy(self.reference["stageConfig"])
        expected_stage["aiInstructions"] = self.profile["global-instructions.txt"]
        expected_stage["experimental"].update({"codeInterpreterEnabled": True, "enableExperimentalFeatures": True})
        self.assertEqual(self.assets["stageConfig"], expected_stage)
        accepted_reference = copy.deepcopy(self.reference)
        accepted_reference["globalProfile"]["status"] = "accepted"
        self.assertEqual(self.build(reference=accepted_reference)["globalProfile"]["status"], "candidate")
        for name in unified.INSTRUCTION_FILES.values():
            text = self.profile[name]
            with self.subTest(name=name):
                self.assertTrue(text.strip())
                self.assertLessEqual(len(text), 15_000)
                self.assertTrue(text.endswith("\n"))
                self.assertNotIn("\r", text)
                self.assertFalse(text.startswith("\ufeff"))
                self.assertEqual(
                    hashlib.sha256(text.encode()).hexdigest(),
                    self.assets["profileManifest"]["files"][name]["sha256"],
                )
        restored = json.loads(json.dumps(self.assets))
        self.assertEqual(unified.verify_unified_assets(restored), report)

    def test_full_ontology_inventory_comes_from_core_not_reference_path_template(self):
        source = self.assets["sources"]["ontology"]
        expected = [
            {"path": [["Entity", node["display_name"]]], "description": node["description"]}
            for node in self.core["elements"]
        ]
        self.assertEqual(source["elements"], expected)
        self.assertEqual(source["description"], self.core["userDescription"])
        self.assertIsNone(self.core["dataSourceInstructions"])
        self.assertIsNone(source["instructions"])
        self.assertNotEqual(source["elements"], self.reference["sources"]["ontology"]["elements"])
        properties = {
            entry["path"][0][1]: entry["description"].split(",") for entry in source["elements"]
        }
        self.assertEqual(len(properties), 10)
        self.assertEqual(sum(map(len, properties.values())), 73)
        self.assertIn("IncomingDonationAmountYen", properties["Municipality"])
        self.assertNotIn("ontologyTemplate", self.assets)
        self.assertNotIn("reference_ontology", self.assets["moduleSources"])
        self.assertNotIn("agentOntologyNameTemplate", self.assets["contract"])
        self.assertEqual(set(self.assets["sources"]), set(agent.KINDS))
        self.assertNotIn("workspaceId", json.dumps(source))
        self.assertNotIn("artifactId", json.dumps(source))

        class UnusablePathTemplate:
            def __deepcopy__(self, memo):
                raise AssertionError("Reference path template must not be consumed.")

        reference = copy.deepcopy(self.reference)
        reference["ontologyTemplate"] = UnusablePathTemplate()
        self.assertEqual(self.build(reference=reference), self.assets)

    def test_all_full_model_relationships_and_property_counts_match_canonical_template(self):
        template = json.loads((
            ROOT / "workshop" / "v2.7.0" / "ontology" / "ontology-full-definition-template.json"
        ).read_bytes())
        self.assertEqual(self.assets["contract"]["expectedOntologyContract"], template["expectedContract"])
        entities = {
            part["content"]["id"]: part["content"]
            for part in template["parts"] if part["path"].startswith("EntityTypes/")
            and part["path"].count("/") == 2 and part["path"].endswith("/definition.json")
        }
        self.assertEqual(sum(len(entity["properties"]) for entity in entities.values()), 72)
        self.assertEqual(sum(len(entity.get("timeseriesProperties", [])) for entity in entities.values()), 1)
        relationships = [
            part["content"] for part in template["parts"] if part["path"].startswith("RelationshipTypes/")
            and part["path"].count("/") == 2 and part["path"].endswith("/definition.json")
        ]
        self.assertEqual(len(relationships), 15)
        text = self.assets["stageConfig"]["aiInstructions"]
        for relation in relationships:
            source = entities[relation["source"]["entityTypeId"]]["name"]
            target = entities[relation["target"]["entityTypeId"]]["name"]
            self.assertIn(f"{source} -{relation['name']}-> {target}", text)
        actual = {entry["path"][0][1]: entry["description"].split(",") for entry in self.assets["sources"]["ontology"]["elements"]}
        for entity in entities.values():
            self.assertEqual(
                actual[entity["name"]],
                [prop["name"] for prop in entity["properties"] + entity.get("timeseriesProperties", [])],
            )

    def test_reference_selection_sql_kql_and_fewshots_are_preserved(self):
        for kind in ("lakehouse_tables", "kusto"):
            before = {key: value for key, value in self.reference["sources"][kind].items() if key != "instructions"}
            excluded = {"instructions", "fewShots"} if kind == "kusto" else {"instructions"}
            after = {key: value for key, value in self.assets["sources"][kind].items() if key not in excluded}
            self.assertEqual(before, after)
            self.assertEqual(
                unified.sha256_json(after), self.assets["profileManifest"]["referenceSelectionsSha256"][kind],
            )
        self.assertEqual(self.assets["sqlDdl"], self.reference["sqlDdl"])
        self.assertEqual(self.assets["kqlFunctions"], self.reference["kqlFunctions"])
        for name in unified.MODULES:
            self.assertEqual(self.assets["moduleSources"][name], self.reference["moduleSources"][name])
        self.assertEqual(set(runtime.load_reference_modules(self.assets)), set(unified.MODULES))
        self.assertNotIn("fewShots", self.reference["sources"]["kusto"])
        self.assertEqual(
            self.assets["sources"]["kusto"]["fewShots"], json.loads(self.profile["kusto-fewshots.json"]),
        )
        selections = self.assets["sources"]["lakehouse_tables"]["elements"]
        self.assertEqual(sum(entry["path"][-1][0] == "Table" for entry in selections), 11)
        self.assertEqual(sum(entry["path"][-1][0] == "Column" for entry in selections), 88)
        self.assertEqual(
            {entry["path"][-1][1]: entry["path"][-1][0] for entry in selections if entry["path"][0] == ["Schema", "agent_ref"]},
            unified.SQL_SELECTION,
        )

    def test_written_helper_signatures_and_all_return_fields_match_real_contracts(self):
        contracts = reference_kql.validate_function_contracts(self.assets["kqlFunctions"])
        kusto = self.profile["kusto-instructions.txt"]
        for name, contract in contracts.items():
            with self.subTest(function=name):
                match = re.search(rf"{name} returns (?:one row with )?(\d+) fields: ([^\n]+)\.", kusto)
                self.assertIsNotNone(match)
                fields = match.group(2).split(", ")
                self.assertEqual(fields, [field for field, _ in contract.return_schema])
                self.assertEqual(int(match.group(1)), len(fields))
                self.assertEqual(
                    re.findall(r"(\w+):datetime\s*=\s*datetime\(null\)", contract.definition.parameters),
                    ["StartUtc", "EndUtc"],
                )
        lakehouse = self.profile["lakehouse-instructions.txt"]
        objects = self.assets["sources"]["lakehouse_tables"]["referenceObjects"]
        for name in ("MunicipalityById", "DonationTraceById"):
            match = re.search(rf"{name} returns: ([^\n]+)\.", lakehouse)
            self.assertEqual(match.group(1).split(", "), [field for field, _ in objects[name]["fields"]])
        ddl = dict(self.assets["sqlDdl"])
        self.assertIn("@RequestedMunicipalityId varchar(64)", ddl["040_municipality_by_id.sql"])
        self.assertIn("MunicipalityById(@RequestedMunicipalityId varchar(64))", lakehouse)
        self.assertIn("@RequestedDonationId bigint", ddl["060_donation_trace_by_id.sql"])
        self.assertIn("DonationTraceById(@RequestedDonationId bigint)", lakehouse)
        projections = re.findall(r'format_datetime\((\w+), "([^"]+)"\)', kusto)
        self.assertEqual(len(projections), 4)
        self.assertEqual({format_ for _, format_ in projections}, {"yyyy-MM-dd HH:mm:ss.fffffff"})
        native_dates = {field for field, type_ in contracts["AgentFileRunSummary"].return_schema if type_ == "datetime"}
        self.assertEqual({field for field, _ in projections}, native_dates)
        for field, _ in projections:
            self.assertIn(
                f'{field} = iff(isnull({field}), "", strcat(replace_string(format_datetime('
                f'{field}, "yyyy-MM-dd HH:mm:ss.fffffff"), " ", "T"), "Z"))', kusto,
            )

    def test_static_operational_graph_ci_and_output_semantics_are_explicit(self):
        global_text = self.profile["global-instructions.txt"]
        required = (
            "full Static 2025 UTC snapshot", "NOT a calendar-year filter",
            "_WorkshopGenerationId", "independent August 2026 raw observations",
            "SUM(ObservationCount)", "SUM(ObservedAmountYen)", "possible duplicates",
            "WindowIsValid=true", "Helpers have no HasMatches", "confirmed zero",
            "Missing grouped rows need an exact-ID scalar aggregate",
            "SourceFile, WorkshopRunId AND ParticipantAlias",
            "literal, untranslated headers: SourceFile, WorkshopRunId, ParticipantAlias, FirstObservedAtUtc, LastObservedAtUtc",
            "including the literal '(reverse)' suffix",
            "ISO-8601 UTC", "separate T/Z concatenation", "leading zeros",
            "BigInt as exact integers (never floats)", "neighborhood",
            "Request GQL paths/instance IDs for Donation",
            "ALL approved Agent sources lack EventID", "EventID-deduplicated",
            "Donor residence is modeled at Prefecture", "Never add the roles or infer their overlap",
            "catalog registration ONLY", "native", "relationship COUNT",
            "ComparisonStatus: Incomplete", "MissingEvidence", "All FOUR metrics",
            "Never calculate, echo or restate a combined static-plus-operational value",
            "Code Interpreter (Preview)", "post-query", "full-scope aggregates",
            "show executed Python plus returned output",
            "chart specification", "not execution", "CI was not completed",
            "browse external sources", "unselected data", "private attributes",
            "TopN/sample cannot establish full-population",
            "normal lookup of an explicitly requested synthetic record ID is allowed",
            "Do not bypass a platform block", "personal income, tax, deduction, wealth",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertTrue(phrase in global_text, f"Missing semantic instruction: {phrase}")
        self.assertTrue(global_text.endswith("All timestamps are UTC.\n"))
        refusal = global_text.split("INCOMPATIBLE ADDITION\n", 1)[1].split("\nCODE INTERPRETER:", 1)[0]
        self.assertIn("Recipient schema: Donation -DonationToMunicipality-> Municipality", refusal)
        texts = "\n".join(self.profile[name] for name in unified.INSTRUCTION_FILES.values())
        self.assertNotRegex(texts, r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
        self.assertNotRegex(texts, r"https?://|DA_Furusato_\d|ONT_Furusato_\d|\b(?:80000|15000|95000)\b")

    def test_answer_footer_preserves_owners_rank_scope_and_no_query_exemptions(self):
        text = self.profile["global-instructions.txt"]
        footer = text.split("ANSWER EVIDENCE FOOTER\n", 1)[1].split("\nOWNERSHIP AND ROUTING", 1)[0]
        for phrase in (
            "including brief ones", "Source | Scope | Metric | Unit",
            "add RankScope for ranks", "every actual owner",
            "Lakehouse SQL, Eventhouse KQL, Ontology", "one row per owner",
            "DatasetScope is not RankScope", "before the final UTC sentence",
            "incompatible-addition frame, supplied examples, clarifications and refusals",
            "never invent source execution",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, footer)
        self.assertLess(text.index("SAFETY BEFORE TOOLS"), text.index("ANSWER EVIDENCE FOOTER"))

    def test_confirmation_gate_preserves_consent_scope_cancellation_and_safe_defaults(self):
        text = self.profile["global-instructions.txt"]
        gate = text.split("CONFIRMATION GATE\n", 1)[1].split("\nANSWER EVIDENCE FOOTER", 1)[0]
        for phrase in (
            "Person wealth/poverty/tax rankings ALWAYS need clarification",
            "tax paid is not donation amount", "No inference",
            "ONE filled proposal", "Static 2025 UTC snapshot",
            "rank donors by cumulative donation amount for <scope>",
            "Default=all donors; geography=residence unless specified",
            "No SQL/KQL/GQL/CI before explicit yes to pending proposal",
            "Pending-scope edits require reconfirmation, no tools",
            "No/cancel clears it",
            "Only unrelated clear requests run directly and clear old proposals",
            "Never infer wealth/poverty", "platform safety wins",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, gate)
        self.assertLess(text.index("SAFETY BEFORE TOOLS"), text.index("CONFIRMATION GATE"))
        self.assertLess(text.index("CONFIRMATION GATE"), text.index("OWNERSHIP AND ROUTING"))
        self.assertIn("inference without querying or estimating", text)
        self.assertIn("Do not bypass a platform block, rephrase a blocked inference", text)

    def test_confirmation_does_not_remove_trace_identity_or_raw_metric_output_contracts(self):
        text = self.profile["global-instructions.txt"]
        self.assertIn("Final trace answers list all eight ID roles (both Prefecture IDs and CategoryId)", text)
        self.assertIn("Keep all 30 fields and all Supplier rows, including nulls", text)
        self.assertIn("Never sum the repeated DonationAmountYen across Suppliers", text)
        self.assertIn("report BOTH full-scope raw metrics (count/JPY) first", text)
        self.assertIn("WindowIsValid=true", text)

    def test_gift_fidelity_applies_to_headings_rows_and_caveats_without_changing_donation_receipts(self):
        text = self.profile["global-instructions.txt"]
        sql = self.profile["lakehouse-instructions.txt"]
        self.assertIn('Use "selected gift" everywhere, never received/delivered', text)
        self.assertIn("later caveats do not excuse receipt claims", text)
        self.assertIn("Check every Gift reference says selection, not receipt", text)
        for phrase in (
            "including in a heading, bullet or summary",
            "not donation money received by a recipient Municipality",
            'use "selected gift", not "received gift"',
            "Say actual receipt is not established",
            "Do not copy a date from an Ontology JSON mirror",
            "requested extras require a separate successful approved SQL query",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, sql)

    def test_native_sql_helper_names_and_metadata_have_no_alias_escape(self):
        text = self.profile["lakehouse-instructions.txt"]
        for phrase in (
            "every native column name and value unchanged",
            "Do not project a subset, rename a field",
            "MunicipalityStoredNationwideCountRank is not returned",
            "Do not alias the derived field to that nonexistent stored field",
            "copy them rather than overwriting them with presentation literals",
            "ReconciliationKey belongs to the final comparison explanation",
            "a recipient-prefecture-only rank is not the nationwide all-donation rank",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertNotIn("explicitly alias the latter", text)
        self.assertNotIn("'MunicipalityId' AS ReconciliationKey", text)
        fields = dict(self.assets["sources"]["lakehouse_tables"]["referenceObjects"]["MunicipalityById"]["fields"])
        self.assertIn("MunicipalityDerivedNationwideCountRank", fields)
        self.assertIn("MunicipalityStoredNationwideAmountRank", fields)
        self.assertNotIn("MunicipalityStoredNationwideCountRank", fields)

    def test_native_kql_helper_contracts_cannot_acquire_synthetic_provenance(self):
        text = self.profile["kusto-instructions.txt"]
        for phrase in (
            "No project/project-away/project-rename or extra columns",
            "Do not request it or append it with extend",
            "Never add EventIdentityFieldExists, EventIdAvailabilityNotice, EventIdentityExplanation",
            "A literal is not a schema check",
            "Never add where WindowIsValid",
            "Copy native field names and SourceSystem, SourceObject, Scope, CountUnit, AmountUnit",
            "The sole presentation rewrite is the packaged UTC extend",
            "DerivedHasMatches", "not a native MV/helper field",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        for contract in reference_kql.validate_function_contracts(self.assets["kqlFunctions"]).values():
            fields = dict(contract.return_schema)
            self.assertFalse({"HasMatches", "EventIdentityFieldExists", "EventIdAvailabilityNotice"} & fields.keys())

    def test_fidelity_changes_preserve_frozen_safety_consent_and_ci_sections(self):
        text = self.profile["global-instructions.txt"]
        for begin, end, digest in (
            ("SAFETY BEFORE TOOLS\n", "\nCONFIRMATION GATE", "cc4b382cb61bb6f432b0161fe800c1468e65bc23edba803d5b14981f0b014a12"),
            ("CONFIRMATION GATE\n", "\nANSWER EVIDENCE FOOTER", "7e81e611a144b6641b4ab6a1f9b5b9825711a4a35775ff46cb1d77c4445ab482"),
            ("CODE INTERPRETER: BOUNDED, EXECUTED, SECONDARY\n", "\nFINAL CHECK", "e5b80c07e654efb844541652105cc2afc498ed09aceb0a6f31689a180e9c5342"),
        ):
            section = text.split(begin, 1)[1].split(end, 1)[0]
            with self.subTest(section=begin):
                self.assertEqual(hashlib.sha256(section.encode("utf-8")).hexdigest(), digest)

    def test_helper_query_shape_preserves_finished_rows_without_banning_custom_mv_aggregates(self):
        text = self.profile["kusto-instructions.txt"]
        guidance = text.split("HELPER QUERY SHAPE FIRST\n", 1)[1].split(
            "\nNATIVE SIGNATURES, NOT INVENTED PARAMETERS", 1,
        )[0]
        for phrase in (
            "finished result sets", "change only its two requested UTC bounds",
            "Keep all native columns and metadata", "row-preserving UTC extend",
            "no summarize, distinct, union, join, top, arg_max",
            "already returns unique MunicipalityID rows with both flags",
            "remove the redundant aggregation and retry the packaged wrapper",
            "Count and JPY amounts are different units",
            "HasMatches is not a native helper field",
            "actual returned results", "valid empty result remains empty",
            "Direct MV aggregates below still use summarize",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guidance)
        self.assertIn(
            "summarize RawObservationCount=sum(ObservationCount), RawObservedAmountYen=sum(ObservedAmountYen)",
            text.split("DIRECT MV: CUSTOM OR EXACT-ID QUERIES ONLY\n", 1)[1],
        )

    def test_ci_handoff_requires_completed_current_inputs_without_reclassifying_valid_empty_results(self):
        text = self.profile["global-instructions.txt"]
        guidance = text.split("CODE INTERPRETER: BOUNDED, EXECUTED, SECONDARY\n", 1)[1].split(
            "\nFINAL CHECK", 1,
        )[0]
        for phrase in (
            "finish required owner queries successfully FIRST; then call CI",
            "No parallel retrieval/CI",
            "current-turn result references/columns",
            "verify supplied files/rows before analysis",
            "Missing input files: retain native results",
            "CI was not completed", "Directory inspection is not analysis",
            "valid empty query results are not failures",
            "Never invent file IDs/paths",
            "instructions, prior answers or another run",
            "execute Python; show executed Python plus returned output",
            "missing/failed artifacts are not success",
            "Export CSV/JSON and PNG by default; Office only if requested",
            "Office downloads may be blocked; do not assume downloadability",
            "native relationship COUNT/path evidence",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guidance)

    def test_incompatible_addition_frame_keeps_both_supplied_components(self):
        refusal = self.profile["global-instructions.txt"].split(
            "INCOMPATIBLE ADDITION\n", 1,
        )[1].split("\nCODE INTERPRETER:", 1)[0]
        self.assertIn("Use ONLY the following response frame", refusal)
        self.assertIn("copy BOTH numbers exactly, including zero", refusal)
        self.assertIn("Never replace a supplied number with source names, blanks", refusal)
        self.assertIn("Query only a missing component", refusal)
        self.assertIn("Never quote or negate it anywhere", refusal)
        self.assertIn("Do not append prose, a combined total or an alternative sum", refusal)
        frame = refusal.split("Recipient schema:", 1)[1].split("All timestamps are UTC.\n", 1)[0]
        self.assertTrue(frame.startswith(" Donation -DonationToMunicipality-> Municipality\n"))
        self.assertIn("Attribution: <User-supplied examples OR current approved-source results", frame)
        static = next(line for line in frame.splitlines() if line.startswith("Static component:"))
        operational = next(line for line in frame.splitlines() if line.startswith("Operational component:"))
        self.assertTrue(static.startswith("Static component: <actual static input or returned value>"))
        self.assertTrue(operational.startswith("Operational component: <actual operational input or returned value>"))
        for line in (static, operational):
            for field in (" | Source: ", " | Scope: ", " | Metric: ", " | Unit: "):
                self.assertIn(field, line)
        self.assertIn("Static 2025 UTC snapshot", static)
        self.assertIn("Donation records OR JPY", static)
        self.assertIn("raw observation records OR JPY", operational)
        self.assertIn("never stored buckets", operational)
        self.assertIn("Raw observations may include duplicates; the datasets are independent.", frame)
        self.assertNotIn("Combined component:", frame)

    def test_kql_fewshots_format_every_native_datetime_after_the_helper(self):
        raw = self.profile[unified.KQL_FEWSHOTS_FILE]
        shots = self.assets["sources"]["kusto"]["fewShots"]
        record = self.assets["profileManifest"]["files"][unified.KQL_FEWSHOTS_FILE]
        self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), record["sha256"])
        self.assertEqual(unified.sha256_json(shots), record["canonicalSha256"])
        self.assertEqual(record["exampleCount"], 3)
        self.assertEqual(len({example["id"] for example in shots["fewShots"]}), 3)
        contracts = reference_kql.validate_function_contracts(self.assets["kqlFunctions"])
        for example, function in zip(shots["fewShots"], unified.KQL_FUNCTIONS):
            with self.subTest(function=function):
                self.assertEqual(set(example), {"id", "question", "query"})
                self.assertIn("all available approved", example["question"])
                query = example["query"]
                self.assertTrue(query.startswith(
                    "let StartUtc = datetime(null);\nlet EndUtc = datetime(null);\n"
                    f"{function}(StartUtc, EndUtc)\n| extend "
                ))
                self.assertEqual(re.findall(r"\|\s*(\w+)", query), ["extend"])
                native_dates = {name for name, kind in contracts[function].return_schema if kind == "datetime"}
                projections = re.findall(r'format_datetime\((\w+), "([^"]+)"\)', query)
                self.assertEqual({name for name, _ in projections}, native_dates)
                self.assertEqual(len(projections), len(native_dates))
                for name, format_ in projections:
                    self.assertEqual(format_, "yyyy-MM-dd HH:mm:ss.fffffff")
                    self.assertIn(
                        f'{name} = iff(isnull({name}), "", strcat(replace_string(format_datetime('
                        f'{name}, "yyyy-MM-dd HH:mm:ss.fffffff"), " ", "T"), "Z"))', query,
                    )
                self.assertNotRegex(example["question"], r"\bT\d{2}\b|\b\d{4}-\d{2}-\d{2}\b")

    def test_kql_fewshot_hash_and_wrapper_guards_are_independent_of_selection(self):
        profile = dict(self.profile)
        profile[unified.KQL_FEWSHOTS_FILE] += "\n"
        with self.assertRaisesRegex(unified.UnifiedAgentError, "file digest"):
            self.build(profile=profile)
        for defect in ("format", "unknown-column", "extra-argument", "sample"):
            shots = json.loads(self.profile[unified.KQL_FEWSHOTS_FILE])
            query = shots["fewShots"][1]["query"]
            if defect == "format":
                query = query.replace("yyyy-MM-dd HH:mm:ss.fffffff", "yyyy-MM-ddTHH:mm:ss.fffffffZ")
            elif defect == "unknown-column":
                query = query.replace("FirstObservedAtUtc", "UnapprovedDatetime")
            elif defect == "extra-argument":
                query = query.replace("AgentFileRunSummary(StartUtc, EndUtc)", "AgentFileRunSummary(StartUtc, EndUtc, 1)")
            else:
                query += "| take 1\n"
            shots["fewShots"][1]["query"] = query
            profile = dict(self.profile)
            raw = json.dumps(shots) + "\n"
            profile[unified.KQL_FEWSHOTS_FILE] = raw
            manifest = json.loads(profile["manifest.json"])
            record = manifest["files"][unified.KQL_FEWSHOTS_FILE]
            record["sha256"] = hashlib.sha256(raw.encode()).hexdigest()
            record["canonicalSha256"] = unified.sha256_json(shots)
            profile["manifest.json"] = json.dumps(manifest) + "\n"
            with self.subTest(defect=defect), self.assertRaisesRegex(unified.UnifiedAgentError, "UTC-only wrapper"):
                self.build(profile=profile)
        for defect in ("question", "missing-fewshots", "other-source-field"):
            changed = copy.deepcopy(self.assets)
            if defect == "question":
                changed["sources"]["kusto"]["fewShots"]["fewShots"][0]["question"] += " Changed."
            elif defect == "missing-fewshots":
                del changed["sources"]["kusto"]["fewShots"]
            else:
                changed["sources"]["kusto"]["extraField"] = "Not part of the approved selection"
            del changed["contract"]["sha256"]
            changed["contract"]["sha256"] = unified.sha256_json(changed)
            with self.subTest(defect=defect), self.assertRaises(unified.UnifiedAgentError):
                unified.verify_unified_assets(changed)
        reference = copy.deepcopy(self.reference)
        reference["sources"]["kusto"]["fewShots"] = self.assets["sources"]["kusto"]["fewShots"]
        with self.assertRaisesRegex(unified.UnifiedAgentError, "selection differs"):
            self.build(reference=reference)

    def test_import_and_in_memory_transform_have_no_io_or_input_mutation(self):
        source = Path(unified.__file__).read_bytes()
        before = copy.deepcopy(self.reference)
        core_before = copy.deepcopy(self.core)
        with (
            patch.object(Path, "read_bytes", side_effect=AssertionError("Unexpected filesystem read")),
            patch.object(Path, "read_text", side_effect=AssertionError("Unexpected filesystem read")),
            patch("builtins.open", side_effect=AssertionError("Unexpected filesystem open")),
            patch.object(socket, "socket", side_effect=AssertionError("Unexpected network")),
            patch.object(socket, "create_connection", side_effect=AssertionError("Unexpected network")),
        ):
            module = ModuleType("_offline_unified_import")
            exec(compile(source, "offline_unified.py", "exec"), module.__dict__)
            self.assertEqual(self.build(), self.assets)
            self.assertEqual(
                module.build_unified_assets(self.reference, self.core, self.profile),
                self.assets,
            )
        self.assertEqual(self.reference, before)
        self.assertEqual(self.core, core_before)
        self.assertEqual(unified.build_unified_assets(self.reference, repo_root=ROOT), self.assets)
        portable = {
            "description": self.core["userDescription"], "instructions": self.core["dataSourceInstructions"],
            "elements": copy.deepcopy(self.assets["sources"]["ontology"]["elements"]),
        }
        self.assertEqual(self.build(core=portable), self.assets)
        changed = self.build()
        changed["sources"]["lakehouse_tables"]["fewShots"]["fewShots"].clear()
        self.assertEqual(self.reference, before)

    def test_missing_global_source_or_profile_fields_never_fall_back(self):
        paths = (
            ("stageConfig", "aiInstructions"), ("stageConfig", "experimental"),
            ("globalProfile", "sha256"), ("globalProfile", "status"),
            ("sources", "lakehouse_tables", "instructions"),
            ("sources", "lakehouse_tables", "fewShots"),
            ("sources", "lakehouse_tables", "referenceObjects"),
            ("sources", "kusto", "description"), ("sources", "kusto", "elements"),
            ("sources", "ontology", "instructions"), ("sources", "ontology", "description"),
            ("sources", "ontology"), ("kqlFunctions", "AgentRawObservationTotals"),
        )
        for path in paths:
            reference = copy.deepcopy(self.reference)
            current = reference
            for key in path[:-1]:
                current = current[key]
            del current[path[-1]]
            with self.subTest(path=path), self.assertRaises(unified.UnifiedAgentError):
                self.build(reference=reference)
        for field in ("dataSourceInstructions", "elements", "userDescription"):
            core = copy.deepcopy(self.core)
            del core[field]
            with self.subTest(core=field), self.assertRaises(unified.UnifiedAgentError):
                self.build(core=core)
        for name in self.profile:
            profile = dict(self.profile)
            del profile[name]
            with self.subTest(file=name), self.assertRaises(unified.UnifiedAgentError):
                self.build(profile=profile)
        with self.assertRaises(unified.UnifiedAgentError):
            unified.build_unified_assets(self.reference)

    def test_ontology_delivery_preserves_explicit_null_without_assuming_support(self):
        self.assertIsNone(self.assets["sources"]["ontology"]["instructions"])
        self.assertIn(
            "do not rely on source-specific Ontology instructions",
            self.assets["stageConfig"]["aiInstructions"],
        )
        self.assertNotIn("ontology-instructions.txt", self.profile)
        self.assertFalse((ROOT / "tools" / "data-agent" / "unified" / "ontology-instructions.txt").exists())
        core = copy.deepcopy(self.core)
        core["dataSourceInstructions"] = "Support has not been established.\n"
        with self.assertRaisesRegex(unified.UnifiedAgentError, "explicit null"):
            self.build(core=core)
        changed = copy.deepcopy(self.assets)
        changed["sources"]["ontology"]["instructions"] = "Not authorized by this profile.\n"
        del changed["contract"]["sha256"]
        changed["contract"]["sha256"] = unified.sha256_json(changed)
        with self.assertRaisesRegex(unified.UnifiedAgentError, "remain explicit null"):
            unified.verify_unified_assets(changed)
        profile = dict(self.profile)
        manifest = json.loads(profile["manifest.json"])
        del manifest["ontologyInstructionPolicy"]
        profile["manifest.json"] = json.dumps(manifest) + "\n"
        with self.assertRaisesRegex(unified.UnifiedAgentError, "missing required fields"):
            self.build(profile=profile)
        profile = dict(self.profile)
        profile["ontology-instructions.txt"] = "Unused fourth instruction file.\n"
        with self.assertRaisesRegex(unified.UnifiedAgentError, "unexpected"):
            self.build(profile=profile)

    def test_unapproved_or_reduced_selections_fail_closed(self):
        for defect in ("extra-source", "extra-kql", "sql-field", "duplicate-table", "missing-source-text"):
            reference = copy.deepcopy(self.reference)
            if defect == "extra-source":
                reference["sources"]["secondOntology"] = reference["sources"]["ontology"]
            elif defect == "extra-kql":
                reference["sources"]["kusto"]["elements"].append({
                    "path": [["Function", "AgentObservationLeaders"]], "description": "Not approved",
                })
            elif defect == "sql-field":
                reference["sources"]["lakehouse_tables"]["referenceObjects"]["MunicipalityById"]["fields"].pop()
            elif defect == "duplicate-table":
                reference["sources"]["lakehouse_tables"]["elements"][0] = reference["sources"]["lakehouse_tables"]["elements"][1]
            else:
                reference["sources"]["kusto"]["instructions"] = ""
            with self.subTest(defect=defect), self.assertRaises(unified.UnifiedAgentError):
                self.build(reference=reference)
        for defect in ("deselected", "missing-entity", "path-only", "unknown-child"):
            core = copy.deepcopy(self.core)
            if defect == "deselected":
                core["elements"][0]["is_selected"] = False
            elif defect == "missing-entity":
                core["elements"].pop()
            elif defect == "path-only":
                core["elements"][0]["description"] = "PrefectureId,PrefectureName"
            else:
                core["elements"][0]["children"] = [{"display_name": "Not approved"}]
            with self.subTest(defect=defect), self.assertRaises(unified.UnifiedAgentError):
                self.build(core=core)

    def test_instruction_limits_and_all_hashes_fail_closed(self):
        for value in ("", " \n", "\ufeffText\n", "Text\r\n", "x" * 15_000 + "\n", "Changed\n"):
            profile = dict(self.profile)
            profile["global-instructions.txt"] = value
            with self.subTest(value=value[:20]), self.assertRaises(unified.UnifiedAgentError):
                self.build(profile=profile)
        reference = copy.deepcopy(self.reference)
        reference["stageConfig"]["aiInstructions"] += "Unpinned change\n"
        with self.assertRaises(unified.UnifiedAgentError):
            self.build(reference=reference)
        reference = copy.deepcopy(self.reference)
        reference["kqlFunctions"]["AgentFileRunSummary"] += "// Unpinned change\n"
        with self.assertRaisesRegex(unified.UnifiedAgentError, "digest"):
            self.build(reference=reference)
        for field in ("stageConfig", "sources", "globalProfile", "sqlDdl", "contract"):
            changed = copy.deepcopy(self.assets)
            del changed[field]
            with self.subTest(field=field), self.assertRaises(unified.UnifiedAgentError):
                unified.verify_unified_assets(changed)
        changed = copy.deepcopy(self.assets)
        changed["stageConfig"]["experimental"]["codeInterpreterEnabled"] = False
        with self.assertRaisesRegex(unified.UnifiedAgentError, "digest"):
            unified.verify_unified_assets(changed)
        changed = copy.deepcopy(self.assets)
        changed["ontologyTemplate"] = {}
        with self.assertRaisesRegex(unified.UnifiedAgentError, "no ontology template"):
            unified.verify_unified_assets(changed)

    def test_repinning_metadata_does_not_relax_bounded_source_counts(self):
        reference = copy.deepcopy(self.reference)
        reference["sources"]["kusto"]["elements"].append({
            "path": [["Function", "UnapprovedHelper"]], "description": "Not approved",
        })
        profile = dict(self.profile)
        manifest = json.loads(profile["manifest.json"])
        manifest["referenceSelectionsSha256"]["kusto"] = unified.sha256_json({
            key: value for key, value in reference["sources"]["kusto"].items() if key != "instructions"
        })
        profile["manifest.json"] = json.dumps(manifest) + "\n"
        with self.assertRaisesRegex(unified.UnifiedAgentError, "counts"):
            self.build(reference=reference, profile=profile)

        core = copy.deepcopy(self.core)
        reduced = {
            entry["path"][0][1]: entry["description"]
            for entry in self.reference["sources"]["ontology"]["elements"]
        }
        for node in core["elements"]:
            node["description"] = reduced[node["display_name"]]
        profile = dict(self.profile)
        manifest = json.loads(profile["manifest.json"])
        manifest["teachingOntologySourceSha256"] = unified.sha256_json({
            "description": core["userDescription"],
            "elements": [
                {"path": [["Entity", node["display_name"]]], "description": node["description"]}
                for node in core["elements"]
            ],
        })
        profile["manifest.json"] = json.dumps(manifest) + "\n"
        with self.assertRaisesRegex(unified.UnifiedAgentError, "72 static plus one time-series"):
            self.build(core=core, profile=profile)

    def test_existing_reference_helpers_accept_unified_assets_with_mock_service_only(self):
        bindings = {
            kind: {"workspaceId": "offline-workspace", "itemId": f"offline-item-{index}"}
            for index, kind in enumerate(agent.KINDS, 1)
        }
        fixture = AgentServiceFixture(self.assets)
        with patch.object(socket, "socket", side_effect=AssertionError("Live network forbidden")):
            result = agent.configure_reference_agent(
                fixture, "offline-workspace", "offline-agent", self.assets, bindings, initialize=True,
            )
            self.assertEqual(result["state"], "CREATED")
            self.assertFalse(result["acceptanceClaimed"])
            for stage in ("staging", "published"):
                for kind in agent.KINDS:
                    actual = {key: result["selections"][f"{stage}.{kind}"][key] for key in ("selectedObjects", "selectedLeaves")}
                    self.assertEqual(actual, unified.SELECTION_COUNTS[kind])
            agent.verify_definition(fixture.published, self.assets, bindings)
            desired = agent.draft_with_runtime(fixture.published, self.assets)
            agent.verify_definition(desired, self.assets, bindings)
            before, after = agent.decode_parts(fixture.published), agent.decode_parts(desired)
            for stage in ("draft", "published"):
                kql_path = agent.serialized_sources(after, stage)["kusto"][0]
                fewshots_path = kql_path.removesuffix("datasource.json") + "fewshots.json"
                self.assertEqual(after[fewshots_path]["value"], self.assets["sources"]["kusto"]["fewShots"])
            without_examples = copy.deepcopy(desired)
            kql_path = agent.serialized_sources(after, "draft")["kusto"][0]
            fewshots_path = kql_path.removesuffix("datasource.json") + "fewshots.json"
            without_examples["parts"] = [part for part in without_examples["parts"] if part["path"] != fewshots_path]
            with self.assertRaisesRegex(agent.ReferenceAgentError, "few-shots"):
                agent.verify_definition(without_examples, self.assets, bindings, stages=("draft",))
            for path in before:
                if path.endswith("/datasource.json"):
                    self.assertEqual(before[path], after[path])
                    if before[path]["value"]["type"] == "ontology":
                        self.assertIsNone(before[path]["value"]["dataSourceInstructions"])
            calls = len(fixture.calls)
            reused = agent.configure_reference_agent(
                fixture, "offline-workspace", "offline-agent", self.assets, bindings, initialize=False,
            )
            self.assertEqual(reused["state"], "REUSED")
            self.assertEqual(len(fixture.calls), calls)
            wrong = copy.deepcopy(bindings)
            wrong["ontology"]["itemId"] = "not-the-approved-teaching-item"
            with self.assertRaises(agent.ReferenceAgentError):
                agent.verify_definition(fixture.published, self.assets, wrong)


if __name__ == "__main__":
    unittest.main()
