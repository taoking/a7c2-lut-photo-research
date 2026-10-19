"""Verify CP callback consumers and a separate MAIN JPEG encoding segment.

This is static evidence only: no camera commands, firmware execution or patch.
Different task queues do not establish ordering or shared image buffers.
"""
import argparse
import json
from pathlib import Path

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_refresh import potential_thumb_path, trace as trace_refresh
from research.trace_lut_snapshot import movw_movt_value


def direct_member_pointer(function_word, adjustment_word, image_base, image_size):
    """Decode the observed ARM direct Thumb member-pointer dispatch form.

    The adjustment's low bit marks virtual dispatch, not the function's Thumb
    bit. Only direct pointers are resolved; no vtable or runtime address guessed.
    The result is a relative target and signed byte adjustment, not a call.
    """
    if any(type(value) is not int or not 0 <= value < 2**32
           for value in (function_word,adjustment_word,image_base)):
        raise ValueError('成员指针和基址需要 uint32 整数')
    if (type(image_size) is not int or image_size <= 0 or image_base % 2
            or image_base+image_size > 2**32):
        raise ValueError('无效程序映射范围')
    if adjustment_word & 1:
        raise ValueError('虚成员指针需要运行时虚表，不能推导直接目标')
    if not function_word & 1:
        raise ValueError('本模型只接受直接 Thumb 入口')
    offset=(function_word & ~1)-image_base
    if not 0 <= offset <= image_size-2:
        raise ValueError('成员指针目标不在程序内')
    signed=adjustment_word if adjustment_word < 2**31 else adjustment_word-2**32
    return {'target_file_offset':offset, 'this_adjustment_bytes':signed >> 1}


