"""Bounded offline UXC/settings contracts, never a device migration planner."""
import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys

from ._vendor.sonycontracts import devicesettings, resources
from .io import write_bytes_new

MAX_RESOURCE = 1024 * 1024
MAX_JSON = 2 * 1024 * 1024
MAX_RECORDS = 4096
MAX_VALUE = 65535
LAYOUTS = {'standalone': tuple(range(0x0200ab2c, 0x0200ab32)),
           'legacy-six': resources.LABEL_IDS}
RESOURCE_FILES = tuple(json.loads(Path(resources.__file__).with_name('resource-files.json').read_text()))
SETTINGS_SCHEMA = 'a7c2-decoded-settings-contract/1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded_read(path, limit):
    """Reject links, non-regular files and growth beyond the declared limit."""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('Input must be a bounded regular file')
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Input exceeds size limit')
    return raw


def read_json(path):
    return decode_json(bounded_read(path, MAX_JSON))


def decode_json(raw):
    """Decode the exact bounded bytes that callers may also fingerprint."""
    if not isinstance(raw, bytes) or len(raw) > MAX_JSON:
        raise ValueError('Expected bounded JSON bytes')
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def finite(value):
        raise ValueError('Non-finite JSON value')
    try:
        result = json.loads(raw.decode('utf-8'),
                            object_pairs_hook=unique, parse_constant=finite)
        pending = [(result, 0)]; visited = 0
        while pending:
            value, depth = pending.pop(); visited += 1
            if depth > 32 or visited > 100000 or isinstance(value, float) and not math.isfinite(value):
                raise ValueError('JSON nesting, item or finite number limit exceeded')
            children = value.values() if isinstance(value, dict) else value if isinstance(value, list) else ()
            pending.extend((child, depth + 1) for child in children)
        return result
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid JSON encoding or nesting') from exc


def decode_resource(raw):
    if not isinstance(raw, bytes) or not 16 <= len(raw) <= MAX_RESOURCE:
        raise ValueError('Resource size outside bounds')
    value = resources.decode(raw)
    if value['group'] != 5 or value['count'] not in (2860, 2866):
        raise ValueError('Unsupported name resource layout')
    spans = []
    for entry in value['entries'].values():
        start = value['data_base'] + entry['pointer'] * 4
        end = raw.find(b'\0', start + 4) + 1
        spans.append((start, end))
    spans.sort()
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('Overlapping resource records')
    if value['count'] == 2866 and not set(LAYOUTS['standalone']) <= value['entries'].keys():
        raise ValueError('Imported name ID missing')
    return value


def names_checked(names):
    if not isinstance(names, dict) or not names:
        raise ValueError('Select name slots 1..6')
    for slot, text in names.items():
        if type(slot) is not int or slot not in range(1, 7):
            raise ValueError('Select name slots 1..6')
        if not isinstance(text, str) or any(ord(c) < 32 or 127 <= ord(c) < 160 for c in text):
            raise ValueError('Name contains controls')
        try:
            size = len(text.encode('utf-8'))
        except UnicodeError as exc:
            raise ValueError('Invalid name Unicode') from exc
        if not 1 <= size <= 63:
            raise ValueError('Name must contain 1..63 UTF-8 bytes')
    return names


def resource_contract(raw, names, layout):
    """Check rename and full-byte inverse in memory; return no resource payload."""
    names_checked(names)
    if layout not in LAYOUTS:
        raise ValueError('Explicit label layout required')
    before = decode_resource(raw)
    if layout == 'legacy-six' and before['count'] != 2866:
        raise ValueError('Legacy-six requires imported labels')
    ids = LAYOUTS[layout]
    target, inverse_plan = resources.rename(raw, names, label_ids=ids)
    after = decode_resource(target)
    restored = resources.inverse(target, inverse_plan)
    if restored != raw:
        raise ValueError('Full resource inverse differs')
    for rid, entry in before['entries'].items():
        expected = names[ids.index(rid) + 1] if rid in ids and ids.index(rid) + 1 in names else entry['text']
        if after['entries'][rid]['text'] != expected:
            raise ValueError('Unselected resource changed')
    for slot, rid in enumerate(ids, 1):
        expected = names.get(slot, 'ST' if before['count'] == 2860 else before['entries'][rid]['text'])
        if after['entries'][rid]['text'] != expected:
            raise ValueError('Selected label differs')
    return {'before_sha256': digest(raw), 'after_sha256': digest(target),
            'restored_sha256': digest(restored), 'before_bytes': len(raw),
            'after_bytes': len(target), 'before_count': before['count'],
            'selected_slots': sorted(names), 'exact_inverse_verified': True}


