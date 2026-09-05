#!/usr/bin/env python3
"""
Raw-data staging pass: FDA Purple Book (biologic BLA patent/exclusivity data).

The Purple Book lists FDA-licensed biological products (BLAs), their
reference-product exclusivity (including 12-year BPCIA reference-product
exclusivity and orphan exclusivity), and biosimilar/interchangeable status
-- a different shape and a different set of exclusivity rules than the
Orange Book's small-molecule NDA patents, so it gets its own parser here
rather than reusing scripts/fetch_orange_book.py's.

Where the data actually lives: purplebooksearch.fda.gov's downloads page
(https://purplebooksearch.fda.gov/downloads) only offers *monthly delta*
CSVs (each one a "Newly Approved (N) / Added in Current Release (R) /
Updated (U)" changes report for that single month -- confirmed by fetching
https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/2026/purplebook-search-August-data-download.csv,
whose first line literally reads "Purple Book Monthly Historical Data
Changes Report - August 2026"). Reconstructing one current snapshot from
those would mean replaying every monthly delta since the file series
started. Instead, the full current database is server-rendered directly
into the HTML of the live search page,
https://purplebooksearch.fda.gov/index.cfm?event=advancedsearch (a ~3.7MB
page containing every product row in one <table>, confirmed by grepping it
for "Dupilumab"/"Ebglyss"/"Adbry" and finding real matches) -- so this
script downloads and parses that page's table instead of a CSV.

For the 10 biologics in this atlas, matches every product row whose
Proprietary Name or Proper Name contains the drug/brand name (originator
AND every biosimilar/interchangeable sharing that INN -- e.g. adalimumab
alone has 10 biosimilar BLAs on file), then builds the schema v2
`exclusivity.purple_book` value directly (atlas/schema.py::PURPLE_BOOK):
the 351(a) reference-product row is the primary record, every 351(k) row
sharing its INN becomes one entry in its `biosimilars` list -- picking
`rows[0]` blindly (an earlier version of this script's ad-hoc inspection
did) would have surfaced e.g. "Abrilada" (a Pfizer adalimumab biosimilar)
as if it were Humira; confirmed by listing every matched adalimumab row's
License Type and cross-checking against the real Humira BLA (125057).

This script's column names come from purplebooksearch.fda.gov's live
search-results table specifically, NOT its monthly CSV download -- the two
use different header spellings for the same concepts (this table:
"First Inter. Excl. Exp. Date", "Ref. Product Excl. Exp. Date"; the CSV:
the fully-spelled-out versions) and the live table spells out month names
in dates ("March 28, 2017") where the CSV abbreviates them ("28-Mar-17") --
confirmed on real rows for Humira/Cosentyx. `atlas.scalars.parse_us_date`
was extended to accept both forms rather than writing a second date parser.

Run:
    python3 scripts/fetch_purple_book.py
"""
import json
import re
import sys
import time
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from atlas.scalars import parse_us_date  # noqa: E402

CACHE_DIR = ROOT / "data" / "_raw_cache" / "purple_book"  # gitignored working cache
STAGING_DIR = ROOT / "data" / "_raw_staging" / "purple_book"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
STAGING_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_URL = "https://purplebooksearch.fda.gov/index.cfm?event=advancedsearch"
EXTRACTED_BY = "fetch_purple_book.py (purplebooksearch.fda.gov live search table, raw staging pass)"

