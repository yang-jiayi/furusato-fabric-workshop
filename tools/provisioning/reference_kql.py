"""Portable, opt-in contracts for the three structural Eventhouse functions.

The caller supplies the authoritative operational-functions/*.kql contents,
normally from a verified bundle. No function body, connection, credential,
source selection, or discovery child is manufactured here. The two runtime
callbacks accept a command/query and return Kusto v1 JSON ``Tables``.

This is deliberately a small parser for the workshop's management statements,
not a general KQL compiler. Unsupported or ambiguous input fails closed.
Runtime reuse requires exact definition tokens (including case, comments, and
literals; only inter-token whitespace is immaterial) and an ordered getschema
contract. A mismatch never causes an alter, drop, retry-as-create, or rollback.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


FUNCTION_NAMES = (
    "AgentRawObservationTotals",
    "AgentFileRunSummary",
    "AgentMunicipalityLeaders",
)
APPROVED_SOURCE = "DonationObservationSummaryForAgent"
VERIFICATION_MARKER = "// Pipeline ingestion verification."
BASE_MANAGEMENT_COMMAND_COUNT = 5
REFERENCE_MANAGEMENT_COMMAND_COUNT = 8

KustoCallback = Callable[[str], Mapping[str, Any]]
ReturnSchema = tuple[tuple[str, str], ...]

__all__ = [
    "FUNCTION_NAMES", "APPROVED_SOURCE", "VERIFICATION_MARKER",
    "BASE_MANAGEMENT_COMMAND_COUNT", "REFERENCE_MANAGEMENT_COMMAND_COUNT",
    "KustoCallback", "ReturnSchema", "KqlContractError", "KqlConflictError",
    "FunctionDefinition", "FunctionContract",
    "extract_kql_management_commands", "parse_function_command",
    "load_function_scripts", "validate_function_contracts", "derive_return_schema",
    "compose_kql_management_commands", "kusto_result_rows",
    "compare_function_definition", "parse_query_schema", "compare_function_schema",
    "provision_reference_functions", "provision_kql",
]


class KqlContractError(ValueError):
    """Malformed input or insufficient structural proof; no repair is implied."""


class KqlConflictError(KqlContractError):
    """A same-name object or its observed definition/schema is not reusable."""


@dataclass(frozen=True)
class _Token:
    text: str
    start: int
    end: int
    kind: str = "symbol"


@dataclass(frozen=True)
class FunctionDefinition:
    """Source slices, not rewritten definitions; parameters/body include braces."""

    name: str
    verb: str
    if_not_exists: bool
    parameters: str
    body: str
    properties: tuple[tuple[str, str], ...]
    command: str
    source_sha256: str


@dataclass(frozen=True)
class FunctionContract:
    definition: FunctionDefinition
    return_schema: ReturnSchema
    folder: str
    docstring: str

    @property
    def name(self) -> str:
        return self.definition.name


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:-[A-Za-z0-9_]+)*")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_CLOSE = {"(": ")", "[": "]", "{": "}"}
_OPERATORS = (">=", "<=", "==", "!=", "=~", "!~", "<>", "=>", "<|")


def _tokens(text: str, *, include_comments: bool = False) -> list[_Token]:
    """Lex strings/comments before delimiters, retaining exact literal bytes."""
    if not isinstance(text, str):
        raise KqlContractError("KQL input must be text.")
    result: list[_Token] = []
    i = 1 if text.startswith("\ufeff") else 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        if text.startswith("//", i):
            end = text.find("\n", i + 2)
            if include_comments:
                stop = len(text) if end < 0 else end
                result.append(_Token(text[i:stop].rstrip("\r"), i, stop, "comment"))
            i = len(text) if end < 0 else end + 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise KqlContractError("Unterminated KQL block comment.")
            if include_comments:
                result.append(_Token(text[i:end + 2], i, end + 2, "comment"))
            i = end + 2
            continue
        start = i
        if text.startswith("```", i):
            end = text.find("```", i + 3)
            if end < 0:
                raise KqlContractError("Unterminated KQL multiline string.")
            i = end + 3
            result.append(_Token(text[start:i], start, i, "string"))
            continue
        # KQL ordinary, verbatim, and obfuscated string literal prefixes.
        prefix = re.match(r"(?:[hH]@?|@[hH]?)?(['\"])", text[i:])
        if prefix:
            quote = prefix.group(1)
            verbatim = "@" in prefix.group(0)
            i += len(prefix.group(0))
            while i < len(text):
                if text[i] == quote:
                    if i + 1 < len(text) and text[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break
                if text[i] == "\\" and not verbatim:
                    i += 2
                else:
                    i += 1
            else:
                raise KqlContractError("Unterminated KQL string literal.")
            if i > len(text):
                raise KqlContractError("Unterminated KQL string escape.")
            result.append(_Token(text[start:i], start, i, "string"))
            continue
        word = _WORD.match(text, i)
        number = _NUMBER.match(text, i)
        if word or number:
            match = word or number
            i = match.end()
            result.append(_Token(match.group(0), start, i, "word" if word else "number"))
            continue
        operator = next((op for op in _OPERATORS if text.startswith(op, i)), None)
        i += len(operator) if operator else 1
        result.append(_Token(text[start:i], start, i))
    return result


def _values(tokens: Sequence[_Token]) -> tuple[str, ...]:
    return tuple(token.text for token in tokens)


def _signature(text: str) -> tuple[str, ...]:
    return _values(_tokens(text))


def _definition_signature(text: str) -> tuple[str, ...]:
    return _values(_tokens(text, include_comments=True))


def _balanced_end(tokens: Sequence[_Token], start: int) -> int:
    """Return the exclusive token index of a balanced group."""
    if start >= len(tokens) or tokens[start].text not in _CLOSE:
        raise KqlContractError("Expected a parenthesized or braced KQL group.")
    stack: list[str] = []
    for index in range(start, len(tokens)):
        token = tokens[index]
        if token.kind == "string":
            continue
        if token.text in _CLOSE:
            stack.append(_CLOSE[token.text])
        elif token.text in _CLOSE.values():
            if not stack or stack.pop() != token.text:
                raise KqlContractError("Mismatched KQL delimiters.")
            if not stack:
                return index + 1
    raise KqlContractError("Unclosed KQL delimiters.")


def _split_top(tokens: Sequence[_Token], delimiter: str) -> list[list[_Token]]:
    pieces: list[list[_Token]] = [[]]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind != "string" and token.text in _CLOSE:
            end = _balanced_end(tokens, index)
            pieces[-1].extend(tokens[index:end])
            index = end
        elif token.text == delimiter and token.kind != "string":
            pieces.append([])
            index += 1
        elif token.kind != "string" and token.text in _CLOSE.values():
            raise KqlContractError("Unexpected closing KQL delimiter.")
        else:
            pieces[-1].append(token)
            index += 1
    return pieces


def _slice(text: str, tokens: Sequence[_Token]) -> str:
    return text[tokens[0].start:tokens[-1].end] if tokens else ""


def _name_end(tokens: Sequence[_Token], index: int) -> tuple[str, int]:
    if index >= len(tokens):
        raise KqlContractError("Missing KQL function name.")
    if tokens[index].kind == "word" and _IDENTIFIER.fullmatch(tokens[index].text):
        return tokens[index].text, index + 1
    if tokens[index].text == "[":
        end = _balanced_end(tokens, index)
        if end == index + 3 and tokens[index + 1].kind == "string":
            return _string_value(tokens[index + 1].text), end
    raise KqlContractError("Unsupported KQL function name.")


def _function_parts(
    text: str, tokens: Sequence[_Token], start: int,
) -> tuple[FunctionDefinition, int]:
    header = _values(tokens[start:start + 3])
    if len(header) != 3 or header[0] != "." or header[1] not in (
        "create", "create-or-alter", "alter",
    ) or header[2] != "function":
        raise KqlContractError("Expected a create/alter function command.")
    index = start + 3
    if_not_exists = index < len(tokens) and tokens[index].text == "ifnotexists"
    if if_not_exists:
        index += 1
    properties: list[tuple[str, str]] = []
    if index < len(tokens) and tokens[index].text == "with":
        opening = index + 1
        end = _balanced_end(tokens, opening)
        if tokens[opening].text != "(":
            raise KqlContractError("Function properties must use parentheses.")
        for part in _split_top(tokens[opening + 1:end - 1], ","):
            if len(part) < 3 or part[0].kind != "word" or part[1].text != "=":
                raise KqlContractError("Invalid KQL function property.")
            if part[0].text in {key for key, _ in properties}:
                raise KqlContractError("Duplicate KQL function property.")
            properties.append((part[0].text, _slice(text, part[2:])))
        index = end
    name, index = _name_end(tokens, index)
    if index >= len(tokens) or tokens[index].text != "(":
        raise KqlContractError("A KQL function requires its parameter parentheses.")
    end = _balanced_end(tokens, index)
    parameters = _slice(text, tokens[index:end])
    index = end
    if index >= len(tokens) or tokens[index].text != "{":
        raise KqlContractError("A KQL function requires a braced body.")
    end = _balanced_end(tokens, index)
    body = _slice(text, tokens[index:end])
    command = _slice(text, tokens[start:end])
    return FunctionDefinition(
        name, header[1], if_not_exists, parameters, body, tuple(properties),
        command, hashlib.sha256(command.encode("utf-8")).hexdigest(),
    ), end


def parse_function_command(script: str) -> FunctionDefinition:
    """Parse exactly one function, including optional defaults and nested bodies."""
    tokens = _tokens(script)
    definition, end = _function_parts(script, tokens, 0)
    if end < len(tokens) and tokens[end].text == ";":
        end += 1
    if end != len(tokens):
        raise KqlContractError("A function source must contain exactly one command.")
    # Pin the supplied authoritative file, including its comments/final newline.
    return FunctionDefinition(
        definition.name, definition.verb, definition.if_not_exists,
        definition.parameters, definition.body, definition.properties,
        definition.command, hashlib.sha256(script.encode("utf-8")).hexdigest(),
    )


def _command_end(text: str, tokens: Sequence[_Token], start: int) -> int:
    head = _values(tokens[start:start + 4])
    if len(head) < 3:
        raise KqlContractError("Incomplete KQL management command.")
    if head[2] == "function":
        return _function_parts(text, tokens, start)[1]
    if head[2] == "materialized-view":
        index = start + 3
        while index < len(tokens):
            if tokens[index].text == "{":
                return _balanced_end(tokens, index)
            if tokens[index].text in ("(", "["):
                index = _balanced_end(tokens, index)
            elif tokens[index].text in (";", "."):
                break
            else:
                index += 1
        raise KqlContractError("A materialized-view command requires a braced body.")
    if head[2] == "table":
        index = start + 4
        if index < len(tokens) and tokens[index].text == "(":
            return _balanced_end(tokens, index)
        if _values(tokens[index:index + 3]) == ("ingestion", "csv", "mapping"):
            index += 3
            if index >= len(tokens) or tokens[index].kind != "string":
                raise KqlContractError("A CSV mapping requires a quoted name.")
            index += 1
            opening = index
            while index < len(tokens) and tokens[index].kind == "string":
                index += 1
            if index == opening:
                raise KqlContractError("A CSV mapping requires a string definition.")
            return index
        if _values(tokens[index:index + 2]) in (
            ("policy", "retention"), ("policy", "update"),
        ):
            index += 2
            opening = index
            while index < len(tokens) and tokens[index].kind == "string":
                index += 1
            if index == opening:
                raise KqlContractError("A KQL policy requires a string definition.")
            return index
        if _values(tokens[index:index + 4]) == ("policy", "caching", "hot", "="):
            index += 4
            if index + 1 >= len(tokens) or tokens[index].kind != "number":
                raise KqlContractError("A caching policy requires a duration.")
            if tokens[index + 1].kind != "word":
                raise KqlContractError("A caching duration requires its unit.")
            return index + 2
    # Retain an unknown command for the caller to reject, without treating its
    # nested strings or groups as new management statements.
    index = start + 1
    while index < len(tokens):
        gap = text[tokens[index - 1].end:tokens[index].start]
        if "\n" in gap or tokens[index].text in (".", ";"):
            break
        if tokens[index].text in _CLOSE:
            index = _balanced_end(tokens, index)
        else:
            index += 1
    return index


def extract_kql_management_commands(script: str) -> list[str]:
    """Extract complete top-level commands; verification queries are excluded.

    Blank lines, literal braces, nested bodies, and comments do not delimit a
    function. Management statements must start a line (indentation is allowed).
    Commands retain their original internal text; no line-based body rewriting
    or function splitting is performed.
    """
    tokens = _tokens(script)
    commands: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        line_start = script.rfind("\n", 0, token.start) + 1
        previous_end = tokens[index - 1].end if index else 0
        # Comments were lexed away, so a leading block comment does not hide a
        # command; an actual preceding token on this line still disqualifies it.
        if token.text == "." and previous_end <= line_start:
            end = _command_end(script, tokens, index)
            commands.append(_slice(script, tokens[index:end]))
            index = end
        elif token.kind != "string" and token.text in _CLOSE:
            index = _balanced_end(tokens, index)
        elif token.kind != "string" and token.text in _CLOSE.values():
            raise KqlContractError("Unexpected closing KQL delimiter.")
        else:
            index += 1
    return commands


def _string_value(literal: str) -> str:
    tokens = _tokens(literal)
    if len(tokens) != 1 or tokens[0].kind != "string":
        raise KqlContractError("Expected a single KQL string literal.")
    if literal.startswith('"'):
        try:
            return json.loads(literal)
        except json.JSONDecodeError as exc:
            raise KqlContractError("Unsupported function string escaping.") from exc
    if literal.startswith("'"):
        return literal[1:-1].replace("''", "'").replace("\\'", "'").replace("\\\\", "\\")
    if literal.startswith(("@'", '@"')):
        quote = literal[1]
        return literal[2:-1].replace(quote * 2, quote)
    raise KqlContractError("Unsupported function metadata string literal.")


# Column shapes come from the authoritative final projects and their offline
# operational-function tests, not from invented native discovery leaf nodes.
_OUTPUT_NAMES = {
    "AgentRawObservationTotals": (
        "RequestedStartUtc", "RequestedEndUtc", "WindowIsValid",
        "TrueFirstObservedAt", "TrueLastObservedAt", "RawObservationCount",
        "RawObservedAmountYen", "Scope", "SourceSystem", "SourceObject",
        "CountUnit", "AmountUnit", "RawDuplicateCaveat", "TimeZoneNotice",
    ),
    "AgentFileRunSummary": (
        "SourceFile", "WorkshopRunId", "ParticipantAlias", "RawObservationCount",
        "RawObservedAmountYen", "FirstObservedAtUtc", "LastObservedAtUtc",
        "RequestedStartUtc", "RequestedEndUtc", "WindowIsValid", "Scope",
        "SourceSystem", "SourceObject", "CountUnit", "AmountUnit",
        "RawDuplicateCaveat", "TimeZoneNotice",
    ),
    "AgentMunicipalityLeaders": (
        "MunicipalityID", "IsCountLeader", "IsAmountLeader",
        "RawObservationCount", "RawObservedAmountYen", "RequestedStartUtc",
        "RequestedEndUtc", "WindowIsValid", "Scope", "SourceSystem",
        "SourceObject", "CountUnit", "AmountUnit", "RawDuplicateCaveat",
        "TimeZoneNotice",
    ),
}
_SOURCE_TYPES = {
    "MunicipalityID": "string", "EventMinute": "datetime",
    "WorkshopRunId": "string", "ParticipantAlias": "string", "SourceFile": "string",
    "ObservationCount": "long", "ObservedAmountYen": "long",
    "FirstObservedAt": "datetime", "LastObservedAt": "datetime",
    "LastPublishedAtUtc": "datetime",
}
_PARAMETERS = "(StartUtc:datetime=datetime(null),EndUtc:datetime=datetime(null))"
_CALLS = {
    "isnull", "sum", "min", "max", "coalesce", "long", "iff", "case",
    "materialize", "toscalar",
}
_OPERATIONS = {"where", "summarize", "extend", "project", "order", "take"}
_LOCALS = {
    "AgentRawObservationTotals": {"WindowIsValid"},
    "AgentFileRunSummary": {"WindowIsValid"},
    "AgentMunicipalityLeaders": {
        "WindowIsValid", "PerMunicipality", "CountLeaderId", "AmountLeaderId",
    },
}


def _contains(values: Sequence[str], text: str) -> bool:
    target = _signature(text)
    return any(tuple(values[i:i + len(target)]) == target for i in range(len(values)))


def _type_of(expr: Sequence[_Token], types: Mapping[str, str]) -> str:
    if len(expr) == 1:
        token = expr[0]
        if token.kind == "string":
            return "string"
        if token.text in types:
            return types[token.text]
    if any(len(_split_top(expr, operator)) > 1 for operator in ("==", "<", ">=", "or", "and")):
        return "bool"
    if len(expr) >= 3 and expr[1].text == "(":
        end = _balanced_end(expr, 1)
        if end != len(expr):
            raise KqlContractError("Unsupported return-column expression.")
        args = _split_top(expr[2:-1], ",")
        name = expr[0].text
        if name == "long":
            return "long"
        if name in ("sum", "min", "max") and len(args) == 1:
            value_type = _type_of(args[0], types)
            if name == "sum" and value_type != "long":
                raise KqlContractError("Raw observation sums must remain long.")
            return value_type
        if name == "coalesce":
            candidates = {_type_of(arg, types) for arg in args}
            if len(candidates) == 1:
                return candidates.pop()
        if name in ("iff", "case") and len(args) == 3:
            left, right = _type_of(args[1], types), _type_of(args[2], types)
            if left == right:
                return left
    raise KqlContractError("Cannot derive a return-column type from the authoritative source.")


def _query_schema(
    tokens: Sequence[_Token], types: dict[str, str], local_tables: set[str],
) -> ReturnSchema:
    stages = _split_top(tokens, "|")
    if len(stages[0]) != 1 or stages[0][0].text not in {APPROVED_SOURCE} | local_tables:
        raise KqlContractError("Function queries must read only the approved summary or local bindings.")
    schema: ReturnSchema = ()
    for stage in stages[1:]:
        if not stage or stage[0].text not in _OPERATIONS:
            raise KqlContractError("Unsupported structural-function query operator.")
        operation = stage[0].text
        if operation in ("summarize", "extend"):
            clauses = _split_top(stage[1:], "by")
            if len(clauses) > 2 or (operation == "extend" and len(clauses) != 1):
                raise KqlContractError("Unsupported structural-function grouping.")
            for part in _split_top(clauses[0], ","):
                if len(part) < 3 or part[1].text != "=":
                    raise KqlContractError("Return columns must use explicit source aliases.")
                types[part[0].text] = _type_of(part[2:], types)
        elif operation == "project":
            names = _split_top(stage[1:], ",")
            if any(len(part) != 1 or part[0].text not in types for part in names):
                raise KqlContractError("The output project must contain known, unrenamed columns.")
            schema = tuple((part[0].text, types[part[0].text]) for part in names)
    return schema


def derive_return_schema(definition: FunctionDefinition) -> ReturnSchema:
    """Infer the narrow source's output types without executing a data query."""
    tokens = _tokens(definition.body)[1:-1]
    statements = _split_top(tokens, ";")
    types = {**_SOURCE_TYPES, "StartUtc": "datetime", "EndUtc": "datetime"}
    local_tables: set[str] = set()
    for statement in statements[:-1]:
        if len(statement) < 5 or statement[0].text != "let" or statement[2].text != "=":
            raise KqlContractError("Unsupported function-local statement.")
        name, expr = statement[1].text, statement[3:]
        if expr[0].text in ("materialize", "toscalar"):
            end = _balanced_end(expr, 1)
            if end != len(expr):
                raise KqlContractError("Unexpected tokens after a function-local query.")
            schema = _query_schema(expr[2:-1], types, local_tables)
            if expr[0].text == "materialize":
                local_tables.add(name)
            elif len(schema) == 1:
                types[name] = schema[0][1]
            else:
                raise KqlContractError("A leader scalar must project exactly one column.")
        else:
            types[name] = _type_of(expr, types)
    return _query_schema(statements[-1], types, local_tables)


