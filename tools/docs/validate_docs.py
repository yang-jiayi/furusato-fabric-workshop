"""Validate the built v2.7.0 Office deliverables and the data validation checklist.

    python tools/docs/validate_docs.py [--out DIR] [--check-urls] [--json]

Exits non-zero when any FAIL finding is produced.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from furusato_docs import (  # noqa: E402
    docx_kit,
    guide_content,
    guide_handson,
    oox as oox_module,
    quality,
    reproducible,
    validators,
)
from furusato_docs.context import load_context, repo_root  # noqa: E402
from furusato_docs.console import use_utf8_streams  # noqa: E402
from furusato_docs.deliverables import deliverable_names, validate_edition  # noqa: E402
from furusato_docs.facts import compute_facts  # noqa: E402
from furusato_docs.oox import StyleCarrier  # noqa: E402
from furusato_docs.notebook_payload import decode_notebook_payload  # noqa: E402
from furusato_docs.parameters import build_parameter_rows, format_default  # noqa: E402
from furusato_docs.publication import (  # noqa: E402
    PublicationError,
    check_directory,
    display_path,
    outside_repo,
    public_word_errors,
    require_public_edition,
)
from furusato_docs.tests10 import build_tests  # noqa: E402
from furusato_docs.typography import ascii_parentheses  # noqa: E402
from furusato_docs.validators import Report, check_forbidden  # noqa: E402


def _yen(value: int) -> str:
    return f"{value:,} 円"


def _num(value: int) -> str:
    return f"{value:,}"


def _plain(text: str) -> str:
    """Backticks mark inline-code spans in the source strings; Word renders them as style."""
    return ascii_parentheses(text.replace("`", ""))


def _duplicate_wording(facts) -> list[tuple[str, str]]:
    """The duplicated day must state the two quantities separately, never conflated."""
    calendar = facts.observation.calendar
    return [
        ("duplicate day", calendar.duplicate_day),
        ("duplicate day raw rows", _num(calendar.duplicate_day_raw_rows)),
        ("duplicate day dedup rows", _num(calendar.duplicate_day_dedup_rows)),
        ("extra duplicate rows", _num(calendar.duplicate_extra_rows_on_day)),
        ("duplicate group rows", _num(calendar.duplicate_group_rows_on_day)),
        ("duplicated EventIDs", _num(calendar.duplicate_event_ids_on_day)),
    ]


def _assert_duplicate_distinction(text: str, facts, report: Report, *, check: str) -> None:
    calendar = facts.observation.calendar
    validators.check_required(text, _duplicate_wording(facts), report, check=check)
    conflated = [
        phrase
        for phrase in (
            f"重複 {_num(calendar.duplicate_group_rows_on_day)} 行を含む",
            f"うち重複 {_num(calendar.duplicate_group_rows_on_day)} 行",
            f"重複 {_num(calendar.duplicate_group_rows_on_day)} 件",
        )
        if phrase in text
    ]
    if conflated:
        report.fail(f"{check}.conflation", f"the group-row count is presented as extra duplicates: {conflated}")
    else:
        report.ok(
            f"{check}.conflation",
            f"extra duplicate rows ({calendar.duplicate_extra_rows_on_day}) and duplicate-group rows "
            f"({calendar.duplicate_group_rows_on_day}) are stated as distinct quantities",
        )


def _calendar_expectations(facts) -> list[tuple[str, str]]:
    """Values the daily-distribution documentation must state verbatim."""
    calendar = facts.observation.calendar
    return [
        ("utc day count", str(calendar.utc_day_count)),
        ("first utc day", calendar.first_utc_day),
        ("last utc day", calendar.last_utc_day),
        ("min rows per day", _num(calendar.min_rows)),
        ("max rows per day", _num(calendar.max_rows)),
        ("min rows day", calendar.min_rows_day),
        ("max rows day", calendar.max_rows_day),
        ("dedup max rows per day", _num(calendar.dedup_max_rows)),
        ("jst day count", str(calendar.jst_day_count)),
        ("jst rollover day", calendar.last_jst_day),
        ("jst rollover rows", _num(calendar.jst_rollover_rows)),
        ("jst rollover start", calendar.jst_rollover_from_utc),
        ("jst rollover end", calendar.jst_rollover_to_utc),
    ]


def validate_guide(
    root: Path, out_dir: Path, context, facts, edition: str = "", *,
    public_documents_only: bool = False,
) -> Report:
    path = out_dir / deliverable_names(context.version, edition).participant
    report = Report(target=display_path(path, root))
    if not path.is_file():
        report.fail("file.exists", "participant guide not found")
        return report
    result = validators.check_document(
        path,
        report,
        version=context.version,
        expected_title_fragment="Fabric IQ Ontology Workshop Furusato Participant",
    )
    text = result["text"]
    if public_documents_only:
        problems = public_word_errors(path, deliverable_names(context.version, edition))
        if problems:
            report.fail("publication.guideContent", "; ".join(problems))
        else:
            report.ok("publication.guideContent", "public scope, in-guide records and parameter references")
        check_in_guide_companions(text, context, build_tests(context, facts), report)
    check_forbidden(text, report)
    quality.check_guide_content(text, context, facts, report, path)
    quality.check_data_agent_practice(context, text, report)
    report.stats.update(quality.check_layout(path, report))
    _check_guide_hyperlinks(path, report)
    _check_guide_runtime_and_shapes(text, context, report)

    expected = context.expected
    increment = context.expected_increment
    static = facts.static
    required = [
        ("version", f"v{context.version}"),
        ("donation rows", _num(expected["donationRows"])),
        ("donation total", _yen(expected["totalDonationAmountYen"])),
        ("node total", _num(expected["nodeTotal"])),
        ("edge total", _num(expected["edgeTotal"])),
        ("increment raw", _num(increment["rawRows"])),
        ("increment unique", _num(increment["uniqueEventIds"])),
        ("increment duplicates", _num(increment["duplicateEventIds"])),
        ("window start", increment["observationWindowUtc"]["from"]),
        ("window end", increment["observationWindowUtc"]["to"]),
        ("published file003", increment["publishedAtUtc"][2]),
        ("metadata objects", _num(context.metadata_object_count)),
        ("top municipality", static.top_municipality_id),
        ("tokyo received", _num(static.tokyo_received_count)),
        ("tokyo resident", _num(static.tokyo_resident_count)),
    ]
    validators.check_required(text, required, report, check="content.expectedValues")

    for entity in context.entities:
        if entity.name not in text:
            report.fail("content.entities", f"{entity.name} missing from the guide")
            break
    else:
        report.ok("content.entities", f"all {len(context.entities)} entity types documented")

    for relationship in context.relationships:
        if relationship.name not in text:
            report.fail("content.relationships", f"{relationship.name} missing from the guide")
            break
    else:
        report.ok("content.relationships", f"all {len(context.relationships)} relationship types documented")

    missing_parameters: list[str] = []
    for key in sorted(context.notebooks):
        for row in build_parameter_rows(context, key):
            if row[0] not in text:
                missing_parameters.append(f"{key}.{row[0]}")
    if missing_parameters:
        report.fail("content.parameters", f"parameters missing from the guide: {missing_parameters}")
    else:
        report.ok(
            "content.parameters",
            f"all {sum(len(build_parameter_rows(context, key)) for key in context.notebooks)} "
            "notebook parameters documented",
        )

    for key in sorted(context.notebooks):
        notebook = context.notebooks[key]
        if notebook.sha256 not in text:
            report.fail("content.notebookHashes", f"{notebook.name} SHA-256 missing")
            break
    else:
        report.ok("content.notebookHashes", "every notebook SHA-256 is quoted in appendix B")

    instructions = context.guide_agent_instructions.strip().splitlines()
    if context.guide_agent_instructions.strip() == context.guide_agent_stage_config["aiInstructions"].strip():
        report.ok("content.agentInstructionParity", "agent-instructions.txt matches the shipped bundle")
    else:
        report.fail(
            "content.agentInstructionParity",
            "agent-instructions.txt and the provisioning bundle disagree; the guide quotes the .txt",
        )
    missing_instruction_lines = [
        line
        for line in instructions
        if line.strip() and line.strip() not in text and _plain(line.strip()) not in text
    ]
    if missing_instruction_lines:
        report.fail(
            "content.agentInstructions",
            f"{len(missing_instruction_lines)} instruction lines missing, first: {missing_instruction_lines[0]!r}",
        )
    else:
        report.ok("content.agentInstructions", "the final agent instructions are reproduced verbatim")

    for fewshot in context.agent_fewshots:
        if ascii_parentheses(fewshot["question"]) not in ascii_parentheses(text):
            report.fail("content.fewShots", f"few-shot question missing: {fewshot['question'][:40]}")
            break
    else:
        report.ok("content.fewShots", f"all {len(context.agent_fewshots)} Lakehouse few-shots documented")

    for source_type in context.agent_sources:
        description = context.guide_source_text(source_type)[0].strip()
        if description and _plain(description) not in text and description not in text:
            report.fail("content.sourceDescriptions", f"{source_type} description missing from the guide")
            break
    else:
        report.ok(
            "content.sourceDescriptions",
            f"all {len(context.agent_sources)} Data Agent source descriptions are reproduced verbatim",
        )

    for source_type in ("lakehouse_tables", "kusto"):
        instructions_text = context.guide_source_text(source_type)[1].strip()
        missing = [
            line
            for line in instructions_text.splitlines()
            if line.strip() and line.strip() not in text and _plain(line.strip()) not in text
        ]
        if missing:
            report.fail(
                "content.sourceInstructions",
                f"{source_type}: {len(missing)} instruction lines missing, first: {missing[0][:70]!r}",
            )
            break
    else:
        report.ok("content.sourceInstructions", "Lakehouse and Eventhouse source instructions are reproduced verbatim")

    variables = context.variable_library.get("variables", [])
    missing_variables = [item["name"] for item in variables if item["name"] not in text]
    if missing_variables:
        report.fail("content.variableLibrary", f"variables missing from the guide: {missing_variables}")
    elif variables:
        report.ok("content.variableLibrary", f"all {len(variables)} Variable Library variables documented")

    pipeline_parameters = list(context.pipeline["properties"]["parameters"])
    missing_pipeline = [name for name in pipeline_parameters if name not in text]
    if missing_pipeline:
        report.fail("content.pipelineParameters", f"pipeline parameters missing: {missing_pipeline}")
    else:
        report.ok("content.pipelineParameters", f"all {len(pipeline_parameters)} pipeline parameters documented")

    validators.check_required(text, _calendar_expectations(facts), report, check="content.dailyDistribution")
    _assert_duplicate_distinction(text, facts, report, check="content.duplicateWording")
    calendar = facts.observation.calendar
    missing_days = [
        entry["date"]
        for entry in calendar.utc_days
        if entry["date"] not in text or _num(entry["rows"]) not in text
    ]
    if missing_days:
        report.fail("content.dailyTable", f"{len(missing_days)} UTC days missing from the guide: {missing_days[:5]}")
    else:
        report.ok(
            "content.dailyTable",
            f"all {calendar.utc_day_count} UTC days and their row counts are tabulated in the guide",
        )
    if context.expected_increment["publishedAtUtc"][2] in text:
        report.ok("content.jstBoundary", "the September publication timestamp is stated as expected behaviour")
    else:
        report.fail("content.jstBoundary", "the file 003 publication timestamp is missing")

    experimental = context.guide_agent_stage_config.get("experimental", {})
    flag = "true" if experimental.get("codeInterpreterEnabled") else "false"
    if f"codeInterpreterEnabled = {flag}" in text or f"codeInterpreterEnabled = {flag}" in _plain(text):
        report.ok(
            "content.codeInterpreterBoundary",
            f"the guide states the selected profile value codeInterpreterEnabled={flag}",
        )
    else:
        report.fail(
            "content.codeInterpreterBoundary",
            f"the guide does not state the shipped Core value codeInterpreterEnabled={flag}",
        )

    diagram_captions = ["図 " + str(index) for index in range(1, 7)]
    if all(caption in text for caption in diagram_captions):
        report.ok("content.figures", "figure numbering starts at 1 and is continuous")

    # Anti-cache guarantee: every diagram the guide embeds must be the byte-exact
    # file currently on disk, so a regenerated diagram can never be missed.
    import hashlib as _hashlib
    import zipfile as _zipfile

    with _zipfile.ZipFile(path) as archive:
        embedded = {
            name: _hashlib.sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if name.startswith("word/media/")
        }
    embedded_digests = list(embedded.values())
    stale: list[str] = []
    for key, variants in sorted(context.diagrams.items()):
        if context.is_unified_guide and key == "system-data-flow":
            continue
        source = variants.get("png") or next(iter(variants.values()))
        digest = _hashlib.sha256(source.read_bytes()).hexdigest()
        occurrences = embedded_digests.count(digest)
        if occurrences != 1:
            stale.append(f"{key} ({'missing/stale' if occurrences == 0 else f'{occurrences} copies'})")
    if stale:
        report.fail(
            "content.diagramFreshness",
            f"the guide does not embed the current diagram bytes for: {stale}",
        )
    else:
        report.ok(
            "content.diagramFreshness",
            f"all {len(context.diagrams) - int(context.is_unified_guide)} required diagrams are byte-identical to docs/assets/v{context.version}",
        )

    heading_ones = [text_value for name, text_value in result["headings"] if name == "Heading1"]
    report.stats["chapters"] = heading_ones
    if len(heading_ones) >= 24:
        report.ok("structure.chapters", f"{len(heading_ones)} top-level chapters/appendices")
    else:
        report.fail("structure.chapters", f"only {len(heading_ones)} top-level headings")

    return report


def check_in_guide_companions(text: str, context, tests, report: Report) -> None:
    """The public guide must retain the rubric/specifications omitted as separate files."""
    if [test.number for test in tests] != list(range(1, 11)):
        report.fail("publication.tenQuestions", "the public guide requires the complete ten-question rubric")
        return
    plain = _plain(text)
    for test in tests:
        section = quality._section(
            plain, f"17.{test.number} {test.test_id}", f"17.{test.number + 1} "
            if test.number < 10 else "17.11 ",
        )
        values = [
            ("question", test.question), ("purpose", test.purpose), ("route", test.route),
            ("query shape", test.query_shape), ("expected answer", test.expected), ("trap", test.trap),
            *[(f"evidence {index}", value) for index, value in enumerate(test.evidence, 1)],
            *[(f"criterion {index}", value) for index, value in enumerate(test.pass_criteria, 1)],
        ]
        validators.check_required(
            section, [(label, _plain(value)) for label, value in values], report,
            check=f"publication.rubric.{test.test_id}",
        )
    normalized = re.sub(r"\s+", " ", plain)
    values = [
        (f"{key}.{row[0]}.{column}", re.sub(r"\s+", " ", _plain(str(value))))
        for key in sorted(context.notebooks)
        for row in build_parameter_rows(context, key)
        for column, value in enumerate(row)
        if str(value).strip()
    ]
    validators.check_required(normalized, values, report, check="publication.parameterSpecifications")


def _check_guide_hyperlinks(path: Path, report: Report) -> None:
    """Every external URL printed in the guide must be a real, clickable link.

    A reference table whose URLs are plain runs forces a reader to retype them and
    produces a PDF with nothing to click. Word needs a ``w:hyperlink`` bound to an
    external relationship, so both halves are checked: every URL in the text has a
    relationship, and every relationship is reachable from a hyperlink element.
    """
    import zipfile

    with zipfile.ZipFile(path) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
        rels = archive.read("word/_rels/document.xml.rels").decode("utf-8")

    external = {
        rid: target
        for rid, target in re.findall(r'Id="([^"]+)"[^>]*Target="(https?://[^"]+)"', rels)
    }
    linked = set(re.findall(r'<w:hyperlink[^>]*r:id="([^"]+)"', document))
    printed = set(re.findall(r"https?://[^\s<>\"、。（）「」]+", re.sub(r"<[^>]+>", " ", document)))

    unlinked = sorted(printed - set(external.values()))
    orphaned = sorted(set(external) - linked)
    if unlinked or orphaned:
        report.fail(
            "guide.hyperlinks",
            f"{len(unlinked)} URL(s) printed without a hyperlink relationship {unlinked[:3]}; "
            f"{len(orphaned)} unreferenced relationship(s)",
        )
    else:
        report.ok(
            "guide.hyperlinks",
            f"all {len(external)} external URLs are clickable Word hyperlinks",
        )


def _check_guide_runtime_and_shapes(text: str, context, report: Report) -> None:
    """The guide must state the same shape count and the same runtime rule.

    Both are numbers or rules a participant acts on directly: how many KQL
    patterns to expect inside the Kusto source instructions, and which runtime a
    Core verdict may be recorded from. A guide that disagrees with the runtime it
    ships sends the participant to configure something else.
    """
    if context.is_unified_guide:
        shots = context.guide_kql_fewshots
        missing = [
            shot["question"] for shot in shots
            if _plain(shot["question"]) not in text or _plain(shot["query"]) not in text
        ]
        if len(shots) == 3 and not missing and _plain("3 件（KQL、固定済み JSON）") in text:
            report.ok("content.kqlFewShots", "all three sealed helper examples and their count are reproduced")
        else:
            report.fail("content.kqlFewShots", f"count={len(shots)}, missing={missing}")
    else:
        shapes = context.guide_source_text("kusto")[1].count(
            "summarize sum(ObservationCount)"
        )
        if _plain(f"KQL の例パターン {shapes} 件") in text:
            report.ok("content.kqlShapeCount", f"the guide states the shipped {shapes} KQL query shapes")
        else:
            report.fail("content.kqlShapeCount", f"the guide does not state the shipped KQL shape count ({shapes})")

    agent = context.workspace_contract["dataAgent"]
    core = agent["coreRuntime"]
    comparison = agent["comparisonRuntime"]
    rules = [
        ("Core runtime is mandatory", f"Core 記録は {core} runtime で実施しなければなりません"),
        ("comparison runtime is excluded", f"{comparison} runtime は比較専用"),
        ("comparison cannot pass Core", f"{comparison} でしか通らなかった問いは Core としては不合格"),
    ]
    missing = [label for label, needle in rules if _plain(needle) not in text]
    if missing:
        report.fail("content.coreRuntimeRule", f"the guide does not state: {missing}")
    else:
        report.ok(
            "content.coreRuntimeRule",
            f"the guide requires {core} for Core verdicts and confines {comparison} to comparison",
        )


def validate_validation_doc(root: Path, out_dir: Path, context, facts, tests, edition: str = "") -> Report:
    path = out_dir / deliverable_names(context.version, edition).validation
    report = Report(target=str(path.relative_to(root)))
    if not path.is_file():
        report.fail("file.exists", "validation document not found")
        return report
    result = validators.check_document(
        path,
        report,
        version=context.version,
        expected_title_fragment="Furusato Data Agent Validation 10",
    )
    text = result["text"]
    check_forbidden(text, report)
    quality.check_validation_doc_content(text, tests, report, path)
    report.stats.update(quality.check_layout(path, report))

    for test in tests:
        for field_name, value in (
            ("question", test.question),
            ("purpose", test.purpose),
            ("route", test.route),
            ("expected", test.expected),
            ("trap", test.trap),
        ):
            if _plain(value) not in text:
                report.fail("content.tests", f"{test.test_id} {field_name} missing")
                break
        else:
            continue
        break
    else:
        report.ok("content.tests", f"all {len(tests)} tests carry question, purpose, route, expectation and trap")

    for value in ("PASS", "FAIL", "UNCLEAR", "EXECUTION_ERROR"):
        if value not in text:
            report.fail("content.resultValues", f"{value} missing")
            break
    else:
        report.ok("content.resultValues", "PASS / FAIL / UNCLEAR / EXECUTION_ERROR present")

    static = facts.static
    observation = facts.observation
    required = [
        ("static rows", _num(static.donation_rows)),
        ("static total", _yen(static.donation_total_yen)),
        ("top municipality id", static.top_municipality_id),
        ("top municipality count", _num(static.top_municipality_count)),
        ("top municipality amount", _yen(static.top_municipality_total_yen)),
        ("T04 prefecture municipalities", str(static.t04_municipality_count)),
        ("tokyo received", _num(static.tokyo_received_count)),
        ("tokyo resident", _num(static.tokyo_resident_count)),
        ("sample donor", static.sample_donation["DonorId"]),
        ("sample gift", static.sample_donation["GiftId"]),
        ("sample supplier", static.sample_donation["SupplierIds"][0]),
        ("observed count", _num(observation.top_observed_count)),
        ("observed amount", _yen(observation.top_observed_amount_yen)),
        ("unique event ids", _num(observation.unique_event_ids)),
        ("raw rows", _num(observation.raw_rows)),
        ("sum refusal", _num(static.donation_rows + observation.raw_rows)),
    ]
    validators.check_required(text, required, report, check="content.expectedValues")

    for pattern in ("SELECT ", "summarize ", "MATCH ", "| where "):
        if pattern in text:
            report.fail("content.heldOut", f"query text leaked into the record: {pattern!r}")
            break
    else:
        report.ok("content.heldOut", "no SQL/KQL/GQL query text is given to the participant")

    test08 = next(test for test in tests if test.number == 8)
    if "この自治体" in test08.question:
        report.fail("content.t08Unbound", "T08 still carries an unbound demonstrative that invites an ID clarification")
    elif "95,000" in test08.question and "総寄付件数" in test08.question:
        report.ok(
            "content.t08Unbound",
            "T08 asserts the 95,000 total explicitly, so the refusal tests the grain boundary rather than an ID",
        )
    else:
        report.fail("content.t08Unbound", "T08 no longer states the asserted 95,000 total")

    test09 = next(test for test in tests if test.number == 9)
    sources_in_route = sum(token in test09.route for token in ("Eventhouse", "Lakehouse", "Ontology"))
    if "3 ソース" in test09.purpose and sources_in_route == 3 and "MunicipalityId" in test09.purpose:
        report.ok(
            "content.t09SourceCount",
            "T09 states three separately queried sources composed by MunicipalityId, matching its route",
        )
    else:
        report.fail(
            "content.t09SourceCount",
            f"T09 purpose and route disagree (route names {sources_in_route} sources)",
        )

    # The record sheet is where a grader decides what "passed" means, so it has to
    # say which runtime the verdict belongs to. A sheet that offers a free
    # Standard/Preview choice lets a Standard-only pass be recorded as a Core pass.
    core_runtime = context.workspace_contract["dataAgent"]["coreRuntime"]
    comparison_runtime = context.workspace_contract["dataAgent"]["comparisonRuntime"]
    runtime_rules = [
        (f"Core {core_runtime} fixed", f"Core のランタイム（{core_runtime} 固定）"),
        (f"{comparison_runtime} comparison field", f"{comparison_runtime} runtime の比較実施"),
        (f"per-test {comparison_runtime} column", f"{comparison_runtime} runtime での比較"),
        ("verdict bound to Core runtime", f"判定（{core_runtime} runtime"),
        ("comparison excluded from the verdict", "Core の判定には使わない"),
    ]
    missing_runtime = [label for label, needle in runtime_rules if _plain(needle) not in text]
    if missing_runtime:
        report.fail("content.coreRuntimeRule", f"the record sheet does not state: {missing_runtime}")
    else:
        report.ok(
            "content.coreRuntimeRule",
            f"the record sheet fixes Core to {core_runtime} and keeps {comparison_runtime} "
            "in a separate comparison field",
        )

    return report


def validate_workbook(root: Path, out_dir: Path, context, facts, edition: str = "") -> Report:
    path = out_dir / deliverable_names(context.version, edition).workbook
    report = Report(target=str(path.relative_to(root)))
    if not path.is_file():
        report.fail("file.exists", "workbook not found")
        return report
    result = validators.check_workbook(path, report)
    text = result["text"]
    check_forbidden(text, report)
    quality.check_workbook_presentation(path, context, report)
    quality.check_workbook_v3(path, context, report)

    workbook = result["workbook"]
    expected_sheets = [
        "Overview",
        "NB01",
        "NB02",
        "NB03",
        "NB04",
        "NB05",
        "Parameters",
        "Parameters_Core",
        "Contracts",
        "IncrementDaily",
    ]
    actual = [sheet.title for sheet in workbook.worksheets]
    if actual == expected_sheets:
        report.ok("workbook.sheets", f"{len(actual)} sheets in the expected order")
    else:
        report.fail("workbook.sheets", f"unexpected sheets: {actual}")

    # "Fit to one page wide" shrinks without a floor, so a wide reference sheet can
    # print 10 pt body text at 5 pt. These sheets therefore carry an explicit scale.
    readable = ("Overview", "NB01", "NB02", "NB03", "NB04", "NB05", "Parameters", "Parameters_Core")
    unreadable = []
    for title in readable:
        sheet = workbook[title]
        scale = sheet.page_setup.scale
        fit = bool(getattr(sheet.sheet_properties.pageSetUpPr, "fitToPage", False))
        if fit or scale is None or int(scale) < MIN_PRINT_SCALE:
            unreadable.append(f"{title}: scale={scale} fitToPage={fit}")
    if unreadable:
        report.fail(
            "workbook.printScale",
            f"sheets that can shrink below {MIN_PRINT_SCALE}% of a 10 pt body: {unreadable}",
        )
    else:
        report.ok(
            "workbook.printScale",
            f"all {len(readable)} reference sheets print at {MIN_PRINT_SCALE}% or larger "
            f"(10 pt body stays at least {10 * MIN_PRINT_SCALE / 100:.0f} pt)",
        )

    # A wide reference sheet runs past one page across at a readable scale, so the
    # identity columns have to repeat or page 2 is a wall of unlabelled values.
    # Excel prints a title column that lies inside the print area once on page 1
    # and repeats it afterwards, so overlapping the area start is correct here.
    required_titles = {
        "Overview": "A:A",
        "NB01": "A:B",
        "NB02": "A:B",
        "NB03": "A:B",
        "NB04": "A:B",
        "NB05": "A:B",
        "Parameters": "A:C",
        "Parameters_Core": "A:A",
    }
    missing = []
    for title, columns in required_titles.items():
        declared = (workbook[title].print_title_cols or "").replace("$", "")
        if declared != columns:
            missing.append(f"{title}: {declared or 'none'} (want {columns})")
    if missing:
        report.fail("workbook.printTitleColumns", f"identity columns do not repeat: {missing}")
    else:
        report.ok(
            "workbook.printTitleColumns",
            f"all {len(required_titles)} tiled sheets repeat their identity columns on every printed page",
        )

    # A2 on Parameters_Core is a full sentence. Excel only spills text into the
    # next cell while it stays empty, and the printed page cuts the spill at the
    # page boundary, so the subtitle has to own a merged box instead.
    core = workbook["Parameters_Core"]
    merged = {str(item) for item in core.merged_cells.ranges}
    if "A2:H2" in merged:
        report.ok("workbook.coreSubtitleMerged", "Parameters_Core A2 spans the used width, so the subtitle prints whole")
    else:
        report.fail("workbook.coreSubtitleMerged", f"Parameters_Core A2 is not merged across the sheet: {sorted(merged)}")

    # Column A on the notebook sheets carries the "File SHA-256" label above a
    # column of one- and two-digit cell numbers. Sized for the numbers it clipped
    # the label, which is the one string on the sheet a reader needs to find.
    narrow = [
        f"{title}: {workbook[title].column_dimensions['A'].width}"
        for title in ("NB01", "NB02", "NB03", "NB04", "NB05")
        if (workbook[title].column_dimensions["A"].width or 0) < MIN_NOTEBOOK_LABEL_WIDTH
    ]
    if narrow:
        report.fail("workbook.notebookLabelColumn", f"column A too narrow for 'File SHA-256': {narrow}")
    else:
        report.ok(
            "workbook.notebookLabelColumn",
            f"all 5 notebook sheets give column A at least {MIN_NOTEBOOK_LABEL_WIDTH} characters",
        )

    parameters_core = workbook["Parameters_Core"]
    header = str(parameters_core.oddHeader.left.text or "")
    if str(parameters_core["A1"].value) in header and str(parameters_core["A2"].value) in header:
        report.ok(
            "workbook.coreTitleRowsPrinted",
            "Parameters_Core prints its title and scope note in the page header, so every tile carries them",
        )
    else:
        report.fail(
            "workbook.coreTitleRowsPrinted",
            "Parameters_Core does not carry its title and scope note in the page header",
        )

    _check_workbook_repair_free(path, report)

    for key in sorted(context.notebooks):
        notebook = context.notebooks[key]
        sheet = workbook[key.replace("Notebook_", "NB")]
        if sheet["B3"].value != notebook.sha256:
            report.fail("workbook.notebookHash", f"{notebook.name} file hash mismatch")
            break
        rows = list(sheet.iter_rows(min_row=6, values_only=True))
        if len(rows) != len(notebook.cells):
            report.fail("workbook.cellCount", f"{notebook.name}: {len(rows)} rows vs {len(notebook.cells)} cells")
            break
        mismatch = [
            (row[0], row[7])
            for row, cell in zip(rows, notebook.cells)
            if row[7] != cell.source_sha256 or row[5] != cell.source_lines
        ]
        if mismatch:
            report.fail("workbook.cellHash", f"{notebook.name}: {len(mismatch)} cell rows disagree")
            break
    else:
        report.ok(
            "workbook.cellInventory",
            "every notebook file hash, cell count, source line count and cell hash matches the shipped notebook",
        )

    parameters = workbook["Parameters"]
    rows = list(parameters.iter_rows(min_row=5, values_only=True))
    expected_rows: list[tuple] = []
    for key in sorted(context.notebooks):
        notebook = context.notebooks[key]
        for values in build_parameter_rows(context, key):
            expected_rows.append((notebook.name, values[0], values[2]))
    actual_rows = [(row[0], row[2], row[4]) for row in rows]
    if actual_rows == expected_rows:
        report.ok("workbook.parameters", f"{len(expected_rows)} parameter rows match the notebooks exactly")
    else:
        report.fail("workbook.parameters", "parameter sheet disagrees with the notebook parameter cells")

    contracts = workbook["Contracts"]
    contract_values = {row[0]: row[1] for row in contracts.iter_rows(min_row=5, values_only=True) if row[0]}
    required_contracts = {
        "Workshop version": context.version,
        "配布 CSV 総数": context.csv_count,
        "Entity types": context.ontology_contract["entityTypes"],
        "Relationship types": context.ontology_contract["relationshipTypes"],
        "Metadata objects": context.metadata_object_count,
        "Increment raw rows": context.expected_increment["rawRows"],
        "Increment unique EventID": context.expected_increment["uniqueEventIds"],
        "Increment duplicate EventID": context.expected_increment["duplicateEventIds"],
    }
    mismatched = {
        name: (contract_values.get(name), value)
        for name, value in required_contracts.items()
        if contract_values.get(name) != value
    }
    if mismatched:
        report.fail("workbook.contracts", f"contract mismatches: {mismatched}")
    else:
        report.ok("workbook.contracts", f"all {len(required_contracts)} key contracts are exact")

    if "2026-08-01T00:02:47Z" in text and "2026-08-31T23:58:20Z" in text:
        report.ok("workbook.window", "August 2026 observation window recorded")
    else:
        report.fail("workbook.window", "observation window missing from the Contracts sheet")

    calendar = facts.observation.calendar
    daily = workbook["IncrementDaily"]
    first_data_row = 7
    day_rows = [
        row
        for row in daily.iter_rows(
            min_row=first_data_row, max_row=first_data_row - 1 + calendar.utc_day_count, values_only=True
        )
    ]
    expected_days = [(entry["date"], entry["rows"], entry["amount"], entry["dedupRows"]) for entry in calendar.utc_days]
    actual_days = [(row[0], row[1], row[2], row[3]) for row in day_rows]
    if actual_days == expected_days:
        report.ok(
            "workbook.dailyDistribution",
            f"{calendar.utc_day_count} UTC days, {calendar.min_rows}-{calendar.max_rows} raw rows per day, exact",
        )
    else:
        report.fail("workbook.dailyDistribution", "the IncrementDaily sheet disagrees with the packaged CSVs")

    _assert_duplicate_distinction(text, facts, report, check="workbook.duplicateWording")

    if context.expected_increment["publishedAtUtc"][2] in text and calendar.last_jst_day in text:
        report.ok("workbook.jstBoundary", "the September publication timestamp and JST rollover are recorded")
    else:
        report.fail("workbook.jstBoundary", "the JST rollover note is missing from the workbook")

    return report


def validate_checklist(root: Path, context, facts) -> Report:
    path = root / "docs" / "data-validation-checklist.md"
    report = Report(target=str(path.relative_to(root)))
    if not path.is_file():
        report.fail("file.exists", "checklist not found")
        return report
    text = path.read_text(encoding="utf-8")
    check_forbidden(text, report)

    expected = context.expected
    increment = context.expected_increment
    static = facts.static
    observation = facts.observation
    required = [
        ("node total", f"{expected['nodeTotal']:,}"),
        ("edge total", f"{expected['edgeTotal']:,}"),
        ("donation total", f"{expected['totalDonationAmountYen']:,}"),
        ("raw rows", f"{increment['rawRows']:,}"),
        ("unique event ids", f"{increment['uniqueEventIds']:,}"),
        ("duplicate event ids", str(increment["duplicateEventIds"])),
        ("raw amount", f"{increment['rawAmountYen']:,}"),
        ("dedup amount", f"{increment['deduplicatedAmountYen']:,}"),
        ("window start", increment["observationWindowUtc"]["from"]),
        ("window end", increment["observationWindowUtc"]["to"]),
        ("published file003", increment["publishedAtUtc"][2]),
        ("metadata objects", str(context.metadata_object_count)),
        ("top municipality", static.top_municipality_id),
        ("observed top count", f"{observation.top_observed_count:,}"),
        ("version", context.version),
    ]
    validators.check_required(text, required, report, check="checklist.expectedValues")

    for table in expected["outputTableCounts"]:
        if table not in text:
            report.fail("checklist.tables", f"{table} missing")
            break
    else:
        report.ok("checklist.tables", f"all {len(expected['outputTableCounts'])} output tables listed")

    for entry in context.increment_files:
        if entry["file"] not in text:
            report.fail("checklist.incrementFiles", f"{entry['file']} missing")
            break
    else:
        report.ok("checklist.incrementFiles", "all increment files listed")

    validators.check_required(text, _calendar_expectations(facts), report, check="checklist.dailyDistribution")
    _assert_duplicate_distinction(text, facts, report, check="checklist.duplicateWording")
    calendar = observation.calendar
    missing_days = [
        entry["date"]
        for entry in calendar.utc_days
        if entry["date"] not in text or f"{entry['rows']:,}".replace(",", "") not in text.replace(",", "")
    ]
    if missing_days:
        report.fail("checklist.dailyTable", f"UTC days missing from the checklist: {missing_days[:5]}")
    else:
        report.ok(
            "checklist.dailyTable",
            f"all {calendar.utc_day_count} UTC days and their row counts are tabulated in the checklist",
        )

    quality_items = [
        ("kql object count", "5 個だけ"),
        ("materialized view", "DonationObservationSummaryForAgent"),
        ("single ingestion", "1 本目は第 12.4 節のゲートで取り込み済み"),
        ("fail closed message", "Count mismatch for timeseriesProperties: Ontology has 0, manifest expects 1"),
        ("fail closed zero", "1 件も登録されません"),
        ("precondition 97", "10 + 72 + 0 + 15 = **97**"),
        ("required 98", "10 + 72 + 1 + 15 = **98**"),
        ("observed pairs", "1,410 通り"),
        ("raw table not selected", "選ぶと T07 が成立しない"),
        ("activator name", context.names["activator"]),
        ("subject gate", "空でないこと"),
        ("increment file name diagnostic", "診断・フォールバック専用"),
        ("metric instance", static.metric_id),
        ("metric count", f"{static.metric_static_count:,}"),
        ("metric amount", f"{static.metric_total_yen:,}"),
        ("flow instance", static.flow_id),
        ("flow reverse instance", static.flow_reverse_id),
        ("timeseries observed count", f"{observation.top_observed_count:,}"),
        ("timeseries observed amount", f"{observation.top_observed_amount_yen:,}"),
        ("cardinality gate", "Edge 1,741 = Municipality 1,741"),
        ("core entity layer", "基幹エンティティ層"),
        ("binding noun", "time-series バインディング"),
    ]
    validators.check_required(text, quality_items, report, check="checklist.qualityGates")

    for phrase in ("明細層", "詳細層", "DonationObservationsForAgent", "time-series バインド（"):
        if phrase in text:
            report.fail("checklist.retiredWording", f"retired wording still present: {phrase}")
            break
    else:
        report.ok("checklist.retiredWording", "no retired layer or projection wording")

    prose = [
        line.strip()
        for line in re.sub(r"```.*?```", "", text, flags=re.S).splitlines()
        if line.strip() and not line.lstrip().startswith(("|", "#", ">", "-", "```"))
    ]
    quality.check_typography(prose, report)

    return report


def validate_runtime_parity(root: Path, context, tests, facts=None) -> Report:
    """Assert the runtime is internally consistent before trusting the values we quote.

    The deliverables mirror `workshop/v2.7.0`, so a stale count inside the runtime
    would silently become a stale number inside the documents. Every value the docs
    reproduce is therefore reconciled against the artifact that owns it.
    """
    import ast
    import json
    import re as _re

    workshop = root / "workshop" / f"v{context.version}"
    report = Report(target=f"workshop/v{context.version} (runtime parity)")
    automation = context.workspace_contract["workshopProvisioningAutomation"]
    published = workshop / "provisioning" / "bundle" / "data-agent" / "Files" / "Config" / "published"
    draft = workshop / "provisioning" / "bundle" / "data-agent" / "Files" / "Config" / "draft"

    def load(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    published_fewshots = load(next(published.glob("lakehouse-tables-*/fewshots.json")))["fewShots"]
    draft_fewshots = load(next(draft.glob("lakehouse-tables-*/fewshots.json")))["fewShots"]
    published_sources = sorted(p.name for p in published.iterdir() if p.is_dir())
    draft_sources = sorted(p.name for p in draft.iterdir() if p.is_dir())

    declared = [
        (
            "fewShotCount",
            automation.get("lakehouseFewShotCount"),
            len(published_fewshots),
            "contract lakehouseFewShotCount vs the shipped Lakehouse few-shots",
        ),
        (
            "sourceCount",
            automation.get("dataAgentSourceCount"),
            len(published_sources),
            "contract dataAgentSourceCount vs the shipped Data Agent sources",
        ),
        (
            "datasetFileCount",
            automation.get("datasetFileCount"),
            context.csv_count,
            "contract datasetFileCount vs the packaged CSVs",
        ),
        (
            "kqlManagementCommandCount",
            automation.get("kqlManagementCommandCount"),
            len(_re.findall(r"^\.[a-z]", context.kql_setup, _re.M)),
            "contract kqlManagementCommandCount vs the KQL setup script",
        ),
    ]
    mismatched = [
        f"{name}: contract={left!r} actual={right!r} ({why})"
        for name, left, right, why in declared
        if left is not None and left != right
    ]
    if mismatched:
        report.fail("runtime.declaredCounts", "; ".join(mismatched))
    else:
        report.ok("runtime.declaredCounts", f"all {len(declared)} declared counts match the shipped assets")

    notebook_path = context.notebooks["Notebook_01"].path
    notebook = load(notebook_path)
    contract_source = next(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
        and "INPUT_CONTRACT =" in "".join(cell.get("source", []))
    )
    contract_module = ast.parse(contract_source, filename=str(notebook_path))
    contract_assignment = next(
        node
        for node in contract_module.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "INPUT_CONTRACT"
            for target in node.targets
        )
    )
    notebook_contract = ast.literal_eval(contract_assignment.value)
    dataset_manifest = load(workshop / "data" / "dataset-manifest.json")
    expected_contract = {
        entry["file"]: {
            "rows": entry["rows"],
            "header": entry["header"],
            "sha256": entry["sha256"],
        }
        for entry in dataset_manifest["files"]
    }
    actual_contract = {
        file_name: {
            "rows": values.get("rows"),
            "header": values.get("header"),
            "sha256": values.get("sha256"),
        }
        for file_name, values in notebook_contract.items()
    }
    if actual_contract == expected_contract:
        report.ok(
            "runtime.notebook01InputContract",
            f"Notebook 01 matches all {len(expected_contract)} seed-file manifest contracts",
        )
    else:
        drift = {
            file_name: {
                field: (
                    expected_contract.get(file_name, {}).get(field),
                    actual_contract.get(file_name, {}).get(field),
                )
                for field in ("rows", "header", "sha256")
                if expected_contract.get(file_name, {}).get(field)
                != actual_contract.get(file_name, {}).get(field)
            }
            for file_name in sorted(set(expected_contract) | set(actual_contract))
            if expected_contract.get(file_name) != actual_contract.get(file_name)
        }
        report.fail(
            "runtime.notebook01InputContract",
            f"Notebook 01 seed contract drift: {drift}",
        )

    if published_sources == draft_sources:
        report.ok("runtime.stageParity.sources", f"draft and published expose the same {len(published_sources)} sources")
    else:
        report.fail("runtime.stageParity.sources", f"draft={draft_sources} published={published_sources}")

    if published_fewshots == draft_fewshots:
        report.ok("runtime.stageParity.fewShots", f"draft and published carry the same {len(published_fewshots)} few-shots")
    else:
        report.fail("runtime.stageParity.fewShots", "draft and published few-shots differ")

    draft_config_json = load(draft / "stage_config.json")
    published_config_json = load(published / "stage_config.json")
    draft_config = draft_config_json["aiInstructions"].strip()
    published_config = published_config_json["aiInstructions"].strip()
    instructions = context.agent_instructions.strip()
    if draft_config == published_config == instructions:
        report.ok("runtime.stageParity.instructions", "agent-instructions.txt, draft and published agree")
    else:
        report.fail(
            "runtime.stageParity.instructions",
            "agent-instructions.txt, the draft stage config and the published stage config disagree",
        )

    draft_flag = (draft_config_json.get("experimental") or {}).get("codeInterpreterEnabled")
    published_flag = (published_config_json.get("experimental") or {}).get("codeInterpreterEnabled")
    if draft_flag is False and published_flag is False:
        report.ok(
            "runtime.codeInterpreter",
            "the Core Data Agent ships with codeInterpreterEnabled=false in both stages",
        )
    else:
        report.fail(
            "runtime.codeInterpreter",
            f"Core must ship Code Interpreter disabled; draft={draft_flag!r} published={published_flag!r}",
        )

    capabilities = [
        ("three-source composition", "up to all three"),
        ("cross-source composition by stable ID", "compose the results only by stable ID"),
        ("exact entity-ID digits", "exact stable ID"),
        ("popularity ambiguity", "人気"),
        ("activity ambiguity", "一番動いた"),
        ("safe wealth language", "金持ち"),
    ]
    absent = [label for label, needle in capabilities if needle not in instructions]
    if absent:
        report.fail("runtime.instructionCapabilities", f"the final instructions do not cover: {absent}")
    else:
        report.ok(
            "runtime.instructionCapabilities",
            f"the final instructions cover all {len(capabilities)} approved behaviours",
        )

    draft_by_type = {}
    for folder in sorted(draft.iterdir()):
        if folder.is_dir() and (folder / "datasource.json").is_file():
            payload = load(folder / "datasource.json")
            draft_by_type[payload["type"]] = payload
    divergent = [
        source_type
        for source_type, payload in context.agent_sources.items()
        if draft_by_type.get(source_type, {}).get("userDescription") != payload.get("userDescription")
        or draft_by_type.get(source_type, {}).get("dataSourceInstructions") != payload.get("dataSourceInstructions")
    ]
    if divergent:
        report.fail("runtime.stageParity.datasources", f"draft and published differ for: {divergent}")
    else:
        report.ok("runtime.stageParity.datasources", "every source description and instruction matches across stages")

    ontology_source = context.agent_sources.get("ontology", {})
    ontology_extras = list(published.glob("ontology-*/fewshots.json"))
    if ontology_source.get("dataSourceInstructions") in (None, "") and not ontology_extras:
        report.ok(
            "runtime.ontologyLayering",
            "the Ontology source carries a description only, with no source instructions or example queries",
        )
    else:
        report.fail(
            "runtime.ontologyLayering",
            "the Ontology source gained source instructions or example queries; the guide documents neither",
        )

    questions = {fewshot["question"].strip() for fewshot in published_fewshots}
    overlap = questions & {test.question.strip() for test in tests}
    if overlap:
        report.fail("runtime.heldOut", f"an example query reuses a participant test question: {overlap}")
    else:
        report.ok("runtime.heldOut", "no example query overlaps the ten held-out participant questions")

    _validate_instruction_budget(report, context.agent_instructions, context)
    _validate_held_out_isolation(report, context, tests, facts, published_fewshots)
    _validate_example_query_quality(report, context, published_fewshots)
    _validate_kusto_shapes(report, context)
    _validate_t04_prefecture(report, context, tests, facts)
    _validate_pin_parity(root, context, report)
    _validate_notebook02_manifest_gate(root, context, report)
    _validate_hash_conventions(root, context, report)
    _validate_lf_determinism(root, report)
    _validate_reseal_determinism(root, report)
    _validate_payload_bundle_parity(root, report)
    _validate_contract_source_parity(root, report)
    _validate_rank_description_parity(root, context, report)
    _validate_ontology_semantics(root, context, report)

    notebook_hashes = [
        ("Notebook_04", automation.get("notebookSha256"), context.notebooks["Notebook_04"].sha256),
        (
            "Notebook_05",
            context.workspace_contract.get("analyticsExtension", {}).get("notebook", {}).get("sha256"),
            context.notebooks["Notebook_05"].sha256,
        ),
    ]
    stale = [
        f"{name}: contract={left} actual={right}"
        for name, left, right in notebook_hashes
        if left is not None and left != right
    ]
    if stale:
        report.fail("runtime.notebookHashes", "; ".join(stale))
    else:
        report.ok("runtime.notebookHashes", "contract notebook hashes match the shipped notebooks")

    contract = context.ontology_contract
    actual = {
        "entityTypes": len(context.entities),
        "staticProperties": sum(len(entity.properties) for entity in context.entities),
        "timeseriesProperties": sum(len(entity.timeseries_properties) for entity in context.entities),
        "relationshipTypes": len(context.relationships),
    }
    ontology_mismatch = {
        key: (contract.get(key), value) for key, value in actual.items() if contract.get(key) != value
    }
    if ontology_mismatch:
        report.fail("runtime.ontologyContract", f"declared vs parsed: {ontology_mismatch}")
    else:
        report.ok(
            "runtime.ontologyContract",
            f"{actual['entityTypes']} entities / {actual['staticProperties']} static properties / "
            f"{actual['timeseriesProperties']} time-series property / {actual['relationshipTypes']} relationships",
        )

    # The element counts the guide tells a participant to tick must agree with the
    # selection the shipped Data Agent bundle actually carries, not just with the
    # dataset manifest they were derived from.
    def _selected(nodes, wanted: str) -> list[str]:
        found: list[str] = []
        for node in nodes:
            if node.get("type") == wanted and node.get("is_selected"):
                found.append(node.get("display_name", ""))
            found.extend(_selected(node.get("children", []), wanted))
        return found

    materialized = [
        entry.name for entry in context.kql_objects if entry.command == "create-or-alter materialized-view"
    ]
    selection = {
        "lakehouse": (
            sorted(_selected(context.agent_sources["lakehouse_tables"].get("elements", []), "lakehouse_tables.table")),
            sorted(context.expected["outputTableCounts"]),
        ),
        "kusto": (
            sorted(_selected(context.agent_sources["kusto"].get("elements", []), "kusto.table")),
            sorted(materialized),
        ),
        "ontology": (
            sorted(_selected(context.agent_sources["ontology"].get("elements", []), "ontology.entity")),
            sorted(entity.name for entity in context.entities),
        ),
    }
    drift = {key: pair for key, pair in selection.items() if pair[0] != pair[1]}
    if drift:
        report.fail("runtime.agentSourceElements", f"selected vs expected: {drift}")
    else:
        report.ok(
            "runtime.agentSourceElements",
            "the Data Agent selects exactly "
            f"{len(selection['lakehouse'][0])} Lakehouse tables, "
            f"{len(selection['kusto'][0])} materialized view, "
            f"{len(selection['ontology'][0])} entity types - and no raw observation table",
        )

    return report


#: Final approved runtime invariants, verified independently and pinned here so a
#: later edit to any mirror or to the packaged data fails the documentation gate.
FINAL_RUNTIME = {
    "agentInstructionsSha256": "fc4efb234dd3a30b5fba4c0a58af04e836dc3d80f15dd9b051cd9c36f58e1384",
    "agentInstructionsChars": 14440,
    "agentInstructionsBytes": 14586,
    #: This release's sealed character budget, not a universal product limit.
    "agentInstructionCharLimit": 15000,
    "agentInstructionMirrors": 4,
    "payloadSha256": "71717e94877900d665d6a40fd375909907801a3862034c6b3d57c865b2ad0a6e",
    "lakehouseFewShots": 3,
    "dataAgentSources": 3,
    "codeInterpreterEnabled": False,
    "incrementUtcDays": 31,
    "incrementMinRowsPerDay": 450,
    "incrementMaxRowsPerDay": 582,
    "curatedLeaderMunicipalityId": "452025",
    "curatedLeaderObservations": 331,
    "curatedLeaderAmountYen": 5737000,
    #: Added by the quality pass: the unused KQL projection layer is gone and
    #: every relationship carries a declared cardinality.
    "kqlManagementCommands": 5,
    "kqlManagementObjects": (
        "DonationEvents",
        "DonationEvents_IncrementCsvMap",
        "DonationObservationSummaryForAgent",
    ),
    "relationshipCardinalitiesDeclared": 15,
    #: Final diagram set for this loop: seven diagrams, PNG + SVG each, no baked
    #: figure numbers, renamed core-entity band. Hashes are read from the shipped
    #: assets, never transcribed by hand.
    "diagramAssets": 14,
    "diagramSha256": {
        "data-agent-source-routing.png": "90243b8105e822714ad49949c661c12bed31f544f9d553a095de1201d34f0ae7",
        "data-agent-source-routing.svg": "4d796309cfb29eed20474ff11498877a24393bac0713f6f7151548c2711f55b6",
        "furusato-ontology-layers.png": "66d3b4e26bc65b0172e0bf5d6d020ddc80fe07ae1ce5bad1fb83a78cfc2d7280",
        "furusato-ontology-layers.svg": "9c8bb4a08f17d0be607b38e4e157a562d4e302aa85772eee9b38934d7c6fe405",
        "ontology-authoring-evaluation-lifecycle.png": "c07b214981a2369905912cb429fe17ed2312f5d872dd59686168169e3437a654",
        "ontology-authoring-evaluation-lifecycle.svg": "e94ba41e5c091177d2381751def3255ba3db701dd22866ab4118dd7f600419ad",
        "ontology-data-agent-poc-production.png": "64798b8b51a1db6cd4cb42494b2abbec58a7ff6bfa17c6b58f655656b0b50a2d",
        "ontology-data-agent-poc-production.svg": "81b79d1e455d59dd9f2250e3427a2e813583a6e410fad80e0fd82d1d2ccc48fc",
        "rdb-bi-ontology-mental-model.png": "cc724c29029c9e632cfc9625105afb9431d474e52f4408f8675c8700c57adc44",
        "rdb-bi-ontology-mental-model.svg": "46a011d165f953fecb0898d99008e59b8d67b4726f89764a144b601898986287",
        "rdb-to-ontology-decision-tree.png": "fe8b2912f5788dc2f82cd44fc83943f597e4d42ab51dc956d37c12bf20f0718d",
        "rdb-to-ontology-decision-tree.svg": "670f944df8a191ab9848f400ab0ec4236713019bcc2ce48711064873ac21cfc3",
        "system-data-flow.png": "1171661fd5109a14cef909496035cf3e26b6111eb5c3c13b6f236475c0758f9f",
        "system-data-flow.svg": "9b66b6e30a5e212f339da99857010c43c7930b59f64d3eaa4369ce390fd5c5f8",
    },
}


def _validate_instruction_budget(report: Report, instructions: str, context) -> None:
    """The sealed global instructions stay inside this workshop's character budget.

    ``agentInstructionCharLimit`` is the budget this distribution seals: the
    reseal tool, the participant contract and this validator all state the same
    number, and the v2.7.0 Data agent screen showed a guard at that value when
    the bundle was built. It is not quoted here as a published product warranty,
    because the screen's guard can move. The check is stated in characters
    because that is the unit the screen counts, and the byte count is reported
    alongside it for the integrity line the guide and the HTML mirror print.
    """
    limit = FINAL_RUNTIME["agentInstructionCharLimit"]
    chars = len(instructions)
    size = len(instructions.encode("utf-8"))
    if chars > limit:
        report.fail(
            "runtime.instructionCharLimit",
            f"the global instructions are {chars:,} characters; this distribution's sealed budget "
            f"is at most {limit:,}",
        )
    else:
        report.ok(
            "runtime.instructionCharLimit",
            f"{chars:,} characters / {size:,} UTF-8 bytes, within the sealed {limit:,}-character budget",
        )

    contract = context.workspace_contract["dataAgent"]
    declared = (
        contract.get("globalInstructionsCharacters"),
        contract.get("globalInstructionsUtf8Bytes"),
        contract.get("globalInstructionsCharLimit"),
    )
    if declared == (chars, size, limit):
        report.ok(
            "runtime.instructionBudgetPinned",
            "the participant contract pins the same character count, byte count and limit",
        )
    else:
        report.fail(
            "runtime.instructionBudgetPinned",
            f"contract declares {declared}, measured {(chars, size, limit)}",
        )

    # The bundle manifest states the same budget under its own shorter names. The
    # contract now carries exactly one pair, so this compares the two files rather
    # than two aliases inside one file - which is the comparison that can actually
    # catch a half-finished reseal.
    manifest = json.loads(
        (
            repo_root() / "workshop" / f"v{context.version}" / "provisioning" / "bundle" / "bundle-manifest.json"
        ).read_text("utf-8")
    )["contracts"]["dataAgent"]
    mirrored = (manifest.get("globalInstructionsChars"), manifest.get("globalInstructionsBytes"))
    if mirrored == (chars, size):
        report.ok(
            "runtime.instructionBudgetLegacyKeys",
            "the bundle manifest states the same character and byte count as the contract",
        )
    else:
        report.fail(
            "runtime.instructionBudgetLegacyKeys",
            f"bundle manifest declares {mirrored}, measured {(chars, size)}",
        )


#: Punctuation and spacing that do not change what a question asks.
_TEMPLATE_NOISE = re.compile(r"[\s、。，．,\.\?？!！「」『』（）\(\)]+")

#: Any run of digits (half- or full-width) is a slot, not part of the shape.
_DIGIT_RUN = re.compile(r"[0-9０-９]+")

#: Two normalised questions this similar are the same question with one slot
#: swapped. Measured against the shipped set: the three neutral examples score at
#: most 0.30 against every held-out test, while the two withdrawn examples that
#: cloned T03 and T05 score 0.75 and 0.52.
_TEMPLATE_SIMILARITY_LIMIT = 0.45

#: Shortest normalised question worth comparing. Below this a coincidental
#: bigram overlap says nothing about intent.
_TEMPLATE_MIN_LENGTH = 12


def _place_name_mask(context) -> re.Pattern[str] | None:
    """Every prefecture and municipality name that occurs in the packaged data.

    A question leaks its template by keeping the sentence and swapping the place,
    so the place has to be removed before two questions are compared. The names
    come from the shipped CSVs rather than a hand-written list, so a dataset that
    gains a municipality cannot silently escape the mask.
    """
    import csv as _csv

    seed = context.root / "workshop" / f"v{context.version}" / "data" / "seed"
    names: set[str] = set()
    for file_name, columns in (
        ("prefectures.csv", ("PrefectureName", "PrefectureNameEn")),
        ("municipalities.csv", ("MunicipalityName", "PrefectureName")),
    ):
        path = seed / file_name
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            for row in _csv.DictReader(handle):
                for column in columns:
                    value = (row.get(column) or "").strip()
                    if len(value) >= 2:
                        names.add(value)
                        # "東京都" also occurs as the bare "東京" in colloquial wording.
                        for suffix in ("都", "道", "府", "県", "市", "区", "町", "村"):
                            if value.endswith(suffix) and len(value) > len(suffix) + 1:
                                names.add(value[: -len(suffix)])
    if not names:
        return None
    # Longest first so 宮崎県 is consumed before 宮崎.
    return re.compile("|".join(re.escape(name) for name in sorted(names, key=len, reverse=True)))


def _question_template(text: str, mask: re.Pattern[str] | None = None) -> str:
    """Normalised shape of a question: no place name, no digits, no punctuation.

    Reduces a question to the part a participant did not choose - the sentence
    pattern - so that two questions differing only by a prefecture, a municipality
    or a stable ID collapse onto the same string. That collapse is the signal:
    an example query built from a held-out test by swapping the place is exactly
    what teaches the agent the answer before the test is run.
    """
    if mask is not None:
        text = mask.sub("", text)
    text = _DIGIT_RUN.sub("", text)
    return _TEMPLATE_NOISE.sub("", text)


def _character_ngrams(text: str, size: int = 2) -> set[str]:
    if len(text) < size:
        return {text} if text else set()
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def _template_similarity(left: str, right: str) -> float:
    """Jaccard overlap of character bigrams, which suits unsegmented Japanese.

    Substring containment alone misses the common case: an example built from a
    test keeps the wording but reorders or trims a clause, so neither string
    contains the other while both still ask the same thing.
    """
    if not left or not right:
        return 0.0
    if left in right or right in left:
        return 1.0
    first = _character_ngrams(left)
    second = _character_ngrams(right)
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def _template_collisions(
    surfaces: list[tuple[str, str]], tests, mask: re.Pattern[str] | None
) -> list[str]:
    """Surfaces whose normalised wording is too close to a held-out question."""
    templates = [
        (test.test_id, _question_template(test.question, mask))
        for test in tests
    ]
    hits: list[str] = []
    for label, text in surfaces:
        if not text:
            continue
        normalised = _question_template(text, mask)
        if len(normalised) < _TEMPLATE_MIN_LENGTH:
            continue
        for test_id, template in templates:
            if len(template) < _TEMPLATE_MIN_LENGTH:
                continue
            score = _template_similarity(template, normalised)
            if score >= _TEMPLATE_SIMILARITY_LIMIT:
                hits.append(f"{label} matches the {test_id} question template (similarity {score:.2f})")
    return sorted(set(hits))


#: The join set that answers a full Donation trace, which is what T05 evaluates.
#: An example query touching all of these reproduces the held-out trace shape no
#: matter how its question is worded.
TRACE_SHAPE_TABLES = frozenset(
    {
        "ot_donation",
        "ot_donor",
        "ot_prefecture",
        "ot_municipality",
        "ot_gift",
        "ot_gift_category",
        "ot_supplier_gift",
        "ot_supplier",
    }
)

#: Example queries withdrawn from this bundle because each one reproduced a
#: held-out test. They are kept as regression fixtures: a gate that no longer
#: catches them has been loosened past the point of usefulness. The two leak by
#: different routes, so each one pins a different gate.
WITHDRAWN_EXAMPLES = (
    {
        "test_id": "T03",
        "label": "few-shot 1 (withdrawn)",
        "gate": "template",
        "question": "福岡県の寄付はどれくらいですか。",
        "query": "SELECT p.PrefectureId FROM dbo.ot_prefecture AS p WHERE p.PrefectureName = N'福岡県';",
    },
    {
        "test_id": "T05",
        "label": "few-shot 3 (withdrawn)",
        "gate": "traceShape",
        "question": (
            "寄付 5000002 の寄付金額、寄付者、在住都道府県、受入自治体と都道府県、返礼品とカテゴリ、"
            "カタログ登録事業者を、すべての安定IDと名前付きで教えてください。"
        ),
        "query": (
            "SELECT d.DonationId FROM dbo.ot_donation AS d "
            "INNER JOIN dbo.ot_donor AS donor ON d.DonorId = donor.DonorId "
            "INNER JOIN dbo.ot_prefecture AS donor_pref ON donor.PrefectureId = donor_pref.PrefectureId "
            "INNER JOIN dbo.ot_municipality AS municipality ON d.MunicipalityId = municipality.MunicipalityId "
            "INNER JOIN dbo.ot_gift AS gift ON d.GiftId = gift.GiftId "
            "INNER JOIN dbo.ot_gift_category AS category ON gift.CategoryId = category.CategoryId "
            "LEFT JOIN dbo.ot_supplier_gift AS sg ON gift.GiftId = sg.GiftId "
            "LEFT JOIN dbo.ot_supplier AS supplier ON sg.SupplierId = supplier.SupplierId "
            "WHERE d.DonationId = 5000002;"
        ),
    },
)


def _query_tables(query: str) -> set[str]:
    return set(re.findall(r"dbo\.([a-z_]+)", query or ""))


def _check_template_gate_regressions(report: Report, tests, mask: re.Pattern[str] | None) -> None:
    """Prove both withdrawn examples are still rejected, each by its own gate.

    The two leaked differently. The first kept T03's sentence and swapped only the
    prefecture, so it is caught by wording similarity once place names are masked.
    The second asked in completely different words but joined the exact eight
    tables a Donation trace needs, so wording says nothing and the join shape is
    the evidence. A gate for one does not cover the other.
    """
    by_id = {test.test_id: test for test in tests}
    undetected: list[str] = []
    detected: list[str] = []
    for fixture in WITHDRAWN_EXAMPLES:
        test = by_id.get(fixture["test_id"])
        if test is None:
            undetected.append(f"{fixture['test_id']} is no longer in the held-out set")
            continue
        if fixture["gate"] == "template":
            score = _template_similarity(
                _question_template(test.question, mask),
                _question_template(fixture["question"], mask),
            )
            if score >= _TEMPLATE_SIMILARITY_LIMIT:
                detected.append(f"{fixture['label']} vs {fixture['test_id']} wording {score:.2f}")
            else:
                undetected.append(
                    f"{fixture['label']} vs {fixture['test_id']} scored only {score:.2f} on wording"
                )
        else:
            tables = _query_tables(fixture["query"])
            if TRACE_SHAPE_TABLES <= tables:
                detected.append(
                    f"{fixture['label']} vs {fixture['test_id']} joins all {len(TRACE_SHAPE_TABLES)} trace tables"
                )
            else:
                undetected.append(
                    f"{fixture['label']} vs {fixture['test_id']} was not recognised as a trace shape "
                    f"(missing {sorted(TRACE_SHAPE_TABLES - tables)})"
                )
    if undetected:
        report.fail("runtime.heldOut.templateGateRegression", "; ".join(undetected))
    else:
        report.ok(
            "runtime.heldOut.templateGateRegression",
            f"the gates still reject both withdrawn examples: {', '.join(detected)}",
        )


#: The entry table of an example query: the first ``FROM dbo.<table>`` it names.
#: Two examples that start from the same table compete for the same question, so
#: whichever the similarity search returns first decides the answer.
_ENTRY_TABLE = re.compile(r"\bFROM\s+(dbo\.[A-Za-z0-9_]+)", re.IGNORECASE)


def _selected_table_names(context) -> set[str]:
    """Every Lakehouse table the shipped datasource definition marks selected."""
    selected: set[str] = set()

    def walk(node: dict) -> None:
        if node.get("type") == "lakehouse_tables.table" and node.get("is_selected"):
            selected.add(str(node.get("display_name")))
        for child in node.get("children", ()):
            walk(child)

    for element in context.agent_sources["lakehouse_tables"].get("elements", ()):
        walk(element)
    return selected


def _validate_example_query_quality(report: Report, context, published_fewshots) -> None:
    """The shipped example queries satisfy the published example-query practice.

    Chapter 16.6.1 prints a checklist derived from first-party documentation. A
    printed checklist proves nothing on its own, so the four mechanical items are
    measured here against the sealed bundle: every question is distinct, every
    query has a body, no two examples start from the same table, and every entry
    table is one the Data Agent actually selects. The held-out isolation of the
    same set is checked by ``_validate_held_out_isolation``.
    """
    questions = [str(shot.get("question", "")).strip() for shot in published_fewshots]
    duplicates = sorted({q for q in questions if questions.count(q) > 1 or not q})
    if duplicates:
        report.fail(
            "runtime.exampleQueries.uniqueQuestions",
            f"example questions are empty or repeated: {[q[:40] for q in duplicates]}",
        )
    else:
        report.ok(
            "runtime.exampleQueries.uniqueQuestions",
            f"all {len(questions)} example questions are non-empty and distinct",
        )

    empty = [
        index
        for index, shot in enumerate(published_fewshots, start=1)
        if not str(shot.get("query", "")).strip()
    ]
    if empty:
        report.fail("runtime.exampleQueries.nonEmpty", f"example queries with no body: {empty}")
    else:
        report.ok(
            "runtime.exampleQueries.nonEmpty",
            f"all {len(published_fewshots)} example queries carry a query body",
        )

    entry = [_ENTRY_TABLE.search(str(shot.get("query", ""))) for shot in published_fewshots]
    tables = [match.group(1) if match else "" for match in entry]
    missing = [index for index, name in enumerate(tables, start=1) if not name]
    repeated = sorted({name for name in tables if name and tables.count(name) > 1})
    if missing or repeated:
        report.fail(
            "runtime.exampleQueries.distinctEntryTables",
            f"examples without a dbo entry table: {missing}; shared entry tables: {repeated}",
        )
    else:
        report.ok(
            "runtime.exampleQueries.distinctEntryTables",
            f"the {len(tables)} example queries start from {len(set(tables))} different tables "
            f"({', '.join(sorted(tables))})",
        )

    selected = _selected_table_names(context)
    unselected = sorted(
        {name.split(".", 1)[1] for name in tables if name and name.split(".", 1)[1] not in selected}
    )
    if not selected:
        report.fail(
            "runtime.exampleQueries.entryTableSelected",
            "the Lakehouse datasource definition marks no table as selected",
        )
    elif unselected:
        report.fail(
            "runtime.exampleQueries.entryTableSelected",
            f"example entry tables the Agent does not select: {unselected}",
        )
    else:
        report.ok(
            "runtime.exampleQueries.entryTableSelected",
            f"every example entry table is among the {len(selected)} selected Lakehouse tables",
        )


def _validate_held_out_isolation(report: Report, context, tests, facts, published_fewshots) -> None:
    """No held-out question, stable ID or oracle value may reach the shipped runtime.

    The Data Agent is configured from four surfaces a participant can read: the
    global instruction block, three source descriptions, the Lakehouse and Kusto
    source instruction blocks, and three Lakehouse example queries. If any of
    them reproduces a test question - verbatim, or with only the place name and
    the digits swapped - or carries one of the expected answers, the ten tests
    stop measuring the agent and start measuring the prompt.
    """
    surfaces: list[tuple[str, str]] = [("global instructions", context.agent_instructions)]
    for source_type, payload in sorted(context.agent_sources.items()):
        surfaces.append((f"{source_type} description", payload.get("userDescription") or ""))
        surfaces.append((f"{source_type} instructions", payload.get("dataSourceInstructions") or ""))
    for index, shot in enumerate(published_fewshots, start=1):
        surfaces.append((f"few-shot {index} question", shot.get("question", "")))
        surfaces.append((f"few-shot {index} query", shot.get("query", "")))

    # 1. Verbatim question reuse and near-duplicate templates.
    mask = _place_name_mask(context)
    template_hits = _template_collisions(surfaces, tests, mask)
    if template_hits:
        report.fail("runtime.heldOut.templates", "; ".join(template_hits))
    else:
        report.ok(
            "runtime.heldOut.templates",
            f"none of the {len(surfaces)} configured surfaces comes within "
            f"{_TEMPLATE_SIMILARITY_LIMIT:.2f} similarity of a held-out question template",
        )

    # 1b. The gate itself is regression-tested against the two example queries
    #     that were withdrawn from this bundle for cloning a held-out test.
    _check_template_gate_regressions(report, tests, mask)

    # 2. Stable IDs and oracle values that only the held-out answers know.
    if facts is None:
        report.warn("runtime.heldOut.values", "facts unavailable; oracle-value scan skipped")
        return
    static = facts.static
    observation = facts.observation
    sample = static.sample_donation
    secrets: dict[str, str] = {
        "T01 donation rows": str(static.donation_rows),
        "T01 donation total": str(static.donation_total_yen),
        "T02 top municipality": str(static.top_municipality_id),
        "T02 top municipality name": str(static.top_municipality_name),
        "T02 runner-up municipality": str(static.second_municipality_id),
        "T03 Tokyo received amount": str(static.tokyo_received_yen),
        "T03 Tokyo resident amount": str(static.tokyo_resident_yen),
        "T05 donation id": str(sample["DonationID"]),
        "T05 donor id": str(sample["DonorId"]),
        "T05 municipality id": str(sample["MunicipalityId"]),
        "T05 gift id": str(sample["GiftId"]),
        "T05 supplier id": str(sample["SupplierIds"][0]),
        "T06 raw observations": str(observation.raw_rows),
        "T06 raw amount": str(observation.raw_amount_yen),
        "T07 unique event ids": str(observation.unique_event_ids),
        "T08 forbidden sum": str(static.donation_rows + observation.raw_rows),
        "T09 observed leader count": str(observation.top_observed_count),
        "T09 observed leader amount": str(observation.top_observed_amount_yen),
    }
    # A place name is only a leak when the test's oracle turns on it.
    secrets["T04 prefecture name"] = str(static.t04_prefecture_name)
    secrets["T04 prefecture id and count"] = f"{static.t04_prefecture_id}:{static.t04_municipality_count}"

    leaks = []
    for label, text in surfaces:
        if not text:
            continue
        for name, needle in secrets.items():
            if needle and needle in text:
                leaks.append(f"{label} contains the {name} value {needle!r}")
    if leaks:
        report.fail("runtime.heldOut.values", "; ".join(sorted(set(leaks))))
    else:
        report.ok(
            "runtime.heldOut.values",
            f"none of the {len(secrets)} held-out stable IDs or oracle values appears in the "
            f"{len(surfaces)} configured Data Agent surfaces",
        )

    # 3. Only generic schema names may appear, and every example query must be
    #    runnable SQL against a table the Agent actually selects.
    selected_tables = set(context.expected["outputTableCounts"])
    unknown = []
    traces = []
    for index, shot in enumerate(published_fewshots, start=1):
        referenced = _query_tables(shot.get("query", ""))
        for table in sorted(referenced - selected_tables):
            unknown.append(f"few-shot {index} queries {table}, which the Agent does not select")
        if TRACE_SHAPE_TABLES <= referenced:
            traces.append(f"few-shot {index} joins the full Donation-trace table set")
    if unknown:
        report.fail("runtime.heldOut.exampleTables", "; ".join(unknown))
    else:
        report.ok(
            "runtime.heldOut.exampleTables",
            f"all {len(published_fewshots)} example queries read only selected Lakehouse tables",
        )

    # 4. Wording can differ completely while the join shape still reproduces a
    #    held-out test. The Donation trace is the case that matters here: T05 is
    #    the only test whose answer is that whole eight-table join.
    if traces:
        report.fail("runtime.heldOut.exampleShapes", "; ".join(traces))
    else:
        report.ok(
            "runtime.heldOut.exampleShapes",
            f"no example query reproduces the {len(TRACE_SHAPE_TABLES)}-table Donation-trace join that T05 evaluates",
        )


def _validate_t04_prefecture(report: Report, context, tests, facts) -> None:
    """T04 names its prefecture in words, so the words and the data must agree.

    The question is approved and fixed. What must be checked is that the declared
    prefecture is still the one the packaged data describes, and that the answer,
    the PrefectureId and the evidence all describe that same prefecture rather
    than one inherited from another test's result.
    """
    import csv as _csv

    if facts is None:
        report.warn("runtime.t04Prefecture", "facts unavailable; T04 coupling check skipped")
        return
    static = facts.static
    seed = context.root / "workshop" / f"v{context.version}" / "data" / "seed" / "municipalities.csv"
    with seed.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in _csv.DictReader(handle) if row["PrefectureID"] == static.t04_prefecture_id]

    problems: list[str] = []
    if not rows:
        problems.append(f"PrefectureId {static.t04_prefecture_id} has no municipality in the packaged data")
    else:
        names = {row["PrefectureName"] for row in rows}
        if names != {static.t04_prefecture_name}:
            problems.append(
                f"PrefectureId {static.t04_prefecture_id} is named {sorted(names)}, "
                f"not {static.t04_prefecture_name!r}"
            )
        if len(rows) != static.t04_municipality_count:
            problems.append(
                f"declared count {static.t04_municipality_count} != {len(rows)} municipalities in the data"
            )

    test = next((item for item in tests if item.test_id == "T04"), None)
    if test is None:
        problems.append("T04 is no longer in the held-out set")
    else:
        if static.t04_prefecture_name not in test.question:
            problems.append(f"the T04 question does not name {static.t04_prefecture_name}")
        for label, text in (("expected", test.expected), ("evidence", "／".join(test.evidence))):
            if static.t04_prefecture_id not in text:
                problems.append(f"T04 {label} does not carry PrefectureId {static.t04_prefecture_id}")
            if str(static.t04_municipality_count) not in text:
                problems.append(f"T04 {label} does not carry the count {static.t04_municipality_count}")
        if static.t04_prefecture_name not in test.expected:
            problems.append(f"T04 expected does not name {static.t04_prefecture_name}")

    if problems:
        report.fail("runtime.t04Prefecture", "; ".join(problems))
    else:
        report.ok(
            "runtime.t04Prefecture",
            f"T04 targets the declared prefecture {static.t04_prefecture_name} "
            f"(PrefectureId {static.t04_prefecture_id}, {static.t04_municipality_count} municipalities) "
            "in its question, expected answer and evidence",
        )


def _validate_pin_parity(root: Path, context, report: Report) -> None:
    """Every pin that names a build artefact must name the artefact on disk.

    These digests are written by three different steps - the reseal, the Office
    build and this validator's own constant - and a run interrupted between them
    leaves a chain that still validates piecewise while pointing at a payload that
    no longer exists. They are therefore all compared against the bytes on disk in
    one place.
    """
    import hashlib as _hashlib
    import json as _json

    workshop = root / "workshop" / f"v{context.version}"
    notebook = workshop / "notebooks" / "Notebook_04_Furusato_Provision_Complete_Workshop.ipynb"
    measured = _hashlib.sha256(notebook.read_bytes()).hexdigest()
    manifest = _json.loads((workshop / "provisioning" / "payload-manifest.json").read_text("utf-8"))
    automation = context.workspace_contract["workshopProvisioningAutomation"]

    problems: list[str] = []
    if automation.get("notebookSha256") != measured:
        problems.append(f"contract notebookSha256={automation.get('notebookSha256', '')[:16]}… != on-disk {measured[:16]}…")
    manifest_digest = _hashlib.sha256(
        (workshop / "provisioning" / "payload-manifest.json").read_bytes()
    ).hexdigest()
    if automation.get("payloadManifestSha256") != manifest_digest:
        problems.append("contract payloadManifestSha256 does not match payload-manifest.json")
    bundle_digest = _hashlib.sha256(
        (workshop / "provisioning" / "bundle" / "bundle-manifest.json").read_bytes()
    ).hexdigest()
    if automation.get("bundleManifestSha256") != bundle_digest:
        problems.append("contract bundleManifestSha256 does not match bundle-manifest.json")
    if manifest.get("payloadSha256") != automation.get("payloadSha256"):
        problems.append("payload-manifest and contract disagree on payloadSha256")
    if FINAL_RUNTIME["payloadSha256"] != manifest.get("payloadSha256"):
        problems.append(
            f"FINAL_RUNTIME payload pin {FINAL_RUNTIME['payloadSha256'][:16]}… != "
            f"sealed {str(manifest.get('payloadSha256'))[:16]}…"
        )

    if problems:
        report.fail("runtime.pinParity", "; ".join(problems))
    else:
        report.ok(
            "runtime.pinParity",
            "the FINAL_RUNTIME pin, both manifests and the participant contract all name the "
            f"sealed payload and the on-disk Notebook 04 ({measured[:16]}…)",
        )


def _validate_hash_conventions(root: Path, context, report: Report) -> None:
    """Each declared hash convention must be the convention that reproduces the pin.

    Three different conventions are in use - canonical JSON of a whole object,
    canonical JSON of one array inside it, and raw file bytes - and a reader who
    applies the wrong one concludes the artefact was tampered with. The contract
    states which is which, so the statement is verified by recomputing the digest
    both ways and requiring only the declared one to match.
    """
    import hashlib as _hashlib
    import json as _json

    workshop = root / "workshop" / f"v{context.version}"
    ontology = context.workspace_contract["ontology"]
    metadata_path = workshop / "ontology" / "ontology-semantic-metadata.json"
    template_path = workshop / "ontology" / "ontology-full-definition-template.json"
    metadata = _json.loads(metadata_path.read_text("utf-8"))
    template = _json.loads(template_path.read_text("utf-8"))

    def canonical_digest(value) -> str:
        return _hashlib.sha256(
            _json.dumps(value, separators=(",", ":"), ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

    cases = [
        (
            "metadataAutomation.manifestSha256",
            ontology["metadataAutomation"]["manifestSha256"],
            ontology["metadataAutomation"].get("manifestHashConvention", ""),
            "canonical compact JSON of the whole manifest",
            canonical_digest(metadata),
            _hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        ),
        (
            "creationAutomation.templateSha256",
            ontology["creationAutomation"]["templateSha256"],
            ontology["creationAutomation"].get("templateHashConvention", ""),
            "canonical compact JSON of the template's parts array",
            canonical_digest(template["parts"]),
            _hashlib.sha256(template_path.read_bytes()).hexdigest(),
        ),
    ]
    problems: list[str] = []
    for label, pinned, convention, expected_wording, canonical_value, raw_value in cases:
        if pinned != canonical_value:
            problems.append(f"{label} does not match its canonical-JSON digest")
        if pinned == raw_value:
            problems.append(f"{label} is ambiguous: canonical and raw digests coincide")
        if "canonical" not in convention or "not the SHA-256 of the file bytes" not in convention:
            problems.append(f"{label} does not state the canonical-JSON convention")
        if expected_wording.split()[-1] not in convention:
            problems.append(f"{label} convention text does not describe {expected_wording!r}")

    raw_cases = {
        "dataset.manifestSha256": (
            context.workspace_contract["dataset"]["manifestSha256"],
            workshop / "data" / "dataset-manifest.json",
        ),
        "dataset.checksumsSha256": (
            context.workspace_contract["dataset"]["checksumsSha256"],
            workshop / "data" / "SHA256SUMS.txt",
        ),
        "kql.sha256": (
            context.workspace_contract["kql"]["sha256"],
            workshop / "kql" / f"Furusato_Eventhouse_Setup_v{context.version}.kql",
        ),
        "relationshipCardinalityCoverage.validatorSha256": (
            ontology["relationshipCardinalityCoverage"]["validatorSha256"],
            root / "tools" / "ontology" / "Test-OntologyCardinality.ps1",
        ),
    }
    for label, (pinned, path) in raw_cases.items():
        if pinned != _hashlib.sha256(path.read_bytes()).hexdigest():
            problems.append(f"{label} is not the SHA-256 of {path.name}'s raw bytes")

    coverage = ontology["relationshipCardinalityCoverage"]
    required = list(coverage.get("requiredAttributes", []))
    if required != [
        "direction",
        "cardinality",
        "grain",
        "sourceParticipation",
        "targetParticipation",
    ]:
        problems.append(f"requiredAttributes={required} omits a participation statement")
    if "actual" not in str(coverage.get("derivationMode", "")):
        problems.append("derivationMode does not name actual-data mode as the default")
    for key, needle in (
        ("derivedFrom", "recomputed from the rows"),
        ("declaredCountFallback", "-FromData:$false"),
    ):
        if needle not in str(coverage.get(key, "")):
            problems.append(f"{key} does not document {needle!r}")

    if problems:
        report.fail("runtime.hashConventions", "; ".join(sorted(set(problems))))
    else:
        report.ok(
            "runtime.hashConventions",
            f"{len(cases)} canonical-JSON pins and {len(raw_cases)} raw-byte pins each reproduce "
            "under the convention the contract declares, and the cardinality coverage documents "
            "actual-data derivation with its declared-count fallback",
        )


def _validate_notebook02_manifest_gate(root: Path, context, report: Report) -> None:
    """Run Notebook 02's own validator over the manifest Notebook 02 ships.

    The notebook refuses to apply anything unless ``validate_manifest`` accepts
    the manifest, so a vocabulary the validator does not know is not a warning -
    it silently makes the whole 98-object metadata step impossible. Checking the
    manifest with a *separate* implementation would not have caught that: the
    only faithful test is to execute the engine the participant runs, against the
    manifest the participant loads, and require the declared object count back.
    """
    import json as _json
    import sys as _sys
    import types as _types

    workshop = root / "workshop" / f"v{context.version}"
    path = workshop / "notebooks" / "Notebook_02_Furusato_Apply_Ontology_Metadata.ipynb"
    notebook = _json.loads(path.read_text("utf-8"))
    engine = "".join(notebook["cells"][NOTEBOOK02_ENGINE_CELL]["source"])
    embedded = "".join(notebook["cells"][NOTEBOOK02_MANIFEST_CELL]["source"])
    marker = "json.loads(r'''"
    start = embedded.find(marker)
    end = embedded.find("''')", start + len(marker))
    if start < 0 or end < 0:
        report.fail("runtime.notebook02Gate", "the embedded manifest literal could not be located")
        return
    manifest = _json.loads(embedded[start + len(marker) : end])

    module = _types.ModuleType("furusato_notebook02_engine")
    _sys.modules[module.__name__] = module
    try:
        exec(compile(engine, "Notebook_02 engine cell", "exec"), module.__dict__)
        counts = module.validate_manifest(manifest)
    except Exception as error:  # the notebook raises OntologyMetadataError by design
        report.fail(
            "runtime.notebook02Gate",
            f"Notebook 02 rejects its own manifest: {type(error).__name__}: {str(error)[:400]}",
        )
        return
    finally:
        _sys.modules.pop(module.__name__, None)

    contract = context.ontology_contract
    expected = {
        "entityTypes": contract["entityTypes"],
        "staticProperties": contract["staticProperties"],
        "timeseriesProperties": contract["timeseriesProperties"],
        "relationshipTypes": contract["relationshipTypes"],
    }
    total = sum(expected.values())
    if counts != expected:
        report.fail("runtime.notebook02Gate", f"validate_manifest returned {counts}, expected {expected}")
        return
    if total != context.metadata_object_count:
        report.fail(
            "runtime.notebook02Gate",
            f"the accepted manifest totals {total}, but the guide promises {context.metadata_object_count}",
        )
        return

    # The vocabulary the notebook accepts has to cover the vocabulary the manifest
    # uses, or the gate above only passes until the next relationship is added.
    prefixes = tuple(module.CARDINALITY_PREFIXES)
    declared = {
        node["semanticEnrichment"]["customAttributes"]["cardinality"]
        for node in manifest["relationships"].values()
    }
    unmatched = sorted(value for value in declared if not value.startswith(prefixes))
    required = set(module.REQUIRED_RELATIONSHIP_ATTRIBUTES)
    missing_attributes = sorted(
        {"sourceParticipation", "targetParticipation"} - required
    )
    if unmatched or missing_attributes:
        report.fail(
            "runtime.notebook02Vocabulary",
            f"cardinalities outside the accepted prefixes={unmatched}; "
            f"participation keys not required={missing_attributes}",
        )
    else:
        report.ok(
            "runtime.notebook02Vocabulary",
            f"the notebook accepts all {len(declared)} declared cardinality shapes and requires "
            f"{len(required)} relationship attributes including both participation statements",
        )

    report.ok(
        "runtime.notebook02Gate",
        f"Notebook 02's own validate_manifest accepts the shipped manifest and plans "
        f"{total} metadata objects ({expected['entityTypes']} + {expected['staticProperties']} + "
        f"{expected['timeseriesProperties']} + {expected['relationshipTypes']})",
    )


#: Cell indexes of the Notebook 02 embed and engine, which the reseal regenerates.
NOTEBOOK02_MANIFEST_CELL = 3
NOTEBOOK02_ENGINE_CELL = 5


def _validate_kusto_shapes(report: Report, context) -> None:
    """The Kusto source instructions must ship as many shapes as they announce."""
    text = context.agent_sources["kusto"].get("dataSourceInstructions") or ""
    match = re.search(r"(One|Two|Three|Four|Five) supported query shapes", text)
    if not match:
        report.fail("runtime.kqlShapeHeading", "the Kusto instructions no longer announce a shape count")
        return
    words = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
    announced = words[match.group(1)]
    # A shape is a bullet inside the shape list; the list runs to the end of the
    # block, and every shape names the aggregate it summarises.
    body = text[match.end() :]
    shapes = [line for line in body.splitlines() if line.startswith("- ")]
    aggregates = body.count("summarize sum(ObservationCount)")
    if announced == len(shapes) == aggregates:
        report.ok(
            "runtime.kqlShapeHeading",
            f"the Kusto instructions announce and deliver {announced} query shapes",
        )
    else:
        report.fail(
            "runtime.kqlShapeHeading",
            f"announced {announced} shapes, found {len(shapes)} bullets and {aggregates} aggregates",
        )

    prohibitions = [line for line in body.splitlines() if line.startswith("- Never ")]
    if prohibitions:
        report.fail(
            "runtime.kqlShapeList",
            f"{len(prohibitions)} prohibition(s) are still mixed into the query-shape list",
        )
    else:
        report.ok("runtime.kqlShapeList", "the query-shape list contains query shapes only")

    _validate_kusto_shape_parity(report, context, announced)


#: Number words the contract and the guide are allowed to spell the count with.
_SHAPE_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
}


def _stated_shape_counts(text: str) -> set[int]:
    """Every KQL shape count a sentence claims, however it spells the number."""
    counts: set[int] = set()
    for match in re.finditer(
        r"\b(one|two|three|four|five|[1-5])\b[^.]{0,60}?KQL[^.]{0,40}?(?:query shape|example pattern)",
        text,
        re.I,
    ):
        counts.add(_SHAPE_WORDS[match.group(1).lower()])
    for match in re.finditer(r"KQL[^。]{0,30}?の例パターン\s*(\d+)\s*件", text):
        counts.add(int(match.group(1)))
    for match in re.finditer(r"(\d+)\s*件の\s*KQL[^。]{0,20}?(?:例パターン|クエリ形)", text):
        counts.add(int(match.group(1)))
    return counts


def _validate_kusto_shape_parity(report: Report, context, announced: int) -> None:
    """The shape count must be the same number in every place that states it.

    Four artefacts repeat it: the Kusto source instructions, the bundle manifest,
    two fields of the participant contract, and the guide chapter that tells a
    participant what to paste. A participant who reads "two" and pastes three
    cannot tell which one is wrong, so they are compared rather than trusted.
    """
    workshop = context.root / "workshop" / f"v{context.version}"
    manifest = json.loads(
        (workshop / "provisioning" / "bundle" / "bundle-manifest.json").read_text("utf-8")
    )
    agent_contract = manifest["contracts"]["dataAgent"]
    contract = context.workspace_contract
    automation = contract["workshopProvisioningAutomation"]
    data_agent = contract["dataAgent"]

    stated: dict[str, set[int]] = {
        "bundle-manifest kustoExampleDelivery": _stated_shape_counts(
            agent_contract.get("kustoExampleDelivery", "")
        ),
        "contract kustoExampleDelivery": _stated_shape_counts(
            automation.get("kustoExampleDelivery", "")
        ),
        "contract kustoExamplePolicy": _stated_shape_counts(data_agent.get("kustoExamplePolicy", "")),
    }
    problems = [
        f"{label} states {sorted(counts) or 'no count'} but the instructions ship {announced}"
        for label, counts in stated.items()
        if counts != {announced}
    ]
    declared_count = agent_contract.get("kustoQueryShapeCount")
    if declared_count != announced:
        problems.append(f"bundle-manifest kustoQueryShapeCount={declared_count} != {announced}")
    if automation.get("kustoQueryShapeCount") != announced:
        problems.append(
            f"contract kustoQueryShapeCount={automation.get('kustoQueryShapeCount')} != {announced}"
        )
    if problems:
        report.fail("runtime.kqlShapeParity", "; ".join(problems))
    else:
        report.ok(
            "runtime.kqlShapeParity",
            f"the bundle manifest and both contract fields all state {announced} KQL query shapes",
        )


#: Rank properties are deterministic row numbers, never dense ranks: two rows with
#: the same amount are separated by their stable ID, so a rank is never shared.
_RANK_ATTRIBUTES = ("rankMethod", "rankSort", "rankScope", "rankTieBreak", "rankPartition")

#: Wording that asserts the ranking method. "Dense" is the one that is actively
#: wrong here: a dense rank shares a number between equal amounts, which is the
#: opposite of what Notebook 01 emits.
_DENSE_RANK_WORDING = re.compile(r"\bdense[- ]?rank\b|\bDense (?:amount|origin|destination|row) rank\b", re.I)


def _ontology_property_descriptions(root: Path, context) -> dict[str, str]:
    import json as _json

    metadata = _json.loads(
        (root / "workshop" / f"v{context.version}" / "ontology" / "ontology-semantic-metadata.json").read_text(
            "utf-8"
        )
    )
    descriptions: dict[str, str] = {}
    for entity in metadata["entities"].values():
        for bucket in ("properties", "timeseriesProperties"):
            for name, node in entity.get(bucket, {}).items():
                descriptions[name] = node["semanticEnrichment"]["description"]
    return descriptions


def _validate_kql_daily_query(context, report: Report) -> None:
    """The shipped script must carry the very query the guide prints.

    Chapter 13.3 tells the participant to reconcile a daily amount table. That is
    only possible if the query in the shipped ``.kql`` projects the same two
    aggregates under the same names as the printed one; a ``RawRows``-only shape
    cannot produce the amount column the guide's table lists. The projection is
    compared token by token after whitespace folding, so a reformat is tolerated
    but a different aggregate is not.
    """
    expected_lines = (
        "DonationEvents",
        "| summarize Rows=count(), TotalYen=sum(DonationAmountYen) by UtcDay=bin(DonatedAt, 1d)",
        "| order by UtcDay asc",
    )
    text = context.kql_setup
    normalised = " ".join(text.split())
    wanted = " ".join(" ".join(expected_lines).split())
    if wanted not in normalised:
        report.fail(
            "runtime.kqlDailyQueryParity",
            "the shipped KQL script does not contain the daily distribution query printed in section 13.3",
        )
        return
    # The guide reconciles Rows and TotalYen; both aggregate names must survive.
    missing = [name for name in ("Rows=count()", "TotalYen=sum(DonationAmountYen)") if name not in normalised]
    if missing:
        report.fail("runtime.kqlDailyQueryParity", f"daily query is missing aggregates: {missing}")
        return
    if "RawRows=count()\n    by UtcDay=format_datetime" in text:
        report.fail("runtime.kqlDailyQueryParity", "the retired format_datetime daily shape is still present")
        return
    # A query is not a management command; the count must not have moved.
    commands = sum(1 for line in text.splitlines() if line.startswith("."))
    if commands != len(context.kql_objects):
        report.fail(
            "runtime.kqlDailyQueryParity",
            f"{commands} leading-dot lines but {len(context.kql_objects)} management objects",
        )
        return
    report.ok(
        "runtime.kqlDailyQueryParity",
        f"the shipped daily query matches section 13.3 verbatim and the script still holds {commands} management commands",
    )


def _validate_reseal_determinism(root: Path, report: Report) -> None:
    """The reseal tool reproduces its own output byte for byte.

    Determinism is the property the whole pin chain rests on: if a second run
    changed anything, no digest in the contract could be trusted. Running the
    tool and diffing the sealed set proves it directly, rather than inferring it
    from the fact that nothing looked different.
    """
    paths = _sealed_runtime_paths(root)
    before = {path: path.read_bytes() for path in paths}
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(root / "tools" / "provisioning" / "reseal_runtime.py")],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        report.fail("runtime.resealDeterminism", f"reseal failed: {result.stderr.strip()[:200]}")
        return
    drifted = [path.relative_to(root).as_posix() for path in paths if path.read_bytes() != before[path]]
    if drifted:
        report.fail(
            "runtime.resealDeterminism",
            f"a second reseal changed {len(drifted)} sealed file(s): {drifted[:4]}",
        )
    else:
        report.ok(
            "runtime.resealDeterminism",
            f"a second reseal reproduced all {len(paths)} sealed files byte for byte",
        )


def _sealed_runtime_paths(root: Path) -> list[Path]:
    """Import the reseal tool's own registry so the two can never disagree."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_reseal_runtime", root / "tools" / "provisioning" / "reseal_runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["_reseal_runtime"] = module
    spec.loader.exec_module(module)
    workshop = root / "workshop" / f"v{module.VERSION}"
    return [path for path in module.sealed_paths(root, workshop) if path.is_file()]


