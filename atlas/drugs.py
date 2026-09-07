"""
Drug-level records (data/drugs/<slug>.json) -- schema v4's "search by drug,
not by trial" restructuring.

Six fields (molecule.mechanism_of_action, adverse_events.boxed_warning,
real_world_safety.faers_summary, exclusivity.{regulatory_application,
orange_book,purple_book}) are facts about a DRUG, not about any one trial:
mechanism of action and boxed warning come from the drug's own FDA label,
FAERS is an ingredient-level post-marketing safety summary, and Orange/
Purple Book exclusivity is a property of the drug's own NDA/BLA. Before v4,
every one of a drug's trials carried an independently-extracted, byte-
identical copy of each of these -- a dataset pass across the 127-trial
corpus found 1,588 verbatim-duplicated (source_excerpt, value) pairs this
way (a drug used across N indications paid this cost N times: Dupilumab x8,
Roflumilast x8, Secukinumab x6, Bimekizumab x5, Abrocitinib/Tapinarof/
Nemolizumab/Icotrokinra x4 each, ...).

v4 moves those 6 fields off the trial record entirely: extracted once into
data/drugs/<slug>.json, referenced (never copied) by every trial of that
drug via a small DRUG_REF pointer (see atlas/schema.py). This mirrors the
results layer's own reference-not-copy idiom for endpoints (atlas/results.py's
ENDPOINT_KEY) -- a trial's own copy of a moved field is a pointer, not a
re-description, so there is exactly one place to look up "everything about
this drug" and exactly one place a fix to it needs to land.

`identity.sponsor` looks drug-level but is NOT moved: it genuinely differs
across a drug's own trials when development/commercial rights changed hands
mid-program (Dupilumab's own trials split Regeneron/Sanofi; Difamilast's
split two distinct Otsuka legal entities) -- collapsing it to one drug-wide
value would be a real loss of trial-specific fact, not a dedup. Confirmed by
running the same duplicate-detection method the UX report's dataset pass
used, grouped by drug, before deciding this field list -- see AGENTS.md.

Similarly, exclusivity.regulatory_application/orange_book are NOT always a
single value per drug: Roflumilast holds 2 distinct FDA applications (cream
NDA 215985, foam NDA 217242), each with its own real, different Orange Book
row. A drug record's `applications` list has one entry per distinct
application_number (almost always exactly 1); a trial's own DRUG_REF pointer
carries the application_number it belongs to so the right entry resolves.

This module is the "search by drug" half of the pipeline strategy change:
`ensure_drug_record` is what a future one-off per-cycle script (see
AGENTS.md's scratch-checkout convention) should call when it discovers a new
trial -- it fetches/builds a drug's facts only the FIRST time that drug is
seen, and simply returns the already-committed record on every later trial
of the same drug, instead of a fresh, independent, wastefully-duplicated
extraction pass per trial.
"""
import copy
import json
import re
from pathlib import Path

DRUGS_DIR = Path(__file__).resolve().parent.parent / "data" / "drugs"

DRUG_SCHEMA_VERSION = 1

# The 7 fields that moved off the trial record (6 original + drug_characterization,
# added cycle 23 per captain instruction -- same drug-level rationale, same pattern).
# Order matches atlas/schema.py's DRUG spec / TRIAL's own field groups.
SINGLE_VALUED_FIELDS = {
    "mechanism_of_action": ("molecule", "mechanism_of_action"),
    "boxed_warning": ("adverse_events", "boxed_warning"),
    "faers_summary": ("real_world_safety", "faers_summary"),
    "drug_characterization": ("real_world_safety", "drug_characterization"),
    "purple_book": ("exclusivity", "purple_book"),
}
APPLICATION_KEYED_FIELDS = {
    "regulatory_application": ("exclusivity", "regulatory_application"),
    "orange_book": ("exclusivity", "orange_book"),
}


def slugify(drug_name: str) -> str:
    """'Roflumilast' -> 'roflumilast'; a real multi-word name (none exist yet
    in this corpus, but a future one might) gets hyphenated, not rejected."""
    s = re.sub(r"[^a-z0-9]+", "-", drug_name.strip().lower()).strip("-")
    if not s:
        raise ValueError(f"drug name {drug_name!r} has no slug-able characters")
    return s


