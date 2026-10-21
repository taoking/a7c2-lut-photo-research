"""Run existing NativeOps and candidate against own fake SDK/OS only."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import captureowned as o, capturecandidate as c, captureinspect as i, capturestore
from lutphoto.capturecontrol import Cancellation
from research.tests.test_capturemsc import tape,model_response
from research.tests import test_captureowned as fixtures
from research.tests.native_sdk_fixture import World,Device,m


class NativeIntegrationTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.OwnedTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.fixture,self.root,self.files=f,f.root,f.files

    def make(self,name='native',*,resources=False,faults=None,cancel=None,**options):
        world=World(self.fixture.system(**options),faults=faults);directory=self.root/name
        return world.run('own',directory,resources=resources,cancel=cancel),world,directory

    def test_full_native_methods_on_fake_sdk_use_fresh_owned_objects(self):
        result,w,directory=self.make()
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE',result.get('reason_type'))
        owners=[owner.device for owner in w.host.owners]
        self.assertEqual(len(owners),3);self.assertEqual([d.phase for d in owners],[0,1,2])
        self.assertEqual(len({id(d) for d in owners}),3);self.assertIs(type(w.ops),m._NativeOps)
        self.assertTrue(all(d.disposed and d.dispose_attempts==1 for d in w.devices))
        self.assertEqual([d for d in w.devices if d.opened],owners)
        for name,d in w.trace:
            if name in ('write','read','control','claim','release','implicit-release','lazy-open','configuration'):
                self.assertIn(d,owners)
        self.assertEqual(w.counts['lazy-open'],3);self.assertEqual(w.counts['implicit-release'],2)
        self.assertEqual(w.counts['release'],1);self.assertEqual(w.system.counts['attach'],1)
        self.assertEqual(result['identity_raw_calls'],28);self.assertEqual(result['auth_raw_calls'],31)
        self.assertFalse(w.system.acquired);self.assertEqual(w.trace[-1][0],'lock-close')
        self.assertEqual(i.inspect_directory(directory)['classification'],'CONSISTENT_SIMULATION_COMPLETE')
        for flag in i.FALSE_COMMON|i.FALSE_PROFILE['owned']:self.assertIs(result[flag],False)

    def test_duplicate_enumeration_rejected_and_each_sdk_object_disposed_once(self):
        w=World(self.fixture.system());device=Device(w,w.system.keys[0]);w.devices.append(device)
        def duplicate(**kw):return iter((device,device)) if kw['idProduct']==m.NORMAL else iter(())
        directory=self.root/'duplicate'
        with patch.object(w.core,'find',duplicate):result=w.run('own',directory)
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(result['owned_handles_opened'],0)
        self.assertEqual(device.dispose_attempts,1);self.assertFalse(device.opened)

    def test_busy_global_lock_and_failed_close_preserve_primary_error(self):
        w=World(self.fixture.system(system_options={'faults':{('global-release',1):OSError('own close')}}),
                faults={('lock-flock',1):BlockingIOError('own busy')})
        directory=self.root/'busy'
        with self.assertRaisesRegex(BlockingIOError,'own busy') as raised:w.run('own',directory)
        self.assertIsInstance(raised.exception.__cause__,OSError)
        self.assertEqual(str(raised.exception.__cause__),'own close')
        self.assertFalse(directory.exists());self.assertFalse(w.devices)
        self.assertEqual(w.counts['lock-close'],1)

    def test_optional_resources_same_service_and_matched_74_materials(self):
        files=self.files|{'resources/'+n:o.s.c.synthetic_resource(False) for n in o.s.c.RESOURCE_FILES}
        result,w,directory=self.make(files=files,resources=True)
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE');self.assertEqual(len(result['files']),74)
        service=w.host.owners[1].device
        self.assertEqual({id(d) for name,d in w.trace if name=='write' and d.idProduct==m.SERVICE},{id(service)})
        self.assertEqual(i.inspect_directory(directory)['classification'],'CONSISTENT_SIMULATION_COMPLETE')

    def test_native_result_matches_existing_candidate_materials_and_protocol_counters(self):
        system=self.fixture.system();reference=c.rehearse('own',self.root/'reference',system)
        result,_,_=self.make()
        for name in ('files','accepted_payload_bytes','accepted_identity_bytes','accepted_auth_bytes','accepted_total_bytes',
                     'identity_queries','identity_raw_calls','auth_raw_calls','requests'):
            self.assertEqual(result[name],reference[name],name)

    def test_enumeration_dispose_failure_stops_before_media_or_owner(self):
        for value in (False,OSError('own SDK close')):
            result,w,directory=self.make(name=type(value).__name__,faults={('dispose',1):value})
            self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(result['owned_handles_opened'],0)
            self.assertEqual(w.devices[0].dispose_attempts,1);self.assertFalse(w.devices[0].opened)
            self.assertEqual(w.counts.get('command',0),0)
            self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_partial_sdk_enumeration_preserves_primary_and_cleans_accumulated_objects(self):
        result,w,directory=self.make(faults={('find',2):TimeoutError('own enumeration'),('dispose',1):OSError('own cleanup')})
        self.assertEqual(result['reason_type'],'TimeoutError');self.assertEqual(len(w.devices),1)
        self.assertEqual(w.devices[0].dispose_attempts,1);self.assertEqual(result['owned_handles_opened'],0)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_open_uses_fresh_enumeration_and_refuses_changed_or_duplicate_sdk_object(self):
        for variant in ('changed','alias','two-objects'):
            with self.subTest(variant=variant):
                w=World(self.fixture.system());find=w.core.find
                def observed(**kw):
                    for d in find(**kw):
                        if w.system.counts['inventory']==3:
                            if variant=='changed':d.port_numbers=()
                            yield d
                            if variant=='alias':yield d
                            elif variant=='two-objects':
                                extra=Device(w,d.key);w.devices.append(extra);yield extra
                        else:yield d
                with patch.object(w.core,'find',observed):result=w.run('own',self.root/variant)
                self.assertEqual(result['owned_handles_opened'],0);self.assertEqual(w.counts.get('lazy-open',0),0)
                self.assertTrue(all(d.dispose_attempts==1 for d in w.devices))

    def test_open_ack_failure_adopts_unopened_sdk_object_and_disposes_once(self):
        event=capturestore.Store.event
        def fail(store,name,**kw):
            if name=='HOST_ACK' and kw=={'operation':'OPEN_HANDLE'}:raise OSError('own journal')
            return event(store,name,**kw)
        with patch.object(capturestore.Store,'event',fail):result,w,directory=self.make()
        owner,=w.host.owners;self.assertTrue(owner.device.disposed);self.assertFalse(owner.device.opened)
        self.assertEqual(owner.device.dispose_attempts,1);self.assertEqual(w.counts.get('claim',0),0)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')
        self.assertEqual(result['owned_handles_opened'],1)

    def test_configuration_failure_after_lazy_open_is_owned_before_cleanup(self):
        result,w,directory=self.make(faults={('configuration',1):OSError('own config')})
        self.assertEqual(result['owned_handles_opened'],1);self.assertEqual(w.counts['lazy-open'],1)
        self.assertEqual(w.host.owners[0].device.dispose_attempts,1);self.assertEqual(w.counts.get('claim',0),0)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_claim_failure_does_not_query_and_disposal_can_implicitly_release(self):
        result,w,_=self.make(system_options={'faults':{('claim',1):OSError('own claim')}})
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(w.counts.get('write',0),0)
        self.assertEqual(w.counts['implicit-release'],1);self.assertEqual(w.counts.get('release',0),0)
        self.assertEqual(w.system.counts.get('attach',0),0)
        self.assertEqual(w.host.owners[0].device.dispose_attempts,1)

    def test_unknown_identity_auth_material_and_stop_have_no_extra_return(self):
        bad=tape();bad[1]=('read',TimeoutError('own CSW'))
        cases=({'initial':bad},{'service_options':{'faults':{('read',2):TimeoutError('own auth')}}},
               {'service_options':{'faults':{('write',8):None}}},
               {'service_options':{'faults':{('control',2):TimeoutError('own stop')}}})
        for index,options in enumerate(cases):
            with self.subTest(index=index):
                result,w,directory=self.make(name='unknown'+str(index),**options)
                self.assertTrue(result['simulated_outcome_unknown']);self.assertFalse(result['simulated_normal_identity_matched'])
                self.assertEqual(result['identity_queries'],1);self.assertTrue(all(d.dispose_attempts==1 for d in w.devices))
                self.assertEqual(w.system.counts.get('attach',0),0)
                self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_full_program_mismatch_only_one_healthy_stop_and_fresh_return(self):
        result,w,directory=self.make(files=self.files|{'appFw.so':bytes(len(self.files['appFw.so']))})
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertFalse(result['simulated_outcome_unknown'])
        self.assertTrue(result['simulated_normal_identity_matched']);self.assertEqual(result['identity_queries'],2)
        self.assertEqual(w.system.service_device.counts['control'],2)
        self.assertNotIn('wire:read:cpapp-b.bin',w.system.peer.trace)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_INCOMPLETE')

    def test_normal_return_serial_is_queried_again_and_mismatch_refused(self):
        result,w,directory=self.make(returned=tape(model_response(b'\4\3\2\1')))
        self.assertEqual(result['identity_raw_calls'],28);self.assertFalse(result['simulated_normal_identity_matched'])
        self.assertEqual(w.counts['lazy-open'],3);self.assertEqual(w.system.counts.get('attach',0),0)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_cooperative_cancel_or_deadline_cannot_preempt_sdk_call(self):
        original=Device.get_active_configuration
        for mode in ('cancel','deadline'):
            with self.subTest(mode=mode):
                token=Cancellation();w=World(self.fixture.system());directory=self.root/mode;observed=[]
                def inside(device):
                    value=original(device)
                    if mode=='cancel':token.cancel()
                    else:w.system.now=1201
                    self.assertTrue(w.system.acquired);self.assertIs(w.host.owners[0].device,device)
                    self.assertEqual(i.inspect_directory(directory)['issues'],['ACTIVE_JOB'])
                    self.assertFalse(device.disposed);observed.append(True);return value
                with patch.object(Device,'get_active_configuration',inside):result=w.run('own',directory,cancel=token)
                self.assertEqual(result['reason_type'],'OperationCancelled' if mode=='cancel' else 'TimeoutError')
                self.assertEqual(observed,[True]);self.assertEqual(w.host.owners[0].device.dispose_attempts,1)
                self.assertEqual(w.counts.get('claim',0),0);self.assertEqual(w.counts.get('write',0),0)

    def test_failed_dispose_journal_still_calls_sdk_once_and_never_advances(self):
        event=capturestore.Store.event
        for name_to_fail in ('HOST_INTENT','HOST_ACK'):
            w=World(self.fixture.system());directory=self.root/name_to_fail
            def fail(store,name,**kw):
                if name==name_to_fail and kw=={'operation':'DISPOSE_RESOURCES'}:raise OSError('own journal')
                return event(store,name,**kw)
            with patch.object(capturestore.Store,'event',fail):result=w.run('own',directory)
            self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(result['owned_handles_opened'],1)
            self.assertEqual(w.host.owners[0].device.dispose_attempts,1);self.assertEqual(w.system.phase,0)

    def test_service_dispose_and_final_release_failure_not_completed_or_retried(self):
        for operation,ordinal in (('dispose',2),('release',1),('attach',1)):
            result,w,directory=self.make(name=operation,system_options={'faults':{(operation,ordinal):OSError('own cleanup')}})
            self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['simulated_service_stop_ack'])
            self.assertTrue(all(d.dispose_attempts==1 for d in w.devices))
            self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_normal_wait_timeout_preserves_stop_without_inventing_return(self):
        result,w,directory=self.make(system_options={'arrivals':{2:((),)}})
        self.assertTrue(result['simulated_service_stop_ack']);self.assertFalse(result['simulated_outcome_unknown'])
        self.assertEqual(result['reason_type'],'ObservationTimeout');self.assertEqual(len(w.host.owners),2)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_store_and_fake_global_lease_order_and_sdk_disposal_before_publication(self):
        w=World(self.fixture.system());directory=self.root/'order';order=[]
        create=capturestore.Store.__init__;close=capturestore.Store.close;put=capturestore.Store.put
        def create_job(store,*args,**kw):
            self.assertEqual(w.counts['lock-flock'],1);self.assertTrue(w.system.acquired);order.append('job-open')
            return create(store,*args,**kw)
        def publish(store,name,*args,**kw):
            if name==o.REPORT:
                self.assertTrue(all(d.disposed for d in w.devices));self.assertTrue(w.system.acquired);order.append('report')
            return put(store,name,*args,**kw)
        def close_job(store):self.assertTrue(w.system.acquired);order.append('job-close');return close(store)
        with patch.object(capturestore.Store,'__init__',create_job),patch.object(capturestore.Store,'put',publish),patch.object(capturestore.Store,'close',close_job):
            result=w.run('own',directory)
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE')
        self.assertEqual(order,['job-open','report','job-close']);self.assertEqual(w.trace[-1][0],'lock-close')

    def test_real_cli_inspects_completed_fake_sdk_evidence_without_modification(self):
        _,_,directory=self.make()
        def stamp():
            return {p.relative_to(directory):(p.stat().st_ino,p.stat().st_mode,p.stat().st_mtime_ns,p.stat().st_ctime_ns,p.read_bytes())
                    for p in directory.rglob('*') if p.is_file()}
        before=stamp()
        result=subprocess.run([sys.executable,'-S','-B','-m','lutphoto.captureinspect','inspect','--directory',str(directory)],
                              capture_output=True,text=True,cwd=Path(__file__).resolve().parents[2],timeout=20)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['classification'],'CONSISTENT_SIMULATION_COMPLETE')
        self.assertEqual(before,stamp());self.assertNotIn(str(directory),result.stdout)

    def test_harness_import_has_no_sdk_and_public_live_guard_stays_closed(self):
        script="import sys; from research.tests import native_sdk_fixture; assert not any(n=='usb' or n.startswith('usb.') or n=='libusb_package' for n in sys.modules); print('PASS')"
        result=subprocess.run([sys.executable,'-S','-B','-c',script],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[2],timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,'PASS\n')
        with self.assertRaises(c.NativeCandidateBlocked):c.capture(archive='own',ops=m._NativeOps(),enable=True)


if __name__=='__main__':unittest.main()
