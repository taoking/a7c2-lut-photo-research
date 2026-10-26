"""Explicit single service-snapshot probe; no program/resource capture or writes.

QAQLeonard 3.0.3 service-first identity, ma1co Senser/BK4 and ajalt hash
provenance: ACKNOWLEDGEMENTS.md. Uses the existing owned transport, fixed
authentication and bounded receiver. Import/help perform no device operation.
This separate result never substitutes for the full capture receipt.
"""
from array import array
from dataclasses import dataclass
import secrets
import sys

from . import capturecamera as c, captureexecution as x, captureidentity as identity
from . import captureauth as a, captureowned as o, bk4
from .capturecontrol import Cancellation
from .capturesignals import SignalCancellation
from .capturestore import Budget, Store, Sink, encoded

SCHEMA='a7c2-service-probe-result/1'
CLI_SCHEMA='a7c2-service-probe-cli-result/1'
SNAPSHOT='evidence/service-identity.bin'
UNPROVEN=('normal_identity_rechecked','program_fingerprints_verified','complete_backup',
          'restore_verified','write_plan_enabled','resume_allowed')


def _location(key):
    return {'pid':key.pid,'bus':key.bus,'ports':list(key.ports),'address':key.address}


class _ProbeHost(o.m._Host):
    """Same ownership/port rules, with explicitly absent initial body identity."""
    def normal(self):
        if self.stage!='NEW':raise RuntimeError('No second probe entry')
        self.stage='INITIAL_ATTEMPT'
        try:
            key=self._unique(o.m.NORMAL);self._unmount();self._unique(o.m.NORMAL,expected=key)
            owner=self._open(key)
            model=self.step('USB_PRODUCT_MODEL',lambda:_model(owner))
            # None means unknown body identity, not a substitute hash. Only the
            # inherited location/transition mechanics consume this tuple.
            self.initial=(key,None);self.stage='NORMAL_OPEN'
            return owner,model
        except BaseException:self.blocked=True;raise

    def normal_return(self):
        if self.stage!='SERVICE_DEPARTED' or any(not p.closed for p in self.owners):
            raise RuntimeError('Close service owner before passive return observation')
        self.stage='RETURN_ATTEMPT'
        key=self._wait(o.m.NORMAL)
        self._unique(o.m.NORMAL,expected=key)
        self.stage='RETURN_OBSERVED'
        return _location(key)  # No new configuration, claim, MSC query or authentication.


def _model(owner):
    """Two bounded standard USB string reads; no storage/Sony model query."""
    host=owner.host
    index=owner.device.iProduct
    if type(index) is not int or not 1<=index<=255:raise ValueError('USB product string index required')
    def string(index,language):
        try:
            host.check()
            if owner.closed or owner.unknown or not owner.claimed or host.ops.descriptor(owner.device)!=owner.profile:
                raise ValueError('Current claimed descriptor required')
            timeout=min(5000,int((host.budget.deadline-host.ops.clock())*1000))
            if timeout<=0:raise TimeoutError('Product observation deadline expired')
            raw=host.ops.control(owner.device,0x80,6,0x0300|index,language,254,timeout)
            host.check()
            if (type(raw) not in (bytes,array) or type(raw) is array and raw.typecode!='B'
                    or not 4<=len(raw)<=254 or len(raw)%2):raise ValueError('Bounded USB string bytes required')
            if type(raw) is array:raw=raw.tobytes()
            if raw[0]!=len(raw) or raw[1]!=3:raise ValueError('Complete USB string descriptor required')
            if host.ops.descriptor(owner.device)!=owner.profile:raise ValueError('Product descriptor changed')
            host.budget.accept(len(raw));return raw[2:]
        except BaseException:owner.unknown=True;raise
    language=int.from_bytes(host.step('USB_STRING_LANGIDS',lambda:string(0,0))[:2],'little')
    if not language:raise ValueError('USB language required')
    model=host.step('USB_PRODUCT_STRING',lambda:string(index,language)).decode('utf-16-le')
    if model!=identity.MODEL:raise ValueError('Observed USB model unsupported')
    return model


