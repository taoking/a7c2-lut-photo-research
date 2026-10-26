"""Ordered self-made transfers through the real raw exchange, without USB.

Boundary cases informed by QAQLeonard 3.0.3; provenance in round 74.
The queue persists across requests, so a leftover end transfer cannot vanish
or be supplied from a separate queue selected by the requested read kind.
"""
from collections import deque
import hashlib
import struct
import unittest
from unittest.mock import patch

from lutphoto import captureprotocol as p, captureraw as r
from research.tests import test_captureauth as auth, test_captureprotocol as fixtures


def header(size, sequence=1):
    return struct.pack('<IHH4B', size, 0x40, sequence, 0, 0, 0, 0)


class Wire:
    def __init__(self, replies):
        self.replies = deque(replies)
        self.pending = deque()
        self.reads, self.writes = [], []

    def write(self, endpoint, raw, *, timeout):
        self.writes.append(raw)
        self.pending.extend(self.replies.popleft())
        return len(raw)

    def read(self, endpoint, maximum, *, timeout):
        self.reads.append((maximum, timeout))
        if not self.pending:
            raise TimeoutError('Self-made peer has no transfer queued')
        raw = self.pending.popleft()
        if isinstance(raw, BaseException):
            raise raw
        if len(raw) > maximum:
            self.pending.appendleft(raw[maximum:])
            raw = raw[:maximum]
        return raw


class FramingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ProtocolTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.channel = self.fixture.c

    def connect(self, replies):
        peer = r.p.s.SyntheticPeer({})
        device = r.SyntheticDevice(0x0336, auth.tape(0x0336), peer)
        port = r._Port(device, self.fixture.budget, self.channel)
        # Start at the already authenticated read boundary; no auth/USB calls.
        port.authenticated = True
        wire = Wire(replies)
        # Keep these patches on this exact synthetic object only.
        self.write_patch = patch.object(device, 'write', side_effect=wire.write)
        self.read_patch = patch.object(device, 'read', side_effect=wire.read)
        self.write_patch.start(); self.read_patch.start()
        self.addCleanup(self.write_patch.stop); self.addCleanup(self.read_patch.stop)
        self.port, self.wire = port, wire

    def read(self, name='ram'):
        return self.port.exchange(name, self.fixture.sink(name))

    def assert_payload(self, result, raw):
        self.assertEqual(result['payload'],
                         {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})

    def assert_no_replay(self):
        writes = list(self.wire.writes)
        with self.assertRaises(RuntimeError):
            self.read('saved')
        self.assertEqual(self.wire.writes, writes)
        self.assertTrue(self.channel.unknown)
        with self.assertRaises(RuntimeError):
            self.channel.claim_exit()

    def test_aligned_final_payload_needs_no_extra_transfer(self):
        raw = b'A' * 512
        self.connect([[header(len(raw)), raw]])
        self.assert_payload(self.read(), raw)
        self.assertEqual(len(self.wire.reads), 2)
        self.assertFalse(self.channel.active)

    def test_nonempty_continuation_is_payload_not_discarded(self):
        raw = b'A' * 32768 + b'B' * 137
        self.connect([[header(len(raw)), raw[:32768], raw[32768:]]])
        self.assert_payload(self.read(), raw)
        self.assertEqual(self.fixture.budget.used, len(raw))
        self.assertEqual([size for size, _ in self.wire.reads], [12, 32768, 137])

    def test_empty_transfer_before_header_is_consumed(self):
        self.connect([[b'', header(3), b'abc']])
        self.assert_payload(self.read(), b'abc')
        self.assertEqual(self.channel.feeds, 3)

    def test_optional_final_empty_survives_until_next_request(self):
        raw = b'A' * 32768
        self.connect([[header(len(raw)), raw, b''], [header(4, 2), b'next']])
        self.assert_payload(self.read(), raw)
        self.assertEqual(list(self.wire.pending), [b''])
        self.assertEqual(len(self.wire.reads), 2)
        self.assert_payload(self.read('saved'), b'next')
        self.assertEqual(len(self.wire.reads), 5)
        self.assertEqual(self.channel.sequence, 3)
        self.assertEqual(len(self.wire.writes), 2)

    def test_fragmented_payload_and_internal_empty_transfers(self):
        raw = b'A' * 32768 + b'B' * 132
        self.connect([[header(len(raw)), raw[:12000], b'', raw[12000:32768],
                       b'', raw[32768:32780], b'', raw[32780:]]])
        self.assert_payload(self.read(), raw)
        self.assertEqual(self.channel.wire_bytes, 17 + 12 + len(raw))

    def test_one_megabyte_continuation_retains_empty_boundary_and_sequence(self):
        raw = b'A' * p.FRAME + b'B' * 512
        transfers = [header(len(raw))]
        for at in range(0, p.FRAME, p.BLOCK):
            transfers.extend([raw[at:at + p.BLOCK], b''])
        transfers.extend([header(512), raw[p.FRAME:]])
        self.connect([transfers])
        result = self.read()
        self.assert_payload(result, raw)
        self.assertEqual(result['frames'], 2)
        self.assertEqual(self.channel.sequence, 2)

    def test_header_shaped_nonempty_continuation_is_preserved(self):
        raw = b'A' * 32768 + header(7, 900) + b'payload'
        self.connect([[header(len(raw)), raw[:32768], raw[32768:]]])
        self.assert_payload(self.read(), raw)

    def test_empty_transfers_cannot_refresh_deadline(self):
        self.connect([[b'', b'', header(1), b'x']])
        self.fixture.budget.deadline = 1.0
        original = self.wire.read
        def timed(*args, **kwargs):
            value = original(*args, **kwargs)
            self.fixture.clock[0] += 0.5
            return value
        self.port._device.read.side_effect = timed
        with self.assertRaises(TimeoutError):
            self.read()
        self.assertEqual(self.wire.reads, [(12, 1000), (12, 500)])
        self.assertEqual(self.fixture.budget.deadline, 1.0)
        self.assert_no_replay()

    def test_empty_transfers_obey_feed_budget_without_more_io(self):
        self.connect([[b'', b'', header(1), b'x']])
        with patch.object(p, 'MAX_FEEDS', 2):
            with self.assertRaises(ValueError):
                self.read()
        self.assertEqual(len(self.wire.reads), 2)
        self.assertEqual(self.channel.feeds, 2)
        self.assertEqual(self.fixture.budget.used, 0)
        self.assert_no_replay()

    def test_missing_body_after_empty_transfer_is_unknown_not_success(self):
        self.connect([[header(1024), b'A' * 512, b'']])
        with self.assertRaises(TimeoutError):
            self.read()
        self.assertEqual(self.fixture.budget.used, 512)
        self.assertIsNone(self.channel.result)
        self.assert_no_replay()

    def test_empty_then_missing_header_preserves_timeout_and_blocks_next_request(self):
        self.connect([[b'']])
        with self.assertRaises(TimeoutError):
            self.read()
        self.assertEqual(len(self.wire.reads), 2)
        self.assert_no_replay()

    def test_wrong_sequence_after_empty_transfer_does_not_replay(self):
        self.connect([[b'', header(1, 2), b'x']])
        with self.assertRaises(ValueError):
            self.read()
        self.assertEqual(len(self.wire.reads), 2)
        self.assertEqual(self.fixture.budget.used, 0)
        self.assert_no_replay()

    def test_short_write_stops_before_any_read(self):
        self.connect([[header(1), b'x']])
        def short(*args, **kwargs):
            return self.wire.write(*args, **kwargs) - 1
        self.port._device.write.side_effect = short
        with self.assertRaises(ValueError):
            self.read()
        self.assertEqual(len(self.wire.writes), 1)
        self.assertEqual(self.wire.reads, [])
        self.assert_no_replay()


if __name__ == '__main__':
    unittest.main()
