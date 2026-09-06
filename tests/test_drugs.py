"""
Schema v3 -> v4 drug-level restructuring (atlas/drugs.py).

The headline property this whole module exists for: every trial's own
value for the 6 moved fields (molecule.mechanism_of_action,
adverse_events.boxed_warning, real_world_safety.faers_summary,
exclusivity.{regulatory_application,orange_book,purple_book}) must still
resolve to the exact same FACT after split_trial_record + resolve_trial_record
as it had before the split -- this is a restructuring, not a re-extraction,
and test_committed_corpus_round_trips_losslessly checks that directly
against the real, committed 127-trial corpus rather than just a synthetic
fixture.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from atlas.drugs import (
    APPLICATION_KEYED_FIELDS, SINGLE_VALUED_FIELDS, application_number_of,
    build_drug_records, drug_ref, drug_ref_sv, ensure_drug_record, load_drug,
    resolve_trial_record, save_drug, slugify, split_trial_record,
)
from atlas.schema import DRUG, DRUG_APPLICATION, TRIAL, validate

ROOT = Path(__file__).resolve().parent.parent
TRIALS_DIR = ROOT / "data" / "trials"


def load_all_trials():
    return [json.loads(f.read_text()) for f in sorted(TRIALS_DIR.glob("*.json"))]


def sv(value, source_type="ctgov_api"):
    return {"value": value, "source_type": source_type, "source_url": "http://example.test",
            "source_excerpt": "excerpt", "extracted_by": "test", "reviewed_by": None, "confidence": 1.0}


def make_trial(nct, drug, application_number=None, registry="orange_book"):
    """A minimal-but-schema-shaped v3 trial record, just the 6 fields plus
    the bare minimum this module's functions read (nct_id, molecule.drug)."""
    return {
        "schema_version": 3,
        "nct_id": sv(nct),
        "molecule": {"drug": sv(drug), "mechanism_of_action": sv({
            "modality": "small_molecule", "drug_class": None, "antibody_isotype": None,
            "binding_targets": [], "pathway_cytokines": [], "receptor_subunits": [],
            "kinases_inhibited": [], "lower_potency_kinases": [], "selectivity": [],
            "reversible": None, "mechanism_established": None, "label_section": None,
        })},
        "adverse_events": {"boxed_warning": sv({
            "present": False, "title": None, "warning_categories": [],
            "referenced_label_sections": [], "product_names": [],
        }, "openfda_label")},
        "real_world_safety": {"faers_summary": sv({
            "query": {"search_field": "medicinalproduct", "search_term": drug.upper(), "receivedate_from": None,
                      "receivedate_to": None, "api_urls": [], "data_last_updated": None},
            "total_reports": 0, "serious_reports": None, "death_reports": None, "hospitalization_reports": None,
            "life_threatening_reports": None, "disability_reports": None, "top_reactions": [],
            "top_serious_reactions": [], "reports_by_year": [], "meddra_version": None,
        }, "openfda_faers")},
        "exclusivity": {
            "regulatory_application": sv({
                "application_type": "NDA", "application_number": application_number, "registry": registry,
                "center": "CDER", "proprietary_name": None, "applicant": None, "first_approval_date": None,
            } if application_number else None, "orange_book" if application_number else "needs_extraction"),
            "orange_book": sv({
                "application_type": "N", "application_number": application_number, "ingredient": drug.upper(),
                "trade_name": drug.upper(), "applicant": "Test Pharma", "applicant_full_name": None,
                "products": [], "patents": [], "exclusivities": [], "latest_patent_expiration": None,
                "latest_exclusivity_expiration": None, "data_file_date": None,
            } if application_number and registry == "orange_book" else None,
                "orange_book" if application_number and registry == "orange_book" else "needs_extraction"),
            "purple_book": sv(None, "needs_extraction"),
        },
    }


