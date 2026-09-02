#!/usr/bin/env python3
"""
Fetch pivotal Phase III AD trials for the v1 drug list from the live
ClinicalTrials.gov API v2 and write one schema-conformant JSON file per
trial to data/trials/<NCT_ID>.json.

Every field value in the output is an object:
    {
      "value": ...,
      "source_type": "ctgov_api" | "needs_extraction",
      "source_url": "...",
      "source_excerpt": "...",
      "extracted_by": "...",
      "reviewed_by": null,
      "confidence": ...
    }

Fields marked "ctgov_api" are read directly out of the live API JSON
response for that NCT ID (the JSON path is recorded in source_excerpt).
Fields marked "needs_extraction" are left with value=null: they require a
follow-up LLM-assisted extraction pass over free-text protocol/SAP/FDA
review documents plus human QA, which is explicitly out of scope for v1
(see README.md).

Run:
    python3 scripts/fetch_trials.py
"""
import json
import time
import urllib.request
from pathlib import Path

API_BASE = "https://clinicaltrials.gov/api/v2/studies"
EXTRACTED_BY = "fetch_trials.py (ctgov_api v2, v1 pass)"

# NCT ID -> (drug, informal trial name / acronym fallback label)
# Assembled by searching the live API for each drug (query.cond=Atopic
# Dermatitis, query.intr=<drug>, filter phase III, adult/adult+adolescent
# interventional RCTs) and picking the trials that are that drug's actual
# pivotal registrational studies (not just any trial mentioning the drug
# as a comparator arm in someone else's program).
TRIALS = {
    "NCT02277743": "Dupilumab",
    "NCT02277769": "Dupilumab",
    "NCT02260986": "Dupilumab",
    "NCT02755649": "Dupilumab",
    "NCT04146363": "Lebrikizumab",
    "NCT04178967": "Lebrikizumab",
    "NCT04250337": "Lebrikizumab",
    "NCT03131648": "Tralokinumab",
    "NCT03160885": "Tralokinumab",
    "NCT03363854": "Tralokinumab",
    "NCT03349060": "Abrocitinib",
    "NCT03575871": "Abrocitinib",
    "NCT03720470": "Abrocitinib",
    "NCT03627767": "Abrocitinib",
    "NCT03569293": "Upadacitinib",
    "NCT03607422": "Upadacitinib",
    "NCT03568318": "Upadacitinib",
}

NEEDS_EXTRACTION = {
    "value": None,
    "source_type": "needs_extraction",
    "source_url": None,
    "source_excerpt": None,
    "extracted_by": None,
    "reviewed_by": None,
    "confidence": None,
}


def ctgov_field(value, url, path, confidence=1.0):
    return {
        "value": value,
        "source_type": "ctgov_api",
        "source_url": url,
        "source_excerpt": path,
        "extracted_by": EXTRACTED_BY,
        "reviewed_by": None,
        "confidence": confidence if value is not None else 0.0,
    }


def needs_extraction():
    return dict(NEEDS_EXTRACTION)


def fetch_study(nct_id: str) -> dict:
    url = f"{API_BASE}/{nct_id}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp), url


