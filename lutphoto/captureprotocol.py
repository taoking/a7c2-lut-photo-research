"""Passive Senser request/framing parser; no driver, USB or auth of its own.

Encodings derive from pinned QAQLeonard transport and ma1co Sony-PMCA-RE.
See ACKNOWLEDGEMENTS.md and the retained Sony-PMCA-RE MIT license.
Response echo/zero-field checks are a conservative, UNVERIFIED profile.
Used by both synthetic sessions and the restricted native capture owner.
File/snapshot length-delimited reads follow QAQLeonard 3.0.3; see round 74.
"""
from dataclasses import dataclass
from types import MappingProxyType
import struct

from . import bk4, customcontracts, programidentity, workercontracts
from .capturestore import Budget, Sink

HEADER = struct.Struct('<IHH4B')
FRAME = 0x100000
BLOCK = 0x8000
MAX_REQUESTS = 512
MAX_FEEDS = 65536
MAX_REQUEST_BYTES = 1024


class CompleteResponseError(ValueError):
    """All framing consumed; command status or completed content rejected."""


@dataclass(frozen=True)
class _Request:
    pfunc: int
    data: bytes
    limit: int
    exact: int | None
    status_prefix: bool = False
    response: int = 0
    guard: bool = False


@dataclass(frozen=True)
class Read:
    kind: str
    maximum: int
    timeout_ms: int


def _guard_paths(sources):
    names = (set(workercontracts.literal(sources['src/fl23/core.py'], 'NATIVE_PATHS'))
             | set(workercontracts.literal(sources['src/looks/looktool/devicesession.py'], 'TEMP_NAMES')))
    if len(names) != 13 or any(type(n) is not str or '/' in n or not n for n in names):
        raise ValueError('Fixed temporary-state inventory differs')
    return tuple(('guard:' + n, '/tmp/jiritsu/' + n) for n in sorted(names)) + (
        ('guard:ld.so.preload', '/tmp/jiritsu/../../etc/ld.so.preload'),)


def _requests(stock, resources, guards=()):
    files = {'appFw.so': ('usr/lib/appFw.so', stock.ap_bytes),
             'cpapp-b.bin': ('cp/cpapp-b.bin', stock.cp_bytes)}
    if resources:
        files.update({n: ('usr/share/app/' + n, customcontracts.MAX_RESOURCE)
                      for n in customcontracts.RESOURCE_FILES})
    requests = {
        'hasp': _Request(0x10, struct.pack('<HHB', 0, 0x1f, 0), 88, 88, response=1),
        'ram': _Request(0x40, struct.pack('<HHB', 0x603, 5, 1), bk4.MAX_SNAPSHOT, None),
        'saved': _Request(0x40, struct.pack('<HHB', 0x603, 5, 0), bk4.MAX_SNAPSHOT, None),
    }
    for name, (path, limit) in files.items():
        requests['select:' + name] = _Request(0x40, struct.pack('<HH', 0x1001, 15)
            + b'\0/tmp/jiritsu/../../' + path.encode('ascii') + b'\0', 0, 0, True)
        requests['read:' + name] = _Request(0x40, struct.pack('<HH', 0x1001, 17)
            + b'\0\xff\0', limit, limit if name in ('appFw.so', 'cpapp-b.bin') else None, True)
    for name, path in guards:
        requests['select:' + name] = _Request(0x40, struct.pack('<HH', 0x1001, 15)
            + b'\0' + path.encode('ascii') + b'\0', 0, 0, True)
        requests['read:' + name] = _Request(0x40, struct.pack('<HH', 0x1001, 17)
            + b'\0\xff\0', 4096, None, True, guard=True)
    return MappingProxyType(requests)


