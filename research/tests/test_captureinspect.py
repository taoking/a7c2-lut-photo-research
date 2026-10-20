"""Own temporary fixtures, read-only filesystem checks and no device access."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import captureinspect as i, capturestore, capturesession
from research.tests import test_capturesession as session_fixture


class InspectTests(unittest.TestCase):
    def setUp(self):
        fixture = session_fixture.SessionTests(methodName='runTest'); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture, self.root = fixture, fixture.root

    def make(self, name='capture', **kwargs):
        _, _, root = self.fixture.run_case(name, **kwargs)
        return root

    def inspect(self, root):
        return i.inspect_directory(root)

    def report(self, root):
        return root / 'session-report.private.json'

    def edit_report(self, root, **values):
        path = self.report(root)
        value = json.loads(path.read_bytes()); value.update(values)
        path.write_bytes(capturestore.encoded(value))

    def snapshot(self, root):
        result = {}
        for path in [root, *root.rglob('*')]:
            info = path.lstat()
            result[path.relative_to(root).as_posix()] = (
                stat.S_IMODE(info.st_mode), info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None)
        return result

    def rewrite_journal(self, root, edit):
        """Rechain an intentionally modified fixture to test semantic checks."""
        previous = '0' * 64
        files = sorted((root / 'events').glob('*.json'))
        for path in files:
            value = json.loads(path.read_bytes()); edit(value)
            value['previous_sha256'] = previous
            raw = capturestore.encoded(value); path.write_bytes(raw)
            previous = hashlib.sha256(raw).hexdigest()
        self.edit_report(root, journal_head_sha256=previous)

    def test_complete_session_consistency_has_no_device_or_resume_claim(self):
        result = self.inspect(self.make())
        self.assertEqual(result['classification'], 'CONSISTENT_SIMULATION_COMPLETE')
        self.assertEqual(result['materials_hashed'], 6)
        self.assertEqual(result['unacknowledged_intents'], 0)
        self.assertEqual(result['issues'], [])
        self.assertTrue(result['inspection_only']); self.assertTrue(result['simulation_only'])
        for key in ('camera_operations_performed', 'actual_source_identity_verified', 'body_binding_verified',
                    'physical_protocol_verified', 'chip_roles_verified', 'snapshot_freshness_verified',
                    'independent_media_verified', 'program_policy_revalidated', 'material_formats_revalidated',
                    'restore_verified', 'write_plan_enabled', 'resume_allowed'):
            self.assertIs(result[key], False, key)

    def test_full_resources_and_old_host_formats_supported(self):
        raw = capturesession.c.synthetic_resource(False)
        files = {**self.fixture.files, **{'resources/' + n: raw for n in i.RESOURCE_FILES}}
        root = self.make('resources', files=files, resources=True)
        result = self.inspect(root)
        self.assertEqual(result['classification'], 'CONSISTENT_SIMULATION_COMPLETE')
        self.assertEqual(result['materials_hashed'], 74)
        self.assertGreater(result['journal_records_checked'], 512)
        _, _, root = self.fixture.fixture.run_case('old-host')
        self.assertEqual(self.inspect(root)['classification'], 'CONSISTENT_SIMULATION_COMPLETE')

    def test_repeat_inspection_preserves_bytes_entries_modes_and_write_timestamps(self):
        root = self.make(); before = self.snapshot(root)
        self.assertEqual(self.inspect(root), self.inspect(root))
        self.assertEqual(before, self.snapshot(root))

    def test_readonly_files_and_directories_need_no_write_permission(self):
        root = self.make()
        paths = [root, *root.rglob('*')]
        try:
            for path in paths: path.chmod(0o500 if path.is_dir() else 0o400)
            before = self.snapshot(root)
            self.assertEqual(self.inspect(root)['classification'], 'CONSISTENT_SIMULATION_COMPLETE')
            self.assertEqual(before, self.snapshot(root))
        finally:
            for path in paths: path.chmod(0o700 if path.is_dir() else 0o600)

    def test_all_opens_are_readonly_and_mutators_never_called(self):
        root = self.make(); real = os.open; opened = []
        def readonly(path, flags, *args, **kwargs):
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
            self.assertFalse(flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            opened.append(str(path)); return real(path, flags, *args, **kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch.object(i.os, 'open', readonly))
            for name in ('write', 'mkdir', 'unlink', 'rename', 'replace', 'fsync', 'chmod', 'chown'):
                stack.enter_context(patch.object(i.os, name, side_effect=AssertionError('Read-only inspection mutated storage')))
            result = self.inspect(root)
        self.assertEqual(result['classification'], 'CONSISTENT_SIMULATION_COMPLETE')
        self.assertNotIn('/var/run/a7c2-fl23-macos.lock', opened)

    def test_report_missing_or_truncated_is_not_complete(self):
        root = self.make('missing'); self.report(root).unlink()
        self.assertEqual(self.inspect(root)['classification'], 'NEEDS_REVIEW_INCOMPLETE')
        root = self.make('truncated'); self.report(root).write_bytes(b'{"schema":')
        result = self.inspect(root)
        self.assertEqual(result['classification'], 'NEEDS_REVIEW_INCOMPLETE')
        self.assertIn('PARTIAL_OR_INVALID_REPORT', result['issues'])

    def test_unknown_auth_packet_and_stop_failures_preserve_unknown(self):
        for index, fault in enumerate(('auth-normal-start', 'auth-service-verify', 'partial:read:appFw.so', 'service-stop')):
            root = self.make(str(index), fault=fault)
            result = self.inspect(root)
            self.assertEqual(result['classification'], 'NEEDS_REVIEW_UNKNOWN')
            self.assertGreater(result['unacknowledged_intents'], 0)

    def test_known_program_rejection_is_incomplete_not_complete(self):
        files = self.fixture.files | {'appFw.so': bytes(len(self.fixture.files['appFw.so']))}
        result = self.inspect(self.make(files=files))
        self.assertEqual(result['classification'], 'NEEDS_REVIEW_INCOMPLETE')
        self.assertEqual(result['unacknowledged_intents'], 0)
        self.assertEqual(result['materials_hashed'], 1)

    def test_known_response_without_durable_ack_remains_unproven(self):
        real = capturestore.Sink.finish
        def fail(sink):
            if sink.relative == 'source/appFw.so': raise OSError('Self-generated post-response sync failure')
            return real(sink)
        with patch.object(capturestore.Sink, 'finish', fail): root = self.make()
        self.assertFalse(json.loads(self.report(root).read_bytes())['simulated_outcome_unknown'])
        result = self.inspect(root)
        self.assertEqual(result['classification'], 'NEEDS_REVIEW_UNKNOWN')
        self.assertEqual(result['unjournaled_materials'], 1)

    def test_stop_ack_persistence_failure_is_not_success(self):
        real = capturestore.Store.event
        def fail(store, event, **details):
            if event == 'ACK' and details.get('operation') == 'service-stop':
                raise OSError('Self-generated ACK failure')
            return real(store, event, **details)
        with patch.object(capturestore.Store, 'event', fail): root = self.make()
        self.assertEqual(self.inspect(root)['classification'], 'NEEDS_REVIEW_UNKNOWN')

    def test_changed_or_missing_recorded_material_is_inconsistent(self):
        for n, mutate in enumerate((lambda p: p.write_bytes(b'CHANGED'), lambda p: p.unlink())):
            root = self.make(str(n)); mutate(root / 'source/appFw.so')
            result = self.inspect(root)
            self.assertEqual(result['classification'], 'EVIDENCE_INCONSISTENT')
            self.assertIn('RECORDED_MATERIAL_DIFFERS', result['issues'])

    def test_unrecorded_partial_material_is_reported(self):
        root = self.make(fault='partial:read:appFw.so')
        result = self.inspect(root)
        self.assertEqual(result['unjournaled_materials'], 1)
        self.assertIn('UNJOURNALED_OR_PARTIAL_MATERIAL', result['issues'])

    def test_unknown_file_contents_are_not_read_or_echoed(self):
        root = self.make(); extra = root / 'source/private-serial-and-password.txt'
        extra.write_bytes(b'PRIVATE'); extra.chmod(0o600)
        real = i._Reader.read; seen = []
        def read(reader, name, *args, **kwargs):
            seen.append(name); return real(reader, name, *args, **kwargs)
        with patch.object(i._Reader, 'read', read): result = self.inspect(root)
        self.assertEqual(result['classification'], 'EVIDENCE_INCONSISTENT')
        self.assertNotIn('source/' + extra.name, seen)
        self.assertNotIn(extra.name, json.dumps(result)); self.assertNotIn('PRIVATE', json.dumps(result))

    def test_report_file_list_cannot_add_arbitrary_paths(self):
        root = self.make(); self.edit_report(root, files={'../../private': {'bytes': 1, 'sha256': '11' * 32}})
        result = self.inspect(root)
        self.assertEqual(result['classification'], 'EVIDENCE_INCONSISTENT')
        self.assertIn('INVALID_REPORT_MATERIALS', result['issues'])
        self.assertNotIn('../../private', json.dumps(result))

    def test_promoted_physical_or_write_flag_is_rejected(self):
        for n, field in enumerate(('camera_operations_performed', 'actual_source_identity_verified', 'write_plan_enabled')):
            root = self.make(str(n)); self.edit_report(root, **{field: True})
            result = self.inspect(root)
            self.assertEqual(result['classification'], 'EVIDENCE_INCONSISTENT')
            self.assertIn('UNSUPPORTED_PHYSICAL_OR_WRITE_CLAIM', result['issues'])

    def test_complete_report_cannot_override_unknown_intent(self):
        root = self.make(fault='partial:read:appFw.so')
        self.edit_report(root, phase='SIMULATED_SESSION_COMPLETE', last_stage='C5', simulated_outcome_unknown=False)
        result = self.inspect(root)
        self.assertEqual(result['classification'], 'EVIDENCE_INCONSISTENT')
        self.assertGreater(result['unacknowledged_intents'], 0)

    def test_report_journal_head_and_count_must_match(self):
        for n, changes in enumerate(({'journal_head_sha256': '00' * 32}, {'journal_records': True}, {'journal_records': 1})):
            root = self.make(str(n)); self.edit_report(root, **changes)
            self.assertEqual(self.inspect(root)['classification'], 'EVIDENCE_INCONSISTENT')

    def test_complete_payload_and_request_counters_are_checked(self):
        for n, changes in enumerate(({'accepted_payload_bytes': 1}, {'requests': 1}, {'accepted_wire_bytes': True}, {'accepted_wire_bytes': 0})):
            root = self.make(str(n)); self.edit_report(root, **changes)
            self.assertEqual(self.inspect(root)['classification'], 'EVIDENCE_INCONSISTENT')

    def test_journal_hole_reorder_and_broken_chain_rejected(self):
        root = self.make('hole'); (root / 'events/00000001.json').unlink()
        self.assertEqual(self.inspect(root)['classification'], 'EVIDENCE_INCONSISTENT')
        root = self.make('chain'); path = root / 'events/00000001.json'
        value = json.loads(path.read_bytes()); value['previous_sha256'] = '00' * 32
        path.write_bytes(capturestore.encoded(value))
        self.assertEqual(self.inspect(root)['classification'], 'EVIDENCE_INCONSISTENT')

    def test_trailing_partial_journal_never_yields_complete(self):
        root = self.make(); events = sorted((root / 'events').glob('*.json')); events[-1].write_bytes(b'{')
        result = self.inspect(root)
        self.assertEqual(result['classification'], 'EVIDENCE_INCONSISTENT')
        self.assertIn('PARTIAL_OR_INVALID_JOURNAL', result['issues'])

    def test_rechained_ack_without_intent_is_still_rejected(self):
        root = self.make()
        def edit(value):
            if value['event'] == 'INTENT' and value['details']['operation'] == 'normal-before': value['event'] = 'ACK'
        self.rewrite_journal(root, edit)
        self.assertIn('ACK_WITHOUT_INTENT', self.inspect(root)['issues'])

    def test_rechained_unsupported_command_and_guard_count_rejected(self):
        for index in range(2):
            root = self.make(str(index))
            def edit(value):
                if index == 0 and value['event'] in ('INTENT', 'ACK') and value['details']['operation'] == 'hasp':
                    value['details']['operation'] = 'writeMemory'
                if index == 1 and value['event'] == 'GUARD_ABSENCE_MODELED': value['details']['count'] = 0
            self.rewrite_journal(root, edit)
            self.assertEqual(self.inspect(root)['classification'], 'EVIDENCE_INCONSISTENT')

    def test_rechained_missing_required_read_is_not_complete(self):
        root = self.make()
        def edit(value):
            if value['event'] in ('INTENT', 'ACK') and value['details']['operation'] == 'ram':
                value['details']['operation'] = 'saved'
        self.rewrite_journal(root, edit)
        self.assertEqual(self.inspect(root)['classification'], 'EVIDENCE_INCONSISTENT')

    def test_complete_report_cannot_hide_review_or_mixed_profile_records(self):
        for index, (event, details) in enumerate((('NEEDS_REVIEW', {'reason_type': 'ValueError', 'outcome_unknown': False}),
                ('SYNTHETIC_PREFLIGHT', {'commit': 'fixture-only', 'archive_sha256': '00' * 32}))):
            root = self.make(str(index)); path = sorted((root / 'events').glob('*.json'))[-1]
            value = json.loads(path.read_bytes()); value.update(event=event, details=details)
            raw = capturestore.encoded(value); path.write_bytes(raw)
            number = value['seq'] + 1
            new = capturestore.encoded({'seq': number, 'previous_sha256': hashlib.sha256(raw).hexdigest(),
                                       'event': 'READY_FOR_REPORT', 'details': {}})
            next_path = root / 'events' / f'{number:08d}.json'; next_path.write_bytes(new); next_path.chmod(0o600)
            self.edit_report(root, journal_records=number + 1, journal_head_sha256=hashlib.sha256(new).hexdigest())
            self.assertEqual(self.inspect(root)['classification'], 'EVIDENCE_INCONSISTENT')

    def test_duplicate_keys_nonfinite_and_deep_json_never_pass(self):
        cases = (b'{"phase":1,"phase":2}', b'{"phase":NaN}', b'{"deep":' + b'[' * 1200 + b'0' + b']' * 1200 + b'}')
        for n, raw in enumerate(cases):
            root = self.make(str(n)); self.report(root).write_bytes(raw)
            self.assertNotEqual(self.inspect(root)['classification'], 'CONSISTENT_SIMULATION_COMPLETE')

    def test_two_report_formats_are_ambiguous(self):
        root = self.make(); path = root / 'capture-report.private.json'
        path.write_bytes(b'{}'); path.chmod(0o600)
        self.assertIn('AMBIGUOUS_REPORTS', self.inspect(root)['issues'])

    def test_symlink_directory_file_and_parent_refused(self):
        root = self.make('file'); file = root / 'source/appFw.so'; file.unlink(); file.symlink_to(self.report(root))
        self.assertEqual(self.inspect(root)['classification'], 'REFUSED')
        root = self.make('folder'); (root / 'resources').rmdir(); (root / 'resources').symlink_to(root / 'source', target_is_directory=True)
        self.assertEqual(self.inspect(root)['classification'], 'REFUSED')
        alias = self.root / 'alias'; alias.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(self.inspect(alias / 'file')['classification'], 'REFUSED')

    def test_fifo_hardlink_and_shared_permissions_refused(self):
        root = self.make('fifo'); os.mkfifo(root / 'source/pipe', 0o600)
        self.assertEqual(self.inspect(root)['classification'], 'REFUSED')
        root = self.make('hardlink'); os.link(root / 'source/appFw.so', self.root / 'outside-link')
        self.assertEqual(self.inspect(root)['classification'], 'REFUSED')
        root = self.make('shared'); root.chmod(0o755)
        self.assertEqual(self.inspect(root)['classification'], 'REFUSED')

    def test_wrong_owner_and_nonempty_lock_refused(self):
        root = self.make('lock'); (root / 'session.lock').write_bytes(b'OTHER')
        self.assertEqual(self.inspect(root)['classification'], 'REFUSED')
        root = self.make('owner')
        with patch.object(capturestore.os, 'geteuid', return_value=os.geteuid() + 1):
            self.assertEqual(self.inspect(root)['classification'], 'REFUSED')

    def test_shared_lock_refuses_active_writer_and_does_not_create_missing_lock(self):
        root = self.make('active')
        fd = os.open(root / 'session.lock', os.O_RDONLY)
        try:
            i.fcntl.flock(fd, i.fcntl.LOCK_EX | i.fcntl.LOCK_NB)
            result = self.inspect(root)
            self.assertEqual(result['classification'], 'REFUSED'); self.assertEqual(result['issues'], ['ACTIVE_JOB'])
        finally: os.close(fd)
        root = self.make('missing'); (root / 'session.lock').unlink()
        self.assertEqual(self.inspect(root)['classification'], 'REFUSED')
        self.assertFalse((root / 'session.lock').exists())

    def test_active_child_writer_is_refused_without_changing_evidence(self):
        root = self.make(); before = self.snapshot(root)
        code = ('import os,sys,fcntl; fd=os.open(sys.argv[1],os.O_RDONLY); '
                'fcntl.flock(fd,fcntl.LOCK_EX); print("LOCKED",flush=True); '
                'sys.stdin.buffer.read(1); os.close(fd)')
        child = subprocess.Popen([sys.executable, '-S', '-B', '-c', code, str(root / 'session.lock')],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            self.assertEqual(child.stdout.readline(), b'LOCKED\n')
            self.assertEqual(self.inspect(root)['issues'], ['ACTIVE_JOB'])
        finally:
            child.communicate(b'x', timeout=5)
        self.assertEqual(self.inspect(root)['classification'], 'CONSISTENT_SIMULATION_COMPLETE')
        self.assertEqual(before, self.snapshot(root))

    def test_empty_or_partially_initialized_host_directory_stays_incomplete(self):
        store = capturestore.Store(self.root / 'early'); store.close()
        result = self.inspect(self.root / 'early')
        self.assertEqual(result['classification'], 'NEEDS_REVIEW_INCOMPLETE')
        self.assertEqual(result['journal_records_checked'], 0)
        (self.root / 'early/resources').rmdir()
        result = self.inspect(self.root / 'early')
        self.assertIn('PARTIAL_DIRECTORY_LAYOUT', result['issues'])
        self.assertEqual(result['classification'], 'NEEDS_REVIEW_INCOMPLETE')

    def test_excessive_metadata_material_size_and_entry_count_refused(self):
        root = self.make('json'); self.report(root).write_bytes(b' ' * 131073)
        self.assertEqual(self.inspect(root)['classification'], 'REFUSED')
        root = self.make('program')
        with (root / 'source/appFw.so').open('r+b') as stream: stream.truncate(128 * i.MIB + 1)
        self.assertEqual(self.inspect(root)['classification'], 'REFUSED')
        root = self.make('entries')
        for n in range(4):
            path = root / ('extra' + str(n)); path.touch(mode=0o600)
        self.assertEqual(self.inspect(root)['classification'], 'REFUSED')

    def test_metadata_and_directory_replacement_during_read_refused(self):
        for index in range(2):
            root = self.make(str(index)); real = i._Reader.read; changed = [False]
            def read(reader, name, *args, **kwargs):
                result = real(reader, name, *args, **kwargs)
                if name == 'source/appFw.so' and not changed[0]:
                    changed[0] = True
                    if index == 0: (root / name).write_bytes(b'X' * len(self.fixture.files['appFw.so']))
                    else:
                        (root / 'source').rename(root / 'old-source'); (root / 'source').mkdir(mode=0o700)
                return result
            with patch.object(i._Reader, 'read', read): result = self.inspect(root)
            self.assertEqual(result['classification'], 'REFUSED')

    def test_replaced_lock_root_and_changed_inventory_refused(self):
        for index in range(3):
            root = self.make(str(index)); real = i._Reader.read; changed = [False]
            def read(reader, name, *args, **kwargs):
                result = real(reader, name, *args, **kwargs)
                if not changed[0]:
                    changed[0] = True
                    if index == 0:
                        (root / 'session.lock').unlink(); (root / 'session.lock').touch(mode=0o600)
                    elif index == 1:
                        root.rename(self.root / 'moved'); root.mkdir(mode=0o700)
                    else: (root / 'resources/new').touch(mode=0o600)
                return result
            with patch.object(i._Reader, 'read', read): result = self.inspect(root)
            self.assertEqual(result['classification'], 'REFUSED')

    def test_total_byte_budget_and_deadline_enforced(self):
        root = self.make()
        real = i.Budget
        with patch.object(i, 'Budget', side_effect=lambda _: real(1)):
            self.assertEqual(self.inspect(root)['classification'], 'REFUSED')
        with patch.object(i.Budget, 'check', side_effect=TimeoutError('Self-generated deadline')):
            self.assertEqual(self.inspect(root)['classification'], 'REFUSED')

    def test_missing_directory_repo_and_traversal_never_create_files(self):
        for root in (self.root / 'absent', capturestore.ROOT, self.root / '../untrusted'):
            self.assertEqual(self.inspect(root)['classification'], 'REFUSED')
        self.assertFalse((self.root / 'absent').exists())

    def test_cli_success_failure_and_output_privacy_under_stdlib(self):
        for index, options in enumerate(({}, {'fault': 'auth-normal-start'})):
            root = self.make(str(index), **options)
            result = subprocess.run([sys.executable, '-S', '-B', '-m', 'lutphoto.captureinspect', 'inspect', '--directory', str(root)],
                capture_output=True, cwd=capturestore.ROOT)
            self.assertEqual(result.returncode, index)
            value = json.loads(result.stdout)
            self.assertFalse(value['resume_allowed'])
            for secret in (str(root), '11' * 32, 'OWN-HEADER', 'fixture-only'):
                self.assertNotIn(secret, result.stdout.decode())
            self.assertEqual(result.stderr, b'')

    def test_cli_has_no_resume_repair_policy_or_device_options(self):
        for option in ('--resume', '--repair', '--policy', '--serial', '--camera'):
            with patch.object(sys, 'stderr'), self.assertRaises(SystemExit) as error:
                i.main(['inspect', '--directory', '/unused', option, 'value'])
            self.assertEqual(error.exception.code, 2)

    def test_import_and_inspection_do_not_load_device_stack(self):
        code = ('import sys; from lutphoto import captureinspect; '
                'captureinspect.inspect_directory("/missing-capture"); '
                'assert not any(n == "usb" or n.startswith("usb.") or n in '
                '("transport", "core", "macfl23.session", "numpy") for n in sys.modules)')
        result = subprocess.run([sys.executable, '-S', '-B', '-c', code], capture_output=True, cwd=capturestore.ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
