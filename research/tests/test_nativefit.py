"""Independent native-table expectations and offline adapter failure boundaries."""
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

import numpy as np
from PIL import Image

from lutphoto._vendor.sonylooks import native
from lutphoto.native_metrics import compare, lab_d65
from lutphoto.nativefit import (MAX_JSON, evaluate_photo, fit, fixtures, json_bytes,
                               load_candidate, load_project, main, publish, read_json)


class NativeMathTests(unittest.TestCase):
    def test_plane_order_signed_range_and_length(self):
        coefficients = np.zeros((405, 3), dtype=int)
        coefficients[0] = [-64, 1, 63]
        coefficients[-1] = [12, -13, 14]
        raw = native.encode(coefficients)
        self.assertEqual(len(raw), 1215)
        self.assertEqual([raw[i] for i in (0, 404, 405, 809, 810, 1214)],
                         [192, 12, 1, 243, 63, 14])
        np.testing.assert_array_equal(native.decode(raw), coefficients)
        for bad in (b'', raw+b'\0', b'\x80'+raw[1:], b'\x40'+raw[1:]):
            with self.subTest(bad=bad[:1]), self.assertRaises(ValueError):
                native.decode(bad)

    def test_constant_planes_have_known_rgb_offset_and_clip(self):
        source = np.array([[.5, .6, .7], [0, 1, .5]])
        coefficients = np.tile([8, -16, 32], (405, 1))
        expected = np.array([[.53125, .5375, .825], [.03125, .9375, .625]])
        np.testing.assert_allclose(native.predict(source, coefficients, np.eye(3)), expected, atol=1e-15)
        np.testing.assert_array_equal(native.predict([[1, 0, 1]], coefficients, np.eye(3)), [[1, 0, 1]])

    def test_luma_lattice_linear_ramp_has_independent_expectation(self):
        source = np.repeat(np.array([[128/255]]), 3, axis=1)
        coefficients = np.zeros((405, 3), dtype=int)
        coefficients[:, 0] = np.repeat(np.arange(5)*8, 81)
        expected = source.copy()
        expected[0, 0] += ((128-16)/219*4)*8/256
        np.testing.assert_allclose(native.predict(source, coefficients, np.eye(3)), expected, atol=1e-15)

    def test_representable_constant_fit_recovers_transform(self):
        render = lambda x: np.clip(x+np.array([8, -4, 12])/256, 0, 1)
        raw, report = native.fit_reference(render, np.eye(3), count=512, seed=901)
        coefficients = native.decode(raw)
        self.assertLess(report['synthetic_holdout']['rgb_mae'], .0005)
        np.testing.assert_array_equal(np.median(coefficients, axis=0), [8, -4, 12])
        self.assertFalse(report['actual_camera_accuracy_verified'])

    def test_lab_d65_known_black_white_red_and_distance(self):
        actual = lab_d65([[0, 0, 0], [1, 1, 1], [1, 0, 0]])
        np.testing.assert_allclose(actual, [[0, 0, 0], [100, 0, 0], [53.2408, 80.0925, 67.2032]], atol=.0001)
        score = compare([[0, 0, 0]], [[1, 1, 1]])
        self.assertAlmostEqual(score['rgb_mae'], 1)
        self.assertAlmostEqual(score['delta_e76_mean'], 100, places=4)
        self.assertEqual(compare([[.1, .2, .3]], [[.1, .2, .3]])['delta_e76_max'], 0)

    def test_vendored_algorithms_are_exact_pinned_bytes(self):
        root = Path(native.__file__).parent
        manifest = json.loads((root/'PROVENANCE.json').read_text())
        for name, meta in manifest['files'].items():
            raw = (root/name).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), meta['sha256'])
            self.assertEqual(len(raw), meta['bytes'])
        self.assertEqual((root/'LICENSE.txt').read_bytes(), Path('docs/UPSTREAM-LICENSE.txt').read_bytes())


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.demo = self.root/'demo'
        fixtures(self.demo)
        self.project_path = self.demo/'project.json'
        self.project = json.loads(self.project_path.read_text())
        self.project['training_samples'] = 512
        self.save_project()

    def save_project(self):
        self.project_path.write_bytes(json_bytes(self.project))

    def fitted(self):
        result = fit(self.project_path, self.root/'fit')
        return self.root/'fit/candidate.json', result

    def test_identity_fit_and_st_photo_evaluation(self):
        candidate, result = self.fitted()
        self.assertTrue(result['acceptance']['passed'])
        self.assertLess(result['synthetic_holdout']['max_channel_error'], 1e-14)
        self.assertEqual((candidate.parent/'correction.table').read_bytes(), b'\0'*1215)
        source = self.demo/'chart.png'
        original = source.read_bytes()
        report = evaluate_photo(self.project_path, candidate, source, self.root/'images', st_input=True)
        self.assertEqual(source.read_bytes(), original)
        self.assertFalse(report['actual_camera_accuracy_verified'])
        self.assertEqual(report['overall']['samples'], 65536)
        self.assertEqual(report['native_clipped_channels_full_image'], 0)
        self.assertFalse(report['regions']['skin']['available'])
        with Image.open(self.root/'images/reference.png') as ref, Image.open(self.root/'images/prediction.png') as pred:
            np.testing.assert_array_equal(np.asarray(ref), np.asarray(pred))
            self.assertIn('icc_profile', pred.info)
            self.assertEqual(len(pred.getexif()), 0)

    def test_unrepresentable_swap_reports_limit_and_failed_threshold(self):
        self.project['source']['path'] = 'swap-rb-17.cube'
        self.save_project()
        _, report = self.fitted()
        self.assertFalse(report['acceptance']['passed'])
        self.assertGreater(report['fitting']['bounded_coefficients'], 0)
        self.assertGreater(report['synthetic_holdout']['rgb_mae'], .02)
        self.assertFalse(report['actual_camera_accuracy_verified'])

    def test_requires_explicit_st_and_separate_srgb_metadata(self):
        candidate, _ = self.fitted()
        with self.assertRaisesRegex(ValueError, 'st-input'):
            evaluate_photo(self.project_path, candidate, self.demo/'chart.png', self.root/'out')
        untagged = self.demo/'untagged.png'
        Image.new('RGB', (4, 4)).save(untagged)
        with self.assertRaises(ValueError):
            evaluate_photo(self.project_path, candidate, untagged, self.root/'out', st_input=True)
        self.assertFalse((self.root/'out').exists())

    def test_bridge_contract_and_render_are_explicit(self):
        self.project['source']['input_space'] = 'linear-srgb'
        self.save_project()
        with self.assertRaisesRegex(ValueError, 'bridge'):
            load_project(self.project_path)
        self.project['source']['bridge'] = {'path': 'swap-rb-17.cube', 'input_space': 'sony-st-srgb',
                                            'output_space': 'linear-srgb', 'evidence': 'Synthetic contract test only'}
        self.save_project()
        reference, meta, *_ = load_project(self.project_path)
        np.testing.assert_allclose(reference([[.2, .3, .4]]), [[.4, .3, .2]], atol=1e-12)
        self.assertIsNotNone(meta['bridge']['sha256'])
        self.project['source']['bridge']['output_space'] = 'wrong-space'
        self.save_project()
        with self.assertRaisesRegex(ValueError, 'bridge'):
            load_project(self.project_path)

    def test_input_domain_rejection_and_explicit_clipping_counts(self):
        cube_path = self.demo/'identity-17.cube'
        raw = cube_path.read_bytes().replace(b'DOMAIN_MIN 0 0 0', b'DOMAIN_MIN 0.1 0.1 0.1')
        cube_path.write_bytes(raw)
        reference, *_ = load_project(self.project_path)
        with self.assertRaisesRegex(ValueError, 'outside'):
            reference([[0, 0, 0]])
        self.project['source']['domain_policy'] = 'clip-and-report'
        self.save_project()
        reference, *_ = load_project(self.project_path)
        np.testing.assert_array_equal(reference([[0, 0, 0], [1, 1, 1]]), [[0, 0, 0], [1, 1, 1]])
        self.assertEqual(reference.clipped_rows, {'bridge_input': 0, 'lut_input': 1})

    def test_changed_source_model_project_and_table_refused(self):
        candidate, _ = self.fitted()
        for name in ('project.json', 'synthetic-model.json', 'identity-17.cube'):
            path = self.demo/name
            original = path.read_bytes()
            path.write_bytes(original+b'\n')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'provenance'):
                load_candidate(self.project_path, candidate)
            path.write_bytes(original)
        table_path = candidate.parent/'correction.table'
        table_path.write_bytes(b'\1'+table_path.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError, 'hash'):
            load_candidate(self.project_path, candidate)

    def test_limits_calibration_thresholds_and_missing_contracts(self):
        invalid = [('seed', True), ('training_samples', 511), ('training_samples', 50001),
                   ('base', 'FL'), ('thresholds', {}),
                   ('thresholds', {'max_rgb_mae': 1e309, 'max_delta_e76_p95': 2})]
        original = self.project.copy()
        for key, value in invalid:
            self.project = {**original, key: value}
            # Deliberately permit infinity for the rejection fixture only.
            self.project_path.write_text(json.dumps(self.project))
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                load_project(self.project_path)
        self.project = original
        self.save_project()
        model_path = self.demo/'synthetic-model.json'
        model = json.loads(model_path.read_text())
        for update in ({'response_matrix': np.zeros((3, 3)).tolist()}, {'evidence': ''},
                       {'coordinate_model': 'verified'}, {'full_camera_characterization': True}):
            model_path.write_bytes(json_bytes({**model, **update}))
            with self.subTest(update=update), self.assertRaises(ValueError):
                load_project(self.project_path)

    def test_non_srgb_output_and_direct_bridge_refused(self):
        for update in ({'output_space': 'log'}, {'bridge': {}}):
            original = self.project['source'].copy()
            self.project['source'].update(update)
            self.save_project()
            with self.assertRaises(ValueError):
                load_project(self.project_path)
            self.project['source'] = original
        self.save_project()
        cube = self.demo/'identity-17.cube'
        cube.write_bytes(cube.read_bytes().replace(b'\n0 0 0\n', b'\n-1 0 0\n', 1))
        with self.assertRaisesRegex(ValueError, 'normalized'):
            load_project(self.project_path)

    def test_existing_directory_and_symlink_are_preserved(self):
        out = self.root/'out'
        out.mkdir()
        sentinel = out/'sentinel'
        sentinel.write_bytes(b'preserve')
        with patch('lutphoto.nativefit.native.fit_reference') as fitter:
            with self.assertRaises(ValueError):
                fit(self.project_path, out)
            fitter.assert_not_called()
        dangling = self.root/'dangling'
        dangling.symlink_to(self.root/'absent')
        with self.assertRaises(ValueError):
            fit(self.project_path, dangling)
        self.assertTrue(dangling.is_symlink())
        self.assertEqual(sentinel.read_bytes(), b'preserve')

    def test_exclusive_publication_cleans_partial_outputs(self):
        def fail(f):
            f.write(b'partial')
            raise OSError('disk failure')
        out = self.root/'out'
        with self.assertRaisesRegex(OSError, 'disk failure'):
            publish(out, {'a': lambda f: f.write(b'one'), 'b': fail})
        self.assertFalse(out.exists())

    def test_region_masks_empty_missing_and_shape_failure(self):
        candidate, _ = self.fitted()
        source = self.demo/'small.png'
        Image.new('RGB', (4, 2), (128, 128, 128)).save(source)
        Image.new('L', (4, 2), 255).save(self.demo/'gray.png')
        Image.new('L', (4, 2), 0).save(self.demo/'skin.png')
        mask_path = self.demo/'masks.json'
        mask_path.write_bytes(json_bytes({'schema': 'a7c2-offline-region-masks/1',
                                         'regions': {'gray': 'gray.png', 'skin': 'skin.png'}}))
        report = evaluate_photo(self.project_path, candidate, source, self.root/'eval',
                                st_input=True, assume_srgb=True, masks_path=mask_path)
        self.assertEqual(report['regions']['gray']['samples'], 8)
        self.assertEqual(report['regions']['skin']['pixels'], 0)
        self.assertFalse(report['regions']['skin']['available'])
        self.assertNotIn('rgb_mae', report['regions']['skin'])
        self.assertFalse(report['regions']['sky']['available'])
        for size, value in (((2, 2), 255), ((4, 2), 127)):
            Image.new('L', size, value).save(self.demo/'gray.png')
            with self.assertRaises(ValueError):
                evaluate_photo(self.project_path, candidate, source, self.root/'bad',
                               st_input=True, assume_srgb=True, masks_path=mask_path)
            self.assertFalse((self.root/'bad').exists())
        Image.new('L', (4, 2), 255).save(self.demo/'gray.png', transparency=255)
        with self.assertRaises(ValueError):
            evaluate_photo(self.project_path, candidate, source, self.root/'bad',
                           st_input=True, assume_srgb=True, masks_path=mask_path)

    def test_json_size_duplicate_and_nonfinite_rejected(self):
        path = self.root/'bad.json'
        for raw in (b'{"a":1,"a":2}', b'{"x":NaN}', b'x'*(MAX_JSON+1), b'[]', b'\xff'):
            path.write_bytes(raw)
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                read_json(path)

    def test_real_cli_and_no_device_imports(self):
        exe = str(Path(sys.executable).absolute())
        commands = [
            ['fit', '--project', str(self.project_path), '--directory', str(self.root/'cli-fit')],
            ['evaluate', '--project', str(self.project_path), '--candidate', str(self.root/'cli-fit/candidate.json'),
             '--input', str(self.demo/'chart.png'), '--directory', str(self.root/'cli-eval'), '--st-input'],
        ]
        for args in commands:
            result = subprocess.run([exe, '-B', '-m', 'lutphoto.nativefit', *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)['actual_camera_accuracy_verified'])
        result = subprocess.run([exe, '-B', '-c',
            "import sys; from lutphoto.nativefit import main; main(['--help'])"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        code = "import sys; import lutphoto.nativefit; assert not any(x.split('.')[0] in ('usb','macfl23','pmca') for x in sys.modules)"
        result = subprocess.run([exe, '-B', '-c', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_controlled_failure_keeps_existing_output(self):
        with contextlib.redirect_stderr(io.StringIO()) as error:
            code = main(['fit', '--project', str(self.project_path), '--directory', str(self.demo)])
        self.assertEqual(code, 1)
        self.assertIn('STOPPED:', error.getvalue())
        self.assertTrue(self.project_path.is_file())

    def test_prediction_png_and_clipping_count_match_known_nonzero_planes(self):
        candidate, _ = self.fitted()
        raw = native.encode(np.tile([32, -16, 8], (405, 1)))
        (candidate.parent/'correction.table').write_bytes(raw)
        metadata = json.loads(candidate.read_text())
        metadata['table']['sha256'] = hashlib.sha256(raw).hexdigest()
        candidate.write_bytes(json_bytes(metadata))
        source = self.demo/'edges.png'
        image = np.array([[[0, 255, 128], [255, 0, 255]]], dtype='uint8')
        Image.fromarray(image).save(source)
        report = evaluate_photo(self.project_path, candidate, source, self.root/'edges',
                                st_input=True, assume_srgb=True)
        self.assertEqual(report['native_clipped_channels_full_image'], 3)
        with Image.open(self.root/'edges/prediction.png') as rendered:
            np.testing.assert_array_equal(np.asarray(rendered), [[[32, 239, 136], [255, 0, 255]]])

    def test_photo_size_bound_and_existing_output_do_not_publish(self):
        candidate, _ = self.fitted()
        with patch('lutphoto.nativefit.MAX_EVAL_PIXELS', 4):
            with self.assertRaisesRegex(ValueError, '4 million'):
                evaluate_photo(self.project_path, candidate, self.demo/'chart.png', self.root/'large', st_input=True)
        self.assertFalse((self.root/'large').exists())
        with self.assertRaisesRegex(ValueError, 'already exists'):
            evaluate_photo(self.project_path, candidate, self.demo/'chart.png', self.demo, st_input=True)

    def test_zero_response_and_extreme_condition_number_are_refused(self):
        for response in (np.zeros((3, 3)), np.diag([1., 1., 1e-8])):
            with self.subTest(response=response.tolist()), self.assertRaises(ValueError):
                native.validate_response(response)


if __name__ == '__main__':
    unittest.main()
