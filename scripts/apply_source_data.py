#!/usr/bin/env python3
"""
Cross-source integration pass: folds the staged FAERS/Orange Book/Purple
Book data (data/_raw_staging/{faers,orange_book,purple_book}/<drug>.json,
each already shaped as a schema v2 sourced value -- see scripts/fetch_faers.py,
fetch_orange_book.py, fetch_purple_book.py) into every schema v2 trial
record's `real_world_safety.faers_summary` and `exclusivity.{orange_book,
purple_book}` fields. Drug-level data (like `openfda_label`): the same
value is reused across every trial of that drug.

`exclusivity.regulatory_application` was already populated by
atlas.migrate.migrate_trial (atlas/regulatory_applications.py) during the
v1->v2 migration -- this script fills in the two registry-specific fields
that migration intentionally left needs_extraction (they didn't exist as a
source yet at migration time). `application_type` on the record's own
`regulatory_application` field says which registry (orange_book vs
purple_book) applies; a drug never gets both.

Only rewrites records that are already schema v2 (skips/errors otherwise,
same convention as scripts/fetch_adverse_events.py's `_refuse_v2` guard,
inverted).

Run after scripts/fetch_faers.py, fetch_orange_book.py, fetch_purple_book.py,
and scripts/migrate_v1_to_v2.py:
    python3 scripts/apply_source_data.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_DIR = ROOT / "data" / "trials"
STAGING = ROOT / "data" / "_raw_staging"


def needs_extraction():
    return {"value": None, "source_type": "needs_extraction", "source_url": None,
            "source_excerpt": None, "extracted_by": None, "reviewed_by": None, "confidence": None}


def load_staged(source: str, drug: str) -> dict:
    path = STAGING / source / f"{drug.lower()}.json"
    if not path.exists():
        return needs_extraction()
    record = json.loads(path.read_text())
    # A staged file's own top-level shape IS already the sourced-value
    # envelope (value/source_type/source_url/source_excerpt/extracted_by) --
    # fetch_faers.py/fetch_orange_book.py/fetch_purple_book.py write it that
    # way directly so this integration step is a straight copy, not a
    # second transformation. Normalize reviewed_by/confidence, which the
    # fetch scripts don't always set explicitly on the success path.
    record.setdefault("reviewed_by", None)
    record.setdefault("confidence", 1.0 if record.get("value") is not None else None)
    record.pop("fetched_at", None)  # not part of the sourced-value envelope
    return {k: record[k] for k in
            ("value", "source_type", "source_url", "source_excerpt", "extracted_by", "reviewed_by", "confidence")}


def main():
    trial_files = sorted(TRIALS_DIR.glob("*.json"))
    updated = 0
    for f in trial_files:
        record = json.loads(f.read_text())
        if record.get("schema_version") != 2:
            raise SystemExit(f"{f.name} is not schema v2 -- run scripts/migrate_v1_to_v2.py first")

        drug = record["molecule"]["drug"]["value"]
        reg_app = record["exclusivity"]["regulatory_application"]["value"]

        record["real_world_safety"]["faers_summary"] = load_staged("faers", drug)

        if reg_app is None:
            # No NDA/BLA join key on file for this drug (e.g. omalizumab's
            # sponsor changed hands / a drug not yet curated into
            # atlas/regulatory_applications.py) -- both registry fields stay
            # needs_extraction, honestly, rather than guessing which applies.
            record["exclusivity"]["orange_book"] = needs_extraction()
            record["exclusivity"]["purple_book"] = needs_extraction()
        elif reg_app["registry"] == "orange_book":
            record["exclusivity"]["orange_book"] = load_staged("orange_book", drug)
            record["exclusivity"]["purple_book"] = needs_extraction()
        elif reg_app["registry"] == "purple_book":
            record["exclusivity"]["purple_book"] = load_staged("purple_book", drug)
            record["exclusivity"]["orange_book"] = needs_extraction()
        else:
            raise SystemExit(f"{f.name}: unrecognised registry {reg_app['registry']!r} for drug {drug!r}")

        f.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        updated += 1
        print(f"{f.name} ({drug}): faers={record['real_world_safety']['faers_summary']['source_type']}, "
              f"orange_book={record['exclusivity']['orange_book']['source_type']}, "
              f"purple_book={record['exclusivity']['purple_book']['source_type']}")

    print(f"Updated {updated} trial files with real_world_safety + exclusivity data")


if __name__ == "__main__":
    main()
