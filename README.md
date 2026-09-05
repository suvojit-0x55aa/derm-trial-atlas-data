# Open Derm Trial Atlas — Data Pipeline (v1 + indication expansion)

Data-backend pipeline for the Open Derm Trial Atlas: structured, sourced
trial-design and safety data for dermatology drug trials. This repo is the
data backend only — fetch, extraction, and build scripts all live here in
`scripts/`. The portal UI (`superderma.ai/atlas`) lives in a separate repo
(`kolai-website`) and is not part of this pipeline.

## What this covers

Real, live-pulled pivotal Phase III trials (adult / adult+adolescent,
systemic therapy), from the [ClinicalTrials.gov API
v2](https://clinicaltrials.gov/data-api/api) (`/api/v2/studies`, no API
key required), across **9 indications, 22 unique drugs, 63 trials**:

### Atopic Dermatitis (6 drugs, 19 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | SOLO 1 (NCT02277743), SOLO 2 (NCT02277769), CHRONOS (NCT02260986), CAFE (NCT02755649) |
| Lebrikizumab | ADvocate1 (NCT04146363), ADvocate2 (NCT04178967), ADhere (NCT04250337) |
| Tralokinumab | ECZTRA 1 (NCT03131648), ECZTRA 2 (NCT03160885), ECZTRA 3 (NCT03363854) |
| Abrocitinib | JADE MONO-1 (NCT03349060), JADE MONO-2 (NCT03575871), JADE COMPARE (NCT03720470), JADE REGIMEN (NCT03627767) |
| Upadacitinib | Measure Up 1 (NCT03569293), Measure Up 2 (NCT03607422), AD Up (NCT03568318) |
| Nemolizumab | ARCADIA 1 (NCT03985943), ARCADIA 2 (NCT03989349) — added 2026-09-05, FDA-approved for AD Jan 2025 |

### Plaque Psoriasis (7 drugs, 17 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Guselkumab | VOYAGE 1 (NCT02207231), VOYAGE 2 (NCT02207244) |
| Risankizumab | UltIMMa-1 (NCT02684370), UltIMMa-2 (NCT02684357) |
| Tildrakizumab | reSURFACE 1 (NCT01722331), reSURFACE 2 (NCT01729754) |
| Bimekizumab | BE VIVID (NCT03370133), BE SURE (NCT03412747), BE RADIANT (NCT03536884) |
| Deucravacitinib | POETYK-PSO-1 (NCT03624127), POETYK-PSO-2 (NCT03611751) |
| Ixekizumab | UNCOVER-1 (NCT01474512), UNCOVER-2 (NCT01597245), UNCOVER-3 (NCT01646177) — added 2026-09-05, FDA-approved 2016 |
| Certolizumab | CIMPASI-1 (NCT02326298), CIMPASI-2 (NCT02326272), CIMPACT (NCT02346240) — added 2026-09-05, FDA-approved 2018 |

Excluded during curation (not pivotal registrational trials — see
`scripts/fetch_trials.py`'s comments for the live-verified reason each was
ruled out): NCT02203032 "NAVIGATE" (guselkumab ustekinumab-inadequate-
responder switch study), NCT03162796 "Discover-1" (guselkumab, but this
trial is actually Psoriatic Arthritis — a different indication), NCT04102007
(single-arm open-label risankizumab post-switch study).

### Hidradenitis Suppurativa (new — 3 drugs, 6 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Adalimumab | PIONEER I (NCT01468207), PIONEER II (NCT01468233) |
| Secukinumab | SUNSHINE (NCT03713619), SUNRISE (NCT03713632) |
| Bimekizumab | BE HEARD I (NCT04242446), BE HEARD II (NCT04242498) |

### Alopecia Areata (new — 3 drugs, 5 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Baricitinib | BRAVE-AA1 (NCT03570749), BRAVE-AA2 (NCT03899259) |
| Ritlecitinib | ALLEGRO-2b/3 (NCT03732807) |
| Deuruxolitinib | THRIVE-AA1 (NCT04518995), THRIVE-AA2 (NCT04797650) — registered on CT.gov under the pre-approval compound code CTP-543 |

### Chronic Spontaneous Urticaria (3 drugs, 6 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Omalizumab | ASTERIA I (NCT01287117), ASTERIA II (NCT01292473), GLACIAL (NCT01264939) — acronyms per literature, CT.gov's own `acronym` field is empty for these 3 |
| Dupilumab | LIBERTY-CSU CUPID (NCT04180488) — master protocol, 3 sub-studies; CSU is a real, separate FDA-approved indication for dupilumab (confirmed via the live openFDA label, section 1.7), distinct from the AD trials above |
| Remibrutinib | REMIX-1 (NCT05030311), REMIX-2 (NCT05032157) — added 2026-09-05, FDA-approved (Rhapsido, NDA 218436) 2025-09-30. Excluded as non-pivotal: NCT05048342 "BISCUIT" (Japan-only open-label regional bridging study, n=71), NCT06868212 "RECLAIM" (active-comparator vs. dupilumab, not yet complete) |

