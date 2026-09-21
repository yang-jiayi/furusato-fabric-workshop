from __future__ import annotations

import importlib.util
import copy
import hashlib
import json
import re
import subprocess
import sys
import types
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools" / "data-agent" / "reference-models" / "reference_models.py"
SPEC = importlib.util.spec_from_file_location("reference_models", MODULE_PATH)
reference_models = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(reference_models)


def fixture_type(sql_type):
    if sql_type == "bigint":
        datatype, length, precision, scale = "bigint", 8, 19, 0
    elif sql_type == "datetime2":
        datatype, length, precision, scale = "datetime2", 8, 26, 6
    else:
        match = re.fullmatch(r"varchar(?:\(([0-9]+)\))?", sql_type)
        assert match, sql_type
        datatype, length, precision, scale = "varchar", int(match[1] or 8000), 0, 0
    return {
        "DataType": datatype, "MaxLength": length, "Precision": precision, "Scale": scale,
        "TypeSchema": "sys", "IsUserDefined": 0,
    }


def fixture_source_catalog():
    return [
        {
            "SchemaName": "dbo", "ObjectName": table, "ObjectType": "USER_TABLE",
            "ColumnName": column, "OrdinalPosition": ordinal, "IsNullable": 1,
            **fixture_type(family),
        }
        for table, columns in reference_models.SOURCE_TYPES.items()
        for ordinal, (column, family) in enumerate(columns.items(), 1)
    ]


def fixture_catalog(*, populated=True, schema_id=7):
    """Synthetic native metadata only; no credentials, data rows or service I/O."""
    source = fixture_source_catalog()
    ddl = dict(reference_models.load_ddl())
    return {
        "state": {
            "DatabaseName": "FixtureLakehouse", "SchemaId": schema_id,
            "SchemaName": None if schema_id is None else "agent_ref",
            "CanViewDefinition": 1, "CanCreateSchema": 1, "CanCreateView": 1,
            "CanCreateFunction": 1, "CanAlterSchema": 1,
        },
        "objects": [
            {
                "SchemaName": "agent_ref", "ObjectName": name, "ObjectType": kind,
                "ObjectTypeCode": "V" if kind == "VIEW" else "IF",
                "Definition": reference_models.split_batches(ddl[reference_models.OBJECT_FILES[name]])[0],
                "UsesAnsiNulls": 1, "UsesQuotedIdentifier": 1, "IsSchemaBound": 0,
                "ExecuteAsPrincipalId": None,
            }
            for name, kind in reference_models.EXPECTED_OBJECTS.items()
        ] if populated else [],
        "columns": [
            {
                **column, "SchemaName": "agent_ref", "ObjectName": name,
                "ObjectType": reference_models.EXPECTED_OBJECTS[name], "IsNullable": 1,
            }
            for name, columns in reference_models.expected_native_columns(source).items()
            for column in columns
        ] if populated else [],
        "parameters": [
            {
                "SchemaName": "agent_ref", "ObjectName": name,
                "ObjectType": reference_models.EXPECTED_OBJECTS[name],
                "ParameterId": ordinal, "ParameterName": parameter,
                "IsOutput": 0, "IsReadOnly": 0, "HasDefaultValue": 0, **fixture_type(sql_type),
            }
            for name, parameters in reference_models.INPUT_PARAMETERS.items()
            for ordinal, (parameter, sql_type) in enumerate(parameters, 1)
        ] if populated else [],
        "types": [], "sourceColumns": source,
        "integrity": dict.fromkeys(reference_models.INTEGRITY_FIELDS, 0),
    }


