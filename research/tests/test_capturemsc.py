"""Independent SCSI wrapper vectors and bounded Sony model records, no USB."""
from array import array
import hashlib
import struct
import unittest

from lutphoto import capturemsc as m
from lutphoto.capturestore import Budget


def model_response(serial=b'\x01\x23\xab\xcd',model=b'ILCE-7CM2',*,plist=b''):
    body=struct.pack('<I',len(plist))+plist+b'\0'*4+bytes([len(model)])+model+b'CODE!'+serial
    return struct.pack('<IHH8x',len(body),1,0)+body


def tape(response=None):
    response=model_response() if response is None else response
    inquiry=bytearray(36);inquiry[4]=31;inquiry[8:16]=b'Sony    '
    todo=[]
    def transaction(cdb,data=b'',incoming=False,request=None):
        size=len(data) if request is None else request
        todo.append(('write',struct.pack('<4sIIBBB16s',b'USBC',0,size,128 if incoming else 0,0,len(cdb),cdb)))
        if size:todo.append(('read' if incoming else 'write',data))
        todo.append(('read',struct.pack('<4sIIB',b'USBS',0,size-len(data) if incoming else 0,0)))
    transaction(b'\0'*6)
    transaction(b'\x12\0\0\0\x05\0',bytes(inquiry[:5]),True)
    transaction(b'\x12\0\0\0\x24\0',bytes(inquiry),True)
    transaction(b'\x7a\x01'+b'\0'*10,struct.pack('<IHH8x',0,1,0)+bytes(8176))
    transaction(b'\x7a\x01'+b'\0'*10,response,True,8192)
    return todo


class Wire:
    def __init__(self,entries=None):self.entries=tape() if entries is None else list(entries);self.calls=[]
    def write(self,raw,timeout):
        self.calls.append(('write',timeout));kind,want=self.entries.pop(0)
        if kind!='write' or raw!=want:raise AssertionError('Golden outbound packet differs')
        return len(raw)
    def read(self,size,timeout):
        self.calls.append(('read',timeout));kind,raw=self.entries.pop(0)
        if kind!='read' or len(raw)>size:raise AssertionError('Golden inbound request differs')
        return array('B',raw)


class IdentityTests(unittest.TestCase):
    def query(self,wire=None,**kw):
        wire=Wire() if wire is None else wire
        return m._Query(wire.write,wire.read,Budget(65536,**kw)),wire

    def test_golden_identity_and_raw_serial_encoding(self):
        q,w=self.query();identity=q.run()
        self.assertEqual(identity,{'model':'ILCE-7CM2','serial_source':'sony-get-camera-info',
            'serial_sha256':hashlib.sha256(b'0123abcd').hexdigest()})
        self.assertNotEqual(identity['serial_sha256'],hashlib.sha256(b'\x01\x23\xab\xcd').hexdigest())
        self.assertEqual((q.transactions,q.calls),(5,14));self.assertFalse(w.entries)
        self.assertEqual(q.budget.used,q.accepted_bytes)
        self.assertTrue(all(0<t<=5000 for _,t in w.calls))

    def test_query_cannot_be_replayed(self):
        q,w=self.query();q.run();count=len(w.calls)
        with self.assertRaises(RuntimeError):q.run()
        self.assertEqual(len(w.calls),count)

    def test_short_model_packet_with_matching_residue(self):
        q,_=self.query(Wire(tape(model_response(plist=b'own opaque data'))));self.assertEqual(q.run()['model'],'ILCE-7CM2')

    def test_complete_error_no_sense_or_retry(self):
        entries=tape();entries[1]=('read',struct.pack('<4sIIB',b'USBS',0,0,1))
        q,w=self.query(Wire(entries))
        with self.assertRaises(m.CompleteMscError):q.run()
        self.assertTrue(q.blocked);self.assertFalse(q.unknown);self.assertEqual(len(w.calls),2)
        with self.assertRaises(RuntimeError):q.run()
        self.assertEqual(len(w.calls),2)

    def test_unreviewed_csw_stops_at_first_wrapper(self):
        for value in (b'FAIL'+bytes(9),struct.pack('<4sIIB',b'USBS',1,0,0),
                      struct.pack('<4sIIB',b'USBS',0,1,0),struct.pack('<4sIIB',b'USBS',0,0,3)):
            with self.subTest(value=value):
                entries=tape();entries[1]=('read',value);q,w=self.query(Wire(entries))
                with self.assertRaises(ValueError):q.run()
                self.assertTrue(q.unknown);self.assertEqual(len(w.calls),2)

    def test_short_or_ambiguous_write_no_read(self):
        for result in (None,True,0,30):
            calls=[]
            q=m._Query(lambda *args:calls.append('write') or result,lambda *args:calls.append('read'),Budget(65536))
            with self.assertRaises(ValueError):q.run()
            self.assertEqual(calls,['write']);self.assertTrue(q.unknown)

    def test_non_byte_or_short_csw(self):
        for result in (b'',bytes(12),bytes(14),[0]*13,array('H',[0]*13),None):
            q=m._Query(lambda raw,t:len(raw),lambda *args:result,Budget(65536))
            with self.assertRaises(ValueError):q.run()
            self.assertTrue(q.unknown)

    def test_deadline_late_completion_is_unknown(self):
        now=[0]
        def write(raw,t):now[0]=2;return len(raw)
        q=m._Query(write,lambda *args:self.fail('No subsequent read'),Budget(65536,seconds=1,clock=lambda:now[0]))
        with self.assertRaises(TimeoutError):q.run()
        self.assertTrue(q.unknown)

    def test_budget_refuses_before_io(self):
        q=m._Query(lambda *args:self.fail('No I/O'),lambda *args:self.fail('No I/O'),Budget(30))
        with self.assertRaises(ValueError):q.run()
        self.assertEqual(q.calls,0)

    def test_remaining_timeout_not_reset(self):
        q,w=self.query(seconds=.2,clock=lambda:0);q.run()
        self.assertTrue(all(t==200 for _,t in w.calls))

    def test_bad_model_or_payload_is_rejected(self):
        inquiry=bytes(8)+b'Sony    '+bytes(20)
        good=model_response()
        for response in (good[:15],good[:16],bytes(8193),struct.pack('<I',9000)+good[4:],
                         model_response(model=b'ILCE-7CR'),model_response(serial=b'\1\2'),
                         good[:16]+struct.pack('<I',65535)+good[20:]):
            with self.subTest(length=len(response)):
                with self.assertRaises(ValueError):m.decode_identity(inquiry,response)

    def test_wrong_manufacturer_stops_before_sony_command(self):
        entries=tape();kind,value=entries[6];self.assertEqual(kind,'read')
        value=value[:8]+b'Other   '+value[16:];entries[6]=kind,value
        q,w=self.query(Wire(entries))
        with self.assertRaises(ValueError):q.run()
        self.assertEqual(len(w.calls),8)

    def test_fixed_command_allowlist(self):
        q,w=self.query()
        for command,kw in ((b'\x03'+bytes(5),{'size':18}),(bytes(6),{'size':1}),
                           (m.INFO_COMMAND,{'out':b'bad'}),(m.INFO_COMMAND,{'size':100}),
                           (b'\x12\0\0\0\x05\0',{'size':6})):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):q._transaction(command,**kw)
        self.assertFalse(w.calls)
