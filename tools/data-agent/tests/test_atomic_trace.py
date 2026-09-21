from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SQL_PATH = (
    ROOT
    / "tools"
    / "data-agent"
    / "reference-models"
    / "060_donation_trace_by_id.sql"
)
SCHEMA_PATH = (
    ROOT
    / "tools"
    / "data-agent"
    / "reference-models"
    / "trace-schema.json"
)


def normalized_sql() -> str:
    return " ".join(SQL_PATH.read_text("utf-8").lower().split())


def fixture_trace(donation: dict, registrations: list[dict]) -> list[dict]:
    """Model the TVF's one Donation x registration LEFT JOIN grain."""
    matching = [
        row
        for row in registrations
        if row["GiftCatalogGiftId"] == donation["GiftId"]
    ]
    matching = matching or [
        {
            "RegisteredSupplierId": None,
            "RegisteredSupplierName": None,
            "RegisteredSupplierDisplayName": None,
            "RegisteredSupplierType": None,
            "RegisteredSupplierTypeEn": None,
        }
    ]
    return [
        {
            "DonationId": donation["DonationId"],
            "DonationAmountYen": donation["DonationAmountYen"],
            "SupplierId": registration["RegisteredSupplierId"],
            "RowGrain": (
                "DonationId x SupplierId registration; "
                "DonationAmountYen is non-additive"
            ),
        }
        for registration in matching
    ]


class AtomicTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = normalized_sql()
        cls.schema = json.loads(SCHEMA_PATH.read_text("utf-8"))

    def test_schema_is_exact_compact_and_uses_canonical_role_aliases(self):
        fields = self.schema["fields"]
        self.assertEqual(len(fields), 30)
        self.assertEqual(len({name for name, _ in fields}), 30)
        self.assertEqual(
            [name for name, _ in fields[:5]],
            [
                "RequestedDonationId",
                "RetrievalMode",
                "DonationId",
                "DonationDisplayName",
                "DonationAmountYen",
            ],
        )
        for name in (
            "DonorId",
            "MunicipalityId",
            "GiftId",
            "CategoryId",
            "SupplierId",
            "DonorDisplayName",
            "MunicipalityDisplayName",
            "GiftDisplayName",
            "SupplierDisplayName",
            "SupplierType",
            "SupplierTypeEn",
            "SourceSystem",
            "DatasetScope",
            "RowGrain",
        ):
            self.assertIn(name, {field for field, _ in fields})

    def test_sql_is_one_inline_tvf_with_exact_lookup_and_left_registration_join(self):
        batches = [
            batch.strip()
            for batch in re.split(r"(?im)^\s*go\s*$", SQL_PATH.read_text("utf-8"))
            if batch.strip()
        ]
        self.assertEqual(len(batches), 1)
        self.assertIn(
            "create function agent_ref.donationtracebyid "
            "( @requesteddonationid bigint ) returns table",
            self.sql,
        )
        self.assertIn(
            "from agent_ref.donationattributes as donation "
            "left join agent_ref.giftcatalogsuppliers as supplier "
            "on supplier.giftcataloggiftid = donation.donationselectedgiftid",
            self.sql,
        )
        self.assertIn("donation.donationid = @requesteddonationid", self.sql)
        self.assertIn("@requesteddonationid is not null", self.sql)

    def test_sql_has_no_collapsing_or_destructive_constructs(self):
        for forbidden in (
            "select *",
            "string_agg",
            "top 1",
            "json_",
            "openjson",
            "drop ",
            "alter ",
            "insert ",
            "update ",
            "delete ",
            "merge ",
            "grant ",
            "begin transaction",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.sql)

    def test_projection_excludes_repeated_dimension_metrics_dates_and_payment(self):
        field_names = {name for name, _ in self.schema["fields"]}
        for excluded in (
            "DonatedAtUtc",
            "DonatedAtJstText",
            "DonationDateJst",
            "DonationYearMonthJst",
            "DonationPaymentMethod",
            "DonationPaymentMethodEn",
            "MunicipalityStaticCount",
            "MunicipalityStaticTotalYen",
            "GiftStaticCount",
            "GiftStaticTotalYen",
            "CategoryStaticCount",
            "CategoryStaticTotalYen",
            "SupplierProvidedGiftCount",
        ):
            self.assertNotIn(excluded, field_names)

    def test_multiple_supplier_fixture_preserves_every_registration(self):
        donation_id = next(iter(range(1, 2)))
        gift_id = next(iter(range(10, 11)))
        donation = {
            "DonationId": donation_id,
            "GiftId": gift_id,
            "DonationAmountYen": 100,
        }
        registrations = [
            {
                "GiftCatalogGiftId": gift_id,
                "RegisteredSupplierId": supplier_id,
                "RegisteredSupplierName": f"Supplier {supplier_id}",
                "RegisteredSupplierDisplayName": f"Display {supplier_id}",
                "RegisteredSupplierType": "Type",
                "RegisteredSupplierTypeEn": "Type",
            }
            for supplier_id in range(20, 23)
        ]
        rows = fixture_trace(donation, registrations)
        self.assertEqual(
            {row["SupplierId"] for row in rows},
            {registration["RegisteredSupplierId"] for registration in registrations},
        )
        self.assertEqual(len(rows), len(registrations))

    def test_zero_supplier_fixture_returns_one_null_supplier_row(self):
        donation = {
            "DonationId": next(iter(range(1, 2))),
            "GiftId": next(iter(range(10, 11))),
            "DonationAmountYen": 100,
        }
        rows = fixture_trace(donation, [])
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["SupplierId"])

    def test_donation_amount_is_explicitly_nonadditive_across_supplier_rows(self):
        donation = {
            "DonationId": next(iter(range(1, 2))),
            "GiftId": next(iter(range(10, 11))),
            "DonationAmountYen": 100,
        }
        registrations = [
            {
                "GiftCatalogGiftId": donation["GiftId"],
                "RegisteredSupplierId": supplier_id,
                "RegisteredSupplierName": "Supplier",
                "RegisteredSupplierDisplayName": "Supplier display",
                "RegisteredSupplierType": "Type",
                "RegisteredSupplierTypeEn": "Type",
            }
            for supplier_id in range(20, 22)
        ]
        rows = fixture_trace(donation, registrations)
        self.assertEqual({row["DonationAmountYen"] for row in rows}, {100})
        self.assertNotEqual(
            sum(row["DonationAmountYen"] for row in rows),
            donation["DonationAmountYen"],
        )
        self.assertIn(
            "non-additive",
            self.schema["object"]["amountSemantics"].lower(),
        )
        self.assertTrue(all("non-additive" in row["RowGrain"] for row in rows))


if __name__ == "__main__":
    unittest.main()
