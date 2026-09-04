"""
exclusivity.regulatory_application -- the NDA/BLA join key that lets
Orange Book (small-molecule NDAs) and Purple Book (biologic BLAs) data
attach to a drug. Drug-level; hand-curated from the actual registry rows,
the same way scripts/fetch_trials.py::TRIALS is curated.

Each row records exactly which line of which registry file it came from
(that line is the sourced value's `source_excerpt`).
"""

ORANGE_BOOK_URL = "https://www.fda.gov/media/76860/download"  # Orange Book data files ZIP (products.txt)
PURPLE_BOOK_URL = "https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/2026/purplebook-search-August-data-download.csv"
FETCHED_ON = "2026-09-05"

APPLICATIONS = {
    "Abrocitinib": {
        "value": {"application_type": "NDA", "application_number": "213871", "registry": "orange_book",
                  "center": "CDER", "proprietary_name": "CIBINQO", "applicant": "PFIZER INC",
                  "first_approval_date": "2022-01-14"},
        "source_type": "orange_book", "source_url": ORANGE_BOOK_URL,
        "source_excerpt": "products.txt: ABROCITINIB~TABLET;ORAL~CIBINQO~PFIZER~50MG~N~213871~001~~Jan 14, 2022~Yes~No~RX~PFIZER INC",
    },
    "Upadacitinib": {
        "value": {"application_type": "NDA", "application_number": "211675", "registry": "orange_book",
                  "center": "CDER", "proprietary_name": "RINVOQ", "applicant": "ABBVIE INC",
                  "first_approval_date": "2019-08-16"},
        "source_type": "orange_book", "source_url": ORANGE_BOOK_URL,
        "source_excerpt": "products.txt: UPADACITINIB~TABLET, EXTENDED RELEASE;ORAL~RINVOQ~ABBVIE~15MG~N~211675~001~~Aug 16, 2019~Yes~No~RX~ABBVIE INC",
    },
    "Dupilumab": {
        "value": {"application_type": "BLA", "application_number": "761055", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Dupixent", "applicant": "Regeneron Pharmaceuticals, Inc.",
                  "first_approval_date": "2017-03-28"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_URL,
        "source_excerpt": "row: Regeneron Pharmaceuticals, Inc. | BLA 761055 | Dupixent | dupilumab | 351(a) | 300MG/2ML Injection Subcutaneous Pre-Filled Syringe | Rx | Licensed | 28-Mar-17 | Original | License 1760 | Product 001 | CDER | Orphan Exclusivity Exp. Date 25-Jan-31",
    },
    "Lebrikizumab": {
        "value": {"application_type": "BLA", "application_number": "761306", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Ebglyss", "applicant": "Eli Lilly and Company",
                  "first_approval_date": "2024-09-13"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_URL,
        "source_excerpt": "row: Eli Lilly and Company | BLA 761306 | Ebglyss | lebrikizumab-lbkz | 351(a) | 250MG/2ML Injection Subcutaneous Autoinjector | Rx | Licensed | 13-Sep-24 | Original | License 1891 | Product 001 | CDER",
    },
    "Tralokinumab": {
        "value": {"application_type": "BLA", "application_number": "761180", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Adbry", "applicant": "LEO Pharma A/S",
                  "first_approval_date": "2021-12-27"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_URL,
        "source_excerpt": "row: LEO Pharma A/S | BLA 761180 | Adbry | tralokinumab-ldrm | 351(a) | 150MG/ML Injection Subcutaneous Pre-Filled Syringe | Rx | Licensed | 27-Dec-21 | Original | License 2169 | Product 001 | CDER",
    },
}


def regulatory_application_field(drug: str) -> dict:
    row = APPLICATIONS.get(drug)
    if row is None:
        return {"value": None, "source_type": "needs_extraction", "source_url": None, "source_excerpt": None,
                "extracted_by": None, "reviewed_by": None, "confidence": None}
    return {
        "value": dict(row["value"]),
        "source_type": row["source_type"],
        "source_url": row["source_url"],
        "source_excerpt": row["source_excerpt"],
        "extracted_by": f"atlas.regulatory_applications (registry file fetched {FETCHED_ON})",
        "reviewed_by": None,
        "confidence": 1.0,
    }
