"""Pure, fail-closed contracts for the six packaged ``agent_ref`` SQL objects.

Import and supplied-string plan/catalog validation do not read repository files,
change sys.path, acquire credentials, or deploy. ``load_ddl``/``build_plan`` are
explicit local-file helpers. The CLI loader and the opt-in notebook adapter
share these contracts; neither may infer ownership from an object count.

Output types below describe SQL, not serialized Agent metadata. Pass-through
length/precision/scale come from the native dbo source catalog, not blank Agent
type fields. TVF result columns belong to sys.columns; sys.parameters describes
only their inputs. T-SQL parameter defaults are checked in the module definition
because sys.parameters.has_default_value does not describe T-SQL defaults.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Mapping

ROOT = Path(__file__).resolve().parent
DDL_ORDER = (
    "001_create_schema.sql",
    "010_municipality_static.sql",
    "020_donation_attributes.sql",
    "030_gift_catalog_suppliers.sql",
    "040_municipality_by_id.sql",
    "050_donation_by_id.sql",
    "060_donation_trace_by_id.sql",
)
EXPECTED_OBJECTS = {
    "MunicipalityStatic": "VIEW",
    "DonationAttributes": "VIEW",
    "GiftCatalogSuppliers": "VIEW",
    "MunicipalityById": "SQL_INLINE_TABLE_VALUED_FUNCTION",
    "DonationById": "SQL_INLINE_TABLE_VALUED_FUNCTION",
    "DonationTraceById": "SQL_INLINE_TABLE_VALUED_FUNCTION",
}
OBJECT_FILES = dict(zip(EXPECTED_OBJECTS, DDL_ORDER[1:]))


class SourceCatalogNotReady(RuntimeError):
    """A required dbo source column has not appeared at the SQL endpoint yet."""


def _source_types(*, strings: str = "", bigints: str = "", timestamps: str = "") -> dict[str, str]:
    return {
        **dict.fromkeys(strings.split(), "varchar"),
        **dict.fromkeys(bigints.split(), "bigint"),
        **dict.fromkeys(timestamps.split(), "datetime2"),
    }


# Notebook01's published dbo tables must be visible at the SQL endpoint first.
# These are type families; forwarded string widths/timestamp precision are read
# natively rather than guessed from a serialized Agent datasource.
SOURCE_TYPES = {
    "ot_municipality": _source_types(
        strings="MunicipalityId MunicipalityName MunicipalityDisplayName",
        bigints="PrefectureId MunicipalityStaticCount MunicipalityStaticTotalYen "
        "MunicipalityAmountRank MunicipalityPrefAmountRank",
    ),
    "ot_prefecture": _source_types(
        strings="PrefectureName PrefectureNameEn",
        bigints="PrefectureId PrefReceivedStaticCount PrefReceivedTotalYen PrefReceivedAmountRank "
        "PrefResidentStaticCount PrefResidentTotalYen PrefResidentAmountRank",
    ),
    "ot_donation": _source_types(
        strings="DonationDisplayName DonatedAtJstText DonationDateJst DonationYearMonthJst "
        "DonationYearMonthJaShort DonationPaymentMethod DonationPaymentMethodEn DonationDataLayer MunicipalityId",
        bigints="DonationId DonationAmountYen DonorId GiftId", timestamps="DonatedAtUtc",
    ),
    "ot_donor": _source_types(
        strings="DonorName DonorDisplayName DonorOccupation DonorOccupationEn",
        bigints="DonorId DonorAge PrefectureId DonorStaticCount DonorStaticTotalYen "
        "DonorStaticMaxYen DonorOverallAmountRank DonorResidenceAmountRank",
    ),
    "ot_gift": _source_types(
        strings="GiftName GiftDisplayName GiftSearchTerms GiftNotes MunicipalityId",
        bigints="GiftId CategoryId GiftStaticCount GiftStaticTotalYen GiftAmountRank",
    ),
    "ot_gift_category": _source_types(
        strings="CategoryName CategoryNameEn CategorySearchTerms",
        bigints="CategoryId CategoryStaticCount CategoryStaticTotalYen CategoryAmountRank",
    ),
    "ot_supplier": _source_types(
        strings="SupplierName SupplierDisplayName SupplierType SupplierTypeEn",
        bigints="SupplierId PrefectureId SupplierProvidedGiftCount",
    ),
    "ot_supplier_gift": _source_types(bigints="GiftId SupplierId"),
}

# A type expression is either an explicit SQL CAST or a fully qualified source
# column. This keeps aliases and ordinal position explicit, including Trace30.
OUTPUT_COLUMNS = {
    "MunicipalityStatic": (
        ("MunicipalityId", "varchar(6)"),
        ("MunicipalityName", "dbo.ot_municipality.MunicipalityName"),
        ("MunicipalityDisplayName", "dbo.ot_municipality.MunicipalityDisplayName"),
        ("PrefectureId", "dbo.ot_municipality.PrefectureId"),
        ("PrefectureName", "dbo.ot_prefecture.PrefectureName"),
        ("PrefectureNameEn", "dbo.ot_prefecture.PrefectureNameEn"),
        ("MunicipalityStaticCount", "bigint"),
        ("MunicipalityStaticTotalYen", "bigint"),
        ("MunicipalityStoredNationwideAmountRank", "bigint"),
        ("MunicipalityStoredPrefectureAmountRank", "bigint"),
        ("MunicipalityDerivedNationwideCountRank", "bigint"),
        ("DefaultPopularityMetric", "varchar(32)"),
        ("DefaultPopularityValue", "bigint"),
        ("DatasetName", "varchar(64)"),
        ("SourceSystem", "varchar(64)"),
        ("DatasetScope", "varchar(64)"),
        ("CountUnit", "varchar(32)"),
        ("AmountUnit", "varchar(8)"),
        ("NationwideRankScope", "varchar(64)"),
        ("PrefectureRankScope", "varchar(64)"),
    ),
    "DonationAttributes": (
        ("DonationId", "dbo.ot_donation.DonationId"),
        ("DonationDisplayName", "dbo.ot_donation.DonationDisplayName"),
        ("DonationAmountYen", "bigint"),
        ("DonatedAtUtc", "dbo.ot_donation.DonatedAtUtc"),
        ("DonatedAtJstText", "dbo.ot_donation.DonatedAtJstText"),
        ("DonationDateJst", "dbo.ot_donation.DonationDateJst"),
        ("DonationYearMonthJst", "dbo.ot_donation.DonationYearMonthJst"),
        ("DonationYearMonthJaShort", "dbo.ot_donation.DonationYearMonthJaShort"),
        ("DonationPaymentMethod", "dbo.ot_donation.DonationPaymentMethod"),
        ("DonationPaymentMethodEn", "dbo.ot_donation.DonationPaymentMethodEn"),
        ("DonationDataLayer", "dbo.ot_donation.DonationDataLayer"),
        ("DonationDonorId", "dbo.ot_donation.DonorId"),
        ("DonorName", "dbo.ot_donor.DonorName"),
        ("DonorDisplayName", "dbo.ot_donor.DonorDisplayName"),
        ("DonorAge", "dbo.ot_donor.DonorAge"),
        ("DonorOccupation", "dbo.ot_donor.DonorOccupation"),
        ("DonorOccupationEn", "dbo.ot_donor.DonorOccupationEn"),
        ("DonorResidencePrefectureId", "dbo.ot_donor.PrefectureId"),
        ("DonorResidencePrefectureName", "dbo.ot_prefecture.PrefectureName"),
        ("DonorResidencePrefectureNameEn", "dbo.ot_prefecture.PrefectureNameEn"),
        ("DonationRecipientMunicipalityId", "varchar(6)"),
        ("RecipientMunicipalityName", "dbo.ot_municipality.MunicipalityName"),
        ("RecipientMunicipalityDisplayName", "dbo.ot_municipality.MunicipalityDisplayName"),
        ("RecipientPrefectureId", "dbo.ot_municipality.PrefectureId"),
        ("RecipientPrefectureName", "dbo.ot_prefecture.PrefectureName"),
        ("RecipientPrefectureNameEn", "dbo.ot_prefecture.PrefectureNameEn"),
        ("DonationSelectedGiftId", "dbo.ot_donation.GiftId"),
        ("GiftName", "dbo.ot_gift.GiftName"),
        ("GiftDisplayName", "dbo.ot_gift.GiftDisplayName"),
        ("GiftSearchTerms", "dbo.ot_gift.GiftSearchTerms"),
        ("GiftNotes", "dbo.ot_gift.GiftNotes"),
        ("GiftCatalogMunicipalityId", "varchar(6)"),
        ("GiftCategoryId", "dbo.ot_gift.CategoryId"),
        ("GiftCategoryName", "dbo.ot_gift_category.CategoryName"),
        ("GiftCategoryNameEn", "dbo.ot_gift_category.CategoryNameEn"),
        ("GiftCategorySearchTerms", "dbo.ot_gift_category.CategorySearchTerms"),
        ("DatasetName", "varchar(64)"),
        ("SourceSystem", "varchar(64)"),
        ("DatasetScope", "varchar(64)"),
        ("DonationAmountUnit", "varchar(8)"),
    ),
    "GiftCatalogSuppliers": (
        ("GiftCatalogGiftId", "dbo.ot_supplier_gift.GiftId"),
        ("GiftName", "dbo.ot_gift.GiftName"),
        ("GiftDisplayName", "dbo.ot_gift.GiftDisplayName"),
        ("GiftSearchTerms", "dbo.ot_gift.GiftSearchTerms"),
        ("GiftNotes", "dbo.ot_gift.GiftNotes"),
        ("GiftCategoryId", "dbo.ot_gift.CategoryId"),
        ("GiftCategoryName", "dbo.ot_gift_category.CategoryName"),
        ("GiftCategoryNameEn", "dbo.ot_gift_category.CategoryNameEn"),
        ("GiftCategorySearchTerms", "dbo.ot_gift_category.CategorySearchTerms"),
        ("GiftCatalogMunicipalityId", "varchar(6)"),
        ("GiftCatalogMunicipalityName", "dbo.ot_municipality.MunicipalityName"),
        ("GiftCatalogMunicipalityDisplayName", "dbo.ot_municipality.MunicipalityDisplayName"),
        ("GiftCatalogPrefectureId", "dbo.ot_municipality.PrefectureId"),
        ("GiftCatalogPrefectureName", "dbo.ot_prefecture.PrefectureName"),
        ("GiftCatalogPrefectureNameEn", "dbo.ot_prefecture.PrefectureNameEn"),
        ("RegisteredSupplierId", "dbo.ot_supplier_gift.SupplierId"),
        ("RegisteredSupplierName", "dbo.ot_supplier.SupplierName"),
        ("RegisteredSupplierDisplayName", "dbo.ot_supplier.SupplierDisplayName"),
        ("RegisteredSupplierType", "dbo.ot_supplier.SupplierType"),
        ("RegisteredSupplierTypeEn", "dbo.ot_supplier.SupplierTypeEn"),
        ("SupplierLocationPrefectureId", "dbo.ot_supplier.PrefectureId"),
        ("SupplierLocationPrefectureName", "dbo.ot_prefecture.PrefectureName"),
        ("SupplierLocationPrefectureNameEn", "dbo.ot_prefecture.PrefectureNameEn"),
        ("RelationshipMeaning", "varchar(64)"),
        ("RowGrain", "varchar(64)"),
        ("ProvenanceLimit", "varchar(64)"),
        ("DatasetName", "varchar(64)"),
        ("SourceSystem", "varchar(64)"),
        ("DatasetScope", "varchar(64)"),
    ),
}
OUTPUT_COLUMNS["MunicipalityById"] = (
    ("RequestedMunicipalityId", "varchar(64)"), ("RetrievalMode", "varchar(32)"),
) + tuple((name, f"agent_ref.MunicipalityStatic.{name}") for name, _ in OUTPUT_COLUMNS["MunicipalityStatic"])
OUTPUT_COLUMNS["DonationById"] = (
    ("RequestedDonationId", "bigint"), ("RetrievalMode", "varchar(32)"),
) + tuple((name, f"agent_ref.DonationAttributes.{name}") for name, _ in OUTPUT_COLUMNS["DonationAttributes"])
OUTPUT_COLUMNS["DonationTraceById"] = (
    ("RequestedDonationId", "bigint"),
    ("RetrievalMode", "varchar(32)"),
    ("DonationId", "agent_ref.DonationAttributes.DonationId"),
    ("DonationDisplayName", "agent_ref.DonationAttributes.DonationDisplayName"),
    ("DonationAmountYen", "agent_ref.DonationAttributes.DonationAmountYen"),
    ("DonorId", "agent_ref.DonationAttributes.DonationDonorId"),
    ("DonorName", "agent_ref.DonationAttributes.DonorName"),
    ("DonorDisplayName", "agent_ref.DonationAttributes.DonorDisplayName"),
    ("DonorResidencePrefectureId", "agent_ref.DonationAttributes.DonorResidencePrefectureId"),
    ("DonorResidencePrefectureName", "agent_ref.DonationAttributes.DonorResidencePrefectureName"),
    ("MunicipalityId", "agent_ref.DonationAttributes.DonationRecipientMunicipalityId"),
    ("MunicipalityName", "agent_ref.DonationAttributes.RecipientMunicipalityName"),
    ("MunicipalityDisplayName", "agent_ref.DonationAttributes.RecipientMunicipalityDisplayName"),
    ("RecipientPrefectureId", "agent_ref.DonationAttributes.RecipientPrefectureId"),
    ("RecipientPrefectureName", "agent_ref.DonationAttributes.RecipientPrefectureName"),
    ("GiftId", "agent_ref.DonationAttributes.DonationSelectedGiftId"),
    ("GiftName", "agent_ref.DonationAttributes.GiftName"),
    ("GiftDisplayName", "agent_ref.DonationAttributes.GiftDisplayName"),
    ("CategoryId", "agent_ref.DonationAttributes.GiftCategoryId"),
    ("CategoryName", "agent_ref.DonationAttributes.GiftCategoryName"),
    ("SupplierId", "agent_ref.GiftCatalogSuppliers.RegisteredSupplierId"),
    ("SupplierName", "agent_ref.GiftCatalogSuppliers.RegisteredSupplierName"),
    ("SupplierDisplayName", "agent_ref.GiftCatalogSuppliers.RegisteredSupplierDisplayName"),
    ("SupplierType", "agent_ref.GiftCatalogSuppliers.RegisteredSupplierType"),
    ("SupplierTypeEn", "agent_ref.GiftCatalogSuppliers.RegisteredSupplierTypeEn"),
    ("DatasetName", "agent_ref.DonationAttributes.DatasetName"),
    ("SourceSystem", "agent_ref.DonationAttributes.SourceSystem"),
    ("DatasetScope", "agent_ref.DonationAttributes.DatasetScope"),
    ("DonationAmountUnit", "agent_ref.DonationAttributes.DonationAmountUnit"),
    ("RowGrain", "varchar(96)"),
)
INPUT_PARAMETERS = {
    "MunicipalityById": (("@RequestedMunicipalityId", "varchar(64)"),),
    "DonationById": (("@RequestedDonationId", "bigint"),),
    "DonationTraceById": (("@RequestedDonationId", "bigint"),),
}

_UNIQUE_KEYS = {
    "DuplicateMunicipalityKeys": ("ot_municipality", "MunicipalityId"),
    "DuplicatePrefectureKeys": ("ot_prefecture", "PrefectureId"),
    "DuplicateDonationKeys": ("ot_donation", "DonationId"),
    "DuplicateDonorKeys": ("ot_donor", "DonorId"),
    "DuplicateGiftKeys": ("ot_gift", "GiftId"),
    "DuplicateCategoryKeys": ("ot_gift_category", "CategoryId"),
    "DuplicateSupplierKeys": ("ot_supplier", "SupplierId"),
    "DuplicateSupplierGiftKeys": ("ot_supplier_gift", "SupplierId, GiftId"),
}
_INTEGRITY_EXPRESSIONS = {
    name: f"(SELECT COUNT_BIG(*) FROM (SELECT {key} FROM dbo.{table} "
    f"GROUP BY {key} HAVING COUNT_BIG(*) > 1) AS q)"
    for name, (table, key) in _UNIQUE_KEYS.items()
}
_INTEGRITY_EXPRESSIONS.update({
    "OrphanDonationDonors": "(SELECT COUNT_BIG(*) FROM dbo.ot_donation d "
    "LEFT JOIN dbo.ot_donor x ON x.DonorId=d.DonorId WHERE x.DonorId IS NULL)",
    "OrphanDonationMunicipalities": "(SELECT COUNT_BIG(*) FROM dbo.ot_donation d "
    "LEFT JOIN dbo.ot_municipality x ON x.MunicipalityId=d.MunicipalityId WHERE x.MunicipalityId IS NULL)",
    "OrphanDonationGifts": "(SELECT COUNT_BIG(*) FROM dbo.ot_donation d "
    "LEFT JOIN dbo.ot_gift x ON x.GiftId=d.GiftId WHERE x.GiftId IS NULL)",
    "OrphanSupplierGiftRows": "(SELECT COUNT_BIG(*) FROM dbo.ot_supplier_gift b "
    "LEFT JOIN dbo.ot_supplier s ON s.SupplierId=b.SupplierId "
    "LEFT JOIN dbo.ot_gift g ON g.GiftId=b.GiftId WHERE s.SupplierId IS NULL OR g.GiftId IS NULL)",
})
INTEGRITY_FIELDS = tuple(_INTEGRITY_EXPRESSIONS)
CATALOG_QUERIES = {
    "state": """
