"""Synthetic address arithmetic and copy offsets; no Sony bytes or device I/O."""
from pathlib import Path
import tempfile
import unittest

from research.trace_vfx_consumers import add_u32_to_address_words, address_copy_path, trace


class AddressConsumerTests(unittest.TestCase):
    def test_low_word_carry_reaches_high_word(self):
        self.assertEqual(add_u32_to_address_words(0xfffffffe,0x12345678,4),
                         (2,0x12345679))
        self.assertEqual(add_u32_to_address_words(1,0xfedcba98,0xffffffff),
                         (0,0xfedcba99))

    def test_wrap_is_64bit_not_unbounded_or_saturating(self):
        self.assertEqual(add_u32_to_address_words(0xffffffff,0xffffffff,1),(0,0))
        self.assertEqual(add_u32_to_address_words(0x80000001,0xffffffff,0x80000001),(2,0))

    def test_nonoverflowing_high_word_is_not_truncated(self):
        self.assertEqual(add_u32_to_address_words(0x12345678,0x87654321,0),
                         (0x12345678,0x87654321))
        self.assertEqual(add_u32_to_address_words(0,0xffffffff,0xffffffff),
                         (0xffffffff,0xffffffff))

    def test_invalid_register_values_refused_before_arithmetic(self):
        for bad in (-1,0x100000000,True,False,1.0,None,'1'):
            for pos in range(3):
                args=[0,0,0];args[pos]=bad
                with self.subTest(bad=bad,pos=pos),self.assertRaises(ValueError):
                    add_u32_to_address_words(*args)

    def test_synthetic_pair_survives_copies_and_consumer_rebasing(self):
        # Copy independently with slices and distinguish low/high words.
        pair=bytes.fromhex('efcdab8967452301')
        source=bytearray(0x320);source[0x160:0x168]=pair
        scratch=source[:]
        job=bytearray(0x360);control=bytearray(0x328)
        job[0x168:0x1d8]=scratch[0x158:0x1c8]
        control[0x160:0x1d0]=scratch[0x158:0x1c8]
        path=address_copy_path()
        self.assertEqual(job[path['job_offset']:path['job_offset']+8],pair)
        self.assertEqual(control[path['control_offset']:path['control_offset']+8],pair)
        self.assertEqual(path['job_view_offset'],0x70*3+0x18)
        self.assertEqual(path['control_view_offset'],0x158)
        self.assertEqual(path['bytes'],8)

    def test_wrong_image_refused_and_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.bin';raw=b'synthetic, no firmware'
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'指纹'):
                trace(path)
            self.assertEqual(path.read_bytes(),raw)


if __name__=='__main__':
    unittest.main()
