"""Expected values for the ten held-out tests, recomputed from the packaged CSVs.

Nothing here is transcribed by hand. Every number the Test 10 document prints is
derived from ``workshop/v2.7.0/data`` at build time and cross-checked against
``dataset-manifest.json``, so the document can never disagree with the data that
participants actually load.
"""

from __future__ import annotations

import collections
import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .context import RuntimeContext


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


#: The prefecture T04 asks about, declared rather than derived.
#:
#: T04 is the reverse-traversal test, and its question names a prefecture in
#: literal Japanese. Deriving that prefecture from another test's answer - the
#: top municipality of T02 - coupled the two: a dataset change that moved the top
#: municipality would have left T04 asking about 宮崎県 while the expected count,
#: the PrefectureId and the evidence all silently described somewhere else. The
#: prefecture is therefore declared here, and ``compute_facts`` fails if the
#: packaged data does not agree with the declaration.
T04_PREFECTURE_ID = "45"
T04_PREFECTURE_NAME = "宮崎県"


@dataclass
class StaticFacts:
    donation_rows: int
    donation_total_yen: int
    top_municipality_id: str
    top_municipality_name: str
    top_municipality_prefecture_id: str
    top_municipality_prefecture_name: str
    top_municipality_count: int
    top_municipality_total_yen: int
    top_municipality_count_rank: int
    top_municipality_amount_rank: int
    second_municipality_id: str
    second_municipality_name: str
    second_municipality_count: int
    second_municipality_total_yen: int
    miyazaki_municipality_count: int
    #: T04 reverse-traversal target, declared in T04_PREFECTURE_* and verified
    #: against the packaged data rather than derived from another test's answer.
    t04_prefecture_id: str
    t04_prefecture_name: str
    t04_municipality_count: int
    tokyo_received_count: int
    tokyo_received_yen: int
    tokyo_resident_count: int
    tokyo_resident_yen: int
    #: MunicipalityCategoryMetric worked example (composite grain, no re-aggregation).
    metric_municipality_id: str = ""
    metric_municipality_name: str = ""
    metric_id: str = ""
    metric_category_id: str = ""
    metric_category_name: str = ""
    metric_static_count: int = 0
    metric_total_yen: int = 0
    metric_municipality_total_count: int = 0
    metric_municipality_total_yen: int = 0
    #: PrefectureDonationFlow worked example (direction matters).
    flow_id: str = ""
    flow_origin_id: str = ""
    flow_origin_label: str = ""
    flow_destination_id: str = ""
    flow_destination_label: str = ""
    flow_static_count: int = 0
    flow_total_yen: int = 0
    flow_reverse_id: str = ""
    flow_reverse_static_count: int = 0
    flow_reverse_total_yen: int = 0
    sample_donation: dict[str, Any] = field(default_factory=dict)


@dataclass
class IncrementCalendar:
    """Per-UTC-day shape of the packaged August 2026 increment."""

    utc_days: list[dict[str, Any]]
    utc_day_count: int
    first_utc_day: str
    last_utc_day: str
    missing_utc_days: list[str]
    min_rows: int
    max_rows: int
    min_rows_day: str
    max_rows_day: str
    dedup_min_rows: int
    dedup_max_rows: int
    duplicate_day: str
    #: Rows that participate in a duplicate group on that day (100 EventIDs x 2 rows).
    duplicate_group_rows_on_day: int
    #: Rows actually removed by deduplication on that day (raw minus deduplicated).
    duplicate_extra_rows_on_day: int
    duplicate_event_ids_on_day: int
    duplicate_day_raw_rows: int
    duplicate_day_dedup_rows: int
    jst_day_count: int
    first_jst_day: str
    last_jst_day: str
    jst_rollover_rows: int
    jst_rollover_from_utc: str
    jst_rollover_to_utc: str


