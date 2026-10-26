"""Single snapshot probe through native methods on self-made SDK/OS only."""
from array import array
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import captureprobe as p, capturecamera as c, captureevidence as e
from research.tests import test_capturecamera as camera, native_sdk_fixture as sdk


class ProductDevice(sdk.Device):
    iProduct=2

    def ctrl_transfer(self,*request,timeout):
        self.ready();assert self.claimed and 0<timeout<=5000
        if request[0]==0x80:
            self.world.record('string',self)
            if request==(0x80,6,0x0300,0,254):return array('B',b'\x04\x03\x09\x04')
            assert request==(0x80,6,0x0302,0x0409,254)
            raw=self.world.product.encode('utf-16-le')
            return array('B',bytes((len(raw)+2,3))+raw)
        self.world.record('control',self)
        # This oracle has an auth-only normal endpoint. A storage inquiry would
        # be rejected by SyntheticDriver's fixed 516-byte packet requirements.
        return self.handle.protocol.ctrl_transfer(*request,timeout=timeout)

    def write(self,endpoint,raw,*,timeout):
        self.ready();assert self.claimed and endpoint==next(ep for ep,_ in self.endpoints if not ep&0x80)
        self.world.record('write',self)
        return self.handle.protocol.write(endpoint,raw,timeout=timeout)

    def read(self,endpoint,size,*,timeout):
        self.ready();assert self.claimed and endpoint==next(ep for ep,_ in self.endpoints if ep&0x80)
        self.world.record('read',self)
        return self.handle.protocol.read(endpoint,size,timeout=timeout)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        f=camera.CameraTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.f,self.root,self.files=f,f.root,f.files

    def world(self,**kw):
        world=sdk.World(self.f.fixture.system(**kw));world.product='ILCE-7CM2';return world

    @contextlib.contextmanager
    def bound(self,world,**kw):
        with self.f.bound(world,**kw),patch.object(sdk,'Device',ProductDevice),\
             patch.object(p.o.m._Owner,'query',side_effect=AssertionError('Probe must never query MSC')):
            yield

    def args(self,name='probe',**kw):
        args=self.f.args(name,**kw);args.pop('resources');return args

    def call(self,world,args):
        with self.bound(world):result=p.probe(**args)
        self.assertEqual(json.loads(args['receipt'].read_bytes()),result)
        return result

    def cli(self,world,args,*,env=None,output=None):
        argv=[]
        for name,value in args.items():argv.extend(('--'+name.replace('_','-'),str(value)))
        out=io.StringIO() if output is None else output
        with self.bound(world,env=env),contextlib.redirect_stdout(out):code=p.main(argv)
        return code,out

    def test_public_entry_reads_one_snapshot_with_separate_passive_return_evidence(self):
        world=self.world();args=self.args();result=self.call(world,args)
        self.assertEqual(result['phase'],'PROBE_COMPLETE')
        self.assertTrue(all(result['cleanup'].values()));self.assertFalse(result['errors'])
        self.assertEqual(result['observations']['service_identity']['serial_source'],p.identity.SERVICE_SOURCE)
        self.assertEqual(result['unproven'],dict.fromkeys(p.UNPROVEN,False))
        self.assertTrue(result['facts']['service_stop_confirmed']);self.assertTrue(result['facts']['normal_usb_reappeared'])
        self.assertFalse(result['facts']['protocol_outcome_unknown'])
        self.assertEqual(world.system.peer.trace,['wire:ram'])
        self.assertEqual(world.system.counts['dispose'],2)
        self.assertEqual(world.system.normal_device.auth.used,15)
        self.assertEqual(world.system.service_device.auth.used,16)
        self.assertEqual([h.used for h in world.system.handles],[0,0,0])
        self.assertEqual(world.counts['string'],2);self.assertFalse(world.system.acquired)
        self.assertEqual(result['snapshot']['bytes'],len(self.files['ram']))
        self.assertEqual((args['directory']/p.SNAPSHOT).read_bytes(),self.files['ram'])
        self.assertEqual(args['receipt'].stat().st_mode&0o777,0o600)
        self.assertFalse(e.valid_receipt(result))

    def test_wrong_model_or_missing_index_stops_before_auth(self):
        for index in range(2):
            world=self.world();args=self.args(str(index))
            if index==0:world.product='ILCE-7CR'
            with patch.object(ProductDevice,'iProduct',0 if index else 2):result=self.call(world,args)
            self.assertEqual(result['phase'],'NEEDS_REVIEW')
            self.assertEqual(world.counts.get('control',0),0);self.assertEqual(world.counts.get('write',0),0)
            self.assertFalse(result['facts']['normal_authenticated'])

    def test_standard_string_timeout_and_bad_length_do_not_enter_auth(self):
        original=ProductDevice.ctrl_transfer
        for i,bad in enumerate((TimeoutError(60,'private model read'),array('B',b'\x06\x03\x09\x04'),
                                array('B',bytes(256)),array('H',[4,3,9,4]))):
            world=self.world();args=self.args(str(i))
            def failed(device,*request,timeout):
                if request[0]==0x80:
                    if isinstance(bad,BaseException):raise bad
                    return bad
                return original(device,*request,timeout=timeout)
            with patch.object(ProductDevice,'ctrl_transfer',failed):result=self.call(world,args)
            self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['facts']['protocol_outcome_unknown'])
            self.assertEqual(world.counts.get('control',0),0)
            self.assertNotIn('private model read',json.dumps(result))
            if i==0:self.assertEqual(result['errors'][0]['errno'],60)

    def test_unknown_authentication_or_material_never_stops_or_reauthenticates(self):
        cases=({'normal_options':{'faults':{('read',1):TimeoutError('normal')}}},
               {'service_options':{'faults':{('read',1):TimeoutError('service')}}},
               {'service_options':{'faults':{('read',8):TimeoutError('material')}}})
        for i,options in enumerate(cases):
            world=self.world(**options);result=self.call(world,self.args(str(i)))
            self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['facts']['protocol_outcome_unknown'])
            self.assertFalse(result['facts']['service_stop_attempted']);self.assertIsNone(result['observations']['service_identity'])
            self.assertEqual(world.system.normal_device.counts['control'],1)
            self.assertEqual(world.system.service_device.counts.get('control',0),0 if i==0 else 1)

    def test_invalid_complete_snapshot_exits_once_and_preserves_failed_material(self):
        world=self.world(files=self.files|{'ram':bytes(len(self.files['ram']))});result=self.call(world,self.args())
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertFalse(result['facts']['snapshot_validated'])
        self.assertFalse(result['facts']['protocol_outcome_unknown']);self.assertTrue(result['facts']['service_stop_confirmed'])
        self.assertTrue(result['facts']['normal_usb_reappeared']);self.assertIsNotNone(result['snapshot'])
        self.assertEqual(world.system.service_device.counts['control'],2)

    def test_stop_failure_is_not_retried_and_keeps_identity_result(self):
        world=self.world(service_options={'faults':{('control',2):TimeoutError('stop')}})
        result=self.call(world,self.args());self.assertEqual(result['phase'],'NEEDS_REVIEW')
        self.assertTrue(result['facts']['snapshot_validated']);self.assertTrue(result['facts']['service_stop_attempted'])
        self.assertFalse(result['facts']['service_stop_confirmed']);self.assertFalse(result['facts']['normal_usb_reappeared'])
        self.assertTrue(result['facts']['protocol_outcome_unknown']);self.assertEqual(world.system.service_device.counts['control'],2)

    def test_return_timeout_keeps_confirmed_stop_without_claiming_return_identity(self):
        world=self.world();find=world.core.find
        def missing(**kw):
            values=list(find(**kw))
            return [] if world.system.phase==2 else values
        with patch.object(world.core,'find',side_effect=missing):result=self.call(world,self.args())
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['facts']['service_stop_confirmed'])
        self.assertFalse(result['facts']['normal_usb_reappeared']);self.assertFalse(result['unproven']['normal_identity_rechecked'])
        self.assertFalse(result['facts']['protocol_outcome_unknown']);self.assertEqual(world.system.service_device.counts['control'],2)

    def test_service_or_return_port_changes_and_multiple_devices_are_rejected(self):
        m=p.o.m
        for phase in (1,2):
            for multiple in (False,True):
                key=m._Key(m.SERVICE if phase==1 else m.NORMAL,1,(1,9),5+phase)
                row=(key,key) if multiple else (key,)
                world=self.world(system_options={'arrivals':{phase:(row,)}})
                result=self.call(world,self.args(str(phase)+str(multiple)))
                self.assertEqual(result['phase'],'NEEDS_REVIEW')
                self.assertFalse(result['facts']['normal_usb_reappeared'])
                self.assertEqual(world.system.service_device.counts.get('control',0),0 if phase==1 else 2)

    def test_inventory_failure_keeps_bounded_host_diagnostic(self):
        world=self.world();args=self.args()
        with patch.object(ProductDevice,'__init__',side_effect=ValueError('private inventory')):
            result=self.call(world,args)
        self.assertEqual(result['phase'],'NEEDS_REVIEW')
        self.assertEqual(len(result['host_diagnostics']),1)
        self.assertFalse(result['facts']['normal_authenticated'])
        self.assertNotIn('private inventory',json.dumps(result))

    def test_cleanup_failure_cannot_turn_observed_probe_into_success(self):
        for operation in ('dispose','global-release'):
            world=self.world(system_options={'faults':{(operation,2 if operation=='dispose' else 1):OSError('cleanup')}})
            result=self.call(world,self.args(operation))
            self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['errors'])
            self.assertFalse(result['cleanup']['owners' if operation=='dispose' else 'global_lease'])

    def test_one_deadline_covers_string_reads_and_authentication(self):
        world=self.world();original=ProductDevice.ctrl_transfer
        def delayed(device,*request,timeout):
            value=original(device,*request,timeout=timeout)
            if request[0]==0x80:world.system.now+=70
            return value
        with patch.object(ProductDevice,'ctrl_transfer',delayed):result=self.call(world,self.args())
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertFalse(result['facts']['normal_authenticated'])
        self.assertEqual(world.counts.get('control',0),0)

    def test_journal_ack_failure_blocks_exit_after_known_authentication(self):
        world=self.world();event=p.Store.event
        def failed(store,name,**details):
            if name=='ACK' and details.get('operation')=='SERVICE_VERIFY':raise OSError('journal')
            return event(store,name,**details)
        with patch.object(p.Store,'event',failed):result=self.call(world,self.args())
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertTrue(result['facts']['service_authenticated'])
        self.assertFalse(result['facts']['service_stop_attempted']);self.assertFalse(world.system.peer.trace)
        self.assertEqual(world.system.service_device.counts['control'],1)

    def test_cancellation_during_read_holds_scopes_until_return_then_stops(self):
        world=self.world();read=ProductDevice.read
        def cancelled(device,endpoint,size,*,timeout):
            value=read(device,endpoint,size,timeout=timeout)
            if device.key.pid==p.o.m.SERVICE and device.handle.protocol.auth.used==15:
                self.assertTrue(world.system.acquired)
                # Signal handler is the installed cooperative flag setter.
                import signal
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM,None)
            return value
        with patch.object(ProductDevice,'read',cancelled):result=self.call(world,self.args())
        self.assertEqual(result['phase'],'NEEDS_REVIEW');self.assertFalse(result['facts']['service_stop_attempted'])
        self.assertFalse(world.system.acquired);self.assertTrue(result['cleanup']['signal_handlers'])

    def test_receipt_failure_preserves_primary_and_never_retries_probe(self):
        world=self.world(service_options={'faults':{('read',8):TimeoutError('private')}});args=self.args()
        def failed(destination,value):raise OSError('private output')
        with patch.object(p._Receipt,'save',failed):code,out=self.cli(world,args)
        value=json.loads(out.getvalue());self.assertEqual(code,1)
        self.assertEqual(value['phase'],'PROBE_OR_DELIVERY_UNCONFIRMED');self.assertEqual(value['reason_type'],'TimeoutError')
        self.assertIn('OSError',value['secondary_error_types']);self.assertFalse(value['receipt_saved'])
        self.assertEqual(world.system.normal_device.counts['control'],1)

    def test_cli_summary_has_no_identity_and_stdout_failure_stays_failure(self):
        world=self.world();code,out=self.cli(world,self.args('ok'))
        self.assertEqual(code,0);value=json.loads(out.getvalue());self.assertEqual(value['schema'],p.CLI_SCHEMA)
        for word in (str(self.root),'serial_sha256','job_id','archive_sha256'):self.assertNotIn(word,out.getvalue())
        class Short(io.StringIO):
            def write(self,raw):return 0
        world=self.world();stderr=io.StringIO()
        with contextlib.redirect_stderr(stderr):code,_=self.cli(world,self.args('short'),output=Short())
        self.assertEqual(code,1);self.assertEqual(json.loads(stderr.getvalue())['phase'],'OUTPUT_UNCONFIRMED')
        self.assertEqual(world.system.normal_device.counts['control'],1)

    def test_declarations_environment_sources_and_existing_outputs_refuse_before_device(self):
        for i,change in enumerate(({'firmware':'2.00'},{'model':'ILCE-7CR'},{'battery_percent':49},{'battery_percent':True})):
            world=self.world()
            with self.bound(world),self.assertRaises(c.CaptureFailure):p.probe(**self.args(str(i),**change))
            self.assertFalse(world.trace)
        world=self.world();args=self.args('env');code,_=self.cli(world,args,env=self.f.env|{'administrator_context_present':False})
        self.assertEqual(code,1);self.assertFalse(world.trace)
        world=self.world();args=self.args('source')
        with patch.object(p.a,'_keys',side_effect=ValueError('source')):code,_=self.cli(world,args)
        self.assertEqual(code,1);self.assertFalse(world.trace);self.assertFalse(args['receipt'].exists())
        for kind in ('directory','receipt'):
            world=self.world();args=self.args(kind)
            if kind=='directory':args[kind].mkdir(mode=0o700)
            else:args[kind].write_bytes(b'existing');args[kind].chmod(0o600)
            before=args[kind].stat();code,_=self.cli(world,args)
            self.assertEqual(code,1);self.assertFalse(world.trace);self.assertEqual(before.st_mtime_ns,args[kind].stat().st_mtime_ns)

    def test_help_import_and_cli_do_not_offer_retry_resources_or_backend(self):
        root=Path(__file__).resolve().parents[2]
        code='import sys; from lutphoto import captureprobe; assert not any(n=="usb" or n.startswith("usb.") or n=="libusb_package" for n in sys.modules)'
        run=subprocess.run([sys.executable,'-S','-B','-c',code],cwd=root,capture_output=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stderr)
        help=subprocess.run([sys.executable,'-S','-B','-m','lutphoto.captureprobe','--help'],cwd=root,capture_output=True,timeout=10)
        self.assertEqual(help.returncode,0,help.stderr)
        for argv in ([],['--retry'],['--resources'],['--backend','own']):
            with contextlib.redirect_stdout(io.StringIO()) as out:code=p.main(argv)
            self.assertEqual(code,2);self.assertEqual(json.loads(out.getvalue())['phase'],'INVALID_ARGUMENTS')


if __name__=='__main__':unittest.main()