@dataclass(frozen=True)
class _Prepared:
    capture: object
    keys: object


def _prepare(archive,directory,*,firmware,battery_percent):
    prepared=x._prepare(archive,directory,firmware=firmware,battery_percent=battery_percent,resources=False)
    _,keys=a._keys(archive)  # All pinned source/key work finishes before native construction.
    channel=prepared.channel
    channel.requests={'ram':channel.requests['ram']}
    channel.guard_names=()
    channel.wire_limit=bk4.MAX_SNAPSHOT+65536
    return _Prepared(prepared,keys)


class _Run:
    def __init__(self,prepared,host,store,result):
        self.prepared,self.host,self.store,self.result=prepared,host,store,result
        self.channel=prepared.capture.channel
        self.ports=[];self.auth=[];self.service=None;self.stage='INITIAL'

    def event(self,name,**details):
        # Existing host wait names carry MODELED for historical reasons. This
        # separate journal states observations, never upgrades a legacy graph.
        name={'HOST_WAIT_BEGIN_MODELED':'USB_WAIT_BEGIN','HOST_WAIT_END_MODELED':'USB_WAIT_END'}.get(name,name)
        if name=='HOST_INTENT':self.result['last_host_operation']=details['operation']
        try:self.store.event(name,**details)
        except BaseException:self.host.blocked=True;raise

    def action(self,name,fn):
        self.stage=name;self.host.check();self.event('INTENT',operation=name)
        value=fn();self.host.check();self.event('ACK',operation=name);return value

    @property
    def unknown(self):
        return self.channel.unknown or any(p.unknown for p in self.ports+self.auth+self.host.owners)

    def authenticate(self,owner,label):
        port=o._OwnedPort(owner,self.channel);self.ports.append(port)
        auth=a._RawAuth(o.r._AuthView(port),self.prepared.keys,self.channel.budget);self.auth.append(auth)
        self.action(label+'_START',auth.control)
        def verify():
            auth.authenticate();port.authenticated=True
            self.result['facts'][label.lower()+'_authenticated']=True
        self.action(label+'_VERIFY',verify)
        return port,auth

    def body(self):
        owner,model=self.action('NORMAL_MODEL',self.host.normal)
        self.result['observations']['usb_model']=model
        self.result['observations']['initial_location']=_location(owner.key)
        self.authenticate(owner,'NORMAL')
        self.action('NORMAL_DEPART',lambda:self.host.departing(owner))
        owner=self.action('SERVICE_ARRIVAL',self.host.service)
        port,self.service=self.authenticate(owner,'SERVICE')
        spec=self.channel.requests['ram']
        sink=Sink(spec.limit,exact=spec.exact,budget=self.channel.budget,store=self.store,relative=SNAPSHOT)
        try:self.result['snapshot']=self.action('READ_RAM_SNAPSHOT',lambda:port.exchange('ram',sink))['payload']
        finally:sink.close()
        self.stage='DECODE_SERVICE_IDENTITY'
        raw=self.store.read(SNAPSHOT,self.result['snapshot'])
        observed=identity.from_snapshot(raw,model=model)
        self.result['observations']['service_identity']=observed
        self.result['facts']['snapshot_validated']=True
        self.event('SERVICE_IDENTITY_PARSED',source=observed['serial_source'])

    def exit(self):
        facts=self.result['facts']
        if (not facts['service_authenticated'] or facts['service_stop_attempted']
                or self.unknown or self.host.blocked or self.host.cancel.requested):return
        self.channel.claim_exit()
        def stop():
            facts['service_stop_attempted']=True
            self.service.control(stop=True);facts['service_stop_confirmed']=True
        self.action('SERVICE_STOP',stop)
        self.action('SERVICE_DEPART',lambda:self.host.departing(self.host.owners[-1]))
        returned=self.action('PASSIVE_NORMAL_RETURN',self.host.normal_return)
        self.result['observations']['returned_location']=returned
        facts['normal_usb_reappeared']=True


