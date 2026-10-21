"""Reviewable coordinator with native-shaped FAKE operations only.

No native SDK import/constructor, live adapter or device CLI. The fake OS
schedules arrivals; the coordinator only observes them through inventory.
Fixed QAQLeonard/ma1co/ajalt sources: ACKNOWLEDGEMENTS.md.
"""
import argparse
import hashlib
import json

from . import captureowned as o, captureinspect, capturemsc, programidentity
from .captureprotocol import OfflineChannel


class NativeCandidateBlocked(RuntimeError):
    pass


def capture(*args,**kwargs):
    """Unconditional stop before inspecting arguments, files or any SDK."""
    raise NativeCandidateBlocked('Live capture is not enabled')


class _CandidateOps:
    """Exact own fake OS; finite methods matching the native host capability.

    This is not an SDK wrapper. Arrival scheduling belongs to this fake world,
    never to the coordinator, an external callback or an actual USB device.
    """
    def __init__(self,system):
        if type(system) is not o.SyntheticSystem:raise TypeError('Exact fake OS required')
        self.system=system

    def clock(self):return self.system.clock()
    def sleep(self,seconds):return self.system.sleep(seconds)
    def acquire(self):return self.system.acquire()
    def unlock(self,fd):return self.system.unlock(fd)
    def inventory(self):
        s=self.system
        if s.phase==0 and s.handles[0].closed and s.normal_device.auth.used==15:s.phase=1
        elif s.phase==1 and s.handles[1].closed and s.service_device.auth.used==16:
            s.phase=2;s.mounted=True
        return s.inventory()
    def media(self,seconds):return self.system.media(seconds)
    def unmount(self,disk,seconds):return self.system.unmount(disk,seconds)
    def open(self,key):return self.system.open(key)
    def descriptor(self,device):return self.system.descriptor(device)
    def active(self,d):return self.system.active(d)
    def detach(self,d):return self.system.detach(d)
    def attach(self,d):return self.system.attach(d)
    def claim(self,d):return self.system.claim(d)
    def release(self,d):return self.system.release(d)
    def dispose(self,d):return self.system.dispose(d)
    def control(self,d,request_type,request,value,index,raw,timeout):
        return self.system.control(d,request_type,request,value,index,raw,timeout)
    def write(self,d,ep,data,timeout):return self.system.write(d,ep,data,timeout)
    def read(self,d,ep,size,timeout):return self.system.read(d,ep,size,timeout)


class _NativeRun(o._Run):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        # No cached peer observation or synthetic arrival capability in flow.
        self.peer=self.system=None

    def preflight(self,resources):
        super().preflight(resources)
        self.event('NATIVE_BINDING_CANDIDATE_MODELED',binding='native-shaped-fake-ops',live_execution_enabled=False)

    def arrive_service(self):pass
    def arrive_normal(self):pass


def rehearse(archive,directory,system,*,resources=False,cancel=None):
    """Exact fresh fake input only; no ops/runner override in public API."""
    cancel,policy,channel=o._prepare(archive,system,resources,cancel)
    host=o.m._Host(_CandidateOps(system),None,firmware=system.peer.version,battery_percent=system.peer.battery,
                   budget=channel.budget,cancel=cancel,wait=True)
    return o._execute(archive,directory,system,host,channel,policy,resources=resources,run_type=_NativeRun)


def review(archive,*,resources=False):
    """Read pinned sources and describe frozen scope. Never grants execution."""
    if type(resources) is not bool:raise TypeError('Explicit resource selection required')
    pin,_=capturemsc.verify_sources(archive)
    policy=programidentity._load_policy(archive)
    stock,=(s for s in policy.sources if s.kind=='stock')
    channel=OfflineChannel(archive,resources=resources,guards=True)
    requests=[{'operation':name,'pfunc':spec.pfunc,'request_bytes':len(spec.data),
               'request_sha256':hashlib.sha256(spec.data).hexdigest(),'payload_limit':spec.limit,
               'payload_exact':spec.exact} for name,spec in sorted(channel.requests.items())]
    return {'schema':'a7c2-native-capture-candidate-review/1','phase':'NATIVE_CANDIDATE_BLOCKED',
        'private_report':True,'source_archive_verified':True,'commit':pin['commit'],'archive_sha256':pin['archive_sha256'],
        'requirements':{'model':'ILCE-7CM2','firmware':'2.01','source_kind':'stock','minimum_battery_percent':50,
                        'full_program_fingerprints_required':True,'ap_bytes':stock.ap_bytes,'cp_bytes':stock.cp_bytes},
        'saved_materials':list(captureinspect.CORE)+(['resources/'+n for n in o.s.c.RESOURCE_FILES] if resources else []),
        'resource_extension_requested':resources,'guard_names':list(channel.guard_names),
        'fixed_request_count':len(requests),'fixed_requests':requests,
        'phases':['fixed-source-and-local-preflight','global-lease-then-new-private-job',
                  'normal-msc-identity-and-auth','close-normal-then-passive-service-wait',
                  'service-auth-and-absence-guards','full-stock-programs-before-settings',
                  'settings-and-optional-resources','repeat-programs-resources-settings-and-guards',
                  'one-known-healthy-stop','close-service-then-passive-normal-wait',
                  'fresh-normal-msc-identity-match','close-handles-then-report-job-and-global-release'],
        'unknown_result_policy':'stop-no-retry-reset-or-additional-protocol-command',
        'blocking_sdk_policy':'cooperative-checks-only-retain-active-job-and-owners-until-call-returns',
        'temporary_device_state_changes':['service-authentication','selected-read-path'],
        'excluded_device_actions':['module-upload-or-execution','file-upload-or-delete','settings-save',
                                   'firmware-write','wbi','reset-or-force-unmount'],
        'live_execution_enabled':False,'native_management_interruptible':False,'sdk_imported_or_loaded':False,
        'camera_operations_performed':False,'camera_version_verified':False,'battery_verified':False,
        'program_fingerprints_verified':False,'physical_port_verified':False,'device_permissions_verified':False,
        'physical_protocol_verified':False,'restore_verified':False,'write_plan_enabled':False}


def main(argv=None):
    parser=argparse.ArgumentParser(prog='python -m lutphoto.capturecandidate',description='Source-only candidate review; no device entry')
    sub=parser.add_subparsers(dest='command',required=True)
    command=sub.add_parser('review');command.add_argument('--archive',required=True)
    command.add_argument('--resources',action='store_true');args=parser.parse_args(argv)
    try:result=review(args.archive,resources=args.resources)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        result={'schema':'a7c2-native-capture-candidate-review/1','phase':'REFUSED','reason_type':type(exc).__name__,
                'camera_operations_performed':False,'live_execution_enabled':False,'write_plan_enabled':False}
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    # Zero means the source-only review succeeded, never that capture is ready.
    return 0 if result['phase']=='NATIVE_CANDIDATE_BLOCKED' else 1


if __name__=='__main__':raise SystemExit(main())
