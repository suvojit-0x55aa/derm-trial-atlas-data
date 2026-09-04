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

One JSON file per trial at `data/trials/<NCT_ID>.json` (**schema v2**, see
below), organized into 9 field groups (39 fields). Every field value is an
object, never a bare scalar:

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
- `protocol_pdf_extraction` — parsed from a trial's own Study Protocol or
  Statistical Analysis Plan PDF (linked from CT.gov's `documentSection`).
  `source_url` is the exact CDN PDF link; `source_excerpt` names the
  section the excerpt came from.
- `publication_extraction` — parsed from a full-text journal publication
  (fetched via PMC when available) or an FDA Drugs@FDA approval-package
  review (Medical/Multi-Discipline/Integrated Review; not CT.gov-linked,
  which is what distinguishes this from `protocol_pdf_extraction`).
  `source_url` is the exact PMC or accessdata.fda.gov PDF link;
  `source_excerpt` names the section/table the excerpt came from, quoting
  the source text directly wherever practical.
- `openfda_label` — pulled from the openFDA structured drug-label API
  (`api.fda.gov/drug/label.json`). Drug-level, not trial-level: the same
  value is reused across every trial of that drug. A `null` value with
  this `source_type` means the label was checked and the field (e.g.
  `boxed_warning`) genuinely isn't present — a confirmed absence, not a
  gap.
- `needs_extraction` — not available in any of the sources above after
  real effort (still only in full protocol tables/appendices, a paywalled
  paper genuinely unreachable, or not published at all). `value` is
  `null` and stays `null` until human QA can fill it — v1 never guesses a
  plausible-sounding clinical number.

- `openfda_faers` — openFDA adverse-event API (`api.fda.gov/drug/event.json`),
  drug-level real-world report summary (`real_world_safety.faers_summary`).
- `orange_book` — FDA Orange Book data files (`products.txt`/`patent.txt`/
  `exclusivity.txt`), small-molecule NDAs only (`exclusivity.orange_book`,
  and the `exclusivity.regulatory_application` join key).
- `purple_book` — FDA Purple Book monthly CSV, biologic BLAs only
  (`exclusivity.purple_book`, and the join key for biologics).

### Schema v2: typed, atomic values (no free-text catch-alls)

Every `value` is a typed structure that can be filtered and compared
directly — no LLM re-parsing of prose at read time. The full field-by-field
reference is generated from the spec in `atlas/schema.py`:

- `docs/SCHEMA.md` — every field, its value type, and the shared sub-types
  (`ScoreCriterion`, `Endpoint`, `RescueTherapy`, `OrangeBookRecord`, …).
- `schema/trial.schema.json` — the same spec as JSON Schema draft-07.

The one atomic building block is **`ScoreCriterion`** — a threshold on a
named clinical scale (`{scale, metric, comparator, value, unit, assessed_at,
…}`) — reused by eligibility severity thresholds, endpoint responder
definitions, endpoint subgroups, rescue triggers, and flare definitions. So
"EASI-75 at week 16" is the same row shape wherever it occurs:

```json
{"scale": "EASI", "metric": "percent_improvement_from_baseline", "comparator": ">=",
 "value": 75, "unit": "percent", ...}
```

What changed from v1 (field renames are recorded in `docs/SCHEMA.md`):

| v1 field (free text) | v2 field (typed) |
|---|---|
| `population.severity_definition` | `population.severity_criteria` — `{severity_label, criteria: [ScoreCriterion], …}` |
| `endpoints.primary_endpoint_measure` / `secondary_endpoint_measures` | `endpoints.primary_endpoints` / `secondary_endpoints` — one `Endpoint` per CT.gov outcome: `measure_type`, `scale`, `responder_criteria`, `timepoints`, `analysis_population`, `subgroup_criteria`, `study_period`, `event_type`; the CT.gov title is kept in `verbatim` |
| `endpoints.endpoint_hierarchy_multiplicity` | `endpoints.multiplicity_control` — procedure, alpha, co-primary endpoints, ordered testing sequence, alpha splits |
| `design.background_therapy_rule` | `design.background_therapy` — regimen type, TCS regimen/step-down rule, recommended agents, prohibited/permitted concomitants |
| `timing_ops.visit_schedule` | `timing_ops.study_schedule` — periods with week bounds, visit cadence/weeks, key weeks, extension |
| `timing_ops.rescue_therapy_rules` | `timing_ops.rescue_therapy` — permitted/trigger, trigger rules as `ScoreCriterion`, discontinuation/resume rules, agents |
| `molecule.dosing_regimen` (string) | list of `Intervention` — route, form, dose, frequency, duration, dosing periods, sites |
| `molecule.mechanism_of_action` (label prose) | `Mechanism` — modality, drug class, isotype, binding targets, cytokines, kinases, fold-selectivity |
| `adverse_events.boxed_warning` (label prose) | `BoxedWarning` — `present`, title, warning categories, referenced label sections |
| `population.min_age` / `max_age` ("18 Years") | `min_age_years` / `max_age_years` (numbers) |
| `timing_ops.*_date` ("2014-09") | `{date: "2014-09-01", precision: "month"}` |

New groups, designed against the real source shapes so incoming data lands in
typed fields (builders in `atlas/sources/`, exercised on real captured rows in
`tests/test_sources.py`):

- `real_world_safety.faers_summary` — openFDA FAERS report counts,
  seriousness breakdown, top MedDRA reaction terms, reports by year.
- `exclusivity.regulatory_application` — the NDA/BLA number (filled for all 5
  drugs from the Orange/Purple Book rows), the join key the other two need.
- `exclusivity.orange_book` — products, patents (number, expiry, use code,
  substance/product claim), exclusivity codes with dates; NDAs only.
- `exclusivity.purple_book` — licensure, BPCIA reference-product /
  interchangeable / orphan exclusivity dates, biosimilars; BLAs only.
  (Separate shape from Orange Book because BLA exclusivity rules differ.)

The v1 prose is not thrown away: it is kept as provenance in `source_excerpt`
(or the endpoint's `verbatim` / intervention's `description`), and
`tests/test_migration_lossless.py` proves, for every trial, that every
number, scale, timepoint, and agent/method token in the v1 prose is present
in the *atomic* v2 value (prose-carrying keys are stripped before the check),
that every v1 `needs_extraction` gap is still a gap (never invented), and
that re-running the migration on the frozen v1 snapshot
(`tests/fixtures/v1_trials/`) reproduces the committed files exactly.

**Every non-`ctgov_api` value here is machine/LLM-extracted, not
hand-verified.** `reviewed_by` is `null` and `confidence` is `< 1.0` on all
of them — they still need the human clinical QA pass (captain + Garvita)
called for in the project brief before being treated as authoritative for
publication.

**Paywalled full-text journal papers were explicitly in scope for this
pass.** Each trial's primary results publication was identified (via
CT.gov's own `referencesModule` where present, or PubMed search by trial
acronym/author/journal otherwise, always confirmed against the live API —
see `AGENTS.md` for the full PMID/DOI list) and a direct fetch was
attempted for every one. Every publisher/repository host tried — NEJM,
Wiley, JAMA Network, JAAD/Elsevier, and a university repository mirror —
sits behind a Cloudflare bot-challenge, one of which escalates to an
interactive "Verify you are human" Turnstile CAPTCHA; this pipeline does
not solve that (defeating an anti-bot check to scrape paywalled content is
out of bounds regardless of the paywall). Two other routes did work:

