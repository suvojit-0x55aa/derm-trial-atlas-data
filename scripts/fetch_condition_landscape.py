#!/usr/bin/env python3
"""
Pull the FULL ClinicalTrials.gov trial landscape for one or more
dermatology conditions -- every trial status (recruiting, terminated,
withdrawn, completed, ...), not just the completed/placebo-controlled
pivotal trials the curated atlas in data/trials/ deliberately restricts
itself to (see AGENTS.md for that curation history).

This is a separate, general-purpose tool. It does NOT read or write
anything under data/trials/ or the generated CSVs -- it writes to its own
tree at data/condition_landscape/<condition-slug>/. See
docs/condition-landscape-quickstart.md for the full usage guide (written
for a reader who has never seen this repo's other pipeline).

Output per condition, under data/condition_landscape/<condition-slug>/:
    trials/<NCT_ID>.json   -- one lightweight record per matching trial
    drugs.json             -- distinct drug/biologic interventions across
                               every trial for this condition
    manifest.json           -- condition, fetch date, trial count, status
                               breakdown for this run
    documents/<NCT_ID>/*.pdf + *.txt   -- only with --fetch-protocol-pdfs

Every trial record is its own thing, regardless of status -- an
IN-FLIGHT or TERMINATED trial is real landscape data, not a gap to fill.
Fields that only make sense for a completed trial with posted results
(e.g. results tables) are out of scope here on purpose; this tool never
attempts the curated atlas's depth (mechanism of action, dosing regimen,
severity criteria, sourced-value provenance envelope). Unlike the curated
atlas, a field here is either what CT.gov's API actually returned or
null -- there is no "needs_extraction" placeholder, because nothing here
is meant to be filled in by a later extraction pass.

Run:
    python3 scripts/fetch_condition_landscape.py --condition psoriasis
    python3 scripts/fetch_condition_landscape.py --condition psoriasis --condition eczema
    python3 scripts/fetch_condition_landscape.py --condition "psoriasis,eczema"
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_BASE = "https://clinicaltrials.gov/api/v2/studies"
CDN_BASE = "https://cdn.clinicaltrials.gov/large-docs"
SCRIPT_VERSION = "1.0"
EXTRACTED_BY = f"fetch_condition_landscape.py v{SCRIPT_VERSION} (ctgov_api v2, any status)"

# CT.gov intervention types that count as a "drug" for drugs.json. Other
# real intervention types on these trials (PROCEDURE, DEVICE, BEHAVIORAL,
# RADIATION, DIAGNOSTIC_TEST, OTHER) are kept on the trial record itself
# but not surfaced as a "drug".
DRUG_INTERVENTION_TYPES = {"DRUG", "BIOLOGICAL"}

DEFAULT_PAGE_SIZE = 1000
DEFAULT_SLEEP = 0.34
DEFAULT_MAX_PROTOCOL_PDFS = 25


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(condition: str) -> str:
    slug = condition.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-") or "condition"


def _http_get_json(url: str, timeout: int = 30) -> dict:
    """Thin wrapper so tests can mock exactly one seam."""
    req = urllib.request.Request(url, headers={"User-Agent": "derm-trial-atlas-data/condition-landscape"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_condition_page(condition: str, page_token: str | None, page_size: int) -> dict:
    params = {"query.cond": condition, "pageSize": str(page_size)}
    if page_token:
        params["pageToken"] = page_token
    url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    return _http_get_json(url)


def fetch_all_studies(condition: str, page_size: int = DEFAULT_PAGE_SIZE,
                       sleep: float = DEFAULT_SLEEP, max_trials: int | None = None) -> list[dict]:
    """Every study CT.gov's query.cond=<condition> matches, any overallStatus,
    paginated via nextPageToken. Each returned dict is a full study record
    (protocolSection + hasResults) -- the list endpoint does not include
    referencesModule/documentSection, which is why supplementary data needs
    its own per-trial fetch (see fetch_supplementary)."""
    studies: list[dict] = []
    page_token = None
    while True:
        payload = fetch_condition_page(condition, page_token, page_size)
        studies.extend(payload.get("studies", []))
        if max_trials is not None and len(studies) >= max_trials:
            return studies[:max_trials]
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
        time.sleep(sleep)
    return studies


def fetch_supplementary(nct_id: str, timeout: int = 30) -> dict:
    """One request per trial for the two fields the bulk list endpoint
    omits: referencesModule (linked publications) and documentSection
    (posted Protocol/SAP/ICF docs). Best-effort: a fetch failure here must
    not take down the whole run, since this is supplementary, not core,
    data."""
    url = f"{API_BASE}/{nct_id}?fields=ReferencesModule,DocumentSection"
    try:
        return _http_get_json(url, timeout=timeout)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return {"_fetch_error": str(exc)}


def _get(d: dict, *path, default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def build_trial_record(raw: dict, supplementary_raw: dict | None, fetched_at: str) -> dict:
    ps = raw.get("protocolSection", {})
    idm = ps.get("identificationModule", {})
    sm = ps.get("statusModule", {})
    spm = ps.get("sponsorCollaboratorsModule", {})
    dm = ps.get("designModule", {})
    elig = ps.get("eligibilityModule", {})
    arms = ps.get("armsInterventionsModule", {})
    outcomes = ps.get("outcomesModule", {})
    conditions_mod = ps.get("conditionsModule", {})
    contacts = ps.get("contactsLocationsModule", {})

    nct_id = idm.get("nctId")
    design_info = dm.get("designInfo", {})
    masking_info = design_info.get("maskingInfo", {})
    enrollment = dm.get("enrollmentInfo", {})

    interventions = [
        {
            "type": i.get("type"),
            "name": i.get("name"),
            "description": i.get("description"),
        }
        for i in arms.get("interventions", [])
    ]

    primary_outcomes = [
        {"measure": o.get("measure"), "time_frame": o.get("timeFrame"), "description": o.get("description")}
        for o in outcomes.get("primaryOutcomes", [])
        if o.get("measure")
    ]
    secondary_outcomes = [
        {"measure": o.get("measure"), "time_frame": o.get("timeFrame"), "description": o.get("description")}
        for o in outcomes.get("secondaryOutcomes", [])
        if o.get("measure")
    ]

    locations = contacts.get("locations", [])
    countries = sorted({loc.get("country") for loc in locations if loc.get("country")})

    supplementary_raw = supplementary_raw or {}
    sup_ps = supplementary_raw.get("protocolSection", {})
    references = [
        {"pmid": r.get("pmid"), "type": r.get("type"), "citation": r.get("citation")}
        for r in _get(sup_ps, "referencesModule", "references", default=[])
    ]
    large_docs = _get(supplementary_raw, "documentSection", "largeDocumentModule", "largeDocs", default=[])
    documents = [
        {
            "label": d.get("label"),
            "type_abbrev": d.get("typeAbbrev"),
            "has_protocol": d.get("hasProtocol"),
            "has_sap": d.get("hasSap"),
            "has_icf": d.get("hasIcf"),
            "date": d.get("date"),
            "filename": d.get("filename"),
            "size_bytes": d.get("size"),
            "url": f"{CDN_BASE}/{nct_id[-2:]}/{nct_id}/{d['filename']}" if nct_id and d.get("filename") else None,
            "local_text_path": None,
        }
        for d in large_docs
    ]
    supplementary_fetch_error = supplementary_raw.get("_fetch_error")

    return {
        "nct_id": nct_id,
        "provenance": {
            "fetched_at": fetched_at,
            "source_url": f"{API_BASE}/{nct_id}",
            "extracted_by": EXTRACTED_BY,
        },
        "status": {
            "overall_status": sm.get("overallStatus"),
            "why_stopped": sm.get("whyStopped"),
            "start_date": _get(sm, "startDateStruct", "date"),
            "primary_completion_date": _get(sm, "primaryCompletionDateStruct", "date"),
            "completion_date": _get(sm, "completionDateStruct", "date"),
            "last_update_post_date": _get(sm, "lastUpdatePostDateStruct", "date"),
            "has_results": raw.get("hasResults", False),
        },
        "identity": {
            "brief_title": idm.get("briefTitle"),
            "official_title": idm.get("officialTitle"),
            "acronym": idm.get("acronym"),
            "lead_sponsor": _get(spm, "leadSponsor", "name"),
            "collaborators": [c.get("name") for c in spm.get("collaborators", []) if c.get("name")],
            "phases": dm.get("phases") or [],
            "study_type": dm.get("studyType"),
        },
        "conditions": conditions_mod.get("conditions") or [],
        "interventions": interventions,
        "design": {
            "allocation": design_info.get("allocation"),
            "intervention_model": design_info.get("interventionModel"),
            "primary_purpose": design_info.get("primaryPurpose"),
            "masking": masking_info.get("masking"),
            "number_of_arms": len(arms.get("armGroups") or []) or None,
            "enrollment_count": enrollment.get("count"),
            "enrollment_type": enrollment.get("type"),
        },
        "eligibility": {
            "min_age": elig.get("minimumAge"),
            "max_age": elig.get("maximumAge"),
            "sex": elig.get("sex"),
            "healthy_volunteers": elig.get("healthyVolunteers"),
            "criteria_text": elig.get("eligibilityCriteria"),
        },
        "outcomes": {
            "primary": primary_outcomes,
            "secondary": secondary_outcomes,
        },
        "locations": {
            "count": len(locations),
            "countries": countries,
        },
        "supplementary": {
            "publications": references,
            "documents": documents,
            "fetch_error": supplementary_fetch_error,
        },
    }


def extract_drugs(trial_records: list[dict]) -> list[dict]:
    """Distinct DRUG/BIOLOGICAL interventions actually tested across these
    trials -- no FDA-approval filter, no curation. Deduped case-insensitively
    on the intervention name; the first-seen casing is kept as the display
    name."""
    by_key: dict[str, dict] = {}
    for record in trial_records:
        nct_id = record["nct_id"]
        for interv in record["interventions"]:
            if interv.get("type") not in DRUG_INTERVENTION_TYPES:
                continue
            name = interv.get("name")
            if not name:
                continue
            key = name.strip().casefold()
            entry = by_key.setdefault(key, {
                "name": name.strip(),
                "intervention_types_seen": set(),
                "nct_ids": [],
            })
            entry["intervention_types_seen"].add(interv["type"])
            if nct_id not in entry["nct_ids"]:
                entry["nct_ids"].append(nct_id)

    drugs = []
    for entry in by_key.values():
        drugs.append({
            "name": entry["name"],
            "intervention_types_seen": sorted(entry["intervention_types_seen"]),
            "trial_count": len(entry["nct_ids"]),
            "nct_ids": sorted(entry["nct_ids"]),
        })
    drugs.sort(key=lambda d: d["name"].casefold())
    return drugs


def status_breakdown(trial_records: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for record in trial_records:
        status = record["status"]["overall_status"] or "UNKNOWN"
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def download_protocol_docs(record: dict, out_dir: Path, budget: list[int], sleep: float) -> None:
    """Best-effort PDF download + pdftotext -layout conversion for this
    trial's posted Protocol/SAP/ICF docs, mirroring
    scripts/fetch_protocol_docs.py's CDN URL pattern. `budget` is a
    single-element list used as a mutable counter so callers can cap the
    total number of PDFs downloaded across an entire run (a common
    condition can have hundreds of trials with posted documents -- see
    docs/condition-landscape-quickstart.md)."""
    if budget[0] <= 0:
        return
    nct_id = record["nct_id"]
    documents = record["supplementary"]["documents"]
    if not documents:
        return
    pdftotext_available = shutil.which("pdftotext") is not None
    trial_doc_dir = out_dir / nct_id
    for doc in documents:
        if budget[0] <= 0:
            return
        url = doc.get("url")
        filename = doc.get("filename")
        if not url or not filename:
            continue
        trial_doc_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = trial_doc_dir / filename
        try:
            if not pdf_path.exists():
                urllib.request.urlretrieve(url, pdf_path)
                time.sleep(sleep)
            if pdftotext_available:
                txt_path = pdf_path.with_suffix(".txt")
                if not txt_path.exists():
                    subprocess.run(["pdftotext", "-layout", str(pdf_path), str(txt_path)], check=True)
                doc["local_text_path"] = str(txt_path.relative_to(out_dir.parent))
            doc["local_pdf_path"] = str(pdf_path.relative_to(out_dir.parent))
        except (urllib.error.URLError, urllib.error.HTTPError, subprocess.CalledProcessError, OSError) as exc:
            doc["download_error"] = str(exc)
        budget[0] -= 1


def build_manifest(condition: str, condition_slug: str, trial_records: list[dict],
                    drugs: list[dict], fetched_at: str, args: argparse.Namespace) -> dict:
    return {
        "condition": condition,
        "condition_slug": condition_slug,
        "query": {"query.cond": condition},
        "source": API_BASE,
        "fetched_at": fetched_at,
        "script_version": SCRIPT_VERSION,
        "trial_count": len(trial_records),
        "drug_count": len(drugs),
        "status_breakdown": status_breakdown(trial_records),
        "options": {
            "page_size": args.page_size,
            "max_trials": args.max_trials,
            "fetch_publications": not args.skip_supplementary,
            "fetch_protocol_pdfs": args.fetch_protocol_pdfs,
            "max_protocol_pdfs": args.max_protocol_pdfs if args.fetch_protocol_pdfs else 0,
        },
        "notes": (
            "Every trial matching CT.gov's query.cond for this condition, any "
            "overallStatus. Not filtered by FDA-approval status, phase, or "
            "design -- this is breadth, not the curated pivotal-trial atlas "
            "in data/trials/. See docs/condition-landscape-quickstart.md."
        ),
    }


def parse_conditions(raw_values: list[str]) -> list[str]:
    conditions: list[str] = []
    for raw in raw_values:
        for part in raw.split(","):
            part = part.strip()
            if part and part not in conditions:
                conditions.append(part)
    return conditions


def run_condition(condition: str, out_root: Path, args: argparse.Namespace) -> None:
    slug = slugify(condition)
    condition_dir = out_root / slug
    trials_dir = condition_dir / "trials"
    trials_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{condition}] listing trials (query.cond={condition!r})...")
    raw_studies = fetch_all_studies(
        condition, page_size=args.page_size, sleep=args.sleep, max_trials=args.max_trials
    )
    print(f"[{condition}] {len(raw_studies)} trials found (all statuses)")

    fetched_at = now_iso()
    trial_records = []
    pdf_budget = [args.max_protocol_pdfs if args.fetch_protocol_pdfs else 0]
    for i, raw in enumerate(raw_studies, start=1):
        nct_id = _get(raw, "protocolSection", "identificationModule", "nctId")
        if not nct_id:
            continue
        supplementary_raw = None
        if not args.skip_supplementary:
            supplementary_raw = fetch_supplementary(nct_id)
            time.sleep(args.sleep)
        record = build_trial_record(raw, supplementary_raw, fetched_at)
        if args.fetch_protocol_pdfs:
            download_protocol_docs(record, condition_dir / "documents", pdf_budget, args.sleep)
        trial_records.append(record)
        (trials_dir / f"{nct_id}.json").write_text(json.dumps(record, indent=2) + "\n")
        if i % 50 == 0:
            print(f"[{condition}] {i}/{len(raw_studies)} trials processed...")

    drugs = extract_drugs(trial_records)
    (condition_dir / "drugs.json").write_text(json.dumps({
        "condition": condition,
        "condition_slug": slug,
        "fetched_at": fetched_at,
        "drug_count": len(drugs),
        "drugs": drugs,
    }, indent=2) + "\n")

    manifest = build_manifest(condition, slug, trial_records, drugs, fetched_at, args)
    (condition_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"[{condition}] wrote {len(trial_records)} trial files + drugs.json + manifest.json to {condition_dir}")
    print(f"[{condition}] status breakdown: {manifest['status_breakdown']}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Pull the full ClinicalTrials.gov landscape (every status) for one or more conditions."
    )
    parser.add_argument(
        "--condition", action="append", default=[], required=True,
        help="Condition name to query (repeatable, or comma-separated), e.g. --condition psoriasis --condition eczema",
    )
    parser.add_argument(
        "--out-dir", default=None,
        help="Output root (default: <repo>/data/condition_landscape)",
    )
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Seconds between CT.gov requests")
    parser.add_argument(
        "--max-trials", type=int, default=None,
        help="Cap trials fetched per condition (useful for a quick test run on a common condition)",
    )
    parser.add_argument(
        "--skip-supplementary", action="store_true",
        help="Skip the per-trial publications/documents lookup (listing data only, much faster)",
    )
    parser.add_argument(
        "--fetch-protocol-pdfs", action="store_true",
        help="Download and pdftotext-convert posted Protocol/SAP/ICF PDFs (off by default: can be slow/large for a common condition)",
    )
    parser.add_argument(
        "--max-protocol-pdfs", type=int, default=DEFAULT_MAX_PROTOCOL_PDFS,
        help=f"Cap on PDFs downloaded per condition when --fetch-protocol-pdfs is set (default {DEFAULT_MAX_PROTOCOL_PDFS})",
    )
    args = parser.parse_args(argv)

    conditions = parse_conditions(args.condition)
    if not conditions:
        parser.error("no conditions given")

    repo_root = Path(__file__).resolve().parent.parent
    out_root = Path(args.out_dir) if args.out_dir else repo_root / "data" / "condition_landscape"
    out_root.mkdir(parents=True, exist_ok=True)

    for condition in conditions:
        run_condition(condition, out_root, args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
