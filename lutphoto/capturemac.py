"""Internal macOS ownership binding, reached by the explicit capture entry.

QAQLeonard/ma1co source provenance: capturemsc and ACKNOWLEDGEMENTS.md.
captureexecution constructs NativeOps only after the source/local prerequisites;
capturecamera is the public owner-capture CLI. Import does no host I/O. Fake-API
tests and host library loading do not establish actual camera communication.
"""
import fcntl
import os
import plistlib
import re
import selectors
import stat
import subprocess
import sys
import time
from dataclasses import dataclass

from .capturemsc import _Query
from .capturecontrol import Cancellation, ObservationTimeout
from .capturestore import Budget
from . import capturediagnostics as diagnostics

LOCK = '/var/run/a7c2-fl23-macos.lock'  # Same exclusion domain as the old installer.
NORMAL, SERVICE = 0x0e8a, 0x0336
DISK = re.compile(r'disk[0-9]+(?:s[0-9]+)*\Z')
IOREGISTRY_COMMAND = ('/usr/sbin/ioreg','-p','IOService','-l','-a')
# A real macOS IOService snapshot exceeded 18 MiB. Keep a finite, separate
# host-registry allowance; diskutil and all camera/protocol bounds stay fixed.
IOREGISTRY_MAX_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class _Key:
    pid: int
    bus: int
    ports: tuple
    address: int

    def __post_init__(self):
        if (type(self.pid) is not int or self.pid not in (NORMAL,SERVICE)
                or type(self.bus) is not int or self.bus<=0
                or type(self.ports) is not tuple or not 1<=len(self.ports)<=16
                or any(type(p) is not int or not 1<=p<=255 for p in self.ports)
                or type(self.address) is not int or not 1<=self.address<=127):
            raise ValueError('Explicit USB location required')

    @property
    def location(self):return self.bus,self.ports


def _bounded_command(argv, seconds, limit=8*1024*1024):
    """Fixed callers only; bound combined output while reading, not afterwards."""
    end=time.monotonic()+seconds
    process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    try:
        result=bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout,selectors.EVENT_READ)
            while True:
                remaining=end-time.monotonic()
                if remaining<=0:raise TimeoutError('Host command deadline expired')
                if not selector.select(remaining):raise TimeoutError('Host command deadline expired')
                part=os.read(process.stdout.fileno(),min(65536,limit+1-len(result)))
                if not part:break
                result.extend(part)
                if len(result)>limit:raise ValueError('Host command output exceeded bound')
        code=process.wait(timeout=max(0.001,end-time.monotonic()))
        if code:raise OSError('Host command failed')  # Never expose command output/paths.
        return bytes(result)
    finally:
        if process.poll() is None:process.kill()
        process.wait();process.stdout.close()


def _walk(tree):
    pending=[tree];count=0
    while pending:
        value=pending.pop();count+=1
        if count>100000:raise ValueError('Registry node bound exceeded')
        if type(value) is list:pending.extend(value)
        elif type(value) is dict:
            yield value
            children=value.get('IORegistryEntryChildren',[])
            if type(children) is not list:raise ValueError('Invalid registry children')
            pending.extend(children)