@dataclass
class ObservationFacts:
    raw_rows: int
    unique_event_ids: int
    duplicate_event_ids: int
    raw_amount_yen: int
    deduplicated_amount_yen: int
    window_start_utc: str
    window_end_utc: str
    per_file: list[dict[str, Any]]
    per_run: list[dict[str, Any]]
    participant_alias: str
    top_observed_municipality_id: str
    top_observed_count: int
    top_observed_amount_yen: int
    calendar: IncrementCalendar | None = None


@dataclass
class TestFacts:
    static: StaticFacts
    observation: ObservationFacts


def compute_facts(context: RuntimeContext) -> TestFacts:
    data = context.root / "workshop" / f"v{context.version}" / "data"
    seed = data / "seed"

    municipalities = {row["MunicipalityID"]: row for row in _read(seed / "municipalities.csv")}
    donors = {row["DonorID"]: row for row in _read(seed / "donors.csv")}
    gifts = {row["GiftID"]: row for row in _read(seed / "gifts.csv")}
    categories = {row["CategoryID"]: row for row in _read(seed / "categories.csv")}
    suppliers = {row["BusinessID"]: row for row in _read(seed / "businesses.csv")}
    supplier_gifts = _read(seed / "business_gifts.csv")
    donations = _read(seed / "donation_orders.csv")

    counts: collections.Counter[str] = collections.Counter()
    amounts: collections.Counter[str] = collections.Counter()
    for row in donations:
        counts[row["MunicipalityID"]] += 1
        amounts[row["MunicipalityID"]] += int(row["DonationAmountYen"])

    by_amount = sorted(amounts.items(), key=lambda item: (-item[1], item[0]))
    by_count = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top_id = by_amount[0][0]
    second_id = by_amount[1][0]

    tokyo_prefecture_id = next(
        row["PrefectureID"]
        for row in _read(seed / "prefectures.csv")
        if row["PrefectureName"] == "東京都"
    )
    tokyo_municipalities = {
        key for key, row in municipalities.items() if row["PrefectureID"] == tokyo_prefecture_id
    }
    tokyo_donors = {key for key, row in donors.items() if row["PrefectureID"] == tokyo_prefecture_id}
    tokyo_received_count = tokyo_received_yen = 0
    tokyo_resident_count = tokyo_resident_yen = 0
    for row in donations:
        amount = int(row["DonationAmountYen"])
        if row["MunicipalityID"] in tokyo_municipalities:
            tokyo_received_count += 1
            tokyo_received_yen += amount
        if row["DonorID"] in tokyo_donors:
            tokyo_resident_count += 1
            tokyo_resident_yen += amount

    sample_id = "5000001"
    sample_row = next(row for row in donations if row["DonationID"] == sample_id)
    sample_gift = gifts[sample_row["GiftID"]]
    sample_municipality = municipalities[sample_row["MunicipalityID"]]
    sample_donor = donors[sample_row["DonorID"]]
    sample_suppliers = [
        suppliers[link["BusinessID"]]
        for link in supplier_gifts
        if link["GiftID"] == sample_row["GiftID"]
    ]
    sample = {
        "DonationID": sample_id,
        "DonationAmountYen": int(sample_row["DonationAmountYen"]),
        "DonatedAtUtc": sample_row["DonatedAt"],
        "PaymentMethod": sample_row["PaymentMethod"],
        "DonorId": sample_row["DonorID"],
        "DonorName": sample_donor["DonorName"],
        "DonorPrefectureId": sample_donor["PrefectureID"],
        "DonorPrefectureName": sample_donor["PrefectureName"],
        "MunicipalityId": sample_row["MunicipalityID"],
        "MunicipalityName": sample_municipality["MunicipalityName"],
        "MunicipalityPrefectureId": sample_municipality["PrefectureID"],
        "MunicipalityPrefectureName": sample_municipality["PrefectureName"],
        "GiftId": sample_row["GiftID"],
        "GiftName": sample_gift["GiftName"],
        "CategoryId": sample_gift["CategoryID"],
        "CategoryName": categories[sample_gift["CategoryID"]]["CategoryName"],
        "SupplierIds": [row["BusinessID"] for row in sample_suppliers],
        "SupplierNames": [row["BusinessName"] for row in sample_suppliers],
    }

    miyazaki_prefecture_id = municipalities[top_id]["PrefectureID"]
    miyazaki_municipality_count = sum(
        1 for row in municipalities.values() if row["PrefectureID"] == miyazaki_prefecture_id
    )

    # T04 names its prefecture in the question text, so the declaration is the
    # contract and the packaged data has to match it - not the other way round.
    t04_rows = [
        row for row in municipalities.values() if row["PrefectureID"] == T04_PREFECTURE_ID
    ]
    if not t04_rows:
        raise ValueError(f"T04 prefecture {T04_PREFECTURE_ID} is not in the packaged municipalities")
    t04_names = {row["PrefectureName"] for row in t04_rows}
    if t04_names != {T04_PREFECTURE_NAME}:
        raise ValueError(
            f"T04 prefecture {T04_PREFECTURE_ID} is named {sorted(t04_names)} in the packaged data, "
            f"not {T04_PREFECTURE_NAME!r}"
        )
    t04_municipality_count = len(t04_rows)

    # MunicipalityCategoryMetric and PrefectureDonationFlow worked examples. Both
    # are recomputed from the donation detail so the guide can show that the
    # pre-aggregated composite grain reconciles, without inviting re-aggregation.
    metric_counts: collections.Counter[tuple[str, str]] = collections.Counter()
    metric_amounts: collections.Counter[tuple[str, str]] = collections.Counter()
    flow_counts: collections.Counter[tuple[str, str]] = collections.Counter()
    flow_amounts: collections.Counter[tuple[str, str]] = collections.Counter()
    for row in donations:
        amount = int(row["DonationAmountYen"])
        category_id = gifts[row["GiftID"]]["CategoryID"]
        metric_counts[(row["MunicipalityID"], category_id)] += 1
        metric_amounts[(row["MunicipalityID"], category_id)] += amount
        residence = donors[row["DonorID"]]["PrefectureID"]
        recipient = municipalities[row["MunicipalityID"]]["PrefectureID"]
        flow_counts[(residence, recipient)] += 1
        flow_amounts[(residence, recipient)] += amount

    metric_key = (top_id, min(cid for (mid, cid) in metric_counts if mid == top_id))
    prefectures = {row["PrefectureID"]: row for row in _read(seed / "prefectures.csv")}
    flow_key = max(
        (key for key in flow_amounts if key[0] != key[1]),
        key=lambda key: (flow_amounts[key], key),
    )
    reverse_key = (flow_key[1], flow_key[0])

    def _flow_label(prefecture_id: str) -> str:
        return f"{prefectures[prefecture_id]['PrefectureName']}（PrefectureId {prefecture_id}）"

    # Instance-key formats are the ones Notebook 01 builds: the metric key pads the
    # category to two digits, the flow key pads both prefecture ids to two digits.
    def _metric_id(municipality_id: str, category_id: str) -> str:
        return f"{municipality_id}-{int(category_id):02d}"

    def _flow_instance_id(origin: str, destination: str) -> str:
        return f"{int(origin):02d}-{int(destination):02d}"

    static = StaticFacts(
        donation_rows=len(donations),
        donation_total_yen=sum(int(row["DonationAmountYen"]) for row in donations),
        top_municipality_id=top_id,
        top_municipality_name=municipalities[top_id]["MunicipalityName"],
        top_municipality_prefecture_id=municipalities[top_id]["PrefectureID"],
        top_municipality_prefecture_name=municipalities[top_id]["PrefectureName"],
        top_municipality_count=counts[top_id],
        top_municipality_total_yen=amounts[top_id],
        top_municipality_count_rank=[key for key, _ in by_count].index(top_id) + 1,
        top_municipality_amount_rank=[key for key, _ in by_amount].index(top_id) + 1,
        second_municipality_id=second_id,
        second_municipality_name=municipalities[second_id]["MunicipalityName"],
        second_municipality_count=counts[second_id],
        second_municipality_total_yen=amounts[second_id],
        miyazaki_municipality_count=miyazaki_municipality_count,
        t04_prefecture_id=T04_PREFECTURE_ID,
        t04_prefecture_name=T04_PREFECTURE_NAME,
        t04_municipality_count=t04_municipality_count,
        tokyo_received_count=tokyo_received_count,
        tokyo_received_yen=tokyo_received_yen,
        tokyo_resident_count=tokyo_resident_count,
        tokyo_resident_yen=tokyo_resident_yen,
        metric_municipality_id=metric_key[0],
        metric_municipality_name=municipalities[metric_key[0]]["MunicipalityName"],
        metric_id=_metric_id(metric_key[0], metric_key[1]),
        metric_category_id=metric_key[1],
        metric_category_name=categories[metric_key[1]]["CategoryName"],
        metric_static_count=metric_counts[metric_key],
        metric_total_yen=metric_amounts[metric_key],
        metric_municipality_total_count=counts[metric_key[0]],
        metric_municipality_total_yen=amounts[metric_key[0]],
        flow_id=_flow_instance_id(*flow_key),
        flow_origin_id=flow_key[0],
        flow_origin_label=_flow_label(flow_key[0]),
        flow_destination_id=flow_key[1],
        flow_destination_label=_flow_label(flow_key[1]),
        flow_static_count=flow_counts[flow_key],
        flow_total_yen=flow_amounts[flow_key],
        flow_reverse_id=_flow_instance_id(*reverse_key),
        flow_reverse_static_count=flow_counts[reverse_key],
        flow_reverse_total_yen=flow_amounts[reverse_key],
        sample_donation=sample,
    )

    events: list[dict[str, str]] = []
    for entry in context.increment_files:
        events.extend(_read(data / "increment" / entry["file"]))

    per_file: dict[str, dict[str, Any]] = {}
    per_run: dict[str, dict[str, Any]] = {}
    for row in events:
        amount = int(row["DonationAmountYen"])
        bucket = per_file.setdefault(
            row["SourceFile"],
            {"file": row["SourceFile"], "rows": 0, "amount": 0, "first": None, "last": None},
        )
        bucket["rows"] += 1
        bucket["amount"] += amount
        bucket["first"] = row["DonatedAt"] if bucket["first"] is None else min(bucket["first"], row["DonatedAt"])
        bucket["last"] = row["DonatedAt"] if bucket["last"] is None else max(bucket["last"], row["DonatedAt"])
        run = per_run.setdefault(
            row["WorkshopRunId"],
            {"run": row["WorkshopRunId"], "rows": 0, "amount": 0, "files": set(), "published": None},
        )
        run["rows"] += 1
        run["amount"] += amount
        run["files"].add(row["SourceFile"])
        run["published"] = (
            row["PublishedAtUtc"]
            if run["published"] is None
            else max(run["published"], row["PublishedAtUtc"])
        )

    seen: set[str] = set()
    deduplicated = 0
    for row in events:
        if row["EventID"] not in seen:
            seen.add(row["EventID"])
            deduplicated += int(row["DonationAmountYen"])

    observed_counts: collections.Counter[str] = collections.Counter()
    observed_amounts: collections.Counter[str] = collections.Counter()
    for row in events:
        observed_counts[row["MunicipalityID"]] += 1
        observed_amounts[row["MunicipalityID"]] += int(row["DonationAmountYen"])
    top_observed = max(observed_amounts.items(), key=lambda item: (item[1], item[0]))

    observation = ObservationFacts(
        raw_rows=len(events),
        unique_event_ids=len(seen),
        duplicate_event_ids=len(events) - len(seen),
        raw_amount_yen=sum(int(row["DonationAmountYen"]) for row in events),
        deduplicated_amount_yen=deduplicated,
        window_start_utc=min(row["DonatedAt"] for row in events),
        window_end_utc=max(row["DonatedAt"] for row in events),
        per_file=[per_file[key] for key in sorted(per_file)],
        per_run=[
            {**per_run[key], "files": sorted(per_run[key]["files"])} for key in sorted(per_run)
        ],
        participant_alias=sorted({row["ParticipantAlias"] for row in events})[0],
        top_observed_municipality_id=top_observed[0],
        top_observed_count=observed_counts[top_observed[0]],
        top_observed_amount_yen=top_observed[1],
        calendar=_build_calendar(events),
    )

    _cross_check(context, static, observation)
    return TestFacts(static=static, observation=observation)


