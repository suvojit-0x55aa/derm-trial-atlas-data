# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.
- **This repo is a pure dataset — no extraction/build scripts live here.** They moved to
  `kolai-website`'s `scripts/atlas/`; that's where to look for or change the pipeline that
  produces `data/trials/*.json`, `trials.csv`, and `sources.csv`. Don't hand-edit the CSVs —
  regenerate them from there.
- Data model, 30-field schema, and fill-status table: see `README.md`.
- Every field value everywhere in `data/trials/*.json` is a sourced-value object (`value`,
  `source_type`, `source_url`, `source_excerpt`, `extracted_by`, `reviewed_by`, `confidence`) —
  never a bare scalar. `source_type` is one of `ctgov_api`, `ctgov_text_extraction`,
  `protocol_pdf_extraction`, `openfda_label`, or `needs_extraction` — see README for what each
  means and how much to trust it.
- Every value with a non-`ctgov_api` source_type is machine/LLM-extracted, not hand-verified —
  `reviewed_by` stays `null` and `confidence < 1.0` until a human (captain + Garvita) signs off.
  Do not treat these as clinically authoritative without that review, and do not upgrade a
  `needs_extraction` field by inference or general knowledge — any future fill must trace to an
  actual quoted source, same as the existing ones.
- `visit_schedule` is deliberately left `needs_extraction` for all 17 trials: the schedule
  lives in multi-page PDF tables that plain-text conversion can't reliably flatten. Don't
  force-fill it from a garbled table extraction — a wrong schedule is worse than a null.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
