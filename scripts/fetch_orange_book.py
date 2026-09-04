#!/usr/bin/env python3
"""
FDA Orange Book (small-molecule NDA patent/exclusivity data) via openFDA's
`drug/orangebook.json` endpoint -- a real, script-friendly mirror of the
Orange Book dataset (confirmed live, 48664+ total records) that sits on
`api.fda.gov`, not on `fda.gov`/`accessdata.fda.gov` -- and is NOT behind
the Akamai bot-detection that blocks both of those directly (see git log
for the prior version of this script, which documents that block in
detail; it was real and reproducible, this endpoint is a different host
entirely).

Output is staged directly in the schema v2 `exclusivity.orange_book` value
shape (atlas/schema.py::ORANGE_BOOK on the fm/derm-trial-atlas-schema-
ontology branch) so a later integration pass is a straight copy into the
sourced-value envelope, not a second transformation.

openFDA quirk worth documenting: each "result" is one PRODUCT row (one
per strength/dosage form under the application), each carrying the FULL
patents[]/exclusivity[] list for its application (i.e. the same set
repeated on every product row of that application) -- there is no
separate per-product patent/exclusivity join in this API shape the way
there is in the raw products.txt/patent.txt/exclusivity.txt files. This
script dedupes the repeated patent/exclusivity rows down to one entry per
(patent_number, patent_use_code) / (exclusivity_code, expiration_date),
collecting every product_number they were seen attached to -- reproducing
the same shape the raw tilde-files would give, from a different real API.

Run:
    python3 scripts/fetch_orange_book.py
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING_DIR = ROOT / "data" / "_raw_staging" / "orange_book"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

OPENFDA_ORANGEBOOK = "https://api.fda.gov/drug/orangebook.json"
EXTRACTED_BY = "fetch_orange_book.py (openfda drug/orangebook.json, v2 pass)"

DRUGS = {
    # Atopic Dermatitis (small-molecule NDAs)
    "Abrocitinib": "ABROCITINIB",
    "Upadacitinib": "UPADACITINIB",
    # Alopecia Areata (oral JAK inhibitors, small-molecule NDAs)
    "Baricitinib": "BARICITINIB",
    "Ritlecitinib": "RITLECITINIB",
    "Deuruxolitinib": "DEURUXOLITINIB",
    # Plaque Psoriasis (oral TYK2 inhibitor, small-molecule NDA)
    "Deucravacitinib": "DEUCRAVACITINIB",
    # Vitiligo (topical JAK inhibitor, small-molecule NDA). Ruxolitinib the
    # ingredient also covers Jakafi/Jakafi XR (oral tablets, NDA 202192 /
    # 217180, oncology/GVHD) -- an unfiltered ingredient search returns all
    # three applications merged, misattributing Opzelura's (the actual
    # vitiligo drug's) patent/exclusivity data with Jakafi's. The tuple form
    # pins the query to application_number 215309 (Opzelura cream) only --
    # confirmed live 2026-09-05: 215309=OPZELURA/CREAM/TOPICAL,
    # 202192=JAKAFI/TABLET/ORAL, 217180=JAKAFI XR/TABLET,EXTENDED RELEASE/ORAL.
    "Ruxolitinib": ("RUXOLITINIB", "215309"),
}


def _get_json(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # openFDA's genuine "no matches" response
        raise


def _iso_date(yyyymmdd):
    if not yyyymmdd or len(yyyymmdd) != 8:
        return None
    return f"{yyyymmdd[0:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def build_record(ingredient: str, results: list) -> dict:
    products = []
    seen_products = set()
    patents = {}
    exclusivities = {}
    for r in results:
        p = r["products"][0]
        pn = r.get("product_number") or p.get("product_number")
        if pn not in seen_products:
            seen_products.add(pn)
            products.append({
                "product_number": pn,
                "strength": p["active_ingredients"][0].get("strength"),
                "dosage_form": p.get("dosage_form"),
                "route": p.get("route"),
                "approval_date": _iso_date(r.get("approval_date")),
                "rld": bool(p.get("reference_listed_drug")),
                "rs": bool(p.get("reference_standard")),
                "te_code": p.get("te_code"),
                "marketing_type": p.get("marketing_status"),
            })
        for pat in r.get("patents", []):
            key = (pat.get("patent_number"), pat.get("patent_use_code"))
            entry = patents.setdefault(key, {
                "patent_number": pat.get("patent_number"),
                "expiration_date": _iso_date(pat.get("expiration_date")),
                "drug_substance_claim": bool(pat.get("drug_substance_flag")),
                "drug_product_claim": bool(pat.get("drug_product_flag")),
                "patent_use_code": pat.get("patent_use_code"),
                "delisted": bool(pat.get("delisted_flag", False)),
                "submission_date": _iso_date(pat.get("patent_submission_date")),
                "product_numbers": [],
            })
            if pn not in entry["product_numbers"]:
                entry["product_numbers"].append(pn)
        for exc in r.get("exclusivity", []):
            key = (exc.get("exclusivity_code"), exc.get("exclusivity_expiration_date"))
            entry = exclusivities.setdefault(key, {
                "code": exc.get("exclusivity_code"),
                "expiration_date": _iso_date(exc.get("exclusivity_expiration_date")),
                "product_numbers": [],
            })
            if pn not in entry["product_numbers"]:
                entry["product_numbers"].append(pn)

    first_product = results[0]["products"][0]
    out_patents = sorted(patents.values(), key=lambda p: (p["expiration_date"] or "", p["patent_number"]))
    out_excl = sorted(exclusivities.values(), key=lambda e: (e["expiration_date"] or "", e["code"]))
    return {
        "application_type": first_product.get("application_type"),
        "application_number": first_product.get("application_number"),
        "ingredient": ingredient,
        "trade_name": first_product.get("brand_name"),
        "applicant": first_product.get("application_name"),
        "applicant_full_name": first_product.get("application_full_name"),
        "products": sorted(products, key=lambda p: p["product_number"] or ""),
        "patents": out_patents,
        "exclusivities": out_excl,
        "latest_patent_expiration": max((p["expiration_date"] for p in out_patents if p["expiration_date"]), default=None),
        "latest_exclusivity_expiration": max((e["expiration_date"] for e in out_excl if e["expiration_date"]), default=None),
        "data_file_date": None,  # openFDA's orangebook.json doesn't expose the source file's release month
    }


def main():
    staged = 0
    for drug, spec in DRUGS.items():
        ingredient, app_filter = spec if isinstance(spec, tuple) else (spec, None)
        print(f"Orange Book (openFDA): {drug}...")
        q = urllib.parse.quote(f'products.active_ingredients.name:"{ingredient}"')
        url = f"{OPENFDA_ORANGEBOOK}?search={q}&limit=100"
        data = _get_json(url)
        if data and app_filter:
            data = dict(data)
            data["results"] = [
                r for r in data["results"]
                if r["products"][0].get("application_number") == app_filter
            ]
        if not data or not data.get("results"):
            print(f"  NOT FOUND for {ingredient} -- staging genuine unreachable finding")
            record = {
                "status": "source_unreachable",
                "ingredient_matched": ingredient,
                "attempted_sources": [{
                    "url": url, "method": "GET",
                    "result": "openFDA drug/orangebook.json returned no matches for this ingredient name.",
                }],
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "extracted_by": EXTRACTED_BY,
            }
        else:
            value = build_record(ingredient, data["results"])
            record = {
                "value": value,
                "source_type": "orange_book",
                "source_url": url,
                "source_excerpt": (
                    f"openFDA drug/orangebook.json, {len(data['results'])} product row(s) "
                    f"matched on products.active_ingredients.name={ingredient!r}"
                ),
                "extracted_by": EXTRACTED_BY,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            print(f"  application {value['application_type']}{value['application_number']} "
                  f"({value['trade_name']}): {len(value['products'])} product(s), "
                  f"{len(value['patents'])} patent(s), {len(value['exclusivities'])} exclusivit(y/ies)")
        (STAGING_DIR / f"{drug.lower()}.json").write_text(json.dumps(record, indent=2) + "\n")
        staged += 1
    print(f"Staged {staged} Orange Book files to {STAGING_DIR}")


if __name__ == "__main__":
    main()
