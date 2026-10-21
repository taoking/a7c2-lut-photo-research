"""Frozen own N2/program/BK4/UXC bundles; no device or real owner material."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import slotbundle as b, slottarget as t
from lutphoto.capturestore import encoded
from research.tests import test_slottarget as target_fixture


class SlotBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = target_fixture.SlotTargetTests
        cls.generator.setUpClass(); cls.addClassCleanup(cls.generator.doClassCleanups)

    def setUp(self):
        self.f = self.generator(methodName='runTest'); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.root = self.f.root.resolve(); self.directory = self.root / 'bundle'
        v = self.f.b
        self.kwargs = dict(ap_path=v.ap_path, cp_path=v.cp_path, ram_path=v.ram_path, saved_path=v.saved_path,
                           selection_path=self.f.f.selection_path, resources_path=self.f.f.resources,
                           ram_roles={'AP': 0, 'CP': 1}, saved_roles={'AP': 0, 'CP': 1})

    def create(self, directory=None):
        with self.f.bound(): return b.create('own', self.directory if directory is None else directory, **self.kwargs)

    def inspect(self, directory=None):
        with self.f.bound(): return b.inspect_directory('own', self.directory if directory is None else directory)

    def create_args(self, directory=None):
        args = self.f.args(self.directory if directory is None else directory)
        args[args.index('--output')] = '--directory'
        return ['create', *args]

    def inspect_args(self, directory=None):
        return ['inspect', '--archive', 'own', '--directory', str(self.directory if directory is None else directory)]

    def manifest(self): return json.loads((self.directory / b.MANIFEST).read_bytes())

    def rehash(self, relative, raw):
        path = self.directory / relative; path.write_bytes(raw)
        manifest = self.manifest(); manifest['files'][relative] = {'bytes': len(raw), 'sha256': b.p.w.sha(raw)}
        (self.directory / b.MANIFEST).write_bytes(encoded(manifest))

    def test_complete_bundle_saves_150_payloads_private_and_reopens_after_writer_close(self):
        result = self.create(); self.assertEqual(result, self.inspect()); self.assertEqual(result['payload_files'], 150)
        self.assertEqual(set(self.manifest()['files']), set(b.LIMITS))
        self.assertTrue(self.manifest()['contains_private_payloads']); self.assertTrue(self.manifest()['settings_scope_only'])
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
        for path in self.directory.rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)
        self.assertFalse(result['device_operations_enabled']); self.assertFalse(result['restore_verified'])
        text = json.dumps(result)
        for secret in (str(self.root), 'Own Film A', 'sha256', '02cf0101', 'before', 'CP-OWN'):
            self.assertNotIn(secret, text)

    def test_fresh_no_site_process_reconstructs_from_bundle_only(self):
        self.create()
        script = """import sys
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from research.tests import test_programidentity as f
from lutphoto import slotbundle as b
v=f.ProgramIdentityTests(methodName='runTest');v.setUp()
try:
 candidate=b.c.decode_json((Path(sys.argv[1])/'source/candidate.json').read_bytes())
 policy=replace(v.policy,commit=candidate['upstream_commit'])
 raw=bytearray(v.runtime_cp);raw[288:7578]=bytes(7290)
 import struct
 struct.pack_into('<6I',raw,264,*([b.p._fnv(bytes(1215))]*6))
 runtime={'cp_zero_tables_sha256':b.p.w.sha(raw),'cp_sources':[]}
 for kind in ('stock','fl23'):
  old=v.cp[kind];runtime['cp_sources'].append({'kind':kind,'windows':[{'offset':at,'before':old[at:at+4096].hex(),'after':raw[at:at+4096].hex()} for at in (0,4096)]})
 with patch.object(b.p,'_load_policy',return_value=policy),patch.object(b.t,'_runtime',return_value=runtime):
  code=b.main(['inspect','--archive','own','--directory',sys.argv[1]])
 assert not any(n=='usb' or n.startswith('usb.') for n in sys.modules)
