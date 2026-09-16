"""
Unit tests for scripts/fetch_condition_landscape.py: the general-purpose,
any-status ClinicalTrials.gov landscape fetcher. This tool is deliberately
separate from the curated atlas (data/trials/) -- these tests mock the
CT.gov API at the one HTTP seam (_http_get_json) rather than hitting the
live API, and never touch data/trials/ or data/condition_landscape/.
"""
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_condition_landscape as fcl  # noqa: E402


def make_study(nct_id, overall_status="COMPLETED", why_stopped=None,
                interventions=None, has_results=False):
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": nct_id,
                "briefTitle": f"A Study of Something for {nct_id}",
                "officialTitle": f"Official Title {nct_id}",
                "acronym": "ACRO",
            },
            "statusModule": {
                "overallStatus": overall_status,
                "whyStopped": why_stopped,
                "startDateStruct": {"date": "2020-01-01"},
                "primaryCompletionDateStruct": {"date": "2021-01-01"},
                "completionDateStruct": {"date": "2021-06-01"},
                "lastUpdatePostDateStruct": {"date": "2021-07-01"},
            },
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": "Some Sponsor Inc."},
                "collaborators": [{"name": "A University"}],
            },
            "designModule": {
                "studyType": "INTERVENTIONAL",
                "phases": ["PHASE3"],
                "designInfo": {
                    "allocation": "RANDOMIZED",
                    "interventionModel": "PARALLEL",
                    "primaryPurpose": "TREATMENT",
                    "maskingInfo": {"masking": "DOUBLE"},
                },
                "enrollmentInfo": {"count": 200, "type": "ACTUAL"},
            },
            "eligibilityModule": {
                "minimumAge": "18 Years",
                "maximumAge": "75 Years",
                "sex": "ALL",
                "healthyVolunteers": False,
                "eligibilityCriteria": "Inclusion: has the condition.",
            },
            "armsInterventionsModule": {
                "armGroups": [{"label": "Drug"}, {"label": "Placebo"}],
                "interventions": interventions if interventions is not None else [
                    {"type": "DRUG", "name": "Examplemab", "description": "A biologic."},
                    {"type": "DRUG", "name": "Placebo", "description": "Matching placebo."},
                ],
            },
            "outcomesModule": {
                "primaryOutcomes": [
                    {"measure": "Responder rate", "timeFrame": "Week 16", "description": "PASI 75."}
                ],
                "secondaryOutcomes": [
                    {"measure": "Safety", "timeFrame": "Week 52", "description": None}
                ],
            },
            "conditionsModule": {"conditions": ["Plaque Psoriasis"]},
            "contactsLocationsModule": {
                "locations": [
                    {"country": "United States"},
                    {"country": "Germany"},
                    {"country": "United States"},
                ]
            },
        },
        "hasResults": has_results,
    }


class SlugifyTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(fcl.slugify("Psoriasis"), "psoriasis")

    def test_spaces_and_punctuation(self):
        self.assertEqual(fcl.slugify("Chronic Spontaneous Urticaria!"), "chronic-spontaneous-urticaria")

    def test_multi_word_condition(self):
        self.assertEqual(fcl.slugify("Atopic  Dermatitis (AD)"), "atopic-dermatitis-ad")

    def test_empty_falls_back(self):
        self.assertEqual(fcl.slugify("   "), "condition")


class ParseConditionsTest(unittest.TestCase):
    def test_repeated_flag(self):
        self.assertEqual(fcl.parse_conditions(["psoriasis", "eczema"]), ["psoriasis", "eczema"])

    def test_comma_separated(self):
        self.assertEqual(fcl.parse_conditions(["psoriasis, eczema"]), ["psoriasis", "eczema"])

    def test_dedup_preserves_first_seen_order(self):
        self.assertEqual(
            fcl.parse_conditions(["psoriasis", "eczema", "psoriasis"]),
            ["psoriasis", "eczema"],
        )

    def test_blank_entries_dropped(self):
        self.assertEqual(fcl.parse_conditions(["psoriasis,, ,eczema"]), ["psoriasis", "eczema"])


