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
# fda.gov/media/... and accessdata.fda.gov's own Orange Book query tool are
# both behind Akamai bot-detection (see scripts/fetch_orange_book.py's
# module docstring) -- openFDA's own mirror of the same dataset is not.
OPENFDA_ORANGEBOOK_URL = "https://api.fda.gov/drug/orangebook.json"
# purplebooksearch.fda.gov's downloads page only offers monthly delta CSVs
# (see scripts/fetch_purple_book.py's module docstring); the live search
# page renders the full current database instead.
PURPLE_BOOK_SEARCH_URL = "https://purplebooksearch.fda.gov/index.cfm?event=advancedsearch"
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
    # --- Plaque Psoriasis / HS / AA: small-molecule NDAs, via openFDA drug/orangebook.json ---
    "Baricitinib": {
        "value": {"application_type": "NDA", "application_number": "207924", "registry": "orange_book",
                  "center": "CDER", "proprietary_name": "OLUMIANT", "applicant": "ELI LILLY AND CO",
                  "first_approval_date": "2018-05-31"},
        "source_type": "orange_book", "source_url": OPENFDA_ORANGEBOOK_URL,
        "source_excerpt": "openFDA drug/orangebook.json: BARICITINIB application N207924, brand OLUMIANT, applicant ELI LILLY AND CO, approved 2018-05-31",
    },
    "Deucravacitinib": {
        "value": {"application_type": "NDA", "application_number": "214958", "registry": "orange_book",
                  "center": "CDER", "proprietary_name": "SOTYKTU", "applicant": "BRISTOL MYERS SQUIBB CO",
                  "first_approval_date": "2022-09-09"},
        "source_type": "orange_book", "source_url": OPENFDA_ORANGEBOOK_URL,
        "source_excerpt": "openFDA drug/orangebook.json: DEUCRAVACITINIB application N214958, brand SOTYKTU, applicant BRISTOL, approved 2022-09-09",
    },
    "Deuruxolitinib": {
        "value": {"application_type": "NDA", "application_number": "217900", "registry": "orange_book",
                  "center": "CDER", "proprietary_name": "LEQSELVI", "applicant": "SUN PHARMACEUTICAL INDUSTRIES INC",
                  "first_approval_date": "2024-07-25"},
        "source_type": "orange_book", "source_url": OPENFDA_ORANGEBOOK_URL,
        "source_excerpt": "openFDA drug/orangebook.json: DEURUXOLITINIB application N217900, brand LEQSELVI, applicant SUN PHARM INDS INC, approved 2024-07-25",
    },
    "Ritlecitinib": {
        "value": {"application_type": "NDA", "application_number": "215830", "registry": "orange_book",
                  "center": "CDER", "proprietary_name": "LITFULO", "applicant": "PFIZER INC",
                  "first_approval_date": "2023-06-23"},
        "source_type": "orange_book", "source_url": OPENFDA_ORANGEBOOK_URL,
        "source_excerpt": "openFDA drug/orangebook.json: RITLECITINIB application N215830, brand LITFULO, applicant PFIZER, approved 2023-06-23",
    },
    # Ruxolitinib the ingredient also covers Jakafi/Jakafi XR (oral, NDA
    # 202192/217180, oncology/GVHD) -- N215309 is specifically Opzelura,
    # the topical cream this atlas's vitiligo trials are for. Approval
    # date here is Opzelura's original NDA approval (Sept 2021, for
    # atopic dermatitis); the vitiligo indication was added by supplement
    # in July 2022 under the same NDA.
    "Ruxolitinib": {
        "value": {"application_type": "NDA", "application_number": "215309", "registry": "orange_book",
                  "center": "CDER", "proprietary_name": "OPZELURA", "applicant": "INCYTE CORP",
                  "first_approval_date": "2021-09-21"},
        "source_type": "orange_book", "source_url": OPENFDA_ORANGEBOOK_URL,
        "source_excerpt": "openFDA drug/orangebook.json: RUXOLITINIB application N215309, brand OPZELURA, applicant INCYTE CORP, approved 2021-09-21",
    },

    # --- Plaque Psoriasis / HS / CSU: biologic BLAs, via purplebooksearch.fda.gov live search table ---
    "Adalimumab": {
        "value": {"application_type": "BLA", "application_number": "125057", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Humira", "applicant": "AbbVie Inc.",
                  "first_approval_date": "2002-12-31"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_SEARCH_URL,
        "source_excerpt": "purplebooksearch.fda.gov live search table: BLA 125057 | Humira | adalimumab | 351(a) | AbbVie Inc. | first approved 2002-12-31",
    },
    "Bimekizumab": {
        "value": {"application_type": "BLA", "application_number": "761151", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Bimzelx", "applicant": "UCB, Inc.",
                  "first_approval_date": "2023-10-17"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_SEARCH_URL,
        "source_excerpt": "purplebooksearch.fda.gov live search table: BLA 761151 | Bimzelx | bimekizumab-bkzx | 351(a) | UCB, Inc. | first approved 2023-10-17",
    },
    "Guselkumab": {
        "value": {"application_type": "BLA", "application_number": "761061", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Tremfya", "applicant": "Janssen Biotech, Inc.",
                  "first_approval_date": "2017-07-13"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_SEARCH_URL,
        "source_excerpt": "purplebooksearch.fda.gov live search table: BLA 761061 | Tremfya | guselkumab | 351(a) | Janssen Biotech, Inc. | first approved 2017-07-13",
    },
    "Omalizumab": {
        "value": {"application_type": "BLA", "application_number": "103976", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Xolair", "applicant": "Genentech, Inc.",
                  "first_approval_date": "2003-06-20"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_SEARCH_URL,
        "source_excerpt": "purplebooksearch.fda.gov live search table: BLA 103976 | Xolair | omalizumab | 351(a) | Genentech, Inc. | first approved 2003-06-20",
    },
    "Risankizumab": {
        "value": {"application_type": "BLA", "application_number": "761105", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Skyrizi", "applicant": "AbbVie Inc.",
                  "first_approval_date": "2019-04-23"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_SEARCH_URL,
        "source_excerpt": "purplebooksearch.fda.gov live search table: BLA 761105 | Skyrizi | risankizumab-rzaa | 351(a) | AbbVie Inc. | first approved 2019-04-23",
    },
    "Secukinumab": {
        "value": {"application_type": "BLA", "application_number": "125504", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Cosentyx", "applicant": "Novartis Pharmaceuticals Corporation",
                  "first_approval_date": "2015-01-21"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_SEARCH_URL,
        "source_excerpt": "purplebooksearch.fda.gov live search table: BLA 125504 | Cosentyx | secukinumab | 351(a) | Novartis Pharmaceuticals Corporation | first approved 2015-01-21",
    },
    "Tildrakizumab": {
        "value": {"application_type": "BLA", "application_number": "761067", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Ilumya", "applicant": "Sun Pharmaceutical Industries Limited",
                  "first_approval_date": "2018-03-20"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_SEARCH_URL,
        "source_excerpt": "purplebooksearch.fda.gov live search table: BLA 761067 | Ilumya | tildrakizumab-asmn | 351(a) | Sun Pharmaceutical Industries Limited | first approved 2018-03-20",
    },
    "Nemolizumab": {
        "value": {"application_type": "BLA", "application_number": "761390", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Nemluvio", "applicant": "Galderma Laboratories, L.P.",
                  "first_approval_date": "2024-08-12"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_SEARCH_URL,
        "source_excerpt": "purplebooksearch.fda.gov live search table: BLA 761390 | Nemluvio | nemolizumab-ilto | 351(a) | Galderma Laboratories, L.P. | first approved 2024-08-12",
    },
    "Ixekizumab": {
        "value": {"application_type": "BLA", "application_number": "125521", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Taltz", "applicant": "Eli Lilly and Company",
                  "first_approval_date": "2016-03-22"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_SEARCH_URL,
        "source_excerpt": "purplebooksearch.fda.gov live search table: BLA 125521 | Taltz | ixekizumab | 351(a) | Eli Lilly and Company | first approved 2016-03-22",
    },
    # Certolizumab pegol is a PEGylated Fab' antibody fragment, licensed as
    # a BLA -- a biologic despite "pegol" suggesting a chemical
    # modification; Purple Book is correct here, not Orange Book. First
    # approved 2008 for Crohn's disease; the plaque-psoriasis indication
    # (this atlas's trials) followed in 2018 under the same BLA.
    "Certolizumab": {
        "value": {"application_type": "BLA", "application_number": "125160", "registry": "purple_book",
                  "center": "CDER", "proprietary_name": "Cimzia", "applicant": "UCB, Inc.",
                  "first_approval_date": "2008-04-22"},
        "source_type": "purple_book", "source_url": PURPLE_BOOK_SEARCH_URL,
        "source_excerpt": "purplebooksearch.fda.gov live search table: BLA 125160 | Cimzia | certolizumab pegol | 351(a) | UCB, Inc. | first approved 2008-04-22",
    },
    "Remibrutinib": {
        "value": {"application_type": "NDA", "application_number": "218436", "registry": "orange_book",
                  "center": "CDER", "proprietary_name": "RHAPSIDO", "applicant": "NOVARTIS",
                  "first_approval_date": "2025-09-30"},
        "source_type": "orange_book", "source_url": OPENFDA_ORANGEBOOK_URL,
        "source_excerpt": "openfda orangebook.json: products.active_ingredients.name=REMIBRUTINIB, application_number N218436, brand_name RHAPSIDO, applicant_full_name NOVARTIS, approval_date 2025-09-30",
    },
    "Delgocitinib": {
        "value": {"application_type": "NDA", "application_number": "219155", "registry": "orange_book",
                  "center": "CDER", "proprietary_name": "ANZUPGO", "applicant": "LEO PHARMA AS",
                  "first_approval_date": "2025-07-23"},
        "source_type": "orange_book", "source_url": OPENFDA_ORANGEBOOK_URL,
        "source_excerpt": "openfda orangebook.json: products.active_ingredients.name=DELGOCITINIB, application_number N219155, brand_name ANZUPGO, applicant_full_name LEO PHARMA AS, approval_date 2025-07-23",
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
