"""Synthetic constant reconstruction and multi-stage LUT field lineage."""
from pathlib import Path
import struct
import tempfile
import unittest

from research.trace_cp import decode_thumb
from research.trace_lut_snapshot import movw_movt_value, snapshot_field_path, trace


def halfword_move(register, immediate, upper=False):
    high=(0xf2c0 if upper else 0xf240) | ((immediate>>12)&15) | (((immediate>>11)&1)<<10)
    low=(((immediate>>8)&7)<<12) | (register<<8) | (immediate&255)
    return struct.pack('<2H',high,low)


class SnapshotConstantTests(unittest.TestCase):
    def decode(self,raw):
        return decode_thumb(raw,0,len(raw),0x1000)

    def test_data_id_regression_nonadjacent_movt_shift_is_16_bits(self):
        raw=halfword_move(0,0x160)+bytes.fromhex('0721')+halfword_move(0,3,True)
        self.assertEqual(movw_movt_value(self.decode(raw),0x1000,0x1006),0x00030160)
        self.assertNotEqual(movw_movt_value(self.decode(raw),0x1000,0x1006),0x00300160)

    def test_unsigned_halfwords_and_nonzero_registers(self):
        for lo,hi,reg in [(0,0,1),(0xffff,0xffff,4),(0xa720,0x165,8),(0x8000,0x8000,10)]:
            with self.subTest(lo=lo,hi=hi,reg=reg):
                ins=self.decode(halfword_move(reg,lo)+halfword_move(reg,hi,True))
                self.assertEqual(movw_movt_value(ins,0x1000,0x1004),(hi<<16)|lo)

    def test_register_overwrite_and_mismatch_refused(self):
        raws=[halfword_move(0,1)+bytes.fromhex('0020')+halfword_move(0,3,True),
              halfword_move(0,1)+bytes.fromhex('00bf')+halfword_move(1,3,True)]
        for raw in raws:
            with self.assertRaises(ValueError):
                movw_movt_value(self.decode(raw),0x1000,0x1006)

    def test_control_flow_and_conditional_blocks_refused(self):
        for middle in [bytes.fromhex('00e0'),bytes.fromhex('00f000f8'),bytes.fromhex('08bf00bf')]:
            raw=halfword_move(0,1)+middle+halfword_move(0,3,True)
            with self.subTest(middle=middle.hex()),self.assertRaises(ValueError):
                movw_movt_value(self.decode(raw),0x1000,0x1004+len(middle))

    def test_missing_reversed_and_wrong_instruction_refused(self):
        ins=self.decode(halfword_move(0,1)+halfword_move(0,3,True))
        for a,b in [(0x1004,0x1000),(0x1000,0x1010),(0xff0,0x1004),(0x1000,0x1000)]:
            with self.subTest(a=a,b=b),self.assertRaises(ValueError):
                movw_movt_value(ins,a,b)
        ins=self.decode(bytes.fromhex('012000bf')+halfword_move(0,3,True))
        with self.assertRaises(ValueError):
            movw_movt_value(ins,0x1000,0x1004)

    def test_missing_intervening_instruction_refused(self):
        raw=halfword_move(0,1)+bytes.fromhex('0020')+halfword_move(0,3,True)
        ins=self.decode(raw)
        with self.assertRaisesRegex(ValueError,'连续'):
            movw_movt_value([ins[0],ins[2]],0x1000,0x1006)

    def test_wrong_image_refused_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.bin';path.write_bytes(b'synthetic only')
            with self.assertRaisesRegex(ValueError,'指纹'):
                trace(path)
            self.assertEqual(path.read_bytes(),b'synthetic only')


class SnapshotLineageTests(unittest.TestCase):
    def test_two_copies_preserve_distinct_values_and_64bit_addresses(self):
        state=bytearray(0xd68);root=bytearray([0x7b])*0xd68;obj=bytearray(0x1500)
        expected=[0x12345678fffffff0,0xfedcba9876543210,48000,124,0xf1234567]
        fields=[(0x68,8),(0x70,8),(0x78,4),(0x7c,4),(0xc0,4)]
        for (offset,width),value in zip(fields,expected):
            state[offset:offset+width]=value.to_bytes(width,'little')
        root[:0xd64]=state[:0xd64]
        obj[0x13d0:0x1430]=root[0x68:0xc8]
        actual=[]
        for field in snapshot_field_path():
            start=0x13b8+field['vfx_input_offset']
            actual.append(int.from_bytes(obj[start:start+field['bytes']],'little'))
        self.assertEqual(actual,expected)
        self.assertEqual(root[0xd64:],b'\x7b'*4)

    def test_field_offsets_match_independent_consumer_layout(self):
        fields=snapshot_field_path()
        self.assertEqual([x['internal_offset'] for x in fields],[0x68,0x70,0x78,0x7c,0xc0])
        self.assertEqual([x['snapshot_offset'] for x in fields],[0x68,0x70,0x78,0x7c,0xc0])
        self.assertEqual([x['vfx_input_offset'] for x in fields],[0x18,0x20,0x28,0x2c,0x70])
        self.assertEqual([x['bytes'] for x in fields],[8,8,4,4,4])


if __name__=='__main__':
    raise SystemExit(unittest.main())
