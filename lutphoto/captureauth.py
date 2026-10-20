"""Strict raw authentication/error boundary, exercised with synthetic drivers.

Protocol and faulty SHA-1 length behavior derive from pinned QAQLeonard's
ma1co Sony-PMCA-RE, whose crypto source credits ajalt/python-sha1.
Copyright (c) 2015 ma1co; retained license: docs/Sony-PMCA-RE-MIT.txt.
No USB imports, enumeration, device entry point or automatic cleanup/retry.
"""
from dataclasses import dataclass, field
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile

from . import customcontracts as c, workercontracts as w
from .capturesession import _normal, _location
from .capturestore import Budget, Store

AUTH = struct.Struct('>HH512s')
START = (0x43, 1, 0x37ff, 0xd7aa)
STOP = (0x43, 1, 0xc800, 0x2855)
PIN = w.ROOT / 'research/upstream-auth.lock.json'


@dataclass(frozen=True)
class _Keys:
    sha1: tuple = field(repr=False)
    sha256: tuple = field(repr=False)


def _sources(archive):
    baseline, _ = w.load_sources(archive, inventory=w.ROOT / 'research/upstream-backup-loader.lock.json')
    pin = json.loads(c.bounded_read(PIN, 32768))
    if (pin['schema'] != 'a7c2-auth-source-audit/1' or pin['camera_integration_enabled'] is not False
            or any(pin[k] != baseline[k] for k in ('commit', 'archive_bytes', 'archive_sha256', 'baseline_lock_sha256'))
            or len(pin['files']) != 9):
        raise ValueError('Authentication source pin differs')
    raw = c.bounded_read(archive, pin['archive_bytes'])
    if len(raw) != pin['archive_bytes'] or hashlib.sha256(raw).hexdigest() != pin['archive_sha256']:
        raise ValueError('Authentication archive differs')
    sources = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        for name, spec in pin['files'].items():
            if name.startswith('/') or '..' in Path(name).parts or spec['bytes'] > 100000:
                raise ValueError('Invalid authentication source inventory')
            value = package.read('a7c2-tools-2.1/' + name)
            blob = hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest()
            if len(value) != spec['bytes'] or hashlib.sha256(value).hexdigest() != spec['sha256'] or blob != spec['git_blob_sha1']:
                raise ValueError('Authentication source member differs')
            sources[name] = value
    return pin, sources


def _keys(archive):
    pin, sources = _sources(archive)
    raw = sources['src/fl23/vendor/pmca/usb/constants.py']
    values = tuple(w.literal(raw, name) for name in ('senserKeysSha1', 'senserKeysSha256'))
    if any(type(v) is not list or len(v) != 3 or any(type(k) is not bytes or len(k) != 512 for k in v) for v in values):
        raise ValueError('Fixed authentication key layout differs')
    return pin, _Keys(*(tuple(v) for v in values))


def _faulty_sha1(raw):
    """SHA-1 compression with Sony's low-five-bit MESSAGE BYTE length field.

    No archive code executes here. The message still uses its full length for
    block padding, while the appended bit count uses len(raw) & 31.
    """
    if type(raw) is not bytes or len(raw) > 1024:
        raise ValueError('Bounded hash input required')
    data = raw + b'\x80'
    data += bytes((56 - len(data)) % 64) + struct.pack('>Q', (len(raw) & 31) * 8)
    state = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0]
    def rotate(value, bits): return ((value << bits) | (value >> (32 - bits))) & 0xffffffff
    for at in range(0, len(data), 64):
        words = list(struct.unpack_from('>16I', data, at))
        for index in range(16, 80): words.append(rotate(words[index-3] ^ words[index-8] ^ words[index-14] ^ words[index-16], 1))
        a, b, cc, d, e = state
        for index, word in enumerate(words):
            if index < 20: f, k = (b & cc) | (~b & d), 0x5a827999
            elif index < 40: f, k = b ^ cc ^ d, 0x6ed9eba1
            elif index < 60: f, k = (b & cc) | (b & d) | (cc & d), 0x8f1bbcdc
            else: f, k = b ^ cc ^ d, 0xca62c1d6
            a, b, cc, d, e = (rotate(a, 5) + f + e + k + word) & 0xffffffff, a, rotate(b, 30), cc, d
        state = [(left + right) & 0xffffffff for left, right in zip(state, (a, b, cc, d, e))]
    return struct.pack('>5I', *state)


def _proof(keys, pid, index, algorithm, challenge):
    if (type(challenge) is not bytes or len(challenge) != 512 or type(index) is not int or not 0 <= index < 3
            or algorithm not in (2, 8) or pid not in (0x0e8a, 0x0336)):
        raise ValueError('Unsupported authentication challenge')
    message = challenge[:4] if pid == 0x0e8a else challenge + (keys.sha1 if algorithm == 2 else keys.sha256)[index]
    return b'\x01' + (_faulty_sha1(message) if algorithm == 2 else hashlib.sha256(message).digest())


