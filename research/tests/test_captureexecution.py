"""Actual assembly on the existing fake SDK/OS, never a live device or lock."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import captureexecution as x, captureevidence as e, captureowned as o, captureinspect as old
from lutphoto import capturesignals as signals
from lutphoto.capturecontrol import Cancellation
from lutphoto.capturestore import Store, Sink, encoded
from research.tests import test_captureowned as fixtures, test_capturesignals as signal_fixtures
from research.tests.native_sdk_fixture import World, Device


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.OwnedTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.fixture,self.root,self.files=f,f.root,f.files

    def make(self,name='execution',*,resources=False,cancel=None,native_faults=None,**options):
        world=World(self.fixture.system(**options),faults=native_faults)
        cancel,policy,channel=o._prepare('own',world.system,resources,cancel)
        world.system.service_device._requests=channel.requests
        world.host=o.m._Host(world.ops,None,firmware='2.01',battery_percent=75,budget=channel.budget,cancel=cancel,wait=True)
        directory=self.root/name
        with world.bound():
            result=x._execute('own',directory,world.host,channel,policy,resources=resources,
                              firmware='2.01',battery_percent=75,execution_kind='self-made-sdk')
        receipt=self.root/(name+'.receipt.json');receipt.write_bytes(encoded(result));receipt.chmod(0o600)
        return result,world,directory,receipt

    def test_core_checkpoint_and_terminal_are_separate_and_strictly_bound(self):
        before={n:signal.getsignal(n) for n in (signal.SIGINT,signal.SIGTERM)}
        result,w,d,r=self.make()
        self.assertEqual(result['phase'],'EXERCISE_COMPLETE');self.assertEqual(e.exit_code(result),0)
        self.assertEqual(set(result['cleanup'].values()),{'CONFIRMED'});self.assertEqual(result['errors'],[])
        self.assertEqual(before,{n:signal.getsignal(n) for n in before});self.assertFalse(w.system.acquired)
        self.assertEqual(w.system.counts['dispose'],3)
        checkpoint=json.loads((d/e.CHECKPOINT).read_bytes())
        self.assertTrue(checkpoint['checkpoint_only']);self.assertEqual(checkpoint['phase'],'MATERIALS_OBSERVED')
        self.assertEqual(checkpoint['observations']['initial'],checkpoint['observations']['returned'])
        self.assertEqual(checkpoint['observations']['initial']['serial_source'],'sony-get-camera-info')
        self.assertEqual(checkpoint['flow']['identity_raw_calls'],28)
        self.assertEqual(checkpoint['flow']['authentication_bytes'],14448)
        for record in self.fixture.records(d):
            self.assertIn(record['event'],e.NATIVE_EVENTS)
            self.assertNotIn('MODELED',record['event']);self.assertNotIn('SYNTHETIC',record['event'])
        missing=e.inspect_directory(d);self.assertEqual(missing['material_evidence'],'CONSISTENT')
        self.assertEqual(missing['classification'],'NEEDS_REVIEW_TERMINAL_MISSING')
        checked=e.inspect_directory(d,receipt=r);self.assertEqual(checked['classification'],'CONSISTENT_EXERCISE_RECORDS')
        self.assertEqual(checked['terminal_evidence'],'MATCHED_COMPLETE');self.assertTrue(all(v is False for v in checked['unproven'].values()))
        self.assertNotEqual(old.inspect_directory(d)['classification'],'CONSISTENT_SIMULATION_COMPLETE')

    def test_resource_extension_uses_existing_same_service_and_74_files(self):
        files=self.files|{'resources/'+n:o.s.c.synthetic_resource(False) for n in o.s.c.RESOURCE_FILES}
        result,w,d,r=self.make(resources=True,files=files)
        self.assertEqual(e.exit_code(result),0);self.assertEqual(len(json.loads((d/e.CHECKPOINT).read_bytes())['files']),74)
        self.assertEqual(e.inspect_directory(d,receipt=r)['classification'],'CONSISTENT_EXERCISE_RECORDS')
        self.assertEqual(w.system.service_device.counts['control'],2)

    def test_known_content_rejection_and_unknown_response_have_distinct_evidence(self):
        for name,options,want in [('reject',{'files':self.files|{'appFw.so':bytes(len(self.files['appFw.so']))}},'INCOMPLETE'),
                ('unknown',{'service_options':{'faults':{('write',8):None}}},'UNKNOWN')]:
            result,w,d,r=self.make(name,**options)
            self.assertEqual(e.exit_code(result),1);self.assertEqual(result['phase'],'NEEDS_REVIEW')
            checked=e.inspect_directory(d,receipt=r);self.assertEqual(checked['material_evidence'],want)
            self.assertEqual(checked['terminal_evidence'],'MATCHED_FAILURE')
            self.assertNotIn('wire:read:cpapp-b.bin',w.system.peer.trace)
            self.assertEqual(w.system.service_device.counts['control'],2 if name=='reject' else 1)

    def test_complete_checkpoint_does_not_hide_store_and_lease_failures(self):
        close=Store.close
        def fail(store):close(store);raise OSError('Own job cleanup')
        with patch.object(Store,'close',fail):
            result,w,d,r=self.make(system_options={'faults':{('global-release',1):TimeoutError('Own lease cleanup')}})
        self.assertTrue(result['material_observations_complete']);self.assertEqual(e.exit_code(result),1)
        self.assertEqual(result['errors'][0],{'stage':'job-store','reason_type':'OSError'})
        self.assertIn({'stage':'global-lease','reason_type':'TimeoutError'},result['errors'])
        checked=e.inspect_directory(d,receipt=r)
        self.assertEqual(checked['material_evidence'],'CONSISTENT');self.assertEqual(checked['classification'],'NEEDS_REVIEW_TERMINAL_FAILURE')
        self.assertFalse(w.system.acquired)

    def test_body_error_remains_first_when_both_cleanup_scopes_fail(self):
        close=Store.close
        def fail(store):close(store);raise OSError('Own job cleanup')
        with patch.object(Store,'close',fail):
            result,_,d,r=self.make(files=self.files|{'appFw.so':bytes(len(self.files['appFw.so']))},
                system_options={'faults':{('global-release',1):TimeoutError('Own lease cleanup')}})
        self.assertEqual(result['errors'][0],{'stage':'body','reason_type':'ValueError'})
        self.assertIn({'stage':'job-store','reason_type':'OSError'},result['errors'])
        self.assertIn({'stage':'global-lease','reason_type':'TimeoutError'},result['errors'])
        self.assertEqual(e.inspect_directory(d,receipt=r)['classification'],'NEEDS_REVIEW_INCOMPLETE')

    def test_cancel_after_checkpoint_is_not_success_and_never_reopens_job(self):
        token=Cancellation();put=Store.put
        def cancel(store,name,*args,**kw):
            value=put(store,name,*args,**kw)
            if name==e.CHECKPOINT:token.cancel()
            return value
        with patch.object(Store,'put',cancel):result,w,d,r=self.make(cancel=token)
        self.assertTrue(result['material_observations_complete']);self.assertTrue(result['cancel_requested'])
        self.assertEqual(result['errors'],[{'stage':'final-cancellation','reason_type':'OperationCancelled'}])
        self.assertEqual(e.inspect_directory(d,receipt=r)['classification'],'NEEDS_REVIEW_TERMINAL_FAILURE')
        self.assertEqual(w.system.counts['dispose'],3)

    def test_cancel_after_owned_open_preserves_checkpoint_without_new_protocol(self):
        token=Cancellation();original=Device.get_active_configuration
        def cancel(device):value=original(device);token.cancel();return value
        with patch.object(Device,'get_active_configuration',cancel):result,w,d,r=self.make(cancel=token)
        self.assertEqual(e.exit_code(result),1);self.assertEqual(result['errors'][0]['reason_type'],'OperationCancelled')
        self.assertIsNotNone(result['checkpoint']);self.assertEqual(w.system.counts.get('control',0),0)
        self.assertEqual(w.system.counts['dispose'],1);self.assertEqual(e.inspect_directory(d,receipt=r)['material_evidence'],'UNKNOWN')

    def test_signal_restore_failure_after_materials_changes_terminal_only(self):
        api=signal_fixtures.FakeSignals();api.faults[3]=OSError('Own restore')
        with patch.object(signals,'signal',api):result,_,d,r=self.make()
        self.assertTrue(result['material_observations_complete']);self.assertEqual(result['cleanup']['signal_handlers'],'UNCONFIRMED')
        self.assertEqual([error['reason_type'] for error in result['errors'] if error['stage']=='signals'],['SignalScopeError','OSError'])
        self.assertEqual(e.inspect_directory(d,receipt=r)['classification'],'NEEDS_REVIEW_TERMINAL_FAILURE')

    def test_custom_signal_handler_refuses_before_lease_and_job(self):
        api=signal_fixtures.FakeSignals();api.handlers[api.SIGTERM]=object()
        with patch.object(signals,'signal',api):result,w,d,_=self.make()
        self.assertFalse(d.exists());self.assertFalse(result['attempted']['lease']);self.assertFalse(w.trace)
        self.assertEqual(e.exit_code(result),1)

    def test_storage_preflight_failure_keeps_consistent_failure_context_without_sdk_inventory(self):
        with patch.object(Store,'require_space',side_effect=OSError('Own free space')):result,w,d,r=self.make()
        self.assertIsNotNone(result['checkpoint']);self.assertEqual(result['errors'][0],{'stage':'body','reason_type':'OSError'})
        self.assertEqual(w.counts.get('enumerate',0),0);self.assertFalse(w.host.owners)
        checked=e.inspect_directory(d,receipt=r)
        self.assertEqual(checked['classification'],'NEEDS_REVIEW_INCOMPLETE');self.assertEqual(checked['terminal_evidence'],'MATCHED_FAILURE')

    def test_source_or_actual_version_preconditions_before_native_construction(self):
        with patch.object(o.m,'_NativeOps',side_effect=AssertionError('No native constructor')):
            for firmware,battery,resources in [('2.00',75,False),('2.01',49,False),('2.01',True,False),('2.01',75,1)]:
                with self.assertRaises(ValueError):x._capture('own',self.root/'no-job',firmware=firmware,battery_percent=battery,resources=resources)
            with patch.object(x.capturepreflight,'inspect',side_effect=ValueError('Own source')):
                with self.assertRaises(ValueError):x._capture('own',self.root/'no-job',firmware='2.01',battery_percent=75)
        self.assertFalse((self.root/'no-job').exists())

    def test_reserved_native_assembly_has_fixed_ops_and_no_external_backend(self):
        policy=o.programidentity._load_policy('own');ops=o.m._NativeOps()
        checked={'phase':'OFFLINE_PREFLIGHT_CHECKED','environment':{'administrator_context_present':True}}
        with patch.object(x.capturepreflight,'inspect',return_value=checked),patch.object(o.m._NativeOps,'__new__',return_value=ops),\
             patch.object(o.m._NativeOps,'__init__',return_value=None),patch.object(x,'_execute',return_value='own-terminal') as execute:
            self.assertEqual(x._capture('own',self.root/'reserved',firmware='2.01',battery_percent=75),'own-terminal')
        args=execute.call_args
        self.assertIs(args.args[2].ops,ops);self.assertEqual(args.kwargs['execution_kind'],'native')
        self.assertEqual(args.kwargs['battery_percent'],75);self.assertIs(args.args[2].budget,args.args[3].budget)
        self.assertFalse((self.root/'reserved').exists())

    def test_real_child_signals_during_configuration_and_material_keep_all_scopes(self):
        f=signal_fixtures.SignalProcessTests(methodName='runTest');f.root=self.root
        f.exercise('configuration',signal.SIGINT,execution=True)
        f.exercise('material',signal.SIGTERM,execution=True)

    def test_real_child_signals_during_stop_and_dispose_never_repeat_protocol(self):
        f=signal_fixtures.SignalProcessTests(methodName='runTest');f.root=self.root
        f.exercise('stop',signal.SIGTERM,execution=True)
        f.exercise('dispose',signal.SIGINT,execution=True)

    def test_native_public_entry_still_refuses_without_accessing_arguments(self):
        from lutphoto import capturecandidate
        class Poison:
            def __fspath__(self):raise AssertionError('No path access')
        with self.assertRaises(capturecandidate.NativeCandidateBlocked):capturecandidate.capture(Poison(),firmware='2.01',enabled=True)

    def test_terminal_cannot_be_rebound_or_upgraded_to_success(self):
        result,_,d,r=self.make()
        for variant in ('job','hash','cleanup','kind','claim','extra','boolean'):
            value=copy.deepcopy(result)
            if variant=='job':value['context']['job_id']='01'*16
            elif variant=='hash':value['checkpoint']['sha256']='00'*32
            elif variant=='cleanup':value['cleanup']['global_lease']='UNCONFIRMED'
            elif variant=='kind':value['phase']='CAPTURE_COMPLETE'
            elif variant=='claim':value['unproven']['restore_verified']=True
            elif variant=='extra':value['enabled']=True
            else:value['attempted']['device']=1
            r.write_bytes(encoded(value))
            self.assertEqual(e.inspect_directory(d,receipt=r)['classification'],'EVIDENCE_INCONSISTENT',variant)

    def test_terminal_contract_rejects_malformed_nested_values_and_nonfinite_numbers(self):
        result,_,_,_=self.make()
        for key in result:
            value=copy.deepcopy(result);value[key]=[{'untrusted':'own'}]
            self.assertFalse(e.valid_receipt(value),key);self.assertEqual(e.exit_code(value),1)
        value=copy.deepcopy(result);value['context']['battery_percent_declared']=float('inf')
        self.assertFalse(e.valid_receipt(value))

    def test_native_checkpoint_cannot_use_legacy_modeled_events(self):
        _,_,d,_=self.make();path=d/'events/00000000.json';value=json.loads(path.read_bytes())
        value.update(event='NATIVE_BINDING_CANDIDATE_MODELED',details={'binding':'native-shaped-fake-ops','live_execution_enabled':False})
        path.write_bytes(encoded(value));self.assertEqual(e.inspect_directory(d)['classification'],'EVIDENCE_INCONSISTENT')

    def test_rechained_program_guard_and_snapshot_markers_must_match_read_positions(self):
        import hashlib
        for variant in ('program-early','guard-late','snapshot-name'):
            _,_,d,_=self.make(variant);paths=sorted((d/'events').glob('*.json'));records=[json.loads(p.read_bytes()) for p in paths]
            if variant=='snapshot-name':
                record=next(r for r in records if r['event']=='SNAPSHOT_FORMAT_CHECKED')
                record['details']['file']='evidence/settings-saved-end.bin'
            else:
                event='PROGRAM_PAIR_MATCHED' if variant=='program-early' else 'GUARDS_ABSENT'
                record=next(r for r in records if r['event']==event);records.remove(record)
                target=next(n for n,r in enumerate(records) if r['event']=='HOST_FILE_VERIFIED' and r['details']['file']=='source/appFw.so')
                records.insert(target+1,record)
            head='0'*64
            for n,(p,record) in enumerate(zip(paths,records)):
                record.update(seq=n,previous_sha256=head);raw=encoded(record);p.write_bytes(raw);head=hashlib.sha256(raw).hexdigest()
            p=d/e.CHECKPOINT;checkpoint=json.loads(p.read_bytes());checkpoint['journal']['head_sha256']=head;p.write_bytes(encoded(checkpoint))
            self.assertEqual(e.inspect_directory(d)['classification'],'EVIDENCE_INCONSISTENT',variant)

    def test_material_and_source_observation_tampering_are_detected(self):
        _,_,d,r=self.make();p=d/e.CHECKPOINT;original=p.read_bytes();value=json.loads(original)
        value['observations']['returned']['serial_sha256']='00'*32;p.write_bytes(encoded(value))
        self.assertEqual(e.inspect_directory(d)['classification'],'EVIDENCE_INCONSISTENT')
        p.write_bytes(original);(d/'source/appFw.so').write_bytes(b'own-modified')
        self.assertEqual(e.inspect_directory(d,receipt=r)['classification'],'EVIDENCE_INCONSISTENT')

    def test_checker_cli_readonly_privacy_and_receipt_permissions(self):
        _,_,d,r=self.make();before={p:(p.stat().st_size,p.stat().st_mtime_ns,p.read_bytes()) for p in d.rglob('*') if p.is_file()}
        output=io.StringIO()
        with contextlib.redirect_stdout(output):code=e.main(['inspect','--directory',str(d),'--receipt',str(r)])
        self.assertEqual(code,0);self.assertNotIn(str(self.root),output.getvalue());self.assertNotIn('serial_sha256',output.getvalue())
        self.assertEqual(before,{p:(p.stat().st_size,p.stat().st_mtime_ns,p.read_bytes()) for p in before})
        r.chmod(0o644);self.assertEqual(e.inspect_directory(d,receipt=r)['classification'],'REFUSED')

    def test_checker_close_failure_is_bounded_and_not_reported_as_success(self):
        _,_,d,r=self.make();close=old._Reader.close
        def failed(reader):close(reader);raise OSError(str(self.root))
        with patch.object(old._Reader,'close',failed):result=e.inspect_directory(d,receipt=r)
        self.assertEqual(result['classification'],'REFUSED');self.assertEqual(result['issues'],['INSPECTION_RELEASE_UNCONFIRMED'])
        self.assertNotIn(str(self.root),json.dumps(result))

    def test_imports_have_no_sdk_signal_or_lock_side_effects_under_no_site(self):
        code="import sys,signal; old=signal.getsignal(signal.SIGINT); from lutphoto import captureexecution,captureevidence; assert signal.getsignal(signal.SIGINT) is old; assert not any(n=='usb' or n.startswith('usb.') or n=='libusb_package' for n in sys.modules); print('PASS')"
        result=subprocess.run([sys.executable,'-S','-B','-c',code],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[2],timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,'PASS\n')

    def test_storage_close_attempts_every_fd_once_and_retains_errors(self):
        store=Store(self.root/'close-all');expected=[*store.fds.values(),store.lock,store.parent];closed=[];close=os.close
        def failed(fd):
            closed.append(fd);close(fd)
            if len(closed) in (1,3):raise OSError('Own ambiguous close')
        with patch.object(os,'close',failed):
            with self.assertRaises(OSError):store.close()
            store.close()
        self.assertEqual(closed,expected);self.assertFalse(store.close_confirmed)
        self.assertEqual(store.close_error_types,('OSError','OSError'));self.assertEqual(store.fds,{})
        store=Store(self.root/'sink-close');sink=Sink(64,store=store,relative='source/appFw.so')
        fd=sink.fd;calls=[]
        def sink_failed(number):calls.append(number);close(number);raise OSError('Own ambiguous sink close')
        with patch.object(os,'close',sink_failed):
            with self.assertRaises(OSError):sink.close()
            sink.close()
        self.assertEqual(calls,[fd]);self.assertIsNone(sink.fd);self.assertTrue(sink.closed)
        store.close()


if __name__=='__main__':unittest.main()
