"""Bounded, device-independent CUBE/native-table fitting and reference rendering."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

from ._vendor.sonylooks import native
from .cube import load_cube, evaluate
from .io import write_bytes_new, write_new
from .native_metrics import compare

SCHEMA = 'a7c2-offline-native-project/1'
CANDIDATE = 'a7c2-offline-native-candidate/1'
UPSTREAM = '7e54d60b458847f1befa6cfd614fbf004b8b0b90'
REGIONS = ('skin', 'gray', 'green', 'sky', 'highlights', 'shadows', 'saturated')
MAX_JSON = 128 * 1024
MAX_EVAL_PIXELS = 4_000_000
MAX_METRIC_SAMPLES = 65536


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()


def read_json(path):
    with Path(path).open('rb') as f:
        raw = f.read(MAX_JSON+1)
    if len(raw) > MAX_JSON:
        raise ValueError('JSON exceeds 128 KiB')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: '+key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Nonfinite JSON number: '+value)
    try:
        data = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique,
                          parse_constant=invalid)
    except (UnicodeError, RecursionError) as e:
        raise ValueError('Invalid JSON encoding or nesting') from e
    if not isinstance(data, dict):
        raise ValueError('JSON object required')
    return data, digest(raw)


def description(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 2048 or any(ord(c) < 32 for c in value):
        raise ValueError('Nonempty bounded '+label+' required')
    try:
        value.encode('utf-8')
    except UnicodeError as e:
        raise ValueError('Invalid Unicode in '+label) from e
    return value


def local_path(base, value):
    description(value, 'local file path')
    return base / value


def integer(value, lower, upper, label):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f'{label} must be an integer {lower}..{upper}')
    return value


def load_project(path):
    path = Path(path)
    project, project_sha = read_json(path)
    if project.get('schema') != SCHEMA or project.get('base') != 'ST':
        raise ValueError('Offline project schema 1 and explicit base ST required')
    calibration, calibration_sha = read_json(local_path(path.parent, project.get('calibration')))
    if calibration.get('schema') != 'a7c2-look-calibration/1' or calibration.get('coordinate_model') != 'bt601-limited-provisional':
        raise ValueError('Explicit provisional ST calibration schema required')
    evidence = description(calibration.get('evidence'), 'calibration evidence')
    if calibration.get('full_camera_characterization') is not False:
        raise ValueError('This adapter supports provisional models only')
    response = native.validate_response(calibration.get('response_matrix'))
    source = project.get('source')
    if not isinstance(source, dict) or source.get('type') != 'cube':
        raise ValueError('This offline adapter currently accepts CUBE only')
    attribution = description(source.get('attribution'), 'source attribution/license')
    space = description(source.get('input_space'), 'LUT input space')
    if source.get('output_space') != 'srgb':
        raise ValueError('Reference output must explicitly be encoded sRGB')
    policy = source.get('domain_policy')
    if policy not in ('reject', 'clip-and-report'):
        raise ValueError('Explicit domain_policy reject or clip-and-report required')
    cube = load_cube(local_path(path.parent, source.get('path')))
    # No hidden output clipping. Normalize HDR/Log outputs in a reviewed reference first.
    if np.any((np.asarray(cube.rows) < 0) | (np.asarray(cube.rows) > 1)):
        raise ValueError('Reference CUBE outputs must be normalized to 0..1 sRGB')
    bridge = None
    bridge_meta = None
    if space == 'sony-st-srgb':
        if 'bridge' in source:
            raise ValueError('Direct ST input must not also specify a bridge')
    else:
        contract = source.get('bridge')
        if not isinstance(contract, dict) or contract.get('input_space') != 'sony-st-srgb' or contract.get('output_space') != space:
            raise ValueError('Non-ST LUT needs an explicit matching ST-to-input bridge')
        bridge_evidence = description(contract.get('evidence'), 'bridge evidence')
        bridge = load_cube(local_path(path.parent, contract.get('path')))
        bridge_meta = {'sha256': bridge.sha256, 'evidence': bridge_evidence,
                       'input_space': 'sony-st-srgb', 'output_space': space}
    seed = integer(project.get('seed', 201), 0, 2**32-1, 'seed')
    count = integer(project.get('training_samples', 12000), 512, 50000, 'training_samples')
    thresholds = project.get('thresholds')
    if not isinstance(thresholds, dict) or set(thresholds) != {'max_rgb_mae', 'max_delta_e76_p95'}:
        raise ValueError('Declare RGB MAE and Delta E76 P95 thresholds before fitting')
    for key, value in thresholds.items():
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError('Positive finite threshold required: '+key)
    meta = {'project_sha256': project_sha, 'calibration_sha256': calibration_sha,
            'calibration_evidence': evidence, 'coordinate_model': calibration['coordinate_model'],
            'response_matrix': response.tolist(), 'reference_sha256': cube.sha256,
            'attribution': attribution, 'input_space': space, 'output_space': 'srgb',
            'domain_policy': policy, 'bridge': bridge_meta}
    return Reference(cube, bridge, response, policy), meta, seed, count, thresholds


class Reference:
    def __init__(self, cube, bridge, response, policy):
        self.cube, self.bridge, self.response, self.policy = cube, bridge, response, policy
        self.clipped_rows = {'bridge_input': 0, 'lut_input': 0}
        self.rendered_rows = 0

    def sample(self, cube, rgb, stage):
        outside = np.any((rgb < cube.domain_min) | (rgb > cube.domain_max), axis=1)
        count = int(np.count_nonzero(outside))
        if count and self.policy == 'reject':
            raise ValueError(f'{stage}: {count} rows outside declared CUBE domain')
        self.clipped_rows[stage] += count
        return evaluate(cube, rgb)

    def __call__(self, rgb):
        rgb = np.asarray(rgb, dtype=float)
        if rgb.ndim != 2 or rgb.shape[1] != 3 or not np.isfinite(rgb).all() or np.any((rgb < 0) | (rgb > 1)):
            raise ValueError('Reference requires normalized finite ST RGB rows')
        self.rendered_rows += len(rgb)
        if self.bridge is not None:
            rgb = self.sample(self.bridge, rgb, 'bridge_input')
        return self.sample(self.cube, rgb, 'lut_input')


def limits(report, thresholds):
    return {'thresholds_declared_before_holdout': thresholds,
            'passed': report['rgb_mae'] <= thresholds['max_rgb_mae'] and
                      report['delta_e76_p95'] <= thresholds['max_delta_e76_p95'],
            'scope': 'offline reference comparison only; not camera acceptance'}


def publish(directory, files):
    """Reserve a fresh directory, write exclusively, clean only our own files on failure."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    written = []
    try:
        for name, writer in files.items():
            target = directory/name
            write_new(target, writer)
            written.append(target)
    except BaseException:
        for target in written:
            target.unlink()
        directory.rmdir()
        raise