def _failure(result,stage,error):
    # Types and bounded numbers only; no exception text, payloads or paths.
    item={'stage':stage,'reason_type':x._error_name(error),'host_operation':result['last_host_operation']}
    for name in ('errno','backend_error_code'):
        try:value=getattr(error,name,None)
        except BaseException:value=None
        item[name]=value if type(value) is int and -65536<=value<=65536 else None
    result['errors'].append(item)


def _execute(prepared,host):
    p=prepared.capture
    if (type(prepared) is not _Prepared or type(host) is not _ProbeHost or type(host.ops) is not o.m._NativeOps
            or host.used or host.event is not None or host.owners or not host.wait_enabled
            or host.budget is not p.channel.budget or set(p.channel.requests)!={'ram'}):
        raise TypeError('Fresh fixed probe assembly required')
    result={'schema':SCHEMA,'private_report':True,'job_id':secrets.token_hex(16),
        'source':{'commit':p.policy.commit,'archive_sha256':p.policy.archive_sha},
        'declared':{'model':identity.MODEL,'firmware':p.firmware,'battery_percent':p.battery_percent},
        'phase':'NEEDS_REVIEW','snapshot':None,'journal':None,'last_host_operation':None,'host_diagnostics':[],
        'observations':dict.fromkeys(('usb_model','service_identity','initial_location','returned_location')),
        'facts':dict.fromkeys(('device_attempted','normal_authenticated','service_authenticated','snapshot_validated',
            'service_stop_attempted','service_stop_confirmed','normal_usb_reappeared','protocol_outcome_unknown'),False),
        'unproven':dict.fromkeys(UNPROVEN,False),
        'cleanup':dict.fromkeys(('owners','job_store','global_lease','signal_handlers'),False),'errors':[]}
    scope=SignalCancellation(host.cancel);store=run=None;entered=False
    try:
        with scope:
            try:
                host.__enter__();entered=True
                store=Store(p.directory,events_limit=512)
                run=_Run(prepared,host,store,result);host.event=run.event
                store.require_space(bk4.MAX_SNAPSHOT+512*16384+131072)
                run.event('SERVICE_PROBE_CONTEXT',job_id=result['job_id'],source=result['source'],declared=result['declared'])
                try:
                    result['facts']['device_attempted']=True;run.body()
                except BaseException as error:_failure(result,run.stage,error)
                try:run.exit()
                except BaseException as error:_failure(result,run.stage,error)
            except BaseException as error:_failure(result,'SETUP',error)
            finally:
                if run is not None and run.unknown:host.blocked=True
                # Close owners while the journal is still open, then the job,
                # then the global lease. No uncertain close is retried.
                for owner in reversed(host.owners):
                    try:owner.close()
                    except BaseException as error:_failure(result,'OWNER_CLOSE',error)
                if store is not None:
                    result['journal']={'records':store.seq,'head_sha256':store.head}
                    try:store.close()
                    except BaseException as error:_failure(result,'STORE_CLOSE',error)
                if entered:
                    try:host.__exit__(None,None,None)
                    except BaseException as error:_failure(result,'LEASE_CLOSE',error)
    except BaseException as error:_failure(result,'SIGNALS',error)
    try:host.cancel.check()
    except BaseException as error:_failure(result,'FINAL_CANCELLATION',error)
    result['facts']['protocol_outcome_unknown']=bool(run and run.unknown)
    result['host_diagnostics']=[] if host.inventory_diagnostic is None else [host.inventory_diagnostic]
    result['cleanup']={'owners':bool(host.owners) and all(owner.close_ok for owner in host.owners),
        'job_store':bool(store and store.close_confirmed),'global_lease':host.lease_release_confirmed,
        'signal_handlers':scope.restoration_confirmed}
    if (not result['errors'] and all(result['cleanup'].values())
            and all(result['facts'][k] for k in ('snapshot_validated','service_stop_confirmed','normal_usb_reappeared'))
            and not result['facts']['protocol_outcome_unknown']):result['phase']='PROBE_COMPLETE'
    return result


