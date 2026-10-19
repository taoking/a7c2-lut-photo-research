"""Synthetic architecture/reference tests; no Sony program bytes are included."""
from pathlib import Path
import random
import struct
import tempfile
import unittest

from capstone import Cs, CS_ARCH_ARM, CS_ARCH_ARM64, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN

from research.trace_cp import boot_base, constant_call_arguments, decode_thumb, thumb_adr_candidates, thumb_bl_candidates, trace
from research.trace_cube_ap import adrp_add_reference, size_check_model, trace as trace_cube


class CPReferenceTests(unittest.TestCase):
    def test_boot_mapping_and_rejection(self):
        raw = struct.pack('<4I', 0xe59f1004, 0xe2811004, 0xe1a0f001, 0x20000c)
        self.assertEqual(boot_base(raw), 0x200000)
        for bad in (b'', raw[:12], b'\0'*4+raw[4:], raw[:12]+struct.pack('<I', 0)):
            with self.subTest(raw=bad):
                with self.assertRaises(ValueError):
                    boot_base(bad)

    def test_adr_alignment_and_register(self):
        # ADR r0,#4 at byte 0 => 8; ADR r3,#4 at byte 2 => also 8.
        raw = struct.pack('<4H', 0xa001, 0xa301, 0xbf00, 0xbf00)
        self.assertEqual(thumb_adr_candidates(raw, 8), [0, 2])
        self.assertEqual(thumb_adr_candidates(raw+b'x', 8), [0, 2])
        self.assertEqual(thumb_adr_candidates(b'', 8), [])

    def test_bl_sign_and_j_bits_against_independent_disassembler(self):
        rng = random.Random(6001)
        cs = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
        cs.detail = True
        for _ in range(120):
            first = 0xf000 | rng.randrange(0x800)
            second = 0xd000 | (rng.randrange(2)<<13) | (rng.randrange(2)<<11) | rng.randrange(0x800)
            raw = struct.pack('<2H', first, second)
            instruction = next(cs.disasm(raw, 0x4000000))
            self.assertEqual(instruction.mnemonic, 'bl')
            expected = instruction.operands[0].imm - 0x4000000
            self.assertEqual(thumb_bl_candidates(raw, expected), [0])

    def test_bl_excludes_blx_and_plain_data(self):
        self.assertEqual(thumb_bl_candidates(struct.pack('<2H', 0xf000, 0xe800), 4), [])
        self.assertEqual(thumb_bl_candidates(b'\0'*8+b'x', 4), [])
        self.assertEqual(thumb_bl_candidates(b'', 0), [])

    def decode(self, code):
        return decode_thumb(code, 0, len(code), 0x1000)

    def test_constant_arguments_and_call_clobbering(self):
        # movs r2,7; bl next; bl next. The second call cannot retain r2.
        raw = struct.pack('<5H', 0x2207, 0xf000, 0xf800, 0xf000, 0xf800)
        calls = constant_call_arguments(self.decode(raw), 0x1000)
        self.assertEqual([c['r2_constant'] for c in calls], [7, None])
        self.assertEqual([c['site_file_offset'] for c in calls], [2, 6])

    def test_unknown_write_and_return_clear_constants(self):
        for middle in (0x6802, 0xbd00):  # ldr r2,[r0]; pop {pc}
            raw = struct.pack('<4H', 0x2207, middle, 0xf000, 0xf800)
            calls = constant_call_arguments(self.decode(raw), 0x1000)
            self.assertIsNone(calls[0]['r2_constant'])

    def test_wide_mov_constant(self):
        # mov.w r2,#300, produced by a Thumb-2 modified immediate instruction.
        raw = bytes.fromhex('4ff49672') + bytes.fromhex('00f000f8')
        calls = constant_call_arguments(self.decode(raw), 0x1000)
        self.assertEqual(calls[0]['r2_constant'], 300)

    def test_invalid_decode_interval_or_truncated_instruction(self):
        for raw, start, end in ((b'\0\xf0', 0, 2), (b'xx', 1, 2), (b'', 0, 2)):
            with self.assertRaises(ValueError):
                decode_thumb(raw, start, end, 0)

    def test_wrong_programs_are_refused_and_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'synthetic.bin'
            path.write_bytes(b'not a Sony program')
            before = path.read_bytes()
            for reader in (trace, trace_cube):
                with self.assertRaisesRegex(ValueError, '指纹'):
                    reader(path)
            self.assertEqual(path.read_bytes(), before)


class APParserReferenceTests(unittest.TestCase):
    def instructions(self, middle=0xd503201f, final=0x91008001):
        cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        cs.detail = True
        # ADRP x0,current page; middle; ADD x1,x0,#0x20.
        return list(cs.disasm(struct.pack('<3I', 0x90000000, middle, final), 0x1000))

    def test_nonadjacent_adrp_add(self):
        self.assertEqual(adrp_add_reference(self.instructions(), 0x1000, 0x1008), 0x1020)

    def test_clobber_branch_and_wrong_source_rejected(self):
        for middle, final in ((0x52800000, 0x91008001), (0x94000000, 0x91008001),
                              (0xd503201f, 0x91008021)):
            with self.assertRaises(ValueError):
                adrp_add_reference(self.instructions(middle, final), 0x1000, 0x1008)

    def test_bad_reference_addresses_rejected(self):
        for first, last in ((0x1000,0x1004), (0x1004,0x1008), (0x1000,0x2000)):
            with self.assertRaises(ValueError):
                adrp_add_reference(self.instructions(), first, last)

    def test_observed_size_bit_test(self):
        self.assertEqual([n for n in range(4096) if size_check_model(n)], [17,33])
        for n in (-1, 0xffffffff, 16, 32, 65):
            self.assertFalse(size_check_model(n))


if __name__ == '__main__':
    unittest.main()
