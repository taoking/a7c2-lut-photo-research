"""Synthetic bit/conditional-store checks; no firmware bytes or device I/O."""
from pathlib import Path
import tempfile
import unittest

from research.trace_vfx_registers import initial_address_words, project_mode_bits, trace


class RegisterProjectionTests(unittest.TestCase):
    def test_mode_roundtrip_and_unrelated_bits(self):
        for word in (0,0xffffffff,0x55555555,0xaaaaaaaa,0x87654321):
            for mode in range(256):
                with self.subTest(word=word,mode=mode):
                    result=project_mode_bits(word,mode)
                    self.assertEqual((result >> 1) & 3,mode % 4)
                    self.assertEqual(result & 0xfffffff9,word & 0xfffffff9)

    def test_mode_byte_uses_only_low_two_bits(self):
        self.assertEqual(project_mode_bits(0,0xff),6)
        self.assertEqual(project_mode_bits(0xffffffff,0xfc),0xfffffff9)
        self.assertEqual(project_mode_bits(0x80,1),0x82)

    def test_invalid_mode_or_control_refused(self):
        for bad in (-1,0x100000000,True,False,1.0,None,'1'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                project_mode_bits(bad,0)
        for bad in (-1,256,True,False,1.0,None,'1'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                project_mode_bits(0,bad)

    def test_formats_three_and_four_clear_both_words(self):
        for code in (3,4):
            self.assertEqual(initial_address_words(code,0x87654321,0x300),(0,0))
            self.assertEqual(initial_address_words(code,0xffffffff,0xffffffff),(0,0))

    def test_other_byte_values_preserve_distinct_words(self):
        for code in set(range(256))-{3,4}:
            with self.subTest(code=code):
                self.assertEqual(initial_address_words(code,0x89abcdef,0x300),
                                 (0x89abcdef,0x300))
        # Boundaries ensure unsigned byte subtraction wraps before comparison.
        for code in (0,1,2,5,255):
            self.assertEqual(initial_address_words(code,0,0xffffffff),(0,0xffffffff))

    def test_invalid_address_projection_inputs_refused(self):
        for bad in (-1,256,True,False,1.0,None,'1'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                initial_address_words(bad,0,0)
        for bad in (-1,0x100000000,True,False,1.0,None,'1'):
            for pos in (1,2):
                args=[3,0,0];args[pos]=bad
                with self.subTest(bad=bad,pos=pos),self.assertRaises(ValueError):
                    initial_address_words(*args)

    def test_wrong_image_refused_without_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.bin';raw=b'only synthetic data'
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'指纹'):
                trace(path)
            self.assertEqual(path.read_bytes(),raw)


if __name__=='__main__':
    unittest.main()
