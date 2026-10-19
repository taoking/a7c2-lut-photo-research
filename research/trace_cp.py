"""Read-only evidence from the pinned original CP: Thumb references and LUT calls.

Reports static, bounded observations. No firmware execution, patch creation,
USB imports, or assertion that a user LUT reaches still-photo JPEG pixels.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS

# Code-only intervals manually checked against the exact original CP image.
# File offsets, exclusive ends; not writable ranges or patch instructions.
FUNCTIONS = {
    'cc_state_compare': (0x13580c, 0x135ba2),
    'camcore_lut_dispatch': (0x324d28, 0x324f1a),
    'camcore_table_upload': (0x682a20, 0x682ad8),
    'vfx_mlut_dispatch': (0x3e076c, 0x3e0970),
    'vfx_user3d': (0x44615c, 0x446380),
}
STRINGS = {
    0x135ba4: b'CC: LutMode Change MOV/MON %02X <- %02X',
    0x135bcc: b'CC: LutMode Change CAP %02X <- %02X',
    0x135bf0: b'CC: LutMode Change SA %02X <- %02X',
    0x324f1c: b'CC: CamCore 3D-Lut table Write Start',
    0x446380: b'ddl_VfxSetMlutUser3D',
}


def boot_base(raw):
    """Recognize the three ARM entry instructions and their embedded literal."""
    if len(raw) < 16:
        raise ValueError('CP 启动头过短')
    ldr, add, jump, literal = struct.unpack_from('<4I', raw)
    if (ldr, add, jump) != (0xe59f1004, 0xe2811004, 0xe1a0f001):
        raise ValueError('未知 CP 入口指令，不能猜测基址')
    base = literal - 12
    if base < 0 or base % 4 or base + len(raw) > 2**32:
        raise ValueError('CP 入口字面量不能构成有效地址映射')
    return base


def thumb_adr_candidates(raw, target):
    """Scan T1 ADR halfwords. Candidates require instruction-boundary validation."""
    import numpy as np
    words = np.frombuffer(raw[:len(raw) // 2 * 2], dtype='<u2')
    indices = np.flatnonzero((words & 0xf800) == 0xa000)
    offsets = indices * 2
    destination = ((offsets + 4) & ~3) + (words[indices] & 255) * 4
    return [int(v) for v in offsets[destination == target]]


def thumb_bl_candidates(raw, target):
    """Scan Thumb-2 BL encodings, including signed S/J1/J2 displacement.

    This deliberately excludes BLX, B.W, register calls, ARM code and inferred
    function boundaries. Hits in data or second halfwords remain candidates.
    """
    import numpy as np
    words = np.frombuffer(raw[:len(raw) // 2 * 2], dtype='<u2')
    high, low = words[:-1], words[1:]
    indices = np.flatnonzero(((high & 0xf800) == 0xf000) & ((low & 0xd000) == 0xd000))
    high, low = high[indices].astype(np.int64), low[indices].astype(np.int64)
    sign = (high >> 10) & 1
    imm = ((sign << 24) | (((~((low >> 13) ^ sign)) & 1) << 23)
           | (((~((low >> 11) ^ sign)) & 1) << 22)
           | ((high & 0x3ff) << 12) | ((low & 0x7ff) << 1))
    imm = np.where(sign != 0, imm - (1 << 25), imm)
    offsets = indices * 2
    return [int(v) for v in offsets[offsets + 4 + imm == target]]


def decode_thumb(raw, start, end, base):
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_LITTLE_ENDIAN, CS_MODE_THUMB
    if not 0 <= start < end <= len(raw) or start % 2 or end % 2:
        raise ValueError('无效 Thumb 分析区间')
    cs = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
    cs.detail = True
    instructions = list(cs.disasm(raw[start:end], base + start))
    if sum(ins.size for ins in instructions) != end - start:
        raise ValueError('分析区间不能完整解码，停止推导')
    return instructions


def constant_call_arguments(instructions, base):
    """Conservative r2 constants in a straight-line block with direct calls.

    Unknown writes invalidate values. Calls clobber r0-r3/r12/lr. Conditional
    instructions and jumps discard state; no path-sensitive value is guessed.
    """
    from capstone.arm import ARM_OP_IMM, ARM_OP_REG, ARM_CC_AL, ARM_CC_INVALID
    constants, calls = {}, []
    for ins in instructions:
        ops = ins.operands
        mnemonic = ins.mnemonic.split('.')[0]
        if mnemonic in ('bl', 'blx'):
            if ops and ops[0].type == ARM_OP_IMM:
                calls.append({'site_file_offset': ins.address-base,
                              'target_file_offset': ops[0].imm-base,
                              'mnemonic': ins.mnemonic, 'r2_constant': constants.get('r2')})
            for reg in ('r0', 'r1', 'r2', 'r3', 'ip', 'r12', 'lr'):
                constants.pop(reg, None)
            continue
        before = dict(constants)
        writes = {ins.reg_name(reg) for reg in ins.regs_access()[1]}
        for reg in writes:
            constants.pop(reg, None)
        if ('pc' in writes or ins.cc not in (ARM_CC_AL, ARM_CC_INVALID)
                or ins.mnemonic.startswith(('b', 'it', 'cb'))):
            constants.clear()
            continue
        if len(ops) == 2 and ops[0].type == ARM_OP_REG and ops[1].type == ARM_OP_IMM:
            reg, value = ins.reg_name(ops[0].reg), ops[1].imm
            if mnemonic in ('mov', 'movs', 'movw'):
                constants[reg] = value & 0xffffffff
            elif mnemonic == 'movt' and reg in before:
                constants[reg] = (value << 16) | (before[reg] & 0xffff)
    return calls


def _require_instruction(index, offset, mnemonic, operands):
    ins = index.get(offset)
    if ins is None or (ins.mnemonic, ins.op_str) != (mnemonic, operands):
        raise ValueError(f'已记录的指令语义未匹配：{offset:#x}')


def trace(path):
    # Gate before decoding or interpreting anything; never modify input data.
    with Path(path).open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != TARGETS['cp']:
            raise ValueError('仅接受完整指纹匹配的原版 CP 2.01')
        stream.seek(0)
        raw = stream.read()
    base = boot_base(raw)
    if base != 0x108000:
        raise ValueError('已知 CP 入口基址不符')
    functions = {name: decode_thumb(raw, start, end, base) for name, (start, end) in FUNCTIONS.items()}
    index = {ins.address-base: ins for instructions in functions.values() for ins in instructions}
    references = []
    for target, text in STRINGS.items():
        if raw[target:target+len(text)+1] != text + b'\0':
            raise ValueError(f'记录的日志常量不匹配：{target:#x}')
        candidates = thumb_adr_candidates(raw, target)
        verified = [at for at in candidates if at in index and index[at].mnemonic == 'adr']
        if not verified:
            raise ValueError(f'缺少已解码函数中的 ADR 引用：{target:#x}')
        references.append({'string_file_offset': hex(target), 'label': text.decode(),
                           'verified_adr_file_offsets': [hex(v) for v in verified],
                           'unvalidated_candidate_count': len(candidates)-len(verified)})
    # Validate the exact log-choice instructions, including their branch targets.
    _require_instruction(index, 0x13599e, 'ldr.w', 'r0, [r8, #4]')
    _require_instruction(index, 0x1359a2, 'ldrb', 'r1, [r0, #3]')
    _require_instruction(index, 0x1359a4, 'cmp', 'r1, #2')
    _require_instruction(index, 0x1359a6, 'bne', f'#{base+0x1359f8:#x}')
    _require_instruction(index, 0x1359a8, 'ldrb', 'r0, [r0, #6]')
    _require_instruction(index, 0x1359aa, 'cmp', 'r0, #1')
    _require_instruction(index, 0x1359ac, 'bne', f'#{base+0x1359fc:#x}')
    _require_instruction(index, 0x324e04, 'bl', f'#{base+0x682a20:#x}')
    # A numeric discriminator selects the confirmed User3D call path.
    _require_instruction(index, 0x3e079a, 'ldr', 'r5, [r4, #8]')
    _require_instruction(index, 0x3e07d8, 'cmp', 'r5, #0xa')
    _require_instruction(index, 0x3e07e4, 'bne', f'#{base+0x3e0854:#x}')
    _require_instruction(index, 0x3e087c, 'bl', f'#{base+0x44615c:#x}')
    calls = {name: constant_call_arguments(instructions, base) for name, instructions in functions.items()}
    copies = [call for call in calls['camcore_table_upload'] if call['target_file_offset'] == 0x51660c]
    sizes = [call['r2_constant'] for call in copies]
    if sizes != [0x12c, 0xf0, 0xf0, 0xc0, 0xc8, 0xa0, 0xa0, 0x80]:
        raise ValueError('CamCore 表上传长度证据不符')
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_LITTLE_ENDIAN
    arm = list(Cs(CS_ARCH_ARM, CS_MODE_ARM | CS_MODE_LITTLE_ENDIAN).disasm(raw[0x51660c:0x516668], base+0x51660c))
    if not any(ins.mnemonic == 'ldm' and ins.op_str.startswith('r1!') for ins in arm) or not any(
            ins.mnemonic == 'stm' and ins.op_str.startswith('r0!') for ins in arm):
        raise ValueError('拷贝入口未确认 source/destination 的块加载/存储')
    return {
        'model': 'ILCE-7CM2', 'firmware': '2.01', 'cp_sha256': TARGETS['cp'],
        'boot_derived_base': hex(base), 'evidence_level': 'bounded-static-control-flow',
        'functions': {name: {'file_start': hex(start), 'file_end_exclusive': hex(end),
                             'instructions': len(functions[name]),
                             'slice_sha256': hashlib.sha256(raw[start:end]).hexdigest()}
                      for name, (start, end) in FUNCTIONS.items()},
        'log_references': references,
        'log_selector': {'selector_pointer_load_file_offset': '0x13599e',
                         'conditions': [
                             {'byte_3': '!= 2', 'label': 'MOV/MON'},
                             {'byte_3': '== 2', 'byte_6': '!= 1', 'label': 'CAP'},
                             {'byte_3': '== 2', 'byte_6': '== 1', 'label': 'SA'}],
                         'scope': '仅证实日志选择；字段枚举及完整运行条件尚未确认'},
        'camcore_upload': {'caller_file_offset': '0x324e04', 'callee_file_offset': '0x682a20',
                           'copy_target_file_offset': '0x51660c', 'chunk_bytes': sizes,
                           'total_bytes_per_reached_upload': sum(sizes),
                           'note': '固定表分段复制，尚未证明其格式等价于用户导入的 17/33 点 CUBE'},
        'user_lut_route': {'wrapper_file_offset': '0x3e076c',
                           'discriminator_source_field_offset': '0x8', 'discriminator': 10,
                           'direct_call_file_offset': '0x3e087c', 'callee_file_offset': '0x44615c',
                           'callee_label': 'ddl_VfxSetMlutUser3D',
                           'note': '已确认数值分支抵达 User3D；未证明完整 JPEG 流程会经过它'},
        'direct_bl_scan_candidates': {hex(target): [hex(v) for v in thumb_bl_candidates(raw, target)]
                                      for target in (0x13580c, 0x324d28, 0x682a20, 0x44615c)},
        'limitations': ['启动入口只给出该平面映像的静态基址依据，不是所有运行时内存映射证明',
                        '直接 BL 扫描可能命中数据或指令后半字，不能当作完整调用图',
                        'CamCore 固定表与 VFX 用户 LUT 的软件入口不同；硬件关系仍待调查',
                        '尚未定位完整 JPEG 的用户 LUT 像素链路；未执行任何固件代码'],
        'photo_pipeline_located': False, 'camera_commands_sent': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cp', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = trace(args.cp)
        raw = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
        write_bytes_new(args.output, raw)
        print(raw.decode(), end='')
        return 0
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f'STOPPED: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