def resource_directory(directory, names, layout):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Resource directory must be a plain directory')
    found = set()
    with os.scandir(directory) as entries:
        for entry in entries:
            found.add(entry.name)
            if len(found) > 68:
                raise ValueError('Expected exactly 68 resource files')
    if found != set(RESOURCE_FILES):
        raise ValueError('Expected exactly the pinned 68 resource filenames')
    reports = {name: resource_contract(bounded_read(directory / name, MAX_RESOURCE), names, layout)
               for name in RESOURCE_FILES}
    counts = {r['before_count'] for r in reports.values()}
    if len(counts) != 1:
        raise ValueError('Mixed resource index layouts')
    return {**boundary(), 'kind': 'resource-contract', 'files': reports,
            'label_layout_assertion': layout, 'resource_files': len(reports)}


@dataclass(frozen=True)
class Record:
    data: bytes
    attr: int


def hex_bytes(text):
    if not isinstance(text, str) or len(text) > MAX_VALUE * 2 or not re.fullmatch(r'(?:[0-9a-f]{2})*', text):
        raise ValueError('Expected bounded canonical lowercase hex')
    return bytes.fromhex(text)


def snapshot(value):
    if not isinstance(value, dict) or set(value) != {'AP', 'CP'}:
        raise ValueError('Expected decoded AP/CP snapshot')
    result = []
    for chip in ('AP', 'CP'):
        rows = value[chip]
        if not isinstance(rows, dict) or len(rows) > MAX_RECORDS:
            raise ValueError('Too many decoded settings')
        records = {}
        for key, row in rows.items():
            if not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{8}', key):
                raise ValueError('Expected canonical 32-bit setting key')
            if not isinstance(row, dict) or set(row) != {'attr', 'data'}:
                raise ValueError('Invalid decoded setting')
            if type(row['attr']) is not int or not 0 <= row['attr'] <= 255:
                raise ValueError('Invalid setting attribute')
            records[int(key, 16)] = Record(hex_bytes(row['data']), row['attr'])
        result.append(records)
    if not set(devicesettings.PROTECTED) <= result[1].keys():
        raise ValueError('Protected CP unit missing')
    return result


class StrictPreservation:
    """The filtered 02cf/CP scope needs no runtime counter exceptions."""
    @staticmethod
    def verify_preservation(before, after, expected):
        kept = 0
        for chip in (0, 1):
            if before[chip].keys() != after[chip].keys():
                raise ValueError('Preservation setting set changed')
            for key, value in before[chip].items():
                other = after[chip][key]
                data = expected.get((chip, key), value.data)
                if other.data != data or other.attr != value.attr:
                    raise ValueError('Preservation value/attribute differs')
                kept += (chip, key) not in expected
        return {'preserved_properties': kept}


def settings_contract(capsule):
    keys = {'schema', 'ram_before', 'saved_before', 'ram_after', 'saved_after', 'expected'}
    if not isinstance(capsule, dict) or set(capsule) != keys or capsule['schema'] != SETTINGS_SCHEMA:
        raise ValueError('Invalid decoded settings contract')
    states = [snapshot(capsule[k]) for k in ('ram_before', 'saved_before', 'ram_after', 'saved_after')]
    rb, sb, ra, sa = states
    supplied = capsule['expected']
    if not isinstance(supplied, dict) or not 1 <= len(supplied) <= 54:
        raise ValueError('Expected 1..54 descriptor-unbound settings')
    expected = {}
    for key, text in supplied.items():
        if not isinstance(key, str) or not re.fullmatch(r'02cf[0-9a-f]{4}', key) or int(key, 16) == devicesettings.SAVED_TELEMETRY:
            raise ValueError('Expected setting outside writable AP scope')
        number = int(key, 16); data = hex_bytes(text)
        if len(data) not in (1, 4):
            raise ValueError('Expected one-byte base or four-byte adjustment value')
        for state in states:
            value = state[0].get(number)
            if value is None or value.attr & 3 or len(value.data) != len(data):
                raise ValueError('Selected setting missing, protected or resized')
        if rb[0][number] != sb[0][number]:
            raise ValueError('Selected RAM/storage differ before import')
        expected[str(number)] = data.hex()
    # Compare RAM/storage too: catches saved-only keys and diagnostic layout drift.
    devicesettings.compare(rb, sb, {}, StrictPreservation)
    devicesettings.require_save_preserves_unsaved(rb, sb, {int(k) for k in expected})
    ram = devicesettings.compare(rb, ra, expected, StrictPreservation)
    saved = devicesettings.compare(sb, sa, expected, StrictPreservation)
    devicesettings.compare(ra, sa, {}, StrictPreservation)
    for state in states[1:]:
        devicesettings.protected_equal(rb, state)
    return {**boundary(), 'kind': 'decoded-settings-contract',
            'expected_fields': len(expected), 'ram': ram, 'saved': saved,
            'scope': {**devicesettings.PRESERVATION_SCOPE,
                      'other_runtime_groups': 'decoded only; not compared or written; no backup performed'},
            'descriptor_write_plan_verified': False, 'raw_backup_parsed': False}