def _validate_lf_determinism(root: Path, report: Report) -> None:
    """Every sealed file is LF, so its raw-byte digest is the same on any platform.

    The runtime pins files by the SHA-256 of their bytes. ``Path.write_text``
    translates ``\\n`` to ``os.linesep``, so a reseal on Windows wrote CRLF and
    produced different manifest digests from the same sources than a reseal on
    Linux would - and a participant unpacking the LF payload could not verify the
    CRLF digests at all. Rejecting a carriage return in any sealed file makes that
    class of drift impossible rather than merely unlikely.
    """
    offenders = [
        path.relative_to(root).as_posix() for path in _sealed_runtime_paths(root) if b"\r" in path.read_bytes()
    ]
    if offenders:
        report.fail(
            "runtime.lfDeterminism",
            f"{len(offenders)} sealed file(s) carry CRLF, so their digests are platform dependent: {offenders[:4]}",
        )
    else:
        report.ok(
            "runtime.lfDeterminism",
            f"all {len(_sealed_runtime_paths(root))} sealed runtime files are LF, so every raw-byte digest is reproducible",
        )


def _validate_payload_bundle_parity(root: Path, report: Report) -> None:
    """The embedded payload must reproduce the bundle bytes without translation.

    The provisioner writes ``payload["bundle"][path]`` straight to the workspace
    and the participant then verifies it against the bundle manifest, which pins
    the SHA-256 of the file on disk. If the payload text needed newline
    normalisation to match, that verification would fail for every text file.
    """
    workshop = root / "workshop" / "v2.7.0"
    bundle_root = workshop / "provisioning" / "bundle"
    notebook = json.loads(
        (workshop / "notebooks" / "Notebook_04_Furusato_Provision_Complete_Workshop.ipynb").read_text("utf-8")
    )
    try:
        payload = decode_notebook_payload(notebook)
    except (ValueError, TypeError, KeyError, SyntaxError, gzip.BadGzipFile, EOFError, zlib.error) as error:
        report.fail("runtime.payloadBundleParity", f"Cannot decode the provisioning payload: {error}")
        return
    if not isinstance(payload.get("bundle"), dict) or not all(
        isinstance(name, str) and isinstance(text, str)
        for name, text in payload["bundle"].items()
    ):
        report.fail("runtime.payloadBundleParity", "Provisioning payload bundle must map paths to text")
        return

    mismatched = [
        rel for rel, text in payload["bundle"].items() if text.encode("utf-8") != (bundle_root / rel).read_bytes()
    ]
    if mismatched:
        report.fail(
            "runtime.payloadBundleParity",
            f"{len(mismatched)} payload bundle file(s) do not equal the bytes on disk: {mismatched[:4]}",
        )
        return

    manifest = json.loads((bundle_root / "bundle-manifest.json").read_text("utf-8"))
    stale = [
        entry["path"]
        for entry in manifest["files"]
        if hashlib.sha256((bundle_root / entry["path"]).read_bytes()).hexdigest() != entry["sha256"]
    ]
    if stale:
        report.fail("runtime.payloadBundleParity", f"bundle manifest digests are stale for: {stale[:4]}")
        return
    report.ok(
        "runtime.payloadBundleParity",
        f"all {len(payload['bundle'])} payload bundle files are byte-identical to disk and "
        f"all {len(manifest['files'])} manifest digests reproduce",
    )


