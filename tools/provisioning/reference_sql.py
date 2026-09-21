"""Opt-in SQL reference deployment for Notebook04, with no import-time I/O.

Source prerequisites
--------------------
Notebook01 must already have published its validated static snapshot into the
discovered, schema-enabled Lakehouse's dbo tables: ot_municipality, ot_prefecture,
ot_donation, ot_donor, ot_gift, ot_gift_category, ot_supplier, ot_supplier_gift.
Wait for those tables/columns to become visible in the SQL analytics endpoint;
this adapter neither writes Delta data nor refreshes SQL endpoint metadata.
The shared reference_models module checks native source types and unique join
keys before any DDL. A gift with no supplier registration is valid: TraceById's
LEFT JOIN returns a null-supplier row. DonationAmountYen repeats per registration
and is non-additive; no data, business SQL, or Agent fields are rewritten here.

Host prerequisites (operator configured, never automatically installed)
----------------------------------------------------------------------
The notebook driver host needs Python pyodbc, Microsoft ODBC Driver 18 for SQL
Server (msodbcsql18), and its OS dependencies (unixODBC on Linux). Installing
only the Python wheel is insufficient. Configure a supported Fabric Environment/
host image, then restart the session if necessary. Driver availability is checked
before invoking the injected zero-argument token provider. The provider must
return an Entra SQL token for https://database.windows.net/ (for example a caller-
supplied lambda using notebookutils.credentials.getToken with that audience).
The host needs TLS/TDS connectivity to the discovered endpoint, normally 1433.
Credentials are never printed, persisted, returned, or sent to a REST API.

The caller supplies environment-specific Lakehouse discovery metadata and
ordered (filename, SQL string) assets, with reference_models in the same packaged
module namespace. No tenant, workspace, database, or server instance is embedded.
Database VIEW DEFINITION is required for complete catalog visibility; CREATE
VIEW/FUNCTION plus CREATE SCHEMA, or ALTER on an existing empty schema, is needed
only for creation. No permissions or schema ownership are changed.

SQL analytics endpoints do not support user transactions. DDL is CREATE-only,
autocommitted, and never retried. A failed/partial creation is an explicit
conflict on the next run, not a success or an invitation to drop/overwrite.
Immediate native re-read after creation must verify all six objects, including
Trace30, before returning CREATED. Native type provenance is returned separately
and MUST NOT be used to fill blank serialized Agent SQL type fields.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import re
import struct
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

ODBC_DRIVER = "ODBC Driver 18 for SQL Server"
SQL_ACCESS_TOKEN_ATTRIBUTE = 1256
SQL_TOKEN_AUDIENCE = "https://database.windows.net/"
_SERVER = re.compile(r"[a-z0-9-]+\.datawarehouse\.fabric\.microsoft\.com", re.I)
_PREREQUISITE_MESSAGE = (
    "SQL reference runtime requires pyodbc and Microsoft ODBC Driver 18 for SQL Server "
    "(msodbcsql18, plus unixODBC on Linux) on the notebook driver host. "
    "Preconfigure the supported Fabric Environment/host and restart the session; "
    "installing the Python wheel alone is insufficient. No credentials were requested "
    "and nothing was installed automatically."
)


class ReferenceSqlError(RuntimeError):
    """Safe, credential-free runtime failure."""


class ReferenceSqlPrerequisiteError(ReferenceSqlError):
    """A local driver prerequisite is absent."""


class SqlCursor(Protocol):
    """The pyodbc cursor surface used by this adapter."""

    @property
    def description(self) -> Sequence[Sequence[Any]] | None: ...
    def execute(self, sql: str) -> Any: ...
    def fetchall(self) -> Sequence[Sequence[Any]]: ...
    def nextset(self) -> bool | None: ...
    def close(self) -> None: ...


class SqlConnection(Protocol):
    """Query timeout is a connection setting in pyodbc, not a cursor setting."""

    timeout: int

    def cursor(self) -> SqlCursor: ...
    def close(self) -> None: ...


class SqlDriver(Protocol):
    """Injectable pyodbc-compatible driver; no concrete dependency at import."""

    def drivers(self) -> Sequence[str]: ...
    def connect(
        self, connection_string: str, *, attrs_before: Mapping[int, bytes],
        autocommit: bool, timeout: int,
    ) -> SqlConnection: ...


@lru_cache(maxsize=1)
def _contracts():
    # Sealed Notebook04 modules are loaded in an isolated package, models first.
    # The fallback is for the local source checkout, without sys.path mutation.
    if __package__:
        try:
            return importlib.import_module(".reference_models", __package__)
        except ModuleNotFoundError as exc:
            if exc.name != __package__ + ".reference_models":
                raise
    path = Path(__file__).resolve().parents[1] / "data-agent/reference-models/reference_models.py"
    spec = importlib.util.spec_from_file_location("_furusato_local_sql_contract", path)
    if spec is None or spec.loader is None:
        raise ReferenceSqlError("The packaged reference_models module is required.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _private_call(operation: Callable[[], Any], message: str, error_type=ReferenceSqlError):
    # Raise *outside* the except suite: raw provider/ODBC exceptions can contain
    # credentials. Do not retain them as __cause__ or __context__ on our error.
    try:
        return operation()
    except Exception:
        pass
    raise error_type(message)


def _database_name(value: Any) -> str:
    if (
        not isinstance(value, str) or not 1 <= len(value) <= 128
        or value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("A nonempty authoritative SQL database displayName is required.")
    return value


def _connection_fields(raw: str) -> dict[str, str]:
    """Parse discovered ODBC-style fields without forwarding arbitrary options."""
    aliases = {
        "server": "server", "data source": "server",
        "database": "database", "initial catalog": "database",
        "encrypt": "encrypt", "trustservercertificate": "trustservercertificate",
        "connection timeout": "timeout", "connect timeout": "timeout",
    }
    fields: dict[str, str] = {}
    position = 0
    while position < len(raw):
        if not raw[position:].strip(" ;"):
            break
        equals = raw.find("=", position)
        if equals < 0:
            raise ValueError("Malformed discovered SQL connectionString.")
        key = raw[position:equals].strip().lower()
        if key not in aliases:
            raise ValueError("Discovered SQL connectionString contains unsupported or credential fields.")
        position = equals + 1
        while position < len(raw) and raw[position].isspace():
            position += 1
        if position < len(raw) and raw[position] == "{":
            position += 1
            pieces = []
            while position < len(raw):
                if raw[position:position + 2] == "}}":
                    pieces.append("}")
                    position += 2
                elif raw[position] == "}":
                    position += 1
                    break
                else:
                    pieces.append(raw[position])
                    position += 1
            else:
                raise ValueError("Malformed quoted discovered SQL connectionString.")
            value = "".join(pieces)
            while position < len(raw) and raw[position].isspace():
                position += 1
            if position < len(raw) and raw[position] != ";":
                raise ValueError("Malformed discovered SQL connectionString separator.")
        else:
            end = raw.find(";", position)
            end = len(raw) if end < 0 else end
            value, position = raw[position:end].strip(), end
        canonical = aliases[key]
        if canonical in fields:
            raise ValueError("Ambiguous duplicate fields in discovered SQL connectionString.")
        fields[canonical] = value
        if position < len(raw):
            position += 1
    return fields


def resolve_sql_endpoint(lakehouse: Mapping[str, Any]) -> dict[str, str]:
    """Purely extract server and authoritative database; never discover remotely.

    Accept the normal bare endpoint hostname or a connection string with
    Server/Data Source and optional Database/Initial Catalog. Explicit endpoint
    databaseName/database/displayName and connection-string catalog fields must
    agree when both exist. Otherwise use the discovered Lakehouse displayName,
    never its ID, a reconstructed participant name, or a hardcoded default.
    """
    properties = lakehouse.get("properties")
    endpoint = properties.get("sqlEndpointProperties") if isinstance(properties, Mapping) else None
    if not isinstance(endpoint, Mapping):
        raise ValueError("Lakehouse properties.sqlEndpointProperties discovery metadata is required.")
    raw = endpoint.get("connectionString")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Lakehouse SQL endpoint connectionString is missing; wait for endpoint readiness.")
    fields = _connection_fields(raw) if "=" in raw else {"server": raw.strip()}
    server = fields.get("server", "")
    if server.lower().startswith("tcp:"):
        server = server[4:]
    if server.endswith(",1433"):
        server = server[:-5]
    if not _SERVER.fullmatch(server):
        raise ValueError("Discovered SQL server must be a Fabric SQL endpoint hostname, using TDS port 1433.")
    databases = [
        _database_name(endpoint[key]) for key in ("databaseName", "database", "displayName")
        if key in endpoint and endpoint[key] is not None
    ]
    if "database" in fields:
        databases.append(_database_name(fields["database"]))
    if len(set(databases)) > 1:
        raise ValueError("Authoritative SQL endpoint database fields disagree.")
    database = databases[0] if databases else _database_name(lakehouse.get("displayName"))
    return {"server": server.lower(), "database": database}


def _odbc_value(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def odbc_connection_string(endpoint: Mapping[str, str]) -> str:
    """Construct TLS-only token authentication settings, safely quoting names."""
    server = endpoint.get("server", "")
    if not isinstance(server, str) or not _SERVER.fullmatch(server):
        raise ValueError("A validated discovered Fabric SQL server is required.")
    database = _database_name(endpoint.get("database"))
    return (
        f"DRIVER={_odbc_value(ODBC_DRIVER)};"
        f"SERVER={_odbc_value('tcp:' + server + ',1433')};"
        f"DATABASE={_odbc_value(database)};Encrypt=yes;TrustServerCertificate=no;"
    )


def require_odbc_driver(db_driver: SqlDriver | None = None) -> SqlDriver:
    """Local preflight: check pyodbc/native driver, with no credentials or connection.

    The parent can call this before its first remote write, retain the result
    in memory, and pass it as deploy_reference_sql(..., db_driver=driver).
    Do not serialize the returned module/driver into a plan or manifest.
    """
    driver = db_driver
    if driver is None:
        driver = _private_call(
            lambda: importlib.import_module("pyodbc"),
            _PREREQUISITE_MESSAGE, ReferenceSqlPrerequisiteError,
        )
    available = _private_call(
        lambda: driver.drivers(), _PREREQUISITE_MESSAGE, ReferenceSqlPrerequisiteError,
    )
    if (
        not isinstance(available, (list, tuple)) or ODBC_DRIVER not in available
        or not callable(getattr(driver, "connect", None))
    ):
        raise ReferenceSqlPrerequisiteError(_PREREQUISITE_MESSAGE)
    return driver


def pack_sql_access_token(token: str) -> bytes:
    """Return SQL_COPT_SS_ACCESS_TOKEN's length-prefixed UTF-16-LE bytes."""
    if not isinstance(token, str) or not token or token != token.strip():
        raise ReferenceSqlError("The injected SQL token provider must return a nonempty token string.")
    encoded = token.encode("utf-16-le")
    return struct.pack("<I", len(encoded)) + encoded


