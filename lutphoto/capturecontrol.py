"""Cooperative host cancellation, never a device interrupt or retry permit."""
import threading


class OperationCancelled(InterruptedError):
    pass


class Cancellation:
    """Exact token, no callback, reason text, signal handler or worker kill."""
    def __init__(self):self._event=threading.Event()
    def cancel(self):self._event.set()
    @property
    def requested(self):return self._event.is_set()
    def check(self):
        if self.requested:raise OperationCancelled('Cooperative capture cancellation observed')


class ObservationTimeout(TimeoutError):
    """A completed polling interval found no stable expected device.

    This says nothing about camera state, successful exit or safe retry.
    Consumers must also verify that their own host emitted this instance.
    """
    def __init__(self,phase):
        if phase not in ('service','normal-return'):raise ValueError('Fixed observation phase required')
        self.phase=phase
        super().__init__('Expected-device observation interval expired')