def _run(prepared):
    if type(prepared) is not _Prepared:raise TypeError('Fixed probe preparation required')
    p=prepared.capture;ops=o.m._NativeOps()
    p.channel.budget=Budget(bk4.MAX_SNAPSHOT+32768+512,seconds=120,clock=ops.clock)
    host=_ProbeHost(ops,None,firmware=p.firmware,battery_percent=p.battery_percent,
                    budget=p.channel.budget,cancel=Cancellation(),wait=True)
    return _execute(prepared,host)


class _Receipt(c._Receipt):
    def save(self,result):
        if (type(result) is not dict or result.get('schema')!=SCHEMA
                or result.get('unproven')!=dict.fromkeys(UNPROVEN,False)
                or result.get('phase') not in ('PROBE_COMPLETE','NEEDS_REVIEW')):
            raise ValueError('Separate probe result required')
        self._save_raw(encoded(result))


def probe(archive,directory,receipt,*,model,firmware,battery_percent):
    """Authorized single attempt only. Does not authorize a subsequent capture."""
    destination=result=None;started=False;failure=None;secondary=[]
    try:
        c._declarations(model,firmware,battery_percent,False)
        prepared=_prepare(archive,directory,firmware=firmware,battery_percent=battery_percent)
        destination=_Receipt(receipt,directory)
        started=True;result=_run(prepared);destination.save(result)
    except BaseException as error:failure=error
    finally:
        if destination is not None:
            try:destination.close()
            except BaseException as error:
                secondary.append(x._error_name(error))
                if failure is None:failure=error
    if failure is not None:
        error=c.CaptureFailure('PROBE_OR_DELIVERY_UNCONFIRMED' if started else 'REFUSED_BEFORE_DEVICE',
            failure,started=started,secondary=secondary)
        if result and result['errors']:
            error.secondary=(error.reason_type,)+error.secondary;error.reason_type=result['errors'][0]['reason_type']
        raise error from failure
    return result


def _summary(phase,**kwargs):
    result=c._summary(phase,**kwargs);result['schema']=CLI_SCHEMA
    result.update(complete_backup=False,program_fingerprints_verified=False,normal_identity_rechecked=False)
    return result


def main(argv=None):
    result=None;code=1
    try:
        parser=c._Parser(prog='python -m lutphoto.captureprobe',description=__doc__,allow_abbrev=False)
        for name in ('archive','directory','receipt','model','firmware'):parser.add_argument('--'+name,required=True)
        parser.add_argument('--battery-percent',required=True,type=int);args=parser.parse_args(argv)
        if not sys.stdout.writable():raise OSError('Result stream not writable')
        sys.stdout.flush()
        value=probe(**vars(args));code=0 if value['phase']=='PROBE_COMPLETE' else 1
        result=_summary(value['phase'],saved=True,started=value['facts']['device_attempted'],
                        reason=value['errors'][0]['reason_type'] if value['errors'] else None)
    except c._Arguments as error:code=2;result=_summary('INVALID_ARGUMENTS',reason=x._error_name(error))
    except c.CaptureFailure as error:
        result=_summary(error.phase,started=error.started,reason=error.reason_type,secondary=error.secondary)
    except (OSError,ValueError,TypeError,KeyboardInterrupt) as error:
        result=_summary('REFUSED_BEFORE_DEVICE',reason=x._error_name(error))
    try:c._emit(result)
    except (OSError,ValueError,TypeError,KeyboardInterrupt) as error:
        failure=_summary('OUTPUT_UNCONFIRMED',saved=bool(result and result['receipt_saved']),
            started=bool(result and result['camera_session_may_have_started']),
            reason=result['reason_type'] if result and result['reason_type'] else x._error_name(error))
        try:sys.stderr.write(encoded(failure).decode());sys.stderr.flush()
        except (OSError,ValueError,TypeError,KeyboardInterrupt):pass
        return 1
    return code


if __name__=='__main__':raise SystemExit(main())