def drug_path(drug_name: str, drugs_dir: Path = DRUGS_DIR) -> Path:
    return drugs_dir / f"{slugify(drug_name)}.json"


def load_drug(drug_name: str, drugs_dir: Path = DRUGS_DIR) -> dict | None:
    path = drug_path(drug_name, drugs_dir)
    return json.loads(path.read_text()) if path.exists() else None


def save_drug(record: dict, drugs_dir: Path = DRUGS_DIR) -> Path:
    drugs_dir.mkdir(parents=True, exist_ok=True)
    path = drug_path(record["drug"], drugs_dir)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return path


def _needs_extraction():
    return {"value": None, "source_type": "needs_extraction", "source_url": None,
            "source_excerpt": None, "extracted_by": None, "reviewed_by": None, "confidence": None}


def drug_ref(drug_name: str, application_number: str | None = None) -> dict:
    """The {"drug", "application_number"} pointer written into a trial's own
    molecule.mechanism_of_action / adverse_events.boxed_warning /
    real_world_safety.faers_summary / exclusivity.{regulatory_application,
    orange_book,purple_book}."""
    return {"drug": drug_name, "application_number": application_number}


def drug_ref_sv(drug_name: str, application_number: str | None = None) -> dict:
    """`drug_ref` wrapped in the sourced-value envelope every trial field
    uses, with source_type "drug_level_ref" -- the pointer itself is never
    "unknown"; only the drug-level fact it points to can be needs_extraction."""
    return {
        "value": drug_ref(drug_name, application_number),
        "source_type": "drug_level_ref", "source_url": None, "source_excerpt": None,
        "extracted_by": None, "reviewed_by": None, "confidence": None,
    }


def application_number_of(trial: dict) -> str | None:
    """The application_number a trial's regulatory_application currently
    names -- works on both a pre-split (v3, full value) and already-split
    (v4, DRUG_REF pointer) trial record, so build_drug_records and a future
    incremental add-a-trial script can both call it."""
    ra = trial["exclusivity"]["regulatory_application"]
    if ra["source_type"] == "drug_level_ref":
        return ra["value"].get("application_number")
    if ra["source_type"] == "needs_extraction" or not ra["value"]:
        return None
    return ra["value"].get("application_number")


def build_drug_records(trial_records: list) -> dict:
    """drug name -> drug record, built from pre-split (v3-shaped, full-value)
    trial records. Confirmed identical (same source_type AND same value)
    across every trial of a drug for mechanism_of_action, boxed_warning,
    faers_summary, and purple_book, and identical WITHIN a given
    application_number for regulatory_application/orange_book (see AGENTS.md)
    -- so taking the first trial's copy (by nct_id order, for determinism) is
    lossless, not an approximation. `identity.sponsor` is deliberately not
    included -- see this module's docstring."""
    by_drug = {}
    for t in trial_records:
        by_drug.setdefault(t["molecule"]["drug"]["value"], []).append(t)

    records = {}
    for drug, trials in by_drug.items():
        trials = sorted(trials, key=lambda t: t["nct_id"]["value"])
        first = trials[0]
        record = {
            "schema_version": DRUG_SCHEMA_VERSION,
            "drug": drug,
            "applications": [],
            "trial_ids": [t["nct_id"]["value"] for t in trials],
        }
        for field, (group, key) in SINGLE_VALUED_FIELDS.items():
            record[field] = copy.deepcopy(first[group][key])

        seen_apps = set()
        for t in trials:
            app_num = application_number_of(t)
            if app_num in seen_apps:
                continue
            seen_apps.add(app_num)
            record["applications"].append({
                "application_number": app_num,
                "regulatory_application": copy.deepcopy(t["exclusivity"]["regulatory_application"]),
                "orange_book": copy.deepcopy(t["exclusivity"]["orange_book"]),
            })
        records[drug] = record
    return records


