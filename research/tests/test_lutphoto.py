"""Independent numeric expectations and photo/CLI failure-boundary tests.

Run separately from the installer's Python 3.10+ tests; needs research deps.
"""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from lutphoto.__main__ import main
from lutphoto.cube import CubeError, MAX_BYTES, evaluate, parse_cube
from lutphoto.fixtures import cube_bytes
from lutphoto.images import apply_photo, srgb_profile
from lutphoto.io import write_bytes_new, write_new
from lutphoto.survey import string_leads, survey_program
from research.trace_ap import adrp_target, direct_callers, plt_got

# Literal standard ordering, independent from the fixture generator.
IDENTITY = b'''TITLE "identity # literal"
LUT_3D_SIZE 2
0 0 0
1 0 0
0 1 0
1 1 0
0 0 1
1 0 1
0 1 1
1 1 1
'''


class CubeTests(unittest.TestCase):
    def test_identity_interior_and_boundary(self):
        data = [[0.123, 0.456, 0.789], [1, 0, 0.5], [0, 0, 0], [1, 1, 1]]
        cube = parse_cube(IDENTITY)
        np.testing.assert_allclose(evaluate(cube, data), data, atol=1e-15)
        self.assertEqual(cube.title, 'identity # literal')
        self.assertEqual(cube.sha256, hashlib.sha256(IDENTITY).hexdigest())

    def test_multilinear_cross_channel_math(self):
        # Each vertex is (r*g, g*b, b*r); the interpolant equals this formula.
        cube = parse_cube(b'LUT_3D_SIZE 2\n0 0 0\n0 0 0\n0 0 0\n1 0 0\n0 0 0\n0 0 1\n0 1 0\n1 1 1\n')
        rng = np.random.default_rng(1024)
        points = rng.random((100, 3))
        r, g, b = points.T
        np.testing.assert_allclose(evaluate(cube, points), np.stack((r*g, g*b, b*r), axis=-1), atol=1e-15)

    def test_asymmetric_domain_and_input_clipping(self):
        cube = parse_cube(IDENTITY.replace(b'LUT_3D_SIZE 2', b'LUT_3D_SIZE 2\nDOMAIN_MIN -1 2 10\nDOMAIN_MAX 1 6 30'))
        points = [[0, 3, 25], [-10, 7, 10], [1, 6, 30]]
        expected = [[0.5, 0.25, 0.75], [0, 1, 0], [1, 1, 1]]
        np.testing.assert_allclose(evaluate(cube, points), expected, atol=1e-15)

    def test_output_values_are_not_clipped_by_reference_kernel(self):
        cube = parse_cube(IDENTITY.replace(b'1 1 1\n', b'2 -1 3\n'))
        np.testing.assert_equal(evaluate(cube, [[1, 1, 1]]), [[2, -1, 3]])

    def test_supported_grid_sizes_and_channel_order(self):
        points = [[0.1234, 0.5678, 0.9012], [0, 1, 0.75]]
        for size in (17, 33):
            with self.subTest(size=size):
                cube = parse_cube(cube_bytes(size, 'swap-rb'))
                np.testing.assert_allclose(evaluate(cube, points), np.asarray(points)[:, ::-1], atol=1e-11)

    def test_bom_comments_crlf(self):
        raw = b'\xef\xbb\xbf# comment\r\n' + IDENTITY.replace(b'\n', b'\r\n')
        self.assertEqual(parse_cube(raw).size, 2)

    def test_invalid_and_unsupported_files(self):
        bad = [
            b'', IDENTITY[:-7], IDENTITY + b'0 0 0\n',
            IDENTITY.replace(b'LUT_3D_SIZE 2', b'LUT_3D_SIZE 66'),
            IDENTITY.replace(b'LUT_3D_SIZE 2', b'LUT_3D_SIZE 1'),
            IDENTITY.replace(b'LUT_3D_SIZE 2', b'LUT_3D_SIZE 2.0'),
            IDENTITY.replace(b'LUT_3D_SIZE 2', b'LUT_1D_SIZE 2'),
            IDENTITY.replace(b'LUT_3D_SIZE 2', b'LUT_3D_SIZE 2\nLUT_1D_SIZE 2'),
            IDENTITY.replace(b'LUT_3D_SIZE 2', b'LUT_3D_SIZE 2\nLUT_3D_SIZE 2'),
            IDENTITY + b'DOMAIN_MIN 0 0 0\n',
            IDENTITY.replace(b'0 0 0\n', b'nan 0 0\n', 1),
            IDENTITY.replace(b'0 0 0\n', b'0 inf 0\n', 1),
            IDENTITY.replace(b'0 0 0\n', b'0 0 1e309\n', 1),
            IDENTITY.replace(b'0 0 0\n', b'0 0 1000001\n', 1),
            IDENTITY.replace(b'LUT_3D_SIZE 2', b'LUT_3D_SIZE 2\nDOMAIN_MAX 0 1 1'),
            IDENTITY.replace(b'LUT_3D_SIZE 2', b'LUT_3D_SIZE 2\nDOMAIN_MIN 1 1 1\nDOMAIN_MAX 0 0 0'),
            IDENTITY.replace(b'LUT_3D_SIZE 2', b'LUT_3D_SIZE 2\nUNKNOWN 1'),
            IDENTITY.replace(b'0 0 0\n', b'0 0\n', 1),
            b'TITLE "unterminated\n' + IDENTITY,
            b'#' + b'a' * 4096 + b'\n' + IDENTITY,
            IDENTITY + b'\x00', IDENTITY + b'\xff', b' ' * (MAX_BYTES + 1),
        ]
        for raw in bad:
            with self.subTest(prefix=raw[:80]):
                with self.assertRaises(CubeError):
                    parse_cube(raw)

    def test_invalid_input_arrays(self):
        for points in ([1, 2], [[0, float('nan'), 0]], 1):
            with self.assertRaises(CubeError):
                evaluate(parse_cube(IDENTITY), points)


class FileAndPhotoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.png'
        self.output = self.root / 'output.png'
        self.pixels = np.array([[[0, 64, 255], [17, 99, 201]], [[250, 5, 128], [255, 255, 255]]], dtype=np.uint8)
        Image.fromarray(self.pixels).save(self.source, icc_profile=srgb_profile())
        self.cube = parse_cube(IDENTITY)

    def apply(self, **kwargs):
        return apply_photo(self.cube, self.source, self.output, lut_space='srgb', **kwargs)

    def test_lossless_identity_preserves_original(self):
        before = self.source.read_bytes()
        result = self.apply()
        with Image.open(self.output) as output:
            np.testing.assert_array_equal(np.asarray(output), self.pixels)
            self.assertIn('icc_profile', output.info)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(result['clipped_channel_values'], 0)
        self.assertFalse(result['camera_processing_verified'])

    def test_swap_math_and_chunk_boundary(self):
        self.cube = parse_cube(cube_bytes(17, 'swap-rb'))
        with patch('lutphoto.images.CHUNK_PIXELS', 1):
            self.apply()
        with Image.open(self.output) as output:
            np.testing.assert_array_equal(np.asarray(output), self.pixels[..., ::-1])

    def test_output_quantization_clipping_is_reported(self):
        self.cube = parse_cube(b'LUT_3D_SIZE 2\n' + b'-1 0.5 2\n' * 8)
        result = self.apply()
        self.assertEqual(result['clipped_channel_values'], 8)
        with Image.open(self.output) as output:
            np.testing.assert_array_equal(np.asarray(output), np.tile([0, 128, 255], (2, 2, 1)))

    def test_untagged_requires_explicit_assumption(self):
        Image.fromarray(self.pixels).save(self.source)
        with self.assertRaisesRegex(ValueError, 'assume-srgb'):
            self.apply()
        self.assertFalse(self.output.exists())
        self.assertEqual(self.apply(assume_srgb=True)['input_interpretation'], 'assumed-srgb')

    def test_invalid_icc_is_not_silently_ignored(self):
        Image.fromarray(self.pixels).save(self.source, icc_profile=b'invalid')
        with self.assertRaisesRegex(ValueError, 'ICC'):
            self.apply(assume_srgb=True)
        self.assertFalse(self.output.exists())

    def test_reject_explicit_other_space_even_with_assumption(self):
        exif = Image.Exif()
        exif[0xA001] = 65535
        Image.fromarray(self.pixels).save(self.source, exif=exif)
        with self.assertRaisesRegex(ValueError, '其他色彩空间'):
            self.apply(assume_srgb=True)

    def test_orientation_applied_and_private_metadata_dropped(self):
        exif = Image.Exif()
        exif[0x0112] = 6
        exif[0x010E] = 'private description'
        Image.fromarray(self.pixels).save(self.source, icc_profile=srgb_profile(), exif=exif)
        self.apply()
        with Image.open(self.output) as output:
            np.testing.assert_array_equal(np.asarray(output), np.rot90(self.pixels, -1))
            self.assertNotIn('exif', output.info)

    def test_refuse_original_existing_output_and_symlink(self):
        with self.assertRaises(ValueError):
            apply_photo(self.cube, self.source, self.source, lut_space='srgb')
        self.output.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            self.apply()
        self.assertEqual(self.output.read_bytes(), b'keep')
        dangling = self.root / 'link.png'
        dangling.symlink_to(self.root / 'absent')
        with self.assertRaises(FileExistsError):
            apply_photo(self.cube, self.source, dangling, lut_space='srgb')

    def test_failure_leaves_no_partial_or_overwritten_file(self):
        def broken(stream):
            stream.write(b'partial')
            raise OSError('injected failure')
        with self.assertRaises(OSError):
            write_new(self.output, broken)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.lutphoto-*')), [])
        self.output.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            write_bytes_new(self.output, b'replace')
        self.assertEqual(self.output.read_bytes(), b'keep')

    def test_reject_formats_size_and_unsupported_space(self):
        Image.new('RGBA', (2, 2)).save(self.source)
        with self.assertRaisesRegex(ValueError, 'RGB 8'):
            self.apply(assume_srgb=True)
        with self.assertRaises(ValueError):
            apply_photo(self.cube, self.source, self.output, lut_space='slog3')
        Image.fromarray(self.pixels).save(self.source, icc_profile=srgb_profile())
        with patch('lutphoto.images.MAX_PIXELS', 3):
            with self.assertRaisesRegex(ValueError, '像素'):
                self.apply()
        with patch('lutphoto.images.MAX_IMAGE_BYTES', 1):
            with self.assertRaisesRegex(ValueError, '128 MiB'):
                self.apply()

    def test_jpeg_output_has_profile(self):
        self.output = self.root / 'output.jpg'
        result = self.apply()
        self.assertEqual(result['format'], 'JPEG')
        with Image.open(self.output) as output:
            self.assertEqual(output.size, (2, 2))
            self.assertIn('icc_profile', output.info)

    def test_rgb16_and_transparent_png_refused(self):
        # A valid RGB16 PNG made directly from PNG chunks, not via Pillow's RGB8 writer.
        import zlib
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        raw = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 16, 2, 0, 0, 0))
        raw += chunk(b'IDAT', zlib.compress(b'\0' + b'\0\x01' * 3)) + chunk(b'IEND', b'')
        self.source.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, '精度'):
            self.apply(assume_srgb=True)
        Image.fromarray(self.pixels).save(self.source, transparency=(0, 64, 255))
        with self.assertRaisesRegex(ValueError, '透明色'):
            self.apply(assume_srgb=True)

    def test_decompression_bomb_is_a_controlled_failure(self):
        import zlib
        raw = self.source.read_bytes()
        header = struct.pack('>IIBBBBB', 100000, 100000, 8, 2, 0, 0, 0)
        chunk = b'IHDR' + header
        raw = raw[:16] + header + struct.pack('>I', zlib.crc32(chunk)) + raw[33:]
        self.source.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, '像素数量'):
            self.apply()
        self.assertFalse(self.output.exists())


