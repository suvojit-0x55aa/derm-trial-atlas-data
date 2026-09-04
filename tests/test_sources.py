"""
The three incoming-source builders, run on real fixture rows/responses
(tests/fixtures/sources/, captured from the live files/API on 2026-09-05)
and validated against the v2 schema they must land in.
"""
import json
import unittest
from pathlib import Path

from atlas.schema import FAERS_SUMMARY, ORANGE_BOOK, PURPLE_BOOK, validate
from atlas.sources.faers import build_faers_summary
from atlas.sources.orange_book import build_orange_book_record, read_tilde_file
from atlas.sources.purple_book import build_purple_book_record, read_purple_book_csv

FIX = Path(__file__).resolve().parent / "fixtures" / "sources"


class OrangeBookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = read_tilde_file((FIX / "orange_book_products_subset.txt").read_text())
        cls.patents = read_tilde_file((FIX / "orange_book_patent_subset.txt").read_text())
        cls.excl = read_tilde_file((FIX / "orange_book_exclusivity_subset.txt").read_text())

    def test_abrocitinib_record(self):
        rec = build_orange_book_record("213871", self.products, self.patents, self.excl, data_file_date="2026-08")
        self.assertEqual(validate(rec, ORANGE_BOOK), [])
        self.assertEqual(rec["trade_name"], "CIBINQO")
        self.assertEqual([p["strength"] for p in rec["products"]], ["50MG", "100MG", "200MG"])
        self.assertEqual(rec["products"][0]["approval_date"], "2022-01-14")
        codes = {(e["code"], e["expiration_date"]) for e in rec["exclusivities"]}
        self.assertIn(("NCE", "2027-01-14"), codes)
        self.assertIn(("NPP", "2026-02-09"), codes)
        self.assertTrue(all(len(e["product_numbers"]) == 3 for e in rec["exclusivities"]))
        self.assertTrue(rec["patents"], "abrocitinib has listed patents")
        self.assertEqual(rec["latest_exclusivity_expiration"], "2027-01-14")

    def test_upadacitinib_record(self):
        rec = build_orange_book_record("211675", self.products, self.patents, self.excl)
        self.assertEqual(validate(rec, ORANGE_BOOK), [])
        self.assertEqual(rec["ingredient"], "UPADACITINIB")
        p8962629 = [p for p in rec["patents"] if p["patent_number"] == "8962629"]
        self.assertTrue(p8962629)
        self.assertTrue(all(p["expiration_date"] == "2031-01-15" and p["drug_substance_claim"] for p in p8962629))
        self.assertEqual(rec["latest_patent_expiration"], "2038-03-09")
        self.assertIn("ODE-538", {e["code"] for e in rec["exclusivities"]})
        self.assertEqual(rec["latest_exclusivity_expiration"], "2032-04-28")

    def test_unknown_application_raises(self):
        with self.assertRaises(ValueError):
            build_orange_book_record("000000", self.products, self.patents, self.excl)


class PurpleBookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_purple_book_csv((FIX / "purple_book_subset.csv").read_text(encoding="utf-8"))

    def test_dupilumab_record(self):
        rec = build_purple_book_record("761055", self.rows, data_file_month="2026-08")
        self.assertEqual(validate(rec, PURPLE_BOOK), [])
        self.assertEqual(rec["proper_name"], "dupilumab")
        self.assertEqual(rec["license_type"], "351(a)")
        self.assertEqual(rec["license_number"], "1760")
        self.assertEqual(rec["first_approval_date"], "2017-03-28")
        self.assertEqual(rec["orphan_exclusivity_expiration"], "2031-01-25")
        self.assertEqual(rec["biosimilars"], [])

    def test_biologics_present(self):
        for bla, name in (("761306", "lebrikizumab-lbkz"), ("761180", "tralokinumab-ldrm")):
            rec = build_purple_book_record(bla, self.rows)
            self.assertEqual(validate(rec, PURPLE_BOOK), [], bla)
            self.assertEqual(rec["proper_name"], name)
            self.assertEqual(rec["center"], "CDER")


class FaersTest(unittest.TestCase):
    def test_summary_from_live_shapes(self):
        total = json.loads((FIX / "faers_one_record_dupilumab.json").read_text())
        serious = json.loads((FIX / "faers_count_serious_reactions_dupilumab.json").read_text())
        by_date = json.loads((FIX / "faers_count_receivedate_dupilumab.json").read_text())
        summary = build_faers_summary(
            "dupilumab", total, reaction_counts=serious, serious_reaction_counts=serious, yearly_counts=by_date,
            seriousness_totals={"serious_reports": 100000, "death_reports": None},
            api_urls=["https://api.fda.gov/drug/event.json?search=patient.drug.openfda.generic_name:%22dupilumab%22&limit=1"],
            sample_record=total["results"][0],
        )
        self.assertEqual(validate(summary, FAERS_SUMMARY), [])
        self.assertEqual(summary["total_reports"], 478975)
        self.assertEqual(summary["query"]["data_last_updated"], "2026-07-30")
        self.assertEqual(summary["top_serious_reactions"][0]["meddra_pt"], "PRODUCT USE IN UNAPPROVED INDICATION")
        self.assertEqual(summary["top_serious_reactions"][0]["report_count"], 4395)
        self.assertEqual(summary["meddra_version"], "19.0")
        self.assertTrue(all(isinstance(r["year"], int) for r in summary["reports_by_year"]))
        self.assertIsNone(summary["death_reports"])


if __name__ == "__main__":
    unittest.main()
