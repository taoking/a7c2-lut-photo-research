"""Read-only capture configuration forwarding and companion role-8 slots.

Selected pointer stores, driver forwarding and opcode-0x23 handling only.
No firmware execution, device payload, complete alias set or runtime identity.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_capture_buffers import bounded_tbb_targets
from research.trace_capture_paths import trace as trace_paths
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handles import bounded_tbh_targets
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp);baseline=trace_paths(cp_path)
    # Helper data island, three TBB tables/padding and setup TBH are excluded.
    ranges=[(0x382bd8,0x383a14),(0x383aa0,0x384328),
            (0x37845c,0x378538),(0x378540,0x3785e0),(0x378648,0x3786e8),
            (0x43f404,0x43f464),(0x43928c,0x439420),
            (0x36d858,0x36d8ec),(0x36d930,0x36dc92),(0x36bc10,0x36bd18),
            (0xa051f4,0xa05220),(0x36c2ac,0x36c2de),
            (0x36c2ea,0x36c2fc),(0x36c306,0x36c3aa),
            (0xa13a60,0xa13a98),(0x408fdc,0x409054),(0x4090ec,0x40915e),
            (0xb13236,0xb13292),(0xb16b4c,0xb16bd6)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    def edge(t,m):return (m,f'#{base+t:#x}')
    require_instructions(index,{
        0x383280:('ldr','r0, [sp, #0x24]'),0x383288:('strd','r0, r6, [sp]'),
        0x383294:call(0x37845c),0x378492:('ldrd','sb, sl, [r7, #8]'),
        0x37851a:('ldr.w','r0, [r5, #0x134]'),0x37851e:('subs','r0, #3'),
        0x378520:('cmp','r0, #6'),0x378522:edge(0x378562,'bhi'),
        0x378524:('mov','lr, r4'),0x378526:('movs','r2, #0'),
        0x378528:('mov','r3, sb'),0x37852a:('mov.w','ip, #0'),
        0x378532:('movs','r1, #0'),0x378534:('tbb','[pc, r0]'),
        0x3785ae:('ldr','r0, [r5, #0x24]'),0x3785b0:('strd','ip, r1, [sp]'),
        0x3785b4:('movs','r4, #0'),0x3785b8:('str','r4, [sp, #8]'),
        0x3785ba:call(0x43f404),0x43f40e:('mov','r6, r2'),0x43f420:('mov','r5, r3'),
        0x43f444:('ldr','r1, [r7, #0x10]'),0x43f44a:('str','r1, [sp, #0x10]'),
        0x43f44c:('ldr','r1, [r7, #0xc]'),0x43f44e:('str','r1, [sp, #0xc]'),
        0x43f450:('ldr','r1, [r7, #8]'),0x43f452:('str','r1, [sp, #8]'),
        0x43f456:('strd','r6, r5, [sp]'),0x43f45a:call(0x43928c),
        0x439324:('ldrd','r1, r0, [r7, #0x10]'),0x439328:('ldrd','r6, r2, [r7, #8]'),
        0x439338:('strd','r6, r2, [sp, #0x34]'),0x43933c:('strd','r1, r0, [sp, #0x3c]'),
        0x439340:('add','r0, sp, #0x34'),0x439344:('adds','r0, #4'),
        0x439346:('str','r0, [sp, #0x24]'),0x43934e:('ldr','r1, [sp, #0x24]'),
        0x439350:('ldr.w','r6, [r1, r4, lsl #2]'),0x43935e:('str','r6, [sp, #0x2c]'),
        0x4393bc:('ldr.w','r0, [sb]'),0x4393c0:('ldr','r4, [r0, #0x28]'),
        0x4393d0:('ldr','r1, [sp, #0x2c]'),0x4393d2:('strd','r1, sl, [sp]'),
        0x4393e8:('blx','r4'),0x439414:('adds','r0, r4, #1'),
        0x439416:('cmp','r0, #3'),0x439418:edge(0x43934e,'bls'),
        0x36d866:('mov','r4, r0'),0x36d8e0:('cmp','r1, #0x21'),
        0x36d8e6:edge(0x36d986,'bhi'),0x36d8e8:('tbh','[pc, r1, lsl #1]'),
        0x36db34:call(0x36bc10),0x36db38:('mov','r5, r0'),0x36db42:('str','r5, [r0]'),
        0x36db5c:('ldr','r5, [r0]'),0x36db60:edge(0x36dc1a,'beq'),
        0x36db78:('movw','r0, #0x5aa0'),0x36db7c:('str','r5, [r4, r0]'),
        0x36dbbc:call(0x36bc10),0x36dbc0:('mov','r5, r0'),
        0x36dbca:('str','r5, [r0]'),0x36dbd4:('str','r5, [r0]'),
        0x36dbde:('movw','r0, #0x5aa0'),0x36dbe4:('str','r5, [r4, r0]'),
        0x36bc20:call(0xa0730c),0x36bc24:('mov','r4, r0'),0x36bd0e:('mov','r0, r4'),
        0xa051f4:('add.w','r1, r0, r1, lsl #2'),0xa051f8:('movw','ip, #0x52e8'),
        0xa051fc:('ldr.w','r0, [r1, ip]'),0xa05208:('add.w','r4, r1, ip'),
        0xa0520c:('mov','r1, r2'),
        0xa0520e:call(0xa13a60),0xa05212:('mov.w','r0, #-1'),0xa05216:('str','r0, [r4]'),
        0x36c2b4:('mov','r5, r1'),0x36c2b6:('mov','r6, r0'),
        0x36c2b8:('movw','r3, #0x5ad8'),0x36c2bc:('add.w','r1, r6, r5, lsl #2'),
        0x36c2c0:('ldr','r0, [r1, r3]'),0x36c2c2:('adds','r4, r0, #1'),
        0x36c2c4:edge(0x36c3a2,'beq.w'),0x36c2c8:('adds','r4, r1, r3'),
        0x36c2ca:('mov','r1, r2'),0x36c2cc:call(0xa13a60),
        0x36c2d0:('mov.w','r0, #-1'),0x36c2d4:('cmp','r5, #0xa'),
        0x36c2d6:('str','r0, [r4]'),0x36c2d8:edge(0x36c2f0,'bhi'),
        0x36c2da:('tbb','[pc, r5]'),0x36c2f0:('sub.w','r0, r5, #0x19'),
        0x36c2f4:('cmp','r0, #8'),0x36c2f6:edge(0x36c3a2,'bhi'),
        0x36c2f8:('tbb','[pc, r0]'),0x36c348:('mov.w','r0, #0x5f80'),
        0x36c34c:('movs','r1, #0'),0x36c34e:edge(0x36c3a0,'b'),
        0x36c3a0:('str','r1, [r6, r0]'),
        0xa13a68:('mov','r4, r1'),0xa13a6a:('mov','r5, r0'),
        0xa13a78:('mov','r0, r5'),0xa13a7a:('mov','r1, r4'),
        0xa13a7c:('movs','r2, #5'),0xa13a7e:call(0x408fdc),
        0x408fe6:('mov','r4, r0'),0x408fea:('mov','r5, r1'),
        0x40901e:('movs','r2, #0x3c'),0x409024:('movt','r2, #0x61'),
        0x409028:call(0x530176),0x409032:('movs','r0, #0x23'),
        0x40903c:('strh','r0, [r6]'),0x40903e:('movs','r0, #0x55'),
        0x409040:('str','r4, [r6, #8]'),0x409042:('strh','r0, [r6, #0x14]'),
        0x409044:('strh','r5, [r6, #0x16]'),0x40911c:('movw','r0, #0x8023'),
        0xb1324e:('ldr','r0, [r5, #0x14]'),
        0xb13252:('ldrh','r1, [r5, #0x22]'),0xb13254:('cmp','r1, #2'),
        0xb13256:edge(0xb13260,'beq'),0xb13260:call(0xb16b4c),
        0xb13266:('uxth','r0, r6'),0xb13268:('cmp','r0, #1'),0xb1326a:edge(0xb13274,'bhi'),
        0xb1326c:('ldr','r0, [r5, #0x14]'),0xb1326e:call(0xb16bd6),
        0xb16bb6:('tst.w','r0, #0xff'),0xb16bba:('strb','r0, [r2]'),
        0xb16bbe:('movs','r0, #1'),0xb16bc0:('strh.w','r0, [ip]'),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    shared=[constant(a,b) for a,b in [(0x36db3a,0x36db3e),(0x36db54,0x36db58),
                                     (0x36dbc2,0x36dbc6),(0x36dbcc,0x36dbd0)]]
    if shared!=[0x1a3ab20,0x1a3ab20,0x1a3ab20,0x1a3ab30]:
        raise ValueError('伴随对象的所查全局来源改变')
    tables={}
    for name,a,n,expected in [
            ('driver_channels',0x378538,7,(0x378540,0x3785ae,0x37857a,0x378582,0x37858e,0x37859a,0x3785a4)),
            ('work_roles_0_to_10',0x36c2de,11,(0x36c2ea,0x36c31a,0x36c320,0x36c326,0x36c334,
                                             0x36c3a2,0x36c3a2,0x36c3a2,0x36c3a2,0x36c348,0x36c350)),
            ('work_roles_25_to_33',0x36c2fc,9,(0x36c306,0x36c360,0x36c37a,0x36c3a2,0x36c3a2,
                                            0x36c3a2,0x36c3a2,0x36c3a2,0x36c38e))]:
        targets=bounded_tbb_targets(cp[a:a+n],a,len(cp))
        if targets!=expected or any(base+t not in index for t in targets):
            raise ValueError('有界通道/角色表与所查代码边界不符')
        tables[name]={'table_file_offset':hex(a),'entries':n,'target_file_offsets':[hex(t) for t in targets]}
    setup=bounded_tbh_targets(cp[0x36d8ec:0x36d930],0x36d8ec,len(cp))
    if (len(setup)!=34 or set(setup)!={0x36d930,0x36d950,0x36d970,0x36d986,0x36dc68}
            or any(base+t not in index for t in setup)):
        raise ValueError('伴随对象准备函数的有界表目标不符')
    handler=struct.unpack_from('<I',cp,0xea64bc-base+0x23*4)[0]
    if handler!=((base+0xb13236)|1) or baseline['photo_pipeline_located'] is not False:
        raise ValueError('操作 0x23 分发表或前轮边界不符')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'explicit-config-driver-boundary-and-shared-companion-role8',
        'explicit_config_forwarding':{
            'flags_from_previous_round':[0x7f,0xff],'helper_call_file_offset':'0x383294',
            'first_pointer_source':'saved original configuration -> wrapper entry stack +0',
            'preparer_file_offset':'0x378648','selected_first_pointer_word_writes':[0x6c,0x70,0x74,0xd8,0xdc,0xe0],
            'candidate_pair_range':[0xf0,0xf8],'selected_writes_overlap_candidate':False,
            'driver_chain':['0x3785ba','0x43f404','0x43928c'],
            'channel_pointer_list_entries':4,'virtual_consumer_vtable_offset':0x28,
            'virtual_call_file_offset':'0x4393e8','per_channel_pointer_argument':'entry stack +0',
            'scope':'显式指针传递到间接调用边界；不穷尽准备循环、其他 helper 分支或下层别名效果'},
        'companion_pointer_sources':{
            'setup_file_offset':'0x36d858','work_pointer_offset':0x5aa0,
            'selected_global_link_vas':[hex(x) for x in sorted(set(shared))],
            'factory_file_offset':'0x36bc10','factory_object_source_file_offset':'0xa0730c',
            'selected_factory_calls':['0x36db34','0x36dbbc'],
            'work_pointer_store_file_offsets':['0x36db7c','0x36dbe4'],
            'reuse_global_load_file_offset':'0x36db5c','setup_tbh_entries':len(setup),
            'scope':'选定新对象发布和全局对象复用；不保证每次拍摄新建、所有写入者或运行对象身份'},
        'companion_role8':{
            'generic_slot_function_file_offset':'0xa051f4','table_base_offset':0x52e8,
            'slot_stride':4,'role':8,'slot_offset':0x52e8+4*8,
            'selected_handle_source':'previously checked capture-zero branch stores work role 9 into companion role 8',
            'scope':'第 8 槽地址和选定捕获保存/取回关系；不宣称全部生产者或不同拍摄间身份已证'},
        'role9_drop_request':{
            'work_function_file_offset':'0x36c2ac','role':9,'option':2,
            'request_chain':['0x36c2cc','0xa13a60','0x408fdc'],
            'domain_id':'0x61003c','opcode':0x23,'reply_opcode':0x8023,'echo_tag':0x55,
            'handler_file_offset':'0xb13236','reference_handler_file_offset':'0xb16b4c',
            'conditional_return_file_offset':'0xb16bd6','reference_result_gate':[0,1],
            'work_slot_clear_file_offset':'0x36c2d6','work_slot_offset':0x5ad8+4*9,
            'work_kind_clear_offset':0x5f80,'work_role9_tbb_target':'0x36c348',
            'scope':'请求及引用/条件归还连接；工作调用者不检查下层返回就清槽，不能当作运行成功或完整回滚'},
        'bounded_tables':tables,'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '原配置指针越过间接调用边界，候选双字在全部调用后不变仍未证明',
            '准备函数读取计数并循环；所列第一项写入不证明所有指针数组范围安全',
            '共享伴随对象可复用；不是每次拍摄独立缓冲或全部句柄生产者证明',
            '操作 0x23 的运行送达、引用处理和归还成功均未验证',
            '动态配置生产、有效传输、照片 LUT 使能、MAIN 身份及色彩/同步仍未闭合'],
        'explicit_config_driver_forwarding_located':True,'companion_shared_pointer_sources_located':True,
        'companion_role8_slot_located':True,'role9_drop_request_located':True,
        **{k:v for k,v in baseline.items() if v is False},
        'companion_role8_all_producers_verified':False,'role9_drop_runtime_success_verified':False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cp',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        raw=(json.dumps(trace(args.cp),ensure_ascii=False,indent=2)+'\n').encode()
        write_bytes_new(args.output,raw);print(raw.decode(),end='');return 0
    except (ValueError,OSError,ImportError) as exc:
        parser.exit(1,f'STOPPED: {exc}\n')


if __name__=='__main__':
    raise SystemExit(main())
