"""Offline patch calibration and pre-fit, frozen scene acceptance. No device APIs."""
import argparse
from collections import Counter
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

import numpy as np

from ._vendor.sonylooks import calibration, native
from ._vendor.sonylooks.color import prophoto_to_srgb, srgb_decode
from .nativefit import (REGIONS, UPSTREAM, MAX_EVAL_PIXELS, description,
                        evaluate_photo, file_digest, integer, json_bytes, load_candidate,
                        load_project, local_path, publish, read_json, read_masks)
from .io import write_bytes_new


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', value):
        raise ValueError('IDs require 1..64 ASCII letters/digits, hyphen or underscore')
    return value


def identifiers(values, label, *, empty=False):
    if not isinstance(values, list) or not (0 if empty else 1) <= len(values) <= 32:
        raise ValueError('Bounded ID list required: '+label)
    result = [identifier(x) for x in values]
    if len(set(result)) != len(result):
        raise ValueError('Duplicate ID in '+label)
    return result


def positive(value, label):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('Positive finite '+label+' required')
    return value


def fresh(directory):
    if Path(directory).exists() or Path(directory).is_symlink():
        raise ValueError('Output already exists')


def calibrate(path, directory):
    fresh(directory)
    data, source_sha = read_json(path)
    if data.get('schema') != 'a7c2-offline-patch-set/1' or data.get('st_space') != 'sony-st-srgb' or data.get('reference_space') != 'linear-prophoto-d50':
        raise ValueError('Explicit paired ST/linear ProPhoto patch schema required')
    if data.get('material_kind') not in ('synthetic', 'camera-paired-declared'):
        raise ValueError('Declare synthetic or camera-paired-declared material')
    evidence = description(data.get('evidence'), 'patch alignment/development evidence')
    response_evidence = description(data.get('response_evidence'), 'response measurement evidence')
    response_scenes = identifiers(data.get('response_scene_ids'), 'response_scene_ids')
    response = native.validate_response(data.get('response_matrix'))
    threshold = positive(data.get('max_holdout_linear_prophoto_mae'), 'holdout MAE threshold')
    patches = data.get('patches')
    if not isinstance(patches, list) or not 64 <= len(patches) <= 512:
        raise ValueError('Use 64..512 aligned patch pairs, at least 32 per split')
    seen, scenes, observations = set(), {}, {}
    source, target, split = [], [], []
    for patch in patches:
        if not isinstance(patch, dict):
            raise ValueError('Patch object required')
        pid, scene, role = identifier(patch.get('id')), identifier(patch.get('scene')), patch.get('split')
        if pid in seen or role not in ('train', 'holdout'):
            raise ValueError('Distinct patch IDs and explicit train/holdout split required')
        if scene in scenes and scenes[scene] != role:
            raise ValueError('A declared scene cannot cross training and holdout')
        seen.add(pid)
        scenes[scene] = role
        pair = np.asarray([patch.get('st_rgb'), patch.get('linear_prophoto')], dtype=float)
        if pair.shape != (2, 3) or not np.isfinite(pair).all() or np.any((pair < 0) | (pair > 1)):
            raise ValueError('Each aligned patch needs two finite normalized RGB triples')
        key = tuple(pair.ravel())
        if key in observations and observations[key] != role:
            raise ValueError('Identical patch pair leaked across train/holdout')
        observations[key] = role
        source.append(pair[0]); target.append(pair[1]); split.append(0 if role == 'train' else 1)
    if len(scenes) > 32 or min(Counter(split).get(i, 0) for i in (0, 1)) < 32:
        raise ValueError('At most 32 scenes; at least 32 patches in each split')
    if min(Counter(p['scene'] for p in patches).values()) < 32:
        raise ValueError('At least 32 patches per declared calibration scene required')
    source, target, split = np.asarray(source), np.asarray(target), np.asarray(split)
    design = source[split == 0]
    rank = int(np.linalg.matrix_rank(design-design.mean(axis=0)))
    if rank < 3:
        raise ValueError('Training patches need independent color variation, not only a gray ramp')
    model = calibration.fit(source, target, split, response, evidence)
    calibration.validate(model, require_inverse=True)
    held = calibration.inverse_st(source[split == 1], model)
    scene_scores = {}
    for scene, role in scenes.items():
        if role == 'holdout':
            ids = [i for i, p in enumerate(patches) if p['scene'] == scene]
            scene_scores[scene] = {**native.metrics(calibration.inverse_st(source[ids], model), target[ids]),
                                   'samples': len(ids)}
    report = {'schema': 'a7c2-offline-calibration-report/1', 'source_sha256': source_sha,
              'upstream_commit': UPSTREAM, 'material_kind': data['material_kind'],
              'train_scene_ids': sorted(s for s in scenes if scenes[s] == 'train'),
              'holdout_scene_ids': sorted(s for s in scenes if scenes[s] == 'holdout'),
              'response_scene_ids': response_scenes, 'response_evidence': response_evidence,
              'response_origin': 'supplied independently; not estimated from these patch pairs',
              'split_counts': {'train': int(np.sum(split == 0)), 'holdout': int(np.sum(split == 1))},
              'training_color_rank': rank, 'holdout': native.metrics(held, target[split == 1]),
              'holdout_scenes': scene_scores, 'algorithm_iterations': 12,
              'acceptance': {'max_holdout_linear_prophoto_mae': threshold,
                             'passed': all(s['rgb_mae'] <= threshold for s in scene_scores.values())},
              'scene_identity': 'declared IDs only; physical independence not verified',
              'actual_camera_accuracy_verified': False}
    model['offline_calibration'] = report
    # The complete model retains the report and source hash without original paths/pairs.
    publish(directory, {'model.json': lambda f: f.write(json_bytes(model)),
                        'calibration.json': lambda f: f.write(json_bytes(report))})
    return report


