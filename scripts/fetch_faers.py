#!/usr/bin/env python3
"""
openFDA FAERS (real-world post-market adverse-event reports) staging pass.

For each atlas drug, hits openFDA's public FAERS endpoint (drug/event.json
-- free, no API key, same api.fda.gov family as drug/label.json used in
fetch_adverse_events.py) with 9 queries and writes one already-schema-v2-
shaped sourced value to data/_raw_staging/faers/<drug>.json (consumed
as-is by scripts/apply_source_data.py -- see that script's docstring):

  1. Total report count -- ?search=patient.drug.medicinalproduct:"<DRUG>"
     &limit=1, reading meta.results.total.
  2-6. The same query AND-ed with serious:1, seriousnessdeath:1,
     seriousnesshospitalization:1, seriousnesslifethreatening:1,
     seriousnessdisabling:1 -- each read the same way, giving
     serious/death/hospitalization/life_threatening/disability counts.
  7. Top reported reaction terms, unfiltered -- count=patient.reaction.
     reactionmeddrapt.exact, top 15, pct_of_reports relative to total.
  8. Top reported reaction terms restricted to serious:1 reports -- same
     shape, pct_of_reports relative to serious_reports.
  9. count=receivedate (per-day counts openFDA returns for a date field
     with no interval modifier) -- aggregated client-side into
     reports_by_year.
  Plus two sort=receivedate:asc/desc, limit=1 queries for the earliest/
  latest report date (receivedate_from/receivedate_to).

IMPORTANT -- do not percent-encode `+`: openFDA's query syntax needs a
LITERAL `+` as its AND/space operator. urllib.parse.quote()'s default
behavior percent-encodes it, which makes openFDA treat it as a literal
plus-sign search character instead -- a filtered query like
`...+AND+serious:1` then silently matches *nothing* rather than erroring.
_quote_search keeps `+`, `:`, and `"` unescaped for exactly this reason;
see AGENTS.md for the full story (this file was accidentally reverted to
a pre-sharp-edge-fix version by an earlier rebase and is being restored
to the multi-query shape here).

A drug can genuinely have few/no real-world reports (recently approved,
less market exposure) -- that is recorded as-is via needs_extraction-style
None fields, not treated as an error. openFDA returns HTTP 404 with an
error body when a search matches nothing; that is a real negative
finding, handled explicitly rather than crashing.

Run:
    python3 scripts/fetch_faers.py
"""
import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING_DIR = ROOT / "data" / "_raw_staging" / "faers"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

OPENFDA_EVENT = "https://api.fda.gov/drug/event.json"
EXTRACTED_BY = "fetch_faers.py (openfda drug/event.json, v2 pass)"

SERIOUSNESS_FIELDS = {
    "serious_reports": "serious:1",
    "death_reports": "seriousnessdeath:1",
    "hospitalization_reports": "seriousnesshospitalization:1",
    "life_threatening_reports": "seriousnesslifethreatening:1",
    "disability_reports": "seriousnessdisabling:1",
}

DRUGS = [
    # Atopic Dermatitis
    "Dupilumab",
    "Lebrikizumab",
    "Tralokinumab",
    "Abrocitinib",
    "Upadacitinib",
    "Nemolizumab",
    # Plaque Psoriasis
    "Guselkumab",
    "Risankizumab",
    "Tildrakizumab",
    "Bimekizumab",
    "Deucravacitinib",
    "Ixekizumab",
    "Certolizumab",
    # Hidradenitis Suppurativa (Adalimumab, Secukinumab; Bimekizumab already listed above)
    "Adalimumab",
    "Secukinumab",
    # Alopecia Areata
    "Baricitinib",
    "Ritlecitinib",
    "Deuruxolitinib",
    # Chronic Spontaneous Urticaria (Dupilumab already listed above)
    "Omalizumab",
    # Prurigo Nodularis (Dupilumab, Nemolizumab already listed above)
    # Vitiligo
    "Ruxolitinib",
]


def _quote_search(search: str) -> str:
    """Percent-encode a search string EXCEPT `+`, `:`, and `"` -- openFDA
    needs those literal (see module docstring)."""
    safe = "+:\""
    out = []
    for ch in search:
        if ch.isalnum() or ch in safe or ch in "-_.~":
            out.append(ch)
        elif ch == " ":
            out.append("+")
        else:
            out.append(f"%{ord(ch):02X}")
    return "".join(out)


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


def _count_query(base_search: str, extra: str | None, count_field: str, top_n: int | None = None):
    search = base_search if not extra else f"{base_search}+AND+{extra}"
    url = f"{OPENFDA_EVENT}?search={_quote_search(search)}&count={count_field}"
    if top_n:
        url += f"&limit={top_n}"
    data = _get_json(url)
    if data is None:
        return [], url
    return data.get("results", []), url


def _total_query(base_search: str, extra: str | None):
    search = base_search if not extra else f"{base_search}+AND+{extra}"
    url = f"{OPENFDA_EVENT}?search={_quote_search(search)}&limit=1"
    data = _get_json(url)
    if data is None:
        return None, url
    return data["meta"]["results"]["total"], url


