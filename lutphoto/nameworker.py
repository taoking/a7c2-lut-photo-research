"""Offline name-worker binding to a verified private single-slot bundle.

Uses pinned QAQLeonard metadata/C and the existing shared compiler and reports.
No target loading, device operations or module export. See ACKNOWLEDGEMENTS.md.
"""
import json
import struct
import subprocess
import sys
import zipfile

from . import slotbundle as b, programworker as program, workercontracts as w
from .capturestore import encoded

NATIVE_RESOURCE_BYTES = 524288


def _metadata(inputs, review, binding):
    """Bind the checked targets; do not regenerate resources or invent AP states."""
    rows, _ = b.m._selection_bytes(inputs.selection)
    slot, (_, name) = next(iter(rows.items()))
    if len(rows) != 1 or slot != review.report['selected_slot'] or w.sha(name.encode()) != review.report['name_utf8_sha256']:
        raise ValueError('Checked single-slot name differs')
    ids = b.c.LAYOUTS[review.report['label_layout_derived_from_program']]
    job = w.sha(b'A7C2-OFFLINE-NAMES\0' + encoded(binding))[:16]
    assets, pointers, files = [], [], {}
    for filename in b.c.RESOURCE_FILES:
        before, target = inputs.resources[filename], review.resources[filename]
        if not 5740 <= len(before) <= NATIVE_RESOURCE_BYTES or not 0 < len(target) <= NATIVE_RESOURCE_BYTES:
            raise ValueError('Resource exceeds pinned native buffer contract')
        decoded = b.c.decode_resource(before)
        if b.c.resources.inverse(target, review.resource_inverses[filename]) != before:
            raise ValueError('Complete resource inverse differs')
        info = {'before_bytes': len(before), 'after_bytes': len(target), 'before_sha256': w.sha(before),
                'after_sha256': w.sha(target), 'before_count': decoded['count']}
        files[filename] = info
        assets.append('{' + json.dumps(filename) + ',' + str(len(before)) + ','
                      + w.cbytes(w.hash_bytes(info['before_sha256'])) + ',' + w.cbytes(w.hash_bytes(info['after_sha256'])) + '}')
        pointers.append('{' + ','.join(str(decoded['entries'].get(rid, {}).get('pointer', 65535)) for rid in ids) + '}')
    source_ap, target_ap = w.sha(inputs.ap), w.sha(review.programs['AP'])
    transition = review.transitions['AP']
    if (source_ap != transition.before_sha or target_ap != transition.after_sha
            or b.t._apply(inputs.ap, transition) != review.programs['AP']
            or b.t._apply(review.programs['AP'], b.t._inverse(transition)) != inputs.ap):
        raise ValueError('Complete AP transition differs')
    lines = ['static const struct Asset assets[]={' + ','.join(assets) + '};',
             'static const u32 asset_count=68;',
             'static const u32 after_sizes[]={' + ','.join(str(v['after_bytes']) for v in files.values()) + '};',
             'static const u32 old_counts[]={' + ','.join(str(v['before_count']) for v in files.values()) + '};',
             'static const u32 label_ids[]={' + ','.join(str(rid) + 'U' for rid in ids) + '};',
             'static const unsigned short old_pointers[68][6]={' + ','.join(pointers) + '};',
             'static const u8 names[6][64]={' + ','.join(w.cbytes(((name if j == slot else 'ST') + '\0').encode()) for j in range(1, 7)) + '};',
             f'static const u32 selected_mask={1 << (slot - 1)};',
             'static const char backup_prefix[]=' + json.dumps('/usr/share/app/.a7c2-lut-' + job + '-') + ';',
             'static const u32 original_uid=57285,original_gid=1000;',
             f'static const u64 ap_size={len(inputs.ap)}UL;',
             'static const u8 ap_plain_hash[32]=' + w.cbytes(w.hash_bytes(source_ap)) + ';',
             'static const u8 ap_named_hash[32]=' + w.cbytes(w.hash_bytes(target_ap)) + ';']
    header = ('\n'.join(lines) + '\n').encode('ascii')
    if len(header) > 1024 * 1024:
        raise ValueError('Name manifest exceeds compilation budget')
    contract = {'schema': 'a7c2-offline-names-worker-contract/1', 'count': 68, 'AP': source_ap,
                'target_AP': target_ap, 'AP_bytes': len(inputs.ap), 'files': files, 'label_ids': list(ids),
                'selected_slot': slot, 'selected_mask': 1 << (slot - 1), 'offline_job_id': job,
                'job_id_is_device_authorization': False, 'pinned_uid': 57285, 'pinned_gid': 1000,
                'actual_file_ownership_verified': False}
    return header, contract


