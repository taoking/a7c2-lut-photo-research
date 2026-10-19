"""UXC-v7 name updates preserving every existing record and other indices."""
import struct

LABEL_IDS=(0x0200ab2d,0x0200ab2c,0x0200ab2e,0x0200ab2f,0x0200ab30,0x0200ab31)

def decode(raw):
    if len(raw)<16 or raw[:8]!=b'uxc\x07\0\0\0\0':raise ValueError('Expected UXC-v7 string resource')
    kind,group,descriptor=struct.unpack_from('<HHI',raw,8);count=descriptor&0x1fff
    if kind!=8 or not count or descriptor!=count|(((count+1)&~1)<<12):raise ValueError('Unsupported UXC index descriptor')
    base=(16+count*2+3)&~3
    if base>=len(raw) or len(raw)%4:raise ValueError('Resource index/alignment differs')
    entries={}
    for i in range(count):
        pointer=struct.unpack_from('<H',raw,16+2*i)[0]
        if pointer==0xffff:continue
        at=base+pointer*4;rid=0x02000000|(group<<13)+i
        if at+5>len(raw) or struct.unpack_from('<I',raw,at)[0]!=(0x1e000000|(rid&0xffffff)):
            raise ValueError('Resource index/record mismatch')
        end=raw.find(b'\0',at+4)
        if end<0:raise ValueError('Unterminated resource name')
        entries[rid]={'text':raw[at+4:end].decode('utf-8'),'index_offset':16+2*i,'pointer':pointer}
    return {'count':count,'group':group,'data_base':base,'entries':entries}

def rename(raw,names,label_ids=LABEL_IDS):
    """Append replacement records; all old data remains available to inversion."""
    source=decode(raw);target=bytearray(raw);changes=[]
    if not names or any(type(s) is not int or s not in range(1,7) for s in names):raise ValueError('Select name slots 1..6')
    if source['group']!=5 or source['count'] not in [2860,2866] or set(label_ids)!=set(range(0x0200ab2c,0x0200ab32)):raise ValueError('Unsupported imported label layout')
    original_count=source['count'];old_base=source['data_base']
    if original_count==2860:
        target[old_base:old_base]=b'\xff\xff'*6
        struct.pack_into('<I',target,12,2866|(2866<<12))
    base=old_base+(12 if original_count==2860 else 0)
    for slot in range(1,7):
        if slot not in names and original_count!=2860:continue
        name=names.get(slot,'ST')
        if not isinstance(name,str) or not 1<=len(name.encode('utf-8'))<=63 or any(ord(c)<32 for c in name):raise ValueError('Name must contain 1..63 UTF-8 bytes without controls')
        rid=label_ids[slot-1];entry=source['entries'].get(rid)
        if entry is None and original_count!=2860:raise ValueError('Imported name ID missing')
        pointer=(len(target)-base)//4
        if pointer>=0xffff:raise ValueError('Resource name index exhausted')
        at=16+2*((rid&0xffffff)-0xa000);struct.pack_into('<H',target,at,pointer)
        target.extend(struct.pack('<I',0x1e000000|(rid&0xffffff))+name.encode('utf-8')+b'\0')
        target.extend(bytes((-len(target))%4))
        changes.append({'slot':slot,'index_offset':at,'before_pointer':entry['pointer'] if entry else 65535,'after_pointer':pointer})
    after=decode(bytes(target))
    for rid,entry in source['entries'].items():
        expected=names.get(label_ids.index(rid)+1,entry['text']) if rid in label_ids else entry['text']
        if after['entries'][rid]['text']!=expected:raise ValueError('Unselected resource name changed')
    return bytes(target),{'before_bytes':len(raw),'after_bytes':len(target),'before_count':original_count,'changes':changes}

def inverse(raw,plan):
    if len(raw)!=plan['after_bytes']:raise ValueError('Resource inverse size differs')
    if plan.get('before_count')==2860:
        old_base=16+2860*2;result=bytearray(raw[:old_base]+raw[old_base+12:plan['before_bytes']+12])
        struct.pack_into('<I',result,12,2860|(2860<<12))
    else:result=bytearray(raw[:plan['before_bytes']])
    for change in plan['changes']:
        if struct.unpack_from('<H',raw,change['index_offset'])[0]!=change['after_pointer']:raise ValueError('Resource inverse pointer differs')
        if change['index_offset']<16+plan.get('before_count',2866)*2:struct.pack_into('<H',result,change['index_offset'],change['before_pointer'])
    decode(bytes(result));return bytes(result)
