"""Owned host/auth/material integration on EXACT self-made systems only.

Pinned QAQLeonard/ma1co/ajalt provenance: ACKNOWLEDGEMENTS.md. No live entry,
SDK import, policy/driver callback, camera/global-lock operation or CLI.
"""
from array import array
from dataclasses import dataclass

from . import captureauth as a, capturemac as m, capturemsc, captureraw as r
from . import capturepipeline as p, capturesession as s, programidentity
from .captureprotocol import OfflineChannel
from .capturecontrol import Cancellation, ObservationTimeout
from .capturestore import Budget, Store, encoded

REPORT='owned-report.private.json'
IDENTITY_ALLOWANCE=65536


@dataclass
class _Handle:
    pid: int
    identity: list
    protocol: object=None
    used: int=0
    closed: bool=False


class SyntheticSystem:
    """Own in-memory OS results and three fake handles, never native callbacks.

    Identity tapes contain explicit (write/read, bytes/exception) records.
    They are independent packet oracles, not cached decoded identities.
    Secret challenges, packets and source identities remain private memory.
    """
    def __init__(self,peer,normal,service,initial_identity,returned_identity,*,locations=None,faults=None,arrivals=None):
        if (type(peer) is not s.SyntheticPeer or any(type(d) is not r.SyntheticDevice or d.peer is not peer
                or d.closed or d.trace or d.auth.used or d.auth.trace for d in (normal,service))
                or normal.pid!=m.NORMAL or service.pid!=m.SERVICE or peer.trace or peer.counts):
            raise TypeError('Exact fresh peer and same-peer synthetic raw devices required')
        r._descriptor(normal);r._descriptor(service)
        for tape in (initial_identity,returned_identity):
            if (type(tape) is not list or not 1<=len(tape)<=14 or any(type(v) is not tuple or len(v)!=2
                    or v[0] not in ('write','read') or type(v[1]) is not bytes and not isinstance(v[1],BaseException)
                    or type(v[1]) is bytes and len(v[1])>8192 for v in tape)):
                raise TypeError('Bounded own identity packet tapes required')
        self.keys=(m._Key(m.NORMAL,1,(1,2),4),m._Key(m.SERVICE,1,(1,2),5),m._Key(m.NORMAL,1,(1,2),6)) if locations is None else locations
        if type(self.keys) is not tuple or len(self.keys)!=3 or any(type(k) is not m._Key for k in self.keys):
            raise TypeError('Three explicit synthetic USB keys required')
        faults={} if faults is None else faults
        if (type(faults) is not dict or len(faults)>32 or any(type(k) is not tuple or len(k)!=2 or type(k[0]) is not str
                or type(k[1]) is not int or not 1<=k[1]<=65536 or callable(v) for k,v in faults.items())):
            raise ValueError('Bounded own host fault results required')
        arrivals={} if arrivals is None else arrivals
        if (type(arrivals) is not dict or any(type(k) is not int or k not in (1,2) or type(v) is not tuple or not 1<=len(v)<=42
                or any(type(row) is not tuple or len(row)>2 or any(type(key) is not m._Key for key in row) for row in v) for k,v in arrivals.items())):
            raise TypeError('Bounded own transition inventory tapes required')
        self.arrivals=dict(arrivals);self.arrival_index={1:0,2:0}
        self.peer,self.normal_device,self.service_device=peer,normal,service
        self.handles=(_Handle(m.NORMAL,list(initial_identity),normal),_Handle(m.SERVICE,[],service),_Handle(m.NORMAL,list(returned_identity)))
        self.faults=dict(faults);self.trace=[];self.counts={};self.phase=0;self.now=0;self.mounted=True;self.acquired=False;self.started=False

    def _record(self,name):
        self.trace.append(name);self.counts[name]=self.counts.get(name,0)+1
        result=self.faults.get((name,self.counts[name]))
        if isinstance(result,BaseException):raise result
        return result

    def _result(self,name,default):
        value=self._record(name)
        return value if (name,self.counts[name]) in self.faults else default

    def clock(self):return self.now
    def sleep(self,seconds):self.now+=seconds
    def acquire(self):
        if self.started:raise RuntimeError('No host-system replay')
        self.started=True;self._record('global-acquire');self.acquired=True;return 1
    def unlock(self,fd):
        if fd!=1 or not self.acquired:raise RuntimeError('No held modeled lock')
        self.acquired=False;return self._record('global-release')
    def inventory(self):
        values=self.arrivals.get(self.phase)
        default=(self.keys[self.phase],)
        if values:
            index=self.arrival_index[self.phase];default=values[min(index,len(values)-1)];self.arrival_index[self.phase]+=1
        return self._result('inventory',default)
    def media(self,seconds):
        return self._result('media',(100,{'disk9':('disk9',True,self.mounted),'disk9s1':('disk9',False,self.mounted)}))
    def unmount(self,disk,seconds):
        if disk!='disk9':raise ValueError('Unknown own fake disk')
        self._record('unmount');self.mounted=False;return b''
    def open(self,key):
        self._record('open')
        if key!=self.keys[self.phase]:raise ValueError('Own fake key changed')
        return self.handles[self.phase]
    def descriptor(self,d):
        value=d.protocol.descriptor if d.protocol is not None else (0x054c,m.NORMAL,0,0,8,6,80,((129,2),(2,2)))
        return self._result('descriptor',value)
    def active(self,d):return self._result('active',d.pid==m.NORMAL)
    def detach(self,d):return self._record('detach')
    def attach(self,d):return self._record('attach')
    def claim(self,d):return self._record('claim')
    def release(self,d):return self._record('release')
    def dispose(self,d):
        if d.closed:raise RuntimeError('No repeated fake SDK disposal')
        d.closed=True
        if d.protocol is not None:d.protocol.closed=True
        return self._record('dispose')
    def _identity(self,d,kind,value):
        if d.closed or d.used>=len(d.identity):raise RuntimeError('No fake identity transfer allowance')
        operation,want=d.identity[d.used];d.used+=1
        if operation!=kind:raise ValueError('Own identity transfer order differs')
        if isinstance(want,BaseException):raise want
        if kind=='write':
            if value!=want:raise ValueError('Independent MSC packet oracle differs')
            return len(value)
        if len(want)>value:raise ValueError('Own fake identity response exceeds request')
        return array('B',want)
    def write(self,d,ep,data,timeout):
        self._record('write')
        return self._identity(d,'write',data) if d.used<len(d.identity) else d.protocol.write(ep,data,timeout=timeout)
    def read(self,d,ep,size,timeout):
        self._record('read')
        return self._identity(d,'read',size) if d.used<len(d.identity) else d.protocol.read(ep,size,timeout=timeout)
    def control(self,d,*args):
        self._record('control');*request,timeout=args
        if d.closed or d.used<len(d.identity):raise RuntimeError('No authentication before fresh identity query')
        return d.protocol.ctrl_transfer(*request,timeout=timeout)
    def service_arrival(self):
        if self.phase!=0 or not self.handles[0].closed or self.normal_device.auth.used!=15:raise RuntimeError('No modeled service arrival allowance')
        self._record('simulate-service-arrival');self.phase=1
    def normal_arrival(self):
        if self.phase!=1 or not self.handles[1].closed or self.service_device.auth.used!=16:raise RuntimeError('No modeled normal arrival allowance')
        self._record('simulate-normal-arrival');self.phase=2;self.mounted=True