def _boundary_date(base_search: str, direction: str) -> tuple[str | None, str]:
    url = f"{OPENFDA_EVENT}?search={_quote_search(base_search)}&sort=receivedate:{direction}&limit=1"
    data = _get_json(url)
    if data is None or not data.get("results"):
        return None, url
    raw = data["results"][0]["receivedate"]
    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}", url


def _reaction_rows(results: list, denom: int | None) -> list:
    rows = []
    for r in results:
        count = r["count"]
        pct = round(100 * count / denom, 2) if denom else None
        rows.append({"meddra_pt": r["term"], "report_count": count, "pct_of_reports": pct})
    return rows


def fetch_drug(drug: str) -> dict:
    base_search = f'patient.drug.medicinalproduct:"{drug.upper()}"'
    api_urls = []

    total, url = _total_query(base_search, None)
    api_urls.append(url)
    if total is None:
        return {
            "query": {
                "search_field": "patient.drug.medicinalproduct", "search_term": drug.upper(),
                "receivedate_from": None, "receivedate_to": None, "api_urls": api_urls,
                "data_last_updated": None,
            },
            "total_reports": None, "serious_reports": None, "death_reports": None,
            "hospitalization_reports": None, "life_threatening_reports": None,
            "disability_reports": None, "top_reactions": [], "top_serious_reactions": [],
            "reports_by_year": [], "meddra_version": None,
        }

    seriousness_totals = {}
    for field, term in SERIOUSNESS_FIELDS.items():
        n, url = _total_query(base_search, term)
        api_urls.append(url)
        # We already know the drug has >=1 total report (checked above), so
        # a 404/"no matches" on this AND-filtered subset query genuinely
        # means zero reports carry that seriousness flag -- 0, not None
        # (None would wrongly claim "couldn't determine").
        seriousness_totals[field] = n if n is not None else 0
        time.sleep(0.2)

    reaction_results, url = _count_query(base_search, None, "patient.reaction.reactionmeddrapt.exact", top_n=15)
    api_urls.append(url)
    time.sleep(0.2)

    serious_reaction_results, url = _count_query(base_search, "serious:1", "patient.reaction.reactionmeddrapt.exact", top_n=15)
    api_urls.append(url)
    time.sleep(0.2)

    daily_results, url = _count_query(base_search, None, "receivedate")
    api_urls.append(url)
    yearly = defaultdict(int)
    for r in daily_results:
        yearly[int(r["time"][0:4])] += r["count"]
    reports_by_year = [{"year": y, "report_count": c} for y, c in sorted(yearly.items())]
    time.sleep(0.2)

    receivedate_from, _ = _boundary_date(base_search, "asc")
    time.sleep(0.2)
    receivedate_to, _ = _boundary_date(base_search, "desc")

    meta = _get_json(f"{OPENFDA_EVENT}?search={_quote_search(base_search)}&limit=1")
    data_last_updated = meta.get("meta", {}).get("last_updated") if meta else None

    return {
        "query": {
            "search_field": "patient.drug.medicinalproduct",
            "search_term": drug.upper(),
            "receivedate_from": receivedate_from,
            "receivedate_to": receivedate_to,
            "api_urls": api_urls,
            "data_last_updated": data_last_updated,
        },
        "total_reports": total,
        "serious_reports": seriousness_totals["serious_reports"],
        "death_reports": seriousness_totals["death_reports"],
        "hospitalization_reports": seriousness_totals["hospitalization_reports"],
        "life_threatening_reports": seriousness_totals["life_threatening_reports"],
        "disability_reports": seriousness_totals["disability_reports"],
        "top_reactions": _reaction_rows(reaction_results, total),
        "top_serious_reactions": _reaction_rows(serious_reaction_results, seriousness_totals["serious_reports"] or total),
        "reports_by_year": reports_by_year,
        "meddra_version": None,
    }


def main():
    for drug in DRUGS:
        print(f"FAERS: {drug}...")
        value = fetch_drug(drug)
        total = value["total_reports"]
        record = {
            "value": value,
            "source_type": "openfda_faers",
            "source_url": value["query"]["api_urls"][0],
            "source_excerpt": (
                f"openFDA drug/event.json aggregate: total_reports={total}, "
                f"serious={value['serious_reports']}, deaths={value['death_reports']}"
                if total is not None else
                f"openFDA drug/event.json: no FAERS reports found for {drug.upper()}"
            ),
            "extracted_by": EXTRACTED_BY,
            "reviewed_by": None,
            "confidence": 1.0 if total is not None else 0.0,
        }

        if total is None:
            print(f"  no FAERS reports found for {drug} (real finding, not an error)")
        else:
            print(f"  total_reports={total}, serious={value['serious_reports']}, "
                  f"deaths={value['death_reports']}, hospitalizations={value['hospitalization_reports']}")

        out_path = STAGING_DIR / f"{drug.lower()}.json"
        out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        time.sleep(0.3)  # be polite to the public API between drugs

    print(f"Staged {len(DRUGS)} FAERS files to {STAGING_DIR}")


if __name__ == "__main__":
    main()
