"""
The v2 trial-record schema: one declarative spec, used three ways --

  * validate(record)      -> list of "path: problem" strings (empty = valid)
  * to_json_schema()      -> JSON Schema (draft-07) for external consumers
  * FIELD_DOCS            -> every sourced-value field path with its type, for docs/SCHEMA.md

Spec nodes are plain dicts:
  {"type": "string"|"integer"|"number"|"boolean"|"date"|"array"|"object"|"any",
   "nullable": bool, "enum": [...], "items": <spec>, "properties": {name: <spec>},
   "description": str}
Objects are strict: keys not in "properties" are errors, and every declared
key must be present (so a consumer can rely on the shape).
"""
import re

from . import SCHEMA_VERSION
from .criteria import COMPARATORS, METRICS, SCALE_VARIANTS, UNITS
from .curated_background import REGIMEN_TYPES
from .curated_multiplicity import PROCEDURES
from .curated_rescue import TRIGGERS
from .curated_schedule import PERIOD_NAMES
from .dosing import DOSE_FORMS, FREQUENCIES, ROUTES
from .endpoints import EVENT_TYPES, MEASURE_TYPES, POPULATIONS, STUDY_PERIODS
from .label import MODALITIES, WARNING_CATEGORIES
from .scalars import DATE_PRECISION
from .severity import BASES
from .sources.orange_book import APPLICATION_TYPES
from .sources.purple_book import LICENSE_TYPES

SOURCE_TYPES = (
    "ctgov_api", "ctgov_text_extraction", "protocol_pdf_extraction", "publication_extraction",
    "openfda_label", "openfda_faers", "orange_book", "purple_book", "needs_extraction",
)


# ---- spec constructors -------------------------------------------------------
def S(type_, nullable=False, description=None, **kw):
    node = {"type": type_, "nullable": nullable}
    if description:
        node["description"] = description
    node.update(kw)
    return node


def STR(nullable=False, d=None): return S("string", nullable, d)
def INT(nullable=False, d=None): return S("integer", nullable, d)
def NUM(nullable=False, d=None): return S("number", nullable, d)
def BOOL(nullable=False, d=None): return S("boolean", nullable, d)
def DATE(nullable=False, d=None): return S("date", nullable, d or "ISO date YYYY-MM-DD")
def ENUM(values, nullable=False, d=None): return S("string", nullable, d, enum=list(values))
def LIST(item, nullable=False, d=None): return S("array", nullable, d, items=item)
def OBJ(props, nullable=False, d=None, **kw): return S("object", nullable, d, properties=props, **kw)
def ANY(d=None): return S("any", True, d)


def SV(value_spec, description):
    """A sourced value: the provenance envelope every atlas field lives in."""
    return OBJ({
        "value": {**value_spec, "nullable": True},
        "source_type": ENUM(SOURCE_TYPES),
        "source_url": STR(nullable=True),
        "source_excerpt": STR(nullable=True),
        "extracted_by": STR(nullable=True),
        "reviewed_by": STR(nullable=True),
        "confidence": NUM(nullable=True),
    }, d=description, sourced=True)


# ---- shared sub-types ----------------------------------------------------------
SCORE_CRITERION = OBJ({
    "scale": STR(True, "canonical scale name, e.g. EASI, IGA, vIGA-AD, BSA, Pruritus NRS; null for non-scale criteria"),
    "scale_component": STR(True, "sub-scale / domain (e.g. 'Sleep domain', 'Anxiety')"),
    "scale_variant": ENUM(SCALE_VARIANTS, True, "pruritus NRS flavour"),
    "metric": ENUM(METRICS),
    "comparator": ENUM(COMPARATORS),
    "value": S("any", False, "number, or list of numbers when comparator is 'in'"),
    "unit": ENUM(UNITS),
    "scale_min": INT(True), "scale_max": INT(True),
    "assessed_at": LIST(STR(), True, "screening | baseline | week_N"),
    "scale_anchors": LIST(OBJ({"score": INT(), "label": STR()}), True),
}, d="ScoreCriterion: one threshold on one clinical scale")

