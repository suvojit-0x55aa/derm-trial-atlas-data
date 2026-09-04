# Project agent memory

This file is the project's committed home for project-intrinsic agent memory: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- This repo is **data only** — `data/trials/*.json`, `trials.csv`, `sources.csv`. No pipeline
  code, no tests. The fetch/extraction/build pipeline that produces this data (and its test
  suite) lives in `kolai-website`; this repo is regenerated from there. Don't hand-edit
  `trials.csv`/`sources.csv` — they're a flattened view of `data/trials/*.json`, rebuilt by the
  pipeline in `kolai-website`.
- Field groups, the full fill-status table, and what `source_type` means: see `README.md`.
- Every field value everywhere in `data/trials/*.json` is a sourced-value object (`value`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`, `reviewed_by`, `confidence`) —
  never a bare scalar. `source_type` is one of `ctgov_api`, `ctgov_text_extraction`,
  `protocol_pdf_extraction`, `publication_extraction`, `openfda_label`, or `needs_extraction`.
- Every value with a non-`ctgov_api` source_type is machine/LLM-extracted, not hand-verified —
  `reviewed_by` stays `null` and `confidence < 1.0` until a human (captain + Garvita) signs off.
  Do not treat these as clinically authoritative without that review, and do not upgrade a
  `needs_extraction` field by inference or general knowledge — every fill must trace to an
  actual quoted source (CT.gov text, a protocol/SAP PDF, openFDA, or a CT.gov `resultsSection`
  table).
- `boxed_warning: null` with `source_type: openfda_label` means the label was checked and
  confirmed absent — a different thing from `needs_extraction` (never checked). Don't collapse
  that distinction when editing.
- `visit_schedule` is deliberately `needs_extraction` for CAFE and JADE REGIMEN: the full
  per-visit schedule lives only in multi-page PDF tables the pipeline couldn't reliably extract.
  Don't force-fill it by inference — a wrong schedule is worse than a null.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
