#!/usr/bin/env python3
"""
Second-pass LLM-assisted extraction over free-text sources: CT.gov's own
eligibilityCriteria/intervention-description text, each trial's Study
Protocol / SAP PDF (CT.gov documentSection), and the openFDA structured
drug-label API.

This fills in several of the fields that scripts/fetch_trials.py left as
needs_extraction, per source_type:

  ctgov_text_extraction   - parsed from a CT.gov API free-text field
                            (eligibilityCriteria, intervention.description)
                            via regex + review; done live by this script.
  protocol_pdf_extraction - parsed from a trial's Study Protocol / SAP PDF.
                            PDF-table extraction isn't reliable enough to
                            automate (see visit_schedule below), so these
                            excerpts were produced by downloading each
                            trial's PDF (CT.gov documentSection -> CDN URL,
                            see fetch_protocol_docs.py), converting with
                            `pdftotext -layout`, and reading the relevant
                            section by hand; the verified excerpts are
                            hardcoded below in RESCUE_RULES,
                            MULTIPLICITY_RULES, and BACKGROUND_THERAPY_PDF,
                            each citing the exact section it came from.
  openfda_label           - openFDA structured drug-label API
                            (drug-level, not trial-level; same value reused
                            across every trial of that drug)

Every value here is machine/LLM-extracted and marked reviewed_by: null and
confidence < 1.0 -- it still needs the human clinical QA pass (captain +
Garvita) called for in the project brief before being treated as
authoritative. visit_schedule is deliberately left needs_extraction: the
schedule lives in large multi-page PDF tables that plain-text PDF
conversion cannot flatten into a trustworthy structured value, and a
garbled table is worse than a null.

Run after scripts/fetch_trials.py:
    python3 scripts/enrich_needs_extraction.py
"""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_DIR = ROOT / "data" / "trials"
CACHE_DIR = ROOT / "data" / "_raw_cache"  # gitignored working cache
CACHE_DIR.mkdir(exist_ok=True)

CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"
CDN_BASE = "https://cdn.clinicaltrials.gov/large-docs"
OPENFDA_LABEL = "https://api.fda.gov/drug/label.json"

EXTRACTED_BY = "enrich_needs_extraction.py (LLM-assisted extraction, v1 pass; pending human QA)"


def fda_setid(drug: str) -> str | None:
    url = f"{OPENFDA_LABEL}?search=openfda.substance_name:{drug.upper()}&limit=1"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
        return data["results"][0]
    except Exception:
        return None


def fetch_full_study(nct_id: str) -> dict:
    cache = CACHE_DIR / f"{nct_id}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    url = f"{CTGOV_API}/{nct_id}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    cache.write_text(json.dumps(data))
    return data




def field(value, source_type, source_url, source_excerpt, confidence):
    return {
        "value": value,
        "source_type": source_type,
        "source_url": source_url,
        "source_excerpt": source_excerpt,
        "extracted_by": EXTRACTED_BY,
        "reviewed_by": None,
        "confidence": confidence,
    }


SEVERITY_RE = re.compile(
    r"^[*\d.\s]*.{0,20}(EASI|IGA|vIGA|body surface area|BSA).{0,200}", re.I
)
BG_THERAPY_RE = re.compile(
    r"background\s+topical\s+therapy"
    r"|standardized\s+background\s+topical"
    r"|(require|must|willing).{0,40}\btopical\s+corticosteroid",
    re.I,
)

# CT.gov intervention names use each company's internal compound code
# rather than the generic drug name for 2 of the 5 drugs; map generic name
# -> the code string that shows up in armsInterventionsModule.interventions.
DRUG_CODE_ALIASES = {
    "abrocitinib": ["pf-04965842"],
    "upadacitinib": ["abt-494"],
}


def extract_severity_and_bg(elig_criteria: str, url: str):
    lines = [l.strip("*-> \t") for l in elig_criteria.split("\n") if l.strip()]
    sev_hits = []
    bg_hits = []
    for l in lines:
        if re.search(r"\b(EASI|IGA|vIGA)\b", l) and re.search(r"[≥≤<>]|BSA|body surface", l):
            sev_hits.append(l)
        elif re.search(r"\bBSA\b|body surface area", l, re.I) and re.search(r"[≥≤<>]", l):
            sev_hits.append(l)
        if BG_THERAPY_RE.search(l):
            bg_hits.append(l)

    sev_field = None
    if sev_hits:
        text = " | ".join(dict.fromkeys(sev_hits))  # dedupe, preserve order
        sev_field = field(
            text, "ctgov_text_extraction", url, text, confidence=0.75
        )
    bg_field = None
    if bg_hits:
        text = " | ".join(dict.fromkeys(bg_hits))
        bg_field = field(text, "ctgov_text_extraction", url, text, confidence=0.7)
    return sev_field, bg_field


