"""Restricted raw I/O and single-owner lifecycle on exact synthetic devices.

QAQLeonard/ma1co protocol and ajalt hash provenance: ACKNOWLEDGEMENTS.md.
No USB imports, device discovery, kernel operations, real handles or CLI.
Endpoint numbers are bound from an explicit descriptor, never guessed.
"""
from array import array
import struct

from . import captureauth as a, capturepipeline as p
from .captureprotocol import OfflineChannel
from .capturestore import Budget


class SyntheticDevice:
    """Own fake PyUSB-shaped results, not a wrapper around a device/callback.

    Authentication and framed material replies share this SAME fake object.
    Written packets and challenges stay in private memory; never serialize it.
    """
    def __init__(self, pid, auth, peer, *, descriptor=None, faults=None, arrays=True):
        if (type(auth) is not a.SyntheticDriver or auth.pid != pid or auth.used or auth.trace
                or type(peer) is not p.s.SyntheticPeer or type(arrays) is not bool
                or type(pid) is not int or pid not in (0x0e8a,0x0336)):
            raise TypeError('Exact unused synthetic authentication and peer required')
        faults = {} if faults is None else faults
        if (type(faults) is not dict or len(faults)>16 or any(type(k) is not tuple or len(k)!=2
                or k[0] not in ('control','write','read','close') or type(k[1]) is not int or not 1<=k[1]<=65536
                or callable(v) for k,v in faults.items())):
            raise ValueError('Bounded explicit fake raw results required')
        default = (0x054c,pid,0,0,8,6,0x50,((0x81,2),(0x02,2))) if pid==0x0e8a else (
            0x054c,pid,0,0,0xff,0,0,((0x83,2),(0x04,2)))
        self.descriptor = default if descriptor is None else descriptor
        self.pid, self.auth, self.peer, self.arrays = pid,auth,peer,arrays
        self.faults, self.trace, self.counts, self.written = dict(faults),[],{},[]
        self.closed, self._pending, self._selected, self._requests = False,None,None,{}

    def _record(self, kind, endpoint=0, timeout=0):
        if self.closed: raise RuntimeError('Synthetic raw handle already closed')
        self.trace.append((kind,endpoint,timeout))
        self.counts[kind]=self.counts.get(kind,0)+1

    def _result(self, kind, value):
        result = self.faults.get((kind,self.counts[kind]),value)
        if isinstance(result,BaseException): raise result
        return result

    def ctrl_transfer(self, request_type, request, value, index, raw, *, timeout):
        self._record('control',timeout=timeout)
        return self._result('control',self.auth.control_out(request_type,request,value,index,raw,timeout))

    def write(self, endpoint, raw, *, timeout):
        self._record('write',endpoint,timeout); self.written.append(raw)
        if self.auth.used < 15: value=self.auth.write(raw,timeout)
        else:
            size,pfunc,seq,*flags=struct.unpack('<IHH4B',raw[:12])
            data=raw[12:]
            if size!=len(data) or any(flags): raise ValueError('Invalid own material request')
            if data==b'\x01\x10\x11\0\0\xff\0':
                name='read:'+self._selected; self._selected=None
            else:
                candidates=[n for n,spec in self._requests.items() if spec.data==data and spec.pfunc==pfunc and not n.startswith('read:')]
                if len(candidates)!=1: raise ValueError('Unknown own fixed material packet')
                name,=candidates
                if name.startswith('select:'): self._selected=name[7:]
            spec=self._requests[name]
            if data!=spec.data or pfunc!=spec.pfunc: raise ValueError('Own fixed request differs')
            self._pending=iter(self.peer.reply(name,raw)); value=len(raw)
        return self._result('write',value)

    def read(self, endpoint, maximum, *, timeout):
        self._record('read',endpoint,timeout)
        value=self.auth.read(maximum,timeout) if self.auth.used<15 else next(self._pending)
        if self.arrays and type(value) is bytes: value=array('B',value)
        return self._result('read',value)

    def close(self):
        self._record('close'); self.closed=True  # Never retry an ambiguous local close.
        return self._result('close',True)


