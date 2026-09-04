"""
Proof that the v1 -> v2 migration loses nothing.

For every trial, the committed v1 record (tests/fixtures/v1_trials/) is
compared against the committed v2 record (data/trials/):

  1. determinism      migrate_trial(v1) == committed v2, byte for byte
  2. untouched fields every v1 sourced value whose shape did not change is
                      identical in v2 (same value, same provenance)
  3. scalar transforms ages/dates map exactly and are reversible
  4. provenance       every v1 prose value is still present verbatim somewhere
                      in v2 (source_excerpt, endpoint verbatim, intervention
                      description)
  5. fact coverage    every number, scale name, timepoint, and agent/method
                      token in a v1 prose value appears in the *atomic* v2
                      value (prose-carrying keys are stripped before checking,
                      so a free-text catch-all cannot satisfy this)
  6. endpoints        1:1 with the v1 titles, in order; every Week/Day number
                      in a title is a timepoint; every EASI-NN / >=N-point
                      threshold in a title is a criterion value
  7. gaps preserved   every v1 needs_extraction field is still
                      needs_extraction in v2 (renamed, never invented), and
                      the only new gaps are the three source placeholders
"""
import json
import re
import unittest
from pathlib import Path

from atlas.criteria import SCALE_PATTERNS
from atlas.migrate import RENAMES, migrate_trial
from atlas.scalars import parse_age_years, parse_ctgov_date

ROOT = Path(__file__).resolve().parent.parent
V1_DIR = ROOT / "tests" / "fixtures" / "v1_trials"
V2_DIR = ROOT / "data" / "trials"

# v1 fields whose *value shape* changed (everything else must be identical).
RESHAPED = {
    ("molecule", "mechanism_of_action"), ("molecule", "dosing_regimen"),
    ("population", "min_age"), ("population", "max_age"), ("population", "severity_definition"),
    ("design", "background_therapy_rule"),
    ("endpoints", "primary_endpoint_measure"), ("endpoints", "secondary_endpoint_measures"),
    ("endpoints", "endpoint_hierarchy_multiplicity"),
    ("timing_ops", "start_date"), ("timing_ops", "primary_completion_date"), ("timing_ops", "completion_date"),
    ("timing_ops", "visit_schedule"), ("timing_ops", "rescue_therapy_rules"),
    ("adverse_events", "most_common_adverse_events"), ("adverse_events", "boxed_warning"),
}
PROSE_FIELDS = [
    ("population", "severity_definition"), ("design", "background_therapy_rule"),
    ("endpoints", "endpoint_hierarchy_multiplicity"), ("timing_ops", "visit_schedule"),
    ("timing_ops", "rescue_therapy_rules"), ("molecule", "mechanism_of_action"),
]
# keys inside structured values that may legitimately carry prose; stripped before fact coverage
PROSE_CARRYING_KEYS = {"description", "verbatim", "source_inconsistency", "population_note", "label", "initial_target"}
NUMBER = re.compile(r"(?<![A-Za-z0-9.])(\d+(?:\.\d+)?)(?![A-Za-z0-9])")
AGENT_TOKENS = [
    "triamcinolone", "fluocinolone", "hydrocortisone", "mometasone", "betamethasone", "clobetasol",
    "cyclosporin", "methotrexate", "mycophenolate", "azathioprine", "prednison", "phototherapy",
    "emollient", "antihistamine", "TCS", "TCI", "dupilumab", "abrocitinib", "lebrikizumab", "tralokinumab",
    "upadacitinib", "Bonferroni", "Holm", "Bretz", "gatekeeping", "graphical", "monotherapy",
    "IgG4", "IL-4R", "IL-13", "JAK1", "JAK2", "JAK3", "TYK2", "half-lives", "medical monitor", "eCRF",
]


def v2_path(group, key):
    return group, RENAMES.get((group, key), key)


def norm(s):
    return re.sub(r"[\s_\-]", "", s.lower())


