"""Verify an AArch64 PLT relocation and enumerate its direct BL callers.

Only direct calls in .text are counted. This is not a complete call graph,
does not identify a photo pipeline, and never produces a patch.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS

SYMBOL = '_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE'


def adrp_target(word, pc):
    if word & 0x9f000000 != 0x90000000:
        raise ValueError('不是 ADRP 指令')
    imm = ((word >> 5) & 0x7ffff) * 4 + ((word >> 29) & 3)
    if imm & 0x100000:
        imm -= 0x200000
    return (pc & ~0xfff) + imm * 4096


def plt_got(raw, pc):
    if len(raw) != 16:
        raise ValueError('PLT 桩长度不符')
    adrp, load, add, branch = struct.unpack('<4I', raw)
    if (adrp & 31 != 16 or load & 0xffc003ff != 0xf9400211
            or add & 0xffc003ff != 0x91000210 or branch != 0xd61f0220):
        raise ValueError('不支持此 PLT 指令结构')
    got = adrp_target(adrp, pc) + ((load >> 10) & 0xfff) * 8
    if adrp_target(adrp, pc) + ((add >> 10) & 0xfff) != got:
        raise ValueError('PLT LOAD 与 ADD 指向不同地址')
    return got


def direct_callers(code, base, target):
    import numpy as np
    if len(code) % 4:
        raise ValueError('AArch64 代码长度未按 4 字节对齐')
    words = np.frombuffer(code, dtype='<u4')
    offsets = np.flatnonzero((words & 0xfc000000) == 0x94000000)
    imm = (words[offsets] & 0x3ffffff).astype(np.int64)
    imm = np.where(imm >= 0x2000000, imm - 0x4000000, imm)
    addresses = base + offsets * 4
    return [int(x) for x in addresses[addresses + imm * 4 == target]]


def trace(path):
    from elftools.elf.elffile import ELFFile
    with Path(path).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != TARGETS['ap']:
            raise ValueError('仅分析精确匹配原版 2.01 的 AP，不接受其他或已改装程序')
        stream.seek(0)
        elf = ELFFile(stream)
        if elf['e_machine'] != 'EM_AARCH64' or not elf.little_endian:
            raise ValueError('需要 little-endian AArch64 ELF')
        symbols = elf.get_section_by_name('.dynsym')
        rel = elf.get_section_by_name('.rela.plt')
        plt = elf.get_section_by_name('.plt')
        text = elf.get_section_by_name('.text')
        candidates = []
        # Confirm the actual stub instructions, rather than trusting the slot formula.
        for index, relocation in enumerate(rel.iter_relocations()):
            if symbols.get_symbol(relocation['r_info_sym']).name != SYMBOL:
                continue
            slot = 32 + index * 16
            address = plt['sh_addr'] + slot
            got = plt_got(plt.data()[slot:slot+16], address)
            if got != relocation['r_offset']:
                raise ValueError('PLT 桩与重定位目标不匹配')
            callers = direct_callers(text.data(), text['sh_addr'], address)
            # These AP code offsets equal VA only within this ELF's .text mapping.
            candidates.append({'symbol': SYMBOL, 'plt_va': hex(address), 'got_va': hex(got),
                               'direct_bl_callers_va': [hex(x) for x in callers],
                               'direct_bl_callers_file_offsets': [
                                   hex(x-text['sh_addr']+text['sh_offset']) for x in callers]})
    if len(candidates) != 1:
        raise ValueError('目标符号未唯一匹配')
    return {'model': 'ILCE-7CM2', 'firmware': '2.01', 'ap_sha256': digest,
            'evidence_level': 'verified-import-and-direct-branch', 'candidates': candidates,
            'limitations': ['仅统计 .text 中静态直接 BL；未覆盖间接调用、尾调用或运行时解析',
                            'MPR 接口用途可能涉及媒体或元数据，未证明它对照片像素应用 LUT'],
            'photo_pipeline_located': False, 'camera_commands_sent': False}


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
