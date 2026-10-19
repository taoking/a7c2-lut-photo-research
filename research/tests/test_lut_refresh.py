"""Synthetic control-flow boundaries, with no Sony instruction fragments."""
from pathlib import Path
import tempfile
import unittest

from research.trace_cp import decode_thumb
from research.trace_lut_refresh import potential_thumb_path, trace


class PotentialPathTests(unittest.TestCase):
    def decode(self, hexadecimal):
        raw=bytes.fromhex(hexadecimal)
        return decode_thumb(raw,0,len(raw),0x1000)

    def test_sequential_and_same_endpoint(self):
        ins=self.decode('00bf00bf00bf')
        self.assertEqual(potential_thumb_path(ins,0x1000,0x1004),[0x1000,0x1002,0x1004])
        self.assertEqual(potential_thumb_path(ins,0x1002,0x1002),[0x1002])

    def test_conditional_branch_has_both_arms_regression(self):
        # Capstone reports an explicit PC write on bne. It must still have
        # branch and fallthrough successors, rather than terminate the path.
        for branch in ('00d1','00b1','00b9'):  # bne / cbz / cbnz
            ins=self.decode(branch+'00bf00bf')
            with self.subTest(branch=branch):
                self.assertEqual(potential_thumb_path(ins,0x1000,0x1004),[0x1000,0x1004])
                self.assertEqual(potential_thumb_path(ins,0x1000,0x1002),[0x1000,0x1002])

    def test_unconditional_branch_never_falls_through(self):
        for branch in ('00e0','00f001b8'):  # 16-bit and 32-bit B
            ins=self.decode(branch+'00bf00bf')
            skipped=ins[1].address
            self.assertIsNone(potential_thumb_path(ins,0x1000,skipped))
            self.assertEqual(potential_thumb_path(ins,0x1000,ins[2].address),
                             [0x1000,ins[2].address])

    def test_return_indirect_pc_write_and_jump_table_stop(self):
        for stop in ('7047','0047','00bd','8746','dfe800f0'):
            ins=self.decode(stop+'00bf')
            with self.subTest(stop=stop):
                self.assertIsNone(potential_thumb_path(ins,0x1000,ins[-1].address))

    def test_call_is_assumed_to_return_without_following_target(self):
        for call in ('00f000f8','8047'):  # BL and BLX r0
            ins=self.decode(call+'00bf')
            self.assertEqual(potential_thumb_path(ins,0x1000,ins[-1].address),
                             [0x1000,ins[-1].address])

    def test_loops_terminate_and_backward_edge_is_retained(self):
        ins=self.decode('00bffde700bf')
        self.assertIsNone(potential_thumb_path(ins,0x1000,0x1004))
        self.assertEqual(potential_thumb_path(ins,0x1002,0x1000),[0x1002,0x1000])
        conditional=self.decode('00bffdd100bf')
        self.assertEqual(potential_thumb_path(conditional,0x1000,0x1004),
                         [0x1000,0x1002,0x1004])

    def test_missing_duplicate_empty_and_nonboundary_endpoints_refused(self):
        ins=self.decode('00bf00bf00bf')
        for block in ([],[ins[0],ins[2]],[ins[0],ins[0],ins[1]]):
            with self.assertRaises(ValueError):
                potential_thumb_path(block,0x1000,0x1004)
        wide=self.decode('00f000f800bf')
        for start,target in ((0x1002,0x1004),(0x1000,0x1002),(0xffe,0x1004),(0x1000,0x1006)):
            with self.assertRaises(ValueError):
                potential_thumb_path(wide,start,target)

    def test_branch_outside_window_does_not_invent_destination(self):
        unconditional=self.decode('10e000bf')
        self.assertIsNone(potential_thumb_path(unconditional,0x1000,0x1002))
        conditional=self.decode('10d100bf')
        self.assertEqual(potential_thumb_path(conditional,0x1000,0x1002),[0x1000,0x1002])

    def test_wrong_image_refused_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.bin'
            path.write_bytes(b'synthetic image for rejection')
            with self.assertRaisesRegex(ValueError,'指纹'):
                trace(path)
            self.assertEqual(path.read_bytes(),b'synthetic image for rejection')


if __name__=='__main__':
    unittest.main()
