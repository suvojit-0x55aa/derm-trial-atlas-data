"""
endpoints.primary_endpoints / endpoints.secondary_endpoints -- one typed
Endpoint object per CT.gov outcome measure, replacing the v1 free-text
`primary_endpoint_measure` string and `secondary_endpoint_measures` list.

    {
      "verbatim": "<CT.gov measure title, unchanged>",   # provenance, not the queryable value
      "rank": "primary" | "secondary",
      "position": 1,                                     # CT.gov order, 1-based
      "measure_type": "responder_rate" | "percent_change_from_baseline" | ...,
      "scale": "EASI" | null,  "scale_component": null,  "scale_variant": null,
      "responder_criteria": [ScoreCriterion],           # AND-combined; responder_rate only
      "baseline_reference": "baseline" | "rescue_baseline" | null,
      "timepoints": [{"value": 16, "unit": "week", "end_value": null}],
      "through": {"value": 52, "unit": "week"} | null,   # "Through Week 52", "up to Week 16"
      "analysis_population": "adolescents" | ... | null,
      "subgroup_criteria": [ScoreCriterion],            # e.g. baseline NRS >= 4, EASI-75 responders at week 16
      "subgroup_labels": ["prior_cyclosporine_use"],     # non-scale subgroups
      "study_period": "double_blind" | "rescue" | "maintenance" | "treatment_period" | null,
      "event_type": "TEAE" | "serious_TEAE" | ... | null, # safety / flare / drug-usage endpoints
      "time_frame": "<CT.gov timeFrame>" | null
    }
"""
import re

from .criteria import criterion, detect_scale, detect_variant, normalize_symbols, num, NUM

MEASURE_TYPES = (
    "responder_rate",
    "percent_change_from_baseline",
    "change_from_baseline",
    "absolute_value",
    "time_to_event",
    "count",
    "loss_of_response",
    "flare_incidence",
    "safety_incidence",
    "immunogenicity",
    "pharmacokinetics",
    "drug_usage",
    "other",
)
POPULATIONS = (
    "main_study", "adolescents", "adults", "pediatrics",
    "full_analysis_set", "per_protocol",
    "prior_cyclosporine_use", "comorbid_asthma", "re_randomized_responders",
    "initially_randomized_to_active",
)
STUDY_PERIODS = ("double_blind", "rescue", "maintenance", "treatment_period")
EVENT_TYPES = (
    "TEAE", "serious_TEAE", "TEAE_leading_to_discontinuation",
    "serious_TEAE_leading_to_discontinuation", "skin_infection_TEAE",
    "skin_infection_TEAE_requiring_systemic_treatment", "AE_or_SAE", "flare",
    "anti_drug_antibodies", "TCS_use", "TCS_free_days", "TCS_TCI_free_days",
    "topical_medication_free_days", "steroid_free_days", "serum_concentration",
    "plasma_concentration",
)

POP_PATTERNS = [
    (r"^Main Study:\s*", "main_study"),
    (r"^Adolescents:\s*", "adolescents"),
    (r"\s*-\s*Adolescents$|\s+for Adolescents\b|\s+in Adolescents\b", "adolescents"),
    (r"\s*-\s*Adults$|\s+for Adults\b|\s+in Adults\b", "adults"),
    (r"\s*-\s*Pediatrics$", "pediatrics"),
    (r":\s*Full Analysis Set(?: \(FAS\))?$", "full_analysis_set"),
    (r":\s*Per Protocol Analysis Set(?: \(PPAS\))?$", "per_protocol"),
    (r"\s+for Participants With Prior CSA Use", "prior_cyclosporine_use"),
    (r"\s+in Participants Who Have Self-[Rr]eported Comorbid Asthma", "comorbid_asthma"),
]
PERIOD_PATTERNS = [
    (r":\s*Double-blind(?: \(DB\))? Period$|During the Double-blind Treatment Period", "double_blind"),
    (r":\s*Rescue Period$", "rescue"),
    (r"in Maintenance Period", "maintenance"),
    (r"Through(?: the)? Treatment Period|During Treatment Period", "treatment_period"),
]
EVENT_PATTERNS = [
    (r"Serious Treatment[- ]Emergent Adverse Events? \(TEAEs?\) Leading to Study Drug Discontinuation", "serious_TEAE_leading_to_discontinuation"),
    (r"Treatment[- ]Emergent Adverse Events? \(TEAEs?\) Leading to Treatment Discontinuation", "TEAE_leading_to_discontinuation"),
    (r"Skin Infection[^()]*TEAEs?[^()]*Requiring Systemic Treatment|Skin Infection Treatment Emergent Adverse Events \(TEAEs\) Requiring Systemic Treatment", "skin_infection_TEAE_requiring_systemic_treatment"),
    (r"Skin Infection", "skin_infection_TEAE"),
    (r"Serious Treatment[- ]Emergent Adverse Event|Treatment Emergent Serious Adverse Events \(TESAEs\)", "serious_TEAE"),
    (r"Treatment[- ]Emergent Adverse Events?", "TEAE"),
    (r"Adverse Event \(AE\) /Serious Adverse Event \(SAE\)", "AE_or_SAE"),
    (r"Anti-drug Antibodies", "anti_drug_antibodies"),
    (r"TCS/TCI-free|Topical Corticosteroid \(TCS\)/Topical Calcineurin Inhibitors \(TCI\) Free Days", "TCS_TCI_free_days"),
    (r"Steroid-free Days", "steroid_free_days"),
    (r"Topical Atopic Dermatitis Medication-Free Days|Days Without Topical Treatment Use", "topical_medication_free_days"),
    (r"Amount of Topical Corticosteroid|Weekly Dose of Topical Corticosteroid", "TCS_use"),
    (r"Serum Concentration", "serum_concentration"),
    (r"Plasma Concentration", "plasma_concentration"),
    (r"\bFlares?\b", "flare"),
]