### Prurigo Nodularis (2 drugs, 4 trials — new indication, added 2026-09-05)

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | PRIME (NCT04183335), PRIME2 (NCT04202679) — FDA-approved for PN Sept 2022 |
| Nemolizumab | OLYMPIA 1 (NCT04501679), OLYMPIA 2 (NCT04501666) — FDA-approved for PN Aug 2024 |

CT.gov maps these trials' condition to "Neurodermatitis" (a MeSH-adjacent
synonym), not the literal string "Prurigo Nodularis" — confirmed as the
correct indication via each trial's title and the sponsor's own registry
page, not assumed from the condition field alone.

### Vitiligo (1 drug, 2 trials — new indication, added 2026-09-05)

| Drug | Pivotal Phase III trials |
|---|---|
| Ruxolitinib (topical cream) | TRuE-V1 (NCT04052425), TRuE-V2 (NCT04057573) — FDA-approved (Opzelura) July 2022 |

Thin (1 drug) but real: Opzelura cream is the only FDA-approved
repigmentation therapy for vitiligo as of this pass. A separate,
previously-investigated 3-drug **oral**-JAK systemic Phase III program
(ritlecitinib "Tranquillo", upadacitinib "Viti-Up", povorcitinib
"STOP-V1/V2") remains excluded: every trial in that program still has
zero posted results — none can populate the `adverse_events` field group
yet. Revisit that program once it reports out; it is unrelated to
Ruxolitinib's topical program above, which already has full results.

### Chronic Hand Eczema (1 drug, 3 trials — new indication, added 2026-09-05)

| Drug | Pivotal Phase III trials |
|---|---|
| Delgocitinib (topical cream) | DELTA 1 (NCT04871711), DELTA 2 (NCT04872101), DELTA TEEN (NCT05355818) — FDA-approved (Anzupgo, NDA 219155) 2025-07-23 |

DELTA 1/2 are the twin global vehicle-controlled adult pivotal trials;
DELTA TEEN extends the same registrational program to adolescents 12-17
(vehicle-controlled, not an open-label extension). Excluded as non-pivotal:
NCT05259722 "DELTA FORCE" (active-comparator vs. Toctino/alitretinoin, not
placebo/vehicle-controlled), NCT04949841 (open-label extension of DELTA
1/2), NCT06004050 (Phase III, no posted results yet).

### Bullous Pemphigoid (1 drug, 1 trial — new indication, added 2026-09-05)

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | LIBERTY-BP (NCT04206553) — Phase 2/3 combined trial, n=106; BP is a real, separate FDA-approved indication for dupilumab (confirmed via the live openFDA label, section 1.8) |

Thinnest indication in the atlas (1 drug, 1 trial), but real and verified —
same precedent as Vitiligo's inclusion. A queued candidate from a prior
cycle (rilzabrutinib/Wayrilz) was checked and does **not** hold up:
rilzabrutinib has zero CT.gov trials for Bullous Pemphigoid and its FDA
label indications are Immune Thrombocytopenia only — a wrong lead, not a
real BP drug. Also checked and excluded: efgartigimod (Vyvgart) has a
completed BP Phase 2/3 trial (NCT05267600) but its FDA label indications
are gMG and CIDP only, not BP.

