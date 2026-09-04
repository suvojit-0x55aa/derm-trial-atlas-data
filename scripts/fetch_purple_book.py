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

For the 3 biologic drugs in this atlas -- Dupilumab (Dupixent), Lebrikizumab
(Ebglyss), Tralokinumab (Adbry) -- matches every product row whose
Proprietary Name or Proper Name contains the drug/brand name, and stages the
full row (BLA number, exclusivity expiration dates, biosimilar-interchangeable
status columns, etc. -- whatever real columns the table has) rather than
picking out fields in advance, since the final trial-JSON schema for this
data is being redesigned in a sibling task.

Run:
    python3 scripts/fetch_purple_book.py
"""
import json
import re
import time
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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


def main():
    html = fetch_search_page()
    all_rows = parse_table(html)
    print(f"Parsed {len(all_rows)} total rows from the Purple Book search table")

    for drug, (proper_fragment, brand) in DRUGS.items():
        print(f"Purple Book: {drug} ({brand})...")
        matched = [r for r in all_rows if matches_drug(r, proper_fragment, brand)]

        record = {
            "drug": drug,
            "brand_name": brand,
            "matched_row_count": len(matched),
            "rows": matched,
            "query_url": SEARCH_URL,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": "purplebooksearch.fda.gov live search table (full current database, server-rendered)",
            "extracted_by": EXTRACTED_BY,
        }

        if not matched:
            print(f"  no rows matched for {drug} (real finding, not an error)")
        else:
            print(f"  matched {len(matched)} row(s)")

        out_path = STAGING_DIR / f"{drug.lower()}.json"
        out_path.write_text(json.dumps(record, indent=2) + "\n")

    print(f"Staged {len(DRUGS)} Purple Book files to {STAGING_DIR}")


if __name__ == "__main__":
    main()
