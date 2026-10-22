"""Injected fake OS/PyUSB tests: never enumerate USB or open the system lock."""
import copy
import os
import plistlib
import stat
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch

from lutphoto import capturemac as m
from test_capturemsc import Wire,tape,model_response


class FakeOps:
    def __init__(self):
        self.now=0;self.trace=[];self.phase=0;self.faults={};self.devices=[]
        self.keys=[m._Key(m.NORMAL,1,(2,3),4),m._Key(m.SERVICE,1,(2,3),5),m._Key(m.NORMAL,1,(2,3),6)]
        self.mounted=True;self.serials=[b'\1\2\3\4',b'\1\2\3\4']
    def clock(self):return self.now
    def sleep(self,seconds):self.now+=seconds
    def record(self,name):
        self.trace.append(name)
        result=self.faults.get(name)
        if isinstance(result,BaseException):raise result
        return result
    def acquire(self):self.record('lock');return 99
    def unlock(self,fd):assert fd==99;return self.record('unlock')
    def inventory(self):
        self.record('inventory');return self.faults.get('keys',(self.keys[self.phase],))
    def media(self,seconds):
        self.record('media');return self.faults.get('media_value',(100,{'disk9':('disk9',True,self.mounted),'disk9s1':('disk9',False,self.mounted)}))
    def unmount(self,name,seconds):
        assert name=='disk9';self.record('unmount');self.mounted=False;return b'own command output'
    def open(self,key):
        self.record('open');assert key==self.keys[self.phase]
        d=NS(key=key,wire=Wire(tape(model_response(self.serials[int(self.phase==2)]))),closed=False)
        self.devices.append(d);return d
    def descriptor(self,d):
        self.record('descriptor')
        return self.faults.get('profile',(0x054c,d.key.pid,0,0,*( (8,6,0x50) if d.key.pid==m.NORMAL else (255,0,0)),((129,2),(2,2))))
    def active(self,d):self.record('active');return self.faults.get('active_value',d.key.pid==m.NORMAL)
    def detach(self,d):return self.record('detach')
    def attach(self,d):return self.record('attach')
    def claim(self,d):return self.record('claim')
    def release(self,d):return self.record('release')
    def dispose(self,d):
        assert not d.closed;d.closed=True;return self.record('dispose')
    def write(self,d,ep,raw,timeout):
        assert not d.closed and ep==2;self.record('write');return d.wire.write(raw,timeout)
    def read(self,d,ep,size,timeout):
        assert not d.closed and ep==129;self.record('read');return d.wire.read(size,timeout)