Ruxolitinib the ingredient also covers Jakafi/Jakafi XR (oral tablets,
NDA 202192/217180, oncology/GVHD use) under separate NDAs from Opzelura
(NDA 215309, this atlas's drug) — `exclusivity.orange_book` is pinned to
215309 specifically (see `scripts/fetch_orange_book.py`), but openFDA's
FAERS `medicinalproduct` search field can't distinguish formulation/route,
so `real_world_safety.faers_summary` for Ruxolitinib is a mix of Opzelura
and Jakafi(XR) reports, not Opzelura-only — a real, documented limitation
of FAERS's report-level data, not a pipeline bug.

Every NCT ID above was pulled live from the API during this pass — none
were guessed or reused from memory (see `data/trials/*.json` →
`source_url` on every field for the exact API call), and every drug/trial
inclusion followed the same hand-curation discipline as the original AD
pass: query by indication + intervention, then individually fetch and
confirm each candidate is a real pivotal arm (not a comparator, switch
study, or wrong-indication trial) before adding it.

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

### Fill status for the 26 newly added trials (Psoriasis, HS, AA, CSU)

The 26 trials added across the 4 new indications went through the same
stage 1 (`fetch_trials.py`), stage 2 (`enrich_needs_extraction.py`), and
stage 3 (`fetch_adverse_events.py`) passes as the 17 AD trials — every
`ctgov_api` field, `mechanism_of_action` (openFDA label), `dosing_regimen`
(CT.gov intervention text), and the full `adverse_events` group are real
and filled the same way. `severity_definition` also auto-filled for most
psoriasis trials (the extraction regex was extended to recognize
PASI/sPGA alongside AD's EASI/IGA/vIGA).

**What's intentionally still `needs_extraction` for these 26 trials, and
why**: `rescue_therapy_rules`, `endpoint_hierarchy_multiplicity`,
`visit_schedule`, and most of `background_therapy_rule` require the same
hand-curated, per-trial protocol/SAP-PDF reading pass that
`RESCUE_RULES`/`MULTIPLICITY_RULES`/`BACKGROUND_THERAPY_PDF` in
`enrich_needs_extraction.py` did for the 17 AD trials — genuinely
labor-intensive curation, not a code gap (most of these 26 trials do have
a protocol/SAP PDF on file at CT.gov, often more than the AD trials did,
so the raw material for a future curation pass exists). Doing that pass
for all 26 trials is out of scope for this batch (same "curation-bound,
not code-bound" scope call the psoriasis-indication scout report made);
it's a well-defined, boundable follow-up in the same shape as the work
already done for AD, not a structural change. `population.severity_definition`
also remains `needs_extraction` for HS/AA/CSU trials specifically: their
severity instruments (HiSCR/IHS4, SALT, UAS7) are checked for by the
extraction regex but most trials phrase the eligibility criterion in a way
the regex doesn't catch — a real, checkable gap, not a fabricated null.

Aggregate: **2457 sourced values across all 63 trials (63 × 39 rows in
`sources.csv`, which flattens nested sub-fields into their own rows);
2166 filled with real data (88.2%), 291 remain `needs_extraction`** — see
`sources.csv` for the per-trial, per-field breakdown.

## Running the pipeline

Requires Python 3.9+, standard library only (no dependencies to install).

```bash
# 1. Fetch trial data live from ClinicalTrials.gov API v2 and write
#    data/trials/<NCT_ID>.json for each of the 63 trials above.
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

# 6. Fetch openFDA FAERS / Orange Book / Purple Book live and stage one
#    schema-shaped sourced value per drug under data/_raw_staging/<source>/.
python3 scripts/fetch_faers.py
python3 scripts/fetch_orange_book.py
python3 scripts/fetch_purple_book.py

# 7. Fold the staged FAERS/Orange Book/Purple Book values into every trial's
#    real_world_safety.faers_summary / exclusivity.{orange_book,purple_book}
#    (drug-level; requires stage 5 to have already set
#    exclusivity.regulatory_application, which decides which registry field
#    is real for that drug).
python3 scripts/apply_source_data.py

# 8. Flatten data/trials/*.json into the repo-root CSVs (see below).
python3 scripts/build_csv.py

# Regenerate docs/SCHEMA.md + schema/trial.schema.json after any change to
# atlas/schema.py (tests fail if they drift):
python3 scripts/export_schema.py

# Run the tests (stdlib unittest; ~40 tests incl. the lossless-migration proof):
python3 -m unittest discover -s tests -t .
```

Stages 2-4 edit **v1** records and refuse to run on a v2 file; to re-enrich,
re-run stage 1 (which resets to the v1 baseline), then 2-5. Stages 6-7 only
touch `real_world_safety`/`exclusivity` and are safe to re-run any time
after stage 5 (they don't require stages 2-4 to have run first, and won't
disturb any other field group).

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
  `reviewed_by`, `confidence`. 63 trials × 39 fields (see counts below;
  regenerated after the indication-expansion + cross-source integration).
- `endpoints.csv` — one row per outcome measure × criterion: `measure_type`,
  `scale`, `timepoints`, `analysis_population`, and the `ScoreCriterion`
  columns, so "EASI-75 responders at week 16" is a column filter.
- `severity_criteria.csv` — one row per baseline-severity `ScoreCriterion`.
- `adverse_event_rates.csv` — one row per (trial, arm, measure[, MedDRA term]).

Re-running `fetch_trials.py` re-pulls fresh data from the live API and
resets every field to its v1 baseline `ctgov_api`/`needs_extraction` state
for every trial in `TRIALS` (so re-run steps 2-5 after it, and re-diff
against the committed `data/trials/*.json` before committing — the 17 AD
trials' curated fields are reproduced by the hand-curated dicts in
`enrich_needs_extraction.py`/`enrich_publications.py`/`atlas/curated_*.py`,
but only the `extracted_by` attribution string, not the content, has ever
drifted from a prior pass); re-run `build_csv.py` last to regenerate the
CSVs.

## Cross-source data (FAERS, Orange Book, Purple Book)

Real data fetched for all 3 sources validated in the cross-source
data-strategy scout report, for every drug across all 9 indications, and
integrated into every trial's real `real_world_safety.faers_summary` /
`exclusivity.{orange_book,purple_book}` schema v2 fields — no free-text/
prose intermediate, no data left sitting in a staging directory.

`scripts/fetch_faers.py`, `fetch_orange_book.py`, and `fetch_purple_book.py`
each fetch live and stage one drug-level sourced value per drug under
`data/_raw_staging/<source>/<drug>.json`, already shaped to match
`atlas/schema.py`'s `FAERS_SUMMARY`/`ORANGE_BOOK`/`PURPLE_BOOK` types
directly (each verified with `atlas.schema.validate()` before being
folded in — not reusing `atlas/sources/*.py`'s builders, which are built
for the *CSV/tilde-file* column-name spellings of these sources; two of
these three live-fetched sources (openFDA's Orange Book mirror, Purple
Book's live search-results table) turned out to use different column
names/date formats than the file-download versions those builders target,
confirmed on real rows — see each script's module docstring). Then
`scripts/apply_source_data.py` copies each drug's staged value into every
trial of that drug, and picks which of `orange_book`/`purple_book` is the
real one per drug from `exclusivity.regulatory_application.value.registry`
(the other stays an honest not-applicable `needs_extraction`, since a
biologic BLA has no Orange Book NDA entry and vice versa).

| Source | Script | Coverage | Result |
|---|---|---|---|
| **openFDA FAERS** (`api.fda.gov/drug/event.json`) | `scripts/fetch_faers.py` | All 22 unique drugs across all 9 indications | ✅ Real data for all 22 — total/serious/death/hospitalization/life-threatening/disability report counts, top 15 reactions (overall and serious-only), and a real per-year report-count histogram (openFDA has no year-granularity aggregation, so this is built by summing its daily `receivedate` buckets — verified lossless: the daily counts for Dupilumab sum to exactly its `total_reports`). Report volume varies enormously with market exposure time (Adalimumab: 46,072 reports; Deuruxolitinib, approved 2025: 1 report) — a real finding, not an error. Ruxolitinib's FAERS search term also matches Jakafi/Jakafi XR (same active ingredient, unrelated oral oncology NDAs) — openFDA's `medicinalproduct` field carries no formulation/route distinction, so this one drug's FAERS numbers are a real, unavoidable mix, not Opzelura-only (see Vitiligo section above). |
| **FDA Purple Book** (biologic BLA exclusivity) | `scripts/fetch_purple_book.py` | 13 biologics (Dupilumab, Lebrikizumab, Tralokinumab, Guselkumab, Risankizumab, Tildrakizumab, Bimekizumab, Adalimumab, Secukinumab, Omalizumab, Nemolizumab, Ixekizumab, Certolizumab) | ✅ Real matched product rows for all 13 (BLA number, approval date, exclusivity fields where populated) — parsed from the live `purplebooksearch.fda.gov` search-results table (its downloads page only offers monthly delta CSVs, not a full snapshot; the live table has the full current dataset, ~2242 product rows). |
| **FDA Orange Book** (small-molecule NDA patent/exclusivity) | `scripts/fetch_orange_book.py` | 9 small molecules (Abrocitinib, Upadacitinib, Baricitinib, Ritlecitinib, Deuruxolitinib, Deucravacitinib, Ruxolitinib, Remibrutinib, Delgocitinib) | ✅ Real patent/exclusivity data for all 9, via **openFDA's `drug/orangebook.json`** endpoint — a separate, script-friendly mirror of the same dataset. The official FDA-hosted routes (the `fda.gov/media/...` ZIP and the `accessdata.fda.gov` query tool) are genuinely blocked by Akamai bot-detection (confirmed independently twice, different User-Agents/cookies/Referers); openFDA's own mirror isn't behind that wall. Ruxolitinib needed an extra `application_number` filter (see script) to isolate Opzelura's NDA (215309) from Jakafi/Jakafi XR's (202192/217180), which otherwise merge under the shared ingredient search. Remibrutinib and Delgocitinib (both approved 2025) needed the exact field name `products.active_ingredients.name` — a plain `ingredient` field search returns a false NOT_FOUND for recent approvals even though the row exists. |

Each of these 3 scripts is a separate parser matching the source's own
shape (FAERS's JSON aggregation API; Purple Book's HTML search table with
BLA/biologic-exclusivity columns; Orange Book's openFDA JSON mirror of the
tilde-delimited NDA patent/exclusivity files, per its own different
ruleset) — none reuse another's parsing logic, per the source-strategy
report's explicit instruction. The NDA/BLA join key
(`exclusivity.regulatory_application`) that ties a drug to its Orange/
Purple Book application lives in `atlas/regulatory_applications.py`,
hand-curated the same way `TRIALS` is.

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
