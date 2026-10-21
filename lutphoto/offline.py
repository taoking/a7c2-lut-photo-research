"""One offline CUBE-to-private-bundle workflow; no camera or device executor.

QAQLeonard/ma1co algorithm and layout provenance: ACKNOWLEDGEMENTS.md.
demo generates every source itself; build accepts only the pinned real policy.
"""
import os
import struct
import sys
import zipfile

from . import settingsplan as settings
from .capturestore import _parent, _private, _same, encoded
from .io import write_bytes_new

b, program, names = settings.b, settings.program, settings.names


def _new_root(directory):
    path = b._new_directory(directory)
    path, parent = _parent(path)
    try:
        os.mkdir(path.name, 0o700, dir_fd=parent)
        fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            _private(os.fstat(fd), True)
            if not _same(os.fstat(fd), os.stat(path.name, dir_fd=parent, follow_symlinks=False)):
                raise ValueError('New output directory changed')
            os.fsync(fd); os.fsync(parent)
        finally: os.close(fd)
    finally: os.close(parent)
    return path


def _fit(root, project, photo, *, assume_srgb=False, masks=None, validation_lock=None):
    from . import nativefit as nf
    nf.fit(project, root / 'candidate', validation_lock=validation_lock)
    evaluation = nf.evaluate_photo(project, root / 'candidate/candidate.json', photo, root / 'evaluation',
                                   st_input=True, assume_srgb=assume_srgb, masks_path=masks)
    candidate, _ = nf.read_json(root / 'candidate/candidate.json')
    if not candidate['acceptance']['passed'] or not evaluation['acceptance']['passed']:
        raise ValueError('Declared offline reference thresholds failed; partial output retained')
    return evaluation


def _fit_binding(root, project, photo, inputs, evaluation, validation_lock):
    from . import nativefit as nf
    # Match the frozen candidate to the explicit project/model and rendered image,
    # rather than accepting a loose N2 JSON alongside an unrelated private bundle.
    _, _, _, _, candidate_sha = nf.load_candidate(project, root / 'candidate/candidate.json')
    candidate, _ = nf.read_json(root / 'candidate/candidate.json')
    if (candidate_sha != program.w.sha(inputs.candidate) or
            evaluation['candidate_sha256'] != candidate_sha or
            nf.file_digest(photo) != evaluation['input_sha256']):
        raise ValueError('Fit, frozen bundle or reference image changed')
    if validation_lock is not None:
        from .nativevalidate import validate_lock
        if validate_lock(project, validation_lock)[1] != candidate.get('validation_lock_sha256'):
            raise ValueError('Validation lock changed after fitting')
    return {'candidate_sha256': candidate_sha, 'table_sha256': program.w.sha(inputs.table),
            'provenance': candidate['provenance'], 'fitting': candidate['fitting'],
            'synthetic_holdout': candidate['synthetic_holdout'], 'acceptance': candidate['acceptance'],
            'image_comparison': evaluation, 'actual_camera_accuracy_verified': False}


def _combine(policy, inputs, review, binding, fit, *, synthetic, source_pin_checked, root):
    ph, pc = program._metadata(review)
    nh, nc = names._metadata(inputs, review, binding)
    contract, before, after = settings._build(policy, inputs, review, binding)
    chain = contract['chain']
    if (chain['program_contract_sha256'] != program.w.sha(encoded(pc)) or
            chain['names_contract_sha256'] != program.w.sha(encoded(nc))):
        raise ValueError('Combined worker/settings contracts differ')
    stages = {}
    if synthetic:
        from ._offlinedemo import encode_snapshot
        (root / 'observations').mkdir(mode=0o700)
        for stage in settings.STAGES:
            expected = after if stage == 'target' else before
            stages[stage] = {}
            for state in ('ram', 'saved'):
                path = root / 'observations' / (stage + '-' + state + '.bin')
                write_bytes_new(path, encode_snapshot(expected[state]))
                observed, _ = settings._snapshot(b.c.bounded_read(path, settings.bk4.MAX_SNAPSHOT), {'AP': 0, 'CP': 1})
                stages[stage][state] = settings._check_snapshot(expected[state], observed)
    return {**program.w.boundary(), 'schema': 'a7c2-unified-offline-result/1',
            'phase': 'OFFLINE_REVIEW_COMPLETE', 'private_report': True,
            'material_kind': 'self-generated-demo' if synthetic else 'owner-files-unverified-origin',
            'synthetic_only': synthetic, 'production_program_identity_checked': not synthetic,
            'fixed_archive_and_worker_sources_checked': source_pin_checked,
            'same_capture_provenance_verified': False, **binding, 'fit': fit, 'bundle': b._summary(review),
            'program_worker': program._report(policy, review, binding, ph, pc),
            'name_worker': names._result(policy, binding, nh, nc),
            'settings': settings._result(policy, binding, contract),
            'selfmade_snapshot_stage_checks': stages, 'actual_snapshot_stages_verified': False,
            'program_and_resource_inverse_checked_offline': True,
            'decoded_settings_inverse_checked_offline': True, 'restore_verified': False,
            'actual_camera_accuracy_verified': False, 'device_operations_enabled': False,
            'device_executor_enabled': False, 'compiled_offline': False,
            'missing_evidence': ['Real SDK and owner capture on exactly supported firmware',
                                 'Same-camera identity, freshness and all 68 resources',
                                 'Actual deployment, unit read/write/save, cold start and recovery',
                                 'Independent Sony ST calibration and paired photographic acceptance']}