def fit(project_path, directory, *, validation_lock=None):
    if Path(directory).exists() or Path(directory).is_symlink():
        raise ValueError('Output directory already exists')
    reference, provenance, seed, count, thresholds = load_project(project_path)
    lock_sha = None
    if validation_lock is not None:
        from .nativevalidate import validate_lock
        lock_sha = validate_lock(project_path, validation_lock)[1]
    raw, fitting = native.fit_reference(reference, reference.response, seed=seed, count=count)
    coefficients = native.decode(raw)
    # Reconstruct the untouched upstream split exactly; no holdout affects selection.
    rng = np.random.default_rng(seed)
    rng.uniform(.015, .985, (count, 3))
    rng.uniform(.015, .985, (2048, 3))
    testing = rng.uniform(.015, .985, (4096, 3))
    expected = reference(testing)
    prediction = native.predict(testing, coefficients, reference.response)
    score = compare(prediction, expected)
    grays = np.repeat(np.linspace(0, 1, 513)[:, None], 3, axis=1)
    gray_score = compare(native.predict(grays, coefficients, reference.response), reference(grays))
    from .native_metrics import lab_d65
    gray_prediction = native.predict(grays, coefficients, reference.response)
    gray_target = reference(grays)
    neutrality = {}
    for label, rgb in (('reference', gray_target), ('prediction', gray_prediction)):
        chroma = np.linalg.norm(lab_d65(rgb)[:, 1:], axis=1)
        neutrality[label] = {'mean_lab_chroma': float(chroma.mean()), 'max_lab_chroma': float(chroma.max())}
    result = {'schema': CANDIDATE, 'adapter_version': 1, 'upstream_commit': UPSTREAM,
              'provenance': provenance, 'table': {'file': 'correction.table', 'bytes': len(raw),
              'sha256': digest(raw), 'layout': 'Y/C1/C2 planes; 5x9x9; signed -64..63'},
              'fitting': fitting, 'synthetic_holdout': score, 'gray_ramp_reference_error': gray_score,
              'gray_ramp_neutrality': neutrality,
              'domain_clipping': reference.clipped_rows, 'reference_rows_evaluated': reference.rendered_rows,
              'acceptance': limits(score, thresholds), 'actual_camera_accuracy_verified': False,
              'device_integration_enabled': False, 'not_a_firmware_image': True,
              'missing_evidence': ['Independent Sony ST camera calibration',
                                   'Paired camera photos and independent scenes',
                                   'Camera preview/JPEG/playback consistency']}
    if validation_lock is not None:
        if validate_lock(project_path, validation_lock)[1] != lock_sha:
            raise ValueError('Validation lock changed while fitting')
        result['validation_lock_sha256'] = lock_sha
    publish(directory, {'correction.table': lambda f: f.write(raw),
                        'candidate.json': lambda f: f.write(json_bytes(result))})
    return result


