"""
exclusivity.orange_book -- typed record for one small-molecule NDA from the
FDA Orange Book data files (https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files,
ZIP of tilde-delimited products.txt / patent.txt / exclusivity.txt).

Value shape:
    {
      "application_type": "N",                 # Appl_Type: N = NDA, A = ANDA
      "application_number": "213871",          # Appl_No, zero-padded as in the file
      "ingredient": "ABROCITINIB", "trade_name": "CIBINQO",
      "applicant": "PFIZER", "applicant_full_name": "PFIZER INC",
      "products": [{"product_number": "001", "strength": "50MG", "dosage_form": "TABLET",
                    "route": "ORAL", "approval_date": "2022-01-14", "rld": true, "rs": false,
                    "te_code": null, "marketing_type": "RX"}],
      "patents": [{"patent_number": "8962629", "expiration_date": "2031-01-15",
                   "drug_substance_claim": true, "drug_product_claim": false,
                   "patent_use_code": "U-3371", "delisted": false,
                   "submission_date": "2019-09-13", "product_numbers": ["001"]}],
      "exclusivities": [{"code": "NCE", "expiration_date": "2027-01-14", "product_numbers": ["001", "002", "003"]}],
      "latest_patent_expiration": "2038-03-09",
      "latest_exclusivity_expiration": "2032-04-28",
      "data_file_date": "2026-08" | null          # month of the Orange Book release used
    }

One patent row per (patent, use code): the same patent number can appear
with several use codes and product numbers in patent.txt; we keep one entry
per (patent_number, patent_use_code) and collect the product numbers it is
listed against.
"""
import csv
import io

from ..scalars import parse_us_date

APPLICATION_TYPES = ("N", "A")


def read_tilde_file(text: str) -> list:
    """Parse one Orange Book .txt (tilde-delimited, header row first) into dicts."""
    reader = csv.DictReader(io.StringIO(text), delimiter="~")
    return [dict(row) for row in reader]


def _flag(v):
    return str(v).strip().upper() in ("Y", "YES")


def build_orange_book_record(appl_no: str, products: list, patents: list, exclusivities: list,
                             appl_type: str = "N", data_file_date=None) -> dict:
    appl_no = str(appl_no).zfill(6)
    prod_rows = [r for r in products if r["Appl_No"] == appl_no and r["Appl_Type"] == appl_type]
    if not prod_rows:
        raise ValueError(f"no Orange Book products for {appl_type}{appl_no}")
    first = prod_rows[0]
    df_route = first["DF;Route"].split(";")
    out_products = []
    for r in sorted(prod_rows, key=lambda x: x["Product_No"]):
        df, route = (r["DF;Route"].split(";") + [None])[:2]
        out_products.append({
            "product_number": r["Product_No"], "strength": r["Strength"],
            "dosage_form": df, "route": route,
            "approval_date": parse_us_date(r["Approval_Date"]),
            "rld": _flag(r["RLD"]), "rs": _flag(r["RS"]),
            "te_code": r["TE_Code"] or None, "marketing_type": r["Type"],
        })
    pat = {}
    for r in patents:
        if r["Appl_No"] != appl_no or r["Appl_Type"] != appl_type:
            continue
        key = (r["Patent_No"], r["Patent_Use_Code"] or None)
        entry = pat.setdefault(key, {
            "patent_number": r["Patent_No"],
            "expiration_date": parse_us_date(r["Patent_Expire_Date_Text"]),
            "drug_substance_claim": _flag(r["Drug_Substance_Flag"]),
            "drug_product_claim": _flag(r["Drug_Product_Flag"]),
            "patent_use_code": r["Patent_Use_Code"] or None,
            "delisted": _flag(r["Delist_Flag"]),
            "submission_date": parse_us_date(r["Submission_Date"]),
            "product_numbers": [],
        })
        if r["Product_No"] not in entry["product_numbers"]:
            entry["product_numbers"].append(r["Product_No"])
    excl = {}
    for r in exclusivities:
        if r["Appl_No"] != appl_no or r["Appl_Type"] != appl_type:
            continue
        entry = excl.setdefault((r["Exclusivity_Code"], r["Exclusivity_Date"]), {
            "code": r["Exclusivity_Code"], "expiration_date": parse_us_date(r["Exclusivity_Date"]),
            "product_numbers": [],
        })
        if r["Product_No"] not in entry["product_numbers"]:
            entry["product_numbers"].append(r["Product_No"])
    out_patents = sorted(pat.values(), key=lambda p: (p["expiration_date"] or "", p["patent_number"], p["patent_use_code"] or ""))
    out_excl = sorted(excl.values(), key=lambda e: (e["expiration_date"] or "", e["code"]))
    return {
        "application_type": appl_type,
        "application_number": appl_no,
        "ingredient": first["Ingredient"],
        "trade_name": first["Trade_Name"],
        "applicant": first["Applicant"],
        "applicant_full_name": first["Applicant_Full_Name"],
        "products": out_products,
        "patents": out_patents,
        "exclusivities": out_excl,
        "latest_patent_expiration": max((p["expiration_date"] for p in out_patents if p["expiration_date"]), default=None),
        "latest_exclusivity_expiration": max((e["expiration_date"] for e in out_excl if e["expiration_date"]), default=None),
        "data_file_date": data_file_date,
    }
