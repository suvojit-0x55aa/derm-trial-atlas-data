"""
exclusivity.purple_book -- typed record for one biologic BLA from the FDA
Purple Book monthly data download
(https://purplebooksearch.fda.gov/ -> Download Purple Book Data, CSV at
accessdata.fda.gov/drugsatfda_docs/PurpleBook/<year>/purplebook-search-<month>-data-download.csv).

BLA exclusivity follows the BPCIA (12-year reference-product exclusivity,
first-interchangeable exclusivity, orphan exclusivity) -- a different rule
set from the Orange Book's NCE/NPP/ODE codes, hence a separate shape.

Value shape:
    {
      "bla_number": "761055", "proprietary_name": "Dupixent", "proper_name": "dupilumab",
      "applicant": "Regeneron Pharmaceuticals, Inc.",
      "license_type": "351(a)",                # 351(a) = originator BLA; 351(k) = biosimilar/interchangeable
      "license_number": "1760", "center": "CDER",
      "products": [{"product_number": "001", "strength": "300MG/2ML", "dosage_form": "Injection",
                    "route": "Subcutaneous", "presentation": "Pre-Filled Syringe",
                    "marketing_status": "Rx", "licensure": "Licensed",
                    "approval_date": "2017-03-28", "submission_type": "Original",
                    "supplement_number": null}],
      "first_approval_date": "2017-03-28",
      "date_of_first_licensure": null,                       # BPCIA reference-product date, when FDA has determined it
      "reference_product_exclusivity_expiration": null,      # 12-year exclusivity end
      "exclusivity_expiration_date": null,
      "first_interchangeable_exclusivity_expiration": null,
      "orphan_exclusivity_expiration": "2031-01-25",
      "patent_list_provided": false,                          # 'Patent List Provided' column (post-2021 files)
      "biosimilars": [{"proper_name": ..., "bla_number": ..., "approval_date": ..., "license_type": "351(k)"}],
      "data_file_month": "2026-08" | null
    }
"""
import csv
import io

from ..scalars import parse_us_date

LICENSE_TYPES = ("351(a)", "351(k)")
# The 2020-era files call two columns differently; accept both spellings.
COLUMN_ALIASES = {
    "License Type": ("License Type", "BLA Type"),
    "Marketing Status": ("Marketing Status", "Status"),
}


def read_purple_book_csv(text: str) -> list:
    """Skip the report preamble rows and return the data rows as dicts."""
    rows = list(csv.reader(io.StringIO(text)))
    header_idx = next(i for i, r in enumerate(rows) if "BLA Number" in r)
    header = rows[header_idx]
    return [dict(zip(header, r)) for r in rows[header_idx + 1:] if any(c.strip() for c in r)]


def _col(row, name):
    for alias in COLUMN_ALIASES.get(name, (name,)):
        if alias in row:
            return row[alias].strip()
    return ""


def _blank_to_none(v):
    v = (v or "").strip()
    return None if v in ("", "-") else v


def build_purple_book_record(bla_number: str, rows: list, data_file_month=None) -> dict:
    bla_number = str(bla_number)
    mine = [r for r in rows if r.get("BLA Number", "").strip() == bla_number]
    if not mine:
        raise ValueError(f"no Purple Book rows for BLA {bla_number}")
    first = mine[0]
    proper = first["Proper Name"].strip()
    products = []
    for r in sorted(mine, key=lambda x: x.get("Product Number", "")):
        products.append({
            "product_number": r.get("Product Number", "").strip() or None,
            "strength": _blank_to_none(r.get("Strength")),
            "dosage_form": _blank_to_none(r.get("Dosage Form")),
            "route": _blank_to_none(r.get("Route of Administration")),
            "presentation": _blank_to_none(r.get("Product Presentation")),
            "marketing_status": _blank_to_none(_col(r, "Marketing Status")),
            "licensure": _blank_to_none(r.get("Licensure")),
            "approval_date": parse_us_date(_blank_to_none(r.get("Approval Date"))),
            "submission_type": _blank_to_none(r.get("Submission Type")),
            "supplement_number": _blank_to_none(r.get("Supplement Number")),
        })
    dates = [p["approval_date"] for p in products if p["approval_date"]]

    def first_nonblank(col):
        for r in mine:
            v = _blank_to_none(r.get(col))
            if v:
                return v
        return None

    biosimilars = []
    for r in rows:
        if _col(r, "License Type") == "351(k)" and r.get("Ref. Product Proper Name", "").strip().lower() == proper.lower():
            key = r["BLA Number"].strip()
            if not any(b["bla_number"] == key for b in biosimilars):
                biosimilars.append({
                    "proper_name": r["Proper Name"].strip(), "proprietary_name": _blank_to_none(r.get("Proprietary Name")),
                    "bla_number": key, "applicant": _blank_to_none(r.get("Applicant")),
                    "approval_date": parse_us_date(_blank_to_none(r.get("Approval Date"))),
                    "license_type": "351(k)",
                    "interchangeable_approval_date": parse_us_date(_blank_to_none(r.get("Inter. Approval Date"))),
                })
    patent_flag = first_nonblank("Patent List Provided")
    return {
        "bla_number": bla_number,
        "proprietary_name": _blank_to_none(first.get("Proprietary Name")),
        "proper_name": proper,
        "applicant": _blank_to_none(first.get("Applicant")),
        "license_type": _col(first, "License Type") or None,
        "license_number": _blank_to_none(first.get("License Number")),
        "center": _blank_to_none(first.get("Center")),
        "products": products,
        "first_approval_date": min(dates) if dates else None,
        "date_of_first_licensure": parse_us_date(first_nonblank("Date of First Licensure")),
        "reference_product_exclusivity_expiration": parse_us_date(first_nonblank("Ref. Product Exclusivity Exp. Date")),
        "exclusivity_expiration_date": parse_us_date(first_nonblank("Exclusivity Expiration Date")),
        "first_interchangeable_exclusivity_expiration": parse_us_date(first_nonblank("First Interchangeable Exclusivity Exp. Date")),
        "orphan_exclusivity_expiration": parse_us_date(first_nonblank("Orphan Exclusivity Exp. Date")),
        "patent_list_provided": (patent_flag or "").upper().startswith("Y") if patent_flag is not None else None,
        "biosimilars": biosimilars,
        "data_file_month": data_file_month,
    }
