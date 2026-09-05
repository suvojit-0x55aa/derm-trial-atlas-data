#!/usr/bin/env python3
"""
Fourth-pass extraction: full-text journal publications and FDA approval-
package reviews, for the fields that CT.gov's own free text and posted
protocol/SAP PDFs did not cover.

Why this exists: per-trial primary result papers are almost all paywalled,
and every publisher/repository host tried (NEJM, Wiley, JAMA Network,
JAAD/Elsevier, a university repository mirror) sits behind a Cloudflare
bot-challenge -- one of them escalates to an interactive "Verify you are
human" Turnstile CAPTCHA, which this pipeline will not solve (defeating an
anti-bot check to scrape paywalled content is not something this project
does, task framing aside). PMC and Unpaywall were checked for every
primary-publication PMID/DOI (see the PMC/Unpaywall lookup notes in
AGENTS.md); PMC had free full text for 4 papers, fetched here. For the
gaps that full-text access still left, FDA Drugs@FDA approval-package
Medical/Multi-Discipline Reviews (accessdata.fda.gov, not behind
Cloudflare) turned out to carry more granular protocol detail --
rescue-therapy algorithms, exact visit schedules, background-therapy
regimens, endpoint testing hierarchies -- than the journal papers
themselves would have.

Every excerpt below was read and hand-selected from the source documents
listed in each entry's `source_url` (the source_type is "publication_extraction",
a new source_type covering both PMC full-text papers and FDA review PDFs;
distinct from `protocol_pdf_extraction`, which is CT.gov-linked
protocol/SAP PDFs). Like RESCUE_RULES/MULTIPLICITY_RULES/BACKGROUND_THERAPY_PDF
in enrich_needs_extraction.py, these are hand-curated (not live-parsed at
runtime) because the underlying PDFs/XML are large and the excerpt
selection required judgment; the raw source files are cached under
data/_raw_cache/papers/ (gitignored) for anyone who wants to re-verify an
excerpt against the source.

Fields intentionally NOT filled here (left needs_extraction) after real
effort, and why:
  - CAFE (NCT02755649), all 6 remaining fields: no PMC entry for its paper
    (PMID 29193016), Unpaywall found no OA location, and it falls between
    the original 2017 Dupixent approval package (predates CAFE, which
    completed 2017-03-31) and the next FDA supplement checked (SUPPL 7,
    2018-10-19, does not mention CAFE or cyclosporine either).
  - JADE MONO-1 (NCT03349060) and JADE COMPARE (NCT03720470)
    rescue_therapy_rules: the abrocitinib NDA 213871 Multi-Discipline
    Review discusses rescue medication's *statistical handling* for these
    trials but never states the protocol-level rescue algorithm itself
    (unlike JADE MONO-2, where an explicit "rescue medication was
    prohibited" eligibility-criteria quote exists in its own PMC paper).
  - JADE REGIMEN (NCT03627767) background_therapy_rule and visit_schedule:
    this is a randomized-withdrawal design (open-label run-in, then
    randomized withdrawal to rescue), structurally different from the
    other trials' parallel-group designs; NDA 213871's review covers it
    only in a one-line summary table (it was still "ONGOING" at that
    review's cutoff) with no detailed design section to extract from.

Run after scripts/enrich_needs_extraction.py and scripts/fetch_adverse_events.py:
    python3 scripts/enrich_publications.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_DIR = ROOT / "data" / "trials"

EXTRACTED_BY = "enrich_publications.py (publication_extraction: PMC full text / FDA approval-package review, v1 pass; pending human QA)"


def field(value, url, source_excerpt, confidence=0.75):
    return {
        "value": value,
        "source_type": "publication_extraction",
        "source_url": url,
        "source_excerpt": source_excerpt,
        "extracted_by": EXTRACTED_BY,
        "reviewed_by": None,
        "confidence": confidence,
    }


def load(nct):
    p = TRIALS_DIR / f"{nct}.json"
    record = json.loads(p.read_text())
    if record.get("schema_version") == 2:
        raise SystemExit(
            f"{p.name} is already schema v2 (structured values); this v1-stage script only edits v1 "
            "records. Re-run scripts/fetch_trials.py to rebuild the v1 baseline, then stages 2-4, then "
            "scripts/migrate_v1_to_v2.py -- see README 'Running the pipeline'.")
    return p, record


def save(p, d):
    p.write_text(json.dumps(d, indent=2) + "\n")


def set_if_needs_extraction(d, group, key, value):
    """Never overwrite a field that already has real data -- only promote
    an actual needs_extraction gap."""
    if d[group][key]["source_type"] == "needs_extraction":
        d[group][key] = value
        return True
    return False


# ---------------------------------------------------------------------------
# Dupilumab -- FDA Medical Review, BLA 761055 (original 2017 approval;
# covers SOLO 1 / SOLO 2 / CHRONOS. CAFE completed after this review and is
# not covered -- see module docstring.)
# ---------------------------------------------------------------------------
DUPI_URL = "http://www.accessdata.fda.gov/drugsatfda_docs/nda/2017/761055Orig1s000MedR.pdf"

RESCUE_1334 = (
    "Rescue treatment for AD could be given at investigator discretion if needed to control "
    "intolerable symptoms. Topical rescue medications did not require study drug discontinuation; "
    "TCI could be used for rescue but were reserved for problem areas (face, neck, intertriginous, "
    "genital areas). Investigators were to limit the first step of rescue to topical medications, "
    "escalating to systemic medications only after >=7 days of inadequate response to topical "
    "treatment. Rescue with systemic corticosteroids or non-steroidal systemic immunosuppressants "
    "(cyclosporine, methotrexate, mycophenolate mofetil, azathioprine, etc.) required immediate "
    "discontinuation of study drug, which could resume no sooner than 5 half-lives after the last "
    "dose of rescue medication."
)
HIERARCHY_1334 = (
    "Hierarchical (serial gatekeeping) testing procedure at the 2-sided alpha=0.025 level per dose "
    "regimen: co-primary endpoints (IGA 0/1 with >=2-point reduction from baseline, and EASI-75) at "
    "Week 16 tested first; if both were statistically significant, a pre-specified ordered sequence "
    "of secondary endpoints was tested with multiplicity controlled via the gatekeeping procedure. "
    "A patient who received rescue medication was counted as a non-responder from the time rescue "
    "was used."
)
VISIT_1334 = (
    "16-week randomized treatment period (35-day screening washout beforehand) with weekly study "
    "drug administration; study visits were weekly during the 16-week treatment period. End-of-"
    "treatment visit at Week 16 (primary endpoint assessed at Week 16). Subjects meeting response "
    "criteria who did not use rescue treatment could continue into a maintenance study; others "
    "underwent >=4 weeks of follow-up through Week 20, then either entered an open-label extension "
    "or were followed every 4 weeks from Week 20 through Week 28 (a 28-week total trial duration for "
    "non-continuers). Not a full per-visit assessment table -- visit-level lab/assessment detail is "
    "not itemized in this source."
)
BACKGROUND_1334 = (
    "Monotherapy design. Prohibited concomitant medications/procedures during the study: live "
    "(attenuated) vaccines, immunomodulating biologics, other investigational drugs, TCS or TCI, and "
    "systemic corticosteroids or non-steroidal systemic immunosuppressive drugs. Subjects were "
    "required to apply moisturizers/emollients twice daily throughout the study."
)
SEC_1334 = 'Section 6.1 "R668-AD-1334 (1334); SOLO 1"'
SEC_1416 = 'Section 6.2 "R668-AD-1416 (1416); SOLO 2" -- "This study was identical in design to 1334; see 6.1"'

RESCUE_1224 = (
    "After Week 2, subjects needing rescue for intolerable symptoms could receive any approved AD "
    "treatment in a staged fashion using a greater treatment intensity. TCS rescue after Week 2 did "
    "not require study drug discontinuation (mometasone 0.1% ointment recommended for high potency; "
    "betamethasone dipropionate 0.05% or clobetasol propionate 0.05% for super-high potency). Rescue "
    "with a systemic immunosuppressant, systemic corticosteroids, or phototherapy required stopping "
    "study drug, restartable ~5 half-lives after systemic rescue (1 month after phototherapy). "
    "Subjects who discontinued study drug for rescue remained in the study for all visits/assessments "
    "and were counted as treatment failures. Rescue treatment was prohibited during the first 2 weeks."
)
HIERARCHY_1224 = (
    "Co-primary endpoint: proportion with IGA 0/1 and >=2-point reduction from baseline at Week 16. "
    "If both co-primary endpoints were statistically significant (2-sided alpha=0.025), a pre-"
    "specified ordered sequence of secondary endpoints (EASI-75 at Week 16; pruritus NRS improvement "
    ">=4 and >=3 from baseline to Week 16; IGA 0/1 with >=2-point reduction at Week 52; EASI-75 at "
    "Week 52; percent change in weekly average peak pruritus NRS to Week 16; pruritus NRS improvement "
    ">=4 and >=3 to Week 52; and further safety-related endpoints through Week 56) was tested with a "
    "serial gatekeeping procedure to control the overall Type I error rate."
)
VISIT_1224 = (
    "64-week trial: 52-week treatment period (with TCS background regimen from Day 1) plus a 12-week "
    "post-treatment follow-up. End-of-treatment visit at Week 52 (1 week after last dose); end-of-"
    "study visit at Week 64. Subjects completing the study could enroll in an open-label extension "
    "(study 1225). Not a full per-visit assessment table -- visit-level lab/assessment detail is not "
    "itemized in this source."
)
SEC_1224 = 'Section 6.3 "R668-AD-1224 (1224); CHRONOS"'

SEVERITY_CHRONOS = (
    "By cross-reference to studies 1334/1416 (SOLO 1/SOLO 2): EASI Score >=16 at screening and "
    "baseline; Investigator's Global Assessment (IGA) Score >=3 (0-4 scale, 3=moderate, 4=severe) at "
    "screening and baseline; >=10% body surface area (BSA) of AD involvement at screening and "
    "baseline."
)


def enrich_dupilumab():
    p, d = load("NCT02277743")  # SOLO 1
    set_if_needs_extraction(d, "timing_ops", "rescue_therapy_rules", field(RESCUE_1334, DUPI_URL, SEC_1334 + ', "Rescue Treatment"'))
    set_if_needs_extraction(d, "endpoints", "endpoint_hierarchy_multiplicity", field(HIERARCHY_1334, DUPI_URL, SEC_1334 + ' (Statistical Analysis Plan discussion, applies to "both trials" 1334 and 1416)'))
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(VISIT_1334, DUPI_URL, SEC_1334 + ', "Trial Design" / "Rescue Treatment"', confidence=0.7))
    set_if_needs_extraction(d, "design", "background_therapy_rule", field(BACKGROUND_1334, DUPI_URL, SEC_1334 + ', "Prohibited Medications and Procedures"'))
    save(p, d)

    p, d = load("NCT02277769")  # SOLO 2
    set_if_needs_extraction(d, "timing_ops", "rescue_therapy_rules", field(RESCUE_1334, DUPI_URL, SEC_1416))
    set_if_needs_extraction(d, "endpoints", "endpoint_hierarchy_multiplicity", field(HIERARCHY_1334, DUPI_URL, SEC_1416 + ' (SAP discussion explicitly covers "both trials" 1334 and 1416)'))
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(VISIT_1334, DUPI_URL, SEC_1416, confidence=0.7))
    set_if_needs_extraction(d, "design", "background_therapy_rule", field(BACKGROUND_1334, DUPI_URL, SEC_1416))
    save(p, d)

    p, d = load("NCT02260986")  # CHRONOS
    set_if_needs_extraction(d, "timing_ops", "rescue_therapy_rules", field(RESCUE_1224, DUPI_URL, SEC_1224 + ', "Rescue Medications"'))
    set_if_needs_extraction(d, "endpoints", "endpoint_hierarchy_multiplicity", field(HIERARCHY_1224, DUPI_URL, SEC_1224 + ', "Statistical Analysis Plan"'))
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(VISIT_1224, DUPI_URL, SEC_1224 + ', "Trial Design" / "Rescue Medications"', confidence=0.7))
    set_if_needs_extraction(d, "population", "severity_definition", field(
        SEVERITY_CHRONOS, DUPI_URL,
        'Section 6.3.2 "Eligibility Criteria" / "Inclusion Criteria": "Disease criteria were the same as for studies 1334 and 1416." (SOLO 1 / SOLO 2)',
        confidence=0.7,
    ))
    save(p, d)


# ---------------------------------------------------------------------------
# Tralokinumab -- FDA Integrated Review, BLA 761180 (covers ECZTRA-1/2/3)
# ---------------------------------------------------------------------------
TRALO_URL = "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2022/761180Orig1s000IntegratedR.pdf"
TRALO_SEC = 'Section 6.2.1 "Trial Design"'

ECZTRA12_VISIT = (
    "16-week initial treatment period (Week 0-16), 36-week maintenance treatment period (Week "
    "16-52), 16-week off-treatment safety follow-up (Week 52-66). \"Subjects had clinic visits at "
    "baseline, screening, and every other week thereafter until Week 52. A follow-up visit was "
    "conducted at Week 66.\" Not a full per-visit assessment table."
)
ECZTRA12_BG = (
    "None -- monotherapy design: \"two identically designed... Phase 3 trials (ECZTRA-1 and "
    "ECZTRA-2) to evaluate the efficacy and safety of tralokinumab monotherapy in adult subjects "
    "with moderate-to-severe atopic dermatitis whose disease is not adequately controlled with "
    "topical prescription therapies or when those therapies are not advisable.\""
)
ECZTRA3_VISIT = (
    "16-week initial treatment period (Week 0-16), 16-week continuation treatment period (Week "
    "16-32), 14-week off-treatment follow-up (Week 32-46). Trial design text also states \"clinic "
    "visits at baseline, screening, and every other week thereafter until Week 52. A follow-up "
    "visit was conducted at Week 66\" -- this appears to reuse ECZTRA-1/2 boilerplate inconsistent "
    "with ECZTRA-3's own stated Week 46 endpoint; quoted as written, not reconciled. Not a full "
    "per-visit assessment table."
)


def enrich_tralokinumab():
    for nct, label in [("NCT03131648", "ECZTRA-1"), ("NCT03160885", "ECZTRA-2")]:
        p, d = load(nct)
        set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(ECZTRA12_VISIT, TRALO_URL, TRALO_SEC + f" ({label})", confidence=0.7))
        set_if_needs_extraction(d, "design", "background_therapy_rule", field(ECZTRA12_BG, TRALO_URL, TRALO_SEC + f" ({label})"))
        save(p, d)

    p, d = load("NCT03363854")  # ECZTRA-3
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(ECZTRA3_VISIT, TRALO_URL, TRALO_SEC + " (ECZTRA-3)", confidence=0.6))
    save(p, d)


# ---------------------------------------------------------------------------
# Abrocitinib -- FDA Multi-Discipline Review, NDA 213871 (JADE MONO-1/2,
# JADE COMPARE; JADE REGIMEN/B7451014 was still "ONGOING" at this review's
# cutoff and has no detailed design section -- see module docstring)
# ---------------------------------------------------------------------------
ABRO_URL = "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2022/213871Orig1s000MultidisciplineR.pdf"
ABRO_SEC = 'Section 8.1.1 "Trial Design"'

JADEMONO_VISIT = (
    "Screening period (28 days), 12-week placebo-controlled double-blind treatment period, 4-week "
    "follow-up period (for subjects not entering the long-term extension). \"Subjects had on-site "
    "visits at screening, baseline (Week 0) and Weeks 2, 4, 8, 12 and 16 (follow-up visit). Subjects "
    "were also contacted via phone calls at Weeks 1 and 6.\""
)
JADEMONO_BG = (
    "None -- monotherapy design: \"Trials B7451012 and B7451013 were monotherapy trials in "
    "adolescents and adults\", randomized double-blind placebo-controlled evaluating abrocitinib "
    "monotherapy."
)
JADECOMPARE_VISIT = (
    "Screening period (28 days), 20-week treatment period, 4-week follow-up. First 16 weeks: "
    "randomized double-blind double-dummy period (abrocitinib + dupilumab-matching placebo vs. "
    "dupilumab + abrocitinib-matching placebo vs. double placebo). Injectable dupilumab/placebo "
    "stopped at Week 16 (final dose Week 14, for washout); Weeks 16-20 continued blinded on oral "
    "product only. Key secondary endpoints measured at Weeks 2 and 16; primary endpoint at Week 12. "
    "Not a full per-visit assessment table."
)


def enrich_abrocitinib():
    p, d = load("NCT03349060")  # JADE MONO-1 = B7451012
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(JADEMONO_VISIT, ABRO_URL, ABRO_SEC + " (Trial B7451012 / JADE MONO-1)"))
    set_if_needs_extraction(d, "design", "background_therapy_rule", field(JADEMONO_BG, ABRO_URL, ABRO_SEC + " (Trial B7451012 / JADE MONO-1)"))
    save(p, d)

    p, d = load("NCT03575871")  # JADE MONO-2 = B7451013 (background/rescue already filled from its own PMC paper)
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(JADEMONO_VISIT, ABRO_URL, ABRO_SEC + " (Trial B7451013 / JADE MONO-2, identically designed to B7451012)"))
    save(p, d)

    p, d = load("NCT03720470")  # JADE COMPARE = B7451029
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(JADECOMPARE_VISIT, ABRO_URL, ABRO_SEC + " (Trial B7451029 / JADE COMPARE)", confidence=0.7))
    save(p, d)


# ---------------------------------------------------------------------------
# Upadacitinib -- FDA Multi-disciplinary Review, NDA 211675/S-004 (Rinvoq AD
# indication supplement; covers Measure Up 1/2 and AD Up)
# ---------------------------------------------------------------------------
UPA_URL = "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2024/211675Orig1s004.pdf"
UPA_SEC = 'Section 8.1.1 "Trial Design"'

MEASUREUP_VISIT = (
    "35-day screening period, 16-week double-blind treatment period, long-term blinded extension to "
    "Week 136, 30-day follow-up visit. \"Subjects were scheduled to have the following study visits: "
    "screening, baseline (Day 1), and Weeks 1, 2, 4, 8, 12, 16, 20, 24, 32, 40, 52, and every 12 "
    "weeks until Week 136.\""
)
MEASUREUP_BG = (
    "None -- monotherapy design: \"Trials M16-045 and M18-891 were identically designed monotherapy "
    "trials\", randomized double-blind placebo-controlled evaluating upadacitinib 15/30 mg "
    "monotherapy."
)
ADUP_VISIT = (
    "35-day screening period, 16-week double-blind treatment period (with protocol-mandated TCS "
    "background regimen), long-term blinded extension to Week 136, 30-day follow-up visit. "
    "\"Subjects were scheduled to have the following study visits: screening, baseline (Day 1), and "
    "Weeks 1, 2, 4, 8, 12, 16, 20, 24, 32, 40, 52, and every 12 weeks until Week 136.\""
)


def enrich_upadacitinib():
    p, d = load("NCT03569293")  # Measure Up 1 = M16-045
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(MEASUREUP_VISIT, UPA_URL, UPA_SEC + " (Trial M16-045 / Measure Up 1)"))
    set_if_needs_extraction(d, "design", "background_therapy_rule", field(MEASUREUP_BG, UPA_URL, UPA_SEC + " (Trial M16-045 / Measure Up 1)"))
    save(p, d)

    p, d = load("NCT03607422")  # Measure Up 2 = M18-891
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(MEASUREUP_VISIT, UPA_URL, UPA_SEC + " (Trial M18-891 / Measure Up 2, identically designed to M16-045)"))
    set_if_needs_extraction(d, "design", "background_therapy_rule", field(MEASUREUP_BG, UPA_URL, UPA_SEC + " (Trial M18-891 / Measure Up 2, identically designed to M16-045)"))
    save(p, d)

    p, d = load("NCT03568318")  # AD Up = M16-047
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(ADUP_VISIT, UPA_URL, UPA_SEC + " (Trial M16-047 / AD Up)"))
    save(p, d)


# ---------------------------------------------------------------------------
# Lebrikizumab -- FDA Multi-disciplinary Review, BLA 761306 (ADvocate 1/2,
# ADhere)
# ---------------------------------------------------------------------------
LEBRI_URL = "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2024/761306Orig1s000MultidisciplineR.pdf"
LEBRI_SEC = 'Section 8 "Review of Relevant Individual Trials... Studies KGAB (ADvocate 1), KGAC (ADvocate 2), and KGAD (ADhere)", "Trial Design"'

ADVOCATE_VISIT = (
    "16-week induction treatment period followed by a 36-week long-term maintenance treatment "
    "period (52 weeks total treatment). Primary endpoint (IGA 0/1 with >=2-pt reduction, and "
    "EASI-75) assessed at Week 16; responders re-randomized at Week 16 to lebrikizumab Q2W, Q4W, or "
    "placebo for maintenance, with maintenance-response checks at Weeks 24, 32, 40, 48. Not a full "
    "per-visit assessment table -- exact interim visit weeks are not itemized in this source."
)
ADVOCATE_BG = (
    "None -- monotherapy design: \"Studies KGAB and KGAC were two phase 3 randomized, double-blind, "
    "placebo-controlled, and parallel group studies sharing an identical study design... to evaluate "
    "the efficacy and safety of lebrikizumab as a monotherapy for moderate-to-severe AD.\""
)
ADHERE_VISIT = (
    "16-week, randomized, double-blind, placebo-controlled, parallel-group study evaluating "
    "lebrikizumab in combination with topical corticosteroid (TCS) treatment vs. placebo+TCS. "
    "Primary endpoint (IGA 0/1 with >=2-pt reduction, and EASI-75) assessed at Week 16. Not a full "
    "per-visit assessment table -- exact interim visit weeks are not itemized in this source."
)


def enrich_lebrikizumab():
    for nct, label in [("NCT04146363", "KGAB / ADvocate 1"), ("NCT04178967", "KGAC / ADvocate 2")]:
        p, d = load(nct)
        set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(ADVOCATE_VISIT, LEBRI_URL, LEBRI_SEC + f" ({label})", confidence=0.65))
        set_if_needs_extraction(d, "design", "background_therapy_rule", field(ADVOCATE_BG, LEBRI_URL, LEBRI_SEC + f" ({label})"))
        save(p, d)

    p, d = load("NCT04250337")  # ADhere = KGAD
    set_if_needs_extraction(d, "timing_ops", "visit_schedule", field(ADHERE_VISIT, LEBRI_URL, LEBRI_SEC + " (KGAD / ADhere)", confidence=0.6))
    save(p, d)


# ---------------------------------------------------------------------------
# JADE MONO-2 -- its own PMC full-text paper (Silverberg et al 2020, JAMA
# Dermatol, PMID 32492087 / PMC7271424): explicit eligibility-criteria quote
# that rescue medication and concomitant AD therapy were prohibited.
# ---------------------------------------------------------------------------
JADEMONO2_PMC_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC7271424/"
JADEMONO2_QUOTE = (
    '"Concomitant use of topical (corticosteroids, calcineurin inhibitors, tars, antibiotic '
    'creams, or topical antihistamines) or systemic therapies for AD or rescue medication was '
    'prohibited. Patients were permitted to use oral antihistamines and topical nonmedicated '
    'emollients."'
)


def enrich_jademono2():
    p, d = load("NCT03575871")
    set_if_needs_extraction(d, "timing_ops", "rescue_therapy_rules", field(
        "No rescue medication provision: concomitant topical or systemic AD therapy and rescue "
        "medication were prohibited under the protocol (monotherapy design). Only oral "
        "antihistamines and topical nonmedicated emollients were permitted.",
        JADEMONO2_PMC_URL, "Methods, Study Design and Treatment: " + JADEMONO2_QUOTE,
    ))
    set_if_needs_extraction(d, "design", "background_therapy_rule", field(
        "None -- monotherapy design; concomitant topical (corticosteroids, calcineurin inhibitors, "
        "tars, antibiotic creams, topical antihistamines) and systemic AD therapies were prohibited.",
        JADEMONO2_PMC_URL, "Methods, Study Design and Treatment: " + JADEMONO2_QUOTE,
    ))
    save(p, d)


# ---------------------------------------------------------------------------
# Tralokinumab adverse_events.discontinuation_due_to_ae_rate -- from the same
# 2 PMC papers, Table 6 (ECZTRA-1/2) and Table 3 (ECZTRA-3), which give a
# clean per-arm discontinuation-due-to-AE count that CT.gov's own posted
# dropout taxonomy didn't break out (see fetch_adverse_events.py docstring).
# ---------------------------------------------------------------------------
ECZTRA12_PMC_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC7986411/"
ECZTRA12_TABLE = (
    'Table 6, "16-week initial treatment period, safety analysis set": "Leading to permanent '
    'discontinuation of IMP" row'
)
ECZTRA3_PMC_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC7986183/"
ECZTRA3_TABLE = (
    'Table 3, "16-week initial treatment period, safety analysis set": "Leading to discontinuation '
    'of IMP" row (Placebo Q2W+TCS N=126; Tralokinumab Q2W+TCS N=252)'
)


def enrich_tralokinumab_ae():
    p, d = load("NCT03131648")  # ECZTRA-1
    set_if_needs_extraction(d, "adverse_events", "discontinuation_due_to_ae_rate", field(
        [
            {"arm": "Placebo", "n_discontinued": 8, "n_started": 196, "pct": 4.1},
            {"arm": "Tralokinumab Q2W", "n_discontinued": 20, "n_started": 602, "pct": 3.3},
        ],
        ECZTRA12_PMC_URL, ECZTRA12_TABLE + " (ECZTRA 1 columns)",
    ))
    save(p, d)

    p, d = load("NCT03160885")  # ECZTRA-2
    set_if_needs_extraction(d, "adverse_events", "discontinuation_due_to_ae_rate", field(
        [
            {"arm": "Placebo", "n_discontinued": 3, "n_started": 200, "pct": 1.5},
            {"arm": "Tralokinumab Q2W", "n_discontinued": 9, "n_started": 592, "pct": 1.5},
        ],
        ECZTRA12_PMC_URL, ECZTRA12_TABLE + " (ECZTRA 2 columns)",
    ))
    save(p, d)

    p, d = load("NCT03363854")  # ECZTRA-3
    set_if_needs_extraction(d, "adverse_events", "discontinuation_due_to_ae_rate", field(
        [
            {"arm": "Placebo Q2W + TCS", "n_discontinued": 1, "n_started": 126, "pct": 0.8},
            {"arm": "Tralokinumab Q2W + TCS", "n_discontinued": 6, "n_started": 252, "pct": 2.4},
        ],
        ECZTRA3_PMC_URL, ECZTRA3_TABLE,
    ))
    save(p, d)


def main():
    enrich_dupilumab()
    enrich_tralokinumab()
    enrich_tralokinumab_ae()
    enrich_abrocitinib()
    enrich_upadacitinib()
    enrich_lebrikizumab()
    enrich_jademono2()
    print("Publication-extraction pass applied.")


if __name__ == "__main__":
    main()
