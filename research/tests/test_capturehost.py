"""Real host filesystem faults and in-memory fake reads; no camera access."""
from dataclasses import replace
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lutphoto import bk4 as b, capturehost as h, capturestore as s
from research.tests import test_programidentity as program_fixture


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def store(self, name='capture'):
        store = s.Store(self.root / name); self.addCleanup(store.close)
        return store

    def test_permissions_exclusive_output_and_complete_readback(self):
        store = self.store()
        info = store.put('source/own.bin', b'OWN DATA')
        self.assertEqual(store.read('source/own.bin', info), b'OWN DATA')
        self.assertEqual(stat.S_IMODE(store.path.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((store.path / 'source/own.bin').stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError): store.put('source/own.bin', b'NEW')
        with self.assertRaises(FileExistsError): s.Store(store.path)
        self.assertEqual((store.path / 'source/own.bin').read_bytes(), b'OWN DATA')

    def test_symlink_ancestor_leaf_and_repository_directory_rejected(self):
        (self.root / 'alias').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError): s.Store(self.root / 'alias/new')
        (self.root / 'leaf').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(FileExistsError): s.Store(self.root / 'leaf')
        with self.assertRaises(ValueError): s.Store(s.ROOT / 'research/output/forbidden-capture')

    def test_shared_parent_and_nonprivate_storage_rejected(self):
        parent = self.root / 'shared'; parent.mkdir(); parent.chmod(0o777)
        with self.assertRaises(ValueError): s.Store(parent / 'capture')
        store = self.store(); store.path.chmod(0o755)
        with self.assertRaises(ValueError): store.put('source/data', b'X')

    def test_space_precheck_is_bounded_but_not_a_write_guarantee(self):
        store = self.store()
        with patch.object(s.os, 'fstatvfs', return_value=SimpleNamespace(f_bavail=1, f_frsize=4096)):
            store.require_space(4096)
            with self.assertRaises(OSError): store.require_space(4097)
        with self.assertRaises(ValueError): store.require_space(True)

    def test_traversal_and_unknown_subdirectory_are_rejected(self):
        store = self.store()
        for name in ('../escape', '/absolute', 'source/../escape', 'source/a/b', 'source/a\\b', 'source/a\0b', 'unknown/a'):
            with self.subTest(name=name), self.assertRaises(ValueError): store.put(name, b'X')

    def test_symlink_fifo_and_hardlink_inputs_rejected_without_blocking(self):
        store = self.store(); info = store.put('source/data', b'OWN')
        (store.path / 'source/link').symlink_to(store.path / 'source/data')
        with self.assertRaises(OSError): store.read('source/link', info)
        os.mkfifo(store.path / 'source/fifo', 0o600)
        with self.assertRaises(ValueError): store.read('source/fifo', info)
        os.link(store.path / 'source/data', self.root / 'extra-link')
        with self.assertRaises(ValueError): store.read('source/data', info)

    def test_subdirectory_replacement_cannot_redirect_write(self):
        store = self.store(); external = self.root / 'outside'; external.mkdir()
        (store.path / 'source').rename(store.path / 'source-old')
        (store.path / 'source').symlink_to(external, target_is_directory=True)
        with self.assertRaises(ValueError): store.put('source/escape', b'OWN')
        self.assertEqual(list(external.iterdir()), [])

    def test_content_change_and_root_replacement_are_detected(self):
        store = self.store(); info = store.put('source/data', b'OWN')
        (store.path / 'source/data').write_bytes(b'BAD')
        with self.assertRaises(ValueError): store.verify('source/data', info)
        store.path.rename(self.root / 'old-capture')
        store.path.mkdir(mode=0o700)
        with self.assertRaises(ValueError): store.put('source/data', b'NEW')

    def test_replaced_lock_inode_is_rejected(self):
        store = self.store(); (store.path / 'session.lock').unlink()
        (store.path / 'session.lock').touch(mode=0o600)
        with self.assertRaises(ValueError): store.put('source/data', b'OWN')

    def test_unexpected_file_owner_is_rejected(self):
        values = list(os.stat(self.root)); values[4] = os.geteuid() + 1
        with self.assertRaises(ValueError): s._private(os.stat_result(values), True)

    def test_directory_sync_failure_does_not_record_verified_file(self):
        store = self.store(); real_sync = os.fsync
        def failing(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError(errno.EIO, 'injected')
            return real_sync(fd)
        with patch.object(s.os, 'fsync', side_effect=failing), self.assertRaises(OSError): store.put('source/data', b'OWN')
        self.assertEqual((store.path / 'source/data').read_bytes(), b'OWN')
        self.assertNotIn('source/data', store.documents)

    def test_zero_write_and_file_sync_failure_leave_partial_evidence(self):
        store = self.store()
        with patch.object(s.os, 'write', return_value=0), self.assertRaises(OSError): store.put('source/zero', b'OWN')
        self.assertEqual((store.path / 'source/zero').read_bytes(), b'')
        with patch.object(s.os, 'fsync', side_effect=OSError(errno.EIO, 'injected')), self.assertRaises(OSError):
            store.put('source/sync', b'OWN')
        self.assertEqual((store.path / 'source/sync').read_bytes(), b'OWN')
        with self.assertRaises(FileExistsError): store.put('source/sync', b'NEW')

    def test_journal_chain_is_bounded_and_contains_no_completion_by_default(self):
        store = self.store(); store.event('INTENT', operation='own-read'); first = store.head
        store.event('ACK', operation='own-read')
        rows = sorted((store.path / 'events').iterdir())
        second = json.loads(rows[1].read_text())
        self.assertEqual(second['previous_sha256'], first)
        self.assertEqual(second['seq'], 1)
        self.assertEqual(first, hashlib.sha256(rows[0].read_bytes()).hexdigest())
        with self.assertRaises(ValueError): store.event('TOO_BIG', data='x' * 16384)
        self.assertEqual(len(list((store.path / 'events').iterdir())), 2)  # Bound checked before file creation.

    def test_cross_process_lock_and_kill_preserve_intent_and_partial_file(self):
        target = self.root / 'child'
        code = """from lutphoto.capturestore import Store,Sink
import sys
store=Store(sys.argv[1]);store.event('INTENT',operation='own-read')
sink=Sink(32,store=store,relative='source/partial');sink.write(b'OWN-PARTIAL')
print('READY',flush=True);sys.stdin.read()
"""
        child = subprocess.Popen([sys.executable, '-S', '-B', '-c', code, str(target)], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def cleanup():
            if child.poll() is None: child.kill()
            child.communicate(timeout=5)
        self.addCleanup(cleanup)
        ready, _, _ = select.select([child.stdout], [], [], 10)
        self.assertTrue(ready); self.assertEqual(child.stdout.readline().strip(), 'READY')
        with (target / 'session.lock').open('r+b') as stream:
            with self.assertRaises(BlockingIOError): fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        child.kill(); child.communicate(timeout=5)
        with (target / 'session.lock').open('r+b') as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertEqual((target / 'source/partial').read_bytes(), b'OWN-PARTIAL')
        self.assertEqual(len(list((target / 'events').iterdir())), 1)
        self.assertFalse((target / 'capture-report.private.json').exists())
        with self.assertRaises(FileExistsError): s.Store(target)


class SinkTests(unittest.TestCase):
    def test_invalid_chunk_types_sizes_and_post_finish_writes_rejected(self):
        sink = s.Sink(s.CHUNK)
        for raw in (b'', bytearray(b'A'), b'X' * (s.CHUNK + 1), 'A'):
            with self.subTest(kind=type(raw)), self.assertRaises(ValueError): sink.write(raw)
        self.assertEqual(sink.size, 0)
        sink.write(b'A'); self.assertEqual(sink.finish()['bytes'], 1)
        with self.assertRaises(ValueError): sink.write(b'B')

    def test_exact_size_and_shared_total_budget(self):
        budget = s.Budget(8); first = s.Sink(8, exact=4, budget=budget)
        first.write(b'1234'); first.finish()
        second = s.Sink(8, budget=budget)
        with self.assertRaises(ValueError): second.write(b'12345')
        self.assertEqual((budget.used, second.size), (4, 0))
        short = s.Sink(8, exact=4); short.write(b'A')
        with self.assertRaises(ValueError): short.finish()

    def test_global_deadline_does_not_reset_between_chunks(self):
        now = [0]; budget = s.Budget(8, seconds=2, clock=lambda: now[0]); sink = s.Sink(8, budget=budget)
        sink.write(b'A'); now[0] = 2
        with self.assertRaises(TimeoutError): sink.write(b'B')
        self.assertEqual((sink.size, budget.used), (1, 1))

    def test_bad_budget_and_payload_bounds_rejected(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError): s.Budget(value)
        for value in (0, -1, True, float('inf'), float('nan')):
            with self.subTest(seconds=value), self.assertRaises(ValueError): s.Budget(8, seconds=value)
        with self.assertRaises(ValueError): s.Sink(8, exact=True)


class CaptureTests(unittest.TestCase):
    def setUp(self):
        fixture = program_fixture.ProgramIdentityTests(methodName='runTest'); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        self.root, self.policy = fixture.root.resolve(), fixture.policy
        self.fl23_ap, self.fl23_cp = fixture.ap['fl23'], fixture.cp['fl23']
        self.ap = {0x02cf0001: b.Property(0, b'A', None, 1),
                   0x02cf0b6e: b.Property(64, bytes(4), bytes(4), 4),
                   0x02770015: b.Property(0, b'X', None, 1)}
        self.cp = {key: b.Property(2, b'CP', None, 2) for key in h.c.devicesettings.PROTECTED}
        raw = self.snapshot()
        self.files = {'ap': fixture.ap['stock'], 'cp': fixture.cp['stock'],
                      'ram': raw, 'saved': raw, 'ram_end': raw, 'saved_end': raw}

    def snapshot(self, ap=None, cp=None):
        return b'OWN-HEADER' + b.fixture_image(self.ap if ap is None else ap) + b.fixture_image(self.cp if cp is None else cp) + b'OWN-TAIL'

    def run_case(self, name='capture', files=None, resources=False, **kwargs):
        tape = h.SyntheticTape(dict(self.files if files is None else files), **kwargs)
        with patch.object(h.p, '_load_policy', return_value=self.policy):
            result = h.simulate('unused', self.root / name, tape, resources=resources)
        return result, tape, self.root / name

    def test_core_capture_checks_full_content_but_never_physical_proofs(self):
        report, tape, root = self.run_case()
        self.assertEqual(report['phase'], 'SIMULATED_HOST_CAPTURE_COMPLETE')
        self.assertEqual(report['last_stage'], 'C5'); self.assertEqual(len(report['files']), 6)
        self.assertTrue(report['program_content_matched_in_rehearsal'])
        self.assertEqual(tape.counts['ap'], 2); self.assertEqual(tape.counts['cp'], 2)
        self.assertEqual(report['accepted_payload_bytes'],
                         2 * (len(self.files['ap']) + len(self.files['cp'])) + 4 * len(self.files['ram']))
        for key, value in h.boundary().items(): self.assertEqual(report[key], value)
        text = json.dumps(report)
        self.assertNotIn(str(self.root), text); self.assertNotIn('11' * 32, text)
        self.assertNotIn('02cf', text); self.assertNotIn('OWN-HEADER', text)
        for name, info in report['files'].items():
            raw = (root / name).read_bytes()
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (info['bytes'], info['sha256']))

    def test_unknown_and_fl23_programs_stop_before_snapshots_and_preserve_source(self):
        for index, replacement in enumerate((bytes(len(self.files['ap'])), self.files['ap'][:-1] + b'Z')):
            files = {**self.files, 'ap': replacement}
            report, tape, root = self.run_case(str(index), files)
            self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertNotIn('read:cp', tape.trace)
            self.assertNotIn('read:ram', tape.trace); self.assertIn('service-stop', tape.trace)
            self.assertEqual((root / 'source/appFw.so').read_bytes(), replacement)
        fixture_source = self.policy.sources[1]
        self.assertEqual(hashlib.sha256(self.fl23_ap).hexdigest(), fixture_source.ap_sha)
        files = {**self.files, 'ap': self.fl23_ap, 'cp': self.fl23_cp}
        report, tape, _ = self.run_case('fl23', files)
        self.assertFalse(report['program_content_matched_in_rehearsal']); self.assertNotIn('read:ram', tape.trace)

    def test_cp_mismatch_and_short_complete_response_are_known_validation_failures(self):
        for index, cp in enumerate((b'Z' * len(self.files['cp']), self.files['cp'][:-1])):
            report, tape, _ = self.run_case(str(index), {**self.files, 'cp': cp})
            self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertFalse(report['simulated_outcome_unknown'])
            self.assertIn('service-stop', tape.trace); self.assertNotIn('read:ram', tape.trace)

    def test_oversize_and_interrupted_reads_never_send_stop_or_retry(self):
        cases = (({**self.files, 'ap': self.files['ap'] + b'X'}, None), (self.files, 'read:ap'))
        for index, (files, fault) in enumerate(cases):
            report, tape, root = self.run_case(str(index), files, fault=fault)
            self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertTrue(report['simulated_outcome_unknown'])
            self.assertNotIn('service-stop', tape.trace); self.assertEqual(tape.counts['ap'], 1)
            self.assertTrue((root / 'source/appFw.so').exists()); self.assertFalse((root / 'source/cpapp-b.bin').exists())

    def test_start_stop_and_normal_return_unknown_have_no_replay(self):
        for fault in ('start-unknown', 'stop-unknown', 'return-unknown'):
            report, tape, _ = self.run_case(fault, fault=fault)
            self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertTrue(report['simulated_outcome_unknown'])
            self.assertEqual(tape.trace.count('service-start'), 1)
            self.assertLessEqual(tape.trace.count('service-stop'), 1)
            if fault == 'start-unknown': self.assertNotIn('service-stop', tape.trace)

    def test_changed_return_model_serial_or_port_rejects_completion(self):
        original = h.SyntheticTape({}).identity
        for index, value in enumerate(({'model': 'OTHER'}, {'serial_sha256': '22' * 32}, {'port': [2, 1]})):
            report, tape, _ = self.run_case(str(index), returned_identity={**original, **value})
            self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertFalse(report['simulated_normal_observation_matched'])
            self.assertEqual(tape.trace.count('service-stop'), 1)

    def test_invalid_initial_observation_stops_before_service(self):
        tape = h.SyntheticTape(self.files); tape.identity['port'] = [True]
        with patch.object(h.p, '_load_policy', return_value=self.policy): result = h.simulate('unused', self.root / 'capture', tape)
        self.assertEqual(result['phase'], 'NEEDS_REVIEW'); self.assertNotIn('service-start', tape.trace)

    def test_insufficient_space_prevents_all_fake_transport_calls(self):
        with patch.object(s.os, 'fstatvfs', return_value=SimpleNamespace(f_bavail=0, f_frsize=4096)):
            result, tape, _ = self.run_case()
        self.assertEqual(result['phase'], 'NEEDS_REVIEW'); self.assertEqual(tape.trace, [])

    def test_program_repeat_change_stops_without_overwriting_initial_file(self):
        report, tape, root = self.run_case(changes={'ap': self.files['ap'][:-1] + b'Z'})
        self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertEqual(tape.counts['ap'], 2)
        self.assertEqual((root / 'source/appFw.so').read_bytes(), self.files['ap'])
        self.assertNotIn('read:ram_end', tape.trace)

    def test_ram_saved_difference_is_preserved_without_save_or_role_guessing(self):
        changed = dict(self.ap); changed[0x02cf0001] = replace(changed[0x02cf0001], data=b'B')
        raw = self.snapshot(ap=changed)
        report, _, root = self.run_case(files={**self.files, 'saved': raw, 'saved_end': raw})
        self.assertEqual(report['phase'], 'SIMULATED_HOST_CAPTURE_COMPLETE')
        self.assertNotEqual((root / 'source/settings-ram.bin').read_bytes(), (root / 'source/settings-saved.bin').read_bytes())
        self.assertFalse(report['chip_roles_verified'])

    def test_snapshot_scope_changes_fail_but_volatile_diagnostic_and_other_groups_allowed(self):
        for index, key in enumerate((0x02cf0001, 0x02cf0b6e, 0x02770015)):
            ap = dict(self.ap); ap[key] = replace(ap[key], data=bytes([90]) * len(ap[key].data))
            report, _, _ = self.run_case(str(index), {**self.files, 'ram_end': self.snapshot(ap=ap)})
            self.assertEqual(report['phase'], 'NEEDS_REVIEW' if index == 0 else 'SIMULATED_HOST_CAPTURE_COMPLETE')
        ap = dict(self.ap); ap[0x02cf0b6e] = replace(ap[0x02cf0b6e], reset_data=b'CHNG')
        report, _, _ = self.run_case('reset', {**self.files, 'ram_end': self.snapshot(ap=ap)})
        self.assertEqual(report['phase'], 'NEEDS_REVIEW')

    def test_malformed_snapshot_is_retained_and_later_reads_stop(self):
        report, tape, root = self.run_case(files={**self.files, 'ram': b'BAD BK4'})
        self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertNotIn('read:saved', tape.trace)
        self.assertEqual((root / 'source/settings-ram.bin').read_bytes(), b'BAD BK4')

    def test_each_protected_cp_observation_change_is_rejected(self):
        for index, key in enumerate(self.cp):
            cp = dict(self.cp); cp[key] = replace(cp[key], data=b'XX')
            report, _, _ = self.run_case(str(index), {**self.files, 'saved_end': self.snapshot(cp=cp)})
            self.assertEqual(report['phase'], 'NEEDS_REVIEW')

    def test_host_file_tamper_after_service_exit_prevents_final_success(self):
        finish = h._Run.finish_service
        def changed(run):
            finish(run)
            (run.store.path / 'source/appFw.so').write_bytes(b'Z' * len(self.files['ap']))
        with patch.object(h._Run, 'finish_service', changed): report, tape, _ = self.run_case()
        self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertFalse(report['host_files_integrity_checked'])
        self.assertEqual(tape.trace.count('service-stop'), 1)

    def test_68_resources_and_repeat_reads_preserve_all_sources(self):
        raw = h.c.synthetic_resource(False)
        files = {**self.files, **{'resource:' + n: raw for n in h.c.RESOURCE_FILES}}
        report, tape, root = self.run_case(files=files, resources=True)
        self.assertEqual(report['phase'], 'SIMULATED_HOST_CAPTURE_COMPLETE'); self.assertEqual(len(report['files']), 74)
        self.assertEqual(report['resource_count'], 2860)
        self.assertEqual(set(p.name for p in (root / 'resources').iterdir()), set(h.c.RESOURCE_FILES))
        self.assertTrue(all(tape.counts['resource:' + n] == 2 for n in h.c.RESOURCE_FILES))

    def test_missing_mixed_corrupt_and_changed_resources_stop(self):
        raw = h.c.synthetic_resource(False); files = {**self.files, **{'resource:' + n: raw for n in h.c.RESOURCE_FILES}}
        first = 'resource:' + h.c.RESOURCE_FILES[0]
        variants = (({k: v for k, v in files.items() if k != first}, {}),
                    ({**files, first: h.c.synthetic_resource(True)}, {}), ({**files, first: b'BAD'}, {}),
                    (files, {'changes': {first: raw + bytes(4)}}))
        for index, (values, options) in enumerate(variants):
            result, _, _ = self.run_case(str(index), values, resources=True, **options)
            self.assertEqual(result['phase'], 'NEEDS_REVIEW')

    def test_disk_full_during_payload_stops_unknown_with_partial_file(self):
        real_write = os.write
        def failing(fd, raw):
            if len(raw) == len(self.files['ap']):
                real_write(fd, raw[:100]); raise OSError(errno.ENOSPC, 'injected')
            return real_write(fd, raw)
        with patch.object(s.os, 'write', side_effect=failing): report, tape, root = self.run_case()
        self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertTrue(report['simulated_outcome_unknown'])
        self.assertEqual((root / 'source/appFw.so').stat().st_size, 100)
        self.assertNotIn('service-stop', tape.trace)

    def test_file_sync_failure_after_response_uses_at_most_one_healthy_exit(self):
        real_sync = os.fsync; failed = [False]
        def failing(fd):
            info = os.fstat(fd)
            if stat.S_ISREG(info.st_mode) and info.st_size == len(self.files['ap']) and not failed[0]:
                failed[0] = True; raise OSError(errno.EIO, 'injected')
            return real_sync(fd)
        with patch.object(s.os, 'fsync', side_effect=failing): report, tape, root = self.run_case()
        self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertFalse(report['simulated_outcome_unknown'])
        self.assertEqual(tape.trace.count('service-stop'), 1)
        self.assertEqual((root / 'source/appFw.so').read_bytes(), self.files['ap'])

    def test_failed_durable_intent_prevents_read_and_existing_directory_cannot_replay(self):
        real_sync = os.fsync; failed = [False]
        def failing(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode):
                data = os.pread(fd, 16384, 0)
                if b'INTENT' in data and b'read:ap' in data and not failed[0]:
                    failed[0] = True; raise OSError(errno.EIO, 'injected')
            return real_sync(fd)
        with patch.object(s.os, 'fsync', side_effect=failing): report, tape, root = self.run_case()
        self.assertEqual(report['phase'], 'NEEDS_REVIEW'); self.assertNotIn('read:ap', tape.trace)
        before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        with patch.object(h.p, '_load_policy', return_value=self.policy), self.assertRaises(FileExistsError):
            h.simulate('unused', root, tape)
        self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_external_backend_and_policy_override_not_exposed(self):
        with self.assertRaises(ValueError): h.simulate('unused', self.root / 'capture', object())
        with self.assertRaises(TypeError): h.simulate('unused', self.root / 'capture', h.SyntheticTape(self.files), policy=self.policy)
        self.assertFalse((self.root / 'capture').exists())

    def test_cli_rejects_policy_identity_and_role_override_arguments(self):
        for option in ('--policy', '--serial', '--roles'):
            result = subprocess.run([sys.executable, '-S', '-B', '-m', 'lutphoto.capturehost', 'rehearse',
                '--archive', 'unused', '--directory', str(self.root / 'capture'), option, 'unused'],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root / 'capture').exists())

    def test_import_and_help_have_no_device_or_numpy_modules(self):
        code = """import sys
import lutphoto.capturehost as h
assert not any(n=='usb' or n.startswith('usb.') or n in ('transport','core','numpy','macfl23.session') for n in sys.modules)
try:h.main(['--help'])
except SystemExit as e:assert e.code==0
"""
        result = subprocess.run([sys.executable, '-S', '-B', '-c', code], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('capture --', result.stdout)


if __name__ == '__main__':
    unittest.main()