def load_candidate(project_path, candidate_path):
    reference, provenance, seed, _, thresholds = load_project(project_path)
    candidate, candidate_sha = read_json(candidate_path)
    table = candidate.get('table', {})
    if candidate.get('schema') != CANDIDATE or candidate.get('adapter_version') != 1 or candidate.get('upstream_commit') != UPSTREAM or candidate.get('provenance') != provenance:
        raise ValueError('Candidate/project/model provenance mismatch; refit explicitly')
    if table.get('file') != 'correction.table' or table.get('bytes') != native.RAW_BYTES:
        raise ValueError('Invalid candidate table descriptor')
    with Path(candidate_path).with_name('correction.table').open('rb') as f:
        raw = f.read(native.RAW_BYTES+1)
    if len(raw) != native.RAW_BYTES or digest(raw) != table.get('sha256'):
        raise ValueError('Candidate table length/hash mismatch')
    if candidate.get('acceptance', {}).get('thresholds_declared_before_holdout') != thresholds:
        raise ValueError('Threshold mismatch')
    return reference, native.decode(raw), seed, thresholds, candidate_sha


def read_masks(path, size):
    from PIL import Image
    if path is None:
        return {}
    data, _ = read_json(path)
    if data.get('schema') != 'a7c2-offline-region-masks/1' or not isinstance(data.get('regions'), dict):
        raise ValueError('Explicit region masks schema required')
    if set(data['regions'])-set(REGIONS):
        raise ValueError('Unknown region name')
    result = {}
    for name, value in data['regions'].items():
        mask_path = local_path(Path(path).parent, value)
        if mask_path.stat().st_size > 16*1024*1024:
            raise ValueError('Mask exceeds 16 MiB')
        with mask_path.open('rb') as f:
            head = f.read(26)
        if head[:8] != b'\x89PNG\r\n\x1a\n' or head[24:26] != b'\x08\x00':
            raise ValueError('Mask must be an 8-bit grayscale PNG')
        with Image.open(mask_path) as image:
            if image.size != size or image.mode != 'L' or 'transparency' in image.info or getattr(image, 'n_frames', 1) != 1 or image.getexif().get(274, 1) != 1:
                raise ValueError('Mask must match the oriented input dimensions')
            values = np.asarray(image).reshape(-1)
            if np.any((values != 0) & (values != 255)):
                raise ValueError('Mask pixels must be binary 0 or 255')
            result[name] = {'pixels': values == 255, 'sha256': file_digest(mask_path)}
    return result


def evaluate_photo(project_path, candidate_path, source, directory, *, st_input=False,
                   assume_srgb=False, masks_path=None):
    from PIL import Image
    from .images import read_srgb, srgb_profile, CHUNK_PIXELS
    if not st_input:
        raise ValueError('Explicit --st-input declaration required; sRGB alone is not Sony ST')
    if Path(directory).exists() or Path(directory).is_symlink():
        raise ValueError('Output directory already exists')
    reference, coefficients, seed, thresholds, candidate_sha = load_candidate(project_path, candidate_path)
    source_sha = file_digest(source)
    image, interpretation = read_srgb(source, assume_srgb=assume_srgb)
    if file_digest(source) != source_sha:
        raise ValueError('Input photo changed while reading')
    if image.width*image.height > MAX_EVAL_PIXELS:
        raise ValueError('Photo evaluation limit is 4 million pixels; prepare a separate reference crop')
    masks = read_masks(masks_path, image.size)
    pixels = np.asarray(image).reshape(-1, 3)
    expected8, predicted8 = np.empty_like(pixels), np.empty_like(pixels)
    clipped_channels = 0
    for start in range(0, len(pixels), CHUNK_PIXELS):
        source_rgb = pixels[start:start+CHUNK_PIXELS].astype(float)/255
        expected = reference(source_rgb)
        ids, weights = native.interpolation(source_rgb)
        unbounded = source_rgb + (coefficients[ids]*weights[:, :, None]).sum(axis=1)/256 @ reference.response
        clipped_channels += int(np.count_nonzero((unbounded < 0) | (unbounded > 1)))
        predicted = np.clip(unbounded, 0, 1)
        expected8[start:start+len(source_rgb)] = np.floor(expected*255+.5).astype('uint8')
        predicted8[start:start+len(source_rgb)] = np.floor(predicted*255+.5).astype('uint8')

    def sampled_score(mask, offset):
        ids = np.flatnonzero(mask) if mask is not None else np.arange(len(pixels))
        total = len(ids)
        if not total:
            return {'available': False, 'pixels': 0, 'reason': 'empty explicit mask'}
        if total > MAX_METRIC_SAMPLES:
            ids = np.random.default_rng(seed+offset).choice(ids, MAX_METRIC_SAMPLES, replace=False)
        rgb = pixels[ids].astype(float)/255
        target = reference(rgb)
        actual = native.predict(rgb, coefficients, reference.response)
        return {'available': True, 'pixels': total, 'sampling': 'all' if total == len(ids) else 'seeded without replacement',
                **compare(actual, target)}

    overall = sampled_score(None, 0)
    regions = {name: {**sampled_score(masks[name]['pixels'], i+1), 'mask_sha256': masks[name]['sha256']} if name in masks else
               {'available': False, 'reason': 'no explicit mask supplied'}
               for i, name in enumerate(REGIONS)}
    result = {'schema': 'a7c2-offline-photo-comparison/1',
              'candidate_sha256': candidate_sha, 'input_interpretation': interpretation,
              'input_sha256': source_sha, 'dimensions': list(image.size),
              'st_input': 'user-declared; not inferred from sRGB metadata',
              'metric_domain': 'float encoded sRGB before PNG quantization; Lab D65 Delta E76',
              'seed': seed, 'overall': overall, 'regions': regions,
              'native_clipped_channels_full_image': clipped_channels,
              'native_clip_channel_denominator': len(pixels)*3,
              'domain_clipping': reference.clipped_rows, 'reference_rows_evaluated': reference.rendered_rows,
              'acceptance': limits(overall, thresholds), 'actual_camera_accuracy_verified': False}
    def png_writer(array):
        def write(f):
            output = Image.fromarray(array.reshape(image.height, image.width, 3))
            output.save(f, format='PNG', icc_profile=srgb_profile())
        return write
    publish(directory, {'reference.png': png_writer(expected8), 'prediction.png': png_writer(predicted8),
                        'comparison.json': lambda f: f.write(json_bytes(result))})
    return result


