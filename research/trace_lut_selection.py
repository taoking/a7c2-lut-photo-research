"""Pinned-original request selection into a direct VFX handle producer.

Reports conditional static table/field/call relationships. Does not execute
firmware, construct device parameters or prove runtime/photo pixel processing.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_capture_buffers import bounded_tbb_targets
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handles import bounded_tbh_targets, trace as trace_handles
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp')
    base=boot_base(cp)
    baseline=trace_handles(cp_path)
    ranges=[(0x3b9ad4,0x3b9af4),(0xa02332,0xa023c8),
            (0x3676e0,0x3676f4),(0x3676fe,0x367770),
            (0x3679c4,0x367a88),
            (0x3b29d0,0x3b2d12),(0x3b2da2,0x3b3b94),
            (0x3dfdd0,0x3dfea0),(0x445660,0x4456c0),
            (0x4452d4,0x44535e)]
    index={i.address:i for a,b in ranges for i in decode_thumb(cp,a,b,base)}
    def call(target):return ('bl',f'#{base+target:#x}')
    require_instructions(index,{
        0x3b9ad4:('mov.w','r0, #0x1500'),
        0x3b9af0:('ldr.w','r0, [sl, r0]'),
        0xa0233c:('subs','r0, #1'), 0xa02342:('cmp','r0, #0xa'),
        0xa02344:('bhs',f'#{base+0xa02364:#x}'),
        0xa0234e:('ldr.w','fp, [r1, r0, lsl #2]'),
        0xa0235a:('ldr.w','r6, [r1, r0, lsl #2]'),
        0xa0237a:('mov.w','sl, #0x6c'),
        0xa02380:('mul','r4, sb, sl'), 0xa02384:('mov','r0, r6'),
        0xa02386:call(0x3676e0), 0xa0238a:('ldrb','r1, [r0, r4]'),
        0xa0238c:('cmp','r1, #1'),
        0xa0238e:('bne',f'#{base+0xa0239c:#x}'),
        0xa02390:('mla','r0, sb, sl, r0'),
        0xa02394:('ldr','r0, [r0, #4]'),
        0xa02396:('str.w','r0, [r8, r5, lsl #2]'),
        0xa0239c:('adds','r6, #1'), 0xa0239e:('cmp','r6, fp'),
        0xa023a0:('bls',f'#{base+0xa02384:#x}'),
        0xa023a2:('cbz',f'r5, #{base+0xa023a8:#x}'),
        0x3676e0:('mov','r2, r0'), 0x3676e2:('subs','r1, r2, #1'),
        0x3676e4:('cmp','r1, #9'), 0x3676f0:('tbb','[pc, r1]'),
        0x3679f4:call(0xa02332),
        0x367a0a:('subs','r0, r5, #1'),
        0x367a10:('movw','r1, #0x8200'),
        0x367a18:('ldr.w','r1, [r1, r0, lsl #2]'),
        0x367a4c:call(0x3b29d0),
        0x3b29e2:('mov','sb, r1'),
        0x3b2a5e:('ldr.w','r5, [sl]'), 0x3b2a62:('mov','r2, sb'),
        0x3b2a64:('cmp','r5, #0x2d'), 0x3b2a66:('it','eq'),
        0x3b2a68:('moveq','r2, #3'), 0x3b2a6a:('cmp.w','sb, #0'),
        0x3b2a6e:('it','ne'), 0x3b2a70:('movne','r2, sb'),
        0x3b2a74:('str','r2, [sp, #0x30]'),
        0x3b2cf8:('ldr','r4, [sp, #0x30]'),
        0x3b2cfc:('str','r0, [sp, #0xa8]'),
        0x3b2cfe:('strd','r0, r4, [sp, #0xa0]'),
        0x3b2d08:('cmp','r5, #0x47'), 0x3b2d0e:('tbh','[pc, r5, lsl #1]'),
        0x3b2eba:('add','r1, sp, #0xa8'), 0x3b2ebc:('add','r2, sp, #0xa4'),
        0x3b2ebe:('mov','r0, r4'), 0x3b2ec0:call(0x3dfdd0),
        0x3b2ec8:('beq.w',f'#{base+0x3b3050:#x}'),
        0x3dfdda:('mov','sb, r2'), 0x3dfde0:('mov','r8, r1'),
        0x3dfdf0:('movs','r2, #3'), 0x3dfdf2:('cmp','r0, #7'),
        0x3dfdf8:('it','lo'), 0x3dfdfa:('addlo','r2, r0, #3'),
        0x3dfdfe:('movs','r4, #0'),
        0x3dfe00:('strd','r2, r1, [sp]'),
        0x3dfe04:('movs','r1, #1'), 0x3dfe06:('mov','r2, r8'),
        0x3dfe08:('movs','r3, #0'), 0x3dfe0a:call(0x445660),
        0x44566e:('mov','r4, r3'), 0x445670:('mov','sb, r2'),
        0x445674:('ldr','r6, [r7, #8]'),
        0x44569e:('mov','r0, r6'), 0x4456a0:call(0x445168),
        0x4456aa:('ldr.w','r8, [sp, #8]'), 0x4456ae:('movs','r0, #0'),
        0x4456b0:('mov','r1, sb'), 0x4456b2:('mov','r3, r4'),
        0x4456b4:('mov','r2, r8'), 0x4456b6:call(0x4452d4),
        0x445344:('adds','r1, #1'),
        0x445346:('pkhbt','r1, r1, r5, lsl #0x10'),
        0x44534a:('cmp','r6, #0'), 0x44534c:('it','eq'),
        0x44534e:('addeq.w','r1, r1, #-0x80000000'),
        0x445354:('str.w','r1, [r8]'),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    lower_va=constant(0xa02352,0xa02356)
    upper_va=constant(0xa02346,0xa0234a)
    selectors_va=constant(0x367a10,0x367a14)
    if (lower_va,upper_va,selectors_va)!=(0xce8230,0xce8260,0xce8200):
        raise ValueError('类别边界或选择值表不符')
    def words(va,count):
        offset=va-base
        if not 0 <= offset <= len(cp)-count*4:
            raise ValueError('u32 表超出映像')
        return list(struct.unpack_from('<'+'I'*count,cp,offset))
    lower=words(lower_va,10);upper=words(upper_va,10);selectors=words(selectors_va,10)
    if lower!=[1,2,3,4,1,3,1,8,9,8] or upper!=[1,2,3,4,2,4,4,8,9,9]:
        raise ValueError('类别到有界家族范围不符')
    if selectors!=[0,1,2,3,4,5,6,0,1,4]:
        raise ValueError('类别到选择参数不符')
    family_tables={
        1:constant(0x3676e8,0x3676ec), 2:constant(0x36773c,0x367740),
        3:constant(0x367746,0x36774a), 4:constant(0x367750,0x367754),
        8:constant(0x3676fe,0x367702), 9:constant(0x36775a,0x36775e)}
    if list(family_tables.values())!=[0x1109f5c,0x110aa54,0x110b54c,0x110c044,0x110cb3c,0x110d634]:
        raise ValueError('请求表家族基址不符')
    family_tbb=bounded_tbb_targets(cp[0x3676f4:0x3676fe],0x3676f4,len(cp))
    if family_tbb!=(0x36773a,0x36773c,0x367746,0x367750,0x367722,
                      0x367722,0x36773a,0x3676fe,0x36775a,0x3676fe):
        raise ValueError('家族选择 TBB 不符')
    task_tbh=bounded_tbh_targets(cp[0x3b2d12:0x3b2da2],0x3b2d12,len(cp))
    if any(base+t not in index for t in family_tbb+task_tbh):
        raise ValueError('选择表目标不是已解码的指令边界')
    rows={}
    for family,va in family_tables.items():
        offset=va-base+0x10*0x6c
        if not 0 <= offset <= len(cp)-8:
            raise ValueError('请求字段超出映像')
        rows[family]=(cp[offset],struct.unpack_from('<I',cp,offset+4)[0])
    if rows!={1:(1,0x17),2:(1,0x1e),3:(1,0x25),4:(1,0x2c),8:(0,0),9:(0,0)}:
        raise ValueError('请求 0x10 的启用字节/实际任务编号不符')
    routes=baseline['capture_open_release']
    selector_routes=words(0x4452b8+base,7)
    if selector_routes!=[0,1,2,3,5,6,4]:
        raise ValueError('驱动选择值到逻辑路由表不符')
    selected=[]
    for category,(lo,hi,selection) in enumerate(zip(lower,upper,selectors),1):
        jobs=[rows[f][1] for f in range(lo,hi+1) if rows[f][0]==1]
        if 0x2d in jobs:
            raise ValueError('本路径需另行分析任务 0x2d 的选择值改写')
        if any(task_tbh[job]!=0x3b2eba for job in jobs):
            raise ValueError('请求选中的任务并非同一直接 VFX 分支')
        selector=selection+3
        selected.append({'category':category,'families':[lo,hi],'enabled_job_ids':jobs,
                         'direct_native_selector_if_jobs_present':selector if jobs else None,
                         'native_route_if_jobs_present':selector_routes[selection] if jobs else None})
    if routes['registry_link_va']!='0x1a7e578':
        raise ValueError('不能与不同注册表比较句柄域')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'request-selected-direct-native-handle-producer',
        'request_selection':{
            'context_category_offset':0x1500,'category_load_file_offset':'0x3b9af0',
            'request_value':0x10,'resolver_file_offset':'0xa02332',
            'family_resolver_file_offset':'0x3676e0','request_row_stride':0x6c,
            'enabled_byte_must_equal':1,'job_id_row_offset':4,
            'category_cases':selected,
            'family_request_rows':[{'family':f,'table_link_va':hex(family_tables[f]),
                                    'enabled':v[0],'job_id':v[1]} for f,v in rows.items()],
            'request_0x10_selected_job_ids':[0x17,0x1e,0x25,0x2c],
            'selected_tbh_target_file_offset':'0x3b2eba',
            'generic_service_branch_job_ids_from_previous_round':[15,16,17,18],
            'scope':'类别 1–7 的静态表选择；8–10 在该请求没有启用项，运行类别/重用状态未验证'},
        'direct_native_output_lineage':{
            'open_chain':['0x3b2ec0','0x3dfdd0','0x445660','0x445168','0x4452d4'],
            'local_token_output_offset':0xa8,
            'producer_output_argument':'0x3dfdd0 r1 -> r8 -> 0x445660 r2 -> sb -> 0x4452d4 r1',
            'publisher_kind_argument':0,'publisher_parameter':0,
            'published_handle_bit31_set_on_this_path':True,
            'capture_module_publisher_parameter_from_round12':1,
            'record_token_offset':0xc,'context_token_offset':0x13b4,
            'record_copy_and_context_store_from_previous_round':['0x3b307e','0x3b322c'],
            'registry_link_va':'0x1a7e578','resolver_file_offset':'0x445788',
            'scope':'LUT 上下文输出在所选分支来自同一原生发布器；不等于捕获模块的实际句柄值'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'excluded_tbb_data':[['0x3676f4','0x3676fe']],
        'excluded_tbh_data':[['0x3b2d12','0x3b2da2']],
        'limitations':[
            '上下文类别的运行来源、其是否属于完整照片流程、重用与释放时刻未验证',
            '类别 1–7 的请求选中直接 VFX 分支，不能把其他通用服务分支令牌混入此路径',
            '两个原生发布调用的标志参数不同；共用注册表不等于运行时同一句柄',
            '位 31 的业务语义未确认，仅记录条件式数值差异',
            '捕获格式 3/4 的有效地址、User3D 最终通道/使能和 MAIN 缓冲仍缺失',
            '没有执行固件、读取硬件寄存器、生成机内参数或补丁'],
        'request_to_actual_direct_vfx_jobs_located':True,
        'conditional_lut_context_to_native_publisher_connected':True,
        'publisher_flag_parameter_difference_located':True,
        'runtime_context_category_verified':False,
        'transfer_and_lut_same_runtime_handle_verified':False,
        'capture_vfx_uses_user_lut_verified':False,'lut_output_to_main_input_connected':False,
        'candidate_pair_reaches_active_pixel_transfer_verified':False,
        'buffer_identity_and_lifetime_verified':False,'lower_driver_output_direction_verified':False,
        'full_resolution_dimensions_verified':False,'color_format_enum_verified':False,
        'ap_to_cp_runtime_verified':False,'photo_pipeline_located':False,'camera_commands_sent':False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cp',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        raw=(json.dumps(trace(args.cp),ensure_ascii=False,indent=2)+'\n').encode()
        write_bytes_new(args.output,raw)
        print(raw.decode(),end='')
        return 0
    except (ValueError,OSError,ImportError) as exc:
        parser.exit(1,f'STOPPED: {exc}\n')


if __name__=='__main__':
    raise SystemExit(main())