SELECT DB_NAME() AS DatabaseName, SCHEMA_ID('agent_ref') AS SchemaId,
       (SELECT name FROM sys.schemas WHERE schema_id=SCHEMA_ID('agent_ref')) AS SchemaName,
       HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DEFINITION') AS CanViewDefinition,
       HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CREATE SCHEMA') AS CanCreateSchema,
       HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CREATE VIEW') AS CanCreateView,
       HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CREATE FUNCTION') AS CanCreateFunction,
       HAS_PERMS_BY_NAME('agent_ref', 'SCHEMA', 'ALTER') AS CanAlterSchema;
""",
    "objects": """
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       RTRIM(o.type) AS ObjectTypeCode, m.definition AS Definition,
       m.uses_ansi_nulls AS UsesAnsiNulls, m.uses_quoted_identifier AS UsesQuotedIdentifier,
       m.is_schema_bound AS IsSchemaBound, m.execute_as_principal_id AS ExecuteAsPrincipalId
FROM sys.objects AS o
JOIN sys.schemas AS s ON s.schema_id=o.schema_id
LEFT JOIN sys.sql_modules AS m ON m.object_id=o.object_id
WHERE s.name='agent_ref'
ORDER BY o.name;
""",
    "columns": """
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       c.column_id AS OrdinalPosition, c.name AS ColumnName, t.name AS DataType,
       ts.name AS TypeSchema, t.is_user_defined AS IsUserDefined,
       c.max_length AS MaxLength, c.precision AS [Precision], c.scale AS Scale,
       c.is_nullable AS IsNullable
