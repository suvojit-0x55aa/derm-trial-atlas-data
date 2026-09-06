"""
results.{arms,arm_results,effect_estimates} -- normalized CT.gov results
(schema v3), built from the same `resultsSection` payload
scripts/fetch_adverse_events.py already parses for adverse_events.*.

This module's job is normalization, not fresh sourcing: CT.gov's raw
results are structured but treacherous (see the design report,
data/derm-trial-atlas-results-schema/report.md in the firstmate repo, S2.4):

  * p-values are inequality bounds ("< 0.0001") 61% of the time -- never
    coerce a bound into a bare float (parse_pvalue).
  * analyses[].paramType is free text: 62 raw spellings for 8 real
    statistics (canonicalize_effect_type).
  * a measurement row's value can be a raw count or a percentage with no
    reliable signal in the unit string (4 inconsistent casings exist) --
    only the outcome measure's own top-level `paramType` disambiguates
    (value_type_of / derive_response_rate).

Every function here is pure (dict in, dict/None out) so the backfill script
and tests can exercise them directly against cached CT.gov payloads.
"""
import hashlib
import re
from collections import Counter

VALUE_TYPE_MAP = {
    "NUMBER": "number",
    "COUNT_OF_PARTICIPANTS": "count_of_participants",
    "MEAN": "mean",
    "LEAST_SQUARES_MEAN": "least_squares_mean",
    "MEDIAN": "median",
    "GEOMETRIC_MEAN": "geometric_mean",
}

# CT.gov's outcome-measure-level dispersionType is free text too, but a much
# smaller, already-near-canonical vocabulary (8 raw strings seen in the live
# corpus). "N% Confidence Interval" carries its own percentage -- parsed
# separately by ci_pct_of, not hardcoded per width.
DISPERSION_TYPE_MAP = {
    "Standard Deviation": "standard_deviation",
    "Standard Error": "standard_error",
    "Inter-Quartile Range": "inter_quartile_range",
    "Full Range": "full_range",
    "Geometric Coefficient of Variation": "geometric_cv",
}
CI_DISPERSION_RE = re.compile(r"^\s*([\d.]+)\s*%\s*Confidence Interval\s*$", re.I)


def dispersion_type_of(raw):
    if not raw:
        return None
    if CI_DISPERSION_RE.match(raw):
        return "confidence_interval"
    return DISPERSION_TYPE_MAP.get(raw)


def ci_pct_of(raw):
    m = CI_DISPERSION_RE.match(raw) if raw else None
    return float(m.group(1)) if m else None

# measure_types that are safety/operational, not efficacy. They are already
# covered by the atlas's separate adverse_events.* field group (built from
# the same resultsSection by scripts/fetch_adverse_events.py), and their
# CT.gov classes[] grain is per-MedDRA-term / per-lab-parameter, not
# per-timepoint like every efficacy measure here -- treating them through
# this generic per-timepoint extractor would misrepresent the row grain.
# Real, checked scope decision (results-layer phase 3), not an oversight.
EXCLUDED_MEASURE_TYPES = {"safety_incidence", "immunogenicity", "pharmacokinetics", "drug_usage"}

# 62 raw analyses[].paramType spellings -> 8 canonical types (verified against
# the live corpus: this covers 2489/2492, 99.88%, matching the design report's
# measured 99.8%). Order matters -- more specific statistics are checked before
# the generic "percentage"/"difference" catch-alls.
EFFECT_TYPE_RULES = [
    (re.compile(r"hazard ratio", re.I), "hazard_ratio"),
    (re.compile(r"odds ratio", re.I), "odds_ratio"),
    (re.compile(r"\brisk ratio\b|\brate ratio\b", re.I), "risk_ratio"),
    (re.compile(r"risk difference", re.I), "risk_difference"),
    (re.compile(r"least square|\bls[- ]?mean|\blsm\b|lsmean", re.I), "ls_mean_difference"),
    (re.compile(r"median difference", re.I), "median_difference"),
    (re.compile(r"responder rate|response rate|proportion of responders|percentage|percent\b|%", re.I),
     "response_rate_difference"),
    (re.compile(r"mean difference|treatment difference|treatment rate difference|\bdifference\b|estimate of difference", re.I),
     "mean_difference"),
]

PVALUE_RE = re.compile(r"^\s*([<>]=?|=)?\s*([\d.]+)\s*$")

