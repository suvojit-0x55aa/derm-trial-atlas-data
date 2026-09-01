# Open Derm Trial Atlas — Data Pipeline (v1)

Data-backend pipeline for the Open Derm Trial Atlas: structured, sourced
trial-design data for atopic dermatitis (AD) drug trials. This repo is the
data backend only. The portal UI (`superderma.ai/atlas`) lives in a
separate repo and is not part of this pipeline.

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

One JSON file per trial at `data/trials/<NCT_ID>.json`, organized into 6
field groups (30 fields total). Every field value is an object, never a
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

- `ctgov_api` — pulled directly from a structured field in the live
  CT.gov API v2 JSON response. `source_excerpt` is the JSON path read.
- `needs_extraction` — not available as a structured API field. Requires
  a future LLM-assisted extraction pass over free-text
  `eligibilityCriteria`/`outcomesModule` blobs, or protocol/SAP/FDA-review
  PDFs, followed by human QA (captain + Garvita). `value` is `null` and
  stays `null` until that follow-up work fills it — v1 never guesses a
  plausible-sounding clinical number here.

### Field groups and v1 fill status

| Group | Field | v1 status | Why |
|---|---|---|---|
| identity | `nct_id` | ✅ filled | CT.gov API |
| identity | `trial_name` (acronym) | ✅ filled | CT.gov API |
| identity | `official_title` | ✅ filled | CT.gov API |
| identity | `sponsor` | ✅ filled | CT.gov API |
| identity | `phase` | ✅ filled | CT.gov API |
| molecule | `drug` | ✅ filled | CT.gov API (intervention name, curated to canonical drug) |
| molecule | `intervention_names` | ✅ filled | CT.gov API |
| molecule | `intervention_type` | ✅ filled | CT.gov API |
| molecule | `mechanism_of_action` | ⏳ needs_extraction | Not a structured API field |
| molecule | `dosing_regimen` | ⏳ needs_extraction | Lives in free-text arm descriptions |
| population | `condition` | ✅ filled | CT.gov API |
| population | `min_age` | ✅ filled | CT.gov API |
| population | `max_age` | ✅ filled | CT.gov API |
| population | `sex` | ✅ filled | CT.gov API |
| population | `enrollment_count` | ✅ filled | CT.gov API |
| population | `severity_definition` (EASI/IGA/BSA screening thresholds) | ⏳ needs_extraction | In free-text `eligibilityCriteria` |
| design | `study_type` | ✅ filled | CT.gov API |
| design | `allocation` | ✅ filled | CT.gov API |
| design | `intervention_model` | ✅ filled | CT.gov API |
| design | `masking` | ✅ filled | CT.gov API |
| design | `number_of_arms` | ✅ filled | CT.gov API |
| design | `background_therapy_rule` | ⏳ needs_extraction | In free-text `eligibilityCriteria` |
| endpoints | `primary_endpoint_measure` | ✅ filled | CT.gov API |
| endpoints | `secondary_endpoint_measures` | ✅ filled | CT.gov API |
| endpoints | `endpoint_hierarchy_multiplicity` | ⏳ needs_extraction | Statistical testing order lives in protocol/SAP, not the API |
| timing_ops | `start_date` | ✅ filled | CT.gov API |
| timing_ops | `primary_completion_date` | ✅ filled | CT.gov API |
| timing_ops | `completion_date` | ✅ filled | CT.gov API |
| timing_ops | `visit_schedule` | ⏳ needs_extraction | Full visit schedule lives in protocol PDFs |
| timing_ops | `rescue_therapy_rules` | ⏳ needs_extraction | In free-text `eligibilityCriteria`/protocol |

**23 of 30 fields filled with real, sourced data in v1. 7 fields are
`needs_extraction` placeholders**, all clustered around clinical
thresholds and protocol detail that only exist as free text or in PDFs
CT.gov's structured API does not expose. Filling those 7 is planned
follow-up work (LLM-assisted extraction + human review), out of scope for
this pass.

## Running the pipeline

Requires Python 3.9+, standard library only (no dependencies to install).

```bash
# 1. Fetch trial data live from ClinicalTrials.gov API v2 and write
#    data/trials/<NCT_ID>.json for each of the 17 trials above.
python3 scripts/fetch_trials.py

# 2. Flatten data/trials/*.json into repo-root trials.csv and sources.csv
python3 scripts/build_csv.py
```

- `trials.csv` — one row per trial, one column per field (the field's
  `value`; `needs_extraction` fields are blank).
- `sources.csv` — one row per sourced value: `nct_id`, `field`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`,
  `reviewed_by`, `confidence`. 17 trials × 30 fields = 510 rows.

Re-running `fetch_trials.py` re-pulls fresh data from the live API and
overwrites the JSON files; re-run `build_csv.py` after to regenerate the
CSVs.

## Out of scope for v1

- LLM-assisted extraction of the 7 `needs_extraction` fields from
  free-text eligibility criteria / outcomes blobs / protocol / SAP / FDA
  review PDFs, and the human QA pass on top of it.
- AACT bulk-seeding (a possible future bulk source, not integrated here).
- Any change to the atlas portal UI or the `kolai-website` repo.
