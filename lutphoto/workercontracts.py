"""Pinned source policies and worker ABI checks; target code is never executed."""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import zipfile

from . import customcontracts, customhost
from .io import write_bytes_new

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / 'research/upstream-worker.lock.json'
NAMES = ('appFw.so', 'cpapp-b.bin')
PROGRAM = struct.Struct('<8sIIII7q4Q')
NAMES_REPORT = struct.Struct('<8sIIII7q6I32s')
REQUEST = struct.Struct('<8sII')
PROGRAM_OFFSETS = dict(zip(('magic', 'version', 'mode', 'phase', 'writes', 'status', 'rollback',
    'remount', 'readonly', 'cleanup', 'euid', 'pid', 'ap_inode', 'cp_inode', 'ap_size', 'cp_size',
    'before_hash', 'after_hash'), (0, 8, 12, 16, 20, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 176)))
NAME_OFFSETS = dict(zip(('magic', 'version', 'mode', 'phase', 'count', 'status', 'rollback',
    'remount', 'readonly', 'plugin_unlink', 'euid', 'pid', 'staged', 'linked', 'committed', 'restored',
    'removed_backups', 'reserved', 'ap_hash'),
    (0, 8, 12, 16, 20, 24, 32, 40, 48, 56, 64, 72, 80, 84, 88, 92, 96, 100, 104)))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def boundary():
    return {'camera_operations_enabled': False, 'actual_source_identity_verified': False,
            'firmware_bound_worker_verified': False, 'native_execution_verified': False,
            'camera_loader_abi_verified': False, 'host_complete_readback_verified': False,
            'physical_validation_verified': False}


def load_sources(archive, *, inventory=None):
    pin = json.loads((PIN if inventory is None else Path(inventory)).read_text())
    schema = 'a7c2-worker-source-audit/1' if inventory is None else 'a7c2-backup-loader-source-audit/1'
    baseline = (ROOT / 'upstream.lock.json').read_bytes()
    if (pin['schema'] != schema or pin['camera_integration_enabled'] is not False
            or sha(baseline) != pin['baseline_lock_sha256']):
        raise ValueError('Source pin or original installer lock differs')
    old = json.loads((ROOT / 'research/upstream-looktool.lock.json').read_text())
    if any(pin[k] != old[k] for k in ('commit', 'archive_bytes', 'archive_sha256')):
        raise ValueError('Worker pin diverges from audited v2.1')
    raw = customcontracts.bounded_read(archive, pin['archive_bytes'])
    if len(raw) != pin['archive_bytes'] or sha(raw) != pin['archive_sha256']:
        raise ValueError('Pinned source archive differs')
    sources = {}
    prefix = 'a7c2-tools-2.1/'
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        names = package.namelist()
        if (len(names) != len(set(names)) or sum(i.file_size for i in package.infolist()) > 20_000_000
                or any(not n.startswith(prefix) or '..' in Path(n).parts for n in names)):
            raise ValueError('Unexpected archive members')
        for name, spec in pin['files'].items():
            if name.startswith('/') or '..' in Path(name).parts or spec['bytes'] > 100000:
                raise ValueError('Invalid source inventory')
            raw = package.read(prefix + name)
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            if len(raw) != spec['bytes'] or sha(raw) != spec['sha256'] or blob != spec['git_blob_sha1']:
                raise ValueError('Pinned source member differs')
            if name in old['files'] and spec != old['files'][name]:
                raise ValueError('Existing source pin differs')
            sources[name] = raw
    return pin, sources


def literal(raw, name):
    tree = ast.parse(raw)
    values = [n.value for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    if len(values) != 1:
        raise ValueError('Expected one literal source assignment')
    return ast.literal_eval(values[0])


def source_report_format(raw):
    tree = ast.parse(raw)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'REPORT' for t in node.targets):
            call = node.value
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name) and call.func.value.id == 'struct'
                    and call.func.attr == 'Struct' and len(call.args) == 1 and not call.keywords):
                return ast.literal_eval(call.args[0])
    raise ValueError('Expected literal struct report format')


