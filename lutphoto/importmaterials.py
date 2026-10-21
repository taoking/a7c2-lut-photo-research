"""Bind local N2 tables/names/resources to read-only program/snapshot checks.

No deployment or firmware/settings transition. Rules credit QAQLeonard and
ma1co as recorded in ACKNOWLEDGEMENTS.md and the retained MIT licenses.
"""
import argparse
import json
import math
import os
from pathlib import Path
import struct
import sys
import zipfile

from . import customcontracts as c, programidentity as p, settingsbinding as s
from .io import write_bytes_new

MAX_JSON_FILE = 128 * 1024
SELECTION = 'a7c2-import-material-selection/1'
CANDIDATE = 'a7c2-offline-native-candidate/1'
TABLE_LAYOUT = 'Y/C1/C2 planes; 5x9x9; signed -64..63'


def _json_file(path):
    raw = c.bounded_read(path, MAX_JSON_FILE)
    return c.decode_json(raw), p.w.sha(raw)


def _relative_directory(base, value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 512 or '\\' in value
            or any(ord(char) < 32 for char in value) or any(part in ('', '.', '..') for part in value.split('/'))
            or Path(value).is_absolute()):
        raise ValueError('Explicit bounded relative candidate directory required')
    directory = Path(base)
    for part in (None, *value.split('/')):
        if part is not None: directory /= part
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('Candidate directory must be plain, without relative symlinks')
    return directory


def _selection(path):
    value, fingerprint = _json_file(path)
    if (not isinstance(value, dict) or set(value) != {'schema', 'slots'} or value['schema'] != SELECTION
            or not isinstance(value['slots'], dict) or not 1 <= len(value['slots']) <= 6):
        raise ValueError('Invalid selected material schema')
    rows = {}
    for slot, row in value['slots'].items():
        if (slot not in tuple('123456') or not isinstance(row, dict) or set(row) != {'candidate', 'name'}):
            raise ValueError('Canonical slots 1..6 and candidate/name required')
        rows[int(slot)] = (row['candidate'], row['name'])
    c.names_checked({slot: row[1] for slot, row in rows.items()})
    return rows, fingerprint


def _candidate_content(directory, commit):
    """Return checked metadata and the same observed table for offline targets."""
    found = set()
    with os.scandir(directory) as entries:
        for entry in entries:
            found.add(entry.name)
            if len(found) > 2: raise ValueError('Expected only two N2 candidate files')
    if found != {'candidate.json', 'correction.table'}:
        raise ValueError('Expected N2 candidate.json and correction.table')
    data, candidate_sha = _json_file(directory / 'candidate.json')
    if (not isinstance(data, dict) or data.get('schema') != CANDIDATE
            or type(data.get('adapter_version')) is not int or data['adapter_version'] != 1
            or data.get('upstream_commit') != commit or data.get('actual_camera_accuracy_verified') is not False
            or data.get('device_integration_enabled') is not False or data.get('not_a_firmware_image') is not True):
        raise ValueError('Unsupported N2 candidate or device/physical claims')
    table = data.get('table')
    if (not isinstance(table, dict) or set(table) != {'file', 'bytes', 'sha256', 'layout'}
            or table['file'] != 'correction.table' or type(table['bytes']) is not int or table['bytes'] != 1215
            or table['layout'] != TABLE_LAYOUT):
        raise ValueError('Unsupported native table descriptor')
    p.w.hash_bytes(table['sha256'])
    raw = c.bounded_read(directory / 'correction.table', 1215)
    if len(raw) != 1215 or p.w.sha(raw) != table['sha256'] or any(64 <= byte < 192 for byte in raw):
        raise ValueError('Native table size/hash/signed range differs')
    provenance = data.get('provenance')
    if not isinstance(provenance, dict): raise ValueError('N2 provenance fingerprints required')
    for name in ('project_sha256', 'calibration_sha256', 'reference_sha256'):
        p.w.hash_bytes(provenance.get(name))
    acceptance, score = data.get('acceptance'), data.get('synthetic_holdout')
    if (not isinstance(acceptance, dict) or acceptance.get('passed') is not True
            or acceptance.get('scope') != 'offline reference comparison only; not camera acceptance'
            or not isinstance(score, dict)):
        raise ValueError('Offline acceptance claims required')
    thresholds = acceptance.get('thresholds_declared_before_holdout')
    if not isinstance(thresholds, dict) or set(thresholds) != {'max_rgb_mae', 'max_delta_e76_p95'}:
        raise ValueError('Declared N2 thresholds required')
    for metric in ('rgb_mae', 'delta_e76_p95'):
        limit, measured = thresholds['max_' + metric], score.get(metric)
        if (not _finite_number(limit) or not _finite_number(measured) or limit <= 0 or not 0 <= measured <= limit):
            raise ValueError('Declared offline acceptance and metrics differ')
    if 'validation_lock_sha256' in data: p.w.hash_bytes(data['validation_lock_sha256'])
    return {'candidate_sha256': candidate_sha, 'table_sha256': p.w.sha(raw), 'table_bytes': len(raw),
            'format_and_declared_acceptance_consistent': True, 'project_model_or_fit_revalidated': False,
            'validation_lock_revalidated': False, 'camera_color_accuracy_verified': False}, raw


