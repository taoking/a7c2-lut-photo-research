"""Read-only, explicit local source/environment/destination checks; no device.

No USB/SDK import, lock, directory creation, native call or permission change.
Passing this inspection never authorizes or enables camera capture.
"""
import argparse
import importlib.metadata
import json
import os
import platform
import re
import sys

from . import capturemsc, programidentity, customcontracts as c
from .capturestore import _parent

EXPECTED={'pyusb':'1.3.1','libusb-package':'1.0.30.0'}


def _environment():
    versions={}
    for package in EXPECTED:
        try:value=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:value=None
        versions[package]=value if type(value) is str and re.fullmatch(r'[0-9][A-Za-z0-9.+-]{0,63}',value) else None
    machine=platform.machine()
    return {'macos':sys.platform=='darwin','python_supported':sys.version_info[:2]>=(3,12),
            'machine':machine if machine in ('arm64','x86_64') else 'other',
            'administrator_context_present':os.geteuid()==0,'dependency_versions':versions,
            'dependencies_match':versions==EXPECTED}


def inspect(archive,directory,*,resources=False):
    """Inspect ONE explicit new output name without creating it or any locks."""
    if type(resources) is not bool:raise TypeError('Explicit resource selection required')
    pin,_=capturemsc.verify_sources(archive)
    policy=programidentity._load_policy(archive);stock,=(p for p in policy.sources if p.kind=='stock')
    # Same material/storage reservation as the coordinator; no space is reserved.
    from . import bk4
    required=stock.ap_bytes+stock.cp_bytes+4*bk4.MAX_SNAPSHOT+2048*16384+131072
    if resources:required+=68*c.MAX_RESOURCE
    path,parent=_parent(directory)
    try:
        try:os.stat(path.name,dir_fd=parent,follow_symlinks=False)
        except FileNotFoundError:pass
        else:raise FileExistsError('New output directory required')
        info=os.fstatvfs(parent)
        space=info.f_frsize>0 and info.f_bavail>=0 and info.f_bavail*info.f_frsize>=required
    finally:os.close(parent)
    environment=_environment();issues=[]
    if not environment['macos']:issues.append('MACOS_REQUIRED_FOR_FUTURE_DEVICE_ENTRY')
    if not environment['python_supported']:issues.append('RESEARCH_PYTHON_UNSUPPORTED')
    if not environment['dependencies_match']:issues.append('PINNED_NATIVE_DEPENDENCIES_DIFFER')
    if not space:issues.append('INSUFFICIENT_CURRENT_FREE_SPACE')
    return {'schema':'a7c2-offline-capture-preflight/1','private_report':True,
        'phase':'OFFLINE_PREFLIGHT_INCOMPLETE' if issues else 'OFFLINE_PREFLIGHT_CHECKED',
        'source_archive_verified':True,'commit':pin['commit'],'archive_sha256':pin['archive_sha256'],
        'environment':environment,'new_output_name_checked':True,'required_storage_bytes':required,'current_free_space_sufficient':space,
        'issues':issues,'camera_operations_performed':False,'global_camera_lock_acquired':False,'job_directory_created':False,
        'sdk_imported_or_loaded':False,'native_management_interruptible':False,'live_capture_enabled':False,
        'camera_version_verified':False,'battery_verified':False,'program_fingerprints_verified':False,
        'physical_port_verified':False,'device_permissions_verified':False,'restore_verified':False,'write_plan_enabled':False,
        'missing_device_evidence':['actual-version-and-battery','normal-protocol-identity','physical-port-and-permissions',
                                   'stock-full-program-fingerprints','native-management-and-response-profile-validation']}


def main(argv=None):
    parser=argparse.ArgumentParser(prog='python -m lutphoto.capturepreflight',description='Read-only local checks; never connects to a camera')
    parser.add_argument('--archive',required=True);parser.add_argument('--directory',required=True)
    parser.add_argument('--resources',action='store_true');args=parser.parse_args(argv)
    try:result=inspect(args.archive,args.directory,resources=args.resources)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        result={'schema':'a7c2-offline-capture-preflight/1','private_report':True,'phase':'REFUSED','reason_type':type(exc).__name__,
                'camera_operations_performed':False,'live_capture_enabled':False,'write_plan_enabled':False}
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0 if result['phase']=='OFFLINE_PREFLIGHT_CHECKED' else 1


if __name__=='__main__':raise SystemExit(main())
