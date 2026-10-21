"""Native-shaped own OS capability only; no SDK/USB or real global lock."""
import contextlib
import inspect
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from lutphoto import capturecandidate as c, captureowned as o, captureinspect as i, capturestore
from lutphoto.capturecontrol import Cancellation, OperationCancelled
from research.tests import test_captureowned as fixtures


class CandidateTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.OwnedTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.fixture,self.root,self.files=f,f.root,f.files
        patch.object(o.m._NativeOps,'__init__',side_effect=AssertionError('No native constructor')).start()
        patch.object(o.m._NativeOps,'_runtime',side_effect=AssertionError('No native runtime')).start()
        self.addCleanup(patch.stopall)

    def make(self,name='candidate',resources=False,**kw):
        system=self.fixture.system(**kw);directory=self.root/name
        result=c.rehearse('own',directory,system,resources=resources)
        return result,system,directory

    def test_same_materials_auth_identity_and_disposal_without_fake_arrival_hooks(self):
        reference,_,_=self.fixture.make(name='reference')
        with patch.object(o.SyntheticSystem,'service_arrival',side_effect=AssertionError('No fake hook')),patch.object(o.SyntheticSystem,'normal_arrival',side_effect=AssertionError('No fake hook')):
            result,system,directory=self.make()
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE')
        for name in ('files','accepted_payload_bytes','accepted_identity_bytes','accepted_auth_bytes','accepted_total_bytes',
                     'requests','identity_queries','identity_raw_calls','auth_raw_calls','owned_handles_opened','owned_handles_closed'):
            self.assertEqual(result[name],reference[name],name)
        self.assertEqual(system.counts['dispose'],3);self.assertFalse(system.acquired)
        self.assertFalse(any('simulate-' in name for name in system.trace))
        records=self.fixture.records(directory)
        self.assertEqual(sum(r['event']=='NATIVE_BINDING_CANDIDATE_MODELED' for r in records),1)
        self.assertEqual(sum(r['event']=='HOST_WAIT_END_MODELED' for r in records),2)
        self.assertEqual(i.inspect_directory(directory)['classification'],'CONSISTENT_SIMULATION_COMPLETE')
        for flag in i.FALSE_COMMON|i.FALSE_PROFILE['owned']:self.assertIs(result[flag],False)

    def test_coordinator_has_no_peer_or_system_arrival_capability(self):
        material=o._Run.materials;seen=[]
        def check(run,resources):
            self.assertIsNone(run.peer);self.assertIsNone(run.system);seen.append(True)
            return material(run,resources)
        with patch.object(c._NativeRun,'materials',check):result,_,_=self.make()
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE');self.assertEqual(seen,[True])

    def test_fake_ops_exposes_only_reviewed_native_method_signatures(self):
        names={'clock','sleep','acquire','unlock','inventory','media','unmount','open','descriptor','active','detach',
               'attach','claim','release','dispose','control','write','read'}
        self.assertEqual({n for n in vars(c._CandidateOps) if not n.startswith('_')},names)
        for name in names-{'clock','sleep'}:
            self.assertEqual(inspect.signature(getattr(c._CandidateOps,name)),inspect.signature(getattr(o.m._NativeOps,name)),name)
        for name in ('clock','sleep'):
            # Python 3.12 does not expose signatures for these C builtins.
            self.assertIs(getattr(o.m._NativeOps,name),getattr(time,'monotonic' if name=='clock' else 'sleep'))
            self.assertEqual(len(inspect.signature(getattr(c._CandidateOps,name)).parameters),1 if name=='clock' else 2)
        with self.assertRaises(TypeError):c._CandidateOps(object())

    def test_resource_scope_74_files_on_same_service(self):
        files=self.files|{'resources/'+n:o.s.c.synthetic_resource(False) for n in o.s.c.RESOURCE_FILES}
        result,system,directory=self.make(files=files,resources=True)
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE');self.assertEqual(len(result['files']),74)
        self.assertEqual(system.counts['dispose'],3);self.assertEqual(system.service_device.counts['control'],2)
        self.assertEqual(i.inspect_directory(directory)['classification'],'CONSISTENT_SIMULATION_COMPLETE')

    def test_delayed_passive_inventory_then_stable_arrival(self):
        keys=self.fixture.system().keys
        result,system,directory=self.make(system_options={'arrivals':{1:((),(keys[0],),(keys[1],),(keys[1],)),2:((),(keys[2],),(keys[2],))}})
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE');self.assertEqual(system.counts['open'],3)
        waits=[r['details']['polls'] for r in self.fixture.records(directory) if r['event']=='HOST_WAIT_END_MODELED']
        self.assertEqual(waits,[4,3]);self.assertEqual(i.inspect_directory(directory)['classification'],'CONSISTENT_SIMULATION_COMPLETE')

    def test_wait_timeouts_have_no_retry_and_preserve_known_stop(self):
        for phase in (1,2):
            with self.subTest(phase=phase):
                result,system,directory=self.make(name='wait'+str(phase),system_options={'arrivals':{phase:((),)}})
                self.assertEqual(result['reason_type'],'ObservationTimeout');self.assertFalse(result['simulated_outcome_unknown'])
                self.assertIs(result['simulated_service_stop_ack'],phase==2)
                self.assertEqual(system.counts['open'],phase);self.assertEqual(system.counts['dispose'],phase)
                self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_unknown_auth_material_stop_or_disposal_forbids_return(self):
        cases=({'service_options':{'faults':{('read',2):TimeoutError('own')}}},
               {'service_options':{'faults':{('write',8):None}}},
               {'service_options':{'faults':{('control',2):TimeoutError('own')}}},
               {'system_options':{'faults':{('dispose',2):False}}})
        for index,options in enumerate(cases):
            with self.subTest(index=index):
                result,system,directory=self.make(name='unknown'+str(index),**options)
                self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertFalse(result['simulated_normal_identity_matched'])
                self.assertEqual(system.counts['open'],2);self.assertEqual(system.counts['dispose'],2)
                self.assertEqual(system.counts.get('attach',0),0)
                self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_known_program_rejection_only_single_healthy_exit(self):
        result,system,directory=self.make(files=self.files|{'appFw.so':bytes(len(self.files['appFw.so']))})
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertFalse(result['simulated_outcome_unknown'])
        self.assertEqual(system.service_device.counts['control'],2);self.assertEqual(result['identity_queries'],2)
        self.assertNotIn('wire:read:cpapp-b.bin',system.peer.trace)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_INCOMPLETE')

    def test_cancel_after_open_adopts_once_before_any_protocol(self):
        token=Cancellation();original=o.SyntheticSystem.open
        def opened(system,key):
            handle=original(system,key);token.cancel();return handle
        with patch.object(o.SyntheticSystem,'open',opened):result,system,_=self.make_cancel(token)
        self.assertEqual(result['reason_type'],'OperationCancelled');self.assertEqual(system.counts['dispose'],1)
        self.assertEqual(system.counts.get('claim',0),0);self.assertEqual(system.counts.get('write',0),0)

    def make_cancel(self,token):
        system=self.fixture.system();directory=self.root/'cancel'
        return c.rehearse('own',directory,system,cancel=token),system,directory

    def test_cancel_before_entry_and_source_failure_do_not_create_job(self):
        token=Cancellation();token.cancel();system=self.fixture.system()
        with self.assertRaises(OperationCancelled):c.rehearse('own',self.root/'bad',system,cancel=token)
        with patch.object(c.capturemsc,'verify_sources',side_effect=ValueError('own source')):
            with self.assertRaises(ValueError):c.rehearse('own',self.root/'bad',system)
        self.assertFalse(system.trace);self.assertFalse((self.root/'bad').exists())

    def test_unsupported_input_subclass_version_replay_and_backend_override_refused(self):
        class External(o.SyntheticSystem):pass
        for system in (object(),External.__new__(External)):
            with self.assertRaises(TypeError):c.rehearse('own',self.root/'bad',system)
        for version,battery in (('2.00',75),('2.01',49),('2.01',True)):
            system=self.fixture.system(version=version,battery=battery)
            with self.assertRaises(ValueError):c.rehearse('own',self.root/'bad',system)
            self.assertFalse(system.trace)
        _,system,_=self.make()
        before=list(system.trace)
        with self.assertRaises(TypeError):c.rehearse('own',self.root/'bad',system)
        with self.assertRaises(TypeError):c.rehearse('own',self.root/'bad',system,ops=object())
        self.assertEqual(system.trace,before)

    def test_same_global_job_report_close_order(self):
        system=self.fixture.system();directory=self.root/'order';order=[]
        put=capturestore.Store.put;close=capturestore.Store.close
        def publish(store,name,*args,**kwargs):
            if name==o.REPORT:
                self.assertTrue(system.acquired);self.assertTrue(all(h.closed for h in system.handles))
                self.assertEqual(i.inspect_directory(directory)['issues'],['ACTIVE_JOB']);order.append('report')
            return put(store,name,*args,**kwargs)
        def closed(store):
            self.assertTrue(system.acquired);order.append('job-close');return close(store)
        with patch.object(capturestore.Store,'put',publish),patch.object(capturestore.Store,'close',closed):
            result=c.rehearse('own',directory,system)
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE');self.assertEqual(order,['report','job-close'])
        self.assertEqual(system.trace[-1],'global-release')

    def test_journal_dispose_ack_failure_never_advances_or_repeats_close(self):
        event=capturestore.Store.event
        def fail(store,name,**kwargs):
            if name=='HOST_ACK' and kwargs=={'operation':'DISPOSE_RESOURCES'}:raise OSError('own journal')
            return event(store,name,**kwargs)
        with patch.object(capturestore.Store,'event',fail):result,system,directory=self.make()
        self.assertEqual(system.counts['dispose'],1);self.assertEqual(system.counts['open'],1)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')
        self.assertTrue(result['host_blocked'])

    def test_review_matches_fixed_request_and_material_scope_without_native_entry(self):
        for resources in (False,True):
            review=c.review('own',resources=resources);channel=c.OfflineChannel('own',resources=resources,guards=True)
            self.assertEqual(review['phase'],'NATIVE_CANDIDATE_BLOCKED');self.assertEqual(review['requirements']['firmware'],'2.01')
            self.assertEqual(review['requirements']['source_kind'],'stock')
            self.assertEqual(len(review['saved_materials']),74 if resources else 6)
            self.assertEqual(review['fixed_request_count'],171 if resources else 35)
            self.assertEqual({r['operation'] for r in review['fixed_requests']},set(channel.requests))
            self.assertEqual(review['guard_names'],list(channel.guard_names));self.assertEqual(len(review['guard_names']),14)
            for name in ('live_execution_enabled','native_management_interruptible','sdk_imported_or_loaded',
                         'camera_operations_performed','camera_version_verified','battery_verified','program_fingerprints_verified'):
                self.assertIs(review[name],False)
            text=json.dumps(review)
            for secret in (str(self.root),'serial_sha256','request_data','request_hex'):self.assertNotIn(secret,text)

    def test_live_capture_always_refuses_before_argument_access_even_with_mutated_review(self):
        class Poison:
            def __fspath__(self):raise AssertionError('No filesystem access')
        review=c.review('own');review['live_execution_enabled']=True
        with self.assertRaises(c.NativeCandidateBlocked):c.capture(Poison(),Poison(),review=review,enabled=True)
        with self.assertRaises(TypeError):c.review('own',resources=1)
        with self.assertRaises(TypeError):c.review('own',firmware='2.00')

    def test_review_cli_only_and_errors_have_no_private_path_or_live_flags(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):code=c.main(['review','--archive','own','--resources'])
        self.assertEqual(code,0);self.assertFalse(json.loads(output.getvalue())['live_execution_enabled'])
        with contextlib.redirect_stderr(io.StringIO()):
            for args in (['capture','--archive','own'],['review','--archive','own','--enable'],['review','--archive','own','--firmware','2.00']):
                with self.assertRaises(SystemExit) as exc:c.main(args)
                self.assertEqual(exc.exception.code,2)
        output=io.StringIO()
        with patch.object(c.capturemsc,'verify_sources',side_effect=OSError(str(self.root))),contextlib.redirect_stdout(output):
            code=c.main(['review','--archive','own'])
        self.assertEqual(code,1);self.assertNotIn(str(self.root),output.getvalue())

    def test_candidate_marker_true_duplicate_late_or_removed_is_inconsistent(self):
        for variant in ('true','duplicate','late','removed'):
            with self.subTest(variant=variant):
                _,_,directory=self.make(name=variant)
                def edit(record):
                    if record['event']=='NATIVE_BINDING_CANDIDATE_MODELED':
                        if variant=='true':record['details']['live_execution_enabled']=True
                        elif variant in ('late','removed'):record.update(event='READY_FOR_REPORT',details={})
                    elif record['event']==('OWNED_HOST_BOUND_MODELED' if variant=='duplicate' else 'RAW_AUTHENTICATION_MODELED') and variant in ('duplicate','late'):
                        record.update(event='NATIVE_BINDING_CANDIDATE_MODELED',details={'binding':'native-shaped-fake-ops','live_execution_enabled':False})
                self.fixture.rechain(directory,edit)
                self.assertEqual(i.inspect_directory(directory)['classification'],'EVIDENCE_INCONSISTENT')

    def test_marker_cannot_allow_old_fake_arrival_sequence_or_other_report_profile(self):
        preflight=o._Run.preflight
        def marked(run,resources):
            preflight(run,resources)
            run.event('NATIVE_BINDING_CANDIDATE_MODELED',binding='native-shaped-fake-ops',live_execution_enabled=False)
        with patch.object(o._Run,'preflight',marked):_,_,directory=self.fixture.make()
        inspected=i.inspect_directory(directory)
        self.assertEqual(inspected['classification'],'EVIDENCE_INCONSISTENT')
        self.assertIn('NATIVE_CANDIDATE_WITH_FAKE_ARRIVAL_HOOK',inspected['issues'])
        _,_,directory=self.make(name='profile');path=directory/o.REPORT;value=json.loads(path.read_bytes())
        value.update(schema='a7c2-synthetic-authenticated-capture/1',phase='SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')
        value['accepted_total_bytes']-=value['accepted_identity_bytes']
        for key in i.OWNED_COUNTERS|{'host_binding_modeled','host_blocked','cleanup_error_type'}:value.pop(key)
        path.unlink();other=directory/'pipeline-report.private.json';other.write_bytes(capturestore.encoded(value));other.chmod(0o600)
        inspected=i.inspect_directory(directory)
        self.assertEqual(inspected['classification'],'EVIDENCE_INCONSISTENT')
        self.assertIn('OWNED_EVIDENCE_WITHOUT_OWNED_REPORT',inspected['issues'])

    def test_source_only_import_under_no_site_loads_no_sdk(self):
        script="import sys; from lutphoto import capturecandidate; assert not any(n=='usb' or n.startswith('usb.') or n in ('libusb_package','macfl23.session','transport') for n in sys.modules); print('PASS')"
        result=subprocess.run([sys.executable,'-S','-B','-c',script],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[2],timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,'PASS\n')


if __name__=='__main__':unittest.main()
