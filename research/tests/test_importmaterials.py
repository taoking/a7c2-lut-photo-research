"""Own N2 output + program/BK4/UXC fixtures; manifests are not body evidence."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lutphoto import customcontracts as c, importmaterials as m, programidentity as p
from research.tests import test_programidentity as program_fixture
from research.tests import test_settingsbinding as binding_fixture


class ImportMaterialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from lutphoto import nativefit
        cls.generated = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.generated.cleanup)
        root = Path(cls.generated.name); nativefit.fixtures(root / 'demo')
        project = root / 'demo/project.json'; value = json.loads(project.read_text()); value['training_samples'] = 512
        project.write_bytes(nativefit.json_bytes(value))
        nativefit.fit(project, root / 'candidate')
        cls.candidate_files = {f.name: f.read_bytes() for f in (root / 'candidate').iterdir()}

    def setUp(self):
        self.f = binding_fixture.SettingsBindingTests(methodName='runTest'); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.f.policy = replace(self.f.policy, commit=json.loads(self.candidate_files['candidate.json'])['upstream_commit'])
        self.root = self.f.root; self.candidate = self.root / 'candidates' / 'own'; self.candidate.mkdir(parents=True)
        for name, raw in self.candidate_files.items(): (self.candidate / name).write_bytes(raw)
        self.selection_path = self.root / 'selection.json'
        self.selection = {'schema': m.SELECTION, 'slots': {'1': {'candidate': 'candidates/own', 'name': 'Own Film A'},
                                                         '6': {'candidate': 'candidates/own', 'name': 'Own Film F'}}}
        self.save_selection(); self.resources = self.root / 'resources'; self.resources.mkdir()
        self.write_resources(True)

    def save_selection(self): self.selection_path.write_text(json.dumps(self.selection))

    def candidate_json(self): return json.loads((self.candidate / 'candidate.json').read_text())

    def save_candidate(self, value): (self.candidate / 'candidate.json').write_text(json.dumps(value))

    def write_resources(self, imported):
        for name in c.RESOURCE_FILES: (self.resources / name).write_bytes(c.synthetic_resource(imported))

    def check(self):
        with patch.object(p, '_load_policy', return_value=self.f.policy):
            return m.check_files('unused', self.f.ap_path, self.f.cp_path, self.f.ram_path, self.f.saved_path,
                self.selection_path, self.resources, {'AP': 0, 'CP': 1}, {'AP': 0, 'CP': 1})

    def args(self, output):
        return ['--archive', 'unused', '--ap', str(self.f.ap_path), '--cp', str(self.f.cp_path),
                '--ram', str(self.f.ram_path), '--saved', str(self.f.saved_path), '--selection', str(self.selection_path),
                '--resources', str(self.resources), '--ram-roles', '0', '1', '--saved-roles', '0', '1', '--output', str(output)]

    def test_actual_n2_generated_candidate_binds_selected_slots_and_names(self):
        result = self.check()
        self.assertEqual(set(result['slots']), {'1', '6'}); self.assertEqual(result['resources']['resource_files'], 68)
        self.assertEqual(result['binding']['descriptors']['selected_slots'], [1, 6])
        self.assertEqual(result['slots']['1']['table_sha256'], hashlib.sha256(bytes(1215)).hexdigest())
        self.assertEqual(result['slots']['1']['name_utf8_sha256'], hashlib.sha256(b'Own Film A').hexdigest())
        self.assertFalse(result['slots']['1']['project_model_or_fit_revalidated'])

    def test_manifest_is_reproducible_and_selection_name_changes_fingerprint(self):
        before = self.check(); self.assertEqual(before['materials_sha256'], self.check()['materials_sha256'])
        self.selection['slots']['1']['name'] = 'Own Changed'; self.save_selection(); after = self.check()
        self.assertNotEqual(before['materials_sha256'], after['materials_sha256'])
        self.assertEqual(before['binding'], after['binding'])
        self.assertNotEqual(before['resources']['files'], after['resources']['files'])

    def test_shared_candidate_is_one_observed_version_for_both_slots(self):
        with patch.object(m, '_candidate', wraps=m._candidate) as read:
            result = self.check()
        self.assertEqual(read.call_count, 1)
        self.assertEqual(result['slots']['1']['candidate_sha256'], result['slots']['6']['candidate_sha256'])

    def test_first_import_accepts_both_supported_resource_counts_without_source_claim(self):
        for imported, count in ((False, 2860), (True, 2866)):
            self.write_resources(imported); result = self.check()
            self.assertEqual(result['label_layout_derived_from_program'], 'standalone')
            self.assertEqual({r['before_count'] for r in result['resources']['files'].values()}, {count})
            self.assertFalse(result['resource_origin_and_capture_verified'])

    def test_legacy_mapping_is_derived_from_program_and_exact_inverse_is_retained(self):
        own = program_fixture.ProgramIdentityTests(methodName='runTest'); own.setUp(); self.addCleanup(own.doCleanups)
        self.f.ap_path.write_bytes(own.legacy_ap); self.f.cp_path.write_bytes(own.legacy_cp)
        result = self.check(); self.assertEqual(result['label_layout_derived_from_program'], 'legacy-six')
        row = result['resources']['files'][c.RESOURCE_FILES[0]]
        raw = c.synthetic_resource(True)
        target, _ = c.resources.rename(raw, {1: 'Own Film A', 6: 'Own Film F'}, c.LAYOUTS['legacy-six'])
        self.assertEqual(row['after_sha256'], hashlib.sha256(target).hexdigest())
        self.assertEqual(row['restored_sha256'], row['before_sha256']); self.assertTrue(row['exact_inverse_verified'])
        self.write_resources(False)
        with self.assertRaises(ValueError): self.check()

    def test_unknown_program_rejects_before_candidate_or_resources_open(self):
        self.f.ap_path.write_bytes(bytes(16384))
        with patch.object(m, '_candidate') as candidate, patch.object(c, 'resource_directory') as resources:
            with self.assertRaises(ValueError): self.check()
        candidate.assert_not_called(); resources.assert_not_called()

    def test_selection_requires_canonical_slots_and_exact_fields(self):
        for slots in ({}, {'01': self.selection['slots']['1']}, {'7': self.selection['slots']['1']}, [],
                      {'1': {'candidate': 'candidates/own', 'name': 'A', 'sha256': '00' * 32}}):
            self.selection['slots'] = slots; self.save_selection()
            with self.assertRaises(ValueError): m._selection(self.selection_path)
        self.selection_path.write_text('{"schema":"' + m.SELECTION + '","slots":{"1":{},"1":{}}}')
        with self.assertRaises(ValueError): m._selection(self.selection_path)

    def test_selected_name_controls_empty_and_utf8_byte_limit(self):
        for name in ('', 'bad\x00', 'bad\x7f', 'bad\x85', '中' * 22, True):
            self.selection['slots']['1']['name'] = name; self.save_selection()
            with self.assertRaises(ValueError): m._selection(self.selection_path)
        self.selection['slots']['1']['name'] = '中' * 21; self.save_selection()
        self.assertEqual(len(m._selection(self.selection_path)[0][1][1].encode()), 63)

    def test_relative_paths_cannot_escape_or_use_symlink_components(self):
        for value in ('', '.', '..', '../other', '/tmp', 'candidates/../own', 'candidates//own', 'candidates\\own', 1):
            with self.assertRaises(ValueError): m._relative_directory(self.root, value)
        (self.root / 'linked').symlink_to(self.candidate, target_is_directory=True)
        with self.assertRaises(ValueError): m._relative_directory(self.root, 'linked')

    def test_candidate_directory_has_exact_files_and_refuses_links(self):
        extra = self.candidate / 'extra.txt'; extra.write_text('own')
        with self.assertRaises(ValueError): m._candidate(self.candidate, self.f.policy.commit)
        extra.unlink(); table = self.candidate / 'correction.table'; raw = table.read_bytes(); table.unlink()
        linked = self.root / 'own.table'; linked.write_bytes(raw); table.symlink_to(linked)
        with self.assertRaises(OSError): m._candidate(self.candidate, self.f.policy.commit)

    def test_candidate_schema_commit_and_unsupported_device_claims(self):
        original = self.candidate_json()
        for key, value in (('schema', 'unknown'), ('adapter_version', True), ('upstream_commit', 'other'),
                           ('actual_camera_accuracy_verified', True), ('device_integration_enabled', True),
                           ('not_a_firmware_image', False)):
            changed = copy.deepcopy(original); changed[key] = value; self.save_candidate(changed)
            with self.subTest(key=key), self.assertRaises(ValueError): m._candidate(self.candidate, self.f.policy.commit)

    def test_candidate_table_descriptor_cannot_redirect_or_change_layout(self):
        original = self.candidate_json()
        for key, value in (('file', '../private.table'), ('bytes', 1214), ('sha256', 'AA' * 32), ('layout', 'RGB')):
            changed = copy.deepcopy(original); changed['table'][key] = value; self.save_candidate(changed)
            with self.subTest(key=key), self.assertRaises(ValueError): m._candidate(self.candidate, self.f.policy.commit)

    def test_table_length_hash_and_range_even_with_recomputed_hash(self):
        original = self.candidate_json(); table = self.candidate / 'correction.table'
        for raw, reset_hash in ((bytes(1214), True), (bytes(1216), True), (b'\x01' + bytes(1214), False),
                                (b'\x40' + bytes(1214), True), (b'\xbf' + bytes(1214), True)):
            value = copy.deepcopy(original); table.write_bytes(raw)
            if reset_hash: value['table']['sha256'] = hashlib.sha256(raw).hexdigest()
            self.save_candidate(value)
            with self.assertRaises(ValueError): m._candidate(self.candidate, self.f.policy.commit)

    def test_declared_acceptance_must_be_true_consistent_and_finite(self):
        original = self.candidate_json()
        for field, value in (('passed', False), ('scope', 'camera acceptance')):
            changed = copy.deepcopy(original); changed['acceptance'][field] = value; self.save_candidate(changed)
            with self.assertRaises(ValueError): m._candidate(self.candidate, self.f.policy.commit)
        for measured in (True, -1, 2, float('nan'), float('inf'), 10**400):
            changed = copy.deepcopy(original); changed['synthetic_holdout']['rgb_mae'] = measured; self.save_candidate(changed)
            with self.assertRaises(ValueError): m._candidate(self.candidate, self.f.policy.commit)
        changed = copy.deepcopy(original); changed['acceptance']['thresholds_declared_before_holdout']['max_rgb_mae'] = 10**400
        self.save_candidate(changed)
        with self.assertRaises(ValueError): m._candidate(self.candidate, self.f.policy.commit)

    def test_candidate_provenance_hashes_and_optional_lock_are_canonical_claims(self):
        original = self.candidate_json()
        for field in ('project_sha256', 'calibration_sha256', 'reference_sha256'):
            changed = copy.deepcopy(original); changed['provenance'][field] = 'bad'; self.save_candidate(changed)
            with self.assertRaises(ValueError): m._candidate(self.candidate, self.f.policy.commit)
        original['validation_lock_sha256'] = '11' * 32; self.save_candidate(original)
        self.assertFalse(m._candidate(self.candidate, self.f.policy.commit)['validation_lock_revalidated'])

    def test_candidate_other_metadata_paths_are_not_followed_or_reported(self):
        candidate = self.candidate_json(); candidate['provenance']['private_source_path'] = '/do-not-follow/private.cube'
        self.save_candidate(candidate); report = self.check()
        self.assertNotIn('do-not-follow', json.dumps(report))
        self.assertFalse(report['slots']['1']['project_model_or_fit_revalidated'])

    def test_json_fingerprints_use_one_read_and_reject_overflow_exponents(self):
        raw = b'{"own":123}'
        with patch.object(c, 'bounded_read', return_value=raw) as read:
            value, digest = m._json_file('unused')
        self.assertEqual(read.call_count, 1); self.assertEqual(value, {'own': 123})
        self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
        for raw in (b'{"extra":1e999}', b'{"x":NaN}', b'{"x":1,"x":2}', b'[' * 34 + b'0' + b']' * 34):
            with self.assertRaises(ValueError): c.decode_json(raw)

    def test_resource_missing_extra_mixed_or_corrupt_inputs_rejected(self):
        file = self.resources / c.RESOURCE_FILES[0]; raw = file.read_bytes()
        file.unlink()
        with self.assertRaises(ValueError): self.check()
        file.write_bytes(raw); extra = self.resources / 'extra.txt'; extra.write_text('own')
        with self.assertRaises(ValueError): self.check()
        extra.unlink(); file.write_bytes(c.synthetic_resource(False))
        with self.assertRaises(ValueError): self.check()
        file.write_bytes(b'bad')
        with self.assertRaises(ValueError): self.check()

    def test_manifest_contains_no_names_paths_or_payloads_and_keeps_boundaries_false(self):
        result = self.check(); text = json.dumps(result)
        self.assertTrue(result['private_report']); self.assertTrue(result['resource_inverse_checked_in_memory'])
        for key in p.w.boundary(): self.assertFalse(result[key])
        for key in ('resource_origin_and_capture_verified', 'snapshot_freshness_verified', 'same_capture_provenance_verified',
                    'complete_program_transition_verified', 'complete_settings_transition_verified', 'independent_backups_verified',
                    'native_worker_generated', 'camera_deployment_enabled', 'firmware_or_settings_write_plan_enabled'):
            self.assertFalse(result[key])
        for private in (str(self.root), 'Own Film A', 'candidates/own', '02cf0101', 'response_matrix', 'before_ram'):
            self.assertNotIn(private, text)

    def test_api_and_cli_fixture_success_preserve_all_inputs_and_existing_output(self):
        files = [f for f in self.root.rglob('*') if f.is_file()]; before = {f: f.read_bytes() for f in files}
        output = self.root / 'manifest.json'
        with patch.object(p, '_load_policy', return_value=self.f.policy): self.assertEqual(m.main(self.args(output)), 0)
        contents = output.read_bytes()
        with patch.object(m, 'check_files') as check: self.assertEqual(m.main(self.args(output)), 1)
        check.assert_not_called(); self.assertEqual(output.read_bytes(), contents)
        self.assertEqual(before, {f: f.read_bytes() for f in files})
        self.assertEqual(m.main(self.args(self.selection_path)), 1)

    def test_actual_cli_bad_archive_does_not_leak_paths_or_create_report(self):
        bad = self.root / 'private.zip'; bad.write_bytes(b'own corrupt archive')
        output = self.root / 'absent.json'; args = self.args(output); args[1] = str(bad)
        result = subprocess.run([sys.executable, '-S', '-B', '-m', 'lutphoto.importmaterials', *args],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1); self.assertFalse(output.exists())
        self.assertNotIn(str(self.root), result.stdout + result.stderr)
        result = subprocess.run([sys.executable, '-S', '-B', '-m', 'lutphoto.importmaterials', *args, '--layout', 'legacy-six'],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)

    def test_standard_library_import_never_loads_numpy_or_device_modules(self):
        script = "import sys; from lutphoto import importmaterials; assert not any(n.split('.')[0] in {'usb','numpy','macfl23','pmca','looktool','transport'} for n in sys.modules)"
        result = subprocess.run([sys.executable, '-S', '-B', '-c', script], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
