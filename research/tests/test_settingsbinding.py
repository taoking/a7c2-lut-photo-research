"""Descriptor-derived local snapshot checks with own programs and BK4 data."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import bk4 as b, programidentity as p, settingsbinding as s
from research.tests import test_programidentity as program_fixture


class SettingsBindingTests(unittest.TestCase):
    def setUp(self):
        fixture = program_fixture.ProgramIdentityTests(methodName='runTest'); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root, self.policy = fixture.root, fixture.policy
        self.ap_path, self.cp_path = fixture.paths()
        self.ram_path, self.saved_path = self.root / 'ram.bin', self.root / 'saved.bin'
        self.ap = {0x02cf0300 + i: b.Property(2, struct.pack('<I', i + 10), None, 4) for i in range(8)}
        for slot in range(1, 7):
            self.ap[0x02cf0100 + slot] = b.Property(0, b'\x01', None, 1)
            for i in range(8):
                self.ap[0x02cf0200 + i * 8 + slot] = b.Property(0, struct.pack('<I', i + 10 + slot), None, 4)
        self.ap[0x02cf0b6e] = b.Property(64, bytes(4), bytes(4), 4)
        self.ap[0x02cf0400] = b.Property(0, b'U', None, 1)
        self.ap[0x02770015] = b.Property(0, b'X', None, 1)
        self.cp = {key: b.Property(2, b'CP-OWN', None, 6) for key in b.c.devicesettings.PROTECTED}
        self.write(self.ram_path); self.write(self.saved_path)

    def write(self, path, ap=None, cp=None, reverse=False):
        images = [b.fixture_image(self.ap if ap is None else ap), b.fixture_image(self.cp if cp is None else cp)]
        path.write_bytes(b'OWN CONTAINER' + b''.join(reversed(images) if reverse else images) + b'OWN TAIL')

    def check(self, slots=(1, 6), ram_roles=None, saved_roles=None):
        with patch.object(p, '_load_policy', return_value=self.policy):
            return s.check_files('unused', self.ap_path, self.cp_path, self.ram_path, self.saved_path, slots,
                {'AP': 0, 'CP': 1} if ram_roles is None else ram_roles,
                {'AP': 0, 'CP': 1} if saved_roles is None else saved_roles)

    def replace_program(self, raw):
        self.ap_path.write_bytes(raw)
        sources = list(self.policy.sources); sources[0] = replace(sources[0], ap_sha=p.w.sha(raw))
        self.policy = replace(self.policy, sources=tuple(sources))  # Own fixture identity only; never a CLI policy option.

    def args(self, output):
        return ['--archive', 'unused', '--ap', str(self.ap_path), '--cp', str(self.cp_path),
                '--ram', str(self.ram_path), '--saved', str(self.saved_path), '--slots', '1', '6',
                '--ram-roles', '0', '1', '--saved-roles', '0', '1', '--output', str(output)]

    def test_all_six_slots_have_descriptor_derived_fields_and_immutable_bindings(self):
        report = self.check(list(range(1, 7)))
        self.assertEqual(report['descriptors']['selected_fields'], 54)
        self.assertEqual(report['descriptors']['ST_reference_fields'], 8)
        self.assertEqual(report['values']['selected_fields_equal_ST'], 0)
        bindings = p._descriptor_bindings(self.ap_path.read_bytes(), [1], self.policy)
        self.assertEqual([f.size for f in bindings.fields], [1] + [4] * 8)
        self.assertEqual([f.reference for f in bindings.fields], [None] + [0x02cf0300 + i for i in range(8)])
        with self.assertRaises(FrozenInstanceError): bindings.fields[0].key = 0

    def test_descriptor_key_remapping_uses_rows_instead_of_assumed_keys(self):
        raw = bytearray(self.ap_path.read_bytes())
        struct.pack_into('<I', raw, 4096 + 10 * 32 + 4, 0x02cf0400)
        self.replace_program(bytes(raw))
        ap = dict(self.ap); del ap[0x02cf0101]
        self.write(self.ram_path, ap); self.write(self.saved_path, ap)
        self.assertTrue(self.check()['provided_snapshot_structure_and_values_checked'])
        del ap[0x02cf0400]; self.write(self.ram_path, ap)
        with self.assertRaisesRegex(ValueError, 'Selected'): self.check()

    def test_missing_selected_or_st_fields_on_either_snapshot_rejected(self):
        for path in (self.ram_path, self.saved_path):
            for key in (0x02cf0101, 0x02cf0201, 0x02cf0300):
                ap = dict(self.ap); del ap[key]; self.write(path, ap)
                with self.subTest(key=key, file=path.name), self.assertRaises(ValueError): self.check()
                self.write(path)

    def test_base_adjustment_and_st_length_mismatches_rejected(self):
        for key, size in ((0x02cf0101, 4), (0x02cf0201, 1), (0x02cf0300, 1)):
            ap = dict(self.ap); ap[key] = b.Property(0, bytes(size), None, size)
            self.write(self.ram_path, ap); self.write(self.saved_path, ap)
            with self.subTest(key=key), self.assertRaises(ValueError): self.check()

    def test_selected_protected_attribute_bits_rejected_but_readonly_st_is_allowed(self):
        self.assertTrue(self.check()['values']['descriptor_field_sizes_and_selected_attributes_checked'])
        for attr in (1, 2, 3):
            ap = dict(self.ap); ap[0x02cf0101] = replace(ap[0x02cf0101], attr=attr)
            self.write(self.ram_path, ap); self.write(self.saved_path, ap)
            with self.subTest(attr=attr), self.assertRaisesRegex(ValueError, 'protected'): self.check()

    def test_selected_ram_saved_difference_rejected(self):
        ap = dict(self.ap); ap[0x02cf0101] = replace(ap[0x02cf0101], data=b'\x02')
        self.write(self.saved_path, ap)
        with self.assertRaisesRegex(ValueError, 'recipe differs'): self.check()

    def test_unsaved_unselected_and_st_values_rejected(self):
        for key in (0x02cf0400, 0x02cf0300, 0x02cf0102):
            ap = dict(self.ap); old = ap[key]; ap[key] = replace(old, data=bytes([99]) + old.data[1:])
            self.write(self.saved_path, ap)
            with self.subTest(key=key), self.assertRaises(ValueError): self.check()

    def test_saved_only_or_missing_scope_fields_rejected_in_both_directions(self):
        for path in (self.ram_path, self.saved_path):
            ap = dict(self.ap); ap[0x02cf0401] = b.Property(0, b'A', None, 1); self.write(path, ap)
            with self.assertRaises(ValueError): self.check()
            self.write(path)

    def test_each_protected_cp_unit_missing_or_changed_rejected(self):
        for key in self.cp:
            for missing in (False, True):
                cp = dict(self.cp)
                if missing: del cp[key]
                else: cp[key] = replace(cp[key], data=b'CP-BAD')
                self.write(self.saved_path, cp=cp)
                with self.subTest(key=key, missing=missing), self.assertRaises(ValueError): self.check()

    def test_diagnostic_value_is_volatile_but_layout_and_reset_remain_checked(self):
        key = 0x02cf0b6e; ap = dict(self.ap); ap[key] = replace(ap[key], data=b'\x99\0\0\0')
        self.write(self.saved_path, ap)
        self.assertFalse(self.check()['values']['diagnostic_value_compared'])
        for value in (replace(ap[key], attr=0, reset_data=None), replace(ap[key], max_size=8),
                      replace(ap[key], reset_data=b'xxxx'), b.Property(64, b'X', b'X', 1)):
            ap[key] = value; self.write(self.saved_path, ap)
            with self.assertRaises(ValueError): self.check()

    def test_unrelated_runtime_groups_can_differ_without_preservation_claim(self):
        ap = dict(self.ap); ap[0x02770015] = replace(ap[0x02770015], data=b'Y')
        self.write(self.saved_path, ap)
        result = self.check()
        self.assertFalse(result['values']['other_runtime_groups_compared'])
        self.assertNotEqual(result['snapshots']['ram']['sha256'], result['snapshots']['saved']['sha256'])

    def test_reset_changes_in_selected_unselected_st_and_cp_are_rejected(self):
        for chip, key in (('AP', 0x02cf0101), ('AP', 0x02cf0400), ('AP', 0x02cf0300), ('CP', next(iter(self.cp)))):
            rows = dict(self.ap if chip == 'AP' else self.cp); old = rows[key]
            rows[key] = replace(old, attr=old.attr | 4, reset_data=bytes(len(old.data)))
            kwargs = {'ap' if chip == 'AP' else 'cp': rows}
            self.write(self.ram_path, **kwargs); self.write(self.saved_path, **kwargs)
            self.assertTrue(self.check()['values']['scoped_reset_and_layout_equal'])
            rows[key] = replace(rows[key], reset_data=b'R' * len(old.data)); self.write(self.saved_path, **kwargs)
            with self.subTest(chip=chip, key=key), self.assertRaisesRegex(ValueError, 'reset'): self.check()
            self.write(self.ram_path); self.write(self.saved_path)

    def test_allocation_changes_with_same_values_and_attributes_are_rejected(self):
        for chip, key in (('AP', 0x02cf0101), ('CP', next(iter(self.cp)))):
            rows = dict(self.ap if chip == 'AP' else self.cp); rows[key] = replace(rows[key], max_size=16)
            self.write(self.saved_path, **{'ap' if chip == 'AP' else 'cp': rows})
            with self.assertRaisesRegex(ValueError, 'layout'): self.check()
            self.write(self.saved_path)

    def test_high_attribute_bits_never_truncated(self):
        ap = dict(self.ap); ap[0x02cf0400] = replace(ap[0x02cf0400], attr=0x100)
        self.write(self.saved_path, ap)
        with self.assertRaisesRegex(ValueError, 'high attribute'): self.check()

    def test_st_match_counts_are_derived_without_requiring_existing_recipes_to_match(self):
        self.assertFalse(self.check()['values']['all_selected_fields_equal_ST'])
        ap = dict(self.ap)
        for slot in (1, 6):
            ap[0x02cf0100 + slot] = replace(ap[0x02cf0100 + slot], data=bytes(1))
            for i in range(8):
                key = 0x02cf0200 + i * 8 + slot; ap[key] = replace(ap[key], data=ap[0x02cf0300 + i].data)
        self.write(self.ram_path, ap); self.write(self.saved_path, ap)
        values = self.check()['values']
        self.assertEqual(values['selected_fields_equal_ST'], 18); self.assertTrue(values['all_selected_fields_equal_ST'])

    def test_roles_are_separate_explicit_assertions_and_never_auto_reordered(self):
        for roles in ({}, {'AP': True, 'CP': 0}, {'AP': 0, 'CP': 0}, {'AP': 1, 'CP': 0}):
            with self.assertRaises(ValueError): self.check(saved_roles=roles)
        self.write(self.saved_path, reverse=True)
        with self.assertRaises(ValueError): self.check()
        self.assertTrue(self.check(saved_roles={'AP': 1, 'CP': 0})['roles_are_caller_assertions'])

    def test_identical_or_old_snapshot_bytes_never_prove_freshness_or_same_body(self):
        with patch.object(p, '_load_policy', return_value=self.policy):
            report = s.check_files('unused', self.ap_path, self.cp_path, self.ram_path, self.ram_path, [1],
                                   {'AP': 0, 'CP': 1}, {'AP': 0, 'CP': 1})
        self.assertEqual(report['snapshots']['ram']['sha256'], report['snapshots']['saved']['sha256'])
        for key in ('snapshot_freshness_verified', 'same_capture_provenance_verified', 'chip_roles_verified',
                    'body_binding_verified', 'outer_wrapper_verified', 'container_complete_backup_verified'):
            self.assertFalse(report[key])

    def test_unknown_program_or_alias_descriptor_rejected_before_snapshots_open(self):
        original = self.ap_path.read_bytes(); self.ap_path.write_bytes(bytes(len(original)))
        with patch.object(s, '_snapshot') as read, self.assertRaises(ValueError): self.check()
        read.assert_not_called()
        raw = bytearray(original); struct.pack_into('<I', raw, 4096 + (0x1520 + 10 - 0x14ea) * 32 + 4, 0x02cf0101)
        self.replace_program(bytes(raw))
        with patch.object(s, '_snapshot') as read, self.assertRaises(ValueError): self.check()
        read.assert_not_called()

    def test_private_report_contains_no_setting_keys_values_targets_or_paths(self):
        report = self.check(); text = json.dumps(report)
        self.assertTrue(report['private_report']); self.assertTrue(report['provided_snapshot_structure_and_values_checked'])
        for key in p.w.boundary(): self.assertFalse(report[key])
        self.assertFalse(report['settings_write_plan_enabled']); self.assertFalse(report['descriptors']['write_plan_enabled'])
        for private in (str(self.root), '02cf0101', '02cf0300', 'CP-OWN', 'before_ram', 'after', 'reference_key'):
            self.assertNotIn(private, text)

    def test_snapshot_checksum_and_links_rejected(self):
        raw = bytearray(self.saved_path.read_bytes()); raw[-9] ^= 1; self.saved_path.write_bytes(raw)
        with self.assertRaises(ValueError): self.check()
        self.saved_path.unlink(); self.saved_path.symlink_to(self.ram_path)
        with self.assertRaises(OSError): self.check()

    def test_cli_fixture_integration_preserves_four_inputs_and_existing_outputs(self):
        paths = (self.ap_path, self.cp_path, self.ram_path, self.saved_path)
        original = [f.read_bytes() for f in paths]; output = self.root / 'binding.json'
        with patch.object(p, '_load_policy', return_value=self.policy): self.assertEqual(s.main(self.args(output)), 0)
        report = output.read_bytes()
        with patch.object(p, '_load_policy') as load: self.assertEqual(s.main(self.args(output)), 1)
        load.assert_not_called(); self.assertEqual(output.read_bytes(), report)
        for path in paths: self.assertEqual(s.main(self.args(path)), 1)
        self.assertEqual(original, [f.read_bytes() for f in paths])

    def test_actual_cli_rejects_bad_archive_without_path_leak_or_report(self):
        source = self.root / 'private.zip'; source.write_bytes(b'own corrupt archive')
        output = self.root / 'absent.json'; args = self.args(output); args[1] = str(source)
        result = subprocess.run([sys.executable, '-S', '-B', '-m', 'lutphoto.settingsbinding', *args],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1); self.assertFalse(output.exists())
        self.assertNotIn(str(self.root), result.stdout + result.stderr)
        result = subprocess.run([sys.executable, '-S', '-B', '-m', 'lutphoto.settingsbinding', *args, '--expected', '{}'],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)  # No externally supplied keys/targets contract.

    def test_standard_library_import_does_not_load_device_or_numpy(self):
        script = "import sys; from lutphoto import settingsbinding; assert not any(n.split('.')[0] in {'usb','numpy','macfl23','pmca','looktool','transport'} for n in sys.modules)"
        result = subprocess.run([sys.executable, '-S', '-B', '-c', script], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
