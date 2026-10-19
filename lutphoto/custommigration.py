"""Synthetic-only N3 transactions. No firmware paths, device I/O or live adapters."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

from .io import write_bytes_new

COMPONENTS = ('AP', 'CP', 'NAMES', 'SETTINGS_RAM', 'SETTINGS_SAVED')
ORDER = ('NAMES', 'CP', 'AP', 'SETTINGS_RAM', 'SETTINGS_SAVED')
STATES = ('S0', 'S1', 'S2', 'S3')
MAGIC = b'A7C2-SYNTHETIC\0'
FAULTS = ('before-intent', 'after-intent', 'partial-write', 'after-write', 'readback-corrupt')
MAX_JSON = 128*1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(data):
    return (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()


def read_capsule(path):
    with Path(path).open('rb') as f:
        raw = f.read(MAX_JSON+1)
    if len(raw) > MAX_JSON:
        raise ValueError('Simulation input exceeds 128 KiB')
    def unique(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise ValueError('Duplicate JSON key')
            data[key] = value
        return data
    def invalid(value):
        raise ValueError('Nonfinite JSON number')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid)
    except (UnicodeError, RecursionError) as e:
        raise ValueError('Invalid simulation JSON') from e


def blob(name, state):
    raw = bytearray(128)
    header = MAGIC+name.encode('ascii')
    raw[:len(header)] = header
    if name in ('AP', 'CP'):
        raw[32:40] = state.encode().ljust(8, b'_')
    if name == 'AP':
        raw[48] = {'S0': 0, 'S1': 0, 'S2': 63, 'S3': 1}[state]
    for slot in range(6):
        if name == 'CP':
            raw[64+slot*8:72+slot*8] = (state+str(slot+1)).encode().ljust(8, b'_')
        elif name == 'NAMES':
            raw[32+slot*12:44+slot*12] = ('look'+str(slot+1)).encode().ljust(12, b' ')
        elif name.startswith('SETTINGS_'):
            raw[32+slot*2:34+slot*2] = b'NT'
    raw[120] = 0x5a  # An unrelated byte that must remain intact.
    return bytes(raw)


def decode_files(values):
    if not isinstance(values, dict) or set(values) != set(COMPONENTS):
        raise ValueError('All five synthetic components required')
    result = {}
    for name, text in values.items():
        if not isinstance(text, str) or len(text) != 256 or not re.fullmatch('[0-9a-f]{256}', text):
            raise ValueError('Only 128-byte lowercase-hex synthetic components accepted')
        raw = bytes.fromhex(text)
        if raw[:32] != blob(name, 'S0')[:32]:
            raise ValueError('Synthetic component marker differs; real firmware is not accepted')
        result[name] = raw
    return result


def hashes(files):
    return {name: sha(raw) for name, raw in files.items()}


def identify(files):
    matches = [state for state in STATES if all(files[name] == blob(name, state) for name in ('AP', 'CP'))]
    if len(matches) != 1:
        raise ValueError('Unknown or mixed synthetic AP/CP identity; no migration allowed')
    return matches[0]


def transition(before, after):
    """Derive disjoint changed spans; callers must still review their allowed scope."""
    result = {}
    for name in COMPONENTS:
        old, new = before[name], after[name]
        if len(old) != len(new) or len(old) != 128:
            raise ValueError('Synthetic component cannot resize')
        windows, start = [], None
        for i in range(len(old)+1):
            differs = i < len(old) and old[i] != new[i]
            if differs and start is None:
                start = i
            if not differs and start is not None:
                windows.append({'offset': start, 'before_hex': old[start:i].hex(), 'after_hex': new[start:i].hex()})
                start = None
        result[name] = {'bytes': len(old), 'before_sha256': sha(old), 'after_sha256': sha(new), 'windows': windows}
    return {'schema': 'a7c2-synthetic-transition/1', 'simulation_only': True, 'files': result}


def apply_one(raw, spec):
    if type(spec.get('bytes')) is not int or spec['bytes'] != 128 or len(raw) != 128 or sha(raw) != spec.get('before_sha256'):
        raise ValueError('Complete synthetic source size/hash differs')
    windows = spec.get('windows')
    if not isinstance(windows, list) or len(windows) > 128:
        raise ValueError('Bounded windows required')
    target, last = bytearray(raw), 0
    for window in windows:
        at = window.get('offset')
        old_text, new_text = window.get('before_hex'), window.get('after_hex')
        if type(at) is not int or not isinstance(old_text, str) or not isinstance(new_text, str) or not 0 < len(old_text) == len(new_text) <= 256:
            raise ValueError('Invalid synthetic window')
        old, new = bytes.fromhex(old_text), bytes.fromhex(new_text)
        if at < last or at+len(old) > len(raw) or not len(old) or raw[at:at+len(old)] != old:
            raise ValueError('Overlapping/out-of-bounds window or before bytes differ')
        target[at:at+len(old)] = new
        last = at+len(old)
    if sha(target) != spec.get('after_sha256'):
        raise ValueError('Complete synthetic target hash differs')
    return bytes(target)


def apply(files, manifest):
    if manifest.get('schema') != 'a7c2-synthetic-transition/1' or manifest.get('simulation_only') is not True or set(manifest.get('files', {})) != set(COMPONENTS) or set(files) != set(COMPONENTS):
        raise ValueError('Only complete synthetic transition schema accepted')
    # Validate every component before returning any target; never mutate caller buffers.
    return {name: apply_one(files[name], manifest['files'][name]) for name in COMPONENTS}


def prepare(capsule):
    if not isinstance(capsule, dict) or capsule.get('schema') != 'a7c2-custom-migration-simulation/1' or capsule.get('material_kind') != 'synthetic':
        raise ValueError('Synthetic simulation capsule required; no live adapter is enabled')
    if capsule.get('model') != 'ILCE-7CM2' or capsule.get('firmware') != '2.01':
        raise ValueError('Simulation model/firmware contract differs')
    body = capsule.get('body_token')
    if not isinstance(body, str) or not re.fullmatch(r'synthetic-[a-z0-9-]{1,40}', body):
        raise ValueError('Use an explicit synthetic body token, never a camera identity')
    source = decode_files(capsule.get('source'))
    state = identify(source)
    if state != capsule.get('source_state'):
        raise ValueError('Claimed source state differs from complete synthetic AP/CP identity')
    backups = capsule.get('backups')
    if not isinstance(backups, list) or len(backups) != 2:
        raise ValueError('Two complete synthetic backup records required')
    media = set()
    for record in backups:
        token = record.get('storage_token')
        if not isinstance(token, str) or not re.fullmatch(r'synthetic-media-[A-Z0-9-]{1,20}', token) or token in media or record.get('body_token') != body:
            raise ValueError('Backup body/storage tokens differ or are duplicated')
        media.add(token)
        if decode_files(record.get('files')) != source:
            raise ValueError('Complete synthetic backup readback differs')
    replacements = capsule.get('replacements')
    if not isinstance(replacements, dict) or not 1 <= len(replacements) <= 6 or any(key not in ('1', '2', '3', '4', '5', '6') for key in replacements):
        raise ValueError('Select distinct synthetic slots 1..6')
    target = {name: bytearray(raw) for name, raw in source.items()}
    selected_bytes = {32+(int(key)-1)*2+j for key in replacements for j in (0, 1)}
    if any(source['SETTINGS_RAM'][i] != source['SETTINGS_SAVED'][i]
           for i in range(32, 128) if i not in selected_bytes):
        raise ValueError('Unselected unsaved settings would be persisted')
    target['AP'][32:40] = b'S3______'
    if state in ('S0', 'S1'):
        target['CP'][32:40] = b'S3______'
    for key, replacement in replacements.items():
        slot = int(key)-1
        table, title = replacement.get('table_hex'), replacement.get('name')
        if not isinstance(table, str) or not re.fullmatch('[0-9a-f]{16}', table) or not isinstance(title, str) or not re.fullmatch('[A-Za-z0-9 _-]{1,12}', title):
            raise ValueError('Toy tables contain eight bytes; toy titles contain 1..12 ASCII characters')
        target['AP'][48] |= 1 << slot
        target['CP'][64+slot*8:72+slot*8] = bytes.fromhex(table)
        target['NAMES'][32+slot*12:44+slot*12] = title.encode().ljust(12, b' ')
        for name in ('SETTINGS_RAM', 'SETTINGS_SAVED'):
            target[name][32+slot*2:34+slot*2] = b'ST'
    target = {name: bytes(raw) for name, raw in target.items()}
    forward, reverse = transition(source, target), transition(target, source)
    if apply(source, forward) != target or apply(target, reverse) != source:
        raise ValueError('Complete forward/reverse simulation differs')
    plan = {'schema': 'a7c2-custom-simulation-plan/1', 'simulation_only': True,
            'source_state': state, 'selected_slots': sorted(map(int, replacements)),
            'before': hashes(source), 'after': hashes(target), 'forward': forward, 'reverse': reverse,
            'complete_inverse_verified_in_memory': True,
            'backup_copies_verified_in_memory': 2, 'independent_media_verified': False,
            'real_layout_adapters_enabled': [], 'camera_operations_enabled': False,
            'settings_scope': 'five toy buffers only; not Sony backup units or 68 UXC resources'}
    return plan, source, target


class Simulation:
    def __init__(self, capsule, direction='install'):
        if direction not in ('install', 'restore'):
            raise ValueError('Simulation direction must be install or restore')
        self.plan, source, target = prepare(capsule)
        self.direction = direction
        self.start, self.goal = (source, target) if direction == 'install' else (target, source)
        self.files = self.start.copy()
        self.phase, self.journal, self.writes = 'PREPARED', [], 0
        self.unknown = False

    def classify(self):
        classes = {}
        for name, raw in self.files.items():
            if raw == self.start[name] == self.goal[name]:
                classes[name] = 'unchanged'
            elif raw == self.start[name]:
                classes[name] = 'source'
            elif raw == self.goal[name]:
                classes[name] = 'target'
            else:
                classes[name] = 'unknown'
        return classes

    def report(self):
        return {'schema': 'a7c2-custom-simulation-result/1', 'simulation_only': True,
                'direction': self.direction, 'phase': self.phase, 'unknown_outcome': self.unknown,
                'plan_sha256': sha(encoded(self.plan)), 'writes_simulated': self.writes,
                'journal': copy.deepcopy(self.journal), 'classification': self.classify(),
                'current_sha256': hashes(self.files), 'automatic_retry_allowed': False,
                'automatic_restore_allowed': False, 'journal_is_durable_device_evidence': False,
                'restore_initial_state': 'computed synthetic target' if self.direction == 'restore' else None,
                'camera_operations_enabled': False, 'physical_validation_verified': False}

    def execute(self, fault=None):
        if self.phase != 'PREPARED':
            raise ValueError('Simulation already started; unknown/finished actions cannot be replayed')
        selected = None
        if fault is not None:
            if not isinstance(fault, str) or fault.count(':') != 1:
                raise ValueError('Fault requires COMPONENT:stage')
            component, stage = fault.split(':')
            if component not in COMPONENTS or stage not in FAULTS:
                raise ValueError('Unknown fault component/stage')
            if self.start[component] == self.goal[component]:
                raise ValueError('Cannot inject a write fault into an unchanged component')
            selected = component, stage
        manifest = self.plan['forward' if self.direction == 'install' else 'reverse']
        if apply(self.files, manifest) != self.goal:
            raise ValueError('Fresh complete preflight differs')
        self.phase = 'PREFLIGHT_VERIFIED'
        self.journal.append({'event': 'complete_preflight_verified'})
        completed = set()
        def stop(name, stage):
            if selected != (name, stage):
                return False
            self.phase = 'NEEDS_REVIEW'; self.unknown = stage != 'before-intent'
            self.journal.append({'event': 'injected_stop', 'component': name, 'stage': stage})
            return True
        order = ORDER if self.direction == 'install' else tuple(reversed(ORDER))
        for name in order:
            if self.start[name] == self.goal[name]:
                continue
            expected = {n: self.goal[n] if n in completed else self.start[n] for n in COMPONENTS}
            if self.files != expected:
                raise ValueError('Fresh full progress readback differs')
            if stop(name, 'before-intent'):
                return self.report()
            self.phase = name+'_WRITE_INTENT'
            self.journal.append({'event': 'write_intent', 'component': name,
                                 'before_sha256': sha(self.files[name]), 'after_sha256': sha(self.goal[name])})
            if stop(name, 'after-intent'):
                return self.report()
            if selected == (name, 'partial-write'):
                window = manifest['files'][name]['windows'][0]
                part = bytes.fromhex(window['after_hex']); count = max(1, len(part)//2)
                changed = bytearray(self.files[name]); at = window['offset']
                changed[at:at+count] = part[:count]; self.files[name] = bytes(changed); self.writes += 1
                stop(name, 'partial-write')
                return self.report()
            self.files[name] = apply_one(self.files[name], manifest['files'][name]); self.writes += 1
            if stop(name, 'after-write'):
                return self.report()
            if selected == (name, 'readback-corrupt'):
                changed = bytearray(self.files[name]); changed[120] ^= 1; self.files[name] = bytes(changed)
                stop(name, 'readback-corrupt')
                return self.report()
            if self.files[name] != self.goal[name]:
                raise ValueError('Complete component readback differs')
            completed.add(name)
            self.journal.append({'event': 'complete_component_verified', 'component': name})
        if self.files != self.goal:
            raise ValueError('Complete transaction readback differs')
        self.phase = 'SIMULATED_TARGET_VERIFIED' if self.direction == 'install' else 'SIMULATED_SOURCE_RESTORED'
        return self.report()


def fixtures(directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    for state in STATES:
        source = {name: blob(name, state).hex() for name in COMPONENTS}
        capsule = {'schema': 'a7c2-custom-migration-simulation/1', 'material_kind': 'synthetic',
                   'model': 'ILCE-7CM2', 'firmware': '2.01', 'body_token': 'synthetic-body-1',
                   'source_state': state, 'source': source,
                   'replacements': {'2': {'table_hex': '0102030405060708', 'name': 'Demo Look'}},
                   'backups': [{'body_token': 'synthetic-body-1', 'storage_token': 'synthetic-media-'+m,
                                'files': source} for m in ('A', 'B')]}
        write_bytes_new(directory/(state+'.json'), encoded(capsule))
    return {'simulation_only': True, 'cases': list(STATES), 'camera_operations_enabled': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('fixtures'); demo.add_argument('--directory', type=Path, required=True)
    for name in ('plan', 'simulate'):
        command = commands.add_parser(name)
        command.add_argument('--capsule', type=Path, required=True); command.add_argument('--output', type=Path, required=True)
        if name == 'simulate':
            command.add_argument('--direction', choices=('install', 'restore'), default='install')
            command.add_argument('--fault')
    args = parser.parse_args(argv)
    try:
        if args.command == 'fixtures':
            result = fixtures(args.directory)
        else:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError('Output already exists')
            capsule = read_capsule(args.capsule)
            result = prepare(capsule)[0] if args.command == 'plan' else Simulation(capsule, args.direction).execute(args.fault)
            write_bytes_new(args.output, encoded(result))
        print(encoded(result).decode(), end='')
        return 2 if result.get('phase') == 'NEEDS_REVIEW' else 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as e:
        print('STOPPED: '+str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
