"""Private offline single-slot bundles; no camera, worker, replay or recovery.

Reuse slottarget's one generator and the existing private Store/Reader. This
artifact contains private full programs, snapshots, names and inverse bytes.
Never publish it. QAQLeonard/ma1co provenance: ACKNOWLEDGEMENTS.md.
"""
from contextlib import contextmanager
import os
import struct
import sys
import zipfile

from . import slottarget as t, captureinspect as i
from .capturestore import Store, _parent, _private, encoded

c, m, p = t.c, t.m, t.p
MIB = 1024 * 1024
SCHEMA = 'a7c2-private-single-slot-bundle/1'
MANIFEST = 'bundle.private.json'
CORE = {'source/appFw.so': ('ap', p.MAX_PROGRAM), 'source/cpapp-b.bin': ('cp', p.MAX_PROGRAM),
        'source/ram.bin': ('ram', t.s.bk4.MAX_SNAPSHOT), 'source/saved.bin': ('saved', t.s.bk4.MAX_SNAPSHOT),
        'source/selection.json': ('selection', m.MAX_JSON_FILE),
        'source/candidate.json': ('candidate', m.MAX_JSON_FILE), 'source/correction.table': ('table', 1215)}
LIMITS = {path: spec[1] for path, spec in CORE.items()}
LIMITS.update({'resources/' + n: c.MAX_RESOURCE for n in c.RESOURCE_FILES})
LIMITS.update({'evidence/target-appFw.so': p.MAX_PROGRAM, 'evidence/target-cpapp-b.bin': p.MAX_PROGRAM,
               'evidence/forward.private.json': c.MAX_JSON, 'evidence/reverse.private.json': c.MAX_JSON,
               'evidence/settings-scoped.private.json': c.MAX_JSON, 'evidence/resource-inverse.private.json': c.MAX_JSON,
               'evidence/review.private.json': 131072})
LIMITS.update({f'evidence/resource-{index:03d}.bin': c.MAX_RESOURCE for index in range(68)})


def _plan(transitions):
    return {chip: {'bytes': plan.size, 'before_sha256': plan.before_sha, 'after_sha256': plan.after_sha,
                   'changes': [{'offset': row.at, 'before': row.before.hex(), 'after': row.after.hex()}
                               for row in plan.changes]} for chip, plan in transitions.items()}


def _payloads(inputs, review):
    result = {path: getattr(inputs, attr) for path, (attr, _) in CORE.items()}
    result.update({'resources/' + n: inputs.resources[n] for n in c.RESOURCE_FILES})
    result.update({'evidence/target-appFw.so': review.programs['AP'],
                   'evidence/target-cpapp-b.bin': review.programs['CP'],
                   'evidence/forward.private.json': encoded(_plan(review.transitions)),
                   'evidence/reverse.private.json': encoded(_plan({k: t._inverse(v) for k, v in review.transitions.items()})),
                   'evidence/settings-scoped.private.json': encoded({'scope_only': True, 'snapshots': review.settings}),
                   'evidence/resource-inverse.private.json': encoded(review.resource_inverses),
                   'evidence/review.private.json': encoded(review.report)})
    result.update({f'evidence/resource-{index:03d}.bin': review.resources[n] for index, n in enumerate(c.RESOURCE_FILES)})
    if set(result) != set(LIMITS) or any(type(raw) is not bytes or not 0 < len(raw) <= LIMITS[n] for n, raw in result.items()):
        raise ValueError('Bundle payload set or size differs')
    return result


def _roles(roles):
    if type(roles) is not dict or set(roles) != {'ram', 'saved'}: raise ValueError('Two explicit snapshot roles required')
    for row in roles.values():
        if (type(row) is not dict or set(row) != {'AP', 'CP'} or any(type(v) is not int for v in row.values())
                or set(row.values()) != {0, 1}):
            raise ValueError('Distinct explicit AP/CP indices required')
    return roles


def _manifest(policy, roles, files):
    return {'schema': SCHEMA, 'commit': policy.commit, 'archive_sha256': policy.archive_sha,
            'offline_only': True, 'contains_private_payloads': True, 'settings_scope_only': True,
            'write_plan_enabled': False, 'roles': _roles(roles), 'files': files}


def _summary(review):
    changes = sum(len(plan.changes) for plan in review.transitions.values())
    return {'schema': 'a7c2-offline-slot-bundle-result/1', 'phase': 'CONSISTENT_OFFLINE_BUNDLE',
            'private_bundle': True, 'payload_files': len(LIMITS), 'selected_slot': review.report['selected_slot'],
            'program_change_windows': changes, 'program_change_required': changes != 0,
            'complete_settings_transition_verified': False, 'device_operations_enabled': False,
            'worker_generated': False, 'restore_verified': False}


def _new_directory(directory):
    path, parent = _parent(directory)
    try:
        _private(os.fstat(parent), True)
        if path.exists() or path.is_symlink(): raise ValueError('New private bundle required')
    finally: os.close(parent)
    return path


