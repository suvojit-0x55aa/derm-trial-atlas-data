# Project agent memory

This file is the project's committed home for project-intrinsic agent memory: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.
- Pipeline overview, commands, and the full field-group + fill-status tables: see `README.md`.
  The pipeline (fetch, extract, build) lives in this repo's `scripts/` — it does not live in
  `kolai-website` or anywhere else. Don't hand-edit `trials.csv`/`sources.csv`; regenerate them
  with `scripts/build_csv.py`.
- Every field value everywhere in `data/trials/*.json` is a sourced-value object (`value`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`, `reviewed_by`, `confidence`) —
  never a bare scalar. `source_type` is one of `ctgov_api`, `ctgov_text_extraction`,
  `protocol_pdf_extraction`, `publication_extraction`, `openfda_label`, `openfda_faers`,
  `orange_book`, `purple_book`, or `needs_extraction` — see README for what each means and how
  much to trust it.
- **Schema v2 (typed values) — `atlas/schema.py` is the single source of truth.** `value` is never
  free prose: each concept is decomposed into atomic typed sub-fields (the shared
  `ScoreCriterion` row is the building block), and prose survives only as provenance in
  `source_excerpt` / an endpoint's `verbatim` / an intervention's `description`. Don't add a
  free-text `notes`-style catch-all; add typed fields to the spec instead, then run
  `scripts/export_schema.py` (regenerates `docs/SCHEMA.md` + `schema/trial.schema.json`; tests
  fail if they drift) and `python3 -m unittest discover -s tests -t .`.
- `tests/fixtures/v1_trials/` is the frozen v1 snapshot that `tests/test_migration_lossless.py`
  migrates and compares against `data/trials/` (determinism, fact coverage, gaps preserved).
  If a parser or curated table changes, regenerate the data by copying the fixtures back over
  `data/trials/` and re-running `scripts/migrate_v1_to_v2.py` — never hand-edit v2 files.
- The four LLM-summarised prose fields (background therapy, multiplicity, schedule, rescue) are
  structured by hand-curated per-trial tables in `atlas/curated_*.py` (same pattern as the
  curated excerpts in the enrich scripts); the regular text (severity criteria, the 358 CT.gov
  endpoint titles, dosing descriptions, FDA label MoA/boxed warning, ages, dates) is parsed by
  deterministic code in `atlas/*.py`. A new trial's prose needs a curated entry or the migration
  raises `KeyError` naming the trial.
- New-source builders (`atlas/sources/faers.py`, `orange_book.py`, `purple_book.py`) turn raw
  API/file rows into schema-valid values; the exact shapes they expect are the real captured
  rows in `tests/fixtures/sources/`. The NDA/BLA join key lives in
  `atlas/regulatory_applications.py` (hand-curated, like `TRIALS`).
- Pipeline runs in 8 stages, in order (stages 2-4 refuse to run on a v2 record; re-run stage 1
  to reset to v1 first; stages 6-7 only touch `real_world_safety`/`exclusivity` and don't
  require 2-4 to have run):
  1. `fetch_trials.py` — clean structured CT.gov fields (identity/molecule/population/design/
     endpoints/timing_ops skeleton).
  2. `enrich_needs_extraction.py` — LLM-assisted second pass over CT.gov free text, protocol/
     SAP PDFs, and openFDA.
  3. `fetch_adverse_events.py` — adds the `adverse_events` group from CT.gov's structured
     `resultsSection` (adverse-event tables, participant-flow dropout reasons) and openFDA's
     `boxed_warning`.
  4. `enrich_publications.py` — hand-curated excerpts from PMC full-text papers and FDA
     Drugs@FDA approval-package reviews, for the fields nothing else reached.
  5. `migrate_v1_to_v2.py` — typed schema v2, validated (idempotent); also sets
     `exclusivity.regulatory_application` from `atlas/regulatory_applications.py`, which stage 7
     uses to pick the right registry.
  6. `fetch_faers.py` / `fetch_orange_book.py` / `fetch_purple_book.py` — live-fetch and stage
     one schema-shaped sourced value per drug under `data/_raw_staging/<source>/`.
  7. `apply_source_data.py` — folds the staged values into every trial of that drug's
     `real_world_safety.faers_summary` and `exclusivity.{orange_book,purple_book}`.
  8. `build_csv.py` — flatten every trial JSON to `trials.csv`, `sources.csv`, `endpoints.csv`,
     `severity_criteria.csv`, `adverse_event_rates.csv`.
  Re-running `fetch_trials.py` resets a trial file to its stage-1 baseline, so re-run stages
  2-7 after it before rebuilding the CSVs.
- Every value with a non-`ctgov_api` source_type is machine/LLM-extracted, not hand-verified —
  `reviewed_by` stays `null` and `confidence < 1.0` until a human (captain + Garvita) signs off.
  Do not treat these as clinically authoritative without that review, and do not upgrade a
  `needs_extraction` field by inference or general knowledge — every fill must trace to an
  actual quoted source (CT.gov text, a downloaded protocol/SAP PDF, openFDA, or a CT.gov
  `resultsSection` table).
- `timing_ops.study_schedule` (v1 `visit_schedule`) holds the trial's period structure and visit
  *cadence*/key weeks, never a per-visit assessment table (`full_visit_table_available` is
  `false` everywhere): that table lives in multi-page PDF tables that plain-text conversion
  can't reliably flatten. Don't try to force-fill it from a garbled `pdftotext` table — a wrong
  schedule is worse than a null (CAFE and JADE REGIMEN stay `needs_extraction`).
- **Paywalled full-text journal papers**: every publisher/repository host tried (NEJM, Wiley,
  JAMA Network, JAAD/Elsevier, a university repository mirror) sits behind a Cloudflare
  bot-challenge, one of which escalates to an interactive CAPTCHA that this pipeline will not
  solve. Two routes around that did work and are used in `enrich_publications.py`: PMC (via
  NCBI's `elink`/`efetch`, not Cloudflare-protected — had free full text for 4 of 13 primary
  papers) and FDA Drugs@FDA approval-package reviews (accessdata.fda.gov, also not
  Cloudflare-protected, and often more granular on protocol detail than the paper itself). Only
  `protocolSection.referencesModule.references[]` with `type: "RESULT"` reliably names a
  trial's primary paper on CT.gov (true for SOLO 1/2 only, out of these 17); for the rest, the
  PMID/DOI was found by PubMed search (trial acronym + drug + journal/author), confirmed against
  the live API — see `enrich_publications.py`'s module docstring for the full per-trial
  breakdown, including which fields are still `needs_extraction` after this and exactly why.
- `RESCUE_RULES`, `MULTIPLICITY_RULES`, and `BACKGROUND_THERAPY_PDF` in
  `enrich_needs_extraction.py` are hand-curated per-trial excerpts (not live-parsed at runtime)
  because automated PDF-table/section extraction wasn't reliable enough — each excerpt was
  produced by downloading the trial's PDF via `fetch_protocol_docs.py`, converting with
  `pdftotext -layout`, and reading the relevant section. If a trial's protocol gets amended,
  re-run `fetch_protocol_docs.py` and re-check the excerpt against the new text.
- `adverse_events` fields are computed directly from CT.gov's structured `resultsSection`
  (`adverseEventsModule`, `participantFlowModule`) — arithmetic over API counts, not free-text
  parsing — so they're `ctgov_api`, not `ctgov_text_extraction`, even though
  `scripts/fetch_adverse_events.py` does the compute. `boxed_warning` distinguishes a confirmed
  absence (v2 `value.present: false` with `source_type: openfda_label`, `source_excerpt` says
  "checked, none present") from `needs_extraction` (never checked) — don't collapse that
  distinction when editing.
- `enrich_publications.py`'s excerpts are hand-curated (like `enrich_needs_extraction.py`'s),
  not live-parsed: the source PDFs/XML were downloaded and read by hand, and only the final
  excerpt text is committed. To re-verify or extend one, re-download from the field's
  `source_url` and re-check the quoted section — an FDA Drugs@FDA TOC page
  (`accessdata.fda.gov/drugsatfda_docs/nda/<year>/<appnum>Orig1s000TOC.html`) builds its PDF
  filenames in client-side JS (`var pdfBaseName` + a flag like `medR`/`multidisciplineR`/
  `integratedR` in `pdfFiles`), so `curl`/`grep` on the raw HTML won't find the link directly —
  read the `pdfFiles`/`pdfBaseName` JS variables in the page source to build the URL by hand.
