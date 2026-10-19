"""Read-only VFX register projections and conditional handle production.

No hardware direction names, firmware execution, device I/O or payloads.
Numeric helpers model only selected instructions with synthetic integers.
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
from research.trace_vfx_consumers import trace as trace_consumers


def project_mode_bits(control, mode):
    """Only BFI #1,#2; other bits preserved here, not by the full driver."""
    if type(control) is not int or not 0 <= control <= 0xffffffff:
        raise ValueError('控制字需要无符号 32 位整数')
    if type(mode) is not int or not 0 <= mode <= 255:
        raise ValueError('模式字段需要无符号字节')
    return (control & ~6) | ((mode & 3) << 1)


def initial_address_words(format_code, low, encoded_high):
    """Selected stores to +0x20/+0x18 only; not a device parameter builder."""
    if type(format_code) is not int or not 0 <= format_code <= 255:
        raise ValueError('格式字段需要无符号字节')
    if any(type(v) is not int or not 0 <= v <= 0xffffffff for v in (low,encoded_high)):
        raise ValueError('地址字段需要无符号 32 位整数')
    return (0,0) if format_code in (3,4) else (low,encoded_high)


def trace(cp_path):
    cp=read_original(cp_path,'cp')
    base=boot_base(cp)
    baseline=trace_consumers(cp_path)
    # Split code at TBB tables; never decode their bytes/padding as instructions.
    ranges=[(0xaac4ec,0xaac4f8),(0xaac9f8,0xaaca6e),
            (0x446e36,0x446e4e),(0xaaeaaa,0xaaeb2e),
            (0x446f64,0x446f6c),(0x446f70,0x446f96),
            (0xa59526,0xa595c6),(0xa58836,0xa5896c),
            (0xa58998,0xa58a24),(0xa59730,0xa5977c),(0xa58b50,0xa58b92),
            (0x37951a,0x37959a),(0xa0a036,0xa0a0cc),
            (0x3791dc,0x379262),(0x44505c,0x4450d2),
            (0x445168,0x44519a),(0x4451a4,0x4452b8),
            (0x4452d4,0x44535e),(0x445366,0x4453ec),
            (0x379072,0x379084),(0xa234c2,0xa234e8),
            (0x3e076c,0x3e0790),(0x3e086e,0x3e0880)]
    index={i.address:i for a,b in ranges for i in decode_thumb(cp,a,b,base)}
    def call(target):return ('bl',f'#{base+target:#x}')
    require_instructions(index,{
        0xaac4ec:('ldr','r1, [sp, #4]'), 0xaac4ee:('mov','r0, r5'),
        0xaac4f0:('mov','r2, r6'), 0xaac4f2:('mov','r3, fp'), 0xaac4f4:call(0xaac9f8),
        0xaac9fc:('rsb','ip, r2, r2, lsl #3'),
        0xaaca00:('add.w','ip, r0, ip, lsl #4'),
        0xaaca08:('ldr.w','lr, [ip, #0x14]'),
        0xaaca0c:('sub.w','r4, lr, #1'), 0xaaca10:('cmp','r4, #0x10'),
        0xaaca12:('bhs',f'#{base+0xaaca50:#x}'),
        0xaaca18:('movs','r0, #3'), 0xaaca1c:('strb.w','r0, [ip, #0xf]'),
        0xaaca32:('cmp','r2, #3'), 0xaaca34:('mov.w','r2, #0'),
        0xaaca38:('it','lt'), 0xaaca3a:('movlt','r2, #1'),
        0xaaca3c:('cmp','r1, #0'), 0xaaca3e:('it','ne'),
        0xaaca40:('movne','r1, #1'), 0xaaca42:('orrs','r1, r2'),
        0xaaca44:('strb','r1, [r0, #8]'),
        0xaaca54:('cmp.w','lr, #0x11'),
        0xaaca58:('bne',f'#{base+0xaaca66:#x}'),
        0xaaca5a:('movs','r4, #4'), 0xaaca5c:('strb','r4, [r0, #0xf]'),
        0xaaca64:('b',f'#{base+0xaaca28:#x}'),
        0x446e3e:('mov','r0, r4'), 0x446e40:('mov','r1, r6'),
        0x446e4a:('b.w',f'#{base+0xaaeaaa:#x}'),
        0xaaeab4:('mov','sb, r1'), 0xaaeabe:('add.w','r5, r0, #0x20'),
        0xaaead4:('mov','r0, r4'), 0xaaead6:('mov','r1, sb'),
        0xaaead8:call(0x446f64), 0xaaeadc:('mov','r6, r0'),
        0xaaeade:('ldr','r0, [r5, #-0x20]'), 0xaaeae2:('cmp','r0, #1'),
        0xaaeae8:('bne',f'#{base+0xaaeb04:#x}'),
        0xaaeaea:('sub.w','r1, r5, #0x18'), 0xaaeaee:('mov','r0, r6'),
        0xaaeaf0:call(0xa59526), 0xaaeaf8:('mov','r0, r6'),
        0xaaeafa:('mov','r1, r5'), 0xaaeafc:call(0xa59730),
        0xaaeb04:('adds','r5, #0x44'), 0xaaeb06:('adds','r4, #1'),
        0xaaeb08:('cmp','r4, #7'),
        0x446f64:('cmp','r1, #3'), 0x446f68:('tbb','[pc, r1]'),
        0x446f70:('subs','r1, r0, #1'), 0x446f72:('cmp','r1, #6'),
        0x446f76:('adds','r0, #0x57'),
        0x446f7a:('cmp','r0, #7'), 0x446f7e:('adds','r0, #0x7f'),
        0x446f82:('cmp','r0, #7'), 0x446f86:('adds','r0, #0x93'),
        0x446f8a:('cmp','r0, #7'), 0x446f8e:('adds','r0, #0x6b'),
        0xa5952e:('mov','r5, r1'), 0xa59530:('mov','r4, r0'),
        0xa595b2:('mov','r0, r4'), 0xa595b4:('mov','r1, r5'),
        0xa595b6:call(0xa58836),
        0xa58840:('add.w','r0, r0, r0, lsl #1'),
        0xa58848:('add.w','r2, ip, r0, lsl #2'),
        0xa5884c:('ldr.w','lr, [r2, #4]'),
        0xa5885c:('ldrb','r3, [r1]'), 0xa58860:('bfi','r0, r3, #1, #2'),
        0xa588ae:('ldrb','r3, [r1, #7]'),
        0xa58932:('ldr','r0, [r1, #0x10]'),
        0xa58934:('str.w','r0, [lr, #0x24]'),
        0xa58938:('subs','r0, r3, #3'), 0xa5893a:('uxtb','r0, r0'),
        0xa5893c:('cmp','r0, #1'), 0xa5893e:('bhi',f'#{base+0xa58948:#x}'),
        0xa58940:('movs','r1, #0'), 0xa58942:('str.w','r1, [lr, #0x20]'),
        0xa58946:('b',f'#{base+0xa58950:#x}'),
        0xa58948:('ldr','r0, [r1, #8]'), 0xa5894a:('str.w','r0, [lr, #0x20]'),
        0xa5894e:('ldr','r1, [r1, #0xc]'), 0xa58950:('str.w','r1, [lr, #0x18]'),
        0xa5895e:('str.w','r0, [lr]'),
        0xa589bc:('ubfx','r2, r2, #1, #2'), 0xa589c0:('strb','r2, [r1]'),
        0xa59744:('mov','r1, sp'), 0xa59748:call(0xa58998),
        0xa59770:('mov','r0, r5'), 0xa59772:('mov','r1, r4'),
        0xa59774:call(0xa58b50),
        0xa58b64:('ldr','r2, [r1, #8]'), 0xa58b66:('str','r2, [r0, #0x28]'),
        0xa58b68:('ldrh','r2, [r1]'), 0xa58b6a:('str','r2, [r0, #0x2c]'),
        0xa58b6c:('ldr','r2, [r1, #0xc]'), 0xa58b6e:('str','r2, [r0, #0x30]'),
        0xa58b70:('ldrh','r2, [r1, #2]'), 0xa58b72:('str','r2, [r0, #0x34]'),
        0xa58b74:('ldr','r2, [r1, #0x10]'), 0xa58b76:('str','r2, [r0, #0x38]'),
        0xa58b78:('ldrh','r2, [r1, #4]'), 0xa58b7a:('str','r2, [r0, #0x3c]'),
        0xa58b7c:('ldr','r2, [r1, #0x14]'), 0xa58b7e:('str','r2, [r0, #0x40]'),
        0xa58b80:('ldrh','r1, [r1, #6]'), 0xa58b82:('str','r1, [r0, #0x44]'),
        0x379558:('add.w','r5, r1, #8'), 0x379588:('str','r5, [r0]'),
        0xa0a044:('mov','r4, r1'), 0xa0a04c:('ldr','r0, [r4, #0x28]'),
        0xa0a04e:('cbz',f'r0, #{base+0xa0a064:#x}'),
        0xa0a064:('mov','r5, r4'), 0xa0a066:('mov','r1, r4'),
        0xa0a068:('mov','r2, r3'), 0xa0a06a:('ldr','r0, [r5], #0x24'),
        0xa0a06e:('ldr.w','ip, [r0, #8]'), 0xa0a074:('mov','r3, r5'),
        0xa0a076:('blx','ip'),
        0x3791e6:('mov','sl, r1'), 0x3791e8:('mov','r8, r3'),
        0x3791ea:('mov','sb, r2'), 0x37920c:('ldr.w','r0, [sb, #8]'),
        0x379210:('cmp','r0, #1'),
        0x379216:('beq',f'#{base+0x379248:#x}'),
        0x379218:('cbnz',f'r0, #{base+0x379274:#x}'),
        0x37921a:('ldr.w','r3, [sl, #0x12c]'),
        0x379226:('mov','r2, r8'), 0x379228:call(0x44505c),
        0x379256:call(0xaaaa78),
        0x445068:('mov','r5, r3'), 0x44506e:('mov','r8, r2'),
        0x445082:('ldr','r1, [r7, #8]'), 0x445084:('add','r2, sp, #8'),
        0x445086:('mov','r0, r5'), 0x445088:call(0x445168),
        0x445092:('ldr.w','sl, [sp, #8]'), 0x445096:('movs','r0, #0'),
        0x445098:('mov','r1, r8'), 0x44509a:('movs','r3, #1'),
        0x44509c:('mov','r2, sl'), 0x44509e:call(0x4452d4),
        0x445170:('mov','r4, r2'), 0x445172:('mov','r5, r1'),
        0x445174:('mov','r6, r0'), 0x445196:('tbb','[pc, r6]'),
        0x4451ac:('ldr','r1, [r0, #4]'), 0x4451ae:('ldr','r2, [r0, #0xc]'),
        0x4451b0:('ldr','r3, [r0, #0x14]'), 0x4451b2:('ldr','r0, [r0, #0x1c]'),
        0x4451b4:('orrs','r1, r2'), 0x4451b6:('orrs','r1, r3'),
        0x4451b8:('orrs','r0, r1'), 0x4451ba:('bne',f'#{base+0x445254:#x}'),
        0x4451bc:('movs','r0, #9'), 0x445254:('movs','r6, #3'),
        0x445260:('str','r0, [r5]'), 0x445262:('movs','r6, #0'),
        0x445282:('ldr','r0, [r5]'), 0x445284:('subs','r0, #3'),
        0x44528a:('adr','r1, #0x2c'), 0x44528c:('ldr.w','r0, [r1, r0, lsl #2]'),
        0x445290:('str','r0, [r4]'),
        0x4452de:('mov','r6, r3'), 0x4452e0:('mov','r5, r2'),
        0x4452e2:('mov','r8, r1'), 0x4452f2:('mov.w','sb, #1'),
        0x4452e4:('cbz',f'r0, #{base+0x4452f2:#x}'),
        0x445332:('adr','r0, #0xb8'), 0x445334:('ldr.w','r1, [r0, r5, lsl #2]'),
        0x445340:('ldr.w','r1, [r0, r1, lsl #3]'),
        0x445344:('adds','r1, #1'), 0x445346:('pkhbt','r1, r1, r5, lsl #0x10'),
        0x44534a:('cmp','r6, #0'), 0x44534c:('it','eq'),
        0x44534e:('addeq.w','r1, r1, #-0x80000000'),
        0x445354:('str.w','r1, [r8]'), 0x44535a:('tbb','[pc, r5]'),
        0x44538a:('str.w','sb, [r0, #0x14]'),
        0x44538e:('str.w','sb, [r0, #0x1c]'),
        0x445392:('strd','r1, sb, [r0]'), 0x445396:('strd','r1, sb, [r0, #8]'),
        0x44539a:('b',f'#{base+0x4453ae:#x}'),
        0x4453ae:('str','r1, [r0, #0x10]'), 0x4453b0:('adds','r0, #0x18'),
        0x4453b2:('str','r1, [r0]'),
        0x379072:('ldr','r0, [r5, #0x24]'), 0x379078:('str','r0, [sp, #0x1c]'),
        0x37907a:('add','r0, sp, #0x1c'), 0x37907c:('str','r0, [sp, #4]'),
        0x379080:call(0x4459c8),
        0xa234c6:('mov','r4, r0'), 0xa234c8:('movw','r0, #0x13b4'),
        0xa234cc:('movw','r1, #0x13b8'), 0xa234d0:('ldr','r0, [r4, r0]'),
        0xa234d2:('add','r1, r4'), 0xa234d4:call(0x3e076c),
        0x3e077a:('str','r0, [sp, #0x30]'),
        0x3e0874:('add','r3, sp, #0x30'), 0x3e087c:call(0x44615c),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    register_map=constant(0xa5883c,0xa58844)
    vtable_prefix=constant(0x379544,0x379550)
    registries=[constant(a,b) for a,b in [(0x4451a4,0x4451a8),(0x445338,0x44533c)]]
    if register_map!=0x1113fb8 or vtable_prefix+8!=0xe769dc or registries!=[0x1a7e578]*2:
        raise ValueError('寄存器映射、模块虚表或注册表地址不符')
    vtable=vtable_prefix+8
    open_pointer=struct.unpack_from('<I',cp,vtable-base+8)[0]
    if open_pointer!=base+0x3791dc+1:
        raise ValueError('模块打开虚表项不是已核对 Thumb 函数')
    selector_routes=list(struct.unpack_from('<7I',cp,0x4452b8))
    seed_slots=list(struct.unpack_from('<7I',cp,0x4453ec))
    if selector_routes!=[0,1,2,3,5,6,4] or seed_slots!=[0,1,2,3,0,0,2]:
        raise ValueError('选择值/路由或句柄计数来源表不符')
    tables=[(0x446f6c,4),(0x44519a,10),(0x44535e,7)]
    targets=[bounded_tbb_targets(cp[a:a+n],a,len(cp)) for a,n in tables]
    if targets[0]!=(0x446f70,0x446f8a,0x446f7a,0x446f82):
        raise ValueError('端口选择表不符')
    if targets[1]!=(0x4451c4,0x4451dc,0x4451a4,0x4451ee,0x445200,
                     0x445210,0x445220,0x445230,0x445244,0x4451a4):
        raise ValueError('选择值分支表不符')
    if targets[2]!=(0x445366,0x445374,0x44537c,0x445384,0x44538a,0x44539c,0x4453a6):
        raise ValueError('句柄发布分支表不符')
    if any(base+t not in index for row in targets for t in row):
        raise ValueError('选择表目标不是已解码代码边界')
    ports=[offset+3 for offset in (0x57,0x6b,0x7f,0x93)]
    register_bases=[struct.unpack_from('<I',cp,register_map-base+12*port+4)[0] for port in ports]
    if register_bases!=[0xf4000380,0xf4100380,0xf4200380,0xf4300380]:
        raise ValueError('第 3 项的四个端口映射不符')
    if baseline['transfer_and_lut_same_runtime_handle_verified'] is not False:
        raise ValueError('不能继承未经证实的句柄身份')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'register-projections-and-conditional-handle-production',
        'descriptor_register_projection':{
            'builder_file_offset':'0xaac9f8','row_stride':0x44,
            'mode_row_offset':8,'mode_expression':'(index < 3) OR (argument_1 != 0)',
            'format_row_offset':0xf,'types_1_through_16_format_code':3,'type_17_format_code':4,
            'submit_file_offset':'0xaaeaf0','driver_descriptor_row_offset':8,
            'writer_file_offset':'0xa58836','mode_control_bits':[1,2],
            'mode_store_file_offset':'0xa58860','mode_readback_file_offset':'0xa589bc',
            'candidate_encoded_pair_row_offset':0x10,
            'pair_register_offsets':[0x20,0x18],
            'format_codes_clearing_initial_pair':[3,4],
            'other_format_codes':'copy row +0x10/+0x14 to register +0x20/+0x18',
            'distinct_word_mapping':{'row_offset':0x18,'register_offset':0x24},
            'second_submit_file_offset':'0xaaeafc','second_writer_file_offset':'0xa58b50',
            'second_writer_register_offsets':[0x28,0x2c,0x30,0x34,0x38,0x3c,0x40,0x44],
            'register_map_link_va':hex(register_map),'map_entry_bytes':12,
            'candidate_index':3,'ports_by_channel':ports,
            'register_bases_by_channel':[hex(v) for v in register_bases],
            'scope':'静态寄存器访问位置；无读写方向语义、运行地址或成功像素传输结论'},
        'capture_handle_production':{
            'selected_module_vtable_link_va':hex(vtable),'open_vtable_offset':8,
            'base_open_file_offset':'0xa0a036','open_file_offset':'0x3791dc',
            'fresh_open_condition':'module +0x28 == 0',
            'handle_field_offset':0x24,'open_config_mode_offset':8,
            'mode_0_chain':['0x379228','0x44505c','0x445168','0x4452d4'],
            'mode_1_alternate_file_offset':'0xaaaa78','mode_1_internals_verified':False,
            'initial_selector':9,'selector_routes_3_through_9':selector_routes,
            'selector_9_route':4,'selector_9_requires_all_four_kind_words_zero':True,
            'busy_selector_status':3,'registry_link_va':hex(registries[0]),
            'route_seed_slots':seed_slots,
            'handle_formula':'low16(seed_handle + 1) | (route << 16); bit31 added iff parameter == 0',
            'mode_0_publisher_parameter':1,'mode_0_registry_kind_word':1,
            'route_4_publishes_same_handle_to_slots':[0,1,2,3],
            'transfer_handle_read_file_offset':'0x379072',
            'scope':'条件式静态生产/取用；未确认该打开分支在照片拍摄时实际执行或后续释放/改写'},
        'lut_submit_handle_source':{
            'callback_file_offset':'0xa234c2','context_handle_offset':0x13b4,
            'context_lut_parameter_offset':0x13b8,'dispatcher_call_file_offset':'0xa234d4',
            'dispatcher_file_offset':'0x3e076c','local_handle_offset':0x30,
            'user_lut_call_file_offset':'0x3e087c',
            'context_field_producer_verified':False,
            'scope':'读出的句柄被存到局部变量再传指针；与捕获模块 +0x24 的身份仍未连接'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'excluded_tbb_data':[[hex(a),hex(a+n)] for a,n in tables],
        'checked_u32_tables':[['0x4452b8','0x4452d4'],['0x4453ec','0x445408']],
        'limitations':[
            '模式字段写入控制位只证明编码位置，不能将 0/1 命名为硬件读/写',
            '格式 3/4 的本次初始化把候选地址寄存器清零，后续地址/队列/内部连通尚待确认',
            '第 3 项的端口映射不等于捕获、LUT 和 MAIN 最终使用同一硬件路径',
            '初始选择值 9 到路由 4 仅在相关打开分支及占用/锁检查成功时成立',
            'LUT 上下文字段生产、捕获/LUT 实际句柄身份及释放/改写/异步顺序未确认',
            '尚未确认照片 LUT 使能、MAIN 同一缓冲、尺寸/格式/色域/伽马或生命周期'],
        'descriptor_mode_to_register_bits_located':True,
        'conditional_address_register_clearing_located':True,
        'capture_handle_production_branch_located':True,
        'lower_driver_output_direction_verified':False,
        'candidate_pair_reaches_active_pixel_transfer_verified':False,
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
