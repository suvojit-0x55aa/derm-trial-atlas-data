"""
Results-layer phase 3: the CT.gov backfill (atlas/results.py) and its
committed output (data/trials/*.json's results.* fields, arm_results.csv,
effect_estimates.csv).

The headline test here is test_ecztra1_easi75_week16_regression: the exact
wrong-answer case the design report proved (data/derm-trial-atlas-results-
schema/report.md S2.3) -- a naive read of ECZTRA 1's two "EASI-75 at week 16"-
adjacent measures picks the wrong one (a re-randomized-responder maintenance
subpopulation, 59.6%/49.1%/33.3%) instead of the real initial-period ITT
result (25.0%/12.7%). This must never regress silently.
"""
import json
import unittest
from pathlib import Path

from atlas.results import (
    canonicalize_effect_type, class_timepoint, classify_arm_role,
    comparison_kind_of, normalize_title, parse_pvalue, qc_arm_result_issues,
    qc_endpoint_hash_issues, sha1_of,
)

ROOT = Path(__file__).resolve().parent.parent
TRIALS = sorted((ROOT / "data" / "trials").glob("*.json"))


def load(nct):
    return json.loads((ROOT / "data" / "trials" / f"{nct}.json").read_text())


class RegressionTest(unittest.TestCase):
    def test_ecztra1_easi75_week16_regression(self):
        """The exact case the design report found and this whole effort exists
        to fix: ECZTRA 1 (Tralokinumab) posts TWO 'EASI-75'-adjacent measures.
        The correct headline (initial-period ITT, week 16) is 25.0%/12.7%.
        A naive read that conflates it with the re-randomized-responder
        maintenance subpopulation at week 52 gets 59.6%/49.1%/33.3% instead --
        real numbers, wrong question."""
        record = load("NCT03131648")
        primary_eps = record["endpoints"]["primary_endpoints"]["value"]
        easi75 = next(e for e in primary_eps if "75% Reduction" in e["verbatim"] and "Among" not in e["verbatim"])
        self.assertEqual(easi75["timepoints"], [{"value": 16, "unit": "week", "end_value": None}])

        rows = [r for r in record["results"]["arm_results"]["value"]
                if r["endpoint"]["rank"] == "primary" and r["endpoint"]["position"] == easi75["position"]]
        self.assertEqual(len(rows), 2, "expected exactly 2 arms (tralokinumab, placebo) on the true primary")
        rates = {r["response_rate_pct"] for r in rows}
        self.assertEqual(rates, {25.0, 12.7}, "wrong headline number -- got the re-randomized subgroup, not the ITT result")

        # the wrong (but legitimately real) subgroup numbers must still exist,
        # just under their OWN distinct endpoint reference, never this one.
        secondary_eps = record["endpoints"]["secondary_endpoints"]["value"]
        subgroup_ep = next(e for e in secondary_eps if "Among Subjects With EASI75" in e["verbatim"])
        self.assertNotEqual((subgroup_ep["rank"] if "rank" in subgroup_ep else "secondary", subgroup_ep["position"]),
                            ("primary", easi75["position"]))
        subgroup_rows = [r for r in record["results"]["arm_results"]["value"]
                         if r["endpoint"]["rank"] == "secondary" and r["endpoint"]["position"] == subgroup_ep["position"]]
        subgroup_rates = {r["response_rate_pct"] for r in subgroup_rows}
        self.assertEqual(subgroup_rates, {59.6, 49.1, 33.3})

    def test_solo1_easi75_week16_matches_report(self):
        """SOLO 1 (Dupilumab) at week 16: 14.7% placebo, 51.3%/52.5% dupilumab --
        the report's own worked example, reproduced from committed data."""
        record = load("NCT02277743")
        eps = {e["position"]: e for e in record["endpoints"]["secondary_endpoints"]["value"]}
        target = next(p for p, e in eps.items() if "Eczema Area and Severity Index-75" in e["verbatim"])
        rows = [r for r in record["results"]["arm_results"]["value"]
                if r["endpoint"]["rank"] == "secondary" and r["endpoint"]["position"] == target
                and r["timepoint"] == {"value": 16, "unit": "week", "end_value": None}]
        self.assertEqual({r["response_rate_pct"] for r in rows}, {14.7, 51.3, 52.5})