def catalog(sources):
    get = lambda name: sources['src/looks/looktool/' + name + '.py']
    asset = json.loads(sources['src/looks/assets/runtime-v1.json'])
    core = sources['src/fl23/core.py']
    if (asset['schema'] != 'a7c2-lut-runtime/1' or asset['physical_first_install_tested'] is not False
            or source_report_format(get('worker')) != PROGRAM.format
            or source_report_format(get('nameworker')) != NAMES_REPORT.format):
        raise ValueError('Runtime policy or upstream report ABI differs')
    templates = [bytes.fromhex(t) for t in asset['ap_templates']]
    if len(templates) != 64 or len(set(templates)) != 64 or any(len(t) != 132 for t in templates):
        raise ValueError('Unexpected AP template inventory')
    pairs = []
    for index, kind in enumerate(('stock', 'fl23')):
        ap = next(s for s in asset['ap_sources'] if s['kind'] == kind)
        cp = next(s for s in asset['cp_sources'] if s['kind'] == kind)
        hashes = literal(core, 'ORIGINAL' if index == 0 else 'FINAL')
        if [ap['sha256'], cp['sha256']] != hashes:
            raise ValueError('Runtime pairs differ from fixed FL23 identities')
        for spec, key in ((ap, 'restore'), (cp, 'windows')):
            spans = []
            for row in spec[key]:
                old = bytes.fromhex(row.get('hex', row.get('before', '')))
                new = bytes.fromhex(row.get('after', old.hex()))
                at = row['offset']
                if type(at) is not int or at < 0 or not old or len(old) != len(new) or at + len(old) > spec['bytes']:
                    raise ValueError('Invalid source policy window')
                spans.append((at, at + len(old)))
            spans.sort()
            if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
                raise ValueError('Overlapping source policy windows')
        pairs.append({'kind': kind, 'AP': {'bytes': ap['bytes'], 'sha256': ap['sha256']},
                      'CP': {'bytes': cp['bytes'], 'sha256': cp['sha256']},
                      'ap_restore_windows': len(ap['restore']), 'cp_bootstrap_windows': len(cp['windows'])})
    table = literal(get('six'), 'TABLE_FILE'); size = literal(get('six'), 'TABLE_BYTES')
    # Descriptor policy reviewed from the pinned devicesettings.plan; no AP is read.
    descriptor = {'table_base': 0x57c6710, 'attribute_origin': 0x14ea, 'row_bytes': 32,
                  'row_format': '<8I', 'selected_slot_selector': 'slot + 9', 'fields_per_slot': 9,
                  'adjustment_attribute_origin': 0x1520, 'adjustment_attribute_stride': 18,
                  'base_row_type': 3, 'base_value_layout': 0x10000,
                  'adjustment_row_type': 0, 'adjustment_value_layout': 0x40000, 'AP_group': '02cf',
                  'protected_CP_units': list(literal(get('devicesettings'), 'PROTECTED')),
                  'diagnostic_AP_field': literal(get('devicesettings'), 'SAVED_TELEMETRY'),
                  'live_descriptors_verified': False, 'write_plan_enabled': False}
    if size != 1215 or table != 0x8000:
        raise ValueError('Unexpected six-table storage policy')
    return {**boundary(), 'schema': 'a7c2-worker-source-policy/1', 'exact_first_import_pairs': pairs,
            'legacy_six': {'AP_sha256': literal(get('six'), 'AP_SHA'),
                           'original_CP_sha256': literal(get('six'), 'CP_SHA'),
                           'normalized_CP_code_sha256': literal(get('device_layout'), 'CODE_SHA'),
                           'label_order': list(customcontracts.LAYOUTS['legacy-six'])},
            'standalone': {'nonzero_masks': 63, 'AP_requires_complete_reconstruction': True,
                           'normalized_CP_code_sha256': asset['cp_code_sha256'],
                           'canonical_zero_tables_sha256': asset['cp_zero_tables_sha256'],
                           'label_order': list(customcontracts.LAYOUTS['standalone'])},
            'tables': {'file_offset': table, 'table_bytes': size, 'count': 6,
                       'code_hash_zero_range': [table + 8, table + 32 + 6 * size],
                       'header_magic': literal(get('six'), 'MAGIC'), 'header_version': literal(get('six'), 'VERSION'),
                       'fnv_checks_required': True, 'native_table_decode_required': True},
            'settings_descriptor_policy': descriptor,
            'program_report': {'bytes': 240, 'prefix_format': PROGRAM.format, 'offsets': PROGRAM_OFFSETS},
            'names_report': {'bytes': NAMES_REPORT.size, 'format': NAMES_REPORT.format, 'offsets': NAME_OFFSETS},
            'request_bytes': REQUEST.size, 'actual_AP_CP_or_descriptors_read': False,
            'patch_bytes_in_report': False, 'physical_first_install_tested': False}


