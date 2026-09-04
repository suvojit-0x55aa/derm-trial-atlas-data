"""
timing_ops.rescue_therapy -- structured decomposition of the v1
`rescue_therapy_rules` prose, one entry per trial.

Value shape:
    {
      "permitted": bool,
      "trigger": "investigator_discretion" | "protocol_response_threshold" | "flare_definition" | "prohibited",
      "earliest_week": 2 | 4 | null,  "prohibited_through_week": 2 | 16 | null,
      "trigger_rules": [{"from_week", "to_week", "criterion": ScoreCriterion, "consecutive_visits"}],
      "flare_definition": [ScoreCriterion],
      "first_step": "topical" | null,
      "topical_min_days_before_systemic": 7 | 14 | null,
      "topical_rescue_requires_study_drug_discontinuation": bool | null,
      "systemic_rescue_requires_study_drug_discontinuation": bool | null,
      "resume_after_systemic_rescue_half_lives": 5 | null,
      "resume_after_phototherapy_months": 1 | null,
      "rescued_counted_as_nonresponder": bool | null,
      "rescued_counted_as_treatment_failure": bool | null,
      "continue_visits_after_discontinuation": bool | null,
      "continue_visits_through_week": 16 | null,
      "topical_rescue_not_counted_after_week": 16 | 52 | null,
      "topical_agents": [{"name", "strength_pct", "form", "potency"}],
      "topical_potency_classes": [{"system": "EU", "comparator": ">", "class": 3}],
      "tci_reserved_areas": ["face", "neck", "intertriginous", "genital"],
      "systemic_agents": [...],
      "oral_corticosteroid_limit": {"agents", "max_mg_per_kg", "max_consecutive_weeks"} | null,
      "rescue_period": {"drug", "dose_mg", "frequency", "duration_weeks", "with_topical_standard_of_care"} | null,
      "escape_arm_washout_half_lives": 5 | null,
      "maintenance_period_rule": {"topical_rescue", "systemic_rescue"} | null,
      "permitted_concomitant": [...],
      "recorded_in_ecrf": bool | null,
      "applies_to_period": "initial_treatment" | "induction" | null,
      "long_term_extension_eligible_after_rescue": bool | null,
      "topical_agent_class": "TCS" | null, "rationale": "monotherapy_design" | null
    }
"""
from .criteria import criterion

TRIGGERS = ("investigator_discretion", "protocol_response_threshold", "flare_definition", "prohibited")


def _agent(name, strength_pct, form, potency):
    return {"name": name, "strength_pct": strength_pct, "form": form, "potency": potency}


def _base(**kw):
    v = {
        "permitted": None, "trigger": None, "earliest_week": None, "prohibited_through_week": None,
        "trigger_rules": [], "flare_definition": [], "first_step": None,
        "topical_min_days_before_systemic": None,
        "topical_rescue_requires_study_drug_discontinuation": None,
        "systemic_rescue_requires_study_drug_discontinuation": None,
        "resume_after_systemic_rescue_half_lives": None, "resume_after_phototherapy_months": None,
        "rescued_counted_as_nonresponder": None, "rescued_counted_as_treatment_failure": None,
        "continue_visits_after_discontinuation": None, "continue_visits_through_week": None,
        "topical_rescue_not_counted_after_week": None,
        "topical_agents": [], "topical_potency_classes": [], "tci_reserved_areas": [],
        "systemic_agents": [], "oral_corticosteroid_limit": None, "rescue_period": None,
        "escape_arm_washout_half_lives": None, "maintenance_period_rule": None,
        "permitted_concomitant": [], "recorded_in_ecrf": None, "applies_to_period": None,
        "long_term_extension_eligible_after_rescue": None,
        "topical_agent_class": None, "rationale": None,
    }
    v.update(kw)
    return v


EASI50_LOSS = criterion("EASI", "percent_improvement_from_baseline", "<", 50, "percent")