- The trial list in `scripts/fetch_trials.py::TRIALS` (which NCT IDs belong to which drug) was
  curated by hand against the live API, not derived by a query filter — if a drug's pivotal
  program changes or a new trial needs adding, update that dict directly rather than
  re-deriving it from a single API query (comparator-arm trials from other drugs' programs can
  otherwise get miscategorized). `TRIALS` is now assembled from 7 per-indication dicts
  (`AD_TRIALS`, `PSORIASIS_TRIALS`, `HS_TRIALS`, `AA_TRIALS`, `CSU_TRIALS`,
  `PRURIGO_NODULARIS_TRIALS`, `VITILIGO_TRIALS`) — add the next indication as its own dict and
  merge it in, don't grow one flat dict. An indication doesn't have to be a one-shot addition:
  a drug already covered can also gain trials in a later pass (e.g. AD went from 5 to 6 drugs,
  Psoriasis from 5 to 7, when Nemolizumab/Ixekizumab/Certolizumab were added on 2026-09-05) —
  re-check `query.cond=<indication>&query.intr=<drug>` for a covered indication's other
  FDA-approved drugs whenever scaling out further, not just brand-new indications.
- **The schema (7 field groups, 35 fields, indication-agnostic) needs no changes to add a new
  indication.** Confirmed for Psoriasis/HS/AA/CSU/Prurigo Nodularis/Vitiligo: `severity_definition`
  and `primary_endpoint_measure`/`secondary_endpoint_measures` are free text, not AD-specific typed
  fields — a new indication's own severity/endpoint vocabulary (PASI/sPGA for psoriasis,
  HiSCR/IHS4 for HS, SALT for AA, UAS7 for CSU, IGA PN-S/Worst Itch NRS for PN, VASI/F-VASI/T-VASI
  for vitiligo) just goes in the same two fields. The `extract_severity_and_bg` regex in
  `enrich_needs_extraction.py` was extended to also recognize these terms; it still won't catch
  every trial's exact eligibility-criteria phrasing (a real per-trial-curation gap, not a code
  bug) — see README's fill-status note for the running total of new trials.
