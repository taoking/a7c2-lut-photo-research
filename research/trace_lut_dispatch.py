"""Trace bounded LUT dispatch tables and snapshot fields without camera I/O."""
import argparse
import io
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions


def dispatch_entry(raw, base, start, count, stride, command, handler_offset=4):
    """Resolve one u16 key/u32 Thumb pointer in a bounded table.

    A pointer in the image is not proof of executable code; callers must decode
    the resolved function separately. No guessed table boundary is accepted.
    """
    values = (base, start, count, stride, command, handler_offset)
    if any(type(v) is not int for v in values):
        raise ValueError('分发表参数必须是整数')
    if not (0 <= base < 2**32 and base+len(raw) <= 2**32
            and start >= 0 and 1 <= count <= 4096 and stride >= 8
            and 2 <= handler_offset <= stride-4 and 0 <= command <= 0xffff
            and start+count*stride <= len(raw)):
        raise ValueError('分发表区间或字段越界')
    hits = [start+n*stride for n in range(count)
            if struct.unpack_from('<H', raw, start+n*stride)[0] == command]
    if len(hits) != 1:
        raise ValueError('命令在指定分发表中没有唯一匹配')
    entry = hits[0]
    pointer = struct.unpack_from('<I', raw, entry+handler_offset)[0]
    target = (pointer & ~1)-base
    if not pointer & 1 or not 0 <= target < len(raw):
        raise ValueError('处理函数不是映像内有效 Thumb 指针')
    return {'command': command, 'entry_file_offset': entry,
            'handler_link_va': pointer, 'handler_file_offset': target}


def copied_fields(source_start, destination_start, size, consumer_start, fields):
    """Map complete fields through an observed fixed-size copy; no bytes copied."""
    bounds = (source_start, destination_start, size, consumer_start)
    if (any(type(v) is not int or not 0 <= v <= 0xffffffff for v in bounds)
            or size == 0 or max(source_start+size, destination_start+size) > 2**32):
        raise ValueError('复制区间无效或回绕')
    result = []
    for name, source, width in fields:
        if (type(source) is not int or type(width) is not int or width <= 0
                or source < source_start or source+width > source_start+size):
            raise ValueError('字段没有完整包含于复制区间')
        destination = destination_start + source-source_start
        if destination < consumer_start:
            raise ValueError('字段位于消费者结构之前')
        result.append({'field': name, 'bytes': width, 'source_offset': source,
                       'object_offset': destination,
                       'consumer_offset': destination-consumer_start})
    return result


