"""Read-only preparation descriptors and LUT completion state relationships.

Sparse static register offsets and raw state writes only. No device access,
firmware execution, complete payload, hardware success or photo pixel claim.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_control import trace as trace_control
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp)
    baseline=trace_control(cp_path)
    ranges=[(0xaaabca,0xaaac00),(0xaaad74,0xaaadb6),
            (0xa70fda,0xa71166),(0xa713f0,0xa71576),
            (0xa74d6a,0xa74ec6),(0xa750f0,0xa75218),
            (0xa7aa0c,0xa7aa42),(0xa6ffe4,0xa6fff8),
            (0x3e076c,0x3e0970),(0x3e09f0,0x3e0a40),
            (0x446224,0x44623e),(0x44632c,0x44634a),(0xa7b1f8,0xa7b252)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    def memcpy():return ('blx',f'#{base+0x51660c:#x}')
    require_instructions(index,{
        0xaaabd8:('movs','r1, #0x14'),0xaaabe0:('add','r0, sp, #0x48'),
        0xaaabe2:('blx',f'#{base+0x516d00:#x}'),
        0xaaabe6:('add','r0, sp, #0x30'),0xaaabe8:('movs','r1, #0x18'),
        0xaaabee:('add','r0, sp, #0x10'),0xaaabf0:('movs','r1, #0x1c'),
        0xaaabea:('blx',f'#{base+0x516d00:#x}'),
        0xaaabf2:('blx',f'#{base+0x516d00:#x}'),
        0xaaad76:('add','r5, sp, #0x48'),0xaaad78:('mov','r1, r5'),
        0xaaad7a:call(0xa70fda),0xaaad80:('mov','r1, r5'),0xaaad82:call(0xa7105e),
        0xaaad88:('mov','r1, r5'),0xaaad8a:call(0xa710e2),
        0xaaad90:('movs','r1, #0'),0xaaad94:call(0xa713f0),
        0xaaad9a:('add','r1, sp, #0x30'),0xaaad9c:call(0xa714f4),
        0xaaada2:('add','r1, sp, #0x10'),0xaaada4:call(0xa71472),
        0xa7102a:('movs','r1, #3'),0xa7102c:('mov','r2, r4'),0xa7102e:call(0xa74dae),
        0xa710ae:('movs','r1, #4'),0xa710b0:('mov','r2, r4'),0xa710b2:call(0xa74dae),
        0xa71132:('movs','r1, #5'),0xa71134:('mov','r2, r4'),0xa71136:call(0xa74dae),
        0xa7143e:('movs','r1, #0xb'),0xa71440:('mov','r2, r4'),0xa71442:call(0xa74d6a),
        0xa714c2:('mov','r1, r4'),0xa714c4:call(0xa74e08),
        0xa71544:('mov','r1, r4'),0xa71546:call(0xa74e6a),
        0xa74d8a:('adds','r1, #0x90'),0xa74d8e:('cmp','r0, #0xf'),
        0xa74d96:('movs','r2, #0x8c'),0xa74d98:memcpy(),
        0xa74d9c:('str','r5, [sp, #4]'),0xa74da0:('str','r0, [sp, #0x14]'),
        0xa74da6:call(0xa7aa0c),0xa74dd0:('adds','r0, #1'),
        0xa74dd6:('b',f'#{base+0xa74de0:#x}'),
        0xa74ddc:memcpy(),
        0xa74de0:('ldm.w','r5, {r0, r1, r2}'),
        0xa74de4:('orr.w','r0, r0, r1, lsl #8'),
        0xa74de8:('orr.w','r0, r0, r2, lsl #16'),
        0xa74dee:('ldrd','r0, r1, [r5, #0xc]'),
        0xa74df2:('orr.w','r0, r0, r1, lsl #1'),
        0xa74dfa:('str','r0, [sp, #0x14]'),0xa74e00:call(0xa7aa0c),
        0xa74e22:('cmp','r2, #0xc'),0xa74e5c:('str','r0, [sp, #0x14]'),
        0xa74e62:call(0xa7aa0c),0xa74e84:('cmp','r2, #0xd'),
        0xa74ea0:('ldrd','r0, r1, [r5, #0x10]'),
        0xa74ea4:('orr.w','r0, r1, r0, lsl #1'),
        0xa74eac:('orr.w','r0, r0, r1, lsl #8'),
        0xa74eb0:('orr.w','r0, r0, r2, lsl #16'),
        0xa74eb8:('str','r0, [sp, #0x14]'),0xa74ebe:call(0xa7aa0c),
        0xa7aa14:('mov','r4, r1'),0xa7aa16:call(0xa6fff8),
        0xa7aa1a:('mov','r5, r0'),0xa7aa22:('ldrd','r0, r1, [r4]'),
        0xa7aa26:('ldr.w','r0, [r0, r6, lsl #2]'),
        0xa7aa2a:('ldr.w','r1, [r1, r6, lsl #2]'),
        0xa7aa2e:('add','r0, r5'),0xa7aa30:call(0xa6ffe4),
        0xa6ffe4:('str','r1, [r0]'),0xa6ffea:('ldr','r0, [r0]'),0xa6fff2:('dsb','sy'),
        0x446228:('ldr','r0, [r6]'),0x44622e:('ldr','r1, [r1]'),
        0x446230:('cmp','r1, r0'),0x446232:('bne',f'#{base+0x44627e:#x}'),
        0x446344:('mov','r2, sb'),0x446346:call(0xa71576),
        0x3e0790:('ldrb.w','r0, [sl]'),0x3e0794:('cmp','r0, #0'),
        0x3e0796:('bne.w',f'#{base+0x3e08f2:#x}'),
        0x3e07c0:('movs','r0, #1'),0x3e07c6:('strb.w','r0, [sl]'),
        0x3e07ca:('movs','r0, #2'),0x3e07d0:('str.w','r0, [sb]'),
        0x3e07de:('str','r6, [r0]'),0x3e07e2:('str','r0, [r1]'),
        0x3e087c:call(0x44615c),
        0x3e09f4:('mov','r4, r0'),0x3e09fa:('movs','r1, #0'),
        0x3e0a00:('strb','r1, [r0]'),
        0x3e0a16:('cbz',f'r4, #{base+0x3e0a3e:#x}'),
        0x3e0a34:('movs','r1, #0'),0x3e0a3a:('str','r1, [r5]'),
        0x3e0a3c:('str','r1, [r0]'),0x3e0a3e:('pop','{r4, r5, r7, pc}'),
        0xa7b206:('cbz',f'r5, #{base+0xa7b236:#x}'),
        0xa7b230:('mvn','r0, #5'),0xa7b236:('movs','r0, #0'),
        0xa7b240:('ldr','r1, [r1]'),0xa7b244:('blx','r1'),0xa7b24e:call(0x45b308),
        0xa75110:('mov.w','r8, #3'),0xa7511e:('str.w','r8, [r4, #0x90]'),
        0xa7512a:('mov.w','sb, #4'),0xa75138:('str.w','sb, [r4, #0x120]'),
        0xa75144:('movs','r5, #5'),0xa75150:('str.w','r5, [r4, #0x1b0]'),
        0xa751d4:('movs','r0, #0xb'),0xa751d8:('str.w','r0, [r4, #0x510]'),
        0xa751ec:('movs','r0, #0xc'),0xa751f0:('str.w','r0, [r4, #0x5a0]'),
        0xa75204:('movs','r6, #0xd'),0xa75210:('str.w','r6, [r4, #0x630]'),
    },base)
    require_instructions(index,{a:('movs','r2, #0x8c') for a in
                         (0xa75118,0xa75132,0xa7514a,0xa751d6,0xa751ee,0xa7520a)},base)
    for a in (0xa70fe0,0xa71064,0xa710e8,0xa713f6,0xa71478,0xa714fa):
        require_instructions(index,{a:('mov','r4, r1'),a+2:('mov','r5, r0')},base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    registry=constant(0xa750f0,0xa750fc)
    callback=constant(0x3e086e,0x3e0878)
    busy=constant(0x3e0788,0x3e078c);state=constant(0x3e07b0,0x3e07b4)
    if (registry!=0x1a78d18 or callback!=((base+0x3e09f0)|1)
            or (busy,state)!=(0x1b1e235,0x1a6aefc)
            or busy!=constant(0x3e09f6,0x3e09fc)
            or state!=constant(0x3e0a30,0x3e0a36)
            or constant(0x3e07d4,0x3e07da)!=constant(0x3e0a18,0x3e0a22)
            or constant(0x446224,0x44622a)!=0x1a7e608
            or baseline['photo_pipeline_located'] is not False):
        raise ValueError('描述表、回调、状态或句柄比较位置不符')
    if any(constant(a,b)!=registry for a,b in
           ((0xa74d72,0xa74d7a),(0xa74db6,0xa74dbe),(0xa74e10,0xa74e16),(0xa74e72,0xa74e78))):
        raise ValueError('准备后配置查找不使用同一描述表')
    # Selected initial bindings only, not a dump of the full registry/parameters.
    specs=[(3,0xa7510c,0xa7511a,0xa75114,0xa75122,[0x100,0x110]),
           (4,0xa75126,0xa75134,0xa7512e,0xa7513c,[0x140,0x150]),
           (5,0xa75140,0xa7514c,0xa75146,0xa75154,[0x180,0x190]),
           (11,0xa751d0,0xa751e0,0xa751dc,0xa751e4,[0x340]),
           (12,0xa751e8,0xa751f8,0xa751f4,0xa751fc,[0x380,0x390,0x3b0]),
           (13,0xa75200,0xa7520c,0xa75206,0xa75214,[0x400,0x410,0x414])]
    rows=[]
    for ident,low,high,destination,site,expected in specs:
        template=constant(low,high)
        if template!=0xcfde28+(ident-2)*0x90:
            raise ValueError('选定初始模板地址不符')
        require_instructions(index,{destination:('addw' if ident>=11 else 'add.w',
                                  f'r0, r4, #{4+(ident-2)*0x90:#x}'),site:memcpy()},base)
        if not base<=template<=base+len(cp)-12:
            raise ValueError('模板头越界')
        pointer,_,count=struct.unpack_from('<3I',cp,template-base)
        if not 1<=count<=3 or not base<=pointer<=base+len(cp)-count*4:
            raise ValueError('选定模板偏移数组越界')
        offsets=list(struct.unpack_from('<'+str(count)+'I',cp,pointer-base))
        if offsets!=expected:raise ValueError('选定配置寄存器偏移不符')
        rows.append({'descriptor_id':ident,'register_offsets':offsets,'write_word_count':count})
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'post-prepare-descriptors-and-completion-state-writes',
        'post_prepare_configuration':{
            'entry_file_offset':'0xaaabca','call_sequence':['0xa70fda','0xa7105e','0xa710e2','0xa713f0','0xa714f4','0xa71472'],
            'call_sequence_descriptor_ids':[3,4,5,11,13,12],
            'initial_local_blocks':[{'offset':0x48,'bytes':0x14},{'offset':0x30,'bytes':0x18},{'offset':0x10,'bytes':0x1c}],
            'initial_local_values_all_zero':True,'scalar_argument_for_descriptor_11':0,
            'registry_link_va':hex(registry),'registry_stride':0x90,'copied_descriptor_bytes':0x8c,
            'selected_initial_descriptor_bindings':rows,
            'direct_writer_chain':['0xa7aa0c','0xa6fff8','0xa6ffe4'],
            'register_base_formula':'0xf4009000 + (logical_context << 20)',
            'scope':'初始模板/参数和直接写入代码；表已初始化、源别名、所有接口效果及实际硬件执行未证'},
        'handle_guard':{'file_offset':'0x446230','expected_handle_link_va':'0x1a7e608',
                        'comparison':'full 32-bit equality; no bit31 mask in selected compare block',
                        'scope':'定位值比较，未解释位 31 业务含义或证明跨调用句柄身份'},
        'completion_callback':{
            'callback_file_offset':'0x3e09f0','callback_thumb_link_va':hex(callback),
            'submission_api_file_offset':'0x44615c','controller_callback_file_offset':'0xa7b1f8',
            'controller_input_zero_maps_to_upper_argument':0,
            'controller_input_nonzero_maps_to_upper_argument':-6,
            'busy_byte_link_va':hex(busy),'dispatch_state_word_link_va':hex(state),
            'selected_parameter_word_link_va':hex(constant(0x3e07d4,0x3e07da)),
            'dispatch_visible_stores':{'busy_byte':1,'state_word':2},
            'callback_visible_stores':{'always_busy_byte':0,'nonzero_argument_state_word':0,'nonzero_argument_selected_parameter_word':0},
            'zero_argument_branch_writes_state_word':False,
            'scope':'可见状态存储与回调参数映射；成功回调不等于照片或整帧完成，且锁/并发/运行顺序未证'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '初始零值不证明所有中间被调函数、别名或并发保持参数内存',
            '描述表初始绑定不证明运行时初始化、所有权或表内容不变',
            '配置块 +0x380 与捕获端口基址不同，不能凭相同偏移连接像素',
            '直接写入接口和准备返回值不构成 MMIO 写入成功比较',
            '回调清忙与配置之后的通道置位之间仍有完整时序/并发缺口',
            '保留状态 2 只是成功回调自身可见存储，未穷举其他状态写者',
            '第 28 位/位 31 业务语义、有效像素、MAIN、尺寸和色彩仍未证'],
        'post_prepare_configuration_targets_located':True,'matching_handle_guard_located':True,
        'completion_callback_state_writes_located':True,'callback_submission_lineage_located':True,
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
