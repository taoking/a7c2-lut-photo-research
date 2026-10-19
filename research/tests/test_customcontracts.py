"""Actual-format synthetic fixtures; no Sony material or device access."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lutphoto import customcontracts as c


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_exact_vendored_bytes_license_and_manifest(self):
        root = Path(c.resources.__file__).parent
        meta = json.loads((root / 'PROVENANCE.json').read_text())
        self.assertEqual(meta['commit'], '7e54d60b458847f1befa6cfd614fbf004b8b0b90')
        for name, spec in meta['files'].items():
            raw = (root / name).read_bytes()
            self.assertEqual(len(raw), spec['bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), spec['sha256'])
        self.assertIn('A7C II FL2/FL3 preview contributors', (root / 'LICENSE.txt').read_text())
        self.assertIn('QAQLeonard', meta['author'])
        self.assertEqual(len(c.RESOURCE_FILES), 68)
        self.assertEqual(len(set(c.RESOURCE_FILES)), 68)
        self.assertFalse(meta['modifications'])
        self.assertFalse(meta['camera_execution_modules_included'])

    def test_stock_extension_and_imported_rename_have_exact_inverse(self):
        for imported in (False, True):
            for layout in c.LAYOUTS:
                if not imported and layout == 'legacy-six': continue
                raw = c.synthetic_resource(imported)
                original = bytes(raw)
                result = c.resource_contract(raw, {2: '自然胶片', 6: 'Sky'}, layout)
                self.assertTrue(result['exact_inverse_verified'])
                self.assertEqual(result['restored_sha256'], c.digest(raw))
                self.assertNotEqual(result['after_sha256'], c.digest(raw))
                self.assertEqual(raw, original)
                self.assertEqual(result['before_count'], 2866 if imported else 2860)

    def test_label_mapping_is_explicit_and_unselected_records_are_preserved(self):
        raw = c.synthetic_resource(True)
        outputs = []
        for layout, ids in c.LAYOUTS.items():
            target, plan = c.resources.rename(raw, {1: 'Film'}, ids)
            before, after = c.decode_resource(raw), c.decode_resource(target)
            for rid, entry in before['entries'].items():
                self.assertEqual(after['entries'][rid]['text'], 'Film' if rid == ids[0] else entry['text'])
            self.assertEqual(c.resources.inverse(target, plan), raw)
            outputs.append(c.digest(target))
        self.assertNotEqual(*outputs)
        for layout in ('auto', 'camera', '', None):
            with self.assertRaises(ValueError): c.resource_contract(raw, {1: 'x'}, layout)
        with self.assertRaises(ValueError): c.resource_contract(c.synthetic_resource(), {1: 'x'}, 'legacy-six')

    def test_stock_initializes_unselected_new_labels_to_st(self):
        raw = c.synthetic_resource()
        target, _ = c.resources.rename(raw, {3: 'Film'}, c.LAYOUTS['standalone'])
        after = c.decode_resource(target)
        for slot, rid in enumerate(c.LAYOUTS['standalone'], 1):
            self.assertEqual(after['entries'][rid]['text'], 'Film' if slot == 3 else 'ST')
        self.assertEqual(after['entries'][0x0200a000]['text'], 'Synthetic unrelated text')

    def test_bad_headers_indices_pointers_utf8_and_termination_rejected(self):
        original = c.synthetic_resource(True)
        cases = [b'', original[:15], b'bad' + original[3:], original[:-1], original + b'\0', b'\0' * (c.MAX_RESOURCE + 1)]
        for at, value, fmt in ((8, 9, '<H'), (10, 6, '<H'), (12, 0, '<I'),
                               (16, 65534, '<H'), (16 + 2 * 2860, 65535, '<H')):
            raw = bytearray(original); struct.pack_into(fmt, raw, at, value); cases.append(bytes(raw))
        base = c.decode_resource(original)['data_base']
        raw = bytearray(original); raw[base + 4] = 255; cases.append(bytes(raw))
        raw = bytearray(original); raw[base + 4:] = b'x' * (len(raw) - base - 4); cases.append(bytes(raw))
        for i, raw in enumerate(cases):
            with self.subTest(i=i), self.assertRaises((ValueError, struct.error)):
                c.decode_resource(raw)

    def test_overlapping_records_rejected_even_when_upstream_decodes(self):
        raw = bytearray(c.synthetic_resource())
        base = c.decode_resource(bytes(raw))['data_base']
        # Entry zero text consumes the byte after the second record header.
        raw[base:] = struct.pack('<I', 0x1e00a000) + b'abcd' + struct.pack('<I', 0x1e00a100) + b'x\0\0\0'
        struct.pack_into('<H', raw, 16 + 256 * 2, 2)
        c.resources.decode(bytes(raw))
        with self.assertRaisesRegex(ValueError, 'Overlapping'): c.decode_resource(bytes(raw))

    def test_names_have_strict_slot_utf8_and_control_bounds(self):
        for names in ({}, {True: 'x'}, {0: 'x'}, {7: 'x'}, {'1': 'x'}, {1: ''},
                      {1: 'x' * 64}, {1: '中' * 22}, {1: '\0'}, {1: '\x7f'},
                      {1: '\x85'}, {1: '\ud800'}, {1: 4}):
            with self.subTest(names=repr(names)), self.assertRaises(ValueError):
                c.resource_contract(c.synthetic_resource(), names, 'standalone')
        c.resource_contract(c.synthetic_resource(), {1: '中' * 21}, 'standalone')

    def test_byte_inverse_corruption_detected(self):
        original = c.resources.inverse
        def damaged(raw, plan):
            restored = original(raw, plan)
            return restored[:-1] + bytes([restored[-1] ^ 1])
        with patch.object(c.resources, 'inverse', damaged), self.assertRaisesRegex(ValueError, 'inverse differs'):
            c.resource_contract(c.synthetic_resource(True), {2: 'Film'}, 'standalone')

    def test_resource_index_exhaustion_is_rejected(self):
        raw = c.synthetic_resource(True)
        base = c.decode_resource(raw)['data_base']
        raw += bytes(base + 65535 * 4 - len(raw))
        with self.assertRaisesRegex(ValueError, 'exhausted'):
            c.resource_contract(raw, {2: 'Film'}, 'standalone')

    def test_directory_requires_all_68_names_plain_files_and_consistent_layout(self):
        c.fixtures(self.root / 'cases'); directory = self.root / 'cases/stock'
        result = c.resource_directory(directory, {2: 'Film'}, 'standalone')
        self.assertEqual(result['resource_files'], 68)
        self.assertFalse(result['actual_source_identity_verified'])
        name = directory / c.RESOURCE_FILES[0]; raw = name.read_bytes(); name.unlink()
        with self.assertRaises(ValueError): c.resource_directory(directory, {2: 'x'}, 'standalone')
        name.write_bytes(raw); extra = directory / 'extra.uxc'; extra.write_bytes(raw)
        with self.assertRaises(ValueError): c.resource_directory(directory, {2: 'x'}, 'standalone')
        extra.unlink(); name.write_bytes(c.synthetic_resource(True))
        with self.assertRaisesRegex(ValueError, 'Mixed'): c.resource_directory(directory, {2: 'x'}, 'standalone')
        name.unlink(); name.symlink_to(self.root / 'cases/imported' / name.name)
        with self.assertRaises(OSError): c.resource_directory(directory, {2: 'x'}, 'standalone')

    def test_complete_settings_contract_reports_only_scope_and_counts(self):
        result = c.settings_contract(c.synthetic_settings())
        self.assertEqual(result['expected_fields'], 1)
        self.assertEqual(result['ram']['preserved_properties'], 5)
        for key in ('descriptor_write_plan_verified', 'raw_backup_parsed', 'camera_operations_enabled',
                    'actual_source_identity_verified', 'physical_validation_verified'):
            self.assertFalse(result[key])
        self.assertNotIn('00112233', json.dumps(result))

    def test_every_protected_cp_unit_and_attribute_is_preserved_across_all_states(self):
        for state in ('saved_before', 'ram_after', 'saved_after'):
            for key in c.devicesettings.PROTECTED:
                for kind in ('missing', 'data', 'attr'):
                    capsule = c.synthetic_settings(); rows = capsule[state]['CP']; name = f'{key:08x}'
                    if kind == 'missing': rows.pop(name)
                    elif kind == 'data': rows[name]['data'] = 'aabbccdd'
                    else: rows[name]['attr'] = 1
                    with self.subTest(state=state, key=name, kind=kind), self.assertRaises(ValueError):
                        c.settings_contract(capsule)

    def test_unselected_unsaved_or_added_removed_setting_is_rejected(self):
        for state in ('saved_before', 'ram_after', 'saved_after'):
            for kind in ('missing', 'extra', 'data', 'attr'):
                capsule = c.synthetic_settings(); rows = capsule[state]['AP']
                if kind == 'missing': rows.pop('02cf0002')
                elif kind == 'extra': rows['02cf0003'] = {'attr': 0, 'data': '01'}
                elif kind == 'data': rows['02cf0002']['data'] = '02000000'
                else: rows['02cf0002']['attr'] = 4
                with self.subTest(state=state, kind=kind), self.assertRaises(ValueError):
                    c.settings_contract(capsule)

    def test_selected_before_ram_saved_mismatch_or_wrong_readback_rejected(self):
        for state, text in (('saved_before', '02'), ('ram_after', '02'), ('saved_after', '02')):
            capsule = c.synthetic_settings(); capsule[state]['AP']['02cf0001']['data'] = text
            with self.assertRaises(ValueError): c.settings_contract(capsule)

    def test_expected_may_not_write_telemetry_other_groups_protected_or_resized(self):
        for key, value in (('02cf0b6e', '00000000'), ('02770015', '00'),
                           ('02a40000', '00112233'), ('02cf0003', '00'), ('02cf0001', '0000')):
            capsule = c.synthetic_settings(); capsule['expected'] = {key: value}
            with self.subTest(key=key), self.assertRaises(ValueError): c.settings_contract(capsule)
        for attr in (1, 2, 3):
            capsule = c.synthetic_settings()
            for state in ('ram_before', 'saved_before', 'ram_after', 'saved_after'):
                capsule[state]['AP']['02cf0001']['attr'] = attr
            with self.assertRaises(ValueError): c.settings_contract(capsule)

    def test_diagnostic_data_can_change_but_presence_attribute_and_length_cannot(self):
        c.settings_contract(c.synthetic_settings())
        for kind in ('missing', 'attr', 'length'):
            capsule = c.synthetic_settings(); rows = capsule['saved_after']['AP']
            if kind == 'missing': rows.pop('02cf0b6e')
            elif kind == 'attr': rows['02cf0b6e']['attr'] = 0
            else: rows['02cf0b6e']['data'] = '01'
            with self.assertRaises(ValueError): c.settings_contract(capsule)

    def test_uncompared_runtime_groups_are_not_write_targets_or_identity_evidence(self):
        capsule = c.synthetic_settings()
        capsule['ram_after']['AP'].pop('02770015')
        capsule['saved_after']['AP']['01070000'] = {'attr': 0, 'data': 'ff'}
        result = c.settings_contract(capsule)
        self.assertFalse(result['actual_source_identity_verified'])

    def test_strict_decoded_json_shape_attributes_keys_hex_and_limits(self):
        cases = []
        for key, value in [('schema', 'wrong'), ('expected', {}), ('extra', True)]:
            capsule = c.synthetic_settings(); capsule[key] = value; cases.append(capsule)
        for key, row in [('2cf0001', {'attr': 0, 'data': '00'}),
                         ('02CF0001', {'attr': 0, 'data': '00'}),
                         ('02cf0001', {'attr': True, 'data': '00'}),
                         ('02cf0001', {'attr': 256, 'data': '00'}),
                         ('02cf0001', {'attr': 0, 'data': '0A'}),
                         ('02cf0001', {'attr': 0, 'data': '00 00'}),
                         ('02cf0001', {'attr': 0, 'data': '0'}),
                         ('02cf0001', {'attr': 0, 'data': '00' * (c.MAX_VALUE + 1)})]:
            capsule = c.synthetic_settings(); capsule['ram_before']['AP'][key] = row; cases.append(capsule)
        for capsule in cases:
            with self.assertRaises(ValueError): c.settings_contract(capsule)
        capsule = c.synthetic_settings()
        capsule['expected'] = {f'02cf{i:04x}': '00' for i in range(55)}
        with self.assertRaises(ValueError): c.settings_contract(capsule)
        capsule = c.synthetic_settings()
        capsule['ram_before']['AP'] = {f'{i:08x}': {'attr': 0, 'data': '00'} for i in range(c.MAX_RECORDS + 1)}
        with self.assertRaises(ValueError): c.settings_contract(capsule)

    def test_json_rejects_duplicates_nonfinite_deep_invalid_utf8_and_oversize(self):
        path = self.root / 'input.json'
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'\xff',
                    b'[' * 2000 + b']' * 2000, b' ' * (c.MAX_JSON + 1)):
            path.write_bytes(raw)
            with self.assertRaises(ValueError): c.read_json(path)

    def test_read_only_inputs_symlinks_and_existing_outputs_are_not_overwritten(self):
        c.fixtures(self.root / 'cases')
        capsule = self.root / 'cases/settings.json'; original = capsule.read_bytes()
        self.assertEqual(c.main(['settings', '--capsule', str(capsule), '--output', str(capsule)]), 1)
        self.assertEqual(capsule.read_bytes(), original)
        link = self.root / 'link.json'; link.symlink_to(capsule)
        with self.assertRaises(OSError): c.read_json(link)
        directory_link = self.root / 'linkdir'; directory_link.symlink_to(self.root / 'cases/stock')
        with self.assertRaises(ValueError): c.resource_directory(directory_link, {1: 'x'}, 'standalone')
        with self.assertRaises(FileExistsError): c.fixtures(self.root / 'cases')

    def test_fixture_failure_cleans_only_its_reserved_directory(self):
        with patch.object(c, 'write_bytes_new', side_effect=OSError('injected')):
            with self.assertRaises(OSError): c.fixtures(self.root / 'failed')
        self.assertFalse((self.root / 'failed').exists())

    def test_cli_works_without_site_packages_device_or_numpy_and_outputs_no_payload(self):
        c.fixtures(self.root / 'cases')
        for label, arguments in (
            ('stock', ['resources', '--directory', str(self.root / 'cases/stock'), '--layout', 'standalone', '--names', str(self.root / 'cases/names.json')]),
            ('legacy', ['resources', '--directory', str(self.root / 'cases/imported'), '--layout', 'legacy-six', '--names', str(self.root / 'cases/names.json')]),
            ('settings', ['settings', '--capsule', str(self.root / 'cases/settings.json')])):
            output = self.root / (label + '.json')
            command = [sys.executable, '-S', '-B', '-m', 'lutphoto.customcontracts', *arguments, '--output', str(output)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(output.read_text()); self.assertFalse(report['camera_operations_enabled'])
            self.assertNotIn('Demo Look', output.read_text())
            self.assertNotIn('00112233', output.read_text())
            repeat = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(repeat.returncode, 1)
        result = subprocess.run([sys.executable, '-S', '-B', '-c',
            "import sys; from lutphoto import customcontracts; assert not any(n.split('.')[0] in {'usb','numpy','macfl23','pmca'} for n in sys.modules); assert 'lutphoto._vendor.sonycontracts.device_layout' not in sys.modules"], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_settings_plan_cannot_be_enabled_without_unbundled_identity_module(self):
        with self.assertRaises(ModuleNotFoundError):
            c.devicesettings.plan(b'', [], [], [1])


if __name__ == '__main__':
    unittest.main()
