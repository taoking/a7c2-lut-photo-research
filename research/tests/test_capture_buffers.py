"""Synthetic TBB table boundaries; no firmware bytes or device access."""
from pathlib import Path
import tempfile
import unittest

from research.trace_capture_buffers import bounded_tbb_targets, trace


class BoundedTBBTests(unittest.TestCase):
    def test_offsets_are_unsigned_halfwords_relative_to_supplied_base(self):
        # These are invented data entries, not encoded Sony instructions.
        self.assertEqual(bounded_tbb_targets(bytes([5,2,255]),0x100,0x400),
                         (0x10a,0x104,0x2fe))

    def test_halfword_aligned_base_need_not_be_word_aligned(self):
        self.assertEqual(bounded_tbb_targets(bytes([2]),0x102,0x200),(0x106,))

    def test_targets_in_table_and_odd_length_padding_are_refused(self):
        for entries in (bytes([0]),bytes([1,2,3]),bytes([0,0,0,0])):
            with self.subTest(entries=list(entries)),self.assertRaises(ValueError):
                bounded_tbb_targets(entries,0x100,0x400)

    def test_last_halfword_must_fit_and_arithmetic_must_not_wrap(self):
        self.assertEqual(bounded_tbb_targets(bytes([2]),0x100,0x106),(0x104,))
        for start,size in ((0x100,0x105),(0x100,0x101),
                           (0xfffffffe,0x100000000)):
            with self.subTest(start=start,size=size),self.assertRaises(ValueError):
                bounded_tbb_targets(bytes([2]),start,size)

    def test_invalid_ranges_types_and_unbounded_tables_are_refused(self):
        for entries,start,size in ((b'',0,512),(bytes(257),0,1024),
                ([2],0,512),(memoryview(b'\x02'),0,512),
                (b'\x02',True,512),(b'\x02',0,False),
                (b'\x02',-2,512),(b'\x02',1,512),
                (b'\x02',512,512),(b'\x02',0,0x100000001)):
            with self.subTest(start=start,size=size),self.assertRaises(ValueError):
                bounded_tbb_targets(entries,start,size)

    def test_duplicate_targets_preserved_without_aliasing_mutable_entries(self):
        entries=bytearray([3,3,4])
        result=bounded_tbb_targets(entries,0x100,0x200)
        self.assertEqual(entries,bytearray([3,3,4]))
        entries[0]=0
        self.assertEqual(result,(0x106,0x106,0x108))

    def test_wrong_firmware_refused_before_any_disassembly(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.bin'
            raw=b'synthetic image only'
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'指纹'):
                trace(path)
            self.assertEqual(path.read_bytes(),raw)


if __name__=='__main__':
    unittest.main()