TIME_FRAME = re.compile(r"\s*\(Time frame: (.*)\)\s*$")
TP_GROUP = re.compile(r"\b(?:Rescue )?(Weeks?|Days?)\s+((?:\d+(?:-\d+)?)(?:\s*,\s*\d+(?:-\d+)?)*(?:,?\s*(?:and|&)\s*\d+(?:-\d+)?)?)")
THROUGH = re.compile(r"(?:Through|up to|Up to|Until)\s+(?:Rescue )?(Week|Day)\s+(\d+)")
RANGE_WEEKS = re.compile(r"(Week|Day) (\d+) to (Week|Day) (\d+)")
NRS_VALUE_PATTERNS = [
    # (regex, metric, unit) -- value group is the number
    (r"(EASI|SCORAD)[- ](\d{2,3})\b(?! Points)", "percent_improvement_from_baseline", "percent"),
    (r"(EASI|SCORAD) (\d{2,3}) Response", "percent_improvement_from_baseline", "percent"),
    (r"(?:>=|=)?\s*(\d{2,3})% (?:Reduction|Improvement)", "percent_improvement_from_baseline", "percent"),
    (r">=\s*(\d{2,3})% Improvement", "percent_improvement_from_baseline", "percent"),
    (r"(?:>=|=)\s*(\d{2,3})%", "percent_improvement_from_baseline", "percent"),
    (r">=\s*(\d+(?:\.\d+)?)[ -][Pp]oints? (?:Improvement|Reduction)", "point_reduction_from_baseline", "points"),
    (r"(?:Reduction|Improvement) (?:of )?(?:\(Reduction )?>=\s*(\d+(?:\.\d+)?)(?:[ -][Pp]oints?)?", "point_reduction_from_baseline", "points"),
    (r"(?:Reduction|Improvement) (?:From Baseline )?(?:in [^,]*? )?of >=\s*(\d+(?:\.\d+)?)", "point_reduction_from_baseline", "points"),
    (r"Reduction of [^,]*?>=\s*(\d+) From Baseline", "point_reduction_from_baseline", "points"),
    (r">=\s*(\d+(?:\.\d+)?)\s*[Pp]oints?", "point_reduction_from_baseline", "points"),
]


def _strip(pattern, text):
    m = re.search(pattern, text)
    return (text[:m.start()] + text[m.end():]).strip() if m else text