class FetchAllStudiesTest(unittest.TestCase):
    def test_paginates_until_no_next_token(self):
        page1 = {"studies": [make_study("NCT00000001"), make_study("NCT00000002")], "nextPageToken": "tok2"}
        page2 = {"studies": [make_study("NCT00000003")], "nextPageToken": None}
        with patch.object(fcl, "_http_get_json", side_effect=[page1, page2]) as mock_get, \
             patch.object(fcl.time, "sleep"):
            studies = fcl.fetch_all_studies("Psoriasis", page_size=2, sleep=0)
        self.assertEqual(len(studies), 3)
        self.assertEqual(mock_get.call_count, 2)
        first_url = mock_get.call_args_list[0].args[0]
        self.assertIn("query.cond=Psoriasis", first_url)
        second_url = mock_get.call_args_list[1].args[0]
        self.assertIn("pageToken=tok2", second_url)

    def test_max_trials_caps_across_pages(self):
        page1 = {"studies": [make_study("NCT00000001"), make_study("NCT00000002")], "nextPageToken": "tok2"}
        with patch.object(fcl, "_http_get_json", side_effect=[page1]), patch.object(fcl.time, "sleep"):
            studies = fcl.fetch_all_studies("Psoriasis", page_size=2, sleep=0, max_trials=2)
        self.assertEqual(len(studies), 2)

    def test_single_page_no_pagination_call(self):
        page1 = {"studies": [make_study("NCT00000001")], "nextPageToken": None}
        with patch.object(fcl, "_http_get_json", side_effect=[page1]) as mock_get:
            studies = fcl.fetch_all_studies("Rosacea", page_size=1000, sleep=0)
        self.assertEqual(len(studies), 1)
        self.assertEqual(mock_get.call_count, 1)


class FetchSupplementaryTest(unittest.TestCase):
    def test_success_passthrough(self):
        payload = {"protocolSection": {"referencesModule": {"references": []}}}
        with patch.object(fcl, "_http_get_json", return_value=payload) as mock_get:
            result = fcl.fetch_supplementary("NCT00000001")
        self.assertEqual(result, payload)
        url = mock_get.call_args.args[0]
        self.assertIn("fields=ReferencesModule,DocumentSection", url)

    def test_network_error_is_swallowed_and_recorded(self):
        with patch.object(fcl, "_http_get_json", side_effect=urllib.error.URLError("boom")):
            result = fcl.fetch_supplementary("NCT00000001")
        self.assertIn("_fetch_error", result)