def criterion(value):
    if not isinstance(value, dict) or set(value) != {'min_samples', 'max_rgb_mae', 'max_delta_e76_p95'}:
        raise ValueError('Each criterion needs min_samples, RGB MAE and Delta E76 P95 limits')
    integer(value['min_samples'], 1, 65536, 'min_samples')
    positive(value['max_rgb_mae'], 'RGB MAE threshold')
    positive(value['max_delta_e76_p95'], 'Delta E76 P95 threshold')
    return value


def snapshot(project_path, manifest_path):
    from .images import read_srgb
    _, provenance, _, _, _ = load_project(project_path)
    project, _ = read_json(project_path)
    model, _ = read_json(local_path(Path(project_path).parent, project['calibration']))
    data, manifest_sha = read_json(manifest_path)
    if data.get('schema') != 'a7c2-offline-scene-set/1' or data.get('material_kind') not in ('synthetic', 'camera-st-declared'):
        raise ValueError('Explicit offline scene set and material kind required')
    description(data.get('evidence'), 'scene evidence')
    required = identifiers(data.get('required_scene_ids'), 'required_scene_ids')
    excluded = identifiers(data.get('excluded_scene_ids'), 'excluded_scene_ids', empty=True)
    calibration_info = model.get('offline_calibration', {})
    if not isinstance(calibration_info, dict):
        raise ValueError('offline_calibration metadata must be an object')
    calibration_scenes = set()
    for key in ('train_scene_ids', 'holdout_scene_ids', 'response_scene_ids'):
        calibration_scenes.update(identifiers(calibration_info.get(key, []), key, empty=True))
    if calibration_scenes-set(excluded) or set(required) & set(excluded):
        raise ValueError('Exclude all declared calibration/response scenes; evaluation IDs must be disjoint')
    thresholds = data.get('thresholds')
    if not isinstance(thresholds, dict) or set(thresholds) != {'overall', 'regions', 'max_bounded_coefficients', 'max_native_clip_fraction'}:
        raise ValueError('Declare overall/region, coefficient and clipping limits before fitting')
    criterion(thresholds['overall'])
    regions = thresholds['regions']
    if not isinstance(regions, dict) or set(regions) != set(REGIONS):
        raise ValueError('Declare thresholds for all seven explicit regions')
    for value in regions.values():
        criterion(value)
    integer(thresholds['max_bounded_coefficients'], 0, 1215, 'max_bounded_coefficients')
    fraction = thresholds['max_native_clip_fraction']
    if type(fraction) not in (int, float) or not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError('Clipping fraction must be finite 0..1')
    entries = data.get('scenes')
    if not isinstance(entries, list) or not 1 <= len(entries) <= 16:
        raise ValueError('Provide 1..16 scene images; absent required scenes remain gaps')
    frozen, seen, photo_hashes = [], set(), set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Scene object required')
        sid = identifier(entry.get('id'))
        if sid in seen or sid not in required or entry.get('st_input') is not True:
            raise ValueError('Distinct required scene IDs and explicit st_input=true required')
        seen.add(sid)
        if type(entry.get('assume_srgb', False)) is not bool:
            raise ValueError('assume_srgb must be boolean')
        source = local_path(Path(manifest_path).parent, entry.get('input'))
        source_sha = file_digest(source)
        if source_sha in photo_hashes:
            raise ValueError('Duplicate photo bytes cannot represent independent scenes')
        photo_hashes.add(source_sha)
        image, interpretation = read_srgb(source, assume_srgb=entry.get('assume_srgb', False))
        if image.width*image.height > MAX_EVAL_PIXELS:
            raise ValueError('Scene evaluation limit is 4 million pixels')
        mask_path = local_path(Path(manifest_path).parent, entry['masks']) if 'masks' in entry else None
        masks_sha = read_json(mask_path)[1] if mask_path else None
        masks = read_masks(mask_path, image.size)
        if file_digest(source) != source_sha or mask_path and read_json(mask_path)[1] != masks_sha:
            raise ValueError('Scene changed while freezing')
        frozen.append({'id': sid, 'input_sha256': source_sha, 'dimensions': list(image.size),
                       'input_interpretation': interpretation, 'masks_manifest_sha256': masks_sha,
                       'mask_sha256': {k: v['sha256'] for k, v in masks.items()}})
    return {'project_provenance': provenance, 'manifest_sha256': manifest_sha,
            'material_kind': data['material_kind'], 'evidence': data['evidence'],
            'required_scene_ids': required, 'excluded_scene_ids': excluded,
            'missing_scene_ids': sorted(set(required)-seen), 'scenes': frozen, 'thresholds': thresholds,
            'calibration_acceptance': calibration_info.get('acceptance'),
            'actual_camera_accuracy_verified': False}


