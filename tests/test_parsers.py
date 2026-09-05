"""
Unit tests for the deterministic parsers, pinned on the real phrasing found
in the 17-trial corpus so a regex change that silently reinterprets a
threshold, timepoint, or scale fails here first.
"""
import unittest

from atlas.dosing import parse_dosing_regimen
from atlas.endpoints import parse_endpoint
from atlas.label import parse_boxed_warning, parse_mechanism
from atlas.scalars import parse_age_years, parse_ctgov_date, parse_us_date
from atlas.severity import parse_severity


def crit(c):
    return (c["scale"], c["metric"], c["comparator"], c["value"], c["unit"])


class SeverityTest(unittest.TestCase):
    def test_solo1_numbered_clauses(self):
        r = parse_severity("3. Eczema Area and Severity Index (EASI) Score ≥16 at the screening and baseline visits; | "
                           "4. Investigator's Global Assessment (IGA) Score ≥3 (on the 0 to 4 IGA scale, in which 3 is moderate and 4 is severe) at the screening and baseline visits; | "
                           "5. ≥10% body surface area (BSA) of AD involvement at the screening and baseline visits;")
        self.assertEqual(r["source_criterion_numbers"], [3, 4, 5])
        self.assertEqual([crit(c) for c in r["criteria"]], [
            ("EASI", "absolute_score", ">=", 16, "score"),
            ("IGA", "absolute_score", ">=", 3, "score"),
            ("BSA", "percent_bsa", ">=", 10, "percent"),
        ])
        iga = r["criteria"][1]
        self.assertEqual((iga["scale_min"], iga["scale_max"]), (0, 4))
        self.assertEqual(iga["scale_anchors"], [{"score": 3, "label": "moderate"}, {"score": 4, "label": "severe"}])
        self.assertEqual(iga["assessed_at"], ["screening", "baseline"])

    def test_ecztra_two_visit_easi(self):
        r = parse_severity("6. AD involvement of ≥10% body surface area at screening and baseline (visit 3). | "
                           "7. An EASI score of ≥12 at screening and 16 at baseline. | 8. An IGA score of ≥3 at screening and at baseline.")
        self.assertEqual(r["baseline_visit_number"], 3)
        easi = [c for c in r["criteria"] if c["scale"] == "EASI"]
        self.assertEqual([(c["value"], c["assessed_at"]) for c in easi], [(12, ["screening"]), (16, ["baseline"])])

    def test_jade_list_and_duration(self):
        r = parse_severity("Diagnosis of atopic dermatitis (AD) for at least 1 year and current status of moderate to severe disease "
                           "(\\>= the following scores: BSA 10%, IGA 3, EASI 16, Pruritus NRS severity 4)")
        self.assertEqual(r["severity_label"], "moderate_to_severe")
        self.assertEqual(crit(r["criteria"][0]), (None, "disease_duration_years", ">=", 1, "years"))
        self.assertEqual({crit(c)[0] for c in r["criteria"][1:]}, {"BSA", "IGA", "EASI", "Pruritus NRS"})
        self.assertEqual(r["criteria"][-1]["scale_variant"], "severity")

    def test_cross_reference(self):
        r = parse_severity("By cross-reference to studies 1334/1416 (SOLO 1/SOLO 2): EASI Score >=16 at screening and baseline; "
                           "Investigator's Global Assessment (IGA) Score >=3 (0-4 scale, 3=moderate, 4=severe) at screening and baseline; "
                           ">=10% body surface area (BSA) of AD involvement at screening and baseline.")
        self.assertEqual(r["basis"], "cross_reference")
        self.assertEqual(r["cross_reference"], {"study_ids": ["1334", "1416"], "trial_names": ["SOLO 1", "SOLO 2"]})
        self.assertEqual(len(r["criteria"]), 3)

    def test_viga_and_worst_pruritus(self):
        r = parse_severity("Active moderate to severe AD defined by Eczema Area and Severity Index (EASI) ≥ 16, validated Investigator's Global Assessment (vIGA) ≥ 3, "
                           "body surface area (BSA) affected by AD ≥ 10%, and weekly average of daily Worst Pruritus numerical rating scale (NRS) score ≥ 4.")
        scales = {c["scale"]: c for c in r["criteria"]}
        self.assertEqual(set(scales), {"EASI", "vIGA-AD", "BSA", "Pruritus NRS"})
        self.assertEqual(scales["Pruritus NRS"]["scale_variant"], "worst_daily_weekly_average")
        self.assertIsNone(scales["EASI"]["scale_variant"])


