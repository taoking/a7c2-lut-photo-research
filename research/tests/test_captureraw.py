"""Exact fake raw handles, real host storage and no USB/device operations."""
from array import array
import hashlib
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import captureraw as r, captureinspect as i, capturestore
from research.tests import test_capturepipeline as fixtures, test_captureauth as auth


class RawTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.PipelineTests(methodName='runTest');fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture,self.root,self.files=fixture,fixture.root,fixture.files

    def make(self,name='raw',*,files=None,resources=False,normal_options=None,service_options=None,**options):
        peer=r.p.s.SyntheticPeer(self.files if files is None else files,**options)
        normal=r.SyntheticDevice(0x0e8a,auth.tape(0x0e8a),peer,**(normal_options or {}))
        service=r.SyntheticDevice(0x0336,auth.tape(0x0336),peer,**(service_options or {}))
        root=self.root/name
        result=r.rehearse('own',root,peer,normal,service,resources=resources)
        return result,peer,normal,service,root

    def assert_closed(self,normal,service):
        for device in (normal,service):
            self.assertTrue(device.closed);self.assertEqual(device.counts.get('close'),1)
            self.assertEqual(device.trace[-1][0],'close')

    def assert_no_commands_after_failure(self,service,kind,ordinal):
        count=0
        for index,row in enumerate(service.trace):
            if row[0]==kind: count+=1
            if row[0]==kind and count==ordinal:
                self.assertEqual([v[0] for v in service.trace[index+1:]],['close']);return
        self.fail('Fault transfer was not reached')

    def test_full_auth_material_and_stop_share_one_service_raw_handle(self):
        result,peer,normal,service,root=self.make()
        self.assertEqual(result['phase'],'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')
        self.assertEqual(result['accepted_auth_bytes'],14448);self.assertEqual(result['auth_raw_calls'],31)
        self.assertEqual(result['accepted_total_bytes'],result['accepted_payload_bytes']+14448)
        self.assertEqual(service.counts['write'],7+result['requests'])
        self.assertEqual(service.counts['control'],2);self.assertEqual(normal.counts['control'],1)
        self.assertEqual(service.written[:7],list(service.auth.expected))
        self.assertEqual(service.auth.written,list(service.auth.expected))
        self.assertTrue(all(row[1]==0x04 for row in service.trace if row[0]=='write'))
        self.assertTrue(all(row[1]==0x83 for row in service.trace if row[0]=='read'))
        self.assertFalse(any(n.startswith('auth-') or n=='service-stop' for n in peer.trace))
        self.assert_closed(normal,service)
        self.assertEqual(i.inspect_directory(root)['classification'],'CONSISTENT_SIMULATION_COMPLETE')
        for flag in i.FALSE_COMMON|i.FALSE_PROFILE['pipeline']:self.assertIs(result[flag],False)

    def test_full_resource_extension_uses_same_raw_handle_and_preserves_materials(self):
        raw=r.p.s.c.synthetic_resource(False)
        files=self.files|{'resources/'+n:raw for n in r.p.s.c.RESOURCE_FILES}
        result,_,normal,service,root=self.make(files=files,resources=True)
        self.assertEqual(result['phase'],'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')
        self.assertEqual(len(result['files']),74);self.assert_closed(normal,service)
        self.assertEqual(service.counts['write'],7+result['requests'])
        self.assertEqual(i.inspect_directory(root)['classification'],'CONSISTENT_SIMULATION_COMPLETE')

    def test_binding_and_close_receipts_have_fixed_order(self):
        *_,root=self.make();rows=self.fixture.records(root)
        self.assertEqual(sum(row['event']=='RAW_HANDLES_BOUND_MODELED' for row in rows),1)
        acks=[];receipts={}
        for row in rows:
            if row['event']=='ACK':acks.append(row['details']['operation'])
            if row['event']=='RAW_HANDLE_CLOSED_MODELED':receipts[row['details']['role']]=len(acks)
        self.assertEqual(receipts,{'normal-initial':3,'service':len(acks)-1})

    def test_descriptor_numbers_are_bound_without_guessing_first_endpoint(self):
        desc=(0x054c,0x0336,0,0,0xff,1,2,((0x07,2),(0x8a,2)))
        result,_,_,service,_=self.make(service_options={'descriptor':desc})
        self.assertEqual(result['phase'],'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')
        self.assertTrue(all(row[1]==7 for row in service.trace if row[0]=='write'))
        self.assertTrue(all(row[1]==0x8a for row in service.trace if row[0]=='read'))

    def test_invalid_vendor_interface_endpoint_descriptors_fail_before_adoption(self):
        peer=r.p.s.SyntheticPeer(self.files)
        base=(0x054c,0x0336,0,0,0xff,0,0,((0x83,2),(0x04,2)))
        cases=[(0x054d,*base[1:]),base[:2]+(1,)+base[3:],base[:3]+(1,)+base[4:],
               base[:4]+(8,6,0x50,base[7]),base[:7]+(((0x81,2),(0x82,2)),),
               base[:7]+(((0x81,3),(0x02,2)),),base[:7]+(((0x80,2),(0x02,2)),),
               base[:7]+(((0x91,2),(0x02,2)),),base[:7]+(((0x81,2),(0x02,2),(0x03,2)),)]
        for index,descriptor in enumerate(cases):
            normal=r.SyntheticDevice(0x0e8a,auth.tape(0x0e8a),peer)
            service=r.SyntheticDevice(0x0336,auth.tape(0x0336),peer,descriptor=descriptor)
            with self.assertRaises(ValueError):r.rehearse('own',self.root/str(index),peer,normal,service)
            self.assertEqual(normal.trace,[]);self.assertEqual(service.trace,[]);self.assertEqual(peer.trace,[])

    def test_raw_none_short_boolean_write_never_retries_or_reads(self):
        for index,value in enumerate((None,True,1)):
            result,_,normal,service,root=self.make(str(index),service_options={'faults':{('write',8):value}})
            self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['simulated_outcome_unknown'])
            self.assert_no_commands_after_failure(service,'write',8);self.assert_closed(normal,service)
            self.assertEqual(i.inspect_directory(root)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_raw_control_none_and_exception_do_not_reauthenticate_or_read(self):
        for index,value in enumerate((None,TimeoutError('own'),KeyboardInterrupt())):
            result,peer,normal,service,_=self.make(str(index),normal_options={'faults':{('control',1):value}})
            self.assertTrue(result['simulated_outcome_unknown'])
            self.assertEqual([row[0] for row in normal.trace],['control','close'])
            self.assertEqual([row[0] for row in service.trace],['close'])
            self.assertNotIn('service-observation',peer.trace)

    def test_bounded_array_and_bytes_read_results_are_both_supported(self):
        for index,arrays in enumerate((True,False)):
            result,*_=self.make(str(index),normal_options={'arrays':arrays},service_options={'arrays':arrays})
            self.assertEqual(result['phase'],'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')

    def test_bad_byte_array_type_none_mutable_or_oversize_read_stops(self):
        for index,value in enumerate((None,bytearray(12),array('I',[0]*3),array('B',[0]*13),b'')):
            result,_,_,service,_=self.make(str(index),service_options={'faults':{('read',8):value}})
            self.assertTrue(result['simulated_outcome_unknown'])
            self.assert_no_commands_after_failure(service,'read',8)

    def test_short_auth_packet_and_material_header_do_not_trigger_extra_reads(self):
        for index,at in enumerate((1,8)):
            result,_,_,service,_=self.make(str(index),service_options={'faults':{('read',at):array('B',[0]*11)}})
            self.assertTrue(result['simulated_outcome_unknown']);self.assert_no_commands_after_failure(service,'read',at)

    def test_material_timeout_or_interrupt_never_sends_stop(self):
        for index,error in enumerate((TimeoutError('own'),KeyboardInterrupt())):
            result,_,_,service,root=self.make(str(index),service_options={'faults':{('read',8):error}})
            self.assertTrue(result['simulated_outcome_unknown']);self.assertEqual(service.counts['control'],1)
            self.assert_no_commands_after_failure(service,'read',8)
            self.assertEqual(i.inspect_directory(root)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_complete_content_rejection_has_one_stop_and_no_later_material(self):
        result,peer,normal,service,root=self.make(files=self.files|{'appFw.so':bytes(len(self.files['appFw.so']))})
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertFalse(result['simulated_outcome_unknown'])
        self.assertTrue(result['simulated_service_stop_ack']);self.assertEqual(service.counts['control'],2)
        self.assertNotIn('wire:read:cpapp-b.bin',peer.trace);self.assertNotIn('wire:ram',peer.trace)
        self.assert_closed(normal,service);self.assertEqual(i.inspect_directory(root)['classification'],'NEEDS_REVIEW_INCOMPLETE')

    def test_half_frame_keeps_partial_file_and_no_followup_command(self):
        result,peer,normal,service,root=self.make(fault='partial:read:appFw.so')
        self.assertTrue(result['simulated_outcome_unknown']);self.assertEqual(service.counts['control'],1)
        self.assertTrue((root/'source/appFw.so').exists());self.assertNotIn('wire:read:cpapp-b.bin',peer.trace)
        self.assert_closed(normal,service)

    def test_final_stop_unknown_has_no_normal_query_and_only_local_close(self):
        result,peer,normal,service,root=self.make(service_options={'faults':{('control',2):TimeoutError('own')}})
        self.assertTrue(result['simulated_outcome_unknown']);self.assertFalse(result['simulated_service_stop_ack'])
        self.assertNotIn('normal-after',peer.trace);self.assert_no_commands_after_failure(service,'control',2)
        self.assert_closed(normal,service);self.assertEqual(i.inspect_directory(root)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_owner_invalidates_borrowed_views_before_local_close(self):
        seen=[];real=r._Run.__init__;close=r.SyntheticDevice.close
        def observe(run,*args):real(run,*args);seen.append(run)
        def closing(device):
            run=seen[0];port=next(port for port in run.ports if port._device is device)
            self.assertTrue(port.closed)
            with self.assertRaises(RuntimeError):port._ready()
            return close(device)
        with patch.object(r._Run,'__init__',observe),patch.object(r.SyntheticDevice,'close',closing):result,*_=self.make()
        self.assertEqual(result['phase'],'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')
        for port in seen[0].ports:
            before=list(port._device.trace);port.close();self.assertEqual(before,port._device.trace)

    def test_normal_close_failure_prevents_service_observation_or_auth(self):
        result,peer,normal,service,root=self.make(normal_options={'faults':{('close',1):OSError('own')}})
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['pipeline_blocked'])
        self.assertNotIn('service-observation',peer.trace);self.assertEqual(service.counts.get('control',0),0)
        self.assert_closed(normal,service);self.assertNotEqual(i.inspect_directory(root)['classification'],'CONSISTENT_SIMULATION_COMPLETE')

    def test_service_close_unconfirmed_keeps_known_stop_but_blocks_normal_query(self):
        for index,value in enumerate((None,False,OSError('own'))):
            result,peer,normal,service,_=self.make(str(index),service_options={'faults':{('close',1):value}})
            self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['pipeline_blocked'])
            self.assertTrue(result['simulated_service_stop_ack']);self.assertNotIn('normal-after',peer.trace)
            self.assert_closed(normal,service)

    def test_both_close_failures_are_attempted_once_without_masking_primary_fault(self):
        result,_,normal,service,_=self.make(normal_options={'faults':{('control',1):TimeoutError('primary'),('close',1):OSError('close')}},
            service_options={'faults':{('close',1):OSError('close')}})
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assert_closed(normal,service)
        self.assertEqual(result['reason_type'],'TimeoutError')

    def test_no_destructor_sends_io_or_closes_a_borrowed_view(self):
        self.assertNotIn('__del__',r._Port.__dict__);self.assertNotIn('__del__',r._AuthView.__dict__)
        self.assertNotIn('close',r._AuthView.__dict__)
        self.assertFalse(any(n in r._Port.__dict__ for n in ('reset','clearHalt','temp','invoke','write','read')))

    def test_total_deadline_is_passed_explicitly_to_raw_read_write_and_control(self):
        real=r._Run.event
        def shorten(run,event,**details):
            value=real(run,event,**details)
            if event=='RAW_AUTHENTICATION_MODELED':run.channel.budget.clock=lambda:1199.0;run.channel.budget.deadline=1200.0
            return value
        with patch.object(r._Run,'event',shorten):result,_,_,service,_=self.make()
        self.assertEqual(result['phase'],'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')
        material=service.trace[15:-1]
        self.assertTrue(material);self.assertTrue(all(v[2]==1000 for v in material))
        self.assertTrue(all(1<=v[2]<=5000 for v in service.trace if v[0]!='close'))

    def test_deadline_expired_before_raw_write_sends_no_material_request(self):
        real=r._Port._io
        def expire(port,kind,*args,**kwargs):
            if port.authenticated and kind=='write':
                port.budget.deadline=port.budget.clock()
            return real(port,kind,*args,**kwargs)
        with patch.object(r._Port,'_io',expire):result,_,_,service,_=self.make()
        self.assertTrue(result['simulated_outcome_unknown']);self.assertEqual(service.counts['write'],7)
        self.assertEqual(service.counts['control'],1)

    def test_deadline_expires_after_send_returns_without_read_or_stop(self):
        runs=[];init=r._Run.__init__;write=r.SyntheticDevice.write
        def observe(run,*args):init(run,*args);runs.append(run)
        def expire(device,*args,**kwargs):
            result=write(device,*args,**kwargs)
            if device.pid==0x0336 and device.counts['write']==8:
                runs[0].channel.budget.deadline=runs[0].channel.budget.clock()
            return result
        with patch.object(r._Run,'__init__',observe),patch.object(r.SyntheticDevice,'write',expire):result,_,_,service,_=self.make()
        self.assertTrue(result['simulated_outcome_unknown']);self.assert_no_commands_after_failure(service,'write',8)

    def test_full_length_rejected_auth_status_never_grants_material_or_stop(self):
        result,peer,_,service,_=self.make(service_options={'faults':{('read',7):array('B',auth.response(6,b'\0'))}})
        self.assertTrue(result['simulated_outcome_unknown']);self.assertEqual(service.counts['control'],1)
        self.assertNotIn('wire:hasp',peer.trace);self.assert_no_commands_after_failure(service,'read',7)

    def test_report_publication_occurs_after_both_owned_handles_closed(self):
        runs=[];init=r._Run.__init__;put=capturestore.Store.put
        def observe(run,*args):init(run,*args);runs.append(run)
        def publish(store,name,raw,**kwargs):
            if name==r.p.REPORT:
                run=runs[0]
                self.assertTrue(all(port.closed and port.close_ok for port in run.ports))
                self.assertNotIn('global-lock-release',run.peer.trace);self.assertIsNotNone(store.lock)
            return put(store,name,raw,**kwargs)
        with patch.object(r._Run,'__init__',observe),patch.object(capturestore.Store,'put',publish):result,*_=self.make()
        self.assertEqual(result['phase'],'SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE')

    def test_readonly_inspection_preserves_raw_lifecycle_receipts_and_materials(self):
        *_,root=self.make()
        def state():
            return {str(path.relative_to(root)):(path.stat().st_ino,path.stat().st_mtime_ns,path.stat().st_ctime_ns,
                    hashlib.sha256(path.read_bytes()).hexdigest()) for path in root.rglob('*') if path.is_file()}
        before=state();self.assertEqual(i.inspect_directory(root)['classification'],'CONSISTENT_SIMULATION_COMPLETE')
        self.assertEqual(before,state())

    def test_descriptor_change_during_raw_read_detected_before_ack_or_next_io(self):
        real=r.SyntheticDevice.read
        def change(device,*args,**kwargs):
            value=real(device,*args,**kwargs)
            if device.pid==0x0336 and device.counts['read']==8:
                device.descriptor=device.descriptor[:7]+(((0x85,2),(0x06,2)),)
            return value
        with patch.object(r.SyntheticDevice,'read',change):result,_,_,service,_=self.make()
        self.assertTrue(result['simulated_outcome_unknown']);self.assert_no_commands_after_failure(service,'read',8)

    def test_intent_or_ack_failure_stops_raw_io_and_still_releases_handles(self):
        for index,kind in enumerate(('INTENT','ACK')):
            real=capturestore.Store.event
            def fail(store,event,**details):
                if event==kind and details.get('operation')=='hasp':raise OSError('own')
                return real(store,event,**details)
            with patch.object(capturestore.Store,'event',fail):result,_,normal,service,_=self.make(str(index))
            self.assertTrue(result['pipeline_blocked']);self.assertEqual(service.counts['control'],1)
            self.assertEqual(service.counts['write'],7+(kind=='ACK'));self.assert_closed(normal,service)

    def test_close_receipt_failure_does_not_retry_close_or_start_service(self):
        real=capturestore.Store.event
        def fail(store,event,**details):
            if event=='RAW_HANDLE_CLOSED_MODELED':raise OSError('own')
            return real(store,event,**details)
        with patch.object(capturestore.Store,'event',fail):result,peer,normal,service,_=self.make()
        self.assertTrue(result['pipeline_blocked']);self.assertNotIn('service-observation',peer.trace)
        self.assert_closed(normal,service)

    def test_space_failure_releases_adopted_handles_without_device_commands(self):
        with patch.object(capturestore.Store,'require_space',side_effect=OSError('own')):
            result,_,normal,service,_=self.make()
        self.assertEqual(result['phase'],'NEEDS_REVIEW')
        self.assertEqual([v[0] for v in normal.trace],['close']);self.assertEqual([v[0] for v in service.trace],['close'])

    def test_existing_directory_refuses_before_adopting_or_closing_inputs(self):
        *_,root=self.make();peer=r.p.s.SyntheticPeer(self.files)
        normal=r.SyntheticDevice(0x0e8a,auth.tape(0x0e8a),peer);service=r.SyntheticDevice(0x0336,auth.tape(0x0336),peer)
        with self.assertRaises(FileExistsError):r.rehearse('own',root,peer,normal,service)
        self.assertEqual(normal.trace,[]);self.assertEqual(service.trace,[])

    def test_unknown_or_closed_raw_handle_cannot_be_reused(self):
        result,peer,normal,service,root=self.make(service_options={'faults':{('read',8):TimeoutError('own')}})
        before=(list(normal.trace),list(service.trace))
        with self.assertRaises(TypeError):r.rehearse('own',root,peer,normal,service)
        self.assertEqual(before,(normal.trace,service.trace))

    def test_wrong_service_peer_external_handle_and_ver200_rejected_before_io(self):
        for index,options in enumerate(({'version':'2.00'},{'battery':49})):
            peer=r.p.s.SyntheticPeer(self.files,**options)
            normal=r.SyntheticDevice(0x0e8a,auth.tape(0x0e8a),peer);service=r.SyntheticDevice(0x0336,auth.tape(0x0336),peer)
            with self.assertRaises(ValueError):r.rehearse('own',self.root/str(index),peer,normal,service)
            self.assertEqual(normal.trace,[]);self.assertEqual(service.trace,[])
        peer=r.p.s.SyntheticPeer(self.files)
        with self.assertRaises(TypeError):r.rehearse('own',self.root/'external',peer,object(),object())
        other=r.p.s.SyntheticPeer(self.files)
        normal=r.SyntheticDevice(0x0e8a,auth.tape(0x0e8a),peer);service=r.SyntheticDevice(0x0336,auth.tape(0x0336),other)
        with self.assertRaises(TypeError):r.rehearse('own',self.root/'other-peer',peer,normal,service)
        self.assertEqual(normal.trace,[]);self.assertEqual(service.trace,[])

    def test_legacy_auth_entry_still_rejects_new_internal_view_or_real_backend(self):
        # New internal views do not widen the pre-existing public auth API.
        seen=[];real=r._Run.__init__
        def observe(run,*args):real(run,*args);seen.append(run)
        with patch.object(r._Run,'__init__',observe):self.make()
        store=capturestore.Store(self.root/'unused');self.addCleanup(store.close)
        flow=r.a.OfflineAuthFlow('own',store,auth.NORMAL)
        with self.assertRaises(TypeError):flow.normal_auth(seen[0].drivers[0])
        self.assertFalse(hasattr(r,'get_device'));self.assertFalse(hasattr(r,'main'))

    def test_readonly_checker_rejects_rechained_missing_duplicate_or_reordered_receipts(self):
        for index in range(3):
            *_,root=self.make(str(index))
            def edit(row):
                if row['event']=='RAW_HANDLE_CLOSED_MODELED':
                    if index==2:row['details']['role']='normal-initial' if row['details']['role']=='service' else 'service'
                    elif row['details']['role']=='service':
                        if index==0:row['event']='NORMAL_SAME_SOURCE_MATCH_MODELED';row['details']={}
                        else:row['details']['role']='normal-initial'
            self.fixture.rechain(root,edit)
            self.assertEqual(i.inspect_directory(root)['classification'],'EVIDENCE_INCONSISTENT')

    def test_raw_reports_and_logs_do_not_expose_handle_endpoint_identity_or_packets(self):
        result,_,normal,service,root=self.make()
        text=json.dumps(result)+''.join(v.read_text() for v in (root/'events').glob('*.json'))+json.dumps(i.inspect_directory(root))
        self.assertNotIn(str(root),text);self.assertNotIn('11'*32,text);self.assertNotIn('descriptor',text)
        for raw in normal.written+service.written:
            self.assertNotIn(raw.hex(),text)
        for key in (*auth.KEYS.sha1,*auth.KEYS.sha256):self.assertNotIn(key.hex(),text)

    def test_no_usb_or_crypto_import_and_real_readonly_cli_supports_raw_evidence(self):
        code=('import sys;from lutphoto import captureraw;'
              'assert not any(n=="usb" or n.startswith("usb.") or n in ("Crypto","Cryptodome","transport","core","numpy","macfl23.session") for n in sys.modules)')
        checked=subprocess.run([sys.executable,'-S','-B','-c',code],capture_output=True,cwd=r.a.w.ROOT)
        self.assertEqual(checked.returncode,0,checked.stderr)
        *_,root=self.make()
        checked=subprocess.run([sys.executable,'-S','-B','-m','lutphoto.captureinspect','inspect','--directory',str(root)],capture_output=True,text=True)
        self.assertEqual(checked.returncode,0,checked.stderr);self.assertNotIn(str(root),checked.stdout)


if __name__=='__main__':unittest.main()
