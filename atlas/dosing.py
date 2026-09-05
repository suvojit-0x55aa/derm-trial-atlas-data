"""
molecule.dosing_regimen -- one typed object per CT.gov intervention,
replacing the v1 "Name: description || Name: description" string.

    {
      "intervention_name": "PF-04965842 100 mg",
      "description": "<CT.gov interventions[].description, unchanged>",   # provenance
      "is_placebo": false,
      "route": "oral" | "subcutaneous" | null,
      "dose_form": "tablet" | "injection" | "solution" | null,
      "dose_value": 100, "dose_unit": "mg",            # only when the source states it
      "units_per_dose": 2,                              # "two tablets"
      "frequency": "once_daily" | "weekly" | "every_2_weeks" | "every_4_weeks" | null,
      "duration_weeks": 12 | null,
      "dosing_periods": [{"start_value": 1, "start_unit": "day", "end_value": 16, "end_unit": "week"}],
      "administration_sites": ["abdomen", "upper thighs", "upper arms"],
      "antibody_isotype": "IgG4" | null,
      "molecular_target": "IL-13" | null,
      "arm_names": ["PF-04965842 100 mg + Injectable Placebo followed by PF-04965842 100 mg"],  # quoted in the description
      "co_administered_with": ["Injectable Placebo"]      # "taken together with X"
    }
"""
import re

ROUTES = ("oral", "subcutaneous", "intravenous", "topical")
DOSE_FORMS = ("tablet", "injection", "solution", "cream", "ointment")
FREQUENCIES = ("once_daily", "twice_daily", "weekly", "every_2_weeks", "every_4_weeks")
WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4}
SITES = ["abdomen", "upper thighs", "upper arms", "thighs"]

SEGMENT_RE = re.compile(r"\s*\|\|\s*")
NAME_RE = re.compile(r"^([^:]+?):\s*(.*)$", re.S)


def _route(t):
    if re.search(r"\borally\b|\boral\b", t, re.I):
        return "oral"
    if re.search(r"subcutaneous", t, re.I):
        return "subcutaneous"
    if re.search(r"intravenous", t, re.I):
        return "intravenous"
    return None


def _form(t):
    if re.search(r"\btablets?\b", t, re.I):
        return "tablet"
    if re.search(r"\binjection\b", t, re.I):
        return "injection"
    if re.search(r"liquid formulation", t, re.I):
        return "solution"
    return None


def _frequency(t):
    if re.search(r"once daily|once a day|\bQD\b", t, re.I):
        return "once_daily"
    if re.search(r"twice daily|\bBID\b", t, re.I):
        return "twice_daily"
    if re.search(r"every other week|every 2 weeks|\bQ2W\b", t, re.I):
        return "every_2_weeks"
    if re.search(r"every 4 weeks|\bQ4W\b", t, re.I):
        return "every_4_weeks"
    if re.search(r"\bweekly\b|\bQW\b", t, re.I):
        return "weekly"
    return None


def _periods(t):
    out = []
    for m in re.finditer(r"from (Day|Week) (\d+) (?:until|to) Week (\d+)", t):
        period = {"start_value": int(m.group(2)), "start_unit": m.group(1).lower(),
                  "end_value": int(m.group(3)), "end_unit": "week"}
        if period not in out:
            out.append(period)
    return out


def parse_intervention(name: str, description: str) -> dict:
    t = f"{name} {description}"
    is_placebo = bool(re.search(r"placebo", name, re.I))
    dose = re.search(r"(\d+(?:\.\d+)?)\s*(mg|mcg|g)\b", name) or (
        None if is_placebo else re.search(r"(\d+(?:\.\d+)?)\s*(mg|mcg|g)\b", description))
    units = re.search(r"\b(one|two|three|four)\s+tablets?", description, re.I)
    dur = re.search(r"for (\d+) weeks", description)
    iso = re.search(r"\b(IgG[1-4])\b", description)
    target = re.search(r"binds to human (IL-\d+)", description)
    sites = [s for s in SITES if s in description.lower() and not (s == "thighs" and "upper thighs" in description.lower())]
    return {
        "intervention_name": name.strip(),
        "description": description,
        "is_placebo": is_placebo,
        "route": _route(t),
        "dose_form": _form(t),
        "dose_value": float(dose.group(1)) if dose and "." in dose.group(1) else (int(dose.group(1)) if dose else None),
        "dose_unit": dose.group(2) if dose else None,
        "units_per_dose": WORD_NUM[units.group(1).lower()] if units else None,
        "frequency": _frequency(description),
        "duration_weeks": int(dur.group(1)) if dur else None,
        "dosing_periods": _periods(description),
        "administration_sites": sites,
        "antibody_isotype": iso.group(1) if iso else None,
        "molecular_target": target.group(1) if target else None,
        "arm_names": re.findall(r'arms? "([^"]+),?"', description),
        "co_administered_with": sorted({m.group(1) for m in re.finditer(r"taken together with ([A-Z][A-Za-z ]+?)(?: from|,|\.)", description)}),
    }


def parse_dosing_regimen(text: str) -> list:
    """Split the v1 'Name: description || Name: description' string into typed interventions."""
    out = []
    for seg in SEGMENT_RE.split(text.strip()):
        m = NAME_RE.match(seg.strip())
        if not m:
            raise ValueError(f"unparsed intervention segment: {seg[:80]!r}")
        out.append(parse_intervention(m.group(1), m.group(2).strip()))
    return out
