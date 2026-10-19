"""Synthetic ARM member-pointer decoding and original-image rejection."""
from pathlib import Path
import tempfile
import unittest

from research.trace_lut_schedule import direct_member_pointer, trace


class DirectMemberPointerTests(unittest.TestCase):
    def test_thumb_bit_is_independent_of_virtual_bit(self):
        self.assertEqual(direct_member_pointer(0x1001,0,0x1000,0x100),
                         {'target_file_offset':0,'this_adjustment_bytes':0})
        self.assertEqual(direct_member_pointer(0x1081,2,0x1000,0x100),
                         {'target_file_offset':0x80,'this_adjustment_bytes':1})

    def test_signed_arithmetic_shift_and_extreme_adjustments(self):
        expected={2:1,0x7ffffffe:0x3fffffff,0xfffffffe:-1,
                  0xfffffffc:-2,0x80000000:-0x40000000}
        for encoded,adjustment in expected.items():
            with self.subTest(encoded=encoded):
                result=direct_member_pointer(0x1001,encoded,0x1000,2)
                self.assertEqual(result['this_adjustment_bytes'],adjustment)

    def test_virtual_dispatch_is_never_guessed(self):
        for adjustment in (1,3,0x80000001,0xffffffff):
            with self.subTest(adjustment=adjustment),self.assertRaisesRegex(ValueError,'虚'):
                direct_member_pointer(0x1001,adjustment,0x1000,0x100)

    def test_arm_or_null_entry_is_outside_model(self):
        for function in (0,0x1000,0x1080):
            with self.subTest(function=function),self.assertRaisesRegex(ValueError,'Thumb'):
                direct_member_pointer(function,0,0x1000,0x100)

    def test_pointer_must_leave_a_whole_thumb_halfword_in_image(self):
        self.assertEqual(direct_member_pointer(0x10ff,0,0x1000,0x100)['target_file_offset'],0xfe)
        for pointer,size in ((0xfff,0x100),(0x1101,0x100),(0x10ff,0xff),(0x1001,1)):
            with self.subTest(pointer=pointer,size=size),self.assertRaisesRegex(ValueError,'程序内'):
                direct_member_pointer(pointer,0,0x1000,size)

    def test_upper_address_space_boundary_does_not_wrap(self):
        self.assertEqual(direct_member_pointer(0xffffffff,0,0xfffff000,0x1000),
                         {'target_file_offset':0xffe,'this_adjustment_bytes':0})
        with self.assertRaises(ValueError):
            direct_member_pointer(0xffffffff,0,0xfffff000,0x1001)

    def test_non_uint32_values_and_booleans_refused(self):
        for value in (-1,2**32,True,1.0,'1',None):
            for argument in range(3):
                args=[0x1001,0,0x1000,0x100]
                args[argument]=value
                with self.subTest(value=value,argument=argument),self.assertRaises(ValueError):
                    direct_member_pointer(*args)

    def test_invalid_or_unaligned_mapping_refused(self):
        for base,size in ((0x1001,4),(0x1000,0),(0x1000,-1),
                          (0x1000,True),(0x1000,1.0),(0xfffffffe,4)):
            with self.subTest(base=base,size=size),self.assertRaises(ValueError):
                direct_member_pointer(0x1001,0,base,size)

    def test_wrong_image_refused_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.bin'
            path.write_bytes(b'synthetic CP only')
            with self.assertRaisesRegex(ValueError,'指纹'):
                trace(path)
            self.assertEqual(path.read_bytes(),b'synthetic CP only')


if __name__=='__main__':
    unittest.main()
