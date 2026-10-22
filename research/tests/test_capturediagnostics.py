"""Own errors and fixed metadata only; no USB imports or camera actions."""
import copy
import json
import unittest
from unittest.mock import patch

from lutphoto import capturediagnostics as d, capturemsc as m
from lutphoto.capturestore import Budget


class DiagnosticTests(unittest.TestCase):
    def context(self,**changes):
        return dict(transaction=5,part='DATA',direction='read',requested_bytes=8192,
                    call_number=13,callback_attempted=True,**changes)

    def failure(self,error=None):
        return d.make_failure(self.context(),'SDK_BULK_READ',OSError(60,'private source') if error is None else error,8451)

    def test_numeric_codes_only_and_no_exception_text_or_conversion(self):
        class USBError(OSError):
            backend_error_code=-7
            def __str__(self):raise AssertionError('Do not stringify errors')
            def __repr__(self):raise AssertionError('Do not repr errors')
        value=self.failure(USBError(60,'private path/identity/payload'))
        self.assertEqual((value['errno'],value['backend_error_code']),(60,-7))
        self.assertEqual(value['reason_type'],'USBError')
        self.assertNotIn('private',json.dumps(value));self.assertTrue(d.valid_failure(value))

    def test_missing_throwing_and_untrusted_code_attributes_are_absent(self):
        class Fault(Exception):
            @property
            def errno(self):raise KeyboardInterrupt('private')
            @property
            def backend_error_code(self):raise OSError('private')
        for error in (Exception(),Fault()):
            value=self.failure(error);self.assertIsNone(value['errno']);self.assertIsNone(value['backend_error_code'])
        for raw in (True,False,1.0,float('inf'),'60',[],{},-(2**31)-1,2**31):
            error=Exception();error.errno=raw;error.backend_error_code=raw
            value=self.failure(error);self.assertIsNone(value['errno']);self.assertIsNone(value['backend_error_code'])
        for raw in (-(2**31),-7,0,60,2**31-1):
            error=Exception();error.errno=raw
            self.assertEqual(self.failure(error)['errno'],raw)

    def test_all_fixed_callback_slots_and_inconsistent_metadata_refused(self):
        for (transaction,part),(number,kind,low,high) in d.SLOTS.items():
            context=dict(transaction=transaction,part=part,call_number=number,direction=kind,
                         requested_bytes=low,callback_attempted=True)
            value=d.make_failure(context,'CALLBACK',OSError(),0)
            self.assertTrue(d.valid_failure(value))
            for key,raw in (('call_number',0),('direction','other'),('requested_bytes',high+1)):
                self.assertFalse(d.valid_failure(value|{key:raw}),(transaction,part,key))
        self.assertFalse(d.valid_failure(self.failure()|{'boundary':'SDK_BULK_WRITE'}))
        self.assertFalse(d.valid_failure(self.failure()|{'returned_bytes':0}))

    def test_malformed_fields_extra_data_and_multiple_failures_refused(self):
        value=self.failure()
        for key in value:
            bad=copy.deepcopy(value);bad[key]=['untrusted']
            self.assertFalse(d.valid_failure(bad),key)
        self.assertFalse(d.valid_failure(value|{'payload':'private'}))
        entry={'owner':'normal-initial','failure':value,'record_error_type':None}
        self.assertTrue(d.valid_records([entry]));self.assertFalse(d.valid_records([entry,entry]))
        self.assertFalse(d.valid_records([entry|{'owner':'service'}]))
        self.assertFalse(d.valid_records([entry|{'failure':None}]))
        self.assertTrue(d.valid_records([entry|{'failure':None,'record_error_type':'OSError'}]))

    def test_precheck_and_invalid_return_boundaries_have_no_accepted_transfer(self):
        q=m._Query(lambda *a:self.fail('No callback'),lambda *a:self.fail('No callback'),Budget(30))
        with self.assertRaises(ValueError):q.run()
        self.assertEqual(q.calls,0);self.assertEqual(q.failure['boundary'],'QUERY_PRECHECK')
        self.assertFalse(q.failure['callback_attempted']);self.assertEqual(q.failure['call_number'],1)
        q=m._Query(lambda *a:30,lambda *a:self.fail('No next IO'),Budget(65536))
        with self.assertRaises(ValueError):q.run()
        self.assertEqual(q.failure['boundary'],'RESULT_VALIDATION')
        self.assertEqual((q.failure['returned_bytes'],q.failure['accepted_bytes']),(30,0))

    def test_late_return_accounting_is_distinct_from_sdk_exception(self):
        now=[0]
        def write(raw,t):now[0]=2;return len(raw)
        q=m._Query(write,lambda *a:self.fail('No next IO'),Budget(65536,seconds=1,clock=lambda:now[0]))
        with self.assertRaises(TimeoutError):q.run()
        self.assertEqual(q.failure['boundary'],'ACCOUNTING')
        self.assertEqual((q.failure['returned_bytes'],q.failure['accepted_bytes']),(31,0))

    def test_recording_failure_does_not_replace_original_or_retry(self):
        primary=OSError(60,'private original')
        def fail(*args):raise primary
        q=m._Query(fail,lambda *a:self.fail('No further IO'),Budget(65536))
        with patch.object(d,'make_failure',side_effect=RuntimeError('private recorder')) as recorder:
            with self.assertRaises(OSError) as caught:q.run()
        self.assertIs(caught.exception,primary);self.assertTrue(q.unknown)
        self.assertIsNone(q.failure);self.assertEqual(q.failure_record_error_type,'RuntimeError')
        self.assertEqual(recorder.call_count,1)
        with self.assertRaises(RuntimeError):q.run()
        self.assertEqual(q.calls,1)
