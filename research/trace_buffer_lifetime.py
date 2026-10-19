"""Read-only unit-slot reuse and selected descriptor creation/release paths.

Static stores and conditional calls only. No complete device handles/messages,
firmware execution, device access or verified photo-buffer lifetime.
"""
import argparse
import json
from pathlib import Path

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_buffer_query import trace as trace_query
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_refresh import potential_thumb_path
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp);baseline=trace_query(cp_path)
    ranges=[(0xb16314,0xb1645a),(0xb1645a,0xb16686),(0xb16686,0xb166de),
            (0xb1671a,0xb16778),(0xb144d6,0xb1452c),(0xb14554,0xb14620),
            (0xb1483e,0xb14930),(0xb15526,0xb155b6),
            (0xb16bd6,0xb16d0e),(0xb14ed6,0xb14f44)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    def edge(t,m):return (m,f'#{base+t:#x}')
    require_instructions(index,{
        0xb16320:('adds','r0, r1, #7'),0xb16326:('movw','r1, #0xffc0'),
        0xb1632a:('movw','r6, #0xc558'),0xb16342:('movt','r6, #0x1a8'),
        0xb1633a:('bic','r0, r0, #7'),0xb16352:('add','r1, r0'),
        0xb16354:('str','r0, [r6]'),0xb16356:('str.w','r1, [sl]'),
        0xb163ee:('add.w','sb, sb, #0x40'),
        0xb16412:('movw','r1, #0x3fe'),0xb1642c:('movs','r1, #0x38'),
        0xb16434:('adds','r0, #8'),0xb16436:('blx',f'#{base+0x516d00:#x}'),
        0xb1643e:call(0xb1671a),0xb1644a:('adds','r5, #0x40'),
        0xb1644e:edge(0xb1642a,'bls'),0xb1649e:call(0xb16686),
        0xb164bc:('ldrh.w','fp, [sp, #8]'),0xb164c8:('lsl.w','r0, fp, #6'),
        0xb164e8:('add.w','r2, r1, fp, lsl #6'),
        0xb164f6:('ldrb','r5, [r6, #0xb]!'),0xb164fa:('cmp','r5, #0x1e'),
        0xb164f4:('movs','r3, #1'),0xb164fc:('it','ls'),
        0xb164fe:('addls','r3, r5, #1'),0xb16502:('strb','r3, [r6]'),
        0xb16504:('strh','r0, [r2, #0xc]'),
        0xb1650c:('bfc','r0, #0xa, #0x16'),0xb1651e:('orr','r0, r0, #0x8000'),
        0xb16526:('and','r0, r3, #0x1f'),0xb1652e:('bic','r2, r2, #0x7c00'),
        0xb16532:('orr.w','r0, r2, r0, lsl #10'),
        0xb1655c:('add.w','r3, r1, r8, lsl #2'),
        0xb16566:('str','r5, [r3, #0x10]!'),0xb16570:call(0xb144d6),
        0xb1658a:('ldr','r3, [r0, #0x10]!'),0xb16590:('str','r2, [r3, #0x28]'),
        0xb16596:('ldr','r2, [r2, #4]'),0xb1659a:('str','r2, [r0, #0x2c]'),
        0xb1659c:('ldr','r0, [sb], #4'),0xb165a0:('adds','r2, r0, #1'),
        0xb165a2:edge(0xb16554,'bne'),0xb16616:('strh.w','sl, [r0, #0xe]'),
        0xb1669e:('cmp','r2, r3'),0xb166a0:edge(0xb166a8,'bne'),
        0xb166b2:('ldrh.w','r3, [r3, r2, lsl #1]'),0xb166b6:('strh','r3, [r0]'),
        0xb166ba:('movw','r3, #0x3ff'),0xb166be:('cmp','r2, r3'),
        0xb166c4:('it','lo'),0xb166c6:('addlo','r3, r2, #1'),0xb166c8:('str','r3, [r1]'),
        0xb16722:('movw','ip, #0x3ff'),0xb1673c:('cmp','r2, ip'),
        0xb1673e:('it','lo'),0xb16740:('addlo','r3, r2, #1'),
        0xb16746:('cmp','r3, r1'),0xb16748:edge(0xb16750,'bne'),
        0xb1675a:('strh.w','r0, [r1, r2, lsl #1]'),0xb16762:('str.w','r3, [lr]'),
        0xb144e0:('mov','r5, r3'),0xb1450e:('add','r3, sp, #4'),
        0xb14510:call(0xb14554),0xb14516:('ldr','r1, [sp, #4]'),
        0xb14520:('str','r1, [r5]'),0xb14522:call(0xb14c58),
        0xb145e0:('ldr.w','r5, [r0, r6, lsl #3]'),0xb145f2:('ldr','r0, [r5, #0x24]'),
        0xb145fe:('ldr','r0, [r5, #4]'),0xb14606:('ldr','r0, [r5, #0x14]'),
        0xb1460c:('ldr','r0, [r5, #0x28]'),0xb14610:('ldrb','r0, [r5, #2]'),
        0xb14616:('str','r5, [r3]'),
        0xb14840:('add.w','r2, sl, #8'),0xb14848:('ldm','r2, {r0, r1, r2}'),
        0xb1484a:('adds.w','fp, r2, r0'),0xb14850:('adc','r3, r1, #0'),
        0xb14856:('str','r3, [sp, #0x14]'),0xb14884:('str','r0, [sp, #0xc]'),
        0xb148c6:call(0xb15526),0xb148ca:('mov','r5, r0'),
        0xb148cc:('cmp','r5, #0'),0xb148ce:edge(0xb149b8,'beq'),
        0xb148de:('ldr','r1, [sp, #0xc]'),0xb148e0:('str','r1, [r5, #8]'),
        0xb148e2:('sub.w','fp, r0, r1'),0xb148e8:('ldr','r0, [sp, #0x14]'),
        0xb148ea:('strd','r0, fp, [r5, #0xc]'),
        0xb148ee:('ldr.w','r0, [r8, #0xc]'),0xb148f2:('str','r0, [r5, #0x14]'),
        0xb148fa:('str.w','sl, [r5, #0x20]'),0xb148fe:('str','r2, [r5, #0x28]'),
        0xb1555c:('ldr.w','r0, [r3, r1, lsl #2]'),
        0xb15560:('cbnz',f'r0, #{base+0xb15580:#x}'),
        0xb1556e:('cmp.w','r2, #0x580'),0xb15586:('str.w','r2, [r3, r1, lsl #2]'),
        0xb16c18:('ldrb','r3, [r1, #0xb]'),0xb16c1a:('ubfx','r2, r2, #0xa, #5'),
        0xb16c1e:('cmp','r2, r3'),0xb16c20:edge(0xb16c7a,'bne'),
        0xb16c28:('ldrh','sl, [r2, #0xc]!'),0xb16c2c:('cmp.w','sl, #7'),
        0xb16c3a:('tst.w','r3, #0xbe'),0xb16c42:('ldrb','r5, [r3, #8]!'),
        0xb16c46:('cmp','r5, #1'),0xb16c48:edge(0xb16c74,'bhi'),
        0xb16c4a:('ldrb','r5, [r1, #0xa]'),0xb16c4c:('cbz',f'r5, #{base+0xb16c84:#x}'),
        0xb16c4e:('movs','r0, #4'),0xb16c50:('strh','r0, [r2]'),
        0xb16c74:('subs','r0, r5, #1'),0xb16c76:('strb','r0, [r3]'),
        0xb16c84:('movs','r3, #0'),0xb16c86:('strh','r3, [r2]'),
        0xb16c88:('ldrh','r1, [r1, #0xe]'),0xb16c9c:('ldr','r0, [r0, #0x10]'),
        0xb16ca8:call(0xb1529a),0xb16cbe:call(0xb14ed6),
        0xb16cc2:('cbnz',f'r0, #{base+0xb16cde:#x}'),0xb16ce0:call(0xb1671a),
        0xb16ce8:('movs','r1, #0'),0xb16cee:('strh','r1, [r0, #0xc]'),
        0xb16cf0:('strh','r1, [r0, #8]'),
        0xb14ee0:call(0xb14ef8),0xb14ee4:('movs','r0, #0'),
        0xb14ee6:('str','r0, [r4, #0x28]'),0xb14eee:edge(0xb14f44,'b.w'),
        0xb14f2e:('strd','r1, r1, [r0, #0x40]'),
        0xb14f36:('str.w','r0, [ip, #0x44]'),0xb14f3a:('strd','ip, r1, [r0, #0x40]'),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    # Keep the shared constant helper conservative: the initialization pair
    # spans BIC, which it deliberately refuses. Its exact operands are checked
    # above; derive the reported address from the later supported pair.
    table=constant(0xb164b8,0xb164c2)
    if (table!=0x1a8c558
            or table!=constant(0xb16c06,0xb16c0e)
            or table!=int(baseline['handle_to_reply_addresses']['unit_table_pointer_link_va'],16)
            or baseline['photo_pipeline_located'] is not False):
        raise ValueError('单元初始化/分配/释放不使用已核对的表指针')
    queue={name:constant(a,b) for name,a,b in [
        ('head_pointer',0xb16686,0xb1668e),('tail_pointer',0xb1668a,0xb16692),
        ('slot_array_pointer',0xb166a8,0xb166ac)]}
    if (queue!={'head_pointer':0x1a8c55c,'tail_pointer':0x1a8c560,'slot_array_pointer':0x1a8c568}
            or constant(0xb1671e,0xb16728)!=queue['tail_pointer']
            or constant(0xb16730,0xb16734)!=queue['head_pointer']
            or constant(0xb16750,0xb16754)!=queue['slot_array_pointer']):
        raise ValueError('取出与归还槽位的队列全局位置不符')
    release=blocks[8]
    if potential_thumb_path(release,base+0xb16cbe,base+0xb16cee,
                            branch_decisions={base+0xb16cc2:True}) is None:
        raise ValueError('描述归还错误边不能连到槽位归还后的清状态存储')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'unit-slot-reuse-selected-descriptor-creation-and-release',
        'unit_slot_reuse':{
            'initialization_file_offset':'0xb16314','table_pointer_link_va':hex(table),
            'table_base_initial_expression':'align input argument 1 upward to 8 bytes',
            'static_table_layout_bytes':0xffc0,'record_stride':0x40,'last_initialized_slot':0x3fe,
            'allocation_file_offset':'0xb1645a','slot_take_file_offset':'0xb16686',
            'slot_return_file_offset':'0xb1671a','queue_globals':{k:hex(v) for k,v in queue.items()},
            'queue_cursor_wrap_value':0x3ff,'tag_byte_offset':0xb,
            'tag_update':'old <= 30: old + 1; otherwise: 1',
            'published_low_handle_fields':{'slot_bits':[0,10],'tag_bits':[10,5],'bit15':1},
            'scope':'选定布局/循环及槽位归还，不证明运行初始化成功、所有配置计数和全生命周期'},
        'descriptor_production':{
            'allocation_chain':['0xb1645a','0xb144d6','0xb14554'],
            'pointer_publish_file_offset':'0xb14520','unit_pointer_array_offset':0x10,'pointer_stride':4,
            'existing_descriptor_candidate_publish_file_offset':'0xb14616',
            'existing_candidate_checks':['class +0x24 matches','flags +4 intersect requested mask',
                                         'word +0x14 != 0','owner +0x28 == 0','byte +2 bit0 == 0'],
            'selected_new_descriptor_allocator':'0xb15526',
            'selected_new_descriptor_fields':{
                'base_pair_offset':8,'base_expression':'parent u64 +8 plus parent u32 +0x10, with carry',
                'relative_offset_offset':0x10,'relative_offset_expression':'selected aligned low value minus child base low',
                'word_offset':0x14,'word_source':'selected layout entry +0xc',
                'parent_pointer_offset':0x20},
            'unit_attachment':{'descriptor_owner_offset':0x28,'descriptor_stamp_offset':0x2c,'unit_stamp_offset':4},
            'record_count_store_file_offset':'0xb16616','record_count_offset':0xe,
            'pointer_slots_fitting_record':(0x40-0x10)//4,
            'scope':'已有描述复用候选与一条新描述构造分支；所有分裂/合并、父描述生产和配置列表界限未穷举'},
        'conditional_release':{
            'entry_file_offset':'0xb16bd6','raw_state_halfword_offset':0xc,
            'selected_state_mask':0xbe,'byte8_greater_than_one':'decrement byte8, without entering descriptor loop',
            'byte8_at_most_one_and_byteA_nonzero':'store state 4 and clear selected reference bytes',
            'byte8_at_most_one_and_byteA_zero':'store state 0; process descriptor pointers, then return slot',
            'descriptor_return_file_offset':'0xb14ed6','descriptor_return_chain':['0xb14ef8','0xb14f44'],
            'direct_descriptor_owner_clear_offset':0x28,'descriptor_list_link_offsets':[0x40,0x44],
            'descriptor_return_nonzero_potential_edge':['0xb16cc2','0xb16cde','0xb16ce0','0xb16cee'],
            'scope':'非零归还返回也有通向槽位归还/清状态的可见边，不宣称完整回滚或全部释放成功'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '同槽位或同地址不证明同一拍摄实例；代号有限循环也不能单独保证永不复用',
            '父描述地址、全部描述变更/分裂/合并以及运行地址空间仍未证',
            '记录内可容纳 12 个指针不证明所有配置列表/运行计数都受此上界约束',
            '只定位选定归还调用与存储；失败副作用、并发、引用与完整生命周期未穷举',
            'DMM 单元句柄的位 15/代号不能解释 VFX 位 31 或证明两者相同',
            '格式 3/4 有效传输、LUT 输出与 MAIN 身份、照片使能及色彩仍未证'],
        'unit_slot_reuse_path_located':True,'unit_tag_wrap_located':True,
        'descriptor_creation_fields_located':True,'conditional_release_path_located':True,
        'all_descriptor_lists_bounded_to_record_verified':False,'unit_descriptor_allocation_lifecycle_verified':False,
        'register_bit_semantics_verified':False,'hardware_control_cache_coherence_verified':False,
        'all_control_writers_and_intervening_effects_verified':False,
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
    parser.add_argument('--cp',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        raw=(json.dumps(trace(args.cp),ensure_ascii=False,indent=2)+'\n').encode()
        write_bytes_new(args.output,raw);print(raw.decode(),end='');return 0
    except (ValueError,OSError,ImportError) as exc:
        parser.exit(1,f'STOPPED: {exc}\n')


if __name__=='__main__':
    raise SystemExit(main())