def _timepoints(text):
    """Extract every numbered timepoint ('at Week 16', 'Weeks 2, 4 and 8', 'Day 2-15')."""
    tps, through = [], None
    tm = THROUGH.search(text)
    if tm:
        through = {"value": int(tm.group(2)), "unit": tm.group(1).lower()}
        text = text[:tm.start()] + text[tm.end():]
    rm = RANGE_WEEKS.search(text)
    if rm:  # "Week 1 to Week 16": the measure runs from a to b
        tps.append({"value": int(rm.group(2)), "unit": rm.group(1).lower(), "end_value": int(rm.group(4))})
        text = text[:rm.start()] + text[rm.end():]
    for m in TP_GROUP.finditer(text):
        unit = "week" if m.group(1).lower().startswith("week") else "day"
        for item in re.split(r"\s*,\s*(?:and\s+)?|\s+and\s+|\s*&\s*|\s+", m.group(2)):
            item = item.strip().strip(",")
            if not item:
                continue
            if "-" in item:
                a, b = item.split("-")
                tps.append({"value": int(a), "unit": unit, "end_value": int(b)})
            else:
                tps.append({"value": int(item), "unit": unit, "end_value": None})
    return tps, through


def _measure_type(t):
    if re.search(r"^Time to|^Time From Baseline to First|^Median Time", t):
        return "time_to_event"
    if "Loss of Response" in t:
        return "loss_of_response"
    if re.search(r"Experiencing a Flare", t):
        return "flare_incidence"
    if re.search(r"^Number of|^Least Square Mean of Number", t):
        return "count"
    if re.search(r"Pharmacokinetics|Plasma Concentration|Serum Concentration", t):
        return "pharmacokinetics"
    if "Anti-drug Antibodies" in t:
        return "immunogenicity"
    if re.search(r"Adverse Event|TEAE|TESAE|Safety and Tolerability", t):
        return "safety_incidence"
    if re.search(r"Amount of Topical|Steroid-free|TCS/TCI|Medication-Free Days|Days Without Topical|Weekly Dose of Topical|Free Days", t):
        return "drug_usage"
    if re.search(r"^Percent(?:age)? Change", t):
        return "percent_change_from_baseline"
    if re.search(r"^Change (?:From Baseline|in)", t):
        return "change_from_baseline"
    if re.search(r"^(?:Percentage of |Proportion of )?(?:Participants|Subjects)|^Reduction (?:of|From Baseline)", t):
        return "responder_rate"
    if re.search(r" at (?:Rescue )?Weeks? \d", t):
        return "absolute_value"
    return "other"


def _population(t):
    pop = None
    for pattern, label in POP_PATTERNS:
        if re.search(pattern, t):
            pop = pop or label
            t = _strip(pattern, t)
    return pop, t


def _period(t):
    per = None
    for pattern, label in PERIOD_PATTERNS:
        if re.search(pattern, t):
            per = label
            t = _strip(pattern, t)
    return per, t


def _event_type(t):
    for pattern, label in EVENT_PATTERNS:
        if re.search(pattern, t):
            return label
    return None


def _iga_criteria(seg, scale):
    """IGA-style categorical response ('0 or 1', 'Clear (0) or Almost Clear (1)', '2 or Higher')."""
    crit = []
    if re.search(r"(?:\"0\" or \"1\"|0 or 1|0/1|0 \(Clear\) or 1 \(Almost Clear\)|'?Clear'? \(0\)'? or '?Almost Clear'? ?\(1\)'?|'Clear' or 'Almost Clear')", seg):
        crit.append(criterion(scale, "absolute_score", "in", [0, 1], "score"))
    elif re.search(r"Clear \(0\)(?! or)", seg):
        crit.append(criterion(scale, "absolute_score", "in", [0], "score"))
    elif re.search(r"Score of (\d) or Higher", seg):
        crit.append(criterion(scale, "absolute_score", ">=", int(re.search(r"Score of (\d) or Higher", seg).group(1)), "score"))
    m = re.search(r"(?:Reduction|Improvement)(?: From Baseline)? of >=\s*(\d)(?:[ -][Pp]oints?)?|>=\s*(\d)[ -][Pp]oints? (?:Improvement|Reduction)|>=\s*(\d)-point Improvement|Reduction >=\s*(\d)[ -]?[Pp]oints?", seg)
    if m:
        pts = int(next(g for g in m.groups() if g))
        crit.append(criterion(scale, "point_reduction_from_baseline", ">=", pts, "points"))
    return crit