def _validate_contract_source_parity(root: Path, report: Report) -> None:
    """Each embedded source text equals the bundle value and its declared digest.

    The contract embeds the description, the instructions and the few-shots so a
    reader can audit what the Agent was told without unpacking the bundle. That
    only helps if the three copies agree, so all three are compared here rather
    than trusting the reseal order.
    """
    workshop = root / "workshop" / "v2.7.0"
    contract = json.loads((workshop / "participant-workspace-contract.json").read_text("utf-8"))
    agent = contract["dataAgent"]

    aliases = [key for key in agent if key.startswith("globalInstructions")]
    retired = {"globalInstructionsChars", "globalInstructionsBytes"} & set(aliases)
    if retired:
        report.fail(
            "runtime.noDuplicateInstructionAliases",
            f"the contract carries retired alias key(s) {sorted(retired)} beside the canonical pair",
        )
    elif {"globalInstructionsCharacters", "globalInstructionsUtf8Bytes"} <= set(aliases):
        report.ok(
            "runtime.noDuplicateInstructionAliases",
            "one canonical pair only: globalInstructionsCharacters / globalInstructionsUtf8Bytes",
        )
    else:
        report.fail("runtime.noDuplicateInstructionAliases", f"canonical count keys missing: {aliases}")

    config = workshop / "provisioning" / "bundle" / "data-agent" / "Files" / "Config" / "published"
    by_type = {}
    for folder in sorted(config.iterdir()):
        if folder.is_dir() and (folder / "datasource.json").is_file():
            definition = json.loads((folder / "datasource.json").read_text("utf-8"))
            by_type[definition["type"]] = definition
    few_shots = json.loads(next(config.glob("lakehouse-tables-*/fewshots.json")).read_text("utf-8"))["fewShots"]

    def sha(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def canonical(value) -> str:
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False, sort_keys=True)

    problems: list[str] = []
    for source in agent["sources"]:
        definition = by_type[source["type"]]
        label = source["type"]
        if source["description"] != definition["userDescription"]:
            problems.append(f"{label}.description differs from the bundle")
        if sha(source["description"]) != source["descriptionSha256"]:
            problems.append(f"{label}.descriptionSha256 does not hash the embedded text")
        if source.get("instructionsSha256") is not None:
            if source["instructions"] != definition["dataSourceInstructions"]:
                problems.append(f"{label}.instructions differs from the bundle")
            if sha(source["instructions"]) != source["instructionsSha256"]:
                problems.append(f"{label}.instructionsSha256 does not hash the embedded text")
        if source.get("fewShotsSha256") is not None:
            if source["fewShots"] != few_shots:
                problems.append(f"{label}.fewShots differs from the bundle")
            if sha(canonical(source["fewShots"])) != source["fewShotsSha256"]:
                problems.append(f"{label}.fewShotsSha256 does not hash the embedded array")
    if problems:
        report.fail("runtime.contractSourceParity", f"{len(problems)} problem(s): {problems[:4]}")
    else:
        report.ok(
            "runtime.contractSourceParity",
            f"all {len(agent['sources'])} contract sources embed the bundle text and hash it correctly",
        )