def build_record(nct_id: str, drug: str, raw: dict, url: str) -> dict:
    ps = raw.get("protocolSection", {})
    idm = ps.get("identificationModule", {})
    dm = ps.get("designModule", {})
    sm = ps.get("statusModule", {})
    spm = ps.get("sponsorCollaboratorsModule", {})
    elig = ps.get("eligibilityModule", {})
    arms = ps.get("armsInterventionsModule", {})
    outcomes = ps.get("outcomesModule", {})
    conditions = ps.get("conditionsModule", {})

    interventions = arms.get("interventions", [])
    intervention_names = [i.get("name") for i in interventions if i.get("name")]
    intervention_types = sorted({i.get("type") for i in interventions if i.get("type")})
    arm_groups = arms.get("armGroups", [])

    primary_outcomes = outcomes.get("primaryOutcomes", [])
    secondary_outcomes = outcomes.get("secondaryOutcomes", [])
    primary_measure = None
    if primary_outcomes:
        po = primary_outcomes[0]
        tf = po.get("timeFrame")
        primary_measure = po.get("measure") + (f" (Time frame: {tf})" if tf else "")
    secondary_measures = [o.get("measure") for o in secondary_outcomes if o.get("measure")]

    phases = dm.get("phases") or []
    design_info = dm.get("designInfo", {})
    masking_info = design_info.get("maskingInfo", {})
    enrollment = dm.get("enrollmentInfo", {})

    record = {
        "nct_id": ctgov_field(nct_id, url, "protocolSection.identificationModule.nctId"),
        "identity": {
            "trial_name": ctgov_field(
                idm.get("acronym"), url, "protocolSection.identificationModule.acronym"
            ),
            "official_title": ctgov_field(
                idm.get("officialTitle"), url, "protocolSection.identificationModule.officialTitle"
            ),
            "sponsor": ctgov_field(
                spm.get("leadSponsor", {}).get("name"),
                url,
                "protocolSection.sponsorCollaboratorsModule.leadSponsor.name",
            ),
            "phase": ctgov_field(phases, url, "protocolSection.designModule.phases"),
        },
        "molecule": {
            "drug": ctgov_field(
                drug, url, "protocolSection.armsInterventionsModule.interventions[].name (curated)"
            ),
            "intervention_names": ctgov_field(
                intervention_names,
                url,
                "protocolSection.armsInterventionsModule.interventions[].name",
            ),
            "intervention_type": ctgov_field(
                intervention_types,
                url,
                "protocolSection.armsInterventionsModule.interventions[].type",
            ),
            "mechanism_of_action": needs_extraction(),
            "dosing_regimen": needs_extraction(),
        },
        "population": {
            "condition": ctgov_field(
                conditions.get("conditions"),
                url,
                "protocolSection.conditionsModule.conditions",
            ),
            "min_age": ctgov_field(
                elig.get("minimumAge"), url, "protocolSection.eligibilityModule.minimumAge"
            ),
            "max_age": ctgov_field(
                elig.get("maximumAge"), url, "protocolSection.eligibilityModule.maximumAge"
            ),
            "sex": ctgov_field(elig.get("sex"), url, "protocolSection.eligibilityModule.sex"),
            "enrollment_count": ctgov_field(
                enrollment.get("count"),
                url,
                "protocolSection.designModule.enrollmentInfo.count",
            ),
            "severity_definition": needs_extraction(),
        },
        "design": {
            "study_type": ctgov_field(
                dm.get("studyType"), url, "protocolSection.designModule.studyType"
            ),
            "allocation": ctgov_field(
                design_info.get("allocation"),
                url,
                "protocolSection.designModule.designInfo.allocation",
            ),
            "intervention_model": ctgov_field(
                design_info.get("interventionModel"),
                url,
                "protocolSection.designModule.designInfo.interventionModel",
            ),
            "masking": ctgov_field(
                masking_info.get("masking"),
                url,
                "protocolSection.designModule.designInfo.maskingInfo.masking",
            ),
            "number_of_arms": ctgov_field(
                len(arm_groups) if arm_groups else None,
                url,
                "len(protocolSection.armsInterventionsModule.armGroups)",
            ),
            "background_therapy_rule": needs_extraction(),
        },
        "endpoints": {
            "primary_endpoint_measure": ctgov_field(
                primary_measure,
                url,
                "protocolSection.outcomesModule.primaryOutcomes[0].measure/timeFrame",
            ),
            "secondary_endpoint_measures": ctgov_field(
                secondary_measures,
                url,
                "protocolSection.outcomesModule.secondaryOutcomes[].measure",
            ),
            "endpoint_hierarchy_multiplicity": needs_extraction(),
        },
        "timing_ops": {
            "start_date": ctgov_field(
                sm.get("startDateStruct", {}).get("date"),
                url,
                "protocolSection.statusModule.startDateStruct.date",
            ),
            "primary_completion_date": ctgov_field(
                sm.get("primaryCompletionDateStruct", {}).get("date"),
                url,
                "protocolSection.statusModule.primaryCompletionDateStruct.date",
            ),
            "completion_date": ctgov_field(
                sm.get("completionDateStruct", {}).get("date"),
                url,
                "protocolSection.statusModule.completionDateStruct.date",
            ),
            "visit_schedule": needs_extraction(),
            "rescue_therapy_rules": needs_extraction(),
        },
    }
    return record


def main():
    out_dir = Path(__file__).resolve().parent.parent / "data" / "trials"
    out_dir.mkdir(parents=True, exist_ok=True)

    for nct_id, drug in TRIALS.items():
        print(f"Fetching {nct_id} ({drug})...")
        raw, url = fetch_study(nct_id)
        record = build_record(nct_id, drug, raw, url)
        out_path = out_dir / f"{nct_id}.json"
        out_path.write_text(json.dumps(record, indent=2) + "\n")
        time.sleep(0.3)  # be polite to the public API

    print(f"Wrote {len(TRIALS)} trial files to {out_dir}")


if __name__ == "__main__":
    main()
