"""
Atomic scalar normalisers for the semi-structured CT.gov values:

  * ages     "18 Years" / "6 Months" -> a number of years (min_age_years, max_age_years)
  * dates    "2014-09" / "2016-01-31" -> {"date": "YYYY-MM-DD", "precision": "year|month|day"}

A partial CT.gov date is padded to the first day of its period so every
`date` sorts and compares as a real ISO date, while `precision` records how
much of it the source actually stated.
"""
import re

AGE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(Year|Month|Week|Day)s?\s*$", re.I)
DATE_PRECISION = ("year", "month", "day")


def parse_age_years(text):
    """'18 Years' -> 18; '6 Months' -> 0.5; None -> None."""
    if text is None:
        return None
    m = AGE_RE.match(str(text))
    if not m:
        raise ValueError(f"unrecognised CT.gov age: {text!r}")
    n, unit = float(m.group(1)), m.group(2).lower()
    years = {"year": n, "month": n / 12, "week": n / 52, "day": n / 365}[unit]
    return int(years) if years.is_integer() else round(years, 4)


def parse_ctgov_date(text):
    """'2014-09' -> {'date': '2014-09-01', 'precision': 'month'}; None -> None."""
    if text is None:
        return None
    parts = str(text).split("-")
    if not all(p.isdigit() for p in parts) or len(parts) not in (1, 2, 3):
        raise ValueError(f"unrecognised CT.gov date: {text!r}")
    padded = parts + ["01"] * (3 - len(parts))
    return {"date": "-".join(padded), "precision": DATE_PRECISION[len(parts) - 1]}


def parse_us_date(text):
    """Orange Book 'Jan 14, 2027' / Purple Book '28-Mar-17' or '3/28/2017' -> 'YYYY-MM-DD'.
    Also accepts the full-month-name form ('March 28, 2017', 'November 23, 2015') --
    purplebooksearch.fda.gov's live search-results table (as opposed to its monthly
    CSV download) spells out the month, confirmed on real rows for Humira/Cosentyx
    during the v2 cross-source integration pass."""
    if text is None or not str(text).strip():
        return None
    from datetime import datetime

    t = str(text).strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%d-%b-%y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(t, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unrecognised source date: {text!r}")


def parse_faers_date(text):
    """openFDA FAERS 'YYYYMMDD' -> 'YYYY-MM-DD'."""
    if text is None:
        return None
    t = str(text)
    if not re.fullmatch(r"\d{8}", t):
        raise ValueError(f"unrecognised FAERS date: {text!r}")
    return f"{t[:4]}-{t[4:6]}-{t[6:]}"