finally:v.doCleanups()
raise SystemExit(code)
"""
        completed = subprocess.run([sys.executable, '-S', '-B', '-c', script, str(self.directory)],
                                   capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), self.inspect()); self.assertNotIn(str(self.root), completed.stdout)

    def test_original_external_paths_can_be_removed_after_freezing_without_external_reads(self):
        self.create()
        for key in ('ap_path', 'cp_path', 'ram_path', 'saved_path', 'selection_path'): self.kwargs[key].unlink()
        for path in self.f.f.candidate.iterdir(): path.unlink()
        for path in self.f.f.resources.iterdir(): path.unlink()
        with patch.object(b.m, '_relative_directory', side_effect=AssertionError('No external candidate directory')):
            self.assertEqual(self.inspect()['phase'], 'CONSISTENT_OFFLINE_BUNDLE')

    def test_all_derived_payload_kinds_rejected_even_if_manifest_hash_is_recomputed(self):
        self.create(); manifest = (self.directory / b.MANIFEST).read_bytes()
        for relative in ('evidence/target-appFw.so', 'evidence/target-cpapp-b.bin', 'evidence/forward.private.json',
                         'evidence/reverse.private.json', 'evidence/settings-scoped.private.json',
                         'evidence/resource-inverse.private.json', 'evidence/review.private.json', 'evidence/resource-000.bin'):
            path = self.directory / relative; raw = path.read_bytes()
            self.rehash(relative, raw[:-1] + bytes([raw[-1] ^ 1]))
            with self.subTest(relative=relative), self.assertRaises(ValueError): self.inspect()
            path.write_bytes(raw); (self.directory / b.MANIFEST).write_bytes(manifest)
        self.assertEqual(self.inspect()['phase'], 'CONSISTENT_OFFLINE_BUNDLE')

    def test_unknown_full_program_source_rejected_after_manifest_rehash(self):
        self.create(); relative = 'source/appFw.so'; raw = bytearray((self.directory / relative).read_bytes()); raw[1] ^= 1
        self.rehash(relative, bytes(raw))
        with self.assertRaisesRegex(ValueError, 'identity'): self.inspect()

    def test_changed_valid_candidate_or_selection_cannot_reuse_old_targets(self):
        self.create(); original = (self.directory / b.MANIFEST).read_bytes()
        relative = 'source/selection.json'; raw = (self.directory / relative).read_bytes(); value = b.c.decode_json(raw)
        value['slots']['1']['name'] = 'Changed Own Name'; self.rehash(relative, encoded(value))
        with self.assertRaises(ValueError): self.inspect()
        (self.directory / relative).write_bytes(raw); (self.directory / b.MANIFEST).write_bytes(original)
        metadata_path = self.directory / 'source/candidate.json'; metadata = b.c.decode_json(metadata_path.read_bytes())
        table = b'\1' * 1215; metadata['table']['sha256'] = b.p.w.sha(table)
        self.rehash('source/correction.table', table); self.rehash('source/candidate.json', encoded(metadata))
        with self.assertRaises(ValueError): self.inspect()

    def test_manifest_requires_exact_policy_flags_fields_file_set_and_strict_roles(self):
        import copy
        self.create(); original = self.manifest()
        changes = []
        for key, value in (('commit', 'ff' * 20), ('archive_sha256', 'ff' * 32), ('write_plan_enabled', True),
                           ('offline_only', 1), ('schema', 'old'), ('unexpected', False)):
            changed = copy.deepcopy(original); changed[key] = value; changes.append(changed)
        for roles in ({'ram': {'AP': True, 'CP': 0}, 'saved': {'AP': 0, 'CP': 1}},
                      {'ram': {'AP': 0, 'CP': 0}, 'saved': {'AP': 0, 'CP': 1}}):
            changed = copy.deepcopy(original); changed['roles'] = roles; changes.append(changed)
        changed = copy.deepcopy(original); changed['files']['../../owner'] = changed['files'].pop('source/appFw.so'); changes.append(changed)
        for changed in changes:
            (self.directory / b.MANIFEST).write_bytes(encoded(changed))
            with self.assertRaises(ValueError): self.inspect()

    def test_manifest_rejects_duplicate_keys_noncanonical_and_excessive_file_sizes(self):
        self.create(); path = self.directory / b.MANIFEST; raw = path.read_bytes()
        for bad in (raw.replace(b'{', b'{"schema":"duplicate",', 1), b' ' + raw, b'{"files":1e999}'):
            path.write_bytes(bad)
            with self.assertRaises(ValueError): self.inspect()
        manifest = b.c.decode_json(raw); manifest['files']['source/appFw.so']['bytes'] = 10**12
        path.write_bytes(encoded(manifest))
        with self.assertRaises(ValueError): self.inspect()

    def test_missing_extra_link_hardlink_shared_or_truncated_payload_refused(self):
        self.create(); path = self.directory / 'source/correction.table'; raw = path.read_bytes()
        extra = self.directory / 'source/unexpected'; extra.write_bytes(b'own'); extra.chmod(0o600)
        with self.assertRaises(ValueError): self.inspect()
        extra.unlink(); path.unlink()
        with self.assertRaises(ValueError): self.inspect()
        path.symlink_to(self.kwargs['ram_path'])
        with self.assertRaises(ValueError): self.inspect()
        path.unlink(); linked = self.root / 'own.table'; linked.write_bytes(raw); linked.chmod(0o600); os.link(linked, path)
        with self.assertRaises(ValueError): self.inspect()
        path.unlink(); path.write_bytes(raw); path.chmod(0o644)
        with self.assertRaises(ValueError): self.inspect()
        path.chmod(0o600); path.write_bytes(raw[:-1])
        with self.assertRaises(ValueError): self.inspect()

    def test_snapshot_roles_remain_explicit_and_source_order_can_differ(self):
        self.f.b.write(self.kwargs['saved_path'], reverse=True)
        self.kwargs['saved_roles'] = {'AP': 1, 'CP': 0}
        self.create(); self.assertEqual(self.manifest()['roles']['saved'], {'AP': 1, 'CP': 0})
        manifest = self.manifest(); manifest['roles']['saved'] = {'AP': 0, 'CP': 1}
        (self.directory / b.MANIFEST).write_bytes(encoded(manifest))
        with self.assertRaises(ValueError): self.inspect()

    def test_settings_payload_is_scoped_and_retains_exact_inverse_metadata(self):
        self.create(); data = b.c.decode_json((self.directory / 'evidence/settings-scoped.private.json').read_bytes())
        self.assertTrue(data['scope_only'])
        for state in data['snapshots'].values():
            self.assertEqual(state['before'], state['inverse']); self.assertEqual(state['before']['CP'], state['target']['CP'])
            self.assertEqual(state['target']['AP'][str(0x02cf0101)]['data'], '00')
        report = b.c.decode_json((self.directory / 'evidence/review.private.json').read_bytes())
        self.assertFalse(report['complete_settings_transition_verified']); self.assertFalse(report['settings']['full_BK4_target_generated'])

    def test_fl23_standalone_and_legacy_bundles_retain_their_exact_source_routes(self):
        pairs = (('fl23', self.f.own.ap['fl23'], self.f.own.cp['fl23']),
                 ('stock-lut', self.f.own.target('stock', 32), self.f.own.runtime_cp),
                 ('fl23-lut', self.f.own.target('fl23', 32), self.f.own.runtime_cp),
                 ('legacy-six', self.f.own.legacy_ap, self.f.own.legacy_cp))
        for kind, ap, cp in pairs:
            self.kwargs['ap_path'].write_bytes(ap); self.kwargs['cp_path'].write_bytes(cp)
            directory = self.root / kind; result = self.create(directory)
            self.assertEqual(result, self.inspect(directory))
            report = b.c.decode_json((directory / 'evidence/review.private.json').read_bytes())
            self.assertEqual(report['source_identity']['kind'], kind)
            self.assertEqual(report['source_identity']['mask'], report['target_identity']['mask'] & ~1 if kind.endswith('-lut') else (63 if kind == 'legacy-six' else 0))
            if kind == 'legacy-six': self.assertEqual((directory / 'evidence/target-appFw.so').read_bytes(), ap)

    def test_creation_and_independent_read_leave_all_75_original_inputs_unchanged(self):
        paths = [self.kwargs[k] for k in ('ap_path', 'cp_path', 'ram_path', 'saved_path', 'selection_path')]
        paths += list(self.f.f.candidate.iterdir()) + list(self.f.f.resources.iterdir())
        def stamp(path):
            info = path.stat()
            return (b.p.w.sha(path.read_bytes()), info.st_ino, info.st_size, info.st_mode, info.st_mtime_ns, info.st_ctime_ns)
        before = {path: stamp(path) for path in paths}
        self.assertEqual(len(before), 75); self.create(); self.inspect()
        self.assertEqual(before, {path: stamp(path) for path in paths})

    def test_zero_program_change_windows_are_kept_zero_without_fake_worker_writes(self):
        self.kwargs['ap_path'].write_bytes(self.f.own.target('stock', 1)); self.kwargs['cp_path'].write_bytes(self.f.zero)
        result = self.create(); self.assertFalse(result['program_change_required']); self.assertEqual(result['program_change_windows'], 0)
        for name in ('forward', 'reverse'):
            plan = b.c.decode_json((self.directory / ('evidence/' + name + '.private.json')).read_bytes())
            self.assertEqual(plan['AP']['changes'], []); self.assertEqual(plan['CP']['changes'], [])
        self.assertFalse(result['worker_generated'])

    def test_partial_save_is_preserved_and_never_reused_or_resumed(self):
        put = b.Store.put; calls = []
        def failed(store, name, raw, **kwargs):
            calls.append(name)
            if len(calls) == 4: raise OSError('Own interrupted save')
            return put(store, name, raw, **kwargs)
        with patch.object(b.Store, 'put', failed), self.assertRaises(OSError): self.create()
        self.assertTrue(self.directory.exists()); self.assertFalse((self.directory / b.MANIFEST).exists())
        with self.assertRaises(ValueError): self.inspect()
        with patch.object(t, '_prepare_files') as prepare, self.assertRaises(ValueError): self.create()
        prepare.assert_not_called(); self.assertEqual(len(calls), 4)

    def test_low_space_and_unknown_input_refuse_without_a_complete_marker(self):
        with patch.object(b.Store, 'require_space', side_effect=OSError('Own no space')), self.assertRaises(OSError): self.create()
        self.assertFalse((self.directory / b.MANIFEST).exists())
        self.kwargs['ap_path'].write_bytes(bytes(16384)); other = self.root / 'unknown'
        with self.assertRaises(ValueError): self.create(other)
        self.assertFalse(other.exists())

    def test_store_close_failure_does_not_report_creator_success_or_repeat_inspection(self):
        close = b.Store.close
        def failed(store): close(store); raise OSError('Own close uncertainty')
        with patch.object(b.Store, 'close', failed), patch.object(b, 'inspect_directory') as check:
            with self.assertRaises(OSError): self.create()
        check.assert_not_called(); self.assertTrue((self.directory / b.MANIFEST).exists())
        self.assertEqual(self.inspect()['phase'], 'CONSISTENT_OFFLINE_BUNDLE')  # File consistency != creator success.

    def test_reader_close_failure_prevents_cli_success(self):
        self.create(); close = b.i._Reader.close; output = io.StringIO()
        def failed(reader): close(reader); raise OSError('Own reader close uncertainty')
        with self.f.bound(), patch.object(b.i._Reader, 'close', failed), contextlib.redirect_stdout(output):
            self.assertEqual(b.main(self.inspect_args()), 1)
        self.assertEqual(output.getvalue(), '')

    def test_existing_writer_lock_and_mutation_during_reconstruction_refuse(self):
        import fcntl
        self.create()
        with (self.directory / 'session.lock').open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(b.i._Refused, 'ACTIVE_JOB'): self.inspect()
        generate = t._generate
        def changed(*args):
            result = generate(*args)
            path = self.directory / 'evidence/forward.private.json'; path.write_bytes(path.read_bytes() + b' ')
            return result
        with patch.object(t, '_generate', changed), self.assertRaisesRegex(ValueError, 'INPUT_CHANGED'): self.inspect()

    def test_cli_rejects_bad_output_parent_or_existing_directory_before_input_reads(self):
        shared = self.root / 'shared'; shared.mkdir(mode=0o755)
        linked = self.root / 'linked'; linked.symlink_to(self.root, target_is_directory=True)
        self.directory.mkdir(mode=0o700)
        for directory in (shared / 'new', linked / 'new', self.directory, Path(__file__).resolve().parents[1] / 'own-bundle'):
            with patch.object(t, '_prepare_files') as prepare, self.assertRaises((ValueError, OSError)):
                self.create(directory)
            prepare.assert_not_called()

    def test_cli_outputs_bounded_summary_and_output_failure_is_non_success(self):
        output = io.StringIO()
        with self.f.bound(), contextlib.redirect_stdout(output): self.assertEqual(b.main(self.create_args()), 0)
        self.assertEqual(json.loads(output.getvalue()), self.inspect()); self.assertNotIn(str(self.root), output.getvalue())
        class Short(io.StringIO):
            def write(self, raw): return super().write(raw[:3])
        with self.f.bound(), contextlib.redirect_stdout(Short()): self.assertEqual(b.main(self.inspect_args()), 1)

    def test_invalid_arguments_bad_source_and_standard_library_import_are_private(self):
        bad = self.root / 'own-private.zip'; bad.write_bytes(b'own invalid archive')
        command = [sys.executable, '-S', '-B', '-m', 'lutphoto.slotbundle']
        args = self.create_args(); args[args.index('--archive') + 1] = str(bad)
        result = subprocess.run(command + args, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1); self.assertNotIn(str(self.root), result.stdout + result.stderr)
        for extra in (['--enable'], ['--policy', str(self.root)], ['--ram-roles', str(self.root), '1']):
            result = subprocess.run(command + args + extra, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2); self.assertNotIn(str(self.root), result.stdout + result.stderr)
        script = "import sys;from lutphoto import slotbundle;assert not any(n.split('.')[0] in {'usb','numpy','macfl23','pmca','looktool','transport'} for n in sys.modules)"
        result = subprocess.run([sys.executable, '-S', '-B', '-c', script], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(subprocess.run(command + ['--help'], capture_output=True, timeout=10).returncode, 0)


if __name__ == '__main__': unittest.main()
