"""Read-only CP evidence for snapshot refresh and queued VFX callbacks.

Potential instruction paths assume calls return and do not solve predicates.
Optional edge decisions must be justified separately by the caller.
They are not proof of execution frequency, camera mode, or JPEG pixel flow.
"""
import argparse
from collections import deque
import json
from pathlib import Path

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value, snapshot_field_path


def potential_thumb_path(instructions, start, target, *, branch_decisions=None, allow_gaps=False):
    """Find a possible bounded path; never follow indirect jumps or jump tables.

    Both conditional arms are possible unless a caller supplies a boolean
    taken/not-taken decision at that instruction address. This does not derive
    or validate predicates, callee effects, aliases or runtime satisfiability.
    Calls may return. Unknown PC writes terminate a path. Input is contiguous
    by default; allow_gaps permits separate decoded blocks, with no invented
    fallthrough edge across a gap. Duplicate/overlapping instructions fail.
    """
    from capstone import CS_GRP_JUMP
    from capstone.arm import ARM_OP_IMM, ARM_CC_AL, ARM_CC_INVALID
    ordered = sorted(instructions, key=lambda ins: ins.address)
    if not ordered:
        raise ValueError('指令区间为空')
    cursor = ordered[0].address
    for ins in ordered:
        if ins.address < cursor or (not allow_gaps and ins.address != cursor):
            raise ValueError('指令区间不连续或重复')
        cursor += ins.size
    index = {ins.address: ins for ins in ordered}
    if start not in index or target not in index:
        raise ValueError('路径端点不是已解码指令边界')
    decisions = {} if branch_decisions is None else branch_decisions
    if type(allow_gaps) is not bool or not isinstance(decisions, dict):
        raise ValueError('路径选项需要布尔值和条件分支决策字典')
    for address, taken in decisions.items():
        ins = index.get(address)
        if type(address) is not int or type(taken) is not bool or ins is None:
            raise ValueError('分支决策必须指向已解码条件分支并使用布尔值')
        mnemonic = ins.mnemonic.split('.')[0]
        conditional = (mnemonic in ('cbz', 'cbnz') or
                       (ins.group(CS_GRP_JUMP) and mnemonic.startswith('b')
                        and mnemonic not in ('bl', 'blx') and ins.operands
                        and ins.operands[0].type == ARM_OP_IMM
                        and ins.cc not in (ARM_CC_AL, ARM_CC_INVALID)))
        if not conditional:
            raise ValueError('不能给调用、无条件跳转或普通指令指定条件决策')
    parent = {start: None}
    queue = deque([start])
    while queue:
        address = queue.popleft()
        if address == target:
            path = []
            while address is not None:
                path.append(address)
                address = parent[address]
            return list(reversed(path))
        ins = index[address]
        mnemonic = ins.mnemonic.split('.')[0]
        next_address = address + ins.size
        if mnemonic in ('bl', 'blx'):
            successors = [next_address]
        elif mnemonic in ('cbz', 'cbnz'):
            successors = [ins.operands[-1].imm, next_address]
        elif (ins.group(CS_GRP_JUMP) and mnemonic.startswith('b')
              and ins.operands and ins.operands[0].type == ARM_OP_IMM):
            successors = [ins.operands[0].imm]
            if ins.cc not in (ARM_CC_AL, ARM_CC_INVALID):
                successors.append(next_address)
        elif (mnemonic in ('bx', 'tbb', 'tbh')
              or any(ins.reg_name(reg) == 'pc' for reg in ins.regs_access()[1])):
            successors = []
        else:
            successors = [next_address]
        if address in decisions:
            # A checked conditional's first successor is the taken target.
            successors = [successors[0] if decisions[address] else next_address]
        for successor in successors:
            if successor in index and successor not in parent:
                parent[successor] = address
                queue.append(successor)
    return None


