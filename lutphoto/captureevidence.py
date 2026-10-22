"""Strict checkpoint/terminal contracts and bounded read-only inspection.

No device entry, SDK, archive execution or evidence repair. Reuses the existing
private reader, hash-chain and operation-graph checks. Native graph vocabulary
is normalized only inside the checker; reports are independent of simulations.
See ACKNOWLEDGEMENTS.md for QAQLeonard/ma1co/ajalt source provenance.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re

from . import captureinspect as i
from . import capturediagnostics as diagnostics

CHECKPOINT='native-checkpoint.private.json'
CHECKPOINT_SCHEMA='a7c2-native-capture-checkpoint/1'
LEGACY_RECEIPT_SCHEMA='a7c2-capture-terminal-receipt/1'
RECEIPT_SCHEMA='a7c2-capture-terminal-receipt/2'
KINDS=('native','self-made-sdk')
UNPROVEN=('physical_protocol_verified','body_binding_verified','chip_roles_verified','outer_wrapper_verified',
    'snapshot_freshness_verified','atomic_capture_verified','independent_media_verified','native_execution_verified',
    'restore_verified','write_plan_enabled','resume_allowed')
TO_NATIVE={'OWNED_HOST_BOUND_MODELED':'OWNER_FLOW_BOUND','OWNED_HANDLE_CLOSED_MODELED':'HANDLE_CLOSE_CONFIRMED',
    'RAW_AUTHENTICATION_MODELED':'AUTHENTICATION_COMPLETE','GUARD_ABSENCE_MODELED':'GUARDS_ABSENT',
    'NORMAL_SAME_SOURCE_MATCH_MODELED':'NORMAL_IDENTITY_MATCHED','HOST_WAIT_BEGIN_MODELED':'PASSIVE_WAIT_BEGIN',
    'HOST_WAIT_END_MODELED':'PASSIVE_WAIT_END'}
TO_GRAPH={value:key for key,value in TO_NATIVE.items()}
TO_GRAPH.update(CAPTURE_CONTEXT='NATIVE_BINDING_CANDIDATE_MODELED',CAPTURE_LOCKS_HELD='SYNTHETIC_LOCK_ORDER',
                PROGRAM_PAIR_MATCHED='PROGRAM_CONTENT_MATCHED')
SHARED_EVENTS={'INTENT','ACK','HOST_INTENT','HOST_ACK','HOST_FILE_VERIFIED','SNAPSHOT_FORMAT_CHECKED','READY_FOR_REPORT','NEEDS_REVIEW'}
NATIVE_EVENTS=SHARED_EVENTS|set(TO_GRAPH)
BOOLS={'outcome_unknown','blocked','program_pair_matched','transition_started','service_stop_ack','normal_identity_matched'}
COUNTS={'payload_bytes','wire_bytes','requests','identity_bytes','identity_queries','identity_raw_calls',
        'authentication_bytes','authentication_raw_calls','total_bytes','handles_opened','handles_closed'}
AUTH_PHASES=('NOT_STARTED','NEW','NORMAL_CONTROL_RETURNED','WAIT_SERVICE','SERVICE_CONTROL_RETURNED',
             'SERVICE_AUTHENTICATED','STOP_CONTROL_RETURNED','NORMAL_RETURN_MATCHED','NEEDS_REVIEW')
ERROR_STAGES=('body','healthy-exit','capture','owners','job-store','global-lease','signals','final-cancellation')


def _hex(value,length=64):return type(value) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}',value) is not None
def valid_error(value):return type(value) is str and re.fullmatch('[A-Za-z_][A-Za-z_0-9]{0,63}',value) is not None
def _false(value):return type(value) is dict and set(value)==set(UNPROVEN) and all(v is False for v in value.values())


def valid_context(value):
    return (type(value) is dict and set(value)=={'job_id','execution_kind','commit','archive_sha256',
        'firmware_declared','battery_percent_declared','resources_requested'} and _hex(value['job_id'],32)
        and type(value['execution_kind']) is str and value['execution_kind'] in KINDS
        and type(value['commit']) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}',value['commit']) is not None
        and (value['execution_kind']!='native' or _hex(value['commit'],40)) and _hex(value['archive_sha256'])
        and value['firmware_declared']=='2.01' and type(value['battery_percent_declared']) is int
        and 50<=value['battery_percent_declared']<=100 and type(value['resources_requested']) is bool)


def valid_receipt(value):
    fields={'schema','private_report','context','checkpoint','phase',
            'material_observations_complete','attempted','cleanup','cancel_requested','errors','unproven'}
    if type(value) is not dict or type(value.get('schema')) is not str:return False
    current=value['schema']==RECEIPT_SCHEMA
    if (value['schema'] not in (LEGACY_RECEIPT_SCHEMA,RECEIPT_SCHEMA)
            or set(value)!=fields|({'identity_diagnostics'} if current else set())
            or current and not diagnostics.valid_records(value['identity_diagnostics'])
            or value['private_report'] is not True or not valid_context(value['context'])
            or not _false(value['unproven']) or value['checkpoint'] is not None and not i._info(value['checkpoint'])
            or type(value['phase']) is not str or value['phase'] not in ('CAPTURE_COMPLETE','EXERCISE_COMPLETE','NEEDS_REVIEW')
            or type(value['material_observations_complete']) is not bool or type(value['cancel_requested']) is not bool):return False
    attempted,cleanup,errors=value['attempted'],value['cleanup'],value['errors']
    if (type(attempted) is not dict or set(attempted)!={'lease','job','device'} or any(type(v) is not bool for v in attempted.values())
            or attempted['device'] and not attempted['job'] or attempted['job'] and not attempted['lease']
            or type(cleanup) is not dict or set(cleanup)!={'owners','job_store','global_lease','signal_handlers'}
            or any(type(v) is not str or v not in ('CONFIRMED','UNCONFIRMED','NOT_ACQUIRED') for v in cleanup.values())
            or type(errors) is not list or len(errors)>64):return False
    for error in errors:
        if (type(error) is not dict or set(error)!={'stage','reason_type'} or type(error['stage']) is not str
                or error['stage'] not in ERROR_STAGES or not valid_error(error['reason_type'])):return False
    if current and value['identity_diagnostics']:
        if value['phase']!='NEEDS_REVIEW' or not errors:return False
        for record in value['identity_diagnostics']:
            if record['failure'] is not None and not any(error['reason_type']==record['failure']['reason_type'] for error in errors):return False
    if value['phase']!='NEEDS_REVIEW':
        phase='CAPTURE_COMPLETE' if value['context']['execution_kind']=='native' else 'EXERCISE_COMPLETE'
        return (value['phase']==phase and value['material_observations_complete'] and value['checkpoint'] is not None
            and all(attempted.values()) and all(v=='CONFIRMED' for v in cleanup.values()) and not errors and not value['cancel_requested'])
    return bool(errors or not value['material_observations_complete'] or value['checkpoint'] is None
                or any(v!='CONFIRMED' for v in cleanup.values()) or value['cancel_requested'])


def exit_code(receipt):
    """Success only after the complete terminal contract; no device action."""
    return 0 if valid_receipt(receipt) and receipt['phase'] in ('CAPTURE_COMPLETE','EXERCISE_COMPLETE') else 1


def _observation(value):
    return (type(value) is dict and set(value)=={'model','serial_source','serial_sha256','pid','bus','ports'}
        and value['model']=='ILCE-7CM2' and value['serial_source']=='sony-get-camera-info' and _hex(value['serial_sha256'])
        and type(value['pid']) is int and value['pid']==0x0e8a and type(value['bus']) is int and 1<=value['bus']<=255
        and type(value['ports']) is list and 1<=len(value['ports'])<=8
        and all(type(n) is int and 1<=n<=255 for n in value['ports']))


class _Evidence(i._Evidence):
    event_names=NATIVE_EVENTS

    def __init__(self):
        super().__init__();self.context=None;self.checkpoint_info=None;self.checkpoint=None
        self.program_positions=[];self.snapshot_positions=[];self.guard_positions=[]

    def details_valid(self,event,details):
        if event=='CAPTURE_CONTEXT':
            valid=self.context is None and self.count==0 and valid_context(details)
            if valid:self.context=details
            return valid
        if event=='CAPTURE_LOCKS_HELD':
            return set(details)=={'global_lease_present','job_lock_present'} and all(v is True for v in details.values())
        return super().details_valid(TO_GRAPH.get(event,event),details)

    def semantic_event(self,event,details):
        if event=='PROGRAM_PAIR_MATCHED':self.program_positions.append((len(self.acks),bool(self.pending or self.host_pending)))
        if event=='SNAPSHOT_FORMAT_CHECKED':self.snapshot_positions.append((details.get('file'),len(self.acks),bool(self.pending or self.host_pending)))
        if event=='GUARDS_ABSENT':self.guard_positions.append((len(self.acks),bool(self.pending or self.host_pending)))
        return TO_GRAPH.get(event,event),details

    def read_checkpoint(self,reader):
        if CHECKPOINT not in reader.inventory:self.problem('CHECKPOINT_MISSING');return False
        raw,self.checkpoint_info=reader.read(CHECKPOINT,131072,content=True)
        try:value=i._json(raw)
        except (ValueError,TypeError,RecursionError):self.problem('INVALID_CHECKPOINT');return False
        fields={'schema','private_report','context','phase','reason_type','checkpoint_only','files','observations','flow','journal','unproven'}
        if (set(value)!=fields or value['schema']!=CHECKPOINT_SCHEMA or value['private_report'] is not True
                or value['checkpoint_only'] is not True or not valid_context(value['context']) or value['context']!=self.context
                or type(value['phase']) is not str or value['phase'] not in ('MATERIALS_OBSERVED','NEEDS_REVIEW')
                or value['reason_type'] is not None and not valid_error(value['reason_type']) or not _false(value['unproven'])):
            self.problem('CHECKPOINT_SCHEMA_OR_CONTEXT',contradiction=True);return False
        self.checkpoint=value;flow=value['flow'];journal=value['journal'];observations=value['observations'];files=value['files']
        if (type(journal) is not dict or set(journal)!={'records','head_sha256'} or type(journal['records']) is not int
                or journal['records']!=self.count or journal['head_sha256']!=self.head):self.problem('CHECKPOINT_JOURNAL_DIFFERS',contradiction=True)
        if (type(flow) is not dict or set(flow)!=BOOLS|COUNTS|{'stage','authentication_phase'}
                or any(type(flow[k]) is not bool for k in BOOLS) or any(type(flow[k]) is not int or not 0<=flow[k]<=2**31 for k in COUNTS)
                or type(flow['stage']) is not str or flow['stage'] not in ('C0','C1','C2','C3','C4','C5')
                or type(flow['authentication_phase']) is not str or flow['authentication_phase'] not in AUTH_PHASES):
            self.problem('INVALID_FLOW',contradiction=True);return False
        if (flow['total_bytes']!=flow['payload_bytes']+flow['identity_bytes']+flow['authentication_bytes']
                or flow['identity_bytes']>65536 or flow['identity_queries']>2 or flow['identity_raw_calls']>28
                or flow['authentication_bytes']>32768 or flow['authentication_raw_calls']>31
                or not 0<=flow['handles_closed']<=flow['handles_opened']<=3):self.problem('FLOW_ACCOUNTING_DIFFERS',contradiction=True)
        if (type(observations) is not dict or set(observations)!={'initial','returned'}
                or any(v is not None and not _observation(v) for v in observations.values())):
            self.problem('INVALID_SOURCE_OBSERVATIONS',contradiction=True);return False
        if (type(files) is not dict or any(type(n) is not str or n not in i.MATERIALS or not i._info(v) for n,v in files.items())):
            self.problem('INVALID_CHECKPOINT_FILES',contradiction=True);return False
        for name,info in files.items():
            if self.actual.get(name)!=info:self.problem('CHECKPOINT_MATERIAL_DIFFERS',contradiction=True)
        if self.verified.keys()-files.keys():self.problem('CHECKPOINT_OMITS_VERIFIED_MATERIAL',contradiction=True)
        if files.keys()-self.verified.keys():self.problem('CHECKPOINT_HAS_UNJOURNALED_MATERIAL')
        self.unknown|=flow['outcome_unknown']
        if value['phase']=='NEEDS_REVIEW':self.problem('MATERIAL_OBSERVATIONS_INCOMPLETE');return False
        resources=self.context['resources_requested'];expected=set(i.CORE)|({'resources/'+n for n in i.RESOURCE_FILES} if resources else set())
        repeated=set(i.CORE[:2])|{n for n in expected if n.startswith('resources/')}
        payload=sum(info['bytes']*(2 if n in repeated else 1) for n,info in self.actual.items())+88
        host_operations=list(self.host_acks)
        waits=(self.active_wait is None and len(self.waits)==2 and [v[0] for v in self.waits]==['service','normal-return']
            and all(v[1]=='found' and 2<=v[2]<=40 for v in self.waits) and [v[5] for v in self.waits]==[3,len(self.acks)-1])
        for _,_,_,start,end,_ in reversed(self.waits):host_operations[start:end]=['INVENTORY']
        program_position=next((n for n,event in enumerate(self.events) if event=='PROGRAM_CONTENT_MATCHED'),-1)
        snapshot_position=next((n for n,event in enumerate(self.events) if event=='SNAPSHOT_FORMAT_CHECKED'),-1)
        plan=i._ack_plan('owned',resources)
        snapshots=[(name,n+1,False) for name,n in zip(i.CORE[2:],(n for n,op in enumerate(plan) if op in ('ram','saved')))]
        valid=(self.actual.keys()==files.keys()==self.verified.keys()==expected and not self.pending and not self.host_pending
            and not self.unknown and not flow['blocked'] and flow['program_pair_matched'] and value['reason_type'] is None
            and flow['stage']=='C5' and flow['transition_started'] and flow['service_stop_ack'] and flow['normal_identity_matched']
            and observations['initial'] is not None and observations['initial']==observations['returned']
            and self.events[-1:] == ['READY_FOR_REPORT'] and self.acks==i._ack_plan('owned',resources)
            and self.events.count('SNAPSHOT_FORMAT_CHECKED')==4 and self.events.count('GUARD_ABSENCE_MODELED')==2
            and self.events.count('SYNTHETIC_LOCK_ORDER')==1 and self.events.count('NORMAL_SAME_SOURCE_MATCH_MODELED')==1
            and self.events.count('PROGRAM_CONTENT_MATCHED')==1 and 0<program_position<snapshot_position
            and self.program_positions==[(plan.index('ram'),False)] and self.snapshot_positions==snapshots
            and self.guard_positions==[(plan.index('select:appFw.so'),False),(plan.index('service-stop'),False)]
            and 'NEEDS_REVIEW' not in self.events and flow['payload_bytes']==payload
            and flow['requests']==sum(op in ('hasp','ram','saved') or op.startswith(('read:','select:')) for op in self.acks)
            and flow['wire_bytes']>=payload+24*flow['requests'] and flow['authentication_bytes']==14448
            and flow['authentication_raw_calls']==31 and flow['authentication_phase']=='NORMAL_RETURN_MATCHED'
            and self.raw_auth_markers==1 and self.native_candidates==1 and self.owned_bindings==1 and waits
            and flow['identity_queries']==2 and flow['identity_raw_calls']==28 and 16930<=flow['identity_bytes']<=33728
            and flow['handles_opened']==flow['handles_closed']==3 and not self.raw_bindings and not self.raw_closes
            and i._host_sequence(host_operations,candidate=True)
            and [n for op,n in self.host_positions if op=='NORMAL_IDENTITY_QUERY']==[0,len(self.acks)-1]
            and [n for op,n in self.host_positions if op=='OPEN_HANDLE']==[0,3,len(self.acks)-1]
            and [n for op,n in self.host_positions if op=='DISPOSE_RESOURCES']==[3,len(self.acks)-1,len(self.acks)]
            and self.owned_closes=={'normal-initial':(3,False),'service':(len(self.acks)-1,False),'normal-return':(len(self.acks),False)})
        if not valid or self.issues:self.problem('COMPLETE_CHECKPOINT_WITH_INCOMPLETE_EVIDENCE',contradiction=True)
        return valid and not self.issues


def _read_receipt(path):
    """One explicit private ordinary file, bounded and unchanged; no search."""
    path,parent=i._parent(path)
    fd=None
    try:
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        try:fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:raise i._Refused('ACTIVE_RECEIPT') from None
        before=os.fstat(fd);i._private(before)
        if not 0<before.st_size<=131072:raise ValueError('Bounded receipt required')
        raw=bytearray()
        while len(raw)<=131072:
            block=os.read(fd,min(i.CHUNK,131073-len(raw)))
            if not block:break
            raw.extend(block)
        if (len(raw)!=before.st_size or i._stamp(before)!=i._stamp(os.fstat(fd))
                or i._stamp(before)!=i._stamp(os.stat(path.name,dir_fd=parent,follow_symlinks=False))):raise ValueError('Receipt changed')
        return i._json(bytes(raw))
    finally:
        error=None
        for handle in (fd,parent):
            if handle is None:continue
            try:os.close(handle)
            except BaseException as cleanup:
                if error is None:error=cleanup
        if error is not None:raise error


def _diagnostics_match(records,checkpoint):
    if not records:return True
    if checkpoint is None:return None  # Missing evidence cannot contradict an observed failure.
    if type(checkpoint.get('flow')) is not dict:return False
    flow=checkpoint['flow']
    for record in records:
        queries=1 if record['owner']=='normal-initial' else 2
        if flow.get('identity_queries')!=queries:return False
        failure=record['failure']
        if failure is None:continue  # Explicit recording error; no invented IO metadata.
        calls=14*(queries-1)+failure['call_number']-int(not failure['callback_attempted'])
        if flow.get('identity_raw_calls')!=calls:return False
        count=flow.get('identity_bytes')
        if type(count) is not int or count<failure['accepted_bytes'] or queries==1 and count!=failure['accepted_bytes']:return False
    return True


def inspect_directory(directory,*,receipt=None):
    """Inspect records, never confer hardware identity or recovery permission."""
    reader=evidence=None;material='INCOMPLETE';terminal='MISSING';kind=None;classification='NEEDS_REVIEW_INCOMPLETE';identity_diagnostics=None
    try:
        reader=i._Reader(directory);evidence=_Evidence()
        expected=set(i.MATERIALS)|{CHECKPOINT,'session.lock'}|{f'events/{n:08d}.json' for n in range(2048)}
        if reader.inventory-expected:evidence.problem('UNEXPECTED_ENTRY',contradiction=True)
        if set(i.FOLDERS)-reader.fds.keys():evidence.problem('PARTIAL_DIRECTORY_LAYOUT')
        evidence.journal(reader);evidence.materials(reader);complete=evidence.read_checkpoint(reader)
        kind=evidence.context['execution_kind'] if evidence.context else None
        if receipt is not None:
            value=_read_receipt(receipt)
            if (not valid_receipt(value) or value['context']!=evidence.context
                    or value['checkpoint']!=evidence.checkpoint_info
                    or evidence.checkpoint is not None and value['material_observations_complete']!=(evidence.checkpoint['phase']=='MATERIALS_OBSERVED')):
                evidence.problem('TERMINAL_BINDING_OR_SCHEMA',contradiction=True);terminal='INCONSISTENT'
            else:
                terminal='MATCHED_COMPLETE' if exit_code(value)==0 else 'MATCHED_FAILURE'
                if value['schema']==RECEIPT_SCHEMA:
                    matched=_diagnostics_match(value['identity_diagnostics'],evidence.checkpoint)
                    if matched is None:evidence.problem('IDENTITY_DIAGNOSTIC_UNBOUND')
                    elif not matched:
                        evidence.problem('IDENTITY_DIAGNOSTIC_DIFFERS',contradiction=True)
                    else:identity_diagnostics=value['identity_diagnostics']
        reader.check()
        if evidence.inconsistent:material='INCONSISTENT';classification='EVIDENCE_INCONSISTENT'
        elif evidence.pending or evidence.host_pending or evidence.unknown:material='UNKNOWN';classification='NEEDS_REVIEW_UNKNOWN'
        elif complete and not evidence.issues:
            material='CONSISTENT'
            classification=('CONSISTENT_CAPTURE_RECORDS' if kind=='native' else 'CONSISTENT_EXERCISE_RECORDS') if terminal=='MATCHED_COMPLETE' else ('NEEDS_REVIEW_TERMINAL_FAILURE' if terminal=='MATCHED_FAILURE' else 'NEEDS_REVIEW_TERMINAL_MISSING')
        else:classification='NEEDS_REVIEW_INCOMPLETE'
    except i._Refused as error:classification='REFUSED';refusal=str(error)
    except (OSError,ValueError,TypeError,RecursionError,KeyError,IndexError):classification='REFUSED';refusal='UNSAFE_UNREADABLE_OR_LIMITED_INPUT'
    except KeyboardInterrupt:classification='REFUSED';refusal='INSPECTION_INTERRUPTED'
    finally:
        if reader is not None:
            try:reader.close()
            except BaseException:classification='REFUSED';refusal='INSPECTION_RELEASE_UNCONFIRMED'
    return {'schema':'a7c2-readonly-capture-evidence-inspection/2','private_report':True,'classification':classification,
        'material_evidence':material,'terminal_evidence':terminal,'execution_kind_declared':kind,
        'identity_diagnostics':identity_diagnostics if classification not in ('REFUSED','EVIDENCE_INCONSISTENT') else None,
        'issues':sorted(evidence.issues) if evidence and classification!='REFUSED' else [refusal] if classification=='REFUSED' else [],
        'journal_records_checked':evidence.count if evidence else 0,'materials_hashed':len(evidence.actual) if evidence else 0,
        'inspection_only':True,'camera_operations_performed':False,'program_policy_revalidated':False,
        'source_archive_revalidated':False,'unproven':dict.fromkeys(UNPROVEN,False)}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True);command=sub.add_parser('inspect')
    command.add_argument('--directory',required=True);command.add_argument('--receipt');args=parser.parse_args(argv)
    result=inspect_directory(args.directory,receipt=args.receipt)
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0 if result['classification'] in ('CONSISTENT_CAPTURE_RECORDS','CONSISTENT_EXERCISE_RECORDS') else 1


if __name__=='__main__':raise SystemExit(main())
