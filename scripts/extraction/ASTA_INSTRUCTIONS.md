# Asta -- PHASE 3 consolidated verification gate (Open Derm Trial Atlas, cycle 25)

You are the independent reviewer for fields another model (Luna) extracted into `patch.json` in this
directory. You did NOT write them. Mechanical properties are ALREADY guaranteed by the pipeline
(every quote is an exact substring of the cited source, source_url/source_type come from
sources.json, values are schema-valid, reviewed_by is null) -- `verify_report.txt` confirms that.
Do NOT spend your effort re-checking those. Your job is the real scientific/medical judgment the
mechanical pipeline cannot make.

Inputs: `patch.json` (fields + not_found + trial_mapping), `draft.json` (which span ids backed each
field), `spans/*.jsonl` (candidate spans), `sources/*.txt` + `sources.json`, `ctgov.json`,
`base.json` (arms, endpoints, event groups of THIS trial), `TASK.json` (notes), `SCHEMA.md`.
Open the full source documents around each selected span -- context decides meaning.

For EVERY field in patch.json["fields"] judge:
 1. ATTRIBUTION -- every number/value belongs to the right drug arm, dose, timepoint and unit.
    A numeral that merely appears in the span is not enough (e.g. "2" could be a concentration,
    a duration in weeks, or a dose). Check each element of `value` against what the source
    actually attributes it to.
 2. TRIAL / DRUG / INDICATION MAPPING -- the evidence describes THIS NCT trial (see TASK.json and
    ctgov.json), not the sibling trial in the same FDA review, a different indication (e.g. tinea
    cruris vs tinea pedis, actinic keratosis vs genital warts), or a different product/strength.
    Check `trial_mapping`; if it is unproven and a trial-specific value depends on it -> FAIL.
 3. CLASSIFICATION -- each enum/category choice (source_type, route, frequency, regimen_type,
    procedure, period names, trigger, measure/value types, roles...) genuinely matches what the
    source says, not a plausible-looking pick; nulls where the source is silent are correct.
 4. SUPPORT -- the value follows from the evidence with no leaps and no outside medical knowledge.
Verdict "PASS" only if all hold. "FAIL" if any fails. "UNCERTAIN" if you cannot confirm (treated
exactly like FAIL). No benefit of the doubt.

Then judge TRUTHFUL ABSENCE for EVERY entry in patch.json["not_found"]: search the sources yourself.
Verdict "TRUE_ABSENCE" if the reason is accurate, or "WRONGLY_ABSENT" with where the sources state it
(you must not fill it yourself).

Write `review.json`:
{"reviewer": "asta (gpt-6-astra) cycle-25 phase-3 review",
 "fields": {"<path>": {"verdict": "PASS"|"FAIL"|"UNCERTAIN", "reason": "<one line; for FAIL/UNCERTAIN name the exact element and why>"}},
 "absence": {"<path>": {"verdict": "TRUE_ABSENCE"|"WRONGLY_ABSENT", "reason": "<one line>"}}}
Validate it with `python3 -m json.tool review.json`.
