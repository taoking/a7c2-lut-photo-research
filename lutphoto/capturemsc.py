"""Bounded, fixed MSC identity query; pinned QAQLeonard/ma1co provenance.

No USB import, discovery, authentication, firmware writes or retry. Raw
callbacks below are INTERNAL host-owner bindings, never a public CLI backend.
"""
from array import array
import hashlib
import io
import json
import struct
import zipfile

from . import captureauth as a, customcontracts as c, workercontracts as w
from .capturestore import Budget

CBW = struct.Struct('<4sIIBBB16s')
CSW = struct.Struct('<4sIIB')
EXT = struct.Struct('<IHH8x')
INFO_COMMAND = b'\x7a\x01\0\0\0' + bytes(7)
INFO_REQUEST = EXT.pack(0,1,0).ljust(8192,b'\0')
PIN = w.ROOT/'research/upstream-host.lock.json'


def verify_sources(archive):
    baseline,shared=a._sources(archive)
    pin=json.loads(c.bounded_read(PIN,32768))
    if (pin['schema']!='a7c2-host-source-audit/1' or pin['camera_integration_enabled'] is not False
            or set(pin['files'])!=set(shared)|{'src/fl23/vendor/pmca/usb/__init__.py','src/fl23/vendor/pmca/usb/driver/__init__.py'}
            or any(pin[k]!=baseline[k] for k in ('repository','tag','commit','archive_sha256','archive_bytes','baseline_lock_sha256'))):
        raise ValueError('Host source inventory differs')
    raw=c.bounded_read(archive,pin['archive_bytes'])
    if len(raw)!=pin['archive_bytes'] or hashlib.sha256(raw).hexdigest()!=pin['archive_sha256']:
        raise ValueError('Host archive differs')
    result={}
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        for name,spec in pin['files'].items():
            if name.startswith('/') or '..' in name.split('/') or not 0<spec['bytes']<=100000:
                raise ValueError('Invalid host source member')
            value=package.read('a7c2-tools-2.1/'+name)
            blob=hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest()
            if len(value)!=spec['bytes'] or hashlib.sha256(value).hexdigest()!=spec['sha256'] or blob!=spec['git_blob_sha1']:
                raise ValueError('Host source member differs')
            if name in shared and value!=shared[name]:raise ValueError('Shared source differs')
            result[name]=value
    return pin,result


class CompleteMscError(ValueError):
    """Complete CSW reports failure; no REQUEST SENSE or busy retry follows."""


def decode_identity(inquiry,response):
    """Same serial source/encoding as SonyExtCmdCamera.getCameraInfo.

    Plist/model-code/trailing data are bounded and skipped, never interpreted
    as a firmware version or retained in a report.
    """
    if type(inquiry) is not bytes or not 32<=len(inquiry)<=255 or inquiry[8:16].decode('latin1').rstrip(' \0')!='Sony':
        raise ValueError('Sony SCSI inquiry required')
    if type(response) is not bytes or not EXT.size<=len(response)<=8192:raise ValueError('Bounded Sony model response required')
    size,_,_=EXT.unpack_from(response)
    if not 4<=size<=len(response)-EXT.size:raise ValueError('Sony model payload length differs')
    body=response[EXT.size:EXT.size+size]
    plist_size=struct.unpack_from('<I',body)[0]
    at=4+plist_size+4
    if at>=len(body):raise ValueError('Truncated model record')
    length=body[at];at+=1
    if length==0 or at+length+9>len(body):raise ValueError('Missing model/code/serial bytes')
    model=body[at:at+length].decode('latin1');at+=length+5
    if model!='ILCE-7CM2':raise ValueError('Unsupported Sony model')
    # Legacy info.serial is binascii.hexlify(raw_four_bytes).decode('latin1').
    digest=hashlib.sha256(body[at:at+4].hex().encode('ascii')).hexdigest()
    return {'model':model,'serial_source':'sony-get-camera-info','serial_sha256':digest}


class _Query:
    def __init__(self,write,read,budget):
        if type(budget) is not Budget:raise TypeError('Shared host Budget required')
        self._write,self._read,self.budget=write,read,budget
        self.unknown=self.blocked=False;self.transactions=self.calls=self.accepted_bytes=0

    def _io(self,kind,value,*,minimum=None):
        if self.unknown or self.blocked:raise RuntimeError('Stopped MSC identity query')
        try:
            self.budget.check()
            maximum=len(value) if kind=='write' else value
            if self.budget.used+maximum>self.budget.limit:raise ValueError('Identity transfer budget exceeded')
            timeout=min(5000,int((self.budget.deadline-self.budget.clock())*1000))
            if timeout<=0:raise TimeoutError('Identity deadline expired')
            self.calls+=1
            result=self._write(value,timeout) if kind=='write' else self._read(value,timeout)
            if kind=='write':
                if type(result) is not int or result!=maximum:raise ValueError('Incomplete MSC send')
                size=maximum
            else:
                if type(result) not in (bytes,array) or type(result) is array and result.typecode!='B':raise ValueError('MSC byte response required')
                size=len(result)
                if not (maximum if minimum is None else minimum)<=size<=maximum:raise ValueError('MSC response length differs')
                result=result if type(result) is bytes else result.tobytes()
            self.budget.accept(size);self.accepted_bytes+=size
            return result
        except BaseException:
            self.unknown=True
            raise

    def _transaction(self,command,*,out=None,size=0,minimum=None):
        inquiry=(type(command) is bytes and len(command)==6 and command[:4]==b'\x12\0\0\0'
                 and command[5:]==b'\0' and (command[4]==5 or 32<=command[4]<=255)
                 and out is None and size==command[4] and minimum is None)
        ready=command==bytes(6) and out is None and size==0 and minimum is None
        model=command==INFO_COMMAND and ((out==INFO_REQUEST and type(out) is bytes and size==0 and minimum is None)
                                         or out is None and size==8192 and minimum==EXT.size)
        if type(command) is not bytes or not (ready or inquiry or model):raise ValueError('Fixed identity commands only')
        if self.transactions>=5:raise RuntimeError('Identity query cannot be replayed')
        self.transactions+=1
        amount=len(out) if out is not None else size
        self._io('write',CBW.pack(b'USBC',0,amount,0 if out is not None or not size else 0x80,0,len(command),command))
        data=b''
        if out is not None:self._io('write',out)
        elif size:data=self._io('read',size,minimum=minimum)
        raw=self._io('read',CSW.size)
        signature,tag,residue,status=CSW.unpack(raw)
        if signature!=b'USBS' or tag!=0 or residue!=(size-len(data) if out is None else 0) or status not in (0,1,2):
            self.unknown=True;raise ValueError('Unreviewed MSC completion wrapper')
        if status:
            self.blocked=True;raise CompleteMscError('MSC command rejected; no retry or sense request')
        return data

    def run(self):
        if self.transactions:raise RuntimeError('One fresh identity query only')
        self._transaction(bytes(6))
        head=self._transaction(b'\x12\0\0\0\x05\0',size=5)
        length=5+head[4]
        if not 32<=length<=255:self.blocked=True;raise ValueError('Unreviewed inquiry length')
        inquiry=self._transaction(bytes((0x12,0,0,0,length,0)),size=length)
        if inquiry[8:16].decode('latin1').rstrip(' \0')!='Sony':self.blocked=True;raise ValueError('Unsupported SCSI manufacturer')
        self._transaction(INFO_COMMAND,out=INFO_REQUEST)
        response=self._transaction(INFO_COMMAND,size=8192,minimum=EXT.size)
        try:return decode_identity(inquiry,response)
        except BaseException:self.blocked=True;raise
