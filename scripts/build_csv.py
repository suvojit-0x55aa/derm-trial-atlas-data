#!/usr/bin/env python3
"""
Flatten every data/trials/<NCT_ID>.json (schema v4) and data/drugs/<slug>.json
(schema v4) into repo-root CSVs:

  trials.csv             one row per trial, one column per sourced field
                         (structured values are JSON-encoded in the cell).
                         6 columns (molecule.mechanism_of_action,
                         adverse_events.boxed_warning,
                         real_world_safety.faers_summary,
                         exclusivity.{regulatory_application,orange_book,
                         purple_book}) hold a DRUG_REF pointer
                         ({"drug", "application_number"}), not the fact
                         itself -- join drugs.csv (and drug_applications.csv
                         for the two application-keyed ones) on `drug` to
                         resolve it, the same reference-not-copy idiom
                         arm_results.csv/effect_estimates.csv already use
                         for endpoints.
  sources.csv            one row per sourced value: nct_id, field, source_type,
                         source_url, source_excerpt, extracted_by, reviewed_by,
                         confidence (the 6 drug-level fields' rows here are
                         "drug_level_ref" pointer citations, not the real
                         fact's own citation -- that's in drug_sources.csv)
  endpoints.csv          one row per outcome measure (primary + secondary),
                         with its atomic fields and one row per responder /
                         subgroup criterion (criterion_index >= 1) so an
                         "EASI-75 at week 16" query is a filter, not a parse
  severity_criteria.csv  one row per baseline-severity ScoreCriterion
  adverse_event_rates.csv one row per (trial, arm, measure) safety rate
  arm_results.csv        one row per endpoint x timepoint x arm CT.gov results
                         measurement; keyed on nct_id + endpoint_rank +
                         endpoint_position to join endpoints.csv's rank/position
  effect_estimates.csv   one row per endpoint x timepoint x pairwise arm
                         comparison; same nct_id/endpoint_rank/endpoint_position
                         join key as arm_results.csv
  drugs.csv              one row per drug: mechanism_of_action, boxed_warning,
                         faers_summary, drug_characterization, purple_book, trial_ids
  drug_applications.csv  one row per (drug, application_number): regulatory_application,
                         orange_book -- almost every drug has exactly 1 row;
                         Roflumilast (2 real FDA applications) has 2
  drug_sources.csv       one row per drug-level sourced value: drug, field,
                         source_type, source_url, source_excerpt, extracted_by,
                         reviewed_by, confidence -- the single citation now
                         backing every trial of that drug

Run:
    python3 scripts/build_csv.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_DIR = ROOT / "data" / "trials"
DRUGS_DIR = ROOT / "data" / "drugs"

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


def _timepoint_cell(tp):
    if not tp:
        return None
    return f"{tp['value']}{'-' + str(tp['end_value']) if tp.get('end_value') else ''}{tp['unit'][0]}"


def arm_result_rows(nct, drug, trial_name, results):
    rows = []
    for r in results["arm_results"]["value"] or []:
        ep = r["endpoint"]
        rows.append({
            "nct_id": nct, "drug": drug, "trial_name": trial_name,
            "endpoint_rank": ep["rank"], "endpoint_position": ep["position"], "endpoint_verbatim_sha1": ep["verbatim_sha1"],
            "arm_id": r["arm_id"], "timepoint": _timepoint_cell(r["timepoint"]),
            "analysis_population": r["analysis_population"], "study_period": r["study_period"],
            "denominator": r["denominator"], "value_type": r["value_type"],
            "reported_value": r["reported_value"], "reported_unit": r["reported_unit"],
            "responders": r["responders"], "response_rate_pct": r["response_rate_pct"],
            "rate_is_derived": r["rate_is_derived"], "dispersion_type": r["dispersion_type"],
            "dispersion_value": r["dispersion_value"], "ci_pct": r["ci_pct"], "ci_lower": r["ci_lower"],
            "ci_upper": r["ci_upper"], "ctgov_class_title": r["ctgov_class_title"],
        })
    return rows


def effect_estimate_rows(nct, drug, trial_name, results):
    rows = []
    for r in results["effect_estimates"]["value"] or []:
        ep = r["endpoint"]
        pv = r["p_value"]
        rows.append({
            "nct_id": nct, "drug": drug, "trial_name": trial_name,
            "endpoint_rank": ep["rank"], "endpoint_position": ep["position"], "endpoint_verbatim_sha1": ep["verbatim_sha1"],
            "timepoint": _timepoint_cell(r["timepoint"]),
            "test_arm_id": r["test_arm_id"], "reference_arm_id": r["reference_arm_id"],
            "comparison_kind": r["comparison_kind"], "effect_type": r["effect_type"],
            "effect_type_verbatim": r["effect_type_verbatim"], "effect_value": r["effect_value"],
            "ci_pct": r["ci_pct"], "ci_lower": r["ci_lower"], "ci_upper": r["ci_upper"], "ci_sides": r["ci_sides"],
            "p_value_comparator": pv["comparator"] if pv else None, "p_value": pv["value"] if pv else None,
            "p_value_verbatim": pv["verbatim"] if pv else None,
            "statistical_method": r["statistical_method"], "adjusted_for": ";".join(r["adjusted_for"]),
        })
    return rows


DRUG_SINGLE_VALUED = ("mechanism_of_action", "boxed_warning", "faers_summary", "drug_characterization", "purple_book")


def drug_row_and_sources(record):
    """(drugs.csv row, drug_sources.csv rows) for one data/drugs/<slug>.json
    record -- the 5 single-valued sourced fields only; applications[] is
    handled separately by drug_application_rows since it is a list, not a
    single sourced value (flatten_fields does not walk into lists)."""
    drug = record["drug"]
    row = {"drug": drug, "schema_version": record["schema_version"], "trial_ids": record["trial_ids"]}
    sources = []
    for field in DRUG_SINGLE_VALUED:
        obj = record[field]
        row[field] = obj.get("value")
        sources.append({"drug": drug, "field": field, **{k: obj.get(k) for k in
                        ("source_type", "source_url", "source_excerpt", "extracted_by", "reviewed_by", "confidence")}})
    return row, sources


def drug_application_rows_and_sources(record):
    """(drug_applications.csv rows, drug_sources.csv rows) for one drug's
    applications[] list -- almost always 1 row; Roflumilast (2 real FDA
    applications) has 2."""
    drug = record["drug"]
    rows, sources = [], []
    for app in record["applications"]:
        app_num = app["application_number"]
        row = {"drug": drug, "application_number": app_num}
        for field in ("regulatory_application", "orange_book"):
            obj = app[field]
            row[field] = obj.get("value")
            sources.append({"drug": drug, "field": f"applications[{app_num}].{field}", **{k: obj.get(k) for k in
                            ("source_type", "source_url", "source_excerpt", "extracted_by", "reviewed_by", "confidence")}})
        rows.append(row)
    return rows, sources


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
    ep_rows, sev_rows, ae_rows, arm_result_csv_rows, effect_estimate_csv_rows = [], [], [], [], []
    for f in trial_files:
        record = json.loads(f.read_text())
        if record.get("schema_version") != 4:
            raise SystemExit(f"{f.name} is not schema v4 -- run scripts/split_drug_level_fields.py first")
        nct = record["nct_id"]["value"]
        drug = record["molecule"]["drug"]["value"]
        trial_name = record["identity"]["trial_name"]["value"]
        row = {"nct_id_file": f.stem, "schema_version": record["schema_version"]}
        for path, obj in flatten_fields({k: v for k, v in record.items() if k != "schema_version"}):
            if path not in seen:
                seen.add(path)
                field_order.append(path)
            # arm_results/effect_estimates already have their own dedicated CSVs
            # (keyed on nct_id + endpoint_rank + endpoint_position) and can run to
            # hundreds of rows per trial -- embedding the whole list again as one
            # JSON cell here blows past Python's csv module field-size limit for a
            # trial with a lot of endpoints x timepoints x arms. Source provenance
            # is still recorded below regardless.
            if path not in ("results.arm_results", "results.effect_estimates"):
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
        results = record["results"]
        arm_result_csv_rows.extend(arm_result_rows(nct, drug, trial_name, results))
        effect_estimate_csv_rows.extend(effect_estimate_rows(nct, drug, trial_name, results))

    write_csv(ROOT / "trials.csv", ["nct_id_file", "schema_version"] + field_order, trial_rows)
    write_csv(ROOT / "sources.csv", ["nct_id", "field", "source_type", "source_url", "source_excerpt", "extracted_by", "reviewed_by", "confidence"], source_rows)
    ep_cols = ["nct_id", "drug", "trial_name", "rank", "position", "measure_type", "scale", "scale_component", "scale_variant",
               "baseline_reference", "timepoints", "through", "analysis_population", "subgroup_labels", "study_period", "event_type",
               "criterion_index", "criterion_role"] + [f"criterion_{k}" for k in CRITERION_COLS] + ["verbatim"]
    write_csv(ROOT / "endpoints.csv", ep_cols, ep_rows)
    write_csv(ROOT / "severity_criteria.csv", ["nct_id", "drug", "trial_name", "criterion_index", "severity_label", "basis"] + CRITERION_COLS + ["scale_anchors"], sev_rows)
    write_csv(ROOT / "adverse_event_rates.csv", ["nct_id", "drug", "trial_name", "measure", "arm", "meddra_pt", "meddra_soc", "n_affected", "n_at_risk", "pct"], ae_rows)
    arm_result_cols = ["nct_id", "drug", "trial_name", "endpoint_rank", "endpoint_position", "endpoint_verbatim_sha1",
                        "arm_id", "timepoint", "analysis_population", "study_period", "denominator", "value_type",
                        "reported_value", "reported_unit", "responders", "response_rate_pct", "rate_is_derived",
                        "dispersion_type", "dispersion_value", "ci_pct", "ci_lower", "ci_upper", "ctgov_class_title"]
    write_csv(ROOT / "arm_results.csv", arm_result_cols, arm_result_csv_rows)
    effect_estimate_cols = ["nct_id", "drug", "trial_name", "endpoint_rank", "endpoint_position", "endpoint_verbatim_sha1",
                             "timepoint", "test_arm_id", "reference_arm_id", "comparison_kind", "effect_type",
                             "effect_type_verbatim", "effect_value", "ci_pct", "ci_lower", "ci_upper", "ci_sides",
                             "p_value_comparator", "p_value", "p_value_verbatim", "statistical_method", "adjusted_for"]
    write_csv(ROOT / "effect_estimates.csv", effect_estimate_cols, effect_estimate_csv_rows)

    drug_files = sorted(DRUGS_DIR.glob("*.json"))
    if not drug_files:
        raise SystemExit(f"No drug files found in {DRUGS_DIR} -- run scripts/split_drug_level_fields.py first")
    drug_rows, drug_source_rows, drug_app_rows = [], [], []
    for f in drug_files:
        record = json.loads(f.read_text())
        if record.get("schema_version") != 1:
            raise SystemExit(f"{f.name} is not drug schema v1")
        row, sources = drug_row_and_sources(record)
        drug_rows.append(row)
        drug_source_rows.extend(sources)
        app_rows, app_sources = drug_application_rows_and_sources(record)
        drug_app_rows.extend(app_rows)
        drug_source_rows.extend(app_sources)

    write_csv(ROOT / "drugs.csv", ["drug", "schema_version"] + list(DRUG_SINGLE_VALUED) + ["trial_ids"], drug_rows)
    write_csv(ROOT / "drug_applications.csv", ["drug", "application_number", "regulatory_application", "orange_book"], drug_app_rows)
    write_csv(ROOT / "drug_sources.csv", ["drug", "field", "source_type", "source_url", "source_excerpt", "extracted_by", "reviewed_by", "confidence"], drug_source_rows)


if __name__ == "__main__":
    main()
