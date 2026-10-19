"""Pinned-original User3D route-to-channel control bit and RAM mirror evidence.

Read-only bounded observations. A cached control-bit write is not proof of
hardware enable, active pixel transfer, runtime handle identity or photo output.
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
from research.trace_lut_receiver import trace as trace_receiver
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp')
    base=boot_base(cp)
    baseline=trace_receiver(cp_path)
    # Inline TBB bytes and its odd-length padding are not instructions.
    ranges=[(0x44615c,0x446380),(0x446914,0x44692a),(0x446932,0x446950),
            (0xaaafac,0xaaaff0),(0xaac326,0xaac36a),(0xaaa0d2,0xaaa130),
            (0xaaad56,0xaaad74),(0xa734d6,0xa73500),
            (0xa73c4a,0xa73d6a)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(target):return ('bl',f'#{base+target:#x}')
    require_instructions(index,{
        0x4461e0:('ldr.w','sl, [sp, #0x38]'),
        0x44621e:('pop.w','{r8, sb, sl, fp}'),
        0x446222:('pop','{r4, r5, r6, r7, pc}'),
        0x446234:('add','r1, sp, #0x34'),0x446236:('mov','r0, sl'),
        0x446238:call(0xaac2da),
        0x44632c:('ldr','r0, [sp, #0x34]'),
        0x446342:('add','r1, sp, #0x10'),0x446344:('mov','r2, sb'),
        0x446346:call(0xa71576),
        0x44634a:('cbz',f'r0, #{base+0x446360:#x}'),
        0x446360:('mov','r0, sl'),0x446362:call(0xaaafac),
        0x446918:('mov','lr, r0'),0x44691a:('movs','r0, #1'),
        0x44691c:('cmp.w','lr, #6'),
        0x446920:('bhi',f'#{base+0x44694e:#x}'),
        0x446922:('mov.w','ip, #0'),0x446926:('tbb','[pc, lr]'),
        0x446932:('mov','ip, lr'),0x446934:('mov','r0, lr'),
        0x446936:('b',f'#{base+0x446946:#x}'),
        0x446938:('movs','r0, #3'),0x44693a:('mov.w','ip, #0'),
        0x44693e:('b',f'#{base+0x446946:#x}'),
        0x446940:('movs','r0, #3'),0x446942:('mov.w','ip, #2'),
        0x446946:('strb.w','ip, [r1]'),0x44694a:('strb','r0, [r2]'),
        0xaaafb4:('sub.w','r2, r7, #0xa'),
        0xaaafc0:('sub.w','r1, r7, #9'),0xaaafc4:call(0x446914),
        0xaaafc8:('cmp','r0, #0'),
        0xaaafca:('bne',f'#{base+0xaaafec:#x}'),
        0xaaafcc:('ldrb','r4, [r7, #-0x9]'),
        0xaaafd0:('ldrb','r0, [r7, #-0xa]'),0xaaafd4:('cmp','r4, r0'),
        0xaaafd6:('bhi',f'#{base+0xaaafea:#x}'),
        0xaaafd8:('uxtb','r0, r4'),0xaaafda:call(0xaac326),
        0xaaafde:('ldrb','r1, [r7, #-0xa]'),0xaaafe2:('adds','r4, #1'),
        0xaaafe4:('uxtb','r0, r4'),0xaaafe6:('cmp','r0, r1'),
        0xaaafe8:('bls',f'#{base+0xaaafd8:#x}'),
        0xaac32c:('mov','r5, sp'),0xaac32e:('mov','r4, r0'),
        0xaac330:('movs','r1, #0x68'),0xaac332:('mov','r0, r5'),
        0xaac334:('blx',f'#{base+0x516d00:#x}'),
        0xaac338:('movs','r0, #1'),0xaac33a:('mov','r1, r4'),
        0xaac33c:('str','r0, [sp, #0x68]'),0xaac33e:('mov','r0, r5'),
        0xaac340:call(0xaaa0d2),
        0xaac350:('mov','r5, sp'),0xaac352:('mov','r4, r0'),
        0xaac354:('movs','r1, #0x6c'),0xaac356:('mov','r0, r5'),
        0xaac358:('blx',f'#{base+0x516d00:#x}'),
        0xaac35c:('mov','r0, r5'),0xaac35e:('mov','r1, r4'),
        0xaac360:call(0xaaa0d2),
        0xaaad62:('uxtb','r0, r4'),0xaaad64:call(0xaac34a),
        0xaaa0e0:('mov.w','r2, #0x1100'),
        0xaaa0e4:('ldr.w','r3, [ip, r1, lsl #2]'),
        0xaaa0ea:('ldr','r0, [r0, #0x68]'),
        0xaaa0ee:('bfi','r3, r0, #0x1c, #1'),
        0xaaa0fc:('ldr.w','r0, [r0, r1, lsl #2]'),
        0xaaa100:('ldr','r3, [sp]'),0xaaa102:('str','r3, [r0, r2]'),
        0xaaa106:('str.w','r3, [ip, r1, lsl #2]'),
        0xaaa10e:('ldr','r0, [r0, r2]'),0xaaa114:('str','r0, [r1]'),
        0xaaa116:('dsb','sy'),
        0xaaa126:('ldr.w','r0, [r1, r0, lsl #2]'),
        0xaaa12a:('ubfx','r0, r0, #0x1c, #1'),
        0xa734d6:('ldr','r0, [sp]'),0xa734e0:('str.w','r0, [r1, #0x400]'),
        0xa734e4:('ldrd','r0, r2, [sp, #0x10]'),
        0xa734e8:('orr.w','r0, r2, r0, lsl #1'),
        0xa734ec:('str.w','r0, [r1, #0x410]'),
        0xa734f0:('add','r3, sp, #4'),0xa734f2:('ldm','r3, {r0, r2, r3}'),
        0xa734f4:('orr.w','r0, r0, r2, lsl #8'),
        0xa734f8:('orr.w','r0, r0, r3, lsl #16'),
        0xa734fc:('str.w','r0, [r1, #0x414]'),
        0xa73c4e:call(0xa6fff8),0xa73c56:('mov','r4, r0'),
        0xa73d52:('add.w','r0, r4, #0x400'),0xa73d56:('movs','r1, #0'),
        0xa73d58:('ldr.w','r2, [r0, r1, lsl #2]'),
        0xa73d5c:('add.w','r3, r5, r1, lsl #2'),
        0xa73d60:('adds','r1, #1'),0xa73d62:('cmp','r1, #0x20'),
        0xa73d64:('str.w','r2, [r3, #0x400]'),
        0xa73d68:('bne',f'#{base+0xa73d58:#x}'),
    },base)
    # ARM interworking entry establishes the zero-fill argument convention.
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
    clear=list(Cs(CS_ARCH_ARM,CS_MODE_ARM).disasm(cp[0x516d00:0x516e38],base+0x516d00))
    if sum(i.size for i in clear)!=0x138:
        raise ValueError('ARM 清零入口不能完整解码')
    require_instructions({i.address:i for i in clear},{
        0x516d00:('mov','r2, r1'),0x516d04:('mov','r1, #0'),
        0x516d08:('b',f'#{base+0x516d0c:#x}'),
        0x516d0c:('and','r3, r1, #0xff'),0x516d10:('mov','r1, r2'),
        0x516d28:('orr','r3, r3, r3, lsl #8'),
        0x516d30:('orr','r3, r3, r3, lsl #16'),
        0x516d44:('mov','r2, r3'),
        0x516da0:('subs','r1, r1, #0x20'),
        0x516da4:('strdge','r2, r3, [ip], #8'),
        0x516da8:('strdge','r2, r3, [ip], #8'),
        0x516dac:('strdge','r2, r3, [ip], #8'),
        0x516db0:('strdge','r2, r3, [ip], #8'),
        0x516db4:('bgt',f'#{base+0x516da0:#x}'),
        0x516dd0:('subs','r1, r1, #4'),
        0x516dd4:('strge','r3, [ip], #4'),
        0x516dd8:('bgt',f'#{base+0x516dd0:#x}'),
    },base)
    insns=list(index.values())
    for ins in insns:
        protected=(('sl',) if base+0x4461e4 <= ins.address < base+0x446360 else
                   ('r4','r5') if base+0xa73c66 <= ins.address < base+0xa73d52 else ())
        # This checked epilogue restores SL and immediately returns via POP PC.
        if ins.address==base+0x44621e:
            continue
        if protected and any(ins.reg_name(reg) in protected for reg in ins.regs_access()[1]):
            raise ValueError('路由或快照复制指针在所查使用前被重设')
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    cache=constant(0xaaa0d4,0xaaa0dc)
    channel_table=constant(0xaaa0f2,0xaaa0f8)
    mirror=constant(0xa734d8,0xa734dc)
    snapshot=constant(0xa73c52,0xa73c5c)
    if (cache,channel_table,mirror,snapshot)!=(0x1a7e538,0xe9d550,0x25f7078,0x25f75f8):
        raise ValueError('通道控制缓存、基址表或 RAM 镜像不符')
    if constant(0xaaa11e,0xaaa122)!=cache:
        raise ValueError('位读取入口不是同一软件缓存')
    targets=bounded_tbb_targets(cp[0x44692a:0x446931],0x44692a,len(cp))
    if targets!=(0x446932,)*4+(0x446938,0x446946,0x446940):
        raise ValueError('七路控制范围表不符')
    if any(base+t not in index for t in targets):
        raise ValueError('控制范围表落点不是核对的指令边界')
    channel_ranges=[(i,i) if t==0x446932 else
                    {0x446938:(0,3),0x446946:(0,1),0x446940:(2,3)}[t]
                    for i,t in enumerate(targets)]
    channel_bases=list(struct.unpack_from('<4I',cp,channel_table-base))
    ports=[0x5a,0x6e,0x82,0x96]
    transfer_bases=[struct.unpack_from('<I',cp,0x1113fb8-base+12*port+4)[0] for port in ports]
    if (channel_bases!=[0xf4000000+i*0x100000 for i in range(4)]
            or transfer_bases!=[v+0x380 for v in channel_bases]):
        raise ValueError('四通道与此前捕获端口的静态基址关系不符')
    if (baseline['configuration_consumer']['accepted_logical_contexts']!=[0,6]
            or baseline['capture_vfx_uses_user_lut_verified'] is not False):
        raise ValueError('不能继承未经证明的运行照片使能')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'user3d-route-channel-bit28-and-ram-mirror',
        'post_submission_control':{
            'user3d_entry_file_offset':'0x44615c','submission_call_file_offset':'0x446346',
            'zero_return_branch_file_offset':'0x44634a',
            'control_call_file_offset':'0x446362','control_entry_file_offset':'0xaaafac',
            'range_resolver_file_offset':'0x446914',
            'route_to_inclusive_channel_ranges':[list(row) for row in channel_ranges],
            'per_channel_constructor_file_offset':'0xaac326',
            'constructor_source_word_offset':0x68,'constructor_source_value':1,
            'writer_file_offset':'0xaaa0d2','register_offset_in_channel_block':0x1100,
            'control_bit':28,'prior_value_source':'software cache indexed by channel',
            'software_cache_link_va':hex(cache),
            'write_expression':'(cached_word & ~(1 << 28)) | ((source_word & 1) << 28)',
            'readback_comparison_present_in_writer':False,
            'cached_bit_reader_file_offset':'0xaaa11e',
            'scope':'提交返回 0 后按路由构造置位调用；位含义、实际写入成功与配置先完成均未证'},
        'channel_block_relation':{
            'control_base_table_link_va':hex(channel_table),
            'physical_channel_count':4,'control_base_formula':'0xf4000000 + (channel << 20)',
            'prior_capture_ports':ports,'capture_port_base_delta_in_same_block':0x380,
            'logical_config_base_formula':baseline['configuration_consumer']['register_base_formula'],
            'logical_route_to_config_context':'identity 0..6 from previously checked table',
            'scope':'同一路由分别选择配置上下文和通道范围；仅静态 MMIO 块关系，非同一运行像素证明'},
        'opposite_value_path':{
            'constructor_file_offset':'0xaac34a','zeroed_source_bytes':0x6c,
            'source_word_offset':0x68,'derived_source_value':0,
            'same_writer_file_offset':'0xaaa0d2','caller_file_offset':'0xaaad64',
            'scope':'定位清零构造器及一处调用，未确认完整模式/拍摄生命周期'},
        'ram_mirrors':{
            'packing_block_file_offset':'0xa734d6','mirror_link_va':hex(mirror),
            'selected_mirror_offsets':[0x400,0x410,0x414],
            'packing_matches_prior_three_write_descriptors':True,
            'snapshot_entry_file_offset':'0xa73c4a','snapshot_link_va':hex(snapshot),
            'register_copy_file_offset':'0xa73d52',
            'register_copy_start':0x400,'register_copy_word_count':0x20,
            'scope':'RAM 打包镜像和另一读取快照；不等于直接硬件写入或已核对配置位含义'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'checked_arm_window':['0x516d00','0x516e38'],
        'excluded_tbb_data_and_padding':['0x44692a','0x446932'],
        'limitations':[
            '第 28 位的功能名/极性未证，不能直接命名照片 LUT 使能',
            '写入以软件缓存为旧值，未证明缓存与当前硬件控制字相同',
            '写后读回和 DSB 没有比较；返回 0 不是硬件成功验证',
            '提交返回后调用置位不证明接收线程已处理或控制器已完成，也不证明反向时序',
            '七配置块到四通道范围是同一路由的两种静态映射，没有一一硬件身份结论',
            '所查同偏移写入为 RAM 镜像，三个配置寄存器的位语义仍未知',
            '未验证源内存所有别名/并发、完整反向生命周期、运行句柄和实际模式',
            '格式 3/4 有效像素、MAIN 同一缓冲与色彩条件仍未连接'],
        'user3d_post_submit_channel_control_located':True,
        'route_to_control_channel_ranges_located':True,
        'cached_bit28_set_and_clear_constructors_located':True,
        'configuration_ram_mirror_distinguished':True,
        'register_bit_semantics_verified':False,'hardware_control_cache_coherence_verified':False,
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