def extract_dosing(raw: dict, drug: str, url: str):
    arms = raw.get("protocolSection", {}).get("armsInterventionsModule", {})
    interventions = arms.get("interventions", [])
    needles = [drug.lower()] + DRUG_CODE_ALIASES.get(drug.lower(), [])
    matches = [
        i for i in interventions
        if any(n in (i.get("name") or "").lower() for n in needles)
        or any(n in (i.get("description") or "").lower() for n in needles)
    ]
    if not matches:
        return None
    text = " || ".join(
        f"{i.get('name')}: {i.get('description')}" for i in matches if i.get("description")
    )
    if not text:
        return None
    return field(text, "ctgov_text_extraction", url, text, confidence=0.8)


def extract_bg_from_tcs_arm(raw: dict, url: str):
    """Fallback for combination-therapy trials: pull the background/concomitant
    Topical Corticosteroid intervention's own description when eligibility-text
    regex found nothing (add-on designs describe the TCS regimen there instead
    of in eligibilityCriteria)."""
    arms = raw.get("protocolSection", {}).get("armsInterventionsModule", {})
    for i in arms.get("interventions", []):
        name = (i.get("name") or "")
        if re.search(r"topical\s+corticosteroid|\bTCS\b", name, re.I) and i.get("description"):
            text = f"{name}: {i.get('description')}"
            return field(text, "ctgov_text_extraction", url, text, confidence=0.65)
    return None


