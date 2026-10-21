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

from lutphoto import captureowned as o, captureinspect
from lutphoto.capturecontrol import Cancellation
from lutphoto.capturesignals import SignalCancellation
from research.tests import test_captureowned as fixtures
from research.tests.native_sdk_fixture import World,Device,Util


def emit(value):print(json.dumps(value,sort_keys=True),flush=True)


def main():
    if len(sys.argv)!=3 or sys.argv[1] not in ('configuration','material','stop','dispose'):
        raise ValueError('Fixed own child scenario required')
    scenario,directory=sys.argv[1:]
    f=fixtures.OwnedTests(methodName='runTest');f.setUp()
    token=Cancellation();world=World(f.system());blocked=False;returned=threading.Event();monitor=None
    import signal
    previous={n:signal.getsignal(n) for n in (signal.SIGINT,signal.SIGTERM)}
    try:
        def state(phase):
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
        with SignalCancellation(token) as scope,point:
            result=world.run('own',directory,cancel=token)
        emit({'phase':'DONE','reason_type':result['reason_type'],'capture_phase':result['phase'],
              'classification':captureinspect.inspect_directory(directory)['classification'],
              'handlers_restored':all(signal.getsignal(n) is old for n,old in previous.items()) and scope.restoration_confirmed,
              'lease_held':world.system.acquired,'sdk_returned':returned.is_set(),'cancel_requested':token.requested,
              'write_calls':world.counts.get('write',0),'read_calls':world.counts.get('read',0),
              'control_calls':world.counts.get('control',0),
              'single_disposal_attempts':all(d.dispose_attempts==1 for d in world.devices),
              'service_stop_ack':result['simulated_service_stop_ack'],
              'normal_identity_matched':result['simulated_normal_identity_matched'],
              'physical_flags_false':all(result[n] is False for n in captureinspect.FALSE_COMMON|captureinspect.FALSE_PROFILE['owned']),
              'device_operations_performed':False,'native_sdk_imported':any(n=='usb' or n.startswith('usb.') or n=='libusb_package' for n in sys.modules)})
    finally:
        if monitor is not None:monitor.join(timeout=2)
        f.doCleanups()


if __name__=='__main__':main()
