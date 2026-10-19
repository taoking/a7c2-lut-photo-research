"""Read-only capture-buffer slots and a separate VFX request constructor.

Matching field locations are static evidence, not object/lifetime identity.
No firmware execution, complete device payload or camera operations.
"""
import argparse
import json
from pathlib import Path

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_pixel_parameters import trace as trace_pixels


def bounded_tbb_targets(entries, table_offset, image_size):
    """Resolve supplied TBB bytes relative to their architectural table base.

    Caller must establish the instruction, index bound and table location.
    Reject targets in the table/padding or outside the image. Returned offsets
    still require independent code-boundary checks; this is not CFG discovery.
    """
    if not isinstance(entries, (bytes, bytearray)) or not 1 <= len(entries) <= 256:
        raise ValueError('需要 1–256 字节的有界 TBB 表')
    if (type(table_offset) is not int or type(image_size) is not int
            or not 0 <= table_offset < image_size <= 0x100000000
            or table_offset % 2):
        raise ValueError('TBB 表基址/映像范围无效')
    code_min = (table_offset + len(entries) + 1) & ~1
    if code_min > image_size:
        raise ValueError('TBB 表被映像边界截断')
    targets = tuple(table_offset + 2 * value for value in entries)
    if any(target < code_min or target + 2 > image_size for target in targets):
        raise ValueError('TBB 目标落在表/填充或映像范围之外')
    return targets