def _validate_rank_description_parity(root: Path, context, report: Report) -> None:
    """The Agent must read one ranking definition, not two that disagree.

    A rank column is described twice: once as an Ontology property and once as a
    selected Lakehouse column in the Data Agent source definition. Those are the
    same measurement, so the two sentences have to be the same sentence. When they
    drift, the Agent is told both that equal amounts share a rank (dense) and that
    they do not (row_number), and nothing in the prompt resolves the contradiction.
    """
    ontology = _ontology_property_descriptions(root, context)
    mismatched: list[str] = []
    checked: list[str] = []

    def visit(node: dict, source: str) -> None:
        name = str(node.get("display_name") or "")
        if name.endswith("Rank") and "description" in node:
            wanted = ontology.get(name)
            if wanted is None:
                mismatched.append(f"{source}.{name} has no Ontology property to mirror")
            else:
                checked.append(f"{source}.{name}")
                if node.get("description") != wanted:
                    mismatched.append(f"{source}.{name} differs from the Ontology description")
        for child in node.get("children", []) or []:
            visit(child, source)

    for source_type, payload in sorted(context.agent_sources.items()):
        for element in payload.get("elements", []) or []:
            visit(element, source_type)

    if mismatched:
        report.fail("runtime.rankDescriptionParity", "; ".join(sorted(set(mismatched))))
    else:
        report.ok(
            "runtime.rankDescriptionParity",
            f"all {len(checked)} Data Agent rank elements repeat the Ontology description verbatim",
        )

    # No approved surface may describe a row_number rank as a dense rank.
    surfaces: list[tuple[str, str]] = [("global instructions", context.agent_instructions)]
    for source_type, payload in sorted(context.agent_sources.items()):
        surfaces.append((f"{source_type} description", payload.get("userDescription") or ""))
        surfaces.append((f"{source_type} instructions", payload.get("dataSourceInstructions") or ""))
        surfaces.append((f"{source_type} elements", json.dumps(payload.get("elements", []), ensure_ascii=False)))
    for index, shot in enumerate(context.agent_fewshots, start=1):
        surfaces.append((f"few-shot {index}", f"{shot.get('question', '')} {shot.get('query', '')}"))
    dense = [label for label, text in surfaces if text and _DENSE_RANK_WORDING.search(text)]
    if dense:
        report.fail("runtime.noDenseRankWording", f"dense-rank wording survives in: {sorted(set(dense))}")
    else:
        report.ok(
            "runtime.noDenseRankWording",
            f"none of the {len(surfaces)} Data Agent surfaces calls a row_number rank a dense rank",
        )