class HostTests(unittest.TestCase):
    def host(self,ops=None,event=None,**kw):
        ops=FakeOps() if ops is None else ops
        return m._Host(ops,event or (lambda *args,**kw:None),firmware='2.01',battery_percent=75,**kw),ops
    def complete(self,h,o):
        owner,identity=h.normal();h.departing(owner);o.phase=1
        service=h.service();h.departing(service);o.phase=2;o.mounted=True
        return identity,h.normal_return()

    def test_fresh_normal_query_and_order(self):
        h,o=self.host();events=[];h.event=lambda name,**kw:events.append((name,kw['operation']))
        with h:
            first,last=self.complete(h,o);self.assertEqual(first,last)
            self.assertEqual(h.stage,'RETURN_QUERIED')
        self.assertEqual(o.trace[0],'lock');self.assertEqual(o.trace[-1],'unlock')
        self.assertEqual(len(o.devices),3);self.assertTrue(all(d.closed for d in o.devices))
        self.assertFalse(o.devices[0].wire.entries);self.assertFalse(o.devices[2].wire.entries)
        self.assertEqual(o.trace.count('dispose'),3)
        self.assertEqual((o.trace.count('release'),o.trace.count('attach')),(1,1))
        self.assertEqual(sum(op=='NORMAL_IDENTITY_QUERY' and name=='HOST_ACK' for name,op in events),2)
        self.assertGreaterEqual(o.now,6)

    def test_return_serial_change_stops_and_disposes_without_reattach(self):
        h,o=self.host();o.serials[1]=b'\4\3\2\1'
        with self.assertRaisesRegex(ValueError,'identity differs'):
            with h:self.complete(h,o)
        self.assertTrue(all(d.closed for d in o.devices));self.assertNotIn('attach',o.trace)
        self.assertEqual(o.trace.count('write'),12)  # Two complete 5-CBW/1-data queries.

    def test_existing_service_or_multiple_cameras_refused_before_media(self):
        for keys in ((),(m._Key(m.SERVICE,1,(2,),1),),(m._Key(m.NORMAL,1,(2,),1),)*2):
            h,o=self.host();o.faults['keys']=keys
            with self.assertRaises(ValueError):
                with h:h.normal()
            self.assertNotIn('media',o.trace);self.assertNotIn('open',o.trace)

    def test_port_change_on_service_refused_before_open(self):
        h,o=self.host();o.keys[1]=m._Key(m.SERVICE,1,(9,),5)
        with self.assertRaises(ValueError):
            with h:
                owner,_=h.normal();h.departing(owner);o.phase=1;h.service()
        self.assertEqual(len(o.devices),1)

    def test_generation_change_during_unmount_refused(self):
        h,o=self.host();original=o.unmount
        def unmount(*args):original(*args);o.keys[0]=m._Key(m.NORMAL,1,(2,3),7)
        o.unmount=unmount
        with self.assertRaises(ValueError):
            with h:h.normal()
        self.assertNotIn('open',o.trace)

    def test_lock_busy_no_other_operations(self):
        h,o=self.host();o.faults['lock']=BlockingIOError()
        with self.assertRaises(BlockingIOError):
            with h:self.fail('Not entered')
        self.assertEqual(o.trace,['lock'])

    def test_version_and_battery_gate_before_any_host_operation(self):
        for version,battery in (('2.00',75),('2.01',True),('2.01',49),('2.01',101),('2.0.1',75)):
            o=FakeOps()
            with self.assertRaises(ValueError):m._Host(o,Mock(),firmware=version,battery_percent=battery)
            self.assertFalse(o.trace)

    def test_partial_claim_failure_no_usb_query_or_explicit_reattach(self):
        h,o=self.host();o.faults['claim']=OSError('own failure')
        with self.assertRaises(OSError):
            with h:h.normal()
        self.assertNotIn('write',o.trace);self.assertNotIn('attach',o.trace)
        self.assertEqual(o.trace.count('dispose'),1)

    def test_detach_failure_does_not_claim(self):
        h,o=self.host();o.faults['detach']=OSError()
        with self.assertRaises(OSError):
            with h:h.normal()
        self.assertNotIn('claim',o.trace);self.assertNotIn('write',o.trace)
        self.assertEqual(o.trace.count('dispose'),1)

    def test_unknown_read_no_additional_protocol_operations(self):
        h,o=self.host();o.faults['read']=TimeoutError()
        with self.assertRaises(TimeoutError):
            with h:h.normal()
        self.assertEqual(o.trace.count('write'),1);self.assertEqual(o.trace.count('read'),1)
        self.assertNotIn('release',o.trace);self.assertNotIn('attach',o.trace)
        self.assertEqual(o.trace[-2:],['dispose','unlock'])

    def test_failed_open_ack_still_adopts_for_cleanup(self):
        def event(name,**kw):
            if name=='HOST_ACK' and kw['operation']=='OPEN_HANDLE':raise OSError('own journal failure')
        h,o=self.host(event=event)
        with self.assertRaises(OSError):
            with h:h.normal()
        self.assertEqual(o.trace[-2:],['dispose','unlock']);self.assertNotIn('claim',o.trace)

    def test_failed_claim_ack_stops_and_disposes(self):
        def event(name,**kw):
            if name=='HOST_ACK' and kw['operation']=='CLAIM_INTERFACE':raise OSError()
        h,o=self.host(event=event)
        with self.assertRaises(OSError):
            with h:h.normal()
        self.assertTrue(h.owners[0].claimed);self.assertNotIn('write',o.trace)
        self.assertNotIn('attach',o.trace);self.assertEqual(o.trace.count('dispose'),1)

    def test_release_failure_still_disposes_and_unlocks_once(self):
        h,o=self.host();o.faults['release']=OSError()
        with self.assertRaises(OSError):
            with h:h.normal()
        self.assertEqual(o.trace.count('dispose'),1);self.assertEqual(o.trace.count('release'),1)
        self.assertNotIn('attach',o.trace);self.assertEqual(o.trace[-1],'unlock')
        h.owners[0].close();self.assertEqual(o.trace.count('dispose'),1)

    def test_primary_error_preserved_despite_dispose_failure(self):
        h,o=self.host();o.faults.update(read=TimeoutError('primary'),dispose=OSError('cleanup'))
        with self.assertRaisesRegex(TimeoutError,'primary'):
            with h:h.normal()
        self.assertEqual(o.trace[-1],'unlock');self.assertTrue(h.blocked)

    def test_service_driver_active_not_detached(self):
        h,o=self.host()
        with self.assertRaises(ValueError):
            with h:
                owner,_=h.normal();h.departing(owner);o.phase=1;o.faults['active_value']=True;h.service()
        self.assertEqual(o.trace.count('detach'),1);self.assertEqual(o.trace.count('dispose'),2)

    def test_kernel_state_not_implemented_refused(self):
        h,o=self.host();o.faults['active']=NotImplementedError()
        with self.assertRaises(NotImplementedError):
            with h:h.normal()
        self.assertNotIn('claim',o.trace);self.assertEqual(o.trace.count('dispose'),1)

    def test_management_bool_is_not_completion(self):
        h,o=self.host();o.faults['claim']=True
        with self.assertRaises(ValueError):
            with h:h.normal()
        self.assertNotIn('write',o.trace)

    def test_no_owner_query_or_transition_replay(self):
        h,o=self.host()
        with h:
            owner,_=h.normal();count=o.trace.count('write')
            with self.assertRaises(RuntimeError):owner.query()
            h.departing(owner)
            with self.assertRaises(ValueError):h.departing(owner)
            with self.assertRaises(RuntimeError):owner.query()
            self.assertEqual(o.trace.count('write'),count)
        with self.assertRaises(RuntimeError):h.__enter__()

    def test_unmount_failure_no_open(self):
        h,o=self.host();o.faults['unmount']=OSError()
        with self.assertRaises(OSError):
            with h:h.normal()
        self.assertNotIn('open',o.trace)

    def test_topology_change_before_unmount(self):
        h,o=self.host();original=o.media;count=[0]
        def media(*args):
            value=original(*args);count[0]+=1
            return (101,value[1]) if count[0]>=8 else value
        o.media=media
        with self.assertRaises(ValueError):
            with h:h.normal()
        self.assertNotIn('unmount',o.trace);self.assertNotIn('open',o.trace)

    def test_media_query_uses_local_remaining_stability_deadline(self):
        h,o=self.host();durations=[];original=o.media
        def media(seconds):
            durations.append(seconds);value=original(seconds)
            # A still-running first query consumes its allotted local interval.
            o.now+=20
            return value
        o.media=media
        with self.assertRaises(TimeoutError):
            with h:h.normal()
        self.assertEqual(durations,[20]);self.assertNotIn('open',o.trace)

    def test_still_mounted_after_unmount_refused(self):
        h,o=self.host();o.unmount=lambda *args:o.record('unmount')
        with self.assertRaises(ValueError):
            with h:h.normal()
        self.assertNotIn('open',o.trace)

    def test_bad_descriptor_no_claim(self):
        for profile in ((0x054c,m.NORMAL,0,0,8,6,80,((129,2),(130,2))),
                        (0x054c,m.NORMAL,1,0,8,6,80,((129,2),(2,2))),
                        (0x054c,m.NORMAL,0,0,8,6,80,((129,3),(2,2)))):
            h,o=self.host();o.faults['profile']=profile
            with self.assertRaises(ValueError):
                with h:h.normal()
            self.assertNotIn('claim',o.trace);self.assertEqual(o.trace.count('dispose'),1)

    def test_fresh_descriptor_change_before_io_refused(self):
        h,o=self.host();original=o.descriptor;count=[0]
        def descriptor(*args):
            value=original(*args);count[0]+=1
            return value if count[0]==1 else (*value[:7],((131,2),(4,2)))
        o.descriptor=descriptor
        with self.assertRaises(ValueError):
            with h:h.normal()
        self.assertNotIn('write',o.trace);self.assertEqual(o.trace.count('dispose'),1)

    def test_shared_deadline_stops_before_new_protocol_command(self):
        h,o=self.host();h.budget.deadline=1
        with self.assertRaises(TimeoutError):
            with h:h.normal()
        self.assertNotIn('open',o.trace)

    def test_unlock_failure_is_not_silent_success(self):
        h,o=self.host();o.faults['unlock']=OSError()
        with self.assertRaises(OSError):
            with h:h.normal()
        self.assertTrue(h.blocked);self.assertIsNone(h.lock)


