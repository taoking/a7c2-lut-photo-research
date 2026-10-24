"""Fake authentication/locks and own framed payloads; no device adapter."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import capturesession as s, captureprotocol as p, capturestore
from research.tests import test_capturehost as fixtures


TEMP = {'libJit.so', 'lut-program-staged.so', 'lut-names-staged.so', 'lut-runtime-staged.so',
        'a7c2.install.request', 'a7c2.install.result', 'a7c2.names.request', 'a7c2.names.result',
        'a7c2.wbi.request', 'a7c2.wbi.result', 'a7c2.runtime.result', 'a7c2.probe.result'}
SOURCES = {'src/fl23/core.py': ('NATIVE_PATHS=' + repr(TEMP | {'a7c2-preview-staged.so'})).encode(),
           'src/looks/looktool/devicesession.py': ('TEMP_NAMES=' + repr(TEMP)).encode()}


class SessionTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.CaptureTests(methodName='runTest'); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture, self.root, self.policy = fixture, fixture.root, fixture.policy
        self.files = {'appFw.so': fixture.files['ap'], 'cpapp-b.bin': fixture.files['cp'],
                      'ram': fixture.files['ram'], 'saved': fixture.files['saved']}
        patch.object(s.programidentity, '_load_policy', return_value=self.policy).start()
        patch.object(p.workercontracts, 'load_sources', return_value=({}, SOURCES)).start()
        self.addCleanup(patch.stopall)

    def run_case(self, name='capture', files=None, resources=False, **options):
        peer = s.SyntheticPeer(self.files if files is None else files, **options)
        report = s.rehearse('own-fixture', self.root / name, peer, resources=resources)
        return report, peer, self.root / name

    def failed(self, report, peer, *, unknown=False, stop=0):
        self.assertEqual(report['phase'], 'NEEDS_REVIEW')
        self.assertEqual(report['simulated_outcome_unknown'], unknown)
        self.assertEqual(peer.trace.count('service-stop'), stop)
        self.assertEqual(peer.trace[-1], 'global-lock-release')

    def test_complete_protocol_and_storage_rehearsal_has_no_physical_claims(self):
        report, peer, root = self.run_case()
        self.assertEqual(report['phase'], 'SIMULATED_SESSION_COMPLETE')
        self.assertEqual(report['last_stage'], 'C5')
        self.assertEqual(len(report['files']), 6)
        self.assertTrue(report['program_content_matched_in_rehearsal'])
        self.assertTrue(report['simulated_normal_identity_matched'])
        self.assertEqual(peer.trace[0], 'global-lock-acquire')
        self.assertEqual(peer.trace[-1], 'global-lock-release')
        self.assertEqual(peer.trace.count('service-stop'), 1)
        self.assertEqual(peer.trace.count('auth-normal-start'), 1)
        self.assertEqual(peer.trace.count('auth-service-verify'), 1)
        for field in ('camera_operations_performed', 'global_camera_lock_acquired', 'physical_protocol_verified',
                      'response_profile_verified', 'actual_source_identity_verified', 'body_binding_verified',
                      'chip_roles_verified', 'outer_wrapper_verified', 'atomic_capture_verified',
                      'snapshot_freshness_verified', 'independent_media_verified', 'native_execution_verified',
                      'restore_verified', 'write_plan_enabled'):
            self.assertIs(report[field], False, field)
        for name, info in report['files'].items():
            raw = (root / name).read_bytes()
            self.assertEqual(info, {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        text = json.dumps(report)
        for secret in (str(root), '11' * 32, 'OWN-HEADER', 'sony-get-camera-info'):
            self.assertNotIn(secret, text)

    def test_every_protocol_or_auth_action_has_a_durable_intent_first(self):
        real = s.SyntheticPeer.step
        folder = self.root / 'capture'
        def observed(peer, name):
            if name.startswith(('auth-', 'wire:')) or name in ('normal-before', 'normal-after', 'service-observation', 'service-stop'):
                events = sorted((folder / 'events').glob('*.json'))
                event = json.loads(events[-1].read_bytes())
                self.assertEqual(event['event'], 'INTENT', name)
                self.assertEqual(event['details']['operation'], name.removeprefix('wire:'))
            return real(peer, name)
        with patch.object(s.SyntheticPeer, 'step', observed):
            report, _, _ = self.run_case()
        self.assertEqual(report['phase'], 'SIMULATED_SESSION_COMPLETE')

    def test_global_then_job_lock_remain_until_report_publication(self):
        real = capturestore.Store.put
        peer = s.SyntheticPeer(self.files)
        def observed(store, name, raw, **kwargs):
            if name == 'session-report.private.json':
                self.assertEqual(peer.trace[0], 'global-lock-acquire')
                self.assertNotIn('global-lock-release', peer.trace)
                self.assertIsNotNone(store.lock)
                self.assertEqual(peer.trace[-1], 'close-normal')
            return real(store, name, raw, **kwargs)
        with patch.object(capturestore.Store, 'put', observed):
            report = s.rehearse('own', self.root / 'capture', peer)
        self.assertEqual(report['phase'], 'SIMULATED_SESSION_COMPLETE')
        self.assertEqual(peer.trace[-1], 'global-lock-release')

    def test_resources_complete_beyond_old_512_event_capacity(self):
        raw = s.c.synthetic_resource(False)
        files = {**self.files, **{'resources/' + n: raw for n in s.c.RESOURCE_FILES}}
        report, peer, _ = self.run_case(files=files, resources=True)
        self.assertEqual(report['phase'], 'SIMULATED_SESSION_COMPLETE')
        self.assertEqual(len(report['files']), 74)
        self.assertGreater(report['journal_records'], 512)
        self.assertLess(report['journal_records'], s.EVENTS_LIMIT)
        for n in s.c.RESOURCE_FILES: self.assertEqual(peer.counts['read:' + n], 2)

    def test_source_gate_stops_unknown_or_known_fl23_before_CP_or_settings(self):
        for i, ap in enumerate((bytes(len(self.files['appFw.so'])), self.fixture.fl23_ap)):
            report, peer, root = self.run_case(str(i), files={**self.files, 'appFw.so': ap})
            self.failed(report, peer, stop=1)
            self.assertNotIn('wire:read:cpapp-b.bin', peer.trace)
            self.assertNotIn('wire:ram', peer.trace)
            self.assertEqual((root / 'source/appFw.so').read_bytes(), ap)

    def test_complete_CP_mismatch_preserves_original_and_exits_once(self):
        files = {**self.files, 'cpapp-b.bin': b'Q' * len(self.files['cpapp-b.bin'])}
        report, peer, root = self.run_case(files=files)
        self.failed(report, peer, stop=1)
        self.assertNotIn('wire:ram', peer.trace)
        self.assertTrue((root / 'source/appFw.so').is_file())

    def test_service_already_present_or_multiple_normal_stops_before_auth(self):
        for i, updates in enumerate(({'service_count': 1}, {'normal_count': 2}, {'normal_count': True})):
            initial = s.SyntheticPeer(self.files).initial | updates
            report, peer, _ = self.run_case(str(i), initial=initial)
            self.failed(report, peer)
            self.assertNotIn('auth-normal-start', peer.trace)

    def test_initial_missing_or_different_identity_source_and_port_rejected(self):
        cases = ({'serial_source': 'usb-descriptor'}, {'serial_sha256': ''}, {'ports': []},
                 {'ports': [True]}, {'bus': -1}, {'model': 'ILCE-7CR'}, {'manufacturer': 'Other'})
        for i, update in enumerate(cases):
            initial = s.SyntheticPeer(self.files).initial | update
            report, peer, _ = self.run_case(str(i), initial=initial)
            self.failed(report, peer)
            self.assertNotIn('auth-normal-start', peer.trace)

    def test_first_auth_interruption_has_no_stop_or_retry(self):
        for name in ('auth-normal-start', 'auth-normal-verify'):
            report, peer, _ = self.run_case(name, fault=name)
            self.failed(report, peer, unknown=True)
            self.assertNotIn('auth-service-start', peer.trace)
            self.assertEqual(peer.trace.count(name), 1)

    def test_second_auth_interruption_has_no_stop_or_native_execution(self):
        for name in ('auth-service-start', 'auth-service-verify'):
            report, peer, _ = self.run_case(name, fault=name)
            self.failed(report, peer, unknown=True)
            self.assertNotIn('wire:hasp', peer.trace)

    def test_wrong_service_port_or_count_never_reauthenticates(self):
        for i, updates in enumerate(({'ports': [1, 3]}, {'service_count': 2}, {'normal_count': 1}, {'pid': 0x0e8a})):
            service = s.SyntheticPeer(self.files).service | updates
            report, peer, _ = self.run_case(str(i), service=service)
            self.failed(report, peer)
            self.assertNotIn('auth-service-start', peer.trace)

    def test_unknown_service_wait_has_no_followup_auth_or_stop(self):
        report, peer, _ = self.run_case(fault='service-observation')
        self.failed(report, peer, unknown=True)
        self.assertNotIn('auth-service-start', peer.trace)

    def test_return_identity_uses_same_source_bus_and_port(self):
        for i, updates in enumerate(({'serial_sha256': '22' * 32}, {'serial_source': 'usb-descriptor'},
                                     {'ports': [1, 3]}, {'bus': 2}, {'service_count': 1})):
            returned = s.SyntheticPeer(self.files).initial | updates
            report, peer, _ = self.run_case(str(i), returned=returned)
            self.failed(report, peer, stop=1)
            self.assertFalse(report['simulated_normal_identity_matched'])

    def test_unknown_stop_and_normal_return_are_not_retried(self):
        for name in ('service-stop', 'normal-after'):
            report, peer, _ = self.run_case(name, fault=name)
            self.failed(report, peer, unknown=True, stop=1)
            self.assertEqual(peer.trace.count('auth-normal-start'), 1)

    def test_failed_local_close_is_not_repeated(self):
        report, peer, _ = self.run_case(fault='close-service')
        self.failed(report, peer, stop=1)
        self.assertEqual(peer.trace.count('close-service'), 1)

    def test_empty_or_present_guard_including_preload_stops_without_cleanup(self):
        for i, (name, raw) in enumerate((('guard:libJit.so', b''), ('guard:a7c2.install.result', b'OWN'),
                                       ('guard:ld.so.preload', b''), ('guard:ld.so.preload', b'/own/library'))):
            report, peer, root = self.run_case(str(i), guards={name: raw})
            self.failed(report, peer, stop=1)
            self.assertNotIn('wire:read:appFw.so', peer.trace)
            self.assertEqual(peer.guards[name], raw)
            self.assertFalse(any('delete' in n or 'remove' in n for n in peer.trace))
            self.assertFalse(list((root / 'source').iterdir()))

    def test_oversized_guard_or_partial_response_stops_as_unknown(self):
        report, peer, _ = self.run_case('oversize', guards={'guard:libJit.so': s.Pattern(0, 4097)})
        self.failed(report, peer, unknown=True)
        report, peer, _ = self.run_case('partial', fault='partial:read:appFw.so')
        self.failed(report, peer, unknown=True)
        self.assertNotIn('wire:read:cpapp-b.bin', peer.trace)

    def test_end_guard_change_preserves_captured_materials_and_stops(self):
        report, peer, root = self.run_case(changes={'guard:libJit.so': b''})
        self.failed(report, peer, stop=1)
        self.assertTrue(report['program_content_matched_in_rehearsal'])
        self.assertEqual((root / 'source/appFw.so').read_bytes(), self.files['appFw.so'])

    def test_repeated_program_or_snapshot_change_fails_without_replay(self):
        cases = ({'appFw.so': self.files['appFw.so'][:-1] + b'Z'}, {'ram': b'BAD BK4'})
        for i, changes in enumerate(cases):
            report, peer, root = self.run_case(str(i), changes=changes)
            self.failed(report, peer, stop=1)
            self.assertEqual((root / 'source/appFw.so').read_bytes(), self.files['appFw.so'])

    def test_initial_RAM_and_saved_may_differ_without_saving(self):
        ap = {**self.fixture.ap, 0x02cf0001: s.bk4.Property(0, b'B', None, 1)}
        files = {**self.files, 'saved': self.fixture.snapshot(ap=ap)}
        report, peer, _ = self.run_case(files=files)
        self.assertEqual(report['phase'], 'SIMULATED_SESSION_COMPLETE')
        self.assertFalse(any('save' in n and n != 'wire:saved' for n in peer.trace))

    def test_failed_intent_sends_no_corresponding_request(self):
        real = capturestore.Store.event
        def fail(store, event, **details):
            if event == 'INTENT' and details.get('operation') == 'read:appFw.so':
                raise OSError('self-generated intent failure')
            return real(store, event, **details)
        with patch.object(capturestore.Store, 'event', fail): report, peer, _ = self.run_case()
        self.failed(report, peer, stop=1)
        self.assertNotIn('wire:read:appFw.so', peer.trace)

    def test_failed_stop_intent_never_sends_stop(self):
        real = capturestore.Store.event
        def fail(store, event, **details):
            if event == 'INTENT' and details.get('operation') == 'service-stop':
                raise OSError('self-generated stop intent failure')
            return real(store, event, **details)
        with patch.object(capturestore.Store, 'event', fail): report, peer, _ = self.run_case()
        self.failed(report, peer)
        self.assertFalse(report['simulated_service_stop_ack'])

    def test_stop_ack_journal_failure_never_repeats_stop(self):
        real = capturestore.Store.event
        def fail(store, event, **details):
            if event == 'ACK' and details.get('operation') == 'service-stop':
                raise OSError('self-generated stop ACK failure')
            return real(store, event, **details)
        with patch.object(capturestore.Store, 'event', fail): report, peer, _ = self.run_case()
        self.failed(report, peer, stop=1)
        self.assertTrue(report['simulated_service_stop_ack'])
        self.assertNotIn('normal-after', peer.trace)

    def test_post_response_file_sync_error_is_known_healthy_exit(self):
        real = capturestore.Sink.finish
        def fail(sink):
            if sink.relative == 'source/appFw.so': raise OSError('self-generated sync failure')
            return real(sink)
        with patch.object(capturestore.Sink, 'finish', fail): report, peer, _ = self.run_case()
        self.failed(report, peer, stop=1)

    def test_disk_error_mid_payload_or_interrupt_is_unknown(self):
        real = capturestore.Sink.write
        for i, exc in enumerate((OSError('self-generated full disk'), KeyboardInterrupt())):
            def fail(sink, raw):
                if sink.relative == 'source/appFw.so': raise exc
                return real(sink, raw)
            with patch.object(capturestore.Sink, 'write', fail): report, peer, _ = self.run_case(str(i))
            self.failed(report, peer, unknown=True)

    def test_resource_change_or_mixed_layout_fails_known(self):
        raw = s.c.synthetic_resource(False)
        files = {**self.files, **{'resources/' + n: raw for n in s.c.RESOURCE_FILES}}
        key = 'resources/' + s.c.RESOURCE_FILES[-1]
        report, peer, _ = self.run_case('changed', files=files, resources=True, changes={key: raw[:-1] + b'Z'})
        self.failed(report, peer, stop=1)
        report, peer, _ = self.run_case('mixed', files=files | {key: s.c.synthetic_resource(True)}, resources=True)
        self.failed(report, peer, stop=1)

    def test_existing_directory_and_fake_lock_failure_prevent_device_actions(self):
        _, _, root = self.run_case()
        before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        peer = s.SyntheticPeer(self.files)
        with self.assertRaises(FileExistsError): s.rehearse('own', root, peer)
        self.assertEqual(peer.trace, ['global-lock-acquire', 'global-lock-release'])
        self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()})
        peer = s.SyntheticPeer(self.files, fault='global-lock-acquire')
        with self.assertRaises(TimeoutError): s.rehearse('own', self.root / 'lock-fail', peer)
        self.assertFalse((self.root / 'lock-fail').exists())

    def test_synthetic_preflight_and_no_backend_policy_overrides(self):
        for opts in ({'version': '2.00'}, {'battery': 49}, {'battery': True}):
            peer = s.SyntheticPeer(self.files, **opts)
            with self.assertRaises(ValueError): s.rehearse('own', self.root / 'preflight', peer)
            self.assertEqual(peer.trace, [])
        for name in ('backend', 'policy', 'roles', 'serial', 'camera_lock'):
            with self.assertRaises(TypeError): s.rehearse('own', self.root / 'unused', s.SyntheticPeer(self.files), **{name: True})
        class Subclass(s.SyntheticPeer): pass
        with self.assertRaises(TypeError): s.rehearse('own', self.root / 'unused', Subclass(self.files))

    def test_bounded_event_capacity_is_explicit_and_default_unchanged(self):
        with self.assertRaises(ValueError):
            capturestore.Store(self.root / 'invalid', events_limit=2049)
        for value in (0, True, 1.2):
            with self.assertRaises(ValueError): capturestore.Store(self.root / 'invalid', events_limit=value)
        store = capturestore.Store(self.root / 'default')
        try:
            self.assertEqual(store.events_limit, 512)
            store.seq = 512
            with self.assertRaises(ValueError): store.event('EXCESS')
        finally: store.close()

    def test_stdlib_import_does_not_load_camera_or_native_stack(self):
        code = ('import sys; from lutphoto import capturesession; '
                'assert not any(n == "usb" or n.startswith("usb.") or n in '
                '("transport", "core", "macfl23.session", "numpy") for n in sys.modules)')
        result = subprocess.run([sys.executable, '-S', '-B', '-c', code],
            cwd=Path(__file__).resolve().parents[2], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class GuardProtocolTests(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        stock = SimpleNamespace(kind='stock', ap_bytes=16, cp_bytes=16)
        patch.object(s.programidentity, '_load_policy', return_value=SimpleNamespace(sources=(stock,))).start()
        patch.object(p.workercontracts, 'load_sources', return_value=({}, SOURCES)).start()
        self.addCleanup(patch.stopall)
        self.channel = p.OfflineChannel('own', guards=True)

    def response(self, raw):
        self.channel.feed(struct.pack('<IHH4B', len(raw), 0x40, self.channel.sequence, 0, 0, 0, 0))
        return self.channel.feed(raw)

    def selected(self):
        self.channel.begin('select:guard:libJit.so')
        self.response(bytes(4))
        self.channel.begin('read:guard:libJit.so', capturestore.Sink(4096, budget=self.channel.budget))

    def test_fixed_guard_inventory_paths_and_opt_in(self):
        self.assertEqual(len(self.channel.guard_names), 14)
        self.assertEqual(len(self.channel.requests), 35)
        self.assertIn('guard:a7c2-preview-staged.so', self.channel.guard_names)
        self.assertEqual(self.channel.requests['select:guard:libJit.so'].data,
                         b'\x01\x10\x0f\x00\0/tmp/jiritsu/libJit.so\0')
        self.assertTrue(self.channel.requests['select:guard:ld.so.preload'].data.endswith(b'/../../etc/ld.so.preload\0'))
        self.assertNotIn('read:guard:libJit.so', p.OfflineChannel('own').requests)

    def test_missing_status_only_is_guard_absence(self):
        self.selected()
        result = self.response(struct.pack('<I', 0x10000006))
        self.assertTrue(result['guard_absent'])
        self.assertFalse(self.channel.blocked)
        self.assertEqual(self.channel.budget.used, 0)

    def test_present_empty_file_is_not_absence(self):
        self.selected()
        result = self.response(bytes(4))
        self.assertFalse(result['guard_absent'])
        self.assertTrue(self.channel.blocked)
        self.assertFalse(self.channel.unknown)
        self.channel.claim_exit()

    def test_missing_with_extra_payload_or_unknown_status_is_rejected(self):
        self.selected()
        with self.assertRaises(p.CompleteResponseError): self.response(struct.pack('<I', 0x10000006) + b'X')
        self.assertFalse(self.channel.unknown)
        self.channel.claim_exit()
        self.channel = p.OfflineChannel('own', guards=True)
        self.selected()
        with self.assertRaises(p.CompleteResponseError): self.response(struct.pack('<I', 0xdead))
        self.assertFalse(self.channel.unknown)

    def test_missing_never_applies_to_program_reads(self):
        self.channel.begin('select:appFw.so'); self.response(bytes(4))
        self.channel.begin('read:appFw.so', capturestore.Sink(16, exact=16, budget=self.channel.budget))
        with self.assertRaises(p.CompleteResponseError): self.response(struct.pack('<I', 0x10000006))
        self.assertTrue(self.channel.blocked)

    def test_guard_must_use_hash_only_sink(self):
        self.channel.begin('select:guard:libJit.so'); self.response(bytes(4))
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            store = capturestore.Store(Path(temp).resolve() / 'new')
            sink = capturestore.Sink(4096, budget=self.channel.budget, store=store, relative='source/forbidden')
            try:
                with self.assertRaises(ValueError): self.channel.begin('read:guard:libJit.so', sink)
            finally:
                sink.close(); store.close()

    def test_unexpected_source_guard_inventory_rejected(self):
        with patch.object(p.workercontracts, 'load_sources', return_value=({}, {
                'src/fl23/core.py': b'NATIVE_PATHS=set()',
                'src/looks/looktool/devicesession.py': b'TEMP_NAMES=set()'})):
            with self.assertRaises(ValueError): p.OfflineChannel('own', guards=True)


if __name__ == '__main__':
    unittest.main()
