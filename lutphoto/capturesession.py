"""Synthetic session coordination over bounded protocol bytes, never USB.

Lifecycle/paths derive from pinned QAQLeonard/ma1co and the retained Mac
adapter. All identity/auth/port/global-lock observations here are fictitious.
See ACKNOWLEDGEMENTS.md; this module cannot accept a real transport backend.
"""
from dataclasses import dataclass
import hashlib
import re
import struct

from . import bk4, customcontracts as c, programidentity
from .capturehost import Pattern, _scope
from .captureprotocol import OfflineChannel
from .capturestore import Sink, Store, encoded

LEGACY_LOCK = '/var/run/a7c2-fl23-macos.lock'  # Only modeled; never opened.
EVENTS_LIMIT = 2048


@dataclass(frozen=True)
class _Identity:
    digest: str
    bus: int
    ports: tuple


def _location(value):
    if (type(value.get('bus')) is not int or not 0 <= value['bus'] <= 255
            or type(value.get('ports')) is not list or not 1 <= len(value['ports']) <= 8
            or any(type(n) is not int or not 1 <= n <= 255 for n in value['ports'])):
        raise ValueError('Explicit bus and physical port observation required')
    return value['bus'], tuple(value['ports'])


def _normal(value):
    if (type(value) is not dict or set(value) != {'manufacturer', 'model', 'serial_source',
            'serial_sha256', 'bus', 'ports', 'pid', 'normal_count', 'service_count'}
            or value['manufacturer'] != 'Sony' or value['model'] != 'ILCE-7CM2'
            or value['serial_source'] != 'sony-get-camera-info'
            or type(value['serial_sha256']) is not str
            or not re.fullmatch('[0-9a-f]{64}', value['serial_sha256'])
            or type(value['pid']) is not int or value['pid'] != 0x0e8a
            or type(value['normal_count']) is not int or value['normal_count'] != 1
            or type(value['service_count']) is not int or value['service_count'] != 0):
        raise ValueError('One normal Sony camera with same-source protocol identity required')
    return _Identity(value['serial_sha256'], *_location(value))


class SyntheticPeer:
    """Own in-memory payloads, fake auth/locks and framed replies, no callbacks."""
    def __init__(self, files, *, guards=None, changes=None, initial=None, returned=None,
                 service=None, fault=None, version='2.01', battery=75):
        for values in (files, guards or {}, changes or {}):
            if type(values) is not dict or any(type(v) not in (bytes, Pattern) and v is not None for v in values.values()):
                raise TypeError('Own synthetic bytes/patterns/absence required')
        self.files, self.guards, self.changes = dict(files), dict(guards or {}), dict(changes or {})
        normal = {'manufacturer': 'Sony', 'model': 'ILCE-7CM2', 'serial_source': 'sony-get-camera-info',
                  'serial_sha256': '11' * 32, 'bus': 1, 'ports': [1, 2], 'pid': 0x0e8a,
                  'normal_count': 1, 'service_count': 0}
        self.initial = normal if initial is None else initial
        self.returned = self.initial if returned is None else returned
        self.service = ({'bus': 1, 'ports': [1, 2], 'pid': 0x0336, 'normal_count': 0, 'service_count': 1}
                        if service is None else service)
        self.fault, self.version, self.battery = fault, version, battery
        self.trace, self.counts = [], {}

    def step(self, name):
        self.trace.append(name)
        if self.fault == name:
            raise TimeoutError('Self-generated session interruption')
        return True

    def normal(self, returning=False):
        self.step('normal-after' if returning else 'normal-before')
        value = self.returned if returning else self.initial
        return {**value, 'ports': list(value['ports'])} if type(value) is dict and type(value.get('ports')) is list else value

    def observe_service(self):
        self.step('service-observation')
        value = self.service
        return {**value, 'ports': list(value['ports'])} if type(value) is dict and type(value.get('ports')) is list else value

    def reply(self, name, packet):
        self.step('wire:' + name)
        _, pfunc, sequence, *_ = struct.unpack('<IHH4B', packet[:12])
        self.counts[name] = self.counts.get(name, 0) + 1
        prefix, response = b'', 0
        if name.startswith('select:'):
            prefix, raw = bytes(4), b''
        elif name.startswith('read:guard:'):
            key = name[5:]
            raw = self.changes.get(key, self.guards.get(key)) if self.counts[name] > 1 else self.guards.get(key)
            prefix = struct.pack('<I', 0x10000006 if raw is None else 0)
            raw = b'' if raw is None else raw
        elif name.startswith('read:'):
            key = name[5:]
            if key in c.RESOURCE_FILES: key = 'resources/' + key
            raw = self.changes.get(key, self.files[key]) if self.counts[name] > 1 else self.files[key]
            prefix = bytes(4)
        elif name == 'hasp':
            raw, response = b'H' * 88, 1
        else:
            raw = self.changes.get(name, self.files[name]) if self.counts[name] > 1 else self.files[name]
        size = len(prefix) + (raw.size if type(raw) is Pattern else len(raw))
        for start in range(0, max(size, 1), 0x100000):
            yield struct.pack('<IHH4B', size - start, pfunc, sequence, 0, 0, 0, response)
            if self.fault == 'partial:' + name:
                raise ConnectionError('Self-generated half response')
            frame = min(size - start, 0x100000)
            for offset in range(start, start + frame, 0x8000):
                length = min(start + frame - offset, 0x8000)
                head = prefix[offset:offset + length] if offset < len(prefix) else b''
                at = max(0, offset - len(prefix)); count = length - len(head)
                block = bytes([raw.byte]) * count if type(raw) is Pattern else raw[at:at + count]
                yield head + block
                if length % 512 == 0:
                    yield b''  # Explicit fake drain result, not file payload.


