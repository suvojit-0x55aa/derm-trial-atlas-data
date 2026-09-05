"""
Schema-level guarantees: every committed trial record validates, the
exported JSON Schema / SCHEMA.md are in sync with atlas/schema.py, the
documentation covers every field, and the flattened CSVs match the JSON.
"""
import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

from atlas import SCHEMA_VERSION
from atlas.schema import FIELD_DOCS, SOURCE_TYPES, to_json_schema, validate

ROOT = Path(__file__).resolve().parent.parent
TRIALS = sorted((ROOT / "data" / "trials").glob("*.json"))


class CommittedDataTest(unittest.TestCase):
    def test_every_trial_validates(self):
        self.assertEqual(len(TRIALS), 63)
        for f in TRIALS:
            rec = json.loads(f.read_text())
            with self.subTest(trial=f.name):
                self.assertEqual(rec["schema_version"], SCHEMA_VERSION)
                self.assertEqual(validate(rec), [])

    def test_no_free_text_values_remain(self):
        """A structured field's value is never a bare string (prose lives in source_excerpt)."""
        structured = {"population.severity_criteria", "design.background_therapy", "endpoints.multiplicity_control",
                      "timing_ops.study_schedule", "timing_ops.rescue_therapy", "molecule.mechanism_of_action",
                      "molecule.dosing_regimen", "adverse_events.boxed_warning",
                      "endpoints.primary_endpoints", "endpoints.secondary_endpoints"}
        for f in TRIALS:
            rec = json.loads(f.read_text())
            for path in structured:
                group, key = path.split(".")
                sv = rec[group][key]
                self.assertNotIsInstance(sv["value"], str, f"{f.name} {path} still holds prose")
                if sv["source_type"] != "needs_extraction":
                    self.assertIsNotNone(sv["value"], f"{f.name} {path}")

    def test_validator_rejects_bad_records(self):
        # SOLO 1 (NCT02277743): a v1 AD trial with severity_criteria, primary_endpoints
        # and dosing_regimen all filled -- unlike TRIALS[0] (alphabetically first, which
        # since the indication-expansion pass can be a trial that's still needs_extraction
        # on one of these fields, e.g. an HS trial with no auto-parsed severity criterion).
        rec = json.loads((ROOT / "data" / "trials" / "NCT02277743.json").read_text())
        rec["population"]["severity_criteria"]["value"]["criteria"][0]["comparator"] = "≥"
        rec["endpoints"]["primary_endpoints"]["value"][0]["measure_type"] = "free text"
        rec["timing_ops"]["start_date"]["value"]["date"] = "2014-09"
        rec["molecule"]["dosing_regimen"]["value"][0]["extra"] = 1
        errors = validate(rec)
        self.assertEqual(len(errors), 4, errors)

    def test_source_types_closed(self):
        seen = set()
        for f in TRIALS:
            rec = json.loads(f.read_text())
            for group in rec.values():
                if isinstance(group, dict):
                    for sv in group.values():
                        if isinstance(sv, dict) and "source_type" in sv:
                            seen.add(sv["source_type"])
                    if "source_type" in group:
                        seen.add(group["source_type"])
        self.assertTrue(seen <= set(SOURCE_TYPES), seen - set(SOURCE_TYPES))


class ExportsInSyncTest(unittest.TestCase):
    def test_json_schema_and_docs_match_spec(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_schema.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_json_schema_is_draft07_and_strict(self):
        js = json.loads((ROOT / "schema" / "trial.schema.json").read_text())
        self.assertEqual(js["$schema"], "http://json-schema.org/draft-07/schema#")
        self.assertFalse(js["additionalProperties"])
        self.assertIn("exclusivity", js["properties"])
        self.assertEqual(js, to_json_schema())

    def test_docs_cover_every_field(self):
        md = (ROOT / "docs" / "SCHEMA.md").read_text()
        for path, _, _ in FIELD_DOCS:
            self.assertIn(f"`{path}`", md)
        self.assertEqual(len(FIELD_DOCS), 39)  # 35 v1 fields + faers_summary + 3 exclusivity fields


class CsvTest(unittest.TestCase):
    def test_flattened_tables_match_json(self):
        eps = list(csv.DictReader((ROOT / "endpoints.csv").open()))
        sev = list(csv.DictReader((ROOT / "severity_criteria.csv").open()))
        trials = list(csv.DictReader((ROOT / "trials.csv").open()))
        sources = list(csv.DictReader((ROOT / "sources.csv").open()))
        n_endpoints = n_crit = 0
        for f in TRIALS:
            rec = json.loads(f.read_text())
            e = rec["endpoints"]
            n_endpoints += len(e["primary_endpoints"]["value"]) + len(e["secondary_endpoints"]["value"])
            sev_val = rec["population"]["severity_criteria"]["value"]
            if sev_val is not None:  # needs_extraction for some new-indication trials -- no criteria to count
                n_crit += len(sev_val["criteria"])
        self.assertEqual(len({(r["nct_id"], r["rank"], r["position"]) for r in eps}), n_endpoints)
        self.assertEqual(len(sev), n_crit)
        self.assertEqual(len(trials), 63)
        self.assertEqual(len(sources), 63 * 39)
        # the atlas's headline query -- "which trials measure EASI-75 at week 16" -- is a plain filter
        easi75_wk16 = [r for r in eps if r["criterion_scale"] == "EASI" and r["criterion_value"] == "75"
                       and r["criterion_role"] == "responder" and "16w" in r["timepoints"].split(";")]
        self.assertGreaterEqual(len({r["nct_id"] for r in easi75_wk16}), 14)


if __name__ == "__main__":
    unittest.main()
