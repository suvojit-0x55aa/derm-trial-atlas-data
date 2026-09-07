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
from atlas.schema import (ARM, ARM_RESULT, EFFECT_ESTIMATE, ENDPOINT_KEY, FIELD_DOCS, PVALUE,
                          SOURCE_TYPES, to_json_schema, validate)

ROOT = Path(__file__).resolve().parent.parent
TRIALS = sorted((ROOT / "data" / "trials").glob("*.json"))


class CommittedDataTest(unittest.TestCase):
    def test_every_trial_validates(self):
        self.assertEqual(len(TRIALS), 140)
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
        self.assertEqual(len(FIELD_DOCS), 44)  # 35 v1 fields + faers_summary + 3 exclusivity fields + 4 v3 results fields + drug_characterization (cycle 23)


class ResultsLayerSchemaTest(unittest.TestCase):
    """Schema v3's results.* types (atlas/schema.py's ENDPOINT_KEY, PVALUE,
    ARM, ARM_RESULT, EFFECT_ESTIMATE), exercised directly against `validate`
    with a custom spec rather than a full trial record."""

    def endpoint_key(self):
        return {"rank": "primary", "position": 1, "verbatim_sha1": "a" * 40}

    def arm_result(self, **overrides):
        result = {
            "endpoint": self.endpoint_key(), "arm_id": "OG000",
            "timepoint": {"value": 16, "unit": "week", "end_value": None},
            "analysis_population": "full_analysis_set", "study_period": "double_blind",
            "denominator": 108, "value_type": "count_of_participants",
            "reported_value": 32.0, "reported_unit": "Participants",
            "responders": 32, "response_rate_pct": 29.6, "rate_is_derived": False,
            "dispersion_type": None, "dispersion_value": None,
            "ci_pct": None, "ci_lower": None, "ci_upper": None,
            "ctgov_class_title": "Week 16",
        }
        result.update(overrides)
        return result

    def effect_estimate(self, **overrides):
        est = {
            "endpoint": self.endpoint_key(), "timepoint": {"value": 16, "unit": "week", "end_value": None},
            "test_arm_id": "OG001", "reference_arm_id": "OG000",
            "comparison_kind": "superiority", "effect_type": "response_rate_difference",
            "effect_type_verbatim": "Difference in Percentages", "effect_value": 29.5,
            "ci_pct": 95.0, "ci_lower": 16.87, "ci_upper": 42.05, "ci_sides": 2,
            "p_value": {"comparator": "<", "value": 0.0001, "verbatim": "< 0.0001"},
            "statistical_method": "Cochran-Mantel-Haenszel", "adjusted_for": [],
        }
        est.update(overrides)
        return est

    def test_endpoint_key_valid(self):
        self.assertEqual(validate(self.endpoint_key(), spec=ENDPOINT_KEY), [])

    def test_endpoint_key_rejects_bad_rank(self):
        errs = validate({**self.endpoint_key(), "rank": "tertiary"}, spec=ENDPOINT_KEY)
        self.assertTrue(errs)

    def test_pvalue_valid_and_keeps_comparator(self):
        pv = {"comparator": "<", "value": 0.0001, "verbatim": "< 0.0001"}
        self.assertEqual(validate(pv, spec=PVALUE), [])

    def test_pvalue_rejects_bad_comparator(self):
        errs = validate({"comparator": "!=", "value": 0.05, "verbatim": "!= 0.05"}, spec=PVALUE)
        self.assertTrue(errs)

    def test_arm_valid(self):
        arm = {"arm_id": "OG000", "label": "Placebo QW + TCS", "role": "placebo",
               "analysis_population": None,
               "intervention_names": ["Placebo"], "dose_value": None, "dose_unit": None,
               "frequency": None, "randomized_n": 108}
        self.assertEqual(validate(arm, spec=ARM), [])

    def test_arm_rejects_bad_role(self):
        arm = {"arm_id": "OG000", "label": "Placebo", "role": "control",
               "analysis_population": None,
               "intervention_names": [], "dose_value": None, "dose_unit": None,
               "frequency": None, "randomized_n": None}
        errs = validate(arm, spec=ARM)
        self.assertTrue(errs)

    def test_arm_result_valid(self):
        self.assertEqual(validate(self.arm_result(), spec=ARM_RESULT), [])

    def test_arm_result_nullable_timepoint(self):
        # a measure with no single timepoint (e.g. "Time to Loss of Response")
        self.assertEqual(validate(self.arm_result(timepoint=None), spec=ARM_RESULT), [])

    def test_arm_result_rejects_missing_key(self):
        bad = self.arm_result()
        del bad["denominator"]
        errs = validate(bad, spec=ARM_RESULT)
        self.assertTrue(errs)

    def test_arm_result_rejects_bad_value_type(self):
        errs = validate(self.arm_result(value_type="percentage"), spec=ARM_RESULT)
        self.assertTrue(errs)

    def test_arm_result_count_type_forces_responders_and_derived_flag_shape(self):
        # schema only enforces shape, not the cross-field QC rule itself (that's
        # phase 3's job) -- but a null responders / false rate_is_derived on a
        # count-of-participants row must still be a *valid*, representable shape
        # (a count row before its rate is derived).
        self.assertEqual(validate(self.arm_result(value_type="count_of_participants",
                                                    responders=None, rate_is_derived=False), spec=ARM_RESULT), [])

    def test_effect_estimate_valid(self):
        self.assertEqual(validate(self.effect_estimate(), spec=EFFECT_ESTIMATE), [])

    def test_effect_estimate_null_effect_type_keeps_verbatim(self):
        # 62 raw paramType spellings map to only 8 canonical types (99.8% of rows) --
        # a row outside those 8 must still validate with effect_type null and the
        # raw label preserved.
        est = self.effect_estimate(effect_type=None, effect_type_verbatim="Hodges-Lehmann Estimation")
        self.assertEqual(validate(est, spec=EFFECT_ESTIMATE), [])

    def test_effect_estimate_nullable_p_value(self):
        self.assertEqual(validate(self.effect_estimate(p_value=None), spec=EFFECT_ESTIMATE), [])

    def test_effect_estimate_rejects_bad_comparison_kind(self):
        errs = validate(self.effect_estimate(comparison_kind="post_hoc"), spec=EFFECT_ESTIMATE)
        self.assertTrue(errs)

    def test_effect_estimate_rejects_bad_effect_type(self):
        errs = validate(self.effect_estimate(effect_type="difference_in_means"), spec=EFFECT_ESTIMATE)
        self.assertTrue(errs)


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
        self.assertEqual(len(trials), 140)
        self.assertEqual(len(sources), 140 * 44)
        # the atlas's headline query -- "which trials measure EASI-75 at week 16" -- is a plain filter
        easi75_wk16 = [r for r in eps if r["criterion_scale"] == "EASI" and r["criterion_value"] == "75"
                       and r["criterion_role"] == "responder" and "16w" in r["timepoints"].split(";")]
        self.assertGreaterEqual(len({r["nct_id"] for r in easi75_wk16}), 14)


if __name__ == "__main__":
    unittest.main()