class _NativeOps:
    """Native API binding for the authorized, explicit owner-capture assembly.

    Import and construction do not enumerate USB. _runtime initializes libusb;
    inventory/open subsequently enumerate it. Tests replace runtime/commands;
    their success does not verify real opening, claiming or communication.
    """
    clock=staticmethod(time.monotonic)
    sleep=staticmethod(time.sleep)

    def _runtime(self):
        import sys
        if sys.platform!='darwin' or os.geteuid()!=0:raise PermissionError('macOS administrator context required')
        if getattr(self,'_sdk',None) is None:
            import usb.core
            import usb.util
            import usb.backend.libusb1
            import libusb_package
            backend=usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
            if backend is None:raise RuntimeError('Packaged libusb backend unavailable')
            self._backend,self._sdk=backend,(usb.core,usb.util)
        return self._sdk

    def acquire(self):
        if sys.platform!='darwin' or os.geteuid()!=0:raise PermissionError('macOS administrator lock required')
        fd=os.open(LOCK,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_nlink!=1 or info.st_mode&0o077:
                raise ValueError('Unsafe global camera lock')
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return fd
        except BaseException as error:
            # A failed local close must not replace the original acquisition
            # error. Its completion is not assumed and acquisition is not retried.
            try:os.close(fd)
            except BaseException as cleanup:raise error from cleanup
            raise

    def unlock(self,fd):os.close(fd)  # No unlink/replacement and no authentication changes.

    def command(self,args,seconds):
        allowed=(args==IOREGISTRY_COMMAND
                 or len(args)==4 and args[:3]==('/usr/sbin/diskutil','info','-plist') and DISK.fullmatch(args[3])
                 or len(args)==3 and args[:2]==('/usr/sbin/diskutil','unmountDisk') and re.fullmatch(r'/dev/disk[0-9]+',args[2]))
        if not allowed:raise ValueError('Fixed non-forced host commands only')
        if type(seconds) not in (int,float) or not 0<seconds<=20:raise ValueError('Bounded command duration required')
        if args==IOREGISTRY_COMMAND:
            return _bounded_command(args,seconds,limit=IOREGISTRY_MAX_BYTES)
        return _bounded_command(args,seconds)

    def media(self,seconds):
        end=self.clock()+seconds
        def command(args):
            remaining=end-self.clock()
            if remaining<=0:raise TimeoutError('Media query deadline expired')
            return self.command(args,min(20,remaining))
        tree=plistlib.loads(command(IOREGISTRY_COMMAND))
        targets=[v for v in _walk(tree) if v.get('IOObjectClass')=='IOUSBHostDevice'
                 and v.get('idVendor')==0x054c and v.get('idProduct')==NORMAL]
        if len(targets)!=1 or type(targets[0].get('IORegistryEntryID')) is not int:raise ValueError('Unique registry target required')
        media={}
        for value in _walk(targets[0]):
            if value.get('IOObjectClass')!='IOMedia':continue
            name=value.get('BSD Name')
            if type(name) is not str or not DISK.fullmatch(name) or name in media:raise ValueError('Unique disk identifier required')
            if len(media)>=64:raise ValueError('Media count bound exceeded')
            info=plistlib.loads(command(('/usr/sbin/diskutil','info','-plist',name)))
            if (info.get('DeviceIdentifier')!=name or info.get('Internal') is not False
                    or info.get('OSInternalMedia') is not False or info.get('BusProtocol')!='USB'
                    or type(info.get('WholeDisk')) is not bool):raise ValueError('Verified external USB media required')
            media[name]=(info.get('ParentWholeDisk'),info['WholeDisk'],bool(info.get('MountPoint')))
        if not media or any(parent not in media or media[parent][1] is not True
                            or whole and parent!=name for name,(parent,whole,_) in media.items()):
            raise ValueError('Verified whole camera disks required')
        return targets[0]['IORegistryEntryID'],media

    def unmount(self,disk,seconds):return self.command(('/usr/sbin/diskutil','unmountDisk','/dev/'+disk),seconds)

    def _devices(self):
        core,util=self._runtime();devices=[]
        try:
            for pid in (NORMAL,SERVICE):
                for device in core.find(find_all=True,idVendor=0x054c,idProduct=pid,backend=getattr(self,'_backend',None)):
                    devices.append(device)
                    if len(devices)>16:raise ValueError('USB inventory bound exceeded')
            return devices,util
        except BaseException:
            self._dispose_all(util,devices,suppress=True)
            raise

    @staticmethod
    def _dispose_all(util,devices,*,suppress=False):
        error=None;seen=set()
        for device in devices:
            # Malformed inventories can alias one SDK object. Keep duplicate
            # observations for rejection, but attempt each local disposal once.
            identity=id(device)
            if identity in seen:continue
            seen.add(identity)
            try:
                if util.dispose_resources(device) is not None:raise ValueError('Unconfirmed enumeration disposal')
            except BaseException as exc:
                if error is None:error=exc
        if error is not None and not suppress:raise error

    @staticmethod
    def key(device):
        if device.idVendor!=0x054c:raise ValueError('Sony identity required')
        return _Key(device.idProduct,device.bus,tuple(device.port_numbers or ()),device.address)

    def inventory(self):
        devices,util=self._devices()
        try:result=tuple(self.key(d) for d in devices)
        except BaseException:
            self._dispose_all(util,devices,suppress=True);raise
        self._dispose_all(util,devices);return result

    def open(self,key):
        devices,util=self._devices();selected=None
        try:
            matches=[d for d in devices if self.key(d)==key]
            if len(devices)!=1 or len(matches)!=1:raise ValueError('Fresh unique device required')
            selected=matches[0]
            return selected
        finally:
            self._dispose_all(util,[d for d in devices if d is not selected],suppress=selected is None)

    def descriptor(self,device):
        interface=device.get_active_configuration()[(0,0)]
        return (device.idVendor,device.idProduct,interface.bInterfaceNumber,interface.bAlternateSetting,
                interface.bInterfaceClass,interface.bInterfaceSubClass,interface.bInterfaceProtocol,
                tuple((ep.bEndpointAddress,ep.bmAttributes) for ep in interface))

    def active(self,d):return d.is_kernel_driver_active(0)
    def detach(self,d):return d.detach_kernel_driver(0)
    def attach(self,d):return d.attach_kernel_driver(0)
    def claim(self,d):return self._runtime()[1].claim_interface(d,0)
    def release(self,d):return self._runtime()[1].release_interface(d,0)
    def dispose(self,d):return self._runtime()[1].dispose_resources(d)
    def control(self,d,request_type,request,value,index,raw,timeout):
        return d.ctrl_transfer(request_type,request,value,index,raw,timeout=timeout)
    def write(self,d,ep,data,timeout):return d.write(ep,data,timeout=timeout)
    def read(self,d,ep,size,timeout):return d.read(ep,size,timeout=timeout)


def _profile(value,pid):
    if (type(value) is not tuple or len(value)!=8 or any(type(n) is not int for n in value[:7])
            or value[:4]!=(0x054c,pid,0,0) or any(not 0<=n<=255 for n in value[4:7]) or type(value[7]) is not tuple or len(value[7])!=2
            or (value[4:7]!=(8,6,0x50) if pid==NORMAL else value[4]!=0xff)):
        raise ValueError('Unreviewed interface')
    for ep in value[7]:
        if (type(ep) is not tuple or len(ep)!=2 or any(type(n) is not int for n in ep)
                or ep[1]!=2 or ep[0]&0x70 or not 0<ep[0]<=0x8f or not ep[0]&15):
            raise ValueError('Exact bulk endpoint pair required')
    incoming=[ep[0] for ep in value[7] if ep[0]&0x80];outgoing=[ep[0] for ep in value[7] if not ep[0]&0x80]
    if len(incoming)!=1 or len(outgoing)!=1:raise ValueError('Unique IN/OUT required')
    return incoming[0],outgoing[0]


class _Owner:
    def __init__(self,host,key,device):
        self.host,self.key,self.device=host,key,device
        self.claimed=self.detached=self.unknown=self.transition=self.closed=False
        self.profile=None;self.queried=False
        self.identity_bytes=self.identity_calls=0;self.close_ok=False
        self.identity_diagnostic=None
        self.close_error_types=[]

    def query(self):
        if self.closed or self.unknown or self.transition or not self.claimed or self.queried or self.key.pid!=NORMAL:
            raise RuntimeError('No fresh MSC capability')
        self.queried=True
        def io(kind,value,timeout):
            boundary='OWNER_PRECHECK';returned=None
            try:
                if self.closed or self.unknown or self.host.blocked:raise RuntimeError('Stopped owner')
                self.host.check()
                boundary='DESCRIPTOR_QUERY';profile=self.host.ops.descriptor(self.device)
                boundary='DESCRIPTOR_CHECK'
                if profile!=self.profile:raise ValueError('Descriptor changed')
                boundary='OWNER_PRECHECK';self.host.check()
                fn=self.host.ops.write if kind=='write' else self.host.ops.read
                boundary='SDK_BULK_WRITE' if kind=='write' else 'SDK_BULK_READ'
                result=fn(self.device,self.outgoing if kind=='write' else self.incoming,value,timeout)
                boundary='OWNER_POSTCHECK';returned=diagnostics.returned_size(kind,result)
                self.host.check();return result
            except BaseException as error:
                query.note_failure(error,boundary,returned)
                raise
        query=_Query(lambda value,timeout:io('write',value,timeout),lambda size,timeout:io('read',size,timeout),self.host.budget)
        try:return self.host.step('NORMAL_IDENTITY_QUERY',query.run)
        except BaseException:
            self.unknown=True;raise
        finally:
            self.identity_bytes=query.accepted_bytes;self.identity_calls=query.calls
            if query.failure_attempted:
                self.identity_diagnostic={'failure':query.failure,'record_error_type':query.failure_record_error_type}

    def close(self):
        if self.closed:return
        self.closed=True  # All views invalid BEFORE release/attach/dispose; never retry.
        error=None
        safe=not (self.unknown or self.transition or self.host.blocked or self.host.cancel.requested)
        try:
            if safe and self.claimed:
                self.host.management('RELEASE_INTERFACE',lambda:self.host.ops.release(self.device));self.claimed=False
            if safe and self.detached:
                self.host.management('ATTACH_KERNEL',lambda:self.host.ops.attach(self.device));self.detached=False
        except BaseException as exc:
            error=exc;self.close_error_types.append(type(exc).__name__)
        try:
            # SDK disposal can implicitly release an interface. This is not proof
            # of physical closure or zero USB-stack activity after a disconnect.
            self.host.dispose(self.device)
        except BaseException as exc:
            self.close_error_types.append(type(exc).__name__)
            if error is None:error=exc
        if error is not None:
            self.host.blocked=True;raise error
        self.close_ok=True


class _Host:
    """Internal lifecycle, with global lock before any future job Store lock.

    No authentication or simulated state switch is implemented here. A future
    coordinator must place reviewed auth/material/stop between these stages.
    This partial binding does NOT generate a completed capture report.
    """
    def __init__(self,ops,event,*,firmware,battery_percent,budget=None,cancel=None,wait=False):
        if firmware!='2.01' or type(firmware) is not str or type(battery_percent) is not int or not 50<=battery_percent<=100:
            raise ValueError('Explicit supported version and actual battery prerequisite required')
        self.cancel=Cancellation() if cancel is None else cancel
        if type(self.cancel) is not Cancellation or type(wait) is not bool:raise TypeError('Exact cooperative token and wait mode required')
        self.wait_enabled=wait;self.last_wait_timeout=None
        self.firmware_declared,self.battery_percent_declared=firmware,battery_percent
        self.ops,self.event=ops,event
        self.budget=Budget(65536,seconds=120,clock=ops.clock) if budget is None else budget
        if type(self.budget) is not Budget:raise TypeError('One shared Budget required')
        self.owners=[];self.lock=None;self.blocked=False;self.initial=None;self.stage='NEW';self.used=False
        self.lease_acquired=self.lease_release_confirmed=False
        self.cleanup_error_types=[]
        self.returned_observation=None

    def __enter__(self):
        if self.used:raise RuntimeError('One host lease only')
        self.check();self.used=True;self.lock=self.ops.acquire();self.lease_acquired=True
        try:self.check()
        except BaseException:
            self.blocked=True
            try:self._unlock()
            except BaseException:pass  # Error types remain available to the invocation receipt.
            self.lock=None
            raise
        return self

    def __exit__(self,kind,error,tb):
        cleanup=None
        for owner in reversed(self.owners):
            try:owner.close()
            except BaseException as exc:
                if cleanup is None:cleanup=exc
        try:self._unlock()
        except BaseException as exc:
            self.blocked=True
            if cleanup is None:cleanup=exc
        self.lock=None
        if error is None and cleanup is not None:raise cleanup
        return False

    def _unlock(self):
        try:self.ops.unlock(self.lock)
        except BaseException as error:
            self.cleanup_error_types.append(type(error).__name__);raise
        self.lease_release_confirmed=True

    def check(self):
        self.cancel.check();self.budget.check()

    def step(self,name,action):
        if self.lock is None or self.blocked:raise RuntimeError('Host lease stopped or missing')
        try:
            self.check();self.event('HOST_INTENT',operation=name)
            result=action()
            self.check();self.event('HOST_ACK',operation=name)
            return result
        except BaseException:
            self.blocked=True;raise

    def dispose(self,device):
        # Local cleanup is attempted even if the journal is already broken.
        # Its intent/ACK are separate from protocol stop and never replayed.
        error=None;intent=False;accepted=False
        try:self.event('HOST_INTENT',operation='DISPOSE_RESOURCES');intent=True
        except BaseException as exc:error=exc
        try:
            if self.ops.dispose(device) is not None:raise ValueError('Unconfirmed SDK disposal')
            accepted=True
        except BaseException as exc:
            if error is None:error=exc
        if intent and accepted:
            try:self.event('HOST_ACK',operation='DISPOSE_RESOURCES')
            except BaseException as exc:
                if error is None:error=exc
        if error is not None:self.blocked=True;raise error

    def management(self,name,action):
        def checked():
            result=action()
            if result is not None:raise ValueError('Expected SDK management completion')
        return self.step(name,checked)

    def _seconds(self):
        self.check();return min(20,self.budget.deadline-self.budget.clock())

    def _unique(self,pid,*,expected=None):
        keys=self.step('INVENTORY',self.ops.inventory)
        if type(keys) is not tuple or len(keys)!=1 or type(keys[0]) is not _Key or keys[0].pid!=pid:
            self.blocked=True;raise ValueError('Exactly one expected camera required')
        key=keys[0]
        if expected is not None and key!=expected or self.initial and key.location!=self.initial[0].location:
            self.blocked=True;raise ValueError('Camera location or generation changed')
        return key

    def _wait(self,pid):
        if self.initial is None:raise RuntimeError('Initial same-port identity required')
        phase='service' if pid==SERVICE else 'normal-return'
        end=min(self.budget.deadline,self.ops.clock()+20)
        candidate=None;since=None;polls=0
        try:
            self.check();self.event('HOST_WAIT_BEGIN_MODELED',phase=phase)
            while True:
                self.cancel.check()
                if self.ops.clock()>=end or polls>=40:
                    self.event('HOST_WAIT_END_MODELED',phase=phase,outcome='timed-out',polls=polls)
                    error=ObservationTimeout(phase);self.last_wait_timeout=error;raise error
                self.check()
                keys=self.step('INVENTORY',self.ops.inventory);polls+=1
                if self.ops.clock()>=end:continue
                if (type(keys) is not tuple or len(keys)>1 or any(type(k) is not _Key
                        or k.location!=self.initial[0].location for k in keys)):
                    raise ValueError('Ambiguous or changed-port transition observation')
                key=keys[0] if keys else None
                if key is not None and key.pid==pid:
                    if key!=candidate:candidate,since=key,self.ops.clock()
                    elif self.ops.clock()-since>=.5:
                        self.event('HOST_WAIT_END_MODELED',phase=phase,outcome='found',polls=polls)
                        return key
                else:candidate=since=None  # Only absence/same-port old PID can wait.
                self.ops.sleep(min(.5,end-self.ops.clock()))
        except BaseException:self.blocked=True;raise

    def _media(self,maximum=20):
        if maximum<=0:raise TimeoutError('Media deadline expired')
        return self.step('MEDIA',lambda:self.ops.media(min(maximum,self._seconds())))

    @staticmethod
    def _topology(value):
        registry,media=value
        if type(registry) is not int or type(media) is not dict or not media:raise ValueError('Verified media required')
        for name,row in media.items():
            if (type(name) is not str or not DISK.fullmatch(name) or type(row) is not tuple or len(row)!=3
                    or type(row[0]) is not str or row[0] not in media or type(row[1]) is not bool
                    or type(row[2]) is not bool or media[row[0]][1] is not True or row[1] and row[0]!=name):
                raise ValueError('Verified disk topology required')
        return registry,tuple(sorted((name,*row[:2]) for name,row in media.items()))

    def _unmount(self):
        end=min(self.budget.deadline,self.ops.clock()+20);previous=None;since=None
        while True:
            value=self._media(end-self.ops.clock());now=self.ops.clock();topology=self._topology(value)
            if now>=end:raise TimeoutError('Camera media did not stabilize')
            if topology!=previous:previous,since=topology,now
            elif now-since>=3:break
            if now>=end:raise TimeoutError('Camera media did not stabilize')
            self.ops.sleep(min(.5,end-now));self.check()
        for name,row in sorted(value[1].items()):
            if not row[1]:continue
            if self._topology(self._media())!=previous:raise ValueError('Media changed before unmount')
            self.step('UNMOUNT',lambda:self.ops.unmount(name,self._seconds()))
        current=self._media()
        if self._topology(current)!=previous or any(row[2] for row in current[1].values()):raise ValueError('Media not fully unmounted')

    def _open(self,key):
        def adopt():
            owner=_Owner(self,key,self.ops.open(key));self.owners.append(owner);return owner
        owner=self.step('OPEN_HANDLE',adopt)  # Adopt BEFORE ACK; failed logging still disposes.
        owner.profile=self.step('DESCRIPTOR',lambda:self.ops.descriptor(owner.device))
        owner.incoming,owner.outgoing=_profile(owner.profile,key.pid)
        active=self.step('KERNEL_ACTIVE',lambda:self.ops.active(owner.device))
        if type(active) is not bool or key.pid==SERVICE and active:raise ValueError('Unreviewed kernel driver state')
        if active:
            def detach():
                result=self.ops.detach(owner.device)
                owner.detached=True  # Attempt changes state before ACK, even if result is unreviewed.
                return result
            self.management('DETACH_KERNEL',detach)
        def claim():
            result=self.ops.claim(owner.device);owner.claimed=True;return result
        self.management('CLAIM_INTERFACE',claim)
        return owner

    def normal(self):
        if self.stage!='NEW':raise RuntimeError('Initial query already attempted')
        self.stage='INITIAL_ATTEMPT'
        try:
            key=self._unique(NORMAL);self._unmount();self._unique(NORMAL,expected=key)
            owner=self._open(key);identity=owner.query();self.initial=key,identity;self.stage='NORMAL_OPEN'
            return owner,dict(identity)
        except BaseException:self.blocked=True;raise

    def departing(self,owner):
        """Invalidate after a reviewed transition; sends no command itself."""
        if owner not in self.owners or owner.closed:raise ValueError('Owned current handle required')
        if self.blocked or owner is not self.owners[-1] or self.stage not in ('NORMAL_OPEN','SERVICE_OPEN'):
            raise RuntimeError('No reviewed transition stage')
        owner.transition=True;owner.close()
        self.stage='NORMAL_DEPARTED' if owner.key.pid==NORMAL else 'SERVICE_DEPARTED'

    def service(self):
        if self.stage!='NORMAL_DEPARTED' or any(not o.closed for o in self.owners):raise RuntimeError('Close normal transition owner first')
        try:
            owner=self._open(self._wait(SERVICE) if self.wait_enabled else self._unique(SERVICE));self.stage='SERVICE_OPEN';return owner
        except BaseException:self.blocked=True;raise

    def normal_return(self):
        if self.stage!='SERVICE_DEPARTED' or any(not o.closed for o in self.owners):raise RuntimeError('Close service owner first')
        self.stage='RETURN_ATTEMPT'
        try:
            key=self._wait(NORMAL) if self.wait_enabled else self._unique(NORMAL)
            self._unmount();self._unique(NORMAL,expected=key)
            owner=self._open(key);identity=owner.query()
            if identity!=self.initial[1]:raise ValueError('Fresh normal identity differs')
            self.returned_observation=dict(identity)
            self.stage='RETURN_QUERIED';return dict(identity)
        except BaseException:self.blocked=True;raise
