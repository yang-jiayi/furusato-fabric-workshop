"""Offline tests: only synthetic DB-API fakes, never auth or remote SQL."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import struct
import sys
import traceback
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path(__file__).with_name("reference_sql.py")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


sql = load_module("_reference_sql_test_runtime", MODULE_PATH)
fixtures = load_module(
    "_reference_sql_native_fixtures", ROOT / "tools/data-agent/tests/test_reference_models.py",
)
models = fixtures.reference_models
TOKEN = "synthetic_test_token_not_a_credential"


def lakehouse():
    return {
        "displayName": "FixtureLakehouse",
        "properties": {
            "sqlEndpointProperties": {
                "connectionString": "discovered-example.datawarehouse.fabric.microsoft.com",
            },
        },
    }


class FakeCursor:
    # Like pyodbc.Cursor, this deliberately has no writable timeout attribute.
    __slots__ = (
        "snapshots", "snapshot_index", "statements", "created", "closed", "close_error",
        "execute_error_on", "fetch_error", "nextset_error_on", "description", "rows",
    )

    def __init__(self, snapshots):
        self.snapshots = copy.deepcopy(snapshots)
        self.snapshot_index = -1
        self.statements = []
        self.created = []
        self.closed = False
        self.close_error = None
        self.execute_error_on = None
        self.fetch_error = None
        self.nextset_error_on = None
        self.description = None
        self.rows = []

    def execute(self, statement):
        self.statements.append(statement)
        if self.execute_error_on and self.execute_error_on in statement:
            raise RuntimeError(TOKEN)
        query_names = {value: key for key, value in models.CATALOG_QUERIES.items()}
        if statement in query_names:
            name = query_names[statement]
            if name == "state":
                self.snapshot_index += 1
            snapshot = self.snapshots[self.snapshot_index]
            value = snapshot[name]
            rows = [value] if name in ("state", "integrity") else value
            names = list(rows[0]) if rows else ["EmptyCatalog"]
            self.description = [(column,) for column in names]
            self.rows = [tuple(row.get(column) for column in names) for row in rows]
        else:
            self.description, self.rows = None, []
            if statement.startswith("CREATE"):
                self.created.append(statement)
            elif not statement.startswith("SET NOCOUNT ON;"):
                raise AssertionError("Unexpected SQL statement in fake.")
        return self

    def fetchall(self):
        if self.fetch_error:
            raise self.fetch_error
        return self.rows

    def nextset(self):
        if self.nextset_error_on and self.nextset_error_on in self.statements[-1]:
            raise RuntimeError(TOKEN)
        return False

    def close(self):
        self.closed = True
        if self.close_error:
            raise self.close_error


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.closed = False
        self.timeout = None
        self.cursor_error = None
        self.close_error = None

    def cursor(self):
        if self.cursor_error:
            raise self.cursor_error
        return self.fake_cursor

    def close(self):
        self.closed = True
        if self.close_error:
            raise self.close_error


class FakeDriver:
    def __init__(self, snapshots=(), *, installed=None):
        self.installed = [sql.ODBC_DRIVER] if installed is None else installed
        self.fake_cursor = FakeCursor(snapshots)
        self.connection = FakeConnection(self.fake_cursor)
        self.connect_calls = []
        self.events = []
        self.connect_error = None

    def drivers(self):
        self.events.append("driver-check")
        return self.installed

    def connect(self, connection_string, **kwargs):
        self.events.append("connect")
        self.connect_calls.append((connection_string, kwargs))
        if self.connect_error:
            raise self.connect_error
        return self.connection


class ReferenceSqlTests(unittest.TestCase):
    def setUp(self):
        self.ddl = models.load_ddl()
        # Cache only the pure contract module, never a driver or credential.
        sql._contracts()
        self.provider = Mock(return_value=TOKEN)

    def deploy(self, driver, metadata=None, **kwargs):
        return sql.deploy_reference_sql(
            lakehouse() if metadata is None else metadata, self.ddl, self.provider,
            db_driver=driver, **kwargs,
        )

    def assert_closed(self, driver):
        self.assertTrue(driver.fake_cursor.closed)
        self.assertTrue(driver.connection.closed)

    def assert_private_error(self, operation, pattern=None):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
             contextlib.redirect_stderr(io.StringIO()) as err:
            try:
                operation()
            except sql.ReferenceSqlError as exc:
                rendered = "".join(traceback.format_exception(exc))
                self.assertNotIn(TOKEN, rendered)
                self.assertIsNone(exc.__cause__)
                self.assertIsNone(exc.__context__)
                if pattern:
                    self.assertRegex(str(exc), pattern)
            else:
                self.fail("Expected a safe runtime error.")
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "")

    def test_fresh_deploys_seven_batches_then_immediately_rereads_native_catalog(self):
        driver = FakeDriver([
            fixtures.fixture_catalog(populated=False, schema_id=None),
            fixtures.fixture_catalog(),
        ])
        result = self.deploy(driver)
        self.assertEqual(result["state"], "CREATED")
        self.assertTrue(result["catalogVerified"])
        self.assertEqual(result["executedFiles"], list(models.DDL_ORDER))
        self.assertEqual(driver.fake_cursor.created, [models.split_batches(text)[0] for _, text in self.ddl])
        self.assertEqual(result["outputColumnCounts"]["DonationTraceById"], 30)
        final_create = driver.fake_cursor.statements.index(driver.fake_cursor.created[-1])
        self.assertEqual(driver.fake_cursor.statements[final_create + 1], models.CATALOG_QUERIES["state"])
        self.assertEqual(driver.fake_cursor.snapshot_index, 1)
        self.provider.assert_called_once_with()
        self.assert_closed(driver)

    def test_missing_source_columns_can_propagate_before_any_ddl(self):
        pending = fixtures.fixture_catalog(populated=False, schema_id=None)
        pending["sourceColumns"] = []
        ready = fixtures.fixture_catalog(populated=False, schema_id=None)
        driver = FakeDriver([pending, ready, fixtures.fixture_catalog()])
        ticks = [0]
        sleeps = []

        def sleep(seconds):
            self.assertEqual(driver.fake_cursor.created, [])
            ticks[0] += seconds
            sleeps.append(seconds)

        result = self.deploy(
            driver, source_wait_timeout=30, poll_interval=5,
            clock=lambda: ticks[0], sleeper=sleep,
        )
        self.assertEqual(result["state"], "CREATED")
        self.assertEqual(sleeps, [5])
        self.assertEqual(driver.fake_cursor.snapshot_index, 2)
        self.assertEqual(len(driver.fake_cursor.created), 7)
        self.provider.assert_called_once_with()
        self.assert_closed(driver)

    def test_source_readiness_timeout_never_creates_or_retries_ddl(self):
        pending = fixtures.fixture_catalog(populated=False, schema_id=None)
        pending["sourceColumns"] = []
        driver = FakeDriver([pending, pending, pending])
        ticks = [0]

        def sleep(seconds):
            ticks[0] += seconds

        with self.assertRaisesRegex(sql.ReferenceSqlError, "no reference DDL"):
            self.deploy(
                driver, source_wait_timeout=10, poll_interval=5,
                clock=lambda: ticks[0], sleeper=sleep,
            )
        self.assertEqual(driver.fake_cursor.created, [])
        self.assert_closed(driver)

    def test_empty_existing_schema_with_any_owner_skips_only_schema_ddl(self):
        for owner in ("operator", "someone-else"):
            before = fixtures.fixture_catalog(populated=False)
            before["state"]["SchemaOwner"] = owner
            driver = FakeDriver([before, fixtures.fixture_catalog()])
            with self.subTest(owner=owner):
                result = self.deploy(driver)
                self.assertEqual(result["state"], "CREATED")
                self.assertEqual(result["executedFiles"], list(models.DDL_ORDER[1:]))
                self.assertEqual(len(driver.fake_cursor.created), 6)
                self.assertFalse(any("CREATE SCHEMA" in statement for statement in driver.fake_cursor.created))
                self.assert_closed(driver)

    def test_exact_reuse_is_read_only_and_preserves_blank_serialized_agent_types(self):
        driver = FakeDriver([fixtures.fixture_catalog()])
        metadata = lakehouse()
        metadata["serializedAgentMetadata"] = {"dataType": "", "parameterDataType": "", "returnType": ""}
        before = copy.deepcopy(metadata)
        result = self.deploy(driver, metadata)
        self.assertEqual(metadata, before)
        self.assertEqual(result["state"], "REUSED")
        self.assertEqual(result["executedFiles"], [])
        self.assertEqual(driver.fake_cursor.created, [])
        self.assertEqual(driver.fake_cursor.snapshot_index, 0)
        self.assertEqual(result["nativeCatalog"]["agentSerializedTypesModified"], False)
        self.assertIn("sys.parameters", result["nativeCatalog"]["provenance"])
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assert_closed(driver)

    def test_trace_missing_partial_foreign_and_mismatch_do_not_write(self):
        cases = []
        partial = fixtures.fixture_catalog()
        for key in ("objects", "columns", "parameters"):
            partial[key] = [row for row in partial[key] if row["ObjectName"] != "DonationTraceById"]
        cases.append(("DonationTraceById", partial))
        foreign = fixtures.fixture_catalog()
        foreign["objects"].append({"ObjectName": "UnmanagedObject", "ObjectType": "VIEW"})
        cases.append(("foreign", foreign))
        mismatch = fixtures.fixture_catalog()
        mismatch["columns"][-1]["MaxLength"] = 64
        cases.append(("mismatch", mismatch))
        wrong_body = fixtures.fixture_catalog()
        wrong_body["objects"][-1]["Definition"] = wrong_body["objects"][-1]["Definition"].replace(
            "LEFT JOIN", "INNER JOIN",
        )
        cases.append(("definition mismatch", wrong_body))
        for message, snapshot in cases:
            driver = FakeDriver([snapshot])
            with self.subTest(message=message), self.assertRaisesRegex(RuntimeError, message):
                self.deploy(driver)
            self.assertEqual(driver.fake_cursor.created, [])
            self.assert_closed(driver)

    def test_immediate_post_create_read_cannot_report_partial_or_wrong_objects_as_success(self):
        for kind in ("missing-trace", "wrong-column", "unavailable-definition", "still-empty"):
            after = fixtures.fixture_catalog()
            if kind == "missing-trace":
                after["objects"].pop()
            elif kind == "wrong-column":
                after["columns"][-1]["ColumnName"] = "IncorrectGrain"
            elif kind == "unavailable-definition":
                after["objects"][-1]["Definition"] = None
            else:
                after = fixtures.fixture_catalog(populated=False)
            driver = FakeDriver([
                fixtures.fixture_catalog(populated=False, schema_id=None), after,
            ])
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                self.deploy(driver)
            self.assertEqual(len(driver.fake_cursor.created), 7)
            self.assertEqual(driver.fake_cursor.snapshot_index, 1)
            self.assert_closed(driver)

    def test_hidden_metadata_fails_before_assuming_absence(self):
        before = fixtures.fixture_catalog(populated=False)
        before["state"]["CanViewDefinition"] = 0
        driver = FakeDriver([before])
        with self.assertRaisesRegex(RuntimeError, "VIEW DEFINITION"):
            self.deploy(driver)
        self.assertEqual(driver.fake_cursor.created, [])
        self.assertEqual(len(driver.fake_cursor.statements), 2)  # session SET then native state only
        self.assert_closed(driver)

    def test_database_identity_mismatch_is_refused(self):
        before = fixtures.fixture_catalog()
        before["state"]["DatabaseName"] = "DifferentDatabase"
        driver = FakeDriver([before])
        with self.assertRaisesRegex(RuntimeError, "discovered database"):
            self.deploy(driver)
        self.assertEqual(driver.fake_cursor.created, [])
        self.assert_closed(driver)

    def test_missing_native_driver_fails_before_token_provider_or_connect(self):
        for installed in ([], ["ODBC Driver 17 for SQL Server"]):
            driver = FakeDriver(installed=installed)
            with self.subTest(installed=installed), self.assertRaisesRegex(
                sql.ReferenceSqlPrerequisiteError, "wheel alone is insufficient",
            ):
                self.deploy(driver)
            self.provider.assert_not_called()
            self.assertEqual(driver.connect_calls, [])

    def test_missing_pyodbc_or_broken_native_driver_is_actionable_and_private(self):
        for error in (ImportError(TOKEN), OSError(TOKEN)):
            with patch.object(sql.importlib, "import_module", side_effect=error):
                self.assert_private_error(sql.require_odbc_driver, "No credentials were requested")
        driver = FakeDriver()
        driver.drivers = Mock(side_effect=RuntimeError(TOKEN))
        self.assert_private_error(lambda: self.deploy(driver), "Microsoft ODBC Driver 18")
        self.provider.assert_not_called()

    def test_token_attribute_encoding_tls_and_timeout_are_correct(self):
        driver = FakeDriver([fixtures.fixture_catalog()])

        def provider():
            driver.events.append("token")
            return TOKEN

        result = sql.deploy_reference_sql(
            lakehouse(), self.ddl, provider, db_driver=driver, connect_timeout=45, query_timeout=123,
        )
        self.assertEqual(driver.events, ["driver-check", "token", "connect"])
        connection_string, kwargs = driver.connect_calls[0]
        self.assertIn("DATABASE={FixtureLakehouse}", connection_string)
        self.assertIn("Encrypt=yes;TrustServerCertificate=no;", connection_string)
        for forbidden in ("UID=", "PWD=", "Authentication=", "MARS", TOKEN):
            self.assertNotIn(forbidden, connection_string)
        self.assertTrue(kwargs["autocommit"])  # no unsupported SQLEP transactions
        self.assertEqual(kwargs["timeout"], 45)
        self.assertEqual(driver.connection.timeout, 123)
        packed = kwargs["attrs_before"][1256]
        self.assertEqual(struct.unpack("<I", packed[:4])[0], len(TOKEN.encode("utf-16-le")))
        self.assertEqual(packed[4:].decode("utf-16-le"), TOKEN)
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assert_closed(driver)

    def test_provider_and_connection_errors_do_not_leak_credentials(self):
        driver = FakeDriver([fixtures.fixture_catalog()])
        self.provider.side_effect = RuntimeError(TOKEN)
        self.assert_private_error(lambda: self.deploy(driver), "token acquisition failed")
        self.assertEqual(driver.connect_calls, [])
        self.provider.side_effect = None
        driver.connect_error = RuntimeError(TOKEN)
        self.assert_private_error(lambda: self.deploy(driver), "SQL connection failed")

    def test_invalid_tokens_never_reach_the_driver(self):
        for token in (None, "", " leading", b"not-a-string"):
            driver = FakeDriver()
            self.provider.return_value = token
            with self.subTest(token_type=type(token)), self.assertRaisesRegex(sql.ReferenceSqlError, "token string"):
                self.deploy(driver)
            self.assertEqual(driver.connect_calls, [])

    def test_cursor_failure_closes_connection_without_leaking_driver_details(self):
        driver = FakeDriver([fixtures.fixture_catalog()])
        driver.connection.cursor_error = RuntimeError(TOKEN)
        self.assert_private_error(lambda: self.deploy(driver), "cursor creation")
        self.assertTrue(driver.connection.closed)

    def test_catalog_execute_and_fetch_failures_close_both_resources(self):
        for failure in ("execute", "fetch"):
            driver = FakeDriver([fixtures.fixture_catalog()])
            if failure == "execute":
                driver.fake_cursor.execute_error_on = "SELECT DB_NAME()"
            else:
                driver.fake_cursor.fetch_error = RuntimeError(TOKEN)
            with self.subTest(failure=failure):
                self.assert_private_error(lambda: self.deploy(driver), "catalog")
                self.assert_closed(driver)
                self.assertEqual(driver.fake_cursor.created, [])

    def test_partial_ddl_and_deferred_driver_failure_are_not_retried_or_rolled_back(self):
        for deferred in (False, True):
            driver = FakeDriver([fixtures.fixture_catalog(populated=False, schema_id=None)])
            if deferred:
                driver.fake_cursor.nextset_error_on = "CREATE VIEW agent_ref.DonationAttributes"
            else:
                driver.fake_cursor.execute_error_on = "CREATE VIEW agent_ref.DonationAttributes"
            with self.subTest(deferred=deferred):
                self.assert_private_error(lambda: self.deploy(driver), "partially created objects")
                self.assertEqual(driver.fake_cursor.snapshot_index, 0)
                self.assertEqual(
                    sum("CREATE VIEW agent_ref.DonationAttributes" in s for s in driver.fake_cursor.statements), 1,
                )
                self.assertFalse(any(
                    statement.startswith(("DROP", "ALTER", "ROLLBACK")) for statement in driver.fake_cursor.statements
                ))
                self.assert_closed(driver)

    def test_close_failure_does_not_leak_or_skip_connection_cleanup(self):
        driver = FakeDriver([fixtures.fixture_catalog()])
        driver.fake_cursor.close_error = RuntimeError(TOKEN)
        driver.connection.close_error = RuntimeError(TOKEN)
        self.assert_private_error(lambda: self.deploy(driver), "closure")
        self.assert_closed(driver)

    def test_primary_mismatch_is_not_hidden_by_closure_failure(self):
        before = fixtures.fixture_catalog()
        before["objects"].pop()
        driver = FakeDriver([before])
        driver.fake_cursor.close_error = RuntimeError(TOKEN)
        with self.assertRaisesRegex(RuntimeError, "DonationTraceById"):
            self.deploy(driver)
        self.assert_closed(driver)

    def test_dry_plan_is_import_safe_side_effect_free_and_does_not_claim_catalog_success(self):
        original = copy.deepcopy(self.ddl)
        with patch.object(sql, "require_odbc_driver", side_effect=AssertionError("driver accessed")), \
             patch.object(Path, "read_text", side_effect=AssertionError("read during pure plan")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("write during pure plan")):
            first = sql.plan_reference_sql(self.ddl)
            self.assertEqual(first, sql.plan_reference_sql(self.ddl))
        self.assertEqual(self.ddl, original)
        self.assertEqual(first["state"], "PLAN_ONLY")
        self.assertEqual(first["catalogState"], "UNINSPECTED")
        self.assertEqual(first["outputColumnCounts"]["DonationTraceById"], 30)
        self.provider.assert_not_called()

    def test_bad_plan_discovery_or_timeouts_fail_before_requesting_credentials(self):
        driver = FakeDriver()
        for ddl in (self.ddl[:-1], tuple(reversed(self.ddl)), dict(self.ddl)):
            with self.subTest(ddl_type=type(ddl)), self.assertRaises(ValueError):
                sql.deploy_reference_sql(lakehouse(), ddl, self.provider, db_driver=driver)
        with self.assertRaises(ValueError):
            self.deploy(driver, {"displayName": "MissingEndpoint"})
        for value in (True, 0, -1, "30", 3601):
            with self.subTest(timeout=value), self.assertRaises(ValueError):
                self.deploy(driver, connect_timeout=value)
        self.provider.assert_not_called()
        self.assertEqual(driver.events, [])

    def test_discovery_uses_authoritative_display_name_not_ids_or_reconstructed_names(self):
        metadata = lakehouse()
        metadata["displayName"] = "Discovered Lakehouse \u65e5\u672c"
        metadata["name"] = "WrongReconstructedName"
        metadata["id"] = "not-a-database-name"
        resolved = sql.resolve_sql_endpoint(metadata)
        self.assertEqual(resolved["database"], metadata["displayName"])
        metadata["properties"]["sqlEndpointProperties"]["databaseName"] = "EndpointDatabase"
        self.assertEqual(sql.resolve_sql_endpoint(metadata)["database"], "EndpointDatabase")
        del metadata["displayName"]
        self.assertEqual(sql.resolve_sql_endpoint(metadata)["database"], "EndpointDatabase")

    def test_discovery_parses_server_and_database_fields_but_rebuilds_secure_options(self):
        metadata = lakehouse()
        endpoint = metadata["properties"]["sqlEndpointProperties"]
        endpoint["connectionString"] = (
            "Data Source=tcp:discovered-example.datawarehouse.fabric.microsoft.com,1433;"
            "Initial Catalog={Endpoint DB};Encrypt=False;TrustServerCertificate=True;"
        )
        resolved = sql.resolve_sql_endpoint(metadata)
        self.assertEqual(resolved["database"], "Endpoint DB")
        self.assertIn("Encrypt=yes;TrustServerCertificate=no;", sql.odbc_connection_string(resolved))
        endpoint["databaseName"] = "DifferentEndpointDB"
        with self.assertRaisesRegex(ValueError, "disagree"):
            sql.resolve_sql_endpoint(metadata)

    def test_discovery_and_connection_values_cannot_inject_odbc_options(self):
        metadata = lakehouse()
        metadata["displayName"] = "Literal};UID=not-a-login;Database=not-a-target"
        connection_string = sql.odbc_connection_string(sql.resolve_sql_endpoint(metadata))
        self.assertIn("DATABASE={Literal}};UID=not-a-login;Database=not-a-target};", connection_string)
        bad_servers = (
            "https://discovered-example.datawarehouse.fabric.microsoft.com",
            "foreign.example.invalid", "discovered-example.datawarehouse.fabric.microsoft.com,1444",
            "Server=discovered-example.datawarehouse.fabric.microsoft.com;UID=hidden;",
            "Server=discovered-example.datawarehouse.fabric.microsoft.com;Database={unterminated",
            "Server=discovered-example.datawarehouse.fabric.microsoft.com;Server=other;",
        )
        for raw in bad_servers:
            metadata["properties"]["sqlEndpointProperties"]["connectionString"] = raw
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                sql.resolve_sql_endpoint(metadata)
        for display_name in (None, "", " leading", "line\nbreak", "x" * 129):
            metadata = lakehouse()
            metadata["displayName"] = display_name
            with self.subTest(display_name=display_name), self.assertRaises(ValueError):
                sql.resolve_sql_endpoint(metadata)

    def test_packaged_import_and_plan_need_no_repository_or_pyodbc(self):
        namespace = "_reference_sql_packaged_fixture"
        package = types.ModuleType(namespace)
        package.__path__ = []
        module = types.ModuleType(namespace + ".reference_sql")
        module.__package__ = namespace
        module.__file__ = str(ROOT / "_not_created_package/reference_sql.py")
        source = MODULE_PATH.read_text("utf-8")
        before_path = sys.path[:]
        with patch.dict(sys.modules, {
            namespace: package, namespace + ".reference_models": models,
        }), patch.object(Path, "read_text", side_effect=AssertionError("repository read")), \
                patch.object(Path, "mkdir", side_effect=AssertionError("filesystem mutation")):
            exec(compile(source, module.__file__, "exec"), module.__dict__)
            self.assertEqual(module.plan_reference_sql(self.ddl)["state"], "PLAN_ONLY")
        self.assertEqual(sys.path, before_path)

    def test_preflight_and_deployment_from_synthetic_package_never_read_adjacent_sql(self):
        namespace = "_reference_sql_synthetic_deployment"
        package = types.ModuleType(namespace)
        package.__path__ = []
        contract = types.ModuleType(namespace + ".reference_models")
        adapter = types.ModuleType(namespace + ".reference_sql")
        for module, name in ((contract, "reference_models"), (adapter, "reference_sql")):
            module.__package__ = namespace
            module.__file__ = str(ROOT / "_not_created_package/modules" / (name + ".py"))
        contract_source = fixtures.MODULE_PATH.read_text("utf-8")
        adapter_source = MODULE_PATH.read_text("utf-8")
        driver = FakeDriver([
            fixtures.fixture_catalog(populated=False, schema_id=None),
            fixtures.fixture_catalog(),
        ])
        before_path = sys.path[:]
        with patch.dict(sys.modules, {
            namespace: package, contract.__name__: contract, adapter.__name__: adapter,
        }), patch.object(Path, "read_text", side_effect=AssertionError("adjacent SQL read")), \
                patch.object(Path, "read_bytes", side_effect=AssertionError("adjacent SQL read")), \
                patch.object(Path, "mkdir", side_effect=AssertionError("filesystem mutation")):
            # Same module order and synthetic __file__ model as Notebook04.
            exec(compile(contract_source, contract.__file__, "exec"), contract.__dict__)
            exec(compile(adapter_source, adapter.__file__, "exec"), adapter.__dict__)
            checked_driver = adapter.require_odbc_driver(driver)
            self.assertIs(checked_driver, driver)
            self.provider.assert_not_called()
            self.assertEqual(driver.connect_calls, [])
            with patch.object(contract, "load_ddl", side_effect=AssertionError("local DDL fallback")):
                result = adapter.deploy_reference_sql(
                    lakehouse(), self.ddl, self.provider, db_driver=checked_driver,
                )
        self.assertEqual(sys.path, before_path)
        self.assertEqual(result["state"], "CREATED")
        self.assertEqual(result["executedFiles"], list(models.DDL_ORDER))
        self.assertEqual(result["outputColumnCounts"]["DonationTraceById"], 30)
        self.provider.assert_called_once_with()
        self.assert_closed(driver)

    def test_no_supplier_registration_is_not_an_integrity_failure(self):
        # Native integrity has zero duplicates/orphans even when the bridge is
        # empty. There is deliberately no supplier-row-count > 0 requirement.
        before = fixtures.fixture_catalog()
        self.assertEqual(before["integrity"]["OrphanSupplierGiftRows"], 0)
        driver = FakeDriver([before])
        self.assertEqual(self.deploy(driver)["state"], "REUSED")
        trace = self.ddl[-1][1]
        self.assertIn("LEFT JOIN agent_ref.GiftCatalogSuppliers", trace)
        self.assertIn("DonationAmountYen is non-additive", trace)


if __name__ == "__main__":
    unittest.main()