- When a trial's `design.background_therapy_rule` gets auto-filled by
  `enrich_needs_extraction.py::extract_bg_from_tcs_arm` (not the `BACKGROUND_THERAPY_PDF`/
  `RESCUE_RULES`/`MULTIPLICITY_RULES` curated dicts), `migrate_v1_to_v2.py` still requires a
  matching entry in `atlas/curated_background.py`'s `BACKGROUND_THERAPY` table or it raises
  `KeyError` — this path fires whenever CT.gov's own arm-intervention text is specific enough to
  read as a real value (not `needs_extraction`), independent of whether a curated excerpt exists.
  Check for this specifically after adding trials: run `migrate_v1_to_v2.py`, and if it raises,
  add a `_base(...)` entry to the relevant `atlas/curated_*.py` table built from the same
  `source_excerpt` text already on the trial record (never invent detail the source doesn't
  carry — see `PRIME_TOPICAL` in `curated_background.py` for the pattern: a
  `standardized_background_topical` entry with `recommended_agents` left empty because CT.gov's
  API text alone didn't specify strengths/potencies).
- **`scripts/fetch_faers.py` was silently reverted to a pre-schema-v2 version at some point**
  (same rebase-loss pattern as Orange Book's `6e2674d` fix, but this one wasn't caught) — it
  staged only `total_report_count`/`top_reactions` instead of the full schema-v2-shaped value
  (`serious_reports`/`death_reports`/`hospitalization_reports`/`life_threatening_reports`/
  `disability_reports`/`top_serious_reactions`/`reports_by_year`/`receivedate_from`/
  `receivedate_to` that `data/trials/*.json` actually carries and `apply_source_data.py`'s
  docstring assumes). Fixed 2026-09-05 by rewriting it to do the same 9-query-per-drug fetch
  `atlas/sources/faers.py`'s docstring describes (`_quote_search` keeps `+`/`:`/`"` literal —
  see the openFDA `+`-encoding sharp edge below). If a future diff of `data/trials/*.json`'s
  `real_world_safety.faers_summary` shows plausible-but-wrong-shaped data after a re-run,
  compare `fetch_faers.py` against a committed trial file's actual shape first — this class of
  drift is real and has happened twice for this repo's cross-source scripts.
  One more edge worth knowing: querying openFDA for a subset (e.g. `serious:1`) on a drug with
  very few total reports can itself return a genuine "no matches" 404 — that means 0 for that
  seriousness flag, not `None`/unknown; `fetch_faers.py` coerces the 404-as-None only for these
  AND-filtered subset queries (never for the base unfiltered query, where no results really does
  mean "no FAERS history for this drug at all").
- **A drug's FAERS/Orange Book/Purple Book data doesn't attach until `atlas/regulatory_applications.py`
  has an entry for it** — `apply_source_data.py` reads `exclusivity.regulatory_application.value.registry`
  to pick orange_book vs purple_book, and that field is set by `atlas.migrate` from
  `regulatory_applications.py`'s `APPLICATIONS` dict at v1→v2 migration time. Since
  `migrate_v1_to_v2.py` is idempotent (skips already-v2 files), adding a NEW drug after trials
  are already migrated means editing `regulatory_application` directly on those trial files (a
  short one-off script, not a full re-migration) before re-running `apply_source_data.py` — see
  git history around 2026-09-05 for the pattern.
