"""Read-only selected capture-to-MAIN stage transitions and callback fields.

Static continuation and table-copy evidence only; no firmware execution,
complete queued messages, device access or verified same-shot buffer identity.
"""
import argparse
import json
from pathlib import Path
import struct

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_capture_buffers import bounded_tbb_targets
from research.trace_capture_work import trace as trace_work
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp);baseline=trace_work(cp_path)
    # The transition table has 21 bytes plus padding; runner table has 7 plus
    # padding. Neither table/padding is decoded as instructions.
    ranges=[(0x371b34,0x371b50),(0x371b66,0x371d22),(0x371d8c,0x371e54),
            (0xa20ec2,0xa20ee2),(0xa0bbe8,0xa0bc6a),(0xa0bc6e,0xa0bcc2),
            (0xa0b94a,0xa0b9a4),(0xa0beee,0xa0bf5e),(0xa0b7c6,0xa0b836),
            (0x37fe60,0x37fe8c),(0xa0863c,0xa086ca),(0xa08e08,0xa08e0e),
            (0x407f1c,0x407f4a),(0x366d08,0x366d66),(0x366d6e,0x366df2),
            (0x37a99e,0x37a9b6)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    def edge(t,m):return (m,f'#{base+t:#x}')
    require_instructions(index,{
        0x371b3e:('mov','r4, r0'),0x371b44:('ldr','r5, [r4, #0x20]'),
        0x371b46:('cmp','r5, #0x14'),0x371b48:edge(0x371bd6,'bhi'),
        0x371b4c:('tbb','[pc, r5]'),
        0x371c38:('add.w','r0, r6, r6, lsl #1'),
        0x371c40:('add.w','r0, r8, r0, lsl #3'),0x371c44:('ldr','r1, [r0, #4]'),
        0x371c46:('mov','r0, r4'),0x371c48:call(0xa20ec2),
        0x371c4e:('str','r6, [r4, #0x20]'),0x371c6e:('movs','r0, #0'),
        0x371c72:('strb.w','r0, [r4, #0x27]'),
        0x371c76:('strd','r0, r0, [r4, #0x18]'),0x371c7a:('strd','r0, r0, [r4, #0x10]'),
        0x371cd2:('mov','r1, r4'),0x371cd4:call(0xa09456),
        0x371cdc:('mov','r1, r4'),0x371ce0:call(0xa08062),
        0x371cea:('mov','r1, r4'),0x371cec:call(0x371d8c),
        0x371d00:('mov','r1, r4'),0x371d02:call(0x371d8c),
        0x371d06:('mov','r0, r4'),0x371d08:call(0xa0194a),
        0x371d0e:('mov','r0, r4'),0x371d10:call(0xa0194a),
        0xa20ec4:('str','r1, [r0, #8]'),0xa20ed0:('ldr.w','r1, [r2, r1, lsl #2]'),
        0xa20ede:('str','r1, [r0, #4]'),
        0x371d96:('mov','r4, r1'),0x371d98:('mov','r8, r0'),
        0x371dc8:('movw','r1, #0xeca4'),0x371dcc:('add.w','r0, r8, r8, lsl #1'),
        0x371dd0:('movt','r1, #0x110'),0x371dd4:('add.w','r0, r1, r0, lsl #3'),
        0x371dd8:('ldr','r2, [r0, #8]'),0x371ddc:('add','r0, sp, #4'),
        0x371dde:('mov','r1, r4'),0x371de0:('blx','r2'),
        0x371de2:('ldr','r3, [sp, #0x14]'),0x371de4:('ldrd','lr, ip, [sp, #4]'),
        0x371de8:('ldrd','r5, r0, [sp, #0xc]'),
        0x371e42:('strd','lr, ip, [r4, #0xc]'),
        0x371e46:('strd','r5, r0, [r4, #0x14]'),0x371e4a:('str','r3, [r4, #0x1c]'),
        0xa0bbf0:('ldr','r5, [r1]'),0xa0bbf4:('movw','r0, #0x5a9c'),
        0xa0bbf8:('ldr','r0, [r5, r0]'),0xa0bbfa:('ldr','r4, [r0, #0x14]'),
        0xa0bbfc:('cmp','r4, #9'),0xa0bc02:call(0xa11958),
        0xa0bc06:('movs','r4, #5'),0xa0bc0c:('movne','r4, #6'),
        0xa0bc24:('cmp','r4, #9'),0xa0bc26:edge(0xa0bc46,'bgt'),
        0xa0bc2c:('add.w','r0, r4, r4, lsl #2'),
        0xa0bc34:('add.w','r0, r1, r0, lsl #2'),
        0xa0bc38:('ldm.w','r0, {r1, r2, r3, r5, r6}'),
        0xa0bc3c:('stm.w','r8, {r1, r2, r3, r5, r6}'),
        0xa0bc76:('ldr','r5, [r1]'),0xa0bc7a:('movw','r0, #0x5a9c'),
        0xa0bc7e:('ldr','r0, [r5, r0]'),0xa0bc80:('ldr','r4, [r0, #0x24]'),
        0xa0bc82:('cmp','r4, #3'),0xa0bc86:('ldr','r0, [r5, #0x3c]'),
        0xa0bc88:('ubfx','r0, r0, #2, #1'),0xa0bc8c:('adds','r4, r0, #1'),
        0xa0bca8:('add.w','r0, r4, r4, lsl #2'),
        0xa0bcb0:('add.w','r0, r1, r0, lsl #2'),
        0xa0bcb4:('ldm.w','r0, {r1, r2, r3, r5, r6}'),
        0xa0bcb8:('stm.w','r8, {r1, r2, r3, r5, r6}'),
        0xa0b952:('ldr','r5, [r1]'),0xa0b95c:('ldr','r4, [r0, #0x18]'),
        0xa0bef6:('ldr','r5, [r1]'),0xa0bf02:('ldr','r4, [r0, #0x1c]'),
        0xa0b7ce:('ldr','r5, [r1]'),0xa0b7da:('ldr','r4, [r0, #0x20]'),
        0x37fe64:('mov','r4, r0'),0x37fe70:('mov','r0, r4'),0x37fe72:call(0xa0863c),
        0x37fe76:('cbz',f'r0, #{base+0x37fe7c:#x}'),
        0x37fe78:('movs','r0, #3'),0x37fe88:('movs','r0, #2'),
        0xa08642:('mov','r4, r0'),0xa08644:('ldr','r0, [r4, #0x20]'),
        0xa08684:('ldr','r0, [r0, #0x14]'),0xa086ba:('str','r1, [sp, #0xc]'),
        0xa086bc:('add','r1, sp, #4'),0xa086be:('mov','r2, r4'),
        0xa086c0:('movs','r3, #0'),0xa086c2:call(0x407f1c),
        0xa08e08:('ldr','r2, [r0, #8]'),0xa08e0a:('mov','r0, r1'),0xa08e0c:('bx','r2'),
        0x407f26:('mov','fp, r1'),0x407f28:('mov','sl, r2'),
        0x407f34:('ldm.w','r2, {r0, r3, r4, r5, r6}'),
        0x407f3a:('stm.w','ip, {r0, r3, r4, r5, r6}'),0x407f3e:('strd','sl, r8, [sp, #0x24]'),
        0x366d0c:('mov','r4, r0'),0x366d42:('mov','r0, r4'),
        0x366d44:('ldr','r2, [r0, #0xc]!'),0x366d48:('ldr','r1, [r0, #4]'),
        0x366d4a:('add.w','r0, r0, r1, asr #1'),
        0x366d5a:('mov','r1, r4'),0x366d5c:('blx','r2'),
        0x366d5e:('cmp','r0, #6'),0x366d60:edge(0x366d8e,'bhi'),
        0x366d62:('tbb','[pc, r0]'),0x366d6e:('ldrb.w','r0, [r4, #0x27]'),
        0x366d72:('adds','r0, #1'),0x366d74:('strb.w','r0, [r4, #0x27]'),
        0x366d7a:('movs','r0, #0x14'),0x366d80:('ldr','r0, [r4, #4]'),
        0x366d86:('mov','r1, r4'),0x366d8c:('bx','r2'),
        0x37a99e:('mov','r0, r4'),0x37a9a4:edge(0x385d00,'b.w'),
        0x37a9ac:('mov','r0, r4'),0x37a9b2:edge(0x3859dc,'b.w'),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    table=constant(0x371c34,0x371c3c)
    callback=constant(0xa086b2,0xa086b6)
    if (table!=0x110eca4 or table!=constant(0x371dc8,0x371dd0)
            or callback!=((base+0x371b34)|1)
            or constant(0xa086a0,0xa086a6)!=((base+0xa08e08)|1)
            or baseline['photo_pipeline_located'] is not False):
        raise ValueError('阶段选择表、后续回调或前轮验证边界不符')
    transitions=bounded_tbb_targets(cp[0x371b50:0x371b65],0x371b50,len(cp))
    results=bounded_tbb_targets(cp[0x366d66:0x366d6d],0x366d66,len(cp))
    if any(base+t not in index for t in transitions+results):
        raise ValueError('阶段/返回值分发表目标未落在所查代码边界')
    chain=[11,12,13,14,15]
    for old,new in zip(chain,chain[1:]):
        target=transitions[old]
        require_instructions(index,{target:('movs',f'r6, #{new:#x}'),
                                    target+2:edge(0x371c34,'b')},base)
    if results!=(0x366d6e,0x366d80,0x366d7a,0x366df0,0x366dd8,0x366d8e,0x366df0):
        raise ValueError('执行返回值到步骤推进/归还路径的表不符')
    entries={}
    for group,factory,storage,source in [
            (11,0xa0bbe8,0x1a50360,0x14),(12,0xa0b94a,0x1a50428,0x18),
            (13,0xa0beee,0x1a50478,0x1c),(14,0xa0b7c6,0x1a504dc,0x20),
            (15,0xa0bc6e,0x1a5052c,0x24)]:
        row=struct.unpack_from('<6I',cp,table-base+group*24)
        if row[1]!=9 or row[2]!=((base+factory)|1) or row[3]!=storage:
            raise ValueError('选定组的类型、工厂和记录表不符')
        entries[str(group)]={'factory_file_offset':hex(factory),'stage_type':row[1],
                             'record_table_link_va':hex(storage),'selection_source_offset':source}
    if (constant(0xa0bc28,0xa0bc30)!=0x1a50360
            or constant(0xa0bca4,0xa0bcac)!=0x1a5052c
            or 2*20+8!=baseline['capture_main_dispatch']['capture_registration_store']['offset']
            or 1*20+8!=baseline['capture_main_dispatch']['main_registration_store']['offset']
            or baseline['bounded_tables']['main']['target_file_offsets'][:2]!=['0x37a97c','0x37a9ac']):
        raise ValueError('捕获/MAIN 工厂与已登记记录表不符')
    false_flags={k:v for k,v in baseline.items() if v is False}
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'selected-stage-continuation-and-work-based-factory-selection',
        'selected_continuation':{
            'request_file_offset':'0xa0863c','queued_callback_file_offset':'0x371b34',
            'request_stage_argument':'original stage -> r2 of 0x407f1c',
            'queue_scope':'descriptor copy/argument storage only; runtime delivery and order unverified',
            'transition_table_file_offset':'0x371b50','transition_table_entries':21,
            'selected_group_chain':chain,'group_field_offset':0x20,'step_field_offset':0x27,
            'selected_direct_stores':'group, type/queue fields, callback fields and step reset; no claim about all callees',
            'scope':'选定组 11–15 切换继续传原阶段指针；不保证回调运行、工作字段和槽位未被中间调用改写'},
        'group_factories':{'table_link_va':hex(table),'record_stride':24,'selected_entries':entries,
                           'selection_root':'pointer at work +0x5a9c',
                           'scope':'工厂输入字段/表项，不将配置值命名为相机模式或像素格式'},
        'callback_copy_and_execution':{
            'factory_consumer_file_offset':'0x371d8c','factory_output_bytes':20,
            'destination_stage_offset':0xc,'runner_file_offset':'0x366d08',
            'runner_member_pointer_offset':0xc,'runner_stage_argument':'r1 = original stage',
            'result_table_file_offset':'0x366d66','result_targets':[hex(t) for t in results],
            'result_zero':'increment stage byte +0x27 and dispatch same stage through its queue field',
            'result_one':'dispatch through queue field without the selected increment',
            'result_two':'call with argument 0x14, then dispatch through queue field',
            'scope':'局部复制、成员调用和返回分支；不解释其他返回值业务含义或完成同步'},
        'conditional_capture_main_selection':{
            'capture_group':11,'capture_effective_index':2,'capture_record_callback_offset':0x30,
            'main_group':15,'main_effective_index':1,'main_record_callback_offset':0x1c,
            'record_stride':20,'capture_entry_file_offset':'0x3816c4','main_entry_file_offset':'0x3859dc',
            'main_step_entries':{'0':'0x385d00','1':'0x3859dc'},
            'capture_special_raw_value':9,'capture_special_effective_values':[5,6],
            'main_special_raw_value':3,'main_special_expression':'1 + bit 2 of work word +0x3c',
            'scope':'仅在对应有效索引与阶段步骤条件成立时接上前轮分发；配置实际值、像素和缓冲身份未证'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '组号、工厂选择值和步骤字节是不同层次，不直接映射相机模式',
            '队列消息复制/返回码不保证运行送达、执行完成或先后顺序',
            '组 12–14 实际处理和前后调用仍可能替换/转移角色 9，需按所选函数核对',
            '原阶段参数的静态传递不证明工作指针、句柄或描述在同次拍摄中保持身份',
            '格式 3/4 有效传输、照片 LUT 使能、完整生命周期及色彩/同步未闭合'],
        'selected_group_transition_path_located':True,'work_based_factory_selection_located':True,
        'stage_callback_copy_located':True,'runner_step_advance_located':True,
        **false_flags,
        'selected_phase_chain_runtime_verified':False,
        'role9_unchanged_through_intervening_stages_verified':False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cp',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        raw=(json.dumps(trace(args.cp),ensure_ascii=False,indent=2)+'\n').encode()
        write_bytes_new(args.output,raw);print(raw.decode(),end='');return 0
    except (ValueError,OSError,ImportError) as exc:
        parser.exit(1,f'STOPPED: {exc}\n')


if __name__=='__main__':
    raise SystemExit(main())
