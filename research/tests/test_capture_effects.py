"""Synthetic constrained graph checks; no firmware execution or fragments."""
from pathlib import Path
import tempfile
import unittest

from research.trace_cp import decode_thumb
from research.trace_lut_refresh import potential_thumb_path


class ConstrainedPathTests(unittest.TestCase):
    def decode(self, hexadecimal, base=0x1000):
        raw=bytes.fromhex(hexadecimal)
        return decode_thumb(raw,0,len(raw),base)

    def test_taken_edge_excludes_fallthrough_and_default_remains_possible(self):
        for branch in ('00d1','00b1','00b9'):
            ins=self.decode(branch+'00bf00bf')
            with self.subTest(branch=branch):
                self.assertIsNone(potential_thumb_path(ins,0x1000,0x1002,
                                  branch_decisions={0x1000:True}))
                self.assertEqual(potential_thumb_path(ins,0x1000,0x1004,
                                 branch_decisions={0x1000:True}),[0x1000,0x1004])
                self.assertIsNotNone(potential_thumb_path(ins,0x1000,0x1002))

    def test_not_taken_edge_does_not_skip_an_intervening_return(self):
        ins=self.decode('00d1704700bf')
        self.assertIsNone(potential_thumb_path(ins,0x1000,0x1004,
                          branch_decisions={0x1000:False}))
        self.assertIsNotNone(potential_thumb_path(ins,0x1000,0x1004))

    def test_separate_blocks_need_explicit_gap_option_and_branch(self):
        ins=self.decode('01e0')+self.decode('00bf',0x1006)
        with self.assertRaises(ValueError):
            potential_thumb_path(ins,0x1000,0x1006)
        self.assertEqual(potential_thumb_path(ins,0x1000,0x1006,allow_gaps=True),
                         [0x1000,0x1006])
        disconnected=self.decode('00bf')+self.decode('00bf',0x1006)
        self.assertIsNone(potential_thumb_path(disconnected,0x1000,0x1006,allow_gaps=True))
        with self.assertRaises(ValueError):
            potential_thumb_path(ins+ins[:1],0x1000,0x1006,allow_gaps=True)

    def test_invalid_decisions_do_not_silently_change_the_graph(self):
        for opcode in ('00bf','00e0','7047','00f000f8'):
            ins=self.decode(opcode+'00bf')
            with self.subTest(opcode=opcode),self.assertRaises(ValueError):
                potential_thumb_path(ins,0x1000,ins[-1].address,
                                     branch_decisions={0x1000:True})
        ins=self.decode('00d100bf00bf')
        for decisions in ({0x1000:1},{0x1001:True},{0x2000:False},[],False):
            with self.subTest(decisions=decisions),self.assertRaises(ValueError):
                potential_thumb_path(ins,0x1000,0x1004,branch_decisions=decisions)
        with self.assertRaises(ValueError):
            potential_thumb_path(ins,0x1000,0x1004,allow_gaps=1)

    def test_decisions_are_not_mutated_and_back_edges_terminate(self):
        ins=self.decode('00bffdd100bf')
        decisions={0x1002:True}
        self.assertIsNone(potential_thumb_path(ins,0x1000,0x1004,branch_decisions=decisions))
        self.assertEqual(decisions,{0x1002:True})
        self.assertIsNotNone(potential_thumb_path(ins,0x1000,0x1004,
                            branch_decisions={0x1002:False}))

    def test_wrong_image_refused_unchanged(self):
        from research.trace_capture_effects import trace
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.bin'
            raw=b'synthetic material only'
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'指纹'):
                trace(path)
            self.assertEqual(path.read_bytes(),raw)


if __name__=='__main__':
    unittest.main()