def _finish(root, result):
    score = result['fit']['image_comparison']['overall']
    count = result['settings']['settings_contract']['forward']['write_count']
    kind = '全部自制；不是本人机身材料，也不是 Sony ST 标定' if result['synthetic_only'] else '本人显式提供；完整程序身份通过，同机来源/新鲜度未证'
    text = f'''# 离线流程结果

材料：{kind}。

CUBE → 1,215 字节原生表 → 参考图/预测误差 → 单槽私人包 → 程序/名称/设置方案 → 离线逆向核对已完成。

| 检查 | 本次结果 |
| --- | --- |
| 原 LUT 与原生预测 | RGB MAE {score['rgb_mae']:.8g}；Delta E76 P95 {score['delta_e76_p95']:.8g} |
| 事先声明的离线阈值 | 拟合留出与本图比较均通过；不代表摄影质量 |
| 单槽包 | {result['bundle']['payload_files']} 份材料重新读回/重建；槽 {result['bundle']['selected_slot']} |
| 程序与 68 份名称资源 | 目标与精确逆向在电脑检查通过 |
| 设置 | 9 个属性；计划改变 {count} 个；全解码映射的虚拟逆向通过 |
| 实际相机、保存、恢复、色彩验收 | 未验证；无设备操作/执行器；未生成完整 BK4 目标 |

[原 LUT 参考图](evaluation/reference.png) · [原生表预测图](evaluation/prediction.png) · [分区误差](evaluation/comparison.json)

程序/名称元数据及设置单元方案、处理顺序和缺口保存在 result.private.json。图像输入中的 ST 身份为声明；自制图只演示数学流程。未给出的分区没有得分，不推断肤色/高光质量。报告结构、解码逆向与顺序要求均不证明实际执行、资源读回、所有运行组保留或恢复。

目录含私人程序/快照/设置/名称/逆向，整份保留在私人位置，不上传 GitHub 或聊天。异常时保留部分目录，不覆盖、不续跑；重新离线演练使用新目录。
'''
    program._save_report(program._output_path(root / 'result.private.json', root / 'bundle'), result)
    write_bytes_new(root / 'RESULT.md', text.encode())
    return result


def demo(directory):
    """No user program/archive input and no way to review an arbitrary demo bundle."""
    from ._offlinedemo import create_input, materials
    root = _new_root(directory)
    create_input(root / 'input')
    project, photo = root / 'input/demo-project.json', root / 'input/chart.png'
    evaluation = _fit(root, project, photo)
    candidate = b.c.bounded_read(root / 'candidate/candidate.json', b.m.MAX_JSON_FILE)
    table = b.c.bounded_read(root / 'candidate/correction.table', 1215)
    policy, runtime, inputs = materials(candidate, table)
    review = b.t._generate(policy, runtime, inputs)
    b._freeze(root / 'bundle', policy, inputs, review)
    del inputs, review
    with b._read_frozen(root / 'bundle', policy) as (inputs, observed, binding, check):
        review = b._regenerate(policy, runtime, inputs, observed)
        check()
        binding = {**binding, 'target_review_sha256': review.report['target_review_sha256']}
        fit = _fit_binding(root, project, photo, inputs, evaluation, None)
        result = _combine(policy, inputs, review, binding, fit, synthetic=True, source_pin_checked=False, root=root)
    return _finish(root, result)