TIMEPOINT = OBJ({"value": INT(), "unit": ENUM(["week", "day"]), "end_value": INT(True)})
ENDPOINT_REF = OBJ({
    "label": STR(), "scale": STR(True), "responder_criteria": LIST(SCORE_CRITERION),
    "timepoint_week": INT(True), "alpha": NUM(True), "step": INT(True),
})
AGENT = OBJ({"name": STR(), "strength_pct": NUM(True), "form": STR(True), "potency": STR(True)})
POTENCY_CLASS = OBJ({"system": STR(True), "comparator": ENUM(COMPARATORS), "class": S("any")})

ENDPOINT = OBJ({
    "verbatim": STR(False, "CT.gov outcome measure title, unchanged (provenance)"),
    "rank": ENUM(["primary", "secondary"]),
    "position": INT(),
    "measure_type": ENUM(MEASURE_TYPES),
    "scale": STR(True), "scale_component": STR(True), "scale_variant": ENUM(SCALE_VARIANTS, True),
    "responder_criteria": LIST(SCORE_CRITERION),
    "baseline_reference": ENUM(["baseline", "rescue_baseline"], True),
    "timepoints": LIST(TIMEPOINT),
    "through": OBJ({"value": INT(), "unit": ENUM(["week", "day"])}, True),
    "analysis_population": ENUM(POPULATIONS, True),
    "subgroup_criteria": LIST(SCORE_CRITERION),
    "subgroup_labels": LIST(ENUM(POPULATIONS)),
    "study_period": ENUM(STUDY_PERIODS, True),
    "event_type": ENUM(EVENT_TYPES, True),
    "time_frame": STR(True, "CT.gov timeFrame text (primary outcomes)"),
})

SEVERITY = OBJ({
    "severity_label": ENUM(["moderate_to_severe"], True),
    "basis": ENUM(BASES),
    "cross_reference": OBJ({"study_ids": LIST(STR()), "trial_names": LIST(STR())}, True),
    "source_criterion_numbers": LIST(INT()),
    "baseline_visit_number": INT(True),
    "criteria": LIST(SCORE_CRITERION),
})

INTERVENTION = OBJ({
    "intervention_name": STR(), "description": STR(False, "CT.gov intervention description, unchanged"),
    "is_placebo": BOOL(), "route": ENUM(ROUTES, True), "dose_form": ENUM(DOSE_FORMS, True),
    "dose_value": NUM(True), "dose_unit": STR(True), "units_per_dose": INT(True),
    "frequency": ENUM(FREQUENCIES, True), "duration_weeks": INT(True),
    "dosing_periods": LIST(OBJ({"start_value": INT(), "start_unit": ENUM(["day", "week"]), "end_value": INT(), "end_unit": ENUM(["day", "week"])})),
    "administration_sites": LIST(STR()),
    "antibody_isotype": STR(True), "molecular_target": STR(True),
})

MECHANISM = OBJ({
    "modality": ENUM(MODALITIES), "drug_class": STR(True), "antibody_isotype": STR(True),
    "binding_targets": LIST(STR()), "pathway_cytokines": LIST(STR()), "receptor_subunits": LIST(STR()),
    "kinases_inhibited": LIST(STR()),
    "selectivity": LIST(OBJ({"over": STR(), "fold": INT(), "comparator": ENUM(["==", ">"])})),
    "reversible": BOOL(True), "mechanism_established": BOOL(True), "label_section": STR(True),
})

BACKGROUND = OBJ({
    "regimen_type": ENUM(REGIMEN_TYPES, True), "background_agent_class": STR(True),
    "tcs_regimen": ENUM(["standardized", "step_down"], True),
    "step_down_rule": OBJ({
        "initial_potency": STR(), "initial_frequency": STR(), "initial_target": STR(True),
        "max_consecutive_weeks": INT(), "then_potency": STR(), "then_frequency": STR(),
        "repeat_on_recurrence": BOOL(), "stop_on_local_or_systemic_toxicity": BOOL(),
    }, True),
    "recommended_agents": LIST(AGENT),
    "emollient_required": BOOL(True), "emollient_frequency": STR(True),
    "prohibited_concomitant": LIST(STR()), "permitted_concomitant": LIST(STR()),
    "applies_to_rerandomized_maintenance": BOOL(True),
    "sponsor_trial_ids": LIST(STR()), "population_note": STR(True),
})