# Manually curated excerpts pulled from each trial's downloaded Study
# Protocol / Statistical Analysis Plan PDF (CT.gov documentSection). Only
# trials with a posted Protocol/SAP have real source material here; the 4
# older Dupilumab trials (SOLO 1/2, CHRONOS, CAFE) have no documentSection
# on CT.gov and are left needs_extraction for these two fields.
RESCUE_RULES = {
    "NCT03131648": (  # ECZTRA 1
        "If medically necessary (i.e., to control intolerable AD symptoms), rescue treatment for AD "
        "may be provided to trial subjects at the discretion of the investigator. Subjects who receive "
        "rescue treatment during the initial treatment period will be considered non-responders, but "
        "continue IMP if rescue was topical. Investigators should limit the first step of rescue to "
        "topical medications and escalate to systemic medications only if no adequate response after "
        "at least 14 days of topical treatment. Systemic corticosteroid/immunosuppressive rescue "
        "requires immediate IMP discontinuation; IMP may resume no sooner than 5 half-lives after the "
        "last dose of systemic rescue medication.",
        "Prot", "Section 9.7 Rescue treatment",
    ),
    "NCT03160885": (  # ECZTRA 2 (same sponsor template as ECZTRA 1)
        "If medically necessary (i.e., to control intolerable AD symptoms), rescue treatment for AD "
        "may be provided to trial subjects at the discretion of the investigator. Subjects who receive "
        "rescue treatment during the initial treatment period will be considered non-responders, but "
        "continue IMP if rescue consisted of topical medications. Investigators should limit the first "
        "step of rescue to topical medications, escalating to systemic medications only after at least "
        "14 days without adequate response. Systemic corticosteroid/immunosuppressive rescue requires "
        "immediate IMP discontinuation; IMP may resume no sooner than 5 half-lives after the last dose "
        "of systemic rescue medication.",
        "Prot", "Section 9.7 Rescue treatment",
    ),
    "NCT03363854": (  # ECZTRA 3
        "If medically necessary (i.e., to control intolerable AD symptoms), rescue treatment for AD may "
        "be provided at investigator discretion. Investigators should limit the first step of rescue to "
        "topical medications (higher-potency TCS: EU Class >3 / US Class <4), escalating to systemic "
        "medications only after at least 14 days without adequate response; subjects on topical rescue "
        "continue IMP. Systemic corticosteroid/immunosuppressive rescue requires immediate IMP "
        "discontinuation; IMP may resume no sooner than 5 half-lives after the last dose of systemic "
        "rescue medication.",
        "Prot", "Section 9.6 Rescue treatment",
    ),
    "NCT03568318": (  # AD Up
        "Starting at the Week 4 visit, rescue treatment for AD may be provided if medically necessary and "
        "prespecified EASI-response thresholds are not met (Week 4-24: <EASI-50 at any 2 consecutive "
        "scheduled visits vs. Baseline; after Week 24: <EASI-50 at any visit vs. Baseline). First step is "
        "high/super-high potency TCS or alternative topical AD medication for >=7 days before escalating "
        "to systemic treatment. From Week 52, topical AD medication is no longer counted as rescue. If "
        "oral corticosteroids are used, rescue is limited to prednisone/prednisolone up to 1 mg/kg for no "
        "more than 2 consecutive weeks.",
        "Prot", "Section 5.4 Rescue Therapy",
    ),
    "NCT03569293": (  # Measure Up 1
        "Starting at the Week 4 visit, rescue treatment for AD may be provided if medically necessary and "
        "prespecified EASI-response thresholds are not met (Week 4-24: <EASI-50 at any 2 consecutive "
        "scheduled visits vs. Baseline; after Week 24: <EASI-50 at any visit vs. Baseline). First step is "
        "topical medication for >=7 days before escalating to systemic treatment. From Week 16, topical AD "
        "medication is no longer counted as rescue for efficacy analysis purposes; only systemic AD "
        "treatments count as rescue thereafter.",
        "Prot", "Section 5.4 Rescue Therapy",
    ),
    "NCT03607422": (  # Measure Up 2 (same design as Measure Up 1)
        "Starting at the Week 4 visit, rescue treatment for AD may be provided if medically necessary and "
        "prespecified EASI-response thresholds are not met (Week 4-24: <EASI-50 at any 2 consecutive "
        "scheduled visits vs. Baseline; after Week 24: <EASI-50 at any visit vs. Baseline). First step is "
        "topical medication for >=7 days before escalating to systemic treatment. From Week 16, topical AD "
        "medication is no longer counted as rescue for efficacy analysis purposes; only systemic AD "
        "treatments count as rescue thereafter.",
        "Prot", "Section 5.4 Rescue Therapy",
    ),
    "NCT03627767": (  # JADE REGIMEN
        "Subjects meeting the protocol definition of flare during the blinded maintenance period enter an "
        "open-label rescue period of another 12-week course of abrocitinib 200 mg QD with topical therapy "
        "per local standard of care. Flare requiring rescue treatment is defined as a loss of at least 50% "
        "of the EASI response achieved at Week 12, combined with an IGA score of 2 or higher.",
        "SAP", "SAP narrative, p.8-9 (open-label rescue period / flare definition)",
    ),
    "NCT04146363": (  # ADvocate1
        "Induction Period: use of topical/systemic AD treatment is prohibited from Baseline through Week "
        "16. If systemic rescue treatment (e.g., oral corticosteroids, phototherapy, cyclosporin) is "
        "required, study drug must be discontinued; the patient continues study visits through Week 16. "
        "Patients needing systemic rescue must wait for rescue-medication washout (>=5 half-lives) before "
        "entering the Escape Arm. Maintenance Period: intermittent topical rescue is permitted; short-term "
        "systemic rescue is assessed case-by-case with the medical monitor.",
        "Prot", "Section 6.3 Rescue Treatment for Atopic Dermatitis",
    ),
    "NCT04178967": (  # ADvocate2 (identical protocol language to ADvocate1)
        "Induction Period: use of topical/systemic AD treatment is prohibited from Baseline through Week "
        "16. If systemic rescue treatment (e.g., oral corticosteroids, phototherapy, cyclosporin) is "
        "required, study drug must be discontinued; the patient continues study visits through Week 16. "
        "Patients needing systemic rescue must wait for rescue-medication washout (>=5 half-lives) before "
        "entering the Escape Arm. Maintenance Period: intermittent topical rescue is permitted; short-term "
        "systemic rescue is assessed case-by-case with the medical monitor.",
        "Prot", "Section 6.3 Rescue Treatment for Atopic Dermatitis",
    ),
    "NCT04250337": (  # ADhere
        "Add-on rescue therapy may be used for intolerable clinical worsening: high-potency TCS or "
        "systemic treatment (e.g., oral corticosteroids, phototherapy, cyclosporin). Study drug must be "
        "discontinued for patients receiving systemic rescue treatment; patients continue attending study "
        "visits through Week 16 regardless. Patients using topical or systemic rescue medication who "
        "complete the study through Week 16 are eligible for a separate long-term extension study. All "
        "rescue use must be captured in the eCRF.",
        "Prot", "Section 6.4 Rescue Treatment for Atopic Dermatitis",
    ),
}

