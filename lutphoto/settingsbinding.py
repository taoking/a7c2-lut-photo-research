"""Read-only descriptor/snapshot binding, never an installation readiness gate.

Based on QAQLeonard's pinned devicesettings rules and the ma1co BK4 format.
See ACKNOWLEDGEMENTS.md and the retained MIT licenses in docs/ and _vendor/.
"""
import argparse
import json
from pathlib import Path
import struct
import sys
import zipfile

from . import bk4, customcontracts as c, programidentity as p
from .io import write_bytes_new


def _snapshot(path, roles):
    raw = c.bounded_read(path, bk4.MAX_SNAPSHOT)
    images = bk4.parse_snapshot(raw)
    decoded, scoped = bk4.project(images, roles)
    return c.snapshot(decoded), scoped, {'sha256': p.w.sha(raw), 'bytes': len(raw),
            'images': [bk4.image_summary(i) for i in images]}


def _check_values(bindings, ram, saved, ram_scope, saved_scope):
    for key in bindings.references:
        if any(key not in state[0] or len(state[0][key].data) != 4 for state in (ram, saved)):
            raise ValueError('ST reference field missing or resized')
    matching = 0
    for field in bindings.fields:
        for state in (ram, saved):
            value = state[0].get(field.key)
            if value is None or len(value.data) != field.size or value.attr & 3:
                raise ValueError('Selected field missing, resized or protected')
        if ram[0][field.key] != saved[0][field.key]:
            raise ValueError('Selected RAM/saved recipe differs')
        reference = bytes(1) if field.reference is None else ram[0][field.reference].data
        matching += ram[0][field.key].data == reference
    # This checks all non-diagnostic 02cf fields and the four CP units in both
    # directions, including saved-only keys. No hypothetical after-state is made.
    compared = c.devicesettings.compare(ram, saved, {}, c.StrictPreservation)
    c.devicesettings.require_save_preserves_unsaved(ram, saved, {f.key for f in bindings.fields})
    c.devicesettings.protected_equal(ram, saved)
    for chip, rows in ram_scope.items():
        if rows.keys() != saved_scope[chip].keys():
            raise ValueError('Scoped field set differs')
        for key, value in rows.items():
            other = saved_scope[chip][key]
            if (value.attr, value.max_size, len(value.data), value.reset_data) != (
                    other.attr, other.max_size, len(other.data), other.reset_data):
                raise ValueError('Scoped reset data or allocation layout differs')
    return {'descriptor_field_sizes_and_selected_attributes_checked': True,
            'selected_RAM_saved_equal': True, 'non_diagnostic_scope_RAM_saved_equal': True,
            'scoped_reset_and_layout_equal': True, 'protected_CP_units_equal': True,
            'selected_fields_equal_ST': matching, 'all_selected_fields_equal_ST': matching == len(bindings.fields),
            'compared_properties': compared['preserved_properties'],
            'diagnostic_value_compared': False, 'other_runtime_groups_compared': False}


def check_files(archive, ap_path, cp_path, ram_path, saved_path, slots, ram_roles, saved_roles):
    policy = p._load_policy(archive)
    ap = p._read_program(ap_path, {s.ap_bytes for s in policy.sources})
    cp = p._read_program(cp_path, {s.cp_bytes for s in policy.sources})
    identity = p._identify(ap, cp, policy)
    bindings = p._descriptor_bindings(ap, slots, policy)
    # No snapshots are opened before the complete program and descriptor gates.
    ram, ram_scope, ram_report = _snapshot(ram_path, ram_roles)
    saved, saved_scope, saved_report = _snapshot(saved_path, saved_roles)
    values = _check_values(bindings, ram, saved, ram_scope, saved_scope)
    return {**p._boundary(), 'schema': 'a7c2-settings-binding-report/1', 'kind': 'local-descriptor-snapshot-binding',
            'commit': policy.commit, 'archive_sha256': policy.archive_sha,
            'local_program_content_verified': True, 'provided_snapshot_structure_and_values_checked': True,
            'raw_backup_parsed': True, 'roles_are_caller_assertions': True, 'scope_projection_only': True,
            'same_capture_provenance_verified': False, 'snapshot_freshness_verified': False,
            'outer_wrapper_verified': False, 'container_complete_backup_verified': False,
            'settings_write_plan_enabled': False, 'identity': identity,
            'descriptors': p._descriptor_summary(bindings), 'values': values,
            'snapshots': {'ram': ram_report, 'saved': saved_report},
            'scope': {**c.devicesettings.PRESERVATION_SCOPE,
                      'other_runtime_groups': 'not compared or written; no backup performed'},
            'keys_values_targets_or_program_bytes_in_report': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'ap', 'cp', 'ram', 'saved', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--slots', type=int, nargs='+', required=True)
    parser.add_argument('--ram-roles', type=int, nargs=2, choices=(0, 1), metavar=('AP_INDEX', 'CP_INDEX'), required=True)
    parser.add_argument('--saved-roles', type=int, nargs=2, choices=(0, 1), metavar=('AP_INDEX', 'CP_INDEX'), required=True)
    args = parser.parse_args(argv)
    try:
        if Path(args.output).exists() or Path(args.output).is_symlink():
            raise ValueError('Output exists')
        result = check_files(args.archive, args.ap, args.cp, args.ram, args.saved, args.slots,
                             dict(zip(('AP', 'CP'), args.ram_roles)), dict(zip(('AP', 'CP'), args.saved_roles)))
        write_bytes_new(args.output, (json.dumps(result, indent=2, allow_nan=False) + '\n').encode())
        print('Read-only settings binding completed; freshness/body/device remain unverified')
        return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration, struct.error, zipfile.BadZipFile) as exc:
        print('Read-only settings binding rejected: ' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
