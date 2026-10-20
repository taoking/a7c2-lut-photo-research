"""Own keys/challenges and independent packet oracles; no device or downloads."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lutphoto import captureauth as a
from lutphoto.capturestore import Budget, Store, encoded
from lutphoto.capturesession import SyntheticPeer

KEYS = a._Keys((b'z' * 512,) * 3, tuple(bytes([11 + n]) * 512 for n in range(3)))
NORMAL = SyntheticPeer({}).initial
SERVICE = SyntheticPeer({}).service
PIN = {'commit': 'own-fixture', 'archive_sha256': '00' * 32}


def response(status, payload=b'', salt=0):
    return struct.pack('>HH', ~(status + salt) & 0xffff, salt) + payload.ljust(512, b'\0')


def tape(pid, algorithms=(8, 8, 8), *, salt=0):
    transfers, writes = [('control', 0)], []
    challenge = b'z' * 512
    for index, algorithm in enumerate(algorithms):
        transfers.extend((('write', 516), ('read', response(algorithm, challenge, salt))))
        message = challenge[:4] if pid == 0x0e8a else challenge + KEYS.sha256[index]
        if algorithm == 8: digest = hashlib.sha256(message).digest()
        elif pid == 0x0e8a: digest = hashlib.sha1(challenge[:4]).digest()
        else: digest = bytes.fromhex('e62fbb6a04ab5fe080dbe235271d214f6cf05569')
        proof = b'\x01' + digest
        writes.extend((b'\xff\xfe\0\0' + bytes(512), b'\xff\xfc\0\0' + proof.ljust(512, b'\0')))
        transfers.extend((('write', 516), ('read', response(4, salt=salt))))
    writes.append(b'\xff\xfa\0\0' + bytes(512))
    transfers.extend((('write', 516), ('read', response(6, b'\x01', salt))))
    if pid == 0x0336: transfers.append(('control', 0))
    return a.SyntheticDriver(pid, transfers, expected_writes=writes)


class HashAndSourceTests(unittest.TestCase):
    def test_short_faulty_sha1_matches_standard_sha1(self):
        for size in range(32):
            value = bytes(range(size))
            self.assertEqual(a._faulty_sha1(value), hashlib.sha1(value).digest())

    def test_long_synthetic_golden_vectors_from_pinned_pure_hash_reference(self):
        self.assertEqual(a._faulty_sha1(bytes(512)).hex(), '338846204ee1c9c28fbc9a607d542d741a594f15')
        self.assertEqual(a._faulty_sha1(b'z' * 1024).hex(), 'e62fbb6a04ab5fe080dbe235271d214f6cf05569')
        self.assertNotEqual(a._faulty_sha1(b'z' * 1024), hashlib.sha1(b'z' * 1024).digest())

    def test_proofs_distinguish_normal_prefix_service_key_and_round(self):
        challenge = bytes(range(256)) * 2
        for index in range(3):
            self.assertEqual(a._proof(KEYS, 0x0e8a, index, 8, challenge), b'\1' + hashlib.sha256(challenge[:4]).digest())
            self.assertEqual(a._proof(KEYS, 0x0336, index, 8, challenge), b'\1' + hashlib.sha256(challenge + KEYS.sha256[index]).digest())

    def test_hash_and_challenge_bounds(self):
        for value in (bytes(1025), bytearray(1), 'not-bytes'):
            with self.assertRaises(ValueError): a._faulty_sha1(value)
        for pid, index, alg, raw in ((1, 0, 8, bytes(512)), (0x0336, True, 8, bytes(512)),
                                   (0x0336, 3, 8, bytes(512)), (0x0336, 0, 9, bytes(512)), (0x0336, 0, 8, b'')):
            with self.assertRaises(ValueError): a._proof(KEYS, pid, index, alg, raw)

    def test_source_keys_are_literal_parsed_without_executing_module(self):
        raw = ('raise AssertionError("Module must not execute")\n'
               'senserKeysSha1=' + repr(list(KEYS.sha1)) + '\nsenserKeysSha256=' + repr(list(KEYS.sha256))).encode()
        with patch.object(a, '_sources', return_value=(PIN, {'src/fl23/vendor/pmca/usb/constants.py': raw})):
            pin, keys = a._keys('own')
        self.assertEqual(keys, KEYS); self.assertEqual(pin, PIN)
        self.assertNotIn('zzzz', repr(keys))

    def test_bad_key_layout_or_expression_is_rejected(self):
        for raw in (b'senserKeysSha1=[]\nsenserKeysSha256=[]',
                    b'senserKeysSha1=evil()\nsenserKeysSha256=[]'):
            with patch.object(a, '_sources', return_value=(PIN, {'src/fl23/vendor/pmca/usb/constants.py': raw})):
                with self.assertRaises(ValueError): a._keys('own')

    def test_real_source_pin_is_offline_and_preserves_old_lock_identity(self):
        pin = json.loads(a.PIN.read_bytes())
        old = json.loads((a.w.ROOT / 'research/upstream-backup-loader.lock.json').read_bytes())
        self.assertEqual(len(pin['files']), 9)
        self.assertIs(pin['camera_integration_enabled'], False)
        for field in ('commit', 'archive_bytes', 'archive_sha256', 'baseline_lock_sha256'):
            self.assertEqual(pin[field], old[field])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'invalid.zip'; path.write_bytes(b'Not the pinned archive')
            with self.assertRaises(ValueError): a._sources(path)


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.store = Store(self.root / 'new-auth'); self.addCleanup(self.store.close)
        self.clock = [0.0]
        self.budget = Budget(32768, seconds=120, clock=lambda: self.clock[0])
        patch.object(a, '_keys', return_value=(PIN, KEYS)).start(); self.addCleanup(patch.stopall)
        self.flow = a.OfflineAuthFlow('own', self.store, NORMAL, budget=self.budget)

    def ready(self, algorithms=(8, 8, 8)):
        normal, service = tape(0x0e8a, algorithms), tape(0x0336, algorithms)
        self.flow.normal_auth(normal); self.flow.service_auth(SERVICE, service)
        return normal, service

    def reset_flow(self):
        self.budget = Budget(32768, seconds=120, clock=lambda: self.clock[0])
        self.flow = a.OfflineAuthFlow('own', self.store, NORMAL, budget=self.budget)

    def assert_stopped(self, driver):
        count = len(driver.trace)
        for action in (lambda: self.flow.normal_auth(driver), lambda: self.flow.service_auth(SERVICE, driver), self.flow.stop,
                       lambda: self.flow.observe_return(NORMAL)):
            with self.assertRaises(RuntimeError): action()
        self.assertEqual(len(driver.trace), count)

    def test_full_raw_flow_exact_packets_lengths_and_boundaries(self):
        normal, service = self.ready()
        self.flow.stop(); self.flow.observe_return(NORMAL)
        result = self.flow.summary()
        self.assertEqual(result['phase'], 'SYNTHETIC_RETURN_MATCHED')
        self.assertEqual(result['status'], 'SIMULATED_AUTH_COMPLETE')
        self.assertFalse(result['outcome_unknown']); self.assertFalse(result['blocked'])
        self.assertEqual(result['accepted_auth_bytes'], 28 * 516)
        self.assertEqual((normal.used, service.used), (15, 16))
        self.assertEqual(normal.written, list(normal.expected))
        self.assertEqual(service.written, list(service.expected))
        for field in ('camera_operations_performed', 'actual_authentication_verified', 'actual_source_identity_verified',
                      'physical_protocol_verified', 'fresh_normal_observation_verified', 'global_camera_lock_acquired',
                      'restore_verified', 'write_plan_enabled', 'resume_allowed'):
            self.assertIs(result[field], False)
        with self.assertRaises(RuntimeError): self.flow.stop()

    def test_both_hash_modes_and_mixed_rounds(self):
        normal, service = self.ready((2, 8, 2))
        self.flow.stop(); self.flow.observe_return(NORMAL)
        self.assertEqual(service.written, list(service.expected))
        self.assertEqual(self.flow.summary()['phase'], 'SYNTHETIC_RETURN_MATCHED')

    def test_response_salt_is_subtracted_as_in_pinned_source(self):
        self.flow.normal_auth(tape(0x0e8a, salt=17))
        self.flow.service_auth(SERVICE, tape(0x0336, salt=19))
        self.flow.stop(); self.flow.observe_return(NORMAL)
        self.assertFalse(self.flow.unknown)

    def test_golden_start_stop_and_packet_structure(self):
        self.assertEqual(a.START, (0x43, 1, 0x37ff, 0xd7aa))
        self.assertEqual(a.STOP, (0x43, 1, 0xc800, 0x2855))
        self.assertEqual(a.AUTH.size, 516)
        self.assertEqual(tape(0x0e8a).expected[0][:4], bytes.fromhex('fffe0000'))

    def test_no_none_boolean_or_nonzero_control_ack(self):
        for index, value in enumerate((None, False, True, 1, b'')):
            if index:
                self.reset_flow()
            driver = tape(0x0e8a); driver.transfers[0] = ('control', value)
            with self.assertRaises(ValueError): self.flow.normal_auth(driver)
            self.assertTrue(self.flow.unknown); self.assertEqual(driver.used, 1)
            self.assert_stopped(driver)

    def test_control_exception_timeout_and_interrupt_propagate_without_stop(self):
        for index, error in enumerate((OSError('own error'), TimeoutError('own timeout'), KeyboardInterrupt())):
            if index: self.reset_flow()
            driver = tape(0x0e8a); driver.transfers[0] = ('control', error)
            with self.assertRaises(type(error)): self.flow.normal_auth(driver)
            self.assertTrue(self.flow.unknown); self.assertEqual(driver.used, 1)
            self.assert_stopped(driver)

    def test_short_none_or_boolean_write_never_retried(self):
        for index, value in enumerate((0, 515, None, True)):
            if index: self.reset_flow()
            driver = tape(0x0e8a); driver.transfers[1] = ('write', value)
            with self.assertRaises(ValueError): self.flow.normal_auth(driver)
            self.assertEqual(driver.used, 2); self.assertTrue(self.flow.unknown)
            self.assert_stopped(driver)

    def test_short_oversize_mutable_and_empty_auth_responses_are_unknown(self):
        for index, value in enumerate((bytes(515), bytes(517), b'', bytearray(516), None)):
            if index: self.reset_flow()
            driver = tape(0x0e8a); driver.transfers[2] = ('read', value)
            with self.assertRaises(ValueError): self.flow.normal_auth(driver)
            self.assertEqual(driver.used, 3); self.assertTrue(self.flow.unknown)
            self.assert_stopped(driver)

    def test_challenge_proof_and_final_status_errors_stop(self):
        for index, (at, raw) in enumerate(((2, response(9)), (4, response(3)), (14, response(6, b'\0')), (14, response(7, b'\1')))):
            if index: self.reset_flow()
            driver = tape(0x0e8a); driver.transfers[at] = ('read', raw)
            with self.assertRaises(ValueError): self.flow.normal_auth(driver)
            self.assertEqual(driver.used, at + 1); self.assertTrue(self.flow.unknown)
            self.assert_stopped(driver)

    def test_packet_endianness_error_and_negative_decoded_status_rejected(self):
        for index, raw in enumerate((struct.pack('<HH512s', ~8 & 0xffff, 0, b'z'*512), struct.pack('>HH512s', 0xffff, 1, b'z'*512))):
            if index: self.reset_flow()
            driver = tape(0x0e8a); driver.transfers[2] = ('read', raw)
            with self.assertRaises(ValueError): self.flow.normal_auth(driver)
            self.assertTrue(self.flow.unknown)

    def test_service_failure_does_not_reauthenticate_or_stop(self):
        self.flow.normal_auth(tape(0x0e8a))
        driver = tape(0x0336); driver.transfers[8] = ('read', TimeoutError('own service response'))
        with self.assertRaises(TimeoutError): self.flow.service_auth(SERVICE, driver)
        self.assertTrue(self.flow.unknown); self.assertEqual(driver.used, 9)
        self.assert_stopped(driver)

    def test_same_port_pid_and_unique_service_observation_required(self):
        for index, change in enumerate(({'bus': 2}, {'ports': [1, 3]}, {'pid': 0x0e8a}, {'normal_count': 1}, {'service_count': 2}, {'service_count': True})):
            if index: self.reset_flow()
            self.flow.normal_auth(tape(0x0e8a)); driver = tape(0x0336)
            with self.assertRaises(ValueError): self.flow.service_auth(SERVICE | change, driver)
            self.assertEqual(driver.used, 0); self.assertTrue(self.flow.unknown)
            self.assert_stopped(driver)

    def test_return_requires_same_source_identity_bus_and_port(self):
        for index, change in enumerate(({'serial_source': 'usb-descriptor'}, {'serial_sha256': '22'*32}, {'bus': 2}, {'ports': [1,3]}, {'service_count': 1})):
            if index: self.reset_flow()
            self.ready(); self.flow.stop()
            with self.assertRaises(ValueError): self.flow.observe_return(NORMAL | change)
            self.assertTrue(self.flow.unknown)
            self.assert_stopped(self.flow.service.driver)

    def test_stop_none_timeout_and_short_ack_cannot_be_repeated(self):
        for index, value in enumerate((None, 1, TimeoutError('own stop'))):
            if index: self.reset_flow()
            _, service = self.ready(); service.transfers[-1] = ('control', value)
            with self.assertRaises(type(value) if isinstance(value, BaseException) else ValueError): self.flow.stop()
            self.assertTrue(self.flow.exit_attempted); self.assertTrue(self.flow.unknown)
            self.assertEqual(service.used, 16); self.assert_stopped(service)

    def test_durable_intent_precedes_raw_io(self):
        real = a.SyntheticDriver._take
        def observe(driver, kind, timeout):
            value = json.loads(sorted((self.store.path / 'events').glob('*.json'))[-1].read_bytes())
            self.assertEqual(value['event'], 'INTENT')
            return real(driver, kind, timeout)
        with patch.object(a.SyntheticDriver, '_take', observe):
            self.ready(); self.flow.stop()

    def test_intent_persistence_failure_sends_nothing_and_blocks_retry(self):
        driver = tape(0x0e8a)
        with patch.object(Store, 'event', side_effect=OSError('own journal')):
            with self.assertRaises(OSError): self.flow.normal_auth(driver)
        self.assertEqual(driver.used, 0); self.assertTrue(self.flow.blocked); self.assertFalse(self.flow.unknown)
        self.assert_stopped(driver)

    def test_stop_ack_journal_failure_preserves_result_and_does_not_replay(self):
        _, service = self.ready(); real = Store.event
        def fail(store, event, **details):
            if event == 'ACK' and details.get('operation') == 'service-stop': raise OSError('own ACK sync')
            return real(store, event, **details)
        with patch.object(Store, 'event', fail):
            with self.assertRaises(OSError): self.flow.stop()
        self.assertEqual(self.flow.phase, 'STOP_CONTROL_RETURNED')
        self.assertTrue(self.flow.exit_attempted); self.assertTrue(self.flow.blocked); self.assertFalse(self.flow.unknown)
        self.assertEqual(self.flow.summary()['status'], 'NEEDS_REVIEW')
        self.assert_stopped(service)

    def test_stop_intent_failure_sends_no_control_and_freezes_flow(self):
        _, service = self.ready()
        with patch.object(Store, 'event', side_effect=OSError('own stop INTENT')):
            with self.assertRaises(OSError): self.flow.stop()
        self.assertEqual(service.used, 15)
        self.assertFalse(self.flow.exit_attempted); self.assertTrue(self.flow.blocked)
        self.assertEqual(self.flow.summary()['status'], 'NEEDS_REVIEW')
        self.assert_stopped(service)

    def test_normal_verify_ack_failure_never_opens_second_auth_stage(self):
        normal = tape(0x0e8a); real = Store.event
        def fail(store, event, **details):
            if event == 'ACK' and details.get('operation') == 'auth-normal-verify': raise OSError('own verify ACK')
            return real(store, event, **details)
        with patch.object(Store, 'event', fail):
            with self.assertRaises(OSError): self.flow.normal_auth(normal)
        self.assertEqual(self.flow.phase, 'WAIT_SERVICE')
        self.assertFalse(self.flow.unknown); self.assertTrue(self.flow.blocked)
        service = tape(0x0336)
        with self.assertRaises(RuntimeError): self.flow.service_auth(SERVICE, service)
        self.assertEqual(service.used, 0)

    def test_deadline_shared_across_both_stages_and_each_raw_call(self):
        normal = tape(0x0e8a); self.clock[0] = 119
        self.flow.normal_auth(normal)
        self.assertTrue(all(timeout == 1000 for _, timeout in normal.trace))
        self.clock[0] = 120; service = tape(0x0336)
        with self.assertRaises(TimeoutError): self.flow.service_auth(SERVICE, service)
        self.assertEqual(service.used, 0); self.assertEqual(self.budget.deadline, 120)
        self.assertTrue(self.flow.blocked)

    def test_timeout_after_completed_raw_transfer_stops_without_next_io(self):
        driver = tape(0x0e8a); real = a.SyntheticDriver._take
        def expire(driver, kind, timeout):
            value = real(driver, kind, timeout); self.clock[0] = 120
            return value
        with patch.object(a.SyntheticDriver, '_take', expire):
            with self.assertRaises(TimeoutError): self.flow.normal_auth(driver)
        self.assertEqual(driver.used, 1); self.assertTrue(self.flow.unknown)

    def test_total_byte_limit_checked_before_raw_read(self):
        self.budget.limit = 516; driver = tape(0x0e8a)
        with self.assertRaises(ValueError): self.flow.normal_auth(driver)
        self.assertEqual(driver.used, 2); self.assertEqual(self.budget.used, 516)
        self.assertTrue(self.flow.unknown)

    def test_no_raw_driver_or_identity_policy_override(self):
        class Derived(a.SyntheticDriver): pass
        for driver in (object(), Derived(0x0e8a, []), tape(0x0336)):
            with self.assertRaises(TypeError): self.flow.normal_auth(driver)
        for key in ('driver', 'policy', 'keys', 'serial', 'camera_lock'):
            with self.assertRaises(TypeError): a.OfflineAuthFlow('own', self.store, NORMAL, **{key: True})

    def test_invalid_initial_model_source_or_port_has_no_auth_io(self):
        for change in ({'serial_source':'usb-descriptor'}, {'model':'OTHER'}, {'ports':[]}, {'service_count':1}):
            with self.assertRaises(ValueError): a.OfflineAuthFlow('own', self.store, NORMAL | change)

    def test_out_of_order_calls_and_duplicate_auth_do_not_send(self):
        service = tape(0x0336)
        with self.assertRaises(RuntimeError): self.flow.service_auth(SERVICE, service)
        with self.assertRaises(RuntimeError): self.flow.stop()
        with self.assertRaises(RuntimeError): self.flow.observe_return(NORMAL)
        self.assertEqual(service.used, 0)
        normal = tape(0x0e8a); self.flow.normal_auth(normal)
        with self.assertRaises(RuntimeError): self.flow.normal_auth(normal)
        self.assertEqual(normal.used, 15)

    def test_summary_and_durable_log_do_not_contain_secrets(self):
        self.ready(); self.flow.stop(); self.flow.observe_return(NORMAL)
        text = json.dumps(self.flow.summary()) + ''.join(path.read_text() for path in (self.store.path / 'events').glob('*.json'))
        for secret in (str(self.store.path), '11'*32, 'zzzz', repr(KEYS.sha1[0]), self.flow.service.driver.written[1].hex()):
            self.assertNotIn(secret, text)

    def test_import_requires_no_usb_crypto_package_or_numpy(self):
        code = ('import sys; from lutphoto import captureauth; '
                'assert not any(n=="usb" or n.startswith("usb.") or n.startswith("Cryptodome") '
                'or n in ("Crypto","transport","core","macfl23.session","numpy") for n in sys.modules)')
        result = subprocess.run([sys.executable,'-S','-B','-c',code],capture_output=True,cwd=a.w.ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
