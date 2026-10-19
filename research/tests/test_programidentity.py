"""Own tiny programs exercise full identity gates; no real firmware is used."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lutphoto import programidentity as p


class ProgramIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ap = {kind: self.ap_program(value) for kind, value in (('stock', 17), ('fl23', 34))}
        self.cp = {kind: bytes([value]) * 8192 for kind, value in (('stock', 17), ('fl23', 34))}
        self.runtime_cp = self.table_program(51)
        self.legacy_cp = self.table_program(68)
        legacy = bytearray(self.ap['stock']); legacy[64] ^= 0x55; self.legacy_ap = bytes(legacy)
        restore = lambda raw: tuple(p._Window(at, raw[at:at + size]) for at, size in
            ((128, 132), (16, 4), (32, 12), *((512 + i * 8, 4) for i in range(6))))
        self.policy = p._Policy(tuple(p._Source(k, len(a), self.sha(a), len(self.cp[k]), self.sha(self.cp[k]), restore(a))
            for k, a in self.ap.items()), tuple(bytes([i]) * 132 for i in range(64)), b'TITL', b'MAP!' * 3,
            self.sha(self.legacy_ap), self.normalized(self.legacy_cp), self.normalized(self.runtime_cp),
            'fixture-only', '00' * 32, hook_at=128, title_at=16, map_at=32,
            labels_at=512, label_stride=8, descriptors_at=4096, table_at=256)

    @staticmethod
    def sha(raw): return hashlib.sha256(raw).hexdigest()

    def ap_program(self, value):
        raw = bytearray([value]) * 16384
        def row(attribute, key, base=False):
            struct.pack_into('<8I', raw, 4096 + (attribute - 0x14ea) * 32,
                             3 if base else 0, key, 0x10000 if base else 0x40000, 0, 0, 0, attribute, 0)
        for i in range(8): row(0x1520 + i * 18, 0x02cf0300 + i)
        for slot in range(1, 7):
            row(0x14ea + slot + 9, 0x02cf0100 + slot, True)
            for i in range(8): row(0x1520 + i * 18 + slot + 9, 0x02cf0200 + i * 8 + slot)
        return bytes(raw)

    def table_program(self, value):
        raw = bytearray([value]) * 8192
        table = (bytes((0, 1, 63, 192, 255)) * 243)
        struct.pack_into('<8I', raw, 256, 0x364c3741, 0x10006, *([p._fnv(table)] * 6))
        raw[288:7578] = table * 6
        return bytes(raw)

    def normalized(self, cp):
        return self.sha(cp[:264] + bytes(7314) + cp[7578:])

    def target(self, kind, mask):
        # Independent full bytearray reconstruction of the documented adapter.
        raw = bytearray(self.ap[kind]); raw[128:260] = bytes([mask]) * 132
        raw[16:20] = b'TITL'; raw[32:44] = b'MAP!' * 3
        for i in range(6):
            if mask & (1 << i): struct.pack_into('<I', raw, 512 + i * 8, 0x0200ab2c + i)
        return bytes(raw)

    def paths(self, ap=None, cp=None):
        a, c = self.root / 'appFw.so', self.root / 'cpapp-b.bin'
        a.write_bytes(self.ap['stock'] if ap is None else ap)
        c.write_bytes(self.cp['stock'] if cp is None else cp)
        return a, c

    def test_exact_first_import_pairs_and_cross_pairs(self):
        for kind in ('stock', 'fl23'):
            result = p._identify(self.ap[kind], self.cp[kind], self.policy)
            self.assertEqual((result['kind'], result['mask'], result['first_import']), (kind, 0, True))
            for cp in (self.cp['fl23' if kind == 'stock' else 'stock'], self.runtime_cp, self.legacy_cp):
                with self.assertRaisesRegex(ValueError, 'matching'): p._identify(self.ap[kind], cp, self.policy)

    def test_all_63_masks_for_both_sources_match_independent_complete_rebuild(self):
        for kind in ('stock', 'fl23'):
            for mask in range(1, 64):
                ap = self.target(kind, mask)
                result = p._identify(ap, self.runtime_cp, self.policy)
                self.assertEqual((result['kind'], result['mask'], result['first_import']), (kind + '-lut', mask, False))
                self.assertEqual(result['AP_sha256'], self.sha(ap))

    def test_unknown_bytes_and_unselected_labels_never_become_ignored_ranges(self):
        original = self.target('stock', 1)
        for at in (0, 64, 127, 128, 259, 260, 16, 32, 512, 520, 16383):
            raw = bytearray(original); raw[at] ^= 0x80
            with self.subTest(at=at), self.assertRaises(ValueError): p._identify(bytes(raw), self.runtime_cp, self.policy)

    def test_zero_or_unknown_template_never_matches_standalone(self):
        for mask in (0, 64):
            with self.assertRaises(ValueError): p._identify(self.target('stock', mask), self.runtime_cp, self.policy)
        for mask in (0, 64, True):
            with self.assertRaises(ValueError): p._target_windows(self.policy, mask)

    def test_legacy_and_standalone_remain_separate_code_identities(self):
        result = p._identify(self.legacy_ap, self.legacy_cp, self.policy)
        self.assertEqual((result['kind'], result['layout'], result['mask']), ('legacy-six', 'full7-v4', 63))
        with self.assertRaises(ValueError): p._identify(self.legacy_ap, self.runtime_cp, self.policy)
        with self.assertRaises(ValueError): p._identify(self.target('stock', 2), self.legacy_cp, self.policy)

    def test_variable_tables_still_bind_the_full_cp_hash_and_unchanged_code(self):
        cp = bytearray(self.runtime_cp); cp[288] = 2
        struct.pack_into('<I', cp, 264, p._fnv(cp[288:1503]))
        result = p._identify(self.target('stock', 1), bytes(cp), self.policy)
        self.assertNotEqual(result['CP_sha256'], self.sha(self.runtime_cp))
        for at in (0, 255, 7578, 8191):
            bad = bytearray(cp); bad[at] ^= 1
            with self.assertRaises(ValueError): p._identify(self.target('stock', 1), bytes(bad), self.policy)

    def test_table_header_checksum_signed_range_and_truncation(self):
        for at in (256, 260, 264, 288, 7577):
            raw = bytearray(self.runtime_cp); raw[at] ^= 0x80
            with self.assertRaises(ValueError): p._tables(bytes(raw), self.policy)
        raw = bytearray(self.runtime_cp); raw[288] = 64
        struct.pack_into('<I', raw, 264, p._fnv(raw[288:1503]))
        with self.assertRaises(ValueError): p._tables(bytes(raw), self.policy)
        with self.assertRaises(ValueError): p._tables(self.runtime_cp[:7577], self.policy)
        self.assertEqual(p._fnv(b'hello'), 0x4f9f2cab)

    def test_all_byte_values_match_upstream_native_decode_range(self):
        from lutphoto._vendor.sonylooks import native
        for value in range(256):
            cp = bytearray(self.runtime_cp); table = bytes([value]) * 1215
            cp[288:1503] = table; struct.pack_into('<I', cp, 264, p._fnv(table))
            try: native.decode(table)
            except ValueError:
                with self.assertRaises(ValueError): p._tables(bytes(cp), self.policy)
            else: p._tables(bytes(cp), self.policy)

    def test_virtual_hash_matches_complete_copy_and_rejects_bad_windows(self):
        raw = b'abcdefghij'; windows = (p._Window(7, b'XY'), p._Window(1, b'12'))
        self.assertEqual(p._hash_after(raw, windows), self.sha(b'a12defgXYj'))
        for rows in ((p._Window(-1, b'x'),), (p._Window(True, b'x'),), (p._Window(0, b''),),
                     (p._Window(9, b'xx'),), (p._Window(1, b'12'), p._Window(2, b'x'))):
            with self.assertRaises(ValueError): p._hash_after(raw, rows)
        with self.assertRaisesRegex(ValueError, 'outside'):
            p._matches_reconstruction(raw, (), (p._Window(0, b'x'),))

    def test_truncated_resized_and_mutable_programs_rejected(self):
        for ap, cp in ((self.ap['stock'][:-1], self.cp['stock']), (self.ap['stock'], self.cp['stock'] + b'x'),
                       (bytearray(self.ap['stock']), self.cp['stock']), (None, self.cp['stock'])):
            with self.assertRaises(ValueError): p._identify(ap, cp, self.policy)

    def test_all_six_slots_have_54_unique_fields_and_eight_shared_st_rows(self):
        result = p._descriptors(self.ap['stock'], [6, 5, 4, 3, 2, 1], self.policy)
        self.assertEqual(result['selected_slots'], list(range(1, 7)))
        self.assertEqual((result['selected_fields'], result['ST_reference_fields'], result['unique_rows_checked']), (54, 8, 62))
        self.assertFalse(result['write_plan_enabled']); self.assertFalse(result['setting_values_verified'])

    def test_slots_types_duplicates_and_empty_selection_rejected(self):
        for slots in ([], [1, 1], [True], [0], [7], ['1'], None, {1}):
            with self.assertRaises(ValueError): p._descriptors(self.ap['stock'], slots, self.policy)

    def test_descriptor_identity_group_type_and_layout_rejected_for_all_row_roles(self):
        for attribute in (0x14ea + 10, 0x1520 + 10, 0x1520):
            at = 4096 + (attribute - 0x14ea) * 32
            for index, value in ((0, 99), (1, 0x02a40000), (1, 0x02cf0b6e), (2, 123), (6, attribute + 1)):
                ap = bytearray(self.ap['stock']); struct.pack_into('<I', ap, at + index * 4, value)
                with self.subTest(attribute=attribute, index=index), self.assertRaises(ValueError):
                    p._descriptors(bytes(ap), [1], self.policy)

    def test_descriptor_extent_and_selected_or_reference_aliases_rejected(self):
        with self.assertRaises(ValueError): p._descriptors(bytes(4096), [1], self.policy)
        def key(attribute): return struct.unpack_from('<I', self.ap['stock'], 4096 + (attribute - 0x14ea) * 32 + 4)[0]
        for attribute, value in ((0x1520 + 10, key(0x14ea + 10)), (0x1520 + 11, key(0x1520 + 10)),
                                 (0x1520 + 10, key(0x1520)), (0x1520 + 18, key(0x1520))):
            raw = bytearray(self.ap['stock']); struct.pack_into('<I', raw, 4096 + (attribute - 0x14ea) * 32 + 4, value)
            with self.assertRaisesRegex(ValueError, 'Aliased'): p._descriptors(bytes(raw), [1, 2], self.policy)

    def test_unknown_pair_rejected_before_any_descriptor_access(self):
        a, c = self.paths(ap=bytes(16384))
        with patch.object(p, '_load_policy', return_value=self.policy), patch.object(p, '_descriptors') as read:
            with self.assertRaises(ValueError): p.inspect_files('unused', a, c, [1])
        read.assert_not_called()

    def test_local_reports_prove_only_content_and_do_not_expose_paths_keys_or_bytes(self):
        a, c = self.paths(); before = (a.read_bytes(), c.read_bytes())
        with patch.object(p, '_load_policy', return_value=self.policy): report = p.inspect_files('unused', a, c, [1, 6])
        self.assertTrue(report['local_program_content_verified']); self.assertTrue(report['private_report'])
        for key in p.w.boundary(): self.assertFalse(report[key])
        self.assertFalse(report['body_binding_verified']); self.assertFalse(report['same_capture_provenance_verified'])
        text = json.dumps(report)
        for private in (str(self.root), '02cf0101', b'TITL'.hex(), 'before_ram', 'after'):
            self.assertNotIn(private, text)
        self.assertEqual(before, (a.read_bytes(), c.read_bytes()))

    def test_read_program_rejects_links_non_regular_and_wrong_size(self):
        a, _ = self.paths(); link = self.root / 'link'; link.symlink_to(a)
        for path in (link, self.root):
            with self.assertRaises((OSError, ValueError)): p._read_program(path, {16384})
        with self.assertRaises(ValueError): p._read_program(a, {8192})
        with patch.object(p, 'MAX_PROGRAM', 1), self.assertRaises(ValueError): p._read_program(a, {16384})

    def test_read_program_rejects_concurrent_metadata_change(self):
        a, _ = self.paths(); before = a.stat()
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        after = SimpleNamespace(**{k: getattr(before, k) for k in fields}); after.st_ctime_ns += 1
        with patch.object(p.os, 'fstat', side_effect=[before, after]), self.assertRaisesRegex(ValueError, 'changed'):
            p._read_program(a, {16384})

    def test_requirements_never_opens_programs(self):
        with patch.object(p, '_load_policy', return_value=self.policy), patch.object(p, '_read_program') as read:
            report = p.requirements('unused')
        read.assert_not_called(); self.assertFalse(report['program_files_read'])
        self.assertFalse(report['camera_required']); self.assertEqual(report['programs']['AP']['bytes'], [16384])

    def test_fixed_source_policy_build_uses_checked_metadata_without_python_execution(self):
        asset = {'ap_sources': [{'kind': s.kind, 'bytes': s.ap_bytes, 'sha256': s.ap_sha,
                  'restore': [{'offset': r.at, 'hex': r.data.hex()} for r in s.restore]} for s in self.policy.sources],
                 'cp_sources': [{'kind': s.kind, 'bytes': s.cp_bytes, 'sha256': s.cp_sha} for s in self.policy.sources],
                 'ap_templates': [t.hex() for t in self.policy.templates], 'title_branch': '00000000',
                 'map': '00' * 12, 'cp_code_sha256': self.policy.standalone_code}
        source = {'src/looks/assets/runtime-v1.json': json.dumps(asset).encode(), 'unused.py': b'raise RuntimeError()'}
        checked = {'legacy_six': {'AP_sha256': self.policy.legacy_ap, 'normalized_CP_code_sha256': self.policy.legacy_code}}
        with patch.object(p.w, 'load_sources', return_value=({'commit': 'fixture', 'archive_sha256': '00' * 32}, source)), \
             patch.object(p.w, 'catalog', return_value=checked) as catalog:
            result = p._load_policy('explicit.zip')
        catalog.assert_called_once_with(source)
        self.assertEqual(result.sources, self.policy.sources); self.assertEqual(result.descriptors_at, 0x57c6710)

    def test_cli_success_and_existing_output_protection(self):
        a, c = self.paths(); output = self.root / 'report.json'
        args = ['inspect', '--archive', 'unused', '--ap', str(a), '--cp', str(c), '--slots', '1', '6', '--output', str(output)]
        with patch.object(p, '_load_policy', return_value=self.policy): self.assertEqual(p.main(args), 0)
        raw = output.read_bytes()
        with patch.object(p, '_load_policy') as load: self.assertEqual(p.main(args), 1)
        load.assert_not_called(); self.assertEqual(output.read_bytes(), raw)
        args[-1] = str(a)
        self.assertEqual(p.main(args), 1); self.assertEqual(a.read_bytes(), self.ap['stock'])

    def test_cli_errors_do_not_expose_private_paths_or_generate_reports(self):
        a, c = self.paths(ap=bytes(16384)); output = self.root / 'absent.json'
        with patch.object(p, '_load_policy', return_value=self.policy):
            self.assertEqual(p.main(['inspect', '--archive', 'unused', '--ap', str(a), '--cp', str(c),
                                     '--slots', '1', '--output', str(output)]), 1)
        self.assertFalse(output.exists())
        bad = self.root / 'private-source.zip'; bad.write_bytes(b'not a pinned archive')
        result = subprocess.run([sys.executable, '-S', '-B', '-m', 'lutphoto.programidentity', 'requirements',
            '--archive', str(bad), '--output', str(output)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1); self.assertNotIn(str(self.root), result.stdout + result.stderr)
        self.assertFalse(output.exists())

    def test_standard_library_imports_no_device_numpy_or_archive_modules(self):
        script = "import sys; from lutphoto import programidentity; assert not any(n.split('.')[0] in {'usb','numpy','macfl23','pmca','looktool','transport'} for n in sys.modules)"
        result = subprocess.run([sys.executable, '-S', '-B', '-c', script], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
