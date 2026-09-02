# Open Derm Trial Atlas — Data Pipeline (v1)

Data-backend pipeline for the Open Derm Trial Atlas: structured, sourced
trial-design and safety data for atopic dermatitis (AD) drug trials. This
repo is the data backend only — fetch, extraction, and build scripts all
live here in `scripts/`. The portal UI (`superderma.ai/atlas`) lives in a
separate repo (`kolai-website`) and is not part of this pipeline.

## What v1 covers

Real, live-pulled pivotal Phase III trials (adult / adult+adolescent,
systemic therapy) for 5 drugs, from the [ClinicalTrials.gov API
v2](https://clinicaltrials.gov/data-api/api) (`/api/v2/studies`, no API
key required):

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | SOLO 1 (NCT02277743), SOLO 2 (NCT02277769), CHRONOS (NCT02260986), CAFE (NCT02755649) |
| Lebrikizumab | ADvocate1 (NCT04146363), ADvocate2 (NCT04178967), ADhere (NCT04250337) |
| Tralokinumab | ECZTRA 1 (NCT03131648), ECZTRA 2 (NCT03160885), ECZTRA 3 (NCT03363854) |
| Abrocitinib | JADE MONO-1 (NCT03349060), JADE MONO-2 (NCT03575871), JADE COMPARE (NCT03720470), JADE REGIMEN (NCT03627767) |
| Upadacitinib | Measure Up 1 (NCT03569293), Measure Up 2 (NCT03607422), AD Up (NCT03568318) |

17 trials total. Every NCT ID above was pulled live from the API during
this pass — none were guessed or reused from memory (see
`data/trials/*.json` → `source_url` on every field for the exact API call).

## Data model

One JSON file per trial at `data/trials/<NCT_ID>.json`, organized into 7
field groups (35 fields total). Every field value is an object, never a
bare scalar:

```json
{
  "value": "SOLO 1",
  "source_type": "ctgov_api",
  "source_url": "https://clinicaltrials.gov/api/v2/studies/NCT02277743",
  "source_excerpt": "protocolSection.identificationModule.acronym",
  "extracted_by": "fetch_trials.py (ctgov_api v2, v1 pass)",
  "reviewed_by": null,
  "confidence": 1.0
}
```

`source_type` is one of:

- `ctgov_api` — read directly from a structured field in the live CT.gov
  API v2 JSON response (including simple arithmetic over structured counts,
  e.g. an adverse-event rate computed from `numAffected`/`numAtRisk`).
  `source_excerpt` is the JSON path read.
- `ctgov_text_extraction` — parsed from a CT.gov API *free-text* field
  (`eligibilityCriteria`, an `intervention.description`) by regex + review,
  not a clean structured field. `source_excerpt` is the matched text.
