"""Bind own frozen bundles to pinned worker metadata; never load target code."""
import contextlib
import fcntl
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import programworker as q
from research.tests import test_slotbundle as fixtures


class ProgramWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SlotBundleTests.setUpClass()
        cls.addClassCleanup(fixtures.SlotBundleTests.doClassCleanups)

    def setUp(self):
        self.f = fixtures.SlotBundleTests(methodName='runTest'); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.root, self.directory = self.f.root, self.f.directory
        self.pin = {'files': {'src/fl23/native/installer.c': {'sha256': '11' * 32}}}

    def bound(self):
        stack = self.f.f.bound()
        stack.enter_context(patch.object(q, '_sources', return_value=(self.pin, {})))
        return stack

    def review(self, **kwargs):
        with self.bound(): return q.review_bundle('own', self.directory, **kwargs)

    def create(self): return self.f.create()

    def packet(self, mode, contract=None):
        c = self.review()['program_contract'] if contract is None else contract
        before = c['after' if mode == 2 else 'before']
        after = c['before' if mode == 2 else 'after']
        return (struct.pack('<8s4I7q4Q', b'A7IRP001', 1, mode, 9, 0 if mode == 0 else c['window_writes'],
                            0, 0, 0, 0, 0, 0, 17, 21, 22, *[c['sizes'][n] for n in q.w.NAMES])
                + b''.join(bytes.fromhex(before[n]) for n in q.w.NAMES)
                + (bytes(64) if mode == 0 else b''.join(bytes.fromhex(after[n]) for n in q.w.NAMES)))

    def args(self, output=None):
        return ['review', '--archive', 'own', '--directory', str(self.directory),
                '--output', str(output or self.root / 'worker.private.json')]

    def cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with self.bound(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err): code = q.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_manifest_contains_exact_full_hashes_and_cp_long_windows_first(self):
        self.create()
        with self.bound(), q.b._open_review('own', self.directory) as (_, review, _):
            header, c = q._metadata(review); text = header.decode()
            ordered = sorted([(chip, row) for chip, label in enumerate(('AP', 'CP'))
                              for row in review.transitions[label].changes],
                             key=lambda v: (v[0] != 1, len(v[1].before) <= 1024, v[1].at))
            for j, (chip, row) in enumerate(ordered):
                self.assertIn(f'{{{row.at}UL,{len(row.before)},{chip},old_{j},new_{j}}}', text)
                self.assertIn(f'old_{j}[]={q.w.cbytes(row.before)}', text)
                self.assertIn(f'new_{j}[]={q.w.cbytes(row.after)}', text)
            self.assertEqual(c['window_writes'], len(ordered))
            for chip, name in zip(('AP', 'CP'), q.w.NAMES):
                source = (self.directory / ('source/' + name)).read_bytes()
                self.assertEqual(c['before'][name], q.w.sha(source))
                self.assertEqual(c['after'][name], q.w.sha(review.programs[chip]))
                self.assertEqual(c['sizes'][name], len(source))
                self.assertIn(q.w.cbytes(bytes.fromhex(c['after'][name])), text)
        result = self.review(); self.assertTrue(result['program_manifest_checked_offline'])
        self.assertEqual(result['manifest_header_sha256'], q.w.sha(header))
        self.assertEqual(result['contract_sha256'], q.w.sha(q.encoded(c)))
        self.assertEqual(result['bundle_manifest_sha256'], q.w.sha((self.directory / q.b.MANIFEST).read_bytes()))
        for key in q.w.boundary(): self.assertFalse(result[key])

    def test_all_source_routes_bind_checked_full_programs_without_compiler_by_default(self):
        own = self.f.f.own
        pairs = [('stock', own.ap['stock'], own.cp['stock']), ('fl23', own.ap['fl23'], own.cp['fl23']),
                 ('stock-lut', own.target('stock', 32), own.runtime_cp),
                 ('fl23-lut', own.target('fl23', 32), own.runtime_cp), ('legacy-six', own.legacy_ap, own.legacy_cp)]
        for label, ap, cp in pairs:
            self.f.kwargs['ap_path'].write_bytes(ap); self.f.kwargs['cp_path'].write_bytes(cp)
            self.directory = self.root / label; self.f.create(self.directory)
            with patch.object(q.w, '_compile_one') as compiler:
                result = self.review(); compiler.assert_not_called()
            self.assertEqual(result['program_contract']['before'], dict(zip(q.w.NAMES, map(q.w.sha, (ap, cp)))))
            self.assertFalse(result['compiled_offline'])

    def test_compile_uses_checked_header_count_under_shared_lock_and_returns_after_close(self):
        self.create(); compiled = []
        def compiler(sources, kind, header, *, expected_windows):
            self.assertEqual(kind, 'program'); self.assertIn(f'window_count={expected_windows}'.encode(), header)
            with (self.directory / 'session.lock').open('rb') as stream:
                with self.assertRaises(BlockingIOError): fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            compiled.append(header); return {'target_code_executed': False}
        with patch.object(q.w, '_compile_one', side_effect=compiler): result = self.review(compile_program=True)
        self.assertTrue(result['compiled_offline']); self.assertEqual(len(compiled), 1)
        with (self.directory / 'session.lock').open('rb') as stream: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_no_program_change_does_not_load_sources_compile_or_accept_report(self):
        self.f.kwargs['ap_path'].write_bytes(self.f.f.own.target('stock', 1))
        self.f.kwargs['cp_path'].write_bytes(self.f.f.zero); self.create()
        with self.bound(), patch.object(q, '_sources') as sources, patch.object(q.w, '_compile_one') as compiler:
            result = q.review_bundle('own', self.directory, compile_program=True)
            with self.assertRaisesRegex(ValueError, 'No program task'): q.check_report('own', self.directory, 'missing', 1)
        sources.assert_not_called(); compiler.assert_not_called()
        self.assertEqual(result['phase'], 'NO_PROGRAM_CHANGE'); self.assertIsNone(result['program_contract'])
        self.assertFalse(result['compiled_offline'])

    def test_bundle_rehashed_tampering_is_rejected_before_metadata_or_compilation(self):
        self.create(); name = 'evidence/target-cpapp-b.bin'; raw = (self.directory / name).read_bytes()
        self.f.rehash(name, bytes([raw[0] ^ 1]) + raw[1:])
        with patch.object(q, '_metadata') as metadata, patch.object(q.w, '_compile_one') as compiler:
            with self.assertRaises(ValueError): self.review(compile_program=True)
        metadata.assert_not_called(); compiler.assert_not_called()

    def test_bundle_mutation_during_compilation_fails_final_reader_check(self):
        self.create()
        def compiler(*args, **kwargs):
            path = self.directory / 'source/correction.table'; path.write_bytes(path.read_bytes())
            return {}
        with patch.object(q.w, '_compile_one', side_effect=compiler), self.assertRaises(ValueError): self.review(compile_program=True)

    def test_compile_dependency_failure_timeout_and_elf_rejection_propagate_without_report(self):
        self.create()
        for error in (ImportError('own missing compiler'), ValueError('own bad ELF'),
                      subprocess.TimeoutExpired('own', 60), OSError('own compiler unavailable')):
            with patch.object(q.w, '_compile_one', side_effect=error):
                code, out, err = self.cli(self.args() + ['--compile-program'])
            self.assertEqual(code, 1); self.assertEqual(out, ''); self.assertNotIn(str(self.root), err)
            self.assertFalse((self.root / 'worker.private.json').exists())

    def test_all_three_report_modes_are_bound_to_this_bundle_and_not_native_origin(self):
        self.create(); path = self.root / 'own-report.bin'
        for mode in range(3):
            path.write_bytes(self.packet(mode))
            with self.bound(): result = q.check_report('own', self.directory, path, mode)
            self.assertTrue(result['report_structure_verified']); self.assertFalse(result['native_report_origin_authenticated'])
            self.assertFalse(result['native_execution_verified']); self.assertFalse(result['restore_verified'])
            self.assertEqual(result['request_sha256'], q.w.sha(b'A7INS001' + struct.pack('<II', mode, 0)))
            for wrong in range(3):
                if wrong != mode:
                    with self.bound(), self.assertRaises(ValueError): q.check_report('own', self.directory, path, wrong)

    def test_report_wrong_full_hash_size_count_status_or_length_fails(self):
        self.create(); path = self.root / 'own-report.bin'; original = self.packet(1)
        for offset in (16, 20, 24, 80, 96, 112, 144, 176, 208):
            raw = bytearray(original)
            if offset == 80: raw[80:88] = bytes(8)
            else: raw[offset] ^= 1
            path.write_bytes(raw)
            with self.bound(), self.assertRaises(ValueError): q.check_report('own', self.directory, path, 1)
        for raw in (original[:-1], original + b'x'):
            path.write_bytes(raw)
            with self.bound(), self.assertRaises(ValueError): q.check_report('own', self.directory, path, 1)
        for mode in (True, -1, 3, '1'):
            with self.bound(), self.assertRaises(ValueError): q.check_report('own', self.directory, path, mode)

    def test_source_policy_mismatch_and_changed_archive_are_not_accepted(self):
        self.create(); policy = self.f.f.b.policy
        with patch.object(q.w, 'load_sources', return_value=({'commit': policy.commit, 'archive_sha256': 'ff' * 32}, {})), patch.object(q.w, 'catalog'):
            with self.assertRaises(ValueError): q._sources('own', policy)
        with self.assertRaises((ValueError, OSError)): q._sources(self.root / 'missing', policy)

    def test_review_and_report_cli_save_private_new_file_and_public_summary_only(self):
        self.create(); code, out, err = self.cli(self.args())
        self.assertEqual((code, err), (0, '')); self.assertFalse(json.loads(out)['compiled_offline'])
        output = self.root / 'worker.private.json'; self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        result = json.loads(output.read_bytes()); self.assertEqual(result, self.review())
        for secret in (str(self.root), 'sha256', 'Own Film', 'before', 'appFw.so'): self.assertNotIn(secret, out)
        path = self.root / 'packet'; path.write_bytes(self.packet(2))
        args = ['check-report', '--archive', 'own', '--directory', str(self.directory), '--report', str(path),
                '--mode', '2', '--output', str(self.root / 'checked.json')]
        self.assertEqual(self.cli(args)[0], 0)
        self.assertEqual(json.loads((self.root / 'checked.json').read_bytes())['phase'], 'REPORT_STRUCTURE_CHECKED')

    def test_outputs_existing_inside_bundle_shared_parent_or_repository_are_refused(self):
        self.create(); existing = self.root / 'existing'; existing.write_bytes(b'KEEP')
        shared = self.root / 'shared'; shared.mkdir(mode=0o755)
        for path in (existing, self.directory / 'evidence/new.json', shared / 'report', q.b.p.w.ROOT / 'NO-REPORT'):
            code, out, _ = self.cli(self.args(path)); self.assertEqual((code, out), (1, ''))
        self.assertEqual(existing.read_bytes(), b'KEEP'); self.assertFalse((self.directory / 'evidence/new.json').exists())

    def test_reader_close_failure_prevents_compiled_success_output(self):
        self.create(); close = q.b.i._Reader.close
        def failed(reader): close(reader); raise OSError('Own close failure')
        with patch.object(q.b.i._Reader, 'close', failed): code, out, _ = self.cli(self.args())
        self.assertEqual((code, out), (1, '')); self.assertFalse((self.root / 'worker.private.json').exists())

    def test_save_and_stdout_failure_are_not_cli_success_and_do_not_overwrite(self):
        self.create()
        with patch.object(q.os, 'write', return_value=0): self.assertEqual(self.cli(self.args())[0], 1)
        self.assertTrue((self.root / 'worker.private.json').exists())
        class Short(io.StringIO):
            def write(self, raw): return 0
        with self.bound(), contextlib.redirect_stdout(Short()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(q.main(self.args(self.root / 'second.json')), 1)
        self.assertTrue((self.root / 'second.json').exists())

    def test_all_bundle_file_content_and_metadata_remain_unchanged(self):
        self.create()
        def stamp():
            result = {}
            for path in self.directory.rglob('*'):
                info = path.stat(); result[str(path)] = (q.w.sha(path.read_bytes()) if path.is_file() else None,
                    info.st_ino, info.st_size, info.st_mode, info.st_mtime_ns, info.st_ctime_ns)
            return result
        before = stamp(); self.review(); path = self.root / 'report'; path.write_bytes(self.packet(0))
        with self.bound(): q.check_report('own', self.directory, path, 0)
        self.assertEqual(before, stamp())

    def test_no_site_cli_help_and_import_have_no_camera_or_compiler_dependency(self):
        script = "import sys;from lutphoto import programworker as q;assert not any(n=='usb' or n.startswith('usb.') or n.startswith('elftools') or n.startswith('ziglang') for n in sys.modules);q.main(['--help'])"
        completed = subprocess.run([sys.executable, '-S', '-B', '-c', script], capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_compiler_metadata_limits_and_window_abi_assertions(self):
        for kind, header, count in (('other', b'x', 1), ('program', b'', 1), ('program', b'x', True),
                                    ('program', b'x', 0), ('program', b'x', 4097), ('names', b'x', 1)):
            with patch.object(q.w.customhost, 'compiler_command') as command:
                with self.assertRaises(ValueError): q.w._compile_one({}, kind, header, expected_windows=count)
                command.assert_not_called()
        with patch.object(q.w.customhost, 'compiler_command', return_value=['own-compiler']):
            def failed(command, **kwargs):
                unit = Path(command[-1]).read_text()
                for part in ('sizeof(struct Window)==32', 'Window,offset)==0', 'Window,length)==8',
                             'Window,chip)==12', 'Window,before)==16', 'Window,after)==24',
                             'sizeof(windows)/sizeof(windows[0])==2', 'sizeof(original_hashes)==64'):
                    self.assertIn(part, unit)
                self.compile_folder = Path(command[-1]).parent
                return type('OwnFailure', (), {'returncode': 1})()
            sources = {'src/fl23/native/installer.c': b'/* own */', 'src/fl23/native/sha256.h': b''}
            with patch.object(q.w.subprocess, 'run', side_effect=failed), self.assertRaises(ValueError):
                q.w._compile_one(sources, 'program', b'/* own */', expected_windows=2)
        self.assertFalse(self.compile_folder.exists())

    def test_argument_errors_hide_values_and_offer_no_device_or_policy_override(self):
        for extra in (['--enable-device'], ['--policy', str(self.root / 'secret')], ['--compile-prog']):
            code, out, err = self.cli(self.args() + extra)
            self.assertEqual((code, out), (2, '')); self.assertNotIn(str(self.root), err)
        with self.assertRaises(ValueError): self.review(compile_program=1)


if __name__ == '__main__': unittest.main()