class _Run:
    def __init__(self, store, peer, channel, policy):
        self.store, self.peer, self.channel, self.policy = store, peer, channel, policy
        self.stock, = (s for s in policy.sources if s.kind == 'stock')
        self.initial = None
        self.files, self.scopes = {}, {}
        self.unknown = self.authenticated = self.transition = self.stop_ack = self.exit_attempted = False
        self.normal_open = self.service_open = self.returned = self.programs_matched = False
        self.stage = 'C0'

    def event(self, event, **details):
        self.store.event(event, **details)

    def call(self, name, action, *, wire=False):
        if self.unknown:
            raise RuntimeError('Unknown synthetic session; no further commands')
        self.channel.budget.check()
        self.event('INTENT', operation=name)
        if name == 'auth-normal-start': self.transition = True
        try:
            value = action()
            if name.startswith('auth-') or name == 'service-stop':
                if value is not True: raise ValueError('Synthetic acknowledgement required')
        except BaseException:
            if wire:
                if self.channel.active: self.channel.abort()
                self.unknown = self.channel.unknown
            else:
                self.unknown = True
            raise
        # Record known protocol state before ACK persistence, so host journal
        # failure cannot accidentally authorize a second auth/stop operation.
        if name == 'auth-service-verify': self.authenticated = True
        if name == 'service-stop': self.stop_ack = True; self.authenticated = False
        self.event('ACK', operation=name)
        return value

    def wire(self, name, sink=None):
        def exchange():
            packet = self.channel.begin(name, sink)
            for raw in self.peer.reply(name, packet):
                self.channel.feed(raw)
            if self.channel.active:
                self.channel.abort()
                raise ValueError('Incomplete synthetic response')
            return self.channel.result
        return self.call(name, exchange, wire=True)

    def guards(self):
        for name in self.channel.guard_names:
            self.wire('select:' + name)
            sink = Sink(4096, budget=self.channel.budget)
            try:
                result = self.wire('read:' + name, sink)
                if result['guard_absent'] is not True:
                    raise ValueError('Existing temporary state; preserve without cleanup')
            finally:
                sink.close()
        self.event('GUARD_ABSENCE_MODELED', count=len(self.channel.guard_names))

    def receive(self, name, relative=None, expected=None):
        operation = name if name in ('ram', 'saved', 'hasp') else 'read:' + name
        if operation.startswith('read:'): self.wire('select:' + name)
        spec = self.channel.requests[operation]
        sink = Sink(spec.limit, exact=spec.exact, budget=self.channel.budget,
                    store=self.store if relative is not None else None, relative=relative)
        try:
            info = self.wire(operation, sink)['payload']
        finally:
            sink.close()
        if relative is not None:
            self.files[relative] = info
            self.event('HOST_FILE_VERIFIED', file=relative, **info)
        if expected is not None and info != expected:
            raise ValueError('Complete synthetic content differs from fixed expectation')
        return info

    def snapshot(self, name, relative, *, end=False):
        info = self.receive(name, relative)
        scope = _scope(self.store.read(relative, info))
        if end and scope != self.scopes[name]:
            raise ValueError('Scoped snapshot changed')
        self.scopes[name] = scope
        self.event('SNAPSHOT_FORMAT_CHECKED', file=relative)

    def exit(self):
        if not self.authenticated or self.unknown or self.exit_attempted:
            return
        def stop():
            self.exit_attempted = True
            self.channel.claim_exit()
            return self.peer.step('service-stop')
        self.call('service-stop', stop)
        self.service_open = False
        self.peer.step('close-service')
        value = self.call('normal-after', lambda: self.peer.normal(True))
        self.normal_open = True
        if _normal(value) != self.initial:
            raise ValueError('Normal same-source identity or physical port changed')
        self.returned = True
        self.event('NORMAL_SAME_SOURCE_MATCH_MODELED')

    def preflight(self, resources):
        maximum = (self.stock.ap_bytes + self.stock.cp_bytes + 4 * bk4.MAX_SNAPSHOT
                   + (68 * c.MAX_RESOURCE if resources else 0) + EVENTS_LIMIT * 16384 + 131072)
        self.store.require_space(maximum)
        self.event('SYNTHETIC_LOCK_ORDER', global_lock_modeled=True, real_global_lock_acquired=False)

    def body(self, resources):
        self.preflight(resources)
        value = self.call('normal-before', self.peer.normal)
        self.normal_open = True
        self.initial = _normal(value)
        self.stage = 'C1'
        for name in ('auth-normal-start', 'auth-normal-verify'):
            self.call(name, lambda n=name: self.peer.step(n))
        self.normal_open = False
        self.peer.step('close-normal')
        service = self.call('service-observation', self.peer.observe_service)
        if (type(service) is not dict or set(service) != {'bus', 'ports', 'pid', 'normal_count', 'service_count'}
                or type(service['pid']) is not int or service['pid'] != 0x0336
                or type(service['normal_count']) is not int or service['normal_count'] != 0
                or type(service['service_count']) is not int or service['service_count'] != 1
                or _location(service) != (self.initial.bus, self.initial.ports)):
            raise ValueError('Service transition lacks the same unique physical port')
        self.service_open = True
        for name in ('auth-service-start', 'auth-service-verify'):
            self.call(name, lambda n=name: self.peer.step(n))
        self.stage = 'C2'
        self.materials(resources)

    def materials(self, resources):
        self.receive('hasp')
        self.guards()
        for name, size, digest in (('appFw.so', self.stock.ap_bytes, self.stock.ap_sha),
                                   ('cpapp-b.bin', self.stock.cp_bytes, self.stock.cp_sha)):
            self.receive(name, 'source/' + name, {'bytes': size, 'sha256': digest})
        self.programs_matched = True; self.stage = 'C3'
        self.snapshot('ram', 'source/settings-ram.bin')
        self.snapshot('saved', 'source/settings-saved.bin')
        count = None
        if resources:
            for name in c.RESOURCE_FILES:
                relative = 'resources/' + name
                info = self.receive(name, relative)
                layout = c.decode_resource(self.store.read(relative, info))['count']
                if count is not None and layout != count: raise ValueError('Mixed synthetic resource layouts')
                count = layout
        for name in ('appFw.so', 'cpapp-b.bin'):
            self.receive(name, expected=self.files['source/' + name])
        if resources:
            for name in c.RESOURCE_FILES: self.receive(name, expected=self.files['resources/' + name])
        self.snapshot('ram', 'evidence/settings-ram-end.bin', end=True)
        self.snapshot('saved', 'evidence/settings-saved-end.bin', end=True)
        self.guards()
        self.stage = 'C4'
        self.exit()
        self.stage = 'C5'

    def report(self, complete, reason=None):
        return {'schema': 'a7c2-synthetic-session-coordination/1', 'private_report': True,
            'phase': 'SIMULATED_SESSION_COMPLETE' if complete else 'NEEDS_REVIEW', 'reason_type': reason,
            'simulation_only': True, 'camera_operations_performed': False, 'global_camera_lock_acquired': False,
            'physical_protocol_verified': False, 'response_profile_verified': False,
            'actual_source_identity_verified': False, 'body_binding_verified': False,
            'chip_roles_verified': False, 'outer_wrapper_verified': False, 'atomic_capture_verified': False,
            'snapshot_freshness_verified': False, 'independent_media_verified': False,
            'native_execution_verified': False, 'restore_verified': False, 'write_plan_enabled': False,
            'last_stage': self.stage, 'simulated_outcome_unknown': self.unknown,
            'simulated_transition_started': self.transition, 'simulated_service_stop_ack': self.stop_ack,
            'simulated_normal_identity_matched': self.returned, 'program_content_matched_in_rehearsal': self.programs_matched,
            'files': self.files, 'accepted_payload_bytes': self.channel.budget.used,
            'accepted_wire_bytes': self.channel.wire_bytes, 'requests': self.channel.calls,
            'journal_records': self.store.seq, 'journal_head_sha256': self.store.head,
            'commit': self.policy.commit, 'archive_sha256': self.policy.archive_sha}


