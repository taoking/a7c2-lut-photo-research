"""Verify bounded AP/CP LUT data-contract evidence; never execute firmware."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.lut_layout import layout_summary, split_summary
from research.trace_ap import direct_callers
from research.trace_cp import boot_base, decode_thumb


def read_original(path, kind):
    with Path(path).open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != TARGETS[kind]:
            raise ValueError(f'仅接受完整指纹匹配的原版 {kind.upper()} 2.01')
        stream.seek(0)
        return stream.read()


def require_instructions(index, expected, base=0):
    for offset, pair in expected.items():
        ins = index.get(offset + base)
        if ins is None or (ins.mnemonic, ins.op_str) != pair:
            raise ValueError(f'已记录的指令不符：{offset:#x}')


def trace(ap_path, cp_path):
    ap, cp = read_original(ap_path, 'ap'), read_original(cp_path, 'cp')
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
    from elftools.elf.elffile import ELFFile
    with io.BytesIO(ap) as stream:
        elf = ELFFile(stream)
        text = elf.get_section_by_name('.text')
        if elf['e_machine'] != 'EM_AARCH64' or not elf.little_endian or text['sh_addr'] != text['sh_offset']:
            raise ValueError('原版 AP 代码映射不符')
        text_bytes, text_base = text.data(), text['sh_addr']
        symbols, plt = elf.get_section_by_name('.dynsym'), elf.get_section_by_name('.plt')
        names = {plt['sh_addr']+32+n*16: symbols.get_symbol(r['r_info_sym']).name
                 for n, r in enumerate(elf.get_section_by_name('.rela.plt').iter_relocations())}
    if names.get(0x165d3e0) != 'memcpy' or names.get(0x165d270) != 'memset':
        raise ValueError('表转换函数的内存导入不符')
    cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    # Some are bounded windows within larger functions, not inferred functions.
    ap_ranges = [(0x302002c, 0x30201d0), (0x3020c98, 0x3020e40),
                 (0x3020e40, 0x3020f70), (0x3021228, 0x3021338),
                 (0x3088858, 0x30889b0), (0x3089634, 0x30896ec),
                 (0x30ac218, 0x30ac298), (0x30ac3fc, 0x30ac424),
                 (0x34ebb84, 0x34ebc5c)]
    ap_index = {}
    for start, end in ap_ranges:
        insns = list(cs.disasm(ap[start:end], start))
        if sum(i.size for i in insns) != end-start:
            raise ValueError('AP 选定区间不能完整解码')
        ap_index.update((i.address, i) for i in insns)
    require_instructions(ap_index, {
        0x302005c: ('mov', 'x2, #0xbb80'), 0x3020060: ('bl', '#0x165d270'),
        0x3020070: ('add', 'x1, x1, #0x190'),
        0x3020074: ('mov', 'x2, #0x60'), 0x3020078: ('bl', '#0x165d3e0'),
        0x3020080: ('cmp', 'w21, #0x11'), 0x3020088: ('cmp', 'w21, #0x21'),
        0x3020094: ('mov', 'w14, #2'), 0x302015c: ('mov', 'w14, #1'),
        0x30200b8: ('mov', 'x16, #0x3e8'), 0x30200c0: ('mov', 'x17, #0x1f40'),
        0x30200c4: ('mov', 'x18, #0x3e80'), 0x30200d8: ('cmp', 'w3, #0x13'),
        0x30200e4: ('cmp', 'w4, #0x13'), 0x30200fc: ('cmp', 'w5, #0x13'),
        0x3020104: ('cmp', 'w3, #0x10'),
        0x3020138: ('strh', 'w12, [x19, x6, lsl #1]'),
        0x3020144: ('strh', 'w11, [x19, x12, lsl #1]'),
        0x3020148: ('strh', 'w10, [x19, x6, lsl #1]'),
        0x3020198: ('mov', 'x21, #0xbb80'), 0x30201ac: ('bl', '#0x165d3e0'),
        0x30201b0: ('str', 'w21, [x20]'), 0x30201b4: ('str', 'x0, [x20, #8]'),
        0x3020cc0: ('mov', 'x0, #0xbb80'), 0x3020cc8: ('add', 'x0, x27, x0'),
        0x3020cd0: ('str', 'x0, [x25]'), 0x3020ce4: ('str', 'x27, [x24]'),
        0x3020da0: ('mov', 'w0, #0xbc00'), 0x3020da4: ('str', 'w0, [x1]'),
        0x3020ef0: ('ldr', 'w22, [x21]'), 0x3020f00: ('bl', '#0x367f414'),
        0x302131c: ('mov', 'x2, #0xbc00'),
        0x3088944: ('cmp', 'w0, #1'), 0x308894c: ('cset', 'w0, eq'),
        0x3088954: ('str', 'w0, [x29, #0x9c]'),
        0x308895c: ('ldrb', 'w2, [x29, #0x9c]'), 0x3088968: ('bl', '#0x30208d4'),
        0x3089684: ('cmp', 'w0, #1'), 0x308968c: ('cset', 'w0, eq'),
        0x3089690: ('str', 'w0, [x29, #0x90]'),
        0x3089698: ('ldrb', 'w2, [x29, #0x90]'), 0x30896a4: ('bl', '#0x30208d4'),
        0x30ac274: ('mov', 'w0, #0xbb80'),
        0x30ac27c: ('stp', 'w0, w0, [x29, #0xd0]'),
        0x30ac280: ('mov', 'w0, #0x7c'), 0x30ac284: ('str', 'w0, [x29, #0xd8]'),
        0x30ac290: ('bl', '#0x34c6418'),
        0x30ac404: ('mov', 'w2, #0'), 0x30ac41c: ('bl', '#0x30208d4'),
        0x34ebba4: ('mov', 'w1, #0x200d'), 0x34ebbac: ('mov', 'w1, #0x166'),
        0x34ebbb4: ('mov', 'w1, #0x24'), 0x34ebc38: ('bl', '#0x34e552c'),
    })
    parity = list(struct.iter_unpack('<3i', ap[0x4bfa190:0x4bfa1f0]))
    if parity != [(r, g, b) for r in range(2) for g in range(2) for b in range(2)]:
        raise ValueError('转换函数的八分组起点常量不符')
    callers = direct_callers(text_bytes, text_base, 0x30208d4)
    if callers != [0x3088968, 0x30896a4, 0x30ac41c]:
        raise ValueError('AP 读取函数直接 BL 集合不符')
    base = boot_base(cp)
    cp_ranges = [(0x25454c, 0x254694), (0x3e076c, 0x3e0970),
                 (0x44615c, 0x446380), (0x446398, 0x446658),
                 (0xa719de, 0xa71ab4), (0xa71ab4, 0xa71b84)]
    cp_index = {i.address: i for start, end in cp_ranges for i in decode_thumb(cp, start, end, base)}
    require_instructions(cp_index, {
        0x2545cc: ('ldrd', 'r1, r2, [r5, #0x10]'),
        0x2545d0: ('ldr', 'r3, [r4, #0x10]'),
        0x2545d2: ('movw', 'r0, #0xa720'), 0x2545d6: ('movt', 'r0, #0x165'),
        0x2545dc: ('str', 'r3, [r0, #0x68]'),
        0x2545e4: ('ldr', 'r3, [r4, #0x14]'), 0x2545e6: ('str', 'r3, [r0, #0x78]'),
        0x2545e8: ('ldr', 'r3, [r4, #0x18]'), 0x2545ec: ('str', 'r1, [r0, #0x70]'),
        0x2545f8: ('ldr', 'r1, [r4, #0x1c]'), 0x2545fa: ('str', 'r1, [r0, #0x7c]'),
        0x254668: ('movw', 'r0, #0xb789'), 0x254670: ('movt', 'r0, #0xf7'),
        0x3e07ee: ('ldr', 'r0, [r4, #0x28]'), 0x3e07f2: ('ldr', 'r0, [r4, #0x2c]'),
        0x3e0812: ('bl', f'#{base+0x446398:#x}'),
        0x4462da: ('bl', f'#{base+0xa719de:#x}'),
        0x446590: ('bl', f'#{base+0xa719de:#x}'),
        0x446602: ('bl', f'#{base+0xa71ab4:#x}'),
        0xa71a34: ('ldr', 'r0, [r5, #4]'), 0xa71a36: ('movw', 'r1, #0xbb80'),
        0xa71a3a: ('cmp', 'r0, r1'), 0xa71a3c: ('bne', f'#{base+0xa71a72:#x}'),
        0xa71a58: ('movw', 'r0, #0x2ee0'),
        0xa71b0a: ('ldr', 'r0, [r5, #4]'), 0xa71b0c: ('cmp', 'r0, #0x7c'),
        0xa71b0e: ('bne', f'#{base+0xa71b42:#x}'),
        0xa71b2a: ('movs', 'r0, #0x1f'),
    }, base)
    log = b'FW: SET_USER_LUT_BINARY_DATA addr:'
    if cp[0xe73789:0xe73789+len(log)] != log:
        raise ValueError('CP 用户 LUT 设置日志引用不符')
    split = split_summary(0xbc00, 0, 0xbb80, 0xbb80, 0x7c)
    return {
        'model': 'ILCE-7CM2', 'firmware': '2.01',
        'ap_sha256': TARGETS['ap'], 'cp_sha256': TARGETS['cp'],
        'evidence_level': 'bounded-data-layout-and-matching-consumer-contracts',
        'ap_reader_callers_file_offsets': list(map(hex, callers)),
        'ap_reader_flags': {'0x3088968': 'snapshot word == 1',
                            '0x30896a4': 'snapshot word == 1', '0x30ac41c': 0,
                            'snapshot_enum_meaning': 'unresolved'},
        'flag_zero_layout': [layout_summary(n) for n in (17, 33)],
        'flag_nonzero_reported_output_bytes': 0xbc00,
        'extended_transfer_spans': split,
        'ap_transfer': {'wrapper_file_offset': '0x34c6418', 'encoder_file_offset': '0x34ebb84',
                        'header_u16': ['0x200d', '0x166', '0x24', '0x8001'],
                        'sender_file_offset': '0x34e552c'},
        'cp_user_lut_setter': {'file_offset': '0x25454c', 'state_link_va': '0x165a720',
                              'table_address_field': '0x68', 'table_length_field': '0x78',
                              'register_address_field': '0x70', 'register_length_field': '0x7c'},
        'cp_consumers': {'user3d_file_offset': '0x44615c', 'artgen_file_offset': '0x446398',
                         'table_upload_file_offset': '0xa719de', 'required_table_bytes': 0xbb80,
                         'register_upload_file_offset': '0xa71ab4', 'required_register_bytes': 0x7c,
                         'table_transfer_count_parameter': 0x2ee0,
                         'register_transfer_count_parameter': 0x1f,
                         'bytes_per_count_ratio': 4},
        'checked_windows': {'ap': [[hex(a), hex(b)] for a, b in ap_ranges],
                            'cp': [[hex(a), hex(b)] for a, b in cp_ranges]},
        'limitations': ['AP 输出区间与 CP 下层长度一致；没有完整证明 IPC 分发和参数快照到 VFX 的每一跳',
                        '读取标志的快照枚举、槽位格式标记与传输分支之间的完整关联尚未确认',
                        'flag-zero 索引模型只覆盖该分支；不代表 IPSX 转换器和全部硬件 LUT 格式',
                        '124 字节寄存器区后的 4 字节用途未定，不能当作更多寄存器写入',
                        '输入色域/伽马、运行缓冲生命周期和完整分辨率 JPEG 路径未确认',
                        '静态验证没有执行 Sony 函数，没有生成机内载荷或补丁'],
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
        result = trace(args.ap, args.cp)
        raw = (json.dumps(result, ensure_ascii=False, indent=2)+'\n').encode()
        write_bytes_new(args.output, raw)
        print(raw.decode(), end='')
        return 0
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f'STOPPED: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
