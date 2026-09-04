"""
population.severity_criteria -- structured replacement for the v1
`severity_definition` free-text field.

Value shape:
    {
      "severity_label": "moderate_to_severe" | null,
      "basis": "eligibility_text" | "cross_reference",
      "cross_reference": {"study_ids": [...], "trial_names": [...]} | null,
      "source_criterion_numbers": [3, 4, 5],   # CT.gov inclusion-list item numbers, if numbered
      "baseline_visit_number": 3 | null,
      "criteria": [ScoreCriterion, ...]
    }

Parsed deterministically from the CT.gov eligibility text the v1 pass
already quoted (every quoted form in the 17-trial corpus is covered by
tests/test_severity.py).
"""
import re

from .criteria import criterion, detect_scale, detect_variant, normalize_symbols, num, NUM

BASES = ("eligibility_text", "cross_reference")

RANGE_NOTE = re.compile(
    r"\((?:on the |scale of )?(\d)[ -]to[ -](\d)(?: IGA)? scale(?:, in which (\d) is (\w+) and (\d) is (\w+))?\)"
    r"|\((\d)-(\d) scale(?:, (\d)=(\w+), (\d)=(\w+))?\)"
    r"|\(scale of (\d) to (\d)\)"
)
VISIT_NOTE = re.compile(r"\(visit (\d+)\)")
CROSS_REF = re.compile(r"^By cross-reference to studies ([\d/]+) \(([^)]+)\):\s*")
DURATION = re.compile(r"(?:for|present for|History of AD for)\s*(?:>=|at least)?\s*(\d+)\s*year", re.I)
JADE_LIST = re.compile(r">=\s*the following scores:\s*([^)]+)\)")
SCALE_THEN_NUM = re.compile(
    r"(EASI|vIGA|IGA|Pruritus NRS(?: severity)?|Worst Pruritus[^>]*?\(NRS\)(?: score)?|BSA)[^|;,>]*?(>=|>|<=|<)\s*" + NUM + r"\s*(%?)"
)
BSA_FIRST = re.compile(r"(>=|>|<=|<)\s*" + NUM + r"\s*%\s*(?:of )?(?:body surface area|Body surface area)")
BSA_AFTER = re.compile(r"body surface area \(BSA\) affected by AD (>=|>)\s*" + NUM + r"%", re.I)
EASI_TWO_VISITS = re.compile(r"EASI score of (>=|>)\s*(\d+) at screening and (\d+) at baseline", re.I)


def _assessed_at(clause: str, whole: str):
    t = clause.lower()
    if "screening" in t and "baseline" in t:
        return ["screening", "baseline"]
    if "baseline" in t:
        return ["baseline"]
    w = whole.lower()
    if "screening" in w and "baseline" in w:
        return ["screening", "baseline"]
    if "baseline" in w:
        return ["baseline"]
    return None


def _scale_criterion(scale_text, comparator, value, is_pct, clause, whole, rng):
    scale, _ = detect_scale(scale_text)
    variant = detect_variant(clause) if scale == "Pruritus NRS" else None
    if scale == "BSA" or is_pct:
        return criterion("BSA", "percent_bsa", comparator, value, "percent",
                         assessed_at=_assessed_at(clause, whole))
    smin, smax, anchors = rng if scale in ("IGA", "vIGA-AD") else (None, None, None)
    return criterion(scale, "absolute_score", comparator, value, "score", variant=variant,
                     scale_min=smin, scale_max=smax, anchors=anchors,
                     assessed_at=_assessed_at(clause, whole))


def _range_note(text):
    m = RANGE_NOTE.search(text)
    if not m:
        return (None, None, None), text
    g = [x for x in m.groups()]
    if g[0] is not None:
        smin, smax, a1, l1, a2, l2 = g[0], g[1], g[2], g[3], g[4], g[5]
    elif g[6] is not None:
        smin, smax, a1, l1, a2, l2 = g[6], g[7], g[8], g[9], g[10], g[11]
    else:
        smin, smax, a1, l1, a2, l2 = g[12], g[13], None, None, None, None
    anchors = None
    if a1:
        anchors = [{"score": int(a1), "label": l1}, {"score": int(a2), "label": l2}]
    return (int(smin), int(smax), anchors), text.replace(m.group(0), "")


def parse_severity(text: str) -> dict:
    whole = normalize_symbols(text)
    out = {
        "severity_label": "moderate_to_severe" if re.search(r"moderate[- ]to[- ]severe", whole, re.I) else None,
        "basis": "eligibility_text",
        "cross_reference": None,
        "source_criterion_numbers": [],
        "baseline_visit_number": None,
        "criteria": [],
    }
    m = CROSS_REF.match(whole)
    if m:
        out["basis"] = "cross_reference"
        out["cross_reference"] = {
            "study_ids": m.group(1).split("/"),
            "trial_names": [s.strip() for s in m.group(2).split("/")],
        }
        whole = whole[m.end():]
    vm = VISIT_NOTE.search(whole)
    if vm:
        out["baseline_visit_number"] = int(vm.group(1))
        whole = whole.replace(vm.group(0), "")
    rng, whole = _range_note(whole)

    dm = DURATION.search(whole)
    if dm:
        out["criteria"].append(criterion(None, "disease_duration_years", ">=", num(dm.group(1)), "years"))

    jm = JADE_LIST.search(whole)
    if jm:
        for item in jm.group(1).split(","):
            item = item.strip()
            im = re.match(r"([A-Za-z ]+?)\s*(\d+)\s*(%?)$", item)
            if not im:
                raise ValueError(f"unparsed severity list item: {item!r}")
            out["criteria"].append(_scale_criterion(im.group(1), ">=", num(im.group(2)), bool(im.group(3)), item, whole, rng))
        return out

    clauses = [c.strip() for c in re.split(r"\s\|\s|;\s", whole) if c.strip()]
    for clause in clauses:
        nm = re.match(r"(\d+)\.\s*", clause)
        if nm:
            out["source_criterion_numbers"].append(int(nm.group(1)))
            clause = clause[nm.end():]
        seen_span = []
        m2 = EASI_TWO_VISITS.search(clause)
        if m2:
            out["criteria"].append(criterion("EASI", "absolute_score", m2.group(1), num(m2.group(2)), "score", assessed_at=["screening"]))
            out["criteria"].append(criterion("EASI", "absolute_score", m2.group(1), num(m2.group(3)), "score", assessed_at=["baseline"]))
            continue
        for bm in list(BSA_FIRST.finditer(clause)) + list(BSA_AFTER.finditer(clause)):
            out["criteria"].append(criterion("BSA", "percent_bsa", bm.group(1), num(bm.group(2)), "percent", assessed_at=_assessed_at(clause, whole)))
            seen_span.append(bm.span())
        for sm in SCALE_THEN_NUM.finditer(clause):
            if any(a <= sm.start() < b for a, b in seen_span):
                continue
            if sm.group(1).upper() == "BSA" and any(c["scale"] == "BSA" for c in out["criteria"]) and _overlaps_bsa(sm, clause):
                continue
            out["criteria"].append(_scale_criterion(sm.group(1), sm.group(2), num(sm.group(3)), bool(sm.group(4)), clause, whole, rng))
    return out


def _overlaps_bsa(sm, clause):
    # "≥ 10% of body surface area (BSA) with AD involvement" is matched by
    # BSA_FIRST already; the trailing "(BSA)" must not double-count it.
    return bool(BSA_FIRST.search(clause))
