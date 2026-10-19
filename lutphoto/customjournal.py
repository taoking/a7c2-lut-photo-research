"""POSIX-only durable synthetic rehearsal; no camera adapter or resume command."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from . import customcontracts as contracts
from . import custommigration as migration

SCHEMA = 'a7c2-durable-synthetic-transaction/1'
LEGACY_CAMERA_LOCK = '/var/run/a7c2-fl23-macos.lock'  # Integration requirement only; never opened here.
STAGES = ('before-intent', 'intent-temporary', 'intent-published', 'after-intent',
          'state-temporary', 'state-published', 'partial-write', 'after-write',
          'verified-temporary', 'verified-published', 'after-verified')
FINAL_STAGES = ('before-complete', 'complete-temporary', 'complete-published')
LIMIT = 128 * 1024


class LockBusy(ValueError):
    pass


class InjectedStop(Exception):
    pass


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def private_directory(path):
    info = Path(path).lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('Expected a private owned directory')


def private_file(info):
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_nlink != 1 or info.st_mode & 0o077):
        raise ValueError('Expected a private owned single-link regular file')


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextlib.contextmanager
def session_lock(directory, *, create=False):
    """All prototype jobs must share this explicit lock directory/inode."""
    directory = Path(directory)
    if create:
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError:
            pass
        else:
            sync_directory(directory.parent)
    private_directory(directory)
    path = directory / 'session.lock'
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open(path, flags | (os.O_CREAT if create else 0), 0o600)
    try:
        info = os.fstat(fd); private_file(info)
        if not info.st_mode & 0o200:
            raise ValueError('Lock must be writable by its owner')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise LockBusy('Another process owns the prototype session') from exc
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise ValueError('Lock inode changed')
        if create:
            os.fsync(fd); sync_directory(directory)
        yield {'device': info.st_dev, 'inode': info.st_ino}
    finally:
        os.close(fd)  # Never unlink: other processes may already have this inode open.


def durable_write(path, value, *, replace=False, checkpoint=lambda stage: None):
    """File sync -> publish -> directory sync; leave failed evidence untouched."""
    path = Path(path); temporary = path.parent / ('.pending-' + uuid.uuid4().hex)
    raw = encoded(value)
    if len(raw) > LIMIT:
        raise ValueError('Synthetic document exceeds limit')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    checkpoint('temporary')
    if replace:
        os.replace(temporary, path)
    else:
        os.link(temporary, path, follow_symlinks=False)
    checkpoint('published')
    sync_directory(path.parent)
    if not replace:
        temporary.unlink(); sync_directory(path.parent)
    return migration.sha(raw)


def read_document(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno()); private_file(info)
        if info.st_size > LIMIT:
            raise ValueError('Synthetic document exceeds limit')
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Synthetic document exceeds limit')
    # Canonical bytes also reject duplicate keys, non-finite numbers and altered encodings.
    value = json.loads(raw)
    if encoded(value) != raw:
        raise ValueError('Document is not canonical')
    return value, migration.sha(raw)


def prepare(capsule, direction):
    if direction not in ('install', 'restore'):
        raise ValueError('Invalid synthetic direction')
    keys = {'schema', 'material_kind', 'model', 'firmware', 'body_token', 'source_state',
            'source', 'backups', 'replacements'}
    if not isinstance(capsule, dict) or set(capsule) != keys or len(encoded(capsule)) > LIMIT:
        raise ValueError('Bounded exact synthetic capsule required')
    for row in capsule.get('backups', []):
        if not isinstance(row, dict) or set(row) != {'body_token', 'storage_token', 'files'}:
            raise ValueError('Invalid synthetic backup shape')
    for row in capsule.get('replacements', {}).values():
        if not isinstance(row, dict) or set(row) != {'name', 'table_hex'}:
            raise ValueError('Invalid synthetic replacement shape')
    plan, source, target = migration.prepare(capsule)
    start, goal = (source, target) if direction == 'install' else (target, source)
    order = migration.ORDER if direction == 'install' else tuple(reversed(migration.ORDER))
    changed = [name for name in order if start[name] != goal[name]]
    return plan, start, goal, changed


def format_contracts():
    """Independent fixture checks, not bindings between toy buffers and Sony units."""
    return {'resource_fixture': contracts.resource_contract(contracts.synthetic_resource(True), {2: 'Demo Look'}, 'standalone'),
            'settings_fixture': contracts.settings_contract(contracts.synthetic_settings()),
            'toy_components_bound_to_real_layout': False}


def boundary():
    return {'schema': 'a7c2-durable-synthetic-report/1', 'simulation_only': True,
            'camera_operations_enabled': False, 'actual_source_identity_verified': False,
            'global_camera_lock_acquired': False, 'independent_media_verified': False,
            'physical_validation_verified': False, 'power_loss_verified': False,
            'journal_authenticity_verified': False, 'automatic_retry_allowed': False,
            'automatic_restore_allowed': False, 'inspection_read_only': True}


def _inspect(directory, lock_identity):
    directory = Path(directory)
    try:
        private_directory(directory)
        expected_names = {'manifest.json', 'capsule.json', 'contracts.json', 'current.json', 'events'}
        if set(os.listdir(directory)) != expected_names:
            raise ValueError('Unexpected or incomplete transaction files')
        capsule, capsule_sha = read_document(directory / 'capsule.json')
        manifest, _ = read_document(directory / 'manifest.json')
        if not isinstance(manifest, dict):
            raise ValueError('Invalid manifest')
        plan, start, goal, changed = prepare(capsule, manifest.get('direction'))
        txid = manifest.get('transaction_id')
        if not isinstance(txid, str) or not re.fullmatch('[0-9a-f]{32}', txid):
            raise ValueError('Invalid transaction identifier')
        contract, contract_sha = read_document(directory / 'contracts.json')
        expected_manifest = {'schema': SCHEMA, 'transaction_id': txid, 'direction': manifest['direction'],
                             'capsule_sha256': capsule_sha, 'plan_sha256': migration.sha(encoded(plan)),
                             'start': migration.hashes(start), 'goal': migration.hashes(goal),
                             'lock_identity': lock_identity, 'contracts_sha256': contract_sha}
        if manifest != expected_manifest or contract != format_contracts():
            raise ValueError('Manifest, lock binding or format contracts differ')
        events = directory / 'events'; private_directory(events)
        names = os.listdir(events)
        if len(names) > 12 or set(names) != {f'{i:08d}.json' for i in range(len(names))}:
            raise ValueError('Journal gaps, extra files or pending publication')
        progress = start.copy()
        expected = [('PREPARED', None, migration.hashes(progress))]
        for name in changed:
            expected.append(('INTENT', name, migration.hashes(progress)))
            progress[name] = goal[name]
            expected.append(('VERIFIED', name, migration.hashes(progress)))
        expected.append(('COMPLETE', None, migration.hashes(goal)))
        if len(names) > len(expected):
            raise ValueError('Journal extends past completion')
        previous = '0' * 64
        for seq in range(len(names)):
            record, record_sha = read_document(events / f'{seq:08d}.json')
            kind, component, observed = expected[seq]
            wanted = {'seq': seq, 'previous_sha256': previous, 'transaction_id': txid,
                      'event': kind, 'component': component, 'observed_sha256': observed}
            if record != wanted or type(record.get('seq')) is not int:
                raise ValueError('Journal chain or protocol differs')
            previous = record_sha
        current, _ = read_document(directory / 'current.json')
        files = migration.decode_files(current)
        observed = migration.hashes(files)
        last = expected[len(names) - 1] if names else (None, None, migration.hashes(start))
        pending = last[1] if last[0] == 'INTENT' else None
        matches = observed == last[2]
        complete = len(names) == len(expected) and files == goal
        classification = {name: ('unchanged' if start[name] == goal[name] == files[name]
                                else 'source' if files[name] == start[name]
                                else 'target' if files[name] == goal[name] else 'unknown')
                          for name in migration.COMPONENTS}
        return {**boundary(), 'phase': ('SIMULATED_TARGET_VERIFIED' if manifest['direction'] == 'install'
                                       else 'SIMULATED_SOURCE_RESTORED') if complete else 'NEEDS_REVIEW',
                'journal_valid': True, 'journal_records': len(names), 'journal_head_sha256': previous,
                'pending_component': pending, 'current_matches_journal': matches,
                'unknown_outcome': pending is not None or not matches,
                'classification': classification, 'direction': manifest['direction']}
    except (ValueError, OSError, TypeError, KeyError, AttributeError, RecursionError):
        return {**boundary(), 'phase': 'NEEDS_REVIEW', 'journal_valid': False,
                'unknown_outcome': True, 'reason': 'invalid_or_incomplete_local_evidence'}


def inspect(directory, lock_directory):
    with session_lock(lock_directory) as identity:
        return _inspect(directory, identity)


def simulate(capsule, directory, lock_directory, *, direction='install', fault=None,
             checkpoint=lambda stage, component: None):
    """Create a fresh experiment; never continue or repair an existing directory."""
    plan, start, goal, changed = prepare(capsule, direction)
    valid_faults = {f'{name}:{stage}' for name in changed for stage in STAGES}
    valid_faults.update(f'TRANSACTION:{stage}' for stage in FINAL_STAGES)
    if fault is not None and fault not in valid_faults:
        raise ValueError('Unknown fault or unchanged component')
    def hit(stage, component):
        checkpoint(stage, component)
        if fault == f'{component}:{stage}':
            raise InjectedStop()
    with session_lock(lock_directory, create=True) as identity:
        directory = Path(directory); directory.mkdir(mode=0o700)
        sync_directory(directory.parent)
        (directory / 'events').mkdir(mode=0o700); sync_directory(directory)
        txid = uuid.uuid4().hex
        capsule_sha = durable_write(directory / 'capsule.json', capsule)
        contract_sha = durable_write(directory / 'contracts.json', format_contracts())
        durable_write(directory / 'manifest.json',
                      {'schema': SCHEMA, 'transaction_id': txid, 'direction': direction,
                       'capsule_sha256': capsule_sha, 'plan_sha256': migration.sha(encoded(plan)),
                       'start': migration.hashes(start), 'goal': migration.hashes(goal),
                       'lock_identity': identity, 'contracts_sha256': contract_sha})
        files = start.copy()
        durable_write(directory / 'current.json', {n: b.hex() for n, b in files.items()})
        previous, seq = '0' * 64, 0
        def emit(kind, component):
            nonlocal previous, seq
            record = {'seq': seq, 'previous_sha256': previous, 'transaction_id': txid,
                      'event': kind, 'component': component, 'observed_sha256': migration.hashes(files)}
            previous = durable_write(directory / 'events' / f'{seq:08d}.json', record,
                                     checkpoint=lambda stage: hit(kind.lower() + '-' + stage, component or 'TRANSACTION'))
            seq += 1
            hit('after-' + kind.lower(), component or 'TRANSACTION')
        def save_current(name):
            durable_write(directory / 'current.json', {n: b.hex() for n, b in files.items()}, replace=True,
                          checkpoint=lambda stage: hit('state-' + stage, name))
        try:
            emit('PREPARED', None)
            for name in changed:
                actual, _ = read_document(directory / 'current.json')
                if migration.decode_files(actual) != files:
                    raise ValueError('Fresh complete progress differs')
                hit('before-intent', name)
                emit('INTENT', name)  # Must fully persist before any simulated mutation.
                actual, _ = read_document(directory / 'current.json')
                if migration.decode_files(actual) != files:
                    raise ValueError('Progress changed after durable intent')
                if fault == f'{name}:partial-write':
                    altered = bytearray(files[name])
                    at = next(i for i in range(128) if files[name][i] != goal[name][i])
                    altered[at] = goal[name][at]; files[name] = bytes(altered)
                    save_current(name); hit('partial-write', name)
                files[name] = goal[name]; save_current(name)
                hit('after-write', name)
                actual, _ = read_document(directory / 'current.json')
                if migration.decode_files(actual) != files:
                    raise ValueError('Fresh complete readback differs')
                emit('VERIFIED', name)
            hit('before-complete', 'TRANSACTION')
            actual, _ = read_document(directory / 'current.json')
            if migration.decode_files(actual) != goal:
                raise ValueError('Final complete readback differs')
            emit('COMPLETE', None)
        except InjectedStop:
            pass
        return _inspect(directory, identity)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('simulate', 'inspect'):
        sub = commands.add_parser(command)
        sub.add_argument('--directory', required=True)
        sub.add_argument('--lock-directory', required=True)
        if command == 'simulate':
            sub.add_argument('--capsule', required=True)
            sub.add_argument('--direction', choices=('install', 'restore'), default='install')
            sub.add_argument('--fault')
    args = parser.parse_args(argv)
    try:
        if args.command == 'simulate':
            report = simulate(contracts.read_json(args.capsule), args.directory, args.lock_directory,
                              direction=args.direction, fault=args.fault)
        else:
            report = inspect(args.directory, args.lock_directory)
        print(encoded(report).decode(), end='')
        return 2 if report['phase'] == 'NEEDS_REVIEW' else 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        print('Offline journal stopped: ' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