NONINFERIORITY_MAP = {
    "SUPERIORITY": "superiority", "SUPERIORITY_OR_OTHER_LEGACY": "superiority",
    "SUPERIORITY_OR_OTHER": "superiority",
    "NON_INFERIORITY": "non_inferiority", "NON_INFERIORITY_OR_EQUIVALENCE_LEGACY": "non_inferiority",
    "EQUIVALENCE": "equivalence",
}

TIME_FRAME_SUFFIX = re.compile(r"\s*\(Time frame:.*\)\s*$")
CLASS_TIMEPOINT_RE = re.compile(r"\b(?:Weeks?|Wks?)\.?\s*(\d+)\b", re.I)
CLASS_TIMEPOINT_DAY_RE = re.compile(r"\bDays?\.?\s*(\d+)\b", re.I)


def sha1_of(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def normalize_title(t: str) -> str:
    """Same normalization on both sides of the endpoint<->outcome-measure
    join: strip the '(Time frame: X)' suffix atlas primary endpoints carry
    (from the v1 fetch's measure+timeFrame concatenation), and the unicode
    >=/<= CT.gov's protocolSection and resultsSection don't always agree on
    (one real corpus case: NCT02728752's ">=" vs "≥")."""
    t = TIME_FRAME_SUFFIX.sub("", t)
    t = t.replace("≥", ">=").replace("≤", "<=")
    return t.strip().rstrip(".").strip()


def canonicalize_effect_type(raw):
    if not raw:
        return None
    for pattern, canon in EFFECT_TYPE_RULES:
        if pattern.search(raw):
            return canon
    return None


def parse_pvalue(raw):
    """CT.gov pValue string -> {comparator, value, verbatim}, or None.
    Keeps the comparator: '< 0.0001' is a bound, not the point estimate
    0.0001 -- 61% of this corpus's p-values are bounds (verified: 1711/2574)."""
    if not raw:
        return None
    m = PVALUE_RE.match(raw)
    if not m:
        return None
    comparator = m.group(1) or "="
    return {"comparator": comparator, "value": float(m.group(2)), "verbatim": raw}


def comparison_kind_of(non_inferiority_type):
    return NONINFERIORITY_MAP.get(non_inferiority_type, "other")


def ci_sides_of(ci_num_sides):
    return {"TWO_SIDED": 2, "ONE_SIDED": 1}.get(ci_num_sides)


def classify_arm_role(label: str, drug: str) -> str:
    """Curated, not CT.gov's own armGroups[].type -- NCT02755649 labels its
    placebo arm EXPERIMENTAL (design report S4.3). Check placebo/vehicle
    text first, since that's the one thing CT.gov's arm titles state
    reliably; fall back to matching the trial's own drug name."""
    low = (label or "").lower()
    if "vehicle" in low:
        return "vehicle"
    if "placebo" in low:
        return "placebo"
    if drug and drug.lower() in low:
        return "investigational"
    return "other"


def class_timepoint(class_title, endpoint_timepoints):
    """A class's own title is the timepoint when it parses as one ('Week 16',
    or 'PASI 75 response at Week 12 (n=...)' with an embedded week number);
    otherwise fall back to the endpoint's own single already-parsed timepoint
    (only when unambiguous -- exactly one), else None (honest gap, never
    guessed) -- e.g. an AE-term class title carries no timepoint at all."""
    if class_title:
        m = CLASS_TIMEPOINT_RE.search(class_title)
        if m:
            return {"value": int(m.group(1)), "unit": "week", "end_value": None}
        m = CLASS_TIMEPOINT_DAY_RE.search(class_title)
        if m:
            return {"value": int(m.group(1)), "unit": "day", "end_value": None}
    if endpoint_timepoints and len(endpoint_timepoints) == 1:
        tp = endpoint_timepoints[0]
        return {"value": tp["value"], "unit": tp["unit"], "end_value": tp.get("end_value")}
    return None


def endpoint_key(rank, position, verbatim):
    return {"rank": rank, "position": position, "verbatim_sha1": sha1_of(verbatim)}


# Phase 3's second disambiguator (design report S5.3): the CT.gov outcome-measure's
# own populationDescription free text states the analysis set explicitly (343
# distinct descriptions seen in this corpus, but a small, well-covered vocabulary
# of real phrasing) -- this is what makes an "EASI-75 at week 16" query safe to
# aggregate rather than just correct at the single-endpoint level. A description
# with no recognizable phrasing (e.g. "Severe pruritus population...") stays None
# rather than force-fit to the nearest wrong POPULATIONS enum value.
POPULATION_PATTERNS = [
    (re.compile(r"per.protocol", re.I), "per_protocol"),
    (re.compile(r"\badolescent", re.I), "adolescents"),
    (re.compile(r"\bpediatric", re.I), "pediatrics"),
    (re.compile(r"\badult", re.I), "adults"),
    (re.compile(r"re-?randomi[sz]ed.*responder|responder.*re-?randomi[sz]ed", re.I), "re_randomized_responders"),
    (re.compile(r"full analysis set|\bfas\b|intent.to.treat|\bitt\b|randomi[sz]ed set|all randomi[sz]ed", re.I),
     "full_analysis_set"),
]


AGE_GROUP_LIST_RE = re.compile(r"adults?\s+and\s+adolescents?|adolescents?\s+and\s+adults?", re.I)


def analysis_population_of(description):
    if not description:
        return None
    # A parenthetical like "(adults and adolescents)" describing the FULL
    # population's age composition is not a sub-population scope -- but it
    # contains the bare word "adolescent" (and "adult"), which the patterns
    # above would otherwise match before ever reaching "full analysis set" /
    # "intent-to-treat" later in the same description. Real, found bug: 4
    # records' full-population primary rows (3 Upadacitinib trials +
    # NCT01194219's re-randomization arm; see AGENTS.md) were mislabeled
    # "adolescents" for exactly this reason. Strip the coordinated age-group
    # phrase before matching so the real population type wins; a genuine
    # adolescent-only sub-study description ("population for adolescents",
    # "ITT_A", "adolescent sub-study") never contains this coordinated form
    # and is unaffected.
    text = AGE_GROUP_LIST_RE.sub("", description)
    for pattern, label in POPULATION_PATTERNS:
        if pattern.search(text):
            return label
    return None


def _om_groups(cache):
    """Every outcome measure's own `groups` list, alongside that OM's
    analysis_population -- the unit `_majority_populations` votes over."""
    oms = cache.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    for om in oms:
        pop = analysis_population_of(om.get("populationDescription"))
        yield om, pop


def _majority_populations(cache):
    """(raw CT.gov results-group id, label) -> the population most of that
    (id, label)'s OWN outcome measures agree on. A single OM's own free-text
    populationDescription can read wrong in isolation -- real, found case:
    NCT03568318's EASI-75 OM (whose arm IS the full-population one) happens
    to mention "adolescent" in an aside about how adolescent efficacy is
    reported separately, so analysis_population_of misreads that one OM as
    "adolescents"; 11 of its 12 sibling OMs for the same (id, label) agree
    it is full_analysis_set. Voting across every OM sharing an (id, label)
    is robust to that kind of single-OM misread without having to hand-special-
    case each real phrasing variant analysis_population_of can be fooled by."""
    votes = {}
    order = []
    for om, pop in _om_groups(cache):
        for g in om.get("groups", []):
            key = (g["id"], g["title"])
            if key not in votes:
                votes[key] = []
                order.append(key)
            votes[key].append(pop)
    majority = {}
    for key, pops in votes.items():
        counts = Counter(p for p in pops if p is not None)
        majority[key] = counts.most_common(1)[0][0] if counts else None
    return majority, order


def build_arm_id_map(cache):
    """(raw CT.gov results-group id, label) -> the id actually written to
    results.arms / arm_results / effect_estimates.

    Real, load-bearing finding: OG### ids are NOT stable trial-wide -- they
    are only unique WITHIN one outcome measure. 51 of 125 trials in this
    corpus reuse an id (e.g. OG001) for a genuinely different arm in a
    different measure, almost always a re-randomization/maintenance-period
    design (ECZTRA 1's own OG001 is 'Placebo Q2W' in its initial-period
    measures and 'Tralokinumab 300 mg Q4W' in its maintenance-period ones),
    and sometimes a main-study-vs-sub-population design (NCT03568318's own
    OG000 is 'Placebo + TCS' in its main-study measures and 'Adolescents:
    Placebo + TCS' in its adolescent-substudy ones). Keying `results.arms`/
    `arm_results`/`effect_estimates` by the raw id alone silently collapses
    two different arms into one.

    An id that labels more than one real arm gets a distinguishing suffix
    per distinct label, first-seen order: `{raw_id}#{population}` using
    that (id, label)'s majority-vote population (see `_majority_populations`)
    when it disambiguates the label from every other label already seen
    under this id (the common case -- a sub-population design); otherwise
    `{raw_id}#2`, `{raw_id}#3`, ... (a same-population relabeling, e.g. a
    crossover arm renamed after re-randomization, where no field in this
    schema states the real distinguisher -- a numbered id still keeps both
    labels distinct without inventing one). An id that labels only one arm
    trial-wide is left exactly as CT.gov wrote it -- no needless churn on
    the other 74 (of 125) trials with no collision."""
    majority, order = _majority_populations(cache)
    labels_by_id = {}
    for raw_id, label in order:
        labels_by_id.setdefault(raw_id, [])
        if label not in labels_by_id[raw_id]:
            labels_by_id[raw_id].append(label)

    id_map = {}
    for raw_id, labels in labels_by_id.items():
        if len(labels) == 1:
            id_map[(raw_id, labels[0])] = raw_id
            continue
        used = set()
        for label in labels:
            pop = majority[(raw_id, label)]
            candidate = f"{raw_id}#{pop}" if pop else None
            if candidate is None or candidate in used:
                idx = 2
                candidate = f"{raw_id}#{idx}"
                while candidate in used:
                    idx += 1
                    candidate = f"{raw_id}#{idx}"
            used.add(candidate)
            id_map[(raw_id, label)] = candidate
    return id_map


def build_arm_registry(record, cache):
    """One row per distinct (resolved arm id, label) pair, unioned across
    every outcome measure -- see `build_arm_id_map` for how a raw CT.gov id
    that labels more than one real arm gets a distinguishing id so both
    labels survive instead of colliding under one id.

    randomized_n is joined from participantFlowModule by title-substring
    match (its groups use a separate FG### id namespace with a different,
    longer title, e.g. 'Initial Treatment Period - Tralokinumab 300 mg
    Q2W' vs the OM's own 'Tralokinumab 300 mg Q2W') -- left null when no
    clean match exists rather than guessed."""
    drug = record["molecule"]["drug"]["value"]
    id_map = build_arm_id_map(cache)
    majority, order = _majority_populations(cache)
    id_to_label = {}
    for raw_id, label in order:
        id_to_label.setdefault(raw_id, [])
        if label not in id_to_label[raw_id]:
            id_to_label[raw_id].append(label)

    started = {}
    pf = cache.get("resultsSection", {}).get("participantFlowModule", {})
    for period in pf.get("periods", []) or []:
        for milestone in period.get("milestones", []) or []:
            if milestone.get("type") != "STARTED":
                continue
            for a in milestone.get("achievements", []) or []:
                fg_id = a.get("groupId")
                fg_title = next((g["title"] for g in pf.get("groups", []) if g["id"] == fg_id), None)
                if fg_title:
                    started[fg_title] = a.get("numSubjects")
        break  # only the first (overall) period carries the trial-wide randomized N

    arms = []
    for raw_id, labels in id_to_label.items():
        for label in labels:
            resolved_id = id_map[(raw_id, label)]
            pop = majority[(raw_id, label)]
            randomized_n = None
            for fg_title, n in started.items():
                if label and (label in fg_title or fg_title in label):
                    try:
                        candidate = int(n)
                    except (TypeError, ValueError):
                        continue
                    # A period-scoped STARTED milestone reports 0 for any arm label
                    # that only exists in a LATER period (e.g. a maintenance-only
                    # re-randomization arm like ECZTRA 1's "Tralokinumab 300 mg
                    # Q4W") -- that 0 means "not part of period 1", not "randomized_n
                    # is really zero". Keep looking for a real, nonzero match instead
                    # of accepting a misleading false zero.
                    if candidate > 0:
                        randomized_n = candidate
                        break
            arms.append({
                "arm_id": resolved_id, "label": label, "role": classify_arm_role(label, drug),
                "analysis_population": pop,
                "intervention_names": [n for n in record["molecule"]["intervention_names"]["value"] or []
                                        if n and label and n.lower() in label.lower()],
                "dose_value": None, "dose_unit": None, "frequency": None,
                "randomized_n": randomized_n,
            })
    return arms


def _index_endpoints(record):
    """(normalized verbatim) -> (rank, position, timepoints) for every atlas
    endpoint, both ranks. Building this once per trial keeps the join O(n)."""
    out = {}
    for rank_key, rank in (("primary_endpoints", "primary"), ("secondary_endpoints", "secondary")):
        for e in record["endpoints"][rank_key]["value"] or []:
            out[normalize_title(e["verbatim"])] = (rank, e["position"], e["timepoints"], e["measure_type"])
    return out


def _class_rows(om):
    """(class, category, measurements) triples -- the report's own grain
    definition ('om x class x category x group')."""
    for cls in om.get("classes", []) or []:
        for cat in cls.get("categories", []) or []:
            yield cls, cat


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def build_arm_results_and_effects(record, cache):
    """Returns (arm_results, effect_estimates) for one trial -- both lists
    of schema-shaped dicts, ready to drop into results.{arm_results,
    effect_estimates}.value. Endpoints with no CT.gov results, or whose
    measure_type is in EXCLUDED_MEASURE_TYPES, contribute nothing."""
    drug = record["molecule"]["drug"]["value"]
    ep_index = _index_endpoints(record)
    oms = cache.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    id_map = build_arm_id_map(cache)
    arm_results, effect_estimates = [], []

    for om in oms:
        key = normalize_title(om.get("title", ""))
        hit = ep_index.get(key)
        if hit is None:
            continue
        rank, position, ep_timepoints, measure_type = hit
        if measure_type in EXCLUDED_MEASURE_TYPES:
            continue
        ep_ref = endpoint_key(rank, position, next(
            e["verbatim"] for e in record["endpoints"][f"{rank}_endpoints"]["value"] if e["position"] == position))

        value_type = VALUE_TYPE_MAP.get(om.get("paramType"))
        if value_type is None:
            continue  # no posted paramType => no classes/measurements to extract (verified: always co-occurs)
        # A real, second variant of the count-vs-percentage trap beyond the one
        # the design report names: CT.gov's own om-level paramType metadata can
        # itself be wrong, not just the unit-string's casing. 10 trials (mostly
        # the oldest in this corpus, e.g. PHOENIX1 2006) post a plain participant
        # COUNT (e.g. "8" of 255) tagged paramType=NUMBER instead of
        # COUNT_OF_PARTICIPANTS -- but their unitOfMeasure is the unambiguous,
        # non-percentage string "Participants", which is never one of the
        # inconsistently-cased *percentage* unit strings the report warns
        # against trusting. Treating that one specific literal value as a
        # correction to a NUMBER paramType is a narrow, safe exception, not a
        # reversion to trusting the unit string in general.
        if value_type == "number" and (om.get("unitOfMeasure") or "").strip().lower() in ("participants", "participant"):
            value_type = "count_of_participants"

        denom_by_group = {}
        for denom in om.get("denoms", []) or []:
            for c in denom.get("counts", []) or []:
                denom_by_group[c["groupId"]] = _num(c.get("value"))
        unit = om.get("unitOfMeasure")
        dispersion_type = dispersion_type_of(om.get("dispersionType"))
        ci_pct = ci_pct_of(om.get("dispersionType"))
        analysis_population = analysis_population_of(om.get("populationDescription"))
        om_labels = {g["id"]: g["title"] for g in om.get("groups", [])}

        for cls, cat in _class_rows(om):
            tp = class_timepoint(cls.get("title"), ep_timepoints)
            for m in cat.get("measurements", []) or []:
                group_id = m.get("groupId")
                value = _num(m.get("value"))
                if value is None:
                    continue
                denominator = denom_by_group.get(group_id)
                responders = response_rate_pct = None
                rate_is_derived = False
                if value_type == "count_of_participants":
                    responders = int(value)
                    # Recognize a responder rate from the MEASUREMENT's own shape
                    # (a count with a real denominator), not from the endpoint's
                    # measure_type classification -- that classifier has a real,
                    # documented coverage gap (AGENTS.md) and 37 trials whose
                    # primary result is genuinely a rate had an empty
                    # response_rate_pct purely because measure_type wasn't typed
                    # responder_rate. Every count_of_participants row with a
                    # denominator is a legitimate "N of M" rate regardless.
                    if denominator:
                        response_rate_pct = round(responders / denominator * 100, 1)
                        rate_is_derived = True
                elif value_type == "number" and unit and "percent" in unit.lower():
                    # Already posted as "percentage of participants" -- it IS a
                    # rate whether or not measure_type says responder_rate.
                    response_rate_pct = value
                # dispersion_value (a single spread number) only for SD/SE/geometric-CV;
                # a CI's own bounds go to ci_lower/ci_upper instead. Inter-quartile-range
                # and full-range also report lowerLimit/upperLimit, but the schema has no
                # generic "dispersion bounds" slot distinct from ci_lower/ci_upper -- a
                # real, documented gap (see AGENTS.md), left null rather than mislabeled
                # as a confidence interval.
                dispersion_value = _num(m.get("spread")) if dispersion_type in ("standard_deviation", "standard_error", "geometric_cv") else None
                ci_lower = _num(m.get("lowerLimit")) if dispersion_type == "confidence_interval" else None
                ci_upper = _num(m.get("upperLimit")) if dispersion_type == "confidence_interval" else None
                arm_results.append({
                    "endpoint": ep_ref, "arm_id": id_map.get((group_id, om_labels.get(group_id)), group_id),
                    "timepoint": tp,
                    "analysis_population": analysis_population, "study_period": None,
                    "denominator": int(denominator) if denominator is not None else None,
                    "value_type": value_type, "reported_value": value, "reported_unit": unit,
                    "responders": responders, "response_rate_pct": response_rate_pct,
                    "rate_is_derived": rate_is_derived,
                    "dispersion_type": dispersion_type, "dispersion_value": dispersion_value,
                    "ci_pct": ci_pct if dispersion_type == "confidence_interval" else None,
                    "ci_lower": ci_lower, "ci_upper": ci_upper,
                    "ctgov_class_title": cls.get("title"),
                })

        analyses = om.get("analyses", []) or []
        classes = om.get("classes", []) or []
        for i, a in enumerate(analyses):
            group_ids = a.get("groupIds") or []
            if len(group_ids) != 2:
                continue  # a pairwise estimate needs exactly a test and a reference arm
            tp = None
            if len(classes) <= 1:
                tp = class_timepoint(classes[0].get("title") if classes else None, ep_timepoints)
            else:
                desc = (a.get("groupDescription") or "")
                matched = next((c for c in classes if c.get("title") and c["title"] in desc), None)
                if matched is None and len(analyses) % len(classes) == 0:
                    matched = classes[i // (len(analyses) // len(classes))]
                tp = class_timepoint(matched.get("title") if matched else None, ep_timepoints)
            pv = parse_pvalue(a.get("pValue"))
            # CT.gov lists the two compared groups without saying which is
            # "test" -- assigning them in CT.gov's own order put the placebo
            # arm on the "test" side 44/102 times in this corpus (e.g. CHRONOS:
            # "Placebo qw vs Dupilumab 300 mg q2w"). Assign by role instead:
            # the investigational arm is always "test", a placebo/vehicle/other
            # (active-comparator) arm is always "reference". When neither or
            # both group labels classify as investigational (rare -- an
            # unresolvable label, or a comparison between two non-drug arms),
            # fall back to CT.gov's own order rather than guess.
            roles = [classify_arm_role(om_labels.get(gid), drug) for gid in group_ids]
            if roles[0] == "investigational" and roles[1] != "investigational":
                test_raw, reference_raw = group_ids[0], group_ids[1]
            elif roles[1] == "investigational" and roles[0] != "investigational":
                test_raw, reference_raw = group_ids[1], group_ids[0]
            else:
                test_raw, reference_raw = group_ids[0], group_ids[1]
            effect_estimates.append({
                "endpoint": ep_ref, "timepoint": tp,
                "test_arm_id": id_map.get((test_raw, om_labels.get(test_raw)), test_raw),
                "reference_arm_id": id_map.get((reference_raw, om_labels.get(reference_raw)), reference_raw),
                "comparison_kind": comparison_kind_of(a.get("nonInferiorityType")),
                "effect_type": canonicalize_effect_type(a.get("paramType")),
                "effect_type_verbatim": a.get("paramType"),
                "effect_value": _num(a.get("paramValue")),
                "ci_pct": _num(a.get("ciPctValue")), "ci_lower": _num(a.get("ciLowerLimit")),
                "ci_upper": _num(a.get("ciUpperLimit")), "ci_sides": ci_sides_of(a.get("ciNumSides")),
                "p_value": pv, "statistical_method": a.get("statisticalMethod"),
                "adjusted_for": [],
            })

    return arm_results, effect_estimates


# ---- QC gates (design report S5.2) -----------------------------------------
# Gates 1, 2, 4, 5 are hard: a row failing one is excluded rather than written
# with a known-bad value. Gate 3 is a diagnostic only (see its docstring) --
# reported, never used to drop a row.

def qc_arm_result_issues(record, row):
    """Gates 1, 2, 5 for one arm_result row. Empty list = clean."""
    issues = []
    enrollment = record["population"]["enrollment_count"]["value"]
    if enrollment is not None and row["denominator"] is not None and row["denominator"] > enrollment:
        issues.append(f"denominator {row['denominator']} > enrollment {enrollment}")
    if row["value_type"] == "count_of_participants":
        if row["responders"] is None:
            issues.append("count_of_participants row has null responders")
        if row["response_rate_pct"] is not None and not row["rate_is_derived"]:
            issues.append("response_rate_pct present but rate_is_derived is false on a count row")
    if row["response_rate_pct"] is not None and not (0 <= row["response_rate_pct"] <= 100):
        issues.append(f"response_rate_pct {row['response_rate_pct']} outside 0-100")
    return issues


def qc_endpoint_hash_issues(record, endpoint_ref):
    """Gate 4: the reference's verbatim_sha1 must match the CURRENT atlas
    endpoint at (rank, position) -- this is exactly the class of bug phase 1
    of this same effort found and fixed (a missing co-primary silently
    shifting every endpoint's position)."""
    eps = record["endpoints"][f"{endpoint_ref['rank']}_endpoints"]["value"] or []
    ep = next((e for e in eps if e["position"] == endpoint_ref["position"]), None)
    if ep is None:
        return [f"no endpoint at {endpoint_ref['rank']}#{endpoint_ref['position']}"]
    if sha1_of(ep["verbatim"]) != endpoint_ref["verbatim_sha1"]:
        return [f"verbatim_sha1 mismatch at {endpoint_ref['rank']}#{endpoint_ref['position']}"]
    return []


def qc_itt_denominator_sum_report(record, arm_results):
    """Gate 3, diagnostic: for each primary endpoint's own timepoint, the
    sum of arm denominators should be close to trial enrollment. Real,
    legitimate exceptions exist (a safety population narrower than ITT, a
    per-cohort master protocol, an interim analysis population) -- this is
    reported for review, never used to exclude a row, unlike gates 1/2/4/5."""
    enrollment = record["population"]["enrollment_count"]["value"]
    if not enrollment:
        return []
    by_key = {}
    for r in arm_results:
        ep = r["endpoint"]
        if ep["rank"] != "primary":
            continue
        key = (ep["rank"], ep["position"], repr(r["timepoint"]))
        by_key.setdefault(key, []).append(r["denominator"] or 0)
    findings = []
    for key, denoms in by_key.items():
        total = sum(denoms)
        if total and abs(total - enrollment) / enrollment > 0.15:
            findings.append(f"{key}: denominator sum {total} vs enrollment {enrollment}")
    return findings


def qc_filter(record, arm_results, effect_estimates):
    """Apply the 5 QC gates. Returns (clean_arm_results, clean_effect_estimates,
    report) where report has 'excluded_arm_results', 'excluded_effect_estimates'
    (each a list of (row, issues)) and 'itt_denominator_warnings' (gate 3,
    diagnostic only)."""
    clean_ar, excluded_ar = [], []
    for row in arm_results:
        issues = qc_arm_result_issues(record, row) + qc_endpoint_hash_issues(record, row["endpoint"])
        (excluded_ar.append((row, issues)) if issues else clean_ar.append(row))

    clean_ee, excluded_ee = [], []
    for row in effect_estimates:
        issues = qc_endpoint_hash_issues(record, row["endpoint"])
        (excluded_ee.append((row, issues)) if issues else clean_ee.append(row))

    return clean_ar, clean_ee, {
        "excluded_arm_results": excluded_ar,
        "excluded_effect_estimates": excluded_ee,
        "itt_denominator_warnings": qc_itt_denominator_sum_report(record, clean_ar),
    }