FROM sys.objects AS o
JOIN sys.schemas AS s ON s.schema_id=o.schema_id
JOIN sys.columns AS c ON c.object_id=o.object_id
JOIN sys.types AS t ON t.user_type_id=c.user_type_id
JOIN sys.schemas AS ts ON ts.schema_id=t.schema_id
WHERE s.name='agent_ref'
ORDER BY o.name, c.column_id;
""",
    "parameters": """
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       p.parameter_id AS ParameterId, p.name AS ParameterName, t.name AS DataType,
       ts.name AS TypeSchema, t.is_user_defined AS IsUserDefined,
       p.max_length AS MaxLength, p.precision AS [Precision], p.scale AS Scale,
       p.is_output AS IsOutput, p.is_readonly AS IsReadOnly,
       p.has_default_value AS HasDefaultValue
FROM sys.objects AS o
JOIN sys.schemas AS s ON s.schema_id=o.schema_id
JOIN sys.parameters AS p ON p.object_id=o.object_id
JOIN sys.types AS t ON t.user_type_id=p.user_type_id
JOIN sys.schemas AS ts ON ts.schema_id=t.schema_id
WHERE s.name='agent_ref'
ORDER BY o.name, p.parameter_id;
""",
    # User types are schema-scoped but are not all represented in sys.objects.
    "types": """