def _descriptor(device):
    if type(device) is not SyntheticDevice: raise TypeError('Exact synthetic raw device required')
    value=device.descriptor
    if (type(value) is not tuple or len(value)!=8 or any(type(n) is not int for n in value[:7])
            or value[:4]!=(0x054c,device.pid,0,0) or type(value[7]) is not tuple or len(value[7])!=2
            or not all(0<=n<=255 for n in value[4:7])
            or (value[4:7]!=(8,6,0x50) if device.pid==0x0e8a else value[4]!=0xff)):
        raise ValueError('Unreviewed configuration/interface descriptor')
    for ep in value[7]:
        if (type(ep) is not tuple or len(ep)!=2 or any(type(n) is not int for n in ep)
                or ep[1]!=2 or ep[0]&0x70 or not 1<=ep[0]&0x0f<=15 or not 0<ep[0]<=0x8f):
            raise ValueError('Unique bulk endpoints required')
    incoming=[ep[0] for ep in value[7] if ep[0]&0x80]
    outgoing=[ep[0] for ep in value[7] if not ep[0]&0x80]
    if len(incoming)!=1 or len(outgoing)!=1: raise ValueError('Ambiguous bulk endpoints')
    return value,incoming[0],outgoing[0]


class _Port:
    """Sole owner; only internal fixed auth/OfflineChannel capabilities use it."""
    def __init__(self, device, budget, channel):
        self._descriptor,self._in,self._out=_descriptor(device)
        if type(budget) is not Budget or type(channel) is not OfflineChannel or channel.budget is not budget:
            raise TypeError('One exact shared channel/budget required')
        self._device,self.budget,self.channel=device,budget,channel
        device._requests=channel.requests
        self.started=self.authenticated=self.stopped=self.unknown=self.closed=self.close_attempted=False
        self.close_ok=False

    def _ready(self):
        if self.closed or self.unknown or self._device.closed: raise RuntimeError('Closed or unknown raw port; no further I/O')
        self.budget.check()
        if _descriptor(self._device)[0]!=self._descriptor: raise ValueError('Bound descriptor changed')

    def _io(self, kind, data=None, *, maximum=0, timeout=5000):
        try:
            self._ready()
            if type(timeout) is not int or timeout<=0: raise ValueError('Explicit remaining timeout required')
            remaining=int((self.budget.deadline-self.budget.clock())*1000)
            duration=min(5000,timeout,remaining)
            if duration<=0: raise TimeoutError('Shared raw I/O deadline expired')
            if kind=='control': result=self._device.ctrl_transfer(*data,b'',timeout=duration)
            elif kind=='write': result=self._device.write(self._out,data,timeout=duration)
            else: result=self._device.read(self._in,maximum,timeout=duration)
            if kind in ('control','write'):
                if type(result) is not int or result!=(0 if kind=='control' else len(data)):
                    raise ValueError('Explicit full raw transfer length required')
            else:
                if type(result) not in (bytes,array) or type(result) is array and result.typecode!='B' or len(result)>maximum:
                    raise ValueError('Bounded byte result required before conversion')
                result=result if type(result) is bytes else result.tobytes()
            self._ready()
            return result
        except BaseException:
            self.unknown=True
            raise

    def exchange(self, name, sink):
        if not self.authenticated or self.stopped: raise RuntimeError('No authenticated material capability')
        try:
            self._ready()
            packet=self.channel.begin(name,sink)
            self._io('write',packet)
            while self.channel.active:
                want=self.channel.next_read()
                self.channel.feed(self._io('read',maximum=want.maximum,timeout=want.timeout_ms))
            return self.channel.result
        except BaseException:
            if self.channel.active: self.channel.abort()
            self.unknown |= self.channel.unknown
            raise

    def close(self):
        if self.close_attempted: return
        self.close_attempted=self.closed=True  # Invalidate every borrowed view BEFORE close.
        try:
            if self._device.close() is not True: raise ValueError('Local close unconfirmed')
            self.close_ok=True
        except BaseException:
            self.unknown=True
            raise


