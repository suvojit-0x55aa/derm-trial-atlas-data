"""
real_world_safety.faers_summary -- typed summary of openFDA FAERS
(`https://api.fda.gov/drug/event.json`) for one drug. Drug-level: the same
value is reused across every trial of that drug (like `openfda_label`).

Value shape:
    {
      "query": {
        "search_field": "patient.drug.openfda.generic_name",
        "search_term": "dupilumab",
        "receivedate_from": "2017-01-01" | null,   # ISO; null = no date filter
        "receivedate_to": "2026-06-30" | null,
        "api_urls": [...],                          # every request that fed this summary
        "data_last_updated": "2026-07-30"           # meta.last_updated from the API
      },
      "total_reports": 478975,
      "serious_reports": int | null,
      "death_reports": int | null,
      "hospitalization_reports": int | null,
      "life_threatening_reports": int | null,
      "disability_reports": int | null,
      "top_reactions": [{"meddra_pt": "PNEUMONIA", "report_count": 4284, "pct_of_reports": 0.89}],
      "top_serious_reactions": [{"meddra_pt": ..., "report_count": ..., "pct_of_reports": ...}],
      "reports_by_year": [{"year": 2017, "report_count": 1234}],
      "meddra_version": "19.0" | null
    }

`build_faers_summary` takes the raw JSON bodies of the count queries so the
fetch script only has to do HTTP; the shapes below mirror the live API
(tests/fixtures/sources/faers_*.json are real responses).
"""
from ..scalars import parse_faers_date

SEARCH_FIELD = "patient.drug.openfda.generic_name"
SERIOUSNESS_FLAGS = {
    "serious_reports": "serious:1",
    "death_reports": "seriousnessdeath:1",
    "hospitalization_reports": "seriousnesshospitalization:1",
    "life_threatening_reports": "seriousnesslifethreatening:1",
    "disability_reports": "seriousnessdisabling:1",
}


def _pct(count, total):
    return round(100.0 * count / total, 2) if total else None


def reaction_rows(count_response: dict, total: int, limit: int = 20) -> list:
    """`count=patient.reaction.reactionmeddrapt.exact` response -> top_reactions rows."""
    rows = []
    for r in count_response.get("results", [])[:limit]:
        rows.append({"meddra_pt": r["term"], "report_count": int(r["count"]),
                     "pct_of_reports": _pct(int(r["count"]), total)})
    return rows


def reports_by_year(count_by_receivedate: dict) -> list:
    """`count=receivedate` response (daily buckets, 'time'/'count') -> yearly totals."""
    years = {}
    for r in count_by_receivedate.get("results", []):
        year = int(str(r["time"])[:4])
        years[year] = years.get(year, 0) + int(r["count"])
    return [{"year": y, "report_count": n} for y, n in sorted(years.items())]


def build_faers_summary(search_term: str, total_response: dict, reaction_counts: dict,
                        serious_reaction_counts: dict, yearly_counts: dict, seriousness_totals: dict,
                        api_urls: list, receivedate_from=None, receivedate_to=None, sample_record=None) -> dict:
    """
    total_response         any query with limit=1 (meta.results.total is the report count)
    reaction_counts        count=patient.reaction.reactionmeddrapt.exact (all reports)
    serious_reaction_counts  same count restricted to serious:1
    yearly_counts          count=receivedate
    seriousness_totals     {"serious_reports": <meta.results.total of serious:1 query>, ...}
    sample_record          one full report, used only to read the MedDRA version
    """
    total = int(total_response["meta"]["results"]["total"])
    meddra = None
    if sample_record:
        reactions = sample_record.get("patient", {}).get("reaction") or []
        meddra = reactions[0].get("reactionmeddraversionpt") if reactions else None
    summary = {
        "query": {
            "search_field": SEARCH_FIELD,
            "search_term": search_term,
            "receivedate_from": parse_faers_date(receivedate_from) if receivedate_from and "-" not in str(receivedate_from) else receivedate_from,
            "receivedate_to": parse_faers_date(receivedate_to) if receivedate_to and "-" not in str(receivedate_to) else receivedate_to,
            "api_urls": list(api_urls),
            "data_last_updated": total_response["meta"].get("last_updated"),
        },
        "total_reports": total,
        "top_reactions": reaction_rows(reaction_counts, total),
        "top_serious_reactions": reaction_rows(serious_reaction_counts, seriousness_totals.get("serious_reports") or total),
        "reports_by_year": reports_by_year(yearly_counts),
        "meddra_version": meddra,
    }
    for key in SERIOUSNESS_FLAGS:
        summary[key] = int(seriousness_totals[key]) if seriousness_totals.get(key) is not None else None
    return summary
