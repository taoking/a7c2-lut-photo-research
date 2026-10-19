"""Pin and verify static AP CUBE-parser observations; no payload generation."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_ap import adrp_target


def size_check_model(size):
    """Model only the observed 32-bit SUB/TST predicate, not the whole parser."""
    return (((size - 17) & 0xffffffff) & 0xffffffef) == 0


def adrp_add_reference(instructions, first, second):
    """Resolve a constant pointer, rejecting intervening writes and branches."""
    from capstone.arm64 import ARM64_OP_REG, ARM64_OP_IMM
    by_address = {ins.address: ins for ins in instructions}
    if first not in by_address or second not in by_address or second <= first:
        raise ValueError('ADRP/ADD 地址不在已解码区间内')
    start, end = by_address[first], by_address[second]
    if start.mnemonic != 'adrp' or end.mnemonic != 'add' or len(end.operands) != 3:
        raise ValueError('需要 ADRP 与立即数 ADD')
    if (end.operands[0].type != ARM64_OP_REG or end.operands[1].type != ARM64_OP_REG
            or end.operands[2].type != ARM64_OP_IMM):
        raise ValueError('不支持此 ADD 操作数')
    register = start.reg_name(start.operands[0].reg)
    if end.reg_name(end.operands[1].reg) != register:
        raise ValueError('ADRP/ADD 源寄存器不同')
    for ins in instructions:
        if first < ins.address < second:
            writes = {ins.reg_name(r).replace('w', 'x', 1) for r in ins.regs_access()[1]}
            if register in writes or ins.mnemonic.startswith(('b', 'ret', 'cb', 'tb')):
                raise ValueError('ADRP/ADD 之间存在基址写入或控制流，不能推导常量')
    word = struct.unpack('<I', start.bytes)[0]
    shift = end.operands[2].shift.value
    return adrp_target(word, first) + (end.operands[2].imm << shift)


def trace(path):
    with Path(path).open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != TARGETS['ap']:
            raise ValueError('仅接受完整指纹匹配的原版 AP 2.01')
        stream.seek(0)
        raw = stream.read()
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
    from elftools.elf.elffile import ELFFile
    with io.BytesIO(raw) as stream:
        elf = ELFFile(stream)
        text = elf.get_section_by_name('.text')
        if elf['e_machine'] != 'EM_AARCH64' or not elf.little_endian or text['sh_addr'] != text['sh_offset']:
            raise ValueError('原版 AP 代码映射不符')
        symbols = elf.get_section_by_name('.dynsym')
        plt = elf.get_section_by_name('.plt')
        relocations = elf.get_section_by_name('.rela.plt')
        names = {plt['sh_addr']+32+i*16: symbols.get_symbol(r['r_info_sym']).name
                 for i, r in enumerate(relocations.iter_relocations())}
    cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    cs.detail = True
    ranges = {'header': (0x3020308, 0x302040c), 'reader': (0x30208d4, 0x3020e40)}
    functions = {}
    for name, (start, end) in ranges.items():
        insns = list(cs.disasm(raw[start:end], start))
        if sum(ins.size for ins in insns) != end-start:
            raise ValueError('CUBE 解析代码区间不能完整解码')
        functions[name] = insns
    index = {ins.address: ins for insns in functions.values() for ins in insns}
    required = {
        0x30209a4: ('sub', 'w0, w0, #0x11'),
        0x30209ac: ('tst', 'w0, #0xffffffef'),
        0x30209b0: ('b.ne', '#0x3020a44'),
        0x3020990: ('bl', '#0x3020308'),
        0x30203e8: ('fcmp', 's0, #0.0'),
        0x30203fc: ('fmov', 's0, #1.00000000'),
        0x3020400: ('fcmp', 's1, s0'),
        0x3020a38: ('fcmp', 's0, #0.0'),
        0x3020a80: ('fmov', 's0, #1.00000000'),
        0x3020a84: ('fcmp', 's1, s0'),
        0x3020b4c: ('cbnz', 'w21, #0x3020c18'),
        0x3020bac: ('strh', 'w2, [x1, w0, uxtw #1]'),
        0x3020c48: ('str', 's3, [x19, w0, sxtw #2]'),
        0x3020c5c: ('str', 'wzr, [x19, w0, sxtw #2]'),
        0x3020da0: ('mov', 'w0, #0xbc00'),
        0x3020da4: ('str', 'w0, [x1]'),
        0x3020e38: ('bl', '#0x302002c'),
    }
    for address, expected in required.items():
        ins = index.get(address)
        if ins is None or (ins.mnemonic, ins.op_str) != expected:
            raise ValueError(f'已记录的解析指令不符：{address:#x}')
    size_string = adrp_add_reference(functions['header'], 0x3020314, 0x3020334)
    range_string = adrp_add_reference(functions['header'], 0x3020328, 0x3020338)
    for address, expected in ((size_string, b'LUT_3D_SIZE\0'), (range_string, b'LUT_3D_INPUT_RANGE\0')):
        if raw[address:address+len(expected)] != expected:
            raise ValueError('解析头字段常量不符')
    if names.get(0x165fd50) != 'strncmp' or names.get(0x165edb0) != 'sscanf':
        raise ValueError('解析函数的 C 库导入符号不符')
    scale, ceiling = struct.unpack_from('<2d', raw, 0x4bfa180)
    if (scale, ceiling) != (8192.0, 65535.0):
        raise ValueError('解析中间量的数值常量不符')
    return {
        'model': 'ILCE-7CM2', 'firmware': '2.01', 'ap_sha256': TARGETS['ap'],
        'evidence_level': 'bounded-parser-instruction-observations',
        'header_file_offset': '0x3020308', 'reader_file_offset': '0x30208d4',
        'constant_references': [
            {'field': 'LUT_3D_SIZE', 'string_file_offset': hex(size_string),
             'adrp_file_offset': '0x3020314', 'add_file_offset': '0x3020334'},
            {'field': 'LUT_3D_INPUT_RANGE', 'string_file_offset': hex(range_string),
             'adrp_file_offset': '0x3020328', 'add_file_offset': '0x3020338'}],
        'size_predicate': {'sub': 17, 'tst_mask': '0xffffffef', 'accepted_u32_sizes': [17, 33]},
        'explicit_input_range_checks': {'minimum': 0, 'maximum': 1,
                                        'scope': '显式 LUT_3D_INPUT_RANGE 字段；未完整复现其余头字段行为'},
        'intermediate_branches': [
            {'flag': 'zero', 'storage': 'interleaved unsigned16 RGB intermediate',
             'scale': scale, 'add_before_truncation': 0.5, 'clamp_after_scale': [0, ceiling],
             'later_converter_file_offset': '0x302002c'},
            {'flag': 'nonzero', 'storage': 'float32 RGB plus zero lane intermediate',
             'later_processing_file_offset': '0x36f6e50',
             'reported_output_bytes': 0xbc00}],
        'limitations': ['两种均是转换链的中间格式，不能直接当作最终硬件载荷',
                        '标志参数语义、后续转换/重采样及 CP 消费关系尚未完全追踪',
                        '未执行原版解析器，未宣称自己的 CUBE 读取器等同 Sony 实现',
                        '尚未证明完整分辨率 JPEG 会使用用户 LUT'],
        'photo_pipeline_located': False, 'camera_commands_sent': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ap', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = trace(args.ap)
        raw = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
        write_bytes_new(args.output, raw)
        print(raw.decode(), end='')
        return 0
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f'STOPPED: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