def _observation(key,identity=None):
    value={'bus':key.bus,'ports':list(key.ports),'pid':key.pid,
           'normal_count':int(key.pid==m.NORMAL),'service_count':int(key.pid==m.SERVICE)}
    return value if identity is None else value|identity|{'manufacturer':'Sony'}


class _OwnedPort(r._Port):
    """Borrowed protocol capability; SDK disposal belongs solely to _Owner."""
    def __init__(self,owner,channel):
        self.owner,self.channel,self.budget,self.pid=owner,channel,channel.budget,owner.key.pid
        if owner.host.budget is not self.budget:raise TypeError('One host/auth/material budget required')
        self.started=self.authenticated=self.stopped=self.unknown=False
        if type(owner.device) is _Handle and owner.device.protocol is not None:
            owner.device.protocol._requests=channel.requests

    def _ready(self):
        o=self.owner
        if o.closed or o.unknown or o.transition or o.host.blocked or not o.claimed or self.unknown:
            raise RuntimeError('Stopped owned protocol capability')
        o.host.check()
        if o.host.ops.descriptor(o.device)!=o.profile:raise ValueError('Owned descriptor changed')
        o.host.check()

    def _io(self,kind,data=None,*,maximum=0,timeout=5000):
        try:
            self._ready();remaining=int((self.budget.deadline-self.budget.clock())*1000)
            if type(timeout) is not int or not 0<timeout or remaining<=0:raise TimeoutError('Owned protocol deadline expired')
            timeout=min(5000,timeout,remaining);o=self.owner;ops=o.host.ops
            if kind=='control':result=ops.control(o.device,*data,b'',timeout)
            elif kind=='write':result=ops.write(o.device,o.outgoing,data,timeout)
            elif kind=='read':result=ops.read(o.device,o.incoming,maximum,timeout)
            else:raise ValueError('Fixed owned I/O kind required')
            if kind!='read':
                if type(result) is not int or result!=(0 if kind=='control' else len(data)):raise ValueError('Explicit full owned transfer required')
            else:
                if type(result) not in (bytes,array) or type(result) is array and result.typecode!='B' or len(result)>maximum:
                    raise ValueError('Bounded owned byte response required')
                result=result if type(result) is bytes else result.tobytes()
            self._ready();return result
        except BaseException:
            self.unknown=self.owner.unknown=True;raise

    def close(self):raise RuntimeError('Borrowed capability cannot dispose its owner')


