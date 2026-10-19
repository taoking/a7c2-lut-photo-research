"""Read-only VFX descriptor copies, address consumption and shared routing.

No whole-program alias proof, hardware output claim, firmware execution or
device payload. Numeric address arithmetic uses synthetic values only.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_capture_buffers import bounded_tbb_targets
from research.trace_capture_effects import trace as trace_effects
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_dispatch import copied_fields
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value


def add_u32_to_address_words(low, high, addend):
    """Model ADDS low + u32 and ADC high + carry, modulo 2**64.

    Does not derive geometry, normalize addresses or encode device parameters.
    """
    if any(type(v) is not int or not 0 <= v <= 0xffffffff for v in (low,high,addend)):
        raise ValueError('地址低/高字及加数需要无符号 32 位整数')
    total=low+addend
    return total & 0xffffffff, (high+(total >> 32)) & 0xffffffff


def address_copy_path():
    """Only offsets/widths through observed copies; no firmware bytes copied."""
    fields=[('candidate_address',0x160,8)]
    scratch=copied_fields(0,0,0x320,0,fields)[0]
    job=copied_fields(0x158,0x168,0x70,8,fields)[0]
    control=copied_fields(0x158,0x160,0x70,0x10,fields)[0]
    return {'bytes':8,'native_offset':0x160,'scratch_offset':scratch['object_offset'],
            'job_offset':job['object_offset'],'job_view_offset':job['consumer_offset'],
            'control_offset':control['object_offset'],
            'control_view_offset':control['consumer_offset']}


def trace(cp_path):
    cp=read_original(cp_path,'cp')
    base=boot_base(cp)
    baseline=trace_effects(cp_path)
    # All four TBB data ranges are excluded from instruction decoding.
    ranges=[(0x4459c8,0x445a2e),(0x445a36,0x445a70),
            (0x445a74,0x445b6e),(0x445b72,0x445dfa),
            (0xaac3a2,0xaac51a),(0xaac7c6,0xaac9f8),
            (0xaac9f8,0xaaca6e),(0x446950,0x4469b8),
            (0x445788,0x44589c),(0x4458ac,0x4458d8),
            (0x44615c,0x446380),(0xaac2da,0xaac302)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(target):return ('bl',f'#{base+target:#x}')
    def copy_call():return ('blx',f'#{base+0x51660c:#x}')
    require_instructions(index,{
        0x4459d2:('ldr','r4, [r7, #0xc]'),
        0x4459d4:('mov','fp, r0'), 0x4459d8:('mov','r6, r1'),
        0x4459da:('mov','r5, r2'), 0x4459dc:('mov','r8, r3'),
        0x4459e6:('movs','r0, #0'), 0x4459e8:('ldr','r1, [r4]'),
        0x4459ea:('add','r2, sp, #0x24'), 0x4459ec:call(0x445788),
        0x445a0e:('strd','r6, r5, [sp, #0x18]'),
        0x445a20:('ldr','r5, [sp, #0x24]'),
        0x445a22:('movs','r0, #1'), 0x445a24:('str','r0, [sp, #0x20]'),
        0x445a26:('cmp','r5, #6'), 0x445a2a:('tbb','[pc, r5]'),
        0x445a36:('uxtb','r0, r5'), 0x445a38:('mov','r4, r5'),
        0x445a3a:('str','r0, [sp, #0x20]'),
        0x445b3e:('movs','r0, #3'), 0x445b40:('movs','r4, #0'),
        0x445b44:('movs','r0, #3'), 0x445b46:('movs','r4, #2'),
        0x445b6a:('tbb','[pc, r0]'),
        0x445b72:('ldr','r1, [sp, #0x18]'),
        0x445b76:('ldr','r1, [sp, #0x1c]'),
        0x445b7a:('mov','r0, sl'), 0x445b7c:('mov','r1, r8'),
        0x445b80:('ldr','r1, [r7, #8]'),
        0x445b82:('mov','r0, sl'), 0x445b84:('mov.w','r2, #0x320'),
        0x445b88:copy_call(),
        0x445bbc:('str','r0, [r6, #0x14]'),
        0x445bc6:('add.w','sb, sl, #0x158'),
        0x445bca:('add.w','r0, r6, #0x168'),
        0x445bce:('movs','r2, #0x70'), 0x445bd0:('mov','r1, sb'),
        0x445bd2:copy_call(), 0x445c12:call(0xaaa378), 0x445c26:call(0xaaa758),
        0x445c5e:('add.w','fp, sl, #0x10'),
        0x445c74:('add.w','r0, sl, #0x160'),
        0x445c78:('mov','r1, sb'), 0x445c7a:('movs','r2, #0x70'),
        0x445c7c:copy_call(),
        0x445cfa:('adds','r4, #8'),
        0x445d4e:('mov','r0, r4'), 0x445d52:call(0xaac3a2),
        0xaac3b2:('mov','r4, r0'), 0xaac3bc:('mov','r0, sb'),
        0xaac3c8:('mov','r3, sb'), 0xaac3d4:('mov','r0, r4'),
        0xaac3d6:call(0xaac3f6),
        0xaac404:('mov','r5, r0'),
        0xaac468:('add.w','r0, r5, sb'), 0xaac46c:('cmp','r6, #2'),
        0xaac46e:('ldr','r2, [r0, #0x10]'),
        0xaac4dc:('mov','r0, r5'), 0xaac4e2:('mov','r1, r6'),
        0xaac4e4:('str.w','fp, [sp]'), 0xaac4e8:call(0xaac7c6),
        0xaac504:('add.w','sb, sb, #0x70'),
        0xaac50a:('adds','r6, #1'), 0xaac50c:('cmp.w','sb, #0x310'),
        0xaac7d2:('rsb','r3, r1, r1, lsl #3'),
        0xaac7da:('add.w','ip, r0, r3, lsl #4'),
        0xaac7e6:('ldrd','r6, fp, [ip, #0x18]'),
        0xaac7ee:('str','r6, [sp, #0x18]'),
        0xaac874:('str.w','fp, [sp, #0x1c]'),
        0xaac8aa:('add.w','r0, r1, r1, lsl #4'),
        0xaac8b4:('add.w','fp, r5, r0, lsl #2'),
        0xaac99e:('ldrd','r2, r1, [sp, #0x18]'),
        0xaac96e:('ldr','r1, [sp, #0x1c]'),
        0xaac970:('ldrd','r3, r2, [sp, #0x14]'),
        0xaac9b8:('adds','r0, r5, r4'), 0xaac9ba:('mla','r0, r0, r3, r6'),
        0xaac9be:('mul','r0, sb, r0'),
        0xaac9c2:('adds.w','r2, r2, r0, lsr #3'),
        0xaac9c6:('ldr.w','r0, [ip, #0x14]'),
        0xaac9ca:('adc','r3, r1, #0'), 0xaac9ce:call(0x446950),
        0xaac9d2:('mov.w','r2, #0x300'),
        0xaac9d6:('and.w','r1, r2, r1, lsl #8'),
        0xaac9da:('strd','r0, r1, [fp, #0x10]'),
        0x446954:('mov','r1, r3'), 0x446956:('cbz',f'r0, #{base+0x44695c:#x}'),
        0x446958:('mov','r4, r2'), 0x44695a:('b',f'#{base+0x4469b2:#x}'),
        0x446966:('ldrd','lr, ip, [r0]'),
        0x446974:('ldrd','r4, r5, [r0, #0x18]'),
        0x44698c:('cmp','r3, #4'),
        0x4469a2:('ldrd','r0, r3, [r0, #0x10]'),
        0x4469b2:('mov','r0, r4'),
        0x445792:('mov','r8, r2'), 0x445794:('mov','r5, r1'),
        0x445796:('mov','r6, r0'),
        0x4457de:('ldr','r2, [r1, #4]'), 0x4457e4:('ldr','r0, [r1]'),
        0x4457e6:('cmp','r0, r5'),
        0x445806:('ldr','r2, [r1, #0xc]'), 0x44580c:('ldr','r0, [r1, #8]'),
        0x44582c:('ldr','r2, [r1, #0x14]'), 0x445832:('ldr','r0, [r1, #0x10]'),
        0x445852:('ldr','r2, [r1, #0x1c]'), 0x445858:('ldr','r0, [r1, #0x18]'),
        0x445890:('subs','r1, r4, #1'), 0x445894:('cmp','r1, #0xe'),
        0x445898:('tbb','[pc, r1]'),
        0x4458ac:('movs','r0, #0'), 0x4458b4:('movs','r0, #1'),
        0x4458b8:('movs','r0, #5'), 0x4458bc:('movs','r0, #2'),
        0x4458c0:('movs','r0, #3'), 0x4458c4:('movs','r0, #6'),
        0x4458c8:('movs','r0, #4'), 0x4458ca:('str.w','r0, [r8]'),
        0x446184:('ldr','r1, [r6]'), 0x446188:('movs','r0, #0'),
        0x44618a:call(0x445788), 0x44619a:('movs','r0, #1'),
        0x44619c:call(0x445788), 0x4461e0:('ldr.w','sl, [sp, #0x38]'),
        0x446234:('add','r1, sp, #0x34'), 0x446236:('mov','r0, sl'),
        0x446238:call(0xaac2da),
        0xaac2e4:('ldr.w','r3, [ip, r2, lsl #3]'),
        0xaac2e8:('cmp','r3, r0'), 0xaac2ee:('cmp','r2, #7'),
        0xaac2f6:('add.w','r0, ip, r2, lsl #3'),
        0xaac2fa:('ldr','r0, [r0, #4]'), 0xaac2fc:('str','r0, [r1]'),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    scratch=constant(0x445b4c,0x445b50)
    job=constant(0x445b8c,0x445b96)
    control=constant(0x445c34,0x445c3c)
    registry=constant(0x4457d4,0x4457da)
    registries=[constant(a,b) for a,b in [(0x4457fe,0x445802),
                                        (0x445824,0x445828),(0x44584a,0x44584e)]]
    lut_table=constant(0xaac2da,0xaac2e0)
    if (scratch,job,control,registry,lut_table)!=(0x2263360,0x2262cd8,0x2263038,0x1a7e578,0xe9d588):
        raise ValueError('描述区或路由注册表地址不符')
    if registries!=[registry]*3:
        raise ValueError('四个注册项不使用同一注册表')
    data_start=lut_table-base
    if not 0 <= data_start <= len(cp)-7*8:
        raise ValueError('逻辑上下文表超出映像')
    contexts=list(struct.iter_unpack('<II',cp[data_start:data_start+7*8]))
    if contexts!=[(i,i) for i in range(7)]:
        raise ValueError('原版逻辑上下文表不符')
    tables=[(0x44589c,15),(0x445a2e,7),(0x445b6e,4),(0x445a70,4)]
    targets=[bounded_tbb_targets(cp[a:a+n],a,len(cp)) for a,n in tables]
    if targets[1]!=(0x445a36,)*4+(0x445b3e,0x445a3c,0x445b44):
        raise ValueError('逻辑路由到通道范围的选择表不符')
    if targets[2]!=(0x445b72,0x445b76,0x445b7a,0x445b80):
        raise ValueError('四个通道指针的选择表不符')
    if targets[3]!=(0x445a74,0x445a7e,0x445a88,0x445a94):
        raise ValueError('通道准备表的已解码目标不符')
    cases={0x4458ac:0,0x4458b4:1,0x4458b8:5,0x4458bc:2,
           0x4458c0:3,0x4458c4:6,0x4458c8:4}
    routes={mask:cases[t] for mask,t in enumerate(targets[0],1) if t in cases}
    if routes!={1:0,2:1,3:5,4:2,8:3,12:6,15:4}:
        raise ValueError('通道掩码到逻辑路由映射不符')
    if any(base+t not in index for table in targets for t in table):
        raise ValueError('选择表目标不是已检查的代码边界')
    lineage=address_copy_path()
    if lineage['job_view_offset']!=3*0x70+0x18:
        raise ValueError('候选双字未落到第 3 号描述项的取值位置')
    if baseline['capture_vfx_uses_user_lut_verified'] is not False:
        raise ValueError('不能沿用未经确认的照片 LUT 状态')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'descriptor-copy-address-consumer-and-shared-logical-routing',
        'address_lineage':lineage,
        'driver_descriptors':{
            'api_file_offset':'0x4459c8','scratch_link_va':hex(scratch),
            'job_link_va':hex(job),'control_link_va':hex(control),
            'native_copy_bytes':0x320,'descriptor_copy_source_offset':0x158,
            'descriptor_copy_bytes':0x70,'job_view_offset':8,
            'control_view_offset':0x10,'intervening_validators':['0xaaa378','0xaaa758'],
            'all_intervening_effects_verified':False},
        'address_consumer':{
            'entry_chain':['0x445d52','0xaac3a2','0xaac3f6','0xaac7c6'],
            'descriptor_count':7,'descriptor_stride':0x70,'candidate_index':3,
            'conditional_on_enabled_descriptor_and_accepted_type':True,
            'pair_load_file_offset':'0xaac7e6','pair_offset_in_indexed_view':0x18,
            'low_add_file_offset':'0xaac9c2','high_adc_file_offset':'0xaac9ca',
            'addend':'32-bit arithmetic result logically shifted right 3; geometry/units not named',
            'normalizer_file_offset':'0x446950',
            'normalizer_behavior':'nonzero mode passes pair; zero mode searches four range mappings',
            'encoded_pair_store_file_offset':'0xaac9da',
            'result_row_stride':0x44,'encoded_pair_row_offset':0x10,
            'encoded_high_word':'(normalized high word << 8) & 0x300',
            'scope':'定位地址计算和传输描述项；未确认硬件方向、实际像素或成功传输'},
        'shared_route_resolver':{
            'file_offset':'0x445788','registry_link_va':hex(registry),
            'registry_count':4,'registry_stride':8,
            'transfer_call_file_offset':'0x4459ec',
            'user_lut_call_file_offsets':['0x44618a','0x44619c'],
            'transfer_kind':0,'user_lut_kinds_tried':[0,1],
            'mask_to_route':[{'mask':m,'route':v} for m,v in routes.items()],
            'route_channel_ranges':[[0,0],[1,1],[2,2],[3,3],[0,3],[0,1],[2,3]],
            'user_lut_context_table_link_va':hex(lut_table),
            'user_lut_logical_contexts':[list(row) for row in contexts],
            'scope':'共用逻辑解析器；实际句柄/时刻和最终硬件通道对应尚未连接'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'excluded_tbb_data':[[hex(a),hex(a+n)] for a,n in tables],
        'limitations':[
            '参数位置连接不是全调用副作用、缓存/别名或运行值保持证明',
            '候选双字参与偏移加法和地址规范化，不能当作最终编码地址直接相等',
            '共用句柄解析器不等于上下层调用拿到同一句柄或最终通道',
            '尚未确认捕获 VFX 的用户 LUT 使能、MAIN 同一缓冲、色域/伽马/尺寸/格式',
            '生成的只是数值报告和合成算术模型，不输出设备参数或载荷'],
        'candidate_field_to_transfer_builder_located':True,
        'transfer_and_user_lut_share_route_resolver':True,
        'lower_driver_output_direction_verified':False,
        'all_intervening_descriptor_effects_verified':False,
        'transfer_and_lut_same_runtime_handle_verified':False,
        'capture_vfx_uses_user_lut_verified':False,'lut_output_to_main_input_connected':False,
        'buffer_identity_and_lifetime_verified':False,'runtime_module_selector_verified':False,
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
