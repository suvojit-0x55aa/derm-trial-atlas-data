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
AD_TRIALS = {
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

# Plaque Psoriasis, Phase III, 5 newer FDA-approved systemic drugs not
# already in the atlas (guselkumab, risankizumab, tildrakizumab,
# bimekizumab, deucravacitinib). Curated 2026-09-05 the same way as
# AD_TRIALS above: query.cond=Plaque Psoriasis, query.intr=<drug>,
# phase III, adult interventional RCTs, every candidate NCT ID individually
# fetched and confirmed as a real pivotal arm (not a comparator). Excluded
# as non-pivotal: NCT02203032 "NAVIGATE" (guselkumab ustekinumab-switch
# study, not first-line), NCT03162796 "Discover-1" (guselkumab, but this
# trial is actually Psoriatic Arthritis -- wrong indication, not this
# atlas's scope), NCT04102007 (single-arm open-label risankizumab
# post-switch study, not a pivotal RCT). Guselkumab therefore contributes
# only 2 pivotal trials (VOYAGE 1/2), not 4.
PSORIASIS_TRIALS = {
    "NCT02207231": "Guselkumab",       # VOYAGE 1, n=837, Janssen
    "NCT02207244": "Guselkumab",       # VOYAGE 2, n=992, Janssen
    "NCT02684370": "Risankizumab",     # UltIMMa-1, n=560, AbbVie
    "NCT02684357": "Risankizumab",     # UltIMMa-2, n=577, AbbVie
    "NCT01722331": "Tildrakizumab",    # reSURFACE 1, n=772, Sun Pharma
    "NCT01729754": "Tildrakizumab",    # reSURFACE 2, n=1090, Sun Pharma
    "NCT03370133": "Bimekizumab",      # BE VIVID, n=567, UCB
    "NCT03412747": "Bimekizumab",      # BE SURE, n=478, UCB
    "NCT03536884": "Bimekizumab",      # BE RADIANT, n=743, UCB
    "NCT03624127": "Deucravacitinib",  # POETYK-PSO-1, n=666, BMS
    "NCT03611751": "Deucravacitinib",  # POETYK-PSO-2, n=1020, BMS
}

# Hidradenitis Suppurativa, Phase III, 3 FDA-approved biologics. Curated
# 2026-09-05: every candidate individually fetched and confirmed randomized,
# placebo-controlled, drug as EXPERIMENTAL arm, resultsSection present.
# Excluded as non-pivotal: NCT01635764 (adalimumab open-label extension),
# NCT02904902 (adalimumab n=15 Japan regional study), NCT04179175
# (secukinumab dosing-interval extension), NCT04901195 "BE HEARD EXT"
# (bimekizumab long-term extension, no posted results).
HS_TRIALS = {
    "NCT01468207": "Adalimumab",   # PIONEER I, n=307, AbbVie
    "NCT01468233": "Adalimumab",   # PIONEER II, n=326, AbbVie
    "NCT03713619": "Secukinumab",  # SUNSHINE, n=544, Novartis
    "NCT03713632": "Secukinumab",  # SUNRISE, n=545, Novartis
    "NCT04242446": "Bimekizumab",  # BE HEARD I, n=505, UCB
    "NCT04242498": "Bimekizumab",  # BE HEARD II, n=509, UCB
}

# Alopecia Areata, Phase III, 3 FDA-approved JAK inhibitors. Curated
# 2026-09-05, same verification pattern. Deuruxolitinib is registered on
# CT.gov under its pre-approval compound code CTP-543, not the approved
# name -- a naive query.intr=Deuruxolitinib search returns zero results.
# Excluded as non-pivotal: NCT04006457 "ALLEGRO-LT" (ritlecitinib
# open-label long-term extension, NON_RANDOMIZED, supportive not primary),
# NCT05041803 (CTP-543 European extension study), several CTP-543/Concert
# Phase II dose-finding studies (correctly excluded by the phase:3 filter).
AA_TRIALS = {
    "NCT03570749": "Baricitinib",     # BRAVE-AA1, n=784, Eli Lilly
    "NCT03899259": "Baricitinib",     # BRAVE-AA2, n=606, Eli Lilly
    "NCT03732807": "Ritlecitinib",    # ALLEGRO-2b/3, n=718, Pfizer
    "NCT04518995": "Deuruxolitinib",  # THRIVE-AA1, n=706, Concert (CT.gov intr name: CTP-543)
    "NCT04797650": "Deuruxolitinib",  # THRIVE-AA2, n=517, Concert (CT.gov intr name: CTP-543)
}

# Chronic Spontaneous Urticaria, Phase III, 2 FDA-approved biologics.
# Curated 2026-09-05. Dupilumab's CSU indication independently confirmed
# via the live openFDA drug label (DUPIXENT label section 1.7, "Chronic
# Spontaneous Urticaria... adult and pediatric patients aged 2 years and
# older... who remain symptomatic despite H1 antihistamine treatment").
# NCT04180488 is a master protocol with 3 sub-studies (A/B/C); confirmed
# distinct from every AD dupilumab NCT already in AD_TRIALS above.
# Excluded (comparator-arm traps): NCT03580356/NCT03580369 "PEARL 1/2"
# (Novartis's pivotal trials for ligelizumab -- omalizumab is only the
# ACTIVE_COMPARATOR arm there, not the drug under test); NCT04426890
# (a biosimilar's own approval trial using omalizumab as reference
# product, not omalizumab's own registrational trial). Also excluded as
# non-pivotal (real omalizumab CSU trials, but post-approval
# label-optimization or small academic studies, not the original
# registrational program): NCT02161562 "OPTIMA", NCT01723072 "X-ACT",
# NCT02329223, NCT01803763.
CSU_TRIALS = {
    "NCT01287117": "Omalizumab",  # ASTERIA I (acronym per literature -- CT.gov's own acronym field is empty), n=319, Genentech
    "NCT01292473": "Omalizumab",  # ASTERIA II (acronym per literature), n=323, Genentech
    "NCT01264939": "Omalizumab",  # GLACIAL (acronym per literature), n=336, Genentech
    "NCT04180488": "Dupilumab",   # LIBERTY-CSU CUPID (master protocol, studies A/B/C), n=397, Sanofi
}

TRIALS = {**AD_TRIALS, **PSORIASIS_TRIALS, **HS_TRIALS, **AA_TRIALS, **CSU_TRIALS}

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