class EndpointTest(unittest.TestCase):
    def test_iga_composite_primary(self):
        e = parse_endpoint('Percentage of Participants With Investigator\'s Global Assessment (IGA) Score of "0" or "1" and Reduction From Baseline of ≥2 Points at Week 16 (Time frame: Week 16)', "primary", 1)
        self.assertEqual(e["measure_type"], "responder_rate")
        self.assertEqual([crit(c) for c in e["responder_criteria"]],
                         [("IGA", "absolute_score", "in", [0, 1], "score"), ("IGA", "point_reduction_from_baseline", ">=", 2, "points")])
        self.assertEqual(e["timepoints"], [{"value": 16, "unit": "week", "end_value": None}])
        self.assertEqual(e["time_frame"], "Week 16")

    def test_easi75_multi_week_double_blind(self):
        e = parse_endpoint("Percentage of Participants Achieving Eczema Area and Severity Index (EASI) Response >=75% Improvement From Baseline at Weeks 12, 16, 28, 40 and 52: Double-blind Period", "secondary", 3)
        self.assertEqual(crit(e["responder_criteria"][0]), ("EASI", "percent_improvement_from_baseline", ">=", 75, "percent"))
        self.assertEqual([t["value"] for t in e["timepoints"]], [12, 16, 28, 40, 52])
        self.assertEqual(e["study_period"], "double_blind")

    def test_subgroup_baseline_threshold(self):
        e = parse_endpoint("Percentage of Participants With a Pruritus NRS Score of ≥5-points at Baseline Who Achieve a ≥4-point Reduction in Pruritus NRS Score From Baseline to Week 16", "secondary", 7)
        self.assertEqual(crit(e["responder_criteria"][0]), ("Pruritus NRS", "point_reduction_from_baseline", ">=", 4, "points"))
        self.assertEqual(crit(e["subgroup_criteria"][0]), ("Pruritus NRS", "absolute_score", ">=", 5, "score"))
        self.assertEqual(e["subgroup_criteria"][0]["assessed_at"], ["baseline"])

    def test_rerandomized_maintenance(self):
        e = parse_endpoint("Percentage of Participants From Those Re-randomized Having Achieved EASI-75 at Week 16 Who Continue to Exhibit EASI-75 at Week 52 (EASI-75 Calculated Relative to Baseline EASI Score)", "secondary", 20)
        self.assertEqual(e["analysis_population"], "re_randomized_responders")
        self.assertEqual(e["subgroup_criteria"][0]["assessed_at"], ["week_16"])
        self.assertEqual({t["value"] for t in e["timepoints"]}, {16, 52})

    def test_measure_types(self):
        cases = {
            "Percent Change From Baseline in Eczema Area and Severity Index (EASI) Score to Week 16": ("percent_change_from_baseline", "EASI"),
            "Change From Baseline in Dermatology Life Quality Index (DLQI) at Week 2, 4, 8 and 12": ("change_from_baseline", "DLQI"),
            "Time to Achieve >=4 Points Improvement From Baseline in Numerical Rating Scale (NRS) for Severity of Pruritus": ("time_to_event", "Pruritus NRS"),
            "Number of Flares Through Week 52": ("count", None),
            "Frequency of Anti-drug Antibodies (ADA)": ("immunogenicity", None),
            "Percentage of Participants With Treatment Emergent Serious Adverse Events (TESAEs) From Baseline Through Week 16": ("safety_incidence", None),
            "DLQI at Week 20": ("absolute_value", "DLQI"),
            "Main Study: Percentage of Participants Experiencing a Flare During the Double-blind Treatment Period": ("flare_incidence", None),
        }
        for title, (mtype, scale) in cases.items():
            e = parse_endpoint(title, "secondary", 1)
            self.assertEqual((e["measure_type"], e["scale"]), (mtype, scale), title)

    def test_hads_dual_threshold_and_component(self):
        e = parse_endpoint("Adolescents: Percentage of Participants Achieving HADS-A Score and HADS-D Score of < 8 at Week 16", "secondary", 1)
        self.assertEqual(e["analysis_population"], "adolescents")
        self.assertEqual([(c["scale_component"], c["comparator"], c["value"]) for c in e["responder_criteria"]],
                         [("Anxiety", "<", 8), ("Depression", "<", 8)])

    def test_day_range_and_through(self):
        e = parse_endpoint("Percentage of Participants With at Least 4 Points Improvement in the Numerical Rating Scale (NRS) for Severity of Pruritus From Baseline at Day 2-15, Week 2, 4, 8, 12 and 16", "secondary", 1)
        self.assertEqual(e["timepoints"][0], {"value": 2, "unit": "day", "end_value": 15})
        e2 = parse_endpoint("Least Square Mean of Number of Steroid-free Days From Baseline up to Week 16", "secondary", 1)
        self.assertEqual(e2["through"], {"value": 16, "unit": "week"})
        self.assertEqual(e2["event_type"], "steroid_free_days")


