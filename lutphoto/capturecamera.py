"""Explicit stock ILCE-7CM2 2.01 fixed-read capture and private receipt delivery.

No SDK, signals, USB, system lock or output creation on import/help. Uses the
single reviewed captureexecution assembly; no backend or enable switches.
QAQLeonard/ma1co/ajalt provenance and licenses: ACKNOWLEDGEMENTS.md.
"""
import argparse
import fcntl
import hashlib
import os
import sys
import unicodedata

from . import captureexecution as x, captureevidence as e
from .capturestore import CHUNK, _parent, _private, _same, encoded

SCHEMA='a7c2-camera-capture-cli-result/1'


class CaptureFailure(RuntimeError):
    def __init__(self,phase,error,*,started=False,secondary=()):
        super().__init__(phase)
        self.phase,self.reason_type,self.started=phase,x._error_name(error),started
        self.secondary=tuple(name if e.valid_error(name) else 'OtherError' for name in secondary)


class _Arguments(ValueError):pass


class _Parser(argparse.ArgumentParser):
    def error(self,message):raise _Arguments('Invalid arguments')


def _declarations(model,firmware,battery_percent,resources):
    if (type(model) is not str or model!='ILCE-7CM2' or type(firmware) is not str or firmware!='2.01'
            or type(battery_percent) is not int or not 50<=battery_percent<=100 or type(resources) is not bool):
        raise ValueError('Explicit supported model/version and actual battery required')


class _Receipt:
    """Reserve one new private ordinary file before any native construction.

    Never remove/overwrite/resume a partial file. The separate job is never
    reopened. Receipt graph readers refuse this file while its flock is held.
    """
    def __init__(self,path,directory):
        self.fd=self.parent=None;self.close_errors=[];self.closed=False
        job_parent=None
        try:
            job,job_parent=_parent(directory)
            self.path,self.parent=_parent(path)
            if self.path==job or job in self.path.parents:raise ValueError('Receipt must be outside job')
            if (_same(os.fstat(job_parent),os.fstat(self.parent))
                    and unicodedata.normalize('NFD',job.name).casefold()==unicodedata.normalize('NFD',self.path.name).casefold()):
                raise ValueError('Receipt aliases job name')
            _private(os.fstat(self.parent),True)
            self.fd=os.open(self.path.name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=self.parent)
            fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.check();os.fsync(self.fd);os.fsync(self.parent)
        except BaseException as error:
            try:self.close()
            except BaseException as cleanup:raise error from cleanup
            raise
        finally:
            if job_parent is not None:
                try:os.close(job_parent)
                except BaseException as error:
                    try:self.close()
                    except BaseException as cleanup:raise error from cleanup
                    raise

    def check(self):
        _private(os.fstat(self.parent),True);_private(os.fstat(self.fd))
        if (not _same(os.fstat(self.fd),os.stat(self.path.name,dir_fd=self.parent,follow_symlinks=False))
                or not _same(os.fstat(self.parent),os.stat(self.path.parent,follow_symlinks=False))):
            raise ValueError('Receipt entry changed')

    def save(self,receipt):
        if not e.valid_receipt(receipt) or receipt['context']['execution_kind']!='native':raise ValueError('Native terminal receipt required')
        raw=encoded(receipt)
        if len(raw)>131072:raise ValueError('Receipt exceeds bound')
        self.check()
        if os.fstat(self.fd).st_size!=0:raise ValueError('Empty reserved receipt required')
        view=memoryview(raw)
        while view:
            count=os.write(self.fd,view[:CHUNK])
            if type(count) is not int or not 0<count<=min(CHUNK,len(view)):raise OSError('Incomplete receipt write')
            view=view[count:]
        os.fsync(self.fd);os.lseek(self.fd,0,os.SEEK_SET)
        digest=hashlib.sha256();size=0
        while True:
            block=os.read(self.fd,min(CHUNK,len(raw)+1-size))
            if not block:break
            size+=len(block);digest.update(block)
            if size>len(raw):raise ValueError('Receipt grew')
        if size!=len(raw) or digest.digest()!=hashlib.sha256(raw).digest():raise ValueError('Receipt readback differs')
        self.check();os.fsync(self.parent)

    def close(self):
        if self.closed:return
        self.closed=True;fds=(self.fd,self.parent);self.fd=self.parent=None;errors=[]
        for fd in fds:
            if fd is None:continue
            try:os.close(fd)
            except BaseException as error:errors.append(error)
        self.close_errors=[x._error_name(error) for error in errors]
        if errors:raise errors[0]