class SyntheticDriver:
    """Preloaded raw results/exceptions and optional independent write oracle.

    Never wraps a device or accepts callbacks. Raw challenges/proofs remain
    private memory only; do not serialize this object or its written packets.
    """
    def __init__(self, pid, transfers, *, expected_writes=None):
        if (type(pid) is not int or pid not in (0x0e8a, 0x0336) or type(transfers) is not list
                or len(transfers) > 32 or any(type(v) is not tuple or len(v) != 2 or v[0] not in ('control', 'write', 'read') for v in transfers)):
            raise ValueError('Bounded synthetic transfer tape required')
        self.pid, self.transfers = pid, list(transfers)
        self.expected = None if expected_writes is None else tuple(expected_writes)
        self.used, self.trace, self.written = 0, [], []

    def _take(self, kind, timeout):
        if type(timeout) is not int or not 1 <= timeout <= 5000:
            raise ValueError('Bounded remaining timeout required')
        self.trace.append((kind, timeout))
        if self.used >= len(self.transfers) or self.transfers[self.used][0] != kind:
            raise RuntimeError('Synthetic raw transfer order differs')
        value = self.transfers[self.used][1]; self.used += 1
        if isinstance(value, BaseException): raise value
        return value

    def control_out(self, request_type, request, value, index, raw, timeout_ms):
        if (request_type, request, value, index) not in (START, STOP) or raw != b'':
            raise ValueError('Only fixed zero-payload start/stop control requests allowed')
        return self._take('control', timeout_ms)

    def write(self, raw, timeout_ms):
        if type(raw) is not bytes or len(raw) != AUTH.size:
            raise ValueError('Fixed authentication packet required')
        if self.expected is not None and (len(self.written) >= len(self.expected) or self.expected[len(self.written)] != raw):
            raise ValueError('Synthetic proof/request differs from independent oracle')
        self.written.append(raw)
        return self._take('write', timeout_ms)

    def read(self, maximum, timeout_ms):
        if maximum != AUTH.size: raise ValueError('Fixed authentication read size required')
        return self._take('read', timeout_ms)


class _RawAuth:
    """No exception swallowing, length-discarding wrapper or automatic retry."""
    def __init__(self, driver, keys, budget):
        self.driver, self.keys, self.budget = driver, keys, budget
        self.unknown = False

    def _io(self, kind, raw=None, *, stop=False):
        if self.unknown: raise RuntimeError('Unknown authentication outcome; no further I/O')
        maximum = AUTH.size if kind in ('read', 'write') else 0
        self.budget.check()
        if self.budget.used + maximum > self.budget.limit: raise ValueError('Authentication byte budget exceeded')
        timeout = min(5000, int((self.budget.deadline - self.budget.clock()) * 1000))
        if timeout <= 0: raise TimeoutError('Authentication deadline expired')
        try:
            if kind == 'control':
                result = self.driver.control_out(*(STOP if stop else START), b'', timeout)
                if type(result) is not int or result != 0: raise ValueError('Control transfer did not return explicit zero length')
            elif kind == 'write':
                result = self.driver.write(raw, timeout)
                if type(result) is not int or result != AUTH.size: raise ValueError('Authentication packet send length differs')
                self.budget.accept(AUTH.size)
            else:
                result = self.driver.read(AUTH.size, timeout)
                if type(result) is not bytes or len(result) != AUTH.size: raise ValueError('Authentication response must be one complete packet')
                self.budget.accept(AUTH.size)
            self.budget.check()
            return result
        except BaseException:
            self.unknown = True
            raise

    def control(self, *, stop=False): self._io('control', stop=stop)

    def _exchange(self, command, data=b''):
        if command not in (1, 3, 5) or type(data) is not bytes or len(data) > 512:
            raise ValueError('Fixed authentication command required')
        self._io('write', AUTH.pack(~command & 0xffff, 0, data))
        packet = self._io('read')
        cmd, salt, payload = AUTH.unpack(packet)
        return (~cmd & 0xffff) - salt, payload

    def authenticate(self):
        try:
            for index in range(3):
                algorithm, challenge = self._exchange(1)
                if algorithm not in (2, 8): raise ValueError('Unsupported authentication algorithm/status')
                status, _ = self._exchange(3, _proof(self.keys, self.driver.pid, index, algorithm, challenge))
                if status != 4: raise ValueError('Authentication proof response rejected')
            status, data = self._exchange(5)
            if status != 6 or data[0] != 1: raise ValueError('Authentication final response rejected')
        except BaseException:
            self.unknown = True
            raise


