"""Offline KQL parser/contract tests; every runtime response is synthetic."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "provisioning"))
sys.path.insert(0, str(ROOT / "tools" / "docs"))

import reference_kql as kql
from furusato_docs.context import parse_kql_objects


BASE = ROOT / "workshop/v2.7.0/kql/Furusato_Eventhouse_Setup_v2.7.0.kql"
FUNCTIONS = ROOT / "tools/data-agent/operational-functions"
LEGACY = "AgentObservationLeaders"
META = (
    ("Scope", "string"), ("SourceSystem", "string"), ("SourceObject", "string"),
    ("CountUnit", "string"), ("AmountUnit", "string"),
    ("RawDuplicateCaveat", "string"), ("TimeZoneNotice", "string"),
)
WINDOW = (
    ("RequestedStartUtc", "datetime"), ("RequestedEndUtc", "datetime"),
    ("WindowIsValid", "bool"),
)
METRICS = (("RawObservationCount", "long"), ("RawObservedAmountYen", "long"))
# Independent synthetic getschema fixtures, matching the source/tests' contracts.
EXPECTED_SCHEMAS = {
    "AgentRawObservationTotals": WINDOW + (
        ("TrueFirstObservedAt", "datetime"), ("TrueLastObservedAt", "datetime"),
    ) + METRICS + META,
    "AgentFileRunSummary": (
        ("SourceFile", "string"), ("WorkshopRunId", "string"), ("ParticipantAlias", "string"),
    ) + METRICS + (
        ("FirstObservedAtUtc", "datetime"), ("LastObservedAtUtc", "datetime"),
    ) + WINDOW + META,
    "AgentMunicipalityLeaders": (
        ("MunicipalityID", "string"), ("IsCountLeader", "bool"), ("IsAmountLeader", "bool"),
    ) + METRICS + WINDOW + META,
}
CLR_TYPES = {
    "bool": "System.Boolean", "datetime": "System.DateTime",
    "long": "System.Int64", "string": "System.String",
}


def table(columns, rows):
    return {"Tables": [{
        "TableName": "PrimaryResult",
        "Columns": [{"ColumnName": name, "DataType": "String"} for name in columns],
        "Rows": rows,
    }]}


def definition_response(script):
    definition = kql.parse_function_command(script)
    properties = dict(definition.properties)
    # The fixture sources have JSON-compatible, ordinary quoted metadata.
    import json
    return table(
        ["Name", "Parameters", "Body", "Folder", "DocString"],
        [[
            definition.name, definition.parameters, definition.body,
            json.loads(properties["folder"]), json.loads(properties["docstring"]),
        ]],
    )


def schema_response(name):
    return table(
        ["ColumnName", "ColumnOrdinal", "DataType", "ColumnType"],
        [[field, index, CLR_TYPES[kind], kind] for index, (field, kind) in enumerate(EXPECTED_SCHEMAS[name])],
    )


class KustoEnvelopeTests(unittest.TestCase):
    def envelope(self, rows):
        result = table(["Name"], rows)
        result["Tables"][0]["TableName"] = "Table_0"
        status = table(["Severity", "StatusCode"], [[4, 0], [6, 0]])["Tables"][0]
        status["TableName"] = "Table_1"
        contents = table(
            ["Ordinal", "Kind", "Name", "Id", "PrettyName"],
            [[0, "QueryResult", "PrimaryResult", "result-id", ""],
             [1, "QueryStatus", "QueryStatus", "status-id", ""]],
        )["Tables"][0]
        contents["TableName"] = "Table_2"
        result["Tables"].extend([status, contents])
        return result

    def test_contents_name_is_not_a_second_function_inventory(self):
        for rows in ([], [["AgentRawObservationTotals"]]):
            with self.subTest(rows=rows):
                self.assertEqual(
                    kql.kusto_result_rows(self.envelope(rows), required_columns=("Name",)),
                    [{"Name": row[0]} for row in rows],
                )

    def test_numbered_status_table_cannot_hide_a_partial_failure(self):
        for severity, code in ((2, 0), (4, 500), ("4", 0), (4, "0")):
            payload = self.envelope([["AgentRawObservationTotals"]])
            payload["Tables"][1]["Rows"] = [[severity, code]]
            with self.subTest(severity=severity, code=code), self.assertRaises(kql.KqlContractError):
                kql.kusto_result_rows(payload, required_columns=("Name",))

    def test_contents_requires_complete_unambiguous_references(self):
        for ordinal in (0, 2, -1, "1", True):
            payload = self.envelope([])
            payload["Tables"][2]["Rows"][1][0] = ordinal
            with self.subTest(ordinal=ordinal), self.assertRaises(kql.KqlContractError):
                kql.kusto_result_rows(payload, required_columns=("Name",))
        payload = self.envelope([])
        payload["Tables"][2]["Rows"].pop()
        with self.assertRaises(kql.KqlContractError):
            kql.kusto_result_rows(payload, required_columns=("Name",))

    def test_multiple_actual_results_remain_ambiguous(self):
        payload = self.envelope([["one"]])
        payload["Tables"][1] = table(["Name"], [["two"]])["Tables"][0]
        payload["Tables"][2]["Rows"][1][1] = "QueryResult"
        with self.assertRaises(kql.KqlContractError):
            kql.kusto_result_rows(payload, required_columns=("Name",))


class SyntheticKusto:
    """No network stack; unrecognized commands/queries fail the test."""

    def __init__(self, scripts, existing=()):
        self.scripts = scripts
        self.functions = {
            name: definition_response(scripts[name]) for name in existing
        }
        self.tables = {"DonationEvents"}
        self.views = {kql.APPROVED_SOURCE}
        self.schemas = {name: schema_response(name) for name in scripts}
        self.calls = []
        self.writes = []
        self.overrides = {}
        self.on_create = None

    def management(self, command):
        self.calls.append(("management", command))
        if command in self.overrides:
            value = self.overrides[command]
            if isinstance(value, Exception):
                raise value
            return copy.deepcopy(value)
        if command == ".show functions | project Name":
            return table(["Name"], [[name] for name in sorted(self.functions)])
        if command == ".show tables | project TableName":
            return table(["TableName"], [[name] for name in sorted(self.tables)])
        if command == ".show materialized-views | project Name":
            return table(["Name"], [[name] for name in sorted(self.views)])
        if command.startswith(".show function "):
            name = command.removeprefix(".show function ")
            return copy.deepcopy(self.functions[name])
        if command.startswith(".create function "):
            definition = kql.parse_function_command(command)
            assert definition.name not in self.functions, "A create-only conflict must not be retried"
            assert command == self.scripts[definition.name].strip()
            self.writes.append(command)
            self.functions[definition.name] = definition_response(self.scripts[definition.name])
            if self.on_create:
                self.on_create(self, definition.name)
            return copy.deepcopy(self.functions[definition.name])
        raise AssertionError(f"Unexpected management command: {command}")

    def query(self, query):
        self.calls.append(("query", query))
        name = query.removesuffix("() | getschema")
        if query != f"{name}() | getschema" or name not in self.schemas:
            raise AssertionError("Only the three metadata-only getschema queries are permitted")
        assert name in self.functions
        return copy.deepcopy(self.schemas[name])

    def provision(self, **kwargs):
        return kql.provision_reference_functions(
            self.scripts, execute_management=self.management,
            execute_query=self.query, enabled=True, **kwargs,
        )


class KqlSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = BASE.read_bytes().decode("utf-8")
        cls.scripts = kql.load_function_scripts(FUNCTIONS)
        cls.contracts = kql.validate_function_contracts(cls.scripts)

    def test_authoritative_sources_only_and_no_legacy_fresh_requirement(self):
        self.assertTrue((FUNCTIONS / f"{LEGACY}.kql").is_file())
        self.assertEqual(tuple(self.scripts), kql.FUNCTION_NAMES)
        for name, source in self.scripts.items():
            self.assertEqual(source, (FUNCTIONS / f"{name}.kql").read_bytes().decode("utf-8"))
            contract = self.contracts[name]
            self.assertEqual(contract.definition.command, source.strip())
            self.assertEqual(
                contract.definition.source_sha256,
                hashlib.sha256(source.encode("utf-8")).hexdigest(),
            )
            self.assertEqual(contract.return_schema, EXPECTED_SCHEMAS[name])
            self.assertEqual(contract.folder, "Agent")
        self.assertEqual([len(c.return_schema) for c in self.contracts.values()], [14, 17, 15])

    def test_default_composition_is_released_five_even_without_reference_sources(self):
        commands = kql.compose_kql_management_commands(self.base)
        self.assertEqual(len(commands), 5)
        self.assertEqual(commands, kql.extract_kql_management_commands(self.base))
        self.assertEqual(commands, kql.compose_kql_management_commands(self.base, {"invalid": None}))
        self.assertFalse(any("function" in command.split("\n", 1)[0] for command in commands))
        for command in commands:
            for forbidden in ("<SourceFile>", "let targetSourceFile", "DistinctEventIDs", "RawRows="):
                self.assertNotIn(forbidden, command)

    def test_enabled_composition_is_unchanged_five_plus_exact_three(self):
        expected = kql.compose_kql_management_commands(self.base)
        commands = kql.compose_kql_management_commands(self.base, self.scripts, enabled=True)
        self.assertEqual(len(commands), 8)
        self.assertEqual(commands[:5], expected)
        self.assertEqual(commands[5:], [self.scripts[name].strip() for name in kql.FUNCTION_NAMES])
        self.assertNotIn(LEGACY, "\n".join(commands))

    def test_gate_rejects_truthy_nonbooleans(self):
        for enabled in ("false", "true", None, 0, 1):
            with self.subTest(enabled=enabled), self.assertRaises(kql.KqlContractError):
                kql.compose_kql_management_commands(self.base, self.scripts, enabled=enabled)

    def test_baseline_boundary_count_order_and_query_leaks_fail(self):
        malformed = [
            self.base.replace(kql.VERIFICATION_MARKER, "// different boundary"),
            self.base.replace(".alter table DonationEvents policy caching hot = 7d", ""),
            self.base.replace(".create-merge table DonationEvents", ".create-merge table Foreign"),
            self.base.replace(
                kql.VERIFICATION_MARKER,
                "DonationEvents | count\n\n" + kql.VERIFICATION_MARKER,
            ),
            self.base.replace(
                kql.VERIFICATION_MARKER,
                self.scripts[kql.FUNCTION_NAMES[0]] + "\n" + kql.VERIFICATION_MARKER,
            ),
        ]
        for source in malformed:
            with self.subTest(source=source[-100:]), self.assertRaises(kql.KqlContractError):
                kql.compose_kql_management_commands(source, self.scripts, enabled=True)

    def test_missing_extra_duplicate_and_wrong_source_names_fail(self):
        bad_inputs = [
            None, {}, {**self.scripts, LEGACY: (FUNCTIONS / f"{LEGACY}.kql").read_text("utf-8")},
            {name: source for name, source in self.scripts.items() if name != kql.FUNCTION_NAMES[0]},
            {**self.scripts, kql.FUNCTION_NAMES[0] + ".kql": self.scripts[kql.FUNCTION_NAMES[0]]},
        ]
        for sources in bad_inputs:
            with self.subTest(keys=list(sources or {})), self.assertRaises(kql.KqlContractError):
                kql.validate_function_contracts(sources)
        sources = dict(self.scripts)
        sources[kql.FUNCTION_NAMES[0]] = self.scripts[kql.FUNCTION_NAMES[1]]
        with self.assertRaisesRegex(kql.KqlContractError, "different function"):
            kql.validate_function_contracts(sources)
        file_keys = {name + ".kql": text for name, text in self.scripts.items()}
        self.assertEqual(kql.validate_function_contracts(file_keys), self.contracts)

    def test_fresh_only_create_is_not_rewritten_into_alter_or_ifnotexists(self):
        for replacement in (".create-or-alter function", ".alter function", ".create function ifnotexists"):
            sources = dict(self.scripts)
            name = kql.FUNCTION_NAMES[0]
            sources[name] = sources[name].replace(".create function", replacement)
            with self.subTest(replacement=replacement), self.assertRaisesRegex(kql.KqlContractError, "fresh-only"):
                kql.validate_function_contracts(sources)

    def test_required_optional_parameters_and_return_shape_are_exact(self):
        name = kql.FUNCTION_NAMES[0]
        changes = [
            ("StartUtc:datetime", "StartUtc:string"),
            ("StartUtc:datetime = datetime(null)", "StartUtc:datetime"),
            ("EndUtc:datetime = datetime(null)", "ExtraUtc:datetime = datetime(null)"),
            ("        TimeZoneNotice\n}", "        TimeZoneNotice,\n        SourceFile\n}"),
            ("RequestedStartUtc = StartUtc", 'RequestedStartUtc = "2026-01-01"'),
            ('folder = "Agent"', 'folder = "Other"'),
        ]
        for before, after in changes:
            sources = dict(self.scripts)
            self.assertIn(before, sources[name])
            sources[name] = sources[name].replace(before, after)
            with self.subTest(after=after), self.assertRaises(kql.KqlContractError):
                kql.validate_function_contracts(sources)

    def test_raw_grain_approved_source_windows_and_leader_contracts_are_guarded(self):
        changes = [
            ("DonationObservationSummaryForAgent", "DonationEvents"),
            ("DonationObservationSummaryForAgent", 'database("foreign").DonationObservationSummaryForAgent'),
            ("sum(ObservationCount)", "count()"),
            ("sum(ObservationCount)", "max(ObservationCount)"),
            ("EventMinute < EndUtc", "EventMinute <= EndUtc"),
            ("EventMinute >= StartUtc", "EventMinute > StartUtc"),
            ("or StartUtc < EndUtc", "or StartUtc <= EndUtc"),
            ("| where WindowIsValid", "| where WindowIsValid\n    | where EventMinute < StartUtc"),
            ('CountUnit = "raw observations"', 'CountUnit = "unique observations"'),
        ]
        for name in kql.FUNCTION_NAMES:
            for before, after in changes:
                with self.subTest(name=name, after=after):
                    sources = dict(self.scripts)
                    sources[name] = sources[name].replace(before, after)
                    with self.assertRaises(kql.KqlContractError):
                        kql.validate_function_contracts(sources)
        sources = dict(self.scripts)
        name = "AgentMunicipalityLeaders"
        sources[name] = sources[name].replace("MunicipalityID asc", "MunicipalityID desc")
        with self.assertRaises(kql.KqlContractError):
            kql.validate_function_contracts(sources)
        name = "AgentFileRunSummary"
        sources = dict(self.scripts)
        sources[name] = sources[name].replace(
            "by SourceFile, WorkshopRunId, ParticipantAlias",
            "by SourceFile, WorkshopRunId, ParticipantAlias, MunicipalityID",
        )
        with self.assertRaises(kql.KqlContractError):
            kql.validate_function_contracts(sources)


class KqlParsingTests(unittest.TestCase):
    def test_nested_function_bodies_and_internal_blank_lines_stay_intact(self):
        function = '''.create function with (
    folder = "Agent",

    docstring = "literal ) } .drop table not_a_command"
) Nested(
    StartUtc:datetime=datetime(null),
    Payload:dynamic=dynamic({"items":[{"x":"}"}]})
)
{
    let NestedLambda = (value:dynamic) {
        value
    };

    let Message = @".create function ""NotReal""() { }";
    let Multiline = ```
.drop table NotReal
{ unmatched literal braces
```;
    // .alter table NotReal policy caching hot = 1d
    /* }
.create function NotReal() { }
    */
    print Value=NestedLambda(Payload)
}'''
        script = function + "\n\n.create function Next() { print n=1 }\n\nprint check=1\n"
        commands = kql.extract_kql_management_commands(script)
        self.assertEqual(commands, [function, ".create function Next() { print n=1 }"])
        definition = kql.parse_function_command(commands[0])
        self.assertEqual(definition.name, "Nested")
        self.assertIn('\n\n    let Message', definition.body)
        self.assertIn('Payload:dynamic=dynamic({"items":[{"x":"}"}]})', definition.parameters)
        self.assertEqual(len(parse_kql_objects(script)), 2)

    def test_function_forms_with_and_without_properties_or_parameters(self):
        for verb in ("create", "create-or-alter", "alter"):
            for properties in ("", "with (folder='Agent', docstring='A ) { text') "):
                for parameters in ("", "StartUtc:datetime=datetime(null), EndUtc:datetime=datetime(null)"):
                    script = f".{verb} function {properties}Example({parameters}) {{ print n=1 }}"
                    with self.subTest(script=script):
                        definition = kql.parse_function_command(script)
                        self.assertEqual(definition.name, "Example")
                        self.assertEqual(definition.parameters, f"({parameters})")
                        objects = parse_kql_objects(script)
                        self.assertEqual(len(objects), 1)
                        self.assertEqual(objects[0].command, f"{verb} function")
                        self.assertEqual(objects[0].kind, "関数")
                        self.assertEqual(objects[0].name, "Example()")
        parsed = kql.parse_function_command(".create function ifnotexists F() { print n=1 }")
        self.assertTrue(parsed.if_not_exists)
        self.assertEqual(parse_kql_objects(parsed.command)[0].name, "F()")

    def test_multiline_headers_and_quoted_name_do_not_have_eight_line_limit(self):
        script = (
            "  .create\nfunction\nwith (\n"
            + "\n".join(f"// metadata line {i}" for i in range(15))
            + '\nfolder="Agent", docstring="test"\n)\n'
            "['Function with spaces'](\nStartUtc:datetime = datetime(null)\n)\n"
            "{\n\nprint result=1\n}\n"
        )
        self.assertEqual(parse_kql_objects(script)[0].name, "Function with spaces()")

    def test_literal_and_comment_management_text_is_not_a_command(self):
        script = '''// .create function Comment() { }
/*
.create function CommentBlock() { }
*/
let text = ".create function Literal() { }";
print Value=text
.create function Actual() { print Value=h@"not a command }" }
print Value=@'
.create function NotActual() { }
'
'''
        self.assertEqual(len(kql.extract_kql_management_commands(script)), 1)
        self.assertEqual(parse_kql_objects(script)[0].name, "Actual()")

    def test_adjacent_commands_and_verification_query_do_not_merge(self):
        script = (
            ".create function First()\n{\nprint n=1\n}\n"
            ".create function Second()\n{\nprint n=2\n}\n"
            "Second() | getschema\n"
        )
        self.assertEqual(len(kql.extract_kql_management_commands(script)), 2)
        for command in kql.extract_kql_management_commands(script):
            self.assertNotIn("getschema", command)

    def test_leading_block_comments_do_not_hide_real_commands(self):
        script = (
            "/* header */ .create function First() { print n=1 }\n"
            "/* multiline\nheader */ .create function Second() { print n=2 }\n"
        )
        self.assertEqual(
            [obj.name for obj in parse_kql_objects(script)],
            ["First()", "Second()"],
        )

    def test_multiline_nonfunction_commands_preserve_internal_blank_lines(self):
        script = '''.create-merge table Small (
    Name:string,

    Number:long
)
.create-or-alter table Small ingestion csv mapping 'Map'

'[{"column":"Name","Properties":{"Ordinal":"0"}},'

'{"column":"Number","Properties":{"Ordinal":"1"}}]'
.create-or-alter materialized-view Summary
on table Small {
    Small

    | summarize Count=count() by Name
}
.alter table Small policy retention

@'{"SoftDeletePeriod":"90.00:00:00","Recoverability":"Enabled"}'
.alter table Small policy caching hot = 7d
Small | count
'''
        commands = kql.extract_kql_management_commands(script)
        self.assertEqual(len(commands), 5)
        self.assertIn("\n\n", commands[0])
        self.assertIn("\n\n", commands[1])
        self.assertIn("\n\n", commands[2])
        self.assertNotIn("Small | count", commands[-1])

    def test_lf_crlf_and_bom_preserve_baseline_and_source_functions(self):
        source = BASE.read_bytes().decode("utf-8")
        windows = "\ufeff" + source.replace("\n", "\r\n")
        self.assertEqual(
            [(obj.command, obj.name, obj.detail) for obj in parse_kql_objects(windows)],
            [(obj.command, obj.name, obj.detail) for obj in parse_kql_objects(source)],
        )
        scripts = kql.load_function_scripts(FUNCTIONS)
        contracts = kql.validate_function_contracts({
            name: text.replace("\n", "\r\n") for name, text in scripts.items()
        })
        self.assertEqual(contracts[kql.FUNCTION_NAMES[0]].return_schema, EXPECTED_SCHEMAS[kql.FUNCTION_NAMES[0]])

    def test_malformed_or_multiple_command_source_fails_closed(self):
        bad_sources = (
            ".create function F() { print x=1",
            '.create function F() { print x="unterminated }',
            ".create function F() { print x=dynamic([}) }",
            ".create function F() { print x=1 } /* unclosed",
            ".create function F() { print x=```unclosed }",
            ".create function F()",
            ".create function F { print x=1 }",
            ".create function F() { print x=1 }\n.create function G() { print y=2 }",
            ".create function F() { print x=1 }\nF() | getschema",
            ".create function with (folder='A', folder='B') F() { print x=1 }",
        )
        for source in bad_sources:
            with self.subTest(source=source), self.assertRaises(kql.KqlContractError):
                kql.parse_function_command(source)
        with self.assertRaisesRegex(ValueError, "Unrecognised KQL"):
            parse_kql_objects(".drop table Foreign")

    def test_original_doc_inventory_details_and_enabled_function_labels(self):
        base = BASE.read_bytes().decode("utf-8")
        self.assertEqual(
            [(obj.command, obj.kind, obj.name, obj.detail) for obj in parse_kql_objects(base)],
            [
                ("create-merge table", "テーブル", "DonationEvents", "12 列"),
                ("create-or-alter ingestion mapping", "ingestion csv mapping",
                 "DonationEvents_IncrementCsvMap", "12 序数"),
                ("create-or-alter materialized-view", "マテリアライズドビュー",
                 kql.APPROVED_SOURCE, "on table DonationEvents"),
                ("alter table policy retention", "ポリシー（retention）", "DonationEvents",
                 "SoftDeletePeriod 90 日 / Recoverability Enabled"),
                ("alter table policy caching", "ポリシー（caching）", "DonationEvents", "hot cache 7 日"),
            ],
        )
        sources = kql.load_function_scripts(FUNCTIONS)
        composed = "\n\n".join(kql.compose_kql_management_commands(base, sources, enabled=True))
        objects = parse_kql_objects(composed)
        self.assertEqual(len(objects), 8)
        self.assertEqual([obj.name for obj in objects[-3:]], [f"{name}()" for name in kql.FUNCTION_NAMES])


class KqlComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scripts = kql.load_function_scripts(FUNCTIONS)
        cls.contract = kql.validate_function_contracts(cls.scripts)[kql.FUNCTION_NAMES[0]]

    def test_show_definition_uses_column_names_not_positional_order(self):
        result = definition_response(self.scripts[self.contract.name])
        result["Tables"][0]["Columns"].reverse()
        result["Tables"][0]["Rows"][0].reverse()
        proof = kql.compare_function_definition(self.contract, result)
        self.assertEqual(proof["command"], f".show function {self.contract.name}")
        self.assertTrue(proof["bodyMatch"])
        self.assertTrue(proof["parametersMatch"])
        self.assertEqual(len(proof["definitionSha256"]), 64)

    def test_layout_only_normalization_preserves_literals_and_token_boundaries(self):
        result = definition_response(self.scripts[self.contract.name])
        row = result["Tables"][0]["Rows"][0]
        row[1] = "( StartUtc : datetime=datetime(null),EndUtc:datetime = datetime(null) )"
        row[2] = row[2].replace("\n", "\r\n").replace("    ", "\t")
        self.assertTrue(kql.compare_function_definition(self.contract, result)["bodyMatch"])
        for changed in (
            row[2].replace("raw observations", "raw  observations"),
            row[2].replace("sum(ObservationCount)", "max(ObservationCount)"),
            row[2] + "// extra comment is not the exact stored body",
            row[2].replace("EventMinute >= StartUtc", "EventMinute > = StartUtc"),
        ):
            value = copy.deepcopy(result)
            value["Tables"][0]["Rows"][0][2] = changed
            with self.subTest(changed=changed[:70]), self.assertRaises(kql.KqlConflictError):
                kql.compare_function_definition(self.contract, value)

    def test_each_definition_field_is_checked_and_substrings_are_not_proof(self):
        replacements = (
            (0, "Foreign"), (1, "()"), (1, None),
            (2, '{ print fake="DonationObservationSummaryForAgent sum(ObservationCount)" }'),
            (3, "Foreign"), (4, "Not the authoritative metadata"),
        )
        for index, value in replacements:
            result = definition_response(self.scripts[self.contract.name])
            result["Tables"][0]["Rows"][0][index] = value
            with self.subTest(index=index), self.assertRaises(kql.KqlConflictError):
                kql.compare_function_definition(self.contract, result)

    def test_incomplete_ambiguous_or_error_tables_do_not_prove_absence(self):
        good = definition_response(self.scripts[self.contract.name])
        malformed = [
            None, {}, {"Tables": []}, {"Tables": {}},
            {"error": {"code": "Forbidden"}, **good},
            {"OneApiErrors": ["failure"], **good},
            {"Tables": good["Tables"] + copy.deepcopy(good["Tables"])},
            table(["Name", "Parameters", "Body"], [["x", "()", "{}"]]),
            table(["Name", "Name"], [["x", "y"]]),
            table(["Name", "Parameters", "Body", "Folder", "DocString"], []),
        ]
        duplicate = copy.deepcopy(good)
        duplicate["Tables"][0]["Rows"] *= 2
        malformed.append(duplicate)
        short_row = copy.deepcopy(good)
        short_row["Tables"][0]["Rows"][0].pop()
        malformed.append(short_row)
        failed = copy.deepcopy(good)
        error_table = table(["Severity", "StatusDescription"], [[2, "partial query failure"]])["Tables"][0]
        error_table["TableName"] = "QueryStatus"
        failed["Tables"].append(error_table)
        malformed.append(failed)
        for value in malformed:
            with self.subTest(value=str(value)[:80]), self.assertRaises(kql.KqlContractError):
                kql.compare_function_definition(self.contract, value)

    def test_getschema_records_actual_order_names_and_both_type_systems(self):
        for name, schema in EXPECTED_SCHEMAS.items():
            result = schema_response(name)
            result["Tables"][0]["Rows"].reverse()
            self.assertEqual(kql.parse_query_schema(result), schema)
        proof = kql.compare_function_schema(self.contract, schema_response(self.contract.name))
        self.assertEqual(proof["provenance"], "query-getschema")
        self.assertEqual(proof["query"], f"{self.contract.name}() | getschema")
        self.assertEqual([column["ordinal"] for column in proof["columns"]], list(range(14)))

    def test_getschema_missing_extra_reordered_and_wrong_type_fields_fail(self):
        name = self.contract.name
        changed_results = []
        changed = schema_response(name)
        changed["Tables"][0]["Rows"].pop()
        changed_results.append(changed)
        changed = schema_response(name)
        changed["Tables"][0]["Rows"].append(["Unexpected", 14, "System.String", "string"])
        changed_results.append(changed)
        changed = schema_response(name)
        rows = changed["Tables"][0]["Rows"]
        rows[0][1], rows[1][1] = rows[1][1], rows[0][1]
        changed_results.append(changed)
        changed = schema_response(name)
        changed["Tables"][0]["Rows"][0][0] = "DifferentName"
        changed_results.append(changed)
        changed = schema_response(name)
        changed["Tables"][0]["Rows"][5][2:] = ["System.String", "string"]
        changed_results.append(changed)
        for value in changed_results:
            with self.subTest(value=value["Tables"][0]["Rows"][:1]), self.assertRaises(kql.KqlConflictError):
                kql.compare_function_schema(self.contract, value)

    def test_native_boolean_storage_type_is_not_a_numeric_schema_change(self):
        for native in ("System.Boolean", "System.SByte"):
            result = schema_response(self.contract.name)
            result["Tables"][0]["Rows"][2][2] = native
            with self.subTest(native=native):
                self.assertEqual(
                    kql.parse_query_schema(result), EXPECTED_SCHEMAS[self.contract.name],
                )
        for index, native in ((2, "System.Int64"), (5, "System.SByte"), (7, "System.SByte")):
            result = schema_response(self.contract.name)
            result["Tables"][0]["Rows"][index][2] = native
            with self.subTest(index=index, native=native), self.assertRaises(kql.KqlContractError):
                kql.parse_query_schema(result)

    def test_malformed_getschema_is_never_substituted_with_source_contracts(self):
        name = self.contract.name
        bad_results = []
        for column, value in ((0, None), (1, True), (1, -1), (1, "0"), (2, "System.Int64"), (3, "real")):
            result = schema_response(name)
            result["Tables"][0]["Rows"][0][column] = value
            bad_results.append(result)
        result = schema_response(name)
        result["Tables"][0]["Rows"][1][1] = 0
        bad_results.append(result)
        result = schema_response(name)
        result["Tables"][0]["Rows"][1][0] = result["Tables"][0]["Rows"][0][0]
        bad_results.append(result)
        bad_results += [{"Tables": []}, table(["ColumnName", "ColumnType"], [["SomeChild", "string"]])]
        for result in bad_results:
            with self.subTest(result=str(result)[:100]), self.assertRaises(kql.KqlContractError):
                kql.parse_query_schema(result)


class KqlRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.scripts = kql.load_function_scripts(FUNCTIONS)
        self.synthetic = SyntheticKusto(self.scripts)

    def test_disabled_runtime_neither_validates_sources_nor_calls_client(self):
        result = kql.provision_kql(object(), "", "", None)
        self.assertEqual(result, {"enabled": False, "functions": {}, "acceptanceClaimed": False})

    def test_fresh_provision_creates_exact_three_then_observes_definitions_and_schemas(self):
        report = self.synthetic.provision()
        self.assertEqual(tuple(report["functions"]), kql.FUNCTION_NAMES)
        self.assertEqual(self.synthetic.writes, [self.scripts[name].strip() for name in kql.FUNCTION_NAMES])
        self.assertTrue(report["enabled"])
        self.assertFalse(report["acceptanceClaimed"])
        for name, proof in report["functions"].items():
            self.assertEqual(proof["state"], "CREATED")
            self.assertEqual(proof["sourceSha256"], hashlib.sha256(self.scripts[name].encode("utf-8")).hexdigest())
            self.assertEqual(proof["definition"]["command"], f".show function {name}")
            self.assertEqual(proof["returnSchema"]["query"], f"{name}() | getschema")
            self.assertEqual(
                [(column["name"], column["type"]) for column in proof["returnSchema"]["columns"]],
                list(EXPECTED_SCHEMAS[name]),
            )
            self.assertNotIn("children", proof)
            create_index = self.synthetic.calls.index(("management", self.scripts[name].strip()))
            show_index = self.synthetic.calls.index(("management", f".show function {name}"))
            self.assertLess(create_index, show_index)

    def test_rerun_reuses_all_without_any_create_alter_or_delete(self):
        first = self.synthetic.provision()
        self.synthetic.writes.clear()
        self.synthetic.calls.clear()
        second = self.synthetic.provision()
        self.assertEqual(self.synthetic.writes, [])
        self.assertEqual({item["state"] for item in second["functions"].values()}, {"REUSED"})
        for name in kql.FUNCTION_NAMES:
            self.assertEqual(
                first["functions"][name]["definition"], second["functions"][name]["definition"],
            )
        self.assertTrue(all(
            command.startswith(".show ") if kind == "management" else command.endswith("() | getschema")
            for kind, command in self.synthetic.calls
        ))

    def test_installed_legacy_is_optional_ignored_and_never_direct_selected(self):
        self.synthetic.functions[LEGACY] = {"not": "inspected or overwritten"}
        report = self.synthetic.provision()
        self.assertNotIn(LEGACY, report["functions"])
        self.assertEqual(len(self.synthetic.writes), 3)
        self.assertFalse(any(LEGACY in command for _, command in self.synthetic.calls))
        self.assertEqual(self.synthetic.functions[LEGACY], {"not": "inspected or overwritten"})

    def test_mismatch_in_existing_last_function_precedes_any_missing_create(self):
        name = kql.FUNCTION_NAMES[-1]
        synthetic = SyntheticKusto(self.scripts, existing=(name,))
        synthetic.functions[name]["Tables"][0]["Rows"][0][2] = "{ print not_the_owned_function=1 }"
        with self.assertRaisesRegex(kql.KqlConflictError, "Body mismatch"):
            synthetic.provision()
        self.assertEqual(synthetic.writes, [])

    def test_schema_mismatch_in_existing_function_precedes_any_missing_create(self):
        name = kql.FUNCTION_NAMES[-1]
        synthetic = SyntheticKusto(self.scripts, existing=(name,))
        synthetic.schemas[name]["Tables"][0]["Rows"].pop()
        with self.assertRaisesRegex(kql.KqlConflictError, "schema mismatch"):
            synthetic.provision()
        self.assertEqual(synthetic.writes, [])

    def test_mixed_existing_missing_preflights_reused_functions_first(self):
        name = kql.FUNCTION_NAMES[-1]
        synthetic = SyntheticKusto(self.scripts, existing=(name,))
        report = synthetic.provision()
        first_create = next(i for i, (_, command) in enumerate(synthetic.calls) if command.startswith(".create "))
        schema_index = synthetic.calls.index(("query", f"{name}() | getschema"))
        self.assertLess(schema_index, first_create)
        self.assertEqual(report["functions"][name]["state"], "REUSED")
        self.assertEqual(len(synthetic.writes), 2)

    def test_foreign_types_and_case_variants_block_before_writes(self):
        name = kql.FUNCTION_NAMES[0]
        for kind, collision in (
            ("tables", name), ("views", name), ("tables", name.lower()),
            ("functions", name.lower()),
        ):
            synthetic = SyntheticKusto(self.scripts)
            inventory = getattr(synthetic, kind)
            if kind == "functions":
                inventory[collision] = {}
            else:
                inventory.add(collision)
            with self.subTest(kind=kind, collision=collision), self.assertRaises(kql.KqlConflictError):
                synthetic.provision()
            self.assertEqual(synthetic.writes, [])

    def test_missing_or_ambiguous_approved_materialized_source_blocks_before_writes(self):
        for kind in ("missing", "table", "function", "variant"):
            synthetic = SyntheticKusto(self.scripts)
            if kind == "missing":
                synthetic.views.clear()
            elif kind == "table":
                synthetic.tables.add(kql.APPROVED_SOURCE)
            elif kind == "function":
                synthetic.functions[kql.APPROVED_SOURCE] = {}
            else:
                synthetic.views.add(kql.APPROVED_SOURCE.lower())
            with self.subTest(kind=kind), self.assertRaises(kql.KqlConflictError):
                synthetic.provision()
            self.assertEqual(synthetic.writes, [])

    def test_malformed_inventory_is_not_treated_as_empty(self):
        command = ".show functions | project Name"
        for response in (
            {"Tables": []}, {}, table(["SomethingElse"], []), table(["Name"], [[None]]),
            table(["Name"], [["same"], ["same"]]), {"error": "denied"},
        ):
            synthetic = SyntheticKusto(self.scripts)
            synthetic.overrides[command] = response
            with self.subTest(response=response), self.assertRaises(kql.KqlContractError):
                synthetic.provision()
            self.assertEqual(synthetic.writes, [])

    def test_transport_failures_propagate_without_creating_or_retrying(self):
        for command in (
            ".show functions | project Name",
            ".show tables | project TableName",
            ".show materialized-views | project Name",
        ):
            synthetic = SyntheticKusto(self.scripts)
            failure = RuntimeError("synthetic access/transport failure")
            synthetic.overrides[command] = failure
            with self.subTest(command=command), self.assertRaises(RuntimeError) as raised:
                synthetic.provision()
            self.assertIs(raised.exception, failure)
            self.assertEqual(synthetic.writes, [])

    def test_invalid_source_fails_before_first_callback(self):
        self.synthetic.scripts = dict(self.scripts)
        name = kql.FUNCTION_NAMES[0]
        self.synthetic.scripts[name] = self.scripts[name].replace(".create function", ".create-or-alter function")
        with self.assertRaises(kql.KqlContractError):
            self.synthetic.provision()
        self.assertEqual(self.synthetic.calls, [])

    def test_create_race_is_not_retried_or_repaired(self):
        command = self.scripts[kql.FUNCTION_NAMES[0]].strip()
        self.synthetic.overrides[command] = RuntimeError("synthetic already-exists race")
        with self.assertRaisesRegex(RuntimeError, "already-exists"):
            self.synthetic.provision()
        self.assertEqual(self.synthetic.writes, [])
        self.assertEqual(self.synthetic.calls.count(("management", command)), 1)
        self.assertFalse(any(
            command.startswith((".alter", ".create-or-alter", ".drop", ".delete"))
            for _, command in self.synthetic.calls
        ))

    def test_post_create_definition_or_schema_conflict_stops_without_cleanup(self):
        for drift in ("definition", "schema"):
            synthetic = SyntheticKusto(self.scripts)

            def change_created(target, name):
                if drift == "definition":
                    target.functions[name]["Tables"][0]["Rows"][0][2] = "{ print foreign=1 }"
                else:
                    target.schemas[name]["Tables"][0]["Rows"].pop()

            synthetic.on_create = change_created
            with self.subTest(drift=drift), self.assertRaises(kql.KqlConflictError):
                synthetic.provision()
            self.assertEqual(len(synthetic.writes), 1)
            self.assertEqual(set(synthetic.functions), {kql.FUNCTION_NAMES[0]})
            self.assertFalse(any(command.startswith((".drop", ".alter")) for _, command in synthetic.calls))

    def test_notebook04_adapter_parameterizes_environment_and_management_flag(self):
        synthetic = self.synthetic
        class Client:
            def __init__(self):
                self.calls = []

            def execute_kusto(self, query_service_uri, database_name, csl, *, management):
                self.calls.append((query_service_uri, database_name, management))
                return synthetic.management(csl) if management else synthetic.query(csl)

        client = Client()
        report = kql.provision_kql(
            client, "https://synthetic.invalid", "offline-test-db", self.scripts, enabled=True,
        )
        self.assertTrue(report["enabled"])
        self.assertTrue(all(uri == "https://synthetic.invalid" and db == "offline-test-db" for uri, db, _ in client.calls))
        self.assertEqual(sum(not management for _, _, management in client.calls), 3)
        for uri, database in (("", "db"), ("uri", ""), ("uri", None)):
            with self.subTest(uri=uri, database=database), self.assertRaises(kql.KqlContractError):
                kql.provision_kql(client, uri, database, self.scripts, enabled=True)


class KqlNamespacePackagingTests(unittest.TestCase):
    def test_public_api_runs_from_python_source_in_named_namespace_package(self):
        package_name = "_furusato_kql_packaging_test"
        module_name = package_name + ".reference_kql"
        previous = {name: sys.modules.get(name) for name in (package_name, module_name)}
        package = types.ModuleType(package_name)
        package.__path__ = []
        package.__package__ = package_name
        module = types.ModuleType(module_name)
        module.__package__ = package_name
        module.__file__ = "<embedded reference_kql.py>"
        package.reference_kql = module
        sys.modules[package_name] = package
        # Dataclasses require registration before exec, just as normal import
        # machinery does; the runtime package must not execute in anonymous globals.
        sys.modules[module_name] = module
        try:
            source = (ROOT / "tools/provisioning/reference_kql.py").read_bytes().decode("utf-8")
            exec(compile(source, module.__file__, "exec"), module.__dict__)
            self.assertTrue({
                "compose_kql_management_commands",
                "provision_reference_functions", "provision_kql",
            }.issubset(module.__all__))
            base = BASE.read_bytes().decode("utf-8")
            scripts = kql.load_function_scripts(FUNCTIONS)
            self.assertEqual(len(module.compose_kql_management_commands(base)), 5)
            combined = module.compose_kql_management_commands(base, scripts, enabled=True)
            self.assertEqual(len(combined), 8)
            self.assertEqual(combined[5:], [scripts[name].strip() for name in kql.FUNCTION_NAMES])
            contracts = module.validate_function_contracts(scripts)
            self.assertEqual(type(contracts[kql.FUNCTION_NAMES[0]]).__module__, module_name)
            synthetic = SyntheticKusto(scripts)
            report = module.provision_reference_functions(
                scripts, execute_management=synthetic.management,
                execute_query=synthetic.query, enabled=True,
            )
            self.assertEqual(len(synthetic.writes), 3)
            self.assertEqual(
                {item["state"] for item in report["functions"].values()}, {"CREATED"},
            )
        finally:
            for name, original in previous.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original


if __name__ == "__main__":
    unittest.main()