def trace(cp_path):
    cp = read_original(cp_path, 'cp')
    base = boot_base(cp)
    ranges = [(0x7d2d54,0x7d2dca), (0x3cf484,0x3cfa6c),
              (0x3cef9a,0x3cefc4), (0x3bef6c,0x3bef8e),
              (0xa234c2,0xa234e8), (0x3dfedc,0x3dff9a),
              (0x407f1c,0x407f4a), (0xa20c16,0xa20c5c),
              (0xa214e2,0xa2153a)]
    blocks = [decode_thumb(cp,a,b,base) for a,b in ranges]
    index = {ins.address:ins for block in blocks for ins in block}
    require_instructions(index, {
        0x7d2d5c: ('mov','r6, r0'), 0x7d2d5e: ('movs','r0, #0x26'),
        0x7d2d60: ('blx',f'#{base+0x4da5a0:#x}'),
        0x7d2d64: ('cbnz',f'r0, #{base+0x7d2da6:#x}'),
        0x7d2d6a: ('mov','r0, r6'), 0x7d2d6c: ('movw','r2, #0xd64'),
        0x7d2d74: ('blx',f'#{base+0x51660c:#x}'),
        0x7d2da0: ('movs','r0, #0x26'),
        0x7d2da2: ('blx',f'#{base+0x4d9f58:#x}'),
        0x3cf4a8: ('addw','r0, pc, #0x70c'),
        0x3cfa32: ('mov','r5, r4'), 0x3cfa66: ('mov','r0, r5'),
        0x3cfa68: ('bl',f'#{base+0x7d2d54:#x}'),
        0x3cefba: ('str','r0, [sp, #0x20]'),
        0x3cefbc: ('add','r1, sp, #0x18'),
        0x3cefbe: ('mov','r0, r4'),
        0x3cefc0: ('bl',f'#{base+0x407f1c:#x}'),
        0x407f26: ('mov','fp, r1'), 0x407f28: ('mov','sl, r2'),
        0x407f2a: ('add','r1, sp, #0x10'),
        0x407f2c: ('mov','r8, r3'), 0x407f30: ('mov','r2, fp'),
        0x407f34: ('ldm.w','r2, {r0, r3, r4, r5, r6}'),
        0x407f38: ('movs','r2, #0x1c'),
        0x407f3a: ('stm.w','ip, {r0, r3, r4, r5, r6}'),
        0x407f3e: ('strd','sl, r8, [sp, #0x24]'),
        0x407f42: ('ldr.w','r0, [sb, #0x18]'),
        0x407f46: ('blx',f'#{base+0x4e4b84:#x}'),
        0x3bef84: ('str','r0, [sp, #0x80]'),
        0x3bef86: ('add','r1, sp, #0x78'),
        0x3bef8a: ('bl',f'#{base+0xa20c16:#x}'),
        0xa20c20: ('ldm.w','r1, {r4, r5, r6, r8, lr}'),
        0xa20c28: ('stm.w','ip, {r4, r5, r6, r8, lr}'),
        0xa20c2c: ('strd','r2, r3, [sp, #0x14]'),
        0xa20c46: ('mov','r2, sp'),
        0xa20c50: ('bl',f'#{base+0xa214e2:#x}'),
        0xa21504: ('ldm','r5!, {r2, r3, r4, r6}'),
        0xa2150a: ('stm','r1!, {r2, r3, r4, r6}'),
        0xa2150c: ('ldm.w','r5, {r2, r3, r4, r6}'),
        0xa21510: ('stm','r1!, {r2, r3, r4, r6}'),
        0xa2151e: ('str','r0, [r2]'), 0xa21520: ('str','r0, [r1, #4]'),
        0xa21526: ('adds','r1, #1'), 0xa21528: ('str.w','r1, [sb, #8]'),
        0xa234c6: ('mov','r4, r0'),
        0xa234c8: ('movw','r0, #0x13b4'),
        0xa234cc: ('movw','r1, #0x13b8'),
        0xa234d0: ('ldr','r0, [r4, r0]'), 0xa234d2: ('add','r1, r4'),
        0xa234d4: ('bl',f'#{base+0x3e076c:#x}'),
        0x3dff12: ('ldr','r1, [r0]'), 0x3dff1c: ('ldrb','r2, [r0]'),
        0x3dff1e: ('cmp','r1, #2'),
        0x3dff20: ('bne',f'#{base+0x3dff54:#x}'),
        0x3dff22: ('eor','r0, r2, #1'), 0x3dff26: ('cmp','r0, #1'),
        0x3dff28: ('bne',f'#{base+0x3dff54:#x}'),
        0x3dff60: ('bpl',f'#{base+0x3dff7e:#x}'),
        0x3dff62: ('cbz',f'r1, #{base+0x3dff7e:#x}'),
        0x3dff64: ('ldrd','r3, r0, [r8]'),
        0x3dff68: ('ldrd','r6, r5, [r8, #8]'),
        0x3dff7a: ('bl',f'#{base+0xa3c57a:#x}'),
        0x3dff7e: ('movs','r0, #0'),
        0x3dff80: ('strd','r0, r0, [r8]'),
        0x3dff84: ('strd','r0, r0, [r8, #8]'),
        0x3dff88: ('b',f'#{base+0x3dff9a:#x}'),
    },base)
    insns = list(index.values())
    def constant(first,last):
        return movw_movt_value(insns,base+first,base+last)
    source = constant(0x7d2d66,0x7d2d70)
    root = constant(0x3cf9e6,0x3cf9ee)
    callback = constant(0x3cef9a,0x3cefae)
    vfx_callback = constant(0x3bef6c,0x3bef80)
    state = constant(0x3dff06,0x3dff0e)
    flag = constant(0x3dff14,0x3dff18)
    log = constant(0x3dff70,0x3dff76)-base
    if (source,root,callback,vfx_callback,state,flag,log) != (
            0x165a720,0x172fe50,base+0x3cf484+1,base+0xa234c2+1,
            0x1a6aefc,0x1b1e235,0xec18fa):
        raise ValueError('刷新地址、回调或就绪状态常量不符')
    # ABI assumption only: callee-saved registers retain values across calls.
    for register,first,last in [('r4',0x3cf9ee,0x3cfa32),('r5',0x3cfa32,0x3cfa68)]:
        if any(register in {i.reg_name(r) for r in i.regs_access()[1]}
               for i in blocks[1] if base+first < i.address < base+last):
            raise ValueError(f'根指针传递期间重新写入 {register}')
    path = potential_thumb_path(blocks[1],base+0x3cf484,base+0x3cfa68)
    if path is None:
        raise ValueError('未找到回调入口到刷新调用的潜在控制流路径')
    for offset,text in [(0x3cfbb8,b'VD_Pre S'),
                        (log,b'FW: StartVfx: MLUT not ready. state=%d wait_cb=%d onoff=%d,%d,%d,%d')]:
        if cp[offset:offset+len(text)+1] != text+b'\0':
            raise ValueError('回调或就绪检查日志不符')
    return {
        'model':'ILCE-7CM2', 'firmware':'2.01', 'cp_sha256':TARGETS['cp'],
        'evidence_level':'static-refresh-and-callback-submission-segments',
        'snapshot_refresh':{
            'source_link_va':hex(source), 'root_link_va':hex(root), 'copy_bytes':0xd64,
            'helper_file_offset':'0x7d2d54', 'copy_call_file_offset':'0x7d2d74',
            'caller_file_offset':'0x3cfa68', 'callback_entry_file_offset':'0x3cf484',
            'callback_descriptor_store_file_offset':'0x3cefba',
            'submission_call_file_offset':'0x3cefc0', 'callback_log':'VD_Pre S',
            'submission_helper_file_offset':'0x407f1c', 'submitted_bytes':0x1c,
            'potential_entry_to_copy_path_instructions':len(path),
            'paired_control_calls':{'argument':0x26, 'before_copy_file_offset':'0x4da5a0',
                                    'after_copy_file_offset':'0x4d9f58',
                                    'copy_condition':'first call returns zero'},
            'field_path':snapshot_field_path()},
        'vfx_callback':{'descriptor_store_file_offset':'0x3bef84',
                        'submission_call_file_offset':'0x3bef8a',
                        'submission_helper_file_offset':'0xa20c16',
                        'list_insert_helper_file_offset':'0xa214e2',
                        'list_node_payload_bytes':32,
                        'entry_file_offset':'0xa234c2', 'handle_object_offset':0x13b4,
                        'input_object_offset':0x13b8,
                        'consumer_call_file_offset':'0xa234d4',
                        'consumer_file_offset':'0x3e076c'},
        'transfer_readiness':{'entry_file_offset':'0x3dfedc',
                              'state_link_va':hex(state), 'byte_flag_link_va':hex(flag),
                              'initial_gate':'state == 2 and byte_flag == 0',
                              'fallback_zero_store_file_offsets':['0x3dff80','0x3dff84'],
                              'fallback_zeroed_bytes':16,
                              'scope':'未就绪分支可清零传入的四个开关字，不等于取消整次传输'},
        'findings':['初始构造之外存在同源、同根、同长度的快照复制调用',
                    'VD_Pre 回调描述符被复制并提交，入口到刷新点存在潜在静态路径',
                    '另一回调描述符进入链表，其入口从对象取得 VFX 句柄/参数并调用 LUT 分发器'],
        'limitations':['路径搜索不求解条件，假定调用可返回；不证明实际执行及频率',
                       '跨调用寄存器传递按 ABI 解释；未完成被调用者内存副作用分析',
                       '成对控制 API 的类型、写入者同步、缓冲生命周期仍未完整证明',
                       '两类回调的全部调度、模式枚举及全分辨率 JPEG 缓冲仍未连接',
                       '就绪检查不证明 LUT 已作用于任何照片，也不确定输入色域/伽马'],
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
