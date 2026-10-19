"""Read-only cached channel control writers and native preparation branches.

Conditional static evidence only; no firmware execution, hardware success,
complete device parameters, pixel path or camera commands.
"""
import argparse
import json
from pathlib import Path

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_capture_buffers import bounded_tbb_targets
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_gate import trace as trace_gate
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_refresh import potential_thumb_path
from research.trace_lut_snapshot import movw_movt_value


def trace(cp_path):
    cp=read_original(cp_path,'cp');base=boot_base(cp)
    baseline=trace_gate(cp_path)
    ranges=[(0xaa8a02,0xaa8a4e),(0xaa8b3e,0xaa8c78),(0xaa97dc,0xaa98b4),
            (0xaac28c,0xaac2da),(0xaaea40,0xaaea5a),(0xaabbda,0xaabc02),
            (0x446de0,0x446df0),(0x446df8,0x446e18),
            (0xaaa266,0xaaa2aa),(0xaab210,0xaab256),
            (0xaaabca,0xaaae6c),(0x3e076c,0x3e0970),
            (0xaac36a,0xaac39e),(0xaaa074,0xaaa0d2),(0xaab99a,0xaab9aa),
            (0xaaa062,0xaaa074)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    def call(t):return ('bl',f'#{base+t:#x}')
    def branch(t,m='beq'):return (m,f'#{base+t:#x}')
    require_instructions(index,{
        0xaa8a06:('movs','r2, #0'),0xaa8a0c:('str.w','r2, [r1, r0, lsl #2]'),
        0xaa8a18:('str.w','r2, [r1, r0, lsl #2]'),
        0xaa8a24:('str.w','r2, [r1, r0, lsl #2]'),0xaa8a28:('bx','lr'),
        0x446de4:('cmp','r0, #6'),0x446de6:branch(0x446e16,'bhi'),
        0x446de8:('movs','r4, #1'),0x446dea:('movs','r5, #0'),
        0x446dec:('tbb','[pc, r0]'),0x446df8:('uxtb','r4, r0'),
        0x446dfa:('mov','r5, r0'),0x446dfe:('movs','r4, #3'),
        0x446e00:('movs','r5, #0'),0x446e04:('movs','r4, #3'),
        0x446e06:('movs','r5, #2'),0x446e0a:call(0xaa8a02),
        0x446e0e:('adds','r5, #1'),0x446e10:('uxtb','r0, r5'),
        0x446e12:('cmp','r0, r4'),0x446e14:branch(0x446e0a,'bls'),
        0xaaa268:call(0x4458d8),0xaaa26e:('cbnz',f'r5, #{base+0xaaa2ce:#x}'),
        0xaaa270:('cmp','r4, #6'),0xaaa272:branch(0xaaa2cc,'bhi'),
        0xaaa296:('mov','r0, r4'),0xaaa298:call(0x446de0),
        0xaab214:call(0x4458d8),0xaab21a:('cbnz',f'r5, #{base+0xaab27a:#x}'),
        0xaab21c:('cmp','r4, #6'),0xaab21e:branch(0xaab278,'bhi'),
        0xaab242:('mov','r0, r4'),0xaab244:call(0x446de0),
        0xaa97e6:('mov','r4, r1'),0xaa980a:('ldr.w','r0, [r0, r4, lsl #2]'),
        0xaa9870:('mov.w','r3, #0x1100'),0xaa9882:('str','r1, [sp, #4]'),
        0xaa9884:('ldr','r1, [sp, #4]'),0xaa9886:('str','r1, [r0, r3]'),
        0xaa988a:('str.w','r1, [r6, r4, lsl #2]'),
        0xaaea56:('b.w',f'#{base+0xaa97dc:#x}'),
        0xaac29a:('mov','r8, r1'),0xaac29c:('mov','r4, r0'),
        0xaac2aa:('cmp','r4, #2'),0xaac2ac:branch(0xaac2ce,'bne'),
        0xaac2c6:('mov','r0, r5'),0xaac2c8:('mov','r1, r8'),
        0xaac2ca:call(0xaaea56),
        0xaa8b40:('movs','r2, #0'),0xaa8b42:('mov.w','ip, #0x1100'),
        0xaa8b46:('str','r2, [sp]'),0xaa8c3c:('ldr','r0, [r0, #0x68]'),
        0xaa8c44:('bfi','r2, r0, #0x1c, #1'),
        0xaa8c58:('str.w','r2, [r0, ip]'),
        0xaa8c5e:('str.w','r2, [r3, r1, lsl #2]'),
        0xaa8a2e:('mov','r4, r1'),0xaa8a30:('mov','r5, r0'),
        0xaa8a40:('add.w','r0, r5, #0x264'),0xaa8a44:('mov','r1, r4'),
        0xaa8a4a:('b.w',f'#{base+0xaa8b3e:#x}'),
        0xaabbe8:('mov','r0, r4'),0xaabbea:call(0xaaa11e),
        0xaabbee:('cmp','r0, #0'),0xaabbf4:('movne','r0, #1'),
        0xaabbf6:('str','r0, [sp, #0x2cc]'),
        0xaabbf8:('mov','r0, sp'),0xaabbfa:call(0xaaea40),
        0xaaea44:('mov','r4, r1'),0xaaea46:call(0xaa8a2a),
        0x3e07b8:('ldr.w','r0, [sb]'),0x3e07bc:('cmp','r0, #1'),
        0x3e07be:branch(0x3e0818,'bne'),0x3e0818:('add','r0, sp, #0x30'),
        0x3e081a:call(0xaaabca),0x3e081e:('mov','r5, r0'),
        0x3e0840:('cbz',f'r5, #{base+0x3e0866:#x}'),
        0x3e0866:('movs','r0, #1'),0x3e0868:('str.w','r0, [sb]'),
        0xaaabd4:('mov','sb, r0'),0xaaabf6:('ldr.w','r1, [sb]'),0xaaac00:call(0x445788),
        0xaaac18:call(0x445788),0xaaac2e:('ldr','r6, [sp, #0x60]'),
        0xaaac4c:call(0xaac2da),0xaaac54:call(0xaaadd6),
        0xaaac5a:('cbz',f'r5, #{base+0xaaaca4:#x}'),
        0xaaac5c:('cmp','r5, #8'),0xaaac5e:branch(0xaaacdc,'bne'),
        0xaaac74:call(0x446914),0xaaac7c:branch(0xaaad00),
        0xaaaca6:call(0xaaae22),0xaaacaa:('cmp','r0, #0'),
        0xaaacac:branch(0xaaad38),0xaaacc2:call(0x446914),
        0xaaacca:branch(0xaaad56),0xaaad0e:call(0xaac302),
        0xaaad20:call(0xa70794),0xaaad26:branch(0xaaacae),
        0xaaad3a:call(0xa70b0a),0xaaad42:('cbz',f'r1, #{base+0xaaadb8:#x}'),
        0xaaadb8:call(0xa70990),0xaaadbc:('cmp','r0, #0'),
        0xaaadbe:branch(0xaaacae,'beq.w'),0xaaad64:call(0xaac34a),
        0xaaad74:('ldr','r0, [sp, #0x5c]'),0xaaad94:call(0xa713f0),
        0xaaad9c:call(0xa714f4),0xaaada4:call(0xa71472),
        0xaaada8:('ldr.w','r0, [sb]'),0xaaadb4:('str','r0, [r1]'),
        0xaaadee:call(0x446914),0xaaae04:call(0xaab99a),
        0xaaae08:('cmp','r0, #1'),0xaaae0a:branch(0xaaae1c,'bne'),
        0xaaae18:('movs','r0, #0'),0xaaae1c:('movs','r0, #8'),
        0xaaae3a:call(0x446914),0xaaae50:call(0xaac36a),
        0xaaae54:('cbz',f'r0, #{base+0xaaae66:#x}'),
        0xaaae62:('movs','r0, #0'),0xaaae66:('movs','r0, #8'),
        0xaac380:call(0xaaa074),0xaac386:('cbz',f'r0, #{base+0xaac398:#x}'),
        0xaac38a:('cbz',f'r0, #{base+0xaac398:#x}'),
        0xaac38e:('cbz',f'r0, #{base+0xaac398:#x}'),
        0xaac392:('cbz',f'r0, #{base+0xaac398:#x}'),
        0xaaa086:('movw','r2, #0x10fc'),0xaaa08a:('ldr','r1, [r1, r2]'),
        0xaaa090:('and','r1, r1, #3'),0xaaa098:('ubfx','r1, r1, #4, #1'),
        0xaaa0a0:('ubfx','r1, r1, #8, #1'),0xaaa0a8:('ubfx','r1, r1, #0xc, #1'),
        0xaab99e:call(0xaaa062),0xaaa06a:('ldr.w','r0, [r1, r0, lsl #2]'),
        0xaaa06e:('ubfx','r0, r0, #0x15, #1'),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    cache=constant(0xaa8a10,0xaa8a14)
    default=constant(0xaa987a,0xaa987e)
    if (hex(cache)!=baseline['post_submission_control']['software_cache_link_va']
            or constant(0xaa9866,0xaa986a)!=cache
            or constant(0xaa8c38,0xaa8c40)!=cache
            or constant(0xaaa062,0xaaa066)!=cache
            or default!=0x10100169 or (default>>28)&1!=1
            or constant(0x3e07b0,0x3e07b4)!=0x1a6aefc
            or constant(0xaaadac,0xaaadb0)!=0x1a7e608):
        raise ValueError('缓存、固定初值或原生调度状态地址不符')
    targets=bounded_tbb_targets(cp[0x446df0:0x446df7],0x446df0,len(cp))
    if (targets!=(0x446df8,)*4+(0x446dfe,0x446e10,0x446e04)
            or any(base+t not in index for t in targets)):
        raise ValueError('释放缓存范围分发不符')
    # Potential witnesses use explicitly supplied raw branch outcomes, not a
    # predicate solver or proof that calls return these values on a camera.
    windows={a:block for (a,_),block in zip(ranges,blocks)}
    preparation=windows[0xaaabca]
    decisions=[
        {0xaaac5a:True,0xaaacac:False,0xaaacca:True,0xaaad60:False},
        {0xaaac5a:True,0xaaacac:True,0xaaad42:True,0xaaadbe:True,
         0xaaacca:True,0xaaad60:False},
        {0xaaac5a:False,0xaaac5e:False,0xaaac7c:True,0xaaad0a:False,
         0xaaad1c:False,0xaaad26:True,0xaaacca:True,0xaaad60:False},
    ]
    for edges in decisions:
        if potential_thumb_path(preparation,base+0xaaac52,base+0xaaad64,
                                branch_decisions={base+a:v for a,v in edges.items()}) is None:
            raise ValueError('所记原始条件不能构成清零的潜在路径')
    if potential_thumb_path(windows[0x3e076c],base+0x3e07b8,base+0x3e081a,
                            branch_decisions={base+0x3e07be:True}) is None:
        raise ValueError('原生调度状态分支不能连接准备入口')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'cache-release-default-rebuild-and-native-prepare-conditions',
        'cache_writers':{
            'software_cache_link_va':hex(cache),
            'cache_only_zero_entry_file_offset':'0xaa8a02',
            'route_range_wrapper_file_offset':'0x446de0',
            'release_call_file_offsets':['0xaaa298','0xaab244'],
            'route_channel_ranges':baseline['post_submission_control']['route_to_inclusive_channel_ranges'],
            'zero_helper_writes_mmio':False,
            'fixed_default_entry_file_offset':'0xaa97dc','fixed_default_word':default,
            'fixed_default_bit28':(default>>28)&1,'default_constructor_file_offset':'0xaac28c',
            'default_constructor_kind_condition':2,
            'full_control_writer_file_offset':'0xaa8b3e','full_control_starts_from':0,
            'full_control_bit28_source_offset':0x68,
            'scope':'释放清缓存、条件式固定初值及整字重建；不证明硬件状态或运行执行顺序'},
        'cached_bit_reapplication':{
            'cached_reader_call_file_offset':'0xaabbea',
            'local_source_word_offset':0x2cc,'apply_call_file_offset':'0xaabbfa',
            'apply_chain':['0xaaea40','0xaa8a2a','0xaa8b3e'],
            'control_substructure_offset':0x264,'bit28_source_offset':0x68,
            'scope':'0x264+0x68=0x2cc 的选定字段连接；所有别名/被调副作用和并发未证'},
        'native_preparation':{
            'dispatch_file_offset':'0x3e076c','raw_state_link_va':'0x1a6aefc',
            'call_file_offset':'0x3e081a','state_condition':'state word != 1 after earlier guards',
            'entry_file_offset':'0xaaabca','handle_route_resolver':'0x445788',
            'cached_bit21_check':'0xaaadd6','live_status_check':'0xaaae22',
            'live_status_register_offset':0x10fc,'selected_live_fields':[[0,2],[4,1],[8,1],[12,1]],
            'live_check_returns_zero_when':'all four selected fields nonzero on every selected channel',
            'clear_call_file_offset':'0xaaad64',
            'potential_clear_conditions':[
                'cached check == 0; live check != 0; range resolution succeeds',
                'cached check == 0; live check == 0; a70b0a and a70990 return 0; range resolution succeeds',
                'cached check == 8; per-channel bit21 constructor; a70794 returns 0; range resolution succeeds'],
            'potential_branch_witnesses':[{hex(a):v for a,v in edges.items()} for edges in decisions],
            'later_calls':['0xa70fda','0xa7105e','0xa710e2','0xa713f0','0xa714f4','0xa71472'],
            'handle_store_link_va':'0x1a7e608',
            'scope':'只核对原始分支和潜在路径；未命名空闲/完成状态，也未证明三种条件真实满足'},
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'excluded_tbb_data_and_padding':['0x446df0','0x446df8'],
        'limitations':[
            '固定初值也置第 28 位，不能从缓存位为 1 推导 User3D 已运行',
            '释放仅清软件缓存的例程不能视为硬件位也已清零，外围释放还有其他副作用',
            '整字重建与缓存保留路径并存，尚未穷举所有写者、别名或并发',
            '第 28 位功能名/极性仍未证，不直接命名照片 LUT 使能',
            '三条潜在清零路径不证明返回值、时序、终止或真实相机执行',
            '原生准备不是前轮配置队列完成/整帧同步的证明',
            '运行类别、句柄位 31、有效像素、MAIN 和色彩条件仍缺证据'],
        'release_cache_zeroing_located':True,'alternative_bit28_writers_located':True,
        'cached_bit_reapplication_located':True,'native_prepare_clear_branches_located':True,
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
    parser.add_argument('--cp',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        raw=(json.dumps(trace(args.cp),ensure_ascii=False,indent=2)+'\n').encode()
        write_bytes_new(args.output,raw);print(raw.decode(),end='')
        return 0
    except (ValueError,OSError,ImportError) as exc:
        parser.exit(1,f'STOPPED: {exc}\n')


if __name__=='__main__':
    raise SystemExit(main())