def _validate_ontology_semantics(root: Path, context, report: Report) -> None:
    """Ontology enrichment invariants the guide, the checklist and NB02/NB03 mirror."""
    import json as _json

    workshop = root / "workshop" / f"v{context.version}"
    metadata = _json.loads((workshop / "ontology" / "ontology-semantic-metadata.json").read_text("utf-8"))

    ranks: dict[str, dict] = {}
    for entity in metadata["entities"].values():
        for name, node in entity.get("properties", {}).items():
            if name.endswith("Rank"):
                ranks[name] = node["semanticEnrichment"]
    dense = sorted(name for name, node in ranks.items() if "Dense" in node["description"])
    missing = sorted(
        f"{name}.{attribute}"
        for name, node in ranks.items()
        for attribute in _RANK_ATTRIBUTES
        if attribute not in node.get("customAttributes", {})
    )
    if dense or missing:
        report.fail(
            "runtime.rankSemantics",
            f"dense wording={dense} missing attributes={missing}",
        )
    else:
        report.ok(
            "runtime.rankSemantics",
            f"all {len(ranks)} rank properties are deterministic row numbers with a declared sort and tie-break",
        )

    keys = {
        "MunCategoryMetricId": "{MunicipalityId}-{CategoryId:02}",
        "PrefCategoryMetricId": "{PrefectureId:02}-{CategoryId:02}",
        "PrefDonationFlowId": "{ResidencePrefectureId:02}-{RecipientPrefectureId:02}",
    }
    key_problems = []
    for entity in metadata["entities"].values():
        for name, node in entity.get("properties", {}).items():
            if name not in keys:
                continue
            attributes = node["semanticEnrichment"].get("customAttributes", {})
            if attributes.get("keyEncoding") != keys[name]:
                key_problems.append(f"{name} keyEncoding={attributes.get('keyEncoding')!r}")
            if "entity type" not in node["semanticEnrichment"]["description"]:
                key_problems.append(f"{name} does not say the entity type disambiguates the key")
    if key_problems:
        report.fail("runtime.compositeKeys", "; ".join(key_problems))
    else:
        report.ok(
            "runtime.compositeKeys",
            f"all {len(keys)} composite metric keys document their encoding and their ambiguity",
        )

    series = metadata["entities"]["Municipality"]["timeseriesProperties"]["IncomingDonationAmountYen"]
    attributes = series["semanticEnrichment"].get("customAttributes", {})
    deduplication = attributes.get("deduplication", "")
    if deduplication.startswith("none") and "duplicate EventIDs retained" in deduplication:
        report.ok(
            "runtime.timeSeriesBoundary",
            "the time-series property declares deduplication = none with duplicates retained",
        )
    else:
        report.fail("runtime.timeSeriesBoundary", f"deduplication={deduplication!r}")

    # Optionality follows the data, not a house style: a source that always emits
    # an edge is one-to-many, and only a source that can emit none is zero-to-many.
    # Test-OntologyCardinality.ps1 recomputes both counts from the seed CSVs.
    optional = {
        "DonorMadeDonation": "zero-to-many from Donor",
        "MunHasCategoryMetric": "zero-to-many from Municipality",
        "MunicipalityCatalogsGift": "one-to-many from Municipality",
        "PrefHasCategoryMetric": "one-to-many from Prefecture",
        "ResidencePrefHasFlow": "one-to-many from Prefecture",
        "SupplierProvidesGift": "many-to-many",
    }
    vocabulary = []
    for name, prefix in optional.items():
        declared = metadata["relationships"][name]["semanticEnrichment"]["customAttributes"]["cardinality"]
        if not declared.startswith(prefix):
            vocabulary.append(f"{name}={declared!r}")
    participation = sorted(
        name
        for name, node in metadata["relationships"].items()
        if not {"sourceParticipation", "targetParticipation"}
        <= set(node["semanticEnrichment"].get("customAttributes", {}))
    )
    if vocabulary or participation:
        report.fail(
            "runtime.cardinalityVocabulary",
            f"wrong optionality={vocabulary} missing participation={participation}",
        )
    else:
        report.ok(
            "runtime.cardinalityVocabulary",
            f"all {len(metadata['relationships'])} relationships declare optionality and participation",
        )

    guard = metadata["relationships"]["MunicipalityCatalogsGift"]["semanticEnrichment"]
    if "dataCoincidenceWarning" in guard.get("customAttributes", {}):
        report.ok(
            "runtime.catalogGuardDisclosure",
            "MunicipalityCatalogsGift discloses that the forbidden path coincides in this dataset",
        )
    else:
        report.fail(
            "runtime.catalogGuardDisclosure",
            "MunicipalityCatalogsGift does not disclose the synthetic-data coincidence",
        )

    layer = metadata["entities"]["Donation"]["properties"]["DonationDataLayer"]["semanticEnrichment"]
    if layer.get("customAttributes", {}).get("constantByDesign") == "true":
        report.ok(
            "runtime.constantLayerProperty",
            "DonationDataLayer is documented as a deliberate constant boundary marker",
        )
    else:
        report.fail("runtime.constantLayerProperty", "DonationDataLayer does not declare constantByDesign")

    template = _json.loads(
        (workshop / "ontology" / "ontology-full-definition-template.json").read_text("utf-8")
    )
    bound: set[str] = set()
    kusto: set[str] = set()
    contextual: set[str] = set()
    for part in template["parts"]:
        if "/DataBindings/" in part["path"]:
            properties = part["content"]["dataBindingConfiguration"]["sourceTableProperties"]
            if properties.get("sourceType") == "KustoTable":
                kusto.add(properties["sourceTableName"])
            else:
                bound.add(properties["sourceTableName"])
        elif "/Contextualizations/" in part["path"]:
            contextual.add(part["content"]["dataBindingTable"]["sourceTableName"])
    declared_lakehouse = set(template["expectedSourceTables"]["lakehouse"])
    declared_eventhouse = set(template["expectedSourceTables"]["eventhouse"])
    problems = []
    if declared_lakehouse != bound | contextual:
        problems.append(f"lakehouse declared={sorted(declared_lakehouse)} actual={sorted(bound | contextual)}")
    if declared_eventhouse != kusto:
        problems.append(f"eventhouse declared={sorted(declared_eventhouse)} actual={sorted(kusto)}")
    if kusto != {"DonationEvents"}:
        problems.append(f"time-series binding reads {sorted(kusto)}, not the raw DonationEvents table")
    if problems:
        report.fail("runtime.ontologySourceTables", "; ".join(problems))
    else:
        report.ok(
            "runtime.ontologySourceTables",
            f"{len(bound)} bound entity tables + {len(contextual - bound)} contextualization-only table "
            f"+ raw {sorted(kusto)[0]} match expectedSourceTables",
        )


