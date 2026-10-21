"""Offline single-slot program/resource targets and scoped settings inverse.

QAQLeonard's pinned device_layout/six/devicesettings rules; ma1co BK4 parsing.
See ACKNOWLEDGEMENTS.md. No archive Python execution, USB, worker or payload
export. Full program targets exist only in memory, never as firmware files.
"""
import argparse
from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import struct
import sys
import zipfile

from . import customcontracts as c, importmaterials as m, programidentity as p, settingsbinding as s
from .capturestore import _parent, _private
from .io import write_bytes_new

SCHEMA = 'a7c2-offline-single-slot-target/1'
MAX_WINDOWS = 4096
MAX_WINDOW_BYTES = 4096


class _Arguments(ValueError): pass


class _Parser(argparse.ArgumentParser):
    def error(self, message): raise _Arguments('Invalid arguments')


@dataclass(frozen=True)
class _Change:
    at: int
    before: bytes
    after: bytes


@dataclass(frozen=True)
class _Transition:
    size: int
    before_sha: str
    after_sha: str
    changes: tuple


def _apply(raw, transition):
    """A whole-source precondition, disjoint byte preconditions and full target."""
    if (type(raw) is not bytes or type(transition) is not _Transition
            or len(raw) != transition.size or p.w.sha(raw) != transition.before_sha
            or len(transition.changes) > MAX_WINDOWS):
        raise ValueError('Complete transition source differs')
    result = bytearray(raw); end = 0
    for row in transition.changes:
        if (type(row) is not _Change or type(row.at) is not int or row.at < end
                or type(row.before) is not bytes or type(row.after) is not bytes
                or not 0 < len(row.before) == len(row.after) <= MAX_WINDOW_BYTES
                or row.at + len(row.before) > len(raw) or raw[row.at:row.at + len(row.before)] != row.before):
            raise ValueError('Invalid transition byte precondition')
        end = row.at + len(row.before); result[row.at:end] = row.after
    if p.w.sha(result) != transition.after_sha:
        raise ValueError('Complete transition target differs')
    return bytes(result)


def _inverse(transition):
    return _Transition(transition.size, transition.after_sha, transition.before_sha,
                       tuple(_Change(r.at, r.after, r.before) for r in transition.changes))


def _transition(before, after, spans):
    if type(before) is not bytes or type(after) is not bytes or len(before) != len(after):
        raise ValueError('Immutable fixed-size programs required')
    changes = []; end = 0
    for at, size in sorted(spans):
        if (type(at) is not int or type(size) is not int or at < end or not 0 < size <= MAX_WINDOW_BYTES
                or at + size > len(before)):
            raise ValueError('Invalid transition extent')
        end = at + size
        if before[at:end] != after[at:end]: changes.append(_Change(at, before[at:end], after[at:end]))
    transition = _Transition(len(before), p.w.sha(before), p.w.sha(after), tuple(changes))
    if _apply(before, transition) != after or _apply(after, _inverse(transition)) != before:
        raise ValueError('Complete forward or inverse reconstruction differs')
    return transition


def _diff_spans(before, after):
    """Pinned first-import grouping: gaps <=16, windows <=4096 bytes."""
    if len(before) != len(after): raise ValueError('Fixed-size diff required')
    spans = []; start = last = None
    for at, (old, new) in enumerate(zip(before, after)):
        if old == new: continue
        if start is None: start = at
        elif at - last > 16 or at - start >= MAX_WINDOW_BYTES:
            spans.append((start, last - start + 1)); start = at
            if len(spans) >= MAX_WINDOWS: raise ValueError('Excessive program differences')
        last = at
    if start is not None: spans.append((start, last - start + 1))
    return spans


def _runtime(archive, policy):
    pin, sources = p.w.load_sources(archive)
    p.w.catalog(sources)
    if pin['commit'] != policy.commit or pin['archive_sha256'] != policy.archive_sha:
        raise ValueError('Runtime source differs from identity policy')
    return json.loads(sources['src/looks/assets/runtime-v1.json'])


