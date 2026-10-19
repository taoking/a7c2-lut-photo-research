"""Read-only pinned AP/CP identity and descriptor checks; no device or planner.

Rules derive from QAQLeonard's fixed device_layout/six/devicesettings sources.
See ACKNOWLEDGEMENTS.md and lutphoto/_vendor/sonycontracts/LICENSE.txt.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import zipfile

from . import workercontracts as w
from .io import write_bytes_new

MAX_PROGRAM = 128 * 1024 * 1024


@dataclass(frozen=True)
class _Window:
    at: int
    data: bytes


@dataclass(frozen=True)
class _Source:
    kind: str
    ap_bytes: int
    ap_sha: str
    cp_bytes: int
    cp_sha: str
    restore: tuple


@dataclass(frozen=True)
class _Policy:
    sources: tuple
    templates: tuple
    title: bytes
    mapping: bytes
    legacy_ap: str
    legacy_code: str
    standalone_code: str
    commit: str
    archive_sha: str
    hook_at: int = 0x35287f0
    title_at: int = 0x1b5cd7c
    map_at: int = 0x4c7cf7c
    labels_at: int = 0x59896f0
    label_stride: int = 0xb8
    descriptors_at: int = 0x57c6710
    table_at: int = 0x8000
    table_bytes: int = 1215
    magic: int = 0x364c3741
    version: int = 0x10006


@dataclass(frozen=True)
class _Field:
    slot: int
    key: int
    size: int
    reference: int | None


@dataclass(frozen=True)
class _Bindings:
    slots: tuple
    fields: tuple
    references: tuple


def _load_policy(archive):
    pin, sources = w.load_sources(archive)
    checked = w.catalog(sources)
    asset = json.loads(sources['src/looks/assets/runtime-v1.json'])
    pairs = []
    for ap in asset['ap_sources']:
        cp = next(s for s in asset['cp_sources'] if s['kind'] == ap['kind'])
        pairs.append(_Source(ap['kind'], ap['bytes'], ap['sha256'], cp['bytes'], cp['sha256'],
                     tuple(_Window(row['offset'], bytes.fromhex(row['hex'])) for row in ap['restore'])))
    return _Policy(tuple(pairs), tuple(bytes.fromhex(t) for t in asset['ap_templates']),
                   bytes.fromhex(asset['title_branch']), bytes.fromhex(asset['map']),
                   checked['legacy_six']['AP_sha256'], checked['legacy_six']['normalized_CP_code_sha256'],
                   asset['cp_code_sha256'], pin['commit'], pin['archive_sha256'])


def _hash_after(raw, windows):
    """Hash a complete virtual reconstruction without allocating a program copy."""
    digest, cursor = hashlib.sha256(), 0
    for row in sorted(windows, key=lambda r: r.at):
        if type(row.at) is not int or row.at < cursor or not row.data or row.at + len(row.data) > len(raw):
            raise ValueError('Invalid or overlapping identity window')
        digest.update(memoryview(raw)[cursor:row.at]); digest.update(row.data)
        cursor = row.at + len(row.data)
    digest.update(memoryview(raw)[cursor:])
    return digest.hexdigest()


def _target_windows(policy, mask):
    if type(mask) is not int or not 1 <= mask <= 63:
        raise ValueError('Nonzero six-slot mask required')
    return (_Window(policy.hook_at, policy.templates[mask]), _Window(policy.title_at, policy.title),
            _Window(policy.map_at, policy.mapping),
            *(_Window(policy.labels_at + i * policy.label_stride, struct.pack('<I', 0x0200ab2c + i))
              for i in range(6) if mask & (1 << i)))


def _matches_reconstruction(raw, restore, targets):
    # Outside restore windows the restored source is the input itself. Its full
    # digest was checked first. Reapply targets inside these windows and compare
    # every restored byte, including unselected labels; no ignored AP ranges.
    remaining = list(targets)
    for row in restore:
        expected = bytearray(row.data)
        for target in tuple(remaining):
            if row.at <= target.at and target.at + len(target.data) <= row.at + len(row.data):
                at = target.at - row.at; expected[at:at + len(target.data)] = target.data
                remaining.remove(target)
        if memoryview(raw)[row.at:row.at + len(row.data)] != expected:
            return False
    if remaining:
        raise ValueError('Target outside pinned reconstruction windows')
    return True


def _fnv(raw):
    value = 2166136261
    for byte in raw:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value


def _tables(cp, policy):
    start = policy.table_at
    if len(cp) < start + 32 + 6 * policy.table_bytes:
        raise ValueError('Truncated six-table storage')
    header = struct.unpack_from('<8I', cp, start)
    if header[:2] != (policy.magic, policy.version):
        raise ValueError('Unsupported six-table header')
    for i in range(6):
        raw = cp[start + 32 + i * policy.table_bytes:start + 32 + (i + 1) * policy.table_bytes]
        # Native decode uses signed int8, restricted to -64..63, plane-major.
        if any(64 <= byte < 192 for byte in raw) or _fnv(raw) != header[i + 2]:
            raise ValueError('Native table value or FNV checksum differs')


def _identify(ap, cp, policy):
    if (not isinstance(ap, bytes) or not isinstance(cp, bytes)
            or len(ap) not in {s.ap_bytes for s in policy.sources}
            or len(cp) not in {s.cp_bytes for s in policy.sources}):
        raise ValueError('Complete pinned program sizes required')
    ap_sha, cp_sha = w.sha(ap), w.sha(cp)
    if ap_sha == policy.legacy_ap:
        kind, mask, first = 'legacy-six', 63, False
    else:
        kind = None
        for source in policy.sources:
            if len(ap) != source.ap_bytes:
                continue
            if ap_sha == source.ap_sha:
                kind, mask, first = source.kind, 0, True
                break
            if _hash_after(ap, source.restore) != source.ap_sha:
                continue
            template = ap[policy.hook_at:policy.hook_at + len(policy.templates[0])]
            if template not in policy.templates:
                continue
            mask = policy.templates.index(template)
            if mask and _matches_reconstruction(ap, source.restore, _target_windows(policy, mask)):
                kind, first = source.kind + '-lut', False
                break
        if kind is None:
            raise ValueError('Unsupported complete AP identity')
    if first:
        source = next(s for s in policy.sources if s.kind == kind)
        if len(cp) != source.cp_bytes or cp_sha != source.cp_sha:
            raise ValueError('Exact matching first-import AP/CP pair required')
    else:
        end = policy.table_at + 32 + 6 * policy.table_bytes
        normalized = _hash_after(cp, (_Window(policy.table_at + 8, bytes(end - policy.table_at - 8)),))
        expected = policy.legacy_code if kind == 'legacy-six' else policy.standalone_code
        if normalized != expected:
            raise ValueError('Unsupported complete normalized CP code identity')
        _tables(cp, policy)
    return {'kind': kind, 'mask': mask, 'first_import': first,
            'layout': 'full7-v4' if kind == 'legacy-six' else 'standalone-v1',
            'AP_sha256': ap_sha, 'CP_sha256': cp_sha}


def _descriptor_bindings(ap, slots, policy):
    if (not isinstance(slots, (tuple, list)) or not slots
            or any(type(s) is not int or s not in range(1, 7) for s in slots) or len(set(slots)) != len(slots)):
        raise ValueError('Select distinct slots 1..6')
    def descriptor(attribute, base=False):
        at = policy.descriptors_at + (attribute - 0x14ea) * 32
        if at < 0 or at + 32 > len(ap):
            raise ValueError('Truncated descriptor row')
        row = struct.unpack_from('<8I', ap, at)
        if (row[6] != attribute or row[1] >> 16 != 0x02cf or row[1] == 0x02cf0b6e
                or row[0] != (3 if base else 0) or row[2] != (0x10000 if base else 0x40000)):
            raise ValueError('Descriptor identity/group/type/layout differs')
        return row[1]
    references = tuple(descriptor(0x1520 + i * 18) for i in range(8))
    selected = []
    for slot in sorted(slots):
        selector = slot + 9
        selected.append(_Field(slot, descriptor(0x14ea + selector, base=True), 1, None))
        selected.extend(_Field(slot, descriptor(0x1520 + i * 18 + selector), 4, references[i]) for i in range(8))
    keys = [f.key for f in selected]
    if len(set(references)) != 8 or len(set(keys)) != len(keys) or set(keys) & set(references):
        raise ValueError('Aliased selected or ST descriptor keys')
    return _Bindings(tuple(sorted(slots)), tuple(selected), references)


def _descriptor_summary(bindings):
    return {'selected_slots': list(bindings.slots), 'selected_fields': len(bindings.fields),
            'ST_reference_fields': len(bindings.references), 'unique_rows_checked': len(bindings.fields) + len(bindings.references),
            'row_shape_verified': True, 'setting_values_verified': False,
            'live_descriptors_verified': False, 'write_plan_enabled': False}


def _descriptors(ap, slots, policy):
    return _descriptor_summary(_descriptor_bindings(ap, slots, policy))


def _boundary():
    return {**w.boundary(), 'schema': 'a7c2-program-identity-report/1', 'private_report': True,
            'body_binding_verified': False, 'chip_roles_verified': False,
            'descriptor_write_plan_verified': False, 'camera_backup_performed': False}


def requirements(archive):
    policy = _load_policy(archive)
    return {**_boundary(), 'kind': 'material-requirements', 'commit': policy.commit,
            'archive_sha256': policy.archive_sha, 'program_files_read': False,
            'programs': {'AP': {'filename': 'appFw.so', 'bytes': sorted({s.ap_bytes for s in policy.sources})},
                         'CP': {'filename': 'cpapp-b.bin', 'bytes': sorted({s.cp_bytes for s in policy.sources})}},
            'inputs_must_be_explicit_local_paths': True, 'same_capture_provenance_required_but_not_proved': True,
            'raw_programs_and_reports_must_remain_private': True, 'camera_required': False}


def _read_program(path, allowed_sizes):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size not in allowed_sizes or not 0 < before.st_size <= MAX_PROGRAM:
            raise ValueError('Expected complete regular program of pinned size')
        raw = stream.read(before.st_size + 1)
        after = os.fstat(stream.fileno())
    stable = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if len(raw) != before.st_size or stable(before) != stable(after):
        raise ValueError('Program changed during read')
    return raw


def inspect_files(archive, ap_path, cp_path, slots):
    policy = _load_policy(archive)
    ap = _read_program(ap_path, {s.ap_bytes for s in policy.sources})
    cp = _read_program(cp_path, {s.cp_bytes for s in policy.sources})
    identity = _identify(ap, cp, policy)  # Never inspect descriptors of an unknown pair.
    descriptors = _descriptors(ap, slots, policy)
    return {**_boundary(), 'kind': 'local-program-content', 'commit': policy.commit,
            'archive_sha256': policy.archive_sha, 'program_files_read': True,
            'local_program_content_verified': True, 'same_capture_provenance_verified': False,
            'identity': identity, 'descriptors': descriptors,
            'program_bytes_in_report': False, 'descriptor_keys_or_values_in_report': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('requirements', 'inspect'):
        command = commands.add_parser(name)
        command.add_argument('--archive', required=True); command.add_argument('--output', required=True)
        if name == 'inspect':
            command.add_argument('--ap', required=True); command.add_argument('--cp', required=True)
            command.add_argument('--slots', type=int, nargs='+', required=True)
    args = parser.parse_args(argv)
    try:
        if Path(args.output).exists() or Path(args.output).is_symlink():
            raise ValueError('Output exists')
        result = (requirements(args.archive) if args.command == 'requirements' else
                  inspect_files(args.archive, args.ap, args.cp, args.slots))
        write_bytes_new(args.output, (json.dumps(result, indent=2, allow_nan=False) + '\n').encode())
        print('Read-only program check completed; body/settings/device remain unverified')
        return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration, struct.error, zipfile.BadZipFile) as exc:
        print('Read-only program check rejected: ' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