def trace(cp_path):
    cp=read_original(cp_path,'cp')
    base=boot_base(cp)
    # Retain the prior round's copy, descriptor creation and readiness checks.
    baseline=trace_refresh(cp_path)
    ranges=[(0xa26fee,0xa27066), (0x644a62,0x644a7a),
            (0x408020,0x408098), (0x768878,0x76887e),
            (0x3cef5a,0x3cf08c), (0x3cf046,0x3cf08c),
            (0x3bee7a,0x3bef8e), (0xa20c16,0xa20c5c),
            (0xa214e2,0xa2153a), (0x3b74c0,0x3b755a),
            (0xa234ac,0xa234b2), (0xa234c2,0xa234e8),
            (0x3d40b4,0x3d4360),
            (0x384f9e,0x384fce), (0x385822,0x385852),
            (0x385b52,0x385b9a), (0x385278,0x385446),
            (0x376e48,0x376ede), (0x42673c,0x4267dc)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    require_instructions(index,{
        0xa27002:('movs','r4, #0'),
        0xa27016:('str','r0, [r2, #0x14]'), 0xa27018:('movs','r0, #0x3c'),
        0xa2701a:('str','r0, [r2, #0x18]'),
        0xa27026:('strd','r0, r4, [r2]'),
        0xa2702a:('strd','r1, r4, [r2, #8]'), 0xa2702e:('str','r2, [r2, #0x10]'),
        0xa27056:('movs','r3, #0x45'), 0xa27058:('str','r3, [r2, #0x18]'),
        0xa2705c:('strd','r0, r4, [r2]'),
        0xa27060:('strd','r1, r4, [r2, #8]'), 0xa27064:('str','r2, [r2, #0x10]'),
        0x644a62:('ldrd','r1, r2, [r0, #8]'),
        0x644a66:('ldr','r0, [r0, #0x10]'),
        0x644a68:('add.w','r0, r0, r2, asr #1'),
        0x644a6c:('tst.w','r2, #1'), 0x644a78:('bx','r1'),
        0x40802e:('mov','r4, r0'), 0x408040:('add','r5, sp, #4'),
        0x408046:('ldr','r0, [r4, #0x18]'), 0x408048:('mov','r1, r5'),
        0x40804e:('blx',f'#{base+0x4e5998:#x}'),
        0x40807c:('ldrd','r3, r6, [sp, #4]'),
        0x408080:('ldrd','r1, r2, [sp, #0x18]'),
        0x408084:('add.w','r0, r5, r6, asr #1'),
        0x408088:('tst.w','r6, #1'),
        0x408094:('blx','r3'), 0x408096:('b',f'#{base+0x408046:#x}'),
        0x768878:('ldr','r2, [r0, #8]'), 0x76887a:('mov','r0, r1'),
        0x76887c:('bx','r2'),
        0x3cef5a:('mov.w','r8, #0'),
        0x3cefa2:('strd','r8, r8, [sp, #0x24]'),
        0x3cefb6:('strd','sl, r8, [sp, #0x18]'),
        0x3cf04e:('movs','r5, #0'),
        0x3cf068:('mov','r0, r4'),
        0x3cf06a:('bl',f'#{base+0x407f1c:#x}'),
        0x3cf072:('strd','r5, r5, [sp, #0x24]'),
        0x3cf076:('strd','sl, r5, [sp, #0x18]'),
        0x3cf082:('str','r0, [sp, #0x20]'),
        0x3cf086:('mov','r0, r4'),
        0x3cf088:('bl',f'#{base+0x407f1c:#x}'),
        0x3bee7e:('movs','r4, #0'), 0x3beec0:('movs','r3, #0'),
        0x3beed0:('mov','r2, fp'),
        0x3bef78:('strd','r4, r4, [sp, #0x84]'),
        0x3bef7c:('strd','r5, r4, [sp, #0x78]'),
        0x3bef84:('str','r0, [sp, #0x80]'),
        0xa21506:('add.w','r1, r0, #8'),
        0x3b7516:('ldr.w','r6, [sb]'), 0x3b751c:('add.w','r4, r6, #8'),
        0x3b7520:('ldrd','r3, r5, [r6, #8]'),
        0x3b7524:('ldrd','r1, r2, [r6, #0x1c]'),
        0x3b7528:('add.w','r0, r4, r5, asr #1'),
        0x3b752c:('tst.w','r5, #1'), 0x3b7538:('blx','r3'),
        0x3b7548:('ldr','r6, [r6]'), 0x3b754a:('cmp','r6, sb'),
        0x3b7556:('bl',f'#{base+0xa212fe:#x}'),
        0xa234ac:('ldr','r2, [r0, #8]'), 0xa234ae:('mov','r0, r1'),
        0xa234b0:('bx','r2'),
        0xa234d4:('bl',f'#{base+0x3e076c:#x}'),
        0x3d40d0:('adr','r0, #0x28c'),
        0x3d414e:('bl',f'#{base+0x3b74c0:#x}'),
        0x384fbc:('movs','r3, #1'), 0x384fb4:('adr','r2, #0xc4'),
        0x384fca:('bl',f'#{base+0x385278:#x}'),
        0x385840:('movs','r3, #2'), 0x385838:('adr','r2, #0xb0'),
        0x38584e:('bl',f'#{base+0x385278:#x}'),
        0x385b66:('adr','r0, #0x14c'), 0x385b68:('adr','r2, #0x138'),
        0x385b80:('bl',f'#{base+0x385278:#x}'),
        0x385442:('bl',f'#{base+0x376e48:#x}'),
        0x376e9a:('bl',f'#{base+0x42673c:#x}'),
        0x42674c:('adr','r1, #0x8c'),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    pre_object=constant(0xa26ff8,0xa2700a)
    co_object=constant(0xa2704a,0xa27050)
    task_entry=constant(0xa26ffe,0xa2700e)
    task_thunk=constant(0xa2701c,0xa27022)
    pre_thunk=constant(0x3cef96,0x3cefaa)
    co_entry=constant(0x3cf06e,0x3cf07e)
    vfx_thunk=constant(0x3bee86,0x3bee92)
    vfx_entry=constant(0x3bef6c,0x3bef80)
    producer_list=constant(0xa20c42,0xa20c48)
    consumer_list=constant(0x3b750e,0x3b7512)
    if (constant(0x3cef9e,0x3cefb2)!=pre_object
            or constant(0x3cf04a,0x3cf058)!=co_object):
        raise ValueError('提交对象与初始化的任务对象不一致')
    if (pre_object,co_object,task_entry,task_thunk,pre_thunk,co_entry,
            vfx_thunk,vfx_entry,producer_list,consumer_list) != (
            0x1a6a6c8,0x1a6a708,base+0x408020+1,base+0x644a62+1,
            base+0x768878+1,base+0x3d40b4+1,base+0xa234ac+1,
            base+0xa234c2+1,0x1a69b34,0x1a69b34):
        raise ValueError('任务对象、回调指针或链表根不符')
    # The known descriptor uses zero adjustment; preserve that evidence rather
    # than resolving a virtual member or inventing runtime node addresses.
    for register,a,b in [('r4',0x3bee7e,0x3bef8a),('r5',0x3bee92,0x3bef7c),
                         ('r2',0x3beed0,0x3bef8a),('r3',0x3beec0,0x3bef8a)]:
        if any(register in {i.reg_name(r) for r in i.regs_access()[1]}
               for i in blocks[6] if base+a < i.address < base+b):
            raise ValueError('描述符或参数寄存器被重新设置')
    for block,register,a,b in [(0,'r4',0xa27002,0xa27066),
                              (5,'r4',0x3cf058,0x3cf088),
                              (4,'r8',0x3cef5a,0x3cefc0),
                              (4,'sl',0x3cefaa,0x3cf088),
                              (5,'r5',0x3cf04e,0x3cf088)]:
        if any(register in {i.reg_name(r) for r in i.regs_access()[1]}
               for i in blocks[block] if base+a < i.address < base+b):
            raise ValueError('任务对象或零调整量被重新设置')
    path_specs=[(9,0x3b74c0,0x3b7538),(12,0x3d40b4,0x3d414e),
                (16,0x385278,0x385442),(17,0x376e48,0x376e9a)]
    paths=[]
    for block,a,b in path_specs:
        path=potential_thumb_path(blocks[block],base+a,base+b)
        if path is None:raise ValueError(f'缺少潜在路径 {a:#x} → {b:#x}')
        paths.append({'start_file_offset':hex(a),'target_file_offset':hex(b),
                      'potential_path_instructions':len(path)})
    labels={0x3d4360:b'VD_CO S', 0x38507c:b'Stage_EncodeJpeg_SCN',
            0x3858ec:b'Stage_EncodeJpeg_THM', 0x385ca4:b'Stage_MainEnc',
            0x385cb4:b'FW: [%d] %s: EncodeJpegBase MAIN', 0x4267dc:b'ddl_jpeg_encode'}
    for offset,label in labels.items():
        if cp[offset:offset+len(label)+1]!=label+b'\0':
            raise ValueError('回调或 JPEG 阶段标签不符')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'static-callback-consumers-and-separate-JPEG-MAIN-segment',
        'event_task':{'loop_file_offset':'0x408020','object_entry_thunk_file_offset':'0x644a62',
                      'configured_entry':direct_member_pointer(task_entry,0,base,len(cp)),
                      'receive_call_file_offset':'0x40804e','dispatch_call_file_offset':'0x408094',
                      'descriptor_bytes':28,'argument_offsets':[20,24],
                      'snapshot_task_object_link_va':hex(pre_object),'snapshot_queue_id':0x3c,
                      'snapshot_callback_file_offset':baseline['snapshot_refresh']['callback_entry_file_offset'],
                      'snapshot_callback_thunk':direct_member_pointer(pre_thunk,0,base,len(cp)),
                      'vfx_task_object_link_va':hex(co_object),'vfx_queue_id':0x45,
                      'vfx_callback_file_offset':'0x3d40b4','vfx_callback_log':'VD_CO S',
                      'ordering_between_queues_verified':False},
        'vfx_list':{'root_link_va':hex(consumer_list),'node_payload_offset':8,
                    'node_argument_offsets':[0x1c,0x20],
                    'consumer_file_offset':'0x3b74c0','indirect_call_file_offset':'0x3b7538',
                    'thunk':direct_member_pointer(vfx_thunk,0,base,len(cp)),
                    'thunk_target_field_offset':8,
                    'callback':direct_member_pointer(vfx_entry,0,base,len(cp)),
                    'argument_source':'submission r2 = fp (object), r3 = 0',
                    'lut_dispatcher_file_offset':'0x3e076c'},
        'jpeg_segment':{'labels':['SCN','THM','MAIN'],
                        'common_prepare_file_offset':'0x385278',
                        'caller_file_offsets':['0x384fca','0x38584e','0x385b80'],
                        'wrapper_file_offset':'0x376e48','wrapper_call_file_offset':'0x385442',
                        'encode_api_file_offset':'0x42673c','encode_call_file_offset':'0x376e9a',
                        'lut_output_to_main_input_connected':False,
                        'full_resolution_dimensions_verified':False},
        'potential_paths':paths,
        'baseline_snapshot_copy_bytes':baseline['snapshot_refresh']['copy_bytes'],
        'findings':['回调描述符的消费者、直接成员指针包装和 LUT 入口已静态连接',
                    'VD_Pre 与 VD_CO 使用不同任务对象/队列，不能按提交位置证明完成顺序',
                    'SCN/THM/MAIN 共用编码准备函数，再经包装函数调用 JPEG API'],
        'limitations':['潜在路径不求解条件，按 ABI 及调用可返回解释；无运行频率或时序证明',
                       '接收 API 的错误处理、队列可靠性和任务启动过程未完整分析',
                       '未把 LUT/VFX 输出地址与 MAIN JPEG 输入的地址、尺寸、格式对应',
                       '输入色域/伽马、写入侧同步和 LUT 缓冲释放仍未确认'],
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'ap_to_cp_runtime_verified':False,'photo_pipeline_located':False,
        'camera_commands_sent':False,
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
