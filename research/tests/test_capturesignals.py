"""Scope failure/ownership checks and actual signals to own fake children."""
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import Mock,patch

from lutphoto import capturesignals as s, captureinspect, captureevidence
from lutphoto.capturecontrol import Cancellation,OperationCancelled
from research.tests import test_captureowned as fixtures


class FakeSignals:
    SIGINT,SIGTERM,SIG_DFL=signal.SIGINT,signal.SIGTERM,signal.SIG_DFL
    default_int_handler=staticmethod(signal.default_int_handler)
    def __init__(self):
        self.handlers={self.SIGINT:self.default_int_handler,self.SIGTERM:self.SIG_DFL}
        self.calls=[];self.faults={};self.after_faults={}
    def getsignal(self,n):return self.handlers[n]
    def signal(self,n,handler):
        self.calls.append((n,handler));number=len(self.calls)
        if number in self.faults:raise self.faults[number]
        old=self.handlers[n];self.handlers[n]=handler
        if number in self.after_faults:raise self.after_faults[number]
        return old


class SignalScopeTests(unittest.TestCase):
    def setUp(self):
        self.api=FakeSignals();self.old=dict(self.api.handlers)
        self.binding=patch.object(s,'signal',self.api);self.binding.start();self.addCleanup(self.binding.stop)

    def test_install_and_restore_default_handlers_in_reverse_order(self):
        token=Cancellation();scope=s.SignalCancellation(token)
        self.assertFalse(self.api.calls)
        with scope:
            self.assertIs(self.api.handlers[self.api.SIGINT],scope._handler)
            self.assertIs(self.api.handlers[self.api.SIGTERM],scope._handler)
            self.assertFalse(scope.restoration_confirmed)
        self.assertEqual(self.api.handlers,self.old);self.assertTrue(scope.restoration_confirmed)
        self.assertEqual([n for n,_ in self.api.calls],[self.api.SIGINT,self.api.SIGTERM,self.api.SIGTERM,self.api.SIGINT])

    def test_sigint_default_disposition_is_also_preserved(self):
        self.api.handlers[self.api.SIGINT]=self.api.SIG_DFL
        with s.SignalCancellation(Cancellation()):pass
        self.assertIs(self.api.handlers[self.api.SIGINT],self.api.SIG_DFL)

    def test_plain_handler_sets_flag_without_event_lock_callback_or_exception(self):
        token=Cancellation();scope=s.SignalCancellation(token);frame=object()
        with patch.object(token,'cancel',side_effect=AssertionError('No callback')) as callback,patch.object(token._event,'set',side_effect=AssertionError('No Event lock')) as event:
            for signum in (self.api.SIGINT,self.api.SIGTERM,self.api.SIGINT):scope._receive(signum,frame)
        callback.assert_not_called();event.assert_not_called();self.assertTrue(token.requested)
        self.assertNotIn(frame,vars(scope).values())
        with self.assertRaises(OperationCancelled):token.check()

    def test_normal_thread_cancellation_still_works_and_signal_request_is_sticky(self):
        token=Cancellation();token.cancel();self.assertTrue(token.requested)
        other=Cancellation()
        with s.SignalCancellation(other) as scope:scope._handler(self.api.SIGTERM,None)
        self.assertTrue(other.requested)

    def test_exact_token_and_already_cancelled_prerequisites_before_install(self):
        class External(Cancellation):pass
        for token in (None,object(),External()):
            with self.assertRaises(TypeError):s.SignalCancellation(token)
        token=Cancellation();token.cancel()
        with self.assertRaises(OperationCancelled):s.SignalCancellation(token).__enter__()
        self.assertFalse(self.api.calls)

    def test_worker_thread_refused_without_signal_changes(self):
        errors=[];scope=s.SignalCancellation(Cancellation())
        def worker():
            try:scope.__enter__()
            except BaseException as exc:errors.append(type(exc))
        thread=threading.Thread(target=worker);thread.start();thread.join(timeout=2)
        self.assertEqual(errors,[s.SignalScopeError]);self.assertFalse(self.api.calls)

    def test_custom_ignored_or_unknown_handlers_refused_without_chaining(self):
        callback=Mock()
        for n in (self.api.SIGINT,self.api.SIGTERM):
            for handler in (callback,signal.SIG_IGN,None):
                self.api.handlers=dict(self.old);self.api.handlers[n]=handler
                with self.assertRaises(s.SignalScopeError):s.SignalCancellation(Cancellation()).__enter__()
                self.assertIs(self.api.handlers[n],handler)
        self.assertFalse(self.api.calls);callback.assert_not_called()

    def test_scope_replay_and_nested_scope_refused(self):
        scope=s.SignalCancellation(Cancellation())
        with scope:
            with self.assertRaises(s.SignalScopeError):s.SignalCancellation(Cancellation()).__enter__()
        with self.assertRaises(s.SignalScopeError):scope.__enter__()
        self.assertEqual(len(self.api.calls),4)

    def test_partial_install_failure_restores_only_owned_changes(self):
        for changed in (False,True):
            self.api.calls=[];self.api.handlers=dict(self.old);self.api.faults={};self.api.after_faults={}
            (self.api.after_faults if changed else self.api.faults)[2]=OSError('own install')
            scope=s.SignalCancellation(Cancellation())
            with self.assertRaisesRegex(OSError,'own install'):scope.__enter__()
            self.assertEqual(self.api.handlers,self.old);self.assertTrue(scope.restoration_confirmed)

    def test_first_install_failure_before_or_after_change_is_rolled_back(self):
        for changed in (False,True):
            self.api.calls=[];self.api.handlers=dict(self.old);self.api.faults={};self.api.after_faults={}
            (self.api.after_faults if changed else self.api.faults)[1]=OSError('own install')
            scope=s.SignalCancellation(Cancellation())
            with self.assertRaisesRegex(OSError,'own install'):scope.__enter__()
            self.assertEqual(self.api.handlers,self.old);self.assertTrue(scope.restoration_confirmed)

    def test_install_race_restores_actual_previous_handler_without_calling_it(self):
        foreign=Mock();original=self.api.signal
        def raced(n,handler):
            if not self.api.calls:self.api.handlers[n]=foreign
            return original(n,handler)
        with patch.object(self.api,'signal',raced):
            scope=s.SignalCancellation(Cancellation())
            with self.assertRaises(s.SignalScopeError):scope.__enter__()
        self.assertIs(self.api.handlers[self.api.SIGINT],foreign);foreign.assert_not_called()
        self.assertTrue(scope.restoration_confirmed)

    def test_install_return_without_matching_readback_is_refused_before_body(self):
        def unconfirmed(n,handler):return self.api.handlers[n]
        scope=s.SignalCancellation(Cancellation())
        with patch.object(self.api,'signal',unconfirmed):
            with self.assertRaises(s.SignalScopeError):scope.__enter__()
        self.assertTrue(scope.restoration_confirmed);self.assertEqual(self.api.handlers,self.old)

    def test_signal_during_install_cancels_entry_and_restores_handlers(self):
        scope=s.SignalCancellation(Cancellation());original=self.api.signal
        def interrupted(n,handler):
            value=original(n,handler)
            if len(self.api.calls)==2:scope._handler(n,None)
            return value
        with patch.object(self.api,'signal',interrupted):
            with self.assertRaises(OperationCancelled):scope.__enter__()
        self.assertTrue(scope.token.requested);self.assertTrue(scope.restoration_confirmed)
        self.assertEqual(self.api.handlers,self.old)

    def test_install_and_restore_failure_preserve_install_error(self):
        self.api.faults={2:OSError('own install'),3:RuntimeError('own restore')}
        scope=s.SignalCancellation(Cancellation())
        with self.assertRaisesRegex(OSError,'own install') as error:scope.__enter__()
        self.assertIsInstance(error.exception.__cause__,s.SignalScopeError)
        self.assertFalse(scope.restoration_confirmed)

    def test_restore_failure_does_not_hide_body_error_or_repeat_restore(self):
        scope=s.SignalCancellation(Cancellation());primary=ValueError('own body')
        self.api.faults[3]=OSError('own restore')
        with self.assertRaises(ValueError) as error:
            with scope:raise primary
        self.assertIs(error.exception,primary);self.assertIsInstance(primary.__cause__,s.SignalScopeError)
        self.assertFalse(scope.restoration_confirmed);self.assertEqual(len(self.api.calls),4)
        with self.assertRaises(s.SignalScopeError):scope.__exit__(None,None,None)
        self.assertEqual(len(self.api.calls),4)

    def test_restore_failure_on_success_still_raises(self):
        self.api.faults[3]=OSError('own restore');scope=s.SignalCancellation(Cancellation())
        with self.assertRaises(s.SignalScopeError):
            with scope:pass
        self.assertFalse(scope.restoration_confirmed)

    def test_changed_handler_is_not_overwritten_but_other_owned_handler_restored(self):
        foreign=Mock();scope=s.SignalCancellation(Cancellation())
        with self.assertRaises(s.SignalScopeError):
            with scope:self.api.handlers[self.api.SIGTERM]=foreign
        self.assertIs(self.api.handlers[self.api.SIGTERM],foreign)
        self.assertIs(self.api.handlers[self.api.SIGINT],self.old[self.api.SIGINT]);foreign.assert_not_called()
        self.assertFalse(scope.restoration_confirmed)

    def test_unconfirmed_restore_return_is_not_claimed_as_restored(self):
        original=self.api.signal
        def unconfirmed(n,handler):
            if handler is self.old[n]:return self.api.handlers[n]
            return original(n,handler)
        scope=s.SignalCancellation(Cancellation())
        with patch.object(self.api,'signal',unconfirmed):
            with self.assertRaises(s.SignalScopeError):
                with scope:pass
        self.assertFalse(scope.restoration_confirmed)

    def test_worker_exit_refused_and_main_thread_can_still_restore(self):
        scope=s.SignalCancellation(Cancellation());scope.__enter__();errors=[]
        def worker():
            try:scope.__exit__(None,None,None)
            except BaseException as exc:errors.append(type(exc))
        thread=threading.Thread(target=worker);thread.start();thread.join(timeout=2)
        self.assertEqual(errors,[s.SignalScopeError]);self.assertEqual(len(self.api.calls),2)
        scope.__exit__(None,None,None);self.assertTrue(scope.restoration_confirmed)

    def test_signal_import_does_not_change_process_handlers_or_import_sdk(self):
        script="import signal,sys; before={n:signal.getsignal(n) for n in (signal.SIGINT,signal.SIGTERM)}; from lutphoto import capturesignals; assert before=={n:signal.getsignal(n) for n in before}; assert not any(n=='usb' or n.startswith('usb.') or n=='libusb_package' for n in sys.modules); print('PASS')"
        result=subprocess.run([sys.executable,'-S','-B','-c',script],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[2],timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,'PASS\n')


class SignalProcessTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.OwnedTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.root=f.root

    def read(self,process):
        buffer=bytearray();end=time.monotonic()+10
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout,selectors.EVENT_READ)
            while b'\n' not in buffer:
                remaining=end-time.monotonic();self.assertGreater(remaining,0,'Own child handshake timeout')
                self.assertTrue(selector.select(remaining),'Own child handshake timeout')
                part=os.read(process.stdout.fileno(),1)
                self.assertTrue(part,'Own child ended before handshake');buffer.extend(part)
                self.assertLess(len(buffer),4096)
        return json.loads(buffer)

    def exercise(self,scenario,signum,*,execution=False):
        directory=self.root/scenario
        child_scenario='execution-'+scenario if execution else scenario
        inspector=captureevidence if execution else captureinspect
        process=subprocess.Popen([sys.executable,'-S','-B','-m','research.tests.signal_capture_child',child_scenario,str(directory)],
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                 cwd=Path(__file__).resolve().parents[2])
        try:
            blocked=self.read(process);self.assertEqual(blocked['phase'],'BLOCKED')
            self.assertTrue(blocked['lease_held']);self.assertFalse(blocked['sdk_returned']);self.assertFalse(blocked['cancel_requested'])
            os.kill(process.pid,signum)  # Only our newly created self-made child.
            observed=self.read(process);self.assertEqual(observed['phase'],'SIGNAL_OBSERVED')
            self.assertTrue(observed['lease_held']);self.assertTrue(observed['owner_retained'])
            self.assertTrue(observed['cancel_requested']);self.assertFalse(observed['sdk_returned'])
            self.assertIs(observed['views_invalidated'],scenario=='dispose')
            report=captureevidence.CHECKPOINT if execution else 'owned-report.private.json'
            self.assertIsNone(process.poll());self.assertFalse((directory/report).exists())
            self.assertEqual(inspector.inspect_directory(directory)['issues'],['ACTIVE_JOB'])
            for n in ('write_calls','read_calls','control_calls'):self.assertEqual(observed[n],blocked[n])
            output,error=process.communicate(input=b'RETURN\n',timeout=10)
            self.assertEqual(process.returncode,0,error.decode())
            done=json.loads(output);self.assertEqual(done['phase'],'DONE');self.assertEqual(done['capture_phase'],'NEEDS_REVIEW')
            self.assertEqual(done['reason_type'],'OperationCancelled');self.assertTrue(done['handlers_restored'])
            self.assertEqual(done['classification'],'NEEDS_REVIEW_UNKNOWN')
            self.assertFalse(done['service_stop_ack']);self.assertFalse(done['normal_identity_matched']);self.assertTrue(done['physical_flags_false'])
            self.assertTrue(done['single_disposal_attempts']);self.assertFalse(done['lease_held']);self.assertTrue(done['sdk_returned'])
            self.assertFalse(done['device_operations_performed']);self.assertFalse(done['native_sdk_imported'])
            for n in ('write_calls','read_calls','control_calls'):self.assertEqual(done[n],observed[n])
            self.assertNotIn(str(directory),output.decode())
            self.assertEqual(inspector.inspect_directory(directory)['classification'],done['classification'])
        finally:
            if process.poll() is None:
                try:
                    if process.stdin is not None and not process.stdin.closed:
                        process.stdin.write(b'RETURN\n');process.stdin.flush()
                    process.communicate(timeout=3)
                except (subprocess.TimeoutExpired,OSError,ValueError):process.kill();process.communicate(timeout=3)
            for stream in (process.stdin,process.stdout,process.stderr):
                if stream is not None:stream.close()

    def test_sigint_during_configuration_keeps_owner_and_job_until_return(self):self.exercise('configuration',signal.SIGINT)
    def test_sigterm_during_material_sends_no_stop_or_new_protocol_after_return(self):self.exercise('material',signal.SIGTERM)
    def test_sigterm_during_stop_does_not_forge_stop_ack_or_return(self):self.exercise('stop',signal.SIGTERM)
    def test_sigint_during_disposal_does_not_repeat_sdk_close(self):self.exercise('dispose',signal.SIGINT)


if __name__=='__main__':unittest.main()