# drug -> (INN/proper name fragment, brand/proprietary name) used to match rows
DRUGS = {
    # Atopic Dermatitis
    "Dupilumab": ("dupilumab", "Dupixent"),
    "Lebrikizumab": ("lebrikizumab", "Ebglyss"),
    "Tralokinumab": ("tralokinumab", "Adbry"),
    # Plaque Psoriasis
    "Guselkumab": ("guselkumab", "Tremfya"),
    "Risankizumab": ("risankizumab", "Skyrizi"),
    "Tildrakizumab": ("tildrakizumab", "Ilumya"),
    "Bimekizumab": ("bimekizumab", "Bimzelx"),
    # Hidradenitis Suppurativa (Bimekizumab already listed above)
    "Adalimumab": ("adalimumab", "Humira"),
    "Secukinumab": ("secukinumab", "Cosentyx"),
    # Chronic Spontaneous Urticaria (Dupilumab already listed above)
    "Omalizumab": ("omalizumab", "Xolair"),
    # Prurigo Nodularis / Atopic Dermatitis, added 2026-09-05
    "Nemolizumab": ("nemolizumab", "Nemluvio"),
    # Plaque Psoriasis, added 2026-09-05
    "Ixekizumab": ("ixekizumab", "Taltz"),
    # Certolizumab pegol (Cimzia) is a PEGylated Fab' antibody fragment,
    # approved via BLA 125160 -- a biologic, not a small-molecule NDA,
    # despite "pegol" suggesting a chemical modification; Purple Book is
    # correct here, not Orange Book.
    "Certolizumab": ("certolizumab pegol", "Cimzia"),
}


