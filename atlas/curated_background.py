"""
design.background_therapy -- structured decomposition of the v1
`background_therapy_rule` prose, one entry per trial (NCT id keyed).

Value shape:
    {
      "regimen_type": "monotherapy" | "combination_tcs" | "standardized_background_topical",
      "background_agent_class": "TCS" | null,
      "tcs_regimen": "standardized" | "step_down" | null,
      "step_down_rule": {initial_potency, initial_frequency, max_consecutive_weeks,
                         then_potency, then_frequency, repeat_on_recurrence,
                         stop_on_local_or_systemic_toxicity} | null,
      "recommended_agents": [{"name", "strength_pct", "form", "potency"}],
      "emollient_required": bool | null, "emollient_frequency": "twice_daily" | null,
      "prohibited_concomitant": [...], "permitted_concomitant": [...],
      "applies_to_rerandomized_maintenance": bool | null,
      "sponsor_trial_ids": ["B7451012", "B7451013"],   # internal study ids quoted by the source
      "study_drug_doses_mg": [15, 30],                 # doses named in the source's design statement
      "population_note": str | null                    # e.g. "adolescents and adults"
    }

These are hand-structured from the same quoted excerpts the v1 pass stored
(the prose itself stays in `source_excerpt`); tests/test_migration_lossless.py
proves every number, agent, and scale token in the prose is present here.
"""

REGIMEN_TYPES = ("monotherapy", "combination_tcs", "standardized_background_topical")


def _agent(name, strength_pct, form, potency):
    return {"name": name, "strength_pct": strength_pct, "form": form, "potency": potency}


TRIAMCINOLONE = _agent("triamcinolone acetonide", 0.1, "cream", "medium")
FLUOCINOLONE = _agent("fluocinolone acetonide", 0.025, "ointment", "medium")
HYDROCORTISONE = _agent("hydrocortisone", 1, "cream", "low")


def _base(**kw):
    v = {
        "regimen_type": None,
        "background_agent_class": None,
        "tcs_regimen": None,
        "step_down_rule": None,
        "recommended_agents": [],
        "emollient_required": None,
        "emollient_frequency": None,
        "prohibited_concomitant": [],
        "permitted_concomitant": [],
        "applies_to_rerandomized_maintenance": None,
        "sponsor_trial_ids": [],
        "study_drug_doses_mg": [],
        "population_note": None,
    }
    v.update(kw)
    return v


SOLO_MONO = _base(
    regimen_type="monotherapy",
    prohibited_concomitant=["live attenuated vaccines", "immunomodulating biologics", "investigational drugs",
                            "TCS", "TCI", "systemic corticosteroids", "non-steroidal systemic immunosuppressants"],
    emollient_required=True, emollient_frequency="twice_daily",
    permitted_concomitant=["moisturizers/emollients"],
)
ECZTRA_MONO = _base(
    regimen_type="monotherapy", sponsor_trial_ids=["ECZTRA-1", "ECZTRA-2"],
    population_note="adult subjects with moderate-to-severe AD not adequately controlled with topical prescription therapies or when those therapies are not advisable",
)
JADE_MONO = _base(
    regimen_type="monotherapy", sponsor_trial_ids=["B7451012", "B7451013"],
    population_note="adolescents and adults",
)
JADE_MONO2 = _base(
    regimen_type="monotherapy",
    prohibited_concomitant=["topical corticosteroids", "topical calcineurin inhibitors", "tars", "antibiotic creams",
                            "topical antihistamines", "systemic AD therapies"],
)
MEASURE_UP_MONO = _base(
    regimen_type="monotherapy", sponsor_trial_ids=["M16-045", "M18-891"], study_drug_doses_mg=[15, 30],
    population_note="upadacitinib 15/30 mg monotherapy",
)
ADVOCATE_MONO = _base(regimen_type="monotherapy", sponsor_trial_ids=["KGAB", "KGAC"])

CHRONOS_TCS = _base(
    regimen_type="combination_tcs", background_agent_class="TCS", tcs_regimen="standardized",
    recommended_agents=[TRIAMCINOLONE, FLUOCINOLONE, HYDROCORTISONE],
)
ECZTRA3_TCS = _base(
    regimen_type="combination_tcs", background_agent_class="TCS", tcs_regimen="standardized",
    applies_to_rerandomized_maintenance=True,
)
ADUP_TCS = _base(
    regimen_type="combination_tcs", background_agent_class="TCS", tcs_regimen="step_down",
    step_down_rule={
        "initial_potency": "medium", "initial_frequency": "once_daily",
        "initial_target": "areas with active lesions until clear or almost clear",
        "max_consecutive_weeks": 3, "then_potency": "low", "then_frequency": "once_daily",
        "repeat_on_recurrence": True, "stop_on_local_or_systemic_toxicity": True,
    },
    recommended_agents=[TRIAMCINOLONE, FLUOCINOLONE, HYDROCORTISONE],
)
JADE_COMPARE_TOPICAL = _base(
    regimen_type="standardized_background_topical", background_agent_class="topical",
    tcs_regimen="standardized",
)
ADHERE_TCS = _base(regimen_type="combination_tcs", background_agent_class="TCS")
# PRIME/PRIME2 (prurigo nodularis): CT.gov's own arm data lists moisturizers,
# low-to-medium potency TCS, and topical calcineurin inhibitors as permitted
# concomitant interventions on BOTH the dupilumab and placebo arms (not an
# investigational-arm-only combination regimen) -- a standardized background
# regimen given to all patients regardless of assignment. The CT.gov API
# text (source_excerpt) doesn't carry the protocol's specific potency/dosing
# detail the way the AD trials' protocol PDFs do, so recommended_agents
# stays empty rather than inventing concentrations not in the source.
PRIME_TOPICAL = _base(
    regimen_type="standardized_background_topical", background_agent_class="topical",
    permitted_concomitant=[
        "Moisturizers", "Low to medium potent topical corticosteroids",
        "Topical calcineurin inhibitors",
    ],
)

BACKGROUND_THERAPY = {
    "NCT02260986": CHRONOS_TCS,
    "NCT02277743": SOLO_MONO,
    "NCT02277769": SOLO_MONO,
    "NCT03131648": ECZTRA_MONO,
    "NCT03160885": ECZTRA_MONO,
    "NCT03349060": JADE_MONO,
    "NCT03363854": ECZTRA3_TCS,
    "NCT03568318": ADUP_TCS,
    "NCT03569293": MEASURE_UP_MONO,
    "NCT03575871": JADE_MONO2,
    "NCT03607422": MEASURE_UP_MONO,
    "NCT03720470": JADE_COMPARE_TOPICAL,
    "NCT04146363": ADVOCATE_MONO,
    "NCT04178967": ADVOCATE_MONO,
    "NCT04250337": ADHERE_TCS,
    "NCT04183335": PRIME_TOPICAL,
    "NCT04202679": PRIME_TOPICAL,
}
