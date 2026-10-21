"""Pure host checks, explicit temporary destination; no USB/native imports."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from lutphoto import capturepreflight as p
from research.tests import test_captureowned as fixtures

ENV={'macos':True,'python_supported':True,'machine':'arm64','administrator_context_present':False,
     'dependency_versions':dict(p.EXPECTED),'dependencies_match':True}


class PreflightTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.OwnedTests(methodName='runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.root=fixture.root
        self.environment=patch.object(p,'_environment',return_value=ENV.copy());self.environment.start();self.addCleanup(patch.stopall)

    def test_check_does_not_create_destination_or_enable_capture(self):
        target=self.root/'new';before=set(self.root.iterdir());result=p.inspect('own',target)
        self.assertEqual(result['phase'],'OFFLINE_PREFLIGHT_CHECKED');self.assertFalse(target.exists());self.assertEqual(set(self.root.iterdir()),before)
        for key in ('camera_operations_performed','global_camera_lock_acquired','job_directory_created','sdk_imported_or_loaded',
                    'native_management_interruptible','live_capture_enabled','camera_version_verified','battery_verified',
                    'program_fingerprints_verified','physical_port_verified','device_permissions_verified','restore_verified','write_plan_enabled'):
            self.assertIs(result[key],False)
        self.assertNotIn(str(target),json.dumps(result));self.assertTrue(result['missing_device_evidence'])

    def test_existing_directory_and_file_refused_without_changes(self):
        for isdir in (True,False):
            target=self.root/str(isdir)
            if isdir:target.mkdir(mode=0o700)
            else:target.write_bytes(b'own contents')
            before=target.stat()
            with self.assertRaises(FileExistsError):p.inspect('own',target)
            self.assertEqual(target.stat().st_mtime_ns,before.st_mtime_ns)

    def test_symlink_output_name_refused_without_reading_target(self):
        source=self.root/'source';source.write_bytes(b'own secret');target=self.root/'link';target.symlink_to(source)
        with self.assertRaises(FileExistsError):p.inspect('own',target)
        self.assertEqual(source.read_bytes(),b'own secret')

    def test_repository_destination_refused(self):
        with self.assertRaises(ValueError):p.inspect('own',Path(p.__file__).resolve().parents[1]/'must-not-exist')

    def test_missing_parent_not_created(self):
        with self.assertRaises(FileNotFoundError):p.inspect('own',self.root/'missing'/'new')
        self.assertFalse((self.root/'missing').exists())

    def test_source_failure_precedes_destination_open(self):
        with patch.object(p.capturemsc,'verify_sources',side_effect=ValueError('own source mismatch')),patch.object(p,'_parent') as parent:
            with self.assertRaises(ValueError):p.inspect('own',self.root/'new')
        parent.assert_not_called()

    def test_wrong_dependencies_report_incomplete_without_installing(self):
        environment=ENV|{'dependencies_match':False,'dependency_versions':{'pyusb':None,'libusb-package':None}}
        with patch.object(p,'_environment',return_value=environment):result=p.inspect('own',self.root/'new')
        self.assertEqual(result['phase'],'OFFLINE_PREFLIGHT_INCOMPLETE');self.assertIn('PINNED_NATIVE_DEPENDENCIES_DIFFER',result['issues'])
        self.assertFalse(result['live_capture_enabled'])

    def test_macos_python_and_space_are_separate_findings(self):
        environment=ENV|{'macos':False,'python_supported':False}
        with patch.object(p,'_environment',return_value=environment),patch.object(p.os,'fstatvfs',return_value=NS(f_frsize=1,f_bavail=1)):
            result=p.inspect('own',self.root/'new')
        self.assertEqual(result['issues'],['MACOS_REQUIRED_FOR_FUTURE_DEVICE_ENTRY','RESEARCH_PYTHON_UNSUPPORTED','INSUFFICIENT_CURRENT_FREE_SPACE'])

    def test_resources_reserve_additional_bytes(self):
        one=p.inspect('own',self.root/'first');two=p.inspect('own',self.root/'second',resources=True)
        self.assertEqual(two['required_storage_bytes']-one['required_storage_bytes'],68*p.c.MAX_RESOURCE)

    def test_cli_refusal_json_does_not_leak_path_or_exception(self):
        stream=io.StringIO()
        with patch.object(p.capturemsc,'verify_sources',side_effect=OSError('own private /forbidden/path')),contextlib.redirect_stdout(stream):
            result=p.main(['--archive','own','--directory',str(self.root/'new')])
        self.assertEqual(result,1);report=json.loads(stream.getvalue());self.assertEqual(report['reason_type'],'OSError')
        self.assertNotIn('/forbidden',stream.getvalue());self.assertNotIn(str(self.root),stream.getvalue())

    def test_cli_checked_and_incomplete_exit_codes(self):
        for ok in (True,False):
            with patch.object(p,'_environment',return_value=ENV|{'dependencies_match':ok}),contextlib.redirect_stdout(io.StringIO()) as stream:
                code=p.main(['--archive','own','--directory',str(self.root/'new')])
            self.assertEqual(code,0 if ok else 1);self.assertFalse(json.loads(stream.getvalue())['live_capture_enabled'])

    def test_metadata_probe_does_not_import_sdk(self):
        self.environment.stop()
        with patch.object(p.importlib.metadata,'version',side_effect=lambda package:p.EXPECTED[package]):result=p._environment()
        self.assertTrue(result['dependencies_match']);self.assertFalse(any(n=='usb' or n.startswith('usb.') or n=='libusb_package' for n in sys.modules))

    def test_metadata_missing_or_unexpected_text_not_reflected(self):
        self.environment.stop()
        for error in (p.importlib.metadata.PackageNotFoundError(),'/private/location'):
            kw={'side_effect':error} if isinstance(error,BaseException) else {'return_value':error}
            with patch.object(p.importlib.metadata,'version',**kw):result=p._environment()
            self.assertFalse(result['dependencies_match']);self.assertEqual(set(result['dependency_versions'].values()),{None})

    def test_import_under_no_site_never_loads_usb(self):
        result=subprocess.run([sys.executable,'-S','-B','-c',
            'from lutphoto import capturepreflight; import sys; assert not any(n=="usb" or n.startswith("usb.") or n=="libusb_package" for n in sys.modules)'],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())
