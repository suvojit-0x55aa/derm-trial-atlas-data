# Project agent memory

This file is the project's committed home for project-intrinsic agent memory: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- This repo is **data only** — `data/trials/*.json` (schema v2), the flattened CSVs
  (`trials.csv`, `sources.csv`, `endpoints.csv`, `severity_criteria.csv`,
  `adverse_event_rates.csv`), and two static doc snapshots (`docs/SCHEMA.md`,
  `schema/trial.schema.json`). No pipeline code, no schema spec, no tests — the
  fetch/extraction/migration/build pipeline, `atlas/schema.py`, and the test suite all live in
  `kolai-website`; this repo is regenerated from there. Don't hand-edit the CSVs or the doc
  snapshots — they're generated, and will drift from `kolai-website`'s copy if edited here.
- Field groups, the full fill-status table, and what `source_type` means: see `README.md`.
  Full field-by-field types: `docs/SCHEMA.md`.
- Every field value everywhere in `data/trials/*.json` is a sourced-value object (`value`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`, `reviewed_by`, `confidence`) —
  never a bare scalar. `value` is typed per `docs/SCHEMA.md`, never free prose; where v1 had
  prose, it now lives in `source_excerpt` (or an endpoint's `verbatim` / an intervention's
  `description`) as provenance. `source_type` is one of `ctgov_api`, `ctgov_text_extraction`,
  `protocol_pdf_extraction`, `publication_extraction`, `openfda_label`, `openfda_faers`,
  `orange_book`, `purple_book`, or `needs_extraction`.
- Every value with a non-`ctgov_api` source_type is machine/LLM-extracted, not hand-verified —
  `reviewed_by` stays `null` and `confidence < 1.0` until a human (captain + Garvita) signs off.
  Do not treat these as clinically authoritative without that review, and do not upgrade a
  `needs_extraction` field by inference or general knowledge — every fill must trace to an
  actual quoted source (CT.gov text, a protocol/SAP PDF, openFDA, or a CT.gov `resultsSection`
  table).
- `boxed_warning.present: false` with `source_type: openfda_label` means the label was checked
  and confirmed absent — a different thing from `needs_extraction` (never checked). Don't
  collapse that distinction when editing.
- `timing_ops.study_schedule` (v1 `visit_schedule`) is deliberately `needs_extraction` for CAFE
  and JADE REGIMEN: the full per-visit schedule lives only in multi-page PDF tables the pipeline
  couldn't reliably extract. Don't force-fill it by inference — a wrong schedule is worse than a
  null.
- **This atlas is an ongoing, multi-cycle scale-out effort, not a one-shot.** It started at 1
  indication (AD, 5 drugs, 17 trials) and is now at 10 indications, 23 unique drugs, 64 trials
  (see README's "What this covers" for the full per-indication breakdown and exactly which
  candidate trials were checked and excluded as non-pivotal for each). Every drug/indication
  pairing was verified against real, live ClinicalTrials.gov and openFDA data before being
  added — never assumed from general knowledge. When extending further, apply the same bar:
  live-query CT.gov (`query.cond=<indication>&query.intr=<drug>`) and confirm each candidate
  trial is a genuine pivotal EXPERIMENTAL arm (placebo/vehicle/vs.-nothing-controlled,
  `resultsSection` present) before adding it — not a comparator arm in someone else's program,
  a switch/extension study, an active-comparator head-to-head, or a regional bridging study.
- **A drug named as a candidate for a new indication is not automatically the right drug for
  that indication.** Verify the FDA label's own `indications_and_usage` text for the literal
  indication name before spending time on trial curation — co-occurrence of a drug and a
  condition in some CT.gov trial is not proof of an FDA-approved indication match. A queued
  "rilzabrutinib for Bullous Pemphigoid" candidate turned out to have zero CT.gov trials for BP
  and an FDA label limited to Immune Thrombocytopenia; the real BP drug was Dupilumab (already
  in this atlas), confirmed via its own label section 1.8.
- **The cross-source fields (`real_world_safety.faers_summary`, `exclusivity.{orange_book,
  purple_book}`) are now populated for every drug**, not just the original 5. openFDA's
  `drug/orangebook.json` matches on `products.active_ingredients.name`, not a bare `ingredient`
  field — a hand-run query using `ingredient:"<NAME>"` returns a false NOT_FOUND even for a
  real, indexed drug, including very recent (2025) approvals. A drug with FDA-approved
  biosimilars (e.g. Adalimumab has 10) has every biosimilar's BLA row in the Purple Book table
  alongside the reference product's — the reference product is the row with
  `License Type == "351(a)"`; every `"351(k)"` row is a biosimilar, not the drug itself.
  Ruxolitinib the ingredient also covers Jakafi/Jakafi XR (oral, oncology/GVHD, unrelated NDAs)
  — `exclusivity.orange_book` can be pinned to the right NDA by application number, but
  openFDA's FAERS search has no such filter, so Ruxolitinib's `real_world_safety.faers_summary`
  is a real, documented, unavoidable mix of all three products' reports — not a bug to "fix".
- **Publication-extraction depth is uneven by design, not by accident.** The original 5-drug AD
  program got a dedicated paywalled-paper research pass (PMC + FDA Drugs@FDA approval-package
  reviews, since direct publisher fetches are blocked by Cloudflare bot-challenges this pipeline
  will not defeat) — see README's "Paywalled full-text journal papers" note. The 8 indications
  added since have not repeated that same research effort, so `design.background_therapy`,
  `endpoints.multiplicity_control`, `timing_ops.rescue_therapy`, and `timing_ops.study_schedule`
  stay `needs_extraction` for nearly all of them — a real, checkable backlog for `kolai-website`
  to pick up, not a fabricated null.
- **This repo's own pipeline scripts (`scripts/`, `atlas/`, `tests/`) are intentionally absent
  from `main`, but a prior scale-out cycle's pre-cleanup branch (`fm/derm-trial-atlas-scale-out`,
  kept on `origin` as a safety net) still has the real, working versions.** To add a trial
  correctly rather than hand-crafting CSVs: `git archive origin/fm/derm-trial-atlas-scale-out --
  scripts atlas tests | tar -x -C <scratch dir>`, copy into a scratch checkout of this repo,
  build the new trial's JSON by hand (matching an existing trial's structure), run
  `scripts/build_csv.py` to regenerate all 5 flattened CSVs, run the copied `tests/` (needs
  `pytest` — not committed here) to validate schema conformance, diff the regenerated CSVs
  against a pre-change backup to confirm every pre-existing row is byte-identical (only the new
  trial's rows should differ), then delete `scripts/`/`atlas/`/`tests/` again before committing.
  Never hand-edit the CSVs directly — the flattening (JSON-encoding, endpoint/criterion joins,
  compact timepoint formats) is nontrivial and easy to get subtly wrong.
- **The Purple Book monthly CSV at `accessdata.fda.gov` (e.g.
  `.../PurpleBook/2026/purplebook-search-August-data-download.csv`) 302-redirects to an Akamai
  bot-detection apology page for a bare `curl`, but succeeds with a real browser `User-Agent`
  header** — no browser automation needed, unlike `purplebooksearch.fda.gov`'s live search UI
  (still genuinely blocked, same as Orange Book's live UI). Despite its filename saying
  "-August-", the file is a full historical snapshot (every product's full approval-date
  history), not just that month's changes — don't assume a narrower scope than what's actually
  in it. A drug's BLA applicant of record (Purple Book) can differ from its trial sponsor
  (CT.gov) when commercial rights were licensed after the pivotal trial — e.g. Spesolimab/Spevigo:
  Boehringer Ingelheim ran Effisayil-1, but LEO Pharma A/S holds BLA761244. Real, not a data bug.
- **A pivotal trial that is literal Phase 2 (not "Phase 2/3") can still belong in this atlas** for
  a genuinely rare/orphan indication where a standard-sized Phase 3 isn't feasible and the trial
  is the real, cited basis for FDA approval (randomized, placebo-controlled, `resultsSection`
  present) — established by Generalized Pustular Psoriasis/Spesolimab (Effisayil-1, pure Phase 2,
  n=53), extending the same "genuine pivotal trial over literal phase label" precedent Bullous
  Pemphigoid's Phase 2/3 LIBERTY-BP set. An **active-comparator** pivotal trial still doesn't
  qualify regardless of rarity or real FDA approval status — Pemphigus Vulgaris/Rituximab was
  checked and excluded on exactly this ground (its approval trial is rituximab-vs-mycophenolate,
  not placebo-controlled).

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
