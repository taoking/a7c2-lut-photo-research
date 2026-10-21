"""Offline program-worker binding/compilation; no loader or device operations.

Consumes only independently regenerated private slot bundles. Pinned C remains
unmodified and is never loaded. QAQLeonard/ma1co: ACKNOWLEDGEMENTS.md.
"""
import os
from pathlib import Path
import struct
import subprocess
import sys
import zipfile

from . import slotbundle as b, workercontracts as w
from .capturestore import _parent, _private, _same, encoded


def _metadata(review):
    """Mirror pinned nativebuild ordering, using the sole checked transition."""
    contract = {'schema': 'a7c2-table-worker-contract/1', 'sizes': {}, 'before': {}, 'after': {}}
    windows = []
    for chip, label in enumerate(('AP', 'CP')):
        plan = review.transitions[label]; target = review.programs[label]
        # Recheck both complete directions, including unchanged files.
        source = b.t._apply(target, b.t._inverse(plan))
        if b.t._apply(source, plan) != target:
            raise ValueError('Complete program transition differs')
        name = w.NAMES[chip]
        contract['sizes'][name] = plan.size
        contract['before'][name] = plan.before_sha; contract['after'][name] = plan.after_sha
        windows.extend((chip, row) for row in plan.changes)
    if not windows:
        return None, None
    if len(windows) > 4096:
        raise ValueError('Too many program windows')
    windows.sort(key=lambda item: (0 if item[0] == 1 else 1, 0 if len(item[1].before) > 1024 else 1, item[1].at))
    if sum(8 * len(row.before) + 160 for _, row in windows) > 1024 * 1024 - 2048:
        raise ValueError('Program manifest exceeds compilation budget')
    lines, rows = [], []
    for index, (chip, row) in enumerate(windows):
        lines.append(f'static const u8 old_{index}[]={w.cbytes(row.before)},new_{index}[]={w.cbytes(row.after)};')
        rows.append(f'{{{row.at}UL,{len(row.before)},{chip},old_{index},new_{index}}}')
    lines += ['static const struct Window windows[]={' + ','.join(rows) + '};',
              f'static const u32 window_count={len(windows)};',
              'static const u64 file_sizes[]={' + ','.join(str(contract['sizes'][n]) + 'UL' for n in w.NAMES) + '};']
    for label, key in (('original', 'before'), ('final', 'after')):
        lines.append('static const u8 ' + label + '_hashes[2][32]={' + ','.join(w.cbytes(w.hash_bytes(contract[key][n])) for n in w.NAMES) + '};')
    contract['window_writes'] = len(windows)
    header = ('\n'.join(lines) + '\n').encode('ascii')
    if len(header) > 1024 * 1024:
        raise ValueError('Program manifest exceeds compilation budget')
    return header, contract


def _sources(archive, policy):
    pin, sources = w.load_sources(archive)
    w.catalog(sources)
    if pin['commit'] != policy.commit or pin['archive_sha256'] != policy.archive_sha:
        raise ValueError('Bundle and worker source policies differ')
    return pin, sources


def _report(policy, review, binding, header, contract):
    return {**w.boundary(), **binding, 'schema': 'a7c2-offline-program-worker/1',
            'phase': 'PROGRAM_METADATA_CHECKED' if contract else 'NO_PROGRAM_CHANGE',
            'commit': policy.commit, 'archive_sha256': policy.archive_sha,
            'program_manifest_checked_offline': True, 'program_change_required': contract is not None,
            'program_contract': contract, 'contract_sha256': w.sha(encoded(contract)),
            'manifest_header_sha256': w.sha(header) if header else None,
            'compiled_offline': False, 'temporary_targets_retained': False,
            'archive_Python_imported_or_executed': False, 'complete_settings_transition_verified': False,
            'names_worker_bound': False, 'restore_verified': False}


def review_bundle(archive, directory, *, compile_program=False):
    if type(compile_program) is not bool:
        raise ValueError('Explicit compile boolean required')
    with b._open_review(archive, directory) as (policy, review, binding):
        header, contract = _metadata(review)
        result = _report(policy, review, binding, header, contract)
        if contract:
            pin, sources = _sources(archive, policy)
            result['upstream_C_source_sha256'] = pin['files']['src/fl23/native/installer.c']['sha256']
            if compile_program:
                result['build'] = w._compile_one(sources, 'program', header, expected_windows=contract['window_writes'])
                result['compiled_offline'] = True
    return result


def check_report(archive, directory, report_path, mode):
    request = w.request('program', mode)
    with b._open_review(archive, directory) as (policy, review, binding):
        header, contract = _metadata(review)
        if contract is None:
            raise ValueError('No program task exists for this bundle')
        _sources(archive, policy)
        raw = b.c.bounded_read(report_path, 240)
        checked = w.validate_program(raw, mode, contract)
        result = {**_report(policy, review, binding, header, contract), **checked,
                  'phase': 'REPORT_STRUCTURE_CHECKED', 'request_sha256': w.sha(request),
                  'report_sha256': w.sha(raw), 'native_report_origin_authenticated': False}
    return result


def _output_path(output, directory):
    path, parent = _parent(output)
    try:
        _private(os.fstat(parent), True)
        bundle = Path(directory).absolute()
        if path == bundle or bundle in path.parents or path.exists() or path.is_symlink():
            raise ValueError('New private report outside the bundle required')
    finally:
        os.close(parent)
    return path


def _save_report(path, result):
    """Exclusive descriptor-relative report, preserving partial output on error."""
    path, parent = _parent(path)
    try:
        _private(os.fstat(parent), True)
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            view = memoryview(encoded(result))
            while view:
                count = os.write(fd, view)
                if not 0 < count <= len(view): raise OSError('Incomplete private report')
                view = view[count:]
            os.fsync(fd); _private(os.fstat(fd))
            if not _same(os.fstat(fd), os.stat(path.name, dir_fd=parent, follow_symlinks=False)):
                raise ValueError('Private report entry changed')
        finally:
            os.close(fd)
        os.fsync(parent)
        if not _same(os.fstat(parent), path.parent.stat(follow_symlinks=False)):
            raise ValueError('Private report directory changed')
    finally:
        os.close(parent)


def main(argv=None):
    parser = b.t._Parser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True, parser_class=b.t._Parser)
    for name in ('review', 'check-report'):
        command = commands.add_parser(name, allow_abbrev=False)
        for option in ('archive', 'directory', 'output'):
            command.add_argument('--' + option, required=True)
        if name == 'review': command.add_argument('--compile-program', action='store_true')
        else:
            command.add_argument('--report', required=True)
            command.add_argument('--mode', type=int, choices=(0, 1, 2), required=True)
    try: args = parser.parse_args(argv)
    except b.t._Arguments:
        print('Offline program worker rejected: INVALID_ARGUMENTS', file=sys.stderr); return 2
    try:
        path = _output_path(args.output, args.directory)
        result = (review_bundle(args.archive, args.directory, compile_program=args.compile_program)
                  if args.command == 'review' else check_report(args.archive, args.directory, args.report, args.mode))
        _save_report(path, result)
        summary = encoded({'phase': result['phase'], 'compiled_offline': result['compiled_offline'],
                           'device_operations_enabled': False}).decode()
        if sys.stdout.write(summary) != len(summary): raise OSError('Incomplete summary output')
        sys.stdout.flush(); return 0
    except (ValueError, OSError, ImportError, KeyError, TypeError, StopIteration, struct.error,
            zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print('Offline program worker rejected: ' + type(error).__name__, file=sys.stderr); return 1


if __name__ == '__main__': raise SystemExit(main())