def _programs(ap, cp, slot, table, policy, runtime=None):
    if type(slot) is not int or slot not in range(1, 7): raise ValueError('One slot 1..6 required')
    if type(table) is not bytes or len(table) != policy.table_bytes or any(64 <= v < 192 for v in table):
        raise ValueError('Checked native table required')
    identity = p._identify(ap, cp, policy); first = identity['first_import']
    target_cp = bytearray(cp)
    if first:
        spec = next(r for r in runtime['cp_sources'] if r['kind'] == identity['kind'])
        for row in spec['windows']:
            at, old, new = row['offset'], bytes.fromhex(row['before']), bytes.fromhex(row['after'])
            if cp[at:at + len(old)] != old or len(old) != len(new):
                raise ValueError('Pinned bootstrap source differs')
            target_cp[at:at + len(new)] = new
        if p.w.sha(target_cp) != runtime['cp_zero_tables_sha256']:
            raise ValueError('Canonical zero-table runtime differs')
    canonical_cp = bytes(target_cp); p._tables(canonical_cp, policy)
    if first and any(canonical_cp[policy.table_at + 32:policy.table_at + 32 + 6 * policy.table_bytes]):
        raise ValueError('Canonical initial tables are not zero')
    at = policy.table_at + 32 + (slot - 1) * policy.table_bytes
    check = policy.table_at + 8 + (slot - 1) * 4
    target_cp[at:at + policy.table_bytes] = table
    struct.pack_into('<I', target_cp, check, p._fnv(table))
    for index in range(6):
        if index == slot - 1: continue
        start = policy.table_at + 32 + index * policy.table_bytes
        checksum = policy.table_at + 8 + index * 4
        if (target_cp[start:start + policy.table_bytes] != canonical_cp[start:start + policy.table_bytes]
                or target_cp[checksum:checksum + 4] != canonical_cp[checksum:checksum + 4]):
            raise ValueError('Unselected table differs')
    target_ap, ap_spans = ap, []
    mask = identity['mask'] | (1 << (slot - 1))
    if identity['kind'] != 'legacy-six':
        source = next(r for r in policy.sources if identity['kind'] in (r.kind, r.kind + '-lut'))
        original = bytearray(ap)
        for row in source.restore: original[row.at:row.at + len(row.data)] = row.data
        if p.w.sha(original) != source.ap_sha: raise ValueError('Complete AP source reconstruction differs')
        for row in p._target_windows(policy, mask): original[row.at:row.at + len(row.data)] = row.data
        target_ap = bytes(original); ap_spans = [(r.at, len(r.data)) for r in source.restore]
    target_cp = bytes(target_cp)
    target_identity = p._identify(target_ap, target_cp, policy)
    if target_identity['mask'] != mask or target_identity['first_import']:
        raise ValueError('Target identity/mask differs')
    if p._descriptor_bindings(ap, [slot], policy) != p._descriptor_bindings(target_ap, [slot], policy):
        raise ValueError('Selected descriptors changed')
    cp_spans = _diff_spans(cp, target_cp) if first else [(at, policy.table_bytes), (check, 4)]
    transitions = {'AP': _transition(ap, target_ap, ap_spans), 'CP': _transition(cp, target_cp, cp_spans)}
    return {'AP': target_ap, 'CP': target_cp}, transitions, identity, target_identity


def _scope_sha(scoped):
    value = {chip: {str(k): {'attr': v.attr, 'data': v.data.hex(), 'reset': None if v.reset_data is None else v.reset_data.hex(),
                            'max_size': v.max_size} for k, v in rows.items()} for chip, rows in scoped.items()}
    return p.w.sha(m._canonical(value))


def _settings(bindings, ram, saved, ram_scope, saved_scope):
    s._check_values(bindings, ram, saved, ram_scope, saved_scope)
    expected = {str(f.key): (bytes(1) if f.reference is None else ram[0][f.reference].data).hex() for f in bindings.fields}
    targets, scopes, summaries = [], [], {}
    for name, before, scoped in (('ram', ram, ram_scope), ('saved', saved, saved_scope)):
        target = [dict(rows) for rows in before]; target_scope = {chip: dict(rows) for chip, rows in scoped.items()}
        for field in bindings.fields:
            data = bytes.fromhex(expected[str(field.key)])
            target[0][field.key] = replace(before[0][field.key], data=data)
            target_scope['AP'][field.key] = replace(scoped['AP'][field.key], data=data)
        c.devicesettings.compare(before, target, expected, c.StrictPreservation)
        c.devicesettings.protected_equal(before, target)
        # Reverse the actual target, then compare every decoded/scoped field,
        # including attributes, reset data, allocation and volatile current data.
        restored = [dict(rows) for rows in target]; restored_scope = {chip: dict(rows) for chip, rows in target_scope.items()}
        for field in bindings.fields:
            if target[0][field.key].data.hex() != expected[str(field.key)]: raise ValueError('Setting target differs')
            restored[0][field.key] = before[0][field.key]
            restored_scope['AP'][field.key] = scoped['AP'][field.key]
        if restored != before or restored_scope != scoped: raise ValueError('Scoped settings inverse differs')
        summaries[name] = {'before_scoped_sha256': _scope_sha(scoped), 'target_scoped_sha256': _scope_sha(target_scope),
                           'restored_scoped_sha256': _scope_sha(restored_scope), 'exact_scoped_inverse_verified': True,
                           'unchanged_AP_properties': len(scoped['AP']) - len(bindings.fields), 'protected_CP_units_preserved': 4}
        targets.append(target); scopes.append(target_scope)
    after = s._check_values(bindings, *targets, *scopes)
    if not after['all_selected_fields_equal_ST']: raise ValueError('Target fields do not match ST')
    return targets, scopes, {'selected_fields': len(bindings.fields), 'all_selected_fields_equal_ST': True,
                            'scoped_reset_attributes_allocation_and_unselected_preserved': True, 'snapshots': summaries,
                            'full_BK4_target_generated': False, 'complete_settings_transition_verified': False,
                            'other_runtime_groups_compared': False}