class NativeBindingTests(unittest.TestCase):
    def test_global_lock_fixed_path_and_no_unlink(self):
        ops=m._NativeOps();info=NS(st_mode=stat.S_IFREG|0o600,st_uid=0,st_nlink=1)
        with patch.object(m.os,'geteuid',return_value=0),patch.object(m.os,'open',return_value=17) as opened,\
             patch.object(m.os,'fstat',return_value=info),patch.object(m.os,'close') as closed,patch.object(m.fcntl,'flock') as locked:
            fd=ops.acquire();ops.unlock(fd)
            self.assertEqual(opened.call_args.args[0],'/var/run/a7c2-fl23-macos.lock')
            self.assertTrue(opened.call_args.args[1]&os.O_NOFOLLOW)
            locked.assert_called_once_with(17,m.fcntl.LOCK_EX|m.fcntl.LOCK_NB);closed.assert_called_once_with(17)

    def test_unsafe_lock_metadata_closes_fd(self):
        for info in (NS(st_mode=stat.S_IFREG|0o644,st_uid=0,st_nlink=1),NS(st_mode=stat.S_IFREG|0o600,st_uid=1,st_nlink=1),
                     NS(st_mode=stat.S_IFREG|0o600,st_uid=0,st_nlink=2),NS(st_mode=stat.S_IFDIR|0o700,st_uid=0,st_nlink=1)):
            with patch.object(m.os,'geteuid',return_value=0),patch.object(m.os,'open',return_value=17),\
                 patch.object(m.os,'fstat',return_value=info),patch.object(m.os,'close') as closed:
                with self.assertRaises(ValueError):m._NativeOps().acquire()
                closed.assert_called_once_with(17)

    def test_command_allowlist_never_force_or_arbitrary_path(self):
        with patch.object(m,'_bounded_command',return_value=b'') as run:
            ops=m._NativeOps();ops.unmount('disk9',1)
            run.assert_called_once_with(('/usr/sbin/diskutil','unmountDisk','/dev/disk9'),1)
            for args in (('/usr/sbin/diskutil','unmountDisk','force','/dev/disk9'),('/bin/sh','-c','anything'),
                         ('/usr/sbin/diskutil','unmountDisk','/dev/disk9s1'),('/usr/sbin/diskutil','info','-plist','../disk9')):
                with self.assertRaises(ValueError):ops.command(args,1)
            self.assertEqual(run.call_count,1)

    def test_larger_output_budget_is_only_for_fixed_host_registry_query(self):
        with patch.object(m,'_bounded_command',return_value=b'') as run:
            ops=m._NativeOps()
            ops.command(('/usr/sbin/ioreg','-p','IOService','-l','-a'),2)
            run.assert_called_once_with(('/usr/sbin/ioreg','-p','IOService','-l','-a'),2,limit=32*1024*1024)
            run.reset_mock()
            ops.command(('/usr/sbin/diskutil','info','-plist','disk9'),2)
            run.assert_called_once_with(('/usr/sbin/diskutil','info','-plist','disk9'),2)
            run.reset_mock()
            with self.assertRaises(ValueError):
                ops.command(('/usr/sbin/ioreg','-p','IOService','-l','-a','-w','0'),2)
            run.assert_not_called()

    def tree(self):
        return [{'IOObjectClass':'IOUSBHostDevice','idVendor':0x054c,'idProduct':m.NORMAL,'IORegistryEntryID':100,
                 'IORegistryEntryChildren':[{'IOObjectClass':'IOMedia','BSD Name':'disk9'}]}]
    def info(self):return dict(DeviceIdentifier='disk9',Internal=False,OSInternalMedia=False,BusProtocol='USB',WholeDisk=True,ParentWholeDisk='disk9')
    def media(self,tree=None,info=None):
        values=[plistlib.dumps(self.tree() if tree is None else tree),plistlib.dumps(self.info() if info is None else info)]
        ops=m._NativeOps()
        with patch.object(ops,'command',side_effect=values):return ops.media(2)

    def test_registry_only_target_child_media(self):
        tree=self.tree();tree.append({'IOObjectClass':'IOMedia','BSD Name':'disk777'})
        self.assertEqual(self.media(tree),(100,{'disk9':('disk9',True,False)}))

    def test_internal_media_and_unknown_parent_refused(self):
        for key,value in (('Internal',True),('OSInternalMedia',True),('BusProtocol','SATA'),('ParentWholeDisk','disk8'),('WholeDisk',1)):
            info=self.info();info[key]=value
            with self.assertRaises(ValueError):self.media(info=info)

    def test_multiple_registry_cameras_refused(self):
        tree=self.tree()*2
        with self.assertRaises(ValueError):self.media(tree)

    def test_native_management_none_and_fixed_interface(self):
        ops=m._NativeOps();util=Mock();util.dispose_resources.return_value=None;d=Mock()
        with patch.object(ops,'_runtime',return_value=(Mock(),util)):
            ops.claim(d);ops.release(d);ops.dispose(d);ops.detach(d);ops.attach(d)
        util.claim_interface.assert_called_once_with(d,0);util.release_interface.assert_called_once_with(d,0)
        util.dispose_resources.assert_called_once_with(d);d.detach_kernel_driver.assert_called_once_with(0)
        d.attach_kernel_driver.assert_called_once_with(0)

    def test_native_read_write_preserve_raw_counts_and_arrays(self):
        ops=m._NativeOps();d=Mock();d.write.return_value=3;d.read.return_value=bytearray(b'bad unvalidated native result')
        self.assertEqual(ops.write(d,2,b'own',40),3)
        self.assertIs(ops.read(d,129,5,40),d.read.return_value)
        d.write.assert_called_once_with(2,b'own',timeout=40);d.read.assert_called_once_with(129,5,timeout=40)

    def test_enumeration_handles_are_disposed_and_reopened(self):
        ops=m._NativeOps();d=NS(idVendor=0x054c,idProduct=m.NORMAL,bus=1,port_numbers=(2,),address=4)
        core=Mock();core.find.side_effect=lambda **kw:[d] if kw['idProduct']==m.NORMAL else []
        util=Mock();util.dispose_resources.return_value=None
        with patch.object(ops,'_runtime',return_value=(core,util)):
            key,=ops.inventory();util.dispose_resources.assert_called_once_with(d)
            util.reset_mock();self.assertIs(ops.open(key),d);util.dispose_resources.assert_not_called()

    def test_native_open_ambiguous_disposes_all(self):
        ops=m._NativeOps();d=NS(idVendor=0x054c,idProduct=m.NORMAL,bus=1,port_numbers=(2,),address=4)
        core=Mock();core.find.side_effect=lambda **kw:[d,copy.copy(d)] if kw['idProduct']==m.NORMAL else []
        util=Mock();util.dispose_resources.return_value=None
        with patch.object(ops,'_runtime',return_value=(core,util)):
            with self.assertRaises(ValueError):ops.open(m._Key(m.NORMAL,1,(2,),4))
        self.assertEqual(util.dispose_resources.call_count,2)

    def test_imports_no_usb_runtime(self):
        self.assertFalse(any(n=='usb' or n.startswith('usb.') for n in sys.modules))

