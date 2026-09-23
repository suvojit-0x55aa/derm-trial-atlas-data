#!/usr/bin/env python3
"""Assemble selected evidence into a schema-valid patch; never generate quotations."""
import argparse
import json
import math
import re
from pathlib import Path

import spans
import verify


EXTRACTED_BY = "luna (gpt-6-luna) cycle-25 extraction pass"
SOURCE_TYPES = set(verify.DRUG["properties"]["mechanism_of_action"]["properties"]["source_type"]["enum"])
LEGACY_CT_TYPE = "ctgov_text_extraction (free text) / ctgov_api (structured numbers)"
DRAFT_KEYS = {"value", "file_key", "section", "span_ids", "note", "confidence"}


def numbers(value, path="value"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from numbers(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from numbers(child, f"{path}[{i}]")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield path, value


def numeric_warnings(value, records):
    warnings = []
    for path, number in numbers(value):
        # A literal token, not 6 inside 16 or 0.6; no unit conversion/rounding.
        pattern = re.compile(r"(?<![\w.,+\-])" + re.escape(str(number)) + r"(?![\w.,]\d|[\w])")
        if not any(pattern.search(r["text"]) for r in records):
            warnings.append(f"{path}={number} does not literally appear in selected spans")
    return warnings


def require(condition, message):
    if not condition:
        raise ValueError(message)


def boolean_warnings(value, path="value"):
    """Surface every assertion; lexical matching cannot establish boolean support."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from boolean_warnings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from boolean_warnings(child, f"{path}[{i}]")
    elif isinstance(value, bool):
        yield (f"{path}={str(value).lower()}: boolean assertion requires evidence; "
               "double-check selected spans (silence is not false)")


def check_published_results(value, source_type, job):
    require(source_type in {"openfda_label", "publication_extraction"},
            "published_results requires openfda_label or publication_extraction; "
            "CT.gov registry results belong in results.arm_results")
    entries = spans.read_json(job / "endpoint_keys.json")
    require(isinstance(entries, list) and all(isinstance(e, dict) and isinstance(e.get("key"), dict)
                                            for e in entries),
            "endpoint_keys.json must list entries with endpoint key objects")
    keys = [entry["key"] for entry in entries]
    base = spans.read_json(job / "base.json")
    arms = ((base.get("results") or {}).get("arms") or {}).get("value") or []
    arm_ids = {a.get("arm_id") for a in arms if isinstance(a, dict)}
    require(bool(arm_ids), "published_results needs base.json results.arms (the trial's registered arm ids) to join rows")
    groups = {}
    for i, row in enumerate(value):
        require(row["endpoint"] in keys,
                f"value[{i}].endpoint must exactly match a key listed in endpoint_keys.json")
        require(row["arm_id"] in arm_ids,
                f"value[{i}].arm_id {row['arm_id']!r} must be an arm_id from base.json results.arms "
                f"({', '.join(sorted(arm_ids))}); map label column names to the registered arm")
        key = json.dumps(row["endpoint"], sort_keys=True)
        groups.setdefault((key, row["arm_id"]), []).append((i, row))
    for rows in groups.values():
        if len(rows) < 2:
            continue
        titles = set()
        for i, row in rows:
            title = row["ctgov_class_title"]
            normalized = spans.collapse(title).casefold() if isinstance(title, str) else ""
            require(normalized and normalized not in titles,
                    f"value[{i}].ctgov_class_title must be nonempty and distinguishing for rows "
                    "sharing an endpoint key and arm; otherwise use distinct listed endpoint keys")
            titles.add(normalized)


def check_intervention_descriptions(value, job):
    ctgov = spans.read_json(job / "ctgov.json")
    interventions = ctgov.get("protocolSection", {}).get("armsInterventionsModule", {}).get("interventions", [])
    require(isinstance(interventions, list), "CT.gov interventions must be a list")
    for i, row in enumerate(value):
        matches = [item for item in interventions if isinstance(item, dict)
                   and item.get("name") == row["intervention_name"]]
        require(len(matches) == 1,
                f"value[{i}].intervention_name must match exactly one CT.gov intervention name")
        description = matches[0].get("description")
        if description is None:
            description = ""
        require(isinstance(description, str) and row["description"] == description,
                f"value[{i}].description must equal the CT.gov intervention description verbatim "
                '(empty string when absent); description is provenance, never edited')


def sourced(path, draft, index, sources, job):
    require(isinstance(draft, dict) and set(draft) == DRAFT_KEYS,
            "draft keys must be value, file_key, section, span_ids, note, confidence")
    spec = verify.SPEC.get(path) or verify.DRUG_SPEC.get(path)
    require(spec is not None, "unknown schema field")
    require(draft["value"] is not None, "null value must be not_found")
    errors = verify.validate(draft["value"], spec, path)
    require(not errors, "schema: " + "; ".join(errors))
    for location, number in numbers(draft["value"]):
        require(not isinstance(number, float) or math.isfinite(number), f"{location}: non-finite number")
    confidence = draft["confidence"]
    require(type(confidence) in (int, float) and math.isfinite(confidence) and 0 <= confidence < 1,
            "confidence must be finite, >= 0 and < 1 (never boolean)")
    require(isinstance(draft["file_key"], str), "file_key must be a string")
    ids = draft["span_ids"]
    require(isinstance(ids, list) and ids and all(isinstance(i, str) for i in ids),
            "span_ids must be a nonempty list of strings")
    require(len(set(ids)) == len(ids), "duplicate span_ids")
    require(all(i in index for i in ids), "unknown span id")
    records = [index[i] for i in ids]
    require(all(i.split(":")[0] == draft["file_key"] for i in ids),
            "all span_ids must belong to file_key (one source per field)")
    files = {r["file"] for r in records}
    require(len(files) == 1, "mixed source files")
    file = records[0]["file"]
    require(file in sources, f"{file} missing from sources.json")
    source = sources[file]
    require(isinstance(source, dict), "source manifest entry must be an object")
    source_type = source.get("source_type")
    if file == "ctgov.json" and source_type == LEGACY_CT_TYPE:
        source_type = "ctgov_text_extraction"
    require(isinstance(source_type, str) and source_type in SOURCE_TYPES and source_type != "needs_extraction",
            "source_type must be a closed enum in sources.json")
    require(file != "ctgov.json" or source_type == "ctgov_text_extraction",
            "string-leaf evidence requires ctgov_text_extraction in sources.json")
    url = source.get("url")
    require(isinstance(url, str) and url.startswith(("https://", "http://")), "invalid source URL in manifest")
    require(isinstance(draft["section"], str) and draft["section"].strip(), "section must be nonempty text")
    require(isinstance(draft["note"], str), "note must be text")
    section = spans.collapse(spans.unquote(draft["section"]))
    note = spans.collapse(spans.unquote(draft["note"]))
    excerpt = section + ": " + " ".join('"' + r["text"] + '"' for r in records)
    if note:
        excerpt += " -- " + note
    # The supplied verifier searches all files together. Enforce the stronger
    # condition here: every parsed quote is contained in one selected candidate.
    quotes = verify.quotes(excerpt)
    require(bool(quotes), "selected evidence has no quote accepted by verify.py (minimum 12 characters)")
    require(all(any(verify.norm(q) in verify.norm(r["text"]) for r in records) for q in quotes),
            "quote parser crossed an evidence boundary")
    if path == "results.published_results":
        check_published_results(draft["value"], source_type, job)
    if path == "molecule.dosing_regimen":
        check_intervention_descriptions(draft["value"], job)
    if path == "identity.why_stopped":
        ctgov = spans.read_json(job / "ctgov.json")
        reason = ctgov.get("protocolSection", {}).get("statusModule", {}).get("whyStopped")
        require(file == "ctgov.json" and isinstance(reason, str) and draft["value"] == reason,
                "why_stopped must equal ctgov protocolSection.statusModule.whyStopped verbatim")
        require(all(r["section"].split(" / ")[0] == "$.protocolSection.statusModule.whyStopped"
                    for r in records), "why_stopped evidence must come from the whyStopped leaf")
    return {"value": draft["value"], "source_type": source_type, "source_url": url,
            "source_excerpt": excerpt, "extracted_by": EXTRACTED_BY,
            "reviewed_by": None, "confidence": confidence}, (
                numeric_warnings(draft["value"], records) + list(boolean_warnings(draft["value"])))


def assemble(job, draft, partial=False):
    job = Path(job)
    task = spans.read_json(job / "TASK.json")
    wanted = task["fields"]
    require(isinstance(wanted, list) and all(isinstance(p, str) for p in wanted)
            and len(set(wanted)) == len(wanted), "TASK.fields must contain unique field paths")
    require(isinstance(draft, dict) and set(draft) <= {"fields", "trial_mapping"},
            "draft must contain fields and optional trial_mapping")
    entries = draft.get("fields")
    require(isinstance(entries, dict) and bool(entries), "draft.fields must be a nonempty object")
    mapping = draft.get("trial_mapping", "")
    require(isinstance(mapping, str), "trial_mapping must be text")
    index = spans.load(job)
    sources = spans.read_json(job / "sources.json")
    require(isinstance(sources, dict), "sources.json must be an object")
    patch = {"fields": {}, "not_found": {}, "trial_mapping": mapping}
    report, warnings = {}, {}
    for path in dict.fromkeys([*wanted, *entries]):
        if path not in entries:
            if not partial:
                report[path] = ["missing from draft; attempt or give an honest not_found reason"]
            continue
        report[path] = []
        try:
            require(path in wanted, "field not requested by TASK.json")
            item = entries[path]
            if isinstance(item, dict) and set(item) == {"not_found"}:
                reason = item["not_found"]
                require(isinstance(reason, str) and reason.strip(), "not_found reason must be nonempty text")
                patch["not_found"][path] = spans.collapse(reason)
            else:
                patch["fields"][path], warnings[path] = sourced(path, item, index, sources, job)
        except ValueError as exc:
            report[path].append(str(exc))
    for path, issues in verify.check(job, patch).items():
        report[path].extend(issues)
    return patch, report, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("--draft", default="draft.json", help="path relative to job (default draft.json)")
    parser.add_argument("--partial", action="store_true", help="two-field smoke tests only; allows unattempted TASK fields")
    args = parser.parse_args()
    output = args.job / "patch.json"
    try:
        draft = spans.read_json(args.job / args.draft)
        patch, report, warnings = assemble(args.job, draft, args.partial)
        print(f'{"STATUS":<12} FIELD / DETAIL')
        for path, issues in report.items():
            status = "FAIL" if issues else "NOT_FOUND" if path in patch["not_found"] else "PASS"
            print(f"{status:<12} {path}")
            for issue in issues:
                print(f"             {issue}")
            for warning in warnings.get(path, []):
                print(f"WARNING      {path}: {warning}")
        require(not any(report.values()), "assembly failed; patch.json was not written")
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(patch, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(output)
        if args.partial:
            print("PARTIAL TEST ONLY: missing TASK fields allowed; not a completed extraction.")
        print(f"Wrote {output}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"ERROR: {exc}\nExisting patch.json, if any, is unchanged; do not submit it as this run's output.\n")


if __name__ == "__main__":
    main()
