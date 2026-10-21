"""Offline descriptor-derived unit plans and snapshot checks; no device executor.

QAQLeonard devicesettings/devicejob semantics; ma1co BK4 parsing. Reuses the
single-slot target generator, source/worker checks and private output contracts.
"""
from dataclasses import replace
import struct
import sys
import zipfile

from . import slotbundle as b, programworker as program, nameworker as names
from .capturestore import encoded

bk4, c, w = b.t.s.bk4, b.c, program.w
STAGES = ('source', 'target', 'restored')


def _snapshot(raw, roles):
    images = bk4.parse_snapshot(raw)
    _, scope = bk4.project(images, roles)
    full = {chip: dict(images[roles[chip]].records) for chip in ('AP', 'CP')}
    return full, scope


def _scope(full):
    return {'AP': {k: v for k, v in full['AP'].items() if k >> 16 == 0x02cf},
            'CP': {k: full['CP'][k] for k in c.devicesettings.PROTECTED}}


def _decoded(scoped):
    return c.snapshot({chip: {f'{key:08x}': {'attr': value.attr, 'data': value.data.hex()}
                             for key, value in rows.items()} for chip, rows in scoped.items()})


def _record(value):
    return {'attr': value.attr, 'bytes': len(value.data), 'max_size': value.max_size,
            'reset': None if value.reset_data is None else value.reset_data.hex()}


def _transition(before, fields, reverse=False):
    """Apply exact unit preconditions to complete decoded maps, not raw BK4."""
    result = {state: {chip: dict(rows) for chip, rows in full.items()} for state, full in before.items()}
    for field in fields:
        for state in ('ram', 'saved'):
            old = bytes.fromhex(field['after'] if reverse else field['before_' + state])
            want = bytes.fromhex(field['before_' + state] if reverse else field['after'])
            value = result[state]['AP'][field['key']]
            if value.data != old or value.attr & 3 or len(value.data) != len(want):
                raise ValueError('Selected unit transition precondition differs')
            result[state]['AP'][field['key']] = replace(value, data=want)
    return result


def _actions(fields, reverse=False):
    units = []
    for row in fields:
        source = row['after'] if reverse else row['before_ram']
        saved = row['after'] if reverse else row['before_saved']
        target = row['before_ram'] if reverse else row['after']
        target_saved = row['before_saved'] if reverse else row['after']
        if target != target_saved:
            raise ValueError('One save cannot restore distinct selected RAM/storage values')
        units.append({'key': row['key'], 'before_ram': source, 'before_saved': saved, 'target': target,
                      'read_before_required': True, 'write_required': source != target,
                      'read_after_write_required': source != target})
    return {'units': units, 'write_count': sum(v['write_required'] for v in units),
            'save_required': any(v['write_required'] or v['before_saved'] != v['target'] for v in units),
            'check_unselected_unsaved_before_save': True,
            'post_RAM_and_saved_snapshots_required': True, 'partial_resume_supported': False}


def _chain(inputs, review, binding):
    program_header, pc = program._metadata(review)
    name_header, nc = names._metadata(inputs, review, binding)
    source = {chip: v.before_sha for chip, v in review.transitions.items()}
    target = {chip: v.after_sha for chip, v in review.transitions.items()}
    if nc['AP'] != source['AP'] or nc['target_AP'] != target['AP'] or nc['selected_slot'] != review.report['selected_slot']:
        raise ValueError('Program/name AP direction or slot differs')
    if pc is not None and (pc['before'] != dict(zip(w.NAMES, (source['AP'], source['CP'])))
                          or pc['after'] != dict(zip(w.NAMES, (target['AP'], target['CP'])))):
        raise ValueError('Complete program contract differs')
    preflight = ['source_programs_resources_settings_recheck']
    if pc is not None: preflight.append('program_mode_0')
    preflight.append('names_mode_0')
    apply = ['names_mode_1_at_source_AP', 'all_68_target_resources_readback']
    if pc is not None: apply += ['program_mode_1', 'complete_target_program_readback']
    else: apply.append('unchanged_complete_programs_recheck')
    apply += ['settings_forward_at_target_programs', 'reload_preparation_requires_separate_review',
              'cold_start_and_runtime_resource_settings_checks', 'owner_photo_preview_acceptance', 'names_mode_3_at_target_AP']
    reverse = ['target_programs_resources_recheck', 'settings_reverse_at_target_programs']
    if pc is not None: reverse += ['program_mode_2', 'complete_source_program_readback']
    else: reverse.append('unchanged_complete_programs_recheck')
    reverse += ['names_mode_2_at_source_AP', 'all_68_source_resources_readback', 'separate_reload_and_cold_start_verification']
    return {'source_programs': source, 'target_programs': target, 'program_change_required': pc is not None,
            'program_contract_sha256': w.sha(encoded(pc)), 'program_header_sha256': w.sha(program_header) if program_header else None,
            'names_contract_sha256': w.sha(encoded(nc)), 'names_header_sha256': w.sha(name_header),
            'preflight_order': preflight, 'apply_order': apply, 'reverse_order': reverse,
            'any_unknown_result': 'stop_preserve_evidence_no_replay_no_automatic_restore',
            'ordered_requirements_only': True, 'executor_enabled': False}


