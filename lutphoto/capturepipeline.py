"""Synthetic raw authentication plus fixed material capture; no live backend.

Reuses pinned QAQLeonard/ma1co contracts, host storage and bounded framing.
No USB/global-lock opening, callbacks, policy injection, retry or device CLI.
"""
from . import captureauth as a, capturesession as s, programidentity
from .captureprotocol import OfflineChannel
from .capturestore import Store, encoded

AUTH_ALLOWANCE = 32768  # Fixed protocol consumes 14,448; never used for materials alone.
REPORT = 'pipeline-report.private.json'


class _Run(s._Run):
    def __init__(self, archive, store, peer, channel, policy, normal, service):
        super().__init__(store, peer, channel, policy)
        self.archive, self.drivers = archive, (normal, service)
        self.auth, self.blocked = None, False

    def event(self, event, **details):
        try: self.store.event(event, **details)
        except BaseException:
            self.blocked = True
            raise

    def call(self, name, action, *, wire=False):
        if self.blocked: raise RuntimeError('Blocked synthetic pipeline; no further I/O')
        return super().call(name, action, wire=wire)

    def sync_auth(self):
        self.unknown |= self.channel.unknown
        if self.auth is None: return
        self.unknown |= self.auth.unknown
        self.blocked |= self.auth.blocked
        self.transition = bool(self.drivers[0].trace)
        self.authenticated = self.auth.phase == 'SERVICE_AUTHENTICATED' and not self.unknown and not self.blocked
        self.exit_attempted = self.auth.exit_attempted
        self.stop_ack |= self.auth.phase in ('STOP_CONTROL_RETURNED', 'SYNTHETIC_RETURN_MATCHED')
        self.returned |= self.auth.phase == 'SYNTHETIC_RETURN_MATCHED'

    def body(self, resources):
        self.preflight(resources)
        value = self.call('normal-before', self.peer.normal)
        self.normal_open = True
        self.initial = s._normal(value)
        self.stage = 'C1'
        self.auth = a.OfflineAuthFlow(self.archive, self.store, value, budget=self.channel.budget)
        try: self.auth.normal_auth(self.drivers[0])
        finally: self.sync_auth()
        self.normal_open = False
        self.peer.step('close-normal')
        service = self.call('service-observation', self.peer.observe_service)
        self.service_open = True
        try: self.auth.service_auth(service, self.drivers[1])
        finally: self.sync_auth()
        self.event('RAW_AUTHENTICATION_MODELED', accepted_auth_bytes=self.auth.accepted_bytes,
                   raw_calls=sum(len(d.trace) for d in self.drivers))
        self.stage = 'C2'
        self.materials(resources)

    def exit(self):
        self.sync_auth()
        if not self.authenticated or self.unknown or self.blocked or self.exit_attempted: return
        self.channel.claim_exit()  # Local allowance only; never sends stop itself.
        try: self.auth.stop()
        finally: self.sync_auth()
        self.service_open = False
        self.peer.step('close-service')
        # INTENT must precede even the fake normal query, not just comparison.
        self.normal_open = True
        try: self.auth._observe_return(lambda: self.peer.normal(True))
        finally: self.sync_auth()
        self.event('NORMAL_SAME_SOURCE_MATCH_MODELED')

    def report(self, complete, reason=None):
        self.sync_auth()
        result = super().report(complete, reason)
        auth_bytes = self.auth.accepted_bytes if self.auth is not None else 0
        result.update(schema='a7c2-synthetic-authenticated-capture/1',
            phase='SIMULATED_AUTHENTICATED_CAPTURE_COMPLETE' if complete else 'NEEDS_REVIEW',
            accepted_payload_bytes=self.channel.budget.used - auth_bytes,
            accepted_auth_bytes=auth_bytes, accepted_total_bytes=self.channel.budget.used,
            auth_raw_calls=sum(len(d.trace) for d in self.drivers),
            authentication_phase=self.auth.phase if self.auth is not None else 'NOT_STARTED',
            shared_budget_modeled=True, pipeline_blocked=self.blocked,
            actual_authentication_verified=False, fresh_normal_observation_verified=False, resume_allowed=False)
        return result


def rehearse(archive, directory, peer, normal_driver, service_driver, *, resources=False):
    """New output, exact own peer/drivers only; cannot accept an actual Session."""
    if (type(peer) is not s.SyntheticPeer or type(resources) is not bool
            or type(normal_driver) is not a.SyntheticDriver or normal_driver.pid != 0x0e8a
            or type(service_driver) is not a.SyntheticDriver or service_driver.pid != 0x0336
            or peer.trace or peer.counts or any(d.trace or d.used for d in (normal_driver, service_driver))):
        raise TypeError('Fresh exact synthetic peer and normal/service drivers required')
    if peer.version != '2.01' or type(peer.battery) is not int or not 50 <= peer.battery <= 100:
        raise ValueError('Synthetic preflight version/battery rejected')
    policy = programidentity._load_policy(archive)
    channel = OfflineChannel(archive, resources=resources, guards=True)
    # One existing 1200s deadline, established before storage/identity/auth.
    # Auth packets and material payload share quota; material wire overhead
    # remains separately bounded by OfflineChannel, never counted twice.
    channel.budget.limit += AUTH_ALLOWANCE
    store = run = None
    peer.step('global-lock-acquire')  # Model only, never open the system lock.
    try:
        store = Store(directory, events_limit=s.EVENTS_LIMIT)
        run = _Run(archive, store, peer, channel, policy, normal_driver, service_driver)
        try:
            run.body(resources)
            if not run.returned or run.blocked or run.unknown or run.channel.active:
                raise RuntimeError('Synthetic pipeline lacks a healthy completed return')
            if run.normal_open:
                run.normal_open = False; peer.step('close-normal')
            run.event('READY_FOR_REPORT')
            for name, info in {**run.files, **store.documents}.items(): store.verify(name, info)
            result = run.report(True)
            store.put(REPORT, encoded(result))
            return result
        except BaseException as exc:
            run.sync_auth()
            if run.authenticated and not run.unknown and not run.blocked and not run.exit_attempted:
                try: run.exit()
                except BaseException: pass
            result = run.report(False, type(exc).__name__)
            try:
                run.event('NEEDS_REVIEW', reason_type=type(exc).__name__, outcome_unknown=run.unknown)
                result = run.report(False, type(exc).__name__)
                store.put(REPORT, encoded(result))
            except BaseException: pass
            return result
    finally:
        try:
            if run is not None:
                if run.service_open:
                    run.service_open = False; peer.step('close-service')
                if run.normal_open:
                    run.normal_open = False; peer.step('close-normal')
        finally:
            try:
                if store is not None: store.close()
            finally: peer.step('global-lock-release')
