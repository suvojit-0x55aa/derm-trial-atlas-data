# Luna extraction task — Open Derm Trial Atlas, cycle 25 (v3)

Extract structured, sourced fields for ONE trial. A wrong value is worse than an
honest `not_found`. The final reviewer receives a mechanically valid patch on its
first pass: all draft work and local checks happen inside your extraction run.
Do not rely on the reviewer to repair quotes, URLs, enums, or schema violations.

## Read before extracting

- `TASK.json`: attempt every listed field and follow trial-specific notes.
- `base.json`: existing trial record, endpoints, arms, event groups, intervention
  names and design; read only. It is context, not a substitute for evidence.
- `ctgov.json`: registry protocol AND results, including participant flow,
  adverse events and baseline characteristics.
- `sources/*.txt` and `sources.json`: evidence documents and their authoritative
  URL/type mappings. Never edit sources to make an extraction pass.
- `SCHEMA.md`: exact value shapes and CLOSED categorical enums. The machine
  schema imported by `verify.py` is the validation authority. If a requested field
  such as `identity.why_stopped` is absent from an older SCHEMA.md, inspect its
  `verify.SPEC` entry; do not invent a schema.
- `example_fields.json`: shape examples from another trial, NEVER evidence for
  this trial's values.
- `endpoint_keys.json`: exact endpoint keys for published result joins.
- `spans.py`, `assemble.py`, `verify.py`: pipeline tools in the design directory.

## Workflow: classify evidence, do not generate quotes

Run from the directory containing the tools (replace `<job>` with the job path):

```sh
python3 spans.py build <job>
python3 spans.py search <job> 'eligibility|moderate|scaling'
python3 spans.py search <job> 'whyStopped|resultsSection'
```

Search prints candidate IDs, source locations, sections/JSON paths, and exact
source text. Read the original surrounding document to understand applicability,
table headers, units, and trial naming. Select as many separate spans as needed,
including table headings and row labels. Never splice or rewrite their texts.

Each `spans/<file_key>.jsonl` record has `id`, `file`, `text`, `line`, `section`.
IDs such as `CTGOV:0054` are stable for unchanged source snapshots and tool version.
For text files, `line` counts source lines; for JSON it counts lines within the
decoded string leaf, whose JSON path is always included in `section`. Formatting
boundaries, source quotation marks, HTML tags and physical line breaks are hard
cuts. Wrapped sentences therefore need multiple IDs. HTML entities are retained.
Rebuilding changed sources requires reselecting evidence. Never edit JSONL files.

Write `<job>/draft.json` with this exact outer format:

```json
{
  "fields": {
    "<group>.<field>": {
      "value": "<replace with the exact schema-typed value>",
      "file_key": "CTGOV",
      "section": "protocolSection: the relevant section or table",
      "span_ids": ["CTGOV:0054"],
      "note": "Interpretation or explicit arithmetic, outside evidence quotes.",
      "confidence": 0.9
    },
    "<another requested field>": {"not_found": "Specific reason after checking the sources"}
  },
  "trial_mapping": "Explain how the source's study naming maps to this NCT ID, with source locations and evidence."
}
```

The example ID illustrates syntax only; select actual IDs for YOUR job. Every
TASK field belongs exactly once in `fields`, either as an extraction or a
`not_found` object. No extra fields. Do not put a separate `not_found` map in the
draft; the assembler creates it in the patch.

You select `file_key` and span IDs; you never type `source_excerpt`, `source_url`,
`source_type`, `extracted_by`, or `reviewed_by`. `section` and `note` are unquoted
context, not supporting evidence. The assembler strips double quotation marks
from both, and quotes only source-derived spans. At least one selected fragment
must satisfy the existing verifier's 12-character minimum quote length; select
additional relevant context when needed, never padding or fabricated text.

All evidence for one field must come from one file, because the patch envelope
has one source URL. Find a source that supports the whole value. One file does
NOT mean one paragraph, page, table, or contiguous excerpt. A single FDA review
often contains BOTH a narrative statement (for example, no deaths occurred in
the development program) and arm denominators in a separate safety table. Select
both sets of spans, plus trial/population mapping and headers, from that review
to support death_rate or discontinuation. Search the whole file before declaring
the evidence unavailable. If a field
requires multiple documents or structured JSON numbers unavailable in string
leaves, do not misattribute evidence: use another sufficient source or mark the
field `not_found` with that limitation. This version does not create candidates
from JSON numeric/boolean leaves or compute `ctgov_api` values. Numeric strings
already present in CT.gov are available as string-leaf evidence.

