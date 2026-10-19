"""Read-only role-9 allocation replies and capture/MAIN stage work fields.

Selected static dispatch, construction and reply stores only. No complete
messages, firmware execution, device access or verified same-shot identity.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_buffer_lifetime import trace as trace_lifetime
from research.trace_capture_buffers import bounded_tbb_targets
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp);baseline=trace_lifetime(cp_path)
    # Exclude all three inline TBB tables, plus the following strings/padding.
    ranges=[(0x36c70c,0x36c77c),(0x36c79e,0x36c810),(0x3a1940,0x3a1a66),
            (0xa3cc42,0xa3cc5e),(0x40a2e0,0x40a3ea),
            (0x40a3ea,0x40a412),(0x40a4dc,0x40a54c),
            (0x408870,0x4088ec),(0x408940,0x40894a),(0x4089d8,0x408a12),
            (0xb12dba,0xb12de0),(0xb12e84,0xb12ef2),
            (0x37a3dc,0x37a3f0),(0x37a3f4,0x37a42a),
            (0x37a42a,0x37a468),(0x37a960,0x37a974),
            (0x37a97c,0x37aa0c),(0xa0d4d2,0xa0d510),
            (0xa0d698,0xa0d6c4),(0x366884,0x366908),(0x366a08,0x366a84),
            (0x3816c4,0x381790),(0x3859dc,0x385a08)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    def edge(t,m):return (m,f'#{base+t:#x}')
    require_instructions(index,{
        0x36c716:('mov','r4, r0'),0x36c718:('movw','r6, #0x5afc'),
        0x36c71c:('ldr','r0, [r4, r6]'),0x36c71e:('adds','r1, r0, #1'),
        0x36c720:edge(0x36c7c6,'bne.w'),0x36c766:('mov.w','r5, #0x620'),
        0x36c76c:('ldr.w','r3, [r4, #0x210]'),0x36c770:('cmp','r3, #0x21'),
        0x36c772:edge(0x36c7f2,'bhi'),0x36c774:('movw','r5, #0x1df'),
        0x36c778:('tbb','[pc, r3]'),0x36c79e:('add','r3, sp, #8'),
        0x36c7a0:('mov','r0, r5'),0x36c7a2:('movs','r1, #0'),
        0x36c7a4:('mov.w','r2, #-1'),0x36c7ac:call(0x3a1940),
        0x36c7b2:('cbz',f'r2, #{base+0x36c7ce:#x}'),
        0x36c7ce:('ldr','r0, [sp, #0x14]'),0x36c7d0:('add','r6, r4'),
        0x36c7d6:('str','r0, [r6]'),0x36c7dc:('str','r5, [r4, r0]'),
        0x36c80a:('movw','r5, #0x1df'),
        0x3a194a:('mov','r4, r3'),0x3a194c:('mov','r8, r2'),
        0x3a194e:('mov','sb, r1'),0x3a1950:('mov','r6, r0'),
        0x3a19ac:('movs','r0, #5'),0x3a19ae:('movs','r1, #0'),
        0x3a19b0:('mov','r2, sb'),0x3a19b2:('mov','r3, r8'),
        0x3a19b4:('strd','r4, r0, [sp]'),0x3a19b8:('mov','r0, r6'),
        0x3a19ba:call(0xa3cc42),0x3a19be:('ldr','r3, [r4, #0xc]'),
        0x3a1a32:('orr','r1, sb, #0x10'),0x3a1a36:('movs','r2, #0'),
        0x3a1a38:('mov','r3, r4'),0x3a1a3c:('mov','r0, r6'),0x3a1a3e:call(0x408870),
        0xa3cc48:('ldr','r1, [r7, #0xc]'),0xa3cc4a:('ldr.w','ip, [r7, #8]'),
        0xa3cc4e:('str','r1, [sp]'),0xa3cc50:('mov','r1, r2'),
        0xa3cc52:('mov','r2, r3'),0xa3cc54:('mov','r3, ip'),0xa3cc56:call(0x40a2e0),
        0x40a2ea:('mov','sl, r1'),0x40a2ee:('mov','r5, r0'),
        0x40a2f2:('mov','r6, r2'),0x40a2f4:('mov','r4, r3'),
        0x40a332:('mov','r2, sb'),0x40a334:('movs','r3, #0x28'),
        0x40a338:call(0x530176),0x40a344:('movs','r0, #0x20'),
        0x40a346:('strh.w','r0, [r8]'),0x40a34a:('movs','r0, #0x55'),
        0x40a34c:('str.w','r5, [r8, #4]'),0x40a350:('str.w','r6, [r8, #0xc]'),
        0x40a354:('strh.w','r0, [r8, #0x14]'),0x40a35a:('strh.w','sl, [r8, #0x16]'),
        0x40a362:('ldr','r0, [sp, #0x14]'),0x40a364:call(0x45cb38),
        0x40a392:('str','r4, [sp, #8]'),0x40a3a8:call(0x45d3a8),
        0x40a3b6:('mov','r1, r0'),0x40a3b8:('cmp','r1, sb'),
        0x40a3ba:edge(0x40a3ea,'beq'),0x40a3ea:('ldr','r4, [sp, #0x10]'),
        0x40a400:('ldrh','r1, [r4]'),0x40a402:('movw','r0, #0x8020'),
        0x40a406:('cmp','r1, r0'),0x40a40a:('ldrheq','r2, [r4, #6]'),
        0x40a40e:('cmpeq','r2, #0x55'),0x40a410:edge(0x40a4dc,'beq'),
        0x40a4dc:('ldr','r3, [r4, #0xc]'),0x40a4de:('adds','r1, r3, #1'),
        0x40a4e0:edge(0x40a54c,'beq'),0x40a4f4:('ldr.w','r8, [sp, #8]'),
        0x40a504:('str.w','r3, [r8, #0xc]'),
        0x40887a:('mov','r5, r1'),0x40887e:('mov','r4, r0'),
        0x408882:('mov','r6, r2'),0x408884:('mov','r8, r3'),
        0x4088b6:('movs','r2, #0x3c'),0x4088ba:('movs','r3, #0xd8'),
        0x4088bc:('movt','r2, #0x61'),0x4088c0:call(0x530176),
        0x4088cc:('movs','r0, #0x20'),0x4088d6:('strh.w','r0, [sb]'),
        0x4088da:('movs','r0, #0x55'),
        0x4088dc:('str.w','r4, [sb, #4]'),0x4088e0:('str.w','r6, [sb, #0xc]'),
        0x4088e4:('strh.w','r0, [sb, #0x14]'),0x4088e8:('strh.w','r5, [sb, #0x16]'),
        0x408940:('ldr','r1, [sp, #0x10]'),0x408942:('ldr','r0, [sp, #0x18]'),
        0x408944:call(0xae401c),
        0x4089dc:('movw','r0, #0x8020'),0x4089e8:('cmp','r0, #0x55'),
        0x4089ec:('ldr.w','r0, [sb, #0xc]'),0x408a04:('mov','r0, r8'),
        0x408a06:('mov','r1, sb'),0x408a08:('movs','r2, #0xd8'),
        0x408a0a:('blx',f'#{base+0x51660c:#x}'),
        0xb12dc4:('mov','r5, r0'),0xb12dc6:('mov','sl, r1'),0xb12dc8:('mov','r8, r2'),
        0xb12dca:('ldrh','r0, [r5, #0xc]'),0xb12dcc:('orr','r0, r0, #0x8000'),
        0xb12dd0:('strh.w','r0, [sl]'),0xb12dd4:('ldrh','r0, [r5, #0x20]'),
        0xb12dd6:('strh.w','r0, [sl, #6]'),
        0xb12e84:('ldrh','r1, [r5, #0x22]'),0xb12e86:('movw','r0, #0x10f'),
        0xb12e8e:('ands','r0, r1'),0xb12e90:('cmp','r0, #4'),
        0xb12e92:edge(0xb12ee6,'bhi'),0xb12e96:('lsl.w','r0, r2, r0'),
        0xb12e9a:('tst.w','r0, #0x13'),0xb12e9e:edge(0xb12ee6,'beq'),
        0xb12ea0:('ldr','r0, [r5, #0x10]'),0xb12ea2:('add.w','r2, sl, #0xc'),
        0xb12ea6:call(0xb1645a),0xb12eac:('cbnz',f'r6, #{base+0xb12ef2:#x}'),
        0xb12ec4:('ldr.w','r0, [sl, #0xc]'),0xb12ed0:call(0xb16a52),
        0x37a3e0:('mov','r4, r0'),0x37a3e2:('ldrb.w','r0, [r4, #0x27]'),
        0x37a3e6:('cmp','r0, #3'),0x37a3e8:edge(0x37a456,'bhi'),
        0x37a3ec:('tbb','[pc, r0]'),0x37a416:('mov','r0, r4'),
        0x37a418:('pop.w','{r4, r5, r7, lr}'),0x37a41c:edge(0x3816c4,'b.w'),
        0x37a964:('mov','r4, r0'),0x37a966:('ldrb.w','r0, [r4, #0x27]'),
        0x37a96a:('cmp','r0, #6'),0x37a96c:edge(0x37a9a8,'bhi'),
        0x37a970:('tbb','[pc, r0]'),0x37a9ac:('mov','r0, r4'),
        0x37a9ae:('pop.w','{r4, r5, r7, lr}'),0x37a9b2:edge(0x3859dc,'b.w'),
        0xa0d50e:('str','r3, [r2, #0x30]'),0xa0d6c2:('str','r3, [r2, #0x1c]'),
        0x366896:('mov','sb, r1'),0x3668b2:('str.w','sb, [sl]'),
        0x3668b6:('strb.w','r6, [sl, #0x27]'),0x366898:('movs','r6, #0'),
        0x366a18:('mov','fp, r1'),0x366a16:('mov','r8, r2'),
        0x366a36:('str.w','r8, [r4]'),0x366a40:('ldrb.w','r0, [fp, #0x44]'),
        0x366a44:('strb.w','r0, [r4, #0x27]'),
        0x3816ce:('ldr','r4, [r0]'),0x38171c:('mov','r0, r4'),0x38171e:call(0x36c70c),
        0x381786:('mov','r0, r4'),0x381788:('movs','r1, #0x2b'),0x38178a:call(0x3818b8),
        0x3859e8:('mov','r4, r0'),0x3859ea:call(0x384d14),0x3859ee:('ldr','r4, [r4]'),
        0x3859f8:('movw','r0, #0x5afc'),0x3859fc:('ldr','r0, [r4, r0]'),
        0x3859fe:('add','r1, sp, #0x250'),0x385a00:call(0xa13bb2),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    domain=constant(0x40a326,0x40a32a)
    # The other backend uses MOVS/MOVT, checked exactly above; the shared
    # MOVW/MOVT helper deliberately does not accept that different pair.
    if domain!=0x61003c or baseline['photo_pipeline_located'] is not False:
        raise ValueError('角色 9 请求域或前轮验证边界不符')
    handler=struct.unpack_from('<I',cp,0xea64bc-base+0x20*4)[0]
    if handler!=((base+0xb12dba)|1):raise ValueError('操作 0x20 的处理项不符')
    tables={}
    for name,a,n,expected in [
            ('allocation',0x36c77c,34,{0x36c79e,0x36c7f2}),
            ('capture',0x37a3f0,4,{0x37a3f4,0x37a45c,0x37a420,0x37a42a}),
            ('main',0x37a974,7,{0x37a97c,0x37a9ac,0x37a9b6,0x37a9c0,
                                 0x37a9ca,0x37a9d4,0x37a9de})]:
        targets=bounded_tbb_targets(cp[a:a+n],a,len(cp))
        if set(targets)!=expected or any(base+t not in index for t in targets):
            raise ValueError('有界阶段/分配表目标不符或未落在所核对指令边界')
        tables[name]={'table_file_offset':hex(a),'entries':n,'target_file_offsets':[hex(t) for t in targets]}
    if (tables['capture']['target_file_offsets'][0]!='0x37a3f4'
            or tables['main']['target_file_offsets'][1]!='0x37a9ac'
            or constant(0xa0d4fe,0xa0d50a)!=((base+0x37a3dc)|1)
            or constant(0xa0d6b2,0xa0d6be)!=((base+0x37a960)|1)
            or constant(0xa0d4d2,0xa0d4da)!=0x1a50360
            or constant(0xa0d698,0xa0d6a0)!=0x1a5052c):
        raise ValueError('捕获/MAIN 阶段选择或函数登记位置不符')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'role9-allocation-reply-and-stage-work-construction',
        'role9_allocation':{
            'producer_file_offset':'0x36c70c','work_slot_offset':0x5afc,
            'reuse_condition':'existing work slot != 0xffffffff returns without the selected allocation call',
            'request_function_file_offset':'0x3a1940','selected_kind_candidates':[0x1df,0x620],
            'caller_option':0,'caller_third_argument':-1,'reply_handle_offset':0xc,
            'success_slot_store_file_offset':'0x36c7d6',
            'selected_backends':[
                {'chain':['0x3a19ba','0xa3cc42','0x40a2e0'],'request_option':0,'request_capacity':0x28,
                 'reply_handle_copy_file_offset':'0x40a504'},
                {'chain':['0x3a1a3e','0x408870'],'request_option':0x10,'request_capacity':0xd8,
                 'reply_copy_file_offset':'0x408a0a','reply_copy_bytes':0xd8}],
            'scope':'已有槽复用、两条条件式后端及成功写槽；不证明运行采用哪条后端或分配成功'},
        'allocation_opcode':{
            'domain_id':hex(domain),'opcode':0x20,'reply_opcode':0x8020,
            'request_tag':0x55,'request_tag_offset':0x14,'reply_tag_offset':6,
            'request_kind_offset':4,'request_option_offset':0x16,
            'handler_file_offset':'0xb12dba','handler_thumb_link_va':hex(handler),
            'selected_option_gate':'(option & 0x10f) in {0, 1, 4}',
            'unit_allocator_file_offset':'0xb1645a','allocator_handle_output':'reply +0xc',
            'optional_address_resolver_file_offset':'0xb16a52',
            'scope':'与查询操作 0x2a 共用已核对分发域；0x55 为回显标识，不是操作码；处理后段及所有副作用未穷举'},
        'stage_work_construction':{
            'initial_constructor_file_offset':'0x366884','initial_work_source':'argument r1 -> stage +0',
            'initial_selector':'stage byte +0x27 = 0',
            'next_constructor_file_offset':'0x366a08','next_work_source':'argument r2 -> new stage +0',
            'next_selector_source':'argument r1 descriptor byte +0x44 -> new stage byte +0x27',
            'scope':'新阶段工作指针来自显式参数，未证明它必等于旧阶段工作指针'},
        'capture_main_dispatch':{
            'selector_offset':0x27,'capture_dispatch_file_offset':'0x37a3dc','capture_selected_value':0,
            'capture_tail_file_offset':'0x37a41c','capture_entry_file_offset':'0x3816c4',
            'capture_work_load_file_offset':'0x3816ce','main_dispatch_file_offset':'0x37a960',
            'main_selected_value':1,'main_tail_file_offset':'0x37a9b2','main_entry_file_offset':'0x3859dc',
            'main_work_load_file_offset':'0x3859ee','main_prequery_helper_file_offset':'0x384d14',
            'capture_registration_store':{'base_link_va':'0x1a50360','offset':0x30},
            'main_registration_store':{'base_link_va':'0x1a5052c','offset':0x1c},
            'forwarding':'selected tail branches pass their original stage pointer as r0',
            'scope':'两种分发表、函数登记与工作字段；不将两个入口当成同一运行阶段/工作实例'},
        'bounded_tables':tables,'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '分配和查询的静态字段衔接不证明消息运行送达、分配成功或同次拍摄',
            '构造器可显式传入新工作指针；仍需核对具体阶段切换、调度及中间改写',
            '阶段选择值 0/1 不是已验证的相机模式枚举',
            'MAIN 查询前调用 0x384d14，全部调用效果和槽位变化尚未穷举',
            '角色 9/10 的既有转移与单元代号循环仍影响身份/生命周期判断',
            '格式 3/4 有效传输、LUT 照片使能、色彩与完整同步仍未闭合'],
        'role9_allocation_reply_path_located':True,'allocation_opcode_handler_located':True,
        'stage_work_constructor_fields_located':True,'capture_main_tail_dispatch_located':True,
        'capture_and_main_same_work_instance_verified':False,
        'all_descriptor_lists_bounded_to_record_verified':False,'unit_descriptor_allocation_lifecycle_verified':False,
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