def _candidate(directory, commit):
    return _candidate_content(directory, commit)[0]


def _finite_number(value):
    if type(value) not in (int, float): return False
    try: return math.isfinite(value)
    except OverflowError: return False


def _layout(identity):
    if identity['kind'] == 'legacy-six' and identity['layout'] == 'full7-v4': return 'legacy-six'
    if identity['kind'] in ('stock', 'fl23', 'stock-lut', 'fl23-lut') and identity['layout'] == 'standalone-v1': return 'standalone'
    raise ValueError('Unsupported program-derived label layout')


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def check_files(archive, ap_path, cp_path, ram_path, saved_path, selection_path, resources_path, ram_roles, saved_roles):
    rows, selection_sha = _selection(selection_path)
    ram_roles, saved_roles = dict(ram_roles), dict(saved_roles)
    binding = s.check_files(archive, ap_path, cp_path, ram_path, saved_path, sorted(rows), ram_roles, saved_roles)
    layout = _layout(binding['identity'])
    candidates, slots = {}, {}
    for slot, (relative, name) in sorted(rows.items()):
        directory = _relative_directory(Path(selection_path).parent, relative)
        if directory not in candidates: candidates[directory] = _candidate(directory, binding['commit'])
        slots[str(slot)] = {**candidates[directory], 'name_utf8_sha256': p.w.sha(name.encode('utf-8'))}
    resources = c.resource_directory(resources_path, {slot: row[1] for slot, row in rows.items()}, layout)
    materials = {'binding': binding, 'selection_sha256': selection_sha, 'slots': slots,
                 'asserted_roles': {'ram': ram_roles, 'saved': saved_roles}, 'resources': resources,
                 'label_layout_derived_from_program': layout}
    return {**p._boundary(), 'schema': 'a7c2-import-material-manifest/1', **materials,
            'materials_sha256': p.w.sha(_canonical(materials)), 'input_fingerprints_recorded': True,
            'resource_inverse_checked_in_memory': True, 'resource_origin_and_capture_verified': False,
            'snapshot_freshness_verified': False, 'same_capture_provenance_verified': False,
            'complete_program_transition_verified': False, 'complete_settings_transition_verified': False,
            'independent_backups_verified': False, 'firmware_or_settings_write_plan_enabled': False,
            'native_worker_generated': False, 'camera_deployment_enabled': False,
            'private_paths_names_or_payloads_in_manifest': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'ap', 'cp', 'ram', 'saved', 'selection', 'resources', 'output'):
        parser.add_argument('--' + name, required=True)
    for name in ('ram', 'saved'):
        parser.add_argument('--' + name + '-roles', type=int, nargs=2, choices=(0, 1),
                            metavar=('AP_INDEX', 'CP_INDEX'), required=True)
    args = parser.parse_args(argv)
    try:
        if Path(args.output).exists() or Path(args.output).is_symlink(): raise ValueError('Output exists')
        result = check_files(args.archive, args.ap, args.cp, args.ram, args.saved, args.selection, args.resources,
                             dict(zip(('AP', 'CP'), args.ram_roles)), dict(zip(('AP', 'CP'), args.saved_roles)))
        write_bytes_new(args.output, (json.dumps(result, indent=2, allow_nan=False) + '\n').encode())
        print('Local material manifest completed; camera/deployment remain unverified')
        return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration, struct.error, zipfile.BadZipFile) as exc:
        print('Local material manifest rejected: ' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
