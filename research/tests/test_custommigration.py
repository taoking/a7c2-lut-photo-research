"""N3 synthetic identities, exact inverses, progress gates and compiler probes."""
import contextlib
import copy
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lutphoto import customhost as host
from lutphoto import custommigration as migration


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        migration.fixtures(self.root/'fixtures')
        self.capsule = migration.read_capsule(self.root/'fixtures/S0.json')

    def test_four_source_states_install_and_exact_restore(self):
        for state in migration.STATES:
            capsule = migration.read_capsule(self.root/f'fixtures/{state}.json')
            plan, source, target = migration.prepare(capsule)
            self.assertEqual(plan['source_state'], state)
            self.assertEqual(migration.apply(source, plan['forward']), target)
            self.assertEqual(migration.apply(target, plan['reverse']), source)
            for direction in ('install', 'restore'):
                simulation = migration.Simulation(capsule, direction)
                report = simulation.execute()
                self.assertEqual(simulation.files, target if direction == 'install' else source)
                self.assertFalse(report['camera_operations_enabled'])
                self.assertFalse(report['physical_validation_verified'])
                self.assertFalse(plan['independent_media_verified'])

    def test_same_size_hash_corruption_or_mixed_ap_cp_is_rejected(self):
        for name in ('AP', 'CP'):
            capsule = copy.deepcopy(self.capsule)
            raw = bytearray.fromhex(capsule['source'][name]); raw[120] ^= 1
            capsule['source'][name] = raw.hex()
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'identity'):
                migration.prepare(capsule)
        self.capsule['source']['CP'] = migration.blob('CP', 'S1').hex()
        with self.assertRaisesRegex(ValueError, 'mixed'):
            migration.prepare(self.capsule)

    def test_claimed_state_model_and_live_material_cannot_bypass_identification(self):
        for key, value in [('source_state', 'S1'), ('model', 'ILCE-7CR'), ('firmware', '2.02'),
                           ('material_kind', 'camera'), ('body_token', 'real-camera')]:
            capsule = {**self.capsule, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                migration.prepare(capsule)

    def test_real_sized_or_unmarked_buffers_cannot_enter_simulation(self):
        for value in ('00'*128, '00'*4096, 'not hex'):
            capsule = copy.deepcopy(self.capsule); capsule['source']['AP'] = value
            with self.assertRaises(ValueError):
                migration.prepare(capsule)

    def test_both_complete_backups_body_and_distinct_storage_tokens_required(self):
        changes = [lambda c: c.update(backups=c['backups'][:1]),
                   lambda c: c['backups'][1].update(body_token='synthetic-another-body'),
                   lambda c: c['backups'][1].update(storage_token=c['backups'][0]['storage_token']),
                   lambda c: c['backups'][1]['files'].pop('NAMES'),
                   lambda c: c['backups'][1]['files'].update(CP=migration.blob('CP', 'S1').hex())]
        for change in changes:
            capsule = copy.deepcopy(self.capsule); change(capsule)
            with self.assertRaises(ValueError):
                migration.prepare(capsule)

    def test_unselected_names_tables_settings_and_protected_bytes_preserved(self):
        plan, source, target = migration.prepare(self.capsule)
        for slot in (0, 2, 3, 4, 5):
            for name, start, width in [('CP', 64, 8), ('NAMES', 32, 12), ('SETTINGS_RAM', 32, 2), ('SETTINGS_SAVED', 32, 2)]:
                a = start+slot*width
                self.assertEqual(source[name][a:a+width], target[name][a:a+width])
        for name in migration.COMPONENTS:
            self.assertEqual(target[name][120], 0x5a)
        self.assertEqual(target['SETTINGS_RAM'][34:36], b'ST')
        self.assertEqual(target['NAMES'][44:56], b'Demo Look   ')

    def test_unsaved_unselected_payload_is_rejected_but_selected_difference_is_reversible(self):
        for at in (32, 120):
            capsule = copy.deepcopy(self.capsule)
            raw = bytearray.fromhex(capsule['source']['SETTINGS_RAM']); raw[at] ^= 1
            capsule['source']['SETTINGS_RAM'] = raw.hex()
            for record in capsule['backups']:
                record['files']['SETTINGS_RAM'] = raw.hex()
            with self.assertRaisesRegex(ValueError, 'Unselected unsaved'):
                migration.prepare(capsule)
        capsule = copy.deepcopy(self.capsule)
        raw = bytearray.fromhex(capsule['source']['SETTINGS_RAM']); raw[34:36] = b'FL'
        capsule['source']['SETTINGS_RAM'] = raw.hex()
        for record in capsule['backups']: record['files']['SETTINGS_RAM'] = raw.hex()
        plan, source, target = migration.prepare(capsule)
        self.assertEqual(migration.apply(target, plan['reverse']), source)

    def test_invalid_slots_or_oversize_toy_titles_and_tables_rejected(self):
        for replacements in ({}, {'7': {'table_hex': '00'*8, 'name': 'x'}},
                             {'2': {'table_hex': '00'*1215, 'name': 'x'}},
                             {'2': {'table_hex': '00'*8, 'name': '../file'}},
                             {'2': {'table_hex': '00'*8, 'name': 'x'*13}}):
            with self.assertRaises(ValueError):
                migration.prepare({**self.capsule, 'replacements': replacements})

    def test_overlap_out_of_bounds_before_bytes_target_hash_and_resizing_rejected(self):
        plan, source, _ = migration.prepare(self.capsule)
        cases = []
        overlap = copy.deepcopy(plan['forward']); overlap['files']['CP']['windows'] *= 2; cases.append(overlap)
        outside = copy.deepcopy(plan['forward']); outside['files']['CP']['windows'][0]['offset'] = 128; cases.append(outside)
        mismatch = copy.deepcopy(plan['forward']); mismatch['files']['CP']['windows'][0]['before_hex'] = 'ff'; cases.append(mismatch)
        digest = copy.deepcopy(plan['forward']); digest['files']['CP']['after_sha256'] = '0'*64; cases.append(digest)
        resized = copy.deepcopy(plan['forward']); resized['files']['CP']['bytes'] = 129; cases.append(resized)
        original = source.copy()
        for manifest in cases:
            with self.assertRaises(ValueError): migration.apply(source, manifest)
            self.assertEqual(source, original)

    def test_each_fault_stage_stops_without_replay_even_if_full_hash_is_target(self):
        for stage in migration.FAULTS:
            sim = migration.Simulation(self.capsule)
            result = sim.execute('CP:'+stage)
            self.assertEqual(result['phase'], 'NEEDS_REVIEW')
            self.assertFalse(result['automatic_retry_allowed'])
            self.assertFalse(result['automatic_restore_allowed'])
            before = sim.files.copy()
            with self.assertRaisesRegex(ValueError, 'cannot be replayed'):
                sim.execute()
            self.assertEqual(before, sim.files)
            if stage == 'after-write': self.assertEqual(result['classification']['CP'], 'target')
            if stage == 'readback-corrupt': self.assertEqual(result['classification']['CP'], 'unknown')

    def test_write_intent_precedes_every_verified_mutation_and_restore_failure_stops(self):
        sim = migration.Simulation(self.capsule); report = sim.execute()
        intents = set()
        for event in report['journal']:
            if event['event'] == 'write_intent': intents.add(event['component'])
            if event['event'] == 'complete_component_verified': self.assertIn(event['component'], intents)
        self.assertEqual(len(intents), report['writes_simulated'])
        restore = migration.Simulation(self.capsule, 'restore')
        result = restore.execute('SETTINGS_SAVED:after-write')
        self.assertTrue(result['unknown_outcome'])
        self.assertEqual(result['phase'], 'NEEDS_REVIEW')

    def test_complete_preflight_refuses_modified_component_before_any_write(self):
        sim = migration.Simulation(self.capsule)
        raw = bytearray(sim.files['NAMES']); raw[120] ^= 1; sim.files['NAMES'] = bytes(raw)
        with self.assertRaises(ValueError): sim.execute()
        self.assertEqual(sim.writes, 0)
        self.assertEqual(sim.journal, [])

    def test_capsule_is_immutable_and_report_does_not_claim_device_evidence(self):
        original = copy.deepcopy(self.capsule)
        sim = migration.Simulation(self.capsule); result = sim.execute()
        self.assertEqual(self.capsule, original)
        self.assertFalse(result['journal_is_durable_device_evidence'])
        with self.assertRaises(ValueError): sim.execute()

    def test_bounded_json_duplicate_nonfinite_and_bad_encoding_rejected(self):
        path = self.root/'bad.json'
        for raw in (b'{"x":0,"x":1}', b'{"x":NaN}', b'\xff', b'0'*(migration.MAX_JSON+1)):
            path.write_bytes(raw)
            with self.assertRaises(ValueError): migration.read_capsule(path)

    def test_real_cli_success_unknown_exit_two_and_existing_output_preserved(self):
        exe = str(Path(sys.executable).absolute())
        capsule = self.root/'fixtures/S0.json'
        original = capsule.read_bytes()
        for command, extra, code in [('plan', [], 0), ('simulate', [], 0),
                                     ('simulate', ['--direction', 'restore'], 0),
                                     ('simulate', ['--fault', 'CP:after-write'], 2)]:
            out = self.root/('result-'+str(len(list(self.root.glob('result-*'))))+'.json')
            r = subprocess.run([exe, '-B', '-m', 'lutphoto.custommigration', command,
                                '--capsule', str(capsule), '--output', str(out), *extra], capture_output=True, text=True)
            self.assertEqual(r.returncode, code, r.stderr)
            self.assertEqual(json.loads(r.stdout), json.loads(out.read_text()))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(migration.main(['plan', '--capsule', str(capsule), '--output', str(out)]), 1)
        self.assertEqual(capsule.read_bytes(), original)

    def test_invalid_fault_cannot_start_or_write(self):
        for fault in ('CP:unknown', 'USB:after-write', 'CP:after-write:again', True):
            sim = migration.Simulation(self.capsule)
            with self.assertRaises(ValueError): sim.execute(fault)
            self.assertEqual(sim.phase, 'PREPARED')
            self.assertEqual(sim.writes, 0)

    def test_all_source_direction_component_fault_combinations_stop(self):
        cases = 0
        for state in migration.STATES:
            capsule = migration.read_capsule(self.root/f'fixtures/{state}.json')
            for direction in ('install', 'restore'):
                for component in migration.COMPONENTS:
                    for stage in migration.FAULTS:
                        with self.subTest(state=state, direction=direction, component=component, stage=stage):
                            sim = migration.Simulation(capsule, direction)
                            result = sim.execute(component+':'+stage)
                            self.assertEqual(result['phase'], 'NEEDS_REVIEW')
                            self.assertEqual(result['unknown_outcome'], stage != 'before-intent')
                            last = result['journal'][-1]
                            self.assertEqual(last['component'], component)
                            self.assertEqual(last['stage'], stage)
                            self.assertFalse(result['automatic_retry_allowed'])
                        cases += 1
        self.assertEqual(cases, 200)


class HostProbeTests(unittest.TestCase):
    def test_absent_toolchain_is_not_reported_as_build_success(self):
        with patch('lutphoto.customhost.compiler_command', return_value=None):
            report = host.inspect_host('zig', compile_probe=True)
        self.assertFalse(report['available']); self.assertFalse(report['probe']['passed'])
        self.assertFalse(report['real_worker_build_verified'])

    def test_unreviewed_zig_version_rejected(self):
        with patch('lutphoto.customhost.importlib.metadata.version', return_value='9.9.9'):
            with self.assertRaises(ValueError): host.compiler_command('zig')

    def test_wrong_elf_architecture_type_and_missing_dynamic_metadata_rejected(self):
        # Minimal ELF64 header, no code/sections. Used only for rejection branches.
        ident = b'\x7fELF\x02\x01\x01'+b'\0'*9
        for machine, kind in ((62, 1), (183, 2), (183, 3)):
            raw = ident+struct.pack('<HHIQQQIHHHHHH', kind, machine, 1, 0, 0, 0, 0, 64, 56, 0, 64, 0, 0)
            with self.assertRaises(ValueError): host.inspect_elf(raw, shared=True)
        with self.assertRaises(ValueError): host.inspect_elf(b'0'*65537, shared=True)

    def test_compiler_failure_and_timeout_report_no_private_diagnostics(self):
        version = subprocess.CompletedProcess([], 0, b'0.13.0\n', b'')
        failure = subprocess.CompletedProcess([], 1, b'', b'secret host diagnostics')
        for outcome in (failure, subprocess.TimeoutExpired('probe', 45)):
            with patch('lutphoto.customhost.compiler_command', return_value=['fake']), \
                 patch('lutphoto.customhost.subprocess.run', side_effect=[version, outcome]):
                report = host.inspect_host('zig', compile_probe=True)
            self.assertFalse(report['probe']['passed'])
            self.assertNotIn('secret', json.dumps(report))
            self.assertFalse(report['generated_target_executed'])

    def test_new_modules_do_not_import_usb_or_legacy_installer(self):
        code = "import sys; import lutphoto.customhost,lutphoto.custommigration; assert not any(x.split('.')[0] in ('usb','macfl23','pmca','keystone','numpy') for x in sys.modules)"
        result = subprocess.run([str(Path(sys.executable).absolute()), '-B', '-c', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_host_cli_preserves_existing_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'; out.write_bytes(b'keep')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(host.main(['--output', str(out)]), 1)
            self.assertEqual(out.read_bytes(), b'keep')


if __name__ == '__main__':
    unittest.main()