SELECT s.name AS SchemaName, t.name AS TypeName
FROM sys.types AS t JOIN sys.schemas AS s ON s.schema_id=t.schema_id
WHERE s.name='agent_ref';
""",
    "sourceColumns": """
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       c.column_id AS OrdinalPosition, c.name AS ColumnName, t.name AS DataType,
       ts.name AS TypeSchema, t.is_user_defined AS IsUserDefined,
       c.max_length AS MaxLength, c.precision AS [Precision], c.scale AS Scale,
       c.is_nullable AS IsNullable
FROM sys.objects AS o
JOIN sys.schemas AS s ON s.schema_id=o.schema_id
JOIN sys.columns AS c ON c.object_id=o.object_id
JOIN sys.types AS t ON t.user_type_id=c.user_type_id
JOIN sys.schemas AS ts ON ts.schema_id=t.schema_id
WHERE s.name='dbo'
  AND o.name IN ('ot_municipality','ot_prefecture','ot_donation','ot_donor',
                 'ot_gift','ot_gift_category','ot_supplier','ot_supplier_gift')
ORDER BY o.name, c.column_id;
""",
    "integrity": "SELECT\n" + ",\n".join(
        f" {expression} AS {name}" for name, expression in _INTEGRITY_EXPRESSIONS.items()
    ) + ";",
}
TYPE_FIELDS = ("DataType", "TypeSchema", "MaxLength", "Precision", "Scale", "IsUserDefined")
FORBIDDEN_SQL = re.compile(
    r"\b(?:ALTER|DROP|GRANT|DENY|REVOKE|INSERT|UPDATE|DELETE|MERGE|TRUNCATE|EXEC(?:UTE)?|"
    r"BEGIN\s+TRAN(?:SACTION)?|COMMIT|ROLLBACK)\b",
    re.IGNORECASE,
)
SERVER_PATTERN = re.compile(
    r"^[a-z0-9-]+\.datawarehouse\.fabric\.microsoft\.com$", re.IGNORECASE
)
DATABASE_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,128}$")
USER_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+$")
GUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
MUNICIPALITY_LOOKUP_PATTERN = re.compile(r"^[0-9]{6}$")
BIGINT_MAX = 9_223_372_036_854_775_807
_SQL_TOKENS = re.compile(
    r"\s+|--[^\r\n]*|/\*.*?\*/|'(?:''|[^'])*'|\[(?:\]\]|[^\]])*\]|"
    r'"(?:""|[^"])*"|@[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*|[0-9]+|.',
    re.DOTALL,
)


def split_batches(sql: str) -> tuple[str, ...]:
    return tuple(
        batch.strip()
        for batch in re.split(r"(?im)^\s*GO\s*(?:--.*)?$", sql)
        if batch.strip()
    )


def load_ddl(root: Path = ROOT) -> tuple[tuple[str, str], ...]:
    return tuple((name, (root / name).read_text("utf-8")) for name in DDL_ORDER)


def validate_runtime(
    server: str, database: str, expected_user: str, tenant_id: str, subscription_id: str
) -> None:
    if not SERVER_PATTERN.fullmatch(server):
        raise ValueError("Server must be a Fabric datawarehouse FQDN.")
    if not DATABASE_PATTERN.fullmatch(database):
        raise ValueError("Database must be a simple SQL identifier.")
    if not USER_PATTERN.fullmatch(expected_user):
        raise ValueError("Expected user must be a UPN.")
    if not GUID_PATTERN.fullmatch(tenant_id) or not GUID_PATTERN.fullmatch(subscription_id):
        raise ValueError("Tenant and subscription IDs must be GUIDs.")


def validate_municipality_lookup_id(value: object) -> str:
    if not isinstance(value, str) or not MUNICIPALITY_LOOKUP_PATTERN.fullmatch(value):
        raise ValueError("Municipality lookup ID must be exactly six ASCII digits.")
    return value


def validate_donation_lookup_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= BIGINT_MAX:
        raise ValueError("Donation lookup ID must be a non-negative SQL bigint.")
    return value


def definition_tokens(sql: str) -> tuple[str, ...]:
    """Ignore formatting/comments, never whitespace or case inside SQL literals."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("SQL definition is missing; exact verification is impossible.")
    batches = split_batches(sql)
    if len(batches) != 1:
        raise ValueError("SQL definition must be one batch.")
    tokens = tuple(
        token for token in _SQL_TOKENS.findall(batches[0])
        if not token.isspace() and not token.startswith(("--", "/*"))
    )
    return tokens[:-1] if tokens and tokens[-1] == ";" else tokens


