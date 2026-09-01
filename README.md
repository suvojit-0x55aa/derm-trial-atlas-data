# Open Derm Trial Atlas — Data

Structured, sourced trial-design data for atopic dermatitis (AD) drug
trials. **This repo is a pure dataset — no extraction or build scripts
live here.** The pipeline that produced this data (ClinicalTrials.gov API
pulls, LLM-assisted free-text/PDF extraction, CSV flattening) now lives in
the `kolai-website` repo, under `scripts/atlas/`. The portal UI
(`superderma.ai/atlas`) also lives in `kolai-website`, separate from this
repo.

## What's in v1

Real pivotal Phase III trials (adult / adult+adolescent, systemic therapy)
for 5 drugs, pulled live from the [ClinicalTrials.gov API
v2](https://clinicaltrials.gov/data-api/api):

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | SOLO 1 (NCT02277743), SOLO 2 (NCT02277769), CHRONOS (NCT02260986), CAFE (NCT02755649) |
| Lebrikizumab | ADvocate1 (NCT04146363), ADvocate2 (NCT04178967), ADhere (NCT04250337) |
| Tralokinumab | ECZTRA 1 (NCT03131648), ECZTRA 2 (NCT03160885), ECZTRA 3 (NCT03363854) |
| Abrocitinib | JADE MONO-1 (NCT03349060), JADE MONO-2 (NCT03575871), JADE COMPARE (NCT03720470), JADE REGIMEN (NCT03627767) |
| Upadacitinib | Measure Up 1 (NCT03569293), Measure Up 2 (NCT03607422), AD Up (NCT03568318) |

17 trials total. Every NCT ID was pulled live from the API — none were
guessed or reused from memory (see `data/trials/*.json` → `source_url` on
every field for the exact source it came from).

## Files

- `data/trials/<NCT_ID>.json` — one file per trial, the canonical dataset.
- `trials.csv` — all 17 trials flattened to one row per trial, one column
  per field (the field's `value`; `needs_extraction` fields are blank).
- `sources.csv` — one row per sourced value (510 = 17 trials × 30 fields):
  `nct_id`, `field`, `source_type`, `source_url`, `source_excerpt`,
  `extracted_by`, `reviewed_by`, `confidence`.

`trials.csv` and `sources.csv` are generated from `data/trials/*.json` —
if you edit the dataset, regenerate them from `kolai-website`'s
`scripts/atlas/build_csv.py` rather than hand-editing the CSVs.

## Data model

Each trial JSON is organized into 6 field groups (30 fields total):
identity, molecule, population, design, endpoints, timing_ops. Every field
value is an object, never a bare scalar:

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

- `ctgov_api` — pulled directly from a structured field in the live
  CT.gov API v2 JSON response. `source_excerpt` is the JSON path read.
- `ctgov_text_extraction` — parsed from a CT.gov API *free-text* field
  (`eligibilityCriteria`, an `intervention.description`) by regex + review,
  not a clean structured field. `source_excerpt` is the matched text.
- `protocol_pdf_extraction` — parsed from a trial's Study Protocol or
  Statistical Analysis Plan PDF (linked from CT.gov's `documentSection`).
  `source_url` is the exact CDN PDF link; `source_excerpt` names the
  section the excerpt came from.
- `openfda_label` — pulled from the openFDA structured drug-label API
  (`api.fda.gov/drug/label.json`). Drug-level, not trial-level: the same
  value is reused across every trial of that drug.
- `needs_extraction` — not available in any of the sources above (still
  only in full protocol tables/appendices, or not published at all).
  `value` is `null` and stays `null` until human QA can fill it — this
  dataset never guesses a plausible-sounding clinical number.

**Every non-`ctgov_api` value here is machine/LLM-extracted, not
hand-verified.** `reviewed_by` is `null` and `confidence` is `< 1.0` on all
of them — they still need a human clinical QA pass (captain + Garvita)
before being treated as authoritative for publication. `visit_schedule` is
deliberately left `needs_extraction` for every trial: the full schedule
lives in large multi-page PDF tables that plain-text PDF conversion cannot
flatten into a trustworthy value, and a garbled table is worse than a null.

## Field groups and fill status

| Group | Field | Status | Source |
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

**510 sourced values total (17 trials × 30 fields). 468 are filled with
real data (391 `ctgov_api`, 36 `ctgov_text_extraction`, 24
`protocol_pdf_extraction`, 17 `openfda_label`); 42 remain
`needs_extraction`.** Every non-`ctgov_api` fill traces to a real, cited
source (CT.gov free text, a downloaded protocol/SAP PDF, or the openFDA
label) and is `reviewed_by: null` pending the human clinical QA pass
(captain + Garvita) before being treated as authoritative for publication.

## Out of scope for this dataset

- Extraction/build tooling — moved to `kolai-website`'s `scripts/atlas/`.
- Human clinical QA on the extracted (non-`ctgov_api`) values.
- Filling `visit_schedule` and the remaining `needs_extraction` cells.
- AACT bulk-seeding (a possible future bulk source, not integrated here).
- Any change to the atlas portal UI.