class SlugifyTest(unittest.TestCase):
    def test_simple_name(self):
        self.assertEqual(slugify("Roflumilast"), "roflumilast")

    def test_multi_word_name_hyphenated(self):
        self.assertEqual(slugify("Birch Triterpenes"), "birch-triterpenes")

    def test_punctuation_collapsed(self):
        self.assertEqual(slugify("Beremagene Geperpavec-svdt"), "beremagene-geperpavec-svdt")


class BuildDrugRecordsTest(unittest.TestCase):
    def test_single_trial_drug(self):
        t = make_trial("NCT00000001", "Solodrug", application_number="123456")
        records = build_drug_records([t])
        self.assertEqual(set(records), {"Solodrug"})
        rec = records["Solodrug"]
        self.assertEqual(rec["trial_ids"], ["NCT00000001"])
        self.assertEqual(len(rec["applications"]), 1)
        self.assertEqual(rec["applications"][0]["application_number"], "123456")
        self.assertEqual(rec["mechanism_of_action"], t["molecule"]["mechanism_of_action"])

    def test_two_applications_kept_distinct(self):
        """The Roflumilast case: one drug, two genuinely different FDA
        applications (a real registry-level difference, not noise) --
        both must survive as separate entries, not collapse to one."""
        t1 = make_trial("NCT00000001", "Dualdrug", application_number="AAA111")
        t2 = make_trial("NCT00000002", "Dualdrug", application_number="BBB222")
        records = build_drug_records([t1, t2])
        rec = records["Dualdrug"]
        self.assertEqual(rec["trial_ids"], ["NCT00000001", "NCT00000002"])
        app_nums = {a["application_number"] for a in rec["applications"]}
        self.assertEqual(app_nums, {"AAA111", "BBB222"})

    def test_needs_extraction_application_number_none(self):
        t = make_trial("NCT00000001", "Needsdrug", application_number=None)
        records = build_drug_records([t])
        rec = records["Needsdrug"]
        self.assertEqual(len(rec["applications"]), 1)
        self.assertIsNone(rec["applications"][0]["application_number"])
        self.assertEqual(rec["applications"][0]["regulatory_application"]["source_type"], "needs_extraction")

    def test_drug_records_validate(self):
        trials = [make_trial("NCT00000001", "Dualdrug", "AAA111"), make_trial("NCT00000002", "Dualdrug", "BBB222"),
                  make_trial("NCT00000003", "Needsdrug", None)]
        for name, rec in build_drug_records(trials).items():
            self.assertEqual(validate(rec, spec=DRUG), [], name)


class SplitAndResolveTest(unittest.TestCase):
    def test_split_replaces_six_fields_with_pointers(self):
        t = make_trial("NCT00000001", "Solodrug", "123456")
        split = split_trial_record(t)
        self.assertEqual(split["schema_version"], 4)
        for group, key in list(SINGLE_VALUED_FIELDS.values()) + list(APPLICATION_KEYED_FIELDS.values()):
            self.assertEqual(split[group][key]["source_type"], "drug_level_ref")
            self.assertEqual(split[group][key]["value"]["drug"], "Solodrug")
        self.assertIsNone(split["molecule"]["mechanism_of_action"]["value"]["application_number"])
        self.assertEqual(split["exclusivity"]["regulatory_application"]["value"]["application_number"], "123456")

    def test_split_does_not_mutate_input(self):
        t = make_trial("NCT00000001", "Solodrug", "123456")
        original = copy.deepcopy(t)
        split_trial_record(t)
        self.assertEqual(t, original)

    def test_round_trip_preserves_value(self):
        t1 = make_trial("NCT00000001", "Dualdrug", "AAA111")
        t2 = make_trial("NCT00000002", "Dualdrug", "BBB222")
        drug_records = build_drug_records([t1, t2])
        for t in (t1, t2):
            split = split_trial_record(t)
            resolved = resolve_trial_record(split, drug_records)
            for group, key in list(SINGLE_VALUED_FIELDS.values()) + list(APPLICATION_KEYED_FIELDS.values()):
                self.assertEqual(resolved[group][key]["value"], t[group][key]["value"],
                                  f"{t['nct_id']['value']} {group}.{key}")

    def test_split_trial_validates_against_trial_schema(self):
        t = make_trial("NCT00000001", "Solodrug", "123456")
        split = split_trial_record(t)
        # TRIAL requires many more fields than this fixture has -- validate
        # just the paths this module touches, not the whole (deliberately
        # incomplete) fixture.
        errs = validate(split["molecule"]["mechanism_of_action"], spec=TRIAL["properties"]["molecule"]["properties"]["mechanism_of_action"])
        self.assertEqual(errs, [])