def check_files(archive, ap_path, cp_path, ram_path, saved_path, selection_path, resources_path, ram_roles, saved_roles):
    rows, selection_sha = m._selection(selection_path)
    if len(rows) != 1: raise ValueError('Exactly one selected slot required')
    slot, (relative, name) = next(iter(rows.items()))
    policy = p._load_policy(archive)
    ap = p._read_program(ap_path, {r.ap_bytes for r in policy.sources})
    cp = p._read_program(cp_path, {r.cp_bytes for r in policy.sources})
    identity = p._identify(ap, cp, policy); bindings = p._descriptor_bindings(ap, [slot], policy)
    ram, ram_scope, ram_report = s._snapshot(ram_path, dict(ram_roles))
    saved, saved_scope, saved_report = s._snapshot(saved_path, dict(saved_roles))
    values = s._check_values(bindings, ram, saved, ram_scope, saved_scope)
    candidate, table = m._candidate_content(m._relative_directory(Path(selection_path).parent, relative), policy.commit)
    _, transitions, _, target_identity = _programs(ap, cp, slot, table, policy,
                                                       _runtime(archive, policy) if identity['first_import'] else None)
    _, _, settings = _settings(bindings, ram, saved, ram_scope, saved_scope)
    resources = {}; counts = set(); layout = m._layout(identity)
    for path in c._resource_files(resources_path):
        raw = c.bounded_read(path, c.MAX_RESOURCE)
        report, target, inverse = c._resource_target(raw, {slot: name}, layout)
        # Bind the inverse to this exact target, not a subsequently reread file.
        if c.resources.inverse(target, inverse) != raw: raise ValueError('Resource inverse differs')
        resources[path.name] = report; counts.add(report['before_count'])
    if len(counts) != 1: raise ValueError('Mixed resource index layouts')
    programs = {chip: {'bytes': t.size, 'before_sha256': t.before_sha, 'target_sha256': t.after_sha,
                       'restored_sha256': p.w.sha(ap if chip == 'AP' else cp),
                       'window_count': len(t.changes), 'window_bytes': sum(len(r.before) for r in t.changes),
                       'exact_forward_and_inverse_verified': True} for chip, t in transitions.items()}
    material = {'commit': policy.commit, 'archive_sha256': policy.archive_sha, 'selected_slot': slot,
                'selection_sha256': selection_sha, 'name_utf8_sha256': p.w.sha(name.encode()), 'candidate': candidate,
                'source_identity': identity, 'target_identity': target_identity, 'programs': programs,
                'input_snapshots': {'ram': ram_report, 'saved': saved_report}, 'input_values': values,
                'settings': settings, 'label_layout_derived_from_program': layout, 'resources': resources,
                'unselected_table_reference': 'canonical-zero-runtime' if identity['first_import'] else 'input-program',
                'unselected_tables_and_checksums_preserved': 5}
    return {**p._boundary(), 'schema': SCHEMA, **material, 'target_review_sha256': p.w.sha(m._canonical(material)),
            'complete_program_transition_verified': True, 'scoped_settings_transition_verified': True,
            'complete_settings_transition_verified': False, 'resource_inverse_checked_in_memory': True,
            'same_capture_provenance_verified': False, 'snapshot_freshness_verified': False,
            'resource_origin_and_capture_verified': False, 'chip_roles_are_caller_assertions': True,
            'independent_backups_verified': False, 'native_worker_generated': False, 'camera_deployment_enabled': False,
            'firmware_or_settings_write_plan_enabled': False, 'payloads_exported': False,
            'private_paths_names_keys_values_or_windows_in_report': False}


def main(argv=None):
    parser = _Parser(description=__doc__, allow_abbrev=False)
    for name in ('archive', 'ap', 'cp', 'ram', 'saved', 'selection', 'resources', 'output'):
        parser.add_argument('--' + name, required=True)
    for name in ('ram', 'saved'):
        parser.add_argument('--' + name + '-roles', type=int, nargs=2, choices=(0, 1),
                            metavar=('AP_INDEX', 'CP_INDEX'), required=True)
    try: args = parser.parse_args(argv)
    except _Arguments:
        print('Offline single-slot target rejected: INVALID_ARGUMENTS', file=sys.stderr)
        return 2
    try:
        output, parent = _parent(args.output)
        try:
            _private(os.fstat(parent), True)
            if output.exists() or output.is_symlink(): raise ValueError('Output exists')
        finally: os.close(parent)
        report = check_files(args.archive, args.ap, args.cp, args.ram, args.saved, args.selection, args.resources,
                             dict(zip(('AP', 'CP'), args.ram_roles)), dict(zip(('AP', 'CP'), args.saved_roles)))
        write_bytes_new(output, (json.dumps(report, indent=2, allow_nan=False) + '\n').encode())
        print('Offline single-slot target/inverse checked; device and recovery remain unverified')
        return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration, struct.error, zipfile.BadZipFile) as error:
        print('Offline single-slot target rejected: ' + type(error).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__': raise SystemExit(main())
