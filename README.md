# Open Derm Trial Atlas — Data (schema v2)

Structured, sourced trial-design and safety data for dermatology drug
trials. **This repo holds data only** — every JSON/CSV file below and
nothing else. The fetch/extraction/build/migration pipeline that produces
this data, the schema spec (`atlas/schema.py`), the portal UI
(`superderma.ai/atlas`), and their tests all live in the separate
`kolai-website` repo; this repo is regenerated from there, not the other
way around.

## What this covers

Real, live-pulled pivotal Phase III trials (adult / adult+adolescent,
systemic therapy), from the [ClinicalTrials.gov API
v2](https://clinicaltrials.gov/data-api/api) (`/api/v2/studies`, no API
key required), across **10 indications, 23 unique drugs, 64 trials**:

### Atopic Dermatitis (6 drugs, 19 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | SOLO 1 (NCT02277743), SOLO 2 (NCT02277769), CHRONOS (NCT02260986), CAFE (NCT02755649) |
| Lebrikizumab | ADvocate1 (NCT04146363), ADvocate2 (NCT04178967), ADhere (NCT04250337) |
| Tralokinumab | ECZTRA 1 (NCT03131648), ECZTRA 2 (NCT03160885), ECZTRA 3 (NCT03363854) |
| Abrocitinib | JADE MONO-1 (NCT03349060), JADE MONO-2 (NCT03575871), JADE COMPARE (NCT03720470), JADE REGIMEN (NCT03627767) |
| Upadacitinib | Measure Up 1 (NCT03569293), Measure Up 2 (NCT03607422), AD Up (NCT03568318) |
| Nemolizumab | ARCADIA 1 (NCT03985943), ARCADIA 2 (NCT03989349) — FDA-approved for AD Jan 2025 |

### Plaque Psoriasis (7 drugs, 17 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Guselkumab | VOYAGE 1 (NCT02207231), VOYAGE 2 (NCT02207244) |
| Risankizumab | UltIMMa-1 (NCT02684370), UltIMMa-2 (NCT02684357) |
| Tildrakizumab | reSURFACE 1 (NCT01722331), reSURFACE 2 (NCT01729754) |
| Bimekizumab | BE VIVID (NCT03370133), BE SURE (NCT03412747), BE RADIANT (NCT03536884) |
| Deucravacitinib | POETYK-PSO-1 (NCT03624127), POETYK-PSO-2 (NCT03611751) |
| Ixekizumab | UNCOVER-1 (NCT01474512), UNCOVER-2 (NCT01597245), UNCOVER-3 (NCT01646177) — FDA-approved 2016 |
| Certolizumab | CIMPASI-1 (NCT02326298), CIMPASI-2 (NCT02326272), CIMPACT (NCT02346240) — FDA-approved 2018 |

Excluded during curation (not pivotal registrational trials): NCT02203032
"NAVIGATE" (guselkumab ustekinumab-inadequate-responder switch study),
NCT03162796 "Discover-1" (guselkumab, but this trial is actually Psoriatic
Arthritis — a different indication), NCT04102007 (single-arm open-label
risankizumab post-switch study).

### Hidradenitis Suppurativa (3 drugs, 6 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Adalimumab | PIONEER I (NCT01468207), PIONEER II (NCT01468233) |
| Secukinumab | SUNSHINE (NCT03713619), SUNRISE (NCT03713632) |
| Bimekizumab | BE HEARD I (NCT04242446), BE HEARD II (NCT04242498) |

### Alopecia Areata (3 drugs, 5 trials)

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
| Remibrutinib | REMIX-1 (NCT05030311), REMIX-2 (NCT05032157) — FDA-approved (Rhapsido, NDA 218436) 2025-09-30. Excluded as non-pivotal: NCT05048342 "BISCUIT" (Japan-only open-label regional bridging study, n=71), NCT06868212 "RECLAIM" (active-comparator vs. dupilumab, not yet complete) |

### Prurigo Nodularis (2 drugs, 4 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | PRIME (NCT04183335), PRIME2 (NCT04202679) — FDA-approved for PN Sept 2022 |
| Nemolizumab | OLYMPIA 1 (NCT04501679), OLYMPIA 2 (NCT04501666) — FDA-approved for PN Aug 2024 |