def freeze(project_path, manifest_path, output):
    fresh(output)
    frozen = snapshot(project_path, manifest_path)
    result = {'schema': 'a7c2-offline-validation-lock/1', 'snapshot': frozen,
              'manifest': os.path.relpath(Path(manifest_path).resolve(), Path(output).parent.resolve()),
              'purpose': 'pre-fit reproducibility contract; not a signature or chronology proof'}
    write_bytes_new(output, json_bytes(result))
    return result


def validate_lock(project_path, path):
    lock, sha = read_json(path)
    if lock.get('schema') != 'a7c2-offline-validation-lock/1':
        raise ValueError('Pre-fit validation lock schema required')
    manifest = local_path(Path(path).parent, lock.get('manifest'))
    if lock.get('snapshot') != snapshot(project_path, manifest):
        raise ValueError('Frozen project/model/scene/threshold provenance changed')
    return lock, sha, manifest


def assess(score, rule):
    if not score.get('available'):
        return {'status': 'unavailable', 'passed': False}
    if score['samples'] < rule['min_samples']:
        return {'status': 'insufficient_samples', 'passed': False}
    passed = score['rgb_mae'] <= rule['max_rgb_mae'] and score['delta_e76_p95'] <= rule['max_delta_e76_p95']
    return {'status': 'passed' if passed else 'failed_threshold', 'passed': passed}


