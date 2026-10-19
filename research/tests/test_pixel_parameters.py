"""Synthetic sparse JPEG projections; no Sony code or device payloads."""
from pathlib import Path
import struct
import tempfile
import unittest

from research.trace_pixel_parameters import initial_jpeg_fields, trace


class InitialJPEGFieldTests(unittest.TestCase):
    def test_distinct_64bit_addresses_keep_high_words_and_order(self):
        source=bytearray(44)
        struct.pack_into('<QQ',source,0,0x12345678fffffff0,0xfedcba9876543210)
        before=bytes(source)
        result=initial_jpeg_fields(source)
        self.assertEqual(result[0],(8,0x12345678fffffff0))
        self.assertEqual(result[0x30],(8,0xfedcba9876543210))
        self.assertEqual(bytes(source),before)

    def test_six_unsigned_halfwords_expand_without_sign_extension(self):
        source=bytearray(44)
        struct.pack_into('<6H',source,0x10,0xffff,0x8000,1,0,0xdead,0xbeef)
        result=initial_jpeg_fields(source)
        expected={8:0xffff,0xc:0x8000,0x10:0xdead,0x14:0xbeef,
                  0x18:1,0x1c:0,0x28:1,0x2c:0,0x44:1,0x48:0}
        for offset,value in expected.items():
            self.assertEqual(result[offset],(4,value))

    def test_little_endian_values_are_not_host_order_or_byte_swapped(self):
        source=bytearray(44)
        source[0:8]=bytes(range(1,9))
        source[0x10:0x12]=bytes((0x12,0x34))
        source[0x1c:0x20]=bytes((0x12,0x34,0x56,0x78))
        result=initial_jpeg_fields(source)
        self.assertEqual(result[0][1],0x0807060504030201)
        self.assertEqual(result[8][1],0x3412)
        self.assertEqual(result[0x3c][1],0x78563412)

    def test_add_wraps_at_32_bits_without_changing_operands(self):
        for left,right,expected in [(0xffffffff,2,1),(0x80000000,0x80000000,0),
                                    (0x10000,0x20000,0x30000)]:
            source=bytearray(44)
            struct.pack_into('<II',source,0x1c,left,right)
            result=initial_jpeg_fields(source)
            self.assertEqual(result[0x38],(4,expected))
            self.assertEqual(result[0x3c],(4,left))
            self.assertEqual(result[0x40],(4,right))

    def test_unknown_word_stays_absent_and_known_fields_do_not_overlap(self):
        result=initial_jpeg_fields(bytes([0x7b])*44)
        occupied=set()
        for offset,(width,value) in result.items():
            span=set(range(offset,offset+width))
            self.assertFalse(span & occupied)
            occupied.update(span)
        self.assertEqual(set(range(0x78))-occupied,set(range(0x4c,0x50)))
        for offset in (0x20,0x24,0x50,0x54,0x58,0x5c,0x60,0x64,0x70,0x74):
            self.assertEqual(result[offset],(4,0))
        self.assertNotIn(0x4c,result)

    def test_two_opaque_words_are_not_combined_into_one_address(self):
        source=bytearray(44)
        struct.pack_into('<II',source,0x24,0x89abcdef,0xfedcba98)
        result=initial_jpeg_fields(source)
        self.assertEqual(result[0x68],(4,0x89abcdef))
        self.assertEqual(result[0x6c],(4,0xfedcba98))
        self.assertEqual(result[0x70],(4,0))

    def test_exact_prefix_required_without_accepting_missing_or_extra_fields(self):
        for bad in (bytes(43),bytes(45),bytes(0x78),None,'x'*44,[0]*44,memoryview(bytes(44))):
            with self.subTest(kind=type(bad).__name__),self.assertRaises(ValueError):
                initial_jpeg_fields(bad)

    def test_result_does_not_alias_mutable_input(self):
        source=bytearray(44)
        source[0x10:0x12]=b'\xff\xff'
        result=initial_jpeg_fields(source)
        source[:]=bytes(44)
        self.assertEqual(result[8],(4,65535))
        self.assertEqual(initial_jpeg_fields(source)[8],(4,0))

    def test_wrong_image_refused_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.bin'
            path.write_bytes(b'synthetic CP only')
            with self.assertRaisesRegex(ValueError,'指纹'):
                trace(path)
            self.assertEqual(path.read_bytes(),b'synthetic CP only')


if __name__=='__main__':
    unittest.main()
