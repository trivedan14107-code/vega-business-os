"""Dependency-free checks for the synthetic dataset."""

import csv
import unittest
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class DatasetIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.customers = read_csv("customers.csv")
        cls.invoices = read_csv("invoices.csv")
        cls.payments = read_csv("payments.csv")
        cls.messages = read_csv("customer_messages.csv")

    def test_expected_record_counts(self) -> None:
        self.assertEqual(len(self.customers), 10)
        self.assertEqual(len(self.invoices), 20)
        self.assertEqual(len(self.payments), 5)
        self.assertEqual(len(self.messages), 11)

    def test_identifiers_are_unique(self) -> None:
        for rows, key in (
            (self.customers, "customer_id"),
            (self.invoices, "invoice_id"),
            (self.payments, "payment_id"),
            (self.messages, "message_id"),
        ):
            identifiers = [row[key] for row in rows]
            self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_references_exist(self) -> None:
        customer_ids = {row["customer_id"] for row in self.customers}
        invoice_ids = {row["invoice_id"] for row in self.invoices}

        self.assertTrue(all(row["customer_id"] in customer_ids for row in self.invoices))
        self.assertTrue(all(row["invoice_id"] in invoice_ids for row in self.payments))
        self.assertTrue(all(row["customer_id"] in customer_ids for row in self.messages))
        self.assertTrue(all(row["invoice_id"] in invoice_ids for row in self.messages))

    def test_invoice_dates_and_amounts_are_valid(self) -> None:
        for invoice in self.invoices:
            self.assertGreater(Decimal(invoice["amount"]), 0)
            self.assertLessEqual(
                date.fromisoformat(invoice["issue_date"]),
                date.fromisoformat(invoice["due_date"]),
            )

    def test_payments_do_not_exceed_invoice_amounts(self) -> None:
        invoice_amounts = {
            row["invoice_id"]: Decimal(row["amount"]) for row in self.invoices
        }
        payment_totals: dict[str, Decimal] = defaultdict(Decimal)
        for payment in self.payments:
            payment_totals[payment["invoice_id"]] += Decimal(payment["amount"])

        for invoice_id, total in payment_totals.items():
            self.assertLessEqual(total, invoice_amounts[invoice_id])

    def test_payment_status_matches_payment_totals(self) -> None:
        payment_totals: dict[str, Decimal] = defaultdict(Decimal)
        for payment in self.payments:
            payment_totals[payment["invoice_id"]] += Decimal(payment["amount"])

        for invoice in self.invoices:
            total = payment_totals[invoice["invoice_id"]]
            amount = Decimal(invoice["amount"])
            if invoice["status"] == "paid":
                self.assertEqual(total, amount)
            elif invoice["status"] == "partially_paid":
                self.assertGreater(total, 0)
                self.assertLess(total, amount)


if __name__ == "__main__":
    unittest.main()