def _check_workbook_repair_free(path: Path, report: Report) -> None:
    """Reject the package shapes Excel answers with a repair prompt.

    Excel repairs a workbook when a part is not well-formed, when it carries a
    revision element the file has no revision store for, or when it declares a
    namespace prefix that nothing uses and nothing declares as ignorable. None of
    those is visible through openpyxl, so the package is inspected directly.
    """
    import xml.etree.ElementTree as ElementTree
    import zipfile

    problems: list[str] = []
    with zipfile.ZipFile(path) as archive:
        parts = {
            name: archive.read(name)
            for name in archive.namelist()
            if name.endswith((".xml", ".rels"))
        }
    for name, blob in sorted(parts.items()):
        try:
            ElementTree.fromstring(blob)
        except ElementTree.ParseError as error:
            problems.append(f"{name} is not well-formed: {error}")
            continue
        text = blob.decode("utf-8", "ignore")
        if "revisionPtr" in text:
            problems.append(f"{name} still carries a revisionPtr element")
        declared = set(re.findall(r'xmlns:([A-Za-z0-9_]+)="', text))
        ignorable = set(" ".join(re.findall(r'mc:Ignorable="([^"]*)"', text)).split())
        body = re.sub(r'\s+xmlns:[A-Za-z0-9_]+="[^"]*"', "", text)
        used = set(re.findall(r"<\s*/?\s*([A-Za-z0-9_]+):", body))
        used |= set(re.findall(r'\s([A-Za-z0-9_]+):[A-Za-z0-9_]+\s*=\s*"', body))
        dangling = sorted(declared - used - ignorable)
        if dangling:
            problems.append(f"{name} declares unused namespace prefixes {dangling}")
    if problems:
        report.fail("workbook.repairFree", "; ".join(problems[:4]))
    else:
        report.ok(
            "workbook.repairFree",
            f"all {len(parts)} XML parts parse, carry no revision residue and declare no unused prefix",
        )


def validate_visual(root: Path, out_dir: Path, context, edition: str = "") -> Report:
    """Gate the screenshots on paper: resolution, flat voids, and blank frames.

    Three defects survive every text check because they are properties of the
    pixels, not of the content model: a capture stretched so far that its UI type
    is unreadable, a capture that is a single flat colour because the screen had
    not painted, and a capture whose only content is the surrounding chrome. Each
    one prints a caption that promises evidence above an image that carries none.
    """
    import hashlib
    import io
    import re as _re
    import zipfile

    from PIL import Image

    report = Report(target="docs (screenshot quality)")
    path = out_dir / deliverable_names(context.version, edition).participant
    if not path.is_file():
        report.fail("visual.guideMissing", f"{path} not found")
        return report

    with zipfile.ZipFile(path) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
        rels = archive.read("word/_rels/document.xml.rels").decode("utf-8")
        targets = dict(_re.findall(r'Id="([^"]+)"[^>]*Target="(media/[^"]+)"', rels))
        media = {
            name: archive.read(name)
            for name in archive.namelist()
            if name.startswith("word/media/")
        }

    placements = _re.findall(r'<wp:extent cx="(\d+)" cy="(\d+)"/>.*?r:embed="([^"]+)"', document, _re.S)
    low_dpi: list[str] = []
    flat: list[str] = []
    measured = 0
    for cx, cy, rid in placements:
        target = targets.get(rid)
        blob = media.get(f"word/{target}") if target else None
        if not blob:
            continue
        image = Image.open(io.BytesIO(blob)).convert("RGB")
        printed_inches = int(cx) / 914400
        if printed_inches <= 0:
            continue
        measured += 1
        dpi = image.width / printed_inches
        if dpi < docx_kit.MIN_FIGURE_DPI:
            low_dpi.append(f"{target} at {dpi:.0f} dpi")
        sample = image.resize((min(image.width, 300), min(image.height, 300)))
        colours = sorted(sample.getcolors(maxcolors=1 << 24) or [], reverse=True)
        if colours:
            share = colours[0][0] / (sample.size[0] * sample.size[1])
            if share >= FLAT_VOID_SHARE:
                flat.append(f"{target} is {share:.1%} one colour")

    if low_dpi:
        report.fail(
            "visual.screenshotDpi",
            f"{len(low_dpi)} figure(s) print below {docx_kit.MIN_FIGURE_DPI} dpi: {low_dpi[:5]}",
        )
    else:
        report.ok(
            "visual.screenshotDpi",
            f"all {measured} placed images print at {docx_kit.MIN_FIGURE_DPI} dpi or better",
        )
    if flat:
        report.fail("visual.flatVoid", f"{len(flat)} blank or flat capture(s): {flat[:5]}")
    else:
        report.ok(
            "visual.flatVoid",
            f"no placed image is more than {FLAT_VOID_SHARE:.0%} a single colour",
        )

    _check_unsettled_captures(report, document, targets, media)
    _check_repaired_captures(report, root)
    _check_capture_privacy(report, root, document)

    carrier = StyleCarrier.archive_path(root)
    with zipfile.ZipFile(carrier) as archive:
        tags = {
            name.split("/")[-1].removesuffix(".png")
            for name in archive.namelist()
            if name.startswith("screenshots/")
        }
        if context.is_unified_guide:
            from furusato_docs.capture_policy import capture_problems

            registry = json.loads(
                (root / "tools" / "docs" / "assets" / "unified-ui-captures.json").read_text("utf-8")
            )
            entries = registry["captures"]
            embedded_hashes = {hashlib.sha256(blob).hexdigest() for blob in media.values()}
            experimental = context.guide_agent_stage_config.get("experimental", {})
            problems = capture_problems(
                registry, context.guide_agent_instructions,
                {
                    tag: hashlib.sha256(archive.read(f"screenshots/{tag}.png")).hexdigest()
                    for tag in entries if tag in tags
                },
                embedded_hashes,
                code_interpreter_enabled=experimental.get("codeInterpreterEnabled") is True,
                preview_enabled=experimental.get("enableExperimentalFeatures") is True,
            )
            if problems:
                report.fail("visual.unifiedUiCaptureProvenance", str(problems))
            else:
                detail = (
                    "unchanged CI illustration verified; obsolete configuration images are not embedded"
                    if registry.get("usage") else
                    "all three unchanged real-UI captures match the profile, registry, carrier and Word"
                )
                report.ok("visual.unifiedUiCaptureProvenance", detail)
    retired = sorted(tags & set(guide_handson.RETIRED_SCREENSHOTS))
    if retired:
        report.fail("visual.retiredNotShipped", f"the carrier still ships retired captures: {retired}")
    else:
        report.ok(
            "visual.retiredNotShipped",
            f"none of the {len(guide_handson.RETIRED_SCREENSHOTS)} retired captures is in the carrier",
        )
    return report


#: A UI capture is never a single colour across the frame. Anything at or above
#: this share is a screenshot the browser had not painted when it was taken.
FLAT_VOID_SHARE = 0.97

#: Personal or environment strings that must never survive into a shipped
#: capture. Checked by OCR when an engine is installed, and always checked
#: against the captions and alt text, which are authored rather than captured.
PRIVACY_TERMS = (    "Jiayi",
    "Yang",
    "ByScout",
    "Premium Per User",
    "only use",
)