class _Flow(r._RawFlow):
    def _observe_return(self,observation):
        try:return super()._observe_return(observation)
        except ObservationTimeout as exc:
            if self.host.last_wait_timeout is exc:
                # Known polling failure does not erase the earlier stop receipt.
                # Its unacknowledged observation still stays unknown to inspection.
                self.unknown=any(stage.unknown for stage in (self.normal,self.service) if stage is not None)
                self.blocked=True;self.phase='STOP_CONTROL_RETURNED'
            raise


class _Run(p._Run):
    def __init__(self,archive,store,system,host,channel,policy):
        s._Run.__init__(self,store,system.peer,channel,policy)
        self.archive,self.system,self.host=archive,system,host
        self.auth=None;self.drivers=[];self.ports=[];self.receipts=set();self.blocked=False
        self.cleanup_error_type=None

    def call(self,name,action,*,wire=False):
        before=self.unknown
        try:return super().call(name,action,wire=wire)
        except ObservationTimeout as exc:
            if not wire and self.host.last_wait_timeout is exc:
                self.unknown=before or self.channel.unknown or any(owner.unknown for owner in self.host.owners)
                self.blocked=True
            raise

    def sync_auth(self):
        self.unknown|=any(o.unknown for o in self.host.owners)
        self.blocked|=self.host.blocked
        super().sync_auth()

    def _port(self,owner):
        port=_OwnedPort(owner,self.channel);view=r._AuthView(port)
        self.ports.append(port);self.drivers.append(view);return view

    def arrive_service(self):
        self.host.step('SIMULATE_SERVICE_ARRIVAL',self.system.service_arrival)

    def arrive_normal(self):
        self.host.step('SIMULATE_NORMAL_ARRIVAL',self.system.normal_arrival)

    def body(self,resources):
        self.preflight(resources)
        self.event('OWNED_HOST_BOUND_MODELED',owned_handles=3,same_service_handle=True)
        owner,identity=self.call('normal-before',self.host.normal)
        value=_observation(owner.key,identity);self.initial=s._normal(value);self.stage='C1'
        view=self._port(owner);self.auth=_Flow(self.archive,self.store,value,budget=self.channel.budget);self.auth.host=self.host
        try:self.auth.normal_auth(view)
        finally:self.sync_auth()
        self._depart(owner,'normal-initial')
        self.arrive_service()
        service=self.call('service-observation',self.host.service)
        try:self.auth.service_auth(_observation(service.key),self._port(service))
        finally:self.sync_auth()
        self.event('RAW_AUTHENTICATION_MODELED',accepted_auth_bytes=self.auth.accepted_bytes,raw_calls=sum(len(d.trace) for d in self.drivers))
        self.stage='C2';self.materials(resources)

    def wire(self,name,sink=None):return self.call(name,lambda:self.ports[1].exchange(name,sink),wire=True)

    def _receipt(self,owner,role):
        if owner.close_ok and role not in self.receipts:
            self.receipts.add(role);self.event('OWNED_HANDLE_CLOSED_MODELED',role=role)

    def _depart(self,owner,role):
        self.host.departing(owner);self._receipt(owner,role)

    def exit(self):
        self.sync_auth()
        if not self.authenticated or self.unknown or self.blocked or self.exit_attempted:return
        self.channel.claim_exit()
        try:self.auth.stop()
        finally:self.sync_auth()
        self._depart(self.host.owners[1],'service')
        self.arrive_normal()
        def returned():
            value=self.host.normal_return();return _observation(self.host.owners[-1].key,value)
        try:self.auth._observe_return(returned)
        finally:self.sync_auth()
        self.event('NORMAL_SAME_SOURCE_MATCH_MODELED')
        owner=self.host.owners[-1];owner.close();self._receipt(owner,'normal-return')

    def failure_close(self):
        self.sync_auth()
        if self.unknown or self.blocked:self.host.blocked=True
        roles=('normal-initial','service','normal-return')
        for index in reversed(range(len(self.host.owners))):
            owner=self.host.owners[index]
            try:
                owner.close();self._receipt(owner,roles[index])
            except BaseException as exc:
                self.blocked=True
                if self.cleanup_error_type is None:self.cleanup_error_type=type(exc).__name__
        self.normal_open=self.service_open=False

    def report(self,complete,reason=None):
        result=super().report(complete,reason)
        identity=sum(o.identity_bytes for o in self.host.owners)
        result.update(schema='a7c2-synthetic-owned-capture/1',phase='SIMULATED_OWNED_CAPTURE_COMPLETE' if complete else 'NEEDS_REVIEW',
            accepted_payload_bytes=result['accepted_payload_bytes']-identity,accepted_identity_bytes=identity,
            identity_queries=sum(o.queried for o in self.host.owners),identity_raw_calls=sum(o.identity_calls for o in self.host.owners),
            owned_handles_opened=len(self.host.owners),owned_handles_closed=sum(o.close_ok for o in self.host.owners),
            host_binding_modeled=True,host_blocked=self.host.blocked,cleanup_error_type=self.cleanup_error_type)
        return result