def _projection_names(sql: str) -> tuple[str, ...]:
    """Read the outer SELECT of this small frozen DDL dialect, not arbitrary SQL."""
    tokens = definition_tokens(sql)
    depth, selects = 0, []
    for index, token in enumerate(tokens):
        if token.upper() == "SELECT":
            selects.append((depth, index))
        depth += (token == "(") - (token == ")")
        if depth < 0:
            raise ValueError("Unbalanced SQL definition.")
    if depth or not selects:
        raise ValueError("Unbalanced SQL definition or missing SELECT.")
    select_depth, start = min(selects)
    expressions, current, depth = [], [], select_depth
    for token in tokens[start + 1:]:
        if token.upper() == "FROM" and depth == select_depth:
            expressions.append(current)
            break
        if token == "," and depth == select_depth:
            expressions.append(current)
            current = []
        else:
            current.append(token)
        depth += (token == "(") - (token == ")")
    else:
        raise ValueError("Outer SELECT has no FROM.")
    result = []
    for expression in expressions:
        if expression == ["donation", ".", "*"]:
            result.extend(name for name, _ in OUTPUT_COLUMNS["DonationAttributes"])
        elif expression and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", expression[-1]):
            result.append(expression[-1])
        else:
            raise ValueError("Every output must have an explicit, known column name.")
    return tuple(result)


def _is_bit(value: object) -> bool:
    return type(value) in (bool, int) and value in (0, 1)


def _native_type(row: Mapping[str, object]) -> tuple[object, ...]:
    if (
        not isinstance(row.get("DataType"), str)
        or not row["DataType"]
        or row.get("TypeSchema") != "sys"
        or not _is_bit(row.get("IsUserDefined"))
        or row["IsUserDefined"] != 0
        or any(type(row.get(key)) is not int for key in ("MaxLength", "Precision", "Scale"))
        or not -1 <= row["MaxLength"] <= 8000
        or not 0 <= row["Precision"] <= 38
        or not 0 <= row["Scale"] <= 38
    ):
        raise RuntimeError("Native catalog type metadata is missing, invalid, or user-defined.")
    return tuple(row[key] for key in TYPE_FIELDS)


def _cast_type(sql_type: str) -> tuple[object, ...]:
    if sql_type == "bigint":
        return ("bigint", "sys", 8, 19, 0, 0)
    match = re.fullmatch(r"varchar\(([1-9][0-9]*)\)", sql_type)
    if match:
        return ("varchar", "sys", int(match[1]), 0, 0, 0)
    raise ValueError(f"Unsupported fixed SQL contract type: {sql_type}")


def validate_source_catalog(
    source_columns: Iterable[Mapping[str, object]],
) -> dict[tuple[str, str], Mapping[str, object]]:
    """Require native source tables/columns; never refresh or mutate dbo tables."""
    result: dict[tuple[str, str], Mapping[str, object]] = {}
    for row in source_columns:
        key = (row.get("ObjectName"), row.get("ColumnName"))
        if (
            row.get("SchemaName") != "dbo"
            or row.get("ObjectType") != "USER_TABLE"
            or key[0] not in SOURCE_TYPES
            or key in result
        ):
            raise RuntimeError("Source catalog is ambiguous or is not the required dbo USER_TABLE catalog.")
        result[key] = row
    for table, columns in SOURCE_TYPES.items():
        for column, family in columns.items():
            row = result.get((table, column))
            if row is None:
                raise SourceCatalogNotReady(f"Required source column dbo.{table}.{column} is missing.")
            native = _native_type(row)
            if row["DataType"] != family or not _is_bit(row.get("IsNullable")):
                raise RuntimeError(f"Source type mismatch for dbo.{table}.{column}.")
            if family == "bigint" and native != _cast_type("bigint"):
                raise RuntimeError(f"Source bigint metadata mismatch for dbo.{table}.{column}.")
            if family == "varchar" and (
                row["MaxLength"] == 0 or row["Precision"] != 0 or row["Scale"] != 0
            ):
                raise RuntimeError(f"Source varchar metadata mismatch for dbo.{table}.{column}.")
    return result