def _build_calendar(events: list[dict[str, str]]) -> IncrementCalendar:
    """Derive the per-UTC-day shape and the UTC-to-JST rollover from the raw rows."""
    raw_rows: collections.Counter[str] = collections.Counter()
    raw_amount: collections.Counter[str] = collections.Counter()
    dedup_rows: collections.Counter[str] = collections.Counter()
    jst_rows: collections.Counter[str] = collections.Counter()
    seen: set[str] = set()
    duplicate_rows: collections.Counter[str] = collections.Counter()
    occurrences: collections.Counter[str] = collections.Counter(row["EventID"] for row in events)

    for row in events:
        stamp = datetime.strptime(row["DonatedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        day = stamp.date().isoformat()
        raw_rows[day] += 1
        raw_amount[day] += int(row["DonationAmountYen"])
        jst_rows[(stamp + timedelta(hours=9)).date().isoformat()] += 1
        if row["EventID"] not in seen:
            seen.add(row["EventID"])
            dedup_rows[day] += 1
        if occurrences[row["EventID"]] > 1:
            duplicate_rows[day] += 1

    days = sorted(raw_rows)
    first, last = date.fromisoformat(days[0]), date.fromisoformat(days[-1])
    missing: list[str] = []
    cursor = first
    while cursor <= last:
        if cursor.isoformat() not in raw_rows:
            missing.append(cursor.isoformat())
        cursor += timedelta(days=1)

    jst_days = sorted(jst_rows)
    rollover_day = jst_days[-1]
    rollover = [
        row["DonatedAt"]
        for row in events
        if (
            datetime.strptime(row["DonatedAt"], "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=9)
        ).date().isoformat()
        == rollover_day
    ]
    duplicate_day = max(duplicate_rows, key=lambda key: duplicate_rows[key]) if duplicate_rows else ""
    # Two distinct quantities on the duplicated day:
    #   group rows  = rows that belong to a duplicate group (one EventID x two rows)
    #   extra rows  = rows deduplication actually removes (raw minus deduplicated)
    group_rows = duplicate_rows[duplicate_day] if duplicate_day else 0
    extra_rows = (raw_rows[duplicate_day] - dedup_rows[duplicate_day]) if duplicate_day else 0

    return IncrementCalendar(
        utc_days=[
            {
                "date": day,
                "rows": raw_rows[day],
                "amount": raw_amount[day],
                "dedupRows": dedup_rows[day],
            }
            for day in days
        ],
        utc_day_count=len(days),
        first_utc_day=days[0],
        last_utc_day=days[-1],
        missing_utc_days=missing,
        min_rows=min(raw_rows.values()),
        max_rows=max(raw_rows.values()),
        min_rows_day=min(raw_rows, key=lambda key: (raw_rows[key], key)),
        max_rows_day=max(raw_rows, key=lambda key: (raw_rows[key], key)),
        dedup_min_rows=min(dedup_rows.values()),
        dedup_max_rows=max(dedup_rows.values()),
        duplicate_day=duplicate_day,
        duplicate_group_rows_on_day=group_rows,
        duplicate_extra_rows_on_day=extra_rows,
        duplicate_event_ids_on_day=extra_rows,
        duplicate_day_raw_rows=raw_rows[duplicate_day] if duplicate_day else 0,
        duplicate_day_dedup_rows=dedup_rows[duplicate_day] if duplicate_day else 0,
        jst_day_count=len(jst_days),
        first_jst_day=jst_days[0],
        last_jst_day=rollover_day,
        jst_rollover_rows=len(rollover),
        jst_rollover_from_utc=min(rollover) if rollover else "",
        jst_rollover_to_utc=max(rollover) if rollover else "",
    )


def _cross_check(context: RuntimeContext, static: StaticFacts, observation: ObservationFacts) -> None:
    expected = context.expected
    increment = context.expected_increment
    checks = [
        ("donationRows", expected["donationRows"], static.donation_rows),
        ("totalDonationAmountYen", expected["totalDonationAmountYen"], static.donation_total_yen),
        ("topMunicipality.MunicipalityId", expected["topMunicipality"]["MunicipalityId"], static.top_municipality_id),
        ("topMunicipality.Count", expected["topMunicipality"]["Count"], static.top_municipality_count),
        ("topMunicipality.TotalYen", expected["topMunicipality"]["TotalYen"], static.top_municipality_total_yen),
        ("tokyo.PrefReceivedStaticCount", expected["tokyoAmbiguity"]["PrefReceivedStaticCount"], static.tokyo_received_count),
        ("tokyo.PrefReceivedTotalYen", expected["tokyoAmbiguity"]["PrefReceivedTotalYen"], static.tokyo_received_yen),
        ("tokyo.PrefResidentStaticCount", expected["tokyoAmbiguity"]["PrefResidentStaticCount"], static.tokyo_resident_count),
        ("tokyo.PrefResidentTotalYen", expected["tokyoAmbiguity"]["PrefResidentTotalYen"], static.tokyo_resident_yen),
        ("increment.rawRows", increment["rawRows"], observation.raw_rows),
        ("increment.uniqueEventIds", increment["uniqueEventIds"], observation.unique_event_ids),
        ("increment.duplicateEventIds", increment["duplicateEventIds"], observation.duplicate_event_ids),
        ("increment.rawAmountYen", increment["rawAmountYen"], observation.raw_amount_yen),
        ("increment.deduplicatedAmountYen", increment["deduplicatedAmountYen"], observation.deduplicated_amount_yen),
        ("increment.window.from", increment["observationWindowUtc"]["from"], observation.window_start_utc),
        ("increment.window.to", increment["observationWindowUtc"]["to"], observation.window_end_utc),
        ("increment.firstFileAmountYen", increment["firstFileAmountYen"], observation.per_file[0]["amount"]),
    ]
    mismatches = [f"{name}: manifest={left!r} computed={right!r}" for name, left, right in checks if left != right]
    if mismatches:
        raise ValueError("Computed facts disagree with dataset-manifest.json:\n  " + "\n  ".join(mismatches))

    calendar = observation.calendar
    if calendar is None:
        raise ValueError("The increment calendar was not derived.")
    if calendar.missing_utc_days:
        raise ValueError(f"The increment has gaps in its UTC day coverage: {calendar.missing_utc_days}")
    if sum(day["rows"] for day in calendar.utc_days) != observation.raw_rows:
        raise ValueError("The per-day row counts do not reconcile to the raw row total.")
    if sum(day["dedupRows"] for day in calendar.utc_days) != observation.unique_event_ids:
        raise ValueError("The per-day deduplicated counts do not reconcile to the unique EventID total.")
    if calendar.first_utc_day != observation.window_start_utc[:10]:
        raise ValueError("The first UTC day disagrees with the observation window start.")
    if calendar.last_utc_day != observation.window_end_utc[:10]:
        raise ValueError("The last UTC day disagrees with the observation window end.")
    if calendar.duplicate_extra_rows_on_day * 2 != calendar.duplicate_group_rows_on_day:
        raise ValueError(
            "Duplicate accounting is inconsistent: every duplicated EventID must contribute "
            "exactly two rows, one of which deduplication removes."
        )
    if calendar.duplicate_extra_rows_on_day != observation.duplicate_event_ids:
        raise ValueError(
            "The rows removed by deduplication on the duplicated day do not match the "
            "duplicate EventID count for the whole increment."
        )
    if calendar.duplicate_day_raw_rows - calendar.duplicate_extra_rows_on_day != calendar.duplicate_day_dedup_rows:
        raise ValueError("raw minus extra duplicate rows does not equal the deduplicated count.")