`sources.json` supplies the real public URL and exact closed source-type enum:
CT.gov string leaves use `ctgov_text_extraction`; posted Protocol/SAP text uses
`protocol_pdf_extraction`; FDA review uses `publication_extraction`; label uses
`openfda_label`. The sample's legacy mixed CT.gov type string is deterministically
resolved to `ctgov_text_extraction`. No other ambiguous type is guessed.

Validate inside the extraction run:

```sh
python3 assemble.py <job>
python3 -m json.tool <job>/patch.json
python3 verify.py <job>
```

Assembly validates the value against the imported schema, resolves evidence and
provenance, sets `extracted_by` to `luna (gpt-6-luna) cycle-25 extraction pass`,
sets `reviewed_by` to null, and runs `verify.check`. It writes `patch.json` only
when every attempted field passes and every TASK field is accounted for. An
error exits nonzero and leaves any previous patch unchanged: never submit that
old patch as the result of a failed run. Resolve errors in YOUR draft or honestly
move unsupported fields to `not_found`, then assemble again before handoff.
These are extraction checks, not a final-review repair loop. Never edit patch.json.

The PASS table also lists every non-null boolean assertion recursively, including
true and false inside arrays and nested objects. These warnings require a source
support check even when the field passes mechanically; they do not certify truth.
Use null for unsupported nullable booleans, or `not_found` when a required boolean
cannot be established. A note cannot substitute for evidence.

Treat each numeric WARNING as work to resolve: select missing supporting spans,
correct the number, explain permitted exact arithmetic, or use `not_found`.
Warnings scan numeric leaves recursively using literal tokens; they do not prove
the correct arm, unit or endpoint, and may flag source words such as `two`, or
`2.0` versus `2`. Number presence alone is not support. Check every number's
meaning yourself. Confidence is normally 0.6–0.95, always finite and below 1.0;
lower confidence when interpretation is needed. Human review remains null.

`--partial` exists only for the supplied two-field tool smoke test. Never use it
for a completed extraction. `NOT_FOUND` is an explicit absence/limitation, not a
successfully extracted field. Do not hide unattempted work as `not_found` to
improve a pass-rate statistic.

## Hard rules: retain the no-fabrication bar

1. Every non-null value must follow DIRECTLY from selected source text for THIS
   trial. No general medical knowledge, no inference from other drugs/trials,
   and no typical designs. Free prose belongs in `note` or a schema-designated
   string (`rationale`, `population_note`, `source_inconsistency`, `description`).
2. FDA reviews/labels often describe two trials together. Use a statement only
   if it explicitly covers this trial or both/each of a pair containing it.
   Establish the mapping using enrollment, arms, dates and protocol numbers in
   `trial_mapping`; identify source paths/span IDs and supporting facts. If you
   include quotations there, resolve their texts programmatically from the
   selected candidates, never hand-type quotes. If mapping is uncertain, do not
   use trial-specific numbers. The mapping itself still needs semantic review.
3. If a field genuinely is not stated after searching all supplied sources, use
   `not_found` with a specific reason. An explicit negative is fillable: a stated
   rescue prohibition or a stated lack of multiplicity adjustment for a single
   primary endpoint. Silence is not evidence of absence.
4. Choose categorical values ONLY from the exact enums in SCHEMA.md/the machine
   schema, including source types, route, frequency, form and period names.
   Never force the nearest wrong enum. If a real concept lacks an enum (e.g.
   single application, gel, foam, suspension or oral solution), use null ONLY
   when that sub-field is nullable and explain it in `note`. Route can still be
   populated when explicitly stated.
5. All keys of a typed object must be present. Null is allowed only when the
   schema explicitly permits it; [] is allowed only for a genuinely empty or
   unrepresented collection. Required non-null sub-fields such as integer
   `alpha_sided` are NEVER null. If unknown, mark the whole field `not_found`;
   never guess a required integer or boolean to satisfy validation.
6. `ScoreCriterion.metric` and `unit` are also closed enums. Drop a criterion
   that cannot be truthfully represented and explain why; never mislabel it.
   If nothing meaningful remains to support the requested field, use `not_found`.
7. Numbers (n, N, %, weeks, days, doses) must be copied, not recomputed, except
   simple exact arithmetic explicitly shown in `note` (e.g. n/N*100 rounded to
   one decimal place). Select evidence for the inputs. Such derived numbers
   still warn when not printed; document the derivation, never suppress evidence
   checks. Do not back-compute responders from percentages.

