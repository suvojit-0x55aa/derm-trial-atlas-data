"""
v1 -> v2 migration of a trial record (data/trials/<NCT_ID>.json).

Rules:
  * every v1 sourced value keeps its provenance envelope; only `value` changes
    shape, `extracted_by` gets a "; structured by atlas.migrate v1->v2" suffix
    on the fields whose value was restructured, and -- where the v1 value was
    prose that is not already quoted in `source_excerpt` -- that prose is
    appended to `source_excerpt` so nothing extracted in v1 is dropped;
  * needs_extraction fields stay needs_extraction under their v2 name;
  * new v2 field groups (real_world_safety, exclusivity) are added as
    needs_extraction placeholders, except `exclusivity.regulatory_application`,
    which is populated from the Orange/Purple Book rows in
    atlas/regulatory_applications.py (the NDA/BLA join key the scale-out task
    needs before it can write Orange/Purple Book data).

`migrate_trial` is pure (dict in, dict out) so tests can run it on fixtures.
"""
import copy

from . import SCHEMA_VERSION
from .curated_background import BACKGROUND_THERAPY
from .curated_multiplicity import MULTIPLICITY_CONTROL
from .curated_rescue import RESCUE_THERAPY
from .curated_schedule import STUDY_SCHEDULE
from .dosing import parse_dosing_regimen
from .endpoints import parse_endpoint
from .label import parse_boxed_warning, parse_mechanism
from .regulatory_applications import regulatory_application_field
from .scalars import parse_age_years, parse_ctgov_date
from .severity import parse_severity

MIGRATOR = "atlas.migrate v1->v2"

CURATED = {
    ("design", "background_therapy_rule"): BACKGROUND_THERAPY,
    ("endpoints", "endpoint_hierarchy_multiplicity"): MULTIPLICITY_CONTROL,
    ("timing_ops", "visit_schedule"): STUDY_SCHEDULE,
    ("timing_ops", "rescue_therapy_rules"): RESCUE_THERAPY,
}
RENAMES = {
    ("population", "severity_definition"): "severity_criteria",
    ("population", "min_age"): "min_age_years",
    ("population", "max_age"): "max_age_years",
    ("design", "background_therapy_rule"): "background_therapy",
    ("endpoints", "primary_endpoint_measure"): "primary_endpoints",
    ("endpoints", "secondary_endpoint_measures"): "secondary_endpoints",
    ("endpoints", "endpoint_hierarchy_multiplicity"): "multiplicity_control",
    ("timing_ops", "visit_schedule"): "study_schedule",
    ("timing_ops", "rescue_therapy_rules"): "rescue_therapy",
}


class AlreadyMigrated(ValueError):
    pass


def needs_extraction():
    return {"value": None, "source_type": "needs_extraction", "source_url": None, "source_excerpt": None,
            "extracted_by": None, "reviewed_by": None, "confidence": None}


def restructure(sv: dict, new_value, keep_prose: bool = True) -> dict:
    """Copy a sourced value with a new typed `value`, preserving the v1 prose as provenance."""
    out = copy.deepcopy(sv)
    old = sv.get("value")
    if sv.get("source_type") == "needs_extraction":
        return out
    out["value"] = new_value
    out["extracted_by"] = f"{sv.get('extracted_by')}; structured by {MIGRATOR}"
    if keep_prose and isinstance(old, str):
        excerpt = sv.get("source_excerpt") or ""
        if old.strip() not in excerpt:
            out["source_excerpt"] = f"{excerpt} -- v1 extracted text: {old}".strip(" -") if excerpt else old
    return out


def _curated(nct_id, sv, table):
    if sv.get("source_type") == "needs_extraction":
        return copy.deepcopy(sv)
    if nct_id not in table:
        raise KeyError(f"no curated structured value for {nct_id} ({sv.get('value', '')[:60]!r}) -- add it to the curated table")
    return restructure(sv, copy.deepcopy(table[nct_id]))


def _endpoints(sv, rank):
    raw = sv.get("value")
    if sv.get("source_type") == "needs_extraction" or raw is None:
        return restructure(sv, None)
    titles = [raw] if isinstance(raw, str) else list(raw)
    return restructure(sv, [parse_endpoint(t, rank, i + 1) for i, t in enumerate(titles)], keep_prose=False)


