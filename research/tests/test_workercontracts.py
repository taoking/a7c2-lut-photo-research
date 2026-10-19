"""Independent packet fixtures, source integrity and worker memory boundaries."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import warnings
import zipfile

from lutphoto import workercontracts as w


class WorkerContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.program_contract = {'schema': 'a7c2-table-worker-contract/1', 'window_writes': 2,
            'sizes': dict(zip(w.NAMES, (256, 512))), 'before': dict(zip(w.NAMES, ('11' * 32, '22' * 32))),
            'after': dict(zip(w.NAMES, ('11' * 32, '33' * 32)))}
        self.name_contract = {'count': 68, 'AP': '11' * 32, 'target_AP': '22' * 32}

    def program_packet(self, mode):
        before = (b'\x11' * 32 + (b'\x33' if mode == 2 else b'\x22') * 32)
        after = bytes(64) if mode == 0 else b'\x11' * 32 + (b'\x22' if mode == 2 else b'\x33') * 32
        return struct.pack('<8s4I7q4Q', b'A7IRP001', 1, mode, 9, 0 if mode == 0 else 2,
                           0, 0, 0, 0, 0, 0, 17, 21, 22, 256, 512) + before + after

    def name_packet(self, mode, counts=None):
        counts = counts if counts is not None else ((68, 68, 68, 0, 0) if mode == 1 else
                                                    (12, 0, 0, 13, 55) if mode == 2 else
                                                    (0, 0, 0, 0, 68) if mode == 3 else (0, 0, 0, 0, 0))
        return struct.pack('<8s4I7q6I32s', b'A7NMR001', 1, mode, 9, 68, 0, 0, 0, 0, 0, 0, 17,
                           *counts, 0, (b'\x22' if mode == 3 else b'\x11') * 32)

    def test_request_modes_magic_reserved_and_boolean_rejection(self):
        for kind, count, magic in (('program', 3, b'A7INS001'), ('names', 4, b'A7NAM001')):
            for mode in range(count):
                self.assertEqual(w.request(kind, mode), magic + struct.pack('<II', mode, 0))
                self.assertEqual(len(w.request(kind, mode)), 16)
            for mode in (-1, count, True, '1', None):
                with self.assertRaises(ValueError): w.request(kind, mode)
        with self.assertRaises(ValueError): w.request('USB', 0)

    def test_program_all_modes_bind_hash_direction_without_native_or_physical_claims(self):
        for mode in range(3):
            result = w.validate_program(self.program_packet(mode), mode, self.program_contract)
            self.assertTrue(result['report_structure_verified'])
            for key in w.boundary(): self.assertFalse(result[key])
            for other in range(3):
                if other != mode:
                    with self.assertRaises(ValueError): w.validate_program(self.program_packet(mode), other, self.program_contract)

    def test_every_program_status_phase_count_pid_inode_size_field_rejected(self):
        raw = self.program_packet(1)
        original = list(struct.unpack_from('<8s4I7q4Q', raw))
        for index in range(16):
            values = original.copy()
            values[index] = b'BADMAGIC' if index == 0 else 0 if index in (11, 12, 13) else values[index] + 1
            bad = struct.pack('<8s4I7q4Q', *values) + raw[112:]
            with self.subTest(index=index), self.assertRaises(ValueError): w.validate_program(bad, 1, self.program_contract)

    def test_program_lengths_complete_hashes_and_zero_preflight_after_required(self):
        for mode in range(3):
            raw = self.program_packet(mode)
            for bad in (raw[:-1], raw + b'x', raw[:112] + bytes(128)):
                with self.assertRaises(ValueError): w.validate_program(bad, mode, self.program_contract)
            for offset in (112, 144, 176, 208):
                bad = bytearray(raw); bad[offset] ^= 1
                with self.assertRaises(ValueError): w.validate_program(bytes(bad), mode, self.program_contract)

    def test_program_invalid_contract_shape_hashes_sizes_and_writes(self):
        for key, value in (('schema', 'wrong'), ('sizes', {}), ('sizes', {n: True for n in w.NAMES}),
                           ('sizes', {n: 2**40 for n in w.NAMES}), ('before', {n: 'AA' * 32 for n in w.NAMES}),
                           ('after', {n: '11' for n in w.NAMES}), ('window_writes', True), ('window_writes', 0),
                           ('window_writes', 4097)):
            contract = copy.deepcopy(self.program_contract); contract[key] = value
            with self.assertRaises(ValueError): w.validate_program(self.program_packet(1), 1, contract)
        for contract in (None, [], {}):
            with self.assertRaises(ValueError): w.validate_program(self.program_packet(1), 1, contract)

    def test_all_name_modes_ap_direction_and_full_68_boundary(self):
        for mode in range(4):
            result = w.validate_names(self.name_packet(mode), mode, self.name_contract)
            self.assertFalse(result['native_execution_verified'])
            self.assertFalse(result['resource_full_readback_verified'])
            self.assertTrue(result['report_structure_verified'])
        for count in (True, 1, 67, 69):
            with self.assertRaises(ValueError): w.validate_names(self.name_packet(1), 1, {**self.name_contract, 'count': count})
        for contract in (None, {}, {'count': 68}, {**self.name_contract, 'AP': 'AA' * 32}):
            with self.assertRaises(ValueError): w.validate_names(self.name_packet(0), 0, contract)

    def test_names_status_uid_cleanup_pid_reserved_ap_hash_and_count_fields(self):
        raw = self.name_packet(1); original = list(struct.unpack('<8s4I7q6I32s', raw))
        for index in list(range(12)) + [17, 18]:
            values = original.copy()
            values[index] = b'BADMAGIC' if index == 0 else bytes(32) if index == 18 else 0 if index == 11 else values[index] + 1
            bad = struct.pack('<8s4I7q6I32s', *values)
            with self.subTest(index=index), self.assertRaises(ValueError): w.validate_names(bad, 1, self.name_contract)
        for mode in range(4):
            raw = self.name_packet(mode)
            for bad in (raw[:-1], raw + b'x'):
                with self.assertRaises(ValueError): w.validate_names(bad, mode, self.name_contract)

    def test_name_mode_count_correlations_fail_closed(self):
        cases = [(0, (1, 0, 0, 0, 0)), (1, (68, 67, 68, 0, 0)), (1, (68, 68, 68, 1, 0)),
                 (2, (14, 0, 0, 13, 55)), (2, (12, 1, 0, 13, 55)), (2, (12, 0, 0, 13, 56)),
                 (2, (0, 0, 0, 69, 0)), (3, (0, 0, 0, 1, 0)), (3, (1, 0, 0, 0, 0))]
        for mode, counts in cases:
            with self.subTest(mode=mode, counts=counts), self.assertRaises(ValueError):
                w.validate_names(self.name_packet(mode, counts), mode, self.name_contract)
        w.validate_names(self.name_packet(2, (0, 0, 0, 0, 0)), 2, self.name_contract)

    def test_ast_extraction_never_executes_source_text(self):
        source = b"raise RuntimeError('do not run')\nAP_SHA='111'\n"
        self.assertEqual(w.literal(source, 'AP_SHA'), '111')
        for raw in (b'X=__import__("os").getcwd()', b'X=1\nX=2', b'Y=1'):
            with self.assertRaises((ValueError, TypeError)): w.literal(raw, 'X')
        self.assertEqual(w.source_report_format(b"raise RuntimeError()\nREPORT=struct.Struct('<8s')"), '<8s')
        with self.assertRaises(ValueError): w.source_report_format(b"REPORT=unknown.Struct('<8s')")

    def policy_sources(self):
        asset = {'schema': 'a7c2-lut-runtime/1', 'physical_first_install_tested': False,
                 'ap_templates': [(bytes([i]) * 132).hex() for i in range(64)],
                 'cp_code_sha256': '55' * 32, 'cp_zero_tables_sha256': '66' * 32}
        ap = [{'kind': kind, 'sha256': h * 32, 'bytes': 1024, 'restore': [{'offset': 16, 'hex': '00'}]}
              for kind, h in (('stock', '11'), ('fl23', '33'))]
        cp = [{'kind': kind, 'sha256': h * 32, 'bytes': 1024,
               'windows': [{'offset': 16, 'before': '00', 'after': '01'}]}
              for kind, h in (('stock', '22'), ('fl23', '44'))]
        asset.update(ap_sources=ap, cp_sources=cp)
        return {'src/looks/assets/runtime-v1.json': json.dumps(asset).encode(),
                'src/fl23/core.py': b"ORIGINAL=['" + b'11' * 32 + b"','" + b'22' * 32 + b"']\nFINAL=['" + b'33' * 32 + b"','" + b'44' * 32 + b"']\n",
                'src/looks/looktool/worker.py': b"REPORT=struct.Struct('<8sIIII7q4Q')",
                'src/looks/looktool/nameworker.py': b"REPORT=struct.Struct('<8sIIII7q6I32s')",
                'src/looks/looktool/device_layout.py': b"CODE_SHA='" + b'77' * 32 + b"'",
                'src/looks/looktool/devicesettings.py': b'PROTECTED=(0x02a40000,0x02a40001,0x02a40002,0x02a4000d)\nSAVED_TELEMETRY=0x02cf0b6e',
                'src/looks/looktool/six.py': b"TABLE_FILE=32768\nTABLE_BYTES=1215\nMAGIC=910964545\nVERSION=65542\nAP_SHA='" + b'88' * 32 + b"'\nCP_SHA='" + b'99' * 32 + b"'"}

    def test_catalog_metadata_only_pairs_ranges_masks_and_descriptor_boundary(self):
        result = w.catalog(self.policy_sources())
        self.assertEqual([p['kind'] for p in result['exact_first_import_pairs']], ['stock', 'fl23'])
        self.assertEqual(result['tables']['code_hash_zero_range'], [32776, 40090])
        self.assertEqual(result['standalone']['nonzero_masks'], 63)
        self.assertFalse(result['actual_AP_CP_or_descriptors_read'])
        self.assertFalse(result['settings_descriptor_policy']['write_plan_enabled'])
        self.assertEqual(result['program_report']['bytes'], 240)
        self.assertEqual(result['names_report']['bytes'], 136)

    def test_catalog_rejects_source_pair_drift_template_changes_and_invalid_windows(self):
        for kind in ('pair', 'physical', 'template', 'overlap', 'bounds', 'resize'):
            source = self.policy_sources(); asset = json.loads(source['src/looks/assets/runtime-v1.json'])
            if kind == 'pair': asset['ap_sources'][0]['sha256'] = 'ff' * 32
            elif kind == 'physical': asset['physical_first_install_tested'] = True
            elif kind == 'template': asset['ap_templates'][1] = asset['ap_templates'][0]
            elif kind == 'overlap': asset['cp_sources'][0]['windows'] *= 2
            elif kind == 'bounds': asset['cp_sources'][0]['windows'][0]['offset'] = 1024
            else: asset['cp_sources'][0]['windows'][0]['after'] = '0000'
            source['src/looks/assets/runtime-v1.json'] = json.dumps(asset).encode()
            with self.subTest(kind=kind), self.assertRaises(ValueError): w.catalog(source)

    def test_real_inventory_pins_14_sources_without_firmware_or_old_lock_replacement(self):
        pin = json.loads(w.PIN.read_text()); old = json.loads((w.ROOT / 'research/upstream-looktool.lock.json').read_text())
        self.assertEqual(len(pin['files']), 14)
        self.assertEqual(pin['archive_sha256'], old['archive_sha256'])
        self.assertFalse(pin['camera_integration_enabled'])
        self.assertEqual(w.sha((w.ROOT / 'upstream.lock.json').read_bytes()), pin['baseline_lock_sha256'])
        for name, spec in pin['files'].items():
            self.assertNotIn(Path(name).suffix, ('.bin', '.so'))
            self.assertEqual(len(spec['sha256']), 64)
            if name in old['files']: self.assertEqual(spec, old['files'][name])

    def fake_archive(self, duplicates=False):
        folder = self.root / 'inventory'; folder.mkdir()
        (folder / 'research').mkdir()
        data = b"raise RuntimeError('source must never execute')\n"
        archive = folder / 'source.zip'
        with zipfile.ZipFile(archive, 'w') as z, warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            z.writestr('a7c2-tools-2.1/test.py', data)
            if duplicates: z.writestr('a7c2-tools-2.1/test.py', data)
        baseline = b'{}\n'; (folder / 'upstream.lock.json').write_bytes(baseline)
        spec = {'bytes': len(data), 'sha256': w.sha(data), 'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}
        pin = {'schema': 'a7c2-worker-source-audit/1', 'camera_integration_enabled': False,
               'baseline_lock_sha256': w.sha(baseline), 'commit': 'fixture',
               'archive_bytes': archive.stat().st_size, 'archive_sha256': w.sha(archive.read_bytes()), 'files': {'test.py': spec}}
        path = folder / 'research/pin.json'; path.write_text(json.dumps(pin))
        (folder / 'research/upstream-looktool.lock.json').write_text(json.dumps(pin))
        return folder, path, archive

    def test_archive_member_identity_is_verified_before_any_source_use(self):
        folder, pinpath, archive = self.fake_archive()
        with patch.object(w, 'ROOT', folder), patch.object(w, 'PIN', pinpath):
            _, sources = w.load_sources(archive); self.assertIn('test.py', sources)
            original_pin = json.loads(pinpath.read_text())
            for key, value in (('bytes', 1), ('sha256', '00' * 32), ('git_blob_sha1', '00' * 20)):
                pin = copy.deepcopy(original_pin); pin['files']['test.py'][key] = value; pinpath.write_text(json.dumps(pin))
                with self.assertRaises(ValueError): w.load_sources(archive)

    def test_duplicate_zip_members_and_modified_or_linked_archives_rejected(self):
        folder, pinpath, archive = self.fake_archive(duplicates=True)
        with patch.object(w, 'ROOT', folder), patch.object(w, 'PIN', pinpath), self.assertRaises(ValueError): w.load_sources(archive)
        small = self.root / 'small.zip'; small.write_bytes(b'not the pinned archive')
        with self.assertRaises(ValueError): w.load_sources(small)
        link = self.root / 'linked.zip'; link.symlink_to(small)
        with self.assertRaises(OSError): w.load_sources(link)

    def test_fixture_headers_and_assertions_do_not_enable_real_layout_or_python_loading(self):
        program = w.fixture_header('program'); names = w.fixture_header('names')
        self.assertIn('256UL,256UL', program)
        self.assertEqual(names.count('string_'), 68)
        self.assertIn('selected_mask=2', names)
        for kind, offsets in (('program', w.PROGRAM_OFFSETS), ('names', w.NAME_OFFSETS)):
            unit = w.assertion_unit(kind)
            self.assertIn('#include "original.c"', unit)
            for name, offset in offsets.items(): self.assertIn(f'Report,{name})=={offset}', unit)
        with self.assertRaises(ValueError): w.fixture_header('camera')

    def fake_elf(self):
        class Symbol(dict):
            name = '_init'
        class Relocations(dict):
            def iter_relocations(self): return iter([{'r_offset': 4096, 'r_addend': 64}])
        return SimpleNamespace(
            iter_segments=lambda: iter(self.segments),
            get_section_by_name=lambda name: SimpleNamespace(iter_tags=lambda: iter([SimpleNamespace(entry=SimpleNamespace(d_tag='DT_INIT', d_val=64))]))
                if name == '.dynamic' else SimpleNamespace(iter_symbols=lambda: iter([Symbol(st_value=64)])),
            iter_sections=lambda: iter([Relocations(sh_type='SHT_RELA')]))

    def set_segments(self):
        self.segments = [{'p_type': 'PT_LOAD', 'p_vaddr': 0, 'p_offset': 0, 'p_filesz': 128, 'p_memsz': 128, 'p_flags': 5},
                         {'p_type': 'PT_LOAD', 'p_vaddr': 4096, 'p_offset': 128, 'p_filesz': 32, 'p_memsz': 4096, 'p_flags': 6}]

    def test_elf_load_ranges_report_zero_fill_not_just_file_size(self):
        self.set_segments()
        with patch('elftools.elf.elffile.ELFFile', return_value=self.fake_elf()): result = w.inspect_loads(bytes(256))
        self.assertEqual(result['zero_fill_bytes'], 4064)
        self.assertEqual(result['virtual_span_bytes'], 8192)
        self.assertTrue(result['relative_addends_in_load_ranges'])

    def test_elf_invalid_extents_initialization_and_relocation_destinations_rejected(self):
        changes = [(0, 'p_filesz', 129), (0, 'p_flags', 4), (1, 'p_memsz', 2**24),
                   (1, 'p_offset', 250), (1, 'p_vaddr', 64), (1, 'p_vaddr', 2**40), (1, 'p_flags', 4)]
        for index, field, value in changes:
            self.set_segments(); self.segments[index][field] = value
            with patch('elftools.elf.elffile.ELFFile', return_value=self.fake_elf()), self.assertRaises(ValueError): w.inspect_loads(bytes(256))
        class BadAddend(dict):
            def iter_relocations(self): return iter([{'r_offset': 4096, 'r_addend': 100000}])
        self.set_segments(); elf = self.fake_elf()
        elf.iter_sections = lambda: iter([BadAddend(sh_type='SHT_RELA')])
        with patch('elftools.elf.elffile.ELFFile', return_value=elf), self.assertRaises(ValueError): w.inspect_loads(bytes(256))

    def test_compiler_absence_failure_and_timeout_do_not_claim_build_success(self):
        sources = {'src/fl23/native/installer.c': b'/* synthetic test */', 'src/fl23/native/sha256.h': b''}
        with patch.object(w.customhost, 'compiler_command', return_value=None), self.assertRaises(ValueError): w.compile_sources(sources)
        for side_effect, result in ((None, SimpleNamespace(returncode=1)), (subprocess.TimeoutExpired('compiler', 1), None)):
            with patch.object(w.customhost, 'compiler_command', return_value=['fixture-compiler']), patch.object(w.subprocess, 'run', side_effect=side_effect, return_value=result):
                with self.assertRaises((ValueError, subprocess.TimeoutExpired)): w.compile_sources(sources)

    def test_cli_preserves_existing_outputs_and_imports_no_device_modules(self):
        output = self.root / 'report.json'
        with patch.object(w, 'audit', return_value=w.boundary()) as audit:
            self.assertEqual(w.main(['--archive', 'not-read', '--output', str(output)]), 0)
            original = output.read_bytes()
            self.assertEqual(w.main(['--archive', 'not-read', '--output', str(output)]), 1)
            self.assertEqual(audit.call_count, 1); self.assertEqual(output.read_bytes(), original)
        result = subprocess.run([sys.executable, '-S', '-B', '-c',
            "import sys; from lutphoto import workercontracts; assert not any(n.split('.')[0] in {'usb','numpy','macfl23','pmca','looktool'} for n in sys.modules)"], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