def atomic_json(value):
    """Serialise a structured value with prose-carrying keys removed."""
    def strip(v):
        if isinstance(v, dict):
            return {k: strip(x) for k, x in v.items() if k not in PROSE_CARRYING_KEYS}
        if isinstance(v, list):
            return [strip(x) for x in v]
        return v
    return json.dumps(strip(value), ensure_ascii=False)


def scales_in(text):
    found = set()
    for pattern, scale, _ in SCALE_PATTERNS:
        if re.search(pattern, text):
            found.add(scale)
    return found


def sourced_fields(record):
    for group, fields in record.items():
        if group == "nct_id":
            yield ("nct_id", None), fields
        elif isinstance(fields, dict):
            for key, sv in fields.items():
                yield (group, key), sv


class LosslessMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = []
        for f in sorted(V1_DIR.glob("*.json")):
            v1 = json.loads(f.read_text())
            v2 = json.loads((V2_DIR / f.name).read_text())
            cls.pairs.append((f.stem, v1, v2))
        assert len(cls.pairs) == 17, "expected the 17 committed v1 trials"

    def test_determinism(self):
        for nct, v1, v2 in self.pairs:
            with self.subTest(nct=nct):
                self.assertEqual(migrate_trial(v1), v2)

    def test_untouched_fields_identical(self):
        for nct, v1, v2 in self.pairs:
            for (group, key), sv in sourced_fields(v1):
                if (group, key) in RESHAPED:
                    continue
                with self.subTest(nct=nct, field=f"{group}.{key}"):
                    target = v2["nct_id"] if group == "nct_id" else v2[group][key]
                    self.assertEqual(sv, target)

    def test_scalar_transforms_exact(self):
        for nct, v1, v2 in self.pairs:
            for key in ("min_age", "max_age"):
                old = v1["population"][key]["value"]
                new = v2["population"][f"{key}_years"]["value"]
                self.assertEqual(new, parse_age_years(old), (nct, key))
                if old is not None:
                    self.assertEqual(f"{new} Years", old, (nct, key))  # reversible
            for key in ("start_date", "primary_completion_date", "completion_date"):
                old = v1["timing_ops"][key]["value"]
                new = v2["timing_ops"][key]["value"]
                self.assertEqual(new, parse_ctgov_date(old), (nct, key))
                cut = {"year": 4, "month": 7, "day": 10}[new["precision"]]
                self.assertEqual(new["date"][:cut], old, (nct, key))  # reversible

    def test_prose_preserved_verbatim(self):
        for nct, v1, v2 in self.pairs:
            for group, key in PROSE_FIELDS + [("adverse_events", "boxed_warning")]:
                old = v1[group][key]["value"]
                if not isinstance(old, str):
                    continue
                excerpt = v2[group][RENAMES.get((group, key), key)]["source_excerpt"] or ""
                with self.subTest(nct=nct, field=key):
                    self.assertIn(old.strip(), excerpt)
            for i, ep in enumerate(v2["endpoints"]["secondary_endpoints"]["value"] or []):
                self.assertEqual(ep["verbatim"], v1["endpoints"]["secondary_endpoint_measures"]["value"][i])
            if v1["molecule"]["dosing_regimen"]["value"]:
                descs = "\n".join(x["description"] for x in v2["molecule"]["dosing_regimen"]["value"])
                for seg in v1["molecule"]["dosing_regimen"]["value"].split(" || "):
                    self.assertIn(seg.split(": ", 1)[1].strip(), descs, (nct, seg[:40]))

    def test_fact_coverage(self):
        for nct, v1, v2 in self.pairs:
            for group, key in PROSE_FIELDS + [("molecule", "dosing_regimen")]:
                old = v1[group][key]["value"]
                if not isinstance(old, str):
                    continue
                new = v2[group][RENAMES.get((group, key), key)]["value"]
                blob = atomic_json(new)
                with self.subTest(nct=nct, field=key):
                    self.assertIsNotNone(new)
                    missing = []
                    own_drug = v1["molecule"]["drug"]["value"].lower()
                    for n in set(NUMBER.findall(old)):
                        if re.search(r"[Pp]hase " + re.escape(n) + r"\b", old):
                            continue  # "Phase 3 trials" is a label, not a fact of the field
                        forms = {n, str(float(n) if "." in n else int(n))}
                        if re.search(re.escape(n) + r"\s*%", old):
                            forms.add(str(round(float(n) / 100, 4)))  # "5%" may be stored as alpha 0.05
                        if not any(re.search(r"(?<![\d.])" + re.escape(f) + r"(?![\d.])", blob) for f in forms):
                            missing.append(n)
                    for scale in scales_in(old):
                        if scale not in blob:
                            missing.append(scale)
                    for tok in AGENT_TOKENS:
                        if tok.lower() == own_drug:
                            continue  # the trial's own drug name is molecule.drug, not a fact of this field
                        if norm(tok) in norm(old) and norm(tok) not in norm(blob):
                            missing.append(tok)
                    self.assertEqual(missing, [], f"{nct} {key}: facts in v1 prose missing from atomic v2 value: {missing}")

    def test_endpoints_one_to_one(self):
        for nct, v1, v2 in self.pairs:
            titles = [v1["endpoints"]["primary_endpoint_measure"]["value"]] + list(v1["endpoints"]["secondary_endpoint_measures"]["value"])
            eps = v2["endpoints"]["primary_endpoints"]["value"] + v2["endpoints"]["secondary_endpoints"]["value"]
            self.assertEqual([e["verbatim"] for e in eps], titles, nct)
            self.assertEqual([e["rank"] for e in eps][:1], ["primary"])
            for e in eps:
                with self.subTest(nct=nct, title=e["verbatim"][:60]):
                    title = re.sub(r"\s*\(Time frame:.*\)\s*$", "", e["verbatim"].replace("≥", ">="))
                    tps = {t["value"] for t in e["timepoints"]} | {t["end_value"] for t in e["timepoints"] if t["end_value"]}
                    if e["through"]:
                        tps.add(e["through"]["value"])
                    for n in re.findall(r"(?:Weeks?|Days?)\s+(\d+)", title) + re.findall(r"(?:Weeks?|Days?)\s+\d+(?:-\d+)?(?:,\s*(?:and\s+)?\d+)*?(?:,\s*(?:and\s+)?|\s+and\s+)(\d+)", title):
                        self.assertIn(int(n), tps, f"timepoint {n} dropped")
                    crit_values = {c["value"] if not isinstance(c["value"], list) else tuple(c["value"])
                                   for c in e["responder_criteria"] + e["subgroup_criteria"]}
                    for n in re.findall(r"(?:EASI|SCORAD)[- ](\d{2,3})\b", title):
                        self.assertIn(int(n), crit_values, f"EASI/SCORAD {n} threshold dropped")
                    for n in re.findall(r">=\s*(\d+(?:\.\d+)?)[ -][Pp]oints?", title):
                        self.assertIn(float(n) if "." in n else int(n), crit_values, f">= {n} points threshold dropped")
                    self.assertNotEqual(e["measure_type"], "other", "unclassified endpoint")

    def test_gaps_preserved_not_invented(self):
        for nct, v1, v2 in self.pairs:
            old_gaps = {v2_path(g, k) for (g, k), sv in sourced_fields(v1) if sv["source_type"] == "needs_extraction"}
            new_gaps = {(g, k) for (g, k), sv in sourced_fields(v2) if sv["source_type"] == "needs_extraction"}
            placeholders = {("real_world_safety", "faers_summary"), ("exclusivity", "orange_book"), ("exclusivity", "purple_book")}
            self.assertEqual(new_gaps, old_gaps | placeholders, nct)
            self.assertEqual(v2["exclusivity"]["regulatory_application"]["source_type"] in ("orange_book", "purple_book"), True, nct)

    def test_field_count(self):
        # 17 trials x 35 v1 fields = 595 sourced values, all still present (renamed) plus 4 new ones per trial
        v1_total = sum(len(list(sourced_fields(v1))) for _, v1, _ in self.pairs)
        v2_total = sum(len(list(sourced_fields(v2))) for _, _, v2 in self.pairs)
        self.assertEqual(v1_total, 595)
        self.assertEqual(v2_total, 595 + 17 * 4)


if __name__ == "__main__":
    unittest.main()