def _threshold_criteria(seg, scale, component, variant, force_reduction=False):
    """Generic responder thresholds on a continuous scale."""
    crit = []
    # absolute-score thresholds: "Score of < 8", "<11 Points", "< 5%", "DLQI Score of 0 or 1", "<2 CDLQI Score"
    m = re.search(r"(?:Score(?:s)? of |Achieving |\(From EASI\) |Area )?(<|<=|>=|>)\s*(\d+(?:\.\d+)?)\s*(%|[Pp]oints)?", seg)
    is_reduction = force_reduction or bool(m) and (
        re.search(r"Reduction|Improvement", seg[:m.start()])
        or re.search(r"^\s*(?:-?\s*[Pp]oints?)?\s*(?:Improvement|Reduction)", seg[m.end():m.end() + 30])
    )
    if m and not is_reduction:
        unit = "percent" if m.group(3) == "%" else "score"
        metric = "percent_bsa" if scale == "BSA" else "absolute_score"
        crit.append(criterion(scale, metric, m.group(1), num(m.group(2)), unit, component=component, variant=variant))
    if re.search(r"Score of 0 or 1", seg) and scale not in ("IGA", "vIGA-AD", "PtGA"):
        crit.append(criterion(scale, "absolute_score", "in", [0, 1], "score", component=component))
    if not crit:
        for pattern, metric, unit in NRS_VALUE_PATTERNS:
            pm = re.search(pattern, seg)
            if pm:
                value = num(pm.group(pm.lastindex))
                comparator = "==" if metric == "percent_improvement_from_baseline" and re.search(r"(?<![>])=\s*" + str(value) + "%", seg) else ">="
                crit.append(criterion(scale, metric, comparator, value, unit, component=component, variant=variant))
                break
    return crit


def _split_subgroup(t):
    """Separate the responder clause from any subgroup clause."""
    subgroup_labels, subgroups, main = [], [], t
    pats = [
        r"\s+Among (?:Participants|Subjects) (?:With|Who Had Achieved) (.*?)(?: After Initial Randomisation to Tralokinumab)?$",
        r"^Percentage of Participants From Those (?:Re-randomized )?(?:With a (.*?) Re-randomized )?Having Achieved (.*?) at Week (\d+) Who Continue(?:d)? to Exhibit (?:an? |and )?",
        r"^Percentage of Participants With (?:an? )?(.*?)(?: Score)? (?:of )?(>=\s*\d+(?:\.\d+)?(?:[ -][Pp]oints?)?) at Baseline (?:Who Achieve |Achieving )",
        r"^Percentage of Participants With (>=\s*\d+(?:\.\d+)?) Points at Baseline and ",
        r"^Percentage of Participants With Baseline (.*?) Score (>=\s*\d+(?:\.\d+)?) and ",
        r"^Reduction From Baseline to Week \d+ of (.*?) of >=\s*\d+ Points Among (?:Participants|Subjects) With Baseline (\w+) (>=\s*\d+)\.?$",
        r"\(Having Achieved (EASI-75) at Week (\d+)\)",
        r"\(From Those Re-randomized Having Achieved (EASI-75) at Week (\d+)\)",
    ]
    if re.search(r"After Initial Randomisation to Tralokinumab", main):
        subgroup_labels.append("initially_randomized_to_active")
        main = _strip(r"\s+After Initial Randomisation to Tralokinumab", main)
    if re.search(r"Re-randomized", main):
        subgroup_labels.append("re_randomized_responders")
    for p in pats:
        m = re.search(p, main)
        if not m:
            continue
        seg = m.group(0)
        subgroups.extend(_subgroup_criteria(seg, main))
        main = (main[:m.start()] + " " + main[m.end():]).strip() if p.startswith("\\s+Among") or p.startswith("\\(") or "Among" in p else main[m.end():]
        if p.startswith(r"^Reduction From Baseline"):
            main = t[:t.index(" Among")]
        break
    return main, subgroups, subgroup_labels


class _Pair:
    def __init__(self, scale, value):
        self._g = (scale, value)

    def group(self, i):
        return self._g[i - 1]


