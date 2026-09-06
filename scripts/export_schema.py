#!/usr/bin/env python3
"""
Render the schema (atlas/schema.py, the single source of truth) into the
three committed artefacts consumers read:

    schema/trial.schema.json   JSON Schema draft-07 of one trial record
    schema/drug.schema.json    JSON Schema draft-07 of one drug record
    docs/SCHEMA.md             field-by-field documentation, with types (both records)

    python3 scripts/export_schema.py          # rewrite all three
    python3 scripts/export_schema.py --check  # exit 1 if any is stale

tests/test_schema.py runs the --check so the committed files can't drift
from the spec.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from atlas import schema as S  # noqa: E402
from atlas.migrate import RENAMES  # noqa: E402

JSON_PATH = ROOT / "schema" / "trial.schema.json"
DRUG_JSON_PATH = ROOT / "schema" / "drug.schema.json"
MD_PATH = ROOT / "docs" / "SCHEMA.md"

NAMED_TYPES = [
    ("ScoreCriterion", S.SCORE_CRITERION), ("Endpoint", S.ENDPOINT), ("EndpointRef", S.ENDPOINT_REF),
    ("Timepoint", S.TIMEPOINT), ("Severity", S.SEVERITY), ("Intervention", S.INTERVENTION),
    ("Mechanism", S.MECHANISM), ("BackgroundTherapy", S.BACKGROUND), ("MultiplicityControl", S.MULTIPLICITY),
    ("StudySchedule", S.SCHEDULE), ("RescueTherapy", S.RESCUE), ("Agent", S.AGENT),
    ("PotencyClass", S.POTENCY_CLASS), ("ArmRate", S.ARM_RATE), ("ArmDiscontinuation", S.ARM_DISC),
    ("AdverseEventTerm", S.AE_TERM), ("BoxedWarning", S.BOXED_WARNING), ("PartialDate", S.DATE_P),
    ("FaersSummary", S.FAERS_SUMMARY), ("ReactionRow", S.REACTION_ROW), ("OrangeBookRecord", S.ORANGE_BOOK),
    ("PurpleBookRecord", S.PURPLE_BOOK), ("RegulatoryApplication", S.REG_APP),
    ("EndpointKey", S.ENDPOINT_KEY), ("PValue", S.PVALUE), ("Arm", S.ARM),
    ("ArmResult", S.ARM_RESULT), ("EffectEstimate", S.EFFECT_ESTIMATE),
    ("DrugRef", S.DRUG_REF), ("DrugApplication", S.DRUG_APPLICATION),
]
NAME_OF = {id(spec["properties"]): name for name, spec in NAMED_TYPES}


def type_name(spec):
    name = NAME_OF.get(id(spec.get("properties")))
    if name:
        base = name
    elif spec["type"] == "array":
        base = f"list[{type_name(spec['items'])}]"
    elif spec["type"] == "object":
        base = "{" + ", ".join(f"{k}: {type_name(v)}" for k, v in spec["properties"].items()) + "}"
    elif "enum" in spec:
        base = "enum(" + " \\| ".join(str(v) for v in spec["enum"]) + ")"
    elif "const" in spec:
        base = f"const {spec['const']}"
    else:
        base = spec["type"]
    return base + (" \\| null" if spec.get("nullable") else "")


def render_md():
    lines = [
        f"# Open Derm Trial Atlas -- schema v{S.SCHEMA_VERSION} (field reference)",
        "",
        "Generated from `atlas/schema.py` by `scripts/export_schema.py`; do not edit by hand.",
        "The machine-readable form is `schema/trial.schema.json`.",
        "",
        "Every field below is a **sourced value**:",
        "",
        "```json",
        '{"value": <typed, see table>, "source_type": "ctgov_api" | ..., "source_url": str|null,',
        ' "source_excerpt": str|null, "extracted_by": str|null, "reviewed_by": str|null, "confidence": number|null}',
        "```",
        "",
        "`source_type` is one of: " + ", ".join(f"`{s}`" for s in S.SOURCE_TYPES) + ".",
        "A `needs_extraction` field always has `value: null`; every other source type carries a value of the",
        "type in the table (nullable where marked). Free prose never lives in `value` -- where a v1 field was",
        "prose, that prose is now in `source_excerpt` (or the endpoint's `verbatim` / intervention's",
        "`description`) as provenance, and `value` holds the atomic decomposition.",
        "",
        "6 fields (`molecule.mechanism_of_action`, `adverse_events.boxed_warning`,",
        "`real_world_safety.faers_summary`, `exclusivity.{regulatory_application,orange_book,purple_book}`)",
        "are `DrugRef` pointers, not the fact itself: the fact is extracted once and lives on",
        "`data/drugs/<slug>.json` (see the 'Drug record fields' section below and `atlas/drugs.py`),",
        "referenced by every trial of that drug instead of re-described per trial.",
        "",
        "## Trial record fields",
        "",
        "| Field | Value type | Meaning | v1 name |",
        "|---|---|---|---|",
    ]
    inverse = {f"{g}.{new}": f"{g}.{old}" for (g, old), new in RENAMES.items()}
    for path, spec, desc in S.FIELD_DOCS:
        v1 = inverse.get(path, "")
        lines.append(f"| `{path}` | {type_name(spec)} | {desc or ''} | {('`' + v1 + '`') if v1 else ''} |")
    lines += ["", f"Plus the top-level literal `schema_version: {S.SCHEMA_VERSION}`.", ""]

    lines += ["## Drug record fields (data/drugs/<slug>.json)", "",
              S.DRUG.get("description", ""), "",
              "| Field | Value type | Meaning |", "|---|---|---|"]
    for path, spec, desc in S.field_paths(S.DRUG):
        lines.append(f"| `{path}` | {type_name(spec)} | {desc or ''} |")
    # `applications`/`trial_ids` are bare (non-sourced) top-level lists, same
    # shape as TRIAL's own `schema_version` -- field_paths only walks sourced
    # values and objects, so these two are documented by hand, same convention
    # as the "Plus the top-level literal schema_version" note below.
    lines.append(f"| `applications` | {type_name(S.DRUG['properties']['applications'])} | "
                 f"{S.DRUG['properties']['applications'].get('description', '')} |")
    lines.append(f"| `trial_ids` | {type_name(S.DRUG['properties']['trial_ids'])} | "
                 f"{S.DRUG['properties']['trial_ids'].get('description', '')} |")
    lines += ["", f"Plus the top-level literals `schema_version: {S.DRUG_SCHEMA_VERSION}` and `drug` (string).", ""]

    for name, spec in NAMED_TYPES:
        lines += [f"## {name}", ""]
        if spec.get("description"):
            lines += [spec["description"], ""]
        lines += ["| Key | Type | Notes |", "|---|---|---|"]
        for key, sub in spec["properties"].items():
            lines.append(f"| `{key}` | {type_name(sub)} | {sub.get('description', '')} |")
        lines.append("")
    return "\n".join(lines)


def main(argv):
    json_text = json.dumps(S.to_json_schema(), indent=2, ensure_ascii=False) + "\n"
    drug_json_text = json.dumps(S.to_json_schema(S.DRUG), indent=2, ensure_ascii=False) + "\n"
    md_text = render_md()
    if "--check" in argv:
        stale = []
        if not JSON_PATH.exists() or JSON_PATH.read_text() != json_text:
            stale.append(str(JSON_PATH))
        if not DRUG_JSON_PATH.exists() or DRUG_JSON_PATH.read_text() != drug_json_text:
            stale.append(str(DRUG_JSON_PATH))
        if not MD_PATH.exists() or MD_PATH.read_text() != md_text:
            stale.append(str(MD_PATH))
        if stale:
            print("stale:", ", ".join(stale), "-- run scripts/export_schema.py")
            return 1
        print("schema exports up to date")
        return 0
    JSON_PATH.parent.mkdir(exist_ok=True)
    MD_PATH.parent.mkdir(exist_ok=True)
    JSON_PATH.write_text(json_text)
    DRUG_JSON_PATH.write_text(drug_json_text)
    MD_PATH.write_text(md_text)
    print(f"wrote {JSON_PATH}, {DRUG_JSON_PATH}, and {MD_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