def _check_repaired_captures(report: Report, root: Path) -> None:
    """The carrier still holds the repaired captures, byte for byte.

    Four Instances captures and the Activator Rules capture were restored from an
    earlier commit, and three more were redacted. All of that lives in the binary
    carrier, so a regeneration of that archive silently reverts it - which is
    exactly how the blank Rules pane came back. Pinning the repaired digests turns
    that regression into a build failure instead of a caption that lies.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_repair_captures", root / "tools" / "docs" / "repair_captures.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["_repair_captures"] = module
    spec.loader.exec_module(module)

    import zipfile as _zipfile

    with _zipfile.ZipFile(module.carrier_path(root)) as archive:
        shipped = {name: archive.read(name) for name in archive.namelist()}
    drift = []
    for repair in module.REPAIRS:
        name = f"screenshots/{repair.tag}.png"
        if name not in shipped:
            drift.append(f"{repair.tag}: missing")
            continue
        digest = hashlib.sha256(shipped[name]).hexdigest()
        if digest != repair.digest:
            drift.append(f"{repair.tag}: {digest[:12]} != pinned {repair.digest[:12]} ({repair.reason})")
    if drift:
        report.fail(
            "visual.repairedCaptures",
            f"{len(drift)} repaired capture(s) reverted; run tools/docs/repair_captures.py: {drift[:4]}",
        )
    else:
        report.ok(
            "visual.repairedCaptures",
            f"all {len(module.REPAIRS)} repaired captures are present at their pinned digests",
        )


def _check_capture_privacy(report: Report, root: Path, document: str) -> None:
    """No shipped capture may name a person, a tenant folder or a licence state.

    The authored layer - captions and alt text - is checked every run because it
    is plain text. The pixels are checked too when an OCR engine is available;
    without one the redaction is verified by the flat-fill regions the redaction
    pass writes, which the carrier hash pins.
    """
    import io as _io
    import re as _re
    import zipfile as _zipfile

    from PIL import Image

    prose = _re.sub(r"<[^>]+>", "", document)
    named = sorted({term for term in PRIVACY_TERMS if term in prose})
    if named:
        report.fail("visual.captionPrivacy", f"captions or alt text name: {named}")
    else:
        report.ok(
            "visual.captionPrivacy",
            f"no caption or alt text carries any of the {len(PRIVACY_TERMS)} personal or environment terms",
        )

    carrier = StyleCarrier.archive_path(root)
    with _zipfile.ZipFile(carrier) as archive:
        shots = {
            name: archive.read(name) for name in archive.namelist() if name.startswith("screenshots/")
        }
    leaked: list[str] = []
    scanned = 0
    for name, blob in sorted(shots.items()):
        text = _ocr_text(Image.open(_io.BytesIO(blob)).convert("RGB"))
        if text is None:
            break
        scanned += 1
        for term in PRIVACY_TERMS:
            if term in text:
                leaked.append(f"{name.split('/')[-1]}: {term}")
    if leaked:
        report.fail("visual.capturePrivacy", f"{len(leaked)} capture(s) still show personal detail: {leaked[:5]}")
    elif scanned:
        report.ok("visual.capturePrivacy", f"OCR found no personal detail in {scanned} captures")
    else:
        report.ok(
            "visual.capturePrivacy",
            "no OCR engine installed; the redaction pass and the pinned carrier hash carry this check",
        )



#: Captions whose evidence is a populated pane: an Instances grid, an Activator
#: rule list, or any caption stating a count. These must clear the strict floors.
EVIDENCE_CAPTION_TERMS = ("Instances", "件数", "rule", "Rules", "ルール", "Running")

#: Share of the body band that may be one uninterrupted run of empty rows.
#: A dialog capture is legitimately mostly white and reaches about 78 %; only a
#: frame that never painted reaches 90 %.
MAX_FLAT_BODY_RUN = 0.90

#: An evidence capture is held to a far tighter band, and to a hard ink floor.
#: The blank Activator frame measured 0.17 % ink with a 56 % band, which slipped
#: past a band-only test; the settled capture measures 1.29 % with 7 %.
MAX_FLAT_EVIDENCE_RUN = 0.40
MIN_EVIDENCE_INK = 0.01

#: Mean share of dark pixels a populated data grid carries in its body band. The
#: four spinner captures measured 0.034 %, the settled ones 2.0 % to 3.8 %.
MIN_GRID_INK = 0.003


def _body_band_metrics(image) -> tuple[float, float]:
    """Longest uninterrupted empty run, and mean ink, over the body of a capture.

    The top of every Fabric capture is chrome - breadcrumb, tab strip, count -
    which paints even while the grid below is still loading. Whole-frame colour
    share therefore misses a spinner: the four Instances captures were 98.9 %
    empty below the tabs yet only 96 % one colour overall, just under the flat
    gate. Measuring the band below the chrome is what separates the two.
    """
    grey = image.convert("L")
    width, height = grey.size
    pixels = grey.load()
    top = int(height * 0.18)
    columns = range(0, width, 4)
    rows = [
        sum(1 for x in columns if pixels[x, y] < 200) / len(columns) for y in range(top, height)
    ]
    if not rows:
        return 0.0, 1.0
    longest = current = 0
    for density in rows:
        current = current + 1 if density < 0.01 else 0
        longest = max(longest, current)
    return longest / len(rows), sum(rows) / len(rows)


def _ocr_text(image) -> str | None:
    """Read a capture when an OCR engine is installed; otherwise say so."""
    try:
        import pytesseract
    except ImportError:
        return None
    try:
        return pytesseract.image_to_string(image)
    except Exception:
        return None


def _check_unsettled_captures(report: Report, document: str, targets: dict, media: dict) -> None:
    """No figure may promise a populated grid above a capture that has none.

    A caption that states an exact instance count is a claim about the pixels
    above it. This pairs each placed image with the caption that follows it and
    rejects the combination that actually shipped: "件数 1,741 を確認する" over a
    frame whose only content was a Loading spinner.
    """
    import io as _io
    import re as _re

    from PIL import Image

    sequence = _re.findall(r'r:embed="(rId\d+)"|図\s*(\d+)\u3000([^<]{0,120})', document)
    pending: str | None = None
    pairs: list[tuple[str, str, str]] = []
    for rid, number, caption in sequence:
        if rid:
            pending = rid
        elif pending:
            pairs.append((pending, number, caption))
            pending = None

    unsettled: list[str] = []
    loading: list[str] = []
    checked = 0
    ocr_used = False
    for rid, number, caption in pairs:
        target = targets.get(rid)
        blob = media.get(f"word/{target}") if target else None
        if not blob:
            continue
        image = Image.open(_io.BytesIO(blob)).convert("RGB")
        flat_run, ink = _body_band_metrics(image)
        checked += 1
        claims_grid = any(term in caption for term in EVIDENCE_CAPTION_TERMS)
        limit = MAX_FLAT_EVIDENCE_RUN if claims_grid else MAX_FLAT_BODY_RUN
        floor = MIN_EVIDENCE_INK if claims_grid else MIN_GRID_INK
        if flat_run >= limit:
            unsettled.append(f"figure {number} body is {flat_run:.0%} one empty run (limit {limit:.0%})")
        elif claims_grid and ink < floor:
            unsettled.append(f"figure {number} promises evidence but carries {ink:.3%} ink (floor {floor:.0%})")
        text = _ocr_text(image) if claims_grid else None
        if text is not None:
            ocr_used = True
            if "Loading" in text:
                loading.append(f"figure {number} still shows Loading")

    if unsettled:
        report.fail("visual.settledCaptures", f"{len(unsettled)} unsettled capture(s): {unsettled[:5]}")
    else:
        report.ok(
            "visual.settledCaptures",
            f"all {checked} placed captures paint their body: no run over {MAX_FLAT_BODY_RUN:.0%} empty "
            f"({MAX_FLAT_EVIDENCE_RUN:.0%} and at least {MIN_EVIDENCE_INK:.0%} ink where the caption "
            f"promises grid or rule evidence)",
        )
    if loading:
        report.fail("visual.noLoadingText", f"OCR found loading text in: {loading[:5]}")
    elif ocr_used:
        report.ok("visual.noLoadingText", "OCR found no loading text in any grid capture")
    else:
        report.ok(
            "visual.noLoadingText",
            "no OCR engine installed; the body-band metrics above carry this check",
        )


#: Printed scale floor for the reference sheets. At 85% a 10 pt body prints at
#: 8.5 pt, comfortably above the 7 pt readability floor on A4.
MIN_PRINT_SCALE = 85

#: Column A on a notebook sheet must hold the string "File SHA-256" whole, which
#: is thirteen characters in the default font.
MIN_NOTEBOOK_LABEL_WIDTH = 13


def validate_final_runtime(root: Path, context, facts) -> Report:
    """Pin the independently revalidated final runtime facts."""
    import hashlib
    import json as _json

    report = Report(target=f"workshop/v{context.version} (final approved facts)")
    workshop = root / "workshop" / f"v{context.version}"
    expected = FINAL_RUNTIME

    raw = (workshop / "data-agent" / "agent-instructions.txt").read_bytes()
    text = raw.decode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    measured = {
        "sha256": (digest, expected["agentInstructionsSha256"]),
        "chars": (len(text), expected["agentInstructionsChars"]),
        "bytes": (len(raw), expected["agentInstructionsBytes"]),
    }
    drift = [f"{name}: {actual!r} != {want!r}" for name, (actual, want) in measured.items() if actual != want]
    if drift:
        report.fail("final.agentInstructions", "; ".join(drift))
    else:
        report.ok(
            "final.agentInstructions",
            f"{len(text)} chars / {len(raw)} UTF-8 bytes / sha256 {digest[:16]}… as approved",
        )

    # Every on-disk mirror of the global instructions must be byte-identical.
    mirrors: list[str] = []

    def scan(value, origin: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                scan(item, f"{origin}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                scan(item, f"{origin}[{index}]")
        elif isinstance(value, str) and hashlib.sha256(value.encode("utf-8")).hexdigest() == digest:
            mirrors.append(origin)

    mirrors.append("data-agent/agent-instructions.txt")
    for path in sorted(workshop.rglob("*.json")):
        scan(_json.loads(path.read_text(encoding="utf-8")), path.relative_to(workshop).as_posix())
    if len(mirrors) == expected["agentInstructionMirrors"]:
        report.ok(
            "final.instructionMirrors",
            f"{len(mirrors)} identical mirrors: {', '.join(sorted(mirrors))}",
        )
    else:
        report.fail(
            "final.instructionMirrors",
            f"expected {expected['agentInstructionMirrors']} identical mirrors, found {len(mirrors)}: {sorted(mirrors)}",
        )

    automation = context.workspace_contract["workshopProvisioningAutomation"]
    payload_manifest = _json.loads((workshop / "provisioning" / "payload-manifest.json").read_text("utf-8"))
    payload_values = {automation.get("payloadSha256"), payload_manifest.get("payloadSha256")}
    if payload_values == {expected["payloadSha256"]}:
        report.ok("final.payloadSha256", f"contract and payload manifest both carry {expected['payloadSha256'][:16]}…")
    else:
        report.fail("final.payloadSha256", f"payload SHA drift: {payload_values}")

    published = workshop / "provisioning" / "bundle" / "data-agent" / "Files" / "Config" / "published"
    stage = _json.loads((published / "stage_config.json").read_text("utf-8"))
    checks = [
        ("Lakehouse few-shots", len(context.agent_fewshots), expected["lakehouseFewShots"]),
        ("Data Agent sources", len(context.agent_sources), expected["dataAgentSources"]),
        (
            "codeInterpreterEnabled",
            (stage.get("experimental") or {}).get("codeInterpreterEnabled"),
            expected["codeInterpreterEnabled"],
        ),
    ]
    calendar = facts.observation.calendar
    observation = facts.observation
    checks += [
        ("increment UTC days", calendar.utc_day_count, expected["incrementUtcDays"]),
        ("min rows per UTC day", calendar.min_rows, expected["incrementMinRowsPerDay"]),
        ("max rows per UTC day", calendar.max_rows, expected["incrementMaxRowsPerDay"]),
        (
            "curated MV leader municipality",
            observation.top_observed_municipality_id,
            expected["curatedLeaderMunicipalityId"],
        ),
        ("curated MV leader observations", observation.top_observed_count, expected["curatedLeaderObservations"]),
        ("curated MV leader amount", observation.top_observed_amount_yen, expected["curatedLeaderAmountYen"]),
    ]
    mismatched = [f"{name}: {actual!r} != {want!r}" for name, actual, want in checks if actual != want]
    if mismatched:
        report.fail("final.approvedValues", "; ".join(mismatched))
    else:
        report.ok("final.approvedValues", f"all {len(checks)} approved runtime values match")

    behaviours = {
        "multi-source up to three": "up to all three",
        "compose by stable ID": "compose the results only by stable ID",
        "exact entity-ID digits": "exact stable ID",
        "popularity ambiguity": "人気",
        "activity ambiguity": "一番動いた",
        "safe wealth language": "金持ち",
        "no-evidence refusal": "承認済みソースから確認できませんでした。",
    }
    absent = [label for label, needle in behaviours.items() if needle not in text]
    if absent:
        report.fail("final.instructionBehaviours", f"missing from the final instructions: {absent}")
    else:
        report.ok("final.instructionBehaviours", f"all {len(behaviours)} approved behaviours present")

    contract = context.workspace_contract
    if "evaluation" in contract:
        report.fail("final.noEvaluationBlock", "the participant contract still carries an evaluation block")
    else:
        report.ok("final.noEvaluationBlock", "the participant contract carries no evaluation block")

    residuals: list[str] = []
    for path in sorted(workshop.rglob("*")):
        if not path.is_file() or path.suffix not in (".json", ".txt", ".kql", ".ipynb"):
            continue
        blob = path.read_text(encoding="utf-8", errors="ignore")
        for needle in ("Eventstream", "core-events_5", "HighValueDonationRule", "CREATE_EVENTSTREAM"):
            if needle in blob:
                residuals.append(f"{path.relative_to(workshop).as_posix()}:{needle}")
    if residuals:
        report.fail("final.noSupersededConcepts", f"runtime still carries: {sorted(set(residuals))}")
    else:
        report.ok(
            "final.noSupersededConcepts",
            "no Eventstream, Core-5 or high-value notification residue anywhere in the runtime",
        )

    objects = context.kql_objects
    names = tuple(entry.name for entry in objects)
    if len(objects) != expected["kqlManagementCommands"]:
        report.fail(
            "final.kqlManagementCommands",
            f"expected {expected['kqlManagementCommands']} management commands, found {len(objects)}: {list(names)}",
        )
    elif not set(expected["kqlManagementObjects"]) <= set(names):
        report.fail("final.kqlManagementCommands", f"unexpected object set: {list(names)}")
    else:
        report.ok(
            "final.kqlManagementCommands",
            f"the setup script creates exactly {len(objects)} management objects and no projection layer",
        )

    _validate_kql_daily_query(context, report)

    declared = sum(1 for item in context.relationships if item.cardinality)
    if declared != expected["relationshipCardinalitiesDeclared"]:
        report.fail(
            "final.relationshipCardinality",
            f"{declared} / {len(context.relationships)} relationships declare a cardinality",
        )
    else:
        report.ok(
            "final.relationshipCardinality",
            f"{declared} / {len(context.relationships)} relationships declare a cardinality",
        )

    baked = []
    figure_pattern = re.compile(r"(図\s*[0-9]|Figure\s*[0-9]|Fig\.?\s*[0-9]|Diagram\s*[0-9]|図表\s*[0-9])")
    for key, entry in sorted(context.diagrams.items()):
        svg = entry.get("svg")
        if svg is None:
            continue
        found = figure_pattern.findall(svg.read_text(encoding="utf-8"))
        if found:
            baked.append(f"{key}:{sorted(set(found))}")
    if baked:
        report.fail("final.diagramNumbering", f"diagrams still bake in a figure number: {baked}")
    else:
        report.ok(
            "final.diagramNumbering",
            f"none of the {len(context.diagrams)} diagrams bake in a figure number",
        )

    assets = sorted((root / "docs" / "assets" / f"v{context.version}").iterdir())
    measured = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in assets}
    if len(measured) != expected["diagramAssets"]:
        report.fail(
            "final.diagramAssets",
            f"expected {expected['diagramAssets']} diagram assets, found {len(measured)}",
        )
    else:
        drifted = [
            name
            for name, digest in sorted(expected["diagramSha256"].items())
            if measured.get(name) != digest
        ]
        if drifted:
            report.fail(
                "final.diagramAssets",
                f"diagram assets changed since the approved set: {drifted}",
            )
        else:
            report.ok(
                "final.diagramAssets",
                f"all {len(measured)} diagram assets match the approved final set byte for byte",
            )

    _validate_supplied_material_provenance(root, context, report)

    return report


#: Every host the tracked sources may reference. Three are first-party Microsoft
#: documentation, the rest are XML/JSON namespaces, Fabric API endpoints, the
#: repository's own CI and licence hosts, and the reserved example domain. A host
#: outside this set means unverified material was cited as if it were published.
ALLOWED_HOSTS = frozenset(
    {
        "learn.microsoft.com",
        "azure.microsoft.com",
        "www.microsoft.com",
        "go.microsoft.com",
        "developer.microsoft.com",
        "api.fabric.microsoft.com",
        "app.fabric.microsoft.com",
        "onelake.dfs.fabric.microsoft.com",
        "database.windows.net",  # Microsoft SQL token audience, not a document source.
        "github.com",
        "raw.githubusercontent.com",
        "code.claude.com",
        "opensource.org",
        "www.w3.org",
        "schemas.openxmlformats.org",
        "schemas.microsoft.com",
        "purl.org",
        "purl.oclc.org",  # ISO Strict OOXML namespace.
        "json-schema.org",
        "example.invalid",
    }
)
PROVENANCE_FIXTURE_HOSTS = {
    "tools/data-agent/tests/test_reference_models.py": {"abc.datawarehouse.fabric.microsoft.com"},
    "tools/html/tests/test_optional_exercise_gate.py": {
        "database.windows.net.evil.invalid", "evil.invalid",
    },
    "tools/provisioning/test_reference_kql.py": {"synthetic.invalid"},
    "tools/provisioning/test_reference_packaging.py": {"fixture.kusto.fabric.microsoft.com"},
    "tools/provisioning/test_reference_sql.py": {"discovered-example.datawarehouse.fabric.microsoft.com"},
}
_URL_HOST = re.compile(r"https?://([A-Za-z0-9.-]+)")

#: Markings and identifiers that only appear on internally-supplied material.
#: None of them may enter the repository in any tracked file. Only the validators
#: and the negative-test module that deliberately plants these strings may own them.
SUPPLIED_MATERIAL_MARKERS = (
    re.compile(r"Microsoft Confidential", re.I),
    re.compile(r"\bInternal Only\b", re.I),
    re.compile(r"\bDo Not Distribute\b", re.I),
)
MARKER_PATTERN_OWNERS = frozenset(
    {
        "tools/docs/validate_docs.py",
        "tools/docs/furusato_docs/quality.py",
        "tools/docs/tests/test_preview_material_gates.py",
        "tools/html/validate_html.py",
    }
)

#: Diagram assets are author-created vector art. A raster payload, an external
#: reference or a missing accessible name would mean a screenshot was pasted in.
_SVG_RASTER = re.compile(r"<image\b|data:image/", re.I)
_SVG_EXTERNAL = re.compile(r'(?:href|src)\s*=\s*"(?!#)(?!data:)[^"]+"', re.I)


def _validate_supplied_material_provenance(root: Path, context, report: Report) -> None:
    """Nothing from the supplied preview material may be redistributed.

    The v2.7.0 documentation update was written from unpublished pages that carry
    confidentiality markings and internal environment identifiers. The substance
    was re-expressed in original wording; none of the artefacts were copied. This
    gate proves that on the tracked tree rather than on a promise: no marking, no
    third-party documentation host, and every diagram still author-created vector
    art whose PNG matches its SVG geometry.
    """
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=False
    )
    names = [line for line in tracked.stdout.splitlines() if line.strip()]
    if not names:
        report.warn("provenance.trackedFiles", "git ls-files produced nothing; provenance scan skipped")
        return

    suspicious_names = [
        name
        for name in names
        if re.search(r"(?:confidential|internal[-_]only|ontology[-_]agent[-_](?:preview|docs|pages))", name, re.I)
    ]
    if suspicious_names:
        report.fail("provenance.noSuppliedFilenames", f"{suspicious_names[:5]}")
    else:
        report.ok(
            "provenance.noSuppliedFilenames",
            f"none of the {len(names)} tracked paths look like supplied preview material",
        )

    text_suffixes = {".py", ".md", ".json", ".txt", ".ps1", ".kql", ".ipynb", ".svg", ".html", ".yml", ".yaml"}
    markings: list[str] = []
    hosts: list[str] = []
    for name in names:
        path = root / name
        if path.suffix.lower() not in text_suffixes or not path.is_file():
            continue
        blob = path.read_text(encoding="utf-8", errors="ignore")
        if name not in MARKER_PATTERN_OWNERS:
            markings += [f"{name}: {p.pattern}" for p in SUPPLIED_MATERIAL_MARKERS if p.search(blob)]
        allowed_hosts = ALLOWED_HOSTS | PROVENANCE_FIXTURE_HOSTS.get(name, set())
        hosts += [
            f"{name}: {host}" for host in sorted(set(_URL_HOST.findall(blob))) if host not in allowed_hosts
        ]
    if markings:
        report.fail("provenance.noConfidentialMarkings", f"{markings[:5]}")
    else:
        report.ok(
            "provenance.noConfidentialMarkings",
            "no tracked text file carries a confidentiality marking from supplied material",
        )
    if hosts:
        report.fail("provenance.noThirdPartyDocHosts", f"{hosts[:5]}")
    else:
        report.ok(
            "provenance.noThirdPartyDocHosts",
            "every URL in the tracked sources points at a first-party or repository host",
        )

    from PIL import Image

    defects: list[str] = []
    for key, entry in sorted(context.diagrams.items()):
        svg_path, png_path = entry.get("svg"), entry.get("png")
        if svg_path is None or png_path is None:
            defects.append(f"{key}: missing an SVG/PNG pair")
            continue
        svg = svg_path.read_text(encoding="utf-8")
        if _SVG_RASTER.search(svg):
            defects.append(f"{key}: SVG embeds a raster payload")
        if _SVG_EXTERNAL.search(svg):
            defects.append(f"{key}: SVG references an external resource")
        if "<title" not in svg or "<desc" not in svg:
            defects.append(f"{key}: SVG has no accessible title/description")
        box = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
        if not box:
            defects.append(f"{key}: SVG has no viewBox")
            continue
        with Image.open(png_path) as image:
            width, height = image.size
        expected_ratio = float(box.group(1)) / float(box.group(2))
        if abs(width / height - expected_ratio) > 0.005:
            defects.append(f"{key}: PNG {width}x{height} does not match the SVG aspect ratio")
    if defects:
        report.fail("provenance.diagramsAreAuthored", f"{defects[:5]}")
    else:
        report.ok(
            "provenance.diagramsAreAuthored",
            f"all {len(context.diagrams)} diagrams are author-created vector art whose PNG "
            "matches the SVG geometry",
        )

    lifecycle = context.diagrams.get("ontology-authoring-evaluation-lifecycle")
    if lifecycle is None or "svg" not in lifecycle or "png" not in lifecycle:
        report.fail("provenance.lifecycleDiagram", "the D.6 lifecycle diagram is missing an SVG/PNG pair")
    else:
        svg = lifecycle["svg"].read_text(encoding="utf-8")
        phases = [
            phrase
            for phrase in (
                "証拠の発見", "ドメイン設計", "構造とグラウンディングの検証",
                "読み取り専用プレビュー", "書き込みゲート",
            )
            if phrase not in svg
        ]
        if phases:
            report.fail("provenance.lifecycleDiagram", f"the lifecycle artwork is missing phases {phases}")
        else:
            report.ok(
                "provenance.lifecycleDiagram",
                "the D.6 lifecycle diagram draws all five generic phases and carries no product screen name",
            )

    _validate_authoring_source_provenance(root, names, report)


#: Presentation, video and animation containers. The Data Agent practice update
#: was written from public Microsoft documentation; no deck, recording or frame
#: grab may enter the tree, and there is no legitimate reason for one to.
_DECK_MEDIA_SUFFIXES = (".pptx", ".ppt", ".pptm", ".ppsx", ".mp4", ".mov", ".gif", ".webm")

#: Shapes an Office authoring trail leaves behind. A copied deck fragment brings
#: an author tuple, a Windows SID, a mail address or a third-party add-in marker
#: with it, so their absence is the evidence that nothing was pasted in. The
#: patterns must not name a real person: the negative tests plant synthetic
#: values (``someone@example.invalid`` and a synthetic SID) instead.
_AUTHORING_TRAIL = (
    (re.compile(r"\bS-1-5-21-\d+-\d+-\d+-\d+\b"), "a Windows security identifier"),
    (
        re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.invalid\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "a mail address",
    ),
    (re.compile(r"\bcp:lastModifiedBy\b|\bdc:creator\b"), "an OOXML author tuple"),
    (re.compile(r"\bthinkcell\b|\bslidewise\b|\bofficeatwork\b", re.I), "a third-party add-in marker"),
)

#: Files that legitimately own the patterns above: the validators that define
#: them and the negative tests that plant synthetic instances of them.
_AUTHORING_TRAIL_OWNERS = frozenset(
    {
        "tools/docs/validate_docs.py",
        "tools/docs/tests/test_data_agent_practice_gates.py",
    }
)

#: Guidance modules the practice update touched. The authoring-trail scan is
#: narrowed to these so an unrelated legacy string elsewhere cannot mask a real
#: paste into the new prose.
_NEW_GUIDANCE_SOURCES = (
    "tools/docs/furusato_docs/guide_agent.py",
    "tools/docs/furusato_docs/guide_content.py",
    "tools/docs/furusato_docs/quality.py",
)


def _validate_authoring_source_provenance(root: Path, names: list[str], report: Report) -> None:
    """No deck, recording or Office authoring trail entered the tree.

    The public-source practice update is prose. It ships no new binary media and
    carries no fragment of anyone's authoring environment; both statements are
    measured against the tracked tree rather than asserted.
    """
    media = sorted(name for name in names if Path(name).suffix.lower() in _DECK_MEDIA_SUFFIXES)
    if media:
        report.fail("provenance.noDeckOrVideoAssets", f"{media[:5]}")
    else:
        report.ok(
            "provenance.noDeckOrVideoAssets",
            f"none of the {len(names)} tracked paths is a presentation, video or animation container",
        )

    trail: list[str] = []
    for name in _NEW_GUIDANCE_SOURCES:
        if name in _AUTHORING_TRAIL_OWNERS:
            continue
        path = root / name
        if not path.is_file():
            trail.append(f"{name}: expected guidance module is missing")
            continue
        blob = path.read_text(encoding="utf-8", errors="ignore")
        for pattern, why in _AUTHORING_TRAIL:
            match = pattern.search(blob)
            if match:
                trail.append(f"{name}: {match.group(0)!r} ({why})")
    if trail:
        report.fail("provenance.noAuthoringTrail", "; ".join(trail[:5]))
    else:
        report.ok(
            "provenance.noAuthoringTrail",
            f"none of the {len(_AUTHORING_TRAIL)} authoring-trail shapes appears in the "
            f"{len(_NEW_GUIDANCE_SOURCES)} guidance modules",
        )

    raster = sorted(
        name
        for name in names
        if name.startswith("docs/assets/") and Path(name).suffix.lower() not in (".svg", ".png")
    )
    pairs = sorted(
        Path(name).stem
        for name in names
        if name.startswith("docs/assets/") and Path(name).suffix.lower() == ".svg"
    )
    orphans = sorted(
        stem for stem in pairs if f"docs/assets/v2.7.0/{stem}.png" not in set(names)
    )
    if raster or orphans:
        report.fail(
            "provenance.noNewRasterAssets",
            f"non-vector-derived assets: {raster[:5]}; SVGs without a PNG twin: {orphans[:5]}",
        )
    else:
        report.ok(
            "provenance.noNewRasterAssets",
            f"all {len(pairs)} diagram assets are SVG originals with a matching PNG and nothing else",
        )


def _check_carrier_labels(archive: Path, report: Report) -> None:
    """The maintained carrier must not seed a superseded classification.

    Whatever the carrier stores is copied into every freshly built shell, so a
    stale label in the asset would silently reappear in the deliverables on the
    next clean rebuild.
    """
    import zipfile

    with zipfile.ZipFile(archive) as source:
        parts = {name: source.read(name) for name in source.namelist()}
    blob = b"".join(value for name, value in parts.items() if name.endswith((".xml", ".rels", ".json")))
    text = blob.decode("utf-8", "ignore")
    hits = validators.forbidden_label_guid_fingerprints(text)
    if hits:
        report.fail("toolchain.carrierLabels", f"style carrier still seeds superseded label GUID fingerprints: {hits}")
    else:
        report.ok(
            "toolchain.carrierLabels",
            f"style carrier is free of all {len(validators.FORBIDDEN_LABEL_GUID_HASHES)} superseded label/tenant GUIDs",
        )

    stored_label = parts.get("parts/docMetadata/LabelInfo.xml", b"").decode("utf-8")
    stored_custom = parts.get("parts/docProps/custom.xml", b"")
    generated = oox_module.custom_properties_xml()
    if validators.EXPECTED_LABEL_ID in stored_label and validators.EXPECTED_SITE_ID in stored_label:
        report.ok("toolchain.carrierLabelInfo", "style carrier stores the approved LabelInfo part")
    else:
        report.fail("toolchain.carrierLabelInfo", "style carrier LabelInfo does not state the approved label")
    if stored_custom == generated:
        report.ok(
            "toolchain.carrierCustomProps",
            "style carrier custom properties are byte-identical to the generated approved set",
        )
    else:
        report.fail(
            "toolchain.carrierCustomProps",
            "style carrier custom properties differ from the deterministic approved set",
        )

    expected_stamp = reproducible.zip_date_time()
    with zipfile.ZipFile(archive) as source:
        infos = source.infolist()
    drifted = [info.filename for info in infos if info.date_time != expected_stamp]
    if drifted:
        report.fail(
            "toolchain.carrierTimestamps",
            f"{len(drifted)} of {len(infos)} carrier members carry a build-time timestamp: {drifted[:4]}",
        )
    else:
        report.ok(
            "toolchain.carrierTimestamps",
            f"all {len(infos)} carrier members carry the fixed build instant {expected_stamp}",
        )


def validate_toolchain(root: Path, context) -> Report:
    from furusato_docs.oox import CompactStyleCarrier, StyleCarrier

    report = Report(target="tools/docs (self-sufficiency)")

    archive = StyleCarrier.archive_path(root)
    if not archive.is_file():
        report.fail("toolchain.styleCarrier", f"maintained style carrier asset missing: {archive}")
        return report
    try:
        carrier = CompactStyleCarrier(archive)
    except Exception as error:
        report.fail("toolchain.styleCarrier", f"{archive.name} is unusable: {error}")
        return report
    report.ok(
        "toolchain.styleCarrier",
        f"{archive.name} carries {len(StyleCarrier.REQUIRED_PARTS)} shell parts and "
        f"{carrier.screenshot_count} screenshots ({archive.stat().st_size:,} bytes)",
    )

    resolved = StyleCarrier.resolve(root)
    if Path(resolved.source) == archive:
        report.ok(
            "toolchain.carrierResolution",
            "StyleCarrier.resolve() returns the maintained asset with no fallback to a superseded deliverable",
        )
    else:
        report.fail("toolchain.carrierResolution", f"resolve() returned {resolved.source}")

    _check_carrier_labels(archive, report)

    superseded = sorted(
        path.relative_to(root).as_posix()
        for pattern in ("*v2.6.0.docx", "*v2.6.0.xlsx", "*Test_100*")
        for path in (root / "docs").glob(pattern)
    )
    if superseded:
        report.warn(
            "toolchain.supersededPresent",
            f"superseded deliverables are still on disk (not used by the build): {superseded}",
        )
    else:
        report.ok("toolchain.supersededPresent", "no superseded deliverable is present")

    # No build or validation module may resolve a superseded deliverable as a path.
    # Only path-like literals count; the ban list and this self-check are excluded.
    offenders: list[str] = []
    path_literal = re.compile(r"""["'](?:\./)?docs/[^"']*(?:v2\.6\.0\.(?:docx|xlsx)|Ontology_Test_100)[^"']*["']""")
    exempt = {"validators.py", "make_style_carrier.py", "validate_docs.py"}
    for path in sorted((root / "tools" / "docs").rglob("*.py")):
        if path.name in exempt:
            continue
        in_deletion_list = False
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.startswith("SUPERSEDED = ("):
                in_deletion_list = True
                continue
            if in_deletion_list:
                if line.startswith(")"):
                    in_deletion_list = False
                continue
            if path_literal.search(line):
                offenders.append(f"{path.relative_to(root).as_posix()}:{number}")
    build_source = (root / "tools" / "docs" / "build_docs.py").read_text(encoding="utf-8")
    if "SUPERSEDED" in build_source and "STYLE_CARRIER_ASSET" in build_source:
        report.ok(
            "toolchain.buildInputs",
            "build_docs.py names the maintained asset and treats the superseded files as a deletion list only",
        )
    else:
        report.fail("toolchain.buildInputs", "build_docs.py no longer declares its style carrier input explicitly")

    if offenders:
        report.fail("toolchain.noLegacyDependency", f"code resolves a superseded deliverable: {offenders}")
    else:
        report.ok(
            "toolchain.noLegacyDependency",
            "no builder or validator resolves a superseded deliverable; only the maintained asset is used",
        )

    return report


