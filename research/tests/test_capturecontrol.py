"""Own OS arrival/cancellation traces; no USB, native calls or system lock."""
import json
import unittest
from unittest.mock import patch

from lutphoto import captureowned as o, captureinspect as i, capturestore
from lutphoto.capturecontrol import Cancellation, OperationCancelled, ObservationTimeout
from research.tests import test_captureowned as fixtures


class TransitionTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.OwnedTests(methodName='runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.fixture,self.root=fixture,fixture.root

    def make(self,arrivals,**kw):
        return self.fixture.make(system_options={'arrivals':arrivals},**kw)

    def test_absence_and_same_port_old_pid_then_stable_expected(self):
        keys=(o.m._Key(o.m.NORMAL,1,(1,2),4),o.m._Key(o.m.SERVICE,1,(1,2),5),o.m._Key(o.m.NORMAL,1,(1,2),6))
        result,system,directory=self.make({1:((),(keys[0],),(keys[1],),(keys[1],)),2:((keys[1],),(),(keys[2],),(keys[2],))})
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE')
        waits=[r['details'] for r in self.fixture.records(directory) if r['event']=='HOST_WAIT_END_MODELED']
        self.assertEqual(waits,[{'phase':'service','outcome':'found','polls':4},{'phase':'normal-return','outcome':'found','polls':4}])
        self.assertEqual(system.counts['open'],3);self.assertEqual(i.inspect_directory(directory)['classification'],'CONSISTENT_SIMULATION_COMPLETE')

    def test_service_never_arrives_no_auth_retry_or_service_commands(self):
        result,system,directory=self.make({1:((),)})
        self.assertEqual(result['reason_type'],'ObservationTimeout');self.assertFalse(result['simulated_outcome_unknown'])
        self.assertFalse(result['simulated_service_stop_ack']);self.assertEqual(system.counts['open'],1)
        self.assertEqual(system.counts['control'],1);self.assertEqual(system.counts['dispose'],1)
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')
        waits=[r['details'] for r in self.fixture.records(directory) if r['event']=='HOST_WAIT_END_MODELED']
        self.assertEqual(waits,[{'phase':'service','outcome':'timed-out','polls':40}])

    def test_normal_return_timeout_keeps_known_stop_and_protocol_result(self):
        result,system,directory=self.make({2:((),)})
        self.assertEqual(result['reason_type'],'ObservationTimeout');self.assertFalse(result['simulated_outcome_unknown'])
        self.assertTrue(result['simulated_service_stop_ack']);self.assertEqual(result['authentication_phase'],'STOP_CONTROL_RETURNED')
        self.assertFalse(result['simulated_normal_identity_matched']);self.assertEqual(system.counts['open'],2)
        self.assertEqual(system.service_device.counts['control'],2);self.assertEqual(system.counts['dispose'],2)
        inspected=i.inspect_directory(directory)
        self.assertEqual(inspected['classification'],'NEEDS_REVIEW_UNKNOWN');self.assertGreater(inspected['unacknowledged_intents'],0)

    def test_both_pids_at_same_port_refused_immediately(self):
        old=o.m._Key(o.m.NORMAL,1,(1,2),4);new=o.m._Key(o.m.SERVICE,1,(1,2),5)
        result,system,_=self.make({1:((old,new),)})
        self.assertEqual(result['reason_type'],'ValueError');self.assertTrue(result['simulated_outcome_unknown'])
        self.assertEqual(system.counts['open'],1);self.assertLess(system.now,4)

    def test_wrong_port_old_pid_is_not_waitable(self):
        key=o.m._Key(o.m.NORMAL,1,(9,),4)
        result,system,_=self.make({1:((key,),)})
        self.assertEqual(result['reason_type'],'ValueError');self.assertEqual(system.counts['open'],1);self.assertLess(system.now,4)

    def test_expected_device_address_must_be_stable_before_open(self):
        first=o.m._Key(o.m.SERVICE,1,(1,2),7);correct=o.m._Key(o.m.SERVICE,1,(1,2),5)
        result,_,directory=self.make({1:((first,),(correct,),(correct,))})
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE')
        first_wait=next(r['details'] for r in self.fixture.records(directory) if r['event']=='HOST_WAIT_END_MODELED')
        self.assertEqual(first_wait['polls'],3)

    def test_sdk_timeout_during_poll_is_not_observation_timeout(self):
        # Initial normal capture uses two inventories, then the service wait.
        result,system,directory=self.fixture.make(system_options={'faults':{('inventory',3):TimeoutError('own SDK')}})
        self.assertEqual(result['reason_type'],'TimeoutError');self.assertTrue(result['simulated_outcome_unknown'])
        self.assertEqual(system.counts['open'],1);self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_injected_observation_exception_not_treated_as_host_deadline_receipt(self):
        result,_,_=self.fixture.make(system_options={'faults':{('inventory',3):ObservationTimeout('service')}})
        self.assertTrue(result['simulated_outcome_unknown'])

    def test_late_sdk_return_cannot_be_treated_as_on_time_arrival(self):
        original=o.SyntheticSystem.inventory
        def slow(system):
            value=original(system)
            if system.phase==1:system.now+=21
            return value
        with patch.object(o.SyntheticSystem,'inventory',slow):result,system,_=self.fixture.make()
        self.assertEqual(result['reason_type'],'ObservationTimeout');self.assertFalse(result['simulated_outcome_unknown'])
        self.assertEqual(system.counts['open'],1)

    def test_global_deadline_expiring_inside_sdk_keeps_unacknowledged_intent(self):
        original=o.SyntheticSystem.inventory
        def slow(system):
            value=original(system)
            if system.phase==1:system.now=1201
            return value
        with patch.object(o.SyntheticSystem,'inventory',slow):result,_,directory=self.fixture.make()
        self.assertEqual(result['reason_type'],'TimeoutError');self.assertTrue(result['simulated_outcome_unknown'])
        self.assertEqual(i.inspect_directory(directory)['classification'],'NEEDS_REVIEW_UNKNOWN')

    def test_cancel_before_entry_creates_nothing(self):
        token=Cancellation();token.cancel();system=self.fixture.system();directory=self.root/'cancelled'
        with self.assertRaises(OperationCancelled):o.rehearse('own',directory,system,cancel=token)
        self.assertFalse(system.trace);self.assertFalse(directory.exists())

    def test_cancel_after_open_adopts_and_disposes_before_claim(self):
        token=Cancellation();original=o.SyntheticSystem.open;system=self.fixture.system()
        def opened(system,*args):
            handle=original(system,*args);token.cancel();return handle
        with patch.object(o.SyntheticSystem,'open',opened):result=o.rehearse('own',self.root/'open-cancel',system,cancel=token)
        self.assertEqual(result['reason_type'],'OperationCancelled');self.assertEqual(system.counts['dispose'],1)
        self.assertEqual(system.counts.get('claim',0),0);self.assertEqual(system.counts.get('write',0),0)

    def test_cancel_between_wait_polls_sends_no_new_protocol_command(self):
        token=Cancellation();original=o.SyntheticSystem.sleep;system=self.fixture.system(system_options={'arrivals':{1:((),)}})
        def sleep(system,seconds):
            original(system,seconds)
            if system.phase==1:token.cancel()
        with patch.object(o.SyntheticSystem,'sleep',sleep):result=o.rehearse('own',self.root/'wait-cancel',system,cancel=token)
        self.assertEqual(result['reason_type'],'OperationCancelled');self.assertEqual(system.counts['open'],1)
        self.assertEqual(system.counts['control'],1);self.assertEqual(system.counts['dispose'],1)

    def test_cancel_inside_msc_send_has_no_followup_csw_read_or_auth(self):
        token=Cancellation();original=o.SyntheticSystem.write;system=self.fixture.system()
        def sent(system,*args):
            result=original(system,*args);token.cancel();return result
        with patch.object(o.SyntheticSystem,'write',sent):result=o.rehearse('own',self.root/'msc-cancel',system,cancel=token)
        self.assertTrue(result['simulated_outcome_unknown']);self.assertEqual(system.counts['write'],1)
        self.assertEqual(system.counts.get('read',0),0);self.assertEqual(system.counts.get('control',0),0)
        self.assertEqual(system.counts['dispose'],1);self.assertEqual(system.counts.get('attach',0),0)

    def test_cancel_inside_material_read_keeps_stop_unattempted(self):
        token=Cancellation();original=o.SyntheticSystem.read;system=self.fixture.system()
        def received(system,handle,*args):
            value=original(system,handle,*args)
            if handle.pid==o.m.SERVICE and system.service_device.auth.used>=15:token.cancel()
            return value
        with patch.object(o.SyntheticSystem,'read',received):result=o.rehearse('own',self.root/'material-cancel',system,cancel=token)
        self.assertTrue(result['simulated_outcome_unknown']);self.assertEqual(system.service_device.counts['control'],1)
        self.assertEqual(system.counts['dispose'],2);self.assertEqual(system.counts.get('attach',0),0)

    def test_external_cancellation_subclass_is_rejected(self):
        class External(Cancellation):pass
        system=self.fixture.system()
        with self.assertRaises(TypeError):o.rehearse('own',self.root/'external',system,cancel=External())
        self.assertFalse(system.trace)

    def test_rechained_wait_poll_count_contradiction_is_rejected(self):
        _,_,directory=self.fixture.make()
        def edit(record):
            if record['event']=='HOST_WAIT_END_MODELED':record['details']['polls']+=1
        self.fixture.rechain(directory,edit)
        self.assertEqual(i.inspect_directory(directory)['classification'],'EVIDENCE_INCONSISTENT')

    def test_old_owned_format_without_waits_remains_inspectable(self):
        original=o.m._Host.__init__
        def legacy(host,*args,**kw):kw['wait']=False;original(host,*args,**kw)
        with patch.object(o.m._Host,'__init__',legacy):result,_,directory=self.fixture.make()
        self.assertEqual(result['phase'],'SIMULATED_OWNED_CAPTURE_COMPLETE')
        self.assertEqual(i.inspect_directory(directory)['classification'],'CONSISTENT_SIMULATION_COMPLETE')

    def test_cancel_after_global_acquire_attempts_release_without_creating_job(self):
        original=o.SyntheticSystem.acquire
        for failed_unlock in (False,True):
            token=Cancellation();system=self.fixture.system(system_options={'faults':{('global-release',1):OSError('own release')}} if failed_unlock else {})
            directory=self.root/('acquire-cancel-'+str(failed_unlock))
            def acquired(system):
                result=original(system);token.cancel();return result
            with patch.object(o.SyntheticSystem,'acquire',acquired):
                with self.assertRaises(OperationCancelled):o.rehearse('own',directory,system,cancel=token)
            self.assertEqual(system.trace,['global-acquire','global-release']);self.assertFalse(directory.exists())