def benchmark(project_path, candidate_path, lock_path, directory):
    fresh(directory)
    lock, lock_sha, manifest_path = validate_lock(project_path, lock_path)
    _, coefficients, _, _, _ = load_candidate(project_path, candidate_path)
    candidate, candidate_sha = read_json(candidate_path)
    if candidate.get('validation_lock_sha256') != lock_sha:
        raise ValueError('Candidate was not fitted with this validation lock; refit explicitly')
    manifest, _ = read_json(manifest_path)
    rules = lock['snapshot']['thresholds']
    directory = Path(directory)
    directory.parent.mkdir(parents=True, exist_ok=True)
    reports, exports = {}, {}
    with tempfile.TemporaryDirectory(prefix='.native-validation-', dir=directory.parent) as tmp:
        for entry in manifest['scenes']:
            sid = entry['id']
            base = Path(manifest_path).parent
            result = evaluate_photo(project_path, candidate_path, local_path(base, entry['input']), Path(tmp)/sid,
                                    st_input=True, assume_srgb=entry.get('assume_srgb', False),
                                    masks_path=local_path(base, entry['masks']) if 'masks' in entry else None)
            frozen_scene = next(s for s in lock['snapshot']['scenes'] if s['id'] == sid)
            actual_masks = {k: v['mask_sha256'] for k, v in result['regions'].items() if 'mask_sha256' in v}
            if (result['input_sha256'] != frozen_scene['input_sha256'] or
                    result['candidate_sha256'] != candidate_sha or actual_masks != frozen_scene['mask_sha256']):
                raise ValueError('Rendered scene/candidate does not match frozen inputs')
            result['criteria'] = {'overall': assess(result['overall'], rules['overall']),
                                  'regions': {k: assess(result['regions'][k], rules['regions'][k]) for k in REGIONS}}
            fraction = result['native_clipped_channels_full_image']/result['native_clip_channel_denominator']
            result['criteria']['clipping'] = {'fraction': fraction, 'passed': fraction <= rules['max_native_clip_fraction']}
            reports[sid] = result
            for name in ('reference.png', 'prediction.png'):
                source = Path(tmp)/sid/name
                def copy(f, source=source):
                    with source.open('rb') as incoming:
                        shutil.copyfileobj(incoming, f)
                exports[sid+'-'+name] = copy
        # Verify again before publishing, including lock, table, candidate and all inputs.
        if validate_lock(project_path, lock_path)[1] != lock_sha or read_json(candidate_path)[1] != candidate_sha:
            raise ValueError('Validation inputs changed during benchmark')
        load_candidate(project_path, candidate_path)
        coverage = {}
        for name in REGIONS:
            available = [sid for sid, r in reports.items() if r['regions'][name].get('available')]
            valid = [reports[sid]['criteria']['regions'][name]['passed'] for sid in available]
            coverage[name] = {'available_scene_ids': available, 'missing_scene_ids': [s for s in reports if s not in available],
                              'passed': bool(available) and all(valid)}
        converged = candidate.get('fitting', {}).get('convergence', {}).get('converged') is True
        bounded = int(np.count_nonzero((coefficients == -64) | (coefficients == 63)))
        calibration_passed = lock['snapshot']['calibration_acceptance']
        # A legacy response-only model is usable for comparison, but lacks patch validation.
        model_gate = isinstance(calibration_passed, dict) and calibration_passed.get('passed') is True
        passed = (not lock['snapshot']['missing_scene_ids'] and model_gate and converged and
                  bounded <= rules['max_bounded_coefficients'] and all(x['passed'] for x in coverage.values()) and
                  all(r['criteria']['overall']['passed'] and r['criteria']['clipping']['passed'] for r in reports.values()))
        result = {'schema': 'a7c2-offline-scene-benchmark/1', 'validation_lock_sha256': lock_sha,
                  'candidate_sha256': candidate_sha, 'material_kind': manifest['material_kind'],
                  'scope': 'model/reference comparisons; declared scene identities only',
                  'criteria': rules, 'scenes': reports, 'region_coverage': coverage,
                  'missing_scene_ids': lock['snapshot']['missing_scene_ids'],
                  'model_patch_acceptance_passed': model_gate, 'fit_converged': converged,
                  'bounded_coefficients': bounded, 'acceptance': {'passed': bool(passed)},
                  'aggregation': 'per-scene thresholds; no pooled or averaged P95',
                  'actual_camera_accuracy_verified': False}
        exports['benchmark.json'] = lambda f: f.write(json_bytes(result))
        publish(directory, exports)
    return result


