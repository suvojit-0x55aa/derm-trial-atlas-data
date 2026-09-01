# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.
- Pipeline overview, commands, and the 30-field schema + fill status table: see `README.md`.
- Every field value everywhere in `data/trials/*.json` is a sourced-value object (`value`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`, `reviewed_by`, `confidence`) —
  never a bare scalar. `source_type` is one of `ctgov_api`, `ctgov_text_extraction`,
  `protocol_pdf_extraction`, `openfda_label`, or `needs_extraction` — see README for what each
  means and how much to trust it.
- Pipeline runs in 3 stages, in order: `fetch_trials.py` (clean structured CT.gov fields) →
  `enrich_needs_extraction.py` (LLM-assisted second pass over free text/PDFs/openFDA) →
  `build_csv.py` (flatten to CSV). Re-running `fetch_trials.py` resets a trial file to its
  stage-1 baseline, so re-run `enrich_needs_extraction.py` after it.
- Every value with a non-`ctgov_api` source_type is machine/LLM-extracted, not hand-verified —
  `reviewed_by` stays `null` and `confidence < 1.0` until a human (captain + Garvita) signs off.
  Do not treat these as clinically authoritative without that review, and do not upgrade a
  `needs_extraction` field by inference or general knowledge — every fill must trace to an
  actual quoted source (CT.gov text, a downloaded protocol/SAP PDF, or openFDA).
- `visit_schedule` is deliberately left `needs_extraction` for all 17 trials: the schedule
  lives in multi-page PDF tables that plain-text conversion can't reliably flatten. Don't try
  to force-fill it from a garbled `pdftotext` table — a wrong schedule is worse than a null.
- `RESCUE_RULES`, `MULTIPLICITY_RULES`, and `BACKGROUND_THERAPY_PDF` in
  `enrich_needs_extraction.py` are hand-curated per-trial excerpts (not live-parsed at runtime)
  because automated PDF-table/section extraction wasn't reliable enough — each excerpt was
  produced by downloading the trial's PDF via `fetch_protocol_docs.py`, converting with
  `pdftotext -layout`, and reading the relevant section. If a trial's protocol gets amended,
  re-run `fetch_protocol_docs.py` and re-check the excerpt against the new text.
- The trial list in `scripts/fetch_trials.py::TRIALS` (which NCT IDs belong to which drug) was
  curated by hand against the live API, not derived by a query filter — if a drug's pivotal
  program changes or a new trial needs adding, update that dict directly rather than
  re-deriving it from a single API query (comparator-arm trials from other drugs' programs can
  otherwise get miscategorized).

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
