"""Useful computer-only preview on explicit own projects, not camera evidence."""
import contextlib
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
from lutphoto._offlinedemo import create_input


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve(); self.inputs = self.root / 'input'
        create_input(self.inputs)
        self.project = self.inputs / 'demo-project.json'; self.photo = self.inputs / 'chart.png'
        value, _ = nf.read_json(self.project); value['training_samples'] = 512
        self.project.write_bytes(nf.json_bytes(value)); self.directory = self.root / 'preview'

    def run_preview(self, **extra):
        return o.preview(self.directory, project=self.project, photo=self.photo, st_input=True, **extra)

    def args(self):
        return ['preview', '--directory', str(self.directory), '--project', str(self.project),
                '--input', str(self.photo), '--st-input']

    def test_preview_needs_no_program_or_archive_and_preserves_all_source_files(self):
        def sources():
            return {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mode, p.stat().st_mtime_ns)
                    for p in self.inputs.iterdir()}
        before = sources()
        with (patch.object(o.b.p, '_load_policy', side_effect=AssertionError('No archive')),
             patch.object(o.b, 'create', side_effect=AssertionError('No bundle')),
             patch.object(o, '_combine', side_effect=AssertionError('No device contracts'))):
            result = self.run_preview()
        self.assertEqual(sources(), before); self.assertTrue(result['offline_thresholds_passed'])
        self.assertEqual(result['phase'], 'OFFLINE_PREVIEW_CHECKED')
        self.assertFalse(result['program_policy_or_bundle_used']); self.assertFalse(result['actual_camera_accuracy_verified'])
        for key in o.program.w.boundary(): self.assertFalse(result[key], key)
        self.assertEqual(set(p.name for p in self.directory.iterdir()), {'candidate', 'evaluation', 'RESULT.md', 'preview.private.json'})
        self.assertEqual(len((self.directory / 'candidate/correction.table').read_bytes()), 1215)
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.directory / 'preview.private.json').stat().st_mode & 0o777, 0o600)

    def test_exceeded_limits_keep_diagnostics_but_exit_one_and_cannot_be_imported(self):
        project, _ = nf.read_json(self.project); project['source']['path'] = 'swap-rb-17.cube'
        project['thresholds']['max_rgb_mae'] = 1e-15; self.project.write_bytes(nf.json_bytes(project))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = o.main(self.args())
        self.assertEqual(code, 1); self.assertEqual(json.loads(out.getvalue())['phase'], 'OFFLINE_PREVIEW_LIMITS_EXCEEDED')
        result = json.loads((self.directory / 'preview.private.json').read_bytes())
        self.assertFalse(result['offline_thresholds_passed']); self.assertTrue(result['failed_criteria'])
        self.assertTrue(all(v['actual'] > v['limit'] for v in result['failed_criteria']))
        self.assertIn('超限', (self.directory / 'RESULT.md').read_text())
        self.assertFalse((self.directory / 'bundle').exists())
        with self.assertRaises(ValueError):
            o.b.m._candidate_bytes((self.directory / 'candidate/candidate.json').read_bytes(),
                                   (self.directory / 'candidate/correction.table').read_bytes(), nf.UPSTREAM)

    def test_ST_declaration_is_required_before_any_input_or_output(self):
        with patch.object(nf, 'fit') as fitting, self.assertRaises(ValueError):
            o.preview(self.directory, project=self.project, photo=self.photo, st_input=False)
        fitting.assert_not_called(); self.assertFalse(self.directory.exists())
        with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(o.main(self.args()[:-1]), 2)

    def test_changed_calibration_after_render_refuses_final_report(self):
        binding = o._reference_binding
        def changed(*args, **kwargs):
            path = self.inputs / 'synthetic-model.json'; value, _ = nf.read_json(path)
            value['evidence'] = 'Modified own model after rendering'; path.write_bytes(nf.json_bytes(value))
            return binding(*args, **kwargs)
        with patch.object(o, '_reference_binding', side_effect=changed), self.assertRaises(ValueError):
            self.run_preview()
        self.assertFalse((self.directory / 'preview.private.json').exists())
        self.assertTrue((self.directory / 'evaluation/reference.png').exists())

    def test_table_or_candidate_changed_after_render_is_not_combined(self):
        binding = o._reference_binding
        for name in ('correction.table', 'candidate.json'):
            self.directory = self.root / name.replace('.', '-')
            def changed(*args, **kwargs):
                path = self.directory / 'candidate' / name; raw = path.read_bytes()
                path.write_bytes((bytes([raw[0] ^ 1]) + raw[1:]) if name.endswith('table') else raw + b' ')
                return binding(*args, **kwargs)
            with patch.object(o, '_reference_binding', side_effect=changed), self.assertRaises(ValueError):
                self.run_preview()
            self.assertFalse((self.directory / 'RESULT.md').exists())

    def test_explicit_region_metrics_and_missing_regions_are_distinct(self):
        from PIL import Image
        mask = self.inputs / 'gray.png'; Image.new('L', (768, 256), 255).save(mask)
        spec = self.inputs / 'masks.json'; spec.write_bytes(nf.json_bytes({'schema': 'a7c2-offline-region-masks/1', 'regions': {'gray': 'gray.png'}}))
        result = self.run_preview(masks=spec); regions = result['fit']['image_comparison']['regions']
        self.assertTrue(regions['gray']['available']); self.assertGreater(regions['gray']['pixels'], 0)
        self.assertFalse(regions['skin']['available']); self.assertNotIn('rgb_mae', regions['skin'])
        self.assertIn('缺少有效显式掩码', (self.directory / 'RESULT.md').read_text())

    def test_unsupported_input_domain_without_bridge_stops_without_fake_conversion(self):
        project, _ = nf.read_json(self.project); project['source']['input_space'] = 'unbridged-log-domain'
        self.project.write_bytes(nf.json_bytes(project))
        with self.assertRaises(ValueError): self.run_preview()
        self.assertFalse((self.directory / 'preview.private.json').exists())
        self.assertFalse((self.directory / 'candidate').exists())

    def test_real_child_cli_has_no_sdk_compiler_or_private_path_output(self):
        script = '''import sys
from lutphoto import offline
code=offline.main(sys.argv[1:])
assert not any(n=='usb' or n.startswith('usb.') or n in ('libusb_package','ziglang','elftools','macfl23.session') for n in sys.modules)
raise SystemExit(code)
'''
        run = subprocess.run([sys.executable, '-B', '-c', script, *self.args()], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(set(json.loads(run.stdout)), {'schema', 'phase', 'offline_thresholds_passed', 'device_operations_enabled'})
        self.assertNotIn(str(self.root), run.stdout + run.stderr)

    def test_help_is_standard_library_only_and_no_program_or_enable_flags_exist(self):
        script = "import sys; from lutphoto import offline; assert 'numpy' not in sys.modules; offline.main(['preview','--help'])"
        run = subprocess.run([sys.executable, '-S', '-B', '-c', script], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        for flag in ('--archive', '--ap', '--enable', '--resume'):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(o.main(self.args() + [flag, str(self.root)]), 2)
            self.assertNotIn(str(self.root), err.getvalue())

    def test_existing_output_and_unsafe_parent_refuse_before_fitting(self):
        self.directory.mkdir(mode=0o700); keep = self.directory / 'keep'; keep.write_bytes(b'own')
        with patch.object(nf, 'fit') as fit, self.assertRaises(ValueError): self.run_preview()
        fit.assert_not_called(); self.assertEqual(keep.read_bytes(), b'own')
        self.directory = self.root / 'other'; self.root.chmod(0o755)
        with patch.object(nf, 'fit') as fit, self.assertRaises(ValueError): self.run_preview()
        fit.assert_not_called()

    def test_stdout_failure_does_not_repeat_preview_or_claim_success(self):
        class Short(io.StringIO):
            def write(self, text): return 0
        result = {'schema': 'own', 'phase': 'OFFLINE_PREVIEW_CHECKED', 'offline_thresholds_passed': True, 'device_operations_enabled': False}
        with patch.object(o, 'preview', return_value=result) as preview, contextlib.redirect_stdout(Short()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(o.main(self.args()), 1)
        preview.assert_called_once()


if __name__ == '__main__': unittest.main()