MULTIPLICITY_RULES = {
    "NCT03131648": (  # ECZTRA 1
        "US submission: a dedicated modified confirmatory testing hierarchy. IGA 0/1 vs. placebo tested "
        "at Week 16 (5% level); if significant, EASI-75 vs. placebo tested (5%); if significant, Pruritus "
        "tested (5%). If all three are significant, alpha is split for 2 secondary endpoints at Week 16 "
        "(1%) tested in parallel with maintenance endpoints at Week 52 (4%), with alpha-recycling between "
        "the two groups if all tests in one group are significant (up to 5%). The 2 Week-16 secondary "
        "endpoints use Holm's method at a 1% level; maintenance endpoints are tested sequentially at 4%.",
        "SAP", "Section 6.6.1 Multiple testing procedure",
    ),
    "NCT03160885": (  # ECZTRA 2 (same modified hierarchy as ECZTRA 1)
        "US submission: the same dedicated modified confirmatory testing hierarchy as ECZTRA 1 -- IGA "
        "0/1, then EASI-75, then Pruritus vs. placebo at Week 16 (5% each, sequential); if all three are "
        "significant, alpha splits between 2 Week-16 secondary endpoints (1%, Holm-adjusted) and 2 "
        "maintenance endpoints at Week 52 (4%, sequential), with alpha-recycling between groups.",
        "SAP", "Section 6.6.1 Multiple testing procedure",
    ),
    "NCT03363854": (  # ECZTRA 3 (add-on with TCS, same hierarchy family)
        "US submission: a dedicated modified confirmatory testing hierarchy analogous to ECZTRA 1/2 -- "
        "primary and secondary endpoints for tralokinumab + TCS vs. placebo + TCS tested in a "
        "prespecified sequential order (IGA 0/1, then EASI-75, then Pruritus) at Week 16, with "
        "maintenance-period endpoints tested in a separate branch.",
        "SAP", "Section 6.6.1 Multiple testing procedure",
    ),
    "NCT03568318": (  # AD Up
        "Overall Type-I error for the primary and secondary endpoints (upadacitinib 15 mg and 30 mg vs. "
        "placebo, both + background TCS) is strongly controlled via a graphical multiple testing "
        "procedure (2-sided alpha 0.05) with a pre-specified alpha transfer path, including downstream "
        "transfer along the endpoint sequence within each dose and cross-dose transfer. Separate graphs "
        "are specified for EU/EMA and US/FDA submissions.",
        "SAP", "Section 4.6 Overall Type-I Error Control",
    ),
    "NCT03569293": (  # Measure Up 1
        "Overall Type-I error for the primary and secondary endpoints (upadacitinib 15 mg and 30 mg vs. "
        "placebo) is strongly controlled via a graphical multiple testing procedure (2-sided alpha 0.05) "
        "with a pre-specified alpha transfer path, including downstream transfer along the endpoint "
        "sequence within each dose and cross-dose transfer. Once an endpoint is rejected, its "
        "significance level transfers to subsequent endpoints per the graph. Separate graphs for EU/EMA "
        "and US/FDA.",
        "SAP", "Section 13.0 Overall Type-I Error Control",
    ),
    "NCT03607422": (  # Measure Up 2 (identical statistical design to Measure Up 1)
        "Same design as Measure Up 1: overall Type-I error for the primary and secondary endpoints "
        "(upadacitinib 15 mg and 30 mg vs. placebo) is strongly controlled via a graphical multiple "
        "testing procedure (2-sided alpha 0.05) with a pre-specified alpha transfer path including "
        "downstream and cross-dose transfer. Separate graphs for EU/EMA and US/FDA.",
        "SAP", "Section 13.0 Overall Type-I Error Control",
    ),
    "NCT03349060": (  # JADE MONO-1
        "A sequential Bonferroni-based iterative multiple testing procedure strongly controls familywise "
        "Type I error at 5% across the two abrocitinib doses (100/200 mg QD) vs. placebo on primary and "
        "key secondary endpoints. Testing starts with the Week 12 co-primary endpoints (IGA, EASI-75) for "
        "200 mg vs. placebo at 5%; if rejected, testing proceeds down one of two alpha-dependent paths "
        "keyed on the Week 2 Pruritus NRS-4 result for 200 mg vs. placebo (tested at 2.5%), each path "
        "carrying its own significance level into a further sequence of endpoint tests.",
        "SAP", "Multiple Testing Procedure (Figure 2 schematic)",
    ),
    "NCT03575871": (  # JADE MONO-2 (identical statistical design to MONO-1)
        "Same design as JADE MONO-1: a sequential Bonferroni-based iterative multiple testing procedure "
        "strongly controls familywise Type I error at 5% across the two abrocitinib doses vs. placebo on "
        "primary and key secondary endpoints, starting with the Week 12 co-primary endpoints (IGA, "
        "EASI-75) for 200 mg vs. placebo, then branching on the Week 2 Pruritus NRS-4 result.",
        "SAP", "Multiple Testing Procedure (Figure 2 schematic)",
    ),
    "NCT03627767": (  # JADE REGIMEN
        "Six key hypotheses (primary + key secondary endpoint, x 2 doses vs. placebo, x the 200 mg-vs-100 "
        "mg comparison) are tested with the familywise Type-I error strongly controlled at 5% via a "
        "sequential gatekeeping procedure: 200 mg vs. placebo primary endpoint first, then its key "
        "secondary; then 100 mg vs. placebo primary, then its key secondary; then 200 mg vs. 100 mg "
        "primary, then its key secondary -- each step gated on the previous hypothesis being rejected.",
        "SAP", "Section 5.1 Hypotheses and Decision Rules",
    ),
    "NCT03720470": (  # JADE COMPARE
        "The familywise Type-I error rate for the co-primary and key secondary endpoints (abrocitinib "
        "100/200 mg vs. placebo) is strongly controlled at 5% (two-sided) using a closed-testing method "
        "based on a sequential, iterative Bonferroni-type approach (dupilumab arm is an active comparator, "
        "not part of the formal multiplicity-controlled hierarchy).",
        "SAP", "Section on Type-I error control (Sample Size/Power)",
    ),
    "NCT04146363": (  # ADvocate1
        "A prespecified graphical multiple testing approach (Bretz 2011, a closed testing procedure) "
        "controls the overall Type I error at 2-sided alpha 0.05 for the primary and major secondary "
        "endpoints. For FDA, IGA 0/1 is tested first, then major secondary endpoints. For EMA, IGA 0/1 "
        "and EASI-75 at Week 16 form a primary endpoint family tested sequentially before major secondary "
        "endpoints; a separate graph may apply to maintenance-period endpoints. Exact testing order/alpha "
        "allocation is finalized in the SAP before unblinding.",
        "Prot", "Section 9.6 Multiplicity Considerations",
    ),
    "NCT04178967": (  # ADvocate2
        "FDA objective: a prespecified graphical multiple testing approach (Bretz et al. 2009, 2011), a "
        "closed testing procedure controlling family-wise error, tests IGA 0/1 at Week 16 first, then a "
        "list of major secondary endpoints (EASI-75, EASI-90, Pruritus NRS-4 at Weeks 16/4/2, IGA 0/1 at "
        "Week 4, IGA 0/1 in adults at Week 16, Sleep-loss at Week 16) via a directed alpha-transfer graph.",
        "SAP", "Section 6.6.1 Multiplicity Control for FDA",
    ),
    "NCT04250337": (  # ADhere
        "US submission: a prespecified graphical multiple testing approach (Bretz 2009, 2011) with a "
        "gatekeeping structure controls the overall Type I error at 2-sided alpha 0.05 across the primary "
        "and major secondary endpoints, tested in sequential order: (1) IGA 0/1 at Week 16, (2) EASI-75 at "
        "Week 16, (3) Pruritus NRS-4 at Week 16, (4) combined EASI-75 & Pruritus NRS-4 at Week 16, (5) "
        "EASI-90 at Week 16.",
        "SAP", "Section 6.6.1 Multiplicity Control for US Submission",
    ),
}