class OfflineAuthFlow:
    """Two raw protocol stages on EXACT synthetic drivers and durable host log.

    Not installed into capturesession; normal/service observations are supplied
    synthetic facts, not freshly queried devices. No raw driver escapes here.
    """
    def __init__(self, archive, store, initial, *, budget=None):
        if type(store) is not Store: raise TypeError('Private host Store required')
        self.pin, self.keys = _keys(archive)
        self.initial = _normal(initial)
        self.store = store
        self.budget = Budget(32768, seconds=120) if budget is None else budget
        if type(self.budget) is not Budget: raise TypeError('Shared host Budget required')
        self.phase, self.unknown, self.blocked, self.exit_attempted = 'NEW', False, False, False
        self.normal = self.service = None

    def _action(self, name, action, phase):
        if self.unknown or self.blocked: raise RuntimeError('Stopped synthetic flow; no subsequent operation')
        try:
            self.budget.check()
            self.store.event('INTENT', operation=name)
        except BaseException:
            self.blocked = True
            raise
        try: action()
        except BaseException:
            self.unknown = self.blocked = True; self.phase = 'NEEDS_REVIEW'
            raise
        self.phase = phase  # Known result before ACK, so persistence failure never replays it.
        try: self.store.event('ACK', operation=name)
        except BaseException:
            self.blocked = True
            raise

    def normal_auth(self, driver):
        if self.phase != 'NEW' or self.unknown or self.blocked: raise RuntimeError('Normal authentication cannot be replayed')
        if type(driver) is not SyntheticDriver or driver.pid != 0x0e8a:
            raise TypeError('Exact normal synthetic driver required')
        self.normal = _RawAuth(driver, self.keys, self.budget)
        self._action('auth-normal-start', self.normal.control, 'NORMAL_CONTROL_RETURNED')
        self._action('auth-normal-verify', self.normal.authenticate, 'WAIT_SERVICE')

    def service_auth(self, observation, driver):
        if self.phase != 'WAIT_SERVICE' or self.unknown or self.blocked: raise RuntimeError('No service transition allowance')
        try:
            if (type(observation) is not dict or set(observation) != {'bus', 'ports', 'pid', 'normal_count', 'service_count'}
                    or type(observation['pid']) is not int or observation['pid'] != 0x0336
                    or type(observation['normal_count']) is not int or observation['normal_count'] != 0
                    or type(observation['service_count']) is not int or observation['service_count'] != 1
                    or _location(observation) != (self.initial.bus, self.initial.ports)
                    or type(driver) is not SyntheticDriver or driver.pid != 0x0336):
                raise ValueError('Service driver/unique same-port observation required')
        except BaseException:
            self.unknown = self.blocked = True; self.phase = 'NEEDS_REVIEW'
            raise
        self.service = _RawAuth(driver, self.keys, self.budget)
        self._action('auth-service-start', self.service.control, 'SERVICE_CONTROL_RETURNED')
        self._action('auth-service-verify', self.service.authenticate, 'SERVICE_AUTHENTICATED')

    def stop(self):
        if self.phase != 'SERVICE_AUTHENTICATED' or self.unknown or self.blocked or self.exit_attempted:
            raise RuntimeError('No healthy single service exit allowance')
        def request():
            self.exit_attempted = True
            self.service.control(stop=True)
        self._action('service-stop', request, 'STOP_CONTROL_RETURNED')

    def observe_return(self, value):
        if self.phase != 'STOP_CONTROL_RETURNED' or self.unknown or self.blocked:
            raise RuntimeError('No normal return observation allowance')
        def validate():
            if _normal(value) != self.initial: raise ValueError('Normal same-source identity/physical port differs')
        self._action('normal-after', validate, 'SYNTHETIC_RETURN_MATCHED')

    def summary(self):
        return {'schema': 'a7c2-synthetic-raw-authentication/1', 'private_report': True,
            'status': ('NEEDS_REVIEW' if self.blocked or self.unknown else
                       'SIMULATED_AUTH_COMPLETE' if self.phase == 'SYNTHETIC_RETURN_MATCHED' else 'IN_PROGRESS'),
            'simulation_only': True, 'phase': self.phase, 'outcome_unknown': self.unknown, 'blocked': self.blocked,
            'accepted_auth_bytes': self.budget.used, 'exit_attempted': self.exit_attempted,
            'camera_operations_performed': False, 'actual_authentication_verified': False,
            'actual_source_identity_verified': False, 'physical_protocol_verified': False,
            'fresh_normal_observation_verified': False, 'global_camera_lock_acquired': False,
            'restore_verified': False, 'write_plan_enabled': False, 'resume_allowed': False,
            'commit': self.pin['commit'], 'archive_sha256': self.pin['archive_sha256']}
