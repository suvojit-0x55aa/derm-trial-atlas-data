"""
timing_ops.study_schedule -- structured decomposition of the v1
`visit_schedule` prose, one entry per trial.

Value shape:
    {
      "screening_days": 35 | null,  "screening_washout": bool | null,
      "periods": [{"name", "start_week", "end_week", "duration_weeks", "blinding", "background_tcs"}],
      "dosing_interval": "weekly" | null,
      "visit_cadence": "weekly" | "every_2_weeks" | "every_4_weeks" | null,
      "visit_cadence_until_week": 52 | null,
      "visit_weeks": [1, 2, 4, ...] | null,  "visit_days": [1] | null,
      "phone_contact_weeks": [1, 6] | null,
      "primary_endpoint_week": 16,
      "end_of_treatment_week": 16 | null, "end_of_study_week": 64 | null,
      "total_duration_weeks": 64 | null,
      "follow_up_weeks": 12 | null, "follow_up_days": 30 | null,
      "follow_up_visit_week": 66 | null,
      "long_term_extension": bool | null, "extension_end_week": 136 | null,
      "extension_visit_interval_weeks": 12 | null, "extension_study_id": "1225" | null,
      "rerandomization_week": 16 | null, "maintenance_arms": ["Q2W", "Q4W", "placebo"] | null,
      "maintenance_response_check_weeks": [24, 32, 40, 48] | null,
      "last_injection_week": 14 | null, "key_secondary_weeks": [2, 16] | null,
      "follow_up_visit_interval_weeks": 4 | null,
      "end_of_treatment_weeks_after_last_dose": 1 | null, "background_tcs_from_day": 1 | null,
      "primary_endpoint_refs": [EndpointRef], "double_dummy_arms": [...], "active_comparator": "dupilumab" | null,
      "boilerplate_reused_from": ["ECZTRA-1"], "conflicts_with_trial": "ECZTRA-3" | null,
      "full_visit_table_available": false,
      "source_inconsistency": str | null     # kept only for ECZTRA-3's boilerplate conflict
    }
"""

PERIOD_NAMES = ("screening", "randomized_treatment", "double_blind_treatment", "initial_treatment",
                "maintenance_treatment", "continuation_treatment", "induction_treatment",
                "long_term_maintenance", "long_term_extension", "follow_up", "double_dummy_treatment",
                "oral_only_treatment", "off_treatment_follow_up")


from .curated_multiplicity import EASI75, IGA01_2PT, ref

PRIMARY_IGA_EASI = [ref("IGA 0/1 + >=2-point reduction", "IGA", IGA01_2PT, 16), ref("EASI-75", "EASI", EASI75, 16)]


def period(name, start, end, blinding=None, background_tcs=None):
    return {"name": name, "start_week": start, "end_week": end,
            "duration_weeks": (end - start) if (start is not None and end is not None) else None,
            "blinding": blinding, "background_tcs": background_tcs}


def _base(**kw):
    v = {
        "screening_days": None, "screening_washout": None, "periods": [],
        "dosing_interval": None, "visit_cadence": None, "visit_cadence_until_week": None,
        "visit_weeks": None, "visit_days": None, "phone_contact_weeks": None,
        "primary_endpoint_week": None, "end_of_treatment_week": None, "end_of_study_week": None,
        "total_duration_weeks": None, "follow_up_weeks": None, "follow_up_days": None,
        "follow_up_visit_week": None, "long_term_extension": None, "extension_end_week": None,
        "extension_visit_interval_weeks": None, "extension_study_id": None,
        "rerandomization_week": None, "maintenance_arms": None,
        "maintenance_response_check_weeks": None, "last_injection_week": None,
        "key_secondary_weeks": None, "follow_up_visit_interval_weeks": None,
        "end_of_treatment_weeks_after_last_dose": None, "background_tcs_from_day": None,
        "primary_endpoint_refs": [], "double_dummy_arms": [], "active_comparator": None,
        "boilerplate_reused_from": [], "conflicts_with_trial": None,
        "full_visit_table_available": False, "source_inconsistency": None,
    }
    v.update(kw)
    return v