MULTIPLICITY = OBJ({
    "procedure": ENUM(PROCEDURES, True), "familywise_error_controlled": BOOL(),
    "alpha": NUM(True), "alpha_sided": INT(), "alpha_per_dose": NUM(True),
    "co_primary_endpoints": LIST(ENDPOINT_REF), "testing_sequence": LIST(ENDPOINT_REF),
    "alpha_split": LIST(OBJ({"group": STR(), "n_endpoints": INT(True), "alpha": NUM(True), "method": STR(), "timepoint_week": INT(True)})),
    "alpha_recycling": BOOL(True), "doses_compared": LIST(STR()), "dose_comparison_order": LIST(STR()),
    "branching_on": {**ENDPOINT_REF, "nullable": True}, "regulatory_variants": LIST(ENUM(["US", "EU"])),
    "rescue_counted_as_nonresponder": BOOL(True), "active_comparator_excluded_from_hierarchy": STR(True),
    "background_tcs": BOOL(True), "method_citations": LIST(STR()), "finalized_in_sap": BOOL(True),
    "same_design_as": LIST(STR()), "further_endpoints_through_week": INT(True),
})

SCHEDULE = OBJ({
    "screening_days": INT(True), "screening_washout": BOOL(True),
    "periods": LIST(OBJ({"name": ENUM(PERIOD_NAMES), "start_week": INT(True), "end_week": INT(True),
                         "duration_weeks": INT(True), "blinding": STR(True), "background_tcs": BOOL(True)})),
    "dosing_interval": STR(True), "visit_cadence": ENUM(["weekly", "every_2_weeks", "every_4_weeks"], True),
    "visit_cadence_until_week": INT(True), "visit_weeks": LIST(INT(), True), "visit_days": LIST(INT(), True),
    "phone_contact_weeks": LIST(INT(), True), "primary_endpoint_week": INT(True),
    "end_of_treatment_week": INT(True), "end_of_study_week": INT(True), "total_duration_weeks": INT(True),
    "follow_up_weeks": INT(True), "follow_up_days": INT(True), "follow_up_visit_week": INT(True),
    "long_term_extension": BOOL(True), "extension_end_week": INT(True), "extension_visit_interval_weeks": INT(True),
    "extension_study_id": STR(True), "rerandomization_week": INT(True), "maintenance_arms": LIST(STR(), True),
    "maintenance_response_check_weeks": LIST(INT(), True), "last_injection_week": INT(True),
    "key_secondary_weeks": LIST(INT(), True), "follow_up_visit_interval_weeks": INT(True),
    "full_visit_table_available": BOOL(), "source_inconsistency": STR(True),
})

RESCUE = OBJ({
    "permitted": BOOL(True), "trigger": ENUM(TRIGGERS, True), "earliest_week": INT(True),
    "prohibited_through_week": INT(True),
    "trigger_rules": LIST(OBJ({"from_week": INT(True), "to_week": INT(True), "criterion": SCORE_CRITERION, "consecutive_visits": INT()})),
    "flare_definition": LIST(SCORE_CRITERION), "first_step": ENUM(["topical", "systemic"], True),
    "topical_min_days_before_systemic": INT(True),
    "topical_rescue_requires_study_drug_discontinuation": BOOL(True),
    "systemic_rescue_requires_study_drug_discontinuation": BOOL(True),
    "resume_after_systemic_rescue_half_lives": INT(True), "resume_after_phototherapy_months": INT(True),
    "rescued_counted_as_nonresponder": BOOL(True), "rescued_counted_as_treatment_failure": BOOL(True),
    "continue_visits_after_discontinuation": BOOL(True), "continue_visits_through_week": INT(True),
    "topical_rescue_not_counted_after_week": INT(True), "topical_agents": LIST(AGENT),
    "topical_potency_classes": LIST(POTENCY_CLASS), "tci_reserved_areas": LIST(STR()),
    "systemic_agents": LIST(STR()),
    "oral_corticosteroid_limit": OBJ({"agents": LIST(STR()), "max_mg_per_kg": NUM(), "max_consecutive_weeks": INT()}, True),
    "rescue_period": OBJ({"drug": STR(), "dose_mg": NUM(), "frequency": ENUM(FREQUENCIES), "duration_weeks": INT(), "with_topical_standard_of_care": BOOL()}, True),
    "escape_arm_washout_half_lives": INT(True),
    "maintenance_period_rule": OBJ({"topical_rescue": STR(), "systemic_rescue": STR()}, True),
    "permitted_concomitant": LIST(STR()), "recorded_in_ecrf": BOOL(True), "applies_to_period": STR(True),
    "long_term_extension_eligible_after_rescue": BOOL(True),
})