class ResultsUnitTest(unittest.TestCase):
    def test_canonicalize_effect_type_covers_the_8_canonical_buckets(self):
        cases = {
            "Odds Ratio (OR)": "odds_ratio", "Hazard Ratio (HR)": "hazard_ratio",
            "Risk Ratio (RR)": "risk_ratio", "Rate ratio": "risk_ratio",
            "Risk Difference (RD)": "risk_difference",
            "LS Mean Difference": "ls_mean_difference", "LSMean difference": "ls_mean_difference",
            "Median Difference (Net)": "median_difference",
            "Difference in Percentage": "response_rate_difference",
            "Treatment difference": "mean_difference",
        }
        for raw, expected in cases.items():
            self.assertEqual(canonicalize_effect_type(raw), expected, raw)

    def test_canonicalize_effect_type_null_for_unmapped(self):
        self.assertIsNone(canonicalize_effect_type("Markov Chain Monte Carlo (MCMC)"))
        self.assertIsNone(canonicalize_effect_type(None))

    def test_parse_pvalue_keeps_the_bound_not_a_bare_float(self):
        self.assertEqual(parse_pvalue("< 0.0001"), {"comparator": "<", "value": 0.0001, "verbatim": "< 0.0001"})
        self.assertEqual(parse_pvalue("<0.001"), {"comparator": "<", "value": 0.001, "verbatim": "<0.001"})

    def test_parse_pvalue_bare_number_defaults_to_equals(self):
        self.assertEqual(parse_pvalue("0.02"), {"comparator": "=", "value": 0.02, "verbatim": "0.02"})

    def test_parse_pvalue_null_input(self):
        self.assertIsNone(parse_pvalue(None))
        self.assertIsNone(parse_pvalue(""))

    def test_classify_arm_role_checks_text_not_ctgov_type(self):
        # design report S4.3: CT.gov's own armGroups[].type is unreliable
        self.assertEqual(classify_arm_role("Placebo Q2W", "Tralokinumab"), "placebo")
        self.assertEqual(classify_arm_role("Vehicle Cream BID", "Ruxolitinib"), "vehicle")
        self.assertEqual(classify_arm_role("Tralokinumab 300 mg Q2W", "Tralokinumab"), "investigational")
        self.assertEqual(classify_arm_role("Adalimumab", "Secukinumab"), "other")

    def test_class_timepoint_from_class_title(self):
        self.assertEqual(class_timepoint("Week 24", []), {"value": 24, "unit": "week", "end_value": None})
        self.assertEqual(class_timepoint("PASI 75 response at Week 12 (n=243, 245, 246)", []),
                         {"value": 12, "unit": "week", "end_value": None})

    def test_class_timepoint_falls_back_to_single_endpoint_timepoint(self):
        tps = [{"value": 16, "unit": "week", "end_value": None}]
        self.assertEqual(class_timepoint(None, tps), {"value": 16, "unit": "week", "end_value": None})
        self.assertEqual(class_timepoint("Safety and Tolerability", tps), {"value": 16, "unit": "week", "end_value": None})

    def test_class_timepoint_honest_null_when_ambiguous(self):
        self.assertIsNone(class_timepoint(None, []))
        self.assertIsNone(class_timepoint(None, [{"value": 4, "unit": "week", "end_value": None},
                                                   {"value": 16, "unit": "week", "end_value": None}]))

    def test_normalize_title_strips_time_frame_suffix_and_unicode_operators(self):
        self.assertEqual(normalize_title("EASI-75 (Time frame: Week 16)"), "EASI-75")
        self.assertEqual(normalize_title("Increase of ≥20 Points"), "Increase of >=20 Points")

    def test_comparison_kind_of(self):
        self.assertEqual(comparison_kind_of("SUPERIORITY"), "superiority")
        self.assertEqual(comparison_kind_of("NON_INFERIORITY"), "non_inferiority")
        self.assertEqual(comparison_kind_of("EQUIVALENCE"), "equivalence")
        self.assertEqual(comparison_kind_of(None), "other")
        self.assertEqual(comparison_kind_of("SOMETHING_ELSE"), "other")