CHRONOS = _base(
    permitted=True, trigger="investigator_discretion", earliest_week=2, prohibited_through_week=2,
    topical_rescue_requires_study_drug_discontinuation=False,
    systemic_rescue_requires_study_drug_discontinuation=True,
    resume_after_systemic_rescue_half_lives=5, resume_after_phototherapy_months=1,
    rescued_counted_as_treatment_failure=True, continue_visits_after_discontinuation=True,
    topical_agent_class="TCS",
    topical_agents=[_agent("mometasone", 0.1, "ointment", "high"),
                    _agent("betamethasone dipropionate", 0.05, None, "super-high"),
                    _agent("clobetasol propionate", 0.05, None, "super-high")],
    systemic_agents=["systemic immunosuppressant", "systemic corticosteroids", "phototherapy"],
)
SOLO = _base(
    permitted=True, trigger="investigator_discretion", first_step="topical",
    topical_min_days_before_systemic=7,
    topical_rescue_requires_study_drug_discontinuation=False,
    systemic_rescue_requires_study_drug_discontinuation=True,
    resume_after_systemic_rescue_half_lives=5,
    tci_reserved_areas=["face", "neck", "intertriginous", "genital"],
    systemic_agents=["systemic corticosteroids", "cyclosporine", "methotrexate", "mycophenolate mofetil", "azathioprine"],
)
ECZTRA1 = _base(
    permitted=True, trigger="investigator_discretion", first_step="topical",
    topical_min_days_before_systemic=14, applies_to_period="initial_treatment",
    topical_rescue_requires_study_drug_discontinuation=False,
    systemic_rescue_requires_study_drug_discontinuation=True,
    resume_after_systemic_rescue_half_lives=5, rescued_counted_as_nonresponder=True,
    systemic_agents=["systemic corticosteroids", "systemic immunosuppressants"],
)
ECZTRA2 = ECZTRA1
ECZTRA3 = _base(**{**ECZTRA1, "applies_to_period": None, "rescued_counted_as_nonresponder": None, "topical_agent_class": "TCS",
                   "topical_potency_classes": [{"system": "EU", "comparator": ">", "class": 3},
                                               {"system": "US", "comparator": "<", "class": 4}]})
ADUP = _base(
    permitted=True, trigger="protocol_response_threshold", earliest_week=4, first_step="topical",
    trigger_rules=[{"from_week": 4, "to_week": 24, "criterion": EASI50_LOSS, "consecutive_visits": 2},
                   {"from_week": 24, "to_week": None, "criterion": EASI50_LOSS, "consecutive_visits": 1}],
    topical_min_days_before_systemic=7, topical_rescue_not_counted_after_week=52, topical_agent_class="TCS",
    topical_potency_classes=[{"system": "US", "comparator": ">=", "class": "high/super-high"}],
    oral_corticosteroid_limit={"agents": ["prednisone", "prednisolone"], "max_mg_per_kg": 1, "max_consecutive_weeks": 2},
)
MEASURE_UP = _base(
    permitted=True, trigger="protocol_response_threshold", earliest_week=4, first_step="topical",
    trigger_rules=ADUP["trigger_rules"], topical_min_days_before_systemic=7,
    topical_rescue_not_counted_after_week=16,
)
JADE_MONO2 = _base(
    permitted=False, trigger="prohibited", rationale="monotherapy_design",
    permitted_concomitant=["oral antihistamines", "topical non-medicated emollients"],
)
JADE_REGIMEN = _base(
    permitted=True, trigger="flare_definition",
    flare_definition=[criterion("EASI", "percent_of_response_lost", ">=", 50, "percent", assessed_at=["week_12"]),
                      criterion("IGA", "absolute_score", ">=", 2, "score")],
    rescue_period={"drug": "abrocitinib", "dose_mg": 200, "frequency": "once_daily", "duration_weeks": 12,
                   "with_topical_standard_of_care": True},
)
ADVOCATE = _base(
    permitted=True, trigger="investigator_discretion", prohibited_through_week=16,
    applies_to_period="induction",
    systemic_rescue_requires_study_drug_discontinuation=True,
    continue_visits_after_discontinuation=True, continue_visits_through_week=16,
    escape_arm_washout_half_lives=5,
    systemic_agents=["oral corticosteroids", "phototherapy", "cyclosporin"],
    maintenance_period_rule={"topical_rescue": "intermittent_permitted", "systemic_rescue": "case_by_case_with_medical_monitor"},
)
ADHERE = _base(
    permitted=True, trigger="investigator_discretion", topical_agent_class="TCS",
    topical_potency_classes=[{"system": None, "comparator": ">=", "class": "high"}],
    systemic_rescue_requires_study_drug_discontinuation=True,
    continue_visits_after_discontinuation=True, continue_visits_through_week=16,
    systemic_agents=["oral corticosteroids", "phototherapy", "cyclosporin"],
    recorded_in_ecrf=True, long_term_extension_eligible_after_rescue=True,
)

RESCUE_THERAPY = {
    "NCT02260986": CHRONOS,
    "NCT02277743": SOLO,
    "NCT02277769": SOLO,
    "NCT03131648": ECZTRA1,
    "NCT03160885": ECZTRA2,
    "NCT03363854": ECZTRA3,
    "NCT03568318": ADUP,
    "NCT03569293": MEASURE_UP,
    "NCT03575871": JADE_MONO2,
    "NCT03607422": MEASURE_UP,
    "NCT03627767": JADE_REGIMEN,
    "NCT04146363": ADVOCATE,
    "NCT04178967": ADVOCATE,
    "NCT04250337": ADHERE,
}