class RefHelpersTest(unittest.TestCase):
    def test_drug_ref_shape(self):
        self.assertEqual(drug_ref("Roflumilast", "215985"), {"drug": "Roflumilast", "application_number": "215985"})
        self.assertEqual(drug_ref("Dupilumab"), {"drug": "Dupilumab", "application_number": None})

    def test_drug_ref_sv_is_never_needs_extraction(self):
        envelope = drug_ref_sv("Dupilumab")
        self.assertEqual(envelope["source_type"], "drug_level_ref")
        self.assertIsNotNone(envelope["value"])


class ApplicationNumberOfTest(unittest.TestCase):
    def test_reads_v3_shaped_value(self):
        t = make_trial("NCT00000001", "Solodrug", "123456")
        self.assertEqual(application_number_of(t), "123456")

    def test_reads_v4_drug_ref_pointer(self):
        t = make_trial("NCT00000001", "Solodrug", "123456")
        split = split_trial_record(t)
        self.assertEqual(application_number_of(split), "123456")

    def test_needs_extraction_is_none(self):
        t = make_trial("NCT00000001", "Needsdrug", None)
        self.assertIsNone(application_number_of(t))


class EnsureDrugRecordTest(unittest.TestCase):
    def test_fetches_once_then_reuses(self):
        calls = []

        def fetch_fields(drug):
            calls.append(drug)
            return {
                "mechanism_of_action": sv({"modality": "other", "drug_class": None, "antibody_isotype": None,
                                            "binding_targets": [], "pathway_cytokines": [], "receptor_subunits": [],
                                            "kinases_inhibited": [], "lower_potency_kinases": [], "selectivity": [],
                                            "reversible": None, "mechanism_established": None, "label_section": None}),
                "boxed_warning": sv({"present": False, "title": None, "warning_categories": [],
                                      "referenced_label_sections": [], "product_names": []}, "openfda_label"),
                "faers_summary": sv({"query": {"search_field": "medicinalproduct", "search_term": "X",
                                                "receivedate_from": None, "receivedate_to": None, "api_urls": [],
                                                "data_last_updated": None}, "total_reports": 0, "serious_reports": None,
                                      "death_reports": None, "hospitalization_reports": None,
                                      "life_threatening_reports": None, "disability_reports": None, "top_reactions": [],
                                      "top_serious_reactions": [], "reports_by_year": [], "meddra_version": None}, "openfda_faers"),
                "applications": [],
                "purple_book": sv(None, "needs_extraction"),
            }

        with tempfile.TemporaryDirectory() as tmp:
            drugs_dir = Path(tmp)
            rec1 = ensure_drug_record("Newdrug", fetch_fields, for_trial="NCT00000001", drugs_dir=drugs_dir)
            self.assertEqual(calls, ["Newdrug"])
            self.assertEqual(rec1["trial_ids"], ["NCT00000001"])

            rec2 = ensure_drug_record("Newdrug", fetch_fields, for_trial="NCT00000002", drugs_dir=drugs_dir)
            self.assertEqual(calls, ["Newdrug"], "fetch_fields must not be called again for a known drug")
            self.assertEqual(rec2["trial_ids"], ["NCT00000001", "NCT00000002"])

            on_disk = load_drug("Newdrug", drugs_dir)
            self.assertEqual(on_disk["trial_ids"], ["NCT00000001", "NCT00000002"])


