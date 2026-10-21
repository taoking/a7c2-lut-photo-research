"""Raw fake auth through fixed material evidence; no camera, media or downloads."""
import hashlib
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import capturepipeline as p, captureauth as a, captureinspect as i, capturestore
from research.tests import test_capturesession as fixtures, test_captureauth as auth_fixture


class PipelineTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.SessionTests(methodName='runTest'); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture, self.root, self.files = fixture, fixture.root, fixture.files
        patch.object(a, '_keys', return_value=(auth_fixture.PIN, auth_fixture.KEYS)).start()
        self.addCleanup(patch.stopall)

    def make(self, name='pipeline', *, files=None, resources=False, normal=None, service=None, service_observation=None, **options):
        if service_observation is not None: options['service'] = service_observation
        peer = p.s.SyntheticPeer(self.files if files is None else files, **options)
        normal = auth_fixture.tape(0x0e8a) if normal is None else normal
        service = auth_fixture.tape(0x0336) if service is None else service
        root = self.root / name
        result = p.rehearse('own', root, peer, normal, service, resources=resources)
        return result, peer, normal, service, root

    def records(self, root):
        return [json.loads(f.read_bytes()) for f in sorted((root / 'events').glob('*.json'))]

    def edit_report(self, root, **values):
        path = root / p.REPORT
        report = json.loads(path.read_bytes()); report.update(values)
        path.write_bytes(capturestore.encoded(report))

    def rechain(self, root, edit):
        head = '0' * 64
        for path in sorted((root / 'events').glob('*.json')):
            value = json.loads(path.read_bytes()); edit(value)
            value['previous_sha256'] = head
            raw = capturestore.encoded(value); path.write_bytes(raw)
            head = hashlib.sha256(raw).hexdigest()
        self.edit_report(root, journal_head_sha256=head)

    def failed(self, result, *, unknown=False, stop=False):
        self.assertEqual(result['phase'], 'NEEDS_REVIEW')
        self.assertIs(result['simulated_outcome_unknown'], unknown)
        self.assertIs(result['simulated_service_stop_ack'], stop)

    def test_complete_core_has_exact_auth_and_separate_payload_accounting(self):
        result, peer, normal, service, root = self.make()
        self.assertEqual(result['phase'], 'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')
        self.assertEqual((normal.used, service.used), (15, 16))
        self.assertEqual(normal.written, list(normal.expected)); self.assertEqual(service.written, list(service.expected))
        payload = 88 + 2 * (len(self.files['appFw.so']) + len(self.files['cpapp-b.bin'])) + 4 * len(self.files['ram'])
        self.assertEqual(result['accepted_payload_bytes'], payload)
        self.assertEqual(result['accepted_auth_bytes'], 14448)
        self.assertEqual(result['accepted_total_bytes'], payload + 14448)
        self.assertEqual(result['auth_raw_calls'], 31)
        self.assertEqual(result['authentication_phase'], 'SYNTHETIC_RETURN_MATCHED')
        self.assertEqual(len(result['files']), 6)
        self.assertFalse(any(n.startswith('auth-') or n == 'service-stop' for n in peer.trace))
        self.assertEqual(peer.trace[0], 'global-lock-acquire'); self.assertEqual(peer.trace[-1], 'global-lock-release')
        self.assertEqual(i.inspect_directory(root)['classification'], 'CONSISTENT_SIMULATION_COMPLETE')
        self.assertFalse((root / 'session-report.private.json').exists())
        for flag in i.FALSE_COMMON | i.FALSE_PROFILE['pipeline']:
            self.assertIs(result[flag], False, flag)

    def test_resource_extension_preserves_74_materials_and_new_check_format(self):
        raw = p.s.c.synthetic_resource(False)
        files = {**self.files, **{'resources/' + n: raw for n in p.s.c.RESOURCE_FILES}}
        result, peer, _, _, root = self.make(files=files, resources=True)
        self.assertEqual(result['phase'], 'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')
        self.assertEqual(len(result['files']), 74); self.assertGreater(result['journal_records'], 512)
        self.assertLess(result['journal_records'], p.s.EVENTS_LIMIT)
        self.assertTrue(all(peer.counts['read:' + n] == 2 for n in p.s.c.RESOURCE_FILES))
        self.assertEqual(i.inspect_directory(root)['materials_hashed'], 74)
        self.assertEqual(i.inspect_directory(root)['classification'], 'CONSISTENT_SIMULATION_COMPLETE')

    def test_only_one_auth_journal_and_marker_in_fixed_position(self):
        _, _, _, _, root = self.make()
        records = self.records(root)
        acks = [r['details']['operation'] for r in records if r['event'] == 'ACK']
        self.assertEqual(acks, i._ack_plan('pipeline', False))
        marker = [r for r in records if r['event'] == 'RAW_AUTHENTICATION_MODELED']
        self.assertEqual(len(marker), 1)
        self.assertEqual(marker[0]['details'], {'accepted_auth_bytes': 14448, 'raw_calls': 30})
        for name in ('auth-normal-start', 'auth-normal-verify', 'auth-service-start', 'auth-service-verify', 'service-stop'):
            self.assertEqual(acks.count(name), 1)

    def test_auth_and_fake_normal_queries_have_intent_before_io(self):
        root = self.root / 'pipeline'; raw = a.SyntheticDriver._take; step = p.s.SyntheticPeer.step
        def last(): return json.loads(sorted((root / 'events').glob('*.json'))[-1].read_bytes())
        def observe(driver, kind, timeout):
            self.assertEqual(last()['event'], 'INTENT')
            self.assertIn(last()['details']['operation'], ('auth-normal-start','auth-normal-verify','auth-service-start','auth-service-verify','service-stop'))
            return raw(driver, kind, timeout)
        def observe_step(peer, name):
            if name in ('normal-before','service-observation','normal-after'):
                self.assertEqual(last()['event'], 'INTENT'); self.assertEqual(last()['details']['operation'], name)
            return step(peer, name)
        with patch.object(a.SyntheticDriver, '_take', observe), patch.object(p.s.SyntheticPeer, 'step', observe_step):
            result, *_ = self.make()
        self.assertEqual(result['last_stage'], 'C5')

    def test_two_auth_modes_and_mixed_rounds_use_actual_packet_checks(self):
        for index, modes in enumerate(((2,2,2),(2,8,2))):
            result, _, _, service, _ = self.make(str(index), normal=auth_fixture.tape(0x0e8a,modes), service=auth_fixture.tape(0x0336,modes))
            self.assertEqual(result['phase'], 'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')
            self.assertEqual(service.written, list(service.expected))

    def test_normal_control_unknown_never_reads_materials_or_second_driver(self):
        normal = auth_fixture.tape(0x0e8a); normal.transfers[0] = ('control', None)
        result, peer, _, service, root = self.make(normal=normal)
        self.failed(result, unknown=True); self.assertEqual(normal.used, 1); self.assertEqual(service.used, 0)
        self.assertFalse(any(n.startswith('wire:') for n in peer.trace))
        self.assertEqual(i.inspect_directory(root)['classification'], 'NEEDS_REVIEW_UNKNOWN')

    def test_service_proof_timeout_forbids_hasps_stop_or_reauth(self):
        service = auth_fixture.tape(0x0336); service.transfers[8] = ('read', TimeoutError('own'))
        result, peer, normal, _, root = self.make(service=service)
        self.failed(result, unknown=True); self.assertEqual((normal.used, service.used), (15,9))
        self.assertNotIn('wire:hasp', peer.trace); self.assertFalse(result['simulated_service_stop_ack'])
        self.assertEqual(i.inspect_directory(root)['classification'], 'NEEDS_REVIEW_UNKNOWN')

    def test_service_observation_must_be_unique_and_same_port(self):
        for index, change in enumerate(({'ports':[1,3]},{'normal_count':1},{'service_count':2})):
            obs = p.s.SyntheticPeer({}).service | change
            result, peer, _, service, _ = self.make(str(index), service_observation=obs)
            self.failed(result, unknown=True); self.assertEqual(service.used, 0)
            self.assertNotIn('wire:hasp', peer.trace)

    def test_complete_bad_AP_exits_once_and_never_reads_CP_or_settings(self):
        files = self.files | {'appFw.so': bytes(len(self.files['appFw.so']))}
        result, peer, _, service, root = self.make(files=files)
        self.failed(result, stop=True); self.assertEqual(service.used, 16)
        self.assertNotIn('wire:read:cpapp-b.bin', peer.trace); self.assertNotIn('wire:ram', peer.trace)
        self.assertEqual((root / 'source/appFw.so').read_bytes(), files['appFw.so'])
        self.assertEqual(i.inspect_directory(root)['classification'], 'NEEDS_REVIEW_INCOMPLETE')

    def test_partial_material_response_keeps_partial_file_and_never_sends_stop(self):
        result, peer, _, service, root = self.make(fault='partial:read:appFw.so')
        self.failed(result, unknown=True); self.assertEqual(service.used, 15)
        self.assertTrue((root / 'source/appFw.so').exists()); self.assertNotIn('wire:read:cpapp-b.bin', peer.trace)
        self.assertEqual(i.inspect_directory(root)['classification'], 'NEEDS_REVIEW_UNKNOWN')

    def test_existing_temp_file_and_bad_snapshot_are_known_stop_conditions(self):
        for name, options in (('temp', {'guards':{'guard:libJit.so':b''}}), ('snapshot', {'files':self.files | {'ram':b'own-bad'}})):
            result, peer, _, service, _ = self.make(name, **options)
            self.failed(result, stop=True); self.assertEqual(service.used, 16)
            self.assertNotIn('wire:saved', peer.trace)

    def test_changed_program_repeat_preserves_first_copy_and_stops(self):
        changed = self.files['appFw.so'][:-1] + b'Z'
        result, peer, _, service, root = self.make(changes={'appFw.so':changed})
        self.failed(result, stop=True); self.assertEqual(service.used, 16)
        self.assertEqual((root / 'source/appFw.so').read_bytes(), self.files['appFw.so'])
        self.assertEqual(peer.counts['read:appFw.so'], 2)

    def test_auth_intent_failure_sends_nothing_and_freezes_pipeline(self):
        real = capturestore.Store.event
        def fail(store, event, **details):
            if event == 'INTENT' and details.get('operation') == 'auth-normal-start': raise OSError('own')
            return real(store,event,**details)
        with patch.object(capturestore.Store, 'event', fail): result, peer, normal, service, _ = self.make()
        self.failed(result); self.assertTrue(result['pipeline_blocked'])
        self.assertEqual((normal.used,service.used),(0,0)); self.assertNotIn('service-observation',peer.trace)

    def test_auth_ack_loss_never_reaches_next_stage_or_healthy_exit(self):
        for index, operation in enumerate(('auth-normal-verify','auth-service-verify')):
            real = capturestore.Store.event
            def fail(store,event,**details):
                if event == 'ACK' and details.get('operation') == operation: raise OSError('own')
                return real(store,event,**details)
            with patch.object(capturestore.Store,'event',fail): result,peer,_,service,root = self.make(str(index))
            self.failed(result); self.assertTrue(result['pipeline_blocked']); self.assertLessEqual(service.used,15)
            self.assertNotIn('wire:hasp',peer.trace)
            self.assertEqual(i.inspect_directory(root)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_material_intent_or_ack_loss_blocks_even_healthy_stop(self):
        for index, kind in enumerate(('INTENT','ACK')):
            real = capturestore.Store.event
            def fail(store,event,**details):
                if event == kind and details.get('operation') == 'read:appFw.so': raise OSError('own')
                return real(store,event,**details)
            with patch.object(capturestore.Store,'event',fail): result,peer,_,service,_ = self.make(str(index))
            self.failed(result); self.assertTrue(result['pipeline_blocked']); self.assertEqual(service.used,15)
            self.assertEqual(peer.counts.get('read:appFw.so',0), 0 if kind=='INTENT' else 1)

    def test_non_io_material_record_failure_does_not_send_cleanup_stop(self):
        real = capturestore.Store.event
        def fail(store,event,**details):
            if event=='HOST_FILE_VERIFIED': raise OSError('own')
            return real(store,event,**details)
        with patch.object(capturestore.Store,'event',fail): result,_,_,service,root=self.make()
        self.failed(result); self.assertTrue(result['pipeline_blocked']); self.assertEqual(service.used,15)
        self.assertTrue((root/'source/appFw.so').is_file())

    def test_stop_intent_failure_keeps_single_allowance_without_control(self):
        real=capturestore.Store.event
        def fail(store,event,**details):
            if event=='INTENT' and details.get('operation')=='service-stop': raise OSError('own')
            return real(store,event,**details)
        with patch.object(capturestore.Store,'event',fail): result,_,_,service,_=self.make()
        self.failed(result); self.assertEqual(service.used,15); self.assertTrue(result['pipeline_blocked'])

    def test_stop_unknown_never_requeries_normal_and_cannot_replay(self):
        service=auth_fixture.tape(0x0336); service.transfers[-1]=('control',TimeoutError('own'))
        result,peer,normal,_,root=self.make(service=service)
        self.failed(result,unknown=True); self.assertEqual(service.used,16); self.assertNotIn('normal-after',peer.trace)
        before=(normal.used,service.used)
        with self.assertRaises(TypeError): p.rehearse('own',root,peer,normal,service)
        self.assertEqual(before,(normal.used,service.used))

    def test_stop_ack_loss_keeps_known_result_but_no_normal_query(self):
        real=capturestore.Store.event
        def fail(store,event,**details):
            if event=='ACK' and details.get('operation')=='service-stop': raise OSError('own')
            return real(store,event,**details)
        with patch.object(capturestore.Store,'event',fail): result,peer,_,service,root=self.make()
        self.failed(result,stop=True); self.assertEqual(service.used,16); self.assertNotIn('normal-after',peer.trace)
        self.assertTrue(result['pipeline_blocked']); self.assertEqual(result['authentication_phase'],'STOP_CONTROL_RETURNED')
        self.assertEqual(i.inspect_directory(root)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_normal_return_unknown_or_identity_change_never_finishes(self):
        for index,options in enumerate(({'fault':'normal-after'},{'returned':p.s.SyntheticPeer({}).initial | {'serial_sha256':'22'*32}})):
            result,_,_,service,root=self.make(str(index),**options)
            self.failed(result,unknown=True,stop=True); self.assertEqual(service.used,16)
            self.assertEqual(i.inspect_directory(root)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_return_ack_loss_blocks_completion_but_preserves_known_exit_and_match(self):
        real=capturestore.Store.event
        def fail(store,event,**details):
            if event=='ACK' and details.get('operation')=='normal-after': raise OSError('own')
            return real(store,event,**details)
        with patch.object(capturestore.Store,'event',fail): result,peer,_,service,root=self.make()
        self.failed(result,stop=True); self.assertTrue(result['pipeline_blocked'])
        self.assertTrue(result['simulated_normal_identity_matched']); self.assertEqual(service.used,16)
        self.assertEqual(peer.trace.count('normal-after'),1)
        self.assertEqual(i.inspect_directory(root)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_interrupt_during_auth_has_no_automatic_stop_or_material_commands(self):
        service=auth_fixture.tape(0x0336); service.transfers[3]=('write',KeyboardInterrupt())
        result,peer,_,_,root=self.make(service=service)
        self.failed(result,unknown=True); self.assertEqual(service.used,4)
        self.assertFalse(any(n.startswith('wire:') for n in peer.trace))
        self.assertEqual(i.inspect_directory(root)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_auth_marker_persistence_failure_blocks_start_of_materials_and_stop(self):
        real=capturestore.Store.event
        def fail(store,event,**details):
            if event=='RAW_AUTHENTICATION_MODELED': raise OSError('own')
            return real(store,event,**details)
        with patch.object(capturestore.Store,'event',fail): result,peer,_,service,_=self.make()
        self.failed(result); self.assertTrue(result['pipeline_blocked']); self.assertEqual(service.used,15)
        self.assertNotIn('wire:hasp',peer.trace)

    def test_no_space_prevents_identity_and_all_raw_calls(self):
        with patch.object(capturestore.Store,'require_space',side_effect=OSError('own no space')):
            result,peer,normal,service,_=self.make()
        self.failed(result); self.assertEqual((normal.used,service.used),(0,0))
        self.assertNotIn('normal-before',peer.trace)

    def test_shared_budget_instance_deadline_and_auth_counter_exclude_materials(self):
        seen=[]; real=p._Run.__init__
        def observe(run,*args): real(run,*args); seen.append(run)
        with patch.object(p._Run,'__init__',observe): result,*_=self.make()
        run,=seen
        self.assertIs(run.auth.budget,run.channel.budget)
        self.assertIs(run.auth.normal.budget,run.channel.budget); self.assertIs(run.auth.service.budget,run.channel.budget)
        self.assertEqual(run.auth.summary()['accepted_auth_bytes'],14448)
        self.assertEqual(run.channel.budget.used,result['accepted_total_bytes'])
        self.assertGreater(run.channel.budget.used,run.auth.accepted_bytes)

    def test_shared_deadline_expires_after_auth_before_first_material(self):
        real=p._Run.event
        def expire(run,event,**details):
            value=real(run,event,**details)
            if event=='RAW_AUTHENTICATION_MODELED': run.channel.budget.deadline=run.channel.budget.clock()
            return value
        with patch.object(p._Run,'event',expire): result,peer,_,service,_=self.make()
        self.failed(result); self.assertEqual(service.used,15); self.assertNotIn('wire:hasp',peer.trace)

    def test_remaining_deadline_is_used_by_final_stop_without_reset(self):
        real=p._Run.event
        def shorten(run,event,**details):
            value=real(run,event,**details)
            if event=='RAW_AUTHENTICATION_MODELED':
                run.channel.budget.clock=lambda:1199.0; run.channel.budget.deadline=1200.0
            return value
        with patch.object(p._Run,'event',shorten): result,_,_,service,_=self.make()
        self.assertEqual(result['phase'],'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')
        self.assertEqual(service.trace[-1],('control',1000))

    def test_shared_total_quota_stops_before_material_payload(self):
        real=p._Run.event
        def cap(run,event,**details):
            value=real(run,event,**details)
            if event=='RAW_AUTHENTICATION_MODELED': run.channel.budget.limit=run.channel.budget.used+87
            return value
        with patch.object(p._Run,'event',cap): result,_,_,service,_=self.make()
        self.failed(result,unknown=True); self.assertEqual(result['accepted_total_bytes'],14448)
        self.assertEqual(service.used,15)

    def test_inspector_rejects_forged_auth_counters_and_physical_flags(self):
        for index,change in enumerate(({'accepted_auth_bytes':0},{'auth_raw_calls':30},{'accepted_total_bytes':1},
                {'actual_authentication_verified':True},{'authentication_phase':'SERVICE_AUTHENTICATED'},
                {'shared_budget_modeled':False},{'pipeline_blocked':True})):
            *_,root=self.make(str(index)); self.edit_report(root,**change)
            self.assertEqual(i.inspect_directory(root)['classification'],'EVIDENCE_INCONSISTENT')

    def test_inspector_rejects_missing_or_rechained_misplaced_raw_auth_marker(self):
        for index in range(3):
            *_,root=self.make(str(index))
            def edit(row):
                if row['event']=='RAW_AUTHENTICATION_MODELED':
                    if index==0: row['event']='NORMAL_SAME_SOURCE_MATCH_MODELED'; row['details']={}
                    elif index==1: row['event']='NORMAL_SAME_SOURCE_MATCH_MODELED'; row['details']={}
                    else: row['details']['raw_calls']=31
                elif index==1 and row['event']=='GUARD_ABSENCE_MODELED':
                    row['event']='RAW_AUTHENTICATION_MODELED'; row['details']={'accepted_auth_bytes':14448,'raw_calls':30}
            self.rechain(root,edit)
            self.assertEqual(i.inspect_directory(root)['classification'],'EVIDENCE_INCONSISTENT')

    def test_standalone_auth_summary_cannot_be_promoted_to_complete_capture(self):
        *_,root=self.make()
        self.edit_report(root,schema='a7c2-synthetic-raw-authentication/1',phase='SIMULATED_AUTH_COMPLETE')
        self.assertEqual(i.inspect_directory(root)['classification'],'EVIDENCE_INCONSISTENT')

    def test_existing_directory_is_never_reused_with_fresh_drivers(self):
        *_,root=self.make(); peer=p.s.SyntheticPeer(self.files)
        normal,service=auth_fixture.tape(0x0e8a),auth_fixture.tape(0x0336)
        before={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}
        with self.assertRaises(FileExistsError): p.rehearse('own',root,peer,normal,service)
        self.assertEqual((normal.used,service.used),(0,0))
        self.assertEqual(before,{str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()})

    def test_inspector_preserves_all_bytes_and_write_metadata(self):
        *_,root=self.make()
        def snapshot():
            return {str(f.relative_to(root)):(f.stat().st_ino,f.stat().st_mtime_ns,f.stat().st_ctime_ns,hashlib.sha256(f.read_bytes()).hexdigest())
                    for f in root.rglob('*') if f.is_file()}
        before=snapshot(); self.assertEqual(i.inspect_directory(root)['classification'],'CONSISTENT_SIMULATION_COMPLETE')
        self.assertEqual(before,snapshot())

    def test_ver200_bad_battery_or_external_backend_rejected_before_any_step(self):
        for index,options in enumerate(({'version':'2.00'},{'battery':49},{'battery':True})):
            peer=p.s.SyntheticPeer(self.files,**options)
            with self.assertRaises(ValueError): p.rehearse('own',self.root/str(index),peer,auth_fixture.tape(0x0e8a),auth_fixture.tape(0x0336))
            self.assertEqual(peer.trace,[]); self.assertFalse((self.root/str(index)).exists())
        peer=p.s.SyntheticPeer(self.files)
        with self.assertRaises(TypeError): p.rehearse('own',self.root/'bad',peer,object(),auth_fixture.tape(0x0336))
        with self.assertRaises(TypeError): p.rehearse('own',self.root/'bad',peer,auth_fixture.tape(0x0e8a),auth_fixture.tape(0x0336),policy=self.fixture.policy)

    def test_summary_log_and_inspection_never_emit_keys_packets_or_identity(self):
        result,_,normal,service,root=self.make()
        text=json.dumps(result)+''.join(f.read_text() for f in (root/'events').glob('*.json'))+json.dumps(i.inspect_directory(root))
        for raw in (*auth_fixture.KEYS.sha1,*auth_fixture.KEYS.sha256,*normal.written,*service.written):
            self.assertNotIn(raw.hex(),text); self.assertNotIn(repr(raw),text)
        self.assertNotIn(str(root),text); self.assertNotIn('11'*32,text)

    def test_import_and_inspector_cli_require_no_device_modules_or_archive(self):
        code=('import sys; from lutphoto import capturepipeline; '
              'assert not any(n=="usb" or n.startswith("usb.") or n in ("Crypto","Cryptodome","transport","core","numpy","macfl23.session") for n in sys.modules)')
        result=subprocess.run([sys.executable,'-S','-B','-c',code],capture_output=True,cwd=p.a.w.ROOT)
        self.assertEqual(result.returncode,0,result.stderr)
        *_,root=self.make()
        result=subprocess.run([sys.executable,'-S','-B','-m','lutphoto.captureinspect','inspect','--directory',str(root)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr); self.assertNotIn(str(root),result.stdout)
        self.assertEqual(json.loads(result.stdout)['classification'],'CONSISTENT_SIMULATION_COMPLETE')


if __name__ == '__main__': unittest.main()
