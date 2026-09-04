#!/usr/bin/env python3
"""
Migrate every data/trials/<NCT_ID>.json from schema v1 (free-text values)
to schema v2 (typed, atomic values) in place, then validate the result.

    python3 scripts/migrate_v1_to_v2.py            # migrate + validate
    python3 scripts/migrate_v1_to_v2.py --check    # validate only (no writes)

Files already at schema_version 2 are left untouched (idempotent). The
transformation itself lives in atlas/migrate.py; this is just the CLI.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from atlas import SCHEMA_VERSION  # noqa: E402
from atlas.migrate import AlreadyMigrated, migrate_trial  # noqa: E402
from atlas.schema import validate  # noqa: E402

TRIALS_DIR = ROOT / "data" / "trials"


def main(argv):
    check_only = "--check" in argv
    files = sorted(TRIALS_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"no trial files in {TRIALS_DIR}")
    migrated, skipped, problems = 0, 0, 0
    for path in files:
        record = json.loads(path.read_text())
        if record.get("schema_version") != SCHEMA_VERSION and not check_only:
            try:
                record = migrate_trial(record)
            except AlreadyMigrated:
                pass
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
            migrated += 1
        else:
            skipped += 1
        errors = validate(record)
        if errors:
            problems += 1
            print(f"{path.name}: {len(errors)} schema problems")
            for e in errors[:20]:
                print(f"   {e}")
    print(f"migrated {migrated}, already v2 {skipped}, files with schema problems {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
