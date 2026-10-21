"""Own frozen inputs -> pinned name metadata, compiler and report boundaries."""
import contextlib
from dataclasses import replace
import fcntl
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import nameworker as q
from research.tests import test_slotbundle as fixtures


class NameWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SlotBundleTests.setUpClass(); cls.addClassCleanup(fixtures.SlotBundleTests.doClassCleanups)

    def setUp(self):
        self.f = fixtures.SlotBundleTests(methodName='runTest'); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.root, self.directory = self.f.root, self.f.directory
        self.pin = {'files': {'src/looks/native/names.c': {'sha256': '22' * 32}}}

    def bound(self):
        stack = self.f.f.bound()
        stack.enter_context(patch.object(q.program, '_sources', return_value=(self.pin, {})))
        return stack

    def review(self, **kwargs):
        with self.bound(): return q.review_bundle('own', self.directory, **kwargs)

    def create(self): return self.f.create(self.directory)

    def args(self, output=None):
        return ['review', '--archive', 'own', '--directory', str(self.directory),
                '--output', str(output or self.root / 'names.private.json')]

    def cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with self.bound(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err): code = q.main(args)
        return code, out.getvalue(), err.getvalue()

    def packet(self, mode, contract=None, counts=None):
        c = self.review()['names_contract'] if contract is None else contract
        counters = counts if counts is not None else ((68, 68, 68, 0, 0) if mode == 1 else
                    (9, 0, 0, 12, 56) if mode == 2 else (0, 0, 0, 0, 68) if mode == 3 else (0, 0, 0, 0, 0))
        return struct.pack('<8s4I7q6I32s', b'A7NMR001', 1, mode, 9, 68, 0, 0, 0, 0, 0, 0, 17,
                           *counters, 0, bytes.fromhex(c['target_AP' if mode == 3 else 'AP']))

    @staticmethod
    def native_target(raw, name, slot, ids):
        # Independent oracle for the C's append/index rules, never target execution.
        result = bytearray(raw); count = struct.unpack_from('<I', raw, 12)[0] & 8191
        if count == 2860:
            result[5736:5736] = b'\xff' * 12; struct.pack_into('<I', result, 12, 2866 | (2866 << 12))
        base = 5748
        for j, rid in enumerate(ids, 1):
            if j != slot and count == 2866: continue
            text = (name if j == slot else 'ST').encode()
            struct.pack_into('<H', result, 16 + 2 * ((rid & 0xffffff) - 0xa000), (len(result) - base) // 4)
            result.extend(struct.pack('<I', 0x1e000000 | (rid & 0xffffff)) + text + b'\0')
            result.extend(bytes((-len(result)) % 4))
        return bytes(result)

    def test_metadata_binds_all_68_originals_targets_pointers_and_both_complete_ap_states(self):
        self.create()
        with self.bound(), q.b._open_bundle('own', self.directory) as (policy, inputs, review, binding):
            header, c = q._metadata(inputs, review, binding); text = header.decode()
            self.assertEqual(list(c['files']), list(q.b.c.RESOURCE_FILES)); self.assertEqual(c['count'], 68)
            self.assertEqual(c['AP'], q.w.sha(inputs.ap)); self.assertEqual(c['target_AP'], q.w.sha(review.programs['AP']))
            self.assertNotEqual(c['AP'], c['target_AP'])
            self.assertIn('selected_mask=1;', text); self.assertIn('original_uid=57285,original_gid=1000', text)
            self.assertIn('/usr/share/app/.a7c2-lut-' + c['offline_job_id'] + '-', text)
            self.assertRegex(c['offline_job_id'], '^[0-9a-f]{16}$')
            for filename, info in c['files'].items():
                source, target = inputs.resources[filename], review.resources[filename]
                self.assertEqual(info['before_sha256'], q.w.sha(source)); self.assertEqual(info['after_sha256'], q.w.sha(target))
                self.assertEqual(info['before_bytes'], len(source)); self.assertEqual(info['after_bytes'], len(target))
                self.assertIn(json.dumps(filename), text)
                decoded = q.b.c.decode_resource(source)
                row = '{' + ','.join(str(decoded['entries'][rid]['pointer']) for rid in c['label_ids']) + '}'
                self.assertIn(row, text)
        result = self.review(); self.assertEqual(result['manifest_header_sha256'], q.w.sha(header))
        self.assertEqual(result['contract_sha256'], q.w.sha(q.encoded(c))); self.assertEqual(c, result['names_contract'])
        for key in q.w.boundary(): self.assertFalse(result[key])

    def test_two_resource_layouts_six_slots_match_independent_native_append_oracle(self):
        selection = self.f.f.f
        for imported in (False, True):
            raw = q.b.c.synthetic_resource(imported)
            for path in self.f.kwargs['resources_path'].iterdir(): path.write_bytes(raw)
            for slot in range(1, 7):
                selection.selection['slots'] = {str(slot): {'candidate': 'candidates/own', 'name': 'Own 胶片 "\\'}}
                # Preserve the fixture's actual candidate-relative directory.
                if not hasattr(self, 'relative'):
                    original = q.b.c.decode_json(self.f.kwargs['selection_path'].read_bytes())
                    self.relative = next(iter(original['slots'].values()))['candidate']
                selection.selection['slots'][str(slot)]['candidate'] = self.relative; selection.save_selection()
                self.directory = self.root / f'resource-{imported}-{slot}'; self.create()
                with self.bound(), q.b._open_bundle('own', self.directory) as (_, inputs, review, binding):
                    header, c = q._metadata(inputs, review, binding)
                    for filename in q.b.c.RESOURCE_FILES:
                        self.assertEqual(review.resources[filename], self.native_target(raw, 'Own 胶片 "\\', slot, c['label_ids']))
                    self.assertIn(q.w.cbytes(('Own 胶片 "\\\0').encode()).encode(), header)
                    self.assertEqual(c['selected_mask'], 1 << (slot - 1))
                    self.assertEqual({r['before_count'] for r in c['files'].values()}, {2866 if imported else 2860})
                    if not imported: self.assertIn(('{' + ','.join(['65535'] * 6) + '}').encode(), header)

    def test_all_program_routes_derive_label_order_and_exact_ap_hashes(self):
        own = self.f.f.own
        for kind, ap, cp in (('fl23', own.ap['fl23'], own.cp['fl23']),
                             ('stock-lut', own.target('stock', 32), own.runtime_cp),
                             ('fl23-lut', own.target('fl23', 32), own.runtime_cp),
                             ('legacy-six', own.legacy_ap, own.legacy_cp)):
            self.f.kwargs['ap_path'].write_bytes(ap); self.f.kwargs['cp_path'].write_bytes(cp)
            self.directory = self.root / kind; self.create()
            with patch.object(q.w, '_compile_one') as compiler: result = self.review()
            compiler.assert_not_called(); c = result['names_contract']; self.assertEqual(c['AP'], q.w.sha(ap))
            expected = q.b.c.LAYOUTS['legacy-six' if kind == 'legacy-six' else 'standalone']
            self.assertEqual(c['label_ids'], list(expected)); self.assertFalse(result['compiled_offline'])
            if kind == 'legacy-six': self.assertEqual(c['AP'], c['target_AP'])

    def test_zero_program_windows_still_bind_and_compile_name_work(self):
        self.f.kwargs['ap_path'].write_bytes(self.f.f.own.target('stock', 1))
        self.f.kwargs['cp_path'].write_bytes(self.f.f.zero); self.assertEqual(self.create()['program_change_windows'], 0)
        with patch.object(q.w, '_compile_one', return_value={'target_code_executed': False}) as compiler:
            result = self.review(compile_names=True)
        compiler.assert_called_once(); self.assertTrue(result['compiled_offline']); self.assertEqual(result['names_contract']['count'], 68)
        self.assertEqual(result['names_contract']['AP'], result['names_contract']['target_AP'])

    def test_compiler_receives_names_metadata_under_shared_lock_and_releases_it(self):
        self.create()
        def compiled(sources, kind, header):
            self.assertEqual(kind, 'names'); self.assertIn(b'asset_count=68', header)
            with (self.directory / 'session.lock').open('rb') as stream:
                with self.assertRaises(BlockingIOError): fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return {'target_code_executed': False}
        with patch.object(q.w, '_compile_one', side_effect=compiled): self.assertTrue(self.review(compile_names=True)['compiled_offline'])
        with (self.directory / 'session.lock').open('rb') as stream: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_changed_bundle_or_rehashed_target_rejected_before_compilation(self):
        self.create(); relative = 'evidence/resource-000.bin'; raw = (self.directory / relative).read_bytes()
        self.f.rehash(relative, raw + b'\0' * 4)
        with patch.object(q, '_metadata') as metadata, patch.object(q.w, '_compile_one') as compiler:
            with self.assertRaises(ValueError): self.review(compile_names=True)
        metadata.assert_not_called(); compiler.assert_not_called()

    def test_mutation_during_compile_and_reader_close_failure_prevent_success(self):
        self.create()
        def compiled(*args):
            path = self.directory / 'source/correction.table'; path.write_bytes(path.read_bytes()); return {}
        with patch.object(q.w, '_compile_one', side_effect=compiled), self.assertRaises(ValueError): self.review(compile_names=True)
        close = q.b.i._Reader.close
        def failed(reader): close(reader); raise OSError('Own uncertain close')
        with patch.object(q.b.i._Reader, 'close', failed): code, out, _ = self.cli(self.args())
        self.assertEqual((code, out), (1, '')); self.assertFalse((self.root / 'names.private.json').exists())

    def test_native_resource_buffer_limit_is_enforced_before_inverse_and_compiler(self):
        self.create()
        with self.bound(), q.b._open_bundle('own', self.directory) as (_, inputs, review, binding):
            filename = q.b.c.RESOURCE_FILES[0]
            for source, target in ((b'x' * 5739, review.resources[filename]),
                                   (inputs.resources[filename], b'x' * 524289)):
                changed_inputs = replace(inputs, resources={**inputs.resources, filename: source})
                changed_review = replace(review, resources={**review.resources, filename: target})
                with patch.object(q.b.c.resources, 'inverse') as inverse:
                    with self.assertRaisesRegex(ValueError, 'native buffer'): q._metadata(changed_inputs, changed_review, binding)
                inverse.assert_not_called()

    def test_all_four_reports_bind_ap_direction_and_never_authenticate_native_origin(self):
        self.create(); path = self.root / 'own-report.bin'; c = self.review()['names_contract']
        for mode in range(4):
            path.write_bytes(self.packet(mode, c))
            with self.bound(): result = q.check_report('own', self.directory, path, mode)
            self.assertTrue(result['report_structure_verified']); self.assertFalse(result['native_report_origin_authenticated'])
            self.assertFalse(result['resource_full_readback_verified']); self.assertFalse(result['restore_verified'])
            self.assertEqual(result['request_sha256'], q.w.sha(b'A7NAM001' + struct.pack('<II', mode, 0)))
            for wrong in range(4):
                if wrong != mode:
                    with self.bound(), self.assertRaises(ValueError): q.check_report('own', self.directory, path, wrong)

    def test_bad_report_hash_status_count_and_length_do_not_pass(self):
        self.create(); path = self.root / 'own-report.bin'; original = self.packet(1)
        for offset in (16, 20, 24, 72, 80, 84, 88, 92, 96, 100, 104):
            raw = bytearray(original)
            if offset == 72: raw[offset:offset + 8] = bytes(8)
            else: raw[offset] ^= 1
            path.write_bytes(raw)
            with self.bound(), self.assertRaises(ValueError): q.check_report('own', self.directory, path, 1)
        for raw in (original[:-1], original + b'x'):
            path.write_bytes(raw)
            with self.bound(), self.assertRaises(ValueError): q.check_report('own', self.directory, path, 1)
        for mode in (True, -1, 4, '1'):
            with self.bound(), self.assertRaises(ValueError): q.check_report('own', self.directory, path, mode)

    def test_restore_and_cleanup_counter_ranges_preserve_existing_contract(self):
        self.create(); c = self.review()['names_contract']; path = self.root / 'report'
        for mode, counts in ((2, (0, 0, 0, 0, 0)), (2, (68, 0, 0, 68, 0)), (3, (0, 0, 0, 0, 0))):
            path.write_bytes(self.packet(mode, c, counts))
            with self.bound(): self.assertTrue(q.check_report('own', self.directory, path, mode)['report_structure_verified'])
        for counts in ((14, 0, 0, 13, 55), (0, 1, 0, 0, 0), (0, 0, 0, 68, 1)):
            path.write_bytes(self.packet(2, c, counts))
            with self.bound(), self.assertRaises(ValueError): q.check_report('own', self.directory, path, 2)

    def test_report_without_resource_hashes_or_job_id_cannot_authenticate_a_bundle(self):
        self.create(); first = self.review(); packet = self.packet(1, first['names_contract'])
        selection = self.f.f.f; selection.selection['slots']['1']['name'] = 'Other Own Name'; selection.save_selection()
        self.directory = self.root / 'other-name'; self.create(); second = self.review()
        self.assertNotEqual(first['contract_sha256'], second['contract_sha256'])
        self.assertNotEqual(first['names_contract']['offline_job_id'], second['names_contract']['offline_job_id'])
        self.assertEqual(first['names_contract']['AP'], second['names_contract']['AP'])
        self.assertEqual(packet, self.packet(1, second['names_contract']))
        path = self.root / 'report'; path.write_bytes(packet)
        with self.bound(): result = q.check_report('own', self.directory, path, 1)
        self.assertTrue(result['report_structure_verified'])
        self.assertFalse(result['report_contains_resource_hashes_or_job_id'])
        self.assertFalse(result['report_authenticates_bundle'])
        self.assertFalse(result['resource_full_readback_verified'])

    def test_missing_compiler_failure_timeout_or_bad_elf_never_publish_success(self):
        self.create()
        for error in (ImportError('own missing dependency'), OSError('own compiler unavailable'),
                      subprocess.TimeoutExpired('own', 60), ValueError('own invalid ELF')):
            with patch.object(q.w, '_compile_one', side_effect=error): code, out, err = self.cli(self.args() + ['--compile-names'])
            self.assertEqual((code, out), (1, '')); self.assertNotIn(str(self.root), err)
            self.assertFalse((self.root / 'names.private.json').exists())

    def test_cli_private_report_public_summary_and_explicit_report_check(self):
        self.create(); code, out, err = self.cli(self.args())
        self.assertEqual((code, err), (0, '')); self.assertEqual(json.loads(out)['phase'], 'NAMES_METADATA_CHECKED')
        report = self.root / 'names.private.json'; self.assertEqual(report.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(report.read_bytes()), self.review())
        for secret in (str(self.root), 'sha256', 'appFw.so', 'Own Film', 'string_'): self.assertNotIn(secret, out)
        path = self.root / 'packet'; path.write_bytes(self.packet(3))
        args = ['check-report', '--archive', 'own', '--directory', str(self.directory), '--report', str(path), '--mode', '3',
                '--output', str(self.root / 'checked.json')]
        self.assertEqual(self.cli(args)[0], 0)

    def test_output_private_new_outside_bundle_and_stdout_failures(self):
        self.create(); existing = self.root / 'existing'; existing.write_bytes(b'KEEP')
        shared = self.root / 'shared'; shared.mkdir(mode=0o755)
        for path in (existing, shared / 'new', self.directory / 'evidence/new.json', q.w.ROOT / 'NO-NAME-REPORT'):
            self.assertEqual(self.cli(self.args(path))[0], 1)
        self.assertEqual(existing.read_bytes(), b'KEEP')
        class Short(io.StringIO):
            def write(self, raw): return 0
        with self.bound(), contextlib.redirect_stdout(Short()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(q.main(self.args()), 1)
        self.assertTrue((self.root / 'names.private.json').exists())

    def test_original_files_and_frozen_bundle_content_metadata_remain_unchanged(self):
        self.create()
        paths = [p for p in self.directory.rglob('*') if p.is_file()]
        paths += [self.f.kwargs[k] for k in ('ap_path', 'cp_path', 'ram_path', 'saved_path', 'selection_path')]
        paths += list(self.f.kwargs['resources_path'].iterdir())
        def stamp():
            return {p: (q.w.sha(p.read_bytes()), p.stat().st_ino, p.stat().st_size, p.stat().st_mode,
                        p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths}
        before = stamp(); self.review(); path = self.root / 'report'; path.write_bytes(self.packet(0))
        with self.bound(): q.check_report('own', self.directory, path, 0)
        self.assertEqual(before, stamp())

    def test_names_abi_assertions_and_failed_compilation_remove_temporary_files(self):
        with patch.object(q.w.customhost, 'compiler_command', return_value=['own-compiler']):
            def failed(command, **kwargs):
                unit = Path(command[-1]).read_text(); self.folder = Path(command[-1]).parent
                for text in ('sizeof(struct Asset)==80', 'Asset,name)==0', 'Asset,size)==8', 'Asset,before)==12',
                             'Asset,after)==44', 'sizeof(assets)/sizeof(assets[0])==68', 'sizeof(old_pointers)==816',
                             'sizeof(names)==384', 'sizeof(ap_named_hash)==32'):
                    self.assertIn(text, unit)
                return type('OwnFailure', (), {'returncode': 1})()
            sources = {'src/looks/native/names.c': b'/* own */', 'src/fl23/native/sha256.h': b''}
            with patch.object(q.w.subprocess, 'run', side_effect=failed), self.assertRaises(ValueError):
                q.w._compile_one(sources, 'names', b'/* own */')
        self.assertFalse(self.folder.exists())

    def test_no_site_import_help_has_no_sdk_or_compiler_dependency(self):
        script = "import sys;from lutphoto import nameworker as q;assert not any(n=='usb' or n.startswith(('usb.','elftools','ziglang','numpy')) for n in sys.modules);q.main(['--help'])"
        done = subprocess.run([sys.executable, '-S', '-B', '-c', script], capture_output=True, text=True, timeout=15)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_unknown_enable_policy_job_id_and_abbreviation_are_rejected_without_echo(self):
        for extra in (['--enable-device'], ['--policy', str(self.root / 'secret')], ['--job-id', '0' * 16], ['--compile-name']):
            code, out, err = self.cli(self.args() + extra)
            self.assertEqual((code, out), (2, '')); self.assertNotIn(str(self.root), err)
        with self.assertRaises(ValueError): self.review(compile_names=1)


if __name__ == '__main__': unittest.main()