def fixtures(directory):
    from PIL import Image
    from .nativefit import fixtures as base_fixtures
    from .images import srgb_profile
    directory = Path(directory)
    base_fixtures(directory)
    rng = np.random.default_rng(311)
    rgb = rng.uniform(.05, .95, (128, 3))
    linear = srgb_decode(rgb) @ np.linalg.inv(prophoto_to_srgb()).T
    patches = {'schema': 'a7c2-offline-patch-set/1', 'material_kind': 'synthetic',
               'st_space': 'sony-st-srgb', 'reference_space': 'linear-prophoto-d50',
               'evidence': 'Self-generated paired samples; synthetic sRGB transfer only',
               'response_evidence': 'Synthetic unit response, not measured from a camera',
               'response_scene_ids': ['response-demo'], 'response_matrix': np.eye(3).tolist(),
               'max_holdout_linear_prophoto_mae': .02,
               'patches': [{'id': f'p{i}', 'scene': 'patch-train' if i < 64 else 'patch-holdout',
                            'split': 'train' if i < 64 else 'holdout', 'st_rgb': np.round(rgb[i], 8).tolist(),
                            'linear_prophoto': np.round(linear[i], 8).tolist()} for i in range(128)]}
    write_bytes_new(directory/'patches.json', json_bytes(patches))
    project, _ = read_json(directory/'project.json')
    project['calibration'] = 'calibrated/model.json'
    write_bytes_new(directory/'validation-project.json', json_bytes(project))
    scenes = []
    colors = np.array([[.65, .45, .35], [.5, .5, .5], [.2, .6, .2], [.3, .6, .9],
                       [.9, .9, .9], [.08, .08, .08], [.9, .1, .8]])
    for n in range(2):
        sid = f'scene-{n+1}'
        image = np.repeat(np.repeat(np.clip(colors+n*.01, 0, 1), 8, axis=0)[None, :, :], 32, axis=0)
        Image.fromarray(np.floor(image*255+.5).astype('uint8')).save(directory/(sid+'.png'), icc_profile=srgb_profile())
        regions = {}
        for i, name in enumerate(REGIONS):
            mask = np.zeros((32, 56), dtype='uint8'); mask[:, i*8:(i+1)*8] = 255
            filename = sid+'-'+name+'.png'
            Image.fromarray(mask).save(directory/filename)
            regions[name] = filename
        write_bytes_new(directory/(sid+'-masks.json'), json_bytes({'schema': 'a7c2-offline-region-masks/1', 'regions': regions}))
        scenes.append({'id': sid, 'input': sid+'.png', 'masks': sid+'-masks.json', 'st_input': True})
    rule = {'min_samples': 32, 'max_rgb_mae': .005, 'max_delta_e76_p95': 2.}
    manifest = {'schema': 'a7c2-offline-scene-set/1', 'material_kind': 'synthetic',
                'evidence': 'Two synthetic color charts; labels demonstrate masks, not real scene diversity',
                'required_scene_ids': ['scene-1', 'scene-2'],
                'excluded_scene_ids': ['patch-train', 'patch-holdout', 'response-demo'],
                'thresholds': {'overall': rule, 'regions': {k: rule for k in REGIONS},
                               'max_bounded_coefficients': 0, 'max_native_clip_fraction': .01}, 'scenes': scenes}
    write_bytes_new(directory/'scenes.json', json_bytes(manifest))
    return {'synthetic_only': True, 'actual_camera_accuracy_verified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('fixtures'); demo.add_argument('--directory', type=Path, required=True)
    cal = sub.add_parser('calibrate'); cal.add_argument('--patches', type=Path, required=True); cal.add_argument('--directory', type=Path, required=True)
    frozen = sub.add_parser('freeze'); frozen.add_argument('--project', type=Path, required=True); frozen.add_argument('--manifest', type=Path, required=True); frozen.add_argument('--output', type=Path, required=True)
    bench = sub.add_parser('benchmark')
    for name in ('project', 'candidate', 'validation-lock', 'directory'):
        bench.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'fixtures': result = fixtures(args.directory)
        elif args.command == 'calibrate': result = calibrate(args.patches, args.directory)
        elif args.command == 'freeze': result = freeze(args.project, args.manifest, args.output)
        else: result = benchmark(args.project, args.candidate, args.validation_lock, args.directory)
        print(json_bytes(result).decode(), end='')
        return 0
    except (ValueError, OSError, TypeError, KeyError, np.linalg.LinAlgError) as e:
        print('STOPPED: '+str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
