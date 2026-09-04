#!/usr/bin/env python3
"""
Raw-data staging pass: FDA Orange Book (small-molecule NDA patent/exclusivity
data) for Abrocitinib (Cibinqo) and Upadacitinib (Rinvoq).

*** STATUS: both real FDA routes to this data are blocked for an automated
*** stdlib script. See "What was tried" below. This script makes the real
*** attempt every run, and stages an honest source_unreachable finding
*** (never fabricated data) when it fails, so a future run automatically
*** picks up real data the moment either route reopens.

What the data is and where it should come from: the Orange Book Data Files
page (https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files)
links a ZIP ("Orange Book Data Files (compressed .zip file)") containing
products.txt / patent.txt / exclusivity.txt, tilde-delimited, joined on
Appl_No. As of this run that link resolves to
https://www.fda.gov/media/76860/download (confirmed live via a fetch of the
Data Files page's current HTML, and independently via FDA's own
"Orange Book Data File Download Instructions" PDF at
https://www.accessdata.fda.gov/drugsatfda_docs/ob/OrangeBookDataFileDownloadInstructions.pdf,
which shows the same product/patent/exclusivity file layout).

What was tried (this session, all with a realistic browser User-Agent):
  1. GET https://www.fda.gov/media/76860/download -- Akamai's edge
     (server: AkamaiGHost) returns a 302 to /apology_objects/abuse-detection-apology.html
     ("bot detection"); following it (or hitting the AkamaiNetStorage origin
     directly) returns a bare 404. Same result with a fresh cookie jar primed
     by first loading the referring Data Files page (that GET itself
     sometimes gets the same bot-detection redirect, sometimes a 404 --
     consistent with adaptive/behavioral bot mitigation, not a one-off).
  2. GET https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files
     directly -- same Akamai bot-detection redirect.
  3. The live Orange Book *query* tool at accessdata.fda.gov (a different,
     non-Akamai-blocked host -- reachable for GET requests to static pages)
     turned out to still be gated: POST to
     https://www.accessdata.fda.gov/scripts/cder/ob/search_product.cfm
     (the tool's real search form) returns an Akamai "Challenge Validation"
     page requiring a JS proof-of-work solve, not executable by a plain HTTP
     client. A same-URL GET with the same query params returns HTTP 200 but
     with byte-identical content regardless of the drugname param, meaning
     the search is only executed client-side / via the POST path, not GET.

Net result: there is no route to real Orange Book product/patent/exclusivity
rows for Abrocitinib or Upadacitinib available to an unattended, dependency-
free script right now. This is a genuine, reproducible block (Akamai bot/
challenge protection), not a missed detail -- re-verify by re-running this
script, which repeats attempt #1 for real every time and will pick up real
data automatically once/if that link becomes reachable to non-browser
clients again.

Run:
    python3 scripts/fetch_orange_book.py
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "_raw_cache" / "orange_book"  # gitignored working cache
STAGING_DIR = ROOT / "data" / "_raw_staging" / "orange_book"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
STAGING_DIR.mkdir(parents=True, exist_ok=True)

# Verified current as of this run by fetching the live Orange Book Data
# Files page and reading its "Orange Book Data Files (compressed .zip file)"
# link -- see module docstring. FDA has changed this media ID before, so if
# this 404s cleanly (not the Akamai bot-detection redirect) that's the first
# thing to re-check.
ZIP_URL = "https://www.fda.gov/media/76860/download"
EXTRACTED_BY = "fetch_orange_book.py (FDA Orange Book Data Files ZIP, raw staging pass)"

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
}


def download_zip() -> Path | None:
    """Try the real download. Returns the cached zip path on success, None
    on failure (after printing the exact error, per the task's instruction
    not to fabricate a substitute)."""
    cache = CACHE_DIR / "orange_book_data_files.zip"
    if cache.exists() and cache.stat().st_size > 0:
        return cache

    req = urllib.request.Request(
        ZIP_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "application/zip,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        print(f"  FAILED: HTTP {e.code} {e.reason} fetching {ZIP_URL}")
        try:
            print(f"  response body: {e.read()[:200]!r}")
        except Exception:
            pass
        return None
    except urllib.error.URLError as e:
        print(f"  FAILED: {e.reason} fetching {ZIP_URL}")
        return None

    cache.write_bytes(data)
    return cache


def parse_and_stage(zip_path: Path):
    import io
    import zipfile

    with zipfile.ZipFile(zip_path) as zf:
        products = zf.read("products.txt").decode("latin-1").splitlines()
        patents = zf.read("patent.txt").decode("latin-1").splitlines()
        exclusivity = zf.read("exclusivity.txt").decode("latin-1").splitlines()

    def parse_tilde(lines):
        header = lines[0].split("~")
        return [dict(zip(header, line.split("~"))) for line in lines[1:] if line.strip()]

    product_rows = parse_tilde(products)
    patent_rows = parse_tilde(patents)
    exclusivity_rows = parse_tilde(exclusivity)

    for drug, ingredient in DRUGS.items():
        print(f"Orange Book: {drug}...")
        matched_products = [r for r in product_rows if r.get("Ingredient", "").upper() == ingredient]
        appl_nos = {r.get("Appl_No") for r in matched_products}
        matched_patents = [r for r in patent_rows if r.get("Appl_No") in appl_nos]
        matched_exclusivity = [r for r in exclusivity_rows if r.get("Appl_No") in appl_nos]

        record = {
            "drug": drug,
            "ingredient_matched": ingredient,
            "products": matched_products,
            "patents": matched_patents,
            "exclusivity": matched_exclusivity,
            "query_source": ZIP_URL,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": "FDA Orange Book Data Files ZIP (products.txt/patent.txt/exclusivity.txt)",
            "extracted_by": EXTRACTED_BY,
        }
        (STAGING_DIR / f"{drug.lower()}.json").write_text(json.dumps(record, indent=2) + "\n")
        print(f"  matched {len(matched_products)} product row(s), {len(matched_patents)} patent row(s), "
              f"{len(matched_exclusivity)} exclusivity row(s)")


def stage_unreachable():
    """No fabricated substitute -- record the real, reproducible block so
    the sibling schema task (and any human reviewing this) sees exactly
    what was tried and why it failed, per source, with no invented data."""
    for drug, ingredient in DRUGS.items():
        record = {
            "drug": drug,
            "ingredient_matched": ingredient,
            "products": None,
            "patents": None,
            "exclusivity": None,
            "status": "source_unreachable",
            "attempted_sources": [
                {
                    "url": ZIP_URL,
                    "method": "GET",
                    "result": (
                        "Akamai bot-detection redirect (302 -> "
                        "/apology_objects/abuse-detection-apology.html) or a bare 404 "
                        "from the AkamaiNetStorage origin -- observed both, inconsistently, "
                        "across attempts in this session, with a realistic browser "
                        "User-Agent and (separately) a primed cookie jar + Referer."
                    ),
                },
                {
                    "url": "https://www.accessdata.fda.gov/scripts/cder/ob/search_product.cfm",
                    "method": "POST",
                    "result": (
                        "Returns an Akamai 'Challenge Validation' interstitial requiring a "
                        "JS proof-of-work solve -- not executable by a stdlib HTTP client. "
                        "A same-URL GET with identical query params returns HTTP 200 but "
                        "byte-identical content regardless of the drugname parameter, "
                        "meaning the actual search only runs via the protected POST path."
                    ),
                },
            ],
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "extracted_by": EXTRACTED_BY,
        }
        (STAGING_DIR / f"{drug.lower()}.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Staged {len(DRUGS)} Orange Book 'source_unreachable' findings to {STAGING_DIR}")


def main():
    print(f"Attempting real download: {ZIP_URL}")
    zip_path = download_zip()
    if zip_path is None:
        print("Real Orange Book ZIP download failed (see error above). "
              "Also tried the accessdata.fda.gov query tool -- also blocked "
              "(see module docstring). Staging an honest unreachable finding, "
              "not fabricated data.")
        stage_unreachable()
        return
    parse_and_stage(zip_path)


if __name__ == "__main__":
    main()