def request(kind, mode):
    if kind not in ('program', 'names') or type(mode) is not int or mode not in range(3 if kind == 'program' else 4):
        raise ValueError('Invalid worker request kind/mode')
    return REQUEST.pack(b'A7INS001' if kind == 'program' else b'A7NAM001', mode, 0)


def hash_bytes(text):
    if not isinstance(text, str) or not re.fullmatch('[0-9a-f]{64}', text):
        raise ValueError('Expected canonical complete SHA-256')
    return bytes.fromhex(text)


def validate_program(raw, mode, contract):
    request('program', mode)
    if not isinstance(raw, bytes) or len(raw) != 240 or not isinstance(contract, dict) or contract.get('schema') != 'a7c2-table-worker-contract/1':
        raise ValueError('Invalid program report/contract schema')
    try:
        sizes = [contract['sizes'][n] for n in NAMES]
        before = [hash_bytes(contract['before'][n]) for n in NAMES]
        after = [hash_bytes(contract['after'][n]) for n in NAMES]
        writes = contract['window_writes']
    except (KeyError, TypeError) as exc:
        raise ValueError('Missing program contract fields') from exc
    if any(type(n) is not int or not 0 < n <= 512 * 1024 * 1024 for n in sizes) or type(writes) is not int or not 1 <= writes <= 4096:
        raise ValueError('Invalid expected sizes/window count')
    v = PROGRAM.unpack_from(raw)
    if (v[:4] != (b'A7IRP001', 1, mode, 9) or any(v[i] for i in range(5, 11))
            or v[11] <= 0 or any(v[i] <= 0 for i in (12, 13))
            or list(v[14:16]) != sizes or v[4] != (0 if mode == 0 else writes)):
        raise ValueError('Program completion/status/count/inode evidence differs')
    if [raw[112:144], raw[144:176]] != (after if mode == 2 else before):
        raise ValueError('Complete program source hashes differ')
    expected_after = [bytes(32), bytes(32)] if mode == 0 else before if mode == 2 else after
    if [raw[176:208], raw[208:240]] != expected_after:
        raise ValueError('Complete program target hashes differ')
    return {**boundary(), 'report_structure_verified': True, 'kind': 'program', 'mode': mode}


def validate_names(raw, mode, contract):
    request('names', mode)
    if not isinstance(raw, bytes) or len(raw) != NAMES_REPORT.size or not isinstance(contract, dict) or type(contract.get('count')) is not int or contract['count'] != 68:
        raise ValueError('Exactly 68 resources and 136 report bytes required')
    try:
        ap = hash_bytes(contract['target_AP'] if mode == 3 else contract['AP'])
    except KeyError as exc:
        raise ValueError('Missing name AP contract hash') from exc
    v = NAMES_REPORT.unpack(raw)
    if (v[:5] != (b'A7NMR001', 1, mode, 9, 68) or any(v[i] for i in range(5, 11))
            or v[11] <= 0 or v[17] != 0 or v[18] != ap or any(n > 68 for n in v[12:17])):
        raise ValueError('Name completion/status/AP/count evidence differs')
    staged, linked, committed, restored, removed = v[12:17]
    if ((mode == 0 and any(v[12:17])) or (mode == 1 and v[12:17] != (68, 68, 68, 0, 0))
            or (mode == 2 and (linked or committed or staged > restored or restored + removed > 68))
            or (mode == 3 and any(v[12:16]))):
        raise ValueError('Name mode-specific counts differ')
    return {**boundary(), 'report_structure_verified': True, 'resource_full_readback_verified': False,
            'kind': 'names', 'mode': mode}


def cbytes(raw):
    return '{' + ','.join(map(str, raw)) + '}'


