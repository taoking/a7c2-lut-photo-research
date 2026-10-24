"""Internal native capture assembly used by the explicit camera frontend.

Uses the existing host/protocol/owner core, not a second transport. Legacy
capturecandidate.capture still refuses unconditionally. Tests replace only
the existing native SDK/system surfaces. QAQLeonard/ma1co/ajalt provenance:
ACKNOWLEDGEMENTS.md. No SDK import, signals or locks at module import time.
"""
import re
import secrets
from dataclasses import dataclass

from . import captureowned as o, capturepreflight, bk4
from .capturecontrol import Cancellation
from .capturesignals import SignalCancellation
from .capturestore import Budget, Store, encoded
from . import captureevidence as e


def _error_name(error):
    name=type(error).__name__
    return name if re.fullmatch('[A-Za-z_][A-Za-z_0-9]{0,63}',name) else 'OtherError'


class _CaptureRun(o._OwnedRun):
    """Owner-based execution with independent checkpoint semantics."""
    def __init__(self,*args,context):
        super().__init__(*args)
        self.context=context;self.program_marker=False

    def event(self,name,**details):
        # These are reviewed graph markers, not a converted synthetic report.
        name=e.TO_NATIVE.get(name,name)
        if name not in e.NATIVE_EVENTS:raise ValueError('Unsupported capture event')
        return super().event(name,**details)

    def preflight(self,resources):
        maximum=(self.stock.ap_bytes+self.stock.cp_bytes+4*bk4.MAX_SNAPSHOT
                 +(68*o.s.c.MAX_RESOURCE if resources else 0)+o.s.EVENTS_LIMIT*16384+131072)
        if self.host.lock is None or self.store.lock is None:raise RuntimeError('Capture locks required')
        self.event('CAPTURE_CONTEXT',**self.context)
        self.event('CAPTURE_LOCKS_HELD',global_lease_present=True,job_lock_present=True)
        self.store.require_space(maximum)

    def snapshot(self,*args,**kwargs):
        if self.programs_matched and not self.program_marker:
            self.event('PROGRAM_PAIR_MATCHED',kind='stock');self.program_marker=True
        return super().snapshot(*args,**kwargs)

    def report(self,*args,**kwargs):
        raise RuntimeError('Native checkpoint cannot use a synthetic report')

    def _observation(self,returned):
        value=self.host.returned_observation if returned else (self.host.initial[1] if self.host.initial else None)
        if value is None:return None
        key=self.host.owners[-1].key if returned else self.host.initial[0]
        return dict(value,pid=key.pid,bus=key.bus,ports=list(key.ports))

    def checkpoint(self,complete,reason):
        self.sync_auth()
        identity=sum(owner.identity_bytes for owner in self.host.owners)
        auth_bytes=self.auth.accepted_bytes if self.auth is not None else 0
        phase=self.auth.phase if self.auth is not None else 'NOT_STARTED'
        return {'schema':e.CHECKPOINT_SCHEMA,'private_report':True,'context':dict(self.context),
            'phase':'MATERIALS_OBSERVED' if complete else 'NEEDS_REVIEW','reason_type':reason,
            'checkpoint_only':True,'files':dict(self.files),
            'observations':{'initial':self._observation(False),'returned':self._observation(True)},
            'flow':{'stage':self.stage,'outcome_unknown':self.unknown,'blocked':self.blocked,
                'program_pair_matched':self.programs_matched,'transition_started':self.transition,
                'service_stop_ack':self.stop_ack,'normal_identity_matched':self.returned,
                'authentication_phase':'NORMAL_RETURN_MATCHED' if phase=='SYNTHETIC_RETURN_MATCHED' else phase,
                'payload_bytes':self.channel.budget.used-identity-auth_bytes,'wire_bytes':self.channel.wire_bytes,
                'requests':self.channel.calls,'identity_bytes':identity,
                'identity_queries':sum(owner.queried for owner in self.host.owners),
                'identity_raw_calls':sum(owner.identity_calls for owner in self.host.owners),
                'authentication_bytes':auth_bytes,'authentication_raw_calls':sum(len(d.trace) for d in self.drivers),
                'total_bytes':self.channel.budget.used,'handles_opened':len(self.host.owners),
                'handles_closed':sum(owner.close_ok for owner in self.host.owners)},
            'journal':{'records':self.store.seq,'head_sha256':self.store.head},
            'unproven':dict.fromkeys(e.UNPROVEN,False)}