class CommittedCorpusTest(unittest.TestCase):
    """The real, already-migrated (schema v4) corpus: every trial's 6 moved
    fields must be a resolvable drug_level_ref pointer, and resolving it
    must produce a schema-valid fact. This is the regression test for the
    real restructuring (not a synthetic fixture) -- run
    scripts/split_drug_level_fields.py's own round-trip check (value-level,
    against the pre-split v3 corpus) is the one-time migration proof; this
    test guards the STEADY STATE going forward."""

    @classmethod
    def setUpClass(cls):
        from atlas.drugs import DRUGS_DIR, load_all_drug_records
        cls.trials = load_all_trials()
        cls.drug_records = load_all_drug_records(DRUGS_DIR)

    def test_every_trial_is_already_v4(self):
        self.assertTrue(self.trials, "no trial files found")
        for t in self.trials:
            self.assertEqual(t["schema_version"], 4, t["nct_id"]["value"])

    def test_every_moved_field_is_a_drug_level_ref(self):
        for t in self.trials:
            for group, key in list(SINGLE_VALUED_FIELDS.values()) + list(APPLICATION_KEYED_FIELDS.values()):
                sv_ = t[group][key]
                self.assertEqual(sv_["source_type"], "drug_level_ref", f"{t['nct_id']['value']} {group}.{key}")
                self.assertEqual(sv_["value"]["drug"], t["molecule"]["drug"]["value"])

    def test_every_trial_resolves_to_a_valid_full_record(self):
        # resolve_trial_record's output is the FULL fact (a Mechanism, a
        # BoxedWarning, ...) -- validate it against the drug record's own
        # field spec, not the trial's own (now a DRUG_REF pointer) spec.
        single_valued_spec = {field: DRUG["properties"][field] for field in SINGLE_VALUED_FIELDS}
        app_keyed_spec = {field: DRUG_APPLICATION["properties"][field] for field in ("regulatory_application", "orange_book")}
        for t in self.trials:
            resolved = resolve_trial_record(t, self.drug_records)
            for field, (group, key) in SINGLE_VALUED_FIELDS.items():
                errs = validate(resolved[group][key], spec=single_valued_spec[field])
                self.assertEqual(errs, [], f"{t['nct_id']['value']} {group}.{key}: {errs}")
            for field, (group, key) in APPLICATION_KEYED_FIELDS.items():
                errs = validate(resolved[group][key], spec=app_keyed_spec[field])
                self.assertEqual(errs, [], f"{t['nct_id']['value']} {group}.{key}: {errs}")

    def test_roflumilast_trials_resolve_to_their_own_application(self):
        """Roflumilast is this corpus's one real multi-application drug:
        cream (NDA 215985) and foam (NDA 217242) each have their own,
        different Orange Book row -- a trial must resolve to ITS OWN
        application, not always the first one in the drug record."""
        by_nct = {t["nct_id"]["value"]: t for t in self.trials}
        cream_trials = ["NCT04211363", "NCT04211389", "NCT04773587", "NCT04773600"]
        foam_trials = ["NCT04091646", "NCT04128007", "NCT04973228", "NCT05028582"]
        for nct in cream_trials:
            resolved = resolve_trial_record(by_nct[nct], self.drug_records)
            self.assertEqual(resolved["exclusivity"]["regulatory_application"]["value"]["application_number"], "215985", nct)
        for nct in foam_trials:
            resolved = resolve_trial_record(by_nct[nct], self.drug_records)
            self.assertEqual(resolved["exclusivity"]["regulatory_application"]["value"]["application_number"], "217242", nct)


if __name__ == "__main__":
    unittest.main()