def rehearse(archive, directory, peer, *, resources=False):
    """New private output only, exact synthetic peer, no transport/lock injection."""
    if type(peer) is not SyntheticPeer or type(resources) is not bool:
        raise TypeError('Exact synthetic peer and explicit resource selection required')
    if (peer.version != '2.01' or type(peer.battery) is not int or not 50 <= peer.battery <= 100):
        raise ValueError('Synthetic preflight version/battery rejected')
    policy = programidentity._load_policy(archive)
    channel = OfflineChannel(archive, resources=resources, guards=True)
    store = run = None
    peer.step('global-lock-acquire')  # Model only; BEFORE Store takes its real job flock.
    try:
        store = Store(directory, events_limit=EVENTS_LIMIT)
        run = _Run(store, peer, channel, policy)
        try:
            run.body(resources)
            # Local handle release and all evidence publication remain inside
            # the modeled global lock and real host job lock.
            if run.normal_open:
                run.normal_open = False
                peer.step('close-normal')
            store.event('READY_FOR_REPORT')
            for name, info in {**run.files, **store.documents}.items(): store.verify(name, info)
            result = run.report(True)
            store.put('session-report.private.json', encoded(result))
            return result
        except BaseException as exc:
            if run.authenticated and not run.unknown and not run.exit_attempted:
                try: run.exit()
                except BaseException: pass
            result = run.report(False, type(exc).__name__)
            try:
                store.event('NEEDS_REVIEW', reason_type=type(exc).__name__, outcome_unknown=run.unknown)
                result = run.report(False, type(exc).__name__)
                store.put('session-report.private.json', encoded(result))
            except BaseException:
                pass
            return result
    finally:
        try:
            if run is not None:
                if run.service_open:
                    run.service_open = False
                    peer.step('close-service')
                if run.normal_open:
                    run.normal_open = False
                    peer.step('close-normal')
        finally:
            try:
                if store is not None: store.close()
            finally:
                peer.step('global-lock-release')
