"""
ScoreCriterion -- the one atomic "threshold on a clinical scale" type reused by
eligibility (severity_criteria), endpoint responder definitions, rescue
triggers, and flare definitions.

    {
      "scale": "EASI",                 # canonical scale name (see SCALES)
      "scale_component": null,         # sub-scale / domain, e.g. "Sleep domain"
      "scale_variant": null,           # e.g. "worst_daily_weekly_average" for pruritus NRS
      "metric": "percent_improvement_from_baseline",
      "comparator": ">=",              # >=, >, <=, <, ==, in
      "value": 75,                     # number, or list of numbers for "in"
      "unit": "percent",               # score | percent | points | years
      "scale_min": null, "scale_max": null,   # only when the source states the range
      "assessed_at": ["screening", "baseline"],  # or null (endpoints carry timepoints)
      "scale_anchors": null            # [{"score": 3, "label": "moderate"}] when the source states them
    }

Only the canonicalisation of scale names and the small regex helpers live
here; the field-specific parsers (severity, endpoints) compose them.
"""
import re

METRICS = (
    "absolute_score",
    "percent_improvement_from_baseline",
    "point_reduction_from_baseline",
    "point_improvement_from_baseline",
    "percent_bsa",
    "disease_duration_years",
    "percent_of_response_lost",
)
COMPARATORS = (">=", ">", "<=", "<", "==", "in")
UNITS = ("score", "percent", "points", "years")
SCALE_VARIANTS = (
    "peak_daily",
    "peak_daily_weekly_average",
    "worst_daily",
    "worst_daily_weekly_average",
    "severity",
)

# Ordered: longer / more specific patterns first. (regex, canonical scale, component)
SCALE_PATTERNS = [
    (r"validated Investigator'?s Global Assessment(?: for AD)?|vIGA-AD|vIGA", "vIGA-AD", None),
    (r"Investigator'?s? Global Assessment|\bIGA\b", "IGA", None),
    (r"Patient Global Assessment|\bPtGA\b", "PtGA", None),
    (r"Eczema Area and Severity Index|\bEASI\b", "EASI", None),
    (r"SCORing Atopic Dermatitis|Scoring Atopic Dermatitis|\bSCORAD\b", "SCORAD", None),
    (r"Children'?s Dermatology Life Quality Index|\bCDLQI\b", "CDLQI", None),
    (r"Dermatology Life Quality Index|\bDLQI\b", "DLQI", None),
    (r"Patient[- ]Oriented Eczema Measure|\bPOEM\b", "POEM", None),
    (r"Pruritus and Symptoms Assessment for Atopic Dermatitis|\bPSAAD\b", "PSAAD", None),
    (r"Atopic Dermatitis Impact Scale|\bADerm-IS\b", "ADerm-IS", None),
    (r"Atopic Dermatitis Symptom Scale|\bADerm-SS\b", "ADerm-SS", None),
    (r"Hospital Anxiety(?: and)? Depression Scale|\bHADS\b", "HADS", None),
    (r"Global Individual Signs Score|\bGISS\b", "GISS", None),
    (r"EuroQol Quality of Life 5-Dimension Youth Scale|\bEQ-5D-Y\b", "EQ-5D-Y", None),
    (r"EuroQol Quality of Life 5-Dimension 5-Level Scale|European Quality of Life-5 Dimensions-5 Levels|\bEQ-5D-5L\b", "EQ-5D-5L", None),
    (r"European Quality of Life-5 Dimensions|\bEQ-5D\b", "EQ-5D", None),
    (r"Pediatric Functional Assessment of Chronic Illness Therapy Fatigue Scale|Peds-FACIT-F", "Peds-FACIT-F", None),
    (r"Functional Assessment of Chronic Illness Therapy Fatigue Scale|\bFACIT-F\b", "FACIT-F", None),
    (r"Patient-Reported Outcomes Measurement Information System|\bPROMIS\b", "PROMIS", None),
    (r"Short Form-36v2|SF-36v2", "SF-36v2", None),
    (r"Asthma Control Questionnaire|\bACQ-5\b", "ACQ-5", None),
    (r"Sleep-loss Score", "Sleep-loss", None),
    (r"(?:Peak|Worst|Pruritus)[^,;]{0,40}?Numeric(?:al)? Rating Scale|Pruritus NRS|Numeric(?:al)? Rating Scale(?: \(NRS\))? for Severity of Pruritus|\bPP-NRS\b|Pruritus[^,;]{0,25}?\bNRS\b|\bNRS\b", "Pruritus NRS", None),
    (r"[Bb]ody [Ss]urface [Aa]rea|\bBSA\b|%BSA", "BSA", None),
]