def fixture_header(kind):
    """Own tiny metadata; never derived from camera programs or identity bypasses."""
    if kind == 'program':
        before = {n: bytearray((b'A7C2-ABI-FIXTURE-' + n.encode()).ljust(256, b'_')) for n in NAMES}
        after = {n: bytearray(raw) for n, raw in before.items()}
        for n in NAMES: before[n][64] = 1; after[n][64] = 2
        lines = ['static const u8 old_0[]={1},new_0[]={2};',
                 'static const struct Window windows[]={{64UL,1,1,old_0,new_0},{64UL,1,0,old_0,new_0}};',
                 'static const u32 window_count=2; static const u64 file_sizes[]={256UL,256UL};']
        for label, values in (('original', before), ('final', after)):
            lines.append('static const u8 ' + label + '_hashes[2][32]={' + ','.join(cbytes(bytes.fromhex(sha(values[n]))) for n in NAMES) + '};')
        return '\n'.join(lines) + '\n'
    if kind != 'names':
        raise ValueError('Unknown fixture kind')
    raw = customcontracts.synthetic_resource(True)
    ids = customcontracts.LAYOUTS['standalone']
    target, _ = customcontracts.resources.rename(raw, {2: 'Demo Look'}, ids)
    parsed = customcontracts.decode_resource(raw)
    row = '{' + ','.join(str(parsed['entries'][rid]['pointer']) for rid in ids) + '}'
    assets = ['{' + json.dumps(name) + ',' + str(len(raw)) + ',' + cbytes(bytes.fromhex(sha(raw))) + ',' + cbytes(bytes.fromhex(sha(target))) + '}' for name in customcontracts.RESOURCE_FILES]
    return '\n'.join([
        'static const struct Asset assets[]={' + ','.join(assets) + '};',
        'static const u32 asset_count=68;',
        'static const u32 after_sizes[]={' + ','.join([str(len(target))] * 68) + '};',
        'static const u32 old_counts[]={' + ','.join(['2866'] * 68) + '};',
        'static const u32 label_ids[]={' + ','.join(map(str, ids)) + '};',
        'static const unsigned short old_pointers[68][6]={' + ','.join([row] * 68) + '};',
        'static const u8 names[6][64]={' + ','.join(cbytes((('Demo Look' if i == 1 else 'ST').encode() + b'\0')) for i in range(6)) + '};',
        'static const u32 selected_mask=2,original_uid=57285,original_gid=1000;',
        'static const char backup_prefix[]="/usr/share/app/.a7c2-lut-0000000000000000-";',
        'static const u64 ap_size=256UL;',
        'static const u8 ap_plain_hash[32]=' + cbytes(bytes.fromhex(sha(b'A7C2 ABI FIXTURE plain'.ljust(256, b'_')))) + ';',
        'static const u8 ap_named_hash[32]=' + cbytes(bytes.fromhex(sha(b'A7C2 ABI FIXTURE named'.ljust(256, b'_')))) + ';']) + '\n'


def assertion_unit(kind):
    offsets = PROGRAM_OFFSETS if kind == 'program' else NAME_OFFSETS
    size = 240 if kind == 'program' else 136
    lines = ['#include "original.c"', '_Static_assert(sizeof(void*)==8 && sizeof(long)==8,"LP64");',
             '_Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"little endian");',
             '_Static_assert(sizeof(struct Request)==16,"request size");',
             '_Static_assert(__builtin_offsetof(struct Request,mode)==8,"request mode");',
             '_Static_assert(__builtin_offsetof(struct Request,reserved)==12,"request reserved");',
             f'_Static_assert(sizeof(struct Report)=={size},"report size");']
    for name, offset in offsets.items():
        lines.append(f'_Static_assert(__builtin_offsetof(struct Report,{name})=={offset},"{name}");')
    return '\n'.join(lines) + '\n'


def inspect_loads(raw):
    from elftools.elf.elffile import ELFFile
    elf = ELFFile(io.BytesIO(raw)); loads = [p for p in elf.iter_segments() if p['p_type'] == 'PT_LOAD']
    if not loads or len(loads) > 8:
        raise ValueError('Missing or excessive worker load segments')
    spans = []
    for p in loads:
        at, size, stored = p['p_vaddr'], p['p_memsz'], p['p_filesz']
        if stored > size or p['p_offset'] + stored > len(raw) or not 0 < size <= 4 * 1024 * 1024 or at + size >= 2**64:
            raise ValueError('Invalid worker load range')
        spans.append((at, at + size))
    spans.sort()
    if spans[-1][1] - spans[0][0] > 8 * 1024 * 1024 or any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('Overlapping worker load ranges')
    init = [t.entry.d_val for t in elf.get_section_by_name('.dynamic').iter_tags() if t.entry.d_tag == 'DT_INIT']
    symbols = [s['st_value'] for s in elf.get_section_by_name('.dynsym').iter_symbols() if s.name == '_init']
    if len(init) != 1 or symbols != init or not any(p['p_flags'] & 1 and p['p_vaddr'] <= init[0] < p['p_vaddr'] + p['p_filesz'] for p in loads):
        raise ValueError('Worker init is not bounded executable file data')
    for section in elf.iter_sections():
        if section['sh_type'] == 'SHT_RELA':
            for r in section.iter_relocations():
                if not any(p['p_flags'] & 2 and p['p_vaddr'] <= r['r_offset'] <= p['p_vaddr'] + p['p_memsz'] - 8 for p in loads):
                    raise ValueError('Relocation target outside writable loaded memory')
                if not any(start <= r['r_addend'] < end for start, end in spans):
                    raise ValueError('Relative addend outside worker loaded ranges')
    return {'load_segments': len(loads), 'virtual_span_bytes': spans[-1][1] - spans[0][0],
            'zero_fill_bytes': sum(p['p_memsz'] - p['p_filesz'] for p in loads),
            'init_in_executable_file_range': True, 'relocation_targets_in_writable_memory': True,
            'relative_addends_in_load_ranges': True}