class _AuthView:
    def __init__(self, port): self._port,self.pid,self.trace=port,port._device.pid,[]

    def control_out(self, request_type, request, value, index, raw, timeout_ms):
        port=self._port; control=(request_type,request,value,index)
        if raw!=b'' or control not in (a.START,a.STOP): raise ValueError('Fixed auth control only')
        if control==a.START:
            if port.started or port.stopped: raise RuntimeError('No second raw start')
            port.started=True
        else:
            if self.pid!=0x0336 or not port.authenticated or port.stopped: raise RuntimeError('No healthy raw stop allowance')
            port.stopped=True
        self.trace.append(('control',timeout_ms))
        return port._io('control',control,timeout=timeout_ms)

    def write(self, raw, timeout_ms):
        port=self._port
        if (not port.started or port.authenticated or port.stopped or type(raw) is not bytes or len(raw)!=516
                or a.AUTH.unpack(raw)[0] not in (0xfffe,0xfffc,0xfffa) or a.AUTH.unpack(raw)[1]!=0):
            raise ValueError('Fixed authentication packet only')
        self.trace.append(('write',timeout_ms));return port._io('write',raw,timeout=timeout_ms)

    def read(self, maximum, timeout_ms):
        port=self._port
        if not port.started or port.authenticated or port.stopped or maximum!=516: raise ValueError('Fixed auth response only')
        self.trace.append(('read',timeout_ms));return port._io('read',maximum=maximum,timeout=timeout_ms)


class _RawFlow(a.OfflineAuthFlow):
    def normal_auth(self, view):
        if self.phase!='NEW' or self.unknown or self.blocked: raise RuntimeError('No raw normal replay')
        if type(view) is not _AuthView or view.pid!=0x0e8a: raise TypeError('Exact bound auth view required')
        self._normal_stage(view);view._port.authenticated=True

    def service_auth(self, observation, view):
        if type(view) is not _AuthView or view.pid!=0x0336: raise TypeError('Exact bound service view required')
        self._service_stage(observation,view);view._port.authenticated=True


class _Run(p._Run):
    def __init__(self, archive,store,peer,channel,policy,normal,service):
        self.ports=(_Port(normal,channel.budget,channel),_Port(service,channel.budget,channel))
        super().__init__(archive,store,peer,channel,policy,*(_AuthView(port) for port in self.ports))
        self.bound=False;self.receipts=set()

    def preflight(self, resources):
        super().preflight(resources)
        self.event('RAW_HANDLES_BOUND_MODELED',owned_handles=2,same_service_handle=True)
        self.bound=True

    def make_auth(self, value): return _RawFlow(self.archive,self.store,value,budget=self.channel.budget)

    def sync_auth(self):
        self.unknown |= any(port.unknown for port in self.ports)
        super().sync_auth()

    def wire(self, name, sink=None):
        return self.call(name,lambda:self.ports[1].exchange(name,sink),wire=True)

    def _close_port(self, index):
        port=self.ports[index]
        try: port.close()
        except BaseException:
            self.blocked=True
            raise
        if self.bound and port.close_ok and index not in self.receipts:
            self.receipts.add(index)  # No receipt retry after journal failure.
            self.event('RAW_HANDLE_CLOSED_MODELED',role='normal-initial' if index==0 else 'service')

    def close_handle(self, role):
        self._close_port(0 if role=='normal' else 1)
        super().close_handle(role)

    def failure_close(self):
        # Host resource release only; never stop/reset/reattach/release-interface.
        for index in (1,0):
            try: self._close_port(index)
            except BaseException: self.blocked=True
        self.service_open=self.normal_open=False


def rehearse(archive,directory,peer,normal_device,service_device,*,resources=False):
    """Exact fake raw handles only; ownership begins after new Store creation."""
    if (type(peer) is not p.s.SyntheticPeer or type(resources) is not bool or peer.trace or peer.counts
            or any(type(d) is not SyntheticDevice or d.closed or d.trace or d.auth.used or d.auth.trace
                   or d.peer is not peer for d in (normal_device,service_device))
            or normal_device.pid!=0x0e8a or service_device.pid!=0x0336):
        raise TypeError('Fresh exact same-peer raw devices required')
    _descriptor(normal_device);_descriptor(service_device)
    if peer.version!='2.01' or type(peer.battery) is not int or not 50<=peer.battery<=100:
        raise ValueError('Synthetic preflight version/battery rejected')
    policy=p.programidentity._load_policy(archive)
    channel=OfflineChannel(archive,resources=resources,guards=True)
    channel.budget.limit+=p.AUTH_ALLOWANCE
    return p._execute(directory,peer,lambda store:_Run(archive,store,peer,channel,policy,normal_device,service_device),resources=resources)
