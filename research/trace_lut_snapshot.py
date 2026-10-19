"""Verify static LUT snapshot copies and a separate front-end VEF request path.

Only reads the pinned CP image. Never executes camera code or emits a payload.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_dispatch import copied_fields
from research.trace_lut_handoff import read_original, require_instructions


def movw_movt_value(instructions, first, last):
    """Resolve a Thumb MOVW/MOVT pair with conservative intervening checks."""
    from capstone.arm import ARM_OP_REG, ARM_OP_IMM, ARM_CC_AL, ARM_CC_INVALID
    by_address = {i.address: i for i in instructions}
    if first >= last or first not in by_address or last not in by_address:
        raise ValueError('MOVW/MOVT 地址缺失或顺序错误')
    low, high = by_address[first], by_address[last]
    cursor = first
    for ins in sorted((i for i in by_address.values() if first <= i.address <= last),
                      key=lambda i:i.address):
        if ins.address != cursor:
            raise ValueError('MOVW/MOVT 区间不连续，不能排除未知写入')
        cursor += ins.size
    for ins, mnemonic in ((low, 'movw'), (high, 'movt')):
        if (ins.mnemonic != mnemonic or len(ins.operands) != 2
                or ins.operands[0].type != ARM_OP_REG or ins.operands[1].type != ARM_OP_IMM
                or ins.cc not in (ARM_CC_AL, ARM_CC_INVALID)
                or not 0 <= ins.operands[1].imm <= 0xffff):
            raise ValueError('需要无条件 MOVW/MOVT 立即数对')
    register = low.operands[0].reg
    if register != high.operands[0].reg:
        raise ValueError('MOVW/MOVT 目标寄存器不同')
    for ins in instructions:
        if first < ins.address < last:
            writes = set(ins.regs_access()[1])
            if (register in writes or ins.cc not in (ARM_CC_AL, ARM_CC_INVALID)
                    or ins.mnemonic.startswith(('b', 'cb', 'it'))
                    or any(ins.reg_name(r) == 'pc' for r in writes)):
                raise ValueError('MOVW/MOVT 之间有覆盖或控制流，不能推导常量')
    return (high.operands[1].imm << 16) | low.operands[1].imm


def snapshot_field_path():
    fields = [('table_address',0x68,8), ('register_address',0x70,8),
              ('table_bytes',0x78,4), ('register_bytes',0x7c,4),
              ('update_counter',0xc0,4)]
    initial = copied_fields(0,0,0xd64,0,fields)
    consumer = copied_fields(0x68,0x13d0,0x60,0x13b8,fields)
    return [{'field': a['field'], 'bytes': a['bytes'],
             'internal_offset': a['source_offset'], 'snapshot_offset': a['object_offset'],
             'object_offset': b['object_offset'], 'vfx_input_offset': b['consumer_offset']}
            for a, b in zip(initial, consumer)]


def trace(cp_path):
    cp = read_original(cp_path, 'cp')
    base = boot_base(cp)
    ranges = [(0x24bd48,0x24bd9e), (0x24c16c,0x24c1b8),
              (0x7d2d4a,0x7d2d54), (0xa26140,0xa268e0),
              (0xa268e0,0xa26966), (0xa26bce,0xa26c50),
              (0xa24406,0xa245b6), (0x3e076c,0x3e0970),
              (0xadd14,0xaddec), (0xaddfe,0xade4c), (0xadf98,0xae05a),
              (0x5f2eb8,0x5f2ec6), (0x5f2d94,0x5f2dd6), (0x5f303c,0x5f31de),
              (0x5edd84,0x5edde6), (0x5edde6,0x5ede5a)]
    functions = [decode_thumb(cp, a, b, base) for a, b in ranges]
    index = {i.address: i for block in functions for i in block}
    require_instructions(index, {
        0x24bd7a: ('bl', f'#{base+0x408728:#x}'),
        0x24c178: ('mov', 'r0, r4'), 0x24c184: ('movw', 'r0, #0xd68'),
        0x24c18c: ('str', 'r0, [r5]'), 0x24c1a8: ('movw', 'r2, #0xa720'),
        0x24c1b0: ('movt', 'r2, #0x165'), 0x24c1b4: ('bl', f'#{base+0xae138e:#x}'),
        0xa26150: ('bl', f'#{base+0x7d2d4a:#x}'), 0xa26158: ('mov', 'r1, r0'),
        0xa2615a: ('movw', 'r2, #0xd64'), 0xa26162: ('mov', 'r0, r4'),
        0xa26164: ('blx', f'#{base+0x51660c:#x}'),
        0xa26664: ('mov', 'r0, r4'), 0xa26666: ('mov', 'r1, r8'),
        0xa26668: ('bl', f'#{base+0xa268e0:#x}'),
        0xa268e4: ('mov', 'r4, r1'), 0xa268e6: ('mov', 'r5, r0'),
        0xa268e8: ('bl', f'#{base+0xa26bce:#x}'), 0xa26bd2: ('str', 'r0, [r1]'),
        0xa244b6: ('ldr.w', 'r1, [sl]'), 0xa244ba: ('movw', 'r0, #0x13d0'),
        0xa244be: ('movs', 'r2, #0x60'), 0xa244c2: ('adds', 'r1, #0x68'),
        0xa244c4: ('blx', f'#{base+0x51660c:#x}'),
        0x3e0812: ('bl', f'#{base+0x446398:#x}'),
        0xadd7a: ('movw', 'r0, #0x2002'), 0xadd82: ('movt', 'r0, #0x11'),
        0xadd86: ('str', 'r0, [sp, #0x98]'),
        0xadd90: ('ldr.w', 'r3, [r5, #0x624]'), 0xadd94: ('cmp', 'r3, #3'),
        0xadd96: ('beq', f'#{base+0xaddfe:#x}'),
        0xade06: ('ldrd', 'r1, r2, [r1]'), 0xade0a: ('ldr.w', 'r3, [r5, #0x634]'),
        0xade0e: ('adds', 'r4, r3, r1'), 0xade10: ('adc', 'r6, r2, #0'),
        0xade18: ('ldr.w', 'r3, [r5, #0x638]'), 0xade1c: ('str', 'r3, [sp, #0xa4]'),
        0xade1e: ('ldr.w', 'r0, [r5, #0x63c]'),
        0xade22: ('adds.w', 'sb, r0, r1'), 0xade26: ('adc', 'sl, r2, #0'),
        0xade2e: ('ldr.w', 'fp, [r5, #0x640]'), 0xade32: ('str.w', 'fp, [sp, #0xb4]'),
        0xadf9c: ('movs', 'r5, #0x48'), 0xadfac: ('movt', 'r5, #0x905a'),
        0xadff0: ('add', 'r1, sp, #0x98'),
        0xadff4: ('movs', 'r2, #0x28'), 0xadff6: ('bl', f'#{base+0x5a63f8:#x}'),
        0x5f2eb8: ('movw', 'r0, #0x2002'), 0x5f2ebe: ('movs', 'r0, #0x11'),
        0x5f2dba: ('ldr', 'r3, [r0, #0x14]'), 0x5f2dca: ('bx', 'r3'),
        0x5f30e8: ('cmp', 'r2, #3'), 0x5f30ea: ('bne', f'#{base+0x5f318a:#x}'),
        0x5f30fa: ('ldrd', 'ip, r2, [r6, #4]'), 0x5f3102: ('ldrd', 'r5, r0, [r6, #0x14]'),
        0x5f3114: ('bl', f'#{base+0x5edde6:#x}'),
        0x5f31a2: ('bl', f'#{base+0x5edd84:#x}'),
        0x5eddc0: ('bl', f'#{base+0x44615c:#x}'),
        0x5ede36: ('bl', f'#{base+0x446398:#x}'),
    }, base)
    insns = list(index.values())
    data_id = movw_movt_value(insns,base+0x24bd5a,base+0x24bd6e)
    exported_id = movw_movt_value(insns,base+0x24c170,base+0x24c174)
    source = movw_movt_value(insns,base+0x7d2d4a,base+0x7d2d4e)
    destination = movw_movt_value(insns,base+0xa26154,base+0xa2615e)
    context = movw_movt_value(insns,base+0xa26656,base+0xa2665e)
    if (data_id, exported_id, source, destination, context) != (
            0x30160,0x30160,0x165a720,0x172fe50,0x173efe8):
        raise ValueError('状态标识或快照地址常量不符')
    # r4 holds the snapshot root across the constructor up to context binding.
    # Calls are interpreted under the ABI's callee-saved r4 rule; this is not an
    # interprocedural memory/lifetime proof.
    for ins in functions[3]:
        if base+0xa26164 < ins.address < base+0xa26668:
            if any(ins.reg_name(r)=='r4' for r in ins.regs_access()[1]):
                raise ValueError('快照构造到绑定之间重新设置了 r4')
    vtable = struct.unpack_from('<6I', cp, 0xc3c9e4)
    if vtable[2:] != (base+0x5f2d94+1,base+0x5f2eb8+1,
                      base+0x5f2ec6+1,base+0x5f303c+1):
        raise ValueError('VEF SetLookName 虚表方法不符')
    typeinfo = struct.unpack_from('<I',cp,0xc3c9e0)[0]-base
    name = struct.unpack_from('<I',cp,typeinfo+4)[0]-base
    expected = b'N3VEF21VefPathCmdSetLookNameE\0'
    if cp[name:name+len(expected)] != expected:
        raise ValueError('VEF 请求类 RTTI 名称不符')
    return {
        'model': 'ILCE-7CM2', 'firmware': '2.01', 'cp_sha256': TARGETS['cp'],
        'evidence_level': 'static-snapshot-source-and-separate-VEF-consumer-segments',
        'internal_snapshot': {'source_link_va':hex(source), 'root_link_va':hex(destination),
                              'context_link_va':hex(context), 'constructor_file_offset':'0xa26140',
                              'initial_copy_bytes':0xd64, 'export_block_bytes':0xd68,
                              'data_registry_id':hex(data_id),
                              'context_binding_file_offset':'0xa26668',
                              'root_pointer_store_file_offset':'0xa26bd2',
                              'field_path':snapshot_field_path()},
        'front_request': {'builder_file_offset':'0xadd14', 'header_u16':[0x2002,0x11],
                          'request_bytes':0x28, 'queue_id':'0x905a0048',
                          'type3_table_offset_field':0x634, 'type3_table_length_field':0x638,
                          'type3_register_offset_field':0x63c, 'type3_register_length_field':0x640,
                          'address_calculation':'64-bit mapped base + 32-bit byte offset, with carry'},
        'matching_receiver': {'class':'VEF::VefPathCmdSetLookName',
                              'vtable_file_offset':'0xc3c9e4', 'header_method_file_offset':'0x5f2eb8',
                              'action_file_offset':'0x5f303c', 'type3_call_file_offset':'0x5f3114',
                              'user3d_wrapper_file_offset':'0x5edd84',
                              'artgen_wrapper_file_offset':'0x5edde6',
                              'common_user3d_api_file_offset':'0x44615c',
                              'common_artgen_api_file_offset':'0x446398'},
        'findings':['内部 LUT 状态到参数根的初始复制、上下文绑定及后续 VFX 字段布局已静态连接',
                    '前端请求构造与匹配的 VEF 接收类也能抵达 User3D/User3DArtGen',
                    '未发现必须把前端 0x0166 直接换算为内部 0x4155 的证据，应分别追踪两条控制路径'],
        'limitations':['前端发送队列到接收对象的全部注册/调度和虚方法 payload 来源未完整追踪',
                       '快照复制与绑定是静态参数流证据，未证明并发同步、缓冲有效期或运行模式',
                       '0xd64 字节复制小于 0xd68 导出块，未推断剩余 4 字节用途',
                       '机内完整分辨率 JPEG、输入色域和伽马仍未确认；没有执行固件'],
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'ap_to_cp_runtime_verified':False, 'photo_pipeline_located':False,
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
