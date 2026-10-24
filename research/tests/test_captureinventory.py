"""Bounded host diagnostics on existing self-made SDK/OS; no USB imports."""
import copy
import json
import unittest
from unittest.mock import Mock, patch

from lutphoto import capturediagnostics as d, captureevidence as e, capturemac as m
from lutphoto.capturestore import Store, encoded
from research.tests import test_captureexecution as fixtures
from research.tests.native_sdk_fixture import Core, Device


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.ExecutionTests(methodName='runTest')
        self.case.setUp();self.addCleanup(self.case.doCleanups)

    def make(self,*args,**kwargs):return self.case.make(*args,**kwargs)

    def assert_initial_failure(self,result,world,directory,receipt,boundary):
        self.assertEqual(result['errors'][0]['stage'],'body')
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertEqual(e.exit_code(result),1)
        self.assertEqual(result['host_diagnostics'][0]['inventory_call'],1)
        self.assertEqual(result['host_diagnostics'][0]['failure']['boundary'],boundary)
        flow=json.loads((directory/e.CHECKPOINT).read_bytes())['flow']
        self.assertTrue(all(flow[k]==0 for k in e.COUNTS))
        self.assertEqual(flow['authentication_phase'],'NOT_STARTED')
        self.assertFalse(flow['transition_started']);self.assertEqual(result['identity_diagnostics'],[])
        self.assertFalse(world.host.owners)
        for name in ('command','configuration','claim','control','write','read'):
            self.assertEqual(world.counts.get(name,0),0,name)
        checked=e.inspect_directory(directory,receipt=receipt)
        self.assertEqual(checked['classification'],'NEEDS_REVIEW_UNKNOWN')
        self.assertEqual(checked['host_diagnostics'],result['host_diagnostics'])
        self.assertEqual(checked['terminal_evidence'],'MATCHED_FAILURE')

    def test_same_six_events_distinguish_sdk_find_and_invalid_cached_bus(self):
        first,w,a,r=self.make('find',native_faults={('find',1):ValueError('private inventory')})
        self.assert_initial_failure(first,w,a,r,'SDK_FIND_NORMAL')
        init=Device.__init__
        def bad(device,*args):init(device,*args);device.bus=-1
        with patch.object(Device,'__init__',bad):second,w,b,r=self.make('bus')
        self.assert_initial_failure(second,w,b,r,'KEY_VALIDATE')
        self.assertEqual(second['host_diagnostics'][0]['failure']['invalid_key_fields'],['BUS'])
        self.assertEqual(w.devices[0].dispose_attempts,1)
        for path in (a,b):
            records=self.case.fixture.records(path)
            self.assertEqual(len(records),6)
            self.assertEqual([v['event'] for v in records],['CAPTURE_CONTEXT','CAPTURE_LOCKS_HELD',
                'OWNER_FLOW_BOUND','INTENT','HOST_INTENT','NEEDS_REVIEW'])

    def test_second_find_failure_disposes_accumulated_object_once_and_keeps_first_error(self):
        result,w,path,r=self.make(native_faults={('find',2):ValueError('private first'),
                                                ('dispose',1):OSError('private secondary')})
        self.assert_initial_failure(result,w,path,r,'SDK_FIND_SERVICE')
        self.assertEqual(result['errors'][0]['reason_type'],'ValueError')
        self.assertEqual(len(w.devices),1);self.assertEqual(w.devices[0].dispose_attempts,1)
        self.assertEqual(w.counts['find'],2)

    def test_inventory_bound_preserves_seventeen_local_disposals_without_second_find(self):
        original=Core.find
        def many(core,**kwargs):
            for device in original(core,**kwargs):
                yield device
                for _ in range(16):
                    extra=Device(core.world,device.key);core.world.devices.append(extra);yield extra
        with patch.object(Core,'find',many):result,w,path,r=self.make()
        self.assert_initial_failure(result,w,path,r,'INVENTORY_LIMIT')
        self.assertEqual(w.counts['find'],1);self.assertEqual(len(w.devices),17)
        self.assertTrue(all(v.dispose_attempts==1 for v in w.devices))

    def test_each_key_field_is_read_once_and_only_invalid_names_are_recorded(self):
        init=Device.__init__;get=Device.__getattribute__;reads={}
        def bad(device,*args):
            init(device,*args);device.idProduct=True;device.bus=-1;device.port_numbers=();device.address=128
        def observed(device,name):
            if name in ('idVendor','idProduct','bus','port_numbers','address'):reads[name]=reads.get(name,0)+1
            return get(device,name)
        with patch.object(Device,'__init__',bad),patch.object(Device,'__getattribute__',observed):
            result,w,path,r=self.make()
        self.assert_initial_failure(result,w,path,r,'KEY_VALIDATE')
        self.assertEqual(reads,dict.fromkeys(('idVendor','idProduct','bus','port_numbers','address'),1))
        failure=result['host_diagnostics'][0]['failure']
        self.assertEqual(failure['invalid_key_fields'],['PID','BUS','PORTS','ADDRESS'])
        self.assertNotIn('ports',failure);self.assertNotIn('address',failure);self.assertNotIn('bus',failure)

    def test_sdk_property_read_and_vendor_check_failures_remain_distinct(self):
        get=Device.__getattribute__;init=Device.__init__
        def failure(device,name):
            if name=='bus':raise ValueError('private property')
            return get(device,name)
        with patch.object(Device,'__getattribute__',failure):result,w,path,r=self.make('read')
        self.assert_initial_failure(result,w,path,r,'KEY_BUS_READ')
        def vendor(device,*args):init(device,*args);device.idVendor=0
        with patch.object(Device,'__init__',vendor):result,w,path,r=self.make('vendor')
        self.assert_initial_failure(result,w,path,r,'KEY_VENDOR_CHECK')

    def test_runtime_and_enumeration_disposal_failures_do_not_open_or_repeat(self):
        ops=m._NativeOps()
        with patch.object(ops,'_runtime',side_effect=ValueError('private runtime')) as runtime:
            with self.assertRaises(ValueError):ops.inventory()
        self.assertEqual(ops._inventory_boundary,'NATIVE_RUNTIME');self.assertEqual(runtime.call_count,1)
        result,w,path,r=self.make('dispose',native_faults={('dispose',1):False})
        self.assert_initial_failure(result,w,path,r,'ENUMERATION_DISPOSE')
        self.assertEqual(w.devices[0].dispose_attempts,1)

    def test_ack_failure_before_or_after_record_is_bound_without_repeating_enumeration(self):
        event=Store.event
        for written in (False,True):
            def fail(store,name,**details):
                if name=='HOST_ACK' and details=={'operation':'INVENTORY'}:
                    if written:event(store,name,**details)
                    raise ValueError('private ACK')
                return event(store,name,**details)
            with patch.object(Store,'event',fail):result,w,path,r=self.make('ack'+str(written))
            self.assert_initial_failure(result,w,path,r,'HOST_ACK')
            self.assertEqual(w.counts['find'],2)
            self.assertEqual(w.devices[0].dispose_attempts,1)

    def test_host_precheck_intent_and_postcheck_failures_keep_original_error(self):
        for boundary in ('HOST_PRECHECK','HOST_INTENT','HOST_POSTCHECK'):
            ops=Mock();ops.inventory.return_value=();ops.clock.return_value=0
            host=m._Host(ops,Mock(),firmware='2.01',battery_percent=75);host.lock=1
            error=ValueError('private host')
            with patch.object(host,'check',side_effect=[error] if boundary=='HOST_PRECHECK' else
                              [None,error] if boundary=='HOST_POSTCHECK' else [None]):
                if boundary=='HOST_INTENT':host.event.side_effect=error
                with self.assertRaises(ValueError) as caught:host.step('INVENTORY',ops.inventory)
            self.assertIs(caught.exception,error)
            self.assertEqual(host.inventory_diagnostic['failure']['boundary'],boundary)
            self.assertEqual(ops.inventory.call_count,int(boundary=='HOST_POSTCHECK'))

    def test_intent_record_failure_can_be_bound_with_or_without_persisted_intent(self):
        event=Store.event
        for written in (False,True):
            def fail(store,name,**details):
                if name=='HOST_INTENT' and details=={'operation':'INVENTORY'}:
                    if written:event(store,name,**details)
                    raise ValueError('private intent')
                return event(store,name,**details)
            with patch.object(Store,'event',fail):result,w,path,r=self.make('intent'+str(written))
            self.assert_initial_failure(result,w,path,r,'HOST_INTENT')
            self.assertEqual(w.counts.get('find',0),0)

    def test_diagnostic_builder_or_cached_field_recording_failure_keeps_primary(self):
        with patch.object(d,'make_inventory_failure',side_effect=RuntimeError('private recorder')) as builder:
            result,w,path,r=self.make('builder',native_faults={('find',1):ValueError('private first')})
        self.assertEqual(builder.call_count,1)
        self.assertEqual(result['errors'][0],{'stage':'body','reason_type':'ValueError'})
        self.assertEqual(result['host_diagnostics'],[{'inventory_call':1,'failure':None,'record_error_type':'RuntimeError'}])
        self.assertEqual(e.inspect_directory(path,receipt=r)['classification'],'NEEDS_REVIEW_UNKNOWN')
        init=Device.__init__
        def bad(device,*args):init(device,*args);device.bus=-1
        with patch.object(Device,'__init__',bad),patch.object(d,'rejected_key_fields',side_effect=OSError('private fields')):
            result,_,path,r=self.make('fields')
        self.assertEqual(result['errors'][0]['reason_type'],'ValueError')
        self.assertEqual(result['host_diagnostics'][0]['record_error_type'],'OSError')
        self.assertEqual(e.inspect_directory(path,receipt=r)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_failure_is_recorded_once_and_blocked_step_does_not_repeat(self):
        result,w,_,_=self.make(native_faults={('find',1):ValueError('private first')})
        original=copy.deepcopy(w.host.inventory_diagnostic);calls=w.counts['find']
        with self.assertRaises(RuntimeError):w.host.step('INVENTORY',w.ops.inventory)
        self.assertEqual(w.host.inventory_diagnostic,original);self.assertEqual(w.counts['find'],calls)
        self.assertEqual(result['host_diagnostics'],[original])

    def test_transition_inventory_failure_is_bound_to_later_call_without_new_auth_or_retry(self):
        result,w,path,r=self.make(native_faults={('find',7):ValueError('private transition')})
        record=result['host_diagnostics'][0]
        self.assertEqual(record['inventory_call'],3)
        self.assertEqual(record['failure']['boundary'],'SDK_FIND_NORMAL')
        self.assertEqual(w.counts['find'],7);self.assertEqual(w.counts['control'],1)
        self.assertEqual(result['identity_diagnostics'],[])
        checked=e.inspect_directory(path,receipt=r)
        self.assertEqual(checked['classification'],'NEEDS_REVIEW_UNKNOWN')
        self.assertEqual(checked['host_diagnostics'],result['host_diagnostics'])

    def test_older_receipts_are_read_without_new_fields_or_rewriting(self):
        for version in (e.LEGACY_RECEIPT_SCHEMA,e.IDENTITY_RECEIPT_SCHEMA):
            for bad in (False,True):
                result,_,path,r=self.make(version.rsplit('/',1)[1]+str(bad),
                    native_faults={('find',1):ValueError('private')} if bad else None)
                result['schema']=version;del result['host_diagnostics']
                if version==e.LEGACY_RECEIPT_SCHEMA:del result['identity_diagnostics']
                r.write_bytes(encoded(result));before=r.read_bytes()
                checked=e.inspect_directory(path,receipt=r)
                self.assertEqual(checked['classification'],'NEEDS_REVIEW_UNKNOWN' if bad else 'CONSISTENT_EXERCISE_RECORDS')
                self.assertIsNone(checked['host_diagnostics']);self.assertEqual(r.read_bytes(),before)
                self.assertFalse(e.valid_receipt(result|{'host_diagnostics':[]}))

    def test_missing_or_forged_new_fields_are_rejected_and_hidden(self):
        result,_,path,r=self.make(native_faults={('find',1):ValueError('private')})
        missing=copy.deepcopy(result);del missing['host_diagnostics'];self.assertFalse(e.valid_receipt(missing))
        for number,boundary in ((2,'SDK_FIND_NORMAL'),(1,'HOST_PRECHECK')):
            forged=copy.deepcopy(result);record=forged['host_diagnostics'][0]
            record['inventory_call']=number;record['failure']['boundary']=boundary
            self.assertTrue(e.valid_receipt(forged));r.write_bytes(encoded(forged))
            checked=e.inspect_directory(path,receipt=r)
            self.assertEqual(checked['classification'],'EVIDENCE_INCONSISTENT')
            self.assertIn('HOST_DIAGNOSTIC_DIFFERS',checked['issues']);self.assertIsNone(checked['host_diagnostics'])
        complete,_,_,_=self.make('complete')
        complete['host_diagnostics']=result['host_diagnostics'];self.assertFalse(e.valid_receipt(complete))

    def test_missing_checkpoint_keeps_diagnostic_unbound_and_unknown(self):
        put=Store.put
        def fail(store,name,*args,**kwargs):
            if name==e.CHECKPOINT:raise OSError('private persistence')
            return put(store,name,*args,**kwargs)
        with patch.object(Store,'put',fail):result,_,path,r=self.make(native_faults={('find',1):ValueError('private first')})
        self.assertEqual(result['errors'][0]['reason_type'],'ValueError')
        checked=e.inspect_directory(path,receipt=r)
        self.assertEqual(checked['classification'],'NEEDS_REVIEW_UNKNOWN')
        self.assertIn('HOST_DIAGNOSTIC_UNBOUND',checked['issues']);self.assertIsNone(checked['host_diagnostics'])

    def test_exact_metadata_shapes_codes_and_privacy(self):
        class Error(OSError):
            backend_error_code=-7
            def __str__(self):raise AssertionError('No exception text')
            def __repr__(self):raise AssertionError('No exception repr')
        failure=d.make_inventory_failure('SDK_FIND_NORMAL',Error(60,'private path/identity'))
        self.assertEqual((failure['errno'],failure['backend_error_code']),(60,-7))
        self.assertNotIn('private',json.dumps(failure))
        record={'inventory_call':1,'failure':failure,'record_error_type':None}
        self.assertTrue(d.valid_inventory_records([record]))
        for key,value in (('inventory_call',True),('inventory_call',2049),('record_error_type','Error')):
            self.assertFalse(d.valid_inventory_records([record|{key:value}]))
        for key,value in (('boundary','private/path'),('invalid_key_fields',['BUS','BUS']),
                          ('invalid_key_fields',['ADDRESS','PID']),('invalid_key_fields',['BUS']),('errno',True)):
            self.assertFalse(d.valid_inventory_failure(failure|{key:value}))
        self.assertFalse(d.valid_inventory_records([record,record]))
        self.assertFalse(d.valid_inventory_failure(failure|{'bus':42}))
        for code in (None,True,1.0,'60',2**31,-2**31-1):
            error=ValueError('private');error.errno=code
            self.assertIsNone(d.make_inventory_failure('SDK_FIND_NORMAL',error)['errno'])


if __name__=='__main__':unittest.main()
