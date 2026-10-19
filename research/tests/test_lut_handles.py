"""Synthetic TBH bounds/endian checks; no original bytes or device access."""
from pathlib import Path
import tempfile
import unittest

from research.trace_lut_handles import bounded_tbh_targets, trace


class BoundedTBHTests(unittest.TestCase):
    def test_little_endian_halfwords_are_scaled_once_without_byte_truncation(self):
        self.assertEqual(bounded_tbh_targets(bytes.fromhex('03003412ffff'),0x102,0x30000),
                         (0x108,0x256a,0x20100))

    def test_duplicate_targets_and_input_immutability(self):
        entries=bytearray.fromhex('030003000400')
        result=bounded_tbh_targets(entries,0x100,0x200)
        self.assertEqual(result,(0x106,0x106,0x108))
        self.assertEqual(entries,bytearray.fromhex('030003000400'))
        entries[0]=0
        self.assertEqual(result,(0x106,0x106,0x108))

    def test_own_table_and_incomplete_target_halfword_refused(self):
        for raw,start,size in ((b'\x00\x00',0x100,0x200),
                (b'\x01\x00\x03\x00',0x100,0x200),
                (b'\x02\x00',0x100,0x105),
                (b'\x02\x00',0xfffffffe,0x100000000)):
            with self.subTest(start=start,size=size),self.assertRaises(ValueError):
                bounded_tbh_targets(raw,start,size)
        self.assertEqual(bounded_tbh_targets(b'\x02\x00',0x100,0x106),(0x104,))

    def test_invalid_inputs_and_truncated_tables_refused(self):
        for raw,start,size in ((b'',0,512),(b'\x02',0,512),(bytes(514),0,2048),
                ([2,0],0,512),(memoryview(b'\x02\x00'),0,512),
                (b'\x02\x00',True,512),(b'\x02\x00',0,False),
                (b'\x02\x00',-2,512),(b'\x02\x00',1,512),
                (b'\x02\x00',0x100,0x101),(b'\x02\x00',0,0x100000001)):
            with self.subTest(start=start,size=size),self.assertRaises(ValueError):
                bounded_tbh_targets(raw,start,size)

    def test_maximum_audited_table_can_target_first_following_instruction(self):
        entries=b'\x00\x01'*256
        self.assertEqual(bounded_tbh_targets(entries,0,514),(512,)*256)

    def test_wrong_original_refused_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.bin';raw=b'no firmware bytes'
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'指纹'):
                trace(path)
            self.assertEqual(path.read_bytes(),raw)


if __name__=='__main__':
    unittest.main()
