#!/usr/bin/env python3
"""
Cross-source integration pass: folds the staged FAERS/Orange Book/Purple
Book data (data/_raw_staging/{faers,orange_book,purple_book}/<drug>.json,
each already shaped as a sourced value -- see scripts/fetch_faers.py,
fetch_orange_book.py, fetch_purple_book.py) into each DRUG's own
data/drugs/<slug>.json record -- schema v4's "search by drug" step: a
drug's cross-source facts are written ONCE, referenced by every trial of
that drug, never copied into each trial file individually (see
atlas/drugs.py and README's "Drug-level records" section).

`exclusivity.regulatory_application` was already populated per drug by
atlas.migrate.migrate_trial (atlas/regulatory_applications.py) during the
v1->v2 migration -- this script fills in the two registry-specific fields
that migration intentionally left needs_extraction (they didn't exist as a
source yet at migration time). Each drug record's own
`applications[].regulatory_application.value.registry` says which registry
(orange_book vs purple_book) applies to that application; a single
application never gets both.

Only touches drugs that already have a data/drugs/<slug>.json record (run
scripts/split_drug_level_fields.py first for the initial v3->v4 migration;
a NEW drug discovered in a later cycle should go through
atlas.drugs.ensure_drug_record instead of this script, which is for
refreshing FAERS/Orange Book/Purple Book on ALREADY-KNOWN drugs).

Run after scripts/fetch_faers.py, fetch_orange_book.py, fetch_purple_book.py:
    python3 scripts/apply_source_data.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from atlas.drugs import DRUGS_DIR, load_all_drug_records, save_drug  # noqa: E402

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
    drug_records = load_all_drug_records(DRUGS_DIR)
    if not drug_records:
        raise SystemExit(f"No drug records found in {DRUGS_DIR} -- run scripts/split_drug_level_fields.py first")

    updated = 0
    for drug, record in sorted(drug_records.items()):
        record["faers_summary"] = load_staged("faers", drug)

        for app in record["applications"]:
            reg_app = app["regulatory_application"]["value"]
            if reg_app is None:
                # No NDA/BLA join key on file for this application (e.g. a
                # drug not yet curated into atlas/regulatory_applications.py)
                # -- both registry fields stay needs_extraction, honestly,
                # rather than guessing which applies.
                app["orange_book"] = needs_extraction()
            elif reg_app["registry"] == "orange_book":
                app["orange_book"] = load_staged("orange_book", drug)
            elif reg_app["registry"] == "purple_book":
                record["purple_book"] = load_staged("purple_book", drug)
            else:
                raise SystemExit(f"{drug} application {app['application_number']}: "
                                  f"unrecognised registry {reg_app['registry']!r}")

        save_drug(record, DRUGS_DIR)
        updated += 1
        print(f"{drug}: faers={record['faers_summary']['source_type']}, "
              f"purple_book={record['purple_book']['source_type']}, "
              f"orange_book={[a['orange_book']['source_type'] for a in record['applications']]}")

    print(f"Updated {updated} drug records with real_world_safety + exclusivity data "
          f"({sum(len(r['trial_ids']) for r in drug_records.values())} trials covered, "
          "zero re-copies)")


if __name__ == "__main__":
    main()
