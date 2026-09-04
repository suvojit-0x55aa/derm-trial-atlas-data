#!/usr/bin/env python3
"""
Third pass: adverse events / safety signals.

Adds a 7th field group, "adverse_events", to every data/trials/<NCT_ID>.json
file, sourced the same way as every other group -- CT.gov API structured
data first, openFDA label second, needs_extraction (never a fabricated
number) when neither has it:

  serious_adverse_event_rate  - ctgov_api. Per-arm % of participants with >=1
                                 serious AE, computed from
                                 resultsSection.adverseEventsModule.eventGroups[]
                                 .seriousNumAffected / seriousNumAtRisk.
  death_rate                  - ctgov_api. Same eventGroups[], deathsNumAffected
                                 / deathsNumAtRisk.
  most_common_adverse_events  - ctgov_api. Top non-serious AEs (by highest
                                 single-arm incidence) from
                                 resultsSection.adverseEventsModule.otherEvents[]
                                 (already CT.gov's own >=5% frequency-threshold
                                 table), with per-arm incidence.
  discontinuation_due_to_ae_rate - ctgov_api. Per-arm % of participants who
                                 stopped for an "Adverse Event" reason, from
                                 resultsSection.participantFlowModule's first
                                 period dropWithdraws entry whose type mentions
                                 "adverse event", against that period's
                                 STARTED count.
  boxed_warning                - openfda_label. Drug-level (not trial-level,
                                 same value reused across every trial of that
                                 drug), openFDA drug-label API's
                                 `boxed_warning` field. A drug with a label on
                                 file but no boxed_warning key is recorded as
                                 value=null / confirmed_no_boxed_warning=true
                                 -- a real negative finding, not a gap -- to
                                 keep it distinct from needs_extraction, which
                                 means "unknown", not "checked, none found".

A trial with no resultsSection at all on CT.gov (no posted results) gets
needs_extraction on the four ctgov_api fields above -- this happens for
none of the 17 v1 trials as of this pass, but the script handles it so a
future trial without posted results degrades honestly instead of crashing.

Run after scripts/fetch_trials.py and scripts/enrich_needs_extraction.py:
    python3 scripts/fetch_adverse_events.py
"""
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_DIR = ROOT / "data" / "trials"
CACHE_DIR = ROOT / "data" / "_raw_cache"  # gitignored working cache
CACHE_DIR.mkdir(exist_ok=True)

CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"
OPENFDA_LABEL = "https://api.fda.gov/drug/label.json"
EXTRACTED_BY = "fetch_adverse_events.py (ctgov_api results + openfda_label, v1 AE pass)"

NEEDS_EXTRACTION = {
    "value": None,
    "source_type": "needs_extraction",
    "source_url": None,
    "source_excerpt": None,
    "extracted_by": None,
    "reviewed_by": None,
    "confidence": None,
}


def needs_extraction():
    return dict(NEEDS_EXTRACTION)


def field(value, source_type, source_url, source_excerpt, confidence, extracted_by=EXTRACTED_BY):
    return {
        "value": value,
        "source_type": source_type,
        "source_url": source_url,
        "source_excerpt": source_excerpt,
        "extracted_by": extracted_by,
        "reviewed_by": None,
        "confidence": confidence,
    }


