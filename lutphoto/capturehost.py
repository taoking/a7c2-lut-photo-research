"""Synthetic host capture rehearsal only. No USB adapter or device command."""
import argparse
from dataclasses import dataclass
import hashlib
import json
import re
import struct
import sys

from . import bk4, customcontracts as c, programidentity as p
from .capturestore import Budget, CHUNK, Sink, Store, encoded


@dataclass(frozen=True)
class Pattern:
    byte: int
    size: int

    def chunks(self):
        if type(self.byte) is not int or not 0 <= self.byte <= 255 or type(self.size) is not int or self.size < 0:
            raise ValueError('Invalid synthetic pattern')
        for at in range(0, self.size, CHUNK):
            yield bytes([self.byte]) * min(CHUNK, self.size - at)


class SyntheticTape:
    """In-memory bytes/patterns and fixed fake observations, never callbacks/I/O."""
    def __init__(self, files, *, fault=None, changes=None, returned_identity=None):
        if type(files) is not dict or any(type(v) not in (bytes, Pattern) for v in files.values()):
            raise ValueError('Own bytes or synthetic patterns required')
        if changes is not None and (type(changes) is not dict or any(type(v) not in (bytes, Pattern) for v in changes.values())):
            raise ValueError('Own synthetic changes required')
        self.files, self.changes, self.fault = dict(files), dict(changes or {}), fault
        self.trace, self.counts = [], {}
        self.identity = {'model': 'ILCE-7CM2', 'serial_sha256': '11' * 32, 'port': [1, 2]}
        self.returned_identity = returned_identity

    def normal(self, returning=False):
        self.trace.append('normal-return' if returning else 'normal-initial')
        if returning and self.fault == 'return-unknown': raise TimeoutError('Synthetic return failure')
        return dict(self.returned_identity if returning and self.returned_identity is not None else self.identity)

    def service(self, stop=False):
        self.trace.append('service-stop' if stop else 'service-start')
        if self.fault == ('stop-unknown' if stop else 'start-unknown'):
            raise TimeoutError('Synthetic service failure')
        return True

    def read(self, name, sink):
        self.trace.append('read:' + name)
        self.counts[name] = self.counts.get(name, 0) + 1
        raw = self.changes[name] if self.counts[name] > 1 and name in self.changes else self.files[name]
        chunks = raw.chunks() if type(raw) is Pattern else (raw[at:at + CHUNK] for at in range(0, len(raw), CHUNK))
        for chunk in chunks:
            sink.write(chunk)
            if self.fault == 'read:' + name: raise ConnectionError('Synthetic interrupted packet')


def boundary():
    return {'schema': 'a7c2-synthetic-host-capture-report/1', 'private_report': True,
            'simulation_only': True, 'camera_operations_enabled': False, 'camera_operations_performed': False,
            'actual_source_identity_verified': False, 'body_binding_verified': False,
            'chip_roles_verified': False, 'outer_wrapper_verified': False,
            'container_complete_backup_verified': False, 'snapshot_freshness_verified': False,
            'atomic_capture_verified': False, 'independent_media_verified': False,
            'global_camera_lock_acquired': False, 'native_execution_verified': False,
            'restore_verified': False, 'physical_validation_verified': False,
            'write_plan_enabled': False, 'automatic_retry_allowed': False}


def _identity(value):
    if (type(value) is not dict or set(value) != {'model', 'serial_sha256', 'port'}
            or value['model'] != 'ILCE-7CM2' or type(value['serial_sha256']) is not str
            or not re.fullmatch('[0-9a-f]{64}', value['serial_sha256'])
            or type(value['port']) is not list or not 1 <= len(value['port']) <= 8
            or any(type(v) is not int or not 1 <= v <= 255 for v in value['port'])):
        raise ValueError('Invalid synthetic identity observation')
    return {**value, 'port': list(value['port'])}