def _prepare(archive,system,resources,cancel):
    """Shared fixed-source preparation; no host action or public backend hook."""
    if (type(system) is not SyntheticSystem or type(resources) is not bool or system.started or system.trace
            or system.peer.trace or system.peer.counts or any(d.closed or d.trace or d.auth.used or d.auth.trace
                for d in (system.normal_device,system.service_device))):
        raise TypeError('Fresh exact synthetic system required')
    cancel=Cancellation() if cancel is None else cancel
    if type(cancel) is not Cancellation:raise TypeError('Exact cooperative token required')
    cancel.check()
    peer=system.peer
    if peer.version!='2.01' or type(peer.battery) is not int or not 50<=peer.battery<=100:raise ValueError('Synthetic supported version/battery required')
    capturemsc.verify_sources(archive)  # Before even modeled host acquisition.
    policy=programidentity._load_policy(archive)
    channel=OfflineChannel(archive,resources=resources,guards=True)
    channel.budget=Budget(channel.budget.limit+p.AUTH_ALLOWANCE+IDENTITY_ALLOWANCE,clock=system.clock)
    return cancel,policy,channel


def _execute(archive,directory,system,host,channel,policy,*,resources,run_type=_Run):
    """Internal lifecycle shared by exact-fake rehearsals, never a live entry."""
    store=run=None
    host.__enter__()
    try:
        store=Store(directory,events_limit=s.EVENTS_LIMIT)
        run=run_type(archive,store,system,host,channel,policy);host.event=run.event
        try:
            run.body(resources);run.sync_auth()
            if not run.returned or run.blocked or run.unknown or channel.active or any(not o.close_ok for o in host.owners):
                raise RuntimeError('Owned lifecycle incomplete')
            host.check();run.event('READY_FOR_REPORT')
            for name,info in {**run.files,**store.documents}.items():store.verify(name,info)
            result=run.report(True);store.put(REPORT,encoded(result));return result
        except BaseException as exc:
            run.sync_auth()
            if run.authenticated and not run.unknown and not run.blocked and not run.exit_attempted:
                try:run.exit()
                except BaseException:pass
            run.failure_close();result=run.report(False,type(exc).__name__)
            try:
                run.event('NEEDS_REVIEW',reason_type=type(exc).__name__,outcome_unknown=run.unknown)
                result=run.report(False,type(exc).__name__);store.put(REPORT,encoded(result))
            except BaseException:pass
            return result
    finally:
        # No live owner may outlast its job journal. Close all before Store,
        # then close the real private job flock, then release the modeled lease.
        try:
            if run is not None:run.failure_close()
        finally:
            try:
                if store is not None:store.close()
            finally:host.__exit__(*__import__('sys').exc_info())


def rehearse(archive,directory,system,*,resources=False,cancel=None):
    """One new private job on an exact unused synthetic system; no backend hook."""
    cancel,policy,channel=_prepare(archive,system,resources,cancel)
    host=m._Host(system,None,firmware=system.peer.version,battery_percent=system.peer.battery,
                 budget=channel.budget,cancel=cancel,wait=True)
    return _execute(archive,directory,system,host,channel,policy,resources=resources)
