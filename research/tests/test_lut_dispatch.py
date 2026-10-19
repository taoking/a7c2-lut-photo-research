"""Synthetic dispatch records and copy lineage; no Sony code or device use."""
from pathlib import Path
import struct
import tempfile
import unittest

from research.trace_lut_dispatch import copied_fields, dispatch_entry, trace


class DispatchTests(unittest.TestCase):
    def table(self, stride):
        raw = bytearray(512)
        for i, (key, pointer) in enumerate([(11,0x1101), (22,0x1143), (33,0x1181)]):
            struct.pack_into('<H', raw, 32+i*stride, key)
            struct.pack_into('<I', raw, 36+i*stride, pointer)
        return raw

    def test_lookup_strides_and_thumb_halfword_address(self):
        for stride in (8, 20):
            result = dispatch_entry(self.table(stride),0x1000,32,3,stride,22)
            self.assertEqual(result['entry_file_offset'],32+stride)
            self.assertEqual(result['handler_file_offset'],0x142)
            self.assertEqual(result['handler_link_va'],0x1143)

    def test_missing_and_duplicate_command_refused(self):
        raw = self.table(20)
        with self.assertRaisesRegex(ValueError,'唯一'):
            dispatch_entry(raw,0x1000,32,3,20,44)
        struct.pack_into('<H',raw,32,22)
        with self.assertRaisesRegex(ValueError,'唯一'):
            dispatch_entry(raw,0x1000,32,3,20,22)

    def test_arm_out_of_image_and_underflow_pointer_refused(self):
        for pointer in (0x1100, 0x999, 0x1201):
            raw=self.table(8)
            struct.pack_into('<I',raw,44,pointer)
            with self.subTest(pointer=pointer),self.assertRaisesRegex(ValueError,'Thumb'):
                dispatch_entry(raw,0x1000,32,3,8,22)

    def test_table_boundaries_and_integer_wrap_refused(self):
        raw=self.table(8)
        for args in [(0x1000,-1,3,8,22), (0x1000,500,3,8,22),
                     (0x1000,32,0,8,22), (0x1000,32,4097,8,22),
                     (0x1000,32,3,7,22), (0xffffffff,32,3,8,22),
                     (0x1000,32,3,8,65536), (True,32,3,8,22)]:
            with self.subTest(args=args),self.assertRaises(ValueError):
                dispatch_entry(raw,*args)
        with self.assertRaises(ValueError):
            dispatch_entry(raw,0x1000,32,3,8,22,handler_offset=5)


class CopyLineageTests(unittest.TestCase):
    def test_nonzero_consumer_base_and_copy_boundaries(self):
        actual=copied_fields(0x20,0x140,0x40,0x100,[('first',0x20,8),('last',0x5c,4)])
        self.assertEqual([x['consumer_offset'] for x in actual],[0x40,0x7c])
        self.assertEqual([x['object_offset'] for x in actual],[0x140,0x17c])

    def test_incomplete_fields_and_consumer_underflow_refused(self):
        for fields in [[('before',0x1f,4)],[('crosses_end',0x5d,4)],
                       [('empty',0x20,0)],[('float',32.0,4)]]:
            with self.subTest(fields=fields),self.assertRaises(ValueError):
                copied_fields(0x20,0x140,0x40,0x100,fields)
        with self.assertRaises(ValueError):
            copied_fields(0x20,0x140,0x40,0x141,[('first',0x20,8)])

    def test_copy_integer_limits_refused(self):
        for bounds in [(0xffffffff,0,2,0),(0,0xffffffff,2,0),
                       (0,0,0,0),(-1,0,2,0),(False,0,2,0)]:
            with self.subTest(bounds=bounds),self.assertRaises(ValueError):
                copied_fields(*bounds,[])

    def test_addresses_and_lengths_survive_synthetic_copy(self):
        # Deliberately use >32-bit addresses and unrelated scalar values.
        fields=[('table',0x68,8),('registers',0x70,8),('length',0x78,4),('generation',0xc0,4)]
        values=[0x1234567887654321,0xfedcba9876543210,48000,0xf1234567]
        source=bytearray(0xc8);dest=bytearray(0x1500)
        for (_,offset,width),value in zip(fields,values):
            source[offset:offset+width]=value.to_bytes(width,'little')
        dest[0x13d0:0x1430]=source[0x68:0xc8]
        mapping=copied_fields(0x68,0x13d0,0x60,0x13b8,fields)
        actual=[int.from_bytes(dest[0x13b8+x['consumer_offset']:
                                     0x13b8+x['consumer_offset']+x['bytes']],'little') for x in mapping]
        self.assertEqual(actual,values)
        self.assertEqual([x['consumer_offset'] for x in mapping],[0x18,0x20,0x28,0x70])

    def test_wrong_programs_refused_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.bin';path.write_bytes(b'synthetic only')
            with self.assertRaisesRegex(ValueError,'指纹'):
                trace(path,path)
            self.assertEqual(path.read_bytes(),b'synthetic only')


if __name__=='__main__':
    unittest.main()