class BuildTrialRecordTest(unittest.TestCase):
    def test_captures_every_status_not_just_completed(self):
        raw = make_study("NCT00000009", overall_status="TERMINATED", why_stopped="Sponsor decision")
        record = fcl.build_trial_record(raw, None, "2026-09-16T00:00:00Z")
        self.assertEqual(record["status"]["overall_status"], "TERMINATED")
        self.assertEqual(record["status"]["why_stopped"], "Sponsor decision")
        self.assertFalse(record["status"]["has_results"])

    def test_core_fields(self):
        raw = make_study("NCT00000010")
        record = fcl.build_trial_record(raw, None, "2026-09-16T00:00:00Z")
        self.assertEqual(record["nct_id"], "NCT00000010")
        self.assertEqual(record["identity"]["lead_sponsor"], "Some Sponsor Inc.")
        self.assertEqual(record["identity"]["collaborators"], ["A University"])
        self.assertEqual(record["design"]["number_of_arms"], 2)
        self.assertEqual(record["design"]["enrollment_count"], 200)
        self.assertEqual(record["locations"]["count"], 3)
        self.assertEqual(record["locations"]["countries"], ["Germany", "United States"])
        self.assertEqual(len(record["outcomes"]["primary"]), 1)
        self.assertEqual(len(record["outcomes"]["secondary"]), 1)

    def test_no_needs_extraction_placeholders(self):
        # unlike the curated atlas, missing data here is a plain null, not
        # a sourced-value envelope with a "needs_extraction" source_type.
        raw = make_study("NCT00000011")
        record = fcl.build_trial_record(raw, None, "2026-09-16T00:00:00Z")
        dumped = json.dumps(record)
        self.assertNotIn("needs_extraction", dumped)

    def test_supplementary_publications_and_documents(self):
        raw = make_study("NCT00000012")
        supplementary = {
            "protocolSection": {
                "referencesModule": {
                    "references": [
                        {"pmid": "12345678", "type": "RESULT", "citation": "Some Author et al."}
                    ]
                }
            },
            "documentSection": {
                "largeDocumentModule": {
                    "largeDocs": [
                        {
                            "typeAbbrev": "Prot",
                            "hasProtocol": True,
                            "hasSap": False,
                            "hasIcf": False,
                            "label": "Study Protocol",
                            "date": "2020-01-01",
                            "filename": "Prot_000.pdf",
                            "size": 12345,
                        }
                    ]
                }
            },
        }
        record = fcl.build_trial_record(raw, supplementary, "2026-09-16T00:00:00Z")
        pubs = record["supplementary"]["publications"]
        self.assertEqual(pubs, [{"pmid": "12345678", "type": "RESULT", "citation": "Some Author et al."}])
        docs = record["supplementary"]["documents"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(
            docs[0]["url"],
            "https://cdn.clinicaltrials.gov/large-docs/12/NCT00000012/Prot_000.pdf",
        )
        self.assertIsNone(record["supplementary"]["fetch_error"])

    def test_supplementary_fetch_error_is_recorded_not_fatal(self):
        raw = make_study("NCT00000013")
        record = fcl.build_trial_record(raw, {"_fetch_error": "timed out"}, "2026-09-16T00:00:00Z")
        self.assertEqual(record["supplementary"]["fetch_error"], "timed out")
        self.assertEqual(record["supplementary"]["publications"], [])
        self.assertEqual(record["supplementary"]["documents"], [])

    def test_missing_supplementary_defaults_empty(self):
        raw = make_study("NCT00000014")
        record = fcl.build_trial_record(raw, None, "2026-09-16T00:00:00Z")
        self.assertEqual(record["supplementary"]["publications"], [])
        self.assertEqual(record["supplementary"]["documents"], [])


class ExtractDrugsTest(unittest.TestCase):
    def test_dedupes_case_insensitively_keeps_first_seen_casing(self):
        records = [
            fcl.build_trial_record(
                make_study("NCT1", interventions=[{"type": "DRUG", "name": "Examplemab", "description": None}]),
                None, "t",
            ),
            fcl.build_trial_record(
                make_study("NCT2", interventions=[{"type": "DRUG", "name": "examplemab", "description": None}]),
                None, "t",
            ),
        ]
        drugs = fcl.extract_drugs(records)
        self.assertEqual(len(drugs), 1)
        self.assertEqual(drugs[0]["name"], "Examplemab")
        self.assertEqual(drugs[0]["trial_count"], 2)
        self.assertEqual(drugs[0]["nct_ids"], ["NCT1", "NCT2"])

    def test_excludes_non_drug_intervention_types(self):
        records = [
            fcl.build_trial_record(
                make_study("NCT1", interventions=[
                    {"type": "DEVICE", "name": "Laser", "description": None},
                    {"type": "PROCEDURE", "name": "Biopsy", "description": None},
                ]),
                None, "t",
            ),
        ]
        drugs = fcl.extract_drugs(records)
        self.assertEqual(drugs, [])

    def test_includes_biological_type(self):
        records = [
            fcl.build_trial_record(
                make_study("NCT1", interventions=[{"type": "BIOLOGICAL", "name": "Some mAb", "description": None}]),
                None, "t",
            ),
        ]
        drugs = fcl.extract_drugs(records)
        self.assertEqual([d["name"] for d in drugs], ["Some mAb"])

    def test_sorted_by_name(self):
        records = [
            fcl.build_trial_record(
                make_study("NCT1", interventions=[
                    {"type": "DRUG", "name": "Zetamab", "description": None},
                    {"type": "DRUG", "name": "Alphamab", "description": None},
                ]),
                None, "t",
            ),
        ]
        drugs = fcl.extract_drugs(records)
        self.assertEqual([d["name"] for d in drugs], ["Alphamab", "Zetamab"])


class StatusBreakdownTest(unittest.TestCase):
    def test_counts_every_status_value(self):
        records = [
            fcl.build_trial_record(make_study("NCT1", overall_status="RECRUITING"), None, "t"),
            fcl.build_trial_record(make_study("NCT2", overall_status="RECRUITING"), None, "t"),
            fcl.build_trial_record(make_study("NCT3", overall_status="TERMINATED"), None, "t"),
            fcl.build_trial_record(make_study("NCT4", overall_status="WITHDRAWN"), None, "t"),
        ]
        breakdown = fcl.status_breakdown(records)
        self.assertEqual(breakdown["RECRUITING"], 2)
        self.assertEqual(breakdown["TERMINATED"], 1)
        self.assertEqual(breakdown["WITHDRAWN"], 1)
        self.assertEqual(sum(breakdown.values()), 4)


class DownloadProtocolDocsTest(unittest.TestCase):
    def _record_with_doc(self, nct_id="NCT00000099"):
        raw = make_study(nct_id)
        supplementary = {
            "documentSection": {
                "largeDocumentModule": {
                    "largeDocs": [
                        {"typeAbbrev": "Prot", "hasProtocol": True, "hasSap": False, "hasIcf": False,
                         "label": "Study Protocol", "date": "2020-01-01", "filename": "Prot_000.pdf", "size": 100},
                        {"typeAbbrev": "SAP", "hasProtocol": False, "hasSap": True, "hasIcf": False,
                         "label": "SAP", "date": "2020-02-01", "filename": "SAP_001.pdf", "size": 100},
                    ]
                }
            }
        }
        return fcl.build_trial_record(raw, supplementary, "t")

    def test_respects_budget_cap_across_documents(self):
        record = self._record_with_doc()
        budget = [1]  # only 1 of the 2 documents should download
        with patch.object(fcl.urllib.request, "urlretrieve") as mock_retrieve, \
             patch.object(fcl.shutil, "which", return_value=None), \
             patch.object(fcl.time, "sleep"), \
             patch.object(Path, "exists", return_value=False), \
             patch.object(Path, "mkdir"):
            fcl.download_protocol_docs(record, Path("/tmp/does-not-matter/documents"), budget, sleep=0)
        self.assertEqual(mock_retrieve.call_count, 1)
        self.assertEqual(budget[0], 0)

    def test_zero_budget_downloads_nothing(self):
        record = self._record_with_doc()
        budget = [0]
        with patch.object(fcl.urllib.request, "urlretrieve") as mock_retrieve:
            fcl.download_protocol_docs(record, Path("/tmp/does-not-matter/documents"), budget, sleep=0)
        mock_retrieve.assert_not_called()

    def test_no_documents_is_a_noop(self):
        record = fcl.build_trial_record(make_study("NCT1"), None, "t")
        budget = [5]
        with patch.object(fcl.urllib.request, "urlretrieve") as mock_retrieve:
            fcl.download_protocol_docs(record, Path("/tmp/does-not-matter/documents"), budget, sleep=0)
        mock_retrieve.assert_not_called()
        self.assertEqual(budget[0], 5)

    def test_download_error_recorded_not_raised(self):
        record = self._record_with_doc()
        budget = [5]
        with patch.object(fcl.urllib.request, "urlretrieve", side_effect=OSError("network down")), \
             patch.object(Path, "exists", return_value=False), \
             patch.object(Path, "mkdir"):
            fcl.download_protocol_docs(record, Path("/tmp/does-not-matter/documents"), budget, sleep=0)
        docs = record["supplementary"]["documents"]
        self.assertTrue(all("download_error" in d for d in docs))


class BuildManifestTest(unittest.TestCase):
    def test_manifest_shape(self):
        import argparse
        records = [fcl.build_trial_record(make_study("NCT1", overall_status="COMPLETED"), None, "t")]
        drugs = fcl.extract_drugs(records)
        args = argparse.Namespace(
            page_size=1000, max_trials=None, skip_supplementary=False,
            fetch_protocol_pdfs=False, max_protocol_pdfs=25,
        )
        manifest = fcl.build_manifest("Psoriasis", "psoriasis", records, drugs, "2026-09-16T00:00:00Z", args)
        self.assertEqual(manifest["condition"], "Psoriasis")
        self.assertEqual(manifest["condition_slug"], "psoriasis")
        self.assertEqual(manifest["trial_count"], 1)
        self.assertEqual(manifest["status_breakdown"], {"COMPLETED": 1})
        self.assertTrue(manifest["options"]["fetch_publications"])
        self.assertFalse(manifest["options"]["fetch_protocol_pdfs"])


if __name__ == "__main__":
    unittest.main()
