"""Read-only native reuse predicates and subsequent scalar configuration.

Raw conditions and selected register fields only; no firmware execution,
camera access, complete device parameters, pixel addresses or hardware proof.
"""
import argparse
import json
from pathlib import Path

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_completion import trace as trace_completion
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_refresh import potential_thumb_path
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp)
    baseline=trace_completion(cp_path)
    ranges=[(0xa29a54,0xa29aac),(0x3e076c,0x3e0970),
            (0xaaaff0,0xaab0ce),(0xa71f0a,0xa71fa2),
            (0xa75010,0xa750e8),(0xa7aaf6,0xa7ab30),
            (0xa7aa6a,0xa7aa8c),(0xa7aaae,0xa7aad0),
            (0xa70354,0xa7041c),(0xa704b2,0xa70548)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    def edge(t,m):return (m,f'#{base+t:#x}')
    require_instructions(index,{
        0xa29a54:('cbz',f'r0, #{base+0xa29aa4:#x}'),
        0xa29a56:('cmp','r1, #0xa'),0xa29a58:edge(0xa29a62,'bne'),
        0xa29a5a:('ldr','r1, [r2, #0x10]'),0xa29a5c:('cmp','r1, #0'),
        0xa29a5e:('it','ne'),0xa29a60:('movne','r1, #0xa'),
        0xa29a6a:('ldr','r3, [r3]'),0xa29a6c:('cmp','r3, #2'),
        0xa29a6e:edge(0xa29aa8,'bne'),0xa29a78:('ldr','r3, [r3]'),
        0xa29a7a:('cmp','r3, r0'),0xa29a7c:edge(0xa29aa8,'bne'),
        0xa29a86:('ldrb','r0, [r0]'),0xa29a88:('eor','r0, r0, #1'),
        0xa29a8c:('lsls','r0, r0, #0x1f'),0xa29a8e:edge(0xa29aa8,'beq'),
        0xa29a90:('cmp','r1, #0xa'),0xa29a92:edge(0xa29aa4,'bne'),
        0xa29a98:('ldr','r0, [r2, #0x58]'),0xa29a9e:('ldr','r1, [r1]'),
        0xa29aa0:('cmp','r1, r0'),0xa29aa2:edge(0xa29aa8,'bne'),
        0xa29aa4:('movs','r0, #1'),0xa29aa6:('bx','lr'),
        0xa29aa8:('movs','r0, #0'),0xa29aaa:('bx','lr'),
        0x3e0776:('mov','r4, r1'),0x3e0778:('cmp','r0, #0'),
        0x3e077a:('str','r0, [sp, #0x30]'),
        0x3e077c:edge(0x3e0968,'beq.w'),0x3e0780:('ldr','r6, [r4]'),
        0x3e0782:('cmp','r6, #0'),0x3e0784:edge(0x3e0968,'beq.w'),
        0x3e0790:('ldrb.w','r0, [sl]'),0x3e0794:('cmp','r0, #0'),
        0x3e0796:edge(0x3e08f2,'bne.w'),0x3e079a:('ldr','r5, [r4, #8]'),
        0x3e079c:('add.w','r8, r4, #0x18'),0x3e07a0:('mov','r0, r6'),
        0x3e07a2:('mov','r2, r8'),0x3e07a4:('mov','r1, r5'),
        0x3e07a6:call(0xa29a54),0x3e07aa:('cmp','r0, #0'),
        0x3e07ac:edge(0x3e08f2,'bne.w'),
        0x3e07e0:('ldr','r0, [r4, #0x70]'),0x3e07e2:('str','r0, [r1]'),
        0x3e08f2:('ldr','r1, [r4, #0x14]'),
        0x3e08f4:('cbz',f'r1, #{base+0x3e094e:#x}'),
        0x3e08fe:('ldr','r0, [r0]'),0x3e0900:('cmp','r0, #2'),
        0x3e0902:edge(0x3e0968,'bne'),0x3e0908:('ldr','r0, [r4, #0x10]'),
        0x3e0916:('ldr','r2, [r6]'),0x3e0918:('cmp','r2, r0'),
        0x3e091a:('it','eq'),0x3e091c:('ldreq','r2, [r5]'),
        0x3e091e:('it','eq'),0x3e0920:('cmpeq','r2, r1'),
        0x3e0922:edge(0x3e0968,'beq'),0x3e0924:('cmp','r0, #0'),
        0x3e0926:('it','eq'),0x3e0928:('moveq','r0, r1'),
        0x3e092a:('add','r2, sp, #0x30'),0x3e092c:call(0xaaaff0),
        0x3e0930:('mov','r1, r0'),0x3e0932:('cbz',f'r1, #{base+0x3e0960:#x}'),
        0x3e0948:('movs','r0, #0'),0x3e094a:('str','r0, [r6]'),
        0x3e094c:edge(0x3e0966,'b'),0x3e0960:('ldr','r0, [r4, #0x10]'),
        0x3e0962:('str','r0, [r6]'),0x3e0964:('ldr','r0, [r4, #0x14]'),
        0x3e0966:('str','r0, [r5]'),
        0xaaaffa:('mov','sl, r0'),0xaaaffe:('mov','r4, r2'),0xaab000:('mov','sb, r1'),
        0xaab00c:('movs','r0, #0'),0xaab00e:('ldr','r1, [r4]'),
        0xaab010:('add','r2, sp, #0x10'),0xaab012:call(0x445788),
        0xaab020:edge(0xaab03c,'beq'),0xaab022:('ldr','r1, [r4]'),
        0xaab024:('add','r2, sp, #0x10'),0xaab026:('movs','r0, #1'),
        0xaab028:call(0x445788),0xaab02e:('cbz',f'r5, #{base+0xaab03c:#x}'),
        0xaab03e:('ldr','r6, [sp, #0x10]'),0xaab054:('mov','r0, r6'),
        0xaab056:call(0xaaadd6),0xaab05c:('cbz',f'r5, #{base+0xaab080:#x}'),
        0xaab080:('add','r1, sp, #0xc'),0xaab082:('mov','r0, r6'),
        0xaab084:call(0xaac2da),0xaab088:('cbz',f'r0, #{base+0xaab0b2:#x}'),
        0xaab08a:('ldr','r0, [sp, #0xc]'),0xaab08c:('mov','r1, sl'),
        0xaab08e:('mov','r2, sb'),0xaab090:call(0xa71f0a),
        0xaab096:('cbz',f'r3, #{base+0xaab0ca:#x}'),0xaab0ca:('movs','r5, #0'),
        0xa71f14:('mov','r5, r2'),0xa71f16:('mov','r6, r1'),0xa71f18:('mov','r4, r0'),
        0xa71f42:('cmp','r4, #7'),0xa71f44:edge(0xa71f5c,'blo'),
        0xa71f5c:('add.w','r8, sp, #0xc'),0xa71f60:('mov','r0, r6'),
        0xa71f62:('mov','r1, r5'),0xa71f64:('mov','r2, r8'),
        0xa71f66:call(0xa7508e),0xa71f6a:('mov','r0, r4'),
        0xa71f6c:('mov','r1, r8'),0xa71f6e:call(0xa75010),
        0xa75082:call(0xa7aaf6),0xa75086:('movs','r0, #0'),
        0xa7508e:('lsls','r0, r0, #9'),0xa75090:('movs','r3, #0'),
        0xa75092:('mov.w','ip, #0'),0xa75096:('udiv','r0, r0, r1'),
        0xa7509a:('uxth','r1, r0'),0xa7509c:('cmp.w','r1, #0x2000'),
        0xa750a0:edge(0xa750b0,'blo'),0xa750a2:('lsrs','r0, r1, #1'),
        0xa750a4:('adds','r3, #1'),0xa750a6:('cmp.w','ip, r1, lsr #14'),
        0xa750aa:('mov','r1, r0'),0xa750ac:edge(0xa750a2,'bne'),
        0xa750b2:('movs','r1, #1'),0xa750b4:('str','r1, [r2]'),
        0xa750b8:('cmp','r1, #0xc'),0xa750ba:('it','hs'),
        0xa750bc:('movhs','r3, #0xc'),0xa750be:('adds','r1, r3, #3'),
        0xa750c0:('strb','r1, [r2, #4]'),0xa750c2:('strb','r1, [r2, #5]'),
        0xa750c4:('strb','r1, [r2, #6]'),0xa750ce:('strh','r0, [r2, #0x14]'),
        0xa750d0:('strh','r0, [r2, #0x16]'),0xa750d2:('strh','r0, [r2, #0x18]'),
        0xa7aafa:('mov','r5, r1'),0xa7aafc:('mov','r4, r0'),
        0xa7aafe:('ldr','r0, [r5]'),0xa7ab00:('cbnz',f'r0, #{base+0xa7ab0a:#x}'),
        0xa7ab0a:('adds','r1, r5, #4'),0xa7ab0c:('mov','r0, r4'),
        0xa7ab0e:call(0xa7aa6a),0xa7ab12:('add.w','r1, r5, #0x14'),
        0xa7ab16:('mov','r0, r4'),0xa7ab18:call(0xa7aaae),
        0xa7ab1c:('ldr','r0, [r5]'),0xa7ab1e:('cmp','r0, #1'),
        0xa7ab20:edge(0xa7ab2e,'bne'),0xa7ab22:('mov','r0, r4'),
        0xa7ab24:('movs','r1, #1'),0xa7ab2a:edge(0xa70354,'b.w'),
        0xa7aa6e:('mov','r4, r1'),0xa7aa70:('mov','r5, r0'),
        0xa7aa72:('ldrb','r1, [r4]'),0xa7aa74:call(0xa70386),
        0xa7aa78:('ldrb','r1, [r4, #1]'),0xa7aa7c:call(0xa703b8),
        0xa7aa80:('ldrb','r1, [r4, #2]'),0xa7aa88:edge(0xa703ea,'b.w'),
        0xa7aab2:('mov','r4, r1'),0xa7aab4:('mov','r5, r0'),
        0xa7aab6:('ldrh','r1, [r4]'),0xa7aab8:call(0xa704b2),
        0xa7aabc:('ldrh','r1, [r4, #2]'),0xa7aac0:call(0xa704e4),
        0xa7aac4:('ldrh','r1, [r4, #4]'),0xa7aacc:edge(0xa70516,'b.w'),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    states={'state_word':constant(0xa29a62,0xa29a66),
            'selected_parameter_word':constant(0xa29a70,0xa29a74),
            'busy_byte':constant(0xa29a7e,0xa29a82),
            'auxiliary_word':constant(0xa29a94,0xa29a9a)}
    if (states!={'state_word':0x1a6aefc,'selected_parameter_word':0x1a6af00,
                 'busy_byte':0x1b1e235,'auxiliary_word':0x1a6af10}
            or constant(0x3e08f6,0x3e08fa)!=states['state_word']
            or constant(0x3e07c2,0x3e07cc)!=states['auxiliary_word']
            or constant(0x3e0904,0x3e090e)!=0x1a6af04
            or constant(0x3e090a,0x3e0912)!=0x1a6af08
            or baseline['photo_pipeline_located'] is not False):
        raise ValueError('前置、回调或后续更新状态位置不符')
    # Seven valid logical contexts only. Selected fields, never a parameter dump.
    specs=[(0xa70354,0x300,0,1),(0xa70386,0x304,0,4),
           (0xa703b8,0x304,8,4),(0xa703ea,0x304,16,4),
           (0xa704b2,0x314,0,13),(0xa704e4,0x314,16,13),
           (0xa70516,0x318,0,13)]
    fields=[]
    for a,offset,lsb,width in specs:
        if constant(a,a+10)!=0xf4009300:
            raise ValueError('标量配置基址不符')
        register='[r3]' if offset==0x300 else f'[r3, #{offset-0x300 if offset-0x300<10 else hex(offset-0x300)}]'
        require_instructions(index,{
            a+8:('cmp','r0, #7'),a+14:('it','lo'),
            a+16:('addlo.w','r3, r2, r0, lsl #20'),
            a+20:('ldr',f'r0, {register}'),
            a+22:('bfi',f'r0, r1, #{lsb if lsb<10 else hex(lsb)}, #{width if width<10 else hex(width)}'),
            a+30:('str',f'r0, {register}'),a+36:('ldr',f'r0, {register}'),
            a+42:('str','r0, [r1]'),
            a+44:('dsb','sy'),a+48:('bx','lr'),
        },base)
        if constant(a+26,a+32)!=0x1a76514:
            raise ValueError('所选字段读回记录位置不符')
        fields.append({'configuration_offset':offset,'lsb':lsb,'width':width})
    # A potential busy edge reaches the scalar call without a completion test.
    # Calls may return; these decisions are not solved runtime predicates.
    dispatcher=blocks[1]
    decisions={0x3e0796:True,0x3e08f4:False,0x3e0902:False,0x3e0922:False}
    if potential_thumb_path(dispatcher,base+0x3e0790,base+0x3e092c,
                            branch_decisions={base+a:v for a,v in decisions.items()}) is None:
        raise ValueError('忙字节旁路不能构成后续更新的潜在路径')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'native-reuse-predicates-and-subsequent-scalar-fields',
        'native_reuse_guard':{
            'entry_file_offset':'0xa29a54','dispatcher_call_file_offset':'0x3e07a6',
            'state_link_vas':{k:hex(v) for k,v in states.items()},
            'guard_arguments_from_dispatcher':['parameter +0','parameter +8','parameter +0x18'],
            'zero_first_argument_returns':1,'dispatcher_rejects_zero_first_argument':True,
            'nonzero_first_argument_result_one_conditions':[
                'state word == 2','saved selected parameter word == first argument',
                'busy byte bit0 == 0',
                'adjusted kind != 10 OR saved auxiliary word == argument block +0x58'],
            'adjusted_kind':'when original kind == 10, use 10 if block +0x10 != 0 else 0; otherwise keep kind',
            'auxiliary_field_dispatcher_offset':0x18+0x58,
            'result_one_edge':'skip full submission and enter 0x3e08f2',
            'scope':'原始值比较；类别/辅助值的拍摄含义、全局并发与实际执行未证'},
        'subsequent_update':{
            'dispatcher_block_file_offset':'0x3e08f2','callee_file_offset':'0xaaaff0',
            'call_file_offset':'0x3e092c',
            'required_conditions':['parameter +0x14 != 0','state word == 2',
                                   '(parameter +0x10, parameter +0x14) differs from cached pair'],
            'cached_pair_link_vas':['0x1a6af04','0x1a6af08'],
            'arguments':['parameter +0x10 if nonzero else parameter +0x14','parameter +0x14','pointer to handle'],
            'zero_return_cached_pair':['original parameter +0x10','original parameter +0x14'],
            'nonzero_return_cached_pair':[0,0],
            'busy_byte_nonzero_can_enter_update':True,
            'busy_edge_potential_branch_witness':{hex(a):v for a,v in decisions.items()},
            'lower_guards':['handle resolver kind0 or kind1 succeeds','cached bit21 range check returns 0',
                            'logical-context mapping succeeds','context < 7 on selected scalar path'],
            'lower_chain':['0xaaaff0','0xa71f0a','0xa7508e','0xa75010','0xa7aaf6'],
            'scope':'参数去重与标量更新路径，不证明必须等待完成回调或完整状态回滚'},
        'scalar_configuration':{
            'constructor_file_offset':'0xa7508e',
            'initial_numeric_operations':['32-bit LSLS first scalar by 9','UDIV by second scalar','UXTH quotient'],
            'later_operations':'selected shift/count normalization; identical three byte fields and three halfword fields',
            'register_base_formula':'0xf4009000 + (logical_context << 20), valid contexts 0..6',
            'selected_register_fields':fields,
            'last_control_write':{'configuration_offset':0x300,'lsb':0,'width':1,'value':1},
            'readback_is_success_comparison':False,
            'scope':'算术派生的标量配置，不是有效像素地址证据；不命名为 RGB/曝光/色彩转换'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '状态 2 不等于整帧完成；忙字节非零也能走标量更新边',
            '前置函数测试忙字节低位，外层首次判定则测试整个字节，不能混写',
            '缓存成功保存原参数而非零值替换后的实参；错误时清两项缓存不等于完整事务回滚',
            '只定位选定配置字段；调用副作用、所有状态写者及运行身份尚未证',
            '数值单位、位功能名、颜色/伽马、格式 3/4 有效像素及 MAIN 仍未证'],
        'native_reuse_guard_located':True,'subsequent_scalar_update_located':True,
        'busy_bypass_update_edge_located':True,'scalar_register_fields_located':True,
        'completion_callback_runtime_execution_verified':False,
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