def expected_native_columns(
    source_columns: Iterable[Mapping[str, object]],
) -> dict[str, tuple[dict[str, object], ...]]:
    """Resolve expected SQL types against native sources, without inventing Agent fields.

    Nullability is retained in the actual catalog as an observation, not guessed
    for SQL expressions (notably ROW_NUMBER, casts, parameters and LEFT JOINs).
    Names, SQL type/schema, width, precision, scale and output order are exact.
    """
    sources = validate_source_catalog(source_columns)
    resolved: dict[tuple[str, str], tuple[object, ...]] = {}
    result = {}
    for name, specs in OUTPUT_COLUMNS.items():
        columns = []
        for ordinal, (column, expression) in enumerate(specs, 1):
            if expression.startswith("dbo."):
                _, table, source_column = expression.split(".")
                native = _native_type(sources[(table, source_column)])
            elif expression.startswith("agent_ref."):
                _, view, source_column = expression.split(".")
                native = resolved[(view, source_column)]
            else:
                native = _cast_type(expression)
            resolved[(name, column)] = native
            columns.append({
                "ColumnName": column, "OrdinalPosition": ordinal,
                **dict(zip(TYPE_FIELDS, native)),
            })
        result[name] = tuple(columns)
    return result


def collision_decision(
    schema_id: int | None,
    objects: Iterable[Mapping[str, object]],
    *,
    columns: Iterable[Mapping[str, object]] = (),
    parameters: Iterable[Mapping[str, object]] = (),
    source_columns: Iterable[Mapping[str, object]] = (),
    ddl: tuple[tuple[str, str], ...] | None = None,
) -> str:
    """Return fresh/reuse, or refuse partial/foreign/unverifiable existing objects.

    An empty existing schema is fresh, irrespective of its owner; the caller
    must verify catalog visibility and CREATE/ALTER rights and skip schema DDL.
    No ownership transfer, ALTER, DROP, or automatic partial repair is allowed.
    """
    objects, columns, parameters = tuple(objects), tuple(columns), tuple(parameters)
    if not objects:
        if columns or parameters:
            raise RuntimeError("Inconsistent empty agent_ref catalog; deployment refused.")
        return "fresh"
    names = [row.get("ObjectName") for row in objects]
    if schema_id is None or len(names) != len(EXPECTED_OBJECTS) or set(names) != set(EXPECTED_OBJECTS):
        missing = sorted(set(EXPECTED_OBJECTS) - set(names))
        foreign = sorted(str(name) for name in set(names) - set(EXPECTED_OBJECTS))
        raise RuntimeError(
            "Partial or foreign agent_ref objects; deployment refused. "
            f"Missing: {missing}; foreign: {foreign}. No automatic repair is performed."
        )
    ddl = load_ddl() if ddl is None else ddl
    validate_plan(ddl)
    definitions = dict(ddl)
    for row in objects:
        name = row["ObjectName"]
        expected_type = EXPECTED_OBJECTS[name]
        if (
            row.get("SchemaName") != "agent_ref"
            or row.get("ObjectType") != expected_type
            or row.get("ObjectTypeCode") != ("V" if expected_type == "VIEW" else "IF")
            or row.get("UsesAnsiNulls") != 1
            or row.get("UsesQuotedIdentifier") != 1
            or row.get("IsSchemaBound") != 0
            or "ExecuteAsPrincipalId" not in row
            or row["ExecuteAsPrincipalId"] is not None
        ):
            raise RuntimeError(f"Native object type/module settings mismatch for agent_ref.{name}.")
        try:
            actual = definition_tokens(row.get("Definition"))
        except ValueError:
            raise RuntimeError(f"Native definition unavailable for agent_ref.{name}.") from None
        if actual != definition_tokens(definitions[OBJECT_FILES[name]]):
            raise RuntimeError(f"Native definition mismatch for agent_ref.{name}.")
    expected = expected_native_columns(source_columns)
    for rows, label in ((columns, "column"), (parameters, "parameter")):
        if any(
            row.get("SchemaName") != "agent_ref"
            or row.get("ObjectName") not in EXPECTED_OBJECTS
            or row.get("ObjectType") != EXPECTED_OBJECTS.get(row.get("ObjectName"))
            for row in rows
        ):
            raise RuntimeError(f"Foreign or invalid native {label} catalog.")
    for name in EXPECTED_OBJECTS:
        actual_columns = [row for row in columns if row["ObjectName"] == name]
        if len(actual_columns) != len(expected[name]):
            raise RuntimeError(f"Native output column count mismatch for agent_ref.{name}.")
        if any(type(row.get("OrdinalPosition")) is not int for row in actual_columns):
            raise RuntimeError(f"Native output order unavailable for agent_ref.{name}.")
        for actual, wanted in zip(sorted(actual_columns, key=lambda row: row["OrdinalPosition"]), expected[name]):
            if (
                actual.get("ColumnName") != wanted["ColumnName"]
                or actual["OrdinalPosition"] != wanted["OrdinalPosition"]
                or _native_type(actual) != tuple(wanted[key] for key in TYPE_FIELDS)
                or not _is_bit(actual.get("IsNullable"))
            ):
                raise RuntimeError(
                    f"Native output name/type/order mismatch for agent_ref.{name}.{wanted['ColumnName']}."
                )
        actual_parameters = [row for row in parameters if row["ObjectName"] == name]
        wanted_parameters = INPUT_PARAMETERS.get(name, ())
        if len(actual_parameters) != len(wanted_parameters):
            raise RuntimeError(f"Native input parameter count mismatch for agent_ref.{name}.")
        if any(type(row.get("ParameterId")) is not int for row in actual_parameters):
            raise RuntimeError(f"Native input parameter order unavailable for agent_ref.{name}.")
        for ordinal, (actual, (parameter_name, sql_type)) in enumerate(
            zip(sorted(actual_parameters, key=lambda row: row["ParameterId"]), wanted_parameters), 1
        ):
            if (
                actual["ParameterId"] != ordinal or actual.get("ParameterName") != parameter_name
                or _native_type(actual) != _cast_type(sql_type)
                or any(actual.get(flag) != 0 for flag in ("IsOutput", "IsReadOnly", "HasDefaultValue"))
            ):
                raise RuntimeError(f"Native input parameter schema mismatch for agent_ref.{name}.")
    return "reuse"