class HostCommandBoundsTests(unittest.TestCase):
    def test_real_large_host_stdout_accepts_reviewed_size_and_still_rejects_overflow(self):
        mib=1024*1024
        for count,limit,accepted in ((9*mib,32*mib,True),(32*mib,32*mib,True),
                                      (32*mib+1,32*mib,False),(8*mib+1,8*mib,False)):
            with self.subTest(count=count,limit=limit):
                command=(sys.executable,'-B','-c',f'import sys; sys.stdout.buffer.write(b"x"*{count})')
                if accepted:
                    self.assertEqual(len(m._bounded_command(command,20,limit=limit)),count)
                else:
                    with self.assertRaisesRegex(ValueError,'^Host command output exceeded bound$'):
                        m._bounded_command(command,20,limit=limit)

    def exercise(self,chunks,*,ready=True,code=0):
        process=Mock();process.poll.return_value=None;process.wait.return_value=code;process.stdout.fileno.return_value=7
        selector=Mock();selector.__enter__=Mock(return_value=selector);selector.__exit__=Mock(return_value=False)
        selector.select.return_value=[(None,None)] if ready else []
        self.process=process
        with patch.object(m.subprocess,'Popen',return_value=process) as popen,patch.object(m.selectors,'DefaultSelector',return_value=selector),\
             patch.object(m.os,'read',side_effect=chunks),patch.object(m.time,'monotonic',return_value=0):
            try:return m._bounded_command(('/fixed/fake',),1,limit=8)
            finally:
                self.assertEqual(popen.call_args.kwargs,{'stdout':m.subprocess.PIPE,'stderr':m.subprocess.STDOUT})
                process.kill.assert_called_once();process.stdout.close.assert_called_once()

    def test_output_cap_checked_during_read_and_process_reaped(self):
        with self.assertRaises(ValueError):self.exercise([b'123456789'])
        self.process.wait.assert_called_once()

    def test_no_output_before_deadline_kills_and_reaps(self):
        with self.assertRaises(TimeoutError):self.exercise([],ready=False)
        self.process.wait.assert_called_once()

    def test_complete_bounded_output(self):
        self.assertEqual(self.exercise([b'1234',b'56',b'']),b'123456')

    def test_nonzero_status_does_not_expose_output(self):
        with self.assertRaisesRegex(OSError,'^Host command failed$'):self.exercise([b'private',b''],code=1)


