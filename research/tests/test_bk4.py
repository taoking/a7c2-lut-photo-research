"""Synthetic BK4 formats, independent packed bytes and fail-closed boundaries."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lutphoto import bk4 as b
from lutphoto import workercontracts as w
from research import audit_backup_loader as audit


class BK4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def checksum(self, raw, start=0):
        raw = bytearray(raw)
        data_at, size = struct.unpack_from('<II', raw, start + 24)
        end = start + data_at + size
        struct.pack_into('<I', raw, start + 32, sum(raw[start:start + 32]) + sum(raw[start + 36:end]))
        return bytes(raw)

    def cell(self, raw, image, key):
        subsystems = struct.unpack_from('<I', raw, image.offset + 16)[0]
        count, first = struct.unpack_from('<HI', raw, image.offset + 256 + (key >> 16) * 6)
        self.assertLess(key & 0xffff, count)
        return image.offset + 256 + subsystems * 6 + (first + (key & 0xffff)) * 6

    def independent_image(self):
        # Deliberately independent of the production HEADER/ENTRY/generator.
        raw = bytearray(289)
        raw[:4] = b'SYN0'; raw[12:16] = b'BK4\0'
        for offset, value in ((16, 1), (20, 1), (24, 288), (28, 1)):
            struct.pack_into('<I', raw, offset, value)
        struct.pack_into('<HI', raw, 256, 1, 0)
        struct.pack_into('<HI', raw, 262, 0, 0x01000120)
        raw[288] = 0x5a
        return self.checksum(raw)

    def fixtures(self):
        directory = self.root / 'case'; b.fixtures(directory)
        return directory

    def test_independently_packed_bk4_matches_published_layout(self):
        raw = self.independent_image(); image = b.parse_image(raw)
        self.assertEqual(b.HEADER.size, 256)
        self.assertEqual(image.records[0], b.Property(0, b'Z', None, 1))
        self.assertEqual(image.size, 289)
        images = b.parse_snapshot(b'opaque\0' + raw + b'\0\0' + raw + b'tail')
        self.assertEqual([i.offset for i in images], [7, 298])

    def test_fixed_variable_oversize_empty_and_reset_values_preserved(self):
        values = {0: b.Property(0, b'A', None, 1), 1: b.Property(0x80, b'AB', None, 6),
                  2: b.Property(1, bytes(range(256)) + bytes(44), None, 300),
                  3: b.Property(4, b'CD', b'EF', 4), 4: b.Property(0, b'', None, 0),
                  5: b.Property(0x100, b'G', None, 1)}
        raw = b.fixture_image(values); image = b.parse_image(raw)
        self.assertEqual(dict(image.records), values)
        self.assertEqual(b.image_summary(image)['attributes_above_8_bits'], 1)
        with self.assertRaises(TypeError): image.records[0] = values[0]

    def test_headers_counts_table_extents_revision_and_checksum_rejected(self):
        original = self.independent_image()
        for raw in (original[:255], original[:-1], b'\0' * 512, original[:-1] + b'x'):
            with self.assertRaises(ValueError): b.parse_image(raw)
        for offset, value in ((16, 0), (16, 65537), (20, 0), (20, b.MAX_PROPERTIES + 1),
                              (24, 256), (28, b.MAX_IMAGE), (24, 0xffffffff)):
            raw = bytearray(original); struct.pack_into('<I', raw, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError): b.parse_image(bytes(raw))
        raw = bytearray(original); raw[12:16] = b'BK2\0'
        with self.assertRaises(ValueError): b.parse_image(self.checksum(raw))
        for offset in (-1, True, len(original)):
            with self.assertRaises(ValueError): b.parse_image(original, offset)

    def test_missing_property_rows_are_not_decoded_and_bad_subsystem_ranges_rejected(self):
        raw = b.fixture_image({2: b.Property(0, b'x', None, 1)})
        image = b.parse_image(raw); self.assertEqual(set(image.records), {2})
        for count, first in ((4, 0), (1, 3), (0, 4)):
            bad = bytearray(raw); struct.pack_into('<HI', bad, 256, count, first)
            with self.assertRaises(ValueError): b.parse_image(self.checksum(bad))

    def test_aliased_subsystem_rows_and_value_storage_rejected_before_copying(self):
        raw = bytearray(b.fixture_image({0: b.Property(0, b'a', None, 1),
                                       0x10000: b.Property(0, b'b', None, 1)}))
        struct.pack_into('<HI', raw, 262, 1, 0)
        with self.assertRaisesRegex(ValueError, 'Aliased'): b.parse_image(self.checksum(raw))
        raw = bytearray(b.fixture_image({0: b.Property(0, b'a', None, 1), 1: b.Property(0, b'b', None, 1)}))
        image = b.parse_image(bytes(raw)); first = self.cell(raw, image, 0); second = self.cell(raw, image, 1)
        raw[second + 2:second + 6] = raw[first + 2:first + 6]
        with self.assertRaisesRegex(ValueError, 'Overlapping'): b.parse_image(self.checksum(raw))

    def test_pointers_into_headers_beyond_end_and_truncated_variable_prefix(self):
        raw = b.fixture_image({0: b.Property(0, b'AB', None, 4)})
        image = b.parse_image(raw); cell = self.cell(raw, image, 0)
        for pointer in (0x01000000, 0x01ffffff, 0xff000000 | len(raw) - 1):
            bad = bytearray(raw); struct.pack_into('<I', bad, cell + 2, pointer)
            with self.assertRaises(ValueError): b.parse_image(self.checksum(bad))
        bad = bytearray(raw); data_at = struct.unpack_from('<I', bad, 24)[0]
        struct.pack_into('<I', bad, 28, 1)
        with self.assertRaisesRegex(ValueError, 'prefix'): b.parse_image(self.checksum(bad))
        for size, maximum in ((5, 4), (2, 65535)):
            bad = bytearray(raw); struct.pack_into('<HH', bad, data_at, size, maximum)
            with self.assertRaises(ValueError): b.parse_image(self.checksum(bad))

    def test_reset_data_must_be_within_declared_image_not_read_from_following_block(self):
        raw = bytearray(b.fixture_image({0: b.Property(4, b'AB', b'CD', 2)}))
        data_size = struct.unpack_from('<I', raw, 28)[0]
        struct.pack_into('<I', raw, 28, data_size - 1)
        bad = self.checksum(raw) + self.independent_image()
        with self.assertRaisesRegex(ValueError, 'reset'): b.parse_image(bad)

    def test_dual_image_requires_exactly_two_and_ignores_invalid_embedded_marker(self):
        one = self.independent_image()
        for raw in (one + bytes(512), one + one[:-1], one + one + one):
            with self.assertRaises(ValueError): b.parse_snapshot(raw)
        payload = b.fixture_image({0: b.Property(0, b'BK4\0 not a header', None, 17)})
        self.assertEqual(len(b.parse_snapshot(payload + one)), 2)

    def test_valid_nested_images_are_ambiguous_even_when_both_checksums_pass(self):
        child = self.independent_image()
        outer = b.fixture_image({0: b.Property(0, child, None, len(child))})
        with self.assertRaisesRegex(ValueError, 'Overlapping valid'): b.parse_snapshot(outer + child)

    def test_scan_and_input_limits_fail_without_unbounded_work(self):
        with self.assertRaisesRegex(ValueError, 'candidate'): b.parse_snapshot(b'BK4\0' * 65 + bytes(512))
        with patch.object(b, 'MAX_SCAN_WORK', 1), self.assertRaisesRegex(ValueError, 'work'): b.parse_snapshot(b.synthetic_snapshot())
        with patch.object(b, 'MAX_SNAPSHOT', 512), self.assertRaises(ValueError): b.parse_snapshot(bytes(513))
        for raw in (bytearray(b.synthetic_snapshot()), 'BK4', None):
            with self.assertRaises(ValueError): b.parse_snapshot(raw)

    def test_metadata_reports_no_values_headers_body_or_role_proof(self):
        report = b.inspect(b.synthetic_snapshot())
        self.assertTrue(report['raw_backup_parsed']); self.assertTrue(report['private_report'])
        for key in b.boundary():
            if key not in ('schema', 'private_report'): self.assertFalse(report[key])
        text = json.dumps(report)
        for private in ('CPTEST', 'TESTDATA', 'SYNTHETIC', 'version', 'region', 'cookie', 'id1'):
            self.assertNotIn(private, text)
        self.assertEqual(report['unparsed_wrapper_bytes'], 39)

    def test_explicit_role_assertion_cannot_be_inferred_or_reversed(self):
        images = b.parse_snapshot(b.synthetic_snapshot())
        decoded, _ = b.project(images, {'AP': 0, 'CP': 1})
        self.assertEqual(len(decoded['CP']), 4)
        self.assertEqual(set(decoded['AP']), {'02cf0001', '02cf0002', '02cf0b6e'})
        for roles in (None, {}, {'AP': True, 'CP': 0}, {'AP': 0, 'CP': 0}, {'AP': 1, 'CP': 0}, {'AP': 0, 'CP': 2}):
            with self.assertRaises(ValueError): b.project(images, roles)

    def test_high_attribute_bits_preserved_by_parser_but_never_truncated_for_bridge(self):
        ap = b.fixture_image({0x02cf0001: b.Property(0x100, b'x', None, 1)})
        cp_raw = b.synthetic_snapshot(); cp = b.parse_snapshot(cp_raw)[1]
        images = b.parse_snapshot(ap + cp_raw[cp.offset:cp.offset + cp.size])
        self.assertEqual(images[0].records[0x02cf0001].attr, 256)
        with self.assertRaisesRegex(ValueError, 'high attribute'): b.project(images, {'AP': 0, 'CP': 1})

    def test_four_snapshot_bridge_preserves_reset_and_scope_without_identity_claim(self):
        directory = self.fixtures(); before = {p: p.read_bytes() for p in directory.iterdir()}
        report = b.compare(directory)
        self.assertTrue(report['scoped_reset_and_layout_preserved'])
        self.assertTrue(report['roles_are_caller_assertions'])
        self.assertFalse(report['body_binding_verified']); self.assertFalse(report['chip_roles_verified'])
        self.assertFalse(report['settings_contract']['raw_backup_parsed'])  # That layer receives decoded records only.
        self.assertTrue(report['raw_backup_parsed'])
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_unselected_settings_change_and_reset_change_are_independently_rejected(self):
        directory = self.fixtures(); path = directory / 'ram-after.bin'; original = path.read_bytes()
        for key, reset in ((0x02cf0002, False), (0x02cf0b6e, True)):
            raw = bytearray(original); image = b.parse_snapshot(bytes(raw))[0]; cell = self.cell(raw, image, key)
            pointer = struct.unpack_from('<I', raw, cell + 2)[0]
            at = image.offset + (pointer & 0xffffff) + (image.records[key].max_size if reset else 0)
            raw[at] ^= 1; path.write_bytes(self.checksum(raw, image.offset))
            with self.assertRaises(ValueError): b.compare(directory)
        path.write_bytes(original)
        self.assertTrue(b.compare(directory)['scoped_reset_and_layout_preserved'])

    def test_changed_allocation_with_identical_values_is_rejected(self):
        directory = self.fixtures(); path = directory / 'ram-after.bin'; raw = path.read_bytes()
        ap, cp = b.parse_snapshot(raw); values = dict(ap.records)
        old = values[0x02cf0002]; values[0x02cf0002] = b.Property(old.attr, old.data, old.reset_data, 8)
        path.write_bytes(b.fixture_image(values) + raw[cp.offset:cp.offset + cp.size])
        with self.assertRaisesRegex(ValueError, 'allocation layout'): b.compare(directory)

    def test_headers_checksum_and_self_asserted_metadata_never_prove_same_body(self):
        directory = self.fixtures(); path = directory / 'saved-after.bin'; raw = bytearray(path.read_bytes())
        image = b.parse_snapshot(bytes(raw))[0]; struct.pack_into('<I', raw, image.offset + 40, 1)
        path.write_bytes(self.checksum(raw, image.offset))
        report = b.compare(directory); self.assertFalse(report['body_binding_verified'])
        config = directory / 'case.json'; value = json.loads(config.read_text()); value['usb_serial_sha256'] = '11' * 32
        config.write_text(json.dumps(value))
        with self.assertRaises(ValueError): b.compare(directory)

    def test_fixtures_and_outputs_are_exclusive_and_links_not_followed(self):
        directory = self.fixtures()
        with self.assertRaises(FileExistsError): b.fixtures(directory)
        source = directory / 'ram-before.bin'; original = source.read_bytes()
        self.assertEqual(b.main(['inspect', '--input', str(source), '--output', str(source)]), 1)
        self.assertEqual(source.read_bytes(), original)
        other = self.root / 'linked'; other.symlink_to(directory)
        with self.assertRaises(ValueError): b.compare(other)
        (directory / 'saved-before.bin').unlink(); (directory / 'saved-before.bin').symlink_to(source)
        with self.assertRaises(OSError): b.compare(directory)

    def test_fixture_failures_clean_owned_new_files_and_no_existing_directory(self):
        with patch.object(b, 'write_bytes_new', side_effect=OSError('injected')), self.assertRaises(OSError): b.fixtures(self.root / 'failed')
        self.assertFalse((self.root / 'failed').exists())

    def test_actual_cli_standard_library_only_and_no_device_imports(self):
        directory = self.root / 'case'
        base = [sys.executable, '-S', '-B', '-m', 'lutphoto.bk4']
        commands = [['fixtures', '--directory', str(directory)],
                    ['inspect', '--input', str(directory / 'ram-before.bin'), '--output', str(self.root / 'inspect.json')],
                    ['compare', '--directory', str(directory), '--output', str(self.root / 'compare.json')]]
        for args in commands:
            result = subprocess.run(base + args, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(str(self.root), result.stdout)
        self.assertEqual(subprocess.run(base + commands[-1], capture_output=True, timeout=10).returncode, 1)
        result = subprocess.run([sys.executable, '-S', '-B', '-c',
            "import sys; from lutphoto import bk4; from research import audit_backup_loader; assert not any(n.split('.')[0] in {'usb','numpy','macfl23','pmca','looktool','transport'} for n in sys.modules)"], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_inventory_matches_fixed_upstream_and_license(self):
        root = w.ROOT; pin = json.loads((root / 'research/upstream-backup-loader.lock.json').read_text())
        old = json.loads((root / 'research/upstream-looktool.lock.json').read_text())
        self.assertEqual(len(pin['files']), 10); self.assertEqual(pin['archive_sha256'], old['archive_sha256'])
        self.assertFalse(pin['camera_integration_enabled'])
        self.assertEqual(w.sha((root / 'upstream.lock.json').read_bytes()), pin['baseline_lock_sha256'])
        for name, spec in pin['files'].items():
            if name in old['files']: self.assertEqual(spec, old['files'][name])
        self.assertIn('Copyright (c) 2015 ma1co', (root / 'docs/Sony-PMCA-RE-MIT.txt').read_text())

    def test_loader_audit_has_no_false_mapping_or_body_claims(self):
        pin = {'commit': 'fixture', 'archive_sha256': '00' * 32}
        with patch.object(audit, 'load_sources', return_value=(pin, {'safe.py': b"raise RuntimeError('never execute')"})):
            report = audit.audit('unused')
        self.assertFalse(report['archive_Python_imported_or_executed'])
        self.assertFalse(report['camera_loader_abi_verified']); self.assertFalse(report['body_binding_verified'])
        self.assertFalse(report['NOR_CP_boot_loading_is_Jiritsu_plugin_loading_proof'])
        self.assertFalse(report['body_interface']['BK4_header_id1_is_body_serial'])
        self.assertTrue(report['host_chain']['trigger_or_main_result_exception_marks_session_unknown'])
        self.assertTrue(report['host_chain']['extras_and_cleanup_are_outside_that_exception_guard'])


if __name__ == '__main__':
    unittest.main()
