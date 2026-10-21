"""Test-only child: real signals around a bounded own fake SDK wait.

Fixed scenarios and self-made fixtures; no SDK, camera or live global lock.
The parent releases stdin after observing cancellation; watchdog cleanup is
restricted to this child in the test, never shipped capture behavior.
"""
import json
import sys
import threading
import time
from unittest.mock import patch

from lutphoto import captureowned as o, captureinspect, captureexecution, captureevidence
from lutphoto.capturecontrol import Cancellation
from lutphoto.capturesignals import SignalCancellation
from research.tests import test_captureowned as fixtures
from research.tests.native_sdk_fixture import World,Device,Util


def emit(value):print(json.dumps(value,sort_keys=True),flush=True)


def main():
    allowed=('configuration','material','stop','dispose')
    if len(sys.argv)!=3 or sys.argv[1] not in allowed+tuple(prefix+n for prefix in ('execution-','public-') for n in allowed):
        raise ValueError('Fixed own child scenario required')
    scenario,directory=sys.argv[1:]
    execution=scenario.startswith('execution-');public=scenario.startswith('public-')
    scenario=scenario.removeprefix('execution-').removeprefix('public-')
    if public:
        from research.tests.test_capturecamera import CameraTests
        f=CameraTests(methodName='runTest')
    else:f=fixtures.OwnedTests(methodName='runTest')
    f.setUp()
    token=Cancellation();world=World(f.fixture.system() if public else f.system());blocked=False;returned=threading.Event();monitor=None
    import signal
    previous={n:signal.getsignal(n) for n in (signal.SIGINT,signal.SIGTERM)}
    try:
        def state(phase):
            nonlocal token
            if public:token=world.host.cancel
            owner=world.host.owners[-1]
            return {'phase':phase,'lease_held':world.system.acquired,'owner_retained':owner in world.host.owners,
                    'views_invalidated':owner.closed,'sdk_returned':returned.is_set(),
                    'cancel_requested':token.requested,'write_calls':world.counts.get('write',0),
                    'read_calls':world.counts.get('read',0),'control_calls':world.counts.get('control',0)}
        def observe():
            end=time.monotonic()+10
            while not token.requested and time.monotonic()<end:time.sleep(.01)
            emit(state('SIGNAL_OBSERVED' if token.requested else 'MONITOR_TIMEOUT'))
        def wait():
            nonlocal blocked,monitor
            if blocked:return
            blocked=True;emit(state('BLOCKED'))
            monitor=threading.Thread(target=observe,daemon=True);monitor.start()
            if sys.stdin.buffer.readline(16)!=b'RETURN\n':raise RuntimeError('Own fake call release required')
            returned.set();monitor.join(timeout=2)

        if scenario=='configuration':
            original=Device.get_active_configuration
            def hook(device):
                result=original(device)
                if device.phase==0:wait()
                return result
            point=patch.object(Device,'get_active_configuration',hook)
        elif scenario=='material':
            original=Device.write
            def hook(device,*args,**kw):
                result=original(device,*args,**kw)
                if device.phase==1 and device.handle.protocol.auth.used==15:wait()
                return result
            point=patch.object(Device,'write',hook)
        elif scenario=='stop':
            original=Device.ctrl_transfer
            def hook(device,*args,**kw):
                result=original(device,*args,**kw)
                if device.phase==1 and args[:4]==o.a.STOP:wait()
                return result
            point=patch.object(Device,'ctrl_transfer',hook)
        else:
            original=Util.dispose_resources
            def hook(util,device):
                result=original(util,device)
                if device.opened and device.phase==0:wait()
                return result
            point=patch.object(Util,'dispose_resources',hook)
        with point:
            if execution or public:
                if public:
                    from pathlib import Path
                    from lutphoto import capturecamera
                    receipt=Path(directory).with_name(Path(directory).name+'-terminal.private.json')
                    execute=captureexecution._execute
                    def host_bound(*args,**kwargs):world.host=args[2];return execute(*args,**kwargs)
                    with f.bound(world),patch.object(captureexecution,'_execute',host_bound):
                        result=capturecamera.capture('own',directory,receipt,model='ILCE-7CM2',firmware='2.01',battery_percent=75)
                else:
                    _,policy,channel=o._prepare('own',world.system,False,token)
                    world.system.service_device._requests=channel.requests
                    world.host=o.m._Host(world.ops,None,firmware='2.01',battery_percent=75,budget=channel.budget,cancel=token,wait=True)
                    with world.bound():
                        result=captureexecution._execute('own',directory,world.host,channel,policy,resources=False,
                            firmware='2.01',battery_percent=75,execution_kind='self-made-sdk')
                from pathlib import Path
                checkpoint=json.loads((Path(directory)/captureevidence.CHECKPOINT).read_bytes())
                reason=result['errors'][0]['reason_type'];stop=checkpoint['flow']['service_stop_ack']
                matched=checkpoint['flow']['normal_identity_matched'];flags=all(v is False for v in result['unproven'].values())
                restored=result['cleanup']['signal_handlers']=='CONFIRMED'
                classification=captureevidence.inspect_directory(directory,receipt=receipt if public else None)['classification']
            else:
                with SignalCancellation(token) as scope:result=world.run('own',directory,cancel=token)
                reason=result['reason_type'];stop=result['simulated_service_stop_ack'];matched=result['simulated_normal_identity_matched']
                flags=all(result[n] is False for n in captureinspect.FALSE_COMMON|captureinspect.FALSE_PROFILE['owned'])
                restored=scope.restoration_confirmed;classification=captureinspect.inspect_directory(directory)['classification']
        emit({'phase':'DONE','reason_type':reason,'capture_phase':result['phase'],
              'classification':classification,
              'handlers_restored':all(signal.getsignal(n) is old for n,old in previous.items()) and restored,
              'lease_held':world.system.acquired,'sdk_returned':returned.is_set(),'cancel_requested':token.requested,
              'write_calls':world.counts.get('write',0),'read_calls':world.counts.get('read',0),
              'control_calls':world.counts.get('control',0),
              'single_disposal_attempts':all(d.dispose_attempts==1 for d in world.devices),
              'service_stop_ack':stop,'normal_identity_matched':matched,'physical_flags_false':flags,
              'device_operations_performed':False,'native_sdk_imported':any(n=='usb' or n.startswith('usb.') or n=='libusb_package' for n in sys.modules)})
    finally:
        if monitor is not None:monitor.join(timeout=2)
        f.doCleanups()


if __name__=='__main__':main()