class DosingTest(unittest.TestCase):
    def test_oral_tablets(self):
        v = parse_dosing_regimen("PF-04965842 100 mg: PF-04965842 100 mg, administered as two tablets to be taken orally once daily for 12 weeks || "
                                 "PF-04965842 200 mg: PF-04965842 200 mg, administered as two tablets to be taken orally once daily for 12 weeks")
        self.assertEqual([(x["dose_value"], x["dose_unit"], x["units_per_dose"], x["frequency"], x["duration_weeks"], x["route"]) for x in v],
                         [(100, "mg", 2, "once_daily", 12, "oral"), (200, "mg", 2, "once_daily", 12, "oral")])

    def test_subcutaneous_sites_and_placebo(self):
        v = parse_dosing_regimen("Dupilumab: Subcutaneous injection alternated among the different quadrants of the abdomen, upper thighs and upper arms || "
                                 "Placebo (for Dupilumab): Subcutaneous injection alternated among the different quadrants of the abdomen, upper thighs and upper arms")
        self.assertEqual(v[0]["administration_sites"], ["abdomen", "upper thighs", "upper arms"])
        self.assertTrue(v[1]["is_placebo"])
        self.assertIsNone(v[1]["dose_value"])

    def test_antibody_description(self):
        v = parse_dosing_regimen("Tralokinumab: Tralokinumab is a human recombinant monoclonal antibody of the IgG4 subclass that specifically binds to human IL-13 and blocks interaction with the IL-13 receptors. It is presented as a liquid formulation for subcutaneous (SC) administration")
        self.assertEqual((v[0]["antibody_isotype"], v[0]["molecular_target"], v[0]["dose_form"], v[0]["route"]), ("IgG4", "IL-13", "solution", "subcutaneous"))


class LabelTest(unittest.TestCase):
    def test_jak_inhibitor_selectivity(self):
        m = parse_mechanism("12.1 Mechanism of Action CIBINQO is a Janus kinase (JAK) inhibitor. Abrocitinib reversibly inhibits JAK1 by blocking the adenosine triphosphate (ATP) binding site. "
                            "In a cell-free isolated enzyme assay, abrocitinib was selective for JAK1 over JAK2 (28-fold), JAK3 (>340-fold), and tyrosine kinase (TYK) 2 (43-fold), as well as the broader kinome. "
                            "The relevance of inhibition of specific JAK enzymes to therapeutic effectiveness is not currently known.")
        self.assertEqual((m["modality"], m["drug_class"], m["kinases_inhibited"], m["reversible"], m["label_section"]),
                         ("small_molecule", "JAK inhibitor", ["JAK1"], True, "12.1"))
        self.assertEqual([(s["over"], s["fold"], s["comparator"]) for s in m["selectivity"]], [("JAK2", 28, "=="), ("JAK3", 340, ">"), ("TYK2", 43, "==")])

    def test_antibody(self):
        m = parse_mechanism("12.1 Mechanism of Action Dupilumab is a human monoclonal IgG4 antibody that inhibits interleukin-4 (IL-4) and interleukin-13 (IL-13) signaling by specifically binding to the IL-4Rα subunit shared by the IL-4 and IL-13 receptor complexes. The mechanism of dupilumab action has not been definitively established.")
        self.assertEqual((m["modality"], m["antibody_isotype"], m["binding_targets"], m["mechanism_established"]),
                         ("monoclonal_antibody", "IgG4", ["IL-4Rα"], False))
        self.assertEqual(set(m["pathway_cytokines"]), {"IL-4", "IL-13"})

    def test_boxed_warning(self):
        b = parse_boxed_warning("WARNING: SERIOUS INFECTIONS, MORTALITY, MALIGNANCY, MAJOR ADVERSE CARDIOVASCULAR EVENTS, and THROMBOSIS SERIOUS INFECTIONS Patients treated with RINVOQ /RINVOQ LQ are at increased risk [see Warnings and Precautions ( 5.1 )]. MORTALITY ... ( 5.2 ) THROMBOSIS ... ( 5.5 )")
        self.assertTrue(b["present"])
        self.assertEqual(b["title"], "SERIOUS INFECTIONS, MORTALITY, MALIGNANCY, MAJOR ADVERSE CARDIOVASCULAR EVENTS, and THROMBOSIS")
        self.assertEqual(b["warning_categories"], ["serious_infections", "mortality", "malignancy", "mace", "thrombosis"])
        self.assertEqual(b["referenced_label_sections"], ["5.1", "5.2", "5.5"])
        self.assertEqual(b["product_names"], ["RINVOQ", "RINVOQ LQ"])
        self.assertEqual(parse_boxed_warning(None)["present"], False)


class ScalarTest(unittest.TestCase):
    def test_ages_and_dates(self):
        self.assertEqual(parse_age_years("18 Years"), 18)
        self.assertEqual(parse_age_years("6 Months"), 0.5)
        self.assertIsNone(parse_age_years(None))
        self.assertEqual(parse_ctgov_date("2014-09"), {"date": "2014-09-01", "precision": "month"})
        self.assertEqual(parse_ctgov_date("2016-01-31"), {"date": "2016-01-31", "precision": "day"})
        self.assertEqual(parse_us_date("Jan 14, 2027"), "2027-01-14")
        self.assertEqual(parse_us_date("28-Mar-17"), "2017-03-28")
        self.assertEqual(parse_us_date("3/28/2017"), "2017-03-28")
        with self.assertRaises(ValueError):
            parse_age_years("adult")


if __name__ == "__main__":
    unittest.main()