CT.gov maps these trials' condition to "Neurodermatitis" (a MeSH-adjacent
synonym), not the literal string "Prurigo Nodularis" — confirmed as the
correct indication via each trial's title and the sponsor's own registry
page, not assumed from the condition field alone.

### Vitiligo (1 drug, 2 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Ruxolitinib (topical cream) | TRuE-V1 (NCT04052425), TRuE-V2 (NCT04057573) — FDA-approved (Opzelura) July 2022 |

Thin (1 drug) but real: Opzelura cream is the only FDA-approved
repigmentation therapy for vitiligo as of this pass. A separate,
previously-investigated 3-drug **oral**-JAK systemic Phase III program
(ritlecitinib "Tranquillo", upadacitinib "Viti-Up", povorcitinib
"STOP-V1/V2") remains excluded: every trial in that program still has
zero posted results — none can populate the `adverse_events` field group
yet.

Ruxolitinib the ingredient also covers Jakafi/Jakafi XR (oral tablets,
NDA 202192/217180, oncology/GVHD use) under separate NDAs from Opzelura
(NDA 215309, this atlas's drug) — `exclusivity.orange_book` is pinned to
215309 specifically, but openFDA's FAERS `medicinalproduct` search field
can't distinguish formulation/route, so `real_world_safety.faers_summary`
for Ruxolitinib is a mix of Opzelura and Jakafi(XR) reports, not
Opzelura-only — a real, documented limitation of FAERS's report-level
data, not a pipeline bug.

### Chronic Hand Eczema (1 drug, 3 trials)

| Drug | Pivotal Phase III trials |
|---|---|
| Delgocitinib (topical cream) | DELTA 1 (NCT04871711), DELTA 2 (NCT04872101), DELTA TEEN (NCT05355818) — FDA-approved (Anzupgo, NDA 219155) 2025-07-23 |

DELTA 1/2 are the twin global vehicle-controlled adult pivotal trials;
DELTA TEEN extends the same registrational program to adolescents 12-17
(vehicle-controlled, not an open-label extension). Excluded as non-pivotal:
NCT05259722 "DELTA FORCE" (active-comparator vs. Toctino/alitretinoin, not
placebo/vehicle-controlled), NCT04949841 (open-label extension of DELTA
1/2), NCT06004050 (Phase III, no posted results yet).

### Bullous Pemphigoid (1 drug, 1 trial)

| Drug | Pivotal Phase III trials |
|---|---|
| Dupilumab | LIBERTY-BP (NCT04206553) — Phase 2/3 combined trial, n=106; BP is a real, separate FDA-approved indication for dupilumab (confirmed via the live openFDA label, section 1.8) |

Thinnest indication in the atlas (1 drug, 1 trial), but real and verified —
same precedent as Vitiligo's inclusion. A drug initially proposed as a
candidate for this indication, rilzabrutinib (Wayrilz), does **not** hold
up: it has zero CT.gov trials for Bullous Pemphigoid and its FDA label
indications are Immune Thrombocytopenia only — a wrong lead, not a real BP
drug. Also checked and excluded: efgartigimod (Vyvgart) has a completed BP
Phase 2/3 trial (NCT05267600) but its FDA label indications are gMG and
CIDP only, not BP.

### Generalized Pustular Psoriasis (1 drug, 1 trial)

| Drug | Pivotal Phase III trials |
|---|---|
| Spesolimab | Effisayil™ 1 (NCT03782792) — Phase 2 pivotal trial, n=53; FDA-approved (Spevigo, BLA761244) Sept 2022 |

Officially a Phase II trial (GPP is an ultra-rare orphan indication —
randomized placebo-controlled trials of this size are the norm for its
approvals), same "genuine pivotal trial, not literal-Phase-3-only"
precedent already established by Bullous Pemphigoid's Phase 2/3 LIBERTY-BP
above. Randomized, double-blind, placebo-controlled, results posted —
confirmed as the real basis for Spevigo's FDA approval via the live
openFDA label (section 1). Checked and excluded as non-pivotal for GPP:
NCT04399837 (Phase 2 flare-prevention trial, not the registrational
flare-treatment trial) and the Palmoplantar Pustulosis extension of the
same program (NCT03135548, NCT04493424 — different indication, and the
long-term trial was terminated). Spevigo's Purple Book applicant is LEO
Pharma A/S, not trial-sponsor Boehringer Ingelheim — BI ran the pivotal
trial and originated the molecule, but licensed US commercial/regulatory
rights to LEO Pharma before approval; a real BLA-holder-vs-sponsor split,
not a data error. Also checked as candidates and excluded: Netherton
Syndrome (multiple real Phase 2/3 programs in progress — QRX003, spesolimab,
dupilumab — but zero FDA-approved systemic therapy exists yet, so no
pivotal trial qualifies) and Discoid/Cutaneous Lupus Erythematosus
(anifrolumab, litifilimab, enpatoran trials all still active/recruiting
with no posted results and no CLE/DLE-specific FDA approval yet).
Pemphigus Vulgaris was also checked: Rituximab is genuinely FDA-approved
for the indication (label section 1.5), but its pivotal trial (NCT02383589,
"Ritux 3") is Rituximab-vs-Mycophenolate-Mofetil — an active-comparator
head-to-head, not placebo/vehicle-controlled — so it fails this atlas's own
inclusion bar and was excluded, not added.

Every NCT ID above was pulled live from the API during curation — none
were guessed or reused from memory (see `data/trials/*.json` →
`source_url` on every field for the exact API call), and every drug/trial
inclusion followed the same hand-curation discipline throughout: query by
indication + intervention, then individually fetch and confirm each
candidate is a real pivotal arm (not a comparator, switch study,
active-comparator head-to-head, regional bridging study, or
wrong-indication trial) before adding it.

## Data model

One JSON file per trial at `data/trials/<NCT_ID>.json` (**schema v2**),
organized into 9 field groups (39 fields). Every field value is an object,
never a bare scalar:

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
  `null` and stays `null` until human QA can fill it — this pipeline never
  guesses a plausible-sounding clinical number.
- `openfda_faers` — openFDA adverse-event API, drug-level real-world
  report summary (`real_world_safety.faers_summary`).
- `orange_book` — FDA Orange Book data (via openFDA's mirror),
  small-molecule NDAs only (`exclusivity.orange_book`, and the
  `exclusivity.regulatory_application` join key).
- `purple_book` — FDA Purple Book live search table, biologic BLAs only
  (`exclusivity.purple_book`, and the join key for biologics).

### Schema v2: typed, atomic values

Every `value` is a typed structure that can be filtered and compared
directly — no re-parsing prose at read time. The full field-by-field
reference is `docs/SCHEMA.md` (human-readable) / `schema/trial.schema.json`
(JSON Schema draft-07) — both are static snapshots generated from
`atlas/schema.py` in `kolai-website`, which owns the spec now. The schema
is indication-agnostic: adding 8 more indications beyond the original AD
set required zero schema changes — `severity_definition`/severity criteria
and the endpoint-measure fields are free text sized for any indication's
own severity/endpoint vocabulary (PASI/sPGA for psoriasis, HiSCR/IHS4 for
HS, SALT for AA, UAS7 for CSU, IGA PN-S/Worst Itch NRS for PN, VASI for
vitiligo, and so on).

The one atomic building block is **`ScoreCriterion`** — a threshold on a
named clinical scale (`{scale, metric, comparator, value, unit,
assessed_at, …}`) — reused by eligibility severity thresholds, endpoint
responder definitions, endpoint subgroups, rescue triggers, and flare
definitions. So "EASI-75 at week 16" is the same row shape wherever it
occurs. What was free text in v1 is typed in v2 (full list in
`docs/SCHEMA.md`); the v1 prose survives as provenance in `source_excerpt`
(or an endpoint's `verbatim` / an intervention's `description`) — it is
never the queryable value. `kolai-website`'s test suite proves the v1→v2
migration is lossless (deterministic, byte-identical on re-run, every v1
fact traceable in the v2 value, every gap preserved, nothing invented).

Cross-source field groups, now populated for every one of the 23 drugs in
the atlas:

- `real_world_safety.faers_summary` — openFDA FAERS report counts,
  seriousness breakdown, top MedDRA reaction terms, reports by year.
  Report volume varies enormously with market exposure time (Adalimumab:
  46,072 reports; Deuruxolitinib, approved 2025: 1 report) — a real
  finding, not an error.
- `exclusivity.regulatory_application` — the NDA/BLA number, the join key
  the other two need.
- `exclusivity.orange_book` — products, patents (number, expiry, use code,
  claims), exclusivity codes with dates; NDAs only (9 small molecules).
- `exclusivity.purple_book` — licensure, BPCIA reference-product /
  interchangeable / orphan exclusivity dates, biosimilars; BLAs only
  (14 biologics; separate shape from Orange Book because BLA exclusivity
  rules differ).

**Every non-`ctgov_api` value here is machine/LLM-extracted, not
hand-verified.** `reviewed_by` is `null` and `confidence` is `< 1.0` on all
of them — they still need the human clinical QA pass (captain + Garvita)
called for in the project brief before being treated as authoritative for
publication.

**Paywalled full-text journal papers were explicitly in scope for the
original 5-drug AD pass.** Each of those trials' primary results
publication was identified (via CT.gov's own `referencesModule` where
present, or PubMed search by trial acronym/author/journal otherwise,
always confirmed against the live API) and a direct fetch was attempted
for every one. Every publisher/repository host tried — NEJM, Wiley, JAMA
Network, JAAD/Elsevier, and a university repository mirror — sits behind a
Cloudflare bot-challenge, one of which escalates to an interactive "Verify
you are human" Turnstile CAPTCHA; this pipeline does not solve that
(defeating an anti-bot check to scrape paywalled content is out of bounds
regardless of the paywall). Two other routes did work: **PMC** (free full
text for 4 of the 13 unique primary-publication PMIDs, via NCBI's
`elink`/`efetch` — not Cloudflare-protected) and **FDA Drugs@FDA
approval-package reviews** (accessdata.fda.gov, also not
Cloudflare-protected, often more granular on protocol detail than the
paper itself). The 8 indications added after that pass did not repeat this
same paywalled-paper research effort — their `publication_extraction`
fills remain confined to the original 17 AD trials; `needs_extraction`
gaps elsewhere in `design.background_therapy`,
`endpoints.multiplicity_control`, `timing_ops.rescue_therapy`, and
`timing_ops.study_schedule` for the newer indications are a real,
un-worked backlog, not a pipeline limitation.

### Fill status (all 64 trials, 39 fields each — 2496 sourced values)

Fields fully or near-fully filled across every trial (`ctgov_api` for the
identity/population/design/endpoints/timing_ops/adverse_events core,
`openfda_label`/`openfda_faers`/`orange_book`/`purple_book` for the
drug-level cross-source groups): `nct_id`, `trial_name`, `official_title`,
`sponsor`, `phase`, `drug`, `intervention_names`, `intervention_type`,
`condition`, `min_age_years`, `max_age_years`, `sex`, `enrollment_count`,
`study_type`, `allocation`, `intervention_model`, `masking`,
`number_of_arms`, `primary_endpoints`, `secondary_endpoints`,
`start_date`, `primary_completion_date`, `completion_date`,
`serious_adverse_event_rate`, `real_world_safety.faers_summary` (64/64),
`exclusivity.regulatory_application` (64/64).

Fields with real, checkable gaps (numerator = filled, out of 64 trials):

| Field | Filled | Gap reason |
|---|---|---|
| `molecule.mechanism_of_action` | 62/64 | openFDA label lookup miss for 2 trials |
| `molecule.dosing_regimen` | 58/64 | no intervention-description text on file at CT.gov for those trials |
| `population.severity_criteria` | 47/64 | extraction regex catches EASI/IGA/BSA (AD) and most PASI/sPGA (psoriasis) phrasing reliably; HiSCR/IHS4 (HS), SALT (AA), UAS7 (CSU), GPPGA/GPPASI (GPP), and some newer trials' eligibility-criteria phrasing not yet caught |
| `design.background_therapy` | 17/64 | curated per-trial excerpts exist only for the original AD program |
| `endpoints.multiplicity_control` | 16/64 | same — curated only for the original AD program |
| `timing_ops.study_schedule` | 15/64 | full per-visit schedule lives only in multi-page PDF tables not reliably machine-extractable; curated cadence exists only for the original AD program |
| `timing_ops.rescue_therapy` | 14/64 | curated only for the original AD program |
| `adverse_events.death_rate` | 54/64 | some trials report zero deaths as a genuine null-count edge case in CT.gov's `resultsSection`, not a missing value |
| `adverse_events.discontinuation_due_to_ae_rate` | 61/64 | CT.gov `resultsSection` gap for a few trials |
| `adverse_events.most_common_adverse_events` | 63/64 | CT.gov `resultsSection` gap for 1 trial |
| `exclusivity.orange_book` | 21/64 | only the 9 NDA small-molecule drugs' trials get this field (BLA biologics use `purple_book` instead) |
| `exclusivity.purple_book` | 43/64 | only the 14 BLA biologic drugs' trials get this field (NDA small molecules use `orange_book` instead) |

**2199 of 2496 sourced values are filled with real data (88.1%); 297
remain `needs_extraction`** — see `sources.csv` for the per-trial,
per-field breakdown. Every non-`ctgov_api` fill was produced by
LLM-assisted reading of a real, cited source (CT.gov free text, a
downloaded protocol/SAP PDF, CT.gov's structured results tables, a PMC
full-text paper, an FDA approval-package review, the openFDA label, or a
live openFDA/FDA registry query) — `kolai-website`'s pipeline records
exactly which excerpt backs which field — and every one is
`reviewed_by: null` pending the human clinical QA pass (captain + Garvita)
before it's treated as authoritative for publication.

## The files in this repo

This repo holds only the pipeline's output — no code, no tests:

- `data/trials/<NCT_ID>.json` — one file per trial (64 files), the
  sourced-value format described above (schema v2).
- `trials.csv` — one row per trial, one column per field (the field's
  `value`, JSON-encoded when structured; `needs_extraction` fields blank).
- `sources.csv` — one row per sourced value: `nct_id`, `field`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`,
  `reviewed_by`, `confidence`. 64 trials × 39 fields = 2496 rows.
- `endpoints.csv` — one row per outcome measure × criterion: `measure_type`,
  `scale`, `timepoints`, `analysis_population`, and the `ScoreCriterion`
  columns, so "EASI-75 responders at week 16" is a column filter.
- `severity_criteria.csv` — one row per baseline-severity `ScoreCriterion`.
- `adverse_event_rates.csv` — one row per (trial, arm, measure[, MedDRA
  term]).
- `docs/SCHEMA.md` / `schema/trial.schema.json` — static snapshots of the
  schema v2 field reference (see the note at the top of each file).

To regenerate or extend this data (fetch, extraction, migration, and build
scripts, the schema spec, and their test suite) see `kolai-website`, which
owns the pipeline this data is exported from.

## Out of scope for this pass

- The human QA pass on top of the LLM-assisted extraction (captain +
  Garvita review of every non-`ctgov_api` value).
- The 291 fields that remain `needs_extraction` (see the fill-status table
  above) — a mix of genuinely unreachable sources (paywalled papers behind
  Cloudflare, PDF tables that don't extract reliably) and real, un-worked
  backlog (the curated per-trial prose tables — background therapy,
  multiplicity control, rescue therapy, visit schedule — built only for
  the original AD program, not yet extended to the 8 indications added
  since).
- Further indication candidates not yet live-verified (this is explicitly
  an ongoing effort, not a one-shot; each addition to date was checked
  against real ClinicalTrials.gov and openFDA data before being added, not
  assumed).
- AACT bulk-seeding (a possible future bulk source, not integrated here).
- Any change to the atlas portal UI or the `kolai-website` repo.