## Semantic rules

These rules address every failure or uncertainty in `phase3_gate_report.txt`
and the seven missed evidence findings in `phase3_absence_findings.txt`.
Mechanical PASS establishes schema/provenance checks, not semantic correctness.

1. **Check every boolean assertion in every field.** Both true and false require
   selected evidence, including `identity.*`, nested objects, and array items.
   Silence never establishes false. Do not set `long_term_extension=false` because
   the described schedule omits an extension. Do not set `finalized_in_sap=true`
   from a method description, SAP amendment summaries, or a checklist referring
   jointly to protocols/SAPs; require explicit evidence of SAP finalization.
   Do not set routine `screening_washout=true` from a prior-treatment exclusion
   or conditional re-screening rule, especially when the protocol explicitly
   specifies no washout. Unsupported nullable flags stay null. For required
   booleans, if neither true nor false is established, use whole-field `not_found`;
   never choose false as a default. The boolean warnings list assertions for
   review; the assembler cannot determine their meaning from word matching.
   (NCT00735462, NCT00750139, NCT01056341, NCT02485704.)

2. **Separate pre-entry restrictions from background therapy during study.**
   Medication exclusions and pre-randomization washouts do not establish
   `prohibited_concomitant` during treatment. Preserve timing and scope in notes;
   include a treatment-period prohibition only when the source establishes it.
   Arm names, assigned treatments, or absence of a listed background intervention
   do not establish `regimen_type=monotherapy`. Per-protocol exclusion criteria
   also do not automatically establish the background-treatment policy. Use null
   where permitted or `not_found` for unsupported required content.
   (NCT00750139, NCT01353976.)

3. **Represent the entire schedule and distinguish contact types.** Include all
   stated periods: screening, treatment, no-treatment, and recurrence follow-up.
   Extract the stated `follow_up_visit_interval_weeks` rather than leaving it
   null when monitoring is described. For example, screening up to four weeks,
   eight weeks of treatment, eight weeks without treatment, and monitoring every
   four weeks for up to twelve weeks after clearance have different anchors;
   retain the conditional anchor in the note and do not invent absolute weeks.
   A Day 14 well-being phone call is not a clinic visit: clinic `visit_days` may
   be [1, 2, 28]. Represent telephone contacts in `phone_contact_weeks` if an exact
   conversion is appropriate (explain it), otherwise in the note. A conditional
   AE follow-up is not a scheduled clinic visit.
   `total_duration_weeks` is the whole trial, not the primary assessment horizon:
   a Week 6 assessment does not override an approximately ten-week trial duration.
   Preserve approximation and timing anchors; record source discrepancies in
   `source_inconsistency` and select the conflicting source spans from the chosen
   file. Do not silently harmonize incompatible timings or sum overlapping phases.
   (NCT00674739, NCT01289015, NCT02485717.)

4. **Preserve the actual multiplicity procedure and family.** Hochberg/Holm
   step-up/step-down families do not by themselves specify a fixed endpoint
   `testing_sequence`. Do not concatenate separate secondary endpoints into a
   fabricated sequence item. Populate a fixed hierarchy only where explicitly
   stated; otherwise use an empty sequence, and represent the described family
   in schema-supported fields (such as `alpha_split`) and the note. If no exact
   procedure enum fits, use null where allowed, never an approximate method enum.
   `familywise_error_controlled=true` requires evidence of error control across
   the stated family. Nominal alpha=0.05 or one primary endpoint does not prove
   overall control when exploratory tests exist and are explicitly unadjusted.
   Do not invent a singleton primary family to rescue that claim. Preserve any
   explicitly different family scopes; false also needs evidence about the
   relevant family, not an assumption. A genuinely stated W24-to-W48 gate can be
   recorded without asserting unsupported SAP finalization.
   (NCT00750139, NCT01056341, NCT02485704, NCT02485717.)

5. **Published results require both valid provenance and a correct endpoint
   join.** Only `openfda_label` or `publication_extraction` evidence is accepted
   for `results.published_results`; registry results belong in `results.arm_results`
   and must not be duplicated here merely because they are public. Do not relabel
   a registry source to bypass this guard. Every endpoint key must exactly match
   an entry in `endpoint_keys.json` (rank, position, and verbatim hash).
   Read that endpoint's verbatim, timepoints, and base record before joining:
   timepoint AND analysis population must match. Overall pooled ITT with overrun
   is not a Stage 1 Interim Analysis endpoint, even if the outcome names resemble
   each other. A valid hash alone is insufficient. If no listed key matches, do
   not manufacture or edit a key; explain the limitation and use `not_found` if
   no supported results can be represented.
   `study_period` follows the treatment/assessment timing: Week 6 after two- or
   four-week dosing is not `treatment_period`. If the closed enum cannot express
   the supported period, use null and explain it.
   (NCT00750139, NCT01056341, NCT01110330.)