def _validate_source(definition: FunctionDefinition) -> ReturnSchema:
    name = definition.name
    if name not in FUNCTION_NAMES:
        raise KqlContractError(f"Not a required structural function: {name!r}.")
    if definition.verb != "create" or definition.if_not_exists:
        raise KqlContractError(f"{name}: authoritative sources must use fresh-only .create function.")
    if _signature(definition.parameters) != _signature(_PARAMETERS):
        raise KqlContractError(f"{name}: expected optional StartUtc/EndUtc datetime(null) parameters.")
    tokens = _tokens(definition.body)[1:-1]
    values = _values(tokens)
    lets = {
        tokens[index + 1].text for index, token in enumerate(tokens[:-1])
        if token.text == "let"
    }
    if lets != _LOCALS[name] or values.count("let") != len(lets):
        raise KqlContractError(f"{name}: unexpected local bindings.")
    allowed = (
        set(_SOURCE_TYPES) | set(_OUTPUT_NAMES[name]) | lets | _CALLS | _OPERATIONS
        | {APPROVED_SOURCE, "StartUtc", "EndUtc", "let", "or", "and", "by", "asc", "desc"}
    )
    for index, token in enumerate(tokens):
        if token.kind == "word" and token.text not in allowed:
            raise KqlContractError(f"{name}: unapproved source, column, or operation {token.text!r}.")
        if token.kind == "word" and index + 1 < len(tokens) and tokens[index + 1].text == "(":
            if token.text not in _CALLS:
                raise KqlContractError(f"{name}: unapproved function call {token.text!r}.")
    required = [
        "let WindowIsValid = isnull(StartUtc) or isnull(EndUtc) or StartUtc < EndUtc;",
        "| where WindowIsValid",
        "| where isnull(StartUtc) or EventMinute >= StartUtc",
        "| where isnull(EndUtc) or EventMinute < EndUtc",
        "RawObservationCount = sum(ObservationCount)",
        "RawObservedAmountYen = sum(ObservedAmountYen)",
        "RequestedStartUtc = StartUtc",
        "RequestedEndUtc = EndUtc",
        'SourceSystem = "Eventhouse"',
        f'SourceObject = "{APPROVED_SOURCE}"',
        'CountUnit = "raw observations"',
        'AmountUnit = "JPY"',
        'RawDuplicateCaveat = "The totals may include duplicate raw observations; '
        'the approved aggregate exposes no event identifier or unique-event metric."',
        'TimeZoneNotice = "All timestamps are UTC."',
    ]
    if name == "AgentRawObservationTotals":
        required.extend((
            "TrueFirstObservedAt = min(FirstObservedAt)",
            "TrueLastObservedAt = max(LastObservedAt)",
            "RawObservationCount = coalesce(RawObservationCount, long(0))",
            "RawObservedAmountYen = coalesce(RawObservedAmountYen, long(0))",
        ))
    elif name == "AgentFileRunSummary":
        required.extend((
            "FirstObservedAtUtc = min(FirstObservedAt)",
            "LastObservedAtUtc = max(LastObservedAt)",
            "by SourceFile, WorkshopRunId, ParticipantAlias | extend",
            "| order by SourceFile asc, WorkshopRunId asc, ParticipantAlias asc",
        ))
    else:
        required.extend((
            "by MunicipalityID );",
            "| order by RawObservationCount desc, MunicipalityID asc | take 1 | project MunicipalityID",
            "| order by RawObservedAmountYen desc, MunicipalityID asc | take 1 | project MunicipalityID",
            "| where MunicipalityID == CountLeaderId or MunicipalityID == AmountLeaderId",
            "IsCountLeader = MunicipalityID == CountLeaderId",
            "IsAmountLeader = MunicipalityID == AmountLeaderId",
            "| order by MunicipalityID asc",
        ))
    if any(not _contains(values, part) for part in required):
        raise KqlContractError(f"{name}: raw-grain, half-open UTC, or provenance contract changed.")
    if values.count(APPROVED_SOURCE) != 1 or values.count("summarize") != 1:
        raise KqlContractError(f"{name}: expected one approved-source aggregation.")
    expected_stages = {
        "AgentRawObservationTotals": (3, 1, 1, 0, 0, 0),
        "AgentFileRunSummary": (3, 1, 1, 1, 0, 2),
        "AgentMunicipalityLeaders": (4, 1, 3, 3, 2, 4),
    }[name]
    if tuple(values.count(op) for op in ("where", "extend", "project", "order", "take", "by")) != expected_stages:
        raise KqlContractError(f"{name}: grouping, filters, or leader-grain contract changed.")
    schema = derive_return_schema(definition)
    if tuple(column for column, _ in schema) != _OUTPUT_NAMES[name]:
        raise KqlContractError(f"{name}: output shape differs from the authoritative contract.")
    expected_types = {
        field: (
            "datetime" if field.endswith(("Utc", "ObservedAt"))
            else "bool" if field in ("WindowIsValid", "IsCountLeader", "IsAmountLeader")
            else "long" if field in ("RawObservationCount", "RawObservedAmountYen")
            else "string"
        ) for field in _OUTPUT_NAMES[name]
    }
    if any(kind != expected_types[field] for field, kind in schema):
        raise KqlContractError(f"{name}: output types differ from the authoritative contract.")
    return schema


