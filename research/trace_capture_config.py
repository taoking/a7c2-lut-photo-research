"""Read-only work configuration pointers and MAIN step-zero role requests.

Inspect selected static rows without assuming runtime selection or combining
different configurations. No firmware execution, payloads or device access.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_capture_buffers import bounded_tbb_targets
from research.trace_capture_stages import trace as trace_stages
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp);baseline=trace_stages(cp_path)
    # Exclude the allocator's 19-byte TBB table and its padding.
    ranges=[(0x37dd28,0x37dd8e),(0x385d00,0x385dd0),
            (0x36c8a4,0x36c8dc),(0x36c8f0,0x36c9d0)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    require_instructions(index,{
        0x37dd32:('ldr.w','sb, [r0]'),0x37dd36:('mov','r0, sb'),0x37dd38:call(0x37df00),
        0x37dd40:('mov','r5, r0'),0x37dd42:('movw','r0, #0x5a98'),
        0x37dd46:('str.w','r5, [sb, r0]'),0x37dd4e:('movw','r0, #0x5a9c'),
        0x37dd52:('ldr.w','r1, [fp, r5, lsl #2]'),0x37dd56:('cmp','r1, #0'),
        0x37dd58:('str.w','r1, [sb, r0]'),0x37dd5c:('bne',f'#{base+0x37dd8e:#x}'),
        0x37dd88:('ldr.w','r0, [fp]'),0x37dd8c:('str','r0, [r4]'),
        0x385d08:('ldr','r4, [r0]'),0x385d34:('mov','r0, r4'),
        0x385d36:('movs','r1, #0x10'),0x385d38:call(0x36c8a4),
        0x385d70:('mov','r0, r4'),0x385d7a:('movs','r1, #0x14'),0x385d7c:call(0x36c8a4),
        0x385d88:('mov','r0, r4'),0x385d8a:('movs','r1, #0x11'),0x385d8c:call(0x36c8a4),
        0x385d92:('mov','r0, r4'),0x385d94:('movs','r1, #0x12'),0x385d96:call(0x36c8a4),
        0x385d9c:('mov','r0, r4'),0x385d9e:('movs','r1, #0xd'),0x385da0:call(0x36c8a4),
        0x385db0:('mov.w','r0, #0'),0x385db6:('moveq','r0, #5'),
        0x385dbc:('movne','r0, #5'),0x385dc2:('moveq','r0, #5'),0x385dc8:('moveq','r0, #5'),
        0x36c8ae:('mov','r6, r0'),0x36c8b0:('movw','sl, #0x5ad8'),
        0x36c8b4:('add.w','r5, r6, r1, lsl #2'),0x36c8b8:('ldr.w','r0, [r5, sl]'),
        0x36c8bc:('adds','r2, r0, #1'),0x36c8be:('bne.w',f'#{base+0x36c9ac:#x}'),
        0x36c8c2:('sub.w','r0, r1, #0xd'),0x36c8c6:('cmp','r0, #0x12'),
        0x36c8c8:('bhi',f'#{base+0x36c91a:#x}'),0x36c8d8:('tbb','[pc, r0]'),
        0x36c98c:('add','r3, sp, #8'),0x36c990:('movs','r1, #0'),
        0x36c992:('mov.w','r2, #-1'),0x36c996:call(0x3a1940),
        0x36c99c:('cbz',f'r3, #{base+0x36c9b4:#x}'),
        0x36c9b4:('ldr','r0, [sp, #0x14]'),0x36c9b6:('add','r5, sl'),
        0x36c9ba:('str','r0, [r5]'),
    },base)
    table=movw_movt_value(list(index.values()),base+0x37dd3c,base+0x37dd4a)
    if table!=0x110f2ec or baseline['photo_pipeline_located'] is not False:
        raise ValueError('工作配置指针表或前轮验证边界不符')
    pointers=struct.unpack_from('<24I',cp,table-base)
    # These are 23 manually scoped static rows, not a proven bound on every
    # runtime selector. Row zero is an external runtime location.
    rows={}
    for j,pointer in enumerate(pointers[1:],1):
        if pointer!=0x110ee9c+(j-1)*0x30 or not base<=pointer<=base+len(cp)-0x30:
            raise ValueError('选定静态配置行的指针/步长/映像边界不符')
        rows[j]=struct.unpack_from('<5I',cp,pointer-base+0x14)
    capture_rows=[j for j,values in rows.items() if values[0]==2]
    main_rows=[j for j,values in rows.items() if values[4] in (1,3)]
    if pointers[0]!=0x1a50644 or capture_rows!=[11] or rows[11]!=(2,0,2,0,0):
        raise ValueError('动态配置位置或选定捕获行不符')
    if set(capture_rows)&set(main_rows):
        raise ValueError('所查静态行不再满足捕获/MAIN 条件分离，须重新审阅')
    targets=bounded_tbb_targets(cp[0x36c8dc:0x36c8ef],0x36c8dc,len(cp))
    if any(base+t not in index for t in targets):raise ValueError('角色分配表目标未落在所查代码边界')
    roles=[0x10,0x14,0x11,0x12,0xd]
    slots={str(role):0x5ad8+4*role for role in roles}
    if 0x5afc in slots.values() or slots['16']!=0x5b18:
        raise ValueError('MAIN 步骤 0 的直接槽位与角色 9/输出槽关系不符')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'work-config-row-separation-and-main-step0-role-slots',
        'configuration_pointer':{
            'producer_file_offset':'0x37dd28','selector_file_offset':'0x37df00',
            'selector_store_offset':0x5a98,'pointer_store_offset':0x5a9c,
            'pointer_table_link_va':hex(table),'zero_pointer_fallback':'table entry 0',
            'entry0_external_link_va':hex(pointers[0]),'static_rows_inspected':23,'static_row_stride':0x30,
            'stage_field_offsets':[0x14,0x18,0x1c,0x20,0x24],
            'scope':'固定指针表和选定行；不证明全部选择器范围、动态行内容、运行采用值或所有写入者'},
        'static_condition_separation':{
            'capture_effective_index2_static_rows':capture_rows,
            'main_raw_index1_or3_static_rows':main_rows,
            'selected_capture_row':{'index':11,'stage11_to15_fields':list(rows[11])},
            'selected_capture_row_main_raw_value':rows[11][4],
            'scope':'所查静态行没有同时满足前轮捕获索引 2 和 MAIN 索引 1/特殊原值 3；不能拼成已证同次拍摄像素链，也不排除动态行/其他捕获路径'},
        'main_step0':{
            'entry_file_offset':'0x385d00','role_allocator_file_offset':'0x36c8a4',
            'roles_in_call_order':roles,'conditional_role':0x14,
            'direct_slot_offsets':{k:hex(v) for k,v in slots.items()},
            'input_role9_slot_offset':0x5afc,'output_role16_slot_offset':0x5b18,
            'allocator_reply_handle_offset':0xc,'selected_handle_store_file_offset':'0x36c9ba',
            'visible_return_values':[0,5],
            'scope':'各角色已有槽复用或请求分配；本辅助函数的所查直接写槽不含角色 9，不证明全部被调用函数无副作用或像素完成'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '配置指针不是不可变身份；其他写入者和动态行 0 尚未穷举',
            '前轮条件式阶段链存在，不意味着其中两种不同配置下的函数属于同次拍摄',
            '仍需连接其他捕获索引/动态配置到真正 MAIN 输入，并审阅中间组的缓冲转移',
            '直接槽位与角色区分不能代替完整引用、同步、生命周期和硬件像素验证',
            '格式 3/4 有效传输、照片 LUT 使能与色彩仍未闭合'],
        'configuration_pointer_production_located':True,'static_config_condition_separation_located':True,
        'main_step0_role_requests_located':True,'role_allocator_direct_slots_located':True,
        **{k:v for k,v in baseline.items() if v is False},
        'dynamic_config_row_verified':False,'all_work_config_writers_and_effects_verified':False,
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
