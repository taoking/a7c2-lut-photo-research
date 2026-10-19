"""Disk faults and real POSIX processes, exclusively using synthetic data."""
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lutphoto import customjournal as j
from lutphoto import custommigration as m


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        m.fixtures(self.root / 'fixtures')
        self.capsule = m.read_capsule(self.root / 'fixtures/S0.json')
        self.locks = self.root / 'locks'

    def create(self, name='job', **kwargs):
        path = self.root / name
        result = j.simulate(self.capsule, path, self.locks, **kwargs)
        return path, result

    def bytes_at(self, root):
        return {p.relative_to(root).as_posix(): (p.lstat().st_mode, p.read_bytes())
                for p in root.rglob('*') if p.is_file()}

    def rewrite(self, path, change):
        data, _ = j.read_document(path); change(data); path.write_bytes(j.encoded(data))

    def cloned(self, source, name):
        target = self.root / name; shutil.copytree(source, target)
        return target

    def child(self, code, *arguments):
        process = subprocess.Popen([sys.executable, '-S', '-B', '-c', code, *map(str, arguments)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def cleanup():
            if process.poll() is None: process.kill()
            process.communicate(timeout=5)
        self.addCleanup(cleanup)
        ready, _, _ = select.select([process.stdout], [], [], 10)
        self.assertTrue(ready, 'child did not reach checkpoint')
        self.assertEqual(process.stdout.readline().strip(), 'READY')
        return process

    def test_all_four_sources_both_directions_persist_and_reinspect(self):
        for state in m.STATES:
            capsule = m.read_capsule(self.root / f'fixtures/{state}.json')
            for direction in ('install', 'restore'):
                path = self.root / (state + direction)
                result = j.simulate(capsule, path, self.locks, direction=direction)
                self.assertEqual(result['phase'], 'SIMULATED_TARGET_VERIFIED' if direction == 'install' else 'SIMULATED_SOURCE_RESTORED')
                self.assertTrue(result['journal_valid']); self.assertTrue(result['current_matches_journal'])
                self.assertFalse(result['unknown_outcome'])
                before = self.bytes_at(path)
                self.assertEqual(j.inspect(path, self.locks), result)
                self.assertEqual(self.bytes_at(path), before)
                for key in ('camera_operations_enabled', 'global_camera_lock_acquired', 'power_loss_verified',
                            'physical_validation_verified', 'journal_authenticity_verified', 'automatic_retry_allowed',
                            'automatic_restore_allowed', 'actual_source_identity_verified', 'independent_media_verified'):
                    self.assertFalse(result[key])

    def test_every_publication_fault_both_directions_stops_and_cannot_replay(self):
        count = 0
        for direction in ('install', 'restore'):
            changed = j.prepare(self.capsule, direction)[3]
            faults = [f'{changed[0]}:{stage}' for stage in j.STAGES]
            faults += [f'TRANSACTION:{stage}' for stage in j.FINAL_STAGES]
            for fault in faults:
                path, result = self.create(str(count), direction=direction, fault=fault); count += 1
                with self.subTest(fault=fault, direction=direction):
                    self.assertEqual(result['phase'], 'NEEDS_REVIEW')
                    self.assertFalse(result['automatic_retry_allowed'])
                    before = self.bytes_at(path)
                    self.assertEqual(j.inspect(path, self.locks), result)
                    with self.assertRaises(FileExistsError): j.simulate(self.capsule, path, self.locks)
                    self.assertEqual(self.bytes_at(path), before)
        self.assertEqual(count, 28)

    def test_all_components_written_without_result_remain_unknown_even_at_target(self):
        for direction in ('install', 'restore'):
            for name in j.prepare(self.capsule, direction)[3]:
                path, result = self.create(direction + name, direction=direction, fault=name + ':after-write')
                self.assertTrue(result['journal_valid']); self.assertTrue(result['unknown_outcome'])
                self.assertEqual(result['pending_component'], name)
                self.assertEqual(result['classification'][name], 'target')
                self.assertEqual(result['phase'], 'NEEDS_REVIEW')

    def test_missing_completion_is_not_recovered_from_all_target_hashes(self):
        path, result = self.create(fault='TRANSACTION:before-complete')
        self.assertTrue(result['journal_valid']); self.assertFalse(result['unknown_outcome'])
        self.assertTrue(all(v in ('target', 'unchanged') for v in result['classification'].values()))
        self.assertEqual(result['phase'], 'NEEDS_REVIEW')
        self.assertFalse(result['automatic_restore_allowed'])

    def test_intent_file_and_directory_synced_before_any_state_publication(self):
        calls = []
        real_sync = j.sync_directory
        def sync(path):
            real_sync(path); calls.append(('synced', Path(path).name))
        def checkpoint(stage, component):
            if stage == 'after-intent':
                self.assertEqual(calls[-2:], [('synced', 'events'), ('synced', 'events')])
            if stage == 'state-temporary':
                records = sorted((self.root / 'job/events').glob('*.json'))
                record, _ = j.read_document(records[-1])
                self.assertEqual(record['event'], 'INTENT'); self.assertEqual(record['component'], component)
                current, _ = j.read_document(self.root / 'job/current.json')
                self.assertEqual(m.hashes(m.decode_files(current)), record['observed_sha256'])
        with patch.object(j, 'sync_directory', sync):
            _, result = self.create(checkpoint=checkpoint)
        self.assertTrue(result['journal_valid'])

    def test_intent_file_sync_error_stops_before_mutating_current(self):
        real_write = j.durable_write
        def write(path, value, **kwargs):
            if Path(path).name == '00000001.json':
                with patch.object(j.os, 'fsync', side_effect=OSError('injected')):
                    return real_write(path, value, **kwargs)
            return real_write(path, value, **kwargs)
        with patch.object(j, 'durable_write', write), self.assertRaises(OSError): self.create()
        current, _ = j.read_document(self.root / 'job/current.json')
        self.assertEqual(m.decode_files(current), j.prepare(self.capsule, 'install')[1])
        self.assertFalse(j.inspect(self.root / 'job', self.locks)['journal_valid'])

    def test_intent_directory_sync_error_preserves_evidence_and_stops_before_mutation(self):
        real_sync = j.sync_directory
        def sync(path):
            if Path(path).name == 'events' and (Path(path) / '00000001.json').exists():
                raise OSError('injected directory sync')
            real_sync(path)
        with patch.object(j, 'sync_directory', sync), self.assertRaises(OSError): self.create()
        current, _ = j.read_document(self.root / 'job/current.json')
        self.assertEqual(m.decode_files(current), j.prepare(self.capsule, 'install')[1])
        result = j.inspect(self.root / 'job', self.locks)
        self.assertEqual(result['phase'], 'NEEDS_REVIEW'); self.assertFalse(result['journal_valid'])
        self.assertTrue(list((self.root / 'job/events').glob('.pending-*')))

    def test_state_directory_sync_error_leaves_pending_intent_without_replay(self):
        real_write = j.durable_write
        def write(path, value, **kwargs):
            if kwargs.get('replace'):
                with patch.object(j, 'sync_directory', side_effect=OSError('state sync')):
                    return real_write(path, value, **kwargs)
            return real_write(path, value, **kwargs)
        with patch.object(j, 'durable_write', write), self.assertRaises(OSError): self.create()
        result = j.inspect(self.root / 'job', self.locks)
        self.assertTrue(result['journal_valid']); self.assertTrue(result['unknown_outcome'])
        self.assertEqual(result['phase'], 'NEEDS_REVIEW')

    def test_changed_progress_after_intent_is_not_overwritten(self):
        def checkpoint(stage, component):
            if stage == 'after-intent':
                path = self.root / 'job/current.json'
                self.rewrite(path, lambda value: value.update(AP=(bytes.fromhex(value['AP'])[:-1] + b'x').hex()))
        with self.assertRaisesRegex(ValueError, 'after durable intent'): self.create(checkpoint=checkpoint)
        result = j.inspect(self.root / 'job', self.locks)
        self.assertEqual(result['classification']['AP'], 'unknown')
        self.assertEqual(result['phase'], 'NEEDS_REVIEW')

    def test_complete_requires_fresh_full_readback(self):
        def checkpoint(stage, component):
            if stage == 'before-complete':
                path = self.root / 'job/current.json'
                self.rewrite(path, lambda value: value.update(CP=(bytes.fromhex(value['CP'])[:-1] + b'x').hex()))
        with self.assertRaisesRegex(ValueError, 'Final complete readback'): self.create(checkpoint=checkpoint)
        self.assertEqual(j.inspect(self.root / 'job', self.locks)['phase'], 'NEEDS_REVIEW')

    def test_real_sigkill_at_intent_and_after_write_releases_lock_without_replay(self):
        code = """import sys
from lutphoto import customjournal as j, custommigration as m
def checkpoint(stage, component):
    if stage == sys.argv[4] and component == 'NAMES':
        print('READY', flush=True); sys.stdin.read()
j.simulate(m.read_capsule(sys.argv[1]), sys.argv[2], sys.argv[3], checkpoint=checkpoint)
"""
        for stage, classification in (('after-intent', 'source'), ('after-write', 'target')):
            path = self.root / stage
            process = self.child(code, self.root / 'fixtures/S0.json', path, self.locks, stage)
            process.kill(); process.communicate(timeout=5)
            self.assertEqual(process.returncode, -9)
            before = self.bytes_at(path); result = j.inspect(path, self.locks)
            self.assertTrue(result['journal_valid']); self.assertTrue(result['unknown_outcome'])
            self.assertEqual(result['pending_component'], 'NAMES')
            self.assertEqual(result['classification']['NAMES'], classification)
            with self.assertRaises(FileExistsError): j.simulate(self.capsule, path, self.locks)
            self.assertEqual(before, self.bytes_at(path))

    def test_shared_lock_rejects_other_job_and_inspection_while_process_is_alive(self):
        path, _ = self.create()
        code = """import sys
from lutphoto.customjournal import session_lock
with session_lock(sys.argv[1]):
    print('READY', flush=True); sys.stdin.read()
"""
        process = self.child(code, self.locks)
        with self.assertRaises(j.LockBusy): j.simulate(self.capsule, self.root / 'other', self.locks)
        with self.assertRaises(j.LockBusy): j.inspect(path, self.locks)
        self.assertFalse((self.root / 'other').exists())
        process.communicate(input='done', timeout=5)
        self.assertEqual(process.returncode, 0)
        self.assertTrue(j.inspect(path, self.locks)['journal_valid'])

    def test_posix_flock_compatibility_uses_same_inode_never_unlinks_lock(self):
        with j.session_lock(self.locks, create=True):
            path = self.locks / 'session.lock'; inode = path.stat().st_ino
            code = """import fcntl, os, sys
fd=os.open(sys.argv[1], os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError: sys.exit(3)
sys.exit(0)
"""
            run = subprocess.run([sys.executable, '-S', '-c', code, str(path)], capture_output=True, timeout=5)
            self.assertEqual(run.returncode, 3)
        self.assertEqual(path.stat().st_ino, inode)
        with j.session_lock(self.locks): self.assertEqual(path.stat().st_ino, inode)
        self.assertIn(repr(j.LEGACY_CAMERA_LOCK), Path('macfl23/cli.py').read_text())

    def test_lock_identity_mismatch_and_insecure_paths_are_rejected(self):
        path, _ = self.create()
        other = self.root / 'other-locks'
        with j.session_lock(other, create=True): pass
        self.assertFalse(j.inspect(path, other)['journal_valid'])
        target = self.locks / 'session.lock'; original = target.read_bytes(); target.unlink()
        outside = self.root / 'outside'; outside.write_bytes(b'untouched')
        target.symlink_to(outside)
        with self.assertRaises(OSError):
            with j.session_lock(self.locks): pass
        self.assertEqual(outside.read_bytes(), b'untouched')
        target.unlink(); os.link(outside, target)
        with self.assertRaises(ValueError):
            with j.session_lock(self.locks): pass
        target.unlink(); target.write_bytes(original); target.chmod(0o666)
        with self.assertRaises(ValueError):
            with j.session_lock(self.locks): pass
        target.unlink(); os.mkfifo(target, 0o600)
        with self.assertRaises(ValueError):
            with j.session_lock(self.locks): pass
        target.unlink(); self.locks.chmod(0o755)
        with self.assertRaises(ValueError):
            with j.session_lock(self.locks): pass

    def test_journal_corruption_hash_order_sequence_binding_and_duplicate_keys_rejected(self):
        base, _ = self.create()
        changes = [lambda x: x.update(seq=True), lambda x: x.update(previous_sha256='f' * 64),
                   lambda x: x.update(transaction_id='f' * 32), lambda x: x.update(event='COMPLETE'),
                   lambda x: x.update(component='AP'), lambda x: x['observed_sha256'].update(AP='f' * 64)]
        for index, change in enumerate(changes):
            path = self.cloned(base, f'corrupt{index}'); record = path / 'events/00000001.json'
            self.rewrite(record, change)
            self.assertFalse(j.inspect(path, self.locks)['journal_valid'])
        for index, raw in enumerate((b'{', b'{}\n', b'{"a":1,"a":2}', b'\xff', b'{"x":NaN}', b' ' * (j.LIMIT + 1))):
            path = self.cloned(base, f'torn{index}')
            (path / 'events/00000001.json').write_bytes(raw)
            self.assertFalse(j.inspect(path, self.locks)['journal_valid'])

    def test_missing_middle_tail_final_extra_and_pending_records_fail_closed(self):
        base, _ = self.create()
        for index, name in enumerate(('00000000.json', '00000001.json', '00000011.json')):
            path = self.cloned(base, 'missing' + str(index)); (path / 'events' / name).unlink()
            self.assertEqual(j.inspect(path, self.locks)['phase'], 'NEEDS_REVIEW')
        for index, name in enumerate(('00000012.json', '.pending-incomplete', 'not-an-event')):
            path = self.cloned(base, 'extra' + str(index)); (path / 'events' / name).write_bytes(b'bad')
            self.assertFalse(j.inspect(path, self.locks)['journal_valid'])
        path = self.cloned(base, 'prefix')
        for p in (path / 'events').iterdir():
            if p.name != '00000000.json': p.unlink()
        result = j.inspect(path, self.locks)
        self.assertTrue(result['journal_valid']); self.assertFalse(result['current_matches_journal'])
        self.assertEqual(result['phase'], 'NEEDS_REVIEW')

    def test_manifest_capsule_and_format_contracts_are_revalidated_not_trusted(self):
        base, _ = self.create()
        for index, (name, change) in enumerate((
            ('manifest.json', lambda x: x.update(plan_sha256='f' * 64)),
            ('manifest.json', lambda x: x['goal'].update(AP='f' * 64)),
            ('manifest.json', lambda x: x.update(extra=True)),
            ('capsule.json', lambda x: x.update(body_token='synthetic-other')),
            ('contracts.json', lambda x: x.update(toy_components_bound_to_real_layout=True)))):
            path = self.cloned(base, 'manifest' + str(index)); self.rewrite(path / name, change)
            self.assertFalse(j.inspect(path, self.locks)['journal_valid'])

    def test_current_unknown_or_reverted_after_complete_is_never_success(self):
        base, _ = self.create()
        path = self.cloned(base, 'unknown')
        self.rewrite(path / 'current.json', lambda x: x.update(AP=(bytes.fromhex(x['AP'])[:-1] + b'x').hex()))
        result = j.inspect(path, self.locks)
        self.assertTrue(result['journal_valid']); self.assertEqual(result['classification']['AP'], 'unknown')
        self.assertEqual(result['phase'], 'NEEDS_REVIEW')
        source = j.prepare(self.capsule, 'install')[1]
        path = self.cloned(base, 'reverted'); (path / 'current.json').write_bytes(j.encoded({n: b.hex() for n, b in source.items()}))
        self.assertEqual(j.inspect(path, self.locks)['phase'], 'NEEDS_REVIEW')

    def test_evidence_permissions_links_nonregular_or_extra_entries_rejected(self):
        base, _ = self.create()
        for index, kind in enumerate(('symlink', 'hardlink', 'public', 'missing', 'extra', 'fifo')):
            path = self.cloned(base, 'paths' + str(index)); manifest = path / 'manifest.json'
            if kind == 'symlink': manifest.unlink(); manifest.symlink_to(base / 'manifest.json')
            elif kind == 'hardlink': manifest.unlink(); os.link(base / 'manifest.json', manifest)
            elif kind == 'public': manifest.chmod(0o644)
            elif kind == 'missing': manifest.unlink()
            elif kind == 'extra': (path / '.pending-unknown').write_bytes(b'bad')
            else: manifest.unlink(); os.mkfifo(manifest, 0o600)
            self.assertFalse(j.inspect(path, self.locks)['journal_valid'])
            if kind == 'hardlink': manifest.unlink()

    def test_inspection_does_not_create_missing_lock_or_transaction(self):
        with self.assertRaises(OSError): j.inspect(self.root / 'absent', self.root / 'absent-locks')
        self.assertFalse((self.root / 'absent-locks').exists())
        with j.session_lock(self.locks, create=True): pass
        self.assertFalse(j.inspect(self.root / 'absent', self.locks)['journal_valid'])
        self.assertFalse((self.root / 'absent').exists())

    def test_real_material_extra_capsule_fields_invalid_fault_and_direction_rejected_before_creation(self):
        for key, value in (('material_kind', 'camera'), ('body_token', 'real-camera'),
                           ('extra', 'private-input'), ('source_state', 'S9')):
            capsule = {**self.capsule, key: value}
            with self.assertRaises(ValueError): j.simulate(capsule, self.root / 'bad', self.locks)
        for fault in ('USB:after-write', 'AP:unknown', 'TRANSACTION:after-complete'):
            with self.assertRaises(ValueError): self.create(fault=fault)
        with self.assertRaises(ValueError): self.create(direction='resume')
        self.assertFalse(self.locks.exists()); self.assertFalse((self.root / 'bad').exists())

    def test_cli_exit_codes_readonly_reinspection_and_standard_library_only(self):
        def run(*args):
            return subprocess.run([sys.executable, '-S', '-B', '-m', 'lutphoto.customjournal', *map(str, args)],
                                  capture_output=True, text=True, timeout=15)
        for name, fault, expected in (('done', None, 0), ('stopped', 'NAMES:after-write', 2)):
            path = self.root / name
            args = ['simulate', '--directory', path, '--lock-directory', self.locks,
                    '--capsule', self.root / 'fixtures/S0.json']
            if fault: args += ['--fault', fault]
            result = run(*args); self.assertEqual(result.returncode, expected, result.stderr)
            report = json.loads(result.stdout); self.assertFalse(report['global_camera_lock_acquired'])
            self.assertNotIn(str(self.root), result.stdout)
            before = self.bytes_at(path)
            checked = run('inspect', '--directory', path, '--lock-directory', self.locks)
            self.assertEqual(checked.returncode, expected); self.assertEqual(json.loads(checked.stdout), report)
            self.assertEqual(run(*args).returncode, 1); self.assertEqual(before, self.bytes_at(path))
        result = subprocess.run([sys.executable, '-S', '-B', '-c',
            "import sys; from lutphoto import customjournal; assert not any(n.split('.')[0] in {'usb','numpy','macfl23','pmca'} for n in sys.modules)"], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