def file_digest(path):
    h = hashlib.sha256()
    length = 0
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            length += len(block)
            if length > 128*1024*1024:
                raise ValueError('Fingerprint input exceeds 128 MiB')
            h.update(block)
    return h.hexdigest()


def fixtures(directory):
    from .fixtures import create_fixtures
    create_fixtures(Path(directory), size=17)
    model = {'schema': 'a7c2-look-calibration/1', 'coordinate_model': 'bt601-limited-provisional',
             'response_matrix': np.eye(3).tolist(), 'full_camera_characterization': False,
             'evidence': 'Synthetic identity response for software testing only; no camera calibration'}
    project = {'schema': SCHEMA, 'base': 'ST', 'calibration': 'synthetic-model.json',
               'seed': 201, 'training_samples': 12000,
               'source': {'type': 'cube', 'path': 'identity-17.cube', 'input_space': 'sony-st-srgb',
                          'output_space': 'srgb', 'domain_policy': 'reject',
                          'attribution': 'Self-generated identity transform for synthetic tests'},
               'thresholds': {'max_rgb_mae': .005, 'max_delta_e76_p95': 2.}}
    write_bytes_new(Path(directory)/'synthetic-model.json', json_bytes(model))
    write_bytes_new(Path(directory)/'project.json', json_bytes(project))
    return {'synthetic_only': True, 'actual_camera_accuracy_verified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('fixtures', help='Synthetic model and CUBE; no camera calibration')
    demo.add_argument('--directory', required=True, type=Path)
    fitting = sub.add_parser('fit', help='Fit one offline table; never connects to USB')
    fitting.add_argument('--project', required=True, type=Path)
    fitting.add_argument('--directory', required=True, type=Path)
    fitting.add_argument('--validation-lock', type=Path)
    photo = sub.add_parser('evaluate', help='Compare reference and predicted native rendering')
    photo.add_argument('--project', required=True, type=Path)
    photo.add_argument('--candidate', required=True, type=Path)
    photo.add_argument('--input', required=True, type=Path)
    photo.add_argument('--directory', required=True, type=Path)
    photo.add_argument('--st-input', action='store_true')
    photo.add_argument('--assume-srgb', action='store_true')
    photo.add_argument('--masks', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'fixtures':
            result = fixtures(args.directory)
        elif args.command == 'fit':
            result = fit(args.project, args.directory, validation_lock=args.validation_lock)
        else:
            result = evaluate_photo(args.project, args.candidate, args.input, args.directory,
                                    st_input=args.st_input, assume_srgb=args.assume_srgb,
                                    masks_path=args.masks)
        print(json_bytes(result).decode(), end='')
        return 0
    except (ValueError, OSError, TypeError, KeyError, np.linalg.LinAlgError) as e:
        print('STOPPED: '+str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
