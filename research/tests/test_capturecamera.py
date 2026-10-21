"""Public capture frontend on the existing self-made SDK/OS only."""
import contextlib
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import capturecamera as c, captureexecution as x, captureevidence as e, captureowned as o
from lutphoto.capturestore import encoded
from research.tests import test_captureowned as fixtures
from research.tests.native_sdk_fixture import World


class CameraTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.OwnedTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.fixture,self.root,self.files=f,f.root,f.files
        self.policy=replace(o.programidentity._load_policy('own'),commit='aa'*20)
        self.env={'macos':True,'python_supported':True,'administrator_context_present':True,
                  'machine':'arm64','dependencies_match':True,'dependency_versions':dict(x.capturepreflight.EXPECTED)}

    @contextlib.contextmanager
    def bound(self,world,*,env=None):
        prepare=x._prepare
        def prepared(*args,**kwargs):
            value=prepare(*args,**kwargs)
            world.system.service_device._requests=value.channel.requests
            return value
        with world.bound(),patch.object(o.programidentity,'_load_policy',return_value=self.policy),\
             patch.object(x.capturepreflight,'_environment',return_value=self.env if env is None else env),\
             patch.object(o.m._NativeOps,'__new__',return_value=world.ops),\
             patch.object(o.m._NativeOps,'__init__',return_value=None),patch.object(x,'_prepare',side_effect=prepared):
            yield

    def args(self,name='camera',**changes):
        result=dict(archive='own',directory=self.root/name,receipt=self.root/(name+'.private.json'),
                    model='ILCE-7CM2',firmware='2.01',battery_percent=75,resources=False)
        result.update(changes);return result

    def cli(self,args):
        result=['capture']
        for name in ('archive','directory','receipt','model','firmware','battery_percent'):
            result.extend(('--'+name.replace('_','-'),str(args[name])))
        if args['resources']:result.append('--resources')
        return result

    def run_cli(self,world,args,*,env=None,output=None):
        output=io.StringIO() if output is None else output
        with self.bound(world,env=env),contextlib.redirect_stdout(output):code=c.main(self.cli(args))
        return code,output

    def test_public_api_fixed_assembly_saves_private_receipt_and_all_materials(self):
        for resources in (False,True):
            files=self.files|({'resources/'+n:o.s.c.synthetic_resource(False) for n in o.s.c.RESOURCE_FILES} if resources else {})
            world=World(self.fixture.system(files=files));args=self.args('core' if not resources else 'resources',resources=resources)
            with self.bound(world):receipt=c.capture(**args)
            self.assertEqual(receipt['phase'],'CAPTURE_COMPLETE');self.assertEqual(receipt['context']['execution_kind'],'native')
            self.assertEqual(args['receipt'].stat().st_mode&0o777,0o600)
            self.assertEqual(json.loads(args['receipt'].read_bytes()),receipt)
            self.assertEqual(e.inspect_directory(args['directory'],receipt=args['receipt'])['classification'],'CONSISTENT_CAPTURE_RECORDS')
            checkpoint=json.loads((args['directory']/e.CHECKPOINT).read_bytes());self.assertEqual(len(checkpoint['files']),74 if resources else 6)
            self.assertFalse(world.system.acquired);self.assertEqual(world.system.counts['dispose'],3)

    def test_cli_success_outputs_summary_only_after_receipt_and_scopes_are_closed(self):
        world=World(self.fixture.system());args=self.args();before={n:signal.getsignal(n) for n in (signal.SIGINT,signal.SIGTERM)}
        test=self
        class Output(io.StringIO):
            def write(self,raw):
                test.assertFalse(world.system.acquired);test.assertTrue(all(h.closed for h in world.system.handles))
                test.assertEqual(before,{n:signal.getsignal(n) for n in before})
                test.assertEqual(e._read_receipt(args['receipt'])['phase'],'CAPTURE_COMPLETE')
                return super().write(raw)
        code,output=self.run_cli(world,args,output=Output());value=json.loads(output.getvalue())
        self.assertEqual(code,0);self.assertEqual(value['phase'],'CAPTURE_COMPLETE');self.assertTrue(value['receipt_saved'])
        for private in (str(self.root),'serial_sha256','job_id','archive_sha256'):self.assertNotIn(private,output.getvalue())

    def test_known_content_rejection_and_unknown_response_preserve_failure_receipts(self):
        cases=({'files':self.files|{'appFw.so':bytes(len(self.files['appFw.so']))}},
               {'service_options':{'faults':{('write',8):None}}})
        for index,options in enumerate(cases):
            world=World(self.fixture.system(**options));args=self.args('failure'+str(index));code,output=self.run_cli(world,args)
            self.assertEqual(code,1);value=json.loads(output.getvalue());self.assertEqual(value['phase'],'NEEDS_REVIEW')
            self.assertTrue(value['receipt_saved']);self.assertNotIn('wire:read:cpapp-b.bin',world.system.peer.trace)
            self.assertEqual(world.system.service_device.counts['control'],2 if index==0 else 1)
            checked=e.inspect_directory(args['directory'],receipt=args['receipt'])
            self.assertEqual(checked['classification'],'NEEDS_REVIEW_INCOMPLETE' if index==0 else 'NEEDS_REVIEW_UNKNOWN')

    def test_invalid_declarations_refuse_before_source_paths_outputs_or_native_constructor(self):
        class Poison:
            def __fspath__(self):raise AssertionError('No path access')
        for changed in ({'model':'ILCE-7CR'},{'firmware':'2.00'},{'battery_percent':49},{'battery_percent':True},{'resources':1}):
            args=self.args(archive=Poison(),directory=Poison(),receipt=Poison());args.update(changed)
            with patch.object(o.m._NativeOps,'__init__',side_effect=AssertionError('No native constructor')):
                with self.assertRaises(c.CaptureFailure) as error:c.capture(**args)
            self.assertEqual(error.exception.phase,'REFUSED_BEFORE_DEVICE');self.assertFalse(error.exception.started)

    def test_invalid_cli_arguments_are_bounded_and_have_exit_two(self):
        args=self.cli(self.args());cases=[[],['capture'],args+['--enable'],args+['--ops','own'],args+['--resume']]
        cases.append([s for s in args if s not in ('--model','ILCE-7CM2')])
        invalid=args.copy();invalid[invalid.index('--battery-percent')+1]=str(self.root);cases.append(invalid)
        with patch.object(x,'_prepare',side_effect=AssertionError('No source work')):
            for argv in cases:
                output=io.StringIO()
                with contextlib.redirect_stdout(output):code=c.main(argv)
                self.assertEqual(code,2);self.assertEqual(json.loads(output.getvalue())['phase'],'INVALID_ARGUMENTS')
                self.assertNotIn(str(self.root),output.getvalue())

    def test_environment_permission_and_dependency_failures_create_no_receipt_or_job(self):
        for key in ('macos','python_supported','dependencies_match','administrator_context_present'):
            world=World(self.fixture.system());args=self.args(key);code,output=self.run_cli(world,args,env=self.env|{key:False})
            self.assertEqual(code,1);self.assertEqual(json.loads(output.getvalue())['phase'],'REFUSED_BEFORE_DEVICE')
            self.assertFalse(world.trace);self.assertFalse(args['receipt'].exists());self.assertFalse(args['directory'].exists())

    def test_source_failure_has_no_receipt_or_native_construction_and_no_path_in_error(self):
        args=self.args();world=World(self.fixture.system())
        with patch.object(x.capturepreflight.capturemsc,'verify_sources',side_effect=ValueError(str(self.root))):
            code,output=self.run_cli(world,args)
        self.assertEqual(code,1);self.assertNotIn(str(self.root),output.getvalue());self.assertFalse(world.trace)
        self.assertFalse(args['receipt'].exists());self.assertFalse(args['directory'].exists())

    def test_existing_receipt_and_job_are_never_overwritten_or_reused(self):
        for kind in ('receipt','directory'):
            args=self.args(kind);world=World(self.fixture.system())
            if kind=='receipt':args[kind].write_bytes(b'owner-existing');args[kind].chmod(0o600)
            else:args[kind].mkdir(mode=0o700)
            before=args[kind].stat()
            code,output=self.run_cli(world,args);self.assertEqual(code,1);self.assertFalse(world.trace)
            after=args[kind].stat();self.assertEqual((before.st_ino,before.st_mtime_ns),(after.st_ino,after.st_mtime_ns))
            if kind=='receipt':self.assertEqual(args[kind].read_bytes(),b'owner-existing')

    def test_receipt_alias_inside_job_shared_parent_or_symlink_refused_before_sdk(self):
        for kind in ('same','case-alias','inside','shared','symlink'):
            args=self.args(kind);world=World(self.fixture.system())
            if kind=='same':args['receipt']=args['directory']
            elif kind=='case-alias':args['receipt']=self.root/kind.upper()
            elif kind=='inside':args['receipt']=args['directory']/'receipt.json'
            elif kind=='shared':
                parent=self.root/'shared-parent';parent.mkdir(mode=0o755);args['receipt']=parent/'new.json'
            else:
                target=self.root/'owner-file';target.write_bytes(b'owner');args['receipt'].symlink_to(target)
            code,_=self.run_cli(world,args);self.assertEqual(code,1,kind);self.assertFalse(world.trace,kind)
            self.assertFalse(args['directory'].exists(),kind)

    def test_receipt_reservation_sync_failure_stops_before_native_construction(self):
        args=self.args();world=World(self.fixture.system())
        with patch.object(os,'fsync',side_effect=OSError('Own sync failure')):code,output=self.run_cli(world,args)
        self.assertEqual(code,1);self.assertEqual(json.loads(output.getvalue())['phase'],'REFUSED_BEFORE_DEVICE')
        self.assertFalse(world.trace);self.assertEqual(args['receipt'].read_bytes(),b'');self.assertFalse(args['directory'].exists())
        args=self.args('constructor-close');world=World(self.fixture.system());parent=c._parent;close=os.close;parents=[]
        def opened(path):
            value=parent(path);parents.append(value[1]);return value
        def failed(fd):
            close(fd)
            if parents and fd==parents[0]:raise OSError('Own job parent close')
            if len(parents)>1 and fd==parents[1]:raise TimeoutError('Own receipt parent close')
        with patch.object(c,'_parent',opened),patch.object(os,'close',failed):code,output=self.run_cli(world,args)
        value=json.loads(output.getvalue());self.assertEqual(code,1);self.assertFalse(world.trace)
        self.assertEqual(value['reason_type'],'OSError');self.assertIn('TimeoutError',value['secondary_error_types'])

    def test_receipt_is_active_until_verified_and_closed(self):
        args=self.args();world=World(self.fixture.system());save=c._Receipt.save;seen=[]
        def checked(destination,value):
            save(destination,value)
            with self.assertRaises(e.i._Refused) as error:e._read_receipt(args['receipt'])
            self.assertEqual(str(error.exception),'ACTIVE_RECEIPT');seen.append(True)
        with patch.object(c._Receipt,'save',checked):code,_=self.run_cli(world,args)
        self.assertEqual(code,0);self.assertEqual(seen,[True]);self.assertEqual(e._read_receipt(args['receipt'])['phase'],'CAPTURE_COMPLETE')

    def test_receipt_partial_write_and_close_failure_return_non_success_without_retry(self):
        args=self.args();world=World(self.fixture.system());close=c._Receipt.close
        def failed_save(destination,value):os.write(destination.fd,b'{');raise OSError('Own partial write')
        def failed_close(destination):close(destination);raise TimeoutError('Own close uncertainty')
        with patch.object(c._Receipt,'save',failed_save),patch.object(c._Receipt,'close',failed_close):code,output=self.run_cli(world,args)
        value=json.loads(output.getvalue());self.assertEqual(code,1);self.assertFalse(value['receipt_saved'])
        self.assertEqual(value['reason_type'],'OSError');self.assertTrue(value['camera_session_may_have_started'])
        self.assertIn('TimeoutError',value['secondary_error_types'])
        self.assertEqual(args['receipt'].read_bytes(),b'{');self.assertEqual(world.system.counts['dispose'],3)

    def test_stdout_partial_write_after_capture_returns_one_and_preserves_receipt(self):
        class Partial(io.StringIO):
            def write(self,raw):super().write(raw[:7]);return 7
        args=self.args();world=World(self.fixture.system());error=io.StringIO()
        with contextlib.redirect_stderr(error):code,output=self.run_cli(world,args,output=Partial())
        self.assertEqual(code,1);failure=json.loads(error.getvalue());self.assertEqual(failure['phase'],'OUTPUT_UNCONFIRMED')
        self.assertTrue(failure['receipt_saved']);self.assertEqual(e._read_receipt(args['receipt'])['phase'],'CAPTURE_COMPLETE')
        self.assertEqual(world.system.counts['dispose'],3);self.assertNotIn('CAPTURE_COMPLETE',output.getvalue())

    def test_stdout_flush_failure_after_capture_is_not_success(self):
        class FailedFlush(io.StringIO):
            calls=0
            def flush(self):
                self.calls+=1
                if self.calls>1:raise BrokenPipeError('Own pipe')
        args=self.args();world=World(self.fixture.system());error=io.StringIO()
        with contextlib.redirect_stderr(error):code,_=self.run_cli(world,args,output=FailedFlush())
        self.assertEqual(code,1);self.assertEqual(json.loads(error.getvalue())['phase'],'OUTPUT_UNCONFIRMED')
        self.assertEqual(e._read_receipt(args['receipt'])['phase'],'CAPTURE_COMPLETE')

    def test_known_closed_stdout_refuses_before_output_reservation(self):
        class Unwritable(io.StringIO):
            def writable(self):return False
        args=self.args();world=World(self.fixture.system());code,output=self.run_cli(world,args,output=Unwritable())
        self.assertEqual(code,1);self.assertFalse(world.trace);self.assertFalse(args['receipt'].exists())
        self.assertEqual(json.loads(output.getvalue())['phase'],'REFUSED_BEFORE_DEVICE')

    def test_import_and_help_under_no_site_have_no_sdk_or_signal_side_effect(self):
        root=Path(__file__).resolve().parents[2]
        script="import signal,sys; old=signal.getsignal(signal.SIGINT); from lutphoto import capturecamera; assert signal.getsignal(signal.SIGINT) is old; assert not any(n=='usb' or n.startswith('usb.') or n=='libusb_package' for n in sys.modules); print('PASS')"
        imported=subprocess.run([sys.executable,'-S','-B','-c',script],capture_output=True,text=True,cwd=root,timeout=10)
        self.assertEqual(imported.returncode,0,imported.stderr);self.assertEqual(imported.stdout,'PASS\n')
        help_result=subprocess.run([sys.executable,'-S','-B','-m','lutphoto.capturecamera','--help'],capture_output=True,text=True,cwd=root,timeout=10)
        self.assertEqual(help_result.returncode,0,help_result.stderr);self.assertIn('capture',help_result.stdout)

    def test_real_cli_rejects_200_and_broken_pipe_never_starts_device_work(self):
        args=self.args();args['firmware']='2.00';root=Path(__file__).resolve().parents[2]
        command=[sys.executable,'-u','-S','-B','-m','lutphoto.capturecamera',*self.cli(args)]
        completed=subprocess.run(command,capture_output=True,text=True,cwd=root,timeout=10)
        self.assertEqual(completed.returncode,1);self.assertEqual(json.loads(completed.stdout)['phase'],'REFUSED_BEFORE_DEVICE')
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=root)
        process.stdout.close()
        _,error=process.communicate(timeout=10)
        self.assertNotEqual(process.returncode,0);self.assertEqual(json.loads(error)['phase'],'OUTPUT_UNCONFIRMED')
        self.assertFalse(args['directory'].exists());self.assertFalse(args['receipt'].exists())

    def test_public_child_signals_keep_receipt_lease_and_job_during_configuration_and_material(self):
        from research.tests import test_capturesignals as s
        helper=s.SignalProcessTests(methodName='runTest');helper.root=self.root
        helper.exercise('configuration',signal.SIGINT,public=True)
        helper.exercise('material',signal.SIGTERM,public=True)

    def test_public_child_signals_during_stop_and_disposal_preserve_failed_receipt(self):
        from research.tests import test_capturesignals as s
        helper=s.SignalProcessTests(methodName='runTest');helper.root=self.root
        helper.exercise('stop',signal.SIGTERM,public=True)
        helper.exercise('dispose',signal.SIGINT,public=True)


if __name__=='__main__':unittest.main()