def load_function_scripts(directory: str | Path) -> dict[str, str]:
    """Read exactly the three owned sources; a legacy function file is ignored."""
    directory = Path(directory)
    return {
        name: (directory / f"{name}.kql").read_bytes().decode("utf-8")
        for name in FUNCTION_NAMES
    }


def validate_function_contracts(
    function_scripts: Mapping[str, str],
) -> dict[str, FunctionContract]:
    """Validate all inputs before any callback; keys are names or name.kql."""
    if not isinstance(function_scripts, Mapping):
        raise KqlContractError("Function sources must be a name-to-text mapping.")
    scripts: dict[str, str] = {}
    for key, text in function_scripts.items():
        if not isinstance(key, str):
            raise KqlContractError("Function source keys must be names.")
        name = key[:-4] if key.endswith(".kql") else key
        if name in scripts:
            raise KqlContractError(f"Duplicate function source: {name}.")
        scripts[name] = text
    if set(scripts) != set(FUNCTION_NAMES):
        raise KqlContractError("Exactly the three structural function sources are required; legacy is not selected.")
    contracts: dict[str, FunctionContract] = {}
    for name in FUNCTION_NAMES:
        definition = parse_function_command(scripts[name])
        if definition.name != name:
            raise KqlContractError(f"{name}: source declares a different function.")
        schema = _validate_source(definition)
        properties = dict(definition.properties)
        if set(properties) != {"folder", "docstring"}:
            raise KqlContractError(f"{name}: unexpected function properties.")
        folder, docstring = (_string_value(properties[key]) for key in ("folder", "docstring"))
        if folder != "Agent" or not docstring.strip():
            raise KqlContractError(f"{name}: authoritative Agent metadata is required.")
        contracts[name] = FunctionContract(definition, schema, folder, docstring)
    return contracts