def _scope(raw):
    """Compare positional scoped observations; never assign AP/CP roles."""
    result = []
    for image in bk4.parse_snapshot(raw):
        digest = hashlib.sha256()
        for key, value in sorted(image.records.items()):
            if key >> 16 != 0x02cf and key not in c.devicesettings.PROTECTED:
                continue
            reset = value.reset_data
            digest.update(struct.pack('<IHHII', key, value.attr, value.max_size, len(value.data),
                                      0xffffffff if reset is None else len(reset)))
            if key != c.devicesettings.SAVED_TELEMETRY: digest.update(value.data)
            if reset is not None: digest.update(reset)
        result.append(digest.hexdigest())
    return result


class _Run:
    def __init__(self, store, tape, source, policy, resources):
        self.store, self.tape, self.source, self.policy = store, tape, source, policy
        self.resources, self.files, self.scopes, self.resource_count = resources, {}, {}, None
        self.active = self.unknown = self.programs_matched = self.exit_confirmed = self.return_confirmed = False
        self.initial = None
        self.stage = 'C0'
        total = 2 * (source.ap_bytes + source.cp_bytes) + 4 * bk4.MAX_SNAPSHOT
        self.budget = Budget(total + (136 * c.MAX_RESOURCE if resources else 0))

    def call(self, name, action):
        self.budget.check()
        self.store.event('INTENT', operation=name)
        try:
            result = action()
            if name in ('service-start', 'service-stop') and result is not True:
                raise ValueError('Synthetic service acknowledgement missing')
        except BaseException:
            self.unknown = True
            raise
        if name == 'service-start': self.active = True
        if name == 'service-stop': self.active = False; self.exit_confirmed = True
        self.store.event('ACK', operation=name)
        return result

    def receive(self, name, relative, limit, *, exact=None, expected=None):
        sink = Sink(limit, exact=exact, budget=self.budget,
                    store=self.store if relative is not None else None, relative=relative)
        try:
            self.call('read:' + name, lambda: self.tape.read(name, sink))
            result = sink.finish()
        finally:
            sink.close()
        if relative is not None:
            self.files[relative] = result
            self.store.event('HOST_FILE_VERIFIED', file=relative, **result)
        if expected is not None and result != expected:
            raise ValueError('Synthetic source or repeated content differs')
        return result

    def snapshot(self, name, relative):
        info = self.receive(name, relative, bk4.MAX_SNAPSHOT)
        scope = _scope(self.store.read(relative, info))
        base = name.removesuffix('_end')
        if name.endswith('_end') and scope != self.scopes[base]:
            raise ValueError('Scoped snapshot observation changed')
        self.scopes[name] = scope
        self.store.event('SNAPSHOT_FORMAT_CHECKED', file=relative, images=2)

    def finish_service(self):
        self.call('service-stop', lambda: self.tape.service(True))
        returned = _identity(self.call('normal-return', lambda: self.tape.normal(True)))
        if returned != self.initial: raise ValueError('Synthetic normal identity changed')
        self.return_confirmed = True
        self.store.event('NORMAL_OBSERVATION_MATCHED')

    def body(self):
        self.store.require_space(self.source.ap_bytes + self.source.cp_bytes + 4 * bk4.MAX_SNAPSHOT
                                 + (68 * c.MAX_RESOURCE if self.resources else 0) + 512 * 16384 + 131072)
        self.store.event('SYNTHETIC_PREFLIGHT', commit=self.policy.commit, archive_sha256=self.policy.archive_sha)
        self.initial = _identity(self.call('normal-initial', self.tape.normal))
        self.stage = 'C1'; self.store.event('STAGE', stage=self.stage)
        self.call('service-start', self.tape.service)
        self.stage = 'C2'; self.store.event('STAGE', stage=self.stage)
        for name, relative, size, digest in (
                ('ap', 'source/appFw.so', self.source.ap_bytes, self.source.ap_sha),
                ('cp', 'source/cpapp-b.bin', self.source.cp_bytes, self.source.cp_sha)):
            self.receive(name, relative, size, exact=size, expected={'bytes': size, 'sha256': digest})
        self.programs_matched = True
        self.stage = 'C3'
        self.store.event('PROGRAM_CONTENT_MATCHED', kind='stock')
        self.snapshot('ram', 'source/settings-ram.bin')
        self.snapshot('saved', 'source/settings-saved.bin')
        if self.resources:
            for name in c.RESOURCE_FILES:
                relative = 'resources/' + name
                info = self.receive('resource:' + name, relative, c.MAX_RESOURCE)
                count = c.decode_resource(self.store.read(relative, info))['count']
                if self.resource_count is not None and count != self.resource_count:
                    raise ValueError('Mixed resource layouts')
                self.resource_count = count
        for name, relative in (('ap', 'source/appFw.so'), ('cp', 'source/cpapp-b.bin')):
            info = self.files[relative]
            self.receive(name, None, info['bytes'], exact=info['bytes'], expected=info)
        if self.resources:
            for name in c.RESOURCE_FILES:
                info = self.files['resources/' + name]
                self.receive('resource:' + name, None, info['bytes'], exact=info['bytes'], expected=info)
        self.snapshot('ram_end', 'evidence/settings-ram-end.bin')
        self.snapshot('saved_end', 'evidence/settings-saved-end.bin')
        self.store.event('OBSERVATIONS_COMPLETE')
        self.stage = 'C4'
        self.finish_service()
        self.stage = 'C5'; self.store.event('STAGE', stage=self.stage)

    def report(self, success, reason=None):
        return {**boundary(), 'phase': 'SIMULATED_HOST_CAPTURE_COMPLETE' if success else 'NEEDS_REVIEW',
                'reason_type': reason, 'host_files_integrity_checked': success,
                'program_content_matched_in_rehearsal': self.programs_matched,
                'simulated_outcome_unknown': self.unknown,
                'simulated_service_exit_confirmed': self.exit_confirmed,
                'simulated_service_still_active': self.active, 'last_stage': self.stage,
                'simulated_normal_observation_matched': self.return_confirmed,
                'resource_extension_requested': self.resources, 'resource_count': self.resource_count,
                'files': self.files, 'accepted_payload_bytes': self.budget.used,
                'journal_records': self.store.seq, 'journal_head_sha256': self.store.head,
                'commit': self.policy.commit, 'archive_sha256': self.policy.archive_sha,
                'private_absolute_paths_identity_values_setting_keys_or_raw_data_in_report': False}