def _build(policy, inputs, review, binding):
    slot = review.report['selected_slot']
    bindings = b.p._descriptor_bindings(inputs.ap, [slot], policy)
    before, scoped = {}, {}
    for state in ('ram', 'saved'):
        before[state], scoped[state] = _snapshot(getattr(inputs, state), getattr(inputs, state + '_roles'))
        if b.t._scope_value(scoped[state]) != review.settings[state]['before']:
            raise ValueError('Original settings scope differs from verified bundle')
    b.t.s._check_values(bindings, _decoded(scoped['ram']), _decoded(scoped['saved']), scoped['ram'], scoped['saved'])
    fields, metadata = [], {}
    for field in bindings.fields:
        key = field.key
        after = review.settings['ram']['target']['AP'][str(key)]['data']
        if after != review.settings['saved']['target']['AP'][str(key)]['data']:
            raise ValueError('Target RAM/storage units differ')
        fields.append({'slot': slot, 'key': key, 'before_ram': before['ram']['AP'][key].data.hex(),
                       'before_saved': before['saved']['AP'][key].data.hex(), 'after': after})
        metadata[str(key)] = {state: _record(before[state]['AP'][key]) for state in ('ram', 'saved')}
    if len(fields) != 9 or len({r['key'] for r in fields}) != 9:
        raise ValueError('Exactly nine descriptor-derived units required')
    after = _transition(before, fields)
    if _transition(after, fields, reverse=True) != before:
        raise ValueError('Complete decoded-map inverse differs')
    for state in ('ram', 'saved'):
        if b.t._scope_value(_scope(after[state])) != review.settings[state]['target']:
            raise ValueError('Unit actions differ from sole target generator')
    forward, reverse = _actions(fields), _actions(fields, reverse=True)
    if forward['save_required']:
        c.devicesettings.require_save_preserves_unsaved(_decoded(scoped['ram']), _decoded(scoped['saved']), {r['key'] for r in fields})
    contract = {'schema': 'a7c2-offline-unit-settings-plan/1', 'selected_slot': slot, 'fields': fields,
                'property_preconditions': metadata, 'forward': forward, 'reverse': reverse,
                'snapshots': {state: {'sha256': w.sha(getattr(inputs, state)), 'roles': getattr(inputs, state + '_roles'),
                                      'decoded_before_sha256': b.t._scope_sha(before[state]),
                                      'decoded_target_sha256': b.t._scope_sha(after[state])} for state in ('ram', 'saved')},
                'chain': _chain(inputs, review, binding),
                'preservation_scope': {**c.devicesettings.PRESERVATION_SCOPE,
                                       'other_runtime_groups': 'decoded differences observed only; not preserved or written'},
                'unit_actions_exported': True, 'decoded_complete_map_inverse_checked_offline': True,
                'full_BK4_target_generated': False, 'raw_BK4_bytes_exported': False, 'outer_wrapper_verified': False}
    return contract, before, after


def _result(policy, binding, contract):
    return {**w.boundary(), **binding, 'schema': 'a7c2-offline-unit-settings-result/1', 'private_report': True,
            'phase': 'UNIT_SETTINGS_PLAN_CHECKED', 'commit': policy.commit, 'archive_sha256': policy.archive_sha,
            'unit_plan_checked_offline': True, 'settings_contract': contract, 'contract_sha256': w.sha(encoded(contract)),
            'device_operations_enabled': False, 'settings_write_plan_enabled': False,
            'complete_settings_transition_verified': False, 'independent_property_readback_verified': False,
            'settings_save_verified': False, 'actual_program_and_name_stage_verified': False,
            'actual_observation_origin_verified': False, 'restore_verified': False,
            'outer_wrapper_verified': False, 'other_runtime_groups_preservation_verified': False}


