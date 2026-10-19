"""Read-only User3D receive/dispatch and configuration command construction.

Static matching queue IDs, selected fields and bounded dispatch only. No device
I/O, firmware execution, complete payload or actual LUT/photo enable claim.
"""
import argparse
import json
from pathlib import Path

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_capture_buffers import bounded_tbb_targets
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_context import trace as trace_context
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp')
    base=boot_base(cp)
    baseline=trace_context(cp_path)
    # Exclude the inline TBB bytes and generic queue diagnostic literals.
    ranges=[(0xa7ac22,0xa7acb6),(0x42d33c,0x42d376),(0x42d37c,0x42d3f4),
            (0xa7adbe,0xa7ae00),(0xa7b3f4,0xa7b46e),(0xa6fff8,0xa7000e),
            (0x42d3f4,0x42d58e),(0xa7b062,0xa7b1f8),(0xa7b1f8,0xa7b282),
            (0x45cb38,0x45cbbc),(0x45cbc0,0x45cc56),(0x45cc58,0x45ccd4),
            (0x45d3a8,0x45d45a)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(target):return ('bl',f'#{base+target:#x}')
    require_instructions(index,{
        0xa7ac34:('add','r5, sp, #0xc'),
        0xa7ac42:('mov','r0, r4'),0xa7ac44:('mov','r1, r5'),
        0xa7ac46:('mov.w','r2, #-1'),0xa7ac4a:call(0x45d3a8),
        0xa7ac4e:('mov','r6, r0'),
        0xa7ac50:('cbz',f'r6, #{base+0xa7ac7a:#x}'),
        0xa7ac7a:('ldr','r0, [sp, #0xc]'),0xa7ac7c:call(0x42d33c),
        0xa7ac80:('ldr','r1, [sp, #0xc]'),0xa7ac82:('mov','r0, r4'),
        0xa7ac84:call(0x45d300),
        0xa7ac8c:('beq',f'#{base+0xa7ac42:#x}'),
        0x45cb46:('mov','r4, r0'),0x45cb4e:('mov','r6, r1'),
        0x45cb64:('uxth.w','sl, r4'),
        0x45cb68:('cmp.w','r4, #-1'),
        0x45cb6c:('bgt',f'#{base+0x45cbc0:#x}'),
        0x45cbc0:('mov','r0, sl'),0x45cbc2:call(0xae399a),
        0x45cbc6:('mov','r8, r0'),
        0x45cbfc:('ldr.w','r0, [r8, #0x1c]'),
        0x45cc00:('sub.w','r4, r6, #0x18'),
        0x45cc04:call(0xae37dc),
        0x45cc58:('str','r4, [r5]'),
        0x45cc7a:('str','r4, [r5]'),0x45cc7c:('str','r4, [r1]'),
        0x45d3b6:('mov','r6, r0'),0x45d3be:('mov','sb, r1'),
        0x45d3e8:('uxth','r0, r6'),0x45d3ea:call(0xae399a),
        0x45d3ee:('mov','r8, r0'),
        0x45d40a:('ldr.w','r3, [r8, #8]'),
        0x45d420:('add.w','r0, r3, #0x18'),
        0x45d426:('str.w','r0, [sb]'),
        0x45d42a:('ldr.w','r0, [r8, #8]'),
        0x45d42e:('ldr','r0, [r0]'),0x45d430:('str.w','r0, [r8, #8]'),
        0x42d342:('mov','r4, r0'),0x42d36c:('ldr','r0, [r4]'),
        0x42d36e:('cmp','r0, #5'),
        0x42d370:('bhi',f'#{base+0x42d3c4:#x}'),
        0x42d372:('tbb','[pc, r0]'),0x42d394:('mov','r0, r4'),
        0x42d39c:('b.w',f'#{base+0xa7adbe:#x}'),
        0xa7adc8:('mov','r4, r0'),
        0xa7add4:('add.w','r1, r4, #0x1c'),0xa7add8:('mov','r2, r5'),
        0xa7adda:('ldr','r0, [r4, #8]'),0xa7addc:call(0xa7b3f4),
        0xa7ade4:('mov','r0, r5'),0xa7adea:('mov','r1, r6'),
        0xa7adec:call(0x42d3f4),0xa7adf0:('ldr','r1, [r4, #0xc]'),
        0xa7adf2:('mov','r0, r6'),0xa7adf4:call(0xa7b062),
        0xa7b3f8:('ldr.w','lr, [r1]'),
        0xa7b406:('str','lr, [r3], #4'),
        0xa7b40a:('ldrd','lr, r4, [r1, #0x10]'),
        0xa7b40e:('orr.w','r4, r4, lr, lsl #1'),0xa7b412:('str','r4, [r3]'),
        0xa7b414:('ldrd','lr, r4, [r1, #4]'),0xa7b418:('ldr','r1, [r1, #0xc]'),
        0xa7b41a:('orr.w','r4, lr, r4, lsl #8'),
        0xa7b41e:('orr.w','r1, r4, r1, lsl #16'),
        0xa7b424:('str.w','r1, [ip, #8]'),
        0xa7b428:('str','r0, [r2]'),0xa7b42a:('movs','r0, #3'),
        0xa7b42c:('mov.w','r1, #0x400'),0xa7b430:('str','r0, [r2, #4]'),
        0xa7b43a:('str.w','ip, [r0]'),0xa7b43e:('str','r1, [r0, #4]'),
        0xa7b440:('movs','r1, #1'),0xa7b442:('str','r1, [r0, #8]'),
        0xa7b446:('str.w','r3, [r0, #0x8c]'),
        0xa7b44a:('mov.w','r3, #0x410'),
        0xa7b44e:('strd','r3, r1, [r0, #0x90]'),
        0xa7b452:('add.w','r3, ip, #8'),0xa7b456:('movw','ip, #0x414'),
        0xa7b45e:('strd','r3, ip, [r0, #0x118]'),
        0xa7b462:('str.w','r1, [r0, #0x120]'),
        0xa7b46a:('str','r0, [r2, #8]'),
        0xa6fff8:('cmp','r0, #7'),
        0xa6fffa:('bhs',f'#{base+0xa7000a:#x}'),
        0xa70004:('add.w','r0, r1, r0, lsl #20'),
        0xa7000a:('movs','r0, #0'),
        0x42d400:('mov','fp, r0'),0x42d402:('ldr.w','r0, [fp]'),
        0x42d406:call(0xa6fff8),0x42d40a:('str','r0, [sp, #4]'),
        0x42d416:('ldr.w','r0, [fp, #8]'),
        0x42d422:('ldr','r1, [sp, #8]'),0x42d424:('ldr','r2, [sp, #4]'),
        0x42d426:('add.w','sl, r1, sb, lsl #4'),
        0x42d42a:('ldr','r1, [r0, #4]'),0x42d42c:('add','r1, r2'),
        0x42d432:('str.w','r1, [sl, #4]'),
        0x42d56e:('ldr.w','r0, [fp, #8]'),0x42d572:('add.w','sb, sb, #1'),
        0x42d576:('adds','r0, #0x8c'),0x42d578:('str.w','r0, [fp, #8]'),
        0x42d57c:('ldr.w','r1, [fp, #4]'),0x42d580:('cmp','sb, r1'),
        0x42d582:('blo.w',f'#{base+0x42d422:#x}'),
        0xa7b06c:('mov','r6, r0'),0xa7b070:('mov','r4, r1'),
        0xa7b0b4:('str.w','r4, [sb]'),
        0xa7b116:('add','r1, sp, #0xc'),0xa7b118:('movs','r0, #5'),
        0xa7b11e:call(0x4790bc),
        0xa7b126:('movs','r0, #5'),0xa7b128:('mov','r1, r6'),
        0xa7b12a:call(0xaeefa4),
        0xa7b176:('mov','r0, r4'),0xa7b178:('mov.w','r1, #0x3e8'),
        0xa7b17c:call(0x45b09c),
        0xa7b200:('mov','r5, r0'),
        0xa7b236:('movs','r0, #0'),0xa7b240:('ldr','r1, [r1]'),
        0xa7b244:('blx','r1'),0xa7b24e:call(0x45b308),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    request_id=constant(0xa7ac2c,0xa7ac3a)
    callback=constant(0xa7b112,0xa7b11a)
    hardware_base=constant(0xa6fffc,0xa70000)
    signal_id=constant(0xa7b0b8,0xa7b0bc)
    if (hex(request_id)!=baseline['user3d_configuration_submission']['submission_id']
            or request_id!=0x2ae085a or callback!=((base+0xa7b1f8)|1)
            or hardware_base!=0xf4009000 or signal_id!=0x2ae085d
            or constant(0xa7b246,0xa7b24a)!=signal_id):
        raise ValueError('接收标识、回调或配置基址不符')
    if (constant(0xa7ade0,0xa7ade6)!=0x262cb50
            or constant(0xa7b3fc,0xa7b400)!=0x262ebbc
            or constant(0xa7b432,0xa7b436)!=0x262ebc8
            or baseline['user3d_configuration_submission']['initial_configuration_words_all_equal']!=1
            or baseline['user3d_configuration_submission']['descriptor_kind']!=2
            or baseline['user3d_configuration_submission']['descriptor_selected_configuration_offset']!=0x1c):
        raise ValueError('配置输入、临时区或命令输出绑定不符')
    targets=bounded_tbb_targets(cp[0x42d376:0x42d37c],0x42d376,len(cp))
    if targets!=(0x42d37c,0x42d388,0x42d394,0x42d3a0,0x42d3ac,0x42d3b8):
        raise ValueError('有界六项描述分发不符')
    if any(base+target not in index for target in targets):
        raise ValueError('描述分发落点不是核对的指令边界')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'matching-receiver-dispatch-and-config-command-construction',
        'receiver':{
            'submission_id':hex(request_id),'entry_file_offset':'0xa7ac22',
            'receive_api_file_offset':'0x45d3a8','receive_call_file_offset':'0xa7ac4a',
            'dispatch_call_file_offset':'0xa7ac7c','dispatch_file_offset':'0x42d33c',
            'release_api_file_offset':'0x45d300','loop_back_file_offset':'0xa7ac8c',
            'queue_lookup_file_offset':'0xae399a','lookup_id_low16':request_id&0xffff,
            'message_header_bytes':0x18,
            'dispatch_kind_targets':[hex(target) for target in targets],
            'selected_kind':2,'selected_handler_file_offset':'0xa7adbe',
            'scope':'同一 ID 的静态收发与队列头关系；不证明系统启动注册、运行投递或顺序'},
        'configuration_consumer':{
            'logical_context_descriptor_offset':8,'callback_descriptor_offset':0xc,
            'six_word_configuration_descriptor_offset':0x1c,
            'packing_file_offset':'0xa7b3f4','write_descriptor_count':3,
            'write_descriptor_stride':0x8c,'words_per_write':1,
            'register_value_sources':[
                {'register_offset':0x400,'value_u32':'c0'},
                {'register_offset':0x410,'value_u32':'c5 | (c4 << 1), truncated to u32'},
                {'register_offset':0x414,'value_u32':'c1 | (c2 << 8) | (c3 << 16), truncated to u32'}],
            'source_field_masks_present_in_packing_block':False,
            'initial_six_ones_derived_values':[1,3,0x10101],
            'argument_0x1e_semantics_verified':False,
            'command_builder_file_offset':'0x42d3f4',
            'logical_context_base_resolver_file_offset':'0xa6fff8',
            'accepted_logical_contexts':[0,6],
            'register_base_formula':'0xf4009000 + (logical_context << 20)',
            'command_node_bytes':0x10,'target_address_store_file_offset':'0x42d432',
            'scope':'数值打包和命令目标构造；寄存器位的业务含义及实际执行未证'},
        'asynchronous_submission':{
            'entry_file_offset':'0xa7b062','controller_number':5,
            'controller_setup_api_file_offset':'0x4790bc',
            'completion_callback_file_offset':'0xa7b1f8',
            'controller_submit_api_file_offset':'0xaeefa4',
            'controller_submit_call_file_offset':'0xa7b12a',
            'completion_signal_id':hex(signal_id),
            'wait_api_file_offset':'0x45b09c','wait_argument':0x3e8,
            'scope':'控制提交、回调和信号等待代码；时间单位、实际完成及图像同步未证'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '同一 ID 与静态循环不证明线程已启动或描述已被真实接收',
            '仅选定种类 2，不把其他五种处理器或 shell 包装器混为该处理器',
            '配置参数 0x1e 的业务语义未证；所查种类 2 处理器取 +8/+c/+1c',
            '六字均为 1 是配置初值；打包为 1/3/0x10101 不等于照片 LUT 硬件使能',
            '七个逻辑配置基址与四个捕获传输通道之间的对应仍需证据',
            '队列、全局临时区、异步回调的完整并发/所有权和运行成功未证',
            '未连接格式 3/4 有效像素、MAIN 同一缓冲与色域/伽马'],
        'matching_receiver_and_dispatch_located':True,
        'six_word_configuration_packing_located':True,
        'configuration_command_construction_located':True,
        'asynchronous_submission_and_callback_located':True,
        'receiver_runtime_delivery_verified':False,'runtime_context_category_verified':False,
        'handle_bit31_semantics_verified':False,'register_bit_semantics_verified':False,
        'submission_hardware_consumption_verified':False,
        'transfer_and_lut_same_runtime_handle_verified':False,
        'capture_vfx_uses_user_lut_verified':False,'lut_output_to_main_input_connected':False,
        'candidate_pair_reaches_active_pixel_transfer_verified':False,
        'buffer_identity_and_lifetime_verified':False,'full_resolution_dimensions_verified':False,
        'color_format_enum_verified':False,'ap_to_cp_runtime_verified':False,
        'photo_pipeline_located':False,'camera_commands_sent':False,
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
