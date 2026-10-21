"""Bounded read-only inspection of explicit synthetic capture directories.

Evidence consistency only, never authentication, replay or recovery permission.
Uses the retained private-storage contracts; no device imports or archive code.
See ACKNOWLEDGEMENTS.md for the QAQLeonard/ma1co source provenance.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import sys

from .capturestore import Budget, CHUNK, DIR_FLAGS, _parent, _private, _same
from .customcontracts import RESOURCE_FILES

MIB = 1024 * 1024
FOLDERS = ('source', 'evidence', 'resources', 'events')
REPORTS = {'capture-report.private.json': ('host', 'a7c2-synthetic-host-capture-report/1', 'SIMULATED_HOST_CAPTURE_COMPLETE'),
           'session-report.private.json': ('session', 'a7c2-synthetic-session-coordination/1', 'SIMULATED_SESSION_COMPLETE'),
           'pipeline-report.private.json': ('pipeline', 'a7c2-synthetic-authenticated-capture/1', 'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE'),
           'owned-report.private.json': ('owned','a7c2-synthetic-owned-capture/1','SIMULATED_OWNED_CAPTURE_COMPLETE')}
CORE = ('source/appFw.so', 'source/cpapp-b.bin', 'source/settings-ram.bin', 'source/settings-saved.bin',
        'evidence/settings-ram-end.bin', 'evidence/settings-saved-end.bin')
MATERIALS = {n: 128 * MIB if n.endswith(('.so', '.bin')) and n in CORE[:2] else 32 * MIB for n in CORE}
MATERIALS.update({'resources/' + n: MIB for n in RESOURCE_FILES})
GUARDS = tuple('guard:' + n for n in sorted(('libJit.so', 'lut-program-staged.so', 'lut-names-staged.so',
    'lut-runtime-staged.so', 'a7c2.install.request', 'a7c2.install.result', 'a7c2.names.request',
    'a7c2.names.result', 'a7c2.wbi.request', 'a7c2.wbi.result', 'a7c2.runtime.result',
    'a7c2.probe.result', 'a7c2-preview-staged.so'))) + ('guard:ld.so.preload',)
FALSE_COMMON = {'camera_operations_performed', 'actual_source_identity_verified', 'body_binding_verified',
    'chip_roles_verified', 'outer_wrapper_verified', 'snapshot_freshness_verified', 'atomic_capture_verified',
    'independent_media_verified', 'global_camera_lock_acquired', 'native_execution_verified', 'restore_verified', 'write_plan_enabled'}
FALSE_PROFILE = {'host': {'camera_operations_enabled', 'container_complete_backup_verified',
    'physical_validation_verified', 'automatic_retry_allowed', 'private_absolute_paths_identity_values_setting_keys_or_raw_data_in_report'},
    'session': {'physical_protocol_verified', 'response_profile_verified'}}
EXTRA_PROFILE = {'host': {'host_files_integrity_checked', 'simulated_service_exit_confirmed',
    'simulated_service_still_active', 'simulated_normal_observation_matched', 'resource_extension_requested', 'resource_count'},
    'session': {'simulated_transition_started', 'simulated_service_stop_ack', 'simulated_normal_identity_matched', 'accepted_wire_bytes', 'requests'}}
FALSE_PROFILE['pipeline'] = FALSE_PROFILE['session'] | {'actual_authentication_verified', 'fresh_normal_observation_verified', 'resume_allowed'}
PIPELINE_COUNTERS = {'accepted_auth_bytes', 'accepted_total_bytes', 'auth_raw_calls'}
EXTRA_PROFILE['pipeline'] = EXTRA_PROFILE['session'] | PIPELINE_COUNTERS | {'authentication_phase', 'shared_budget_modeled', 'pipeline_blocked'}
OWNED_COUNTERS={'accepted_identity_bytes','identity_queries','identity_raw_calls','owned_handles_opened','owned_handles_closed'}
FALSE_PROFILE['owned']=FALSE_PROFILE['pipeline']
EXTRA_PROFILE['owned']=EXTRA_PROFILE['pipeline']|OWNED_COUNTERS|{'host_binding_modeled','host_blocked','cleanup_error_type'}
HOST_OPERATIONS={'INVENTORY','MEDIA','UNMOUNT','OPEN_HANDLE','DESCRIPTOR','KERNEL_ACTIVE','DETACH_KERNEL',
    'CLAIM_INTERFACE','NORMAL_IDENTITY_QUERY','DISPOSE_RESOURCES','RELEASE_INTERFACE','ATTACH_KERNEL',
    'SIMULATE_SERVICE_ARRIVAL','SIMULATE_NORMAL_ARRIVAL'}



COMMON = {'schema', 'private_report', 'simulation_only', 'phase', 'reason_type', 'last_stage',
    'simulated_outcome_unknown', 'program_content_matched_in_rehearsal', 'files', 'accepted_payload_bytes',
    'journal_records', 'journal_head_sha256', 'commit', 'archive_sha256'}
EVENTS = {'INTENT', 'ACK', 'STAGE', 'HOST_FILE_VERIFIED', 'SNAPSHOT_FORMAT_CHECKED', 'SYNTHETIC_PREFLIGHT',
    'PROGRAM_CONTENT_MATCHED', 'OBSERVATIONS_COMPLETE', 'NORMAL_OBSERVATION_MATCHED', 'SYNTHETIC_LOCK_ORDER',
    'GUARD_ABSENCE_MODELED', 'NORMAL_SAME_SOURCE_MATCH_MODELED', 'READY_FOR_REPORT', 'NEEDS_REVIEW', 'RAW_AUTHENTICATION_MODELED', 'RAW_HANDLES_BOUND_MODELED', 'RAW_HANDLE_CLOSED_MODELED','HOST_INTENT','HOST_ACK','OWNED_HOST_BOUND_MODELED','OWNED_HANDLE_CLOSED_MODELED','HOST_WAIT_BEGIN_MODELED','HOST_WAIT_END_MODELED'}


class _Refused(ValueError):
    pass


def _stamp(info):
    # Reading can update atime. It is neither evidence of a writer nor a
    # metadata field that a read-only checker can promise to preserve.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _info(value):
    return (type(value) is dict and set(value) == {'bytes', 'sha256'}
        and type(value['bytes']) is int and 0 < value['bytes'] <= 128 * MIB
        and type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']))


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def constant(_): raise ValueError('Non-finite JSON')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    if type(value) is not dict: raise ValueError('JSON object required')
    return value


class _Reader:
    def __init__(self, directory):
        self.parent = self.lock = None
        self.fds, self.dirs, self.files, self.inventory = {}, {}, {}, set()
        self.budget = Budget(512 * MIB)
        try:
            self.path, self.parent = _parent(directory)
            self.fds[''] = os.open(self.path.name, DIR_FLAGS, dir_fd=self.parent)
            _private(os.fstat(self.fds['']), True)
            self.lock = os.open('session.lock', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fds[''])
            info = os.fstat(self.lock); _private(info)
            if info.st_size != 0: raise _Refused('INVALID_JOB_LOCK')
            if not _same(info, os.stat('session.lock', dir_fd=self.fds[''], follow_symlinks=False)):
                raise _Refused('INPUT_CHANGED')
            try: fcntl.flock(self.lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError: raise _Refused('ACTIVE_JOB') from None
            self.lock_stamp = self.files['session.lock'] = _stamp(info)
            roots = self._list('', 8)
            for name in roots & set(FOLDERS):
                self.fds[name] = os.open(name, DIR_FLAGS, dir_fd=self.fds[''])
                _private(os.fstat(self.fds[name]), True)
                self._list(name, 2048 if name == 'events' else 80)
            self.check()
        except BaseException:
            self.close()
            raise

    def _list(self, folder, limit):
        fd = self.fds[folder]; _private(os.fstat(fd), True)
        names = set()
        with os.scandir(fd) as entries:
            for entry in entries:
                if len(names) >= limit: raise _Refused('ENTRY_LIMIT')
                names.add(entry.name)
                relative = folder + '/' + entry.name if folder else entry.name
                info = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
                if not folder and entry.name in FOLDERS:
                    _private(info, True)
                else:
                    _private(info)
                    self.files[relative] = _stamp(info)
                    self.inventory.add(relative)
        self.dirs[folder] = (_stamp(os.fstat(fd)), names)
        return names

    def _folder(self, relative):
        folder, _, name = relative.rpartition('/')
        return self.fds[folder], name

    def read(self, relative, limit, *, content=False):
        self.budget.check()
        folder, name = self._folder(relative)
        if self.files.get(relative) is None: raise _Refused('INPUT_CHANGED')
        if self.files[relative][5] > limit: raise _Refused('FILE_LIMIT')
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
        try:
            before = os.fstat(fd); _private(before)
            if _stamp(before) != self.files[relative]: raise _Refused('INPUT_CHANGED')
            if self.budget.used + before.st_size > self.budget.limit: raise _Refused('TOTAL_BYTE_LIMIT')
            digest, size, raw = hashlib.sha256(), 0, bytearray()
            while True:
                self.budget.check()
                block = os.read(fd, min(CHUNK, limit + 1 - size))
                if not block: break
                if size + len(block) > limit: raise _Refused('FILE_LIMIT')
                self.budget.accept(len(block)); size += len(block); digest.update(block)
                if content: raw.extend(block)
            if _stamp(os.fstat(fd)) != self.files[relative] or size != before.st_size:
                raise _Refused('INPUT_CHANGED')
            return (bytes(raw) if content else None), {'bytes': size, 'sha256': digest.hexdigest()}
        finally:
            os.close(fd)

    def check(self):
        self.budget.check()
        root = self.fds['']
        if _stamp(os.fstat(self.lock)) != self.lock_stamp or self.files['session.lock'] != self.lock_stamp:
            raise _Refused('INPUT_CHANGED')
        if not _same(os.fstat(root), os.stat(self.path.name, dir_fd=self.parent, follow_symlinks=False)):
            raise _Refused('INPUT_CHANGED')
        for folder, (stamp, names) in self.dirs.items():
            fd = self.fds[folder]
            if _stamp(os.fstat(fd)) != stamp: raise _Refused('INPUT_CHANGED')
            if folder and _stamp(os.stat(folder, dir_fd=root, follow_symlinks=False)) != stamp:
                raise _Refused('INPUT_CHANGED')
            current = set()
            with os.scandir(fd) as entries:
                for entry in entries:
                    if len(current) > len(names): raise _Refused('INPUT_CHANGED')
                    current.add(entry.name)
            if current != names: raise _Refused('INPUT_CHANGED')
        for relative, stamp in self.files.items():
            folder, name = self._folder(relative)
            if _stamp(os.stat(name, dir_fd=folder, follow_symlinks=False)) != stamp:
                raise _Refused('INPUT_CHANGED')

    def close(self):
        for fd in self.fds.values(): os.close(fd)
        self.fds.clear()
        if self.lock is not None: os.close(self.lock); self.lock = None
        if self.parent is not None: os.close(self.parent); self.parent = None


def _ack_plan(profile, resources):
    if profile == 'host':
        optional = ['read:resource:' + n for n in RESOURCE_FILES] if resources else []
        return ['normal-initial', 'service-start', 'read:ap', 'read:cp', 'read:ram', 'read:saved',
            *optional, 'read:ap', 'read:cp', *optional, 'read:ram_end', 'read:saved_end', 'service-stop', 'normal-return']
    def pair(name): return ['select:' + name, 'read:' + name]
    guards = [op for n in GUARDS for op in pair(n)]
    programs = pair('appFw.so') + pair('cpapp-b.bin')
    optional = [op for n in RESOURCE_FILES for op in pair(n)] if resources else []
    return ['normal-before', 'auth-normal-start', 'auth-normal-verify', 'service-observation',
        'auth-service-start', 'auth-service-verify', 'hasp', *guards, *programs, 'ram', 'saved',
        *optional, *programs, *optional, 'ram', 'saved', *guards, 'service-stop', 'normal-after']


def _host_sequence(operations):
    """Exact modeled lifecycle with variable bounded media polling, no values."""
    position=0
    def take(name):
        nonlocal position
        if position>=len(operations) or operations[position]!=name:raise ValueError('Host order')
        position+=1
    def optional(name):
        nonlocal position
        if position<len(operations) and operations[position]==name:position+=1;return True
        return False
    def normal():
        take('INVENTORY');media=unmount=0
        while position<len(operations) and operations[position] in ('MEDIA','UNMOUNT'):
            if optional('MEDIA'):media+=1
            else:take('UNMOUNT');unmount+=1
        if media<3 or unmount<1:raise ValueError('Media lifecycle')
        for name in ('INVENTORY','OPEN_HANDLE','DESCRIPTOR','KERNEL_ACTIVE'):take(name)
        detached=optional('DETACH_KERNEL');take('CLAIM_INTERFACE');take('NORMAL_IDENTITY_QUERY')
        return detached
    try:
        normal();take('DISPOSE_RESOURCES');take('SIMULATE_SERVICE_ARRIVAL')
        for name in ('INVENTORY','OPEN_HANDLE','DESCRIPTOR','KERNEL_ACTIVE','CLAIM_INTERFACE','DISPOSE_RESOURCES','SIMULATE_NORMAL_ARRIVAL'):take(name)
        detached=normal();take('RELEASE_INTERFACE')
        if detached:take('ATTACH_KERNEL')
        take('DISPOSE_RESOURCES')
        return position==len(operations)
    except ValueError:return False


class _Evidence:
    def __init__(self):
        self.issues, self.inconsistent = set(), False
        self.pending, self.acks, self.events, self.verified = {}, [], [], {}
        self.actual, self.count, self.head = {}, 0, '0' * 64
        self.orphans, self.unknown = 0, False
        self.raw_auth_markers = 0
        self.raw_bindings, self.raw_closes = 0, {}
        self.host_pending,self.host_acks,self.owned_closes={},[],{};self.owned_bindings=0
        self.host_positions=[];self.waits=[];self.active_wait=None

    def details_valid(self, event, details):
        if event in ('OBSERVATIONS_COMPLETE', 'NORMAL_OBSERVATION_MATCHED', 'NORMAL_SAME_SOURCE_MATCH_MODELED', 'READY_FOR_REPORT'):
            return not details
        if event=='HOST_WAIT_BEGIN_MODELED':
            return set(details)=={'phase'} and details['phase'] in ('service','normal-return')
        if event=='HOST_WAIT_END_MODELED':
            return (set(details)=={'phase','outcome','polls'} and details['phase'] in ('service','normal-return')
                and details['outcome'] in ('found','timed-out') and type(details['polls']) is int and 0<=details['polls']<=40)
        if event in ('HOST_INTENT','HOST_ACK'):
            return set(details)=={'operation'} and type(details['operation']) is str and details['operation'] in HOST_OPERATIONS
        if event=='OWNED_HOST_BOUND_MODELED':
            return set(details)=={'owned_handles','same_service_handle'} and type(details['owned_handles']) is int and details['owned_handles']==3 and details['same_service_handle'] is True
        if event=='OWNED_HANDLE_CLOSED_MODELED':
            return set(details)=={'role'} and details['role'] in ('normal-initial','service','normal-return')
        if event == 'RAW_HANDLES_BOUND_MODELED':
            return (set(details)=={'owned_handles','same_service_handle'}
                and type(details['owned_handles']) is int and details['owned_handles']==2 and details['same_service_handle'] is True)
        if event == 'RAW_HANDLE_CLOSED_MODELED':
            return set(details)=={'role'} and details['role'] in ('normal-initial','service')
        if event == 'RAW_AUTHENTICATION_MODELED':
            return (set(details) == {'accepted_auth_bytes', 'raw_calls'}
                and type(details['accepted_auth_bytes']) is int and details['accepted_auth_bytes'] == 14448
                and type(details['raw_calls']) is int and details['raw_calls'] == 30)
        if event == 'STAGE': return set(details) == {'stage'} and details['stage'] in ('C1', 'C2', 'C5')
        if event == 'PROGRAM_CONTENT_MATCHED': return details == {'kind': 'stock'}
        if event == 'SYNTHETIC_LOCK_ORDER':
            return (set(details) == {'global_lock_modeled', 'real_global_lock_acquired'}
                and details['global_lock_modeled'] is True and details['real_global_lock_acquired'] is False)
        if event == 'GUARD_ABSENCE_MODELED':
            return set(details) == {'count'} and type(details['count']) is int and details['count'] == 14
        if event == 'SNAPSHOT_FORMAT_CHECKED':
            return (set(details) in ({'file'}, {'file', 'images'}) and details.get('file') in CORE[2:]
                and ('images' not in details or type(details['images']) is int and details['images'] == 2))
        if event == 'SYNTHETIC_PREFLIGHT':
            return (set(details) == {'commit', 'archive_sha256'} and type(details['commit']) is str
                and 0 < len(details['commit']) <= 64 and type(details['archive_sha256']) is str
                and re.fullmatch('[0-9a-f]{64}', details['archive_sha256']))
        return True

    def problem(self, code, *, contradiction=False):
        self.issues.add(code)
        self.inconsistent |= contradiction

    def journal(self, reader):
        files = sorted(n for n in reader.inventory if n.startswith('events/'))
        allowed = set(_ack_plan('host', True) + _ack_plan('session', True))
        for index, name in enumerate(files):
            if name != f'events/{index:08d}.json':
                self.problem('JOURNAL_SEQUENCE_GAP', contradiction=True); break
            raw, info = reader.read(name, 16384, content=True)
            try:
                record = _json(raw)
                if (set(record) != {'seq', 'previous_sha256', 'event', 'details'}
                        or type(record['seq']) is not int or record['seq'] != index
                        or record['previous_sha256'] != self.head
                        or type(record['event']) is not str or record['event'] not in EVENTS
                        or type(record['details']) is not dict):
                    self.problem('JOURNAL_STRUCTURE_OR_CHAIN', contradiction=True); break
            except (ValueError, TypeError, RecursionError):
                self.problem('PARTIAL_OR_INVALID_JOURNAL'); break
            event, details = record['event'], record['details']
            if not self.details_valid(event, details): self.problem('INVALID_EVENT_DETAILS', contradiction=True)
            if event in ('INTENT', 'ACK'):
                op = details.get('operation')
                if set(details) != {'operation'} or type(op) is not str or op not in allowed:
                    self.problem('UNSUPPORTED_OPERATION', contradiction=True); break
                if event == 'INTENT':
                    if op in self.pending: self.problem('DUPLICATE_PENDING_INTENT', contradiction=True)
                    self.pending[op] = index
                else:
                    if op not in self.pending: self.problem('ACK_WITHOUT_INTENT', contradiction=True)
                    self.pending.pop(op, None); self.acks.append(op)
            elif event=='HOST_WAIT_BEGIN_MODELED':
                if self.active_wait is not None or self.owned_bindings!=1 or self.host_pending:
                    self.problem('INVALID_HOST_WAIT_BEGIN',contradiction=True)
                self.active_wait=(details.get('phase'),len(self.host_acks),len(self.acks))
            elif event=='HOST_WAIT_END_MODELED':
                if self.active_wait is None or details.get('phase')!=self.active_wait[0]:
                    self.problem('INVALID_HOST_WAIT_END',contradiction=True)
                else:
                    phase,start,position=self.active_wait;polls=details.get('polls')
                    if type(polls) is not int or self.host_acks[start:]!=['INVENTORY']*polls or self.host_pending:
                        self.problem('HOST_WAIT_POLL_EVIDENCE_DIFFERS',contradiction=True)
                    self.waits.append((phase,details.get('outcome'),polls,start,len(self.host_acks),position))
                self.active_wait=None
            elif event in ('HOST_INTENT','HOST_ACK'):
                op=details.get('operation')
                if type(op) is not str or op not in HOST_OPERATIONS:
                    self.problem('UNSUPPORTED_HOST_OPERATION',contradiction=True);break
                if event=='HOST_INTENT':
                    if self.host_pending and op!='DISPOSE_RESOURCES':self.problem('OVERLAPPED_HOST_INTENT',contradiction=True)
                    self.host_pending.setdefault(op,[]).append(index)
                else:
                    if op not in self.host_pending:self.problem('HOST_ACK_WITHOUT_INTENT',contradiction=True)
                    if op in self.host_pending:
                        self.host_pending[op].pop()
                        if not self.host_pending[op]:del self.host_pending[op]
                    self.host_acks.append(op);self.host_positions.append((op,len(self.acks)))
            elif event=='OWNED_HOST_BOUND_MODELED':
                self.owned_bindings+=1
                if self.owned_bindings!=1 or self.acks or self.pending or self.host_acks or self.host_pending:
                    self.problem('OWNED_BINDING_OUT_OF_ORDER',contradiction=True)
            elif event=='OWNED_HANDLE_CLOSED_MODELED':
                role=details.get('role')
                if self.owned_bindings!=1 or role in self.owned_closes:
                    self.problem('OWNED_CLOSE_WITHOUT_UNIQUE_BINDING',contradiction=True)
                if type(role) is str:self.owned_closes[role]=(len(self.acks),bool(self.pending or self.host_pending))
            elif event == 'HOST_FILE_VERIFIED':
                file = details.get('file')
                expected = {k: v for k, v in details.items() if k != 'file'}
                if type(file) is not str or file not in MATERIALS or not _info(expected):
                    self.problem('INVALID_MATERIAL_RECORD', contradiction=True); break
                if file in self.verified: self.problem('DUPLICATE_MATERIAL_RECORD', contradiction=True)
                self.verified[file] = expected
            elif event == 'RAW_HANDLES_BOUND_MODELED':
                self.raw_bindings += 1
                if self.raw_bindings!=1 or self.acks or self.pending:
                    self.problem('RAW_BINDING_OUT_OF_ORDER',contradiction=True)
            elif event == 'RAW_HANDLE_CLOSED_MODELED':
                role=details.get('role')
                if self.raw_bindings!=1 or role in self.raw_closes:
                    self.problem('RAW_CLOSE_WITHOUT_UNIQUE_BINDING',contradiction=True)
                if type(role) is str: self.raw_closes[role]=(len(self.acks),bool(self.pending))
            elif event == 'RAW_AUTHENTICATION_MODELED':
                self.raw_auth_markers += 1
                if self.pending or self.acks != _ack_plan('pipeline', False)[:6] or self.raw_auth_markers != 1:
                    self.problem('RAW_AUTH_MARKER_OUT_OF_ORDER', contradiction=True)
            elif event == 'NEEDS_REVIEW':
                if (set(details) != {'reason_type', 'outcome_unknown'}
                        or type(details.get('outcome_unknown')) is not bool
                        or type(details.get('reason_type')) is not str or not 0 < len(details['reason_type']) <= 128):
                    self.problem('INVALID_REVIEW_RECORD', contradiction=True)
                self.unknown |= details.get('outcome_unknown') is True
            self.head, self.count = info['sha256'], index + 1
            self.events.append(event)

    def materials(self, reader):
        for name in sorted(reader.inventory & MATERIALS.keys()):
            _, self.actual[name] = reader.read(name, MATERIALS[name])
        for name, info in self.verified.items():
            if self.actual.get(name) != info: self.problem('RECORDED_MATERIAL_DIFFERS', contradiction=True)
        self.orphans = len(self.actual.keys() - self.verified.keys())
        if self.orphans: self.problem('UNJOURNALED_OR_PARTIAL_MATERIAL')

    def report(self, reader):
        names = reader.inventory & REPORTS.keys()
        if len(names) > 1:
            self.problem('AMBIGUOUS_REPORTS', contradiction=True); return False
        if not names:
            self.problem('REPORT_MISSING'); return False
        name, = names
        profile, schema, phase = REPORTS[name]
        raw, _ = reader.read(name, 131072, content=True)
        try: report = _json(raw)
        except (ValueError, TypeError, RecursionError):
            self.problem('PARTIAL_OR_INVALID_REPORT'); return False
        fields = COMMON | FALSE_COMMON | FALSE_PROFILE[profile] | EXTRA_PROFILE[profile]
        if (set(report) != fields or report.get('schema') != schema
                or report.get('simulation_only') is not True or report.get('private_report') is not True
                or report.get('phase') not in (phase, 'NEEDS_REVIEW')):
            self.problem('REPORT_SCHEMA_MISMATCH', contradiction=True); return False
        if any(report[k] is not False for k in FALSE_COMMON | FALSE_PROFILE[profile]):
            self.problem('UNSUPPORTED_PHYSICAL_OR_WRITE_CLAIM', contradiction=True)
        if (type(report['commit']) is not str or not 0 < len(report['commit']) <= 64
                or type(report['archive_sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', report['archive_sha256'])
                or report['last_stage'] not in ('C0', 'C1', 'C2', 'C3', 'C4', 'C5')
                or report['reason_type'] is not None and (type(report['reason_type']) is not str or len(report['reason_type']) > 128)):
            self.problem('INVALID_REPORT_METADATA', contradiction=True)
        boolean = {'simulated_outcome_unknown', 'program_content_matched_in_rehearsal'}
        nonboolean = {'resource_count'} if profile == 'host' else {'accepted_wire_bytes', 'requests'}
        if profile in ('pipeline','owned'): nonboolean |= PIPELINE_COUNTERS | {'authentication_phase'}
        if profile=='owned':nonboolean |= OWNED_COUNTERS|{'cleanup_error_type'}
        boolean |= EXTRA_PROFILE[profile] - nonboolean
        if any(type(report[k]) is not bool for k in boolean):
            self.problem('INVALID_REPORT_FLAGS', contradiction=True)
        if (type(report['journal_records']) is not int or report['journal_records'] != self.count
                or report['journal_head_sha256'] != self.head):
            self.problem('REPORT_JOURNAL_DIFFERS', contradiction=True)
        counters = {'accepted_payload_bytes'} | ({'accepted_wire_bytes', 'requests'} if profile != 'host' else set())
        if profile in ('pipeline','owned'): counters |= PIPELINE_COUNTERS
        for counter in counters:
            if type(report[counter]) is not int or not 0 <= report[counter] <= 2**31:
                self.problem('INVALID_REPORT_COUNTER', contradiction=True)
        if profile in ('pipeline','owned'):
            if (report['authentication_phase'] not in ('NOT_STARTED','NEW','NORMAL_CONTROL_RETURNED','WAIT_SERVICE',
                    'SERVICE_CONTROL_RETURNED','SERVICE_AUTHENTICATED','STOP_CONTROL_RETURNED','SYNTHETIC_RETURN_MATCHED','NEEDS_REVIEW')
                    or report['accepted_auth_bytes'] > 32768 or report['auth_raw_calls'] > 31
                    or report['accepted_total_bytes'] != report['accepted_payload_bytes'] + report['accepted_auth_bytes'] + (report.get('accepted_identity_bytes',0) if profile=='owned' else 0)):
                self.problem('INVALID_AUTHENTICATION_ACCOUNTING', contradiction=True)
        if profile=='owned':
            counters |= OWNED_COUNTERS
            for counter in OWNED_COUNTERS:
                if type(report[counter]) is not int or not 0<=report[counter]<=65536:self.problem('INVALID_OWNED_COUNTER',contradiction=True)
            if (report['accepted_identity_bytes']>65536 or report['identity_queries']>2 or report['identity_raw_calls']>28
                    or not 0<=report['owned_handles_closed']<=report['owned_handles_opened']<=3
                    or report['cleanup_error_type'] is not None and (type(report['cleanup_error_type']) is not str or len(report['cleanup_error_type'])>128)):
                self.problem('INVALID_OWNED_ACCOUNTING',contradiction=True)
        elif self.host_acks or self.host_pending or self.owned_bindings or self.owned_closes or self.waits or self.active_wait:
            self.problem('OWNED_EVIDENCE_WITHOUT_OWNED_REPORT',contradiction=True)
        files = report['files']
        if type(files) is not dict or any(type(n) is not str or n not in MATERIALS or not _info(v) for n, v in files.items()):
            self.problem('INVALID_REPORT_MATERIALS', contradiction=True); files = {}
        for file, info in files.items():
            if self.actual.get(file) != info: self.problem('REPORT_MATERIAL_DIFFERS', contradiction=True)
        if self.verified.keys() - files.keys(): self.problem('REPORT_OMITS_VERIFIED_MATERIAL', contradiction=True)
        if files.keys() - self.verified.keys(): self.problem('REPORT_HAS_UNJOURNALED_MATERIAL')
        self.unknown |= report['simulated_outcome_unknown'] is True
        complete = report['phase'] == phase
        if complete:
            resources = any(n.startswith('resources/') for n in self.actual)
            expected = set(CORE) | ({'resources/' + n for n in RESOURCE_FILES} if resources else set())
            prerequisites = (self.actual.keys() == expected and files.keys() == expected
                and self.verified.keys() == expected and not self.pending and not self.host_pending and not self.unknown
                and report['program_content_matched_in_rehearsal'] is True and report['reason_type'] is None
                and report['last_stage'] == 'C5' and self.events and self.events[-1] == 'READY_FOR_REPORT'
                and self.acks == _ack_plan(profile, resources)
                and self.events.count('SNAPSHOT_FORMAT_CHECKED') == 4 and 'NEEDS_REVIEW' not in self.events
                and ('SYNTHETIC_PREFLIGHT' not in self.events if profile != 'host' else 'SYNTHETIC_LOCK_ORDER' not in self.events))
            repeated = set(CORE[:2]) | {n for n in expected if n.startswith('resources/')}
            payload = sum(info['bytes'] * (2 if n in repeated else 1) for n, info in self.actual.items())
            prerequisites &= report['accepted_payload_bytes'] == payload + (88 if profile != 'host' else 0)
            if profile == 'host':
                prerequisites &= (report['host_files_integrity_checked'] is True
                    and report['simulated_service_exit_confirmed'] is True
                    and report['simulated_service_still_active'] is False
                    and report['simulated_normal_observation_matched'] is True
                    and report['resource_extension_requested'] is resources
                    and report['resource_count'] in ((2860, 2866) if resources else (None,))
                    and self.events.count('NORMAL_OBSERVATION_MATCHED') == 1
                    and self.events.count('SYNTHETIC_PREFLIGHT') == 1
                    and self.events.count('PROGRAM_CONTENT_MATCHED') == 1
                    and self.events.count('OBSERVATIONS_COMPLETE') == 1)
            else:
                prerequisites &= (report['simulated_transition_started'] is True
                    and report['simulated_service_stop_ack'] is True and report['simulated_normal_identity_matched'] is True
                    and self.events.count('GUARD_ABSENCE_MODELED') == 2
                    and self.events.count('NORMAL_SAME_SOURCE_MATCH_MODELED') == 1
                    and self.events.count('SYNTHETIC_LOCK_ORDER') == 1
                    and report['requests'] == sum(op in ('hasp', 'ram', 'saved') or op.startswith(('read:', 'select:')) for op in self.acks)
                    and report['accepted_wire_bytes'] >= report['accepted_payload_bytes'] + 24 * report['requests'])
            if profile in ('pipeline','owned'):
                prerequisites &= (report['accepted_auth_bytes'] == 14448 and report['auth_raw_calls'] == 31
                    and report['authentication_phase'] == 'SYNTHETIC_RETURN_MATCHED'
                    and report['shared_budget_modeled'] is True and report['pipeline_blocked'] is False
                    and self.raw_auth_markers == 1)
                if self.raw_bindings:
                    prerequisites &= (self.raw_bindings==1 and self.raw_closes=={
                        'normal-initial':(3,False),'service':(len(self.acks)-1,False)})
            else:
                prerequisites &= self.raw_auth_markers == 0 and self.raw_bindings == 0 and not self.raw_closes
            if profile=='owned':
                host_operations=list(self.host_acks)
                wait_valid=self.active_wait is None
                if self.waits:
                    wait_valid &= len(self.waits)==2 and [v[0] for v in self.waits]==['service','normal-return']
                    wait_valid &= all(v[1]=='found' and type(v[2]) is int and 2<=v[2]<=40 for v in self.waits)
                    wait_valid &= [v[5] for v in self.waits]==[3,len(self.acks)-1]
                    for _,_,_,start,end,_ in reversed(self.waits):host_operations[start:end]=['INVENTORY']
                prerequisites &= wait_valid and (report['host_binding_modeled'] is True and report['host_blocked'] is False
                    and report['cleanup_error_type'] is None and report['identity_queries']==2 and report['identity_raw_calls']==28
                    and 16930<=report['accepted_identity_bytes']<=33728
                    and report['owned_handles_opened']==report['owned_handles_closed']==3 and self.owned_bindings==1
                    and not self.raw_bindings and not self.raw_closes and _host_sequence(host_operations)
                    and [n for op,n in self.host_positions if op=='NORMAL_IDENTITY_QUERY']==[0,len(self.acks)-1]
                    and [n for op,n in self.host_positions if op=='OPEN_HANDLE']==[0,3,len(self.acks)-1]
                    and [n for op,n in self.host_positions if op=='DISPOSE_RESOURCES']==[3,len(self.acks)-1,len(self.acks)]
                    and self.owned_closes=={'normal-initial':(3,False),'service':(len(self.acks)-1,False),'normal-return':(len(self.acks),False)})
            if not prerequisites or self.issues:
                self.problem('COMPLETE_REPORT_WITH_INCOMPLETE_EVIDENCE', contradiction=True)
        else:
            self.problem('REHEARSAL_NOT_COMPLETE')
        return complete


def _result(classification, evidence=None, refusal=None):
    return {'schema': 'a7c2-readonly-synthetic-capture-inspection/1', 'private_report': True,
        'classification': classification, 'inspection_only': True, 'simulation_only': True,
        'camera_operations_performed': False, 'actual_source_identity_verified': False,
        'body_binding_verified': False, 'physical_protocol_verified': False, 'actual_authentication_verified': False, 'chip_roles_verified': False,
        'snapshot_freshness_verified': False, 'independent_media_verified': False,
        'program_policy_revalidated': False, 'material_formats_revalidated': False,
        'restore_verified': False, 'write_plan_enabled': False, 'resume_allowed': False,
        'journal_records_checked': evidence.count if evidence else 0,
        'unacknowledged_intents': len(evidence.pending)+sum(map(len,evidence.host_pending.values())) if evidence else 0,
        'materials_hashed': len(evidence.actual) if evidence else 0,
        'unjournaled_materials': evidence.orphans if evidence else 0,
        'issues': sorted(evidence.issues) if evidence else [refusal]}


def inspect_directory(directory):
    """Open an explicit existing directory read-only; never repair or search."""
    reader = None
    try:
        reader = _Reader(directory)
        evidence = _Evidence()
        expected = set(MATERIALS) | set(REPORTS) | {'session.lock'}
        expected |= {f'events/{n:08d}.json' for n in range(2048)}
        if reader.inventory - expected: evidence.problem('UNEXPECTED_ENTRY', contradiction=True)
        if set(FOLDERS) - reader.fds.keys(): evidence.problem('PARTIAL_DIRECTORY_LAYOUT')
        evidence.journal(reader); evidence.materials(reader)
        complete = evidence.report(reader)
        reader.check()
        if evidence.inconsistent: classification = 'EVIDENCE_INCONSISTENT'
        elif evidence.pending or evidence.host_pending or evidence.unknown: classification = 'NEEDS_REVIEW_UNKNOWN'
        elif complete and not evidence.issues: classification = 'CONSISTENT_SIMULATION_COMPLETE'
        else: classification = 'NEEDS_REVIEW_INCOMPLETE'
        return _result(classification, evidence)
    except _Refused as exc:
        return _result('REFUSED', refusal=str(exc))
    except (OSError, ValueError, TypeError, RecursionError):
        return _result('REFUSED', refusal='UNSAFE_UNREADABLE_OR_LIMITED_INPUT')
    finally:
        if reader is not None: reader.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('inspect', help='Inspect one existing synthetic directory without modifying it')
    command.add_argument('--directory', required=True)
    args = parser.parse_args(argv)
    try: result = inspect_directory(args.directory)
    except KeyboardInterrupt: result = _result('REFUSED', refusal='INSPECTION_INTERRUPTED')
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result['classification'] == 'CONSISTENT_SIMULATION_COMPLETE' else 1


if __name__ == '__main__':
    sys.exit(main())
