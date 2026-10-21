"""Integrated CLI and binding tests on own bytes; never device/owner materials."""
import contextlib
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lutphoto import offline as o, nativefit as nf
from research.tests import test_slotbundle as fixtures


class OfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name).resolve()
        cls.demo_root = cls.root / 'demo'
        cls.result = o.demo(cls.demo_root)
        fixtures.SlotBundleTests.setUpClass(); cls.addClassCleanup(fixtures.SlotBundleTests.doClassCleanups)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve(); self.directory = self.root / 'output'

    def fixture(self):
        f = fixtures.SlotBundleTests(methodName='runTest'); f.setUp(); self.addCleanup(f.doCleanups)
        nf.fixtures(self.root / 'input')
        project = self.root / 'input/project.json'
        value = json.loads(project.read_text()); value['training_samples'] = 512; project.write_bytes(nf.json_bytes(value))
        kwargs = {k: v for k, v in f.kwargs.items() if k != 'selection_path'}
        kwargs.update(project=project, photo=self.root / 'input/chart.png', st_input=True, slot=1, name='Own Demo')
        return f, kwargs

    def bound(self, fixture):
        stack = fixture.f.bound()
        stack.enter_context(patch.object(o.program, '_sources', return_value=({}, {})))
        return stack

    def test_demo_is_complete_and_explicitly_synthetic_with_no_physical_claims(self):
        r = self.result
        self.assertTrue(r['synthetic_only']); self.assertEqual(r['material_kind'], 'self-generated-demo')
        self.assertEqual(r['bundle']['payload_files'], 150)
        self.assertEqual(r['settings']['settings_contract']['forward']['write_count'], 9)
        self.assertEqual(set(r['selfmade_snapshot_stage_checks']), set(o.settings.STAGES))
        for rows in r['selfmade_snapshot_stage_checks'].values():
            self.assertTrue(all(v['strict_scope_checked'] for v in rows.values()))
        for key in (*o.program.w.boundary(), 'production_program_identity_checked', 'fixed_archive_and_worker_sources_checked',
                    'actual_camera_accuracy_verified', 'actual_snapshot_stages_verified', 'restore_verified', 'compiled_offline'):
            self.assertFalse(r[key], key)
        self.assertFalse(r['settings']['settings_contract']['chain']['executor_enabled'])
        self.assertIn('全部自制', (self.demo_root / 'RESULT.md').read_text())
        self.assertNotEqual((self.demo_root / 'candidate/correction.table').read_bytes(), bytes(1215))
        self.assertNotEqual((self.demo_root / 'input/chart.png').read_bytes(), (self.demo_root / 'evaluation/reference.png').read_bytes())

    def test_fit_image_bundle_and_all_three_contracts_are_bound(self):
        r = self.result; candidate = (self.demo_root / 'candidate/candidate.json').read_bytes()
        self.assertEqual(r['fit']['candidate_sha256'], nf.digest(candidate))
        self.assertEqual(r['fit']['candidate_sha256'], r['fit']['image_comparison']['candidate_sha256'])
        chain = r['settings']['settings_contract']['chain']
        for key, prefix in (('program_contract_sha256', 'program_worker'), ('names_contract_sha256', 'name_worker')):
            self.assertEqual(chain[key], r[prefix]['contract_sha256'])
        self.assertEqual(chain['source_programs']['AP'], r['name_worker']['names_contract']['AP'])
        self.assertEqual(chain['target_programs']['AP'], r['name_worker']['names_contract']['target_AP'])
        for key in ('bundle_manifest_sha256', 'target_review_sha256'):
            self.assertTrue(all(r[name][key] == r[key] for name in ('program_worker', 'name_worker', 'settings')))

    def test_demo_cli_in_fresh_process_has_bounded_summary_and_no_sdk_or_compiler(self):
        script = '''import sys
from lutphoto import offline
rc=offline.main(sys.argv[1:])
assert not any(n == 'usb' or n.startswith('usb.') or n in ('transport','core','macfl23.session','ziglang') for n in sys.modules)
raise SystemExit(rc)
'''
        run = subprocess.run([sys.executable, '-B', '-c', script, 'demo', '--directory', str(self.directory)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(set(result), {'schema', 'phase', 'synthetic_only', 'device_operations_enabled'})
        self.assertNotIn(str(self.root), run.stdout + run.stderr)
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.directory / 'result.private.json').stat().st_mode & 0o777, 0o600)

    def test_demo_never_loads_archive_or_accepts_external_programs(self):
        with patch.object(o.b.p, '_load_policy', side_effect=AssertionError('No real policy in demo')):
            self.assertTrue(o.demo(self.directory)['synthetic_only'])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(o.main(['demo', '--directory', str(self.root / 'other'), '--ap', 'private']), 2)

    def test_synthetic_bundle_is_rejected_by_production_manifest_policy(self):
        from lutphoto._offlinedemo import materials
        policy, _, _ = materials((self.demo_root / 'candidate/candidate.json').read_bytes(), bytes(1215))
        real_source_hash = replace(policy, archive_sha='01' * 32)
        with patch.object(o.b.p, '_load_policy', return_value=real_source_hash), self.assertRaises(ValueError):
            o.b.inspect_directory('pinned', self.demo_root / 'bundle')

    def test_build_runs_real_fit_and_original_generator_under_test_only_fixture_policy(self):
        f, kwargs = self.fixture()
        def original_files():
            return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mode, p.stat().st_mtime_ns)
                    for p in f.root.rglob('*') if p.is_file()}
        original = original_files()
        with self.bound(f): result = o.build('own', self.directory, **kwargs)
        self.assertEqual(original_files(), original)
        self.assertFalse(result['synthetic_only']); self.assertTrue(result['production_program_identity_checked'])
        self.assertFalse(result['same_capture_provenance_verified']); self.assertEqual(result['selfmade_snapshot_stage_checks'], {})
        self.assertTrue(result['fit']['acceptance']['passed'])
        self.assertEqual((self.directory / 'bundle/source/candidate.json').read_bytes(),
                         (self.directory / 'candidate/candidate.json').read_bytes())
        self.assertFalse(result['device_operations_enabled'])

    def test_unsupported_owner_source_rejects_before_fit_or_output(self):
        f, kwargs = self.fixture(); kwargs['ap_path'].write_bytes(bytes(16384))
        with self.bound(f), patch.object(o, '_fit') as fitting, self.assertRaises(ValueError):
            o.build('own', self.directory, **kwargs)
        fitting.assert_not_called(); self.assertFalse(self.directory.exists())

    def test_build_requires_explicit_st_and_valid_slot_before_reading_private_files(self):
        f, kwargs = self.fixture()
        for changes in ({'st_input': False}, {'slot': True}, {'slot': 7}, {'name': 'bad\0name'}):
            with patch.object(o.b.p, '_load_policy') as policy, self.assertRaises(ValueError):
                o.build('own', self.directory, **{**kwargs, **changes})
            policy.assert_not_called()

    def test_failed_reference_thresholds_preserve_candidate_and_prevent_bundle(self):
        f, kwargs = self.fixture(); project = kwargs['project']; value = json.loads(project.read_text())
        value['source']['path'] = 'swap-rb-17.cube'; value['thresholds']['max_rgb_mae'] = 1e-15
        project.write_bytes(nf.json_bytes(value))
        with self.bound(f), self.assertRaises(ValueError): o.build('own', self.directory, **kwargs)
        self.assertTrue((self.directory / 'candidate/correction.table').is_file())
        self.assertFalse((self.directory / 'bundle').exists()); self.assertFalse((self.directory / 'result.private.json').exists())

    def test_fit_binding_refuses_changed_project_photo_and_unrelated_frozen_candidate(self):
        from lutphoto._offlinedemo import materials
        raw = (self.demo_root / 'candidate/candidate.json').read_bytes()
        _, _, inputs = materials(raw + b' ', bytes(1215))
        with self.assertRaises(ValueError):
            o._fit_binding(self.demo_root, self.demo_root / 'input/demo-project.json', self.demo_root / 'input/chart.png',
                           inputs, self.result['fit']['image_comparison'], None)
        f, kwargs = self.fixture()
        # Mutation before _fit_binding is detected, not trusted from a JSON hash.
        binding = o._fit_binding
        def changed(*args, **options):
            kwargs['photo'].write_bytes(b'changed owner image')
            return binding(*args, **options)
        with self.bound(f), patch.object(o, '_fit_binding', side_effect=changed), self.assertRaises(ValueError):
            o.build('own', self.directory, **kwargs)
        self.assertFalse((self.directory / 'result.private.json').exists())

    def test_final_reader_close_failure_cannot_publish_complete_result(self):
        f, kwargs = self.fixture(); original = o.b.i._Reader.close; closed = []
        def uncertain(reader):
            original(reader); closed.append(True)
            if len(closed) == 2: raise OSError('Unknown final reader close')
        with self.bound(f), patch.object(o.b.i._Reader, 'close', uncertain), self.assertRaises(OSError):
            o.build('own', self.directory, **kwargs)
        self.assertTrue((self.directory / 'bundle').exists()); self.assertFalse((self.directory / 'result.private.json').exists())

    def test_changed_project_calibration_before_final_binding_refuses_success(self):
        f, kwargs = self.fixture(); binding = o._fit_binding
        def changed(*args, **options):
            path = self.root / 'input/synthetic-model.json'
            value = json.loads(path.read_text()); value['evidence'] = 'Changed synthetic calibration'
            path.write_bytes(nf.json_bytes(value))
            return binding(*args, **options)
        with self.bound(f), patch.object(o, '_fit_binding', side_effect=changed), self.assertRaises(ValueError):
            o.build('own', self.directory, **kwargs)
        self.assertFalse((self.directory / 'result.private.json').exists())

    def test_rehashed_target_tamper_after_creation_is_rejected_by_final_reader(self):
        f, kwargs = self.fixture(); create = o.b.create
        def changed(*args, **options):
            result = create(*args, **options); directory = self.directory / 'bundle'
            relative = 'evidence/target-appFw.so'; path = directory / relative
            raw = path.read_bytes(); raw = bytes([raw[0] ^ 1]) + raw[1:]; path.write_bytes(raw)
            manifest = json.loads((directory / o.b.MANIFEST).read_bytes())
            manifest['files'][relative] = {'bytes': len(raw), 'sha256': nf.digest(raw)}
            (directory / o.b.MANIFEST).write_bytes(o.encoded(manifest))
            return result
        with self.bound(f), patch.object(o.b, 'create', side_effect=changed), self.assertRaises(ValueError):
            o.build('own', self.directory, **kwargs)
        self.assertFalse((self.directory / 'result.private.json').exists())

    def test_reconstruction_mutation_rejects_before_entering_bundle_consumer(self):
        f, _ = self.fixture(); f.create(); generate = o.b.t._generate; consumed = []
        def changed(*args):
            review = generate(*args)
            path = f.directory / 'evidence/forward.private.json'
            path.write_bytes(path.read_bytes() + b' ')
            return review
        with f.f.bound(), patch.object(o.b.t, '_generate', side_effect=changed), self.assertRaises(ValueError):
            with o.b._open_bundle('own', f.directory): consumed.append(True)
        self.assertEqual(consumed, [])

    def test_missing_optional_fit_dependency_has_bounded_error_without_path(self):
        with patch.object(o, 'demo', side_effect=ImportError(str(self.root))), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(o.main(['demo', '--directory', str(self.directory)]), 1)
        self.assertNotIn(str(self.root), err.getvalue()); self.assertNotIn('Traceback', err.getvalue())

    def test_existing_repository_shared_or_linked_parent_refused_without_overwrite(self):
        self.directory.mkdir(); (self.directory / 'keep').write_bytes(b'own')
        for path in (self.directory, Path(__file__).resolve().parents[2] / 'do-not-create-d3'):
            with self.assertRaises(ValueError): o.demo(path)
        link = self.root / 'link'; link.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)): o.demo(link / 'child')
        self.root.chmod(0o755)
        with self.assertRaises(ValueError): o.demo(self.root / 'shared')
        self.assertEqual((self.directory / 'keep').read_bytes(), b'own')

    def test_cli_help_is_standard_library_only_and_override_errors_are_private(self):
        script = "import sys; from lutphoto import offline; assert 'numpy' not in sys.modules; raise SystemExit(offline.main(sys.argv[1:]))"
        for arguments in (['--help'], ['demo', '--help'], ['build', '--help']):
            run = subprocess.run([sys.executable, '-S', '-B', '-c', script, *arguments], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
        for flag in ('--policy', '--enable', '--resume', '--firmware'):
            with contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(o.main(['demo', '--directory', str(self.directory), flag, str(self.root)]), 2)
            self.assertNotIn(str(self.root), error.getvalue())

    def test_stdout_failure_is_non_success_and_never_repeats_pipeline(self):
        class Short(io.StringIO):
            def write(self, text): return 0
        with patch.object(o, 'demo', return_value=self.result) as run, contextlib.redirect_stdout(Short()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(o.main(['demo', '--directory', str(self.directory)]), 1)
        run.assert_called_once()


if __name__ == '__main__': unittest.main()
