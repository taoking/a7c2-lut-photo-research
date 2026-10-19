"""Read-only secondary transfer fields and capture/MAIN query boundaries.

Selected scalar/zero fields and validated reply-copy code only. No complete
device parameters, firmware execution, camera I/O or active-pixel claim.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value
from research.trace_vfx_registers import trace as trace_registers


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp)
    baseline=trace_registers(cp_path)
    # The four u32 mask entries after 0x40ea08 are data, never instructions.
    ranges=[(0xaac7c6,0xaac9f8),(0xaac9f8,0xaaca6e),
            (0xaaeaaa,0xaaeb2e),(0xa59730,0xa5977c),(0xa58b50,0xa58b92),
            (0x40e9e0,0x40ea08),(0xa595b2,0xa595ea),
            (0x3818b8,0x38193a),(0x381a06,0x381a86),
            (0x3859dc,0x385a94),(0xa13bb2,0xa13c16),
            (0x409858,0x4099d8)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    def edge(t,m):return (m,f'#{base+t:#x}')
    require_instructions(index,{
        0xaac7da:('add.w','ip, r0, r3, lsl #4'),
        0xaac7e6:('ldrd','r6, fp, [ip, #0x18]'),
        0xaac7ee:('str','r6, [sp, #0x18]'),
        0xaac874:('str.w','fp, [sp, #0x1c]'),
        0xaac8b4:('add.w','fp, r5, r0, lsl #2'),
        0xaac8b8:('mul','r0, r8, sb'),0xaac8bc:('lsrs','r2, r0, #3'),
        0xaac8be:('str.w','r2, [fp, #0x18]'),
        0xaac8cc:('sub.w','r2, r4, r8'),0xaac8d2:('mla','r3, lr, r4, r2'),
        0xaac8d6:('mul','r3, r3, sb'),0xaac8da:('asrs','r4, r3, #0x1f'),
        0xaac8dc:('add.w','r3, r3, r4, lsr #29'),0xaac8e2:('asrs','r3, r3, #3'),
        0xaac8e6:('str','r3, [r4, #0x28]!'),
        0xaac8f4:('movw','r6, #0xffff'),0xaac8f8:('udiv','r5, sl, r3'),
        0xaac8fc:('add','r6, r5'),0xaac8fe:('mov','r5, fp'),
        0xaac900:('strh','r6, [r5, #0x20]!'),
        0xaac920:('movs','r0, #0'),0xaac922:('strh.w','r0, [fp, #0x22]'),
        0xaac926:('str.w','r0, [fp, #0x2c]'),
        0xaac936:('str','r0, [r4]'),0xaac93e:('strh','r1, [r5]'),
        0xaac94c:('str.w','r1, [fp, #0x2c]'),
        0xaac958:('strh.w','r0, [fp, #0x22]'),
        0xaac964:('movs','r0, #0'),0xaac966:('strh.w','r0, [r1, #0xee]'),
        0xaac96a:('str.w','r0, [r1, #0xf8]'),
        0xaac97c:('strh.w','r0, [fp, #0x22]'),
        0xaac99a:('str.w','r0, [fp, #0x2c]'),
        0xaac9a4:('movs','r0, #0'),0xaac9a8:('str.w','r0, [fp, #0x30]'),
        0xaac9ac:('strh.w','r0, [fp, #0x24]'),
        0xaac9b0:('str.w','r0, [fp, #0x34]'),0xaac9b4:('strh.w','r0, [fp, #0x26]'),
        0xaac9c2:('adds.w','r2, r2, r0, lsr #3'),
        0xaac9ca:('adc','r3, r1, #0'),0xaac9ce:call(0x446950),
        0xaac9da:('strd','r0, r1, [fp, #0x10]'),
        0xaaca30:('movs','r3, #0'),0xaaca4c:('str','r3, [r0, #0x1c]'),
        0xaaeabe:('add.w','r5, r0, #0x20'),
        0xaaeaea:('sub.w','r1, r5, #0x18'),0xaaeaf0:call(0xa59526),
        0xaaeafa:('mov','r1, r5'),0xaaeafc:call(0xa59730),0xaaeb04:('adds','r5, #0x44'),
        0xa5973a:('mov','r4, r1'),0xa5973c:('mov','r5, r0'),
        0xa5973e:call(0x40e9e0),0xa59742:('mov','r6, r0'),
        0xa59750:edge(0xa59764,'bne'),0xa59756:edge(0xa59764,'bne'),
        0xa5975c:edge(0xa59764,'bne'),0xa59762:edge(0xa59770,'beq'),
        0xa59764:('mvn','r0, #7'),
        0xa59770:('mov','r0, r5'),0xa59772:('mov','r1, r4'),0xa59774:call(0xa58b50),
        0x40e9f4:('ldr','r0, [r0, #0x1c]'),0x40e9f6:('ubfx','r0, r0, #0x12, #2'),
        0x40e9fe:('adr','r1, #8'),0x40ea00:('ldr.w','r0, [r1, r0, lsl #2]'),
        0x40ea04:('bx','lr'),
        0xa595b6:call(0xa58836),0xa595c8:call(0xa58cc0),
        0xa595cc:('cbnz',f'r0, #{base+0xa595ea:#x}'),0xa595d8:call(0xa58b50),
        0x3818c6:('add.w','fp, sp, #0x40'),0x3818cc:('mov','sl, r0'),
        0x381a2e:('movw','r0, #0x5afc'),0x381a32:('add.w','r1, fp, #0xd8'),
        0x381a36:('ldr.w','r0, [sl, r0]'),0x381a3a:call(0xa13bb2),
        0x3859ee:('ldr','r4, [r4]'),0x3859f8:('movw','r0, #0x5afc'),
        0x3859fc:('ldr','r0, [r4, r0]'),0x3859fe:('add','r1, sp, #0x250'),
        0x385a00:call(0xa13bb2),0x385a5c:('ldrd','r1, r2, [sp, #0x268]'),
        0x385a6c:('strd','r1, r2, [sp, #0x30]'),
        0xa13bba:('mov','r6, r0'),0xa13bbc:('mov','r4, r1'),
        0xa13bca:('mov','r0, r6'),0xa13bcc:('mov','r1, r4'),
        0xa13bce:('movs','r2, #5'),0xa13bd0:call(0x409858),
        0x409862:('mov','r5, r0'),0x409866:('mov','r4, r1'),
        0x4098ac:('movs','r0, #0x2a'),
        0x4098b6:('strh.w','r0, [sb]'),0x4098ba:('movs','r0, #0x55'),
        0x4098bc:('str.w','r5, [sb, #8]'),0x4098c0:('strh.w','r0, [sb, #0x14]'),
        0x409910:call(0xae401c),
        0x409976:('ldrsh.w','r1, [sb, #2]'),0x40997a:('cbz',f'r1, #{base+0x40998a:#x}'),
        0x40998a:('ldrh.w','r1, [sb]'),0x40998e:('movw','r0, #0x802a'),
        0x409992:('cmp','r1, r0'),0x409994:edge(0x4099b8,'bne'),
        0x409996:('ldrh.w','r0, [sb, #6]'),0x40999a:('cmp','r0, #0x55'),
        0x40999c:edge(0x4099b8,'bne'),0x40999e:('ldrh.w','r0, [sb, #8]'),
        0x4099a2:('cbz',f'r0, #{base+0x4099e2:#x}'),
        0x4099a4:('ldr.w','r0, [sb, #0x20]'),0x4099a8:('cbz',f'r0, #{base+0x4099e2:#x}'),
        0x4099aa:('mov','r0, r4'),0x4099ac:('mov','r1, sb'),
        0x4099ae:('movs','r2, #0xd8'),0x4099b0:('blx',f'#{base+0x51660c:#x}'),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    register_map=constant(0x40e9e0,0x40e9e8)
    if (register_map!=0x1113fb8
            or register_map!=constant(0xa58b50,0xa58b58)
            or constant(0xa595ce,0xa595d4)!=0x1a742b0
            or baseline['photo_pipeline_located'] is not False):
        raise ValueError('传输映射、初始配置来源或继承边界不符')
    masks=list(struct.unpack_from('<4I',cp,0x40ea08))
    if masks!=[7,1,15,0]:raise ValueError('两位字段选择的四项掩码表不符')
    for a in (0xa5974c,0xa59752,0xa59758,0xa5975e):
        offset=8+((a-0xa5974c)//6)*4
        require_instructions(index,{a:('ldr',f'r0, [r4, #{offset if offset<10 else hex(offset)}]'),
                                    a+2:('tst','r0, r6')},base)
    rows=[]
    # The second API receives row+0x20. Preserve the mixed u16/u32 widths.
    specs=[(0xa58b64,8,4,0x28,'arithmetic'),(0xa58b68,0,2,0x2c,'count-like halfword; units unknown'),
           (0xa58b6c,12,4,0x30,'branch-dependent arithmetic or zero'),
           (0xa58b70,2,2,0x34,'branch-dependent halfword'),
           (0xa58b74,16,4,0x38,'zero'),(0xa58b78,4,2,0x3c,'zero'),
           (0xa58b7c,20,4,0x40,'zero'),(0xa58b80,6,2,0x44,'zero')]
    for a,source,width,dest,kind in specs:
        source_operand='[r1]' if source==0 else f'[r1, #{source if source<10 else hex(source)}]'
        target_register='r1' if a==0xa58b80 else 'r2'
        require_instructions(index,{a:('ldr' if width==4 else 'ldrh',f'{target_register}, {source_operand}'),
                                   a+2:('str',f'{target_register}, [r0, #{hex(dest)}]')},base)
        rows.append({'row_offset':0x20+source,'bytes':width,'register_offset':dest,'construction':kind})
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'secondary-transfer-field-lineage-and-buffer-query-boundary',
        'secondary_transfer_fields':{
            'builder_file_offset':'0xaac7c6','row_stride':0x44,
            'submission_file_offset':'0xaaeafc','api_file_offset':'0xa59730',
            'api_argument_row_offset':0x20,'writer_file_offset':'0xa58b50','fields':rows,
            'zero_register_offsets_on_selected_builder_path':[0x38,0x3c,0x40,0x44],
            'distinct_word':{'row_offset':0x18,'register_offset':0x24,
                             'raw_expression':'32-bit product of selected scalars, logically shifted right 3'},
            'candidate_address_pair_row_offset':0x10,
            'candidate_pair_register_offsets':[0x20,0x18],
            'formats_clearing_candidate_pair':[3,4],
            'secondary_writer_rewrites_candidate_pair_registers':False,
            'additional_initialization_call_file_offset':'0xa595d8',
            'additional_initialization_source_link_va':'0x1a742b0',
            'scope':'选定构造/写入字段，不据算术或寄存器偏移给出完整几何/地址/硬件方向含义'},
        'secondary_guard':{
            'mask_lookup_file_offset':'0x40e9e0','selector_register_offset':0x1c,
            'selector_lsb':18,'selector_width':2,'mask_table_file_offset':'0x40ea08','mask_table':masks,
            'checked_api_word_offsets':[8,12,16,20],
            'condition':'each selected u32 AND mask == 0 before direct secondary write',
            'scope':'位约束，不命名为已验证像素格式或字节对齐单位'},
        'capture_main_query_boundary':{
            'shared_work_slot_offset':0x5afc,'shared_role_index':9,
            'capture_query_call_file_offset':'0x381a3a','main_query_call_file_offset':'0x385a00',
            'query_wrapper_file_offset':'0xa13bb2','message_api_file_offset':'0x409858',
            'query_third_argument':5,'transport_call_file_offset':'0x409910',
            'request_header':0x2a,'request_command_offset':0x14,'request_command':0x55,
            'request_handle_offset':8,'reply_header':0x802a,'reply_command_offset':6,
            'selected_reply_guards':['signed halfword +2 == 0','halfword +8 != 0','word +0x20 != 0'],
            'reply_copy_file_offset':'0x4099b0','reply_copy_bytes':0xd8,
            'reply_pair_offset':0x18,'capture_candidate_config_pair_offset':0xd8+0x18,
            'main_local_pair_copy_file_offset':'0x385a6c',
            'scope':'两处槽位/查询/字段的静态对应；工作实例、两次响应身份和接收端缓冲生产未证'},
        'critical_gaps':[
            {'id':'P1','gap':'格式 3/4 的实际有效地址和成功像素传输',
             'known':'初始清候选地址寄存器；后续八字段来自选定算术/计数/零值',
             'needed':'实际地址建立/启动路径；不能把剩余寄存器自动当基址'},
            {'id':'P2','gap':'捕获与 User3D 同一运行句柄/通道及照片使能',
             'known':'共用逻辑注册表；位 31 发布差异和多种缓存位写者',
             'needed':'同一实例/时刻的句柄与通道对应、实际模式条件'},
            {'id':'P3','gap':'LUT 输出与 MAIN 输入的同一缓冲和生命周期',
             'known':'两处查询同偏移槽位；通过 0x2a/0x55 消息回复复制信息',
             'needed':'查询接收端的句柄解析/响应生产，以及跨阶段所有权和复用关系'},
            {'id':'P4','gap':'色域/伽马、完整尺寸/格式及同步',
             'known':'只定位字段和原始状态，未证明业务含义或整帧完成',
             'needed':'独立色彩与格式证据；静态无法判定的项目保留为后置观测假设'}],
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'excluded_data_windows':[['0x40ea08','0x40ea18']],
        'secondary_transfer_field_lineage_located':True,'secondary_bit_guard_located':True,
        'buffer_query_reply_copy_located':True,'capture_main_shared_slot_located':True,
        'buffer_query_receiver_located':False,'secondary_register_semantics_verified':False,
        'register_bit_semantics_verified':False,'hardware_control_cache_coherence_verified':False,
        'all_control_writers_and_intervening_effects_verified':False,
        'configuration_completed_before_control_write_verified':False,
        'submission_hardware_consumption_verified':False,'receiver_runtime_delivery_verified':False,
        'runtime_context_category_verified':False,'handle_bit31_semantics_verified':False,
        'transfer_and_lut_same_runtime_handle_verified':False,
        'capture_vfx_uses_user_lut_verified':False,'lut_output_to_main_input_connected':False,
        'candidate_pair_reaches_active_pixel_transfer_verified':False,
        'buffer_identity_and_lifetime_verified':False,'full_resolution_dimensions_verified':False,
        'color_format_enum_verified':False,'ap_to_cp_runtime_verified':False,
        'photo_pipeline_located':False,'camera_commands_sent':False,
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
