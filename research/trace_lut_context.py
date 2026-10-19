"""Read-only category configuration provenance and User3D submission shape.

No device I/O, firmware execution, pixel/enable claim or complete device
parameters. Reports selected static fields and submission relationships only.
"""
import argparse
import json
from pathlib import Path

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_dispatch import copied_fields
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_selection import trace as trace_selection
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp')
    base=boot_base(cp)
    baseline=trace_selection(cp_path)
    ranges=[(0x3b61a4,0x3b6596),(0xa25db4,0xa25dbe),
            (0xa26140,0xa26168),(0xa26656,0xa2666c),(0xa26bce,0xa26be6),
            (0x44615c,0x446380),(0xa71576,0xa71632),(0xa7b282,0xa7b36c)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(target):return ('bl',f'#{base+target:#x}')
    require_instructions(index,{
        0x3b61ae:('mov','fp, r0'), 0x3b61b0:call(0xa25db4),
        0x3b61b4:('ldr','r0, [r0, #0xc]'),
        0x3b61b6:('ldr.w','r4, [r0, #0x698]'),
        0x3b61be:('cbz',f'r4, #{base+0x3b61f0:#x}'),
        0x3b61c0:('ldr','r0, [r0, #0x2c]'), 0x3b61c4:('ldrb','r0, [r0, #1]'),
        0x3b61d4:('beq',f'#{base+0x3b61f0:#x}'),
        0x3b61de:('ldrb','r0, [r0, #0x16]'),
        0x3b61e0:('lsls','r0, r0, #0x1e'),
        0x3b61e2:('bmi',f'#{base+0x3b61f0:#x}'),
        0x3b61e4:call(0xa25db4), 0x3b61e8:('ldr','r0, [r0, #0xc]'),
        0x3b61ea:('add.w','r8, r0, #0x20'),
        0x3b61ee:('b',f'#{base+0x3b61fa:#x}'),
        0x3b61f0:call(0xa25db4), 0x3b61f4:('ldr','r0, [r0, #0xc]'),
        0x3b61f6:('add.w','r8, r0, #0x630'),
        0x3b657a:('add.w','r2, r8, #0x74'),
        0x3b657e:('movw','r1, #0x14fc'),
        0x3b6582:('ldm.w','r2, {r3, r4, r5, r6}'),
        0x3b6586:('add','r1, fp'),
        0x3b658c:('stm','r1!, {r3, r4, r5, r6}'),
        0xa25dbc:('bx','lr'),
        0xa26664:('mov','r0, r4'), 0xa26666:('mov','r1, r8'),
        0xa26668:call(0xa268e0),
        0xa26be0:('addw','r2, r0, #0xe18'),
        0xa26be4:('str','r2, [r1, #0xc]'),
        0x446234:('add','r1, sp, #0x34'),
        0x446170:('mov','sb, r2'),
        0x446238:call(0xaac2da),
        0x4462c6:('movs','r0, #1'),
        0x4462ca:('strd','r0, r0, [sp, #0x10]'),
        0x4462ce:('strd','r0, r0, [sp, #0x18]'),
        0x4462d2:('strd','r0, r0, [sp, #0x20]'),
        0x44632c:('ldr','r0, [sp, #0x34]'),
        0x446342:('add','r1, sp, #0x10'), 0x446344:('mov','r2, sb'),
        0x446346:call(0xa71576),
        0xa71584:('mov','sb, r1'), 0xa71586:('mov','r5, r0'),
        0xa7158a:('mov','r6, r2'),
        0xa715be:('cmp','r5, #7'), 0xa715c0:('blo',f'#{base+0xa715d8:#x}'),
        0xa715d8:('movs','r0, #2'), 0xa715da:('str','r0, [sp, #0x10]'),
        0xa715dc:('movs','r0, #0x1e'),
        0xa715de:('add','r1, sp, #0x14'),
        0xa715e0:('stm','r1!, {r0, r5, r6}'),
        0xa715ea:('str','r0, [sp, #0x20]'),
        0xa715f6:('ldm.w','sb, {r1, r2, r3, r4, r5, r6}'),
        0xa715fa:('stm','r0!, {r1, r2, r3, r4, r5, r6}'),
        0xa715fc:('mov','r0, r8'), 0xa715fe:call(0xa7b282),
        0xa7b290:('mov','sb, r0'), 0xa7b292:('add','r1, sp, #0xc'),
        0xa7b294:('movs','r2, #0x38'), 0xa7b296:('movs','r3, #0'),
        0xa7b29e:('mov','r0, r8'), 0xa7b2a0:call(0x45d204),
        0xa7b2b0:('mov','r1, sb'), 0xa7b2b2:('ldr','r0, [sp, #0xc]'),
        0xa7b2b4:('ldm','r1!, {r2, r3, r4, r6}'),
        0xa7b2b6:('stm','r0!, {r2, r3, r4, r6}'),
        0xa7b2b8:('ldm','r1!, {r2, r3, r4, r5, r6}'),
        0xa7b2ba:('stm','r0!, {r2, r3, r4, r5, r6}'),
        0xa7b2bc:('ldm.w','r1, {r2, r3, r4, r5, r6}'),
        0xa7b2c0:('stm','r0!, {r2, r3, r4, r5, r6}'),
        0xa7b2ec:('ldr','r1, [sp, #0xc]'), 0xa7b2ee:('mov','r0, r8'),
        0xa7b2f0:call(0x45cb38),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    context=constant(0xa25db4,0xa25db8)
    bound_context=constant(0xa26656,0xa2665e)
    root=constant(0xa26154,0xa2615e)
    request_id=constant(0xa715e2,0xa715e6)
    common_id=constant(0xa7b28c,0xa7b29a)
    if (context,bound_context,root,request_id,common_id)!=(0x173efe8,0x173efe8,0x172fe50,0x2ae085a,0x2ae085a):
        raise ValueError('配置绑定或公共提交标识不符')
    # Callee-saved register identity, not source-memory or full side-effect proof.
    for ins in blocks[0]:
        if base+0x3b61fa <= ins.address < base+0x3b6582:
            if any(ins.reg_name(reg)=='r8' for reg in ins.regs_access()[1]):
                raise ValueError('选定配置指针在复制前被重新设置')
    field=copied_fields(0x74,0x14fc,0x10,0,[('category',0x78,4)])[0]
    if field['object_offset']!=baseline['request_selection']['context_category_offset']:
        raise ValueError('配置块类别字段不能连接上一轮类别读取')
    root_offsets=[0xe18+branch+0x78 for branch in (0x20,0x630)]
    if root_offsets!=[0xeb0,0x14c0] or any(offset < 0xd64 for offset in root_offsets):
        raise ValueError('类别配置来源或初始 LUT 快照边界不符')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'category-config-copy-and-user3d-submission-descriptor',
        'category_provenance':{
            'consumer_context_offset':0x1500,'config_copy_entry_file_offset':'0x3b61a4',
            'global_context_link_va':hex(context),'bound_root_link_va':hex(root),
            'binding_store_file_offset':'0xa26be4','binding_offset_in_global_context':0xc,
            'bound_subobject_root_offset':0xe18,'selected_input_subobject_offsets':[0x20,0x630],
            'raw_selection_fields':['bound subobject +0x698','global context +0x2c pointer byte +1',
                                    'global 0x1a533a4 +0x16 bit 1'],
            'copy_source_offset':0x74,'copy_destination_offset':0x14fc,'copy_bytes':0x10,
            'category_offset_in_selected_input':0x78,'field_mapping':field,
            'category_source_root_offsets':root_offsets,
            'category_source_initial_link_vas':[hex(root+offset) for offset in root_offsets],
            'initial_lut_snapshot_copy_bytes_from_prior_round':0xd64,
            'category_inside_that_initial_copy':False,
            'scope':'条件式初始绑定与字段复制；配置写入者、运行分支、所有别名/刷新副作用未证'},
        'user3d_configuration_submission':{
            'api_file_offset':'0x44615c','config_call_file_offset':'0x446346',
            'config_builder_file_offset':'0xa71576','accepted_logical_contexts':[0,6],
            'selected_configuration_word_count':6,'initial_configuration_words_all_equal':1,
            'descriptor_kind':2,'descriptor_argument':0x1e,
            'descriptor_logical_context_offset':8,'descriptor_callback_offset':0xc,
            'descriptor_selected_configuration_offset':0x1c,
            'common_submit_file_offset':'0xa7b282','submission_id':hex(request_id),
            'request_buffer_call_file_offset':'0xa7b2a0','request_buffer_api_file_offset':'0x45d204',
            'request_buffer_bytes':0x38,'copy_word_groups':[4,5,5],
            'submit_call_file_offset':'0xa7b2f0','submit_api_file_offset':'0x45cb38',
            'scope':'相关成功分支构造并提交固定描述；接收者、硬件消费/使能和像素处理未证'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'limitations':[
            '类别来自两种配置子区，不能凭偏移/条件数值命名照片或视频分支',
            '初始绑定地址与读取关系不证明运行时选择、配置值或对象生命周期',
            '类别来源位于先前 0xd64 LUT 初始复制之外，不可由 LUT 刷新复制推定类别刷新',
            '保存寄存器不等于所有被调函数/别名对来源内存无副作用',
            '六个配置字为 1 及描述种类 2 不直接等于实际硬件使能',
            '尚未定位句柄位 31 的业务消费，未连接 MAIN/有效像素/色彩条件'],
        'category_config_copy_and_binding_located':True,
        'category_outside_initial_lut_snapshot_located':True,
        'user3d_configuration_submission_located':True,
        'runtime_context_category_verified':False,'config_source_all_effects_verified':False,
        'handle_bit31_semantics_verified':False,'submission_hardware_consumption_verified':False,
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