class OfflineChannel:
    """Generate fixed request bytes and consume explicit read results.

The legacy class name is retained. The caller feeds ONE result per Read;
empty transfers carry no bytes and never renew the shared deadline or budget.
No callback can open a device here. begin() records a possibly sent request;
abort() after begin poisons the channel, including a partial outbound write.
"""
    def __init__(self, archive, *, resources=False, guards=False, budget=None):
        if type(resources) is not bool or type(guards) is not bool:
            raise ValueError('Explicit resource/guard selection required')
        _, sources = workercontracts.load_sources(archive, inventory=workercontracts.ROOT / 'research/upstream-backup-loader.lock.json')
        policy = programidentity._load_policy(archive)
        stock, = (s for s in policy.sources if s.kind == 'stock')
        paths = _guard_paths(sources) if guards else ()
        self.guard_names = tuple(name for name, _ in paths)
        self.requests = _requests(stock, resources, paths)
        payload = 88 + 2 * (stock.ap_bytes + stock.cp_bytes) + 4 * bk4.MAX_SNAPSHOT + 2 * len(paths) * 4096
        if resources:
            payload += 136 * customcontracts.MAX_RESOURCE
        self.budget = Budget(payload) if budget is None else budget
        if type(self.budget) is not Budget:
            raise TypeError('Host Budget required')
        # One budget/deadline across all replies. Include requests, status words
        # and frame headers. Empty transfers count against MAX_FEEDS and time,
        # not bytes; no extra read is scheduled after a completed response.
        cap = self.budget.limit
        self.wire_limit = (cap + MAX_REQUESTS * (MAX_REQUEST_BYTES + HEADER.size + 4)
            + ((cap + FRAME - 1) // FRAME) * HEADER.size)
        self.wire_bytes = self.feeds = self.calls = 0
        self.sequence, self.selected = 1, None
        self.active = self.unknown = self.blocked = self.exit_claimed = False
        self.result = None

    def _check(self, maximum=0):
        self.budget.check()
        if self.wire_bytes + maximum > self.wire_limit:
            raise ValueError('Whole-session wire budget exceeded')

    def _poison(self):
        self.active = False
        self.unknown = self.blocked = True
        self.result = None

    def begin(self, name, sink=None):
        if self.active or self.blocked or self.exit_claimed:
            raise RuntimeError('Channel cannot issue another request')
        try:
            self._check()
            if type(name) is not str or name not in self.requests:
                raise ValueError('Unknown fixed read operation')
            spec = self.requests[name]
            if name.startswith('read:') and self.selected != name[5:]:
                raise ValueError('Matching successful fixed select required')
            if spec.limit:
                if (type(sink) is not Sink or sink.closed or sink.size
                        or sink.limit != spec.limit or sink.exact != spec.exact
                        or sink.budget is not self.budget
                        or spec.guard and sink.store is not None):
                    raise ValueError('Fresh correctly bounded shared-budget Sink required')
            elif sink is not None:
                raise ValueError('Select response has no payload sink')
            if self.calls >= MAX_REQUESTS or self.sequence > 0xffff:
                raise ValueError('Request/sequence budget exhausted; no wrap')
            packet = HEADER.pack(len(spec.data), spec.pfunc, self.sequence, 0, 0, 0, 0) + spec.data
            if len(packet) > MAX_REQUEST_BYTES:
                raise ValueError('Fixed request exceeds wire allowance')
            self._check(len(packet))
        except BaseException:
            self.blocked = True
            raise
        self.wire_bytes += len(packet)
        self.calls += 1
        self.active = True
        self.name, self.spec, self.sink = name, spec, sink
        self.phase, self.need = 'header', HEADER.size
        self.total = self.frames = 0
        self.prefix = bytearray()
        self.result = None
        return packet

    def next_read(self):
        if not self.active:
            raise RuntimeError('No active response')
        try:
            if self.feeds >= MAX_FEEDS:
                raise ValueError('Read-result budget exhausted')
            self._check(self.need)
            left = int((self.budget.deadline - self.budget.clock()) * 1000)
            if left <= 0:
                raise TimeoutError('Protocol deadline expired')
            return Read(self.phase, self.need, left)
        except BaseException:
            self._poison()
            raise

    def feed(self, raw):
        """Consume one bounded read result. Nonempty headers remain exact.

        Data may fragment. A zero-length transfer leaves the current phase and
        remaining length unchanged. Nonempty data is never treated as drain.
        Any optional final empty transfer is left for the next normal read.
        """
        if not self.active:
            self._poison()
            raise RuntimeError('Unsolicited read result outside an active response')
        expected = self.next_read()
        try:
            if type(raw) is not bytes or len(raw) > expected.maximum:
                raise ValueError('Invalid or excessive read result')
            self.feeds += 1
            self.wire_bytes += len(raw)
            if not raw:
                return None
            if self.phase == 'header':
                if len(raw) != HEADER.size:
                    raise ValueError('Short Senser header')
                size, pfunc, seq, version, micon, offset, response = HEADER.unpack(raw)
                # Echo/zero-field restrictions are defensive design decisions,
                # NOT established reply invariants of a physical ILCE-7CM2.
                if (seq != self.sequence or pfunc != self.spec.pfunc
                        or version or micon or offset):
                    raise ValueError('Unreviewed header profile or wrong sequence')
                maximum = self.spec.limit + (4 if self.spec.status_prefix else 0)
                self.frames += 1
                amount = min(size, FRAME)
                if (size > maximum or self.total + amount > maximum
                        or self.frames > max(1, (maximum + FRAME - 1) // FRAME)):
                    raise ValueError('Declared or cumulative response exceeds fixed bound')
                prefix_left = 4 - len(self.prefix) if self.spec.status_prefix else 0
                if self.budget.used + max(0, amount - prefix_left) > self.budget.limit:
                    raise ValueError('Declared frame exceeds remaining payload budget')
                # Do not infer monotonic remaining-size fields: fixed PMCA only
                # uses min(size, FRAME) and size > FRAME as continuation.
                self.total += amount
                self.frame_left, self.more, self.response = amount, size > FRAME, response
                if amount:
                    self._data_chunk()
                else:
                    return self._frame_end()
            elif self.phase == 'data':
                payload = raw
                if self.spec.status_prefix and len(self.prefix) < 4:
                    n = min(4 - len(self.prefix), len(raw))
                    self.prefix.extend(raw[:n]); payload = raw[n:]
                if payload:
                    self.sink.write(payload)
                self.need -= len(raw)
                self.frame_left -= len(raw)
                if not self.need:
                    if self.frame_left:
                        self._data_chunk()
                    else:
                        return self._frame_end()
            return None
        except BaseException:
            # _frame_end marks framing consumed before status/content/fsync
            # checks. Failures before that boundary leave protocol unknown.
            if self.active:
                self._poison()
            else:
                self.blocked = True
            raise

    def _data_chunk(self):
        self.phase = 'data'
        self.need = min(self.frame_left, BLOCK)

    def _frame_end(self):
        if self.more:
            self.phase, self.need = 'header', HEADER.size
            return None
        self.active = False
        self.sequence += 1
        self.budget.check()
        if self.response != self.spec.response:
            raise CompleteResponseError('Complete command returned unsuccessful response')
        if self.spec.status_prefix:
            if len(self.prefix) != 4:
                raise CompleteResponseError('Complete Jiritsu status rejected')
            status = struct.unpack('<I', self.prefix)[0]
            if status and not (self.spec.guard and status == 0x10000006 and self.total == 4):
                raise CompleteResponseError('Complete Jiritsu status rejected')
        size = self.total - len(self.prefix)
        if (self.spec.exact is not None and size != self.spec.exact
                or self.spec.limit and not size and not self.spec.guard):
            raise CompleteResponseError('Complete response has incorrect payload length')
        info = self.sink.finish() if self.sink is not None and size else None
        if self.spec.guard and not size:
            self.sink.close()
        if self.name.startswith('select:'):
            self.selected = self.name[7:]
        elif self.name.startswith('read:'):
            self.selected = None
        # Retain the legacy passive-parser receipt fields. This parser cannot
        # attest the source of fed bytes; the outer capture owner reports I/O.
        self.result = {'operation': self.name, 'payload': info, 'frames': self.frames,
            'simulation_only': True, 'physical_protocol_verified': False,
            'response_profile_verified': False, 'camera_operations_performed': False}
        if self.spec.guard:
            self.result['guard_absent'] = status == 0x10000006
            if not self.result['guard_absent']:
                self.blocked = True  # Existing state, including an empty file, stops new reads.
        return self.result

    def abort(self):
        """Caller observed interruption/timeout/partial outbound write."""
        if self.active:
            self._poison()

    def claim_exit(self):
        """Consume one local exit allowance; sends NO stop/auth/USB command."""
        if self.active or self.unknown or self.exit_claimed:
            raise RuntimeError('No known healthy exit allowance')
        self._check()
        self.exit_claimed = self.blocked = True