def _ordered_ddl(ddl_assets: Iterable[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    if isinstance(ddl_assets, (str, bytes, Mapping)):
        raise ValueError("SQL assets must be ordered (filename, SQL string) pairs.")
    assets = tuple(ddl_assets)
    if any(
        not isinstance(entry, (tuple, list)) or len(entry) != 2
        or any(not isinstance(value, str) for value in entry) for entry in assets
    ):
        raise ValueError("SQL assets must be ordered (filename, SQL string) pairs.")
    ddl = tuple((name, text) for name, text in assets)
    _contracts().validate_plan(ddl)
    return ddl


def plan_reference_sql(ddl_assets: Iterable[tuple[str, str]]) -> dict[str, Any]:
    """Pure dry plan; supplied strings only, no driver, tokens, files or writes."""
    ddl = _ordered_ddl(ddl_assets)
    contracts = _contracts()
    return {
        "state": "PLAN_ONLY", "catalogState": "UNINSPECTED", "schema": "agent_ref",
        "objects": dict(contracts.EXPECTED_OBJECTS),
        "outputColumnCounts": {name: len(columns) for name, columns in contracts.OUTPUT_COLUMNS.items()},
        "files": [
            {"path": name, "sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest()}
            for name, sql in ddl
        ],
    }


def _query(cursor: SqlCursor, sql: str) -> list[dict[str, Any]]:
    _private_call(lambda: cursor.execute(sql), "Native SQL catalog read failed; no success is claimed.")
    description = _private_call(
        lambda: cursor.description, "Native SQL catalog schema read failed; no success is claimed.",
    )
    if description is None:
        raise ReferenceSqlError("Native SQL catalog query returned no schema.")
    names = [column[0] for column in description]
    if any(not isinstance(name, str) for name in names) or len(set(names)) != len(names):
        raise ReferenceSqlError("Native SQL catalog query returned ambiguous column names.")
    values = _private_call(lambda: cursor.fetchall(), "Native SQL catalog fetch failed; no success is claimed.")
    if any(len(row) != len(names) for row in values):
        raise ReferenceSqlError("Native SQL catalog query returned an incomplete row.")
    return [dict(zip(names, row)) for row in values]


def read_native_catalog(cursor: SqlCursor, *, database: str) -> dict[str, Any]:
    """Read a complete native snapshot through an already-open injected cursor."""
    contracts = _contracts()
    catalog = {}
    for name, sql in contracts.CATALOG_QUERIES.items():
        rows = _query(cursor, sql)
        if name in ("state", "integrity"):
            if len(rows) != 1:
                raise ReferenceSqlError(f"Native {name} catalog must contain exactly one row.")
            catalog[name] = rows[0]
        else:
            catalog[name] = rows
        if name == "state":
            contracts.validate_catalog_state(catalog[name], database=database)
        elif name == "sourceColumns":
            contracts.validate_source_catalog(rows)
    return catalog


def _execute(cursor: SqlCursor, sql: str) -> None:
    message = (
        "SQL reference DDL/session setup failed. No success is claimed; any partially "
        "created objects are left intact and will require explicit operator resolution."
    )
    _private_call(lambda: cursor.execute(sql), message)
    # Some DB-API errors arrive only while draining subsequent result sets.
    while _private_call(lambda: cursor.nextset(), message):
        pass


def _native_result(catalog: Mapping[str, Any], decision: str, executed: list[str]) -> dict[str, Any]:
    contracts = _contracts()
    return {
        "state": "REUSED" if decision == "reuse" else "CREATED",
        "schema": "agent_ref", "catalogVerified": True, "executedFiles": executed,
        "objects": dict(contracts.EXPECTED_OBJECTS),
        "outputColumnCounts": {name: len(columns) for name, columns in contracts.OUTPUT_COLUMNS.items()},
        "nativeCatalog": {
            "provenance": "sys.objects/sys.sql_modules/sys.columns/sys.parameters",
            "agentSerializedTypesModified": False,
            "objects": [
                {
                    "name": row["ObjectName"], "type": row["ObjectType"],
                    "definitionSha256": hashlib.sha256(
                        " ".join(contracts.definition_tokens(row["Definition"])).encode("utf-8")
                    ).hexdigest(),
                }
                for row in catalog["objects"]
            ],
            "columns": [dict(row) for row in catalog["columns"]],
            "parameters": [dict(row) for row in catalog["parameters"]],
        },
    }


def deploy_reference_sql(
    lakehouse: Mapping[str, Any],
    ddl_assets: Iterable[tuple[str, str]],
    token_provider: Callable[[], str],
    *,
    db_driver: SqlDriver | None = None,
    connect_timeout: int = 30,
    query_timeout: int = 180,
    source_wait_timeout: int = 0,
    poll_interval: int = 10,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """CREATE all absent objects, reuse all exact, otherwise explicitly fail.

    ``db_driver`` is pyodbc-compatible (drivers/connect) for offline tests.
    The token callable is invoked exactly once, only after local plan, discovery,
    timeout and native driver validation. Connections/cursors are always closed.
    No token or raw driver/provider error becomes a returned value or log.
    Optional bounded readiness polling retries only missing source-column
    metadata before DDL; type, permission and integrity conflicts fail at once.
    A post-CREATE catalog read is still immediate and is never retried.
    """
    ddl = _ordered_ddl(ddl_assets)
    endpoint = resolve_sql_endpoint(lakehouse)
    connection_string = odbc_connection_string(endpoint)
    for value in (connect_timeout, query_timeout):
        if type(value) is not int or not 1 <= value <= 3600:
            raise ValueError("SQL connection/query timeouts must be integers from 1 through 3600 seconds.")
    if type(source_wait_timeout) is not int or not 0 <= source_wait_timeout <= 7200:
        raise ValueError("SQL source readiness timeout must be an integer from 0 through 7200 seconds.")
    if type(poll_interval) is not int or not 1 <= poll_interval <= 120:
        raise ValueError("SQL source readiness poll interval must be an integer from 1 through 120 seconds.")
    if not callable(token_provider):
        raise ValueError("An injected zero-argument SQL token provider is required.")
    driver = require_odbc_driver(db_driver)
    connection = cursor = None
    token = packed = None
    try:
        try:
            token = _private_call(token_provider, "SQL token acquisition failed; provider details are suppressed.")
            packed = pack_sql_access_token(token)
            connection = _private_call(
                lambda: driver.connect(
                    connection_string, attrs_before={SQL_ACCESS_TOKEN_ATTRIBUTE: packed},
                    autocommit=True, timeout=connect_timeout,
                ),
                "SQL connection failed. Check the discovered endpoint, database, SQL audience and TDS access; "
                "driver details are suppressed.",
            )
        finally:
            token = packed = None
        # pyodbc exposes query timeout on Connection, inherited by new cursors;
        # Cursor.timeout is not a supported pyodbc attribute.
        _private_call(
            lambda: setattr(connection, "timeout", query_timeout),
            "SQL query timeout could not be configured.",
        )
        cursor = _private_call(lambda: connection.cursor(), "SQL cursor creation failed; driver details are suppressed.")
        _execute(cursor, "SET NOCOUNT ON; SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;")
        contracts = _contracts()
        deadline = clock() + source_wait_timeout
        while True:
            try:
                before = read_native_catalog(cursor, database=endpoint["database"])
            except contracts.SourceCatalogNotReady:
                if source_wait_timeout == 0:
                    raise
                remaining = deadline - clock()
                if remaining <= 0:
                    raise ReferenceSqlError(
                        "Required dbo columns did not become visible at the SQL endpoint before timeout. "
                        "Wait for Notebook01 SQL metadata synchronization; no reference DDL was attempted."
                    ) from None
                sleeper(min(poll_interval, remaining))
            else:
                break
        decision = contracts.catalog_decision(before, ddl, database=endpoint["database"])
        executed = []
        after = before
        if decision == "fresh":
            for name, sql in ddl:
                if name == "001_create_schema.sql" and before["state"]["SchemaId"] is not None:
                    continue
                _execute(cursor, contracts.split_batches(sql)[0])
                executed.append(name)
            # No sleep, retry, or optimistic success after a CREATE response.
            after = read_native_catalog(cursor, database=endpoint["database"])
            if contracts.catalog_decision(after, ddl, database=endpoint["database"]) != "reuse":
                raise ReferenceSqlError("Immediate native catalog re-read did not confirm all six exact SQL objects.")
        return _native_result(after, decision, executed)
    finally:
        failed = sys.exc_info()[0] is not None
        close_failed = False
        for resource in (cursor, connection):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    close_failed = True
        if close_failed and not failed:
            raise ReferenceSqlError("SQL resource closure failed; driver details are suppressed.")
