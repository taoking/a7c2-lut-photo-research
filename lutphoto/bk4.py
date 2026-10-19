"""Bounded read-only BK4 decoding; format knowledge credits Sony-PMCA-RE.

See docs/Sony-PMCA-RE-MIT.txt. No setters, device access or identity inference.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys
from types import MappingProxyType

from . import customcontracts as c
from .io import write_bytes_new

HEADER = struct.Struct('<III4s5I4xI20x32s96x32s32x')
ENTRY = struct.Struct('<HI')
MAX_IMAGE = 16 * 1024 * 1024
MAX_SNAPSHOT = 32 * 1024 * 1024
MAX_PROPERTIES = 65536
MAX_CANDIDATES = 64
MAX_SCAN_WORK = 64 * 1024 * 1024
FILES = {'ram_before': 'ram-before.bin', 'saved_before': 'saved-before.bin',
         'ram_after': 'ram-after.bin', 'saved_after': 'saved-after.bin'}


@dataclass(frozen=True)
class Property:
    attr: int
    data: bytes
    reset_data: bytes | None
    max_size: int


@dataclass(frozen=True)
class Image:
    offset: int
    size: int
    sha256: str
    records: object
    declared_properties: int
    unreferenced_properties: int


def image_header(raw, offset):
    if type(offset) is not int or offset < 0 or offset + HEADER.size > len(raw):
        raise ValueError('Truncated BK4 header')
    h = HEADER.unpack_from(raw, offset)
    subsystems, properties, data_at, data_size = h[4:8]
    total = data_at + data_size
    if (h[3] != b'BK4\0' or not 1 <= subsystems <= 65536 or not 1 <= properties <= MAX_PROPERTIES
            or data_at < HEADER.size + ENTRY.size * (subsystems + properties)
            or not HEADER.size <= total <= MAX_IMAGE or offset + total > len(raw)):
        raise ValueError('Unsupported BK4 header or extent')
    return h, total


def parse_image(raw, offset=0):
    if not isinstance(raw, bytes) or len(raw) > MAX_SNAPSHOT:
        raise ValueError('Expected bounded immutable snapshot bytes')
    h, total = image_header(raw, offset)
    view = memoryview(raw)[offset:offset + total]
    if sum(view[:32]) + sum(view[36:]) != h[8]:
        raise ValueError('BK4 additive checksum differs')
    subsystems, properties, data_at = h[4:7]
    table = HEADER.size + subsystems * ENTRY.size
    used, descriptors, spans = set(), [], []
    for group in range(subsystems):
        count, first = ENTRY.unpack_from(view, HEADER.size + group * ENTRY.size)
        if first + count > properties:
            raise ValueError('Subsystem exceeds property table')
        for local in range(count):
            index = first + local
            if index in used:
                raise ValueError('Aliased subsystem property rows are unsupported')
            used.add(index)
            attr, pointer = ENTRY.unpack_from(view, table + index * ENTRY.size)
            if pointer == 0xffffffff:
                continue
            size, start = pointer >> 24, pointer & 0xffffff
            if start < data_at or start >= total:
                raise ValueError('Property points outside data region')
            payload, maximum = start, size
            if size in (0, 255):
                prefix = 4 if size == 0 else 2
                if start + prefix > total:
                    raise ValueError('Truncated property length prefix')
                if size == 0:
                    size, maximum = struct.unpack_from('<HH', view, start)
                else:
                    size = maximum = struct.unpack_from('<H', view, start)[0]
                payload += prefix
            end = payload + maximum + (size if attr & 0x74 else 0)
            if size > maximum or end > total:
                raise ValueError('Property or reset data exceeds image')
            descriptors.append(((group << 16) | local, attr, payload, size, maximum))
            spans.append((start, end))
    # Check ownership before copying data: aliases must not amplify allocations.
    spans.sort()
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('Overlapping property storage is unsupported')
    records = {}
    for key, attr, at, size, maximum in descriptors:
        reset = bytes(view[at + maximum:at + maximum + size]) if attr & 0x74 else None
        records[key] = Property(attr, bytes(view[at:at + size]), reset, maximum)
    return Image(offset, total, hashlib.sha256(view).hexdigest(), MappingProxyType(records), properties,
                 properties - len(used))


def parse_snapshot(raw):
    if not isinstance(raw, bytes) or not 2 * HEADER.size <= len(raw) <= MAX_SNAPSHOT:
        raise ValueError('Expected bounded dual-image snapshot')
    images, cursor, candidates, work = [], 0, 0, 0
    while True:
        marker = raw.find(b'BK4\0', cursor)
        if marker < 0:
            break
        cursor = marker + 1; candidates += 1
        if candidates > MAX_CANDIDATES:
            raise ValueError('Too many BK4 candidate markers')
        try:
            _, total = image_header(raw, marker - 12)
        except ValueError:
            continue
        work += total
        if work > MAX_SCAN_WORK:
            raise ValueError('BK4 scan work limit exceeded')
        try:
            image = parse_image(raw, marker - 12)
        except ValueError:
            continue
        if any(image.offset < old.offset + old.size and old.offset < image.offset + image.size for old in images):
            raise ValueError('Overlapping valid BK4 candidates')
        images.append(image)
        if len(images) > 2:
            raise ValueError('Ambiguous extra valid BK4 image')
    if len(images) != 2:
        raise ValueError('Exactly two unambiguous valid BK4 images required')
    return tuple(images)


def boundary():
    return {'schema': 'a7c2-bk4-offline-report/1', 'private_report': True,
            'camera_operations_enabled': False, 'actual_source_identity_verified': False,
            'chip_roles_verified': False, 'body_binding_verified': False,
            'container_complete_backup_verified': False, 'outer_wrapper_verified': False,
            'descriptor_write_plan_verified': False, 'physical_validation_verified': False}


def image_summary(image):
    return {'offset': image.offset, 'bytes': image.size, 'active_properties': len(image.records),
            'declared_properties': image.declared_properties, 'unreferenced_properties': image.unreferenced_properties,
            'reset_properties': sum(p.reset_data is not None for p in image.records.values()),
            'attributes_above_8_bits': sum(p.attr > 255 for p in image.records.values())}


def inspect(raw):
    images = parse_snapshot(raw)
    return {**boundary(), 'kind': 'snapshot-format', 'input_sha256': hashlib.sha256(raw).hexdigest(),
            'raw_backup_parsed': True, 'images': [image_summary(i) for i in images],
            'unparsed_wrapper_bytes': len(raw) - sum(i.size for i in images)}


def project(images, roles):
    if (not isinstance(roles, dict) or set(roles) != {'AP', 'CP'}
            or any(type(i) is not int for i in roles.values()) or set(roles.values()) != {0, 1}):
        raise ValueError('Explicit distinct AP/CP image indices 0/1 required')
    selected = {'AP': {k: p for k, p in images[roles['AP']].records.items() if k >> 16 == 0x02cf},
                'CP': {k: p for k, p in images[roles['CP']].records.items() if k in c.devicesettings.PROTECTED}}
    if not selected['AP'] or set(selected['CP']) != set(c.devicesettings.PROTECTED):
        raise ValueError('Role assertion lacks required scoped fields')
    if any(p.attr > 255 for records in selected.values() for p in records.values()):
        raise ValueError('Unsupported high attribute bits; never truncate')
    decoded = {chip: {f'{k:08x}': {'attr': p.attr, 'data': p.data.hex()} for k, p in rows.items()}
               for chip, rows in selected.items()}
    return decoded, selected


def compare(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Plain comparison directory required')
    config = c.read_json(directory / 'case.json')
    if (not isinstance(config, dict) or set(config) != {'schema', 'roles', 'expected'}
            or config['schema'] != 'a7c2-bk4-comparison/1'):
        raise ValueError('Invalid BK4 comparison case')
    decoded, scoped, summaries = {}, {}, {}
    for state, name in FILES.items():
        raw = c.bounded_read(directory / name, MAX_SNAPSHOT)
        images = parse_snapshot(raw)
        decoded[state], scoped[state] = project(images, config['roles'])
        summaries[state] = {'sha256': hashlib.sha256(raw).hexdigest(), 'images': [image_summary(i) for i in images]}
    result = c.settings_contract({'schema': c.SETTINGS_SCHEMA, 'expected': config['expected'], **decoded})
    base = scoped['ram_before']
    for other in scoped.values():
        for chip, rows in base.items():
            if rows.keys() != other[chip].keys():
                raise ValueError('Scoped field set changed')
            for key, p in rows.items():
                q = other[chip][key]
                if (p.attr, p.max_size, len(p.data), p.reset_data) != (q.attr, q.max_size, len(q.data), q.reset_data):
                    raise ValueError('Scoped reset data or allocation layout changed')
    return {**boundary(), 'kind': 'four-snapshot-comparison', 'raw_backup_parsed': True,
            'roles_are_caller_assertions': True, 'scope_projection_only': True,
            'scoped_reset_and_layout_preserved': True, 'snapshots': summaries,
            'settings_contract': result}


def fixture_image(properties):
    """Generate own BK4-format data only; never modify parsed input."""
    if not properties or any(type(k) is not int or not 0 <= k <= 0xfffffffe or k & 0xffff == 65535 for k in properties):
        raise ValueError('Invalid fixture property IDs')
    groups = {}
    for key in properties:
        groups[key >> 16] = max(groups.get(key >> 16, 0), (key & 0xffff) + 1)
    subsystems, count = max(groups) + 1, sum(groups.values())
    if subsystems > 65536 or count > MAX_PROPERTIES:
        raise ValueError('Fixture table count exceeds limit')
    table = HEADER.size + subsystems * ENTRY.size
    data_at = (table + count * ENTRY.size + 3) & ~3
    raw = bytearray(data_at)
    for i in range(count): ENTRY.pack_into(raw, table + i * ENTRY.size, 0, 0xffffffff)
    first = 0
    for group in range(subsystems):
        number = groups.get(group, 0); ENTRY.pack_into(raw, HEADER.size + group * ENTRY.size, number, first)
        for local in range(number):
            p = properties.get((group << 16) | local)
            if p is None: continue
            size = len(p.data)
            if (type(p.attr) is not int or not 0 <= p.attr <= 65535 or not size <= p.max_size <= 65535
                    or (p.reset_data is not None) != bool(p.attr & 0x74)
                    or p.reset_data is not None and len(p.reset_data) != size):
                raise ValueError('Invalid fixture value/reset layout')
            start = len(raw)
            if size != p.max_size or size == 0:
                code = 0; raw.extend(struct.pack('<HH', size, p.max_size))
            elif size >= 255:
                code = 255; raw.extend(struct.pack('<H', size))
            else: code = size
            raw.extend(p.data); raw.extend(bytes(p.max_size - size))
            if p.reset_data is not None: raw.extend(p.reset_data)
            ENTRY.pack_into(raw, table + (first + local) * ENTRY.size, p.attr, (code << 24) | start)
        first += number
    if len(raw) > MAX_IMAGE:
        raise ValueError('Fixture image exceeds limit')
    HEADER.pack_into(raw, 0, 0x544e5953, 0, 1, b'BK4\0', subsystems, count, data_at, len(raw) - data_at,
                     0, 0, b'SYNTHETIC BK4 format', b'TESTDATA')
    struct.pack_into('<I', raw, 32, sum(raw[:32]) + sum(raw[36:]))
    return bytes(raw)


def synthetic_snapshot(after=False):
    ap = {0x02cf0001: Property(0, b'\0' if after else b'\1', None, 1),
          0x02cf0002: Property(8, b'\1\0\0\0', None, 4),
          0x02cf0b6e: Property(64, bytes([2 if after else 1]) + bytes(3), bytes(4), 4),
          0x02770015: Property(0, b'\2' if after else b'\1', None, 1),
          0x02770016: Property(1, bytes(range(256)) + bytes(44), None, 300)}
    cp = {key: Property(2, b'CPTEST' + bytes([i, 0]), None, 16) for i, key in enumerate(c.devicesettings.PROTECTED)}
    return b'SYNTHETIC CONTAINER\0' + fixture_image(ap) + bytes(16) + fixture_image(cp) + b'END'


def fixtures(directory):
    directory = Path(directory); directory.mkdir()
    created = []
    try:
        config = {'schema': 'a7c2-bk4-comparison/1', 'roles': {'AP': 0, 'CP': 1}, 'expected': {'02cf0001': '00'}}
        for state, name in FILES.items():
            path = directory / name; write_bytes_new(path, synthetic_snapshot(state.endswith('after'))); created.append(path)
        path = directory / 'case.json'; write_bytes_new(path, (json.dumps(config, indent=2) + '\n').encode()); created.append(path)
    except BaseException:
        for path in reversed(created): path.unlink()
        directory.rmdir()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    fixture = commands.add_parser('fixtures'); fixture.add_argument('--directory', required=True)
    check = commands.add_parser('inspect'); check.add_argument('--input', required=True); check.add_argument('--output', required=True)
    comparison = commands.add_parser('compare'); comparison.add_argument('--directory', required=True); comparison.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'fixtures': fixtures(args.directory)
        else:
            if Path(args.output).exists() or Path(args.output).is_symlink(): raise ValueError('Output exists')
            result = inspect(c.bounded_read(args.input, MAX_SNAPSHOT)) if args.command == 'inspect' else compare(args.directory)
            write_bytes_new(args.output, (json.dumps(result, indent=2, allow_nan=False) + '\n').encode())
        print('Offline BK4 check completed; roles/body/device remain unverified')
        return 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError, struct.error) as exc:
        print('Offline BK4 check rejected: ' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
