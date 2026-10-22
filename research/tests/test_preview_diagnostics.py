"""Real malformed inputs produce bounded Chinese hints, never private values."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lutphoto import nativefit as nf, offline as o
from lutphoto._offlinedemo import create_input
from lutphoto.inputerrors import InputProblem, preview_hint


class PreviewDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='private-preview-'); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve(); self.inputs = self.root / 'input'
        create_input(self.inputs)
        self.project = self.inputs / 'demo-project.json'; self.photo = self.inputs / 'chart.png'
        self.value, _ = nf.read_json(self.project); self.value['training_samples'] = 512
        self.project.write_bytes(nf.json_bytes(self.value)); self.directory = self.root / 'preview'
        self.marker = 'PERSONAL-LUT-TITLE-PATH-AND-ICC'

    def args(self):
        return ['preview', '--directory', str(self.directory), '--project', str(self.project),
                '--input', str(self.photo), '--st-input']

    def rejected(self, code):
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            status = o.main(self.args())
        self.assertEqual(status, 1); self.assertEqual(out.getvalue(), '')
        self.assertIn('[' + code + ']', err.getvalue()); self.assertIn('预览已停止', err.getvalue())
        self.assertLess(len(err.getvalue()), 400)
        self.assertNotIn(str(self.root), err.getvalue()); self.assertNotIn(self.marker, err.getvalue())
        self.assertFalse((self.directory / 'preview.private.json').exists())
        self.assertFalse((self.directory / 'RESULT.md').exists())

    def test_project_model_cube_bridge_and_domain_checks_still_reject(self):
        original = {p: p.read_bytes() for p in self.inputs.iterdir()}
        cases = ('missing-project', 'duplicate-key', 'singular-model', 'broken-cube',
                 'hdr-output', 'missing-bridge', 'broken-bridge', 'domain')
        expected = ('PROJECT', 'PROJECT', 'MODEL', 'CUBE', 'LUT_OUTPUT', 'BRIDGE', 'BRIDGE', 'DOMAIN')
        for case, code in zip(cases, expected):
            with self.subTest(case=case):
                for path, raw in original.items(): path.write_bytes(raw)
                project = json.loads(nf.json_bytes(self.value)); source = project['source']
                self.directory = self.root / case
                if case == 'missing-project':
                    self.project.unlink()
                elif case == 'duplicate-key':
                    self.project.write_text('{"' + self.marker + '":0,"' + self.marker + '":1}')
                elif case == 'singular-model':
                    model = self.inputs / 'synthetic-model.json'; value, _ = nf.read_json(model)
                    value['response_matrix'] = [[0, 0, 0]] * 3; model.write_bytes(nf.json_bytes(value))
                elif case in ('broken-cube', 'hdr-output', 'domain'):
                    cube = self.inputs / source['path']
                    if case == 'broken-cube': cube.write_text('LUT_PRIVATE_' + self.marker + ' 7\n')
                    else:
                        rows = '\n'.join('2 0 0' if case == 'hdr-output' else f'{r} {g} {b}'
                                         for b in (0, 1) for g in (0, 1) for r in (0, 1))
                        domain = 'DOMAIN_MIN 0.2 0.2 0.2\n' if case == 'domain' else ''
                        cube.write_text('LUT_3D_SIZE 2\n' + domain + rows + '\n')
                else:
                    source['input_space'] = 'log-' + self.marker
                    if case == 'broken-bridge':
                        source['bridge'] = {'input_space': 'sony-st-srgb', 'output_space': source['input_space'],
                                            'evidence': 'Selfmade invalid file', 'path': self.marker + '.cube'}
                    self.project.write_bytes(nf.json_bytes(project))
                self.rejected(code)
                self.assertFalse((self.directory / 'candidate').exists())

    def test_image_space_icc_and_format_do_not_get_silent_fixes(self):
        from PIL import Image
        for case, code in (('untagged', 'IMAGE_SPACE'), ('other-space', 'IMAGE_SPACE'), ('icc', 'ICC'), ('rgba', 'IMAGE')):
            with self.subTest(case=case):
                self.directory = self.root / case; self.photo = self.inputs / (case + '.png')
                image = Image.new('RGBA' if case == 'rgba' else 'RGB', (4, 4))
                options = {}
                if case == 'other-space':
                    exif = Image.Exif(); exif[0xA001] = 65535; options['exif'] = exif
                if case == 'icc': options['icc_profile'] = self.marker.encode()
                image.save(self.photo, **options); original = self.photo.read_bytes()
                self.rejected(code); self.assertEqual(self.photo.read_bytes(), original)
                self.assertTrue((self.directory / 'candidate/candidate.json').exists())
        # An explicit conflicting declaration still refuses --assume-srgb.
        self.directory = self.root / 'other-assumed'; self.photo = self.inputs / 'other-space.png'
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(o.main(self.args() + ['--assume-srgb']), 1)
        self.assertIn('[IMAGE_SPACE]', err.getvalue())

    def test_bad_mask_and_missing_image_retain_candidate_without_success_report(self):
        mask = self.inputs / 'masks.json'
        mask.write_bytes(nf.json_bytes({'schema': 'a7c2-offline-region-masks/1', 'regions': {self.marker: 'absent.png'}}))
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(o.main(self.args() + ['--masks', str(mask)]), 1)
        self.assertIn('[MASK]', err.getvalue()); self.assertNotIn(self.marker, err.getvalue())
        self.assertFalse((self.directory / 'preview.private.json').exists())
        self.directory = self.root / 'missing-image'; self.photo = self.inputs / (self.marker + '.png')
        self.rejected('IMAGE')

    def test_invalid_freeze_lock_stops_before_fitting_table(self):
        lock = self.inputs / 'lock.json'; lock.write_text('{"schema":"' + self.marker + '"}')
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(o.main(self.args() + ['--validation-lock', str(lock)]), 1)
        self.assertIn('[VALIDATION_LOCK]', err.getvalue()); self.assertNotIn(self.marker, err.getvalue())
        self.assertFalse((self.directory / 'candidate').exists())

    def test_changed_binding_gets_source_hint_without_printing_exception(self):
        with patch.object(o, '_reference_binding', side_effect=ValueError(self.marker + str(self.root))):
            self.rejected('SOURCE_CHANGED')
        self.assertTrue((self.directory / 'evaluation/reference.png').exists())

    def test_output_refusal_precedes_fit_and_preserves_existing_file(self):
        self.directory.mkdir(mode=0o700); keep = self.directory / self.marker; keep.write_bytes(b'keep')
        with patch.object(nf, 'fit') as fit:
            self.rejected('OUTPUT_DIRECTORY')
        fit.assert_not_called(); self.assertEqual(keep.read_bytes(), b'keep')

    def test_unknown_import_and_output_failures_are_bounded_and_not_retried(self):
        for error, code in ((ImportError(self.marker), 'DEPENDENCY'), (OSError(str(self.root)), 'INCOMPLETE'),
                            (ValueError(self.marker), 'INCOMPLETE')):
            with self.subTest(code=code), patch.object(o, 'preview', side_effect=error) as preview:
                self.rejected(code)
                preview.assert_called_once()

    def test_python_api_keeps_valueerror_and_original_message_but_hint_is_fixed(self):
        error = InputProblem('CUBE', self.marker)
        self.assertIsInstance(error, ValueError); self.assertEqual(str(error), self.marker)
        self.assertNotIn(self.marker, preview_hint(error))
        error.code = self.marker
        self.assertIn('[INCOMPLETE]', preview_hint(error)); self.assertNotIn(self.marker, preview_hint(error))


if __name__ == '__main__': unittest.main()