ARM_RATE = OBJ({"arm": STR(), "n_affected": INT(), "n_at_risk": INT(), "pct": NUM(True)})
ARM_DISC = OBJ({"arm": STR(), "n_discontinued": INT(), "n_started": INT(), "pct": NUM(True)})
AE_TERM = OBJ({"meddra_pt": STR(), "meddra_soc": STR(True), "per_arm": LIST(ARM_RATE)})
BOXED_WARNING = OBJ({
    "present": BOOL(), "title": STR(True), "warning_categories": LIST(ENUM(list(WARNING_CATEGORIES))),
    "referenced_label_sections": LIST(STR()), "product_names": LIST(STR()),
})

DATE_P = OBJ({"date": DATE(), "precision": ENUM(DATE_PRECISION)})

REACTION_ROW = OBJ({"meddra_pt": STR(), "report_count": INT(), "pct_of_reports": NUM(True)})
FAERS_SUMMARY = OBJ({
    "query": OBJ({"search_field": STR(), "search_term": STR(), "receivedate_from": DATE(True),
                  "receivedate_to": DATE(True), "api_urls": LIST(STR()), "data_last_updated": DATE(True)}),
    "total_reports": INT(), "serious_reports": INT(True), "death_reports": INT(True),
    "hospitalization_reports": INT(True), "life_threatening_reports": INT(True), "disability_reports": INT(True),
    "top_reactions": LIST(REACTION_ROW), "top_serious_reactions": LIST(REACTION_ROW),
    "reports_by_year": LIST(OBJ({"year": INT(), "report_count": INT()})), "meddra_version": STR(True),
})

ORANGE_BOOK = OBJ({
    "application_type": ENUM(APPLICATION_TYPES), "application_number": STR(), "ingredient": STR(),
    "trade_name": STR(), "applicant": STR(), "applicant_full_name": STR(True),
    "products": LIST(OBJ({"product_number": STR(), "strength": STR(), "dosage_form": STR(), "route": STR(True),
                          "approval_date": DATE(True), "rld": BOOL(), "rs": BOOL(), "te_code": STR(True),
                          "marketing_type": STR()})),
    "patents": LIST(OBJ({"patent_number": STR(), "expiration_date": DATE(True), "drug_substance_claim": BOOL(),
                         "drug_product_claim": BOOL(), "patent_use_code": STR(True), "delisted": BOOL(),
                         "submission_date": DATE(True), "product_numbers": LIST(STR())})),
    "exclusivities": LIST(OBJ({"code": STR(), "expiration_date": DATE(True), "product_numbers": LIST(STR())})),
    "latest_patent_expiration": DATE(True), "latest_exclusivity_expiration": DATE(True),
    "data_file_date": STR(True),
})

