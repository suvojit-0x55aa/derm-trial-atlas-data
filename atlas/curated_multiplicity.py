"""
endpoints.multiplicity_control -- structured decomposition of the v1
`endpoint_hierarchy_multiplicity` prose, one entry per trial.

Value shape:
    {
      "procedure": "serial_gatekeeping" | "graphical" | "sequential_bonferroni" |
                   "closed_testing_bonferroni" | "gatekeeping_with_holm",
      "familywise_error_controlled": true,
      "alpha": 0.05, "alpha_sided": 2, "alpha_per_dose": 0.025 | null,
      "co_primary_endpoints": [EndpointRef],
      "testing_sequence": [EndpointRef],          # ordered; each has step + alpha where stated
      "alpha_split": [{"group", "alpha", "method", "timepoint_week"}],
      "alpha_recycling": bool | null,
      "doses_compared": ["100 mg", "200 mg"],
      "dose_comparison_order": ["200 mg vs placebo", ...],
      "branching_on": EndpointRef | null,          # JADE MONO: Week-2 NRS-4 result at 2.5%
      "regulatory_variants": ["US", "EU"],
      "rescue_counted_as_nonresponder": bool | null,
      "active_comparator_excluded_from_hierarchy": "dupilumab" | null,
      "background_tcs": bool | null,
      "method_citations": ["Bretz 2009", "Bretz 2011"],
      "finalized_in_sap": bool | null,
      "same_design_as": ["NCT03349060"] | [],
      "further_endpoints_through_week": 56 | null
    }

EndpointRef = {"label", "scale", "responder_criteria": [ScoreCriterion],
               "timepoint_week", "alpha", "step"}
"""
from .criteria import criterion

PROCEDURES = ("serial_gatekeeping", "graphical", "sequential_bonferroni",
              "closed_testing_bonferroni", "gatekeeping_with_holm")

IGA01 = [criterion("IGA", "absolute_score", "in", [0, 1], "score")]
IGA01_2PT = IGA01 + [criterion("IGA", "point_reduction_from_baseline", ">=", 2, "points")]
EASI75 = [criterion("EASI", "percent_improvement_from_baseline", ">=", 75, "percent")]
EASI90 = [criterion("EASI", "percent_improvement_from_baseline", ">=", 90, "percent")]
NRS4 = [criterion("Pruritus NRS", "point_reduction_from_baseline", ">=", 4, "points")]
NRS3 = [criterion("Pruritus NRS", "point_reduction_from_baseline", ">=", 3, "points")]


def ref(label, scale, crit, week=None, alpha=None, step=None):
    return {"label": label, "scale": scale, "responder_criteria": crit,
            "timepoint_week": week, "alpha": alpha, "step": step}


def _base(**kw):
    v = {
        "procedure": None, "familywise_error_controlled": True,
        "alpha": None, "alpha_sided": 2, "alpha_per_dose": None,
        "co_primary_endpoints": [], "testing_sequence": [],
        "alpha_split": [], "alpha_recycling": None,
        "doses_compared": [], "dose_comparison_order": [],
        "branching_on": None, "regulatory_variants": [],
        "rescue_counted_as_nonresponder": None,
        "active_comparator_excluded_from_hierarchy": None,
        "background_tcs": None, "method_citations": [],
        "finalized_in_sap": None, "same_design_as": [],
        "further_endpoints_through_week": None,
    }
    v.update(kw)
    return v