def validate_catalog_state(state: Mapping[str, object], *, database: str) -> None:
    if state.get("DatabaseName") != database:
        raise RuntimeError("Native SQL database does not match the discovered database displayName.")
    if state.get("CanViewDefinition") != 1:
        raise RuntimeError(
            "Database VIEW DEFINITION visibility is required to distinguish absent from hidden objects. "
            "Deployment refused; this loader never changes permissions."
        )
    if "SchemaId" not in state or (
        state["SchemaId"] is not None
        and (type(state["SchemaId"]) is not int or state["SchemaId"] <= 0)
    ):
        raise RuntimeError("Native schema state is missing or invalid.")
    if state.get("SchemaName") != (None if state["SchemaId"] is None else "agent_ref"):
        raise RuntimeError("Native schema name/case mismatch; deployment refused.")


def catalog_decision(
    catalog: Mapping[str, object],
    ddl: tuple[tuple[str, str], ...],
    *,
    database: str,
) -> str:
    """Validate a complete native snapshot before CREATE or a successful reuse."""
    validate_plan(ddl)
    if any(key not in catalog for key in CATALOG_QUERIES):
        raise RuntimeError("Incomplete native catalog snapshot; deployment refused.")
    state = catalog["state"]
    validate_catalog_state(state, database=database)
    if catalog["types"]:
        raise RuntimeError("Foreign schema-scoped types exist in agent_ref; deployment refused.")
    decision = collision_decision(
        state["SchemaId"], catalog["objects"],
        columns=catalog["columns"], parameters=catalog["parameters"],
        source_columns=catalog["sourceColumns"], ddl=ddl,
    )
    validate_source_catalog(catalog["sourceColumns"])
    integrity = catalog["integrity"]
    for field in INTEGRITY_FIELDS:
        if type(integrity.get(field)) is not int or integrity[field] != 0:
            raise RuntimeError(f"Source integrity gate {field} failed or is unavailable.")
    if decision == "fresh":
        required = ["CanCreateView", "CanCreateFunction"]
        required.append("CanCreateSchema" if state["SchemaId"] is None else "CanAlterSchema")
        if any(state.get(permission) != 1 for permission in required):
            raise RuntimeError(
                "Creating agent_ref objects requires database CREATE VIEW/CREATE FUNCTION and "
                "CREATE SCHEMA (absent schema) or ALTER on the empty existing schema. "
                "Ownership is not inferred and permissions are never changed."
            )
    return decision


def _assert_query_contract(name: str, sql: str) -> None:
    lowered = sql.lower()
    if name == "010_municipality_static.sql":
        required = (
            "from dbo.ot_municipality as m",
            "left join dbo.ot_prefecture as p",
            "row_number() over",
            "m.municipalitystaticcount",
            "m.municipalityid",
            "allmunicipalitiesincludingzerodonation",
        )
    elif name == "020_donation_attributes.sql":
        required = (
            "from dbo.ot_donation as d",
            "left join dbo.ot_donor as donor",
            "left join dbo.ot_prefecture as residence_pref",
            "left join dbo.ot_municipality as recipient_mun",
            "left join dbo.ot_prefecture as recipient_pref",
            "left join dbo.ot_gift as gift",
            "left join dbo.ot_gift_category as category",
            "d.donatedatutc",
        )
        if "ot_supplier" in lowered:
            raise ValueError("DonationAttributes must remain at Donation grain.")
        repeated_aggregates = (
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
        )
        if any(column in lowered for column in repeated_aggregates):
            raise ValueError("DonationAttributes cannot repeat dimension aggregates.")
    elif name == "030_gift_catalog_suppliers.sql":
        required = (
            "from dbo.ot_supplier_gift as bridge",
            "left join dbo.ot_supplier as supplier",
            "bridge.giftid",
            "bridge.supplierid",
            "registeredcatalogsupplier",
            "nomanufactureorshipmentclaim",
        )
        if "string_agg" in lowered or "top 1" in lowered:
            raise ValueError("Supplier registrations cannot be collapsed or selected arbitrarily.")
        if any(
            column in lowered
            for column in (
                "giftstaticcount",
                "giftstatictotalyen",
                "giftamountrank",
                "supplierprovidedgiftcount",
            )
        ):
            raise ValueError("GiftCatalogSuppliers cannot repeat dimension aggregates.")
    elif name == "040_municipality_by_id.sql":
        required = (
            "@requestedmunicipalityid varchar(64)",
            "@requestedmunicipalityid as varchar(64)) as requestedmunicipalityid",
            "'exact-id lookup' as varchar(32)) as retrievalmode",
            "datalength(@requestedmunicipalityid) = 6",
            "@requestedmunicipalityid collate latin1_general_100_bin2_utf8 not like '%[^0-9]%'",
            "from agent_ref.municipalitystatic",
            "municipalityid = @requestedmunicipalityid",
        )
    elif name == "050_donation_by_id.sql":
        required = (
            "@requesteddonationid bigint",
            "@requesteddonationid as bigint) as requesteddonationid",
            "'exact-id lookup' as varchar(32)) as retrievalmode",
            "from agent_ref.donationattributes",
            "@requesteddonationid is not null",
            "donationid = @requesteddonationid",
        )
    elif name == "060_donation_trace_by_id.sql":
        required = (
            "@requesteddonationid bigint",
            "@requesteddonationid as bigint) as requesteddonationid",
            "'exact-id lookup' as varchar(32)) as retrievalmode",
            "from agent_ref.donationattributes as donation",
            "left join agent_ref.giftcatalogsuppliers as supplier",
            "on supplier.giftcataloggiftid = donation.donationselectedgiftid",
            "where @requesteddonationid is not null and donation.donationid = @requesteddonationid );",
            "'donationid x supplierid registration; donationamountyen is non-additive'",
            "as varchar(96) ) as rowgrain",
        )
        if re.search(r"\b(?:DISTINCT|TOP|GROUP\s+BY|STRING_AGG|SUM|COUNT)\b", sql, re.I):
            raise ValueError("DonationTraceById must preserve every registration and its non-additive amount.")
        if len(re.findall(r"\bJOIN\b", sql, re.I)) != 1:
            raise ValueError("DonationTraceById must retain exactly one LEFT registration JOIN.")
    else:
        return
    missing = [term for term in required if term not in lowered]
    if missing:
        raise ValueError(f"{name} is missing contract terms: {missing}")