PURPLE_BOOK = OBJ({
    "bla_number": STR(), "proprietary_name": STR(True), "proper_name": STR(), "applicant": STR(True),
    "license_type": ENUM(LICENSE_TYPES, True), "license_number": STR(True), "center": STR(True),
    "products": LIST(OBJ({"product_number": STR(True), "strength": STR(True), "dosage_form": STR(True), "route": STR(True),
                          "presentation": STR(True), "marketing_status": STR(True), "licensure": STR(True),
                          "approval_date": DATE(True), "submission_type": STR(True), "supplement_number": STR(True)})),
    "first_approval_date": DATE(True), "date_of_first_licensure": DATE(True),
    "reference_product_exclusivity_expiration": DATE(True), "exclusivity_expiration_date": DATE(True),
    "first_interchangeable_exclusivity_expiration": DATE(True), "orphan_exclusivity_expiration": DATE(True),
    "patent_list_provided": BOOL(True),
    "biosimilars": LIST(OBJ({"proper_name": STR(), "proprietary_name": STR(True), "bla_number": STR(), "applicant": STR(True),
                             "approval_date": DATE(True), "license_type": ENUM(["351(k)"]), "interchangeable_approval_date": DATE(True)})),
    "data_file_month": STR(True),
})

REG_APP = OBJ({
    "application_type": ENUM(["NDA", "BLA"]), "application_number": STR(), "registry": ENUM(["orange_book", "purple_book"]),
    "center": STR(True), "proprietary_name": STR(True), "applicant": STR(True), "first_approval_date": DATE(True),
})


# ---- the trial record ----------------------------------------------------------
TRIAL = OBJ({
    "schema_version": S("integer", False, "always 2", const=SCHEMA_VERSION),
    "nct_id": SV(STR(), "ClinicalTrials.gov identifier"),
    "identity": OBJ({
        "trial_name": SV(STR(), "CT.gov acronym (null when the registry has none)"),
        "official_title": SV(STR(), "CT.gov official title"),
        "sponsor": SV(STR(), "lead sponsor name"),
        "phase": SV(LIST(STR()), "CT.gov phases, e.g. ['PHASE3']"),
    }),
    "molecule": OBJ({
        "drug": SV(STR(), "canonical drug name (curated)"),
        "intervention_names": SV(LIST(STR()), "CT.gov intervention names"),
        "intervention_type": SV(LIST(STR()), "CT.gov intervention types"),
        "mechanism_of_action": SV(MECHANISM, "typed mechanism from the FDA label section 12.1; label text in source_excerpt"),
        "dosing_regimen": SV(LIST(INTERVENTION), "one typed object per CT.gov intervention"),
    }),
    "population": OBJ({
        "condition": SV(LIST(STR()), "CT.gov conditions"),
        "min_age_years": SV(NUM(), "minimum age in years (CT.gov '18 Years' -> 18)"),
        "max_age_years": SV(NUM(), "maximum age in years; null = no upper limit stated"),
        "sex": SV(ENUM(["ALL", "FEMALE", "MALE"]), "CT.gov sex"),
        "enrollment_count": SV(INT(), "CT.gov enrollment count"),
        "severity_criteria": SV(SEVERITY, "baseline severity eligibility thresholds as ScoreCriterion rows"),
    }),
    "design": OBJ({
        "study_type": SV(STR(), "CT.gov studyType"),
        "allocation": SV(STR(), "CT.gov allocation"),
        "intervention_model": SV(STR(), "CT.gov interventionModel"),
        "masking": SV(STR(), "CT.gov masking"),
        "number_of_arms": SV(INT(), "count of CT.gov armGroups"),
        "background_therapy": SV(BACKGROUND, "monotherapy vs combination design and the background regimen"),
    }),
    "endpoints": OBJ({
        "primary_endpoints": SV(LIST(ENDPOINT), "typed primary outcome measures (CT.gov order)"),
        "secondary_endpoints": SV(LIST(ENDPOINT), "typed secondary outcome measures (CT.gov order)"),
        "multiplicity_control": SV(MULTIPLICITY, "testing hierarchy / Type-I-error control"),
    }),
    "timing_ops": OBJ({
        "start_date": SV(DATE_P, "CT.gov start date with precision"),
        "primary_completion_date": SV(DATE_P, "CT.gov primary completion date with precision"),
        "completion_date": SV(DATE_P, "CT.gov completion date with precision"),
        "study_schedule": SV(SCHEDULE, "periods, visit cadence, key weeks"),
        "rescue_therapy": SV(RESCUE, "rescue-treatment rules"),
    }),
    "adverse_events": OBJ({
        "serious_adverse_event_rate": SV(LIST(ARM_RATE), "per-arm serious AE rate from CT.gov results"),
        "death_rate": SV(LIST(ARM_RATE), "per-arm death rate from CT.gov results"),
        "most_common_adverse_events": SV(LIST(AE_TERM), "top non-serious AEs by MedDRA PT with per-arm rates"),
        "discontinuation_due_to_ae_rate": SV(LIST(ARM_DISC), "per-arm discontinuation-for-AE rate"),
        "boxed_warning": SV(BOXED_WARNING, "typed boxed warning; present=false is a confirmed absence"),
    }),
    "real_world_safety": OBJ({
        "faers_summary": SV(FAERS_SUMMARY, "openFDA FAERS post-marketing report summary (drug-level)"),
    }),
    "exclusivity": OBJ({
        "regulatory_application": SV(REG_APP, "NDA/BLA join key for Orange/Purple Book (drug-level)"),
        "orange_book": SV(ORANGE_BOOK, "Orange Book patents + exclusivities (small-molecule NDAs only)"),
        "purple_book": SV(PURPLE_BOOK, "Purple Book licensure + BPCIA exclusivity (biologic BLAs only)"),
    }),
})


