"""Read-only same-config capture/MAIN candidates and role-9 exchange sites.

Static candidates and bounded paths only; no dynamic configuration recovery,
firmware execution, complete messages or verified photo-pixel identity.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_capture_buffers import bounded_tbb_targets
from research.trace_capture_config import trace as trace_config
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_refresh import potential_thumb_path
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp);baseline=trace_config(cp_path)
    # Exclude the two six-byte step tables and the helper's inline data island.
    ranges=[(0xa0d534,0xa0d55a),(0x37a5e8,0x37a5fc),(0x37a602,0x37a688),
            (0x37a6ac,0x37a6c0),(0x37a6c6,0x37a74c),
            (0x382834,0x3828d8),(0x3829d2,0x382a08),(0x382a08,0x382a78),
            (0x382bd8,0x383a14),(0x383aa0,0x384328)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    def edge(t,m):return (m,f'#{base+t:#x}')
    require_instructions(index,{
        0xa0d544:('str','r3, [r2, #0x6c]'),0xa0d556:('str.w','r3, [r2, #0x80]'),
        0x37a5ec:('mov','r4, r0'),0x37a5ee:('ldrb.w','r0, [r4, #0x27]'),
        0x37a5f2:('cmp','r0, #5'),0x37a5f4:edge(0x37a682,'bhi'),
        0x37a5f8:('tbb','[pc, r0]'),0x37a638:('mov','r0, r4'),
        0x37a63a:('pop.w','{r4, r5, r7, lr}'),0x37a63e:edge(0x382834,'b.w'),
        0x37a6b0:('mov','r4, r0'),0x37a6b2:('ldrb.w','r0, [r4, #0x27]'),
        0x37a6b6:('cmp','r0, #5'),0x37a6b8:edge(0x37a746,'bhi'),
        0x37a6bc:('tbb','[pc, r0]'),0x37a6f2:('mov','r0, r4'),
        0x37a6f4:('pop.w','{r4, r5, r7, lr}'),0x37a6f8:edge(0x382834,'b.w'),
        0x38283e:('ldr','r4, [r0]'),0x38288c:('mov','r0, r4'),0x38288e:call(0x36c70c),
        0x382892:('adds','r0, #1'),0x382894:edge(0x3829fe,'beq.w'),
        0x3828cc:('mov','r0, r4'),0x3828ce:call(0x36c844),
        0x3829d2:('ldr.w','r0, [r4, #0x210]'),0x3829d6:('cmp','r0, #3'),
        0x3829d8:edge(0x3829e2,'beq'),0x3829da:('movw','r0, #0x65b4'),
        0x3829de:('ldr','r0, [r4, r0]'),0x3829e0:('cbz',f'r0, #{base+0x382a46:#x}'),
        0x3829e2:('movs','r1, #0x7f'),0x3829e4:('mov','r0, r4'),0x3829e6:call(0x3818b8),
        0x3829ea:('mov','r1, r0'),0x3829ec:('cbz',f'r1, #{base+0x382a08:#x}'),
        0x382a46:('movs','r1, #0xff'),0x382a48:edge(0x3829e4,'b'),
        0x382a08:('ldrb.w','r0, [r6, #0xe7]'),0x382a0c:('cbz',f'r0, #{base+0x382a78:#x}'),
        0x382a0e:('movw','r1, #0x5aa0'),0x382a12:('ldr','r0, [r4, r1]'),
        0x382a14:('cbz',f'r0, #{base+0x382a78:#x}'),0x382a16:('adds','r6, r4, r1'),
        0x382a18:('ldr.w','r1, [r4, #0x208]'),0x382a1c:('cbz',f'r1, #{base+0x382a4a:#x}'),
        0x382a1e:('movw','r5, #0x5308'),0x382a28:('movw','r0, #0x1df'),
        0x382a2c:call(0xa13a1a),0x382a30:('mov','r0, r4'),
        0x382a32:('movs','r1, #9'),0x382a34:('movs','r2, #2'),0x382a36:call(0x36c2ac),
        0x382a3a:('ldr','r0, [r6]'),0x382a3c:('movw','r1, #0x5afc'),
        0x382a40:('ldr','r0, [r0, r5]'),0x382a42:('str','r0, [r4, r1]'),
        0x382a5c:('movw','r5, #0x5afc'),0x382a66:('ldr','r1, [r4, r5]'),
        0x382a6a:call(0xa13a1a),0x382a6e:('ldr','r0, [r4, r5]'),
        0x382a70:('ldr','r1, [r6]'),0x382a72:('movw','r2, #0x5308'),
        0x382a76:('str','r0, [r1, r2]'),
        0x382bea:('tst.w','r5, #1'),0x382bf4:edge(0x382f50,'bne.w'),
        0x382c9e:('lsls','r0, r5, #0x19'),0x382ca0:edge(0x3832ea,'bpl.w'),
        0x382ccc:('ldr.w','r3, [fp, #0x1c8]'),
        0x383280:('ldr','r0, [sp, #0x24]'),0x383288:('strd','r0, r6, [sp]'),
        0x383294:call(0x37845c),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    if (constant(0xa0d534,0xa0d540)!=((base+0x37a5e8)|1)
            or constant(0xa0d546,0xa0d552)!=((base+0x37a6ac)|1)
            or baseline['photo_pipeline_located'] is not False):
        raise ValueError('捕获索引 5/6 登记或前轮边界不符')
    tables={}
    for ident,a,step,target in [(5,0x37a5fc,2,0x37a638),(6,0x37a6c0,1,0x37a6f2)]:
        targets=bounded_tbb_targets(cp[a:a+6],a,len(cp))
        if targets[step]!=target or any(base+t not in index for t in targets):
            raise ValueError('有界捕获步骤表不符或目标不在所查指令边界')
        tables[str(ident)]={'table_file_offset':hex(a),'entries':6,'capture_step':step,
                            'target_file_offsets':[hex(t) for t in targets]}
    selected=[]
    for j in range(1,24):
        pointer=struct.unpack_from('<I',cp,0x110f2ec-base+4*j)[0]
        if pointer!=0x110ee9c+(j-1)*0x30:raise ValueError('前轮静态行位置改变')
        fields=struct.unpack_from('<5I',cp,pointer-base+0x14)
        if fields[0]==5 and fields[4] in (1,3):
            if fields[1:4]!=(0,0,0):raise ValueError('选定同配置中间组值改变')
            selected.append({'static_row':j,'capture_raw_value':fields[0],
                             'intervening_group_raw_values':list(fields[1:4]),'main_raw_value':fields[4]})
    if [r['static_row'] for r in selected]!=[1,2,3,4,5,12]:
        raise ValueError('所查同配置候选不符')
    graph=blocks[8]+blocks[9];paths=[]
    for flags in (0x7f,0xff):
        decisions={base+0x382bf4:bool(flags&1),base+0x382ca0:not bool(flags&0x40)}
        for target in (0x382ccc,0x383280,0x383294):
            if potential_thumb_path(graph,base+0x382bd8,base+target,
                                    branch_decisions=decisions,allow_gaps=True) is None:
                raise ValueError('新标志下选定 0x40 显式配置路径不再有潜在连接')
            paths.append({'flags':flags,'target_file_offset':hex(target),'potential_path_exists':True})
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'same-static-config-capture-candidates-and-conditional-role9-exchange',
        'same_config_candidates':{
            'selected_static_rows':selected,'capture_factory_file_offset':'0xa0bbe8',
            'capture_record_table_link_va':'0x1a50360','capture_index5_callback_offset':0x6c,
            'capture_index6_callback_offset':0x80,'step_tables':tables,
            'capture_entry_file_offset':'0x382834','main_entry_file_offset':'0x3859dc',
            'main_raw3_condition':'effective main index 1 when work word +0x3c bit 2 is zero',
            'scope':'同一静态行的条件兼容和分发入口，不保证运行选择、步骤顺序或像素身份'},
        'alternate_capture':{
            'work_source':'stage +0','role9_producer_call_file_offset':'0x38288e',
            'additional_allocator_call_file_offset':'0x3828ce',
            'builder_file_offset':'0x3818b8','builder_call_file_offset':'0x3829e6',
            'flags_when_work210_is3_or_work65b4_nonzero':0x7f,'other_selected_flags':0xff,
            'helper_file_offset':'0x382bd8','checked_potential_0x40_paths':paths,
            'scope':'不能套用旧 0x2b 调用排除 0x40 分支的结论；全部 helper/驱动/别名效果未证'},
        'conditional_role9_exchange':{
            'post_builder_file_offset':'0x382a08','builder_success_value':0,
            'companion_pointer_work_offset':0x5aa0,
            'companion_handle_offset':0x5308,'work_role9_slot_offset':0x5afc,
            'work208_nonzero':'call role 9 operation 2, then companion +0x5308 -> work +0x5afc',
            'work208_zero':'after selected calls, work +0x5afc -> companion +0x5308',
            'replace_store_file_offset':'0x382a42','save_store_file_offset':'0x382a76',
            'scope':'全局字节门槛与伴随指针非零门槛后的选定存储，不是完整引用/所有权转移证明'},
        'dynamic_configuration_status':{
            'row_link_va':'0x1a50644','producer_status':'not located in this scoped search',
            'scope':'保留前轮指针表引用；未找到选定常量引用不证明没有写入者，亦不推断动态内容为零'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '动态行生产/全部配置写入者、实际静态索引和相机模式仍未验证',
            '捕获索引 5/6 的其他步骤、异步调用及中间组效果未全部审阅',
            '同配置连接不证明完整 LUT 像素链；新 0x40 分支须保留调用/别名缺口',
            '捕获后可以覆盖角色 9；同槽位不保证 MAIN 读取的就是最初捕获缓冲',
            '格式 3/4 有效传输、照片 LUT 使能、色彩及完整生命周期仍未闭合'],
        'same_static_config_selection_located':True,'alternate_capture_entry_located':True,
        'selected_capture_flags_located':True,'post_capture_role9_exchange_located':True,
        'helper_0x40_potential_path_located':True,
        **{k:v for k,v in baseline.items() if v is False},
        'same_config_capture_to_main_runtime_verified':False,'helper_all_effects_at_new_flags_verified':False,
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