- `protocol_pdf_extraction` — parsed from a trial's Study Protocol or
  Statistical Analysis Plan PDF (linked from CT.gov's `documentSection`).
  `source_url` is the exact CDN PDF link; `source_excerpt` names the
  section the excerpt came from.
- `openfda_label` — pulled from the openFDA structured drug-label API
  (`api.fda.gov/drug/label.json`). Drug-level, not trial-level: the same
  value is reused across every trial of that drug. A `null` value with
  this `source_type` means the label was checked and the field (e.g.
  `boxed_warning`) genuinely isn't present — a confirmed absence, not a
  gap.
- `needs_extraction` — not available in any of the sources above (still
  only in full protocol tables/appendices, a paywalled full-text journal
  paper this environment can't fetch, or not published at all). `value` is
  `null` and stays `null` until human QA can fill it — v1 never guesses a
  plausible-sounding clinical number.

**Every non-`ctgov_api` value here is machine/LLM-extracted, not
hand-verified.** `reviewed_by` is `null` and `confidence` is `< 1.0` on all
of them — they still need the human clinical QA pass (captain + Garvita)
called for in the project brief before being treated as authoritative for
publication. `visit_schedule` is deliberately left `needs_extraction` for
every trial: the full schedule lives in large multi-page PDF tables that
plain-text PDF conversion cannot flatten into a trustworthy value, and a
garbled table is worse than a null.

**Paywalled full-text journal papers were explicitly in scope for this
pass but are out of reach from this environment**: each trial's primary
results publication is a real, identifiable `type: "RESULT"` reference in
CT.gov's own `protocolSection.referencesModule` (e.g. the SOLO 1/SOLO 2
NEJM paper, PMID 27690741) — but a direct fetch of that paper returns
HTTP 403 (paywalled, no subscription/authentication mechanism exists in
this sandbox). Fields that would need that full text stay honestly
`needs_extraction` rather than being filled from an abstract or guessed.

### Field groups and v1 fill status

| Group | Field | v1 status | Source |
|---|---|---|---|
| identity | `nct_id` | ✅ filled | `ctgov_api` |
| identity | `trial_name` (acronym) | ✅ filled | `ctgov_api` |
| identity | `official_title` | ✅ filled | `ctgov_api` |
| identity | `sponsor` | ✅ filled | `ctgov_api` |
| identity | `phase` | ✅ filled | `ctgov_api` |
| molecule | `drug` | ✅ filled | `ctgov_api` (intervention name, curated to canonical drug) |
| molecule | `intervention_names` | ✅ filled | `ctgov_api` |
| molecule | `intervention_type` | ✅ filled | `ctgov_api` |
| molecule | `mechanism_of_action` | ✅ filled (17/17) | `openfda_label` — drug-level FDA label text |
| molecule | `dosing_regimen` | ✅ filled (16/17) | `ctgov_text_extraction` — intervention description; null only where CT.gov has no description text on file (Dupilumab CAFE) |
| population | `condition` | ✅ filled | `ctgov_api` |
| population | `min_age` | ✅ filled | `ctgov_api` |
| population | `max_age` | ✅ filled | `ctgov_api` |
| population | `sex` | ✅ filled | `ctgov_api` |
| population | `enrollment_count` | ✅ filled | `ctgov_api` |
| population | `severity_definition` (EASI/IGA/BSA screening thresholds) | ✅ filled (16/17) | `ctgov_text_extraction` — matched `eligibilityCriteria` lines; null where CT.gov's own criteria text is abbreviated (Dupilumab CHRONOS) |
| design | `study_type` | ✅ filled | `ctgov_api` |
| design | `allocation` | ✅ filled | `ctgov_api` |
| design | `intervention_model` | ✅ filled | `ctgov_api` |
| design | `masking` | ✅ filled | `ctgov_api` |
| design | `number_of_arms` | ✅ filled | `ctgov_api` |
| design | `background_therapy_rule` | ⚠️ partial (5/17) | `ctgov_text_extraction`/`protocol_pdf_extraction` — only trials with a background/combination TCS regimen have one; monotherapy trials correctly have none |
| endpoints | `primary_endpoint_measure` | ✅ filled | `ctgov_api` |
| endpoints | `secondary_endpoint_measures` | ✅ filled | `ctgov_api` |
| endpoints | `endpoint_hierarchy_multiplicity` | ✅ filled (13/17) | `protocol_pdf_extraction` — SAP/protocol multiplicity-control section; needs_extraction for the 4 trials with no Study Documents posted on CT.gov (Dupilumab SOLO 1/2, CHRONOS, CAFE) |
| timing_ops | `start_date` | ✅ filled | `ctgov_api` |
| timing_ops | `primary_completion_date` | ✅ filled | `ctgov_api` |
| timing_ops | `completion_date` | ✅ filled | `ctgov_api` |
| timing_ops | `visit_schedule` | ⏳ needs_extraction (0/17) | Full schedule lives in multi-page PDF tables; not reliably machine-extractable, deliberately left null (see note above) |
| timing_ops | `rescue_therapy_rules` | ✅ filled (10/17) | `protocol_pdf_extraction` — protocol Rescue Treatment/Therapy section; needs_extraction where the term isn't used this way in the posted documents (Pfizer JADE MONO-1/2, JADE COMPARE) or no documents are posted (the 4 older Dupilumab trials) |
| adverse_events | `serious_adverse_event_rate` | ✅ filled (17/17) | `ctgov_api` — per-arm % from `resultsSection.adverseEventsModule.eventGroups[]` |
| adverse_events | `death_rate` | ✅ filled (17/17) | `ctgov_api` — per-arm % from the same `eventGroups[]` |
| adverse_events | `most_common_adverse_events` | ✅ filled (17/17) | `ctgov_api` — top non-serious AEs by incidence from `adverseEventsModule.otherEvents[]` (CT.gov's own ≥5% frequency-threshold table) |
| adverse_events | `discontinuation_due_to_ae_rate` | ⚠️ partial (13/17) | `ctgov_api` — from `participantFlowModule` dropout reasons; needs_extraction where a trial's posted dropout taxonomy has no clean "Adverse Event" category (the 3 Tralokinumab ECZTRA trials, Dupilumab CAFE) |
| adverse_events | `boxed_warning` | ✅ filled (17/17) | `openfda_label` — drug-level; `null` for Dupilumab/Tralokinumab/Lebrikizumab means confirmed no boxed warning, not a gap |

**595 sourced values total (17 trials × 35 fields). 549 are filled with
real data (455 `ctgov_api`, 36 `ctgov_text_extraction`, 24
`protocol_pdf_extraction`, 34 `openfda_label`); 46 remain
`needs_extraction`.** Every non-`ctgov_api` fill was produced by LLM-assisted
reading of a real, cited source (CT.gov free text, a downloaded protocol/SAP
PDF, CT.gov's structured results tables, or the openFDA label) — see
`scripts/enrich_needs_extraction.py` and `scripts/fetch_adverse_events.py`
for exactly which excerpt backs which field — and every one is
`reviewed_by: null` pending the human clinical QA pass (captain + Garvita)
before it's treated as authoritative for publication.

## Running the pipeline

Requires Python 3.9+, standard library only (no dependencies to install).

```bash
# 1. Fetch trial data live from ClinicalTrials.gov API v2 and write
#    data/trials/<NCT_ID>.json for each of the 17 trials above.
python3 scripts/fetch_trials.py

# 2. LLM-assisted second pass: fill severity_definition, background_therapy_rule,
#    dosing_regimen, mechanism_of_action, rescue_therapy_rules, and
#    endpoint_hierarchy_multiplicity from CT.gov free text, protocol/SAP PDFs,
#    and the openFDA label API (see source_type table above).
python3 scripts/enrich_needs_extraction.py

# 3. Adverse events / safety pass: adds the adverse_events group from CT.gov's
#    structured resultsSection (adverse-event tables, participant-flow dropout
#    reasons) and the openFDA boxed_warning field.
python3 scripts/fetch_adverse_events.py

# 4. Flatten data/trials/*.json into repo-root trials.csv and sources.csv
python3 scripts/build_csv.py
```

Optional: `python3 scripts/fetch_protocol_docs.py` re-downloads every
trial's Study Protocol/SAP PDF and converts it to text under
`data/_raw_cache/` (gitignored) — use it to re-verify or refresh a
`protocol_pdf_extraction` excerpt against the source PDF. Requires
`pdftotext` (poppler).

- `trials.csv` — one row per trial, one column per field (the field's
  `value`; `needs_extraction` fields are blank).
- `sources.csv` — one row per sourced value: `nct_id`, `field`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`,
  `reviewed_by`, `confidence`. 17 trials × 35 fields = 595 rows.

Re-running `fetch_trials.py` re-pulls fresh data from the live API and
resets every field to its baseline `ctgov_api`/`needs_extraction` state
(so re-run steps 2-3 after it); re-run `build_csv.py` last to regenerate
the CSVs.

## Out of scope for v1

- The human QA pass on top of the LLM-assisted extraction (captain +
  Garvita review of every non-`ctgov_api` value).
- `visit_schedule` and the other fields that remain `needs_extraction`
  after real extraction effort (see fill-status table above) — genuinely
  not available from a machine-readable source in this environment.
- AACT bulk-seeding (a possible future bulk source, not integrated here).
- Any change to the atlas portal UI or the `kolai-website` repo.