def trace(ap_path, cp_path):
    ap, cp = read_original(ap_path, 'ap'), read_original(cp_path, 'cp')
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
    from elftools.elf.elffile import ELFFile
    with io.BytesIO(ap) as stream:
        elf = ELFFile(stream)
        text, symbols = elf.get_section_by_name('.text'), elf.get_section_by_name('.dynsym')
        if elf['e_machine'] != 'EM_AARCH64' or not elf.little_endian or text['sh_addr'] != text['sh_offset']:
            raise ValueError('AP ELF 代码映射不符')
        plt = elf.get_section_by_name('.plt')
        names = {plt['sh_addr']+32+n*16: symbols.get_symbol(r['r_info_sym']).name
                 for n, r in enumerate(elf.get_section_by_name('.rela.plt').iter_relocations())}
    expected_names = {0x1660060: 'osal_valloc_msg_wait', 0x165d600: 'osal_set_msg_src',
                      0x165ead0: 'osal_snd_msg', 0x165e940: 'osal_rcv_msg_tmo',
                      0x1660350: 'osal_free_msg'}
    if any(names.get(va) != name for va, name in expected_names.items()):
        raise ValueError('AP OSAL 消息导入符号不符')
    cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    ap_ranges = [(0x34ebb84, 0x34ebc5c), (0x34e552c, 0x34e57cc)]
    ai = {}
    for start, end in ap_ranges:
        insns = list(cs.disasm(ap[start:end], start))
        if sum(i.size for i in insns) != end-start:
            raise ValueError('AP 消息函数区间不能完整解码')
        ai.update((i.address, i) for i in insns)
    require_instructions(ai, {
        0x34ebba4: ('mov', 'w1, #0x200d'), 0x34ebbac: ('mov', 'w1, #0x166'),
        0x34ebc04: ('ldr', 'w1, [x0, #0xc]'),
        0x34ebc08: ('stp', 'w4, w3, [x29, #0x44]'),
        0x34ebc10: ('stp', 'w1, w2, [x29, #0x4c]'),
        0x34ebc20: ('stp', 'w1, w0, [x29, #0x54]'),
        0x34ebc38: ('bl', '#0x34e552c'), 0x34e5584: ('bl', '#0x1660060'),
        0x34e56cc: ('bl', '#0x165d3e0'), 0x34e56d8: ('bl', '#0x165d600'),
        0x34e56e4: ('bl', '#0x165ead0'), 0x34e5784: ('bl', '#0x165e940'),
        0x34e57a4: ('bl', '#0x1660350'),
    })
    base = boot_base(cp)
    front = dispatch_entry(cp, base, 0xc0e818, 124, 8, 0x166)
    internal = dispatch_entry(cp, base, 0xff2b8c, 350, 20, 0x4155)
    if (front['entry_file_offset'], front['handler_file_offset'],
            internal['entry_file_offset'], internal['handler_file_offset']) != (
            0xc0e960, 0x5929ee, 0xff4428, 0x25454c):
        raise ValueError('LUT 分发表位置或处理函数不符')
    ranges = [(0x592db6, 0x592de6), (0x5929ee, 0x592a66),
              (0x254f70, 0x255092), (0x25454c, 0x254694),
              (0xa25db4, 0xa25dbe), (0xa24406, 0xa245b6),
              (0xa26bce, 0xa26c50), (0xa234c2, 0xa234e8),
              (0x3e076c, 0x3e0970)]
    ci = {i.address: i for start, end in ranges for i in decode_thumb(cp, start, end, base)}
    require_instructions(ci, {
        0x592db6: ('ldrh', 'r2, [r0, #2]'),
        0x592db8: ('movw', 'ip, #0x6818'), 0x592dbe: ('movt', 'ip, #0xd1'),
        0x592dc2: ('ldrh.w', 'r3, [ip, r1, lsl #3]'),
        0x592dcc: ('cmp', 'r1, #0x7c'), 0x592dda: ('ldr', 'r1, [r1, #4]'),
        0x592ddc: ('blx', 'r1'),
        0x5929f6: ('ldrb', 'r1, [r0, #8]'), 0x5929f8: ('movw', 'r2, #0x34c8'),
        0x5929fc: ('movt', 'r2, #0x1ff'), 0x592a00: ('str.w', 'r1, [r2, #0x624]'),
        0x592a04: ('ldrb', 'r6, [r0, #9]'), 0x592a06: ('str.w', 'r6, [r2, #0x628]'),
        0x592a0a: ('ldr', 'r3, [r0, #0xc]'), 0x592a0c: ('str.w', 'r3, [r2, #0x62c]'),
        0x592a10: ('ldr', 'r4, [r0, #0x10]'), 0x592a12: ('str.w', 'r4, [r2, #0x630]'),
        0x592a16: ('ldr.w', 'sl, [r0, #0x14]'), 0x592a1a: ('str.w', 'sl, [r2, #0x634]'),
        0x592a1e: ('ldr', 'r5, [r0, #0x18]'), 0x592a20: ('str.w', 'r5, [r2, #0x638]'),
        0x592a24: ('ldr.w', 'r8, [r0, #0x1c]'), 0x592a28: ('str.w', 'r8, [r2, #0x63c]'),
        0x592a2c: ('ldr.w', 'sb, [r0, #0x20]'), 0x592a38: ('str.w', 'sb, [r2, #0x640]'),
        0x254f8a: ('ldrh', 'r1, [r4, #2]'),
        0x254fa6: ('movw', 'r3, #0xab8c'), 0x254faa: ('movt', 'r3, #0x10f'),
        0x254fbc: ('adds', 'r5, #0x14'), 0x254fc0: ('cmp.w', 'r3, #0x15e'),
        0x255074: ('ldr', 'r1, [r5, #-0x4]'), 0x25507a: ('blx', 'r1'),
        0x25463e: ('ldr.w', 'r0, [r4, #0xc0]'), 0x254646: ('adds', 'r0, #1'),
        0x25464c: ('str.w', 'r0, [r4, #0xc0]'),
        0xa25db4: ('movw', 'r0, #0xefe8'), 0xa25db8: ('movt', 'r0, #0x173'),
        0xa26bd2: ('str', 'r0, [r1]'),
        0xa24412: ('bl', f'#{base+0xa25db4:#x}'), 0xa24416: ('mov', 'sl, r0'),
        0xa24476: ('mov.w', 'fp, #0x13c0'), 0xa244a8: ('ldr.w', 'r0, [r4, fp]'),
        0xa244b2: ('cmp', 'r0, #0xa'), 0xa244b4: ('bne', f'#{base+0xa244c8:#x}'),
        0xa244b6: ('ldr.w', 'r1, [sl]'), 0xa244ba: ('movw', 'r0, #0x13d0'),
        0xa244be: ('movs', 'r2, #0x60'), 0xa244c0: ('add', 'r0, r4'),
        0xa244c2: ('adds', 'r1, #0x68'), 0xa244c4: ('blx', f'#{base+0x51660c:#x}'),
        0xa234cc: ('movw', 'r1, #0x13b8'), 0xa234d2: ('add', 'r1, r4'),
        0xa234d4: ('bl', f'#{base+0x3e076c:#x}'),
        0x3e079c: ('add.w', 'r8, r4, #0x18'), 0x3e07e6: ('ldrd', 'r0, r1, [r8]'),
        0x3e07ee: ('ldr', 'r0, [r4, #0x28]'), 0x3e07f2: ('ldr', 'r0, [r4, #0x2c]'),
        0x3e07e0: ('ldr', 'r0, [r4, #0x70]'),
    }, base)
    fields = copied_fields(0x68, 0x13d0, 0x60, 0x13b8, [
        ('table_address', 0x68, 8), ('register_address', 0x70, 8),
        ('table_bytes', 0x78, 4), ('register_bytes', 0x7c, 4),
        ('generation_counter', 0xc0, 4)])
    return {
        'model': 'ILCE-7CM2', 'firmware': '2.01',
        'ap_sha256': TARGETS['ap'], 'cp_sha256': TARGETS['cp'],
        'evidence_level': 'verified-dispatch-segments-and-snapshot-field-copy',
        'ap_message_imports': {hex(va): name for va, name in expected_names.items()},
        'front_dispatch': front, 'internal_dispatch': internal,
        'front_state_link_va': '0x1ff34c8', 'internal_state_link_va': '0x165a720',
        'snapshot_context_link_va': '0x173efe8',
        'snapshot_copy': {'producer_file_offset': '0xa24406', 'when_selector': 10,
                          'source_offset': 0x68, 'object_offset': 0x13d0, 'bytes': 0x60,
                          'consumer_struct_object_offset': 0x13b8, 'fields': fields},
        'verified_segments': ['AP OSAL message allocation/send/reply imports',
                              'CP command 0x0166 dispatch -> front state',
                              'CP command 0x4155 dispatch -> internal LUT state setter',
                              'snapshot root + 0x68 -> object + 0x13d0 -> VFX input + 0x18'],
        'unresolved_edges': ['AP OSAL 目标队列到 CP 前端调度的完整路由尚未追踪',
                             '前端 0x0166 状态/后续请求如何关联内部 0x4155，未完整还原',
                             '本工具不覆盖内部状态到快照根的初始复制；新增定位见 research.trace_lut_snapshot',
                             '准备函数与消费函数的全部状态机调度、并发与缓冲生命周期未验证',
                             '完整分辨率 JPEG 调用、色域和伽马未确认'],
        'checked_windows': {'ap': [[hex(a), hex(b)] for a, b in ap_ranges],
                            'cp': [[hex(a), hex(b)] for a, b in ranges]},
        'limitations': ['分发表的指针由实际查表指令与目标函数共同验证；不把间接调用当作直接 BL',
                        '字段映射来自 96 字节复制及消费者读取，未执行原版固件',
                        '两个命令编号属于不同分发域，未证明能直接互换',
                        '静态结构相同不代表模式可用或 JPEG 已通过用户 LUT'],
        'ap_to_cp_runtime_verified': False, 'photo_pipeline_located': False,
        'camera_commands_sent': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ap', type=Path, required=True)
    parser.add_argument('--cp', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw = (json.dumps(trace(args.ap, args.cp), ensure_ascii=False, indent=2)+'\n').encode()
        write_bytes_new(args.output, raw)
        print(raw.decode(), end='')
        return 0
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f'STOPPED: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