def _gate(enabled: bool) -> None:
    if type(enabled) is not bool:
        raise KqlContractError("The reference feature gate must be a boolean.")


def compose_kql_management_commands(
    base_script: str,
    function_scripts: Mapping[str, str] | None = None,
    *,
    enabled: bool = False,
) -> list[str]:
    """Return released five commands, or five plus three when explicitly enabled.

    Baseline statements remain untouched. The caller owns executing/verifying
    those five and invokes the strict function provisioner before Agent discovery;
    it must not blindly replay the appended .create commands on an existing DB.
    """
    _gate(enabled)
    if VERIFICATION_MARKER not in base_script:
        raise KqlContractError("The released KQL verification boundary is missing.")
    schema_text = base_script.split(VERIFICATION_MARKER, 1)[0]
    commands = extract_kql_management_commands(schema_text)
    prefixes = (
        ".create-merge table DonationEvents (",
        ".create-or-alter table DonationEvents ingestion csv mapping",
        ".create-or-alter materialized-view DonationObservationSummaryForAgent",
        ".alter table DonationEvents policy retention",
        ".alter table DonationEvents policy caching",
    )
    if len(commands) != BASE_MANAGEMENT_COMMAND_COUNT or any(
        _signature(command)[:len(_signature(prefix))] != _signature(prefix)
        for command, prefix in zip(commands, prefixes)
    ):
        raise KqlContractError("The released baseline must contain its original five management commands.")
    # Unlike extraction for documentation, composition cannot silently discard a
    # query or stray token in the setup region and claim the region was validated.
    if _signature(schema_text) != _signature("\n".join(commands)):
        raise KqlContractError("Non-management text leaked into the KQL setup region.")
    if not enabled:
        return commands
    contracts = validate_function_contracts(function_scripts)
    return commands + [contracts[name].definition.command for name in FUNCTION_NAMES]