# ---- validation ------------------------------------------------------------------
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate(value, spec=TRIAL, path="$") -> list:
    errors = []
    if value is None:
        if not spec.get("nullable"):
            errors.append(f"{path}: null not allowed")
        return errors
    t = spec["type"]
    if "const" in spec and value != spec["const"]:
        errors.append(f"{path}: must be {spec['const']!r}")
    if t == "any":
        return errors
    if t == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
        elif "enum" in spec and value not in spec["enum"]:
            errors.append(f"{path}: {value!r} not in {spec['enum']}")
    elif t == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{path}: expected integer, got {value!r}")
    elif t == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{path}: expected number, got {value!r}")
    elif t == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{path}: expected boolean, got {value!r}")
    elif t == "date":
        if not isinstance(value, str) or not DATE_RE.match(value):
            errors.append(f"{path}: expected ISO date, got {value!r}")
    elif t == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
        else:
            for i, item in enumerate(value):
                errors.extend(validate(item, spec["items"], f"{path}[{i}]"))
    elif t == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
            return errors
        props = spec["properties"]
        for key in value:
            if key not in props:
                errors.append(f"{path}.{key}: unexpected key")
        for key, sub in props.items():
            if key not in value:
                errors.append(f"{path}.{key}: missing")
                continue
            if spec.get("sourced") and key == "value" and value.get("source_type") == "needs_extraction":
                if value["value"] is not None:
                    errors.append(f"{path}.value: needs_extraction must carry a null value")
                continue
            errors.extend(validate(value[key], sub, f"{path}.{key}"))
    return errors


# ---- exports ---------------------------------------------------------------------
def to_json_schema(spec=TRIAL):
    t = spec["type"]
    if t == "any":
        node = {}
    elif t == "date":
        node = {"type": "string", "format": "date"}
    elif t == "array":
        node = {"type": "array", "items": to_json_schema(spec["items"])}
    elif t == "object":
        node = {"type": "object", "additionalProperties": False,
                "properties": {k: to_json_schema(v) for k, v in spec["properties"].items()},
                "required": list(spec["properties"])}
    else:
        node = {"type": t}
    if "enum" in spec:
        node["enum"] = list(spec["enum"])
    if "const" in spec:
        node["const"] = spec["const"]
    if spec.get("nullable"):
        node = {"anyOf": [node, {"type": "null"}]} if node else {}
    if spec.get("description"):
        node["description"] = spec["description"]
    if spec is TRIAL:
        node = {"$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Open Derm Trial Atlas trial record (schema v2)", **node}
    return node


def field_paths(spec=TRIAL, prefix=""):
    """Every sourced-value field path -> (spec of its value, description)."""
    out = []
    if spec.get("sourced"):
        return [(prefix, spec["properties"]["value"], spec.get("description"))]
    if spec["type"] == "object":
        for key, sub in spec["properties"].items():
            out.extend(field_paths(sub, f"{prefix}.{key}" if prefix else key))
    return out


FIELD_DOCS = field_paths()
