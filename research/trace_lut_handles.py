"""Read-only LUT handle output lineage and capture release branches.

Static field and call relationships only. No runtime identity, active pixel
transfer, firmware execution, device access or generated payloads.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_capture_buffers import bounded_tbb_targets
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value
from research.trace_vfx_registers import trace as trace_registers


def bounded_tbh_targets(entries, table_offset, image_size):
    """Resolve 1–256 supplied little-endian halfwords, not firmware discovery.

    Caller establishes TBH, the index bound and table base independently.
    Targets must clear the entire table and fit a Thumb halfword in the image;
    each result still needs a separately decoded instruction boundary.
    """
    if (not isinstance(entries,(bytes,bytearray)) or len(entries) % 2
            or not 2 <= len(entries) <= 512):
        raise ValueError('需要 1–256 项的小端有界 TBH 表')
    if (type(table_offset) is not int or type(image_size) is not int
            or not 0 <= table_offset < image_size <= 0x100000000
            or table_offset % 2):
        raise ValueError('TBH 表基址/映像范围无效')
    end=table_offset+len(entries)
    if end > image_size:
        raise ValueError('TBH 表被映像边界截断')
    targets=tuple(table_offset+2*row[0] for row in struct.iter_unpack('<H',entries))
    if any(target < end or target+2 > image_size for target in targets):
        raise ValueError('TBH 目标落在表或映像范围之外')
    return targets


def trace(cp_path):
    cp=read_original(cp_path,'cp')
    base=boot_base(cp)
    baseline=trace_registers(cp_path)
    # The 72-entry TBH and seven-entry TBB including padding are data only.
    ranges=[(0x3b9b02,0x3b9b70),(0xa28e92,0xa290d0),
            (0x3679c4,0x367a88),(0x3b29d0,0x3b2d12),(0x3b2da2,0x3b3b94),
            (0x3dd778,0x3dd7fc),(0x43f320,0x43f3f0),
            (0x4380bc,0x4380d8),(0x43817a,0x43821c),
            (0xa9ce0a,0xa9ce1e),(0xaa0f94,0xaa0fa6),
            (0xaaaa78,0xaaab20),(0x4452d4,0x4452fa),
            (0x37936c,0x379418),(0x379444,0x3794fa),
            (0xa0a0cc,0xa0a146),(0xaaa222,0xaaa2d8),(0xaab1e0,0xaab284),
            (0x4458d8,0x44590e),(0x445916,0x445958),
            (0xa59652,0xa596c8),(0xa5896c,0xa58998),(0x173270,0x1734ac)]
    index={i.address:i for a,b in ranges for i in decode_thumb(cp,a,b,base)}
    def call(target):return ('bl',f'#{base+target:#x}')
    require_instructions(index,{
        0x3b9b02:('movw','r3, #0x13b4'), 0x3b9b06:('add','r3, sl'),
        0x3b9b08:('str','r3, [sp, #0x18]'), 0x3b9b6c:call(0xa28e92),
        0xa28e94:('add','r7, sp, #0xc'),
        0xa28fea:('ldr.w','ip, [r7, #0x20]'),
        0xa28ff8:('strd','r1, ip, [sp, #0x10]'),
        0xa28ffe:('movs','r1, #0x10'), 0xa29006:call(0x3679c4),
        0x3679c6:('add','r7, sp, #0xc'),
        0x3679f4:call(0xa02332), 0x3679f8:('cbz',f'r0, #{base+0x367a1e:#x}'),
        0x367a44:('ldr','r0, [r7, #0x1c]'),
        0x367a46:('str','r0, [sp, #0x18]'), 0x367a4c:call(0x3b29d0),
        0x3b29d2:('add','r7, sp, #0xc'),
        0x3b2c16:('add.w','r8, r1, sb, lsl #6'),
        0x3b2c3e:('str.w','r8, [sp, #0x20]'),
        0x3b2d08:('cmp','r5, #0x47'),
        0x3b2d0a:('bhi.w',f'#{base+0x3b340e:#x}'),
        0x3b2d0e:('tbh','[pc, r5, lsl #1]'),
        0x3b2e1e:('add','r0, sp, #0xa0'),
        0x3b2e22:('str','r0, [sp]'), 0x3b2e24:('add','r2, sp, #0xa8'),
        0x3b2e26:('add','r3, sp, #0xa4'), 0x3b2e28:('mov.w','r0, #0x400000'),
        0x3b2e2c:call(0x3dd778),
        0x3b2e32:('beq.w',f'#{base+0x3b3050:#x}'),
        0x3b3060:('ldm','r3, {r1, r2, r3}'),
        0x3b3050:('add','r3, sp, #0xa0'),
        0x3b3076:('add.w','r5, r4, r5, lsl #6'),
        0x3b307e:('strd','r8, r3, [r5, #8]'),
        0x3b314a:('ldr.w','r8, [sp, #0x20]'),
        0x3b31bc:('ldr.w','r8, [sp, #0x20]'),
        0x3b31f4:('mov','lr, r8'),
        0x3b31f6:('ldr.w','r8, [r7, #0x20]'),
        0x3b3222:('cmp.w','r8, #0'),
        0x3b3226:('beq',f'#{base+0x3b3230:#x}'),
        0x3b3228:('ldr.w','r0, [lr, #0xc]'),
        0x3b322c:('str.w','r0, [r8]'),
        0x3dd784:('mov','r4, r2'), 0x3dd788:('ldr','r2, [r7, #8]'),
        0x3dd792:('str','r4, [sp]'), 0x3dd7a8:call(0x43f320),
        0x43f32c:('ldr','r0, [r7, #8]'), 0x43f330:('mov','r5, r2'),
        0x43f33e:('str','r0, [sp, #0x18]'),
        0x43f362:('str','r5, [sp, #0x14]'),
        0x43f364:('add','r1, sp, #0x18'), 0x43f366:('add','r2, sp, #0x1c'),
        0x43f368:('strd','r2, r1, [sp]'), 0x43f372:call(0x4380bc),
        0x4380be:('add','r7, sp, #0xc'),
        0x4380c8:('mov','sb, r2'), 0x4380ca:('mov','r8, r1'),
        0x43817a:('mov','r0, r5'),
        0x4381e6:('mov','r0, r5'), 0x4381e8:call(0xa9ce0a),
        0x4381ec:('ldr','r1, [r7, #0xc]'), 0x4381ee:('ldr','r1, [r1]'),
        0x4381f0:('str','r0, [r1]'),
        0xa9ce0a:('ldr.w','r0, [r0, #0x90]'), 0xa9ce0e:('bx','lr'),
        0xa9ce10:('ldrb.w','r2, [r0, #0x8c]'),
        0xa9ce14:('orr.w','r1, r1, r2, lsl #16'),
        0xa9ce18:('str.w','r1, [r0, #0x90]'),
        0xaa0f94:('ldrh.w','r0, [r8, #0xc]'), 0xaa0f98:('adds','r0, #1'),
        0xaa0f9a:('strh.w','r0, [r8, #0xc]'), 0xaa0f9e:('uxth','r1, r0'),
        0xaa0fa0:('mov','r0, r4'), 0xaa0fa2:call(0xa9ce10),
        0xaaaa86:('mov','r6, r3'), 0xaaaa8a:('mov','r8, r2'),
        0xaaaa9e:('ldr','r1, [r7, #8]'), 0xaaaaa0:('add','r2, sp, #4'),
        0xaaaaa2:('mov','r0, r6'), 0xaaaaa4:call(0x445168),
        0xaaaaac:('ldr.w','sb, [sp, #4]'), 0xaaaab0:('movs','r0, #1'),
        0xaaaab2:('mov','r1, r8'), 0xaaaab4:('movs','r3, #1'),
        0xaaaab6:('mov','r2, sb'), 0xaaaab8:call(0x4452d4),
        0x4452e6:('cmp','r0, #1'), 0x4452ea:('mov.w','sb, #2'),
        0x379380:('ldr','r0, [r5]'), 0x379382:('ldr.w','r1, [r4, #0x130]'),
        0x379386:('cmp','r1, r0'), 0x3793e6:('movs','r0, #1'),
        0x37944a:('str','r2, [sp, #0x14]'),
        0x37947a:('add','r2, sp, #0x14'), 0x37947e:call(0x44673c),
        0x379498:('ldr.w','r0, [r4, #0x148]'), 0x37949c:('cmp','r0, #1'),
        0x37949e:('beq',f'#{base+0x3794aa:#x}'),
        0x3794a0:('cbnz',f'r0, #{base+0x3794cc:#x}'),
        0x3794a2:('add','r0, sp, #0x14'), 0x3794a4:call(0xaaa222),
        0x3794aa:('add','r0, sp, #0x14'), 0x3794ac:call(0xaab1e0),
        0x3794e8:('movs','r0, #1'), 0x3794ee:('strb','r0, [r5]'),
        0xa0a0da:('mov','r4, r1'), 0xa0a0e2:('ldr','r0, [r4, #0x28]'),
        0xa0a0e4:('cmp','r0, #1'), 0xa0a0e6:('bne',f'#{base+0xa0a10c:#x}'),
        0xa0a0ea:('ldr','r2, [r4, #0x24]'),
        0xa0a0ee:('ldr','r3, [r0, #0x10]'), 0xa0a0f2:('blx','r3'),
        0xa0a0f8:('tst.w','r0, #0xff'),
        0xa0a100:('beq',f'#{base+0xa0a13e:#x}'),
        0xa0a102:('mov.w','r0, #-1'), 0xa0a106:('str','r0, [r4, #0x24]'),
        0xa0a110:('subs','r0, #1'), 0xa0a114:('str','r0, [r4, #0x28]'),
        0xaaa248:('movs','r0, #0'), 0xaaa24a:call(0x445788),
        0xaaa268:call(0x4458d8),
        0xaab206:('movs','r0, #1'), 0xaab208:call(0x445788),
        0xaab214:call(0x4458d8),
        0x445906:('add.w','r0, r1, #0xc'), 0x44590a:('tbb','[pc, r4]'),
        0x445920:('movs','r0, #0'), 0x445922:('str','r0, [r1, #4]'),
        0x445924:('str','r0, [r1, #0xc]'),
        0x445926:('b',f'#{base+0x445930:#x}'),
        0x445930:('str','r0, [r1, #0x14]'),
        0x445932:('add.w','r0, r1, #0x1c'),
        0x445936:('movs','r1, #0'), 0x445938:('str','r1, [r0]'),
        0xa59662:('ldrb','r1, [r4]'),
        0xa59674:('ldrb','r0, [r0, r5]'), 0xa59676:('cmp','r0, r1'),
        0xa59678:('bne',f'#{base+0xa596c2:#x}'), 0xa5967e:call(0xa5896c),
        0xa58980:('ldr','r2, [r1, #0xc]'), 0xa58982:('str','r2, [r0, #0x24]'),
        0xa58984:('ldrb','r2, [r1]'), 0xa58986:('cbz',f'r2, #{base+0xa5898e:#x}'),
        0xa58988:('movs','r1, #0'), 0xa5898a:('str','r1, [r0, #0x20]'),
        0xa5898c:('b',f'#{base+0xa58994:#x}'),
        0xa5898e:('ldr','r2, [r1, #4]'), 0xa58990:('str','r2, [r0, #0x20]'),
        0xa58992:('ldr','r1, [r1, #8]'), 0xa58994:('str','r1, [r0, #0x18]'),
        0x173450:('mov','r1, sp'), 0x173452:('movs','r0, #0xad'),
        0x173456:call(0xa59652),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    records=constant(0x3b2c0c,0x3b2c12)
    registry=constant(0x4458fe,0x445902)
    if records!=0x1a539a8 or registry!=0x1a7e578:
        raise ValueError('任务记录或下层注册表地址不符')
    vtable=baseline['capture_handle_production']['selected_module_vtable_link_va']
    vtable=int(vtable,16)
    pointers=struct.unpack_from('<II',cp,vtable-base+0xc)
    if pointers!=(base+0x37936c+1,base+0x379444+1):
        raise ValueError('配置检查/释放虚表项不符')
    tbh=bounded_tbh_targets(cp[0x3b2d12:0x3b2da2],0x3b2d12,len(cp))
    if tbh[0xf:0x13]!=(0x3b2e1e,)*4:
        raise ValueError('任务编号 15–18 的服务分支不符')
    tbb=bounded_tbb_targets(cp[0x44590e:0x445915],0x44590e,len(cp))
    if tbb!=(0x445916,0x445936,0x44591a,0x445932,0x445920,0x445928,0x44592e):
        raise ValueError('路由到类型字清除分支不符')
    if any(base+t not in index for row in (tbh,tbb) for t in row):
        raise ValueError('表目标不是独立解码的指令边界')
    if baseline['transfer_and_lut_same_runtime_handle_verified'] is not False:
        raise ValueError('不能继承未经证实的运行句柄身份')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'conditional-handle-output-and-release-lineage',
        'lut_handle_output_lineage':{
            'caller_file_offset':'0x3b9b02','context_field_offset':0x13b4,
            'call_chain':['0x3b9b6c','0xa28e92','0x3679c4','0x3b29d0'],
            'request_value_at_middle_call':0x10,
            'stack_pointer_offsets':[
                {'callee':'0xa28e92','incoming_sp_offset':0x18,'forwarded_sp_offset':0x14},
                {'callee':'0x3679c4','incoming_sp_offset':0x14,'forwarded_sp_offset':0x18},
                {'callee':'0x3b29d0','incoming_sp_offset':0x18,'store_file_offset':'0x3b322c'}],
            'record_array_link_va':hex(records),'record_stride':0x40,
            'record_token_offset':0xc,'record_to_output_store_file_offset':'0x3b322c',
            'record_token_source':'successful selected branch: local +0xa8 via 0x3b307e',
            'service_branch_job_ids':[15,16,17,18],
            'service_branch_chain':['0x3b2e2c','0x3dd778','0x43f320','0x4380bc'],
            'service_return_field_offset':0x90,
            'service_token_assembly':'low16(manager u16 +0xc incremented) OR (object byte +0x8c << 16)',
            'service_object_index_producer_verified':False,
            'actual_job_selection_from_request_verified':False,
            'backend_token_to_driver_handle_conversion_verified':False,
            'scope':'连接非空输出指针与任务记录字段；未证明每次请求走同一分支、相同实例或最终下层句柄'},
        'capture_open_release':{
            'mode_1_open_file_offset':'0xaaaa78','shared_selector_file_offset':'0x445168',
            'shared_publisher_file_offset':'0x4452d4','mode_1_publisher_kind_argument':1,
            'mode_1_registry_kind_word':2,
            'config_compare_vtable_offset':0xc,'config_compare_file_offset':'0x37936c',
            'release_vtable_offset':0x10,'release_file_offset':'0x379444',
            'base_release_file_offset':'0xa0a0cc','module_count_offset':0x28,
            'module_handle_offset':0x24,
            'last_reference_condition':'module count == 1; callee success byte != 0',
            'last_reference_handle_sentinel':0xffffffff,
            'base_skips_own_count_and_handle_stores_on_last_reference_failure':True,
            'other_counts':'decrement branch, including wrap if zero; caller preconditions not proven',
            'mode_0_release_file_offset':'0xaaa222','mode_1_release_file_offset':'0xaab1e0',
            'registry_resolver_file_offset':'0x445788','kind_clear_file_offset':'0x4458d8',
            'registry_link_va':hex(registry),'route_4_explicit_zero_offsets':[4,12,20,28],
            'handle_words_explicitly_zeroed_by_kind_clear':False,
            'kind_invalidation_precedes_further_cleanup_calls':True,
            'scope':'静态引用计数/释放分支；完整并发、错误清理和重用时序未验证'},
        'address_update':{
            'entry_file_offset':'0xa59652','writer_file_offset':'0xa5896c',
            'nonzero_mode_requires_cached_format_match':True,
            'nonzero_first_byte':'clear both +0x20/+0x18 address registers',
            'zero_first_byte':'copy argument +4/+8 to +0x20/+0x18 after validation',
            'checked_caller_entry_file_offset':'0x173270',
            'checked_caller_call_file_offset':'0x173456','checked_caller_port':0xad,
            'candidate_capture_ports':[0x5a,0x6e,0x82,0x96],
            'scope':'已核对直接调用端口不同，尚未连接捕获格式 3/4 的有效像素地址'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'excluded_tbh_data':[['0x3b2d12','0x3b2da2']],
        'excluded_tbb_data_and_padding':[['0x44590e','0x445916']],
        'limitations':[
            '请求值 0x10 与任务编号 0–71 属于不同选择域，不直接等同',
            '上下文输出指针已追到任务记录 +0xc，但服务令牌到下层句柄的转换尚未连接',
            '配置检查虚表项 +0xc 不是释放项；释放使用 +0x10',
            '类型字清除保留显式句柄字，不证明其他调用/别名/异步状态不改变',
            '下层类型字清除先于后续清理；基础包装的失败分支不能当作整个关闭事务未改变状态',
            '引用计数零值的先决条件、并发保护和完整错误补偿尚未验证',
            '独立端口 0xad 的地址更新不能直接套用捕获候选端口',
            '照片 LUT 使能、MAIN 同一缓冲、格式/尺寸/色彩和生命周期仍未完成'],
        'lut_context_output_pointer_lineage_located':True,
        'capture_release_and_kind_invalidation_located':True,
        'alternate_open_publisher_kind_located':True,
        'separate_address_update_caller_located':True,
        'lut_context_complete_handle_producer_verified':False,
        'transfer_and_lut_same_runtime_handle_verified':False,
        'candidate_pair_reaches_active_pixel_transfer_verified':False,
        'lower_driver_output_direction_verified':False,
        'all_intervening_descriptor_effects_verified':False,
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
