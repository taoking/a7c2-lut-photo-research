"""Unified own OS/MSC/auth/material fixtures; no SDK or live lock/device."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import captureowned as o, captureinspect as i, capturestore, capturemsc
from research.tests import test_capturepipeline as fixture, test_captureauth as auth
from research.tests.test_capturemsc import tape, model_response
from research.tests.test_captureidentity import snapshot_with_serial


class OwnedTests(unittest.TestCase):
    def setUp(self):
        f=fixture.PipelineTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.fixture,self.root=f,f.root
        self.files={**f.files, **{name:snapshot_with_serial(f.files[name]) for name in ('ram','saved')}}
        patch.object(capturemsc,'verify_sources',return_value=(auth.PIN,{})).start();self.addCleanup(patch.stopall)

    def system(self,*,files=None,initial=None,returned=None,normal_options=None,service_options=None,system_options=None,**peer_options):
        peer=o.s.SyntheticPeer(self.files if files is None else files,**peer_options)
        normal=o.r.SyntheticDevice(o.m.NORMAL,auth.tape(o.m.NORMAL),peer,**(normal_options or {}))
        service=o.r.SyntheticDevice(o.m.SERVICE,auth.tape(o.m.SERVICE),peer,**(service_options or {}))
        return o.SyntheticSystem(peer,normal,service,tape() if initial is None else initial,tape() if returned is None else returned,**(system_options or {}))

    def make(self,name='owned',resources=False,**kw):
        system=self.system(**kw);directory=self.root/name
        result=o.rehearse('own',directory,system,resources=resources)
        return result,system,directory

    def records(self,directory):return self.fixture.records(directory)

    def rechain(self,directory,edit):
        head='0'*64
        for path in sorted((directory/'events').glob('*.json')):
            record=json.loads(path.read_bytes());edit(record);record['previous_sha256']=head
            raw=capturestore.encoded(record);path.write_bytes(raw);head=hashlib.sha256(raw).hexdigest()
        path=directory/o.REPORT;report=json.loads(path.read_bytes());report['journal_head_sha256']=head;path.write_bytes(capturestore.encoded(report))

    def test_full_three_owner_capture_and_fresh_protocol_identity(self):
        result,system,directory=self.make()
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE')
        self.assertEqual((result['identity_queries'],result['identity_raw_calls']),(2,28))
        self.assertEqual(result['accepted_identity_bytes'],2*sum(len(raw) for _,raw in tape()))
        self.assertEqual(result['accepted_auth_bytes'],14448);self.assertEqual(result['auth_raw_calls'],31)
        self.assertEqual(result['accepted_total_bytes'],sum(result[k] for k in ('accepted_auth_bytes','accepted_identity_bytes','accepted_payload_bytes')))
        self.assertEqual((result['owned_handles_opened'],result['owned_handles_closed']),(3,3))
        self.assertEqual(system.counts['dispose'],3);self.assertEqual(system.counts['release'],1);self.assertEqual(system.counts['attach'],1)
        self.assertTrue(all(d.closed for d in system.handles));self.assertEqual([d.used for d in system.handles],[14,0,14])
        self.assertEqual(system.service_device.counts['control'],2)
        self.assertEqual(system.service_device.counts['write'],7+result['requests'])
        self.assertFalse(any(n in system.peer.trace for n in ('normal-before','normal-after','service-observation')))
        self.assertEqual(i.inspect_directory(directory)['classification'],'CONSISTENT_SIMULATION_COMPLETE')
        for flag in i.FALSE_COMMON|i.FALSE_PROFILE['owned']:self.assertIs(result[flag],False)

    def test_resource_extension_same_service_and_all_materials(self):
        resource=o.s.c.synthetic_resource(False);files=self.files|{'resources/'+name:resource for name in o.s.c.RESOURCE_FILES}
        result,system,directory=self.make(files=files,resources=True)
        self.assertEqual(len(result['files']),74);self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE')
        self.assertEqual(system.counts['dispose'],3);self.assertLess(result['journal_records'],2048)
        self.assertEqual(i.inspect_directory(directory)['classification'],'CONSISTENT_SIMULATION_COMPLETE')

    def test_changed_return_serial_is_fresh_query_failure(self):
        result,system,directory=self.make(returned=tape(model_response(b'\4\3\2\1')))
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(result['identity_raw_calls'],28)
        self.assertFalse(result['simulated_normal_identity_matched']);self.assertTrue(result['simulated_service_stop_ack'])
        self.assertEqual(system.counts.get('attach',0),0);self.assertEqual(system.counts['dispose'],3)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_unknown_initial_msc_stops_before_auth(self):
        initial=tape();initial[1]=('read',TimeoutError('own'))
        result,system,directory=self.make(initial=initial)
        self.assertTrue(result['simulated_outcome_unknown']);self.assertEqual(result['identity_raw_calls'],2)
        self.assertEqual(system.counts.get('control',0),0);self.assertEqual(system.counts['dispose'],1)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_unknown_auth_has_no_service_material_stop_or_new_query(self):
        result,system,directory=self.make(service_options={'faults':{('read',2):TimeoutError('own')}})
        self.assertTrue(result['simulated_outcome_unknown']);self.assertEqual(result['identity_queries'],1)
        self.assertFalse(system.peer.counts);self.assertEqual(system.service_device.counts['control'],1)
        self.assertEqual(system.counts['dispose'],2)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_known_program_rejection_stops_once_and_requeries_normal(self):
        result,system,directory=self.make(files=self.files|{'appFw.so':bytes(len(self.files['appFw.so']))})
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertFalse(result['simulated_outcome_unknown'])
        self.assertTrue(result['simulated_service_stop_ack']);self.assertTrue(result['simulated_normal_identity_matched'])
        self.assertEqual(result['identity_queries'],2);self.assertEqual(system.service_device.counts['control'],2)
        self.assertNotIn('wire:read:cpapp-b.bin',system.peer.trace)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_INCOMPLETE')

    def test_unknown_material_has_no_stop_return_or_reattach(self):
        result,system,directory=self.make(service_options={'faults':{('write',8):None}})
        self.assertTrue(result['simulated_outcome_unknown']);self.assertEqual(result['identity_queries'],1)
        self.assertEqual(system.service_device.counts['control'],1);self.assertNotIn('simulate-normal-arrival',system.trace)
        self.assertEqual(system.trace[-3:],['write','dispose','global-release'])
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_service_disposal_failure_preserves_stop_and_forbids_return(self):
        result,system,directory=self.make(system_options={'faults':{('dispose',2):OSError('own')}})
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['simulated_service_stop_ack'])
        self.assertEqual(result['identity_queries'],1);self.assertFalse(result['simulated_normal_identity_matched'])
        self.assertEqual(system.counts['dispose'],2);self.assertNotIn('simulate-normal-arrival',system.trace)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_source_gate_before_modeled_global_acquisition(self):
        system=self.system()
        with patch.object(capturemsc,'verify_sources',side_effect=ValueError('source differs')):
            with self.assertRaises(ValueError):o.rehearse('own',self.root/'bad',system)
        self.assertFalse(system.trace);self.assertFalse((self.root/'bad').exists())

    def test_unsupported_version_refused_without_job_or_host(self):
        for version,battery in (('2.00',75),('2.01',True),('2.01',49)):
            system=self.system(version=version,battery=battery)
            with self.assertRaises(ValueError):o.rehearse('own',self.root/'bad',system)
            self.assertFalse(system.trace);self.assertFalse((self.root/'bad').exists())

    def test_existing_directory_not_adopted_or_device_disposed(self):
        directory=self.root/'existing';directory.mkdir(mode=0o700);system=self.system()
        with self.assertRaises(FileExistsError):o.rehearse('own',directory,system)
        self.assertEqual(system.trace,['global-acquire','global-release']);self.assertEqual(list(directory.iterdir()),[])
        self.assertTrue(all(not d.closed for d in system.handles))

    def test_public_guard_rejects_backend_subclass_and_replay(self):
        class External(o.SyntheticSystem):pass
        for system in (object(),External.__new__(External),o.m._NativeOps()):
            with self.assertRaises(TypeError):o.rehearse('own',self.root/'bad',system)
        _,system,_=self.make()
        before=list(system.trace)
        with self.assertRaises(TypeError):o.rehearse('own',self.root/'bad',system)
        self.assertEqual(system.trace,before)

    def test_global_then_job_lock_close_publish_unlock_order(self):
        system=self.system();directory=self.root/'ordered';order=[]
        create=capturestore.Store.__init__;close=capturestore.Store.close;put=capturestore.Store.put
        def creating(store,*args,**kw):
            self.assertTrue(system.acquired);self.assertEqual(system.trace,['global-acquire']);order.append('job-open');return create(store,*args,**kw)
        def publishing(store,name,*args,**kw):
            if name==o.REPORT:
                self.assertTrue(system.acquired);self.assertTrue(all(h.closed for h in system.handles))
                self.assertEqual(i.inspect_directory(directory)['issues'],['ACTIVE_JOB']);order.append('report')
            return put(store,name,*args,**kw)
        def closing(store):
            self.assertTrue(system.acquired);self.assertTrue(all(h.closed for h in system.handles));order.append('job-close');return close(store)
        with patch.object(capturestore.Store,'__init__',creating),patch.object(capturestore.Store,'put',publishing),patch.object(capturestore.Store,'close',closing):
            result=o.rehearse('own',directory,system)
        self.assertEqual(order,['job-open','report','job-close']);self.assertFalse(system.acquired)
        self.assertEqual(system.trace[-1],'global-release');self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE')

    def test_host_intent_precedes_every_msc_send_and_auth_intent_precedes_control(self):
        system=self.system();directory=self.root/'intent';send=o.SyntheticSystem.write;control=o.SyntheticSystem.control
        def latest():return json.loads(sorted((directory/'events').glob('*.json'))[-1].read_bytes())
        def write(backend,handle,*args):
            if handle.used<len(handle.identity):self.assertEqual(latest(),dict(latest(),event='HOST_INTENT',details={'operation':'NORMAL_IDENTITY_QUERY'}))
            return send(backend,handle,*args)
        def controlling(backend,handle,*args):
            self.assertEqual(latest()['event'],'INTENT');self.assertIn(latest()['details']['operation'],('auth-normal-start','auth-service-start','service-stop'))
            return control(backend,handle,*args)
        with patch.object(o.SyntheticSystem,'write',write),patch.object(o.SyntheticSystem,'control',controlling):result=o.rehearse('own',directory,system)
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE')

    def test_failed_open_ack_still_disposes_before_job_close(self):
        event=capturestore.Store.event
        def fail(store,name,**kw):
            if name=='HOST_ACK' and kw=={'operation':'OPEN_HANDLE'}:raise OSError('own journal')
            return event(store,name,**kw)
        with patch.object(capturestore.Store,'event',fail):result,system,directory=self.make()
        self.assertEqual(system.counts['dispose'],1);self.assertEqual(system.counts.get('claim',0),0)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')
        self.assertTrue(result['host_blocked'])

    def test_failed_dispose_intent_still_disposes_but_never_advances(self):
        event=capturestore.Store.event
        def fail(store,name,**kw):
            if name=='HOST_INTENT' and kw=={'operation':'DISPOSE_RESOURCES'}:raise OSError('own journal')
            return event(store,name,**kw)
        with patch.object(capturestore.Store,'event',fail):result,system,directory=self.make()
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['host_blocked'])
        self.assertEqual(system.counts['dispose'],1);self.assertNotIn('simulate-service-arrival',system.trace)
        self.assertNotEqual(i.inspect_directory(directory)['classification'],'CONSISTENT_SIMULATION_COMPLETE')

    def test_failed_dispose_ack_does_not_repeat_sdk_close(self):
        event=capturestore.Store.event
        def fail(store,name,**kw):
            if name=='HOST_ACK' and kw=={'operation':'DISPOSE_RESOURCES'}:raise OSError('own journal')
            return event(store,name,**kw)
        with patch.object(capturestore.Store,'event',fail):result,system,directory=self.make()
        self.assertEqual(system.counts['dispose'],1);self.assertNotIn('simulate-service-arrival',system.trace)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_primary_unknown_and_secondary_dispose_error_preserved(self):
        initial=tape();initial[1]=('read',TimeoutError('primary own'))
        result,system,directory=self.make(initial=initial,system_options={'faults':{('dispose',1):OSError('secondary own')}})
        self.assertEqual(result['reason_type'],'TimeoutError');self.assertEqual(result['cleanup_error_type'],'OSError')
        self.assertEqual(system.counts['dispose'],1);self.assertEqual(system.trace[-1],'global-release')
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_final_release_error_keeps_known_stop_and_return_but_not_complete(self):
        result,system,directory=self.make(system_options={'faults':{('release',1):OSError('own')}})
        self.assertTrue(result['simulated_service_stop_ack']);self.assertTrue(result['simulated_normal_identity_matched'])
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(system.counts['dispose'],3)
        self.assertEqual(system.counts.get('attach',0),0)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_unlock_failure_raises_even_if_private_report_exists(self):
        system=self.system(system_options={'faults':{('global-release',1):OSError('own unlock')}});directory=self.root/'unlock'
        with self.assertRaisesRegex(OSError,'own unlock'):o.rehearse('own',directory,system)
        self.assertTrue((directory/o.REPORT).exists());self.assertEqual(system.counts['dispose'],3)
        self.assertFalse(system.acquired)

    def test_job_close_failure_raises_and_global_release_still_attempted(self):
        close=capturestore.Store.close;system=self.system()
        def fail(store):close(store);raise OSError('own job close')
        with patch.object(capturestore.Store,'close',fail):
            with self.assertRaisesRegex(OSError,'own job close'):o.rehearse('own',self.root/'close-fail',system)
        self.assertEqual(system.trace[-1],'global-release');self.assertEqual(system.counts['dispose'],3)

    def test_unknown_stop_never_opens_return_handle(self):
        result,system,directory=self.make(service_options={'faults':{('control',2):TimeoutError('own')}})
        self.assertFalse(result['simulated_service_stop_ack']);self.assertEqual(result['identity_queries'],1)
        self.assertEqual(system.counts['open'],2);self.assertEqual(system.counts['dispose'],2)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_port_change_before_service_open_refused(self):
        locations=(o.m._Key(o.m.NORMAL,1,(1,2),4),o.m._Key(o.m.SERVICE,1,(9,),5),o.m._Key(o.m.NORMAL,1,(1,2),6))
        result,system,directory=self.make(system_options={'locations':locations})
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(system.counts['open'],1)
        self.assertEqual(system.counts['dispose'],1);self.assertFalse(system.peer.counts)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_host_lock_busy_no_job_or_cleanup(self):
        system=self.system(system_options={'faults':{('global-acquire',1):BlockingIOError()}})
        with self.assertRaises(BlockingIOError):o.rehearse('own',self.root/'busy',system)
        self.assertEqual(system.trace,['global-acquire']);self.assertFalse((self.root/'busy').exists())

    def test_shared_budget_object_and_deadline_before_all_three_queries_and_auth(self):
        seen=[];ready=o._OwnedPort._ready;query=o.m._Owner.query
        def remember(budget):
            seen.append((id(budget),budget.deadline));self.assertEqual(budget.deadline,1200)
        def protocol(port):remember(port.budget);return ready(port)
        def identity(owner):remember(owner.host.budget);return query(owner)
        with patch.object(o._OwnedPort,'_ready',protocol),patch.object(o.m._Owner,'query',identity):result,_,_=self.make()
        self.assertEqual(len(set(seen)),1);self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE')

    def test_report_does_not_contain_raw_identity_or_host_locations(self):
        _,_,directory=self.make();text=(directory/o.REPORT).read_text()
        self.assertNotIn(hashlib.sha256(b'0123abcd').hexdigest(),text)
        for word in ('serial_sha256','disk9','endpoint','bus','ports','/dev/','/Users/'):
            self.assertNotIn(word,text)
        for record in self.records(directory):self.assertNotIn('serial',str(record))

    def test_rechained_host_query_ack_removed_retains_unknown(self):
        _,_,directory=self.make();done=[False]
        def remove(record):
            if not done[0] and record['event']=='HOST_ACK' and record['details'].get('operation')=='NORMAL_IDENTITY_QUERY':
                record['event']='NORMAL_SAME_SOURCE_MATCH_MODELED';record['details']={};done[0]=True
        self.rechain(directory,remove)
        result=i.inspect_directory(directory)
        self.assertNotEqual(result['classification'],'CONSISTENT_SIMULATION_COMPLETE');self.assertGreater(result['unacknowledged_intents'],0)

    def test_rechained_duplicate_owner_receipt_or_wrong_stage_rejected(self):
        for case in ('duplicate','wrong-stage'):
            _,_,directory=self.make(case)
            def edit(record):
                if record['event']=='OWNED_HANDLE_CLOSED_MODELED' and record['details']['role']=='normal-return':
                    record['details']['role']='service' if case=='duplicate' else 'normal-initial'
            self.rechain(directory,edit)
            self.assertEqual(i.inspect_directory(directory)['classification'],'EVIDENCE_INCONSISTENT')

    def test_rechained_host_operation_order_changed_rejected(self):
        _,_,directory=self.make()
        def edit(record):
            if record['event'] in ('HOST_INTENT','HOST_ACK') and record['details'].get('operation')=='NORMAL_IDENTITY_QUERY':record['details']['operation']='CLAIM_INTERFACE'
        self.rechain(directory,edit)
        self.assertEqual(i.inspect_directory(directory)['classification'],'EVIDENCE_INCONSISTENT')

    def test_identity_counts_and_unsupported_physical_claims_rejected(self):
        for key,value in (('accepted_identity_bytes',0),('identity_raw_calls',27),('owned_handles_closed',2),
                          ('fresh_normal_observation_verified',True),('global_camera_lock_acquired',True)):
            _,_,directory=self.make(key);path=directory/o.REPORT;report=json.loads(path.read_bytes());report[key]=value;path.write_bytes(capturestore.encoded(report))
            self.assertEqual(i.inspect_directory(directory)['classification'],'EVIDENCE_INCONSISTENT')

    def test_readonly_inspection_preserves_contents_inodes_and_write_times(self):
        _,_,directory=self.make()
        def snapshot():
            return {str(p.relative_to(directory)):(p.stat().st_ino,p.stat().st_mode,p.stat().st_mtime_ns,p.stat().st_ctime_ns,
                    hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None) for p in [directory,*directory.rglob('*')]}
        before=snapshot();result=i.inspect_directory(directory)
        self.assertEqual(result['classification'],'CONSISTENT_SIMULATION_COMPLETE');self.assertEqual(snapshot(),before)

    def test_persistent_journal_failure_stops_protocol_and_disposes(self):
        event=capturestore.Store.event;broken=[False]
        def fail(store,name,**kw):
            if name=='ACK' and kw=={'operation':'auth-service-verify'}:broken[0]=True
            if broken[0]:raise OSError('own journal unavailable')
            return event(store,name,**kw)
        with patch.object(capturestore.Store,'event',fail):result,system,directory=self.make()
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertFalse(system.peer.counts)
        self.assertEqual(system.counts['dispose'],2);self.assertEqual(system.service_device.counts['control'],1)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_import_under_no_site_has_no_usb_or_native_runtime(self):
        result=subprocess.run([sys.executable,'-S','-B','-c',
            'from lutphoto import captureowned; import sys; assert not any(n=="usb" or n.startswith("usb.") or n=="libusb_package" for n in sys.modules)'],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())

    def test_deadline_expired_in_auth_never_restarts_for_materials(self):
        control=o.SyntheticSystem.control
        def expires(system,*args):
            result=control(system,*args);system.now=1201;return result
        with patch.object(o.SyntheticSystem,'control',expires):result,system,directory=self.make()
        self.assertTrue(result['simulated_outcome_unknown']);self.assertEqual(system.counts['control'],1)
        self.assertEqual(system.counts['dispose'],1);self.assertFalse(system.peer.counts)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_real_readonly_cli_accepts_new_format_without_writing(self):
        _,_,directory=self.make()
        before={p:(p.read_bytes(),p.stat().st_mtime_ns,p.stat().st_ctime_ns) for p in directory.rglob('*') if p.is_file()}
        result=subprocess.run([sys.executable,'-S','-B','-m','lutphoto.captureinspect','inspect','--directory',str(directory)],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertEqual(json.loads(result.stdout)['classification'],'CONSISTENT_SIMULATION_COMPLETE')
        self.assertEqual(before,{p:(p.read_bytes(),p.stat().st_mtime_ns,p.stat().st_ctime_ns) for p in before})

    def test_forged_owned_claim_on_old_pipeline_report_is_rejected(self):
        _,_,directory=self.make();old=directory/'pipeline-report.private.json';path=directory/o.REPORT
        value=json.loads(path.read_bytes());value['schema']='a7c2-synthetic-authenticated-capture/1';value['phase']='SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE'
        for key in i.OWNED_COUNTERS|{'host_binding_modeled','host_blocked','cleanup_error_type'}:value.pop(key)
        value['accepted_total_bytes']=value['accepted_auth_bytes']+value['accepted_payload_bytes']
        path.unlink();old.write_bytes(capturestore.encoded(value));old.chmod(0o600)
        self.assertEqual(i.inspect_directory(directory)['classification'],'EVIDENCE_INCONSISTENT')

    def test_unknown_final_return_query_does_not_trigger_reauth_or_second_stop(self):
        returned=tape();returned[1]=('read',TimeoutError('own late identity'))
        result,system,directory=self.make(returned=returned)
        self.assertTrue(result['simulated_service_stop_ack']);self.assertFalse(result['simulated_normal_identity_matched'])
        self.assertEqual(system.service_device.counts['control'],2);self.assertEqual(system.counts['dispose'],3)
        self.assertEqual(system.counts.get('attach',0),0);self.assertEqual(result['identity_raw_calls'],16)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')