CHRONOS = _base(
    periods=[period("randomized_treatment", 0, 52, background_tcs=True), period("follow_up", 52, 64)],
    end_of_treatment_week=52, end_of_study_week=64, total_duration_weeks=64, follow_up_weeks=12,
    long_term_extension=True, extension_study_id="1225", end_of_treatment_weeks_after_last_dose=1,
    background_tcs_from_day=1,
)
SOLO = _base(
    screening_days=35, screening_washout=True,
    periods=[period("randomized_treatment", 0, 16), period("follow_up", 16, 20), period("follow_up", 20, 28)],
    dosing_interval="weekly", visit_cadence="weekly", visit_cadence_until_week=16,
    primary_endpoint_week=16, end_of_treatment_week=16, end_of_study_week=28, total_duration_weeks=28,
    follow_up_weeks=4, long_term_extension=True, follow_up_visit_interval_weeks=4,
)
ECZTRA12 = _base(
    periods=[period("initial_treatment", 0, 16), period("maintenance_treatment", 16, 52),
             period("off_treatment_follow_up", 52, 66)],
    visit_cadence="every_2_weeks", visit_cadence_until_week=52, follow_up_visit_week=66,
    primary_endpoint_week=16, end_of_treatment_week=52, end_of_study_week=66, total_duration_weeks=66,
    follow_up_weeks=16,
)
ECZTRA3 = _base(
    periods=[period("initial_treatment", 0, 16), period("continuation_treatment", 16, 32),
             period("off_treatment_follow_up", 32, 46)],
    visit_cadence="every_2_weeks", visit_cadence_until_week=52, follow_up_visit_week=66,
    primary_endpoint_week=16, end_of_treatment_week=32, end_of_study_week=46, total_duration_weeks=46,
    follow_up_weeks=14, boilerplate_reused_from=["ECZTRA-1", "ECZTRA-2"], conflicts_with_trial="ECZTRA-3",
    source_inconsistency="Source trial-design text reuses ECZTRA-1/2 boilerplate (visits every other week until Week 52, follow-up at Week 66) that conflicts with ECZTRA-3's own Week 46 end; quoted as written, not reconciled.",
)
JADE_MONO = _base(
    screening_days=28,
    periods=[period("double_blind_treatment", 0, 12, blinding="double_blind"), period("follow_up", 12, 16)],
    visit_weeks=[0, 2, 4, 8, 12, 16], phone_contact_weeks=[1, 6],
    primary_endpoint_week=12, end_of_treatment_week=12, end_of_study_week=16, total_duration_weeks=16,
    follow_up_weeks=4, long_term_extension=True, follow_up_visit_week=16,
)
JADE_COMPARE = _base(
    screening_days=28,
    periods=[period("double_dummy_treatment", 0, 16, blinding="double_blind"),
             period("oral_only_treatment", 16, 20, blinding="double_blind"), period("follow_up", 20, 24)],
    primary_endpoint_week=12, end_of_treatment_week=20, end_of_study_week=24, total_duration_weeks=24,
    follow_up_weeks=4, last_injection_week=14, key_secondary_weeks=[2, 16],
    double_dummy_arms=["abrocitinib + dupilumab-matching placebo", "dupilumab + abrocitinib-matching placebo", "double placebo"],
    active_comparator="dupilumab",
)
MEASURE_UP = _base(
    screening_days=35,
    periods=[period("double_blind_treatment", 0, 16, blinding="double_blind"),
             period("long_term_extension", 16, 136, blinding="double_blind")],
    visit_days=[1], visit_weeks=[1, 2, 4, 8, 12, 16, 20, 24, 32, 40, 52],
    extension_visit_interval_weeks=12, extension_end_week=136, long_term_extension=True,
    primary_endpoint_week=16, follow_up_days=30, end_of_treatment_week=136,
)
ADUP = _base(**{**MEASURE_UP, "periods": [
    period("double_blind_treatment", 0, 16, blinding="double_blind", background_tcs=True),
    period("long_term_extension", 16, 136, blinding="double_blind"),
]})
ADVOCATE = _base(
    periods=[period("induction_treatment", 0, 16), period("long_term_maintenance", 16, 52)],
    primary_endpoint_week=16, end_of_treatment_week=52, total_duration_weeks=52,
    rerandomization_week=16, maintenance_arms=["lebrikizumab Q2W", "lebrikizumab Q4W", "placebo"],
    maintenance_response_check_weeks=[24, 32, 40, 48], primary_endpoint_refs=PRIMARY_IGA_EASI,
)
ADHERE = _base(
    periods=[period("randomized_treatment", 0, 16, blinding="double_blind", background_tcs=True)],
    primary_endpoint_week=16, end_of_treatment_week=16, total_duration_weeks=16,
    primary_endpoint_refs=PRIMARY_IGA_EASI, active_comparator=None,
)

STUDY_SCHEDULE = {
    "NCT02260986": CHRONOS,
    "NCT02277743": SOLO,
    "NCT02277769": SOLO,
    "NCT03131648": ECZTRA12,
    "NCT03160885": ECZTRA12,
    "NCT03349060": JADE_MONO,
    "NCT03363854": ECZTRA3,
    "NCT03568318": ADUP,
    "NCT03569293": MEASURE_UP,
    "NCT03575871": JADE_MONO,
    "NCT03607422": MEASURE_UP,
    "NCT03720470": JADE_COMPARE,
    "NCT04146363": ADVOCATE,
    "NCT04178967": ADVOCATE,
    "NCT04250337": ADHERE,
}