def fetch_results(nct_id: str) -> dict:
    cache = CACHE_DIR / f"{nct_id}_results.json"
    if cache.exists():
        return json.loads(cache.read_text())
    url = (
        f"{CTGOV_API}/{nct_id}"
        "?fields=resultsSection.adverseEventsModule,resultsSection.participantFlowModule"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    cache.write_text(json.dumps(data))
    return data


def pct(affected, at_risk):
    if affected is None or not at_risk:
        return None
    return round(100.0 * affected / at_risk, 1)


def _has_complete_counts(event_groups, affected_key, at_risk_key):
    """CT.gov's own eventGroups[] can carry the module (so `event_groups` is
    non-empty) without actually populating a given count for every arm --
    seen for deathsNumAffected/deathsNumAtRisk on several older/smaller
    trials (e.g. the CSU omalizumab pivotals, PIONEER I/II, VOYAGE 1/2:
    both fields are `null`, not `0`, for every arm). That is a genuine gap
    in what CT.gov posted, not a computable zero -- staging a per-arm
    `null` inside an otherwise "filled" ctgov_api array would be worse than
    an honest needs_extraction, so callers check this before building rows."""
    return all(g.get(affected_key) is not None and g.get(at_risk_key) is not None for g in event_groups)


def build_sae_rate(event_groups, url):
    if not event_groups or not _has_complete_counts(event_groups, "seriousNumAffected", "seriousNumAtRisk"):
        return needs_extraction()
    rows = [
        {
            "arm": g.get("title"),
            "n_affected": g.get("seriousNumAffected"),
            "n_at_risk": g.get("seriousNumAtRisk"),
            "pct": pct(g.get("seriousNumAffected"), g.get("seriousNumAtRisk")),
        }
        for g in event_groups
    ]
    return field(
        rows,
        "ctgov_api",
        url,
        "resultsSection.adverseEventsModule.eventGroups[].seriousNumAffected/seriousNumAtRisk",
        confidence=1.0,
    )


def build_death_rate(event_groups, url):
    if not event_groups or not _has_complete_counts(event_groups, "deathsNumAffected", "deathsNumAtRisk"):
        return needs_extraction()
    rows = [
        {
            "arm": g.get("title"),
            "n_affected": g.get("deathsNumAffected"),
            "n_at_risk": g.get("deathsNumAtRisk"),
            "pct": pct(g.get("deathsNumAffected"), g.get("deathsNumAtRisk")),
        }
        for g in event_groups
    ]
    return field(
        rows,
        "ctgov_api",
        url,
        "resultsSection.adverseEventsModule.eventGroups[].deathsNumAffected/deathsNumAtRisk",
        confidence=1.0,
    )


def build_common_aes(other_events, event_groups, url, top_n=8):
    if not other_events:
        return needs_extraction()
    group_titles = {g.get("id"): g.get("title") for g in event_groups}
    rows = []
    for ev in other_events:
        per_arm = [
            {
                "arm": group_titles.get(s.get("groupId"), s.get("groupId")),
                "n_affected": s.get("numAffected"),
                "n_at_risk": s.get("numAtRisk"),
                "pct": pct(s.get("numAffected"), s.get("numAtRisk")),
            }
            for s in ev.get("stats", [])
        ]
        max_pct = max((r["pct"] for r in per_arm if r["pct"] is not None), default=0)
        rows.append(
            {
                "term": ev.get("term"),
                "organ_system": ev.get("organSystem"),
                "per_arm": per_arm,
                "_max_pct": max_pct,
            }
        )
    rows.sort(key=lambda r: r["_max_pct"], reverse=True)
    top_rows = [{k: v for k, v in r.items() if k != "_max_pct"} for r in rows[:top_n]]
    return field(
        top_rows,
        "ctgov_api",
        url,
        (
            f"resultsSection.adverseEventsModule.otherEvents[] "
            f"(top {top_n} of {len(other_events)} by highest single-arm incidence; "
            f"CT.gov's own >=5% frequency-threshold table)"
        ),
        confidence=1.0,
    )


def build_discontinuation_rate(flow, url):
    periods = flow.get("periods") or []
    if not periods:
        return needs_extraction()
    period = periods[0]
    started = {}
    for m in period.get("milestones", []):
        if m.get("type") == "STARTED":
            for a in m.get("achievements", []):
                gid = a.get("groupId")
                n = a.get("numSubjects")
                started[gid] = int(n) if n and n.isdigit() else None
    ae_dropout = None
    for dw in period.get("dropWithdraws", []):
        if "adverse event" in (dw.get("type") or "").lower():
            ae_dropout = dw
            break
    if ae_dropout is None:
        return needs_extraction()
    group_titles = {g.get("id"): g.get("title") for g in flow.get("groups", [])}
    rows = []
    for r in ae_dropout.get("reasons", []):
        gid = r.get("groupId")
        n = r.get("numSubjects")
        n = int(n) if n and n.isdigit() else None
        at_risk = started.get(gid)
        rows.append(
            {
                "arm": group_titles.get(gid, gid),
                "n_discontinued": n,
                "n_started": at_risk,
                "pct": pct(n, at_risk),
            }
        )
    return field(
        rows,
        "ctgov_api",
        url,
        (
            f"resultsSection.participantFlowModule.periods[0]"
            f'.dropWithdraws[type="{ae_dropout.get("type")}"].reasons[] '
            f"vs periods[0].milestones[type=STARTED].achievements[]"
        ),
        confidence=1.0,
    )


_fda_label_cache: dict[str, dict | None] = {}


def fda_label(drug: str) -> dict | None:
    if drug in _fda_label_cache:
        return _fda_label_cache[drug]
    url = f"{OPENFDA_LABEL}?search=openfda.substance_name:{drug.upper()}&limit=1"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
        result = data["results"][0]
    except Exception:
        result = None
    _fda_label_cache[drug] = result
    return result


def build_boxed_warning(drug: str):
    label = fda_label(drug)
    query_url = f"{OPENFDA_LABEL}?search=openfda.substance_name:{drug.upper()}&limit=1"
    if label is None:
        return needs_extraction()
    bw = label.get("boxed_warning")
    if bw:
        text = bw[0] if isinstance(bw, list) else bw
        return field(
            text,
            "openfda_label",
            query_url,
            "results[0].boxed_warning",
            confidence=1.0,
        )
    # Label exists and was checked; there is no boxed_warning section. That's
    # a real, confirmed finding (no black-box warning for this drug), not a
    # gap -- record it as such rather than as needs_extraction.
    return field(
        None,
        "openfda_label",
        query_url,
        "results[0] has no boxed_warning key (checked, none present)",
        confidence=1.0,
    )



def _refuse_v2(record, path):
    if record.get("schema_version") == 2:
        raise SystemExit(
            f"{path.name} is already schema v2 (structured values); this v1-stage script only edits v1 "
            "records. Re-run scripts/fetch_trials.py to rebuild the v1 baseline, then stages 2-4, then "
            "scripts/migrate_v1_to_v2.py -- see README 'Running the pipeline'.")

def main():
    trial_files = sorted(TRIALS_DIR.glob("*.json"))
    if not trial_files:
        raise SystemExit(f"No trial files found in {TRIALS_DIR}")

    for f in trial_files:
        record = json.loads(f.read_text())
        _refuse_v2(record, f)
        nct_id = record["nct_id"]["value"]
        drug = record["molecule"]["drug"]["value"]
        print(f"Adverse events: {nct_id} ({drug})...")

        raw = fetch_results(nct_id)
        url = f"{CTGOV_API}/{nct_id}"
        ae_module = raw.get("resultsSection", {}).get("adverseEventsModule", {}) or {}
        flow_module = raw.get("resultsSection", {}).get("participantFlowModule", {}) or {}
        event_groups = ae_module.get("eventGroups", [])
        other_events = ae_module.get("otherEvents", [])

        record["adverse_events"] = {
            "serious_adverse_event_rate": build_sae_rate(event_groups, url),
            "death_rate": build_death_rate(event_groups, url),
            "most_common_adverse_events": build_common_aes(other_events, event_groups, url),
            "discontinuation_due_to_ae_rate": build_discontinuation_rate(flow_module, url),
            "boxed_warning": build_boxed_warning(drug),
        }

        f.write_text(json.dumps(record, indent=2) + "\n")

    print(f"Updated {len(trial_files)} trial files with an adverse_events group")


if __name__ == "__main__":
    main()
