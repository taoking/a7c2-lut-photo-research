"""Read-only capture-helper branch constraints and module initialization.

Explicit pointer paths are bounded observations, not a whole-program alias,
asynchronous effect or runtime buffer-preservation proof. No device access.
"""
import argparse
import json
from pathlib import Path

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_capture_buffers import trace as trace_buffers
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_refresh import potential_thumb_path
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp')
    base=boot_base(cp)
    baseline=trace_buffers(cp_path)
    # The helper contains an inline data island, not a contiguous code region.
    ranges=[(0x382bd8,0x383a14),(0x383aa0,0x384328),
            (0x37845c,0x378538),(0x378540,0x3785e0),(0x378648,0x3786e8),
            (0x37e0a4,0x37e0c8),(0x37e302,0x37e376),
            (0x37e3ce,0x37e4cc),(0xa0b72e,0xa0b748),
            (0x37951a,0x37959a),(0xa09faa,0xa0a036),
            (0xa0b7a2,0xa0b7a8),(0xa0b7c0,0xa0b7c6)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={ins.address:ins for block in blocks for ins in block}
    def call(target):return ('bl',f'#{base+target:#x}')
    require_instructions(index,{
        0x382be2:('mov','r5, r1'), 0x382be6:('mov','fp, r3'),
        0x382bea:('tst.w','r5, #1'),
        0x382bf2:('str','r5, [sp, #0x20]'),
        0x382bf4:('bne.w',f'#{base+0x382f50:#x}'),
        0x382c9e:('lsls','r0, r5, #0x19'),
        0x382ca0:('bpl.w',f'#{base+0x3832ea:#x}'),
        0x382ccc:('ldr.w','r3, [fp, #0x1c8]'),
        0x382fb0:('str.w','fp, [sp, #0x24]'),
        0x382fd8:('movw','fp, #0x67ac'),
        0x383280:('ldr','r0, [sp, #0x24]'),
        0x383288:('strd','r0, r6, [sp]'), 0x383294:call(0x37845c),
        0x3832ea:('ldr.w','fp, [sp, #0x20]'),
        0x384278:('ldrd','r5, fp, [sp, #0x20]'),
        0x38427e:('bne.w',f'#{base+0x382bf8:#x}'),
        0x3842f8:('b.w',f'#{base+0x382bf8:#x}'),
        0x37845c:('push','{r4, r5, r6, r7, lr}'),
        0x37845e:('add','r7, sp, #0xc'),
        0x378492:('ldrd','sb, sl, [r7, #8]'),
        0x3784e0:('add.w','r0, sb, #0x6c'),
        0x3784e4:('str','r0, [sp, #0x1c]'),
        0x3784f8:('add.w','r0, sb, #0xd8'),
        0x3784fc:('str','r0, [sp, #0xc]'),
        0x378510:('add','r1, sp, #0x1c'),
        0x378512:('add','r2, sp, #0xc'), 0x378516:call(0x378648),
        0x3785ba:call(0x43f404),
        0x378652:('mov','r6, r1'), 0x378654:('mov','r5, r2'),
        0x37867a:('ldr','r3, [r6]'),
        0x378680:('str.w','ip, [r3]'), 0x378688:('str','r4, [r3, #8]'),
        0x37868c:('str.w','lr, [r3]'), 0x378692:('str','r4, [r3, #4]'),
        0x3786aa:('ldr','r6, [r5]'),
        0x3786b8:('str','r2, [r6]'), 0x3786be:('str','r4, [r6, #8]'),
        0x3786c2:('str','r3, [r6]'), 0x3786c6:('str','r4, [r6, #4]'),
        0x37e0ae:('mov','r8, r0'), 0x37e0b4:('mov','r6, r1'),
        0x37e0c2:call(0x37377c), 0x37e0c6:('mov','sl, r0'),
        0x37e302:('lsls','r0, r6, #0x1a'),
        0x37e304:('bmi',f'#{base+0x37e316:#x}'),
        0x37e316:('movs','r0, #1'), 0x37e31a:call(0xa0b72e),
        0x37e31e:('mov','r4, r0'), 0x37e370:('str','r4, [sp, #0x14]'),
        0x37e4ba:('ldr','r1, [sp, #0x14]'),
        0x37e4bc:('movw','r0, #0x5bdc'),
        0x37e4c0:('str.w','r1, [r8, r0]'),
        0x37e4c4:('movw','r0, #0x5be0'),
        0x37e4c8:('str.w','sl, [r8, r0]'),
        0xa0b736:('cmp','r0, #0'),
        0xa0b740:('it','eq'), 0xa0b742:('moveq','r1, r2'),
        0xa0b744:('mov','r0, r1'), 0xa0b746:('bx','lr'),
        0x379540:call(0xa09faa), 0x37955c:('movs','r1, #7'),
        0x379560:('str.w','r1, [r0, #0x12c]'),
        0x379582:call(0xa09faa), 0x379586:('movs','r1, #9'),
        0x37958a:('str.w','r1, [r0, #0x12c]'),
        0xa0a034:('bx','lr'),
        0xa0b7a2:('strd','r1, r2, [r0]'), 0xa0b7a6:('bx','lr'),
        0xa0b7c0:('movs','r1, #0'), 0xa0b7c2:('str','r1, [r0, #4]'),
        0xa0b7c4:('bx','lr'),
    },base)
    flags=baseline['capture_stage']['flags_at_this_call']
    if flags!=0x2b:
        raise ValueError('调用标志不符，不能沿用本轮边界')
    graph=blocks[0]+blocks[1]
    decisions={base+0x382bf4:bool(flags & 1),
               base+0x382ca0:not bool(flags & (1 << (31-0x19)))}
    targets=(0x382ccc,0x383280,0x383294)
    paths=[]
    for target in targets:
        unconstrained=potential_thumb_path(graph,base+0x382bd8,base+target,allow_gaps=True)
        constrained=potential_thumb_path(graph,base+0x382bd8,base+target,
                                         allow_gaps=True,branch_decisions=decisions)
        if unconstrained is None or constrained is not None:
            raise ValueError('配置指针路径与显式标志约束不符')
        paths.append({'target_file_offset':hex(target),
                      'unconstrained_path_exists':True,
                      'path_under_supplied_flag_decisions':False})
    all_ins=list(index.values())
    def constant(first,last):return movw_movt_value(all_ins,base+first,base+last)
    selected=constant(0xa0b732,0xa0b73c)
    alternate=constant(0xa0b72e,0xa0b738)
    initialized=[constant(0x379534,0x37953c),constant(0x379576,0x37957e)]
    if initialized!=[alternate,selected] or selected!=0x1a4e6a4:
        raise ValueError('模块选择地址与初始化对象不一致')
    # This base constructor has no calls and never changes the object in r0.
    base_constructor=blocks[10]
    if any(i.mnemonic.split('.')[0] in ('bl','blx') or
           any(i.reg_name(reg)=='r0' for reg in i.regs_access()[1])
           for i in base_constructor):
        raise ValueError('基础构造函数不再能确认返回原对象指针')
    writes=sorted({anchor+offset for anchor in (0x6c,0xd8) for offset in (0,4,8)})
    candidate=(0xf0,0xf8)
    overlap=any(start<candidate[1] and start+4>candidate[0] for start in writes)
    if overlap:
        raise ValueError('已知准备写入与候选地址意外重叠')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'bounded-explicit-pointer-paths-and-module-initialization',
        'helper_effect_scope':{
            'entry_file_offset':'0x382bd8','flags_at_current_call':flags,
            'input_config_register':'r3 -> fp; saved at local stack +0x24',
            'config_consuming_gate':{'shift_left':0x19,'tested_mask':0x40,
                                   'branch_file_offset':'0x382ca0','taken_at_0x2b':True},
            'checked_paths':paths,
            'assumptions':['两处条件决策由已核对的调用标志和寄存器保持/重载提供',
                           '调用按可返回处理；不求解其余条件，不跟踪被调函数或异步别名'],
            'excluded_inline_data_file_range':['0x383a14','0x383aa0']},
        'potential_writes_when_0x40_enabled':{
            'wrapper_file_offset':'0x37845c','preparer_file_offset':'0x378648',
            'first_channel_pointer':'saved input configuration',
            'preparer_word_offsets_in_config':writes,'write_bytes':4,
            'candidate_address_range':list(candidate),
            'known_preparer_writes_overlap_candidate':overlap,
            'further_driver_call_file_offset':'0x3785ba','further_driver_file_offset':'0x43f404',
            'scope':'仅列出第一项指针对应的潜在显式写入；不外推下层接口或间接别名'},
        'capture_module_initialization':{
            'selection_function_file_offset':'0x37e0a4','enable_mask':0x20,
            'getter_file_offset':'0xa0b72e','getter_argument':1,
            'selected_object_link_va':hex(selected),'alternate_object_link_va':hex(alternate),
            'work_module_pointer_offset':0x5bdc,'work_companion_value_offset':0x5be0,
            'companion_source_function_file_offset':'0x37377c',
            'initial_selector_offset':0x12c,'selected_initial_value':9,'alternate_initial_value':7,
            'initializer_write_file_offset':'0x37958a',
            'selected_channel_api_arguments':[2,3,4,5],
            'basis':'已核对初始化、非零选择、存槽及第九轮四通道分派；不等于已运行'},
        'limitations':[
            '有界显式路径排除不等于全部调用、别名或异步副作用已审计',
            '0x40 分支存在可写准备入口，但当前 0x2b 调用不进入该显式路径',
            '已知准备写入不覆盖候选双字，不代表整个查询回复始终不变',
            '模块初始选择值 9 不等于相机模式，也未验证运行时是否改写',
            '候选输出角色、用户 LUT 接入、MAIN 同一实例/缓冲及色彩条件仍有缺口'],
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'explicit_0x40_config_paths_excluded_at_0x2b':True,
        'capture_module_initial_selection_linked':True,
        'query_address_preserved_across_all_calls_verified':False,
        'runtime_module_selector_verified':False,
        'capture_vfx_uses_user_lut_verified':False,
        'lut_output_to_main_input_connected':False,'buffer_identity_and_lifetime_verified':False,
        'full_resolution_dimensions_verified':False,'color_format_enum_verified':False,
        'ap_to_cp_runtime_verified':False,'photo_pipeline_located':False,
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
