"""Test-only fake SDK/OS below the EXISTING native methods and coordinator.

No SDK import, native library, system lock, process or USB operation. Runtime,
OS syscalls and command execution are replaced before any native method runs.
This fixture has no CLI and is not imported by shipped lutphoto entry points.
"""
from contextlib import ExitStack,contextmanager
import os
import plistlib
import stat
from types import SimpleNamespace as NS
from unittest.mock import patch

from lutphoto import capturecandidate as candidate, captureowned as owned

m=owned.m


class Device:
    def __init__(self,world,key):
        self.world,self.key=world,key
        self.idVendor,self.idProduct=0x054c,key.pid
        self.bus,self.port_numbers,self.address=key.bus,key.ports,key.address
        self.phase=world.system.phase;self.opened=self.disposed=self.claimed=False
        self.dispose_attempts=0

    def ready(self):
        if self.disposed:raise AssertionError('No use of disposed fake SDK object')

    @property
    def handle(self):return self.world.system.handles[self.phase]

    @property
    def endpoints(self):
        # Returned-normal fixture has an MSC tape and no auth/material object.
        return ((129,2),(2,2)) if self.handle.protocol is None else self.handle.protocol.descriptor[7]

    def get_active_configuration(self):
        self.ready()
        if not self.opened:self.opened=True;self.world.record('lazy-open',self)
        self.world.record('configuration',self)
        p=self.world.system.descriptor(self.handle)
        interface=NS(bInterfaceNumber=p[2],bAlternateSetting=p[3],bInterfaceClass=p[4],
                     bInterfaceSubClass=p[5],bInterfaceProtocol=p[6])
        return Configuration(interface,tuple(NS(bEndpointAddress=a,bmAttributes=b) for a,b in p[7]))

    def is_kernel_driver_active(self,interface):
        self.ready();assert interface==0;return self.world.system.active(self.handle)
    def detach_kernel_driver(self,interface):
        self.ready();assert interface==0;return self.world.system.detach(self.handle)
    def attach_kernel_driver(self,interface):
        self.ready();assert interface==0;return self.world.system.attach(self.handle)
    def ctrl_transfer(self,*request,timeout):
        self.ready();assert self.claimed;self.world.record('control',self)
        return self.world.system.control(self.handle,*request,timeout)
    def write(self,endpoint,raw,*,timeout):
        self.ready();assert self.claimed and type(timeout) is int and 0<timeout<=5000
        assert endpoint==next(ep for ep,kind in self.endpoints if not ep&0x80)
        self.world.record('write',self)
        return self.world.system.write(self.handle,endpoint,raw,timeout)
    def read(self,endpoint,size,*,timeout):
        self.ready();assert self.claimed and type(timeout) is int and 0<timeout<=5000
        assert endpoint==next(ep for ep,kind in self.endpoints if ep&0x80)
        self.world.record('read',self)
        return self.world.system.read(self.handle,endpoint,size,timeout)


class Interface:
    def __init__(self,fields,endpoints):self.__dict__.update(vars(fields));self.endpoints=endpoints
    def __iter__(self):return iter(self.endpoints)


class Configuration:
    def __init__(self,fields,endpoints):self.interface=Interface(fields,endpoints)
    def __getitem__(self,index):
        assert index==(0,0);return self.interface


class Core:
    def __init__(self,world):self.world=world;self.current=()
    def find(self,*,find_all,idVendor,idProduct,backend):
        w=self.world;s=w.system
        assert find_all is True and idVendor==0x054c and backend is w.backend
        assert idProduct in (m.NORMAL,m.SERVICE)
        if idProduct==m.NORMAL:
            if s.phase==0 and s.handles[0].closed and s.normal_device.auth.used==15:s.phase=1
            elif s.phase==1 and s.handles[1].closed and s.service_device.auth.used==16:s.phase=2;s.mounted=True
            self.current=s.inventory()
        w.record('find')
        for key in self.current:
            if key.pid==idProduct:
                device=Device(w,key);w.devices.append(device);yield device


class Util:
    def __init__(self,world):self.world=world
    def claim_interface(self,device,interface):
        device.ready();assert interface==0
        self.world.record('claim',device);device.claimed=True
        return self.world.system.claim(device.handle)
    def release_interface(self,device,interface):
        device.ready();assert interface==0
        self.world.record('release',device)
        result=self.world.system.release(device.handle)
        if result is None:device.claimed=False
        return result
    def dispose_resources(self,device):
        # Count even failed/repeated attempts: never hide them by idempotence.
        device.dispose_attempts+=1;device.ready();device.disposed=True
        value=self.world.record('dispose',device)
        if device.claimed:self.world.record('implicit-release',device);device.claimed=False
        result=self.world.system.dispose(device.handle) if device.opened else None
        return result if value is None else value