- **Ruxolitinib is two unrelated drugs sharing one ingredient name**: Opzelura (topical cream,
  NDA 215309, this atlas's vitiligo/AD drug) and Jakafi/Jakafi XR (oral tablets, NDA
  202192/217180, oncology/GVHD — not in this atlas at all). Orange Book: `fetch_orange_book.py`'s
  `DRUGS` dict supports a `(ingredient, application_number)` tuple form specifically to pin the
  query to 215309 and drop the other two applications' rows before they merge into one record.
  FAERS: openFDA's `medicinalproduct` search field carries no formulation/route distinction, so
  this filter trick doesn't exist there — Ruxolitinib's `real_world_safety.faers_summary` is a
  real, documented, unavoidable mix of all three products' reports (see README's Vitiligo
  section). Don't try to "fix" the FAERS numbers down to Opzelura-only; there is no query that
  can do that with the data FAERS exposes.
- **Re-running `fetch_trials.py` against the full `TRIALS` dict resets every trial to baseline,
  including previously hand-curated trials** — always diff `data/trials/*.json` against the
  committed version afterward and restore any file whose only diff is content that used to be
  hand-curated (rescue_therapy_rules, endpoint_hierarchy_multiplicity, etc., populated by
  `enrich_needs_extraction.py`'s/`enrich_publications.py`'s hardcoded per-NCT-ID dicts) before
  those enrichment scripts re-run — re-running the full stage 1-4 pipeline in order does
  correctly reproduce hand-curated content (the excerpts are hardcoded by NCT ID, not re-derived
  from live external state), but the `extracted_by` attribution string for early trials has
  drifted from an earlier pass in ways unrelated to any single agent's edits — check for that
  specific (harmless, cosmetic) diff before assuming a real regression.
- **Cross-source data (FAERS, Orange Book, Purple Book)** is fetched by `scripts/fetch_faers.py`,
  `scripts/fetch_purple_book.py`, and `scripts/fetch_orange_book.py` (staged under
  `data/_raw_staging/<source>/<drug>.json`, already schema-shaped) and folded into every trial's
  `real_world_safety.faers_summary` / `exclusivity.{orange_book,purple_book}` by
  `scripts/apply_source_data.py` — see README's "Cross-source data" section for per-source
  status. Orange Book and Purple Book are separate parsers by design — different file shapes and
  exclusivity rules (NDA patent law vs. BLA/BPCIA biologic exclusivity) — never merge them into
  one parser. Two sharp edges hit while building these, worth knowing before re-touching them:
  - openFDA's query syntax needs a **literal** `+` as its AND/space operator — percent-encoding
    it (`urllib.parse.quote()`'s default behavior) makes openFDA treat it as a literal plus-sign
    search character instead, so a filtered query like `...+AND+serious:1` silently matches
    *nothing* rather than erroring. `fetch_faers.py::_quote_search` keeps `+`, `:`, and `"`
    unescaped for exactly this reason — don't "clean up" that safe-chars list.
  - A drug with FDA-approved biosimilars (e.g. Adalimumab has 10) has *every* biosimilar's BLA
    row in the Purple Book table alongside the reference product's — picking the first matched
    row blindly surfaces a biosimilar (e.g. "Abrilada") instead of the actual reference product
    (Humira). Always filter to `License Type == "351(a)"` for the primary record and route every
    `"351(k)"` row into that record's own `biosimilars` list (see
    `fetch_purple_book.py::build_purple_book_value`).
  - `atlas/sources/orange_book.py` and `purple_book.py`'s builders are shaped for the *file-download*
    (tilde/CSV) versions of these sources; the live API/page versions this repo actually fetches
    from use different column names and date formats (confirmed on real rows) — the fetch scripts
    build the schema shape directly rather than forcing a mismatch through those builders.
  - openFDA's `drug/orangebook.json` matches on `products.active_ingredients.name`, not a bare
    `ingredient` field — a hand-run query using `ingredient:"<NAME>"` returns a false NOT_FOUND
    even for a real, indexed drug (confirmed on Remibrutinib/Delgocitinib, both approved
    2025-07/2025-09: `fetch_orange_book.py`'s actual query worked immediately once run; a manual
    `ingredient:` query first suggested, wrongly, that openFDA's Orange Book mirror hadn't
    indexed them yet). Trust `fetch_orange_book.py`'s own query shape, not an ad hoc one, before
    concluding a recent NDA is genuinely unindexed.
  - A drug named as a candidate for a new indication is not automatically the right drug for that
    indication — verify the FDA label's own indications section, not just that the drug and
    condition co-occur in some CT.gov trial. A queued "rilzabrutinib for Bullous Pemphigoid"
    candidate turned out to have zero CT.gov trials for BP and an FDA label limited to Immune
    Thrombocytopenia; the real BP drug was Dupilumab (already in this atlas), confirmed via its
    own label section 1.8. Checking the openFDA label's `indications_and_usage` text for the
    literal indication name is the fast, reliable check before spending time on trial curation.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