6. **Keep result rows distinguishable.** If multiple rows share the same
   endpoint key and arm, each must have a nonblank, distinguishing
   `ctgov_class_title` copied from the source, or use distinct matching listed
   endpoint keys. This guard applies even if other row properties differ.
   A combined secondary endpoint must not hide effective-treatment and
   mycological-cure rows with null class titles; preserve the separate printed
   labels, counts, denominators and rates. Cosmetic case/whitespace changes
   are not distinguishing labels. Select row labels and arm/column headers;
   never invent class labels merely to satisfy the assembler.
   (NCT01290341.)

7. **Intervention descriptions are immutable provenance.** For each
   `intervention_name`, copy the matching CT.gov
   `protocolSection.armsInterventionsModule.interventions[].description`
   character for character, preserving whitespace, punctuation, application
   duration, volume and administration sites. Use the exact registry name;
   an unknown or ambiguous name fails. Missing/null registry descriptions become
   the empty string. Never truncate, summarize or enrich this description with
   another source. Put additional supported dosing detail in typed fields or the
   note while retaining an accurately attributable single-file evidence envelope.
   In particular, do not drop one application for six hours or the placebo's
   up-to-120-mL neck-to-soles instructions. (NCT02485717.)

8. **Severity comparators must preserve threshold wording.** At least mild
   erythema means >= 1 when the source scale establishes mild=1, not == 1.
   Select both the eligibility wording and scale anchors. Moderate/severe
   baseline observations can reveal an erroneous equality restriction but do
   not replace eligibility evidence. Preserve >=, >, <=, <, or equality exactly
   as supported. (NCT01353976.)

9. **Reconcile safety evidence before choosing values or declaring absence.**
   Search safety summaries, deaths narratives, trial-mapping/population sections,
   arm denominator tables, discontinuation tables, and reviewer corrections.
   Select multiple spans from ONE sufficient review file, including headers and
   denominators; they need not be on the same page as the event statement.
   An explicit program-wide or pooled-population no-deaths statement supports
   zero in included trial arms only when that trial's inclusion and the relevant
   safety population/time horizon are established. Use its safety-arm denominators,
   not unverified randomized or efficacy denominators. Similarly, an explicitly
   exhaustive sole-death account assigned to another study can establish absence
   in this study if coverage is clear; a non-exhaustive account cannot.
   Check arm allocation for nonzero deaths and corrected discontinuation counts.
   Do not assume two narratives describe the same person or distinct people:
   dermatitis withdrawal plus serious-hypertension discontinuation in one vehicle
   arm requires reconciliation, not an unsupported n=1 and 0.7%. Explain an
   unresolved conflict; leave unsupported nullable content null or use `not_found`
   if required content cannot be supported. Do not silently pick or sum counts.
   (NCT01353976 conflict; NCT00674739/NCT00735462 exhaustive death accounting;
   NCT00735462 corrected discontinuations; NCT01056341 pooled safety inclusion;
   NCT01289015/NCT01290341 program-wide absence and trial-specific denominators.)

   Before `not_found`, search every supplied document and distinguish genuinely
   missing data from data outside a particular paragraph. Missing CT.gov numeric
   keys are not inaccessible numeric evidence: inspect whether the keys exist.
   The NCT00750139 absence finding points to a clinical-review death statement
   and a statistical-review denominator table in DIFFERENT files. That finding
   warrants further searching for a sufficient single source; it does not waive
   the one-file rule or prove those two files are one review. If no file supports
   the whole field, state the precise cross-document limitation honestly. Never
   combine files, edit sources, or misattribute spans to force an extraction.

10. **Mechanism fields cannot exceed or omit explicit label statements.**
    Inhibits an enzyme does not establish that it binds that enzyme: populate
    `binding_targets` only when the label explicitly says binds/targets, not from
    pharmacologic inference. Use an empty collection if binding is unstated.
    `label_section` must reproduce an actual source section identifier; do not
    invent 12.4 for an unnumbered CLINICAL PHARMACOLOGY / Microbiology / Mode of
    Action heading. Use the printed heading when the schema permits, otherwise
    null with explanation. Search the whole label, including section 11, for
    `drug_class`; populate a stated class such as pediculicide and scabicide
    rather than leaving it null just because section 12.1 omits it. Select the
    class span along with mechanism spans from that same label.
    (Econazole, Ketoconazole, Spinosad.)

