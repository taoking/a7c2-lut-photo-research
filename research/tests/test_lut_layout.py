"""Independent lattice expectations and span boundaries; no camera material."""
from itertools import product
from pathlib import Path
import tempfile
import unittest

from research.lut_layout import legacy_source_rows, layout_summary, split_summary
from research.trace_lut_handoff import read_original, trace


class LayoutTests(unittest.TestCase):
    def test_17_grid_covers_each_input_once_and_zero_pads(self):
        rows = legacy_source_rows(17)
        self.assertEqual(len(rows), 8000)
        self.assertEqual(sorted(x for x in rows if x is not None), list(range(17**3)))
        self.assertEqual(rows.count(None), 3087)

    def test_bank_positions_against_independent_coordinate_formula(self):
        # Invert CUBE's red-fast row numbering, then calculate destination.
        rows = legacy_source_rows(17)
        for b, g, r in product(range(17), repeat=3):
            bank = (r % 2)*4 + (g % 2)*2 + b % 2
            destination = bank*1000 + (r//2)*100 + (g//2)*10 + b//2
            self.assertEqual(rows[destination], r + 17*g + 17*17*b)
        self.assertIsNone(rows[999])
        self.assertIsNone(rows[7999])

    def test_33_grid_selects_even_coordinates_without_interpolation(self):
        rows = legacy_source_rows(33)
        actual = {x for x in rows if x is not None}
        expected = {r + 33*g + 33*33*b for r, g, b in product(range(0, 33, 2), repeat=3)}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 17**3)
        self.assertNotIn(1, actual)
        self.assertIn(32 + 32*33 + 32*33*33, actual)

    def test_layout_counts_and_channel_planes(self):
        for n in (17, 33):
            result = layout_summary(n)
            self.assertEqual(result['valid_samples_per_bank'], [729,648,648,576,648,576,576,512])
            self.assertEqual(result['channel_plane_bytes'], 16000)
            self.assertEqual(result['total_table_bytes'], 48000)

    def test_wrong_sizes_and_types_refused(self):
        for n in (0, 16, 65, -1, 17.0, '17', True):
            with self.subTest(n=n), self.assertRaises(ValueError):
                legacy_source_rows(n)

    def test_transfer_keeps_tail_separate_from_registers(self):
        result = split_summary(48128, 0, 48000, 48000, 124)
        self.assertEqual(result['unassigned_bytes'], 4)
        self.assertEqual(result['registers'], {'offset':48000, 'bytes':124})

    def test_overflow_overlap_empty_and_invalid_spans_refused(self):
        for values in [(100, 0, 80, 79, 10), (100, 0, 80, 80, 21),
                       (100, 0, 0, 80, 20), (100, 0, 80, 80, 0),
                       (0xffffffff, 0xfffffffe, 4, 0, 1),
                       (100, -1, 80, 80, 20), (100, False, 80, 80, 20),
                       (100.0, 0, 80, 80, 20)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                split_summary(*values)

    def test_wrong_original_files_refused_without_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'synthetic.bin'
            path.write_bytes(b'synthetic material only')
            before = path.read_bytes()
            for kind in ('ap', 'cp'):
                with self.assertRaisesRegex(ValueError, '指纹'):
                    read_original(path, kind)
            with self.assertRaisesRegex(ValueError, '指纹'):
                trace(path, path)
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