def compile_sources(sources):
    from elftools.common.exceptions import ELFError
    command = customhost.compiler_command('zig')
    if command is None:
        raise ValueError('Audited Zig 0.13.0 environment required')
    results = {}
    with tempfile.TemporaryDirectory(prefix='a7c2-worker-abi-') as temporary:
        root = Path(temporary)
        for kind, member in (('program', 'src/fl23/native/installer.c'), ('names', 'src/looks/native/names.c')):
            folder = root / kind; folder.mkdir()
            (folder / 'original.c').write_bytes(sources[member])
            (folder / 'sha256.h').write_bytes(sources['src/fl23/native/sha256.h'])
            header = fixture_header(kind); unit = assertion_unit(kind)
            (folder / 'fixture.h').write_text(header); (folder / 'assertions.c').write_text(unit)
            env = os.environ.copy()
            env['ZIG_GLOBAL_CACHE_DIR'] = str(root / 'global-cache'); env['ZIG_LOCAL_CACHE_DIR'] = str(root / 'local-cache')
            flags = ['cc', '-target', 'aarch64-linux-gnu', '-shared', '-fPIC', '-O2', '-ffreestanding',
                     '-fno-builtin', '-fno-stack-protector', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                     '-nostdlib', '-g0', '-Wl,--strip-debug', '-Wl,--no-undefined', '-Wl,-Bsymbolic', '-Wl,-z,noexecstack',
                     '-I', str(folder), '-DPATCH_MANIFEST="fixture.h"', '-o', str(folder / 'worker.elf'), str(folder / 'assertions.c')]
            process = subprocess.run(command + flags, env=env, capture_output=True, timeout=60)
            if process.returncode:
                raise ValueError('Pinned C source/ABI compilation failed; diagnostics omitted')
            raw = customcontracts.bounded_read(folder / 'worker.elf', 65536)
            try:
                elf_report = {**customhost.inspect_elf(raw, shared=True), **inspect_loads(raw)}
            except ELFError as exc:
                raise ValueError('Malformed compiled worker ELF') from exc
            results[kind] = {**elf_report,
                             'upstream_C_source_sha256': sha(sources[member]), 'fixture_header_sha256': sha(header.encode()),
                             'assertions_sha256': sha(unit.encode()), 'compile_time_ABI_assertions_passed': True,
                             'metadata_kind': 'own synthetic fixture only', 'target_code_executed': False}
    return results


def audit(archive, *, compile_workers=False):
    pin, sources = load_sources(archive)
    report = {**boundary(), 'schema': 'a7c2-worker-contract-audit/1', 'commit': pin['commit'],
              'archive_sha256': pin['archive_sha256'], 'verified_source_files': len(sources), 'policy': catalog(sources),
              'archive_Python_imported_or_executed': False, 'reviewed_vendored_resource_module_used': True,
              'upstream_C_compiled_with_fixture_metadata': False,
              'temporary_targets_retained': False}
    if compile_workers:
        report['builds'] = compile_sources(sources)
        report['upstream_C_compiled_with_fixture_metadata'] = True
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--compile-workers', action='store_true')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if Path(args.output).exists() or Path(args.output).is_symlink():
            raise ValueError('Output already exists')
        report = audit(args.archive, compile_workers=args.compile_workers)
        write_bytes_new(args.output, (json.dumps(report, indent=2, allow_nan=False) + '\n').encode())
        print('Offline source/worker contract audit completed; no target code execution')
        return 0
    except (ValueError, OSError, ImportError, KeyError, TypeError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        print('Offline worker audit stopped: ' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