def _ae_terms(sv):
    if sv.get("value") is None:
        return copy.deepcopy(sv)
    rows = [{"meddra_pt": r["term"], "meddra_soc": r.get("organ_system"), "per_arm": r["per_arm"]} for r in sv["value"]]
    return restructure(sv, rows)


def migrate_trial(v1: dict) -> dict:
    if v1.get("schema_version") == SCHEMA_VERSION:
        raise AlreadyMigrated(v1["nct_id"]["value"])
    nct = v1["nct_id"]["value"]
    idn, mol, pop, des, end, tim, ae = (v1[g] for g in ("identity", "molecule", "population", "design", "endpoints", "timing_ops", "adverse_events"))
    drug = mol["drug"]["value"]

    out = {
        "schema_version": SCHEMA_VERSION,
        "nct_id": copy.deepcopy(v1["nct_id"]),
        "identity": copy.deepcopy(idn),
        "molecule": {
            "drug": copy.deepcopy(mol["drug"]),
            "intervention_names": copy.deepcopy(mol["intervention_names"]),
            "intervention_type": copy.deepcopy(mol["intervention_type"]),
            "mechanism_of_action": restructure(mol["mechanism_of_action"], parse_mechanism(mol["mechanism_of_action"]["value"]))
            if mol["mechanism_of_action"]["value"] else copy.deepcopy(mol["mechanism_of_action"]),
            "dosing_regimen": restructure(mol["dosing_regimen"], parse_dosing_regimen(mol["dosing_regimen"]["value"]), keep_prose=False)
            if mol["dosing_regimen"]["value"] else copy.deepcopy(mol["dosing_regimen"]),
        },
        "population": {
            "condition": copy.deepcopy(pop["condition"]),
            "min_age_years": restructure(pop["min_age"], parse_age_years(pop["min_age"]["value"]), keep_prose=False),
            "max_age_years": restructure(pop["max_age"], parse_age_years(pop["max_age"]["value"]), keep_prose=False),
            "sex": copy.deepcopy(pop["sex"]),
            "enrollment_count": copy.deepcopy(pop["enrollment_count"]),
            "severity_criteria": restructure(pop["severity_definition"], parse_severity(pop["severity_definition"]["value"]))
            if pop["severity_definition"]["value"] else copy.deepcopy(pop["severity_definition"]),
        },
        "design": {
            **{k: copy.deepcopy(des[k]) for k in ("study_type", "allocation", "intervention_model", "masking", "number_of_arms")},
            "background_therapy": _curated(nct, des["background_therapy_rule"], BACKGROUND_THERAPY),
        },
        "endpoints": {
            "primary_endpoints": _endpoints(end["primary_endpoint_measure"], "primary"),
            "secondary_endpoints": _endpoints(end["secondary_endpoint_measures"], "secondary"),
            "multiplicity_control": _curated(nct, end["endpoint_hierarchy_multiplicity"], MULTIPLICITY_CONTROL),
        },
        "timing_ops": {
            **{k: restructure(tim[k], parse_ctgov_date(tim[k]["value"]), keep_prose=False)
               for k in ("start_date", "primary_completion_date", "completion_date")},
            "study_schedule": _curated(nct, tim["visit_schedule"], STUDY_SCHEDULE),
            "rescue_therapy": _curated(nct, tim["rescue_therapy_rules"], RESCUE_THERAPY),
        },
        "adverse_events": {
            "serious_adverse_event_rate": copy.deepcopy(ae["serious_adverse_event_rate"]),
            "death_rate": copy.deepcopy(ae["death_rate"]),
            "most_common_adverse_events": _ae_terms(ae["most_common_adverse_events"]),
            "discontinuation_due_to_ae_rate": copy.deepcopy(ae["discontinuation_due_to_ae_rate"]),
            "boxed_warning": restructure(ae["boxed_warning"], parse_boxed_warning(ae["boxed_warning"]["value"])),
        },
        "real_world_safety": {"faers_summary": needs_extraction()},
        "exclusivity": {
            "regulatory_application": regulatory_application_field(drug),
            "orange_book": needs_extraction(),
            "purple_book": needs_extraction(),
        },
    }
    # The null-with-openfda_label boxed warning: value becomes {present: false}, keep the "checked, none" excerpt.
    bw = out["adverse_events"]["boxed_warning"]
    if ae["boxed_warning"]["value"] is None and ae["boxed_warning"]["source_type"] == "openfda_label":
        bw["extracted_by"] = f"{ae['boxed_warning'].get('extracted_by')}; structured by {MIGRATOR}"
    return out