class SurveyAndCLITests(unittest.TestCase):
    def test_direct_branch_sign_and_opcode(self):
        code = struct.pack('<4I', 0x94000002, 0xd503201f, 0x97fffffe, 0x14000000)
        self.assertEqual(direct_callers(code, 0x1000, 0x1008), [0x1000])
        self.assertEqual(direct_callers(code, 0x1000, 0x1000), [0x1008])
        self.assertEqual(direct_callers(code, 0x1000, 0x100c), [])
        with self.assertRaises(ValueError):
            direct_callers(b'x', 0, 0)

    def test_plt_structure_and_adrp_sign(self):
        self.assertEqual(adrp_target(0xb0000010, 0x1234), 0x2000)
        self.assertEqual(adrp_target(0xf0fffff0, 0x1234), 0)
        stub = struct.pack('<4I', 0x90000010, 0xf9400211, 0x91000210, 0xd61f0220)
        self.assertEqual(plt_got(stub, 0x1234), 0x1000)
        with self.assertRaises(ValueError):
            plt_got(stub[:-1], 0)
        with self.assertRaises(ValueError):
            plt_got(stub[:-4] + b'\0'*4, 0)
        with self.assertRaises(ValueError):
            adrp_target(0, 0)

    def test_string_offsets_and_truncation_do_not_claim_pipeline(self):
        data = b'xx.cube\0' + 'PPLUT'.encode('utf-16-le') + b'LUT' * 40
        leads = string_leads(data, limit=2)
        self.assertEqual(leads[0]['file_offsets'], ['0x2'])
        self.assertTrue(any(v['encoding'] == 'utf-16-le' for v in leads))
        self.assertTrue(any(v['more_hits'] for v in leads))

    def test_unknown_program_refused_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'unknown.bin'
            path.write_bytes(b'LUT_3D_SIZE PPLUT')
            with self.assertRaisesRegex(ValueError, '指纹'):
                survey_program(path, 'ap')
            self.assertEqual(path.read_bytes(), b'LUT_3D_SIZE PPLUT')

    def test_real_cli_fixture_apply_inspect_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'fixtures'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['fixtures', '--directory', str(root)]), 0)
                self.assertEqual(main(['apply', '--lut', str(root/'identity-17.cube'), '--input', str(root/'chart.png'),
                                       '--output', str(root/'identity.png'), '--lut-space', 'srgb']), 0)
            with Image.open(root/'chart.png') as original, Image.open(root/'identity.png') as output:
                np.testing.assert_array_equal(np.asarray(original), np.asarray(output))
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(main(['inspect', str(root/'identity-17.cube')]), 0)
            self.assertFalse(json.loads(captured.getvalue())['camera_compatibility_verified'])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['fixtures', '--directory', str(root)]), 1)
                self.assertEqual(main(['inspect', str(root/'missing.cube')]), 1)

    def test_independent_process_imports_no_camera_modules(self):
        process = subprocess.run([sys.executable, '-B', '-c',
            'import lutphoto.__main__, sys; assert not any(x == "usb" or x.startswith(("usb.", "macfl23", "pmca")) for x in sys.modules)'],
            capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)


if __name__ == '__main__':
    unittest.main()