## Stopped trials

Always read `protocolSection.statusModule.overallStatus`. For TERMINATED,
WITHDRAWN or SUSPENDED trials:

- When `identity.why_stopped` is in TASK.json, set its value to
  `protocolSection.statusModule.whyStopped` **verbatim**, preserving even its
  whitespace; select that leaf's spans. The assembler enforces exact equality.
  If absent/empty, use `not_found` explaining the registry did not provide it.
- Inspect `resultsSection` even when the trial stopped. Available enrollment,
  participant flow, efficacy and safety data still need extraction where requested.
- When evidence establishes that a requested field could not exist because the
  trial stopped before that stage, use exactly
  `{"not_found": "trial stopped before this stage"}`. Do not apply this reason
  automatically to all missing results or to planned design/SAP fields; stopped
  trials can have both plans and observed results. Use a more specific ordinary
  absence reason when timing is unknown.

## Field-specific guidance

- `molecule.dosing_regimen`: one Intervention per CT.gov intervention referencing
  this drug. Include placebo/vehicle when its description references the drug or
  it is the matching vehicle/comparator, following the example. `description` is
  the CT.gov intervention description unchanged (empty string if absent). Add
  label/protocol dosing detail only with selected supporting evidence and an
  accurately attributable single-source envelope.
- `population.severity_criteria`: baseline disease-severity eligibility thresholds
  as ScoreCriterion rows, basis `eligibility_text`. `severity_label` is
  `moderate_to_severe` only when literally stated; otherwise null. Diagnosis
  alone with no quantitative/graded threshold means `not_found` with that reason.
- `design.background_therapy`: monotherapy/combination and permitted/prohibited
  concomitant medications, with source-derived short strings. Preserve whether
  a restriction applies before randomization or during treatment.
- `endpoints.multiplicity_control`: SAP/FDA statistical-review testing hierarchy
  and alpha control. `EndpointRef.responder_criteria` can be [] when not
  representable. Unknown required `alpha_sided` makes the field `not_found`.
- `timing_ops.study_schedule`: periods, visits, primary endpoint timing and
  follow-up. Use `visit_days` for day schedules; period names are a closed enum.
- `timing_ops.rescue_therapy`: extract rescue rules, explicit prohibition or
  explicit absence. Silence about rescue is insufficient. A stated prohibition
  of other treatment during study may support the field; explain in `rationale`.
  Do not convert a pre-randomization washout into a during-study prohibition.
- `adverse_events.death_rate`, `discontinuation_due_to_ae_rate`,
  `most_common_adverse_events` (only if requested): per-arm counts for THIS trial
  from FDA review/label/CT.gov. Match arm names to `results.arms[].label` or CT.gov
  event group titles in base.json. A no-deaths statement covering both phase 3
  trials plus this trial's event-group `seriousNumAtRisk` can support zero rates
  in principle, but this single-source/string-leaf pipeline must not miscite
  cross-document numeric evidence. Use a sufficient source or `not_found`.
- `results.published_results`: list of ArmResult rows for primary/key efficacy
  endpoints, FDA label section 14 preferred, FDA review otherwise, THIS trial
  only. `endpoint` must copy a matching entry's key from endpoint_keys.json;
  `arm_id` must come from base.json results.arms. When n (N) is given:
  `value_type=count_of_participants`, `reported_value=n`, `denominator=N`,
  `responders=n`, `response_rate_pct` is the printed %, `rate_is_derived=false`.
  `ctgov_class_title` preserves a printed distinguishing outcome/class label when
  rows share an endpoint key and arm; otherwise it can be null. Never invent a
  label to pass the guard. Dispersion and CI are null unless printed; `timepoint`
  follows the label and must match the referenced endpoint. The selected manifest supplies `openfda_label` or
  `publication_extraction`. Include row AND column/arm headers in evidence.

Final output is the assembled `patch.json` with `fields`, `not_found`, and
`trial_mapping`. Every sourced envelope has exactly `value`, `source_type`,
`source_url`, `source_excerpt`, `extracted_by`, `reviewed_by`, `confidence`.
Preserve the draft and generated spans as the audit trail.
