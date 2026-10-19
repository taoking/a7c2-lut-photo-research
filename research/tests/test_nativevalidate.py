"""Patch split isolation and frozen-scene acceptance without camera access."""
import contextlib
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

from lutphoto.nativefit import fit, json_bytes, read_json
from lutphoto.nativevalidate import (assess, benchmark, calibrate, fixtures, freeze,
                                    main, validate_lock)


class CalibrationAndSceneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root/'data'
        fixtures(self.data)
        self.project = self.data/'validation-project.json'
        project, _ = read_json(self.project)
        project['training_samples'] = 512
        self.project.write_bytes(json_bytes(project))
        self.patches = self.data/'patches.json'
        self.manifest = self.data/'scenes.json'
        self.lock = self.root/'validation.lock.json'

    def calibrated(self):
        return calibrate(self.patches, self.data/'calibrated')

    def frozen_fit(self):
        self.calibrated()
        freeze(self.project, self.manifest, self.lock)
        fit(self.project, self.root/'fit', validation_lock=self.lock)
        return self.root/'fit/candidate.json'

    def update(self, path, change):
        data, _ = read_json(path)
        change(data)
        path.write_bytes(json_bytes(data))

    def test_calibration_split_evidence_and_normalized_holdout(self):
        report = self.calibrated()
        model, _ = read_json(self.data/'calibrated/model.json')
        self.assertTrue(report['acceptance']['passed'])
        self.assertLess(report['holdout']['rgb_mae'], .002)
        self.assertEqual(report['split_counts'], {'train': 64, 'holdout': 64})
        self.assertEqual(report['train_scene_ids'], ['patch-train'])
        self.assertEqual(report['holdout_scene_ids'], ['patch-holdout'])
        self.assertFalse(report['actual_camera_accuracy_verified'])
        self.assertFalse(model['full_camera_characterization'])
        self.assertIn('not estimated', report['response_origin'])
        self.assertTrue(np.all(np.diff(model['inverse_curve']) >= 0))

    def test_holdout_values_cannot_affect_learned_curve_or_matrix(self):
        self.calibrated()
        first, _ = read_json(self.data/'calibrated/model.json')
        def mutate(data):
            for p in data['patches']:
                if p['split'] == 'holdout':
                    p['linear_prophoto'] = [0., 0., 0.]
        self.update(self.patches, mutate)
        report = calibrate(self.patches, self.root/'changed-holdout')
        second, _ = read_json(self.root/'changed-holdout/model.json')
        for key in ('inverse_axis', 'inverse_curve', 'inverse_matrix', 'response_matrix'):
            np.testing.assert_array_equal(first[key], second[key])
        self.assertFalse(report['acceptance']['passed'])

    def test_patch_ids_scenes_exact_pairs_and_counts_cannot_leak(self):
        original = self.patches.read_bytes()
        changes = [
            lambda d: d['patches'][64].update(id=d['patches'][0]['id']),
            lambda d: d['patches'][64].update(scene='patch-train'),
            lambda d: d['patches'][64].update(st_rgb=d['patches'][0]['st_rgb'], linear_prophoto=d['patches'][0]['linear_prophoto']),
            lambda d: d.update(patches=d['patches'][:80]),
            lambda d: d['patches'][0].update(id='../outside'),
            lambda d: d['patches'][0].update(scene='too-small'),
        ]
        for i, change in enumerate(changes):
            self.patches.write_bytes(original)
            self.update(self.patches, change)
            with self.subTest(i=i), self.assertRaises(ValueError):
                calibrate(self.patches, self.root/f'invalid-{i}')
            self.assertFalse((self.root/f'invalid-{i}').exists())

    def test_patch_numeric_spaces_gray_rank_and_response_evidence_rejected(self):
        original = self.patches.read_bytes()
        changes = [lambda d: d.update(reference_space='srgb'),
                   lambda d: d.update(response_evidence=''),
                   lambda d: d.update(response_matrix=np.zeros((3, 3)).tolist()),
                   lambda d: d['patches'][0].update(st_rgb=[2, 0, 0]),
                   lambda d: d.update(max_holdout_linear_prophoto_mae=True),
                   lambda d: [p.update(st_rgb=[p['st_rgb'][0]]*3) for p in d['patches']]]
        for i, change in enumerate(changes):
            self.patches.write_bytes(original); self.update(self.patches, change)
            with self.subTest(i=i), self.assertRaises(ValueError):
                calibrate(self.patches, self.root/f'bad-{i}')

    def test_frozen_candidate_benchmark_and_all_region_coverage(self):
        candidate = self.frozen_fit()
        report = benchmark(self.project, candidate, self.lock, self.root/'benchmark')
        self.assertTrue(report['acceptance']['passed'])
        self.assertFalse(report['actual_camera_accuracy_verified'])
        self.assertEqual(report['material_kind'], 'synthetic')
        self.assertEqual(len(report['scenes']), 2)
        self.assertTrue(all(x['passed'] for x in report['region_coverage'].values()))
        self.assertEqual(report['scenes']['scene-1']['regions']['skin']['samples'], 256)
        self.assertEqual(len(list((self.root/'benchmark').glob('*.png'))), 4)
        self.assertEqual(json.loads((self.root/'benchmark/benchmark.json').read_text()), report)

    def test_manifest_threshold_or_photo_drift_refuses_before_fitting(self):
        self.calibrated()
        freeze(self.project, self.manifest, self.lock)
        for target in (self.manifest, self.data/'scene-1.png', self.data/'scene-1-gray.png',
                       self.data/'calibrated/model.json'):
            original = target.read_bytes(); target.write_bytes(original+b'\n')
            with self.subTest(target=target.name), patch('lutphoto.nativefit.native.fit_reference') as fitter:
                with self.assertRaises(ValueError):
                    fit(self.project, self.root/'bad-fit', validation_lock=self.lock)
                fitter.assert_not_called()
            self.assertFalse((self.root/'bad-fit').exists())
            target.write_bytes(original)

    def test_legacy_candidate_cannot_acquire_validation_after_fit(self):
        self.calibrated()
        fit(self.project, self.root/'legacy')
        freeze(self.project, self.manifest, self.lock)
        with self.assertRaisesRegex(ValueError, 'not fitted'):
            benchmark(self.project, self.root/'legacy/candidate.json', self.lock, self.root/'bad')
        self.assertFalse((self.root/'bad').exists())

    def test_replaced_lock_and_changed_thresholds_require_refit(self):
        candidate = self.frozen_fit()
        self.update(self.manifest, lambda d: d['thresholds']['overall'].update(max_rgb_mae=.1))
        with self.assertRaisesRegex(ValueError, 'provenance changed'):
            validate_lock(self.project, self.lock)
        new_lock = self.root/'new.lock.json'
        freeze(self.project, self.manifest, new_lock)
        with self.assertRaisesRegex(ValueError, 'not fitted'):
            benchmark(self.project, candidate, new_lock, self.root/'bad')

    def test_scene_overlap_duplicate_bytes_and_st_contract_refused(self):
        self.calibrated()
        original = self.manifest.read_bytes()
        changes = [lambda d: d['required_scene_ids'].append('patch-train'),
                   lambda d: d.update(excluded_scene_ids=[]),
                   lambda d: d['scenes'][1].update(input='scene-1.png'),
                   lambda d: d['scenes'][0].update(st_input=False),
                   lambda d: d['scenes'][0].update(id='../escaped')]
        for i, change in enumerate(changes):
            self.manifest.write_bytes(original); self.update(self.manifest, change)
            with self.subTest(i=i), self.assertRaises(ValueError):
                freeze(self.project, self.manifest, self.root/f'bad-{i}.json')

    def test_missing_required_scene_is_a_gap_not_a_pass(self):
        self.update(self.manifest, lambda d: d['required_scene_ids'].append('scene-missing'))
        candidate = self.frozen_fit()
        report = benchmark(self.project, candidate, self.lock, self.root/'benchmark')
        self.assertEqual(report['missing_scene_ids'], ['scene-missing'])
        self.assertFalse(report['acceptance']['passed'])

    def test_missing_region_and_insufficient_region_samples_fail_coverage(self):
        self.update(self.data/'scene-1-masks.json', lambda d: d['regions'].pop('skin'))
        self.update(self.data/'scene-2-masks.json', lambda d: d['regions'].pop('skin'))
        mask = np.zeros((32, 56), dtype='uint8'); mask[0, 0] = 255
        Image.fromarray(mask).save(self.data/'scene-1-gray.png')
        candidate = self.frozen_fit()
        report = benchmark(self.project, candidate, self.lock, self.root/'benchmark')
        self.assertFalse(report['acceptance']['passed'])
        self.assertEqual(report['region_coverage']['skin']['available_scene_ids'], [])
        self.assertFalse(report['region_coverage']['gray']['passed'])
        self.assertEqual(report['scenes']['scene-1']['criteria']['regions']['gray']['status'], 'insufficient_samples')

    def test_bad_available_region_cannot_be_averaged_into_good_scene(self):
        self.calibrated()
        project, _ = read_json(self.project)
        project['source']['path'] = 'swap-rb-17.cube'
        self.project.write_bytes(json_bytes(project))
        freeze(self.project, self.manifest, self.lock)
        fit(self.project, self.root/'fit', validation_lock=self.lock)
        result = benchmark(self.project, self.root/'fit/candidate.json', self.lock, self.root/'benchmark')
        self.assertFalse(result['acceptance']['passed'])
        self.assertGreater(result['bounded_coefficients'], 0)
        self.assertFalse(result['region_coverage']['skin']['passed'])

    def test_missing_patch_validation_remains_an_explicit_model_gap(self):
        self.calibrated()
        self.update(self.data/'calibrated/model.json', lambda d: d.pop('offline_calibration'))
        freeze(self.project, self.manifest, self.lock)
        fit(self.project, self.root/'fit', validation_lock=self.lock)
        result = benchmark(self.project, self.root/'fit/candidate.json', self.lock, self.root/'benchmark')
        self.assertFalse(result['model_patch_acceptance_passed'])
        self.assertFalse(result['acceptance']['passed'])

    def test_existing_paths_and_dangling_symlinks_are_preserved(self):
        with self.assertRaises(ValueError):
            calibrate(self.patches, self.data)
        link = self.root/'link'; link.symlink_to(self.root/'absent')
        with self.assertRaises(ValueError):
            calibrate(self.patches, link)
        self.assertTrue(link.is_symlink())
        self.calibrated(); freeze(self.project, self.manifest, self.lock)
        original = self.lock.read_bytes()
        with self.assertRaises(ValueError):
            freeze(self.project, self.manifest, self.lock)
        self.assertEqual(self.lock.read_bytes(), original)

    def test_criterion_missing_empty_small_and_high_error_are_distinct(self):
        rule = {'min_samples': 32, 'max_rgb_mae': .01, 'max_delta_e76_p95': 2.}
        self.assertEqual(assess({'available': False}, rule)['status'], 'unavailable')
        self.assertEqual(assess({'available': True, 'samples': 1}, rule)['status'], 'insufficient_samples')
        score = {'available': True, 'samples': 64, 'rgb_mae': .02, 'delta_e76_p95': 1.}
        self.assertEqual(assess(score, rule)['status'], 'failed_threshold')
        score['rgb_mae'] = .001
        self.assertTrue(assess(score, rule)['passed'])

    def test_benchmark_failure_cleans_staging_and_keeps_destination_absent(self):
        candidate = self.frozen_fit()
        with patch('lutphoto.nativevalidate.evaluate_photo', side_effect=OSError('simulated failure')):
            with self.assertRaisesRegex(OSError, 'simulated failure'):
                benchmark(self.project, candidate, self.lock, self.root/'benchmark')
        self.assertFalse((self.root/'benchmark').exists())
        self.assertFalse(list(self.root.glob('.native-validation-*')))

    def test_invalid_frozen_criteria_rejected_before_output(self):
        self.calibrated()
        original = self.manifest.read_bytes()
        changes = [lambda d: d['thresholds']['regions'].pop('skin'),
                   lambda d: d['thresholds']['overall'].update(min_samples=65537),
                   lambda d: d['thresholds'].update(max_native_clip_fraction=True),
                   lambda d: d['thresholds'].update(max_bounded_coefficients=-1)]
        for i, change in enumerate(changes):
            self.manifest.write_bytes(original); self.update(self.manifest, change)
            output = self.root/f'bad-{i}.json'
            with self.subTest(i=i), self.assertRaises(ValueError):
                freeze(self.project, self.manifest, output)
            self.assertFalse(output.exists())

    def test_temporarily_changed_image_cannot_be_reported_as_frozen(self):
        from lutphoto.nativevalidate import evaluate_photo
        candidate = self.frozen_fit()
        def changed(*args, **kwargs):
            source = Path(args[2])
            original = source.read_bytes()
            source.write_bytes((self.data/'scene-2.png').read_bytes())
            try:
                return evaluate_photo(*args, **kwargs)
            finally:
                source.write_bytes(original)
        with patch('lutphoto.nativevalidate.evaluate_photo', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'does not match frozen'):
                benchmark(self.project, candidate, self.lock, self.root/'benchmark')
        self.assertFalse((self.root/'benchmark').exists())
        self.assertFalse(list(self.root.glob('.native-validation-*')))

    def test_real_cli_full_flow_and_controlled_failure(self):
        exe = str(Path(sys.executable).absolute())
        commands = [('lutphoto.nativevalidate', ['calibrate', '--patches', str(self.patches), '--directory', str(self.data/'calibrated')]),
                    ('lutphoto.nativevalidate', ['freeze', '--project', str(self.project), '--manifest', str(self.manifest), '--output', str(self.lock)]),
                    ('lutphoto.nativefit', ['fit', '--project', str(self.project), '--directory', str(self.root/'fit'), '--validation-lock', str(self.lock)]),
                    ('lutphoto.nativevalidate', ['benchmark', '--project', str(self.project), '--candidate', str(self.root/'fit/candidate.json'), '--validation-lock', str(self.lock), '--directory', str(self.root/'benchmark')])]
        for module, args in commands:
            result = subprocess.run([exe, '-B', '-m', module, *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout).get('actual_camera_accuracy_verified', False))
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(main(['calibrate', '--patches', str(self.patches), '--directory', str(self.data)]), 1)
        self.assertIn('STOPPED:', error.getvalue())
        code = "import sys; import lutphoto.nativevalidate; assert not any(x.split('.')[0] in ('usb','macfl23','pmca','scipy') for x in sys.modules)"
        result = subprocess.run([exe, '-B', '-c', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