class CleanupAndGateTests(unittest.TestCase):
    def test_enumeration_disposal_failure_still_attempts_every_handle(self):
        util=Mock();util.dispose_resources.side_effect=[OSError('first'),None]
        with self.assertRaisesRegex(OSError,'first'):m._NativeOps._dispose_all(util,[object(),object()])
        self.assertEqual(util.dispose_resources.call_count,2)

    def test_non_mac_or_non_root_acquire_never_opens_lock(self):
        for platform,uid in (('linux',0),('darwin',501)):
            with patch.object(m.sys,'platform',platform),patch.object(m.os,'geteuid',return_value=uid),patch.object(m.os,'open') as opened:
                with self.assertRaises(PermissionError):m._NativeOps().acquire()
                opened.assert_not_called()

    def test_query_ack_failure_never_requeries_cached_or_new_handle(self):
        ops=FakeOps()
        def event(name,**kw):
            if name=='HOST_ACK' and kw['operation']=='NORMAL_IDENTITY_QUERY':raise OSError('journal')
        host=m._Host(ops,event,firmware='2.01',battery_percent=75)
        with self.assertRaises(OSError):
            with host:host.normal()
        self.assertEqual(ops.trace.count('write'),6);self.assertEqual(ops.trace.count('dispose'),1)
        self.assertNotIn('attach',ops.trace);self.assertTrue(host.blocked)

    def test_unknown_dispose_result_is_failure_and_not_repeated(self):
        ops=FakeOps();ops.faults['dispose']=True
        host=m._Host(ops,Mock(),firmware='2.01',battery_percent=75)
        with self.assertRaisesRegex(ValueError,'disposal'):
            with host:host.normal()
        host.owners[0].close();self.assertEqual(ops.trace.count('dispose'),1)