CHRONOS = _base(
    procedure="serial_gatekeeping", alpha=0.05, alpha_per_dose=0.025,
    co_primary_endpoints=[ref("IGA 0/1 + >=2-point reduction", "IGA", IGA01_2PT, 16)],
    testing_sequence=[
        ref("EASI-75", "EASI", EASI75, 16, step=1),
        ref("Pruritus NRS >=4-point improvement", "Pruritus NRS", NRS4, 16, step=2),
        ref("Pruritus NRS >=3-point improvement", "Pruritus NRS", NRS3, 16, step=3),
        ref("IGA 0/1 + >=2-point reduction", "IGA", IGA01_2PT, 52, step=4),
        ref("EASI-75", "EASI", EASI75, 52, step=5),
        ref("Percent change in weekly average peak pruritus NRS", "Pruritus NRS", [], 16, step=6),
        ref("Pruritus NRS >=4-point improvement", "Pruritus NRS", NRS4, 52, step=7),
        ref("Pruritus NRS >=3-point improvement", "Pruritus NRS", NRS3, 52, step=8),
    ],
    further_endpoints_through_week=56,
)
SOLO = _base(
    procedure="serial_gatekeeping", alpha=0.05, alpha_per_dose=0.025,
    co_primary_endpoints=[ref("IGA 0/1 + >=2-point reduction", "IGA", IGA01_2PT, 16),
                          ref("EASI-75", "EASI", EASI75, 16)],
    rescue_counted_as_nonresponder=True,
)
ECZTRA1 = _base(
    procedure="gatekeeping_with_holm", alpha=0.05, regulatory_variants=["US"],
    testing_sequence=[
        ref("IGA 0/1", "IGA", IGA01, 16, alpha=0.05, step=1),
        ref("EASI-75", "EASI", EASI75, 16, alpha=0.05, step=2),
        ref("Pruritus NRS >=4-point improvement", "Pruritus NRS", NRS4, 16, alpha=0.05, step=3),
    ],
    alpha_split=[
        {"group": "week16_secondary", "n_endpoints": 2, "alpha": 0.01, "method": "holm", "timepoint_week": 16},
        {"group": "maintenance", "n_endpoints": None, "alpha": 0.04, "method": "sequential", "timepoint_week": 52},
    ],
    alpha_recycling=True,
)
ECZTRA2 = _base(
    procedure="gatekeeping_with_holm", alpha=0.05, regulatory_variants=["US"], same_design_as=["NCT03131648"],
    testing_sequence=ECZTRA1["testing_sequence"],
    alpha_split=[
        {"group": "week16_secondary", "n_endpoints": 2, "alpha": 0.01, "method": "holm", "timepoint_week": 16},
        {"group": "maintenance", "n_endpoints": 2, "alpha": 0.04, "method": "sequential", "timepoint_week": 52},
    ],
    alpha_recycling=True,
)
ECZTRA3 = _base(
    procedure="gatekeeping_with_holm", regulatory_variants=["US"], same_design_as=["NCT03131648", "NCT03160885"],
    background_tcs=True,
    testing_sequence=[
        ref("IGA 0/1", "IGA", IGA01, 16, step=1),
        ref("EASI-75", "EASI", EASI75, 16, step=2),
        ref("Pruritus NRS >=4-point improvement", "Pruritus NRS", NRS4, 16, step=3),
    ],
    alpha_split=[{"group": "maintenance", "n_endpoints": None, "alpha": None, "method": "separate_branch", "timepoint_week": None}],
)
JADE_MONO1 = _base(
    procedure="sequential_bonferroni", alpha=0.05,
    doses_compared=["100 mg", "200 mg"], dose_comparison_order=["200 mg vs placebo"],
    co_primary_endpoints=[ref("IGA 0/1 + >=2-point reduction", "IGA", IGA01_2PT, 12, alpha=0.05),
                          ref("EASI-75", "EASI", EASI75, 12, alpha=0.05)],
    branching_on=ref("Pruritus NRS >=4-point improvement", "Pruritus NRS", NRS4, 2, alpha=0.025),
)
JADE_MONO2 = _base(**{**JADE_MONO1, "same_design_as": ["NCT03349060"]})
JADE_REGIMEN = _base(
    procedure="serial_gatekeeping", alpha=0.05, doses_compared=["100 mg", "200 mg"],
    dose_comparison_order=["200 mg vs placebo", "100 mg vs placebo", "200 mg vs 100 mg"],
    testing_sequence=[
        ref("primary endpoint, 200 mg vs placebo", None, [], None, step=1),
        ref("key secondary endpoint, 200 mg vs placebo", None, [], None, step=2),
        ref("primary endpoint, 100 mg vs placebo", None, [], None, step=3),
        ref("key secondary endpoint, 100 mg vs placebo", None, [], None, step=4),
        ref("primary endpoint, 200 mg vs 100 mg", None, [], None, step=5),
        ref("key secondary endpoint, 200 mg vs 100 mg", None, [], None, step=6),
    ],
)
JADE_COMPARE = _base(
    procedure="closed_testing_bonferroni", alpha=0.05, doses_compared=["100 mg", "200 mg"],
    active_comparator_excluded_from_hierarchy="dupilumab",
)
MEASURE_UP1 = _base(
    procedure="graphical", alpha=0.05, doses_compared=["15 mg", "30 mg"],
    regulatory_variants=["EU", "US"], alpha_recycling=True,
)
MEASURE_UP2 = _base(**{**MEASURE_UP1, "same_design_as": ["NCT03569293"]})
ADUP = _base(**{**MEASURE_UP1, "background_tcs": True})
ADVOCATE1 = _base(
    procedure="graphical", alpha=0.05, regulatory_variants=["US", "EU"],
    method_citations=["Bretz 2011"], finalized_in_sap=True,
    testing_sequence=[ref("IGA 0/1", "IGA", IGA01, 16, step=1)],
    co_primary_endpoints=[ref("IGA 0/1", "IGA", IGA01, 16), ref("EASI-75", "EASI", EASI75, 16)],
)
ADVOCATE2 = _base(
    procedure="graphical", regulatory_variants=["US"], method_citations=["Bretz 2009", "Bretz 2011"],
    testing_sequence=[
        ref("IGA 0/1", "IGA", IGA01, 16, step=1),
        ref("EASI-75", "EASI", EASI75, 16, step=2),
        ref("EASI-90", "EASI", EASI90, 16, step=3),
        ref("Pruritus NRS >=4-point improvement", "Pruritus NRS", NRS4, 16, step=4),
        ref("Pruritus NRS >=4-point improvement", "Pruritus NRS", NRS4, 4, step=5),
        ref("Pruritus NRS >=4-point improvement", "Pruritus NRS", NRS4, 2, step=6),
        ref("IGA 0/1", "IGA", IGA01, 4, step=7),
        ref("IGA 0/1 in adults", "IGA", IGA01, 16, step=8),
        ref("Sleep-loss", "Sleep-loss", [], 16, step=9),
    ],
)
ADHERE = _base(
    procedure="graphical", alpha=0.05, regulatory_variants=["US"], method_citations=["Bretz 2009", "Bretz 2011"],
    testing_sequence=[
        ref("IGA 0/1", "IGA", IGA01, 16, step=1),
        ref("EASI-75", "EASI", EASI75, 16, step=2),
        ref("Pruritus NRS >=4-point improvement", "Pruritus NRS", NRS4, 16, step=3),
        ref("EASI-75 and Pruritus NRS >=4-point improvement", "EASI", EASI75 + NRS4, 16, step=4),
        ref("EASI-90", "EASI", EASI90, 16, step=5),
    ],
)

MULTIPLICITY_CONTROL = {
    "NCT02260986": CHRONOS,
    "NCT02277743": SOLO,
    "NCT02277769": SOLO,
    "NCT03131648": ECZTRA1,
    "NCT03160885": ECZTRA2,
    "NCT03349060": JADE_MONO1,
    "NCT03363854": ECZTRA3,
    "NCT03568318": ADUP,
    "NCT03569293": MEASURE_UP1,
    "NCT03575871": JADE_MONO2,
    "NCT03607422": MEASURE_UP2,
    "NCT03627767": JADE_REGIMEN,
    "NCT03720470": JADE_COMPARE,
    "NCT04146363": ADVOCATE1,
    "NCT04178967": ADVOCATE2,
    "NCT04250337": ADHERE,
}