def fetch_search_page() -> str:
    cache = CACHE_DIR / "advancedsearch.html"
    if cache.exists():
        return cache.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(
        SEARCH_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; derm-trial-atlas-data/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    cache.write_text(html, encoding="utf-8")
    return html


def strip_tags(cell_html: str) -> str:
    text = re.sub(r"<[^>]+>", "", cell_html)
    return unescape(text).strip()


def parse_table(html: str) -> list[dict]:
    thead_match = re.search(r"<thead.*?</thead>", html, re.S | re.I)
    tbody_match = re.search(r"<tbody.*?</tbody>", html, re.S | re.I)
    if not thead_match or not tbody_match:
        raise RuntimeError("Purple Book search page: could not find table thead/tbody")

    headers = [strip_tags(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", thead_match.group(0), re.S)]

    rows = []
    for row_html in re.findall(r"<tr>(.*?)</tr>", tbody_match.group(0), re.S):
        cells = [strip_tags(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)]
        if not cells:
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def matches_drug(row: dict, proper_fragment: str, brand: str) -> bool:
    proper = row.get("Proper Name", "").lower()
    proprietary = row.get("Proprietary Name", "").lower()
    return proper_fragment.lower() in proper or brand.lower() == proprietary


def _blank(v):
    v = (v or "").strip()
    return None if v in ("", "-") else v


def build_purple_book_value(matched: list) -> dict:
    """matched: every row (reference product + every biosimilar sharing its
    INN) already filtered to one drug by matches_drug(). Splits reference
    (351(a)) from biosimilars (351(k)) and builds the schema PURPLE_BOOK shape."""
    reference_rows = [r for r in matched if r.get("License Type", "").startswith("351(a)")]
    if not reference_rows:
        raise ValueError("no 351(a) reference-product row among matched rows -- only biosimilars found")
    bla_number = reference_rows[0]["BLA Number"]
    ref_rows = [r for r in reference_rows if r["BLA Number"] == bla_number]
    first = ref_rows[0]

    products = []
    for r in sorted(ref_rows, key=lambda x: x.get("Product Number", "")):
        products.append({
            "product_number": _blank(r.get("Product Number")),
            "strength": _blank(r.get("Strength")),
            "dosage_form": _blank(r.get("Dosage Form")),
            "route": _blank(r.get("Route of Administration")),
            "presentation": _blank(r.get("Product Presentation")),
            "marketing_status": _blank(r.get("Marketing Status")),
            "licensure": _blank(r.get("Licensure")),
            "approval_date": parse_us_date(_blank(r.get("Approval Date"))),
            "submission_type": _blank(r.get("Submission Type")),
            "supplement_number": _blank(r.get("Supplement Number")),
        })
    dates = [p["approval_date"] for p in products if p["approval_date"]]

    def first_nonblank(col):
        for r in ref_rows:
            v = _blank(r.get(col))
            if v:
                return v
        return None

    biosimilars = []
    for r in matched:
        if r.get("License Type", "").startswith("351(k)"):
            key = r["BLA Number"]
            if not any(b["bla_number"] == key for b in biosimilars):
                biosimilars.append({
                    "proper_name": r["Proper Name"],
                    "proprietary_name": _blank(r.get("Proprietary Name")),
                    "bla_number": key,
                    "applicant": _blank(r.get("Applicant")),
                    "approval_date": parse_us_date(_blank(r.get("Approval Date"))),
                    "license_type": "351(k)",
                    "interchangeable_approval_date": parse_us_date(_blank(r.get("Inter. Approval Date"))),
                })

    patent_flag = first_nonblank("Patent List Provided")
    return {
        "bla_number": bla_number,
        "proprietary_name": _blank(first.get("Proprietary Name")),
        "proper_name": first["Proper Name"],
        "applicant": _blank(first.get("Applicant")),
        "license_type": "351(a)",
        "license_number": _blank(first.get("License Number")),
        "center": _blank(first.get("Center")),
        "products": products,
        "first_approval_date": min(dates) if dates else None,
        "date_of_first_licensure": parse_us_date(first_nonblank("Date of First Licensure")),
        "reference_product_exclusivity_expiration": parse_us_date(first_nonblank("Ref. Product Excl. Exp. Date")),
        "exclusivity_expiration_date": parse_us_date(first_nonblank("Exclusivity Expiration Date")),
        "first_interchangeable_exclusivity_expiration": parse_us_date(first_nonblank("First Inter. Excl. Exp. Date")),
        "orphan_exclusivity_expiration": parse_us_date(first_nonblank("Orphan Exclusivity Expiration Date")),
        "patent_list_provided": patent_flag.upper().startswith("Y") if patent_flag else None,
        "biosimilars": sorted(biosimilars, key=lambda b: b["bla_number"]),
        "data_file_month": None,  # the live search table doesn't expose a release-month field
    }


def main():
    html = fetch_search_page()
    all_rows = parse_table(html)
    print(f"Parsed {len(all_rows)} total rows from the Purple Book search table")

    staged = 0
    for drug, (proper_fragment, brand) in DRUGS.items():
        print(f"Purple Book: {drug} ({brand})...")
        matched = [r for r in all_rows if matches_drug(r, proper_fragment, brand)]
        fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if not matched:
            record = {
                "value": None, "source_type": "needs_extraction",
                "source_url": SEARCH_URL,
                "source_excerpt": f"no rows matched proper/proprietary name for {drug} ({brand})",
                "extracted_by": EXTRACTED_BY, "reviewed_by": None, "confidence": None,
            }
            print(f"  no rows matched for {drug} (real finding, not an error)")
        else:
            try:
                value = build_purple_book_value(matched)
            except ValueError as e:
                record = {
                    "value": None, "source_type": "needs_extraction",
                    "source_url": SEARCH_URL,
                    "source_excerpt": f"{drug}: {e}",
                    "extracted_by": EXTRACTED_BY, "reviewed_by": None, "confidence": None,
                }
                print(f"  FAILED to build record: {e}")
            else:
                record = {
                    "value": value,
                    "source_type": "purple_book",
                    "source_url": SEARCH_URL,
                    "source_excerpt": (
                        f"purplebooksearch.fda.gov live search table, BLA {value['bla_number']} "
                        f"({value['proprietary_name']}), {len(value['biosimilars'])} biosimilar(s) on file"
                    ),
                    "extracted_by": EXTRACTED_BY,
                    "fetched_at": fetched_at,
                }
                print(f"  BLA {value['bla_number']} ({value['proprietary_name']}): "
                      f"{len(value['products'])} product(s), {len(value['biosimilars'])} biosimilar(s)")

        out_path = STAGING_DIR / f"{drug.lower()}.json"
        out_path.write_text(json.dumps(record, indent=2) + "\n")
        staged += 1

    print(f"Staged {staged} Purple Book files to {STAGING_DIR}")


if __name__ == "__main__":
    main()