class ReferenceModelTests(unittest.TestCase):
    def decision(self, catalog):
        return reference_models.catalog_decision(
            catalog, reference_models.load_ddl(), database="FixtureLakehouse",
        )

    def test_plan_hashes_the_same_single_read_that_it_validates(self):
        root = MODULE_PATH.parent
        originals = {(root / name): (root / name).read_bytes() for name in reference_models.DDL_ORDER}
        reads = {}
        original_read_bytes = Path.read_bytes
        original_read_text = Path.read_text

        def swapped_bytes(path):
            if path not in originals:
                return original_read_bytes(path)
            reads[path] = reads.get(path, 0) + 1
            return originals[path] if reads[path] == 1 else b"CREATE SCHEMA another_schema;\nGO\n"

        def swapped_text(path, *args, **kwargs):
            if path not in originals:
                return original_read_text(path, *args, **kwargs)
            return swapped_bytes(path).decode("utf-8")

        with patch.object(Path, "read_bytes", swapped_bytes), patch.object(Path, "read_text", swapped_text):
            plan = reference_models.build_plan()
        for entry in plan["files"]:
            path = root / entry["path"]
            self.assertEqual(reads[path], 1)
            self.assertEqual(entry["sha256"], hashlib.sha256(originals[path]).hexdigest())

    def test_plan_is_deterministic_and_every_file_is_one_batch(self):
        first = reference_models.build_plan()
        second = reference_models.build_plan()
        self.assertEqual(first, second)
        self.assertEqual(first["defaultMode"], "plan-only")
        self.assertEqual([item["batches"] for item in first["files"]], [1] * 7)
        self.assertEqual(
            set(first["objects"]),
            {
                "MunicipalityStatic",
                "DonationAttributes",
                "GiftCatalogSuppliers",
                "MunicipalityById",
                "DonationById",
                "DonationTraceById",
            },
        )
        self.assertTrue(all(len(item["sha256"]) == 64 for item in first["files"]))

    def test_mutating_a_returned_plan_does_not_change_shared_contracts(self):
        plan = reference_models.build_plan()
        plan["objects"].clear()
        plan["nativeCatalogQueries"].clear()
        reference_models.validate_plan()
        self.assertEqual(len(reference_models.EXPECTED_OBJECTS), 6)
        self.assertIn("parameters", reference_models.CATALOG_QUERIES)

    def test_contract_validator_enforces_grain_and_role_separation(self):
        reference_models.validate_plan()
        ddl = dict(reference_models.load_ddl())
        municipality = " ".join(ddl["010_municipality_static.sql"].lower().split())
        donation = " ".join(ddl["020_donation_attributes.sql"].lower().split())
        suppliers = " ".join(ddl["030_gift_catalog_suppliers.sql"].lower().split())

        self.assertIn("from dbo.ot_municipality as m", municipality)
        self.assertIn("municipalitystaticcount", municipality)
        self.assertIn("row_number() over", municipality)
        self.assertIn("cast(m.municipalityid as varchar(6)) asc", municipality)
        self.assertNotIn("where ", municipality)

        self.assertIn("from dbo.ot_donation as d", donation)
        self.assertNotIn("ot_supplier", donation)
        self.assertIn("donorresidenceprefectureid", donation)
        self.assertIn("donationrecipientmunicipalityid", donation)
        self.assertIn("donationselectedgiftid", donation)
        self.assertIn("d.donatedatutc", donation)
        self.assertIn("donationamountyen", donation)
        for repeated_aggregate in (
            "donorstaticcount",
            "donorstatictotalyen",
            "donorstaticmaxyen",
            "donoroverallamountrank",
            "donorresidenceamountrank",
            "prefreceivedstaticcount",
            "prefreceivedtotalyen",
            "prefreceivedamountrank",
            "prefresidentstaticcount",
            "prefresidenttotalyen",
            "prefresidentamountrank",
            "municipalitystaticcount",
            "municipalitystatictotalyen",
            "municipalityamountrank",
            "municipalityprefamountrank",
            "giftstaticcount",
            "giftstatictotalyen",
            "giftamountrank",
            "categorystaticcount",
            "categorystatictotalyen",
            "categoryamountrank",
        ):
            self.assertNotIn(repeated_aggregate, donation)

        self.assertIn("from dbo.ot_supplier_gift as bridge", suppliers)
        self.assertNotIn("string_agg", suppliers)
        self.assertNotIn("top 1", suppliers)
        self.assertIn("nomanufactureorshipmentclaim", suppliers)
        for repeated_aggregate in (
            "giftstaticcount",
            "giftstatictotalyen",
            "giftamountrank",
            "supplierprovidedgiftcount",
        ):
            self.assertNotIn(repeated_aggregate, suppliers)

    def test_new_objects_are_documented_as_partial_not_complete_core_corpus(self):
        readme = " ".join(
            (MODULE_PATH.parent / "README.md").read_text("utf-8").split()
        )
        self.assertIn("not a complete replacement for the existing Core corpus", readme)
        self.assertIn("registered donors with no Donations", readme)
        self.assertIn("retaining the necessary existing dimensions and facts", readme)

    def test_parameterized_lookup_types_and_exact_predicates_are_required(self):
        ddl = dict(reference_models.load_ddl())
        municipality = " ".join(ddl["040_municipality_by_id.sql"].lower().split())
        donation = " ".join(ddl["050_donation_by_id.sql"].lower().split())
        self.assertIn("@requestedmunicipalityid varchar(64)", municipality)
        self.assertIn("datalength(@requestedmunicipalityid) = 6", municipality)
        self.assertIn(
            "@requestedmunicipalityid collate latin1_general_100_bin2_utf8 "
            "not like '%[^0-9]%'",
            municipality,
        )
        self.assertIn("municipalityid = @requestedmunicipalityid", municipality)
        self.assertIn("as requestedmunicipalityid", municipality)
        self.assertIn("@requesteddonationid bigint", donation)
        self.assertIn("donationid = @requesteddonationid", donation)
        self.assertIn("as requesteddonationid", donation)
        self.assertIn("as retrievalmode", municipality)
        self.assertIn("as retrievalmode", donation)

    def test_client_lookup_validation_rejects_malformed_values(self):
        valid_municipality = "1" * 6
        self.assertEqual(
            reference_models.validate_municipality_lookup_id(valid_municipality),
            valid_municipality,
        )
        for value in (
            None,
            1,
            "",
            "1" * 5,
            "1" * 7,
            "１２３４５６",
            "12345A",
            " 12345",
        ):
            with self.subTest(municipality=value), self.assertRaises(ValueError):
                reference_models.validate_municipality_lookup_id(value)

        self.assertEqual(reference_models.validate_donation_lookup_id(1), 1)
        for value in (None, True, -1, "1", reference_models.BIGINT_MAX + 1):
            with self.subTest(donation=value), self.assertRaises(ValueError):
                reference_models.validate_donation_lookup_id(value)

    def test_bad_sql_is_rejected_before_any_deployment(self):
        ddl = list(reference_models.load_ddl())
        name, sql = ddl[1]
        ddl[1] = (name, sql + "\nDROP VIEW dbo.ot_municipality;\n")
        with self.assertRaisesRegex(ValueError, "forbidden"):
            reference_models.validate_plan(tuple(ddl))

        ddl = list(reference_models.load_ddl())
        name, sql = ddl[2]
        ddl[2] = (name, sql.replace("FROM dbo.ot_donation AS d", "FROM dbo.ot_donation AS d LEFT JOIN dbo.ot_supplier AS s ON 1=1"))
        with self.assertRaisesRegex(ValueError, "Donation grain"):
            reference_models.validate_plan(tuple(ddl))

    def test_extra_create_and_wrong_schema_are_rejected(self):
        ddl = list(reference_models.load_ddl())
        ddl[0] = (ddl[0][0], "CREATE SCHEMA another_schema;\nGO\n")
        with self.assertRaisesRegex(ValueError, "Only the agent_ref schema"):
            reference_models.validate_plan(tuple(ddl))
        ddl = list(reference_models.load_ddl())
        ddl[0] = (
            ddl[0][0], "CREATE SCHEMA agent_ref; CREATE TABLE dbo.Extra (n bigint);\nGO\n"
        )
        with self.assertRaisesRegex(ValueError, "one CREATE statement"):
            reference_models.validate_plan(tuple(ddl))

    def test_explicit_legacy_evidence_operation_is_mocked_and_not_an_import_side_effect(self):
        target = ROOT / "not-created-evidence"
        publication = types.ModuleType("furusato_docs.publication")
        publication.outside_repo = Mock(return_value=target)
        publication.safe_path = Mock(side_effect=lambda value: value)
        before_path = sys.path[:]
        with patch.dict(sys.modules, {"furusato_docs.publication": publication}), \
             patch.object(Path, "exists", return_value=False), patch.object(Path, "mkdir") as mkdir:
            self.assertEqual(reference_models.prepare_evidence_directory(target), target.resolve())
            mkdir.assert_called_once_with(parents=True, exist_ok=False)
            publication.outside_repo.assert_called_once_with(target, ROOT)
            with patch.object(Path, "exists", return_value=True), self.assertRaises(FileExistsError):
                reference_models.prepare_evidence_directory(target)
        self.assertEqual(sys.path, before_path)

    def test_loader_checks_native_exits_and_cannot_hide_partial_function_failure(self):
        script = (MODULE_PATH.parent / "deploy_reference_models.ps1").read_text("utf-8")
        self.assertIn("--prepare-evidence $EvidenceDirectory", script)
        self.assertIn("[IO.FileMode]::CreateNew", script)
        self.assertIn('if ($LASTEXITCODE -ne 0)', script)
        self.assertIn("DDL changed after local plan validation", script)
        self.assertNotIn("$functionErrors", script)
        self.assertNotIn("continue", script)

    def test_missing_or_reordered_files_fail_closed(self):
        ddl = reference_models.load_ddl()
        with self.assertRaisesRegex(ValueError, "order"):
            reference_models.validate_plan(tuple(reversed(ddl)))
        with self.assertRaisesRegex(ValueError, "order"):
            reference_models.validate_plan(ddl[:-1])

    def test_loader_can_validate_its_already_split_single_statement_batches(self):
        ddl = tuple((name, reference_models.split_batches(sql)[0]) for name, sql in reference_models.load_ddl())
        reference_models.validate_plan(ddl)
        self.assertEqual(
            reference_models.catalog_decision(fixture_catalog(), ddl, database="FixtureLakehouse"),
            "reuse",
        )

    def test_stdin_catalog_cli_accepts_loader_batches_without_any_evidence_writes(self):
        request = {
            "catalog": fixture_catalog(), "database": "FixtureLakehouse",
            "ddl": [(name, reference_models.split_batches(text)[0]) for name, text in reference_models.load_ddl()],
        }
        result = subprocess.run(
            [sys.executable, "-B", str(MODULE_PATH), "--catalog-decision"],
            input=json.dumps(request), text=True, encoding="utf-8",
            capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"decision": "reuse"})

    def test_empty_schema_is_fresh_without_inferring_or_changing_ownership(self):
        self.assertEqual(reference_models.collision_decision(None, []), "fresh")
        self.assertEqual(reference_models.collision_decision(7, []), "fresh")
        for owner in ("caller", "another-owner"):
            catalog = fixture_catalog(populated=False)
            catalog["state"]["SchemaOwner"] = owner
            with self.subTest(owner=owner):
                self.assertEqual(self.decision(catalog), "fresh")
        with self.assertRaisesRegex(RuntimeError, "Partial or foreign"):
            reference_models.collision_decision(
                7, [{"ObjectName": "MunicipalityStatic", "ObjectType": "VIEW"}]
            )

    def test_six_exact_objects_reuse_only_after_full_native_verification(self):
        catalog = fixture_catalog()
        self.assertEqual(self.decision(catalog), "reuse")
        self.assertEqual(
            {name: len(columns) for name, columns in reference_models.OUTPUT_COLUMNS.items()},
            {
                "MunicipalityStatic": 20, "DonationAttributes": 40, "GiftCatalogSuppliers": 29,
                "MunicipalityById": 22, "DonationById": 42, "DonationTraceById": 30,
            },
        )
        # Existing exact objects need metadata visibility, not CREATE permissions.
        for field in ("CanCreateSchema", "CanCreateView", "CanCreateFunction", "CanAlterSchema"):
            catalog["state"][field] = 0
        self.assertEqual(self.decision(catalog), "reuse")

    def test_output_names_types_and_order_match_authoritative_schema_documents(self):
        documented = json.loads(
            (ROOT / "tools/data-agent/source-contract/entrypoint-schema.json").read_text("utf-8")
        )["objects"]
        trace = json.loads((MODULE_PATH.parent / "trace-schema.json").read_text("utf-8"))
        documented["DonationTraceById"] = {"returnValues": trace["fields"]}
        resolved = reference_models.expected_native_columns(fixture_source_catalog())
        for name, entry in documented.items():
            fields = entry.get("fields", entry.get("returnValues"))
            with self.subTest(name=name):
                self.assertEqual([column["ColumnName"] for column in resolved[name]], [f[0] for f in fields])
                self.assertEqual(
                    [column["DataType"] for column in resolved[name]],
                    [f[1].split("(")[0] for f in fields],
                )

    def test_trace_missing_is_partial_not_successful_five_object_reuse(self):
        catalog = fixture_catalog()
        for key in ("objects", "columns", "parameters"):
            catalog[key] = [row for row in catalog[key] if row["ObjectName"] != "DonationTraceById"]
        with self.assertRaisesRegex(RuntimeError, "Missing:.*DonationTraceById"):
            self.decision(catalog)

    def test_foreign_objects_types_and_hidden_catalog_are_refused(self):
        cases = []
        foreign = fixture_catalog()
        foreign["objects"].append({"ObjectName": "Foreign", "ObjectType": "USER_TABLE"})
        cases.append(foreign)
        wrong_case = fixture_catalog()
        wrong_case["objects"][0]["ObjectName"] = "municipalitystatic"
        cases.append(wrong_case)
        hidden = fixture_catalog(populated=False, schema_id=None)
        hidden["state"]["CanViewDefinition"] = 0
        cases.append(hidden)
        schema_type = fixture_catalog(populated=False)
        schema_type["types"] = [{"SchemaName": "agent_ref", "TypeName": "ForeignType"}]
        cases.append(schema_type)
        no_alter = fixture_catalog(populated=False)
        no_alter["state"]["CanAlterSchema"] = 0
        cases.append(no_alter)
        for catalog in cases:
            with self.subTest(catalog=catalog["state"]), self.assertRaises(RuntimeError):
                self.decision(catalog)

    def test_native_column_name_type_length_precision_scale_and_order_are_exact(self):
        for field, replacement in (
            ("ColumnName", "WrongColumn"), ("DataType", ""), ("DataType", "nvarchar"),
            ("MaxLength", 64), ("Precision", 2), ("Scale", 1), ("OrdinalPosition", 2),
            ("TypeSchema", "dbo"), ("IsUserDefined", 1),
        ):
            catalog = fixture_catalog()
            catalog["columns"][0][field] = replacement
            with self.subTest(field=field, replacement=replacement), self.assertRaises(RuntimeError):
                self.decision(catalog)
        catalog = fixture_catalog()
        catalog["columns"] = catalog["columns"][:-1]
        with self.assertRaisesRegex(RuntimeError, "DonationTraceById"):
            self.decision(catalog)

    def test_native_input_parameter_contract_is_not_a_return_column_count(self):
        for field, replacement in (
            ("ParameterId", 0), ("ParameterName", "@Wrong"), ("DataType", "int"),
            ("MaxLength", 6), ("IsOutput", 1), ("HasDefaultValue", 1), ("IsReadOnly", 1),
        ):
            catalog = fixture_catalog()
            catalog["parameters"][0][field] = replacement
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, "parameter"):
                self.decision(catalog)
        catalog = fixture_catalog()
        catalog["parameters"].pop()
        with self.assertRaisesRegex(RuntimeError, "DonationTraceById"):
            self.decision(catalog)

    def test_definition_comparison_preserves_literal_case_and_whitespace(self):
        catalog = fixture_catalog()
        original = catalog["objects"][-1]["Definition"]
        catalog["objects"][-1]["Definition"] = "-- Formatting only\n" + original.replace(
            "CREATE FUNCTION", "CREATE\nFUNCTION",
        )
        self.assertEqual(self.decision(catalog), "reuse")
        for changed in (
            original.replace("non-additive", "NON-ADDITIVE"),
            original.replace("DonationId x SupplierId", "DonationId  x SupplierId"),
            original.replace("LEFT JOIN", "INNER JOIN"),
            original.replace("@RequestedDonationId bigint", "@RequestedDonationId bigint = 1"),
            None,
        ):
            catalog["objects"][-1]["Definition"] = changed
            with self.subTest(changed=changed), self.assertRaisesRegex(RuntimeError, "definition"):
                self.decision(catalog)

    def test_native_object_type_and_module_settings_are_exact(self):
        for field, replacement in (
            ("ObjectType", "SQL_TABLE_VALUED_FUNCTION"), ("ObjectTypeCode", "TF"),
            ("UsesAnsiNulls", 0), ("UsesQuotedIdentifier", 0), ("IsSchemaBound", 1),
            ("ExecuteAsPrincipalId", 2),
        ):
            catalog = fixture_catalog()
            catalog["objects"][-1][field] = replacement
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, "module settings"):
                self.decision(catalog)

    def test_sources_and_integrity_are_required_even_for_an_empty_schema(self):
        for populated in (False, True):
            for field in ("DuplicateSupplierGiftKeys", "DuplicateDonorKeys", "OrphanDonationGifts"):
                catalog = fixture_catalog(populated=populated)
                catalog["integrity"][field] = 1
                with self.subTest(populated=populated, field=field), self.assertRaisesRegex(RuntimeError, field):
                    self.decision(catalog)
            catalog = fixture_catalog(populated=populated)
            catalog["sourceColumns"].pop()
            with self.assertRaisesRegex(RuntimeError, "source column"):
                self.decision(catalog)
        catalog = fixture_catalog()
        column = next(row for row in catalog["sourceColumns"] if row["ColumnName"] == "DonorName")
        column["MaxLength"] = 7000
        with self.assertRaisesRegex(RuntimeError, "name/type/order"):
            self.decision(catalog)

    def test_trace_plan_rejects_changed_grain_and_nonexact_output(self):
        ddl = reference_models.load_ddl()
        name, source = ddl[-1]
        for changed in (
            source.replace("LEFT JOIN", "INNER JOIN"),
            source.replace("non-additive", "additive"),
            source.replace("donation.GiftName,", ""),
            source.replace("donation.GiftName,", "donation.GiftName AS WrongName,"),
            source.replace("SELECT\n", "SELECT DISTINCT\n"),
            source.replace("donation.DonationId = @RequestedDonationId",
                           "donation.DonationId = @RequestedDonationId AND supplier.RegisteredSupplierId IS NOT NULL"),
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                reference_models.validate_plan(ddl[:-1] + ((name, changed),))

    def test_catalog_validation_is_pure_and_does_not_mutate_input(self):
        catalog = fixture_catalog()
        ddl = reference_models.load_ddl()
        before = copy.deepcopy(catalog)
        with patch.object(Path, "read_bytes", side_effect=AssertionError("unexpected read")), \
             patch.object(Path, "read_text", side_effect=AssertionError("unexpected read")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("unexpected write")):
            self.assertEqual(
                reference_models.catalog_decision(
                    catalog, ddl, database="FixtureLakehouse",
                ), "reuse",
            )
        self.assertEqual(catalog, before)

    def test_import_does_not_mutate_sys_path_or_require_repository_docs(self):
        module = types.ModuleType("_portable_reference_models")
        module.__file__ = str(ROOT / "reference_models.py")
        source = MODULE_PATH.read_text("utf-8")
        before_path = sys.path[:]
        with patch.object(Path, "read_text", side_effect=AssertionError("unexpected import read")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("unexpected import write")):
            exec(compile(source, module.__file__, "exec"), module.__dict__)
        self.assertEqual(sys.path, before_path)
        self.assertEqual(len(module.EXPECTED_OBJECTS), 6)

    def test_powershell_dry_plan_precedes_auth_and_private_evidence(self):
        script = (MODULE_PATH.parent / "deploy_reference_models.ps1").read_text("utf-8")
        local_return = script.index("if (-not $Apply)")
        self.assertLess(local_return, script.index("& az account show"))
        self.assertLess(local_return, script.index("--prepare-evidence $EvidenceDirectory"))
        self.assertIn('"060_donation_trace_by_id.sql"', script)
        self.assertIn('Get-CatalogDecision $after', script)
        self.assertIn('"after-parameters.json"', script)

    def test_runtime_coordinates_are_validated_but_not_persisted(self):
        reference_models.validate_runtime(
            "abc-123.datawarehouse.fabric.microsoft.com",
            "Lakehouse_Name",
            "user@example.test",
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        )
        bad_cases = (
            ("https://abc.datawarehouse.fabric.microsoft.com", "Db", "u@example.test"),
            ("abc.datawarehouse.fabric.microsoft.com", "Db;DROP", "u@example.test"),
            ("abc.datawarehouse.fabric.microsoft.com", "Db", "not-a-upn"),
        )
        for server, database, user in bad_cases:
            with self.subTest(server=server, database=database, user=user):
                with self.assertRaises(ValueError):
                    reference_models.validate_runtime(
                        server,
                        database,
                        user,
                        "11111111-1111-1111-1111-111111111111",
                        "22222222-2222-2222-2222-222222222222",
                    )

    def test_live_target_coordinates_have_no_defaults(self):
        script = (MODULE_PATH.parent / "deploy_reference_models.ps1").read_text("utf-8")
        for parameter in (
            "$Server",
            "$Database",
            "$ExpectedUser",
            "$TenantId",
            "$SubscriptionId",
            "$EvidenceDirectory",
        ):
            self.assertIn(
                f"[Parameter(Mandatory = $true)][string]{parameter}",
                script,
            )
        self.assertNotRegex(script, r"(?i)param\s*\([^)]*\.datawarehouse\.fabric\.microsoft\.com")
        self.assertNotRegex(script, r"(?i)param\s*\([^)]*[0-9a-f]{8}-[0-9a-f-]{27}")


if __name__ == "__main__":
    unittest.main()