def _execute(archive,directory,host,channel,policy,*,resources,firmware,battery_percent,execution_kind):
    """Private fixed assembly. A receipt is returned AFTER every scope exits.

    It is not written by reopening the job after its lock has been released.
    No public backend override, replay, hard cancellation or automatic retry.
    """
    context={'job_id':secrets.token_hex(16),'execution_kind':execution_kind,
        'commit':policy.commit,'archive_sha256':policy.archive_sha,'firmware_declared':firmware,
        'battery_percent_declared':battery_percent,'resources_requested':resources}
    if not e.valid_context(context):raise ValueError('Explicit capture prerequisites required')
    if (type(host) is not o.m._Host or type(host.ops) is not o.m._NativeOps
            or host.budget is not channel.budget or host.used or host.owners or host.event is not None
            or not host.wait_enabled or host.firmware_declared!=firmware or host.battery_percent_declared!=battery_percent):
        raise TypeError('Fresh native host and shared budget required')
    errors=[];store=run=None;info=None;complete=False;lease_entered=False
    attempted={'lease':False,'job':False,'device':False}
    scope=SignalCancellation(host.cancel)
    def failed(stage,error):
        seen=set()
        for _ in range(4):
            if error is None or id(error) in seen:break
            seen.add(id(error));errors.append({'stage':stage,'reason_type':_error_name(error)})
            error=error.__cause__
    def record_names(stage,names):
        recorded=[value for value in errors if value['stage']==stage]
        for name in names:
            value={'stage':stage,'reason_type':name if e.valid_error(name) else 'OtherError'}
            if value in recorded:recorded.remove(value)
            else:errors.append(value)
    try:
        with scope:
            try:
                attempted['lease']=True;host.__enter__();lease_entered=True
                attempted['job']=True;store=Store(directory,events_limit=o.s.EVENTS_LIMIT)
                run=_CaptureRun(archive,store,host,channel,policy,context=context);host.event=run.event
                try:
                    attempted['device']=True;run.body(resources);run.sync_auth()
                    if (not run.returned or not run.programs_matched or run.blocked or run.unknown or channel.active
                            or len(host.owners)!=3 or any(not owner.close_ok for owner in host.owners)):
                        raise RuntimeError('Capture observations incomplete')
                    host.check();run.event('READY_FOR_REPORT')
                    for name,value in {**run.files,**store.documents}.items():store.verify(name,value)
                    complete=True
                except BaseException as error:
                    failed('body',error);run.sync_auth()
                    if (run.authenticated and not run.unknown and not run.blocked and not run.exit_attempted
                            and not host.cancel.requested):
                        try:run.exit()
                        except BaseException as cleanup:failed('healthy-exit',cleanup)
                run.failure_close()
                if not complete:
                    run.event('NEEDS_REVIEW',reason_type=errors[0]['reason_type'],outcome_unknown=run.unknown)
                info=store.put(e.CHECKPOINT,encoded(run.checkpoint(complete,errors[0]['reason_type'] if errors else None)))
            except BaseException as error:failed('capture',error)
            finally:
                if run is not None:
                    try:run.failure_close()
                    except BaseException as error:failed('owners',error)
                for owner in host.owners:record_names('owners',owner.close_error_types)
                if store is not None:
                    try:store.close()
                    except BaseException as error:failed('job-store',error)
                    record_names('job-store',store.close_error_types)
                if lease_entered:
                    try:host.__exit__(None,None,None)
                    except BaseException as error:failed('global-lease',error)
                record_names('global-lease',host.cleanup_error_types)
    except BaseException as error:failed('signals',error)
    try:host.cancel.check()
    except BaseException as error:failed('final-cancellation',error)
    cleanup={'owners':('CONFIRMED' if all(owner.close_ok for owner in host.owners) else 'UNCONFIRMED') if host.owners else 'NOT_ACQUIRED',
        'job_store':('CONFIRMED' if store.close_confirmed else 'UNCONFIRMED') if store is not None else ('UNCONFIRMED' if attempted['job'] else 'NOT_ACQUIRED'),
        'global_lease':('CONFIRMED' if host.lease_release_confirmed else 'UNCONFIRMED') if host.lease_acquired else ('UNCONFIRMED' if attempted['lease'] else 'NOT_ACQUIRED'),
        'signal_handlers':'CONFIRMED' if scope.restoration_confirmed else 'UNCONFIRMED'}
    success=(complete and info is not None and not errors and all(value=='CONFIRMED' for value in cleanup.values()))
    receipt={'schema':e.RECEIPT_SCHEMA,'private_report':True,'context':context,'checkpoint':info,
        'phase':('CAPTURE_COMPLETE' if execution_kind=='native' else 'EXERCISE_COMPLETE') if success else 'NEEDS_REVIEW',
        'material_observations_complete':complete,'attempted':attempted,'cleanup':cleanup,
        'cancel_requested':host.cancel.requested,'errors':errors,'unproven':dict.fromkeys(e.UNPROVEN,False),
        'identity_diagnostics':[dict(owner.identity_diagnostic,owner='normal-initial' if n==0 else 'normal-return')
                                for n,owner in enumerate(host.owners) if owner.identity_diagnostic is not None],
        'host_diagnostics':[] if host.inventory_diagnostic is None else [host.inventory_diagnostic]}
    # A bounded terminal result, not a claim that stdout/process exit is atomic.
    if not e.valid_receipt(receipt):raise RuntimeError('Invalid internal terminal receipt')
    return receipt