1. **PMC** had free full text for 4 of the 13 unique primary-publication
   PMIDs (checked via NCBI's `elink` `pubmed_pmc` linkage, then fetched
   with `efetch` — NCBI's own API is not behind Cloudflare). Fetched and
   mined for ECZTRA-1/2, ECZTRA-3, JADE MONO-2, and ADhere.
2. **FDA Drugs@FDA approval-package reviews** (accessdata.fda.gov, also
   not Cloudflare-protected) turned out to carry *more* granular
   protocol detail than the journal papers would have — exact visit
   schedules, rescue-therapy algorithms, background-therapy regimens, and
   endpoint testing hierarchies, organized in clearly labeled per-trial
   sections. This filled the majority of the remaining gaps across all 5
   drugs (see `scripts/enrich_publications.py` for the full per-trial
   breakdown and exact citations).

**Unpaywall** (checked for all 13 PMIDs via DOI) reported a legal
open-access location for 10 of them — but "legal OA" doesn't mean
"programmatically fetchable": every one of those 10 locations is on a
Cloudflare-protected host too, so Unpaywall's coverage didn't add
anything PMC/FDA hadn't already provided.

This closed most of the gap (46 → 10 `needs_extraction` fields
remaining). What's still genuinely unreachable, and why:

- **CAFE (NCT02755649), all 6 remaining fields**: no PMC entry for its
  paper, no Unpaywall OA location, and it falls in the gap between the
  original 2017 Dupixent FDA approval package (predates CAFE, which
  completed 2017-03-31) and the next FDA supplement checked (2018-10-19,
  doesn't mention CAFE or cyclosporine either).
- **JADE MONO-1 and JADE COMPARE `rescue_therapy_rules`**: the abrocitinib
  FDA review discusses these trials' rescue medication only in terms of
  its *statistical handling*, never states the protocol-level rescue
  algorithm — unlike JADE MONO-2, whose own PMC paper has an explicit
  "rescue medication was prohibited" eligibility-criteria quote.
- **JADE REGIMEN `background_therapy_rule` and `visit_schedule`**: a
  randomized-withdrawal design (open-label run-in, then randomized
  withdrawal to rescue) structurally unlike the other trials; it was
  still "ONGOING" at the FDA review's cutoff, covered only in a one-line
  summary table with no detailed design section to extract from.
- **Dupilumab `dosing_regimen`** (CAFE): no intervention-description text
  on file at CT.gov for this trial specifically.
- `visit_schedule` note: where filled, this is the trial's visit
  *cadence* (screening/baseline/weekly-or-per-protocol visits through a
  named endpoint, sometimes an itemized list of visit weeks when the
  source gave one) — not a full per-visit lab/assessment table, which
  still isn't reliably machine-extractable from these sources.

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
| molecule | `mechanism_of_action` | ✅ filled (17/17) | `openfda_label` — typed from the drug-level FDA label text (kept in `source_excerpt`) |
| molecule | `dosing_regimen` | ✅ filled (16/17) | `ctgov_text_extraction` — intervention description; null only where CT.gov has no description text on file (Dupilumab CAFE) |
| population | `condition` | ✅ filled | `ctgov_api` |
| population | `min_age_years` | ✅ filled | `ctgov_api` |
| population | `max_age_years` | ✅ filled | `ctgov_api` |
| population | `sex` | ✅ filled | `ctgov_api` |
| population | `enrollment_count` | ✅ filled | `ctgov_api` |
| population | `severity_criteria` (EASI/IGA/BSA screening thresholds as `ScoreCriterion` rows) | ✅ filled (17/17) | `ctgov_text_extraction` (16) direct; `publication_extraction` (1) — CHRONOS, by an FDA-review cross-reference to SOLO 1/2's identical criteria |
| design | `study_type` | ✅ filled | `ctgov_api` |
| design | `allocation` | ✅ filled | `ctgov_api` |
| design | `intervention_model` | ✅ filled | `ctgov_api` |
| design | `masking` | ✅ filled | `ctgov_api` |
| design | `number_of_arms` | ✅ filled | `ctgov_api` |
| design | `background_therapy` | ✅ filled (15/17) | `ctgov_text_extraction`/`protocol_pdf_extraction`/`publication_extraction` — combination-TCS trials have a regimen, monotherapy trials confirmed "none" from FDA-review/paper text; needs_extraction only for CAFE and JADE REGIMEN |
| endpoints | `primary_endpoints` | ✅ filled | `ctgov_api` |
| endpoints | `secondary_endpoints` | ✅ filled | `ctgov_api` |
| endpoints | `multiplicity_control` | ✅ filled (16/17) | `protocol_pdf_extraction` (13) / `publication_extraction` (3, SOLO 1/2/CHRONOS via FDA review); needs_extraction only for CAFE |
| timing_ops | `start_date` | ✅ filled | `ctgov_api` |
| timing_ops | `primary_completion_date` | ✅ filled | `ctgov_api` |
| timing_ops | `completion_date` | ✅ filled | `ctgov_api` |
| timing_ops | `study_schedule` | ✅ filled (15/17) | `publication_extraction` — visit cadence/key timepoints from FDA reviews or PMC papers (see note above on granularity); needs_extraction only for CAFE and JADE REGIMEN |
| timing_ops | `rescue_therapy` | ✅ filled (14/17) | `protocol_pdf_extraction` (10) / `publication_extraction` (4); needs_extraction for CAFE, JADE MONO-1, JADE COMPARE |
| adverse_events | `serious_adverse_event_rate` | ✅ filled (17/17) | `ctgov_api` — per-arm % from `resultsSection.adverseEventsModule.eventGroups[]` |
| adverse_events | `death_rate` | ✅ filled (17/17) | `ctgov_api` — per-arm % from the same `eventGroups[]` |
| adverse_events | `most_common_adverse_events` | ✅ filled (17/17) | `ctgov_api` — top non-serious AEs by incidence from `adverseEventsModule.otherEvents[]` (CT.gov's own ≥5% frequency-threshold table) |
| adverse_events | `discontinuation_due_to_ae_rate` | ✅ filled (16/17) | `ctgov_api` (13) direct; `publication_extraction` (3, the 3 Tralokinumab ECZTRA trials, from their PMC papers' AE tables); needs_extraction only for CAFE |
| adverse_events | `boxed_warning` | ✅ filled (17/17) | `openfda_label` — drug-level; `present: false` for Dupilumab/Tralokinumab/Lebrikizumab means confirmed no boxed warning, not a gap |
| real_world_safety | `faers_summary` | ⬜ needs_extraction (17/17) | `openfda_faers` — structured home ready; populated by the scale-out pass |
| exclusivity | `regulatory_application` | ✅ filled (17/17) | `orange_book` (Abrocitinib, Upadacitinib NDAs) / `purple_book` (Dupilumab, Lebrikizumab, Tralokinumab BLAs) — the NDA/BLA join key |
| exclusivity | `orange_book` | ⬜ needs_extraction (17/17) | `orange_book` — structured home ready (builder + fixture test in place); populated by the scale-out pass |
| exclusivity | `purple_book` | ⬜ needs_extraction (17/17) | `purple_book` — structured home ready; populated by the scale-out pass |

**595 v1 sourced values (17 trials × 35 fields), all carried into v2 (663 = 17 × 39 with the 4 new fields). 585 are filled with
real data (455 `ctgov_api`, 36 `ctgov_text_extraction`, 24
`protocol_pdf_extraction`, 36 `publication_extraction`, 34
`openfda_label`); 10 remain `needs_extraction`, all on CAFE (6),
JADE MONO-1 (1), JADE COMPARE (1), and JADE REGIMEN (2) — see the list
above for exactly why each one is unreachable.** Every non-`ctgov_api`
fill was produced by LLM-assisted reading of a real, cited source (CT.gov
free text, a downloaded protocol/SAP PDF, CT.gov's structured results
tables, a PMC full-text paper, an FDA approval-package review, or the
openFDA label) — see `scripts/enrich_needs_extraction.py`,
`scripts/fetch_adverse_events.py`, and `scripts/enrich_publications.py`
for exactly which excerpt backs which field — and every one is
`reviewed_by: null` pending the human clinical QA pass (captain +
Garvita) before it's treated as authoritative for publication.

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

# 4. Publication pass: fills remaining gaps from PMC full-text papers and
#    FDA Drugs@FDA approval-package reviews (hand-curated excerpts, see
#    scripts/enrich_publications.py's docstring for what was and wasn't
#    reachable and why).
python3 scripts/enrich_publications.py

# 5. Migrate the v1 records (free-text values) to schema v2 (typed values) in
#    place and validate them against atlas/schema.py. Idempotent.
python3 scripts/migrate_v1_to_v2.py

# 6. Flatten data/trials/*.json into the repo-root CSVs (see below).
python3 scripts/build_csv.py

# Regenerate docs/SCHEMA.md + schema/trial.schema.json after any change to
# atlas/schema.py (tests fail if they drift):
python3 scripts/export_schema.py

# Run the tests (stdlib unittest; ~40 tests incl. the lossless-migration proof):
python3 -m unittest discover -s tests -t .
```

Stages 2-4 edit **v1** records and refuse to run on a v2 file; to re-enrich,
re-run stage 1 (which resets to the v1 baseline), then 2-5. Passes that write
the new v2-only groups (FAERS, Orange/Purple Book) run *after* stage 5 and use
the builders in `atlas/sources/` to produce values the schema accepts.

Optional: `python3 scripts/fetch_protocol_docs.py` re-downloads every
trial's Study Protocol/SAP PDF and converts it to text under
`data/_raw_cache/` (gitignored) — use it to re-verify or refresh a
`protocol_pdf_extraction` excerpt against the source PDF. Requires
`pdftotext` (poppler). The PMC papers and FDA review PDFs behind
`publication_extraction` excerpts aren't re-fetched by any script (they
were downloaded by hand during this pass); their cached copies would live
under `data/_raw_cache/papers/` if you re-created that directory, and the
exact URL to re-fetch each one from is in the corresponding field's
`source_url`.

- `trials.csv` — one row per trial, one column per field (the field's
  `value`, JSON-encoded when structured; `needs_extraction` fields are blank).
- `sources.csv` — one row per sourced value: `nct_id`, `field`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`,
  `reviewed_by`, `confidence`. 17 trials × 39 fields = 663 rows.
- `endpoints.csv` — one row per outcome measure × criterion: `measure_type`,
  `scale`, `timepoints`, `analysis_population`, and the `ScoreCriterion`
  columns, so "EASI-75 responders at week 16" is a column filter.
- `severity_criteria.csv` — one row per baseline-severity `ScoreCriterion`.
- `adverse_event_rates.csv` — one row per (trial, arm, measure[, MedDRA term]).

Re-running `fetch_trials.py` re-pulls fresh data from the live API and
resets every field to its v1 baseline `ctgov_api`/`needs_extraction` state
(so re-run steps 2-5 after it); re-run `build_csv.py` last to regenerate
the CSVs.

## Out of scope for v1

- The human QA pass on top of the LLM-assisted extraction (captain +
  Garvita review of every non-`ctgov_api` value).
- The 10 fields that remain `needs_extraction` after real extraction
  effort across CT.gov, protocol/SAP PDFs, PMC, Unpaywall, and FDA
  approval-package reviews (see the fill-status table and the notes
  above it) — genuinely not available from a machine-readable,
  non-CAPTCHA-gated source in this environment.
- AACT bulk-seeding (a possible future bulk source, not integrated here).
- Any change to the atlas portal UI or the `kolai-website` repo.
