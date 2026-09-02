#!/usr/bin/env python3
"""
Download each trial's Study Protocol / SAP PDF (when CT.gov's
documentSection lists one) and convert it to plain text with
`pdftotext -layout`. This is the reproduction step behind the hardcoded
excerpts in scripts/enrich_needs_extraction.py's RESCUE_RULES,
MULTIPLICITY_RULES, and BACKGROUND_THERAPY_PDF dicts -- run it if you want
to re-verify an excerpt or pull a new one from the source PDF yourself.

Requires the `pdftotext` binary (poppler-utils / poppler on Homebrew).

Run:
    python3 scripts/fetch_protocol_docs.py
"""
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_DIR = ROOT / "data" / "trials"
CACHE_DIR = ROOT / "data" / "_raw_cache"
CACHE_DIR.mkdir(exist_ok=True)

CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"
CDN_BASE = "https://cdn.clinicaltrials.gov/large-docs"


def main():
    if not shutil.which("pdftotext"):
        raise SystemExit(
            "pdftotext not found on PATH (install poppler / poppler-utils) -- "
            "required to convert downloaded PDFs to text."
        )

    trial_files = sorted(TRIALS_DIR.glob("*.json"))
    for tf in trial_files:
        nct_id = json.loads(tf.read_text())["nct_id"]["value"]
        with urllib.request.urlopen(f"{CTGOV_API}/{nct_id}", timeout=30) as resp:
            raw = json.load(resp)
        docs = raw.get("documentSection", {}).get("largeDocumentModule", {}).get("largeDocs", [])
        if not docs:
            print(f"{nct_id}: no Study Documents posted on CT.gov")
            continue
        for doc in docs:
            filename = doc["filename"]
            url = f"{CDN_BASE}/{nct_id[-2:]}/{nct_id}/{filename}"
            pdf_path = CACHE_DIR / f"{nct_id}_{filename}"
            if not pdf_path.exists():
                urllib.request.urlretrieve(url, pdf_path)
            txt_path = pdf_path.with_suffix(".txt")
            subprocess.run(["pdftotext", "-layout", str(pdf_path), str(txt_path)], check=True)
            print(f"{nct_id}: {filename} -> {txt_path.name}")


if __name__ == "__main__":
    main()