def _subgroup_criteria(seg, whole):
    crit = []
    for m in list(re.finditer(r"(EASI|SCORAD)[- ]?(\d{2,3})\b", seg)) + list(re.finditer(r">=\s*(?P<v>\d{2,3})% Reduction in (?P<s>EASI|SCORAD)", seg)):
        if "v" in m.groupdict() and m.group("v"):
            m = _Pair(m.group("s"), m.group("v"))
        wk = re.search(r"at Week (\d+)", seg)
        crit.append(criterion(m.group(1), "percent_improvement_from_baseline", ">=", int(m.group(2)), "percent",
                              assessed_at=[f"week_{wk.group(1)}"] if wk else None))
    if re.search(r"IGA (?:of 0/1|0 or 1|Score of 0 or 1)", seg):
        wk = re.search(r"at Week (\d+)", seg)
        crit.append(criterion("IGA", "absolute_score", "in", [0, 1], "score", assessed_at=[f"week_{wk.group(1)}"] if wk else None))
        pm = re.search(r">=\s*(\d)-point Improvement", seg)
        if pm:
            crit.append(criterion("IGA", "point_reduction_from_baseline", ">=", int(pm.group(1)), "points", assessed_at=[f"week_{wk.group(1)}"] if wk else None))
    if re.search(r"Achieved >=\s*(\d)-point Reduction", seg):
        pm = re.search(r"Achieved >=\s*(\d)-point Reduction", seg)
        wk = re.search(r"at Week (\d+)", seg)
        crit.append(criterion("Pruritus NRS", "point_reduction_from_baseline", ">=", int(pm.group(1)), "points", assessed_at=[f"week_{wk.group(1)}"] if wk else None))
    pre = re.split(r"Re-randomized|Having Achieved", seg)[0]
    bm = re.search(r"(?:With (?:an? )?|Baseline )?([A-Za-z' ()-]*?)(?:Score|Total Score|Index Score|Subscale)?\s*(?:of )?(>=|<|>)\s*(\d+(?:\.\d+)?)(?:[ -][Pp]oints?)? at Baseline|Baseline ([A-Za-z' ()-]*?) Score (>=|<)\s*(\d+(?:\.\d+)?)|Baseline (\w+) (>=)\s*(\d+)", pre)
    if bm:
        g = bm.groups()
        if g[0] is not None or g[1] is not None:
            label, comp, val = g[0], g[1], g[2]
        elif g[3] is not None:
            label, comp, val = g[3], g[4], g[5]
        else:
            label, comp, val = g[6], g[7], g[8]
        scale, comp_name = detect_scale(label or "")
        if scale is None:
            scale, comp_name = detect_scale(whole)
        crit.append(criterion(scale, "absolute_score", comp, num(val), "score", component=comp_name,
                              variant=detect_variant(whole) if scale == "Pruritus NRS" else None,
                              assessed_at=["baseline"]))
    return crit


def parse_endpoint(title: str, rank: str, position: int, time_frame=None) -> dict:
    t = normalize_symbols(title)
    if time_frame is None:
        tm = TIME_FRAME.search(t)
        if tm:
            time_frame = tm.group(1)
            t = t[:tm.start()].strip()
    t = t.rstrip(".").strip()
    pop, t = _population(t)
    period, t = _period(t)
    main, subgroup, subgroup_labels = _split_subgroup(t)
    if "re_randomized_responders" in subgroup_labels and pop is None:
        pop = "re_randomized_responders"
    mtype = _measure_type(t if t.startswith("Percentage of Participants") else main)
    scale, component = detect_scale(main)
    if scale is None:
        scale, component = detect_scale(t)
    variant = detect_variant(main if detect_scale(main)[0] else t) if scale == "Pruritus NRS" else None
    tps, through = _timepoints(t)
    if not tps and through is None and time_frame:
        tps, through = _timepoints(normalize_symbols(time_frame))
    baseline_ref = "rescue_baseline" if "Rescue Baseline" in t else ("baseline" if "Baseline" in t else None)
    event_type = _event_type(t)
    responder = []
    if mtype in ("responder_rate", "loss_of_response", "time_to_event"):
        if re.search(r"HADS-A\)? Score and .*?HADS-D\)? Score of < 8", main):
            responder = [criterion("HADS", "absolute_score", "<", 8, "score", component="Anxiety"),
                         criterion("HADS", "absolute_score", "<", 8, "score", component="Depression")]
        elif scale in ("IGA", "vIGA-AD", "PtGA"):
            responder = _iga_criteria(main, scale)
        elif scale is not None:
            responder = _threshold_criteria(main, scale, component, variant,
                                            force_reduction=bool(re.search(r"Who Achieve a >=|at Baseline Achieving >=", t)))
    return {
        "verbatim": title,
        "rank": rank,
        "position": position,
        "measure_type": mtype,
        "scale": scale,
        "scale_component": component,
        "scale_variant": variant,
        "responder_criteria": responder,
        "baseline_reference": baseline_ref,
        "timepoints": tps,
        "through": through,
        "analysis_population": pop,
        "subgroup_criteria": subgroup,
        "subgroup_labels": subgroup_labels,
        "study_period": period,
        "event_type": event_type,
        "time_frame": time_frame,
    }
