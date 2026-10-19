"""Read-only buffer-query registration, opcode dispatch and address production.

Sparse static evidence from the pinned CP only; no firmware execution, device
access, complete message construction or active photo-pixel verification.
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
from research.trace_transfer_fields import trace as trace_fields


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp)
    baseline=trace_fields(cp_path)
    ranges=[(0x409890,0x4098c4),(0x40990c,0x409914),(0x530176,0x5301ba),
            (0xae401c,0xae4024),(0x495da4,0x495dca),
            (0x45c902,0x45c95e),(0x45c96c,0x45c9b8),
            (0x45cdf0,0x45ce22),(0x45cee4,0x45cef0),
            (0xae3c34,0xae3c60),(0xae428e,0xae42a0),
            (0xb1620a,0xb1623e),(0xb13df6,0xb13ed6),
            (0xb13f96,0xb13fde),(0xb13764,0xb137ac),(0xb16a52,0xb16b4c)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    def edge(t,m):return (m,f'#{base+t:#x}')
    def memcpy():return ('blx',f'#{base+0x51660c:#x}')
    require_instructions(index,{
        0x409896:('movs','r2, #0x3c'),0x409898:('add','r0, sp, #4'),
        0x40989a:('movs','r3, #0xd8'),0x40989c:('movt','r2, #0x61'),
        0x4098a0:call(0x530176),0x4098bc:('str.w','r5, [sb, #8]'),
        0x4098ba:('movs','r0, #0x55'),0x4098c0:('strh.w','r0, [sb, #0x14]'),
        0x40990c:('ldr','r1, [sp, #4]'),0x40990e:('ldr','r0, [sp, #0xc]'),
        0x409910:call(0xae401c),
        0x53017e:('mov','r4, r0'),0x530184:('add.w','r0, r4, #8'),
        0x53018e:('stm','r0!, {r2, r5, r6}'),0x530194:('mov','r0, r2'),
        0x530196:('mov','r2, r3'),0x530198:call(0x40ab24),
        0xae401c:('movs','r2, #0'),0xae401e:('movs','r3, #0'),
        0xae4020:edge(0x45cd60,'b.w'),0x495daa:('movs','r0, #0x3c'),
        0x495db8:('movt','r0, #0x61'),0x495dc4:call(0x45c8f8),
        0x45c908:('mov','r4, r2'),0x45c90a:('mov','r8, r3'),
        0x45c94a:('strd','fp, fp, [sl, #8]'),
        0x45c974:('str.w','r1, [sl, #8]'),0x45c978:('strd','r4, r8, [sl, #0x14]'),
        0x45c98e:('ldr','r0, [r4, #0x14]'),0x45c990:('cbnz',f'r0, #{base+0x45c9a6:#x}'),
        0x45c9a2:('str.w','sl, [r4, #0x14]'),
        0x45cdf2:call(0xae399a),0x45cdf6:('mov','sb, r0'),
        0x45ce18:('ldr.w','r5, [sb, #0x14]'),
        0x45cee4:('ldr','r3, [r5, #8]'),0x45ceec:('blx','r3'),
        0xae3c3c:('mov','r4, r2'),0xae3c3e:('mov','r6, r0'),0xae3c40:('mov','r5, r1'),
        0xae3c48:('ldrd','r2, r1, [r5, #0x14]'),
        0xae3c4c:('add.w','r0, r6, #0x18'),0xae3c50:('blx','r2'),
        0xae4290:('ldr','r0, [r0, #-0x8]'),
        0xb16210:('mov','r4, r0'),0xb16212:call(0xae428e),
        0xb16220:call(0xae402a),0xb16224:('uxth','r2, r5'),
        0xb16226:('mov','r1, r4'),0xb16228:call(0xb13df6),
        0xb13e00:('add','r4, sp, #0xe8'),0xb13e02:('mov','sl, r1'),
        0xb13e04:('mov','r6, r0'),0xb13e08:('mov','fp, r2'),
        0xb13e10:('add.w','sb, sp, #0x10'),0xb13e14:('movs','r1, #0xd8'),
        0xb13e18:('blx',f'#{base+0x516d00:#x}'),
        0xb13e1c:('adds','r4, #0xc'),0xb13e20:('mov','r1, sl'),
        0xb13e22:('cmp.w','fp, #0x28'),0xb13e26:('mov','r0, r4'),
        0xb13e28:('it','lo'),0xb13e2a:('movlo','r2, fp'),
        0xb13e2c:('it','hs'),0xb13e2e:('movhs','r2, #0x28'),0xb13e30:memcpy(),
        0xb13e7e:('ldrh.w','r0, [sp, #0xf4]'),0xb13e8c:('cmp','r0, #0x2e'),
        0xb13e8e:edge(0xb13eb2,'blo'),0xb13ebe:('add.w','r2, sb, #0x18'),
        0xb13ec6:('ldr.w','r3, [r1, r0, lsl #2]'),
        0xb13eca:('add','r0, sp, #0xe8'),0xb13ecc:('mov','r1, sb'),0xb13ece:('blx','r3'),
        0xb1376c:('mov','r5, r0'),0xb1376e:('mov','r4, r1'),
        0xb13770:('movw','r1, #0x1001'),0xb13774:('ldrh','r0, [r5, #0xc]'),
        0xb13776:('add.w','r3, r4, #8'),0xb1377a:('orr','r0, r0, #0x8000'),
        0xb1377e:('strh','r0, [r4]'),0xb13780:('ldrh','r0, [r5, #0x20]'),
        0xb13782:('strh','r0, [r4, #6]'),0xb13784:('ldr','r0, [r5, #0x14]'),
        0xb13788:call(0xb16a52),0xb13796:call(0xb15bc2),
        0xb16a58:('strh.w','r0, [sp]'),0xb16a5c:('movw','r4, #0x3ff'),
        0xb16a60:('ldrh.w','ip, [sp]'),0xb16a6c:('bfc','ip, #0xa, #0x16'),
        0xb16a70:('cmp','ip, r4'),0xb16a72:edge(0xb16a7e,'bne'),
        0xb16a86:('ldr','r4, [r4]'),0xb16a88:('add.w','ip, r4, ip, lsl #6'),
        0xb16a8c:('ldrb.w','r4, [ip, #0xb]'),0xb16a90:('ubfx','r0, r0, #0xa, #5'),
        0xb16a94:('cmp','r0, r4'),0xb16a96:edge(0xb16abe,'bne'),
        0xb16a9e:('ldrh','r4, [lr, #0xc]!'),0xb16aa2:('subs','r5, r4, #1'),
        0xb16aa4:('cmp','r5, #2'),0xb16aa6:edge(0xb16ac4,'bhs'),
        0xb16ab0:('movw','r5, #0x1001'),0xb16ab4:('cmp','r1, r5'),
        0xb16ab6:edge(0xb16ae6,'beq'),0xb16ac4:('cmp','r4, #3'),
        0xb16ac6:edge(0xb16b36,'bne'),0xb16ac8:('movw','r0, #0x1001'),
        0xb16acc:('cmp','r1, r0'),0xb16ace:edge(0xb16ae6,'beq'),
        0xb16ae6:('ldrh.w','lr, [ip, #0xe]'),0xb16aee:('strh.w','lr, [r3]'),
        0xb16af4:('add.w','ip, ip, #0x10'),0xb16af8:('movs','r3, #0'),
        0xb16afa:('ldr.w','r5, [ip, r3, lsl #2]'),0xb16afe:('ldrd','r4, r1, [r5, #8]'),
        0xb16b02:('ldr','r0, [r5, #0x10]'),0xb16b04:('adds','r0, r0, r4'),
        0xb16b06:('str','r0, [r2]'),0xb16b08:('adc','r0, r1, #0'),
        0xb16b0e:('str','r0, [r2, #4]'),0xb16b10:('ldr','r0, [r5, #0x14]'),
        0xb16b12:('str','r0, [r2, #8]'),0xb16b14:('adds','r2, #0x10'),
        0xb16b18:edge(0xb16afa,'blo'),
        0xb13f96:('ldrh.w','r0, [sp, #0x10]'),0xb13f9a:('movw','r1, #0x8020'),
        0xb13f9e:('subs','r1, r0, r1'),0xb13fa0:('movs','r0, #0x28'),
        0xb13fa2:('cmp','r1, #0xa'),0xb13fa4:edge(0xb13fca,'bhi'),
        0xb13fa8:('lsl.w','r1, r2, r1'),0xb13fac:('movw','r2, #0x457'),
        0xb13fb0:('tst','r1, r2'),0xb13fb2:edge(0xb13fca,'beq'),
        0xb13fb4:('ldrh.w','r0, [sp, #0x18]'),0xb13fb8:('subs','r1, r0, #1'),
        0xb13fbc:('cmp','r1, #0xb'),0xb13fbe:edge(0xb13fc8,'bhi'),
        0xb13fc0:('movs','r1, #0x18'),0xb13fc2:('add.w','r0, r1, r0, lsl #4'),
        0xb13fcc:('cmp','r1, fp'),0xb13fce:('it','hi'),0xb13fd0:('movhi','r0, fp'),
        0xb13fd2:('add','r1, sp, #0x10'),0xb13fd6:('mov','r0, sl'),0xb13fda:memcpy(),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    domain=index[base+0x409896].operands[1].imm | (index[base+0x40989c].operands[1].imm<<16)
    registration_domain=index[base+0x495daa].operands[1].imm | (index[base+0x495db8].operands[1].imm<<16)
    callback=constant(0x495db0,0x495dc0)
    adapter=constant(0x45c96c,0x45c970)
    table=constant(0xb13eba,0xb13ec2)
    units=constant(0xb16a7e,0xb16a82)
    if (domain!=0x61003c or domain!=registration_domain
            or callback!=((base+0xb1620a)|1) or adapter!=((base+0xae3c34)|1)
            or table!=0xea64bc or units!=0x1a8c558
            or baseline['photo_pipeline_located'] is not False):
        raise ValueError('查询域、回调、操作表或单元表位置不符')
    table_offset=table-base
    if not 0<=table_offset<=len(cp)-0x2e*4:
        raise ValueError('有界操作表超出原版映像')
    handler=struct.unpack_from('<I',cp,table_offset+0x2a*4)[0]
    if handler!=((base+0xb13764)|1):raise ValueError('操作 0x2a 的 Thumb 处理项不符')
    if (0x55!=baseline['capture_main_query_boundary']['request_command']
            or not ((1<<((0x2a|0x8000)-0x8020))&0x457)):
        raise ValueError('历史字段值或操作 0x2a 的回复长度分支不符')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'buffer-query-registration-dispatch-and-unit-record-addresses',
        'query_registration':{
            'domain_id':hex(domain),'registration_call_file_offset':'0x495dc4',
            'registration_api_file_offset':'0x45c8f8','callback_file_offset':'0xb1620a',
            'callback_thumb_link_va':hex(callback),'common_adapter_file_offset':'0xae3c34',
            'sender_object_constructor_file_offset':'0x530176','sender_domain_object_offset':8,
            'scope':'相同注册域、回调描述及发送对象字段；初始化成功、全调用副作用和运行送达未证'},
        'opcode_dispatch':{
            'dispatcher_file_offset':'0xb13df6','table_link_va':hex(table),
            'opcode_upper_bound_exclusive':0x2e,'selected_opcode':0x2a,
            'selected_handler_file_offset':'0xb13764','selected_handler_thumb_link_va':hex(handler),
            'request_copy_log_offset':0xc,'request_copy_bytes':'min(message capacity, 0x28)',
            'reply_address_records_offset':0x18,
            'request_tag_offset':0x14,'selected_request_tag':0x55,'reply_tag_offset':6,
            'tag_relationship':'request +0x14 -> internal log +0x20 -> reply +6, copied halfword',
            'prior_report_label_correction':'trace_transfer_fields 的 command 字段为历史位置标签；0x55 是回显标识，不是第二个分发操作码'},
        'handle_to_reply_addresses':{
            'resolver_file_offset':'0xb16a52','selected_resolver_option':0x1001,
            'lookup_uses_low_handle_bits':16,'slot_lsb':0,'slot_width':10,'rejected_slot':0x3ff,
            'tag_lsb':10,'tag_width':5,'record_tag_byte_offset':0xb,
            'unit_table_pointer_link_va':hex(units),'unit_record_stride':0x40,
            'record_state_halfword_offset':0xc,'selected_option_accepted_raw_states':[1,2,3],
            'record_count_halfword_offset':0xe,'reply_count_halfword_offset':8,
            'descriptor_pointer_array_offset':0x10,'descriptor_pointer_stride':4,
            'descriptor_base_pair_offset':8,'descriptor_addend_offset':0x10,
            'reply_pair_expression':'descriptor u64 at +8 plus u32 at +0x10, with carry',
            'descriptor_word_offset':0x14,'reply_record_word_offset':8,'reply_record_stride':0x10,
            'post_resolution_call_file_offset':'0xb13796','post_resolution_callee':'0xb15bc2',
            'scope':'运行单元记录的间接字段来源；记录分配/复用、容量、地址空间及真实像素仍未证'},
        'reply_copy_boundary':{
            'reply_header_expression':'request opcode OR 0x8000','selected_reply_header':0x802a,
            'selected_count_range_for_variable_length':[1,12],
            'selected_length_expression':'0x18 + 0x10 * count, otherwise 0x28',
            'copy_length_limit':'min(selected length, caller message capacity)',
            'maximum_selected_variable_length':0x18+0x10*12,
            'copy_call_file_offset':'0xb13fda',
            'scope':'回复复制分支上界，不代表已证明单元记录计数/分配容量或全部别名安全'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '0x55 是回显标识；不能把同一个请求值再当一层操作分发',
            '静态注册/字段连接不证明运行初始化、送达、锁和全部同步',
            'DMM 单元句柄的低 16 位解析不能套用到原生 VFX 位 31 业务语义',
            '回复地址来自描述基址加偏移，描述的分配/更新/释放/复用还未追完',
            '未穷举查询后处理 b15bc2、其他调用、全局别名和并发副作用',
            '捕获与 MAIN 两次请求的实例/句柄/回复身份以及格式 3/4 实际传输仍未证'],
        'buffer_query_receiver_located':True,'request_tag_echo_located':True,
        'handle_record_address_production_located':True,'bounded_reply_copy_located':True,
        'buffer_query_runtime_delivery_verified':False,'unit_descriptor_allocation_lifecycle_verified':False,
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