class QcGateTest(unittest.TestCase):
    """Gates 1, 2, 4, 5 (design report S5.2) -- unit-level, independent of any
    committed trial data."""

    def record(self, enrollment=200):
        return {"population": {"enrollment_count": {"value": enrollment}},
                "endpoints": {"primary_endpoints": {"value": [
                    {"position": 1, "verbatim": "Real Endpoint Title"}]}}}

    def row(self, **overrides):
        base = {"denominator": 100, "value_type": "number", "responders": None,
                "response_rate_pct": None, "rate_is_derived": False}
        base.update(overrides)
        return base

    def test_gate1_denominator_exceeds_enrollment(self):
        issues = qc_arm_result_issues(self.record(enrollment=50), self.row(denominator=100))
        self.assertTrue(any("denominator" in i for i in issues))

    def test_gate1_clean_when_within_enrollment(self):
        self.assertEqual(qc_arm_result_issues(self.record(enrollment=200), self.row(denominator=100)), [])

    def test_gate2_count_type_requires_responders(self):
        issues = qc_arm_result_issues(self.record(), self.row(value_type="count_of_participants", responders=None))
        self.assertTrue(any("responders" in i for i in issues))

    def test_gate2_count_type_with_rate_requires_derived_flag(self):
        issues = qc_arm_result_issues(self.record(), self.row(
            value_type="count_of_participants", responders=50, response_rate_pct=50.0, rate_is_derived=False))
        self.assertTrue(any("rate_is_derived" in i for i in issues))

    def test_gate5_rate_out_of_range(self):
        issues = qc_arm_result_issues(self.record(), self.row(response_rate_pct=150.0))
        self.assertTrue(any("outside 0-100" in i for i in issues))

    def test_gate4_hash_mismatch_caught(self):
        record = self.record()
        ref = {"rank": "primary", "position": 1, "verbatim_sha1": sha1_of("A Different Title")}
        issues = qc_endpoint_hash_issues(record, ref)
        self.assertTrue(any("mismatch" in i for i in issues))

    def test_gate4_hash_match_clean(self):
        record = self.record()
        ref = {"rank": "primary", "position": 1, "verbatim_sha1": sha1_of("Real Endpoint Title")}
        self.assertEqual(qc_endpoint_hash_issues(record, ref), [])


class CommittedDataQcTest(unittest.TestCase):
    """Every arm_result/effect_estimate actually committed passes the 4 hard
    QC gates -- re-verified independently of the backfill script's own
    (identical) filtering, so a future hand-edit can't silently reintroduce
    a violation."""

    def test_every_committed_arm_result_passes_hard_gates(self):
        checked = 0
        for f in TRIALS:
            record = json.loads(f.read_text())
            for row in record["results"]["arm_results"]["value"] or []:
                checked += 1
                issues = qc_arm_result_issues(record, row) + qc_endpoint_hash_issues(record, row["endpoint"])
                self.assertEqual(issues, [], f"{f.name}: {issues}")
        self.assertGreater(checked, 5000)

    def test_every_committed_effect_estimate_passes_hash_gate(self):
        checked = 0
        for f in TRIALS:
            record = json.loads(f.read_text())
            for row in record["results"]["effect_estimates"]["value"] or []:
                checked += 1
                issues = qc_endpoint_hash_issues(record, row["endpoint"])
                self.assertEqual(issues, [], f"{f.name}: {issues}")
        self.assertGreater(checked, 1000)

    def test_published_results_never_populated(self):
        # out of scope for this task (design report S5.4) -- literature/label
        # results are a distinct, deliberately-untouched field.
        for f in TRIALS:
            record = json.loads(f.read_text())
            pr = record["results"]["published_results"]
            self.assertEqual(pr["source_type"], "needs_extraction", f.name)
            self.assertIsNone(pr["value"], f.name)


if __name__ == "__main__":
    unittest.main()