def simulate(archive, directory, tape, *, resources=False):
    """Only the exact in-memory fake backend is supported; no policy override."""
    if type(tape) is not SyntheticTape or type(resources) is not bool:
        raise ValueError('Exact synthetic backend required')
    policy = p._load_policy(archive)
    sources = [s for s in policy.sources if s.kind == 'stock']
    if len(sources) != 1: raise ValueError('One pinned stock pair required')
    store = Store(directory)
    try:
        run = _Run(store, tape, sources[0], policy, resources)
        try:
            run.body()
            store.event('READY_FOR_REPORT')
            for name, info in {**run.files, **store.documents}.items(): store.verify(name, info)
            result = run.report(True)
            store.put('capture-report.private.json', encoded(result))
            return result
        except BaseException as exc:
            if run.active and not run.unknown:
                try: run.finish_service()
                except BaseException: pass
            result = run.report(False, type(exc).__name__)
            try:
                store.event('NEEDS_REVIEW', reason_type=type(exc).__name__, outcome_unknown=run.unknown)
                result = run.report(False, type(exc).__name__)
                store.put('capture-report.private.json', encoded(result))
            except BaseException:
                pass  # Retain partial files/intents; never overwrite failed evidence.
            return result
    finally:
        store.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('rehearse', help='Generate own zero patterns and check pinned-policy rejection')
    demo.add_argument('--archive', required=True); demo.add_argument('--directory', required=True)
    demo.add_argument('--case', choices=('unknown-program', 'oversize'), default='unknown-program')
    args = parser.parse_args(argv)
    try:
        policy = p._load_policy(args.archive)
        source = next(s for s in policy.sources if s.kind == 'stock')
        tape = SyntheticTape({'ap': Pattern(0, source.ap_bytes + (args.case == 'oversize'))})
        result = simulate(args.archive, args.directory, tape)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0 if result['phase'] == 'SIMULATED_HOST_CAPTURE_COMPLETE' else 1
    except (Exception, KeyboardInterrupt) as exc:
        print('Synthetic capture rejected: ' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
