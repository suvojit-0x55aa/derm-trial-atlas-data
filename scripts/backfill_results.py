#!/usr/bin/env python3
"""
Re-run atlas.results over the cached CT.gov `resultsSection` payload for every
trial with results, and overwrite results.{arms,arm_results,effect_estimates}
in data/trials/<NCT_ID>.json with the freshly-derived values.

This is the same operation the results-layer effort's original backfill did
(PR #10) -- atlas/results.py's functions are pure (record + raw CT.gov study
JSON in, schema-shaped dicts out), so re-running it after a fix to those
functions (a parser bug, a new disambiguation rule) is the correct way to
propagate the fix into the committed data, never a hand-edit of the JSON.

Raw CT.gov payloads are not committed to this repo (they are the multi-MB
`resultsSection` JSON CT.gov's API returns, one per trial) -- this script
re-fetches any missing ones into `--cache-dir` (default /tmp/ctgov_cache) and
reuses what is already cached otherwise, so a re-run after a code fix does
not require refetching all 125 trials from a cold cache.

Usage:
    python3 scripts/backfill_results.py [NCT_ID ...]   # default: every trial
                                                        # with existing results
    python3 scripts/backfill_results.py --dry-run       # report changes, write nothing
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_DIR = ROOT / "data" / "trials"

import sys
sys.path.insert(0, str(ROOT))
from atlas.results import build_arm_registry, build_arm_results_and_effects, qc_filter

CTGOV_URL = "https://clinicaltrials.gov/api/v2/studies/{nct}?format=json"
EXTRACTED_BY = "atlas.results (ctgov_api v2, results-layer phase 3 backfill re-run)"


def fetch_or_load(nct, cache_dir: Path):
    cache_file = cache_dir / f"{nct}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    cache_dir.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(CTGOV_URL.format(nct=nct), timeout=30) as resp:
        raw = resp.read()
    cache_file.write_bytes(raw)
    time.sleep(0.3)  # be polite to CT.gov's API
    return json.loads(raw)


def sourced(value, source_url, source_excerpt):
    return {
        "value": value, "source_type": "ctgov_api", "source_url": source_url,
        "source_excerpt": source_excerpt, "extracted_by": EXTRACTED_BY,
        "reviewed_by": None, "confidence": 1.0,
    }


def backfill_one(record, cache):
    """Only touches (and only bumps provenance on) a results.* field whose
    freshly-derived VALUE actually differs from what is committed -- a
    trial the fix doesn't affect stays byte-identical, not just
    value-identical, so a diff only ever shows real changes."""
    arms = build_arm_registry(record, cache)
    arm_results, effect_estimates = build_arm_results_and_effects(record, cache)
    arm_results, effect_estimates, qc_report = qc_filter(record, arm_results, effect_estimates)
    url = f"https://clinicaltrials.gov/api/v2/studies/{record['nct_id']['value']}"
    new_fields = {
        "arms": (arms, "resultsSection.outcomeMeasuresModule.outcomeMeasures[].groups[]"),
        "arm_results": (arm_results, "resultsSection.outcomeMeasuresModule.outcomeMeasures[].{denoms,classes[].categories[].measurements[]}"),
        "effect_estimates": (effect_estimates, "resultsSection.outcomeMeasuresModule.outcomeMeasures[].analyses[]"),
    }
    changed_fields = []
    for key, (new_value, excerpt) in new_fields.items():
        if json.dumps(new_value, sort_keys=True) != json.dumps(record["results"][key]["value"], sort_keys=True):
            record["results"][key] = sourced(new_value, url, excerpt)
            changed_fields.append(key)
    return record, qc_report, changed_fields


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nct_ids", nargs="*", help="default: every trial with existing results.arm_results")
    ap.add_argument("--cache-dir", default="/tmp/ctgov_cache")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cache_dir = Path(args.cache_dir)

    files = sorted(TRIALS_DIR.glob("*.json"))
    targets = set(args.nct_ids) if args.nct_ids else None

    changed = 0
    for f in files:
        record = json.loads(f.read_text())
        nct = record["nct_id"]["value"]
        had_results = bool(record["results"]["arm_results"]["value"])
        if targets is not None and nct not in targets:
            continue
        if targets is None and not had_results:
            continue  # no CT.gov results for this trial -- nothing to backfill

        cache = fetch_or_load(nct, cache_dir)
        record, qc_report, changed_fields = backfill_one(record, cache)
        if changed_fields:
            changed += 1
            print(f"{nct}: changed {changed_fields} "
                  f"({len(record['results']['arm_results']['value'])} arm_results, "
                  f"{len(record['results']['effect_estimates']['value'])} effect_estimates)")
            if qc_report["excluded_arm_results"] or qc_report["excluded_effect_estimates"]:
                print(f"  QC excluded: {len(qc_report['excluded_arm_results'])} arm_results, "
                      f"{len(qc_report['excluded_effect_estimates'])} effect_estimates")
            if not args.dry_run:
                f.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")

    print(f"\n{changed} of {len(files)} trial files changed" + (" (dry run, nothing written)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