class PackagedBackendTests(unittest.TestCase):
    def sdk(self,backend):
        import types
        usb=types.ModuleType('usb');usb.__path__=[]
        core=types.ModuleType('usb.core');core.find=Mock(return_value=[])
        util=types.ModuleType('usb.util')
        group=types.ModuleType('usb.backend');group.__path__=[]
        lib=types.ModuleType('usb.backend.libusb1');lib.get_backend=Mock(return_value=backend)
        package=types.ModuleType('libusb_package');package.find_library=Mock()
        usb.core,usb.util,usb.backend=core,util,group;group.libusb1=lib
        return {'usb':usb,'usb.core':core,'usb.util':util,'usb.backend':group,'usb.backend.libusb1':lib,'libusb_package':package}

    def test_explicit_packaged_backend_selected_once_and_passed_to_find(self):
        backend=object();sdk=self.sdk(backend);ops=m._NativeOps()
        with patch.dict(sys.modules,sdk),patch.object(m.os,'geteuid',return_value=0),patch.object(m.sys,'platform','darwin'):
            self.assertEqual(ops.inventory(),());self.assertEqual(ops.inventory(),())
        sdk['usb.backend.libusb1'].get_backend.assert_called_once_with(find_library=sdk['libusb_package'].find_library)
        self.assertEqual(sdk['usb.core'].find.call_count,4)
        self.assertTrue(all(call.kwargs['backend'] is backend for call in sdk['usb.core'].find.call_args_list))

    def test_missing_packaged_backend_stops_before_enumeration(self):
        sdk=self.sdk(None)
        with patch.dict(sys.modules,sdk),patch.object(m.os,'geteuid',return_value=0),patch.object(m.sys,'platform','darwin'):
            with self.assertRaises(RuntimeError):m._NativeOps().inventory()
        sdk['usb.core'].find.assert_not_called()

    def test_native_control_preserves_count_and_explicit_timeout(self):
        device=Mock();device.ctrl_transfer.return_value=0
        self.assertEqual(m._NativeOps().control(device,0x43,1,0x37ff,0xd7aa,b'',123),0)
        device.ctrl_transfer.assert_called_once_with(0x43,1,0x37ff,0xd7aa,b'',timeout=123)

    def test_disposal_journal_failure_still_invalidates_and_disposes_once(self):
        ops=FakeOps()
        def event(name,**details):
            if name=='HOST_ACK' and details['operation']=='DISPOSE_RESOURCES':raise OSError('own journal')
        host=m._Host(ops,event,firmware='2.01',battery_percent=75)
        with self.assertRaises(OSError):
            with host:host.normal()
        host.owners[0].close();self.assertTrue(host.owners[0].closed);self.assertFalse(host.owners[0].close_ok)
        self.assertEqual(ops.trace.count('dispose'),1);self.assertEqual(ops.trace[-1],'unlock')