def trace(cp_path):
    cp = read_original(cp_path, 'cp')
    base = boot_base(cp)
    baseline = trace_pixels(cp_path)
    # Inline TBB tables are deliberately excluded from instruction decoding.
    ranges = [(0x36c70c,0x36c77c),(0x36c79e,0x36c810),
              (0xa05122,0xa05192),(0x37efb0,0x37efee),(0x37f0ec,0x37f152),
              (0x3816c4,0x38171c),(0x38171c,0x381790),
              (0x3818b8,0x38193a),(0x3819dc,0x381a90),
              (0x381b1a,0x381b24),(0x381df2,0x381e0a),
              (0x381e80,0x381ea4),(0x381f3e,0x381f6c),
              (0x384354,0x38436e),(0x3843e2,0x384434),
              (0x384434,0x3844ac),(0x3844ac,0x38455a),
              (0x38469a,0x3846bc),(0x3846f8,0x384744),
              (0x378f28,0x378ffc),(0x379004,0x3790a8),
              (0x3790f4,0x3791c4)]
    blocks = [decode_thumb(cp,a,b,base) for a,b in ranges]
    index = {i.address:i for block in blocks for i in block}
    def call(target): return ('bl', f'#{base+target:#x}')
    require_instructions(index, {
        0x36c716:('mov','r4, r0'), 0x36c718:('movw','r6, #0x5afc'),
        0x36c71c:('ldr','r0, [r4, r6]'), 0x36c71e:('adds','r1, r0, #1'),
        0x36c720:('bne.w',f'#{base+0x36c7c6:#x}'),
        0x36c778:('tbb','[pc, r3]'),
        0x36c79e:('add','r3, sp, #8'), 0x36c7a0:('mov','r0, r5'),
        0x36c7a2:('movs','r1, #0'), 0x36c7a4:('mov.w','r2, #-1'),
        0x36c7ac:call(0x3a1940), 0x36c7b0:('mov','r2, r0'),
        0x36c7b2:('cbz',f'r2, #{base+0x36c7ce:#x}'),
        0x36c7ce:('ldr','r0, [sp, #0x14]'), 0x36c7d0:('add','r6, r4'),
        0x36c7d6:('str','r0, [r6]'), 0x36c7d8:('mov.w','r0, #0x5f80'),
        0x36c7dc:('str','r5, [r4, r0]'),
        0xa0512a:('mov','r6, r1'), 0xa0512c:('mov','sb, r0'),
        0xa0512e:('movw','r1, #0x5ad8'), 0xa05134:('mov','r4, r2'),
        0xa05136:('add.w','r0, sb, r6, lsl #2'),
        0xa0513a:('adds','r5, r0, r1'), 0xa05156:('str','r4, [r5]'),
        0xa0515a:('cmp','r6, #9'), 0xa0515e:('mov.w','r0, #0x5f80'),
        0xa05164:('movw','r0, #0x5f84'), 0xa05168:('str.w','r8, [sb, r0]'),
        0x37efb0:('movw','r5, #0x5afc'), 0x37efb4:('movw','r1, #0x52f0'),
        0x37efba:('ldr','r0, [r4, r5]'), 0x37efbc:('str','r0, [r6, r1]'),
        0x37efda:('mov.w','r0, #-1'), 0x37efde:('str','r0, [r4, r5]'),
        0x37f0ec:('movw','r0, #0x5afc'), 0x37f0f4:('movs','r1, #0xa'),
        0x37f0f6:('adds','r5, r4, r0'), 0x37f0f8:('movw','r0, #0x52f0'),
        0x37f0fc:('add.w','sl, r6, r0'),
        0x37f110:('mov','r0, r4'), 0x37f116:('ldr','r2, [r5]'),
        0x37f118:call(0xa05122), 0x37f11c:('mov.w','r8, #-1'),
        0x37f124:('mov','r0, r4'), 0x37f126:('movs','r1, #9'),
        0x37f128:('str.w','r8, [r5]'), 0x37f136:('ldr.w','r2, [sl]'),
        0x37f13a:call(0xa05122), 0x37f13e:('str.w','r8, [sl]'),
        0x3816ce:('ldr','r4, [r0]'), 0x38171c:('mov','r0, r4'),
        0x38171e:call(0x36c70c), 0x381786:('mov','r0, r4'),
        0x381788:('movs','r1, #0x2b'), 0x38178a:call(0x3818b8),
        0x3818c6:('add.w','fp, sp, #0x40'),
        0x3818ca:('mov','sb, r1'), 0x3818cc:('mov','sl, r0'),
        0x381a06:('ands','r4, sb, #0x10'),
        0x381a28:('lsls.w','r0, sb, #0x1a'),
        0x381a2c:('bpl',f'#{base+0x381a4c:#x}'),
        0x381a2e:('movw','r0, #0x5afc'),
        0x381a32:('add.w','r1, fp, #0xd8'),
        0x381a36:('ldr.w','r0, [sl, r0]'), 0x381a3a:call(0xa13bb2),
        0x381a8a:('strd','sb, r4, [sp, #0x30]'),
        0x381b1a:('ldr','r0, [sp, #0x34]'), 0x381b1c:('mov','fp, sl'),
        0x381b20:('beq.w',f'#{base+0x381df2:#x}'),
        0x381df6:('mov','sl, fp'), 0x381e92:('add','r3, sp, #0x40'),
        0x381e98:call(0x382bd8), 0x381f5a:('add','r3, sp, #0x40'),
        0x381f5c:('ldr','r1, [sp, #0x30]'), 0x381f5e:('mov','r0, sl'),
        0x381f60:call(0x384354),
        0x384362:('mov','r6, r3'), 0x38436a:('str','r0, [sp, #0x18]'),
        0x3843e2:('ldr','r0, [sp, #0x18]'),
        0x3843e4:('lsls','r0, r0, #0x1a'),
        0x3843e6:('bpl.w',f'#{base+0x384790:#x}'),
        0x3843ee:('mov','r4, r6'),
        0x384434:('ldrd','r3, r5, [r4, #0xf0]'),
        0x38443a:('strd','r5, r3, [sp, #0x20]'),
        0x38444c:('movt','r1, #0x172'), 0x384450:('mla','r4, r2, ip, r1'),
        0x384454:('add.w','r5, r4, #0x10'), 0x384460:('str','r5, [sp, #0x28]'),
        0x38449e:('str','r4, [sp, #0x3c]'),
        0x3844ac:('ldr','r0, [sp, #0x3c]'),
        0x3844ae:('add.w','r5, r0, r8'),
        0x3844f0:('ldr','r1, [sp, #0x34]'), 0x3844f2:('ldr','r1, [r1]'),
        0x3844f4:('cmp','r1, #1'), 0x3844f6:('bne',f'#{base+0x3844fe:#x}'),
        0x3844fc:('b',f'#{base+0x384556:#x}'),
        0x384502:('ldr','r1, [sp, #0x20]'),
        0x384504:('str.w','r1, [r5, #0x174]'),
        0x384508:('ldr','r1, [sp, #0x24]'),
        0x38450a:('str.w','r1, [r5, #0x170]'),
        0x3846a2:('add.w','r8, r8, #0x320'),
        0x3846b2:('cmp.w','r8, #0xc80'),
        0x3846f8:('movw','r1, #0x33f0'), 0x3846fc:('mov.w','r0, #0xc90'),
        0x384704:('movt','r1, #0x172'), 0x384708:('mla','r0, r4, r0, r1'),
        0x38470c:('add.w','fp, r0, #0x970'),
        0x384710:('add.w','r5, r0, #0x650'),
        0x384714:('add.w','r6, r0, #0x330'),
        0x38472c:('ldr','r0, [sp, #0x28]'),
        0x384734:('strd','r0, r6, [sp]'), 0x384738:('strd','r5, fp, [sp, #8]'),
        0x38473e:('ldr','r3, [sp, #0x3c]'), 0x384740:call(0x378f28),
        0x378f28:('push','{r4, r5, r6, r7, lr}'),
        0x378f2a:('add','r7, sp, #0xc'), 0x378f32:('mov','r5, r1'),
        0x378f34:('mov','r8, r3'),
        0x378f5a:('ldrd','r3, r2, [r7, #0x10]'),
        0x378f5e:('ldrd','sl, fp, [r7, #8]'),
        0x378fe4:('ldr.w','r0, [r5, #0x12c]'),
        0x378fe8:('subs','r4, r0, #3'), 0x378fea:('cmp','r4, #6'),
        0x378fec:('bhi',f'#{base+0x37902a:#x}'),
        0x378ff0:('mov','r2, sl'), 0x378ff8:('tbb','[pc, r4]'),
        0x379004:('movs','r2, #0'), 0x379006:('mov','r1, sl'),
        0x379008:('movs','r3, #0'),
        0x37900a:('b',f'#{base+0x37905a:#x}'),
        0x379042:('movs','r1, #0'), 0x379044:('movs','r2, #0'),
        0x379046:('mov','r3, sl'),
        0x379048:('b',f'#{base+0x37905a:#x}'),
        0x37904a:('movs','r1, #0'), 0x37904c:('movs','r2, #0'),
        0x37904e:('movs','r3, #0'), 0x379050:('mov','ip, sl'),
        0x379052:('b',f'#{base+0x379072:#x}'),
        0x379054:('movs','r3, #0'),
        0x379056:('mov','r1, sl'), 0x379058:('mov','r2, fp'),
        0x37905a:('mov.w','ip, #0'),
        0x37905e:('b',f'#{base+0x379072:#x}'),
        0x379060:('movs','r1, #0'), 0x379062:('movs','r2, #0'),
        0x379064:('mov','r3, sl'), 0x379066:('mov','ip, fp'),
        0x379068:('b',f'#{base+0x379072:#x}'),
        0x37906a:('ldrd','r3, ip, [r7, #0x10]'),
        0x37906e:('mov','r1, sl'), 0x379070:('mov','r2, fp'),
        0x379074:('str.w','ip, [sp]'), 0x37907e:('mov','r0, r8'),
        0x379080:call(0x4459c8),
    }, base)
    targets = bounded_tbb_targets(cp[0x378ffc:0x379003],0x378ffc,len(cp))
    expected = (0x379004,0x379072,0x379042,0x37904a,0x379054,0x379060,0x37906a)
    if targets != expected or any(base+t not in index for t in targets):
        raise ValueError('VFX 通道选择表与已解码目标不一致')
    # The six-u16 companion/selector are offsets, not proven dimensions/enums.
    require_instructions(index, {
        0x384448:('movw','r1, #0x33f0'), 0x38441a:('mov.w','ip, #0xc90'),
        0x384486:('movw','r0, #0x65b4'), 0x38448a:('add','r0, r8'),
        0x38448c:('mov.w','r8, #0'), 0x384490:('str','r0, [sp, #0x34]'),
    }, base)
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'capture-slot-producer-and-conditional-native-field-layout',
        'main_role_slot':{
            'setter_file_offset':'0xa05122','slot_array_object_offset':0x5ad8,
            'slot_bytes':4,'role_index':9,'object_offset':0x5afc,
            'role_10_object_offset':0x5b00,
            'jpeg_output_object_offset':baseline['main_jpeg_buffers']['output_handle_object_offset'],
            'producer_file_offset':'0x36c70c','request_call_file_offset':'0x36c7ac',
            'request_function_file_offset':'0x3a1940','reply_handle_offset':0xc,
            'store_file_offset':'0x36c7d6','companion_object_offset':0x5f80,
            'request_api_semantics_fully_verified':False},
        'ownership_changes':{
            'move_out_file_offset':'0x37efb0','other_object_slot_offset':0x52f0,
            'move_out_invalidates_source':True,
            'replace_file_offset':'0x37f0ec',
            'operations':['old role 9 -> role 10','clear role 9',
                          'other object +0x52f0 -> role 9','clear other slot'],
            'scope':'局部指令中的转移；不推断对象实例、调用时刻或释放已完成'},
        'capture_stage':{
            'entry_file_offset':'0x3816c4','buffer_producer_call_file_offset':'0x38171e',
            'builder_file_offset':'0x3818b8','builder_call_file_offset':'0x38178a',
            'flags_at_this_call':0x2b,'query_enable_bit':0x20,
            'info_query_call_file_offset':'0x381a3a','handle_object_offset':0x5afc,
            'query_reply_config_offset':0xd8,
            'candidate_address_config_offset':0xd8+0x18,
            'request_builder_file_offset':'0x384354',
            'intervening_helper_file_offset':'0x382bd8',
            'intervening_helper_effects_fully_audited':False},
        'capture_native_layout':{
            'address_load_file_offset':'0x384434','source_bytes':8,
            'constructor_channel_stride':0x320,'channel_pointer_offset':0x10,
            'constructor_address_offsets':[0x170,0x174],
            'api_channel_address_offsets':[0x160,0x164],
            'condition':'flags & 0x20 and work object +0x65b4 != 1',
            'word_order':'little-endian low word then high word; temporary stack pair is reversed',
            'wrapper_file_offset':'0x378f28','api_call_file_offset':'0x379080',
            'api_file_offset':'0x4459c8',
            'same_api_and_candidate_offsets_as_previous_vfx_path':True,
            'role_verified_in_lower_driver':False},
        'bounded_channel_selector':{
            'module_field_offset':0x12c,'values':list(range(3,10)),
            'tbb_file_offset':'0x378ff8','table_file_range':['0x378ffc','0x379003'],
            'targets':[hex(t) for t in targets],
            'first_constructed_channel_api_argument':[2,3,4,5,2,4,2],
            'argument_basis':'r0 is argument 1; argument 5 is entry stack +0',
            'camera_mode_enum_verified':False},
        'limitations':[
            '相同对象偏移/查询回复位置不证明 VFX 与 MAIN 使用同一实例或同一时刻的句柄',
            '0x382bd8 等中间调用对查询区和状态的全部影响尚未审计',
            '捕获 VFX 与用户 LUT 上传/就绪状态的关系尚未连接',
            '候选双字的下层输出角色、真实尺寸、格式、色彩条件和缓冲寿命未验证',
            '切换表只按已检查边界解析，不宣称完整调用图或运行路径可行'],
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'matching_slot_and_native_field_layout_located':True,
        'lut_output_to_main_input_connected':False,
        'capture_vfx_uses_user_lut_verified':False,
        'buffer_identity_and_lifetime_verified':False,
        'full_resolution_dimensions_verified':False,'color_format_enum_verified':False,
        'ap_to_cp_runtime_verified':False,'photo_pipeline_located':False,
        'camera_commands_sent':False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cp',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    try:
        raw = (json.dumps(trace(args.cp),ensure_ascii=False,indent=2)+'\n').encode()
        write_bytes_new(args.output,raw)
        print(raw.decode(),end='')
        return 0
    except (ValueError,OSError,ImportError) as exc:
        parser.exit(1,f'STOPPED: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