def _tables(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        raise KqlContractError("Kusto callback must return a JSON object.")
    for key in ("error", "Error", "errors", "Errors", "Exceptions", "OneApiErrors", "HasErrors"):
        if payload.get(key):
            raise KqlContractError("Kusto returned an error instead of structural proof.")
    tables = payload.get("Tables")
    if not isinstance(tables, list):
        raise KqlContractError("Kusto structural proof is missing its Tables array.")
    records = []
    contents = []
    for table in tables:
        if not isinstance(table, Mapping):
            raise KqlContractError("Malformed Kusto result table.")
        for key in ("error", "Error", "Errors", "OneApiErrors", "HasErrors"):
            if table.get(key):
                raise KqlContractError("Kusto result table contains an error.")
        columns, rows = table.get("Columns"), table.get("Rows")
        if not isinstance(columns, list) or not isinstance(rows, list):
            raise KqlContractError("Kusto result table requires Columns and Rows arrays.")
        names = [column.get("ColumnName") if isinstance(column, Mapping) else None for column in columns]
        if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
            raise KqlContractError("Kusto result column names are missing or ambiguous.")
        table_records = []
        for row in rows:
            if not isinstance(row, list) or len(row) != len(names):
                raise KqlContractError("Malformed Kusto result row.")
            record = dict(zip(names, row))
            if record.get("OneApiErrors") or record.get("HasErrors"):
                raise KqlContractError("Kusto reported a partial query failure.")
            table_records.append(record)
        records.append(table_records)
        if names == ["Ordinal", "Kind", "Name", "Id", "PrettyName"]:
            contents.append(len(records) - 1)

    status_indexes = {
        index for index, table in enumerate(tables) if table.get("TableName") == "QueryStatus"
    }
    result_indexes = list(range(len(tables)))
    if contents:
        if len(contents) != 1:
            raise KqlContractError("Ambiguous Kusto table-of-contents metadata.")
        contents_index = contents[0]
        entries = records[contents_index]
        ordinals = [entry["Ordinal"] for entry in entries]
        if (
            any(type(ordinal) is not int for ordinal in ordinals)
            or len(set(ordinals)) != len(ordinals)
            or set(ordinals) != set(range(len(tables))) - {contents_index}
            or any(entry["Kind"] not in {"QueryResult", "QueryProperties", "QueryStatus"} for entry in entries)
        ):
            raise KqlContractError("Malformed Kusto table-of-contents references.")
        result_indexes = [entry["Ordinal"] for entry in entries if entry["Kind"] == "QueryResult"]
        status_indexes.update(entry["Ordinal"] for entry in entries if entry["Kind"] == "QueryStatus")
        if not result_indexes:
            raise KqlContractError("Kusto metadata did not identify a query result.")
    for index in status_indexes:
        for record in records[index]:
            severity = record.get("Severity")
            code = record.get("StatusCode", 0)
            if type(severity) is not int or severity <= 2 or type(code) is not int or code != 0:
                raise KqlContractError("Kusto QueryStatus is not a successful structural proof.")
    return [tables[index] for index in result_indexes]


def kusto_result_rows(
    payload: Mapping[str, Any], *, required_columns: Sequence[str],
) -> list[dict[str, Any]]:
    """Read one unambiguous result table by column names, never substring search."""
    candidates = []
    for table in _tables(payload):
        names = [column["ColumnName"] for column in table["Columns"]]
        if set(required_columns).issubset(names):
            candidates.append([dict(zip(names, row)) for row in table["Rows"]])
    if len(candidates) != 1:
        raise KqlContractError("Expected exactly one Kusto structural result table.")
    return candidates[0]


def compare_function_definition(
    contract: FunctionContract, show_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Require an exact .show function identity, Parameters, Body, and metadata."""
    rows = kusto_result_rows(
        show_result, required_columns=("Name", "Parameters", "Body", "Folder", "DocString"),
    )
    if len(rows) != 1:
        raise KqlConflictError(f"{contract.name}: .show function did not return exactly one definition.")
    row = rows[0]
    expected = {
        "Name": contract.name, "Folder": contract.folder, "DocString": contract.docstring,
    }
    if any(row[key] != value for key, value in expected.items()):
        raise KqlConflictError(f"{contract.name}: foreign function identity or metadata.")
    for key, source in (
        ("Parameters", contract.definition.parameters), ("Body", contract.definition.body),
    ):
        value = row[key]
        if not isinstance(value, str) or _definition_signature(value) != _definition_signature(source):
            raise KqlConflictError(f"{contract.name}: .show function {key} mismatch; refusing overwrite.")
    observed = {key: row[key] for key in ("Name", "Parameters", "Body", "Folder", "DocString")}
    return {
        "command": f".show function {contract.name}",
        "parametersMatch": True,
        "bodyMatch": True,
        "definitionSha256": hashlib.sha256(
            json.dumps(observed, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
    }


_CLR_TYPES = {
    "bool": {"System.Boolean", "System.SByte"},
    "datetime": {"System.DateTime"},
    "long": {"System.Int64"},
    "string": {"System.String"},
}


def parse_query_schema(payload: Mapping[str, Any]) -> ReturnSchema:
    """Read the actual getschema result, including ordinal and CLR/KQL agreement."""
    rows = kusto_result_rows(
        payload, required_columns=("ColumnName", "ColumnOrdinal", "DataType", "ColumnType"),
    )
    if not rows:
        raise KqlContractError("A function getschema result must not be empty.")
    ordinals = [row["ColumnOrdinal"] for row in rows]
    if any(type(ordinal) is not int for ordinal in ordinals) or sorted(ordinals) != list(range(len(rows))):
        raise KqlContractError("The getschema column ordinals are not unique and contiguous.")
    rows.sort(key=lambda row: row["ColumnOrdinal"])
    names = [row["ColumnName"] for row in rows]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
        raise KqlContractError("The getschema column names are missing or duplicated.")
    for row in rows:
        if (
            not isinstance(row["ColumnType"], str)
            or not isinstance(row["DataType"], str)
            or row["DataType"] not in _CLR_TYPES.get(row["ColumnType"], set())
        ):
            raise KqlContractError("The getschema CLR and KQL column types do not agree.")
    return tuple((row["ColumnName"], row["ColumnType"]) for row in rows)


def compare_function_schema(
    contract: FunctionContract, schema_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare source-derived columns to query getschema, not discovery children."""
    schema = parse_query_schema(schema_result)
    if schema != contract.return_schema:
        raise KqlConflictError(f"{contract.name}: query getschema output schema mismatch; refusing overwrite.")
    return {
        "query": f"{contract.name}() | getschema",
        "provenance": "query-getschema",
        "columns": [
            {"name": name, "type": kind, "ordinal": index}
            for index, (name, kind) in enumerate(schema)
        ],
    }


def _inventory(
    execute_management: KustoCallback, command: str, column: str,
) -> set[str]:
    rows = kusto_result_rows(execute_management(command), required_columns=(column,))
    names = [row[column] for row in rows]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
        raise KqlContractError(f"Ambiguous Kusto object inventory for {command}.")
    return set(names)


def provision_reference_functions(
    function_scripts: Mapping[str, str],
    *,
    execute_management: KustoCallback,
    execute_query: KustoCallback,
    enabled: bool = False,
) -> dict[str, Any]:
    """Create missing functions or reuse exact ones, then prove all three.

    The orchestrator binds the environment and verifies the five baseline
    objects first. Read/permission/transport failures propagate, never mean
    "absent". All installed functions are checked before the first create.
    A create race or post-create mismatch stops without overwrite or cleanup.
    Only getschema queries are submitted; there are no native Agent questions.
    """
    _gate(enabled)
    result: dict[str, Any] = {"enabled": enabled, "functions": {}, "acceptanceClaimed": False}
    if not enabled:
        return result
    contracts = validate_function_contracts(function_scripts)
    functions = _inventory(execute_management, ".show functions | project Name", "Name")
    tables = _inventory(execute_management, ".show tables | project TableName", "TableName")
    views = _inventory(execute_management, ".show materialized-views | project Name", "Name")
    source_collisions = {
        item for item in tables | functions
        if item.casefold() == APPROVED_SOURCE.casefold()
    }
    source_variants = {
        item for item in views
        if item.casefold() == APPROVED_SOURCE.casefold() and item != APPROVED_SOURCE
    }
    if APPROVED_SOURCE not in views or source_collisions or source_variants:
        raise KqlConflictError("The approved summary materialized view must exist before function provisioning.")
    for name in FUNCTION_NAMES:
        collisions = {item for item in tables | views if item.casefold() == name.casefold()}
        variants = {item for item in functions if item.casefold() == name.casefold() and item != name}
        if collisions or variants:
            raise KqlConflictError(f"{name}: foreign same-name/case-variant object; refusing overwrite.")

    def verify(contract: FunctionContract, state: str) -> dict[str, Any]:
        definition = compare_function_definition(
            contract, execute_management(f".show function {contract.name}"),
        )
        schema = compare_function_schema(
            contract, execute_query(f"{contract.name}() | getschema"),
        )
        return {
            "state": state,
            "sourceSha256": contract.definition.source_sha256,
            "definition": definition,
            "returnSchema": schema,
        }

    # Complete read-only preflight before creating even the first missing one.
    for name in FUNCTION_NAMES:
        if name in functions:
            result["functions"][name] = verify(contracts[name], "REUSED")
    for name in FUNCTION_NAMES:
        if name not in functions:
            _tables(execute_management(contracts[name].definition.command))
            result["functions"][name] = verify(contracts[name], "CREATED")
    result["functions"] = {name: result["functions"][name] for name in FUNCTION_NAMES}
    return result


def provision_kql(
    client: Any,
    query_uri: str,
    database_name: str,
    function_scripts: Mapping[str, str],
    *,
    enabled: bool = False,
) -> dict[str, Any]:
    """Notebook04 adapter for execute_kusto(uri, db, csl, *, management).

    No environment, endpoint, or database is inferred. Callers with a different
    client interface can inject the two command-to-JSON callbacks directly.
    """
    _gate(enabled)
    if enabled and any(not isinstance(value, str) or not value.strip() for value in (query_uri, database_name)):
        raise KqlContractError("An explicit environment query URI and database name are required.")
    return provision_reference_functions(
        function_scripts,
        execute_management=lambda command: client.execute_kusto(
            query_uri, database_name, command, management=True,
        ),
        execute_query=lambda query: client.execute_kusto(
            query_uri, database_name, query, management=False,
        ),
        enabled=enabled,
    )