def review_bundle(archive, directory):
    with b._open_bundle(archive, directory) as (policy, inputs, review, binding):
        program._sources(archive, policy)
        contract, _, _ = _build(policy, inputs, review, binding)
        result = _result(policy, binding, contract)
    return result


def _check_snapshot(expected, observed):
    old, new = _scope(expected), _scope(observed)
    c.devicesettings.compare(_decoded(old), _decoded(new), {}, c.StrictPreservation)
    c.devicesettings.protected_equal(_decoded(old), _decoded(new))
    for chip in ('AP', 'CP'):
        if old[chip].keys() != new[chip].keys(): raise ValueError('Scoped field set differs')
        for key, value in old[chip].items():
            if _record(value) != _record(new[chip][key]):
                raise ValueError('Attribute, reset data or allocation differs')
    outside = {(chip, key) for chip, rows in expected.items() for key in rows if key not in old[chip]}
    outside |= {(chip, key) for chip, rows in observed.items() for key in rows if key not in new[chip]}
    return {'strict_scope_checked': True, 'diagnostic_value_compared': False,
            'outside_scope_changed_properties': sum(expected[chip].get(key) != observed[chip].get(key) for chip, key in outside),
            'outside_scope_is_diagnostic_only': True}


def check_files(archive, directory, *, stage, ram_path, saved_path, ram_roles, saved_roles):
    if type(stage) is not str or stage not in STAGES: raise ValueError('Explicit supported observation stage required')
    with b._open_bundle(archive, directory) as (policy, inputs, review, binding):
        program._sources(archive, policy)
        contract, before, after = _build(policy, inputs, review, binding)
        expected = after if stage == 'target' else before
        observations = {}
        for state, path, roles in (('ram', ram_path, ram_roles), ('saved', saved_path, saved_roles)):
            raw = c.bounded_read(path, bk4.MAX_SNAPSHOT)
            observed, _ = _snapshot(raw, roles)
            observations[state] = {**_check_snapshot(expected[state], observed), 'sha256': w.sha(raw), 'roles': roles}
        result = {**_result(policy, binding, contract), 'phase': 'SNAPSHOT_SCOPE_CHECKED',
                  'observed_stage': stage, 'provided_snapshot_scope_checked_offline': True, 'observations': observations}
    return result


def main(argv=None):
    parser = b.t._Parser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True, parser_class=b.t._Parser)
    for name in ('review', 'check'):
        command = commands.add_parser(name, allow_abbrev=False)
        for option in ('archive', 'directory', 'output'): command.add_argument('--' + option, required=True)
        if name == 'check':
            command.add_argument('--stage', choices=STAGES, required=True)
            for state in ('ram', 'saved'):
                command.add_argument('--' + state, required=True)
                command.add_argument('--' + state + '-roles', type=int, nargs=2, choices=(0, 1), required=True,
                                     metavar=('AP_INDEX', 'CP_INDEX'))
    try: args = parser.parse_args(argv)
    except b.t._Arguments:
        print('Offline settings plan rejected: INVALID_ARGUMENTS', file=sys.stderr); return 2
    try:
        output = program._output_path(args.output, args.directory)
        result = (review_bundle(args.archive, args.directory) if args.command == 'review' else
                  check_files(args.archive, args.directory, stage=args.stage, ram_path=args.ram, saved_path=args.saved,
                              ram_roles=dict(zip(('AP', 'CP'), args.ram_roles)), saved_roles=dict(zip(('AP', 'CP'), args.saved_roles))))
        program._save_report(output, result)
        summary = encoded({'phase': result['phase'], 'write_count': result['settings_contract']['forward']['write_count'],
                           'device_operations_enabled': False}).decode()
        if sys.stdout.write(summary) != len(summary): raise OSError('Incomplete summary output')
        sys.stdout.flush(); return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration, struct.error, zipfile.BadZipFile) as error:
        print('Offline settings plan rejected: ' + type(error).__name__, file=sys.stderr); return 1


if __name__ == '__main__': raise SystemExit(main())