class FakeOS:
    O_RDWR,O_CREAT,O_NOFOLLOW,O_NONBLOCK=os.O_RDWR,os.O_CREAT,os.O_NOFOLLOW,os.O_NONBLOCK
    def __init__(self,world):self.world=world
    def geteuid(self):return 0
    def open(self,path,flags,mode):
        assert path==m.LOCK and flags==self.O_RDWR|self.O_CREAT|self.O_NOFOLLOW|self.O_NONBLOCK and mode==0o600
        self.world.record('lock-open');self.world.system.acquire();return 900001
    def fstat(self,fd):
        assert fd==900001;self.world.record('lock-stat')
        return NS(st_mode=stat.S_IFREG|0o600,st_uid=0,st_nlink=1)
    def close(self,fd):
        assert fd==900001;self.world.record('lock-close');return self.world.system.unlock(1)


class FakeFcntl:
    LOCK_EX,LOCK_NB=2,4
    def __init__(self,world):self.world=world
    def flock(self,fd,flags):
        assert fd==900001 and flags==self.LOCK_EX|self.LOCK_NB;return self.world.record('lock-flock')


class World:
    """Own SDK objects/OS data only, no parallel authentication coordinator."""
    def __init__(self,system,*,faults=None):
        if type(system) is not owned.SyntheticSystem:raise TypeError('Exact own fake system required')
        self.system=system;self.devices=[];self.trace=[];self.counts={};self.faults={} if faults is None else dict(faults)
        self.backend=object();self.core=Core(self);self.util=Util(self)
        self.ops=m._NativeOps();self.ops._backend=self.backend
        self.ops.clock=system.clock;self.ops.sleep=system.sleep;self.host=None

    def record(self,name,device=None):
        self.trace.append((name,device));self.counts[name]=self.counts.get(name,0)+1
        value=self.faults.get((name,self.counts[name]))
        if isinstance(value,BaseException):raise value
        return value

    def command(self,args,seconds,*,limit=8*1024*1024):
        assert 0<seconds<=20;self.record('command')
        if args==('/usr/sbin/ioreg','-p','IOService','-l','-a'):
            assert limit==m.IOREGISTRY_MAX_BYTES
            return plistlib.dumps([{'IOObjectClass':'IOUSBHostDevice','idVendor':0x054c,'idProduct':m.NORMAL,
                'IORegistryEntryID':100,'IORegistryEntryChildren':[
                    {'IOObjectClass':'IOMedia','BSD Name':'disk9'},{'IOObjectClass':'IOMedia','BSD Name':'disk9s1'}]}])
        assert limit==8*1024*1024
        if args[:3]==('/usr/sbin/diskutil','info','-plist'):
            name=args[3];assert name in ('disk9','disk9s1')
            value={'DeviceIdentifier':name,'Internal':False,'OSInternalMedia':False,'BusProtocol':'USB',
                   'WholeDisk':name=='disk9','ParentWholeDisk':'disk9'}
            if self.system.mounted:value['MountPoint']='/Volumes/OWN-FAKE'
            return plistlib.dumps(value)
        assert args==('/usr/sbin/diskutil','unmountDisk','/dev/disk9')
        return self.system.unmount('disk9',seconds)

    @contextmanager
    def bound(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(m,'os',FakeOS(self)))
            stack.enter_context(patch.object(m,'sys',NS(platform='darwin')))
            stack.enter_context(patch.object(m,'fcntl',FakeFcntl(self)))
            stack.enter_context(patch.object(m,'_bounded_command',self.command))
            stack.enter_context(patch.object(self.ops,'_runtime',return_value=(self.core,self.util)))
            yield self.ops

    def run(self,archive,directory,*,resources=False,cancel=None):
        cancel,policy,channel=owned._prepare(archive,self.system,resources,cancel)
        # Configure the fake material oracle, not the coordinator or SDK code.
        self.system.service_device._requests=channel.requests
        self.host=m._Host(self.ops,None,firmware=self.system.peer.version,battery_percent=self.system.peer.battery,
                          budget=channel.budget,cancel=cancel,wait=True)
        with self.bound():
            return owned._execute(archive,directory,self.host,channel,policy,
                                  resources=resources,run_type=candidate._NativeRun)