@dataclass(frozen=True)
class _Prepared:
    archive: object
    directory: object
    firmware: str
    battery_percent: int
    resources: bool
    policy: object
    channel: object


def _prepare(archive,directory,*,firmware,battery_percent,resources=False):
    """Source/local checks before output reservation or NativeOps construction."""
    if (type(firmware) is not str or firmware!='2.01' or type(battery_percent) is not int
            or not 50<=battery_percent<=100 or type(resources) is not bool):
        raise ValueError('Supported firmware and actual battery required')
    checked=capturepreflight.inspect(archive,directory,resources=resources)
    if checked['phase']!='OFFLINE_PREFLIGHT_CHECKED' or not checked['environment']['administrator_context_present']:
        raise ValueError('Local native prerequisites incomplete')
    policy=o.programidentity._load_policy(archive)
    channel=o.OfflineChannel(archive,resources=resources,guards=True)
    channel.budget=Budget(channel.budget.limit+o.p.AUTH_ALLOWANCE+o.IDENTITY_ALLOWANCE)
    return _Prepared(archive,directory,firmware,battery_percent,resources,policy,channel)


def _run(prepared):
    """The single fixed native assembly; no injected ops, runner or clock."""
    if type(prepared) is not _Prepared:raise TypeError('Internal preparation required')
    token=Cancellation();ops=o.m._NativeOps()
    host=o.m._Host(ops,None,firmware=prepared.firmware,battery_percent=prepared.battery_percent,
                   budget=prepared.channel.budget,cancel=token,wait=True)
    return _execute(prepared.archive,prepared.directory,host,prepared.channel,prepared.policy,
                    resources=prepared.resources,firmware=prepared.firmware,
                    battery_percent=prepared.battery_percent,execution_kind='native')


def _capture(archive,directory,*,firmware,battery_percent,resources=False):
    """Internal convenience wrapper; public device calls use capturecamera."""
    return _run(_prepare(archive,directory,firmware=firmware,battery_percent=battery_percent,resources=resources))
