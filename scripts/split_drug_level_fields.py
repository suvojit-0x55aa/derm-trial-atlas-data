#!/usr/bin/env python3
"""
One-time schema v3 -> v4 restructuring: moves the 6 drug-level fields
(molecule.mechanism_of_action, adverse_events.boxed_warning,
real_world_safety.faers_summary, exclusivity.{regulatory_application,
orange_book,purple_book}) off every data/trials/<NCT_ID>.json and onto a new
data/drugs/<slug>.json per drug, referenced by DRUG_REF pointers -- see
atlas/drugs.py and atlas/schema.py's DRUG spec for the shapes and rationale.

This is the "drug-first" restructuring itself (not the ongoing pipeline
strategy change -- that is atlas.drugs.ensure_drug_record, called by a
future one-off add-a-trial script). Run once against the whole corpus:

    python3 scripts/split_drug_level_fields.py

Idempotent: running it again on already-v4 trial files is a no-op (skips
any record whose schema_version is already 4).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from atlas.drugs import DRUGS_DIR, build_drug_records, save_drug, split_trial_record  # noqa: E402
from atlas.schema import DRUG, TRIAL, validate  # noqa: E402

TRIALS_DIR = ROOT / "data" / "trials"


def main():
    trial_files = sorted(TRIALS_DIR.glob("*.json"))
    trials = [json.loads(f.read_text()) for f in trial_files]

    already_v4 = [t for t in trials if t.get("schema_version") == 4]
    if len(already_v4) == len(trials):
        print("Every trial is already schema v4 -- nothing to split.")
        return
    if already_v4:
        raise SystemExit(f"{len(already_v4)} of {len(trials)} trials are already v4 and the rest are not -- "
                          "partial state, investigate before re-running.")
    for t in trials:
        if t.get("schema_version") != 3:
            raise SystemExit(f"{t['nct_id']['value']} is schema v{t.get('schema_version')}, not v3 -- "
                              "run atlas.migrate.migrate_v2_to_v3 first")

    drug_records = build_drug_records(trials)
    print(f"Built {len(drug_records)} drug records from {len(trials)} trials.")

    for name, record in sorted(drug_records.items()):
        errs = validate(record, spec=DRUG)
        if errs:
            raise SystemExit(f"drug record {name!r} fails validation: {errs[:5]}")
        path = save_drug(record)
        print(f"  wrote {path.relative_to(ROOT)} ({len(record['trial_ids'])} trials"
              + (f", {len(record['applications'])} applications" if len(record['applications']) > 1 else "") + ")")

    for f, t in zip(trial_files, trials):
        split = split_trial_record(t)
        errs = validate(split, spec=TRIAL)
        if errs:
            raise SystemExit(f"{f.name}: split trial record fails validation: {errs[:5]}")
        f.write_text(json.dumps(split, indent=2, ensure_ascii=False) + "\n")

    print(f"Split {len(trials)} trial files to schema v4.")


if __name__ == "__main__":
    main()