def create(archive, directory, *, ap_path, cp_path, ram_path, saved_path, selection_path, resources_path,
           ram_roles, saved_roles):
    """Freeze explicit inputs, save exact private targets/inverses, then reopen.

    Failure preserves partial output, never repairs/removes/reuses it. Completion
    markers and consistent bytes do not prove the original process exited well.
    """
    directory = _new_directory(directory)
    policy, runtime, inputs = t._prepare_files(archive, ap_path, cp_path, ram_path, saved_path,
                                              selection_path, resources_path, ram_roles, saved_roles)
    review = t._generate(policy, runtime, inputs); payloads = _payloads(inputs, review)
    total = sum(len(raw) for raw in payloads.values())
    if total + 131072 > 512 * MIB: raise ValueError('Bundle exceeds independent reader budget')
    store = Store(directory)
    try:
        store.require_space(total + 131072)
        files = {name: store.put(name, payloads[name], limit=LIMITS[name]) for name in sorted(LIMITS)}
        manifest = _manifest(policy, {'ram': inputs.ram_roles, 'saved': inputs.saved_roles}, files)
        store.put(MANIFEST, encoded(manifest)); store.check()
    except BaseException as error:
        try: store.close()
        except BaseException as cleanup: raise error from cleanup
        raise
    else: store.close()
    # Release the input/target copies before the independent reader reconstructs
    # them. The closed job is never reopened for writing.
    del inputs, review, payloads, runtime
    return inspect_directory(archive, directory)


@contextmanager
def _open_review(archive, directory):
    """Read only the fixed bundle inventory; regenerate from its frozen inputs.

    No original external path, manifest-directed path, policy override or device
    is used. A directory owner can rebuild a different valid bundle; no signature.
    """
    policy = p._load_policy(archive); reader = i._Reader(directory)
    try:
        if reader.inventory != set(LIMITS) | {MANIFEST, 'session.lock'} or set(reader.dirs) != {'', *i.FOLDERS}:
            raise ValueError('Incomplete or extra bundle contents')
        raw, _ = reader.read(MANIFEST, 131072, content=True); manifest = c.decode_json(raw)
        if type(manifest) is not dict or type(manifest.get('files')) is not dict or set(manifest['files']) != set(LIMITS):
            raise ValueError('Fixed bundle manifest required')
        files = manifest['files']; roles = _roles(manifest.get('roles'))
        if any(not i._info(spec) or spec['bytes'] > LIMITS[name] for name, spec in files.items()):
            raise ValueError('Bounded complete file fingerprints required')
        if encoded(_manifest(policy, roles, files)) != raw: raise ValueError('Manifest source, schema or flags differ')
        observed = {}
        for name in sorted(LIMITS):
            content, info = reader.read(name, LIMITS[name], content=True)
            if info != files[name]: raise ValueError('Complete payload fingerprint differs')
            observed[name] = content
        reader.check()
        core = {attr: observed[path] for path, (attr, _) in CORE.items()}
        inputs = t._Inputs(**core, resources={n: observed['resources/' + n] for n in c.RESOURCE_FILES},
                           ram_roles=roles['ram'], saved_roles=roles['saved'])
        identity = p._identify(inputs.ap, inputs.cp, policy)
        runtime = t._runtime(archive, policy) if identity['first_import'] else None
        review = t._generate(policy, runtime, inputs)
        expected = _payloads(inputs, review)
        if any(observed[name] != expected[name] for name in LIMITS):
            raise ValueError('Frozen targets, inverse or review differ from regenerated result')
        reader.check()
        yield policy, review, {'bundle_manifest_sha256': p.w.sha(raw),
                               'target_review_sha256': review.report['target_review_sha256']}
        reader.check()
    except BaseException as error:
        try: reader.close()
        except BaseException as cleanup: raise error from cleanup
        raise
    else: reader.close()


def inspect_directory(archive, directory):
    """Return the existing summary only after the shared reader closes well."""
    with _open_review(archive, directory) as (_, review, _):
        result = _summary(review)
    return result


def main(argv=None):
    parser = t._Parser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True, parser_class=t._Parser)
    for name in ('create', 'inspect'):
        command = commands.add_parser(name, allow_abbrev=False)
        for option in ('archive', 'directory'): command.add_argument('--' + option, required=True)
        if name == 'create':
            for option in ('ap', 'cp', 'ram', 'saved', 'selection', 'resources'): command.add_argument('--' + option, required=True)
            for option in ('ram', 'saved'):
                command.add_argument('--' + option + '-roles', type=int, nargs=2, choices=(0, 1),
                                     metavar=('AP_INDEX', 'CP_INDEX'), required=True)
    try: args = parser.parse_args(argv)
    except t._Arguments:
        print('Offline slot bundle rejected: INVALID_ARGUMENTS', file=sys.stderr); return 2
    try:
        if args.command == 'create':
            result = create(args.archive, args.directory, ap_path=args.ap, cp_path=args.cp, ram_path=args.ram,
                            saved_path=args.saved, selection_path=args.selection, resources_path=args.resources,
                            ram_roles=dict(zip(('AP', 'CP'), args.ram_roles)), saved_roles=dict(zip(('AP', 'CP'), args.saved_roles)))
        else: result = inspect_directory(args.archive, args.directory)
        raw = encoded(result).decode()
        if sys.stdout.write(raw) != len(raw): raise OSError('Incomplete summary output')
        sys.stdout.flush(); return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration, struct.error, zipfile.BadZipFile) as error:
        print('Offline slot bundle rejected: ' + type(error).__name__, file=sys.stderr); return 1


if __name__ == '__main__': raise SystemExit(main())
