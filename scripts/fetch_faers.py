#!/usr/bin/env python3
"""
Raw-data staging pass: openFDA FAERS (real-world post-market adverse events).

For each of the 5 atlas drugs, hits openFDA's public FAERS endpoint
(drug/event.json -- free, no API key, same api.fda.gov family as
drug/label.json used in fetch_adverse_events.py) with two queries:

  1. Total report count -- ?search=patient.drug.medicinalproduct:"<DRUG>"
     &limit=1, reading meta.results.total. This is the number of FAERS
     reports that name the drug anywhere in patient.drug[].medicinalproduct,
     which is the correct "how many real-world reports mention this drug"
     figure. (A tempting shortcut is to instead read the top entry's count
     from the count-by-medicinalproduct.exact query below, but that
     undercounts: FAERS reporters spell/format a drug's name inconsistently
     -- brand name, INN, with or without the suffix, "BRAND (INN)" combined
     forms, etc. -- so the .exact term groupby splits one drug's reports
     across several distinct term strings. meta.results.total from a plain
     search is the one number that reflects the full search-matched set.)
  2. Top reported reaction terms -- ?search=patient.drug.medicinalproduct:"<DRUG>"
     &count=patient.reaction.reactionmeddrapt.exact, top 15 by count. This
     endpoint counts every reaction term co-occurring in the matched reports
     (each report can list several reactions), ranked by frequency -- it is
     openFDA's own aggregation, not a client-side re-derivation.

This is a RAW STAGING pass, not final schema integration: output goes to
data/_raw_staging/faers/<drug>.json, not data/trials/. The final trial-JSON
field names/shape for FAERS data are being redesigned in a sibling task;
this script's only job is to prove the fetch works and stage the real
numbers, so each staged file keeps the fields as openFDA returns them
(term, count) rather than wrapping them in the data/trials/ sourced-value
object shape.

A drug can genuinely have few real-world reports (a recently approved drug
has had less market exposure to generate them) -- that is recorded as-is,
not treated as an error. Of the 5 drugs here, all had FAERS reports as of
this run; the script still handles a genuine zero/not-found result
(openFDA returns HTTP 404 with an error body when a search matches
nothing) so a future drug with no FAERS history yet degrades honestly
instead of crashing.

Run:
    python3 scripts/fetch_faers.py
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING_DIR = ROOT / "data" / "_raw_staging" / "faers"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

OPENFDA_EVENT = "https://api.fda.gov/drug/event.json"
EXTRACTED_BY = "fetch_faers.py (openfda drug/event.json, raw staging pass)"

DRUGS = [
    # Atopic Dermatitis
    "Dupilumab",
    "Lebrikizumab",
    "Tralokinumab",
    "Abrocitinib",
    "Upadacitinib",
    # Plaque Psoriasis
    "Guselkumab",
    "Risankizumab",
    "Tildrakizumab",
    "Bimekizumab",
    "Deucravacitinib",
    # Hidradenitis Suppurativa (Adalimumab, Secukinumab; Bimekizumab already listed above)
    "Adalimumab",
    "Secukinumab",
    # Alopecia Areata
    "Baricitinib",
    "Ritlecitinib",
    "Deuruxolitinib",
    # Chronic Spontaneous Urticaria (Dupilumab already listed above)
    "Omalizumab",
]


def _get_json(url: str) -> dict | None:
    """GET a url and return parsed JSON, or None for openFDA's genuine
    "no matches" response (HTTP 404 with an error body) -- that is a real
    negative finding, not a failure. Any other HTTP error propagates."""
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            body = json.loads(e.read().decode())
            if body.get("error", {}).get("code") == "NOT_FOUND":
                return None
        raise


def fetch_total_report_count(drug: str) -> tuple[int | None, str]:
    search = urllib.parse.quote(f'patient.drug.medicinalproduct:"{drug.upper()}"')
    url = f"{OPENFDA_EVENT}?search={search}&limit=1"
    data = _get_json(url)
    if data is None:
        return None, url
    return data["meta"]["results"]["total"], url


def fetch_top_reactions(drug: str, top_n: int = 15) -> tuple[list, str]:
    search = urllib.parse.quote(f'patient.drug.medicinalproduct:"{drug.upper()}"')
    url = f"{OPENFDA_EVENT}?search={search}&count=patient.reaction.reactionmeddrapt.exact&limit={top_n}"
    data = _get_json(url)
    if data is None:
        return [], url
    return [
        {"term": r["term"], "count": r["count"]} for r in data.get("results", [])
    ], url


def main():
    for drug in DRUGS:
        print(f"FAERS: {drug}...")
        total, count_url = fetch_total_report_count(drug)
        time.sleep(0.3)  # openFDA rate limit is generous but be polite
        reactions, reactions_url = fetch_top_reactions(drug)

        record = {
            "drug": drug,
            "total_report_count": total,
            "top_reactions": reactions,
            "query_urls": {
                "total_report_count": count_url,
                "top_reactions": reactions_url,
            },
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": "openFDA drug/event.json (FAERS)",
            "extracted_by": EXTRACTED_BY,
        }

        if total is None:
            print(f"  no FAERS reports found for {drug} (real finding, not an error)")
        else:
            print(f"  total_report_count={total}, top_reactions={len(reactions)}")

        out_path = STAGING_DIR / f"{drug.lower()}.json"
        out_path.write_text(json.dumps(record, indent=2) + "\n")

    print(f"Staged {len(DRUGS)} FAERS files to {STAGING_DIR}")


if __name__ == "__main__":
    main()