def build(archive, directory, *, project, photo, st_input, slot, name, ap_path, cp_path,
          ram_path, saved_path, resources_path, ram_roles, saved_roles, assume_srgb=False,
          masks=None, validation_lock=None):
    if st_input is not True: raise ValueError('Explicit ST input declaration required')
    selection = encoded({'schema': b.m.SELECTION, 'slots': {str(slot): {'candidate': 'candidate', 'name': name}}})
    b.m._selection_bytes(selection)
    if type(slot) is not int: raise ValueError('Integer slot required')
    # Reject unsupported/unknown owner programs and settings before expensive fit
    # or creating output. create/open below independently repeat their own gates.
    policy = b.p._load_policy(archive)
    program._sources(archive, policy)
    b.t.s.check_files(archive, ap_path, cp_path, ram_path, saved_path, [slot], ram_roles, saved_roles)
    root = _new_root(directory)
    evaluation = _fit(root, project, photo, assume_srgb=assume_srgb, masks=masks, validation_lock=validation_lock)
    selection_path = root / 'selection.private.json'; write_bytes_new(selection_path, selection)
    b.create(archive, root / 'bundle', ap_path=ap_path, cp_path=cp_path, ram_path=ram_path, saved_path=saved_path,
             selection_path=selection_path, resources_path=resources_path, ram_roles=ram_roles, saved_roles=saved_roles)
    with b._open_bundle(archive, root / 'bundle') as (policy, inputs, review, binding):
        program._sources(archive, policy)
        fit = _fit_binding(root, project, photo, inputs, evaluation, validation_lock)
        result = _combine(policy, inputs, review, binding, fit, synthetic=False, source_pin_checked=True, root=root)
    return _finish(root, result)


def main(argv=None):
    parser = b.t._Parser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True, parser_class=b.t._Parser)
    for command in ('demo', 'build'):
        sub = commands.add_parser(command, allow_abbrev=False)
        sub.add_argument('--directory', required=True)
        if command == 'build':
            for option in ('archive', 'project', 'input', 'ap', 'cp', 'ram', 'saved', 'resources', 'name'):
                sub.add_argument('--' + option, required=True)
            sub.add_argument('--slot', required=True, type=int, choices=range(1, 7))
            sub.add_argument('--st-input', required=True, action='store_true')
            sub.add_argument('--assume-srgb', action='store_true')
            sub.add_argument('--masks'); sub.add_argument('--validation-lock')
            for state in ('ram', 'saved'):
                sub.add_argument('--' + state + '-roles', type=int, nargs=2, choices=(0, 1), required=True)
    try: args = parser.parse_args(argv)
    except b.t._Arguments:
        print('Unified offline workflow rejected: INVALID_ARGUMENTS', file=sys.stderr); return 2
    try:
        if args.command == 'demo': result = demo(args.directory)
        else:
            result = build(args.archive, args.directory, project=args.project, photo=args.input, st_input=args.st_input,
                           slot=args.slot, name=args.name, ap_path=args.ap, cp_path=args.cp, ram_path=args.ram,
                           saved_path=args.saved, resources_path=args.resources,
                           ram_roles=dict(zip(('AP', 'CP'), args.ram_roles)), saved_roles=dict(zip(('AP', 'CP'), args.saved_roles)),
                           assume_srgb=args.assume_srgb, masks=args.masks, validation_lock=args.validation_lock)
        raw = encoded({key: result[key] for key in ('schema', 'phase', 'synthetic_only', 'device_operations_enabled')}).decode()
        if sys.stdout.write(raw) != len(raw): raise OSError('Incomplete summary output')
        sys.stdout.flush(); return 0
    except (ValueError, OSError, KeyError, TypeError, ImportError, StopIteration, struct.error, zipfile.BadZipFile) as error:
        print('Unified offline workflow rejected: ' + type(error).__name__ + '; preserve partial output', file=sys.stderr)
        return 1


if __name__ == '__main__': raise SystemExit(main())
