#!/usr/bin/env python3
"""
Flatten every data/trials/<NCT_ID>.json file into two repo-root CSVs:

  trials.csv  - one row per trial, one column per field (the field's
                "value", real data or null for needs_extraction fields).
  sources.csv - one row per sourced value: trial id, field, source_type,
                source_url, source_excerpt.

Run:
    python3 scripts/build_csv.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_DIR = ROOT / "data" / "trials"


def flatten_fields(record: dict, prefix: str = "") -> list[tuple[str, dict]]:
    """Walk the nested trial record, returning (field_path, field_obj) pairs
    for every leaf that looks like a sourced-value object (has "value" and
    "source_type" keys)."""
    out = []
    for key, val in record.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict) and "value" in val and "source_type" in val:
            out.append((path, val))
        elif isinstance(val, dict):
            out.extend(flatten_fields(val, path))
    return out


def value_to_cell(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def main():
    trial_files = sorted(TRIALS_DIR.glob("*.json"))
    if not trial_files:
        raise SystemExit(f"No trial files found in {TRIALS_DIR}")

    all_rows = []
    field_paths_order: list[str] = []
    seen_paths = set()
    sources_rows = []

    for f in trial_files:
        record = json.loads(f.read_text())
        fields = flatten_fields(record)
        row = {"nct_id_file": f.stem}
        for path, obj in fields:
            if path not in seen_paths:
                seen_paths.add(path)
                field_paths_order.append(path)
            row[path] = value_to_cell(obj.get("value"))
            sources_rows.append(
                {
                    "nct_id": f.stem,
                    "field": path,
                    "source_type": obj.get("source_type"),
                    "source_url": obj.get("source_url"),
                    "source_excerpt": obj.get("source_excerpt"),
                    "extracted_by": obj.get("extracted_by"),
                    "reviewed_by": obj.get("reviewed_by"),
                    "confidence": obj.get("confidence"),
                }
            )
        all_rows.append(row)

    # trials.csv
    trials_csv_path = ROOT / "trials.csv"
    fieldnames = ["nct_id_file"] + field_paths_order
    with trials_csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    # sources.csv
    sources_csv_path = ROOT / "sources.csv"
    sources_fieldnames = [
        "nct_id",
        "field",
        "source_type",
        "source_url",
        "source_excerpt",
        "extracted_by",
        "reviewed_by",
        "confidence",
    ]
    with sources_csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=sources_fieldnames)
        writer.writeheader()
        for row in sources_rows:
            writer.writerow(row)

    print(f"Wrote {trials_csv_path} ({len(all_rows)} rows, {len(fieldnames)} columns)")
    print(f"Wrote {sources_csv_path} ({len(sources_rows)} rows)")


if __name__ == "__main__":
    main()