def boundary():
    return {'schema': 'a7c2-offline-contract-report/1', 'camera_operations_enabled': False,
            'actual_source_identity_verified': False, 'physical_validation_verified': False,
            'camera_backup_performed': False}


def synthetic_resource(imported=False):
    """Own format fixture; no Sony resource bytes."""
    count = 2866 if imported else 2860
    raw = bytearray(b'uxc\x07\0\0\0\0' + struct.pack('<HHI', 8, 5, count | (count << 12)))
    raw.extend(b'\xff\xff' * count)
    base = len(raw)
    records = {0: 'Synthetic unrelated text'}
    if imported:
        records.update({0xb2c + i: f'Synthetic label {i+1}' for i in range(6)})
    for index, text in records.items():
        struct.pack_into('<H', raw, 16 + 2 * index, (len(raw) - base) // 4)
        raw.extend(struct.pack('<I', 0x1e00a000 + index) + text.encode() + b'\0')
        raw.extend(bytes(-len(raw) % 4))
    return bytes(raw)


def synthetic_settings():
    def state(after):
        ap = {'02cf0001': {'attr': 0, 'data': '00' if after else '01'},
              '02cf0002': {'attr': 0, 'data': '01000000'},
              '02cf0b6e': {'attr': 64, 'data': '02000000' if after else '01000000'},
              '02770015': {'attr': 0, 'data': '02' if after else '01'}}
        cp = {f'{key:08x}': {'attr': 0, 'data': '00112233'} for key in devicesettings.PROTECTED}
        return {'AP': ap, 'CP': cp}
    return {'schema': SETTINGS_SCHEMA, 'ram_before': state(False), 'saved_before': state(False),
            'ram_after': state(True), 'saved_after': state(True), 'expected': {'02cf0001': '00'}}


def fixtures(directory):
    directory = Path(directory)
    directory.mkdir()  # Exclusive reservation; never reuse an existing directory.
    created = []
    try:
        for kind, imported in (('stock', False), ('imported', True)):
            child = directory / kind; child.mkdir(); created.append(child)
            for name in RESOURCE_FILES:
                path = child / name; write_bytes_new(path, synthetic_resource(imported)); created.append(path)
        for name, value in (('names.json', {'2': 'Demo Look'}), ('settings.json', synthetic_settings())):
            path = directory / name
            write_bytes_new(path, (json.dumps(value, indent=2) + '\n').encode()); created.append(path)
    except BaseException:
        for path in reversed(created):
            path.rmdir() if path.is_dir() else path.unlink()
        directory.rmdir()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    fixture = sub.add_parser('fixtures'); fixture.add_argument('--directory', required=True)
    resource = sub.add_parser('resources')
    resource.add_argument('--directory', required=True)
    resource.add_argument('--layout', choices=LAYOUTS, required=True)
    resource.add_argument('--names', required=True); resource.add_argument('--output', required=True)
    setting = sub.add_parser('settings')
    setting.add_argument('--capsule', required=True); setting.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'fixtures':
            fixtures(args.directory)
        else:
            if args.command == 'resources':
                raw_names = read_json(args.names)
                if not isinstance(raw_names, dict) or any(k not in ('1', '2', '3', '4', '5', '6') for k in raw_names):
                    raise ValueError('Select name slots 1..6')
                report = resource_directory(args.directory, {int(k): v for k, v in raw_names.items()}, args.layout)
            else:
                report = settings_contract(read_json(args.capsule))
            write_bytes_new(args.output, (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())
        print('Offline contract completed; no camera operations')
        return 0
    except (ValueError, OSError, struct.error) as exc:
        # Do not echo paths, setting values or original resource names.
        print('Offline contract rejected: ' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
