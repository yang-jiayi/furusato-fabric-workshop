"""Offline contract tests for the bounded Eventhouse functions."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FUNCTIONS = ROOT / "tools" / "data-agent" / "operational-functions"
TOTALS = FUNCTIONS / "AgentRawObservationTotals.kql"
LEADERS = FUNCTIONS / "AgentObservationLeaders.kql"
FILE_RUN = FUNCTIONS / "AgentFileRunSummary.kql"
MUNICIPALITY_LEADERS = FUNCTIONS / "AgentMunicipalityLeaders.kql"

NOTICE = "All timestamps are UTC."
CAVEAT = (
    "The totals may include duplicate raw observations; the approved aggregate "
    "exposes no event identifier or unique-event metric."
)


def read_lf(path: Path) -> str:
    raw = path.read_bytes()
    if b"\r" in raw or not raw.endswith(b"\n"):
        raise AssertionError(f"{path.name} must use LF and end with one newline")
    return raw.decode("utf-8")


def local_leaders(rows: list[tuple[str, int, int]]) -> list[dict[str, object]]:
    """Reference only: deterministic winner selection without live ingestion."""
    per_municipality: dict[str, list[int]] = {}
    for municipality_id, count, amount in rows:
        totals = per_municipality.setdefault(municipality_id, [0, 0])
        totals[0] += count
        totals[1] += amount
    if not per_municipality:
        return []
    count_id, count_values = min(
        per_municipality.items(),
        key=lambda item: (-item[1][0], item[0]),
    )
    amount_id, amount_values = min(
        per_municipality.items(),
        key=lambda item: (-item[1][1], item[0]),
    )
    return [
        {
            "LeaderMetric": "RawObservationCount",
            "MunicipalityID": count_id,
            "RawObservationCount": count_values[0],
            "RawObservedAmountYen": count_values[1],
        },
        {
            "LeaderMetric": "RawObservedAmountYen",
            "MunicipalityID": amount_id,
            "RawObservationCount": amount_values[0],
            "RawObservedAmountYen": amount_values[1],
        },
    ]


def local_unique_leaders(
    rows: list[tuple[str, int, int]],
) -> list[dict[str, object]]:
    """Reference only: unique Municipality grain with leader flags."""
    per_municipality: dict[str, list[int]] = {}
    for municipality_id, count, amount in rows:
        totals = per_municipality.setdefault(municipality_id, [0, 0])
        totals[0] += count
        totals[1] += amount
    if not per_municipality:
        return []
    count_id = min(
        per_municipality,
        key=lambda item: (-per_municipality[item][0], item),
    )
    amount_id = min(
        per_municipality,
        key=lambda item: (-per_municipality[item][1], item),
    )
    return [
        {
            "MunicipalityID": municipality_id,
            "IsCountLeader": municipality_id == count_id,
            "IsAmountLeader": municipality_id == amount_id,
            "RawObservationCount": per_municipality[municipality_id][0],
            "RawObservedAmountYen": per_municipality[municipality_id][1],
        }
        for municipality_id in sorted({count_id, amount_id})
    ]


class OperationalFunctionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.totals = read_lf(TOTALS)
        cls.leaders = read_lf(LEADERS)
        cls.file_run = read_lf(FILE_RUN)
        cls.municipality_leaders = read_lf(MUNICIPALITY_LEADERS)

    def test_exact_owned_create_commands_and_optional_parameters(self):
        self.assertTrue(
            self.totals.startswith(".create function with ("),
            "Must fail if the function already exists",
        )
        self.assertTrue(self.leaders.startswith(".create function with ("))
        self.assertTrue(self.file_run.startswith(".create function with ("))
        self.assertTrue(
            self.municipality_leaders.startswith(".create function with (")
        )
        self.assertNotIn(
            ".create-or-alter",
            self.totals
            + self.leaders
            + self.file_run
            + self.municipality_leaders,
        )
        for name, text in (
            ("AgentRawObservationTotals", self.totals),
            ("AgentObservationLeaders", self.leaders),
            ("AgentFileRunSummary", self.file_run),
            ("AgentMunicipalityLeaders", self.municipality_leaders),
        ):
            self.assertIn(
                f"{name}(\n    StartUtc:datetime = datetime(null),"
                "\n    EndUtc:datetime = datetime(null)\n)",
                text,
            )

    def test_only_approved_materialized_view_is_queried(self):
        specifications = (
            (
                self.totals,
                {"WindowIsValid"},
                set(),
                {
                    "AgentRawObservationTotals",
                    "coalesce",
                    "datetime",
                    "iff",
                    "isnull",
                    "long",
                    "max",
                    "min",
                    "sum",
                    "with",
                },
                [],
            ),
            (
                self.leaders,
                {
                    "WindowIsValid",
                    "PerMunicipality",
                    "CountLeader",
                    "AmountLeader",
                },
                {"PerMunicipality"},
                {
                    "AgentObservationLeaders",
                    "datetime",
                    "iff",
                    "isnull",
                    "materialize",
                    "sum",
                    "with",
                },
                [("union", "CountLeader, AmountLeader")],
            ),
            (
                self.file_run,
                {"WindowIsValid"},
                set(),
                {
                    "AgentFileRunSummary",
                    "case",
                    "datetime",
                    "isnull",
                    "max",
                    "min",
                    "sum",
                    "with",
                },
                [],
            ),
            (
                self.municipality_leaders,
                {
                    "WindowIsValid",
                    "PerMunicipality",
                    "CountLeaderId",
                    "AmountLeaderId",
                },
                {"PerMunicipality"},
                {
                    "AgentMunicipalityLeaders",
                    "case",
                    "datetime",
                    "isnull",
                    "materialize",
                    "sum",
                    "toscalar",
                    "with",
                },
                [],
            ),
        )
        for (
            text,
            expected_lets,
            allowed_local_sources,
            expected_calls,
            expected_unions,
        ) in specifications:
            self.assertEqual(text.count("DonationObservationSummaryForAgent"), 2)
            self.assertNotIn("DonationEvents", text)
            self.assertNotIn("EventID", text.split("RawDuplicateCaveat =", 1)[0])
            self.assertNotRegex(
                text.lower(),
                r"\b(join|lookup|external_table|materialized_view|database|cluster|"
                r"table)\s*\(",
            )
            code_only = re.sub(r"//[^\n]*", "", text)
            code_only = re.sub(r'"(?:[^"\\]|\\.)*"', '""', code_only)
            self.assertNotRegex(
                code_only,
                r"\[[^\]]+\]",
                "Bracketed/escaped source entities are not permitted",
            )
            commands = [
                line.strip()
                for line in text.splitlines()
                if line.lstrip().startswith(".")
            ]
            self.assertEqual(commands, [".create function with ("])
            self.assertNotRegex(
                text.lower(),
                r"(?m)^\s*\.(alter|drop|set|ingest|execute|append|delete|rename)\b",
            )
            lets = set(re.findall(r"(?m)^\s*let\s+([A-Za-z_][A-Za-z0-9_]*)\s*=", text))
            self.assertEqual(lets, expected_lets)
            source_text = re.sub(
                r"(?ms)^\s*\| project\b.*?(?=^\s*\||^\s*\})",
                "",
                text,
            )
            lines = source_text.splitlines()
            standalone_sources = set()
            for index, line in enumerate(lines):
                match = re.fullmatch(
                    r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*",
                    line,
                )
                following = next(
                    (
                        candidate.strip()
                        for candidate in lines[index + 1 :]
                        if candidate.strip()
                    ),
                    "",
                )
                if match and following.startswith("|"):
                    standalone_sources.add(match.group(1))
            self.assertEqual(
                standalone_sources,
                {"DonationObservationSummaryForAgent"} | allowed_local_sources,
            )
            source_code = re.sub(
                r"(?ms)^\s*\| project\b.*?(?=^\s*\||^\s*\})",
                "",
                code_only,
            )
            inline_sources = {
                source
                for groups in re.findall(
                    r"(?m)(?:^[ \t]*|(?<![<>=!])=[ \t]*)"
                    r"(?:([A-Za-z_][A-Za-z0-9_]*)[ \t]*\|"
                    r"|([A-Za-z_][A-Za-z0-9_]*)[ \t]*\n[ \t]*\|)",
                    source_code,
                )
                for source in groups
                if source
            }
            self.assertEqual(
                inline_sources,
                {"DonationObservationSummaryForAgent"} | allowed_local_sources,
            )
            calls = set(
                re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", text)
            )
            self.assertEqual(calls, expected_calls)
            unions = [
                (match.group(1).strip(), match.group(2).strip())
                for match in re.finditer(
                    r"(?im)^\s*(\|?\s*union)\s+([^\n]+)$",
                    text,
                )
            ]
            self.assertEqual(unions, expected_unions)

    def test_half_open_utc_filter_and_window_names_are_explicit(self):
        for text in (
            self.totals,
            self.leaders,
            self.file_run,
            self.municipality_leaders,
        ):
            self.assertIn("EventMinute >= StartUtc", text)
            self.assertIn("EventMinute < EndUtc", text)
            self.assertIn("RequestedStartUtc = StartUtc", text)
            self.assertIn("RequestedEndUtc = EndUtc", text)
            self.assertIn('"RequestedHalfOpenUtcWindow"', text)
            self.assertIn("WindowIsValid", text)
            self.assertNotIn("startofday", text.lower())
            self.assertNotIn("endofday", text.lower())

    def test_totals_is_one_atomic_scalar_row_without_grouping(self):
        self.assertEqual(self.totals.count("| summarize"), 1)
        summarize = self.totals.split("| summarize", 1)[1].split("| extend", 1)[0]
        self.assertNotRegex(summarize, r"\bby\b")
        self.assertIn("RawObservationCount = sum(ObservationCount)", summarize)
        self.assertIn("RawObservedAmountYen = sum(ObservedAmountYen)", summarize)
        self.assertIn("TrueFirstObservedAt = min(FirstObservedAt)", summarize)
        self.assertIn("TrueLastObservedAt = max(LastObservedAt)", summarize)
        self.assertIn(
            "RawObservationCount = coalesce(RawObservationCount, long(0))",
            self.totals,
        )
        self.assertIn(
            "RawObservedAmountYen = coalesce(RawObservedAmountYen, long(0))",
            self.totals,
        )

    def test_leaders_aggregates_once_then_returns_two_metric_rows(self):
        self.assertEqual(self.leaders.count("| summarize"), 1)
        self.assertEqual(self.leaders.count("by MunicipalityID"), 1)
        self.assertEqual(self.leaders.count("| order by"), 3)
        self.assertEqual(self.leaders.count("| take 1"), 2)
        self.assertIn("union CountLeader, AmountLeader", self.leaders)
        self.assertIn('LeaderMetric = "RawObservationCount"', self.leaders)
        self.assertIn('LeaderMetric = "RawObservedAmountYen"', self.leaders)
        self.assertIn("LeaderValue = RawObservationCount", self.leaders)
        self.assertIn("LeaderValue = RawObservedAmountYen", self.leaders)

    def test_deterministic_tie_breaks_are_declared(self):
        self.assertRegex(
            self.leaders,
            re.compile(
                r"RawObservationCount desc,\n\s+MunicipalityID asc"
            ),
        )
        self.assertRegex(
            self.leaders,
            re.compile(
                r"RawObservedAmountYen desc,\n\s+MunicipalityID asc"
            ),
        )
        self.assertNotRegex(
            self.leaders,
            r"RawObservationCount desc,\n\s+RawObservedAmountYen desc",
        )
        self.assertNotRegex(
            self.leaders,
            r"RawObservedAmountYen desc,\n\s+RawObservationCount desc",
        )
        fixture = [
            ("B", 4, 100),
            ("A", 4, 1),
            ("C", 1, 120),
            ("D", 2, 120),
        ]
        self.assertEqual(
            local_leaders(fixture),
            [
                {
                    "LeaderMetric": "RawObservationCount",
                    "MunicipalityID": "A",
                    "RawObservationCount": 4,
                    "RawObservedAmountYen": 1,
                },
                {
                    "LeaderMetric": "RawObservedAmountYen",
                    "MunicipalityID": "C",
                    "RawObservationCount": 1,
                    "RawObservedAmountYen": 120,
                },
            ],
        )
        self.assertEqual(local_leaders([]), [])

    def test_contract_metadata_is_complete_and_exact(self):
        for text in (
            self.totals,
            self.leaders,
            self.file_run,
            self.municipality_leaders,
        ):
            self.assertIn(f'TimeZoneNotice = "{NOTICE}"', text)
            self.assertIn(f'RawDuplicateCaveat = "{CAVEAT}"', text)
            self.assertIn('SourceSystem = "Eventhouse"', text)
            self.assertIn(
                'SourceObject = "DonationObservationSummaryForAgent"',
                text,
            )
            self.assertIn('CountUnit = "raw observations"', text)
            self.assertIn('AmountUnit = "JPY"', text)
            self.assertIn("| where WindowIsValid", text)
        for text in (self.totals, self.leaders):
            self.assertIn("Caller must reject WindowIsValid=false", text)
        self.assertIn("Invalid windows return no rows", self.file_run)
        self.assertIn(
            "Invalid windows return no rows",
            self.municipality_leaders,
        )

    def test_file_run_summary_has_exact_detail_contract(self):
        self.assertEqual(self.file_run.count("| summarize"), 1)
        summarize = self.file_run.split("| summarize", 1)[1].split(
            "| extend",
            1,
        )[0]
        self.assertIn(
            "by SourceFile, WorkshopRunId, ParticipantAlias",
            summarize,
        )
        self.assertIn(
            "RawObservationCount = sum(ObservationCount)",
            summarize,
        )
        self.assertIn(
            "RawObservedAmountYen = sum(ObservedAmountYen)",
            summarize,
        )
        self.assertIn(
            "FirstObservedAtUtc = min(FirstObservedAt)",
            summarize,
        )
        self.assertIn(
            "LastObservedAtUtc = max(LastObservedAt)",
            summarize,
        )
        project = self.file_run.rsplit("| project", 1)[1].split(
            "| order by",
            1,
        )[0]
        fields = [
            line.strip().rstrip(",")
            for line in project.splitlines()
            if line.strip()
        ]
        self.assertEqual(
            fields,
            [
                "SourceFile",
                "WorkshopRunId",
                "ParticipantAlias",
                "RawObservationCount",
                "RawObservedAmountYen",
                "FirstObservedAtUtc",
                "LastObservedAtUtc",
                "RequestedStartUtc",
                "RequestedEndUtc",
                "WindowIsValid",
                "Scope",
                "SourceSystem",
                "SourceObject",
                "CountUnit",
                "AmountUnit",
                "RawDuplicateCaveat",
                "TimeZoneNotice",
            ],
        )

    def test_file_run_summary_rejects_invalid_and_derived_grain_logic(self):
        where_valid = self.file_run.index("| where WindowIsValid")
        summarize = self.file_run.index("| summarize")
        self.assertLess(where_valid, summarize)
        self.assertNotRegex(
            self.file_run,
            r"(?i)\b(union|iff|bin|datetime_diff|"
            r"EventMinuteGrainSeconds|TOTAL)\b",
        )
        self.assertNotIn("long(", self.file_run)
        self.assertNotIn("real(", self.file_run)
        self.assertIn(
            "use AgentRawObservationTotals for whole-window totals",
            self.file_run,
        )

    def test_municipality_leaders_has_unique_grain_and_exact_contract(self):
        text = self.municipality_leaders
        self.assertEqual(text.count("| summarize"), 1)
        self.assertEqual(text.count("\n          by MunicipalityID"), 1)
        self.assertEqual(text.count("DonationObservationSummaryForAgent"), 2)
        self.assertEqual(text.count("| take 1"), 2)
        self.assertEqual(text.count("toscalar("), 2)
        self.assertNotRegex(text, r"(?im)^\s*\|?\s*union\b")
        self.assertNotIn("LeaderMetric", text)
        self.assertIn(
            "| where MunicipalityID == CountLeaderId "
            "or MunicipalityID == AmountLeaderId",
            text,
        )
        self.assertIn(
            "IsCountLeader = MunicipalityID == CountLeaderId",
            text,
        )
        self.assertIn(
            "IsAmountLeader = MunicipalityID == AmountLeaderId",
            text,
        )
        project = text.rsplit("| project", 1)[1].split("| order by", 1)[0]
        fields = [
            line.strip().rstrip(",")
            for line in project.splitlines()
            if line.strip()
        ]
        self.assertEqual(
            fields,
            [
                "MunicipalityID",
                "IsCountLeader",
                "IsAmountLeader",
                "RawObservationCount",
                "RawObservedAmountYen",
                "RequestedStartUtc",
                "RequestedEndUtc",
                "WindowIsValid",
                "Scope",
                "SourceSystem",
                "SourceObject",
                "CountUnit",
                "AmountUnit",
                "RawDuplicateCaveat",
                "TimeZoneNotice",
            ],
        )

    def test_unique_leader_fixtures_cover_same_different_and_ties(self):
        same_winner = local_unique_leaders(
            [("B", 2, 20), ("A", 4, 40), ("A", 1, 5)]
        )
        self.assertEqual(
            same_winner,
            [
                {
                    "MunicipalityID": "A",
                    "IsCountLeader": True,
                    "IsAmountLeader": True,
                    "RawObservationCount": 5,
                    "RawObservedAmountYen": 45,
                }
            ],
        )
        different_winners = local_unique_leaders(
            [("A", 8, 10), ("B", 2, 50), ("A", 1, 3)]
        )
        self.assertEqual(
            different_winners,
            [
                {
                    "MunicipalityID": "A",
                    "IsCountLeader": True,
                    "IsAmountLeader": False,
                    "RawObservationCount": 9,
                    "RawObservedAmountYen": 13,
                },
                {
                    "MunicipalityID": "B",
                    "IsCountLeader": False,
                    "IsAmountLeader": True,
                    "RawObservationCount": 2,
                    "RawObservedAmountYen": 50,
                },
            ],
        )
        tied = local_unique_leaders(
            [("B", 4, 100), ("A", 4, 100), ("C", 1, 20)]
        )
        self.assertEqual(
            tied,
            [
                {
                    "MunicipalityID": "A",
                    "IsCountLeader": True,
                    "IsAmountLeader": True,
                    "RawObservationCount": 4,
                    "RawObservedAmountYen": 100,
                }
            ],
        )
        self.assertEqual(local_unique_leaders([]), [])

    def test_unique_leader_sorting_uses_only_primary_metric_then_id(self):
        text = self.municipality_leaders
        self.assertRegex(
            text,
            re.compile(
                r"RawObservationCount desc, MunicipalityID asc"
            ),
        )
        self.assertRegex(
            text,
            re.compile(
                r"RawObservedAmountYen desc, MunicipalityID asc"
            ),
        )
        self.assertNotRegex(
            text,
            r"RawObservationCount desc,\s*RawObservedAmountYen",
        )
        self.assertNotRegex(
            text,
            r"RawObservedAmountYen desc,\s*RawObservationCount",
        )

    def test_no_hardcoded_answers_questions_or_cross_source_instructions(self):
        combined = (
            self.totals
            + self.leaders
            + self.file_run
            + self.municipality_leaders
        )
        self.assertNotRegex(combined, r"\b\d{5,}\b")
        self.assertNotRegex(combined, r"datetime\(\d{4}-")
        self.assertNotRegex(combined, r"(?i)\b(question|answer|sql|gql|next)\b")
        self.assertNotRegex(combined, r"(?i)\b(unique|dedup)\s*(count|amount|metric)")
        self.assertNotIn("MunicipalityName", combined)


if __name__ == "__main__":
    unittest.main()
