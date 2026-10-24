"""Finite failure metadata only; no I/O, exception text or device data."""
from array import array
import re

SCHEMA='a7c2-msc-identity-failure/1'
BOUNDARIES={'QUERY_PRECHECK','CALLBACK','DESCRIPTOR_QUERY','DESCRIPTOR_CHECK',
            'OWNER_PRECHECK','SDK_BULK_READ','SDK_BULK_WRITE','OWNER_POSTCHECK',
            'RESULT_VALIDATION','ACCOUNTING'}
# Transaction, part -> attempted callback slot, direction, permitted length.
SLOTS={(1,'CBW'):(1,'write',31,31),(1,'CSW'):(2,'read',13,13),
       (2,'CBW'):(3,'write',31,31),(2,'DATA'):(4,'read',5,5),(2,'CSW'):(5,'read',13,13),
       (3,'CBW'):(6,'write',31,31),(3,'DATA'):(7,'read',32,255),(3,'CSW'):(8,'read',13,13),
       (4,'CBW'):(9,'write',31,31),(4,'DATA'):(10,'write',8192,8192),(4,'CSW'):(11,'read',13,13),
       (5,'CBW'):(12,'write',31,31),(5,'DATA'):(13,'read',8192,8192),(5,'CSW'):(14,'read',13,13)}


def valid_error(value):
    return type(value) is str and re.fullmatch('[A-Za-z_][A-Za-z_0-9]{0,63}',value) is not None


def error_name(error):
    name=type(error).__name__
    return name if valid_error(name) else 'OtherError'


def _code(value):return type(value) is int and -(2**31)<=value<2**31


def _error_code(error,name):
    try:value=getattr(error,name,None)
    except BaseException:return None
    return value if _code(value) else None  # No coercion, repr, message or cause traversal.


def returned_size(kind,value):
    size=value if kind=='write' else (len(value) if type(value) is bytes or type(value) is array and value.typecode=='B' else None)
    return size if type(size) is int and 0<=size<=8192 else None


def valid_failure(value):
    fields={'schema','transaction','part','direction','requested_bytes','call_number','callback_attempted',
            'boundary','returned_bytes','accepted_bytes','reason_type','errno','backend_error_code'}
    if (type(value) is not dict or set(value)!=fields or value['schema']!=SCHEMA
            or type(value['transaction']) is not int or type(value['part']) is not str
            or type(value['direction']) is not str or type(value['boundary']) is not str
            or value['boundary'] not in BOUNDARIES or not valid_error(value['reason_type'])):return False
    slot=SLOTS.get((value['transaction'],value['part']))
    if (slot is None or type(value['call_number']) is not int or value['call_number']!=slot[0]
            or value['direction']!=slot[1] or type(value['requested_bytes']) is not int
            or not slot[2]<=value['requested_bytes']<=slot[3]
            or type(value['callback_attempted']) is not bool
            or value['callback_attempted']!=(value['boundary']!='QUERY_PRECHECK')
            or type(value['accepted_bytes']) is not int or not 0<=value['accepted_bytes']<=65536
            or value['returned_bytes'] is not None and (type(value['returned_bytes']) is not int or not 0<=value['returned_bytes']<=8192)
            or any(value[k] is not None and not _code(value[k]) for k in ('errno','backend_error_code'))):return False
    if value['boundary'] in ('SDK_BULK_READ','SDK_BULK_WRITE'):
        if value['direction']!=('read' if value['boundary']=='SDK_BULK_READ' else 'write'):return False
    return value['returned_bytes'] is None or value['boundary'] in ('OWNER_POSTCHECK','RESULT_VALIDATION','ACCOUNTING')


def make_failure(context,boundary,error,accepted_bytes,returned_bytes=None):
    value=dict(context,schema=SCHEMA,boundary=boundary,returned_bytes=returned_bytes,
               accepted_bytes=accepted_bytes,reason_type=error_name(error),
               errno=_error_code(error,'errno'),backend_error_code=_error_code(error,'backend_error_code'))
    if not valid_failure(value):raise ValueError('Invalid bounded identity diagnostic')
    return value


def valid_records(value):
    if type(value) is not list or len(value)>1:return False  # One failure stops capture.
    for record in value:
        if (type(record) is not dict or set(record)!={'owner','failure','record_error_type'}
                or type(record['owner']) is not str or record['owner'] not in ('normal-initial','normal-return')):return False
        if record['failure'] is None:
            if not valid_error(record['record_error_type']):return False
        elif not valid_failure(record['failure']) or record['record_error_type'] is not None:return False
    return True


INVENTORY_SCHEMA='a7c2-host-inventory-failure/1'
INVENTORY_BOUNDARIES={'HOST_PRECHECK','HOST_INTENT','CALLBACK','NATIVE_RUNTIME',
    'SDK_FIND_NORMAL','SDK_FIND_SERVICE','INVENTORY_LIMIT','KEY_VENDOR_READ','KEY_VENDOR_CHECK',
    'KEY_PID_READ','KEY_BUS_READ','KEY_PORTS_READ','KEY_ADDRESS_READ','KEY_VALIDATE',
    'ENUMERATION_DISPOSE','HOST_POSTCHECK','HOST_ACK'}
KEY_FIELDS=('PID','BUS','PORTS','ADDRESS')


def rejected_key_fields(pid,bus,ports,address):
    """Only names of invalid cached fields; never re-read SDK properties."""
    return [name for name,valid in zip(KEY_FIELDS,(
        type(pid) is int and pid in (0x0e8a,0x0336),
        type(bus) is int and bus>0,
        type(ports) is tuple and 1<=len(ports)<=16 and all(type(p) is int and 1<=p<=255 for p in ports),
        type(address) is int and 1<=address<=127)) if not valid]


def valid_inventory_failure(value):
    fields={'schema','operation','boundary','invalid_key_fields','reason_type','errno','backend_error_code'}
    if (type(value) is not dict or set(value)!=fields or value['schema']!=INVENTORY_SCHEMA
            or value['operation']!='INVENTORY' or type(value['boundary']) is not str
            or value['boundary'] not in INVENTORY_BOUNDARIES or not valid_error(value['reason_type'])
            or any(value[k] is not None and not _code(value[k]) for k in ('errno','backend_error_code'))):return False
    names=value['invalid_key_fields']
    if type(names) is not list or any(type(n) is not str or n not in KEY_FIELDS for n in names):return False
    return names==[n for n in KEY_FIELDS if n in names] and (not names or value['boundary']=='KEY_VALIDATE')


def make_inventory_failure(boundary,error,invalid_key_fields=()):
    value={'schema':INVENTORY_SCHEMA,'operation':'INVENTORY','boundary':boundary,
           'invalid_key_fields':list(invalid_key_fields),'reason_type':error_name(error),
           'errno':_error_code(error,'errno'),'backend_error_code':_error_code(error,'backend_error_code')}
    if not valid_inventory_failure(value):raise ValueError('Invalid bounded inventory diagnostic')
    return value


def valid_inventory_records(value):
    if type(value) is not list or len(value)>1:return False
    for record in value:
        if (type(record) is not dict or set(record)!={'inventory_call','failure','record_error_type'}
                or type(record['inventory_call']) is not int or not 1<=record['inventory_call']<=2048):return False
        if record['failure'] is None:
            if not valid_error(record['record_error_type']):return False
        elif not valid_inventory_failure(record['failure']) or record['record_error_type'] is not None:return False
    return True
