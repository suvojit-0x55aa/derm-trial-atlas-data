#!/usr/bin/env python3
"""
Flatten every data/trials/<NCT_ID>.json (schema v2) into repo-root CSVs:

  trials.csv             one row per trial, one column per sourced field
                         (structured values are JSON-encoded in the cell)
  sources.csv            one row per sourced value: nct_id, field, source_type,
                         source_url, source_excerpt, extracted_by, reviewed_by,
                         confidence
  endpoints.csv          one row per outcome measure (primary + secondary),
                         with its atomic fields and one row per responder /
                         subgroup criterion (criterion_index >= 1) so an
                         "EASI-75 at week 16" query is a filter, not a parse
  severity_criteria.csv  one row per baseline-severity ScoreCriterion
  adverse_event_rates.csv one row per (trial, arm, measure) safety rate

Run:
    python3 scripts/build_csv.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_DIR = ROOT / "data" / "trials"

CRITERION_COLS = ["scale", "scale_component", "scale_variant", "metric", "comparator", "value", "unit",
                  "scale_min", "scale_max", "assessed_at"]


def flatten_fields(record: dict, prefix: str = "") -> list:
    """(field_path, sourced_value) for every leaf sourced-value object."""
    out = []
    for key, val in record.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict) and "value" in val and "source_type" in val:
            out.append((path, val))
        elif isinstance(val, dict):
            out.extend(flatten_fields(val, path))
    return out


def cell(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: cell(row.get(k)) for k in fieldnames})
    print(f"Wrote {path} ({len(rows)} rows, {len(fieldnames)} columns)")


def endpoint_rows(nct, drug, trial_name, endpoints):
    rows = []
    for ep in endpoints:
        base = {
            "nct_id": nct, "drug": drug, "trial_name": trial_name, "rank": ep["rank"], "position": ep["position"],
            "measure_type": ep["measure_type"], "scale": ep["scale"], "scale_component": ep["scale_component"],
            "scale_variant": ep["scale_variant"], "baseline_reference": ep["baseline_reference"],
            "timepoints": ";".join(f"{t['value']}{'-' + str(t['end_value']) if t['end_value'] else ''}{t['unit'][0]}" for t in ep["timepoints"]),
            "through": f"{ep['through']['value']}{ep['through']['unit'][0]}" if ep["through"] else None,
            "analysis_population": ep["analysis_population"], "subgroup_labels": ";".join(ep["subgroup_labels"]),
            "study_period": ep["study_period"], "event_type": ep["event_type"], "verbatim": ep["verbatim"],
        }
        crits = [("responder", c) for c in ep["responder_criteria"]] + [("subgroup", c) for c in ep["subgroup_criteria"]]
        if not crits:
            rows.append({**base, "criterion_index": 0, "criterion_role": None})
        for i, (role, c) in enumerate(crits, 1):
            rows.append({**base, "criterion_index": i, "criterion_role": role,
                         **{f"criterion_{k}": c[k] for k in CRITERION_COLS}})
    return rows


def main():
    trial_files = sorted(TRIALS_DIR.glob("*.json"))
    if not trial_files:
        raise SystemExit(f"No trial files found in {TRIALS_DIR}")

    trial_rows, field_order, seen, source_rows = [], [], set(), []
    ep_rows, sev_rows, ae_rows = [], [], []
    for f in trial_files:
        record = json.loads(f.read_text())
        if record.get("schema_version") != 2:
            raise SystemExit(f"{f.name} is not schema v2 -- run scripts/migrate_v1_to_v2.py first")
        nct = record["nct_id"]["value"]
        drug = record["molecule"]["drug"]["value"]
        trial_name = record["identity"]["trial_name"]["value"]
        row = {"nct_id_file": f.stem, "schema_version": record["schema_version"]}
        for path, obj in flatten_fields({k: v for k, v in record.items() if k != "schema_version"}):
            if path not in seen:
                seen.add(path)
                field_order.append(path)
            row[path] = obj.get("value")
            source_rows.append({"nct_id": f.stem, "field": path, **{k: obj.get(k) for k in
                                ("source_type", "source_url", "source_excerpt", "extracted_by", "reviewed_by", "confidence")}})
        trial_rows.append(row)

        eps = (record["endpoints"]["primary_endpoints"]["value"] or []) + (record["endpoints"]["secondary_endpoints"]["value"] or [])
        ep_rows.extend(endpoint_rows(nct, drug, trial_name, eps))
        sev = record["population"]["severity_criteria"]["value"]
        for i, c in enumerate(sev["criteria"] if sev else [], 1):
            sev_rows.append({"nct_id": nct, "drug": drug, "trial_name": trial_name, "criterion_index": i,
                             "severity_label": sev["severity_label"], "basis": sev["basis"], **c})
        ae = record["adverse_events"]
        for measure in ("serious_adverse_event_rate", "death_rate", "discontinuation_due_to_ae_rate"):
            for r in ae[measure]["value"] or []:
                ae_rows.append({"nct_id": nct, "drug": drug, "trial_name": trial_name, "measure": measure, "arm": r["arm"],
                                "n_affected": r.get("n_affected", r.get("n_discontinued")),
                                "n_at_risk": r.get("n_at_risk", r.get("n_started")), "pct": r["pct"], "meddra_pt": None, "meddra_soc": None})
        for term in ae["most_common_adverse_events"]["value"] or []:
            for r in term["per_arm"]:
                ae_rows.append({"nct_id": nct, "drug": drug, "trial_name": trial_name, "measure": "most_common_adverse_events",
                                "arm": r["arm"], "n_affected": r["n_affected"], "n_at_risk": r["n_at_risk"], "pct": r["pct"],
                                "meddra_pt": term["meddra_pt"], "meddra_soc": term["meddra_soc"]})

    write_csv(ROOT / "trials.csv", ["nct_id_file", "schema_version"] + field_order, trial_rows)
    write_csv(ROOT / "sources.csv", ["nct_id", "field", "source_type", "source_url", "source_excerpt", "extracted_by", "reviewed_by", "confidence"], source_rows)
    ep_cols = ["nct_id", "drug", "trial_name", "rank", "position", "measure_type", "scale", "scale_component", "scale_variant",
               "baseline_reference", "timepoints", "through", "analysis_population", "subgroup_labels", "study_period", "event_type",
               "criterion_index", "criterion_role"] + [f"criterion_{k}" for k in CRITERION_COLS] + ["verbatim"]
    write_csv(ROOT / "endpoints.csv", ep_cols, ep_rows)
    write_csv(ROOT / "severity_criteria.csv", ["nct_id", "drug", "trial_name", "criterion_index", "severity_label", "basis"] + CRITERION_COLS + ["scale_anchors"], sev_rows)
    write_csv(ROOT / "adverse_event_rates.csv", ["nct_id", "drug", "trial_name", "measure", "arm", "meddra_pt", "meddra_soc", "n_affected", "n_at_risk", "pct"], ae_rows)


if __name__ == "__main__":
    main()