def split_trial_record(trial: dict) -> dict:
    """v3(-shaped) trial record -> v4: the 6 drug-level fields replaced by a
    thin DRUG_REF pointer. Every other field is untouched (deep-copied)."""
    out = copy.deepcopy(trial)
    drug = out["molecule"]["drug"]["value"]
    app_num = application_number_of(trial)
    out["schema_version"] = 4
    for field, (group, key) in SINGLE_VALUED_FIELDS.items():
        out[group][key] = drug_ref_sv(drug)
    for field, (group, key) in APPLICATION_KEYED_FIELDS.items():
        out[group][key] = drug_ref_sv(drug, app_num)
    return out


def resolve_trial_record(trial: dict, drug_records: dict) -> dict:
    """v4 trial record -> the full v3-shaped dict (same content as before
    the split), by resolving each DRUG_REF pointer against the drug-level
    record it names. Used by build_csv.py and anything else that wants a
    trial's own complete facts without caring whether they live on the trial
    or the drug record -- the whole point of "reference, don't copy" is that
    this function is the only place that has to know the difference."""
    out = copy.deepcopy(trial)
    drug_name = out["molecule"]["drug"]["value"]
    drec = drug_records[drug_name]

    for field, (group, key) in SINGLE_VALUED_FIELDS.items():
        assert out[group][key]["source_type"] == "drug_level_ref", (drug_name, group, key)
        out[group][key] = copy.deepcopy(drec[field])

    app_num = out["exclusivity"]["regulatory_application"]["value"].get("application_number")
    app_entry = next((a for a in drec["applications"] if a["application_number"] == app_num), None)
    if app_entry is None:
        # Defensive fallback only -- every trial's own application_number was
        # derived FROM this same drug's applications list at split time, so
        # this should never actually miss; falls back to the drug's first
        # (often only) application rather than raising, since a resolve
        # consumer (build_csv.py) should degrade, not crash, on a real corpus.
        app_entry = drec["applications"][0]
    out["exclusivity"]["regulatory_application"] = copy.deepcopy(app_entry["regulatory_application"])
    out["exclusivity"]["orange_book"] = copy.deepcopy(app_entry["orange_book"])
    return out


def load_all_drug_records(drugs_dir: Path = DRUGS_DIR) -> dict:
    records = (json.loads(p.read_text()) for p in sorted(drugs_dir.glob("*.json")))
    return {r["drug"]: r for r in records}


def ensure_drug_record(drug_name: str, fetch_fields, for_trial: str | None = None,
                        drugs_dir: Path = DRUGS_DIR) -> dict:
    """The actual "search by drug" pipeline entrypoint: return the drug's
    already-committed record if one exists (no re-fetch, no re-extraction --
    this is the fix), otherwise call `fetch_fields(drug_name)` ONCE to build
    a fresh one and commit it.

    `fetch_fields(drug_name)` must return a dict shaped like build_drug_records'
    per-drug output MINUS `trial_ids` (this function adds `for_trial` itself --
    see below), i.e. {"mechanism_of_action": <SV>, "boxed_warning": <SV>,
    "faers_summary": <SV>, "applications": [...], "purple_book": <SV>}. A
    future per-cycle add-a-trial script calls THIS once per new trial, never
    `fetch_fields` directly -- so a second (or 8th) trial of an already-known
    drug costs zero extra network calls and zero extra stored duplication.

    `for_trial` (the new trial's own NCT id, when the caller has one) is
    appended to `trial_ids` if not already present, and the record is
    re-saved -- so data/drugs/<slug>.json's own `trial_ids` list stays
    accurate as new trials of a known drug are added, even though its FACTS
    are never re-fetched."""
    existing = load_drug(drug_name, drugs_dir)
    if existing is not None:
        if for_trial and for_trial not in existing["trial_ids"]:
            existing["trial_ids"].append(for_trial)
            save_drug(existing, drugs_dir)
        return existing
    fresh = fetch_fields(drug_name)
    record = {
        "schema_version": DRUG_SCHEMA_VERSION,
        "drug": drug_name,
        "mechanism_of_action": fresh["mechanism_of_action"],
        "boxed_warning": fresh["boxed_warning"],
        "faers_summary": fresh["faers_summary"],
        "drug_characterization": fresh["drug_characterization"],
        "applications": fresh["applications"],
        "purple_book": fresh["purple_book"],
        "trial_ids": [for_trial] if for_trial else [],
    }
    save_drug(record, drugs_dir)
    return record