SCALES = sorted({s for _, s, _ in SCALE_PATTERNS})

# (regex, canonical component) -- applied after a scale is known
COMPONENT_PATTERNS = [
    (r"Sleep Domain", "Sleep domain"),
    (r"Emotional State Domain", "Emotional State domain"),
    (r"Daily Activities Domain", "Daily Activities domain"),
    (r"Skin Pain", "Skin Pain"),
    (r"TSS-7|7-Item Total Symptom Score", "TSS-7"),
    (r"Total Hospital Anxiety", "Total"),
    (r"HADS-A\b|[:-] Anxiety (?:Scale|Subscale)|PROMIS\)? Anxiety", "Anxiety"),
    (r"HADS-D\b|[:-] Depression (?:Scale|Subscale)|PROMIS\)? Depression", "Depression"),
    (r"VAS(?: Score)? of Itch and Sleep Loss|Visual Analog(?:ue)? Scale \(VAS\) of Itch and Sleep Loss|Visual Analog(?:ue)? Scale \(VAS\) Score of Itch and Sleep Loss|VAS of Itch and Sleep Loss", "VAS Itch and Sleep Loss"),
    (r"Visual Analog(?:ue)? Scale \(VAS\) of Itch|VAS Itch", "VAS Itch"),
    (r"Visual Analog(?:ue)? Scale \(VAS\) Sleep Loss|Visual Analogue Scale of Sleep Loss", "VAS Sleep Loss"),
    (r"Visual Analog(?:ue)? Scale(?: \(VAS\))?(?: Score)?|Visual Analog Score \(VAS\)|VAS Score|- VAS|\bVAS\b", "VAS"),
    (r"Index Value|Health State Index", "Index"),
    (r"Physical Component Summary", "Physical Component Summary"),
    (r"Mental Component Summary", "Mental Component Summary"),
    (r"Total Score", "Total"),
]

NUM = r"(\d+(?:\.\d+)?)"


def normalize_symbols(text: str) -> str:
    """Map the many spellings of comparison operators onto ASCII tokens."""
    t = text.replace("≥", ">=").replace("≤", "<=").replace("\\>=", ">=")
    t = re.sub(r"Greater Than or Equal(?: to)?(?: \(>=\))?", ">=", t, flags=re.I)
    t = re.sub(r"Less Than(?: or Equal to)? \(<\)|Less Than \(<\)", "<", t, flags=re.I)
    t = re.sub(r"\bat [Ll]east\b", ">=", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def detect_scale(text: str):
    """Return (scale, component) for the first clinical scale named in text."""
    best = None
    for pattern, scale, _ in SCALE_PATTERNS:
        m = re.search(pattern, text)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), scale)
    if best is None:
        return None, None
    scale = best[1]
    component = None
    for pattern, comp in COMPONENT_PATTERNS:
        if re.search(pattern, text):
            component = comp
            break
    return scale, component


def criterion(scale, metric, comparator, value, unit, component=None, variant=None,
              scale_min=None, scale_max=None, assessed_at=None, anchors=None) -> dict:
    assert metric in METRICS, metric
    assert comparator in COMPARATORS, comparator
    assert unit in UNITS, unit
    assert variant is None or variant in SCALE_VARIANTS, variant
    return {
        "scale": scale,
        "scale_component": component,
        "scale_variant": variant,
        "metric": metric,
        "comparator": comparator,
        "value": value,
        "unit": unit,
        "scale_min": scale_min,
        "scale_max": scale_max,
        "assessed_at": assessed_at,
        "scale_anchors": anchors,
    }


def detect_variant(text: str):
    """Pruritus-NRS flavour named in text (peak vs worst daily, weekly average)."""
    t = text.lower()
    if "pruritus" not in t and "nrs" not in t:
        return None
    weekly = "weekly average" in t
    if "worst" in t:
        return "worst_daily_weekly_average" if weekly else "worst_daily"
    if "peak" in t:
        return "peak_daily_weekly_average" if weekly else "peak_daily"
    if "severity" in t:
        return "severity"
    return None


def num(s: str):
    f = float(s)
    return int(f) if f.is_integer() else f