def capture(archive,directory,receipt,*,model,firmware,battery_percent,resources=False):
    """Explicit device operation. Call only for an authorized owner capture.

    Returns the internal terminal receipt only after delivery/close succeeds.
    This is fixed reading with temporary service state changes, not installation.
    """
    destination=None;started=False;failure=None;result=None;secondary=[]
    try:
        _declarations(model,firmware,battery_percent,resources)
        prepared=x._prepare(archive,directory,firmware=firmware,battery_percent=battery_percent,resources=resources)
        destination=_Receipt(receipt,directory)
        started=True;result=x._run(prepared)
        destination.save(result)
    except BaseException as error:failure=error
    finally:
        if destination is not None:
            try:destination.close()
            except BaseException as cleanup:
                secondary.append(x._error_name(cleanup))
                if failure is None:failure=cleanup
    if failure is not None:
        phase='CAPTURE_OR_DELIVERY_UNCONFIRMED' if started else 'REFUSED_BEFORE_DEVICE'
        cause=failure.__cause__;seen={id(failure)}
        for _ in range(4):
            if cause is None or id(cause) in seen:break
            seen.add(id(cause));secondary.append(x._error_name(cause));cause=cause.__cause__
        for name in destination.close_errors if destination else ():
            if name not in secondary:secondary.append(name)
        error=CaptureFailure(phase,failure,started=started,secondary=secondary)
        if result is not None and e.valid_receipt(result) and result['errors']:
            # Delivery uncertainty must not erase a known body failure. The
            # phase still reports delivery failure and no retry is permitted.
            primary=result['errors'][0]['reason_type']
            error.secondary=(error.reason_type,)+error.secondary
            error.reason_type=primary
        raise error from failure
    return result


def _summary(phase,*,saved=False,started=False,reason=None,secondary=()):
    return {'schema':SCHEMA,'private_report':True,'phase':phase,'receipt_saved':saved,
        'camera_session_may_have_started':started,'reason_type':reason,'secondary_error_types':list(secondary),
        'write_plan_enabled':False,'restore_verified':False}


def _emit(result):
    raw=encoded(result).decode()
    if sys.stdout.write(raw)!=len(raw):raise OSError('Incomplete result output')
    sys.stdout.flush()


def main(argv=None):
    result=None;code=1
    try:
        parser=_Parser(prog='python -m lutphoto.capturecamera',description=__doc__,allow_abbrev=False)
        sub=parser.add_subparsers(dest='command',required=True,parser_class=_Parser)
        command=sub.add_parser('capture',allow_abbrev=False)
        for name in ('archive','directory','receipt','model','firmware'):command.add_argument('--'+name,required=True)
        command.add_argument('--battery-percent',required=True,type=int)
        command.add_argument('--resources',action='store_true');args=parser.parse_args(argv)
        # This checks only a known failed output stream, never promises that a
        # pipe or filesystem will stay writable after the device session.
        if not sys.stdout.writable():raise OSError('Result stream is not writable')
        sys.stdout.flush()
        try:
            receipt=capture(args.archive,args.directory,args.receipt,model=args.model,firmware=args.firmware,
                            battery_percent=args.battery_percent,resources=args.resources)
            code=e.exit_code(receipt)
            result=_summary(receipt['phase'],saved=True,started=receipt['attempted']['device'],
                            reason=receipt['errors'][0]['reason_type'] if receipt['errors'] else None)
        except CaptureFailure as error:
            result=_summary(error.phase,started=error.started,reason=error.reason_type,secondary=error.secondary)
    except _Arguments as error:
        code=2;result=_summary('INVALID_ARGUMENTS',reason=type(error).__name__)
    except (OSError,ValueError,TypeError,KeyboardInterrupt) as error:
        result=_summary('REFUSED_BEFORE_DEVICE',reason=x._error_name(error))
    try:_emit(result)
    except (OSError,ValueError,TypeError,KeyboardInterrupt) as error:
        primary=result['reason_type'] if result and result['reason_type'] else x._error_name(error)
        secondary=((x._error_name(error),)+tuple(result['secondary_error_types'])) if result and result['reason_type'] else ()
        failure=_summary('OUTPUT_UNCONFIRMED',saved=bool(result and result['receipt_saved']),
            started=bool(result and result['camera_session_may_have_started']),reason=primary,secondary=secondary)
        try:sys.stderr.write(encoded(failure).decode());sys.stderr.flush()
        except (OSError,ValueError,TypeError,KeyboardInterrupt):pass
        return 1
    return code


if __name__=='__main__':raise SystemExit(main())