def check_urls(report: Report, timeout: int = 12) -> None:
    failures: list[str] = []
    checked = 0
    for _title, url in guide_content.REFERENCE_LINKS:
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "furusato-docs-validator/2.7.0"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                checked += 1
                if response.status >= 400:
                    failures.append(f"{url} -> HTTP {response.status}")
        except urllib.error.HTTPError as error:
            checked += 1
            if error.code >= 400:
                failures.append(f"{url} -> HTTP {error.code}")
        except Exception as error:  # network policy, DNS, TLS
            report.warn("links.external", f"{url} could not be checked ({error.__class__.__name__})")
    if failures:
        report.fail("links.external", "; ".join(failures))
    elif checked:
        report.ok("links.external", f"{checked} reference URLs responded with a success status")


def validate_render(
    root: Path, out_dir: Path, context, tests, edition: str = "", *,
    public_documents_only: bool = False,
) -> Report:
    """Render every page of both documents and reject blank / caption-only pages."""
    import shutil
    import tempfile

    report = Report(target="rendered pages")
    names = deliverable_names(context.version, edition)
    scratch = Path(tempfile.mkdtemp(prefix="furusato-render-", dir=str(out_dir)))
    try:
        for name, is_validation, first_body in (
            # The participant guide's front matter is the cover plus the contents
            # listing; the listing now runs to page 7, so the body starts on 8.
            (names.participant, False, 8),
            (names.validation, True, 3),
        ):
            if public_documents_only and is_validation:
                continue
            path = out_dir / name
            if not path.is_file():
                report.fail("render.file", f"{name} not found")
                continue
            stats = quality.check_render(path, scratch, report, first_body_page=first_body)
            result = stats.pop("result", None)
            if is_validation and result is not None:
                quality.check_test_record_pages(result, tests, report)
            report.stats[name] = stats
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return report


def validate_public_documents(root: Path, out_dir: Path, context, facts, edition: str) -> list[Report]:
    """Read-only document checks, not the repository/runtime packaging and reseal audit."""
    names = deliverable_names(context.version, edition)
    require_public_edition(edition)
    out_dir = outside_repo(out_dir, root)
    check_directory(out_dir, names, required=(names.participant,))
    return [
        validate_toolchain(root, context),
        validate_guide(root, out_dir, context, facts, edition, public_documents_only=True),
        validate_visual(root, out_dir, context, edition),
    ]


def main(argv: list[str] | None = None) -> int:
    use_utf8_streams()
    parser = argparse.ArgumentParser(description="Validate the Furusato v2.7.0 Office deliverables.")
    parser.add_argument("--out", default=None, help="Directory holding the deliverables (default: docs)")
    parser.add_argument("--edition", default="", type=validate_edition, help="Named correction edition")
    parser.add_argument(
        "--public-documents-only", action="store_true",
        help="Validate only the participant Word, without companion/checklist or runtime-reseal checks",
    )
    parser.add_argument("--check-urls", action="store_true", help="Also check the reference URLs")
    parser.add_argument(
        "--render",
        action="store_true",
        help="Also render every page with Word and reject blank or caption-only pages",
    )
    parser.add_argument("--json", action="store_true", help="Emit the machine-readable report only")
    arguments = parser.parse_args(argv)
    if arguments.public_documents_only and not arguments.out:
        parser.error("--public-documents-only requires --out")

    root = repo_root()
    out_dir = root / (arguments.out or "docs")
    if not arguments.public_documents_only:
        out_dir = out_dir.resolve()
    context = load_context(root, document_edition=arguments.edition)
    facts = compute_facts(context)
    tests = build_tests(context, facts)

    if arguments.public_documents_only:
        try:
            reports = validate_public_documents(root, out_dir, context, facts, arguments.edition)
        except PublicationError as error:
            parser.error(str(error))
    else:
        reports = [
            validate_final_runtime(root, context, facts),
            validate_toolchain(root, context),
            validate_runtime_parity(root, context, tests, facts),
            validate_guide(root, out_dir, context, facts, arguments.edition),
            validate_validation_doc(root, out_dir, context, facts, tests, arguments.edition),
            validate_workbook(root, out_dir, context, facts, arguments.edition),
            validate_checklist(root, context, facts),
            validate_visual(root, out_dir, context, arguments.edition),
        ]
    if arguments.render:
        reports.append(validate_render(
            root, out_dir, context, tests, arguments.edition,
            public_documents_only=arguments.public_documents_only,
        ))
    if arguments.check_urls:
        link_report = Report(target="reference URLs")
        check_urls(link_report)
        reports.append(link_report)

    payload = {
        "version": context.version,
        "edition": arguments.edition,
        "publicDocumentsOnly": arguments.public_documents_only,
        "results": [
            {
                "target": report.target,
                "pass": report.passed,
                "stats": report.stats,
                "findings": [
                    {"level": finding.level, "check": finding.check, "message": finding.message}
                    for finding in report.findings
                ],
            }
            for report in reports
        ],
    }
    if arguments.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            print(f"\n=== {report.target} ===")
            for finding in report.findings:
                marker = {"PASS": "  ok  ", "WARN": " warn ", "FAIL": " FAIL "}[finding.level]
                print(f"[{marker}] {finding.check}: {finding.message}")
            if report.stats:
                print(f"  stats: {json.dumps(report.stats, ensure_ascii=False)}")
        failures = sum(len(report.failures) for report in reports)
        warnings = sum(len(report.warnings) for report in reports)
        print(f"\n{failures} failure(s), {warnings} warning(s)")

    return 1 if any(not report.passed for report in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