def validate_plan(ddl: tuple[tuple[str, str], ...] | None = None) -> None:
    ddl = load_ddl() if ddl is None else ddl
    if tuple(name for name, _ in ddl) != DDL_ORDER:
        raise ValueError("DDL files or deployment order differ from the frozen contract.")
    combined = "\n".join(sql for _, sql in ddl)
    if FORBIDDEN_SQL.search(combined):
        raise ValueError("Destructive, security, DML, or transaction SQL is forbidden.")
    if re.search(r"\bCREATE\s+(?:VIEW|FUNCTION)\s+(?!agent_ref\.)", combined, re.I):
        raise ValueError("Every programmable object must be created under agent_ref.")
    for name, sql in ddl:
        batches = split_batches(sql)
        if len(batches) != 1:
            raise ValueError(f"{name} must contain exactly one executable batch.")
        code = re.sub(r"'(?:''|[^'])*'", "''", batches[0])
        code = re.sub(r"/\*.*?\*/|--[^\r\n]*", "", code, flags=re.DOTALL).strip()
        if len(re.findall(r"\bCREATE\b", code, re.I)) != 1 or code.count(";") != 1 or not code.endswith(";"):
            raise ValueError(f"{name} must contain exactly one CREATE statement.")
        if name == "001_create_schema.sql" and not re.fullmatch(
            r"CREATE\s+SCHEMA\s+agent_ref\s*;", code, re.I
        ):
            raise ValueError("Only the agent_ref schema may be created.")
        _assert_query_contract(name, re.sub(r"\s+", " ", sql))
    found = {
        object_name: kind.upper()
        for kind, object_name in re.findall(
            r"\bCREATE\s+(VIEW|FUNCTION)\s+agent_ref\.([A-Za-z][A-Za-z0-9_]*)",
            combined,
            re.IGNORECASE,
        )
    }
    expected_kinds = {
        name: "FUNCTION" if kind == "SQL_INLINE_TABLE_VALUED_FUNCTION" else kind
        for name, kind in EXPECTED_OBJECTS.items()
    }
    if found != expected_kinds:
        raise ValueError(f"Unexpected programmable object contract: {found}")
    by_file = dict(ddl)
    for name, path in OBJECT_FILES.items():
        if _projection_names(by_file[path]) != tuple(column for column, _ in OUTPUT_COLUMNS[name]):
            raise ValueError(f"{name} output names/order differ from the exact SQL contract.")


def build_plan(root: Path = ROOT) -> dict[str, object]:
    raw_files = {name: (root / name).read_bytes() for name in DDL_ORDER}
    ddl = tuple((name, raw_files[name].decode("utf-8")) for name in DDL_ORDER)
    validate_plan(ddl)
    return {
        "schema": "agent_ref",
        "defaultMode": "plan-only",
        "files": [
            {
                "path": name,
                "sha256": hashlib.sha256(raw_files[name]).hexdigest(),
                "batches": len(split_batches(sql)),
            }
            for name, sql in ddl
        ],
        "objects": dict(EXPECTED_OBJECTS),
        "outputColumnCounts": {name: len(columns) for name, columns in OUTPUT_COLUMNS.items()},
        "nativeCatalogQueries": dict(CATALOG_QUERIES),
    }


def prepare_evidence_directory(path: Path) -> Path:
    # Legacy explicit CLI-only evidence operation. Notebook packaging must not
    # import repository docs or modify sys.path just to load these pure helpers.
    repository = ROOT.parents[2]
    old_path = sys.path[:]
    try:
        sys.path.insert(0, str(repository / "tools" / "docs"))
        from furusato_docs.publication import outside_repo, safe_path
    finally:
        sys.path[:] = old_path
    destination = outside_repo(path, repository)
    if destination.exists():
        raise FileExistsError("Use a fresh private evidence directory; never overwrite a prior run.")
    destination.mkdir(parents=True, exist_ok=False)
    return safe_path(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare-evidence", type=Path)
    modes.add_argument("--catalog-decision", action="store_true",
                       help="Validate only the supplied DDL/native catalog JSON on stdin.")
    arguments = parser.parse_args()
    if arguments.catalog_decision:
        request = json.load(sys.stdin)
        decision = catalog_decision(
            request["catalog"], tuple(tuple(entry) for entry in request["ddl"]),
            database=request["database"],
        )
        print(json.dumps({"decision": decision}, sort_keys=True))
    else:
        plan = build_plan()
        if arguments.prepare_evidence is not None:
            plan["evidenceDirectory"] = str(prepare_evidence_directory(arguments.prepare_evidence))
        print(json.dumps(plan, indent=2, sort_keys=True))