# Trials where the combination-therapy background regimen isn't stated as a
# single quotable eligibility-criteria sentence or a separate TCS
# intervention entry, but is confirmed in the Study Protocol body text.
BACKGROUND_THERAPY_PDF = {
    "NCT03363854": (  # ECZTRA 3 (tralokinumab + TCS combination design)
        "Tralokinumab (or placebo) is given in combination with a background topical "
        "corticosteroid (TCS) regimen throughout the study; all subjects, including "
        "those re-randomized into the maintenance continuation period, stay on the TCS "
        "regimen.",
        "Prot", "Continuation treatment period narrative (\"All subjects will stay on the TCS regimen\")",
    ),
}



def _refuse_v2(record, path):
    if record.get("schema_version") == 2:
        raise SystemExit(
            f"{path.name} is already schema v2 (structured values); this v1-stage script only edits v1 "
            "records. Re-run scripts/fetch_trials.py to rebuild the v1 baseline, then stages 2-4, then "
            "scripts/migrate_v1_to_v2.py -- see README 'Running the pipeline'.")

def main():
    fda_cache = {}
    trial_files = sorted(TRIALS_DIR.glob("*.json"))
    for tf in trial_files:
        record = json.loads(tf.read_text())
        _refuse_v2(record, tf)
        nct_id = record["nct_id"]["value"]
        drug = record["molecule"]["drug"]["value"]
        raw = fetch_full_study(nct_id)
        ctgov_url = f"{CTGOV_API}/{nct_id}"
        docs = raw.get("documentSection", {}).get("largeDocumentModule", {}).get("largeDocs", [])

        elig_criteria = raw["protocolSection"].get("eligibilityModule", {}).get("eligibilityCriteria", "")
        sev, bg = extract_severity_and_bg(elig_criteria, ctgov_url)
        if sev:
            record["population"]["severity_definition"] = sev
        if not bg:
            bg = extract_bg_from_tcs_arm(raw, ctgov_url)
        if not bg and nct_id in BACKGROUND_THERAPY_PDF:
            text, doc_type, section = BACKGROUND_THERAPY_PDF[nct_id]
            fname = next(d["filename"] for d in docs if d.get("typeAbbrev") == doc_type)
            bg = field(text, "protocol_pdf_extraction",
                       f"{CDN_BASE}/{nct_id[-2:]}/{nct_id}/{fname}", section, confidence=0.7)
        if bg:
            record["design"]["background_therapy_rule"] = bg

        dosing = extract_dosing(raw, drug, ctgov_url)
        if dosing:
            record["molecule"]["dosing_regimen"] = dosing

        if drug not in fda_cache:
            fda_cache[drug] = fda_setid(drug)
        fda_result = fda_cache[drug]
        if fda_result:
            moa_list = fda_result.get("mechanism_of_action")
            if moa_list:
                setid = fda_result.get("id")
                url = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}"
                record["molecule"]["mechanism_of_action"] = field(
                    moa_list[0], "openfda_label", url,
                    "openFDA drug/label mechanism_of_action (FDA-approved label, section 12.1)",
                    confidence=0.9,
                )

        has_prot = any(d.get("hasProtocol") for d in docs)
        has_sap = any(d.get("hasSap") for d in docs)

        if nct_id in RESCUE_RULES:
            text, doc_type, section = RESCUE_RULES[nct_id]
            fname = next(d["filename"] for d in docs if d.get("typeAbbrev") == doc_type)
            url = f"{CDN_BASE}/{nct_id[-2:]}/{nct_id}/{fname}"
            record["timing_ops"]["rescue_therapy_rules"] = field(
                text, "protocol_pdf_extraction", url, section, confidence=0.75
            )

        if nct_id in MULTIPLICITY_RULES:
            text, doc_type, section = MULTIPLICITY_RULES[nct_id]
            fname = next(d["filename"] for d in docs if d.get("typeAbbrev") == doc_type)
            url = f"{CDN_BASE}/{nct_id[-2:]}/{nct_id}/{fname}"
            record["endpoints"]["endpoint_hierarchy_multiplicity"] = field(
                text, "protocol_pdf_extraction", url, section, confidence=0.75
            )

        tf.write_text(json.dumps(record, indent=2) + "\n")
        print(f"{nct_id}: enriched (prot={has_prot}, sap={has_sap})")


if __name__ == "__main__":
    main()
