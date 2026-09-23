"""Regression tests for evidence/provenance boundaries and the extraction gate."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "scripts" / "extraction"
sys.path.insert(0, str(HERE))

import assemble
import spans
import verify



class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.job = Path(self.tmp.name)
        (self.job / "sources").mkdir()
        self.text = ('# Trial report\nA genuine source sentence with 16 participants. Another sentence.\n\n'
                     'Arm | N | Event count\nActive | 16 | 0\nVehicle | 6 | 1\n'
                     'She said "a long quoted source phrase" and “a curly source phrase”.\n'
                     '<table><tr><td>First HTML row text</td><td>16</td></tr>'
                     '<tr><td>Second HTML row text</td></tr></table>\n'
                     '## Next heading\n* First list item\n* Second list item\n'
                     'A wrapped sentence\ncontinues on another line.\n')
        (self.job / "sources/doc.txt").write_text(self.text)
        (self.job / "sources/other.txt").write_text('Evidence in a different source only.\n')
        self.ct = {"protocolSection": {"statusModule": {
            "overallStatus": "TERMINATED", "whyStopped": "Stopped for business reasons.\nNo safety concern."
        }}, "resultsSection": {"description": "Results exist even for this stopped trial.", "count": 42}}
        self.write("ctgov.json", self.ct)
        self.write("sources.json", {
            "sources/doc.txt": {"url": "https://example.org/doc", "source_type": "publication_extraction"},
            "sources/other.txt": {"url": "https://example.org/other", "source_type": "publication_extraction"},
            "ctgov.json": {"url": "https://clinicaltrials.gov/api/v2/studies/NCT12345678",
                           "source_type": assemble.LEGACY_CT_TYPE}})
        self.write("TASK.json", {"fields": ["identity.official_title"]})
        spans.build(self.job)
        self.index = spans.load(self.job)
        record = next(r for r in self.index.values() if r["text"].startswith("A genuine"))
        self.item = {"value": "A genuine source sentence with 16 participants.", "file_key": "DOC",
                     "span_ids": [record["id"]], "section": "Trial report", "note": "", "confidence": 0.9}
        self.draft = {"fields": {"identity.official_title": self.item}, "trial_mapping": "Single trial test fixture"}

    def write(self, file, value):
        (self.job / file).write_text(json.dumps(value, ensure_ascii=False))

    def run_assembly(self):
        return assemble.assemble(self.job, self.draft)

    def select_field(self, field, value):
        self.write('TASK.json', {'fields': [field]})
        self.item['value'] = value
        self.draft['fields'] = {field: self.item}

    def published_fixture(self):
        key = {'rank': 'primary', 'position': 1, 'verbatim_sha1': 'a' * 40}
        self.write('endpoint_keys.json', [{'key': key, 'verbatim': 'Complete cure at Week 6'}])
        self.write('base.json', {'results': {'arms': {'value': [{'arm_id': 'OG000'}, {'arm_id': 'OG001'}]}}})
        props = verify.SPEC['results.published_results']['items']['properties']
        row = {k: None for k in props}
        row.update(endpoint=key, arm_id='OG000', value_type='count_of_participants',
                   reported_value=0, rate_is_derived=False)
        self.select_field('results.published_results', [row])
        return row

    def dosing_fixture(self, description='Topical application.\nOne application for six hours.'):
        self.ct['protocolSection']['armsInterventionsModule'] = {
            'interventions': [{'name': 'Active drug', 'description': description}]}
        self.write('ctgov.json', self.ct)
        spans.build(self.job)
        props = verify.SPEC['molecule.dosing_regimen']['items']['properties']
        row = {k: [] if v['type'] == 'array' else None for k, v in props.items()}
        row.update(intervention_name='Active drug', description=description, is_placebo=False)
        self.select_field('molecule.dosing_regimen', [row])
        return row

    def test_published_results_accepts_only_label_or_publication(self):
        self.published_fixture()
        sources = spans.read_json(self.job / 'sources.json')
        for source_type in assemble.SOURCE_TYPES - {'needs_extraction'}:
            with self.subTest(source_type=source_type):
                sources['sources/doc.txt']['source_type'] = source_type
                self.write('sources.json', sources)
                report = self.run_assembly()[1]
                if source_type in {'openfda_label', 'publication_extraction'}:
                    self.assertFalse(any(report.values()), report)
                else:
                    self.assertIn('published_results requires', str(report))

    def test_published_results_rejects_registry_string_leaves(self):
        self.published_fixture()
        self.item.update(file_key='CTGOV', span_ids=[r['id'] for r in self.index.values()
                                                  if r['section'] == '$.resultsSection.description'])
        self.assertIn('results.arm_results', str(self.run_assembly()[1]))

    def test_published_endpoint_key_requires_exact_membership(self):
        row = self.published_fixture()
        original = row['endpoint'].copy()
        for part, wrong in [('rank', 'secondary'), ('position', 2), ('verbatim_sha1', 'b' * 40)]:
            with self.subTest(part=part):
                row['endpoint'] = {**original, part: wrong}
                self.assertIn('endpoint_keys.json', str(self.run_assembly()[1]))
        row['endpoint'] = original
        self.assertFalse(any(self.run_assembly()[1].values()))

    def test_published_arm_id_must_be_a_registered_arm(self):
        row = self.published_fixture()
        for wrong in ['Placebo', 'OG002', 'OG000#full_analysis_set']:
            with self.subTest(arm_id=wrong):
                row['arm_id'] = wrong
                self.assertIn('base.json results.arms', str(self.run_assembly()[1]))
        row['arm_id'] = 'OG001'
        self.assertFalse(any(self.run_assembly()[1].values()))

    def test_repeated_endpoint_arm_requires_distinct_nonblank_titles(self):
        row = self.published_fixture()
        other = {**row, 'ctgov_class_title': 'Effective treatment'}
        self.item['value'].append(other)
        for title in [None, '', '  ', 'Effective treatment', ' effective   TREATMENT ']:
            with self.subTest(title=title):
                row['ctgov_class_title'] = title
                self.assertIn('distinguishing', str(self.run_assembly()[1]))
        row['ctgov_class_title'] = 'Mycological cure'
        self.assertFalse(any(self.run_assembly()[1].values()))

    def test_distinct_endpoint_or_arm_does_not_require_titles(self):
        row = self.published_fixture()
        self.item['value'].append({**row, 'arm_id': 'OG001'})
        self.assertFalse(any(self.run_assembly()[1].values()))
        other_key = {**row['endpoint'], 'position': 2, 'verbatim_sha1': 'b' * 40}
        self.write('endpoint_keys.json', [{'key': row['endpoint']}, {'key': other_key}])
        self.item['value'][1] = {**row, 'endpoint': other_key}
        self.assertFalse(any(self.run_assembly()[1].values()))

    def test_dosing_description_is_verbatim_including_whitespace(self):
        row = self.dosing_fixture()
        exact = row['description']
        self.assertFalse(any(self.run_assembly()[1].values()))
        for edited in ['Topical application.', exact.replace('\n', ' '), exact + ' ', '']:
            with self.subTest(edited=edited):
                row['description'] = edited
                self.assertIn('description verbatim', str(self.run_assembly()[1]))

    def test_dosing_missing_description_requires_empty_string(self):
        row = self.dosing_fixture()
        intervention = self.ct['protocolSection']['armsInterventionsModule']['interventions'][0]
        for missing in ['absent', None, '']:
            with self.subTest(missing=missing):
                if missing == 'absent':
                    intervention.pop('description', None)
                else:
                    intervention['description'] = missing
                self.write('ctgov.json', self.ct)
                spans.build(self.job)
                row['description'] = ''
                self.assertFalse(any(self.run_assembly()[1].values()))
                row['description'] = 'An invented description'
                self.assertIn('description verbatim', str(self.run_assembly()[1]))

    def test_dosing_intervention_name_requires_unique_exact_match(self):
        row = self.dosing_fixture()
        for name in ['Unknown drug', 'active drug', 'Active drug ']:
            row['intervention_name'] = name
            self.assertIn('match exactly one', str(self.run_assembly()[1]))
        row['intervention_name'] = 'Active drug'
        interventions = self.ct['protocolSection']['armsInterventionsModule']['interventions']
        interventions.append(interventions[0].copy())
        self.write('ctgov.json', self.ct)
        spans.build(self.job)
        self.assertIn('match exactly one', str(self.run_assembly()[1]))

    def test_dosing_checks_every_intervention_by_name_not_position(self):
        row = self.dosing_fixture()
        interventions = self.ct['protocolSection']['armsInterventionsModule']['interventions']
        interventions.append({'name': 'Vehicle', 'description': 'Vehicle description.'})
        self.write('ctgov.json', self.ct)
        spans.build(self.job)
        vehicle = {**row, 'intervention_name': 'Vehicle', 'description': 'Vehicle description.',
                   'is_placebo': True}
        self.item['value'] = [vehicle, row]
        self.assertFalse(any(self.run_assembly()[1].values()))
        row['description'] = 'Vehicle description.'
        self.assertIn('value[1].description', str(self.run_assembly()[1]))

    def test_boolean_warnings_include_true_false_and_nested_paths_only(self):
        value = {'identity': {'flag': False}, 'nested': [True, None, 0, 1, 'false', {'flag': False}]}
        warnings = list(assemble.boolean_warnings(value))
        self.assertEqual(len(warnings), 3)
        for warning, path in zip(warnings, ['value.identity.flag=false', 'value.nested[0]=true',
                                          'value.nested[5].flag=false']):
            self.assertIn(path, warning)
            self.assertIn('requires evidence', warning)
        self.assertIn('value=false', list(assemble.boolean_warnings(False))[0])
        self.assertEqual(list(assemble.boolean_warnings(None)), [])

    def test_boolean_assertions_are_warnings_in_cli_pass_table(self):
        row = self.published_fixture()
        for flag in [True, False]:
            with self.subTest(flag=flag):
                row['rate_is_derived'] = flag
                patch, report, warnings = self.run_assembly()
                self.assertFalse(any(report.values()))
                self.assertIn('boolean assertion', str(warnings))
                self.write('draft.json', self.draft)
                result = subprocess.run([sys.executable, str(HERE / 'assemble.py'), str(self.job)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertRegex(result.stdout, r'PASS\s+results.published_results')
                self.assertIn(f'value[0].rate_is_derived={str(flag).lower()}', result.stdout)
                self.assertIn('WARNING', result.stdout)

    def test_one_file_can_supply_separate_narrative_and_table_spans(self):
        row = self.published_fixture()
        row.update(denominator=16, responders=0, response_rate_pct=0)
        selected = [r for r in self.index.values() if r['file'] == 'sources/doc.txt'
                    and (r['text'].startswith('A genuine') or r['text'] in
                         ['Arm | N | Event count', 'Active | 16 | 0'])]
        self.item['span_ids'] = [r['id'] for r in selected]
        patch, report, _ = self.run_assembly()
        self.assertFalse(any(report.values()))
        excerpt = patch['fields']['results.published_results']['source_excerpt']
        for record in selected:
            self.assertIn('"' + record['text'] + '"', excerpt)
        self.item['span_ids'].append('OTHER:0001')
        self.assertIn('one source per field', str(self.run_assembly()[1]))

    def test_new_guard_failure_preserves_existing_patch(self):
        row = self.published_fixture()
        self.write('draft.json', self.draft)
        command = [sys.executable, str(HERE / 'assemble.py'), str(self.job)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        original = (self.job / 'patch.json').read_bytes()
        row['endpoint']['position'] = 99
        self.write('draft.json', self.draft)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('endpoint_keys.json', result.stdout)
        self.assertEqual(original, (self.job / 'patch.json').read_bytes())

    def test_all_candidates_are_substrings_of_individual_source_lines(self):
        leaves = dict(spans.string_leaves(self.ct))
        for record in self.index.values():
            if record["file"] == "ctgov.json":
                source = leaves[record["section"].split(" / ")[0]]
            else:
                source = (self.job / record["file"]).read_text()
            line = source.splitlines()[record["line"] - 1]
            self.assertIn(record["text"], spans.collapse(line))
            self.assertFalse(any(spans.is_double_quote(c) for c in record["text"]))

    def test_boundaries_and_decimals(self):
        texts = [r["text"] for r in self.index.values()]
        for text in ['# Trial report', 'Another sentence.', 'Active | 16 | 0',
                     'Vehicle | 6 | 1', 'First HTML row text', 'Second HTML row text',
                     '* First list item', '* Second list item', 'A wrapped sentence']:
            self.assertIn(text, texts)
        self.assertEqual(list(spans.sentences('Dose 2.5 mg. Next.')), ['Dose 2.5 mg.', 'Next.'])
        self.assertEqual(list(spans.fragments('Dose < 10 mg and > 2 mg.')), ['Dose < 10 mg and > 2 mg.'])

    def test_build_is_byte_stable(self):
        before = {p.name: p.read_bytes() for p in (self.job / 'spans').glob('*.jsonl')}
        spans.build(self.job)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.job / 'spans').glob('*.jsonl')})

    def test_json_paths_and_results_are_indexed_but_numeric_leaves_are_not(self):
        records = [r for r in self.index.values() if r['file'] == 'ctgov.json']
        self.assertTrue(any(r['section'] == '$.resultsSection.description' for r in records))
        self.assertFalse(any(r['text'] == '42' for r in records))

    def test_provenance_and_verifier(self):
        patch, report, warnings = self.run_assembly()
        self.assertFalse(any(report.values()))
        value = patch['fields']['identity.official_title']
        self.assertEqual(value['source_url'], 'https://example.org/doc')
        self.assertEqual(value['source_type'], 'publication_extraction')
        self.assertIsNone(value['reviewed_by'])
        self.assertEqual(value['extracted_by'], assemble.EXTRACTED_BY)
        self.assertEqual(verify.check(self.job, patch), {'identity.official_title': []})

    def test_note_and_section_cannot_introduce_quotes(self):
        self.item['section'] = '“Invented section words here”'
        self.item['note'] = '"invented connective words" ＂more invented words＂'
        patch, report, _ = self.run_assembly()
        self.assertFalse(any(report.values()))
        excerpt = patch['fields']['identity.official_title']['source_excerpt']
        self.assertEqual(verify.quotes(excerpt), [self.index[self.item['span_ids'][0]]['text']])

    def test_embedded_source_quotes_do_not_create_connective_quotes(self):
        self.item['span_ids'] = [r['id'] for r in self.index.values()
                                 if r['file'] == 'sources/doc.txt' and r['line'] == 7]
        patch, report, _ = self.run_assembly()
        self.assertFalse(any(report.values()))
        self.assertEqual(verify.check(self.job, patch), {'identity.official_title': []})

    def test_unknown_and_cross_file_ids_fail(self):
        for ids in [['DOC:9999'], ['OTHER:0001'], [self.item['span_ids'][0], 'OTHER:0001']]:
            with self.subTest(ids=ids):
                self.item['span_ids'] = ids
                self.assertTrue(any(self.run_assembly()[1].values()))

    def test_stale_and_tampered_span_files_fail(self):
        path = self.job / 'spans/DOC.jsonl'
        original = path.read_text()
        path.write_text(original.replace('A genuine', 'A forged'))
        with self.assertRaisesRegex(ValueError, 'stale or altered'):
            self.run_assembly()
        path.write_text(original)
        (self.job / 'sources/doc.txt').write_text(self.text + 'Additional source evidence.\n')
        with self.assertRaisesRegex(ValueError, 'stale or altered'):
            self.run_assembly()

    def test_closed_enum_rejects_invented_value(self):
        self.write('TASK.json', {'fields': ['identity.overall_status']})
        self.draft['fields'] = {'identity.overall_status': self.item}
        self.item['value'] = 'PAUSED'
        self.assertIn('not in', str(self.run_assembly()[1]))

    def test_required_integer_cannot_be_null(self):
        field = 'endpoints.multiplicity_control'
        self.write('TASK.json', {'fields': [field]})
        self.item['value'] = {k: None if v.get('nullable') else [] if v['type'] == 'array'
                              else False if v['type'] == 'boolean' else 2
                              for k, v in verify.SPEC[field]['properties'].items()}
        self.item['value']['alpha_sided'] = None
        self.draft['fields'] = {field: self.item}
        self.assertIn('alpha_sided: null not allowed', str(self.run_assembly()[1]))

    def test_missing_typed_object_keys_fail(self):
        field = 'design.background_therapy'
        self.write('TASK.json', {'fields': [field]})
        self.item['value'] = {'regimen_type': 'monotherapy'}
        self.draft['fields'] = {field: self.item}
        self.assertIn('missing', str(self.run_assembly()[1]))

    def test_invalid_source_type_and_missing_manifest_fail(self):
        source = spans.read_json(self.job / 'sources.json')
        source['sources/doc.txt']['source_type'] = 'made_up'
        self.write('sources.json', source)
        self.assertIn('source_type', str(self.run_assembly()[1]))
        del source['sources/doc.txt']
        self.write('sources.json', source)
        self.assertIn('missing from sources.json', str(self.run_assembly()[1]))

    def test_draft_cannot_type_url_or_quotes(self):
        for key in ['source_url', 'source_type', 'source_excerpt', 'reviewed_by']:
            self.item[key] = 'forged'
            self.assertIn('draft keys', str(self.run_assembly()[1]))
            del self.item[key]

    def test_bad_confidence(self):
        for confidence in [None, True, 1, -0.1, float('nan'), float('inf')]:
            self.item['confidence'] = confidence
            self.assertIn('confidence', str(self.run_assembly()[1]))

    def test_numeric_warning_is_literal_and_recursive(self):
        records = [{'text': '16 people, 0.5 mg, 2.0 weeks, and 0 events.'}]
        self.assertEqual(assemble.numeric_warnings({'a': [16, 0.5, 2.0, 0, False]}, records), [])
        warnings = assemble.numeric_warnings({'a': [6, 5, 2, 999]}, records)
        self.assertEqual(len(warnings), 4)
        self.assertIn('value.a[0]=6', warnings[0])

    def test_complete_task_coverage_and_partial_mode(self):
        self.write('TASK.json', {'fields': ['identity.official_title', 'identity.sponsor']})
        self.assertIn('missing from draft', str(self.run_assembly()[1]))
        self.assertFalse(any(assemble.assemble(self.job, self.draft, partial=True)[1].values()))
        self.draft['fields']['identity.sponsor'] = {'not_found': 'Not present in supplied test sources'}
        patch, report, _ = self.run_assembly()
        self.assertFalse(any(report.values()))
        self.assertEqual(set(patch['not_found']), {'identity.sponsor'})

    def test_not_found_reason_and_unrequested_field(self):
        self.draft['fields']['identity.official_title'] = {'not_found': ''}
        self.assertIn('nonempty', str(self.run_assembly()[1]))
        self.draft['fields']['identity.sponsor'] = {'not_found': 'Unrequested'}
        self.assertIn('not requested', str(self.run_assembly()[1]))

    def test_why_stopped_is_verbatim_for_all_stopped_statuses(self):
        field = 'identity.why_stopped'
        self.write('TASK.json', {'fields': [field]})
        self.item.update(value=self.ct['protocolSection']['statusModule']['whyStopped'], file_key='CTGOV',
                         span_ids=[r['id'] for r in self.index.values() if 'whyStopped' in r['section']])
        self.draft['fields'] = {field: self.item}
        for status in ['TERMINATED', 'WITHDRAWN', 'SUSPENDED']:
            self.ct['protocolSection']['statusModule']['overallStatus'] = status
            self.write('ctgov.json', self.ct)
            spans.build(self.job)
            patch, report, _ = self.run_assembly()
            self.assertFalse(any(report.values()))
            self.assertEqual(patch['fields'][field]['value'], self.item['value'])
            self.assertEqual(patch['fields'][field]['source_type'], 'ctgov_text_extraction')
        self.item['value'] = 'A paraphrased stopping reason.'
        self.assertIn('verbatim', str(self.run_assembly()[1]))

    def test_short_evidence_fails_honestly(self):
        self.item['span_ids'] = [r['id'] for r in self.index.values() if r['text'] == '16']
        self.assertIn('minimum 12', str(self.run_assembly()[1]))

    def test_strict_json(self):
        for text in ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}']:
            (self.job / 'bad.json').write_text(text)
            with self.assertRaises(ValueError):
                spans.read_json(self.job / 'bad.json')

    def test_cli_writes_only_after_success_and_search_handles_bad_regex(self):
        self.write('draft.json', self.draft)
        command = [sys.executable, str(HERE / 'assemble.py'), str(self.job)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        original = (self.job / 'patch.json').read_bytes()
        self.item['confidence'] = 1
        self.write('draft.json', self.draft)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAIL', result.stdout)
        self.assertEqual(original, (self.job / 'patch.json').read_bytes())
        command = [sys.executable, str(HERE / 'spans.py'), 'search', str(self.job)]
        result = subprocess.run(command + ['whyStopped'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CTGOV:', result.stdout)
        result = subprocess.run(command + ['['], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