def _result(policy, binding, header, contract):
    return {**w.boundary(), **binding, 'schema': 'a7c2-offline-names-worker/1',
            'phase': 'NAMES_METADATA_CHECKED', 'commit': policy.commit, 'archive_sha256': policy.archive_sha,
            'names_metadata_checked_offline': True, 'names_contract': contract,
            'manifest_header_sha256': w.sha(header), 'contract_sha256': w.sha(encoded(contract)),
            'compiled_offline': False, 'temporary_targets_retained': False,
            'archive_Python_imported_or_executed': False, 'native_report_origin_authenticated': False,
            'report_contains_resource_hashes_or_job_id': False, 'report_authenticates_bundle': False,
            'resource_full_readback_verified': False, 'complete_settings_transition_verified': False,
            'restore_verified': False, 'device_operations_enabled': False}


def review_bundle(archive, directory, *, compile_names=False):
    if type(compile_names) is not bool: raise ValueError('Explicit compile boolean required')
    with b._open_bundle(archive, directory) as (policy, inputs, review, binding):
        header, contract = _metadata(inputs, review, binding)
        pin, sources = program._sources(archive, policy)
        result = _result(policy, binding, header, contract)
        result['upstream_C_source_sha256'] = pin['files']['src/looks/native/names.c']['sha256']
        if compile_names:
            result['build'] = w._compile_one(sources, 'names', header)
            result['compiled_offline'] = True
    return result


def check_report(archive, directory, report_path, mode):
    request = w.request('names', mode)
    with b._open_bundle(archive, directory) as (policy, inputs, review, binding):
        header, contract = _metadata(inputs, review, binding)
        program._sources(archive, policy)
        raw = b.c.bounded_read(report_path, 136)
        checked = w.validate_names(raw, mode, contract)
        result = {**_result(policy, binding, header, contract), **checked,
                  'phase': 'REPORT_STRUCTURE_CHECKED', 'request_sha256': w.sha(request), 'report_sha256': w.sha(raw)}
    return result


def main(argv=None):
    parser = b.t._Parser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True, parser_class=b.t._Parser)
    for name in ('review', 'check-report'):
        command = commands.add_parser(name, allow_abbrev=False)
        for option in ('archive', 'directory', 'output'): command.add_argument('--' + option, required=True)
        if name == 'review': command.add_argument('--compile-names', action='store_true')
        else:
            command.add_argument('--report', required=True)
            command.add_argument('--mode', type=int, choices=(0, 1, 2, 3), required=True)
    try: args = parser.parse_args(argv)
    except b.t._Arguments:
        print('Offline name worker rejected: INVALID_ARGUMENTS', file=sys.stderr); return 2
    try:
        output = program._output_path(args.output, args.directory)
        result = (review_bundle(args.archive, args.directory, compile_names=args.compile_names)
                  if args.command == 'review' else check_report(args.archive, args.directory, args.report, args.mode))
        program._save_report(output, result)
        summary = encoded({'phase': result['phase'], 'compiled_offline': result['compiled_offline'],
                           'device_operations_enabled': False}).decode()
        if sys.stdout.write(summary) != len(summary): raise OSError('Incomplete summary output')
        sys.stdout.flush(); return 0
    except (ValueError, OSError, ImportError, KeyError, TypeError, StopIteration, struct.error,
            zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print('Offline name worker rejected: ' + type(error).__name__, file=sys.stderr); return 1


if __name__ == '__main__': raise SystemExit(main())
