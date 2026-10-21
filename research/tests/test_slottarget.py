"""One-slot targets on own N2/program/BK4/UXC bytes, never camera material."""
from dataclasses import replace
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch
import contextlib

from lutphoto import slottarget as t, customcontracts as c, programidentity as p, importmaterials as m
from research.tests import test_importmaterials as material_fixture, test_programidentity as program_fixture


class SlotTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate a genuine N2 offline candidate once, reuse the existing fixture.
        cls.generator = material_fixture.ImportMaterialTests
        cls.generator.setUpClass(); cls.addClassCleanup(cls.generator.doClassCleanups)

    def setUp(self):
        self.f = self.generator(methodName='runTest'); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.f.selection['slots'].pop('6'); self.f.save_selection()
        self.root = self.f.root; self.b = self.f.f
        self.own = program_fixture.ProgramIdentityTests(methodName='runTest'); self.own.setUp(); self.addCleanup(self.own.doCleanups)
        zero = bytearray(self.own.runtime_cp); zero[288:7578] = bytes(7290)
        struct.pack_into('<6I', zero, 264, *([p._fnv(bytes(1215))] * 6)); self.zero = bytes(zero)
        self.runtime = {'cp_zero_tables_sha256': p.w.sha(self.zero), 'cp_sources': []}
        for kind in ('stock', 'fl23'):
            old = self.own.cp[kind]
            self.runtime['cp_sources'].append({'kind': kind, 'windows': [
                {'offset': at, 'before': old[at:at + 4096].hex(), 'after': self.zero[at:at + 4096].hex()}
                for at in (0, 4096)]})

    def bound(self):
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(p, '_load_policy', return_value=self.b.policy))
        stack.enter_context(patch.object(t, '_runtime', return_value=self.runtime))
        return stack

    def check(self):
        with self.bound():
            return t.check_files('own', self.b.ap_path, self.b.cp_path, self.b.ram_path, self.b.saved_path,
                                 self.f.selection_path, self.f.resources, {'AP': 0, 'CP': 1}, {'AP': 0, 'CP': 1})

    def args(self, output): return self.f.args(output.resolve())

    @staticmethod
    def table(): return bytes((0, 1, 63, 192, 255)) * 243

    def test_first_import_stock_and_fl23_all_six_single_slots_match_independent_full_targets(self):
        for kind in ('stock', 'fl23'):
            for slot in range(1, 7):
                after, changes, source, target = t._programs(self.own.ap[kind], self.own.cp[kind], slot,
                                                           self.table(), self.b.policy, self.runtime)
                self.assertTrue(source['first_import']); self.assertFalse(target['first_import'])
                self.assertEqual(after['AP'], self.own.target(kind, 1 << (slot - 1)))
                expected = bytearray(self.zero); at = 288 + (slot - 1) * 1215
                expected[at:at + 1215] = self.table(); struct.pack_into('<I', expected, 264 + (slot - 1) * 4, p._fnv(self.table()))
                self.assertEqual(after['CP'], bytes(expected))
                self.assertEqual(t._apply(after['AP'], t._inverse(changes['AP'])), self.own.ap[kind])
                self.assertEqual(t._apply(after['CP'], t._inverse(changes['CP'])), self.own.cp[kind])

    def test_standalone_update_unions_masks_and_preserves_five_tables_and_checksums(self):
        for kind in ('stock', 'fl23'):
            for mask, slot in ((1, 6), (32, 1), (63, 3), (8, 4)):
                ap, cp = self.own.target(kind, mask), self.own.runtime_cp
                after, changes, _, target = t._programs(ap, cp, slot, bytes(1215), self.b.policy)
                self.assertEqual(target['mask'], mask | 1 << (slot - 1))
                self.assertEqual(after['AP'], self.own.target(kind, target['mask']))
                expected = bytearray(cp); at = 288 + (slot - 1) * 1215
                expected[at:at + 1215] = bytes(1215); struct.pack_into('<I', expected, 264 + (slot - 1) * 4, p._fnv(bytes(1215)))
                self.assertEqual(after['CP'], bytes(expected))
                self.assertEqual(t._apply(after['CP'], t._inverse(changes['CP'])), cp)

    def test_legacy_layout_keeps_entire_ap_and_rejects_standalone_cp(self):
        for slot in range(1, 7):
            after, changes, source, target = t._programs(self.own.legacy_ap, self.own.legacy_cp, slot, bytes(1215), self.b.policy)
            self.assertEqual(after['AP'], self.own.legacy_ap); self.assertEqual(changes['AP'].changes, ())
            self.assertEqual(source['layout'], 'full7-v4'); self.assertEqual(target['mask'], 63)
        with self.assertRaises(ValueError): t._programs(self.own.legacy_ap, self.own.runtime_cp, 1, self.table(), self.b.policy)

    def test_whole_source_and_target_hashes_are_required_in_both_directions(self):
        before, after = b'abcdefghij', b'aBCdefghij'; plan = t._transition(before, after, [(1, 2)])
        for raw, transition in ((b'abcdefghik', plan), (b'aBCdefghik', t._inverse(plan)),
                                (before, replace(plan, after_sha='00' * 32))):
            with self.assertRaises(ValueError): t._apply(raw, transition)
        with self.assertRaises(ValueError): t._transition(before, b'aBCdefghiK', [(1, 2)])
        self.assertEqual(t._apply(t._apply(before, plan), t._inverse(plan)), before)

    def test_transition_rejects_overlap_bounds_bool_resize_and_mismatched_window_bytes(self):
        raw = bytes(8192)
        for spans in ([(0, 4), (3, 2)], [(-1, 1)], [(True, 1)], [(0, True)], [(0, 4097)], [(8191, 2)], [(0, 0)]):
            with self.subTest(spans=spans), self.assertRaises(ValueError): t._transition(raw, raw, spans)
        with self.assertRaises(ValueError): t._transition(raw, raw + b'x', [])
        bad = t._Transition(8192, p.w.sha(raw), p.w.sha(raw), (t._Change(0, b'x', b'\0'),))
        with self.assertRaises(ValueError): t._apply(raw, bad)
        self.assertEqual(t._transition(raw, raw, []).changes, ())

    def test_first_import_difference_grouping_covers_gaps_and_exact_4096_limit(self):
        raw = bytes(9000); changed = bytearray(raw)
        for at in (0, 16, 33, 34, 4095, 4096, 8191, 8192): changed[at] = 1
        spans = t._diff_spans(raw, bytes(changed))
        self.assertEqual(spans, [(0, 17), (33, 2), (4095, 2), (8191, 2)])
        self.assertEqual(t._diff_spans(bytes(8193), b'\1' * 8193), [(0, 4096), (4096, 4096), (8192, 1)])
        t._transition(raw, bytes(changed), spans)
        with self.assertRaises(ValueError): t._diff_spans(b'a', b'ab')
        with patch.object(t, 'MAX_WINDOWS', 1), self.assertRaises(ValueError): t._diff_spans(bytes(100), b'\1' + bytes(98) + b'\1')

    def test_bootstrap_before_bytes_and_canonical_complete_hash_cannot_be_relaxed(self):
        import copy
        for change in ('before', 'after', 'hash'):
            runtime = copy.deepcopy(self.runtime)
            if change == 'hash': runtime['cp_zero_tables_sha256'] = '00' * 32
            else: runtime['cp_sources'][0]['windows'][0][change] = 'ff' + runtime['cp_sources'][0]['windows'][0][change][2:]
            with self.assertRaises(ValueError):
                t._programs(self.own.ap['stock'], self.own.cp['stock'], 1, self.table(), self.b.policy, runtime)

    def test_single_slot_report_binds_complete_inputs_and_all_68_resource_targets(self):
        result = self.check(); self.assertEqual(result['schema'], t.SCHEMA)
        self.assertTrue(result['complete_program_transition_verified']); self.assertTrue(result['scoped_settings_transition_verified'])
        self.assertEqual(result['settings']['selected_fields'], 9); self.assertEqual(len(result['resources']), 68)
        self.assertEqual(result['unselected_table_reference'], 'canonical-zero-runtime')
        self.assertEqual(result['unselected_tables_and_checksums_preserved'], 5)
        for row in result['programs'].values(): self.assertEqual(row['before_sha256'], row['restored_sha256'])
        for row in result['resources'].values(): self.assertEqual(row['before_sha256'], row['restored_sha256'])
        self.assertEqual(result['target_review_sha256'], self.check()['target_review_sha256'])

    def test_only_one_slot_is_accepted_before_program_or_candidate_reads(self):
        self.f.selection['slots']['6'] = self.f.selection['slots']['1']; self.f.save_selection()
        with patch.object(p, '_load_policy') as policy, self.assertRaises(ValueError):
            t.check_files(None, None, None, None, None, self.f.selection_path, None, {}, {})
        policy.assert_not_called()

    def test_unknown_program_and_unsaved_scope_refuse_before_candidate_or_resources(self):
        for case in ('program', 'unsaved'):
            if case == 'program': self.b.ap_path.write_bytes(bytes(16384))
            else:
                self.b.ap_path.write_bytes(self.own.ap['stock'])
                changed = dict(self.b.ap); changed[0x02cf0400] = replace(changed[0x02cf0400], data=b'Z')
                self.b.write(self.b.saved_path, ap=changed)
            with patch.object(m, '_candidate_content') as candidate, patch.object(c, '_resource_files') as resources:
                with self.assertRaises(ValueError): self.check()
            candidate.assert_not_called(); resources.assert_not_called()

    def test_scoped_settings_match_st_and_preserve_metadata_diagnostic_and_cp_exactly(self):
        for chip, key in (('AP', 0x02cf0101), ('AP', 0x02cf0201), ('CP', next(iter(self.b.cp)))):
            rows = dict(self.b.ap if chip == 'AP' else self.b.cp); old = rows[key]
            rows[key] = replace(old, attr=old.attr | 4, reset_data=b'R' * len(old.data), max_size=16)
            self.b.write(self.b.ram_path, **{'ap' if chip == 'AP' else 'cp': rows})
            self.b.write(self.b.saved_path, **{'ap' if chip == 'AP' else 'cp': rows})
            bindings = p._descriptor_bindings(self.b.ap_path.read_bytes(), [1], self.b.policy)
            ram, rs, _ = t.s._snapshot(self.b.ram_path, {'AP': 0, 'CP': 1})
            saved, ss, _ = t.s._snapshot(self.b.saved_path, {'AP': 0, 'CP': 1})
            targets, scopes, report = t._settings(bindings, ram, saved, rs, ss)
            self.assertEqual(targets[0][0][0x02cf0101].data, b'\0')
            for i in range(8): self.assertEqual(targets[0][0][0x02cf0201 + i * 8].data, ram[0][0x02cf0300 + i].data)
            self.assertEqual(scopes[0]['CP'], rs['CP']); self.assertEqual(scopes[0]['AP'][0x02cf0b6e], rs['AP'][0x02cf0b6e])
            for k in rs[chip]:
                a, b = rs[chip][k], scopes[0][chip][k]
                self.assertEqual((a.attr, a.reset_data, a.max_size), (b.attr, b.reset_data, b.max_size))
            self.assertFalse(report['full_BK4_target_generated']); self.assertFalse(report['complete_settings_transition_verified'])

    def test_descriptor_remapping_controls_settings_targets_instead_of_assumed_keys(self):
        raw = bytearray(self.b.ap_path.read_bytes()); struct.pack_into('<I', raw, 4096 + 10 * 32 + 4, 0x02cf0400)
        self.b.replace_program(bytes(raw)); rows = dict(self.b.ap); del rows[0x02cf0101]
        self.b.write(self.b.ram_path, ap=rows); self.b.write(self.b.saved_path, ap=rows)
        bindings = p._descriptor_bindings(bytes(raw), [1], self.b.policy)
        ram, rs, _ = t.s._snapshot(self.b.ram_path, {'AP': 0, 'CP': 1})
        after, _, report = t._settings(bindings, ram, ram, rs, rs)
        self.assertEqual(after[0][0][0x02cf0400].data, b'\0'); self.assertEqual(report['selected_fields'], 9)
        self.assertTrue(self.check()['scoped_settings_transition_verified'])

    def test_names_follow_source_layout_and_stock_resources_fill_missing_labels_with_st(self):
        for kind, imported in (('stock', False), ('stock-lut', True), ('legacy-six', True)):
            self.f.write_resources(imported)
            if kind == 'stock-lut': self.b.ap_path.write_bytes(self.own.target('stock', 2)); self.b.cp_path.write_bytes(self.own.runtime_cp)
            elif kind == 'legacy-six': self.b.ap_path.write_bytes(self.own.legacy_ap); self.b.cp_path.write_bytes(self.own.legacy_cp)
            report = self.check(); self.assertEqual(report['label_layout_derived_from_program'], 'legacy-six' if kind == 'legacy-six' else 'standalone')
            raw = c.synthetic_resource(imported); ids = c.LAYOUTS[report['label_layout_derived_from_program']]
            target, _ = c.resources.rename(raw, {1: 'Own Film A'}, ids)
            self.assertEqual(next(iter(report['resources'].values()))['after_sha256'], p.w.sha(target))
        self.f.write_resources(False)
        with self.assertRaises(ValueError): self.check()

    def test_mixed_missing_extra_or_linked_resources_are_rejected_without_report(self):
        name = c.RESOURCE_FILES[0]; path = self.f.resources / name; raw = path.read_bytes()
        path.write_bytes(c.synthetic_resource(False))
        with self.assertRaises(ValueError): self.check()
        path.write_bytes(raw); extra = self.f.resources / 'extra'; extra.write_bytes(b'own')
        with self.assertRaises(ValueError): self.check()
        extra.unlink(); path.unlink()
        with self.assertRaises(ValueError): self.check()
        path.symlink_to(self.b.ram_path)
        with self.assertRaises(OSError): self.check()

    def test_candidate_is_read_once_and_changed_table_fails_before_target_construction(self):
        with patch.object(m, '_candidate_content', wraps=m._candidate_content) as candidate:
            self.check()
        self.assertEqual(candidate.call_count, 1)
        (self.f.candidate / 'correction.table').write_bytes(b'\1' * 1215)
        with patch.object(t, '_programs') as generate, self.assertRaises(ValueError): self.check()
        generate.assert_not_called()

    def test_private_report_has_no_payload_paths_names_keys_or_unverified_physical_claims(self):
        report = self.check(); text = json.dumps(report)
        self.assertTrue(report['private_report']); self.assertFalse(report['payloads_exported'])
        for key in ('actual_source_identity_verified', 'native_execution_verified', 'physical_validation_verified',
                    'same_capture_provenance_verified', 'snapshot_freshness_verified', 'independent_backups_verified',
                    'complete_settings_transition_verified', 'firmware_or_settings_write_plan_enabled', 'camera_deployment_enabled'):
            self.assertFalse(report[key], key)
        for secret in (str(self.root), 'Own Film A', '02cf0101', '02cf0300', 'before_hex', 'after_hex', 'before_ram', 'CP-OWN'):
            self.assertNotIn(secret, text)

    def test_cli_private_new_output_and_inputs_are_preserved(self):
        inputs = [self.b.ap_path, self.b.cp_path, self.b.ram_path, self.b.saved_path,
                  self.f.selection_path, *(self.f.candidate.iterdir()), *(self.f.resources.iterdir())]
        original = {path: (path.read_bytes(), path.stat()) for path in inputs}; output = self.root / 'slot.private.json'
        with self.bound(): self.assertEqual(t.main(self.args(output)), 0)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600); raw = output.read_bytes()
        with patch.object(t, 'check_files') as check: self.assertEqual(t.main(self.args(output)), 1)
        check.assert_not_called(); self.assertEqual(output.read_bytes(), raw)
        for path, (content, info) in original.items():
            self.assertEqual(path.read_bytes(), content)
            self.assertEqual((path.stat().st_ino, path.stat().st_mtime_ns, path.stat().st_ctime_ns), (info.st_ino, info.st_mtime_ns, info.st_ctime_ns))

    def test_cli_refuses_shared_or_repo_output_before_reading_materials(self):
        shared = self.root / 'shared'; shared.mkdir(mode=0o755)
        for output in (shared / 'new.json', Path(__file__).resolve().parents[1] / 'own-output.json'):
            with patch.object(t, 'check_files') as check: self.assertEqual(t.main(self.args(output)), 1)
            check.assert_not_called(); self.assertFalse(output.exists())

    def test_cli_refuses_linked_output_parent_and_report_delivery_failure(self):
        link = self.root / 'linked-output'; link.symlink_to(self.root, target_is_directory=True)
        args = self.args(self.root / 'not-created.private.json'); args[-1] = str(link / 'not-created.private.json')
        with patch.object(t, 'check_files') as check: self.assertEqual(t.main(args), 1)
        check.assert_not_called()
        output = self.root / 'delivery.private.json'
        with self.bound(), patch.object(t, 'write_bytes_new', side_effect=OSError('Own failed delivery')):
            self.assertEqual(t.main(self.args(output)), 1)
        self.assertFalse(output.exists())

    def test_runtime_requires_same_pinned_archive_and_never_executes_source_python(self):
        source = {'src/looks/assets/runtime-v1.json': json.dumps(self.runtime).encode(), 'own.py': b'raise AssertionError()'}
        policy = self.b.policy; pin = {'commit': policy.commit, 'archive_sha256': policy.archive_sha}
        with patch.object(p.w, 'load_sources', return_value=(pin, source)), patch.object(p.w, 'catalog') as catalog:
            self.assertEqual(t._runtime('own', policy), self.runtime)
        catalog.assert_called_once_with(source)
        for changed in (replace(policy, commit='different'), replace(policy, archive_sha='ff' * 32)):
            with patch.object(p.w, 'load_sources', return_value=(pin, source)), patch.object(p.w, 'catalog'):
                with self.assertRaises(ValueError): t._runtime('own', changed)

    def test_real_no_site_cli_refuses_bad_source_and_unknown_options_without_private_echo(self):
        bad = self.root / 'private.zip'; bad.write_bytes(b'own bad source'); output = self.root / 'new.private.json'
        args = self.args(output); args[1] = str(bad)
        command = [sys.executable, '-S', '-B', '-m', 'lutphoto.slottarget']
        result = subprocess.run(command + args, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1); self.assertNotIn(str(self.root), result.stdout + result.stderr)
        for addition in (['--enable'], ['--policy', str(self.root)], ['--slots', '1'], ['--ram-roles', str(self.root), '1']):
            result = subprocess.run(command + args + addition, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2); self.assertNotIn(str(self.root), result.stdout + result.stderr)
        self.assertFalse(output.exists())

    def test_standard_library_import_and_help_have_no_device_numpy_or_archive_execution(self):
        script = "import sys; from lutphoto import slottarget; assert not any(n.split('.')[0] in {'usb','numpy','macfl23','pmca','looktool','transport'} for n in sys.modules)"
        result = subprocess.run([sys.executable, '-S', '-B', '-c', script], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        help_result = subprocess.run([sys.executable, '-S', '-B', '-m', 'lutphoto.slottarget', '--help'], capture_output=True, timeout=10)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)


if __name__ == '__main__': unittest.main()
