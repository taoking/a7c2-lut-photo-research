"""Explicit main-thread SIGINT/SIGTERM scope; no device or live entry.

The Python handler sets one flag. It never calls Event.set, raises, logs,
closes resources or kills a worker. Native calls may still block indefinitely.
"""
import signal
import threading

from .capturecontrol import Cancellation


class SignalScopeError(RuntimeError):
    pass


class SignalCancellation:
    """One standalone scope before acquiring any capture lease/job.

    Only default handlers are accepted. Embedded/custom/ignored handlers are
    refused; no callbacks, chaining, nested adoption or escalation switches.
    This scope is not automatically installed by any shipped entry point.
    """
    def __init__(self,token):
        if type(token) is not Cancellation:raise TypeError('Exact cooperative token required')
        self.token=token;self._handler=self._receive;self._previous={};self._installed=[]
        self._used=self._entered=False;self.restoration_confirmed=False

    def _receive(self,signum,frame):
        self.token._signal_requested=True

    def _restore(self,*,partial=False):
        failed=None
        for signum in reversed(self._installed):
            try:
                current=signal.getsignal(signum);previous=self._previous[signum]
                if partial and current is previous:continue
                if current is not self._handler:raise SignalScopeError('Signal handler ownership changed')
                signal.signal(signum,previous)
                if signal.getsignal(signum) is not previous:raise SignalScopeError('Signal restoration differs')
            except BaseException as exc:
                if failed is None:failed=exc
        self._installed.clear();self._entered=False
        self.restoration_confirmed=failed is None
        if failed is not None:raise SignalScopeError('Signal restoration is unconfirmed') from failed

    def __enter__(self):
        if self._used:raise SignalScopeError('Signal scope cannot be replayed')
        if threading.current_thread() is not threading.main_thread():raise SignalScopeError('Main thread required')
        self.token.check();self._used=True
        signals=(signal.SIGINT,signal.SIGTERM)
        self._previous={n:signal.getsignal(n) for n in signals}
        if (self._previous[signal.SIGINT] is not signal.SIG_DFL
                and self._previous[signal.SIGINT] is not signal.default_int_handler
                or self._previous[signal.SIGTERM] is not signal.SIG_DFL):
            raise SignalScopeError('Default standalone signal handlers required')
        try:
            for signum in signals:
                self._installed.append(signum)  # Also account for an unconfirmed install.
                previous=signal.signal(signum,self._handler)
                if previous is not self._previous[signum]:
                    self._previous[signum]=previous
                    raise SignalScopeError('Signal handler changed during installation')
                if signal.getsignal(signum) is not self._handler:
                    raise SignalScopeError('Signal installation is unconfirmed')
            self.token.check()
            self._entered=True;return self
        except BaseException as error:
            try:self._restore(partial=True)
            except SignalScopeError as cleanup:raise error from cleanup
            raise

    def __exit__(self,kind,error,traceback):
        if not self._entered:raise SignalScopeError('No active signal scope')
        if threading.current_thread() is not threading.main_thread():raise SignalScopeError('Main thread required')
        try:self._restore()
        except SignalScopeError as cleanup:
            if error is not None:raise error from cleanup
            raise
        return False
