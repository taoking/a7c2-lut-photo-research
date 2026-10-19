"""Read-only JPEG field projection, VFX parameters and shared LUT readiness.

Reports initial parameter fields, not a complete or final device payload.
Never executes firmware or assumes the VFX output is the MAIN JPEG input.
"""
import argparse
import json
from pathlib import Path

from lutphoto.io import write_bytes_new
from lutphoto.survey import TARGETS
from research.trace_cp import boot_base, decode_thumb
from research.trace_lut_handoff import read_original, require_instructions
from research.trace_lut_schedule import trace as trace_schedule
from research.trace_lut_snapshot import movw_movt_value


# Source prefix offset/width -> initial parameter offset/width. No encoder.
JPEG_FIELDS=((0,8,0,8),(8,8,0x30,8),
             (0x10,2,8,4),(0x12,2,0xc,4),(0x18,2,0x10,4),(0x1a,2,0x14,4),
             (0x14,2,0x18,4),(0x16,2,0x1c,4),(0x14,2,0x28,4),(0x16,2,0x2c,4),
             (0x1c,4,0x3c,4),(0x20,4,0x40,4),(0x14,2,0x44,4),(0x16,2,0x48,4),
             (0x24,4,0x68,4),(0x28,4,0x6c,4))
JPEG_INITIAL_ZERO_OFFSETS=(0x20,0x24,0x50,0x54,0x58,0x5c,0x60,0x64,0x70,0x74)


def initial_jpeg_fields(prefix):
    """Project exactly the known 44-byte prefix into sparse numeric fields.

    Values are (byte width, unsigned value). Unspecified fields are absent.
    This is the initial constructor only: later code rewrites e.g. +0x60/+0x64.
    No binary payload, padding, dimensions or color enum are invented.
    """
    if not isinstance(prefix,(bytes,bytearray)) or len(prefix)!=0x2c:
        raise ValueError('需要恰好 44 字节的合成参数前缀')
    source=bytes(prefix)
    values={dst:(width,int.from_bytes(source[src:src+n],'little'))
            for src,n,dst,width in JPEG_FIELDS}
    left=int.from_bytes(source[0x1c:0x20],'little')
    right=int.from_bytes(source[0x20:0x24],'little')
    values[0x38]=(4,(left+right)&0xffffffff)
    values.update({offset:(4,0) for offset in JPEG_INITIAL_ZERO_OFFSETS})
    return dict(sorted(values.items()))


def trace(cp_path):
    cp=read_original(cp_path,'cp')
    base=boot_base(cp)
    baseline=trace_schedule(cp_path)
    ranges=[(0x3859dc,0x385a94),(0x385278,0x3852e6),
            (0x39d764,0x39d7da),(0xa13bb2,0xa13be4),(0x40998a,0x4099b8),
            (0x3dfedc,0x3e06c4),(0x3e076c,0x3e0970),(0x3e09f0,0x3e0a3e),
            (0x3853fc,0x385428),(0x385b6e,0x385b84)]
    blocks=[decode_thumb(cp,a,b,base) for a,b in ranges]
    index={i.address:i for block in blocks for i in block}
    require_instructions(index,{
        0x3859f8:('movw','r0, #0x5afc'), 0x3859fc:('ldr','r0, [r4, r0]'),
        0x3859fe:('add','r1, sp, #0x250'),
        0x385a00:('bl',f'#{base+0xa13bb2:#x}'),
        0x385a08:('movw','r8, #0x5b18'), 0x385a0c:('ldr.w','r0, [r4, r8]'),
        0x385a10:('add','r1, sp, #0x178'),
        0x385a12:('bl',f'#{base+0xa13bb2:#x}'),
        0x385a5c:('ldrd','r1, r2, [sp, #0x268]'),
        0x385a62:('add.w','sl, sp, #0x30'), 0x385a68:('movw','r0, #0x6088'),
        0x385a6c:('strd','r1, r2, [sp, #0x30]'),
        0x385a70:('ldrd','sb, fp, [sp, #0x190]'),
        0x385a74:('strd','sb, fp, [sp, #0x38]'),
        0x385a86:('movs','r2, #0xc'), 0x385a8a:('adds','r1, r4, r0'),
        0x385a8c:('add.w','r0, sl, #0x10'),
        0x385a90:('blx',f'#{base+0x51660c:#x}'),
        0x385284:('mov','r6, r1'), 0x385288:('movs','r4, #0'),
        0x38528c:('ldrd','r0, r1, [r6]'), 0x385290:('strd','r0, r1, [sp, #0xd8]'),
        0x385294:('ldrh','r0, [r6, #0x10]'), 0x385296:('str','r0, [sp, #0xe0]'),
        0x385298:('ldrh','r0, [r6, #0x12]'), 0x38529a:('str','r0, [sp, #0xe4]'),
        0x38529c:('ldrh','r0, [r6, #0x18]'), 0x38529e:('str','r0, [sp, #0xe8]'),
        0x3852a0:('ldrh','r0, [r6, #0x1a]'), 0x3852a2:('str','r0, [sp, #0xec]'),
        0x3852a4:('ldrh','r0, [r6, #0x14]'), 0x3852a6:('str','r0, [sp, #0xf0]'),
        0x3852a8:('ldrh','r1, [r6, #0x16]'), 0x3852aa:('str','r1, [sp, #0xf4]'),
        0x3852ac:('strd','r4, r4, [sp, #0xf8]'),
        0x3852b0:('strd','r0, r1, [sp, #0x100]'),
        0x3852b4:('ldrd','r2, r3, [r6, #8]'), 0x3852b8:('strd','r2, r3, [sp, #0x108]'),
        0x3852bc:('ldrd','r2, r3, [r6, #0x1c]'), 0x3852c0:('adds','r5, r3, r2'),
        0x3852c2:('strd','r5, r2, [sp, #0x110]'),
        0x3852c6:('strd','r3, r0, [sp, #0x118]'), 0x3852ca:('str','r1, [sp, #0x120]'),
        0x3852cc:('strd','r4, r4, [sp, #0x130]'),
        0x3852d0:('strd','r4, r4, [sp, #0x128]'),
        0x3852d6:('ldr','r0, [r6, #0x24]'), 0x3852d8:('str','r0, [sp, #0x140]'),
        0x3852da:('ldr','r0, [r6, #0x28]'),
        0x3852dc:('strd','r0, r4, [sp, #0x144]'),
        0x3852e0:('str','r4, [sp, #0x14c]'),
        0x3852e2:('strd','r4, r4, [sp, #0x138]'),
        0x385404:('mov','r8, fp'),
        0x385406:('add.w','r0, r6, r8, lsl #2'),
        0x38540a:('ldr','r0, [r0, #0x2c]'),
        0x38540c:('strd','r0, r0, [sp, #0x138]'),
        0x385422:('add','r0, sp, #0xd8'),
        0x385424:('bl',f'#{base+0x39d764:#x}'),
        0x385b7a:('add','r1, sp, #0x30'),
        0x385b80:('bl',f'#{base+0x385278:#x}'),
        0x39d76e:('mov','sb, r0'), 0x39d778:('adr','r0, #0x214'),
        0x39d78a:('ldm.w','sb, {r2, r3, ip, lr}'),
        0x39d7b2:('adr','r0, #0x1e8'), 0x39d7bc:('ldrd','r2, r3, [sb, #0x30]'),
        0xa13bd0:('bl',f'#{base+0x409858:#x}'),
        0x4099aa:('mov','r0, r4'), 0x4099ac:('mov','r1, sb'),
        0x4099ae:('movs','r2, #0xd8'),
        0x4099b0:('blx',f'#{base+0x51660c:#x}'),
        0x3dfedc:('push','{r4, r5, r6, r7, lr}'),
        0x3dfede:('add','r7, sp, #0xc'),
        0x3dffd0:('ldr','r1, [r7, #0xc]'), 0x3dffda:('ldr','r2, [r1]'),
        0x3dffec:('ldr','r0, [r7, #0x10]'),
        0x3dfff0:('ldr','r1, [r2, #8]'), 0x3dfff2:('str.w','r1, [sp, #0x990]'),
        0x3dfff6:('ldrh','r0, [r0, #2]'), 0x3dfff8:('str.w','r0, [sp, #0x994]'),
        0x3dffd8:('ldr','r4, [r7, #0x1c]'), 0x3dffee:('cmp','r4, #0'),
        0x3e0038:('beq',f'#{base+0x3e0044:#x}'),
        0x3e003e:('ldrd','r3, r5, [r4]'),
        0x3e004a:('str.w','r3, [sp, #0xad8]'),
        0x3e0050:('str.w','r5, [sp, #0xadc]'),
        0x3e0054:('ldrh','r3, [r3]'), 0x3e0056:('str.w','r3, [sp, #0xae0]'),
        0x3e07bc:('cmp','r0, #1'), 0x3e07be:('bne',f'#{base+0x3e0818:#x}'),
        0x3e07c0:('movs','r0, #1'), 0x3e07c6:('strb.w','r0, [sl]'),
        0x3e07ca:('movs','r0, #2'), 0x3e07d0:('str.w','r0, [sb]'),
        0x3e0812:('bl',f'#{base+0x446398:#x}'),
        0x3e087c:('bl',f'#{base+0x44615c:#x}'),
        0x3e08e0:('movs','r0, #0'),
        0x3e08e6:('strb.w','r0, [sl]'), 0x3e08ea:('str.w','r0, [sb]'),
        0x3e09f4:('mov','r4, r0'), 0x3e09fa:('movs','r1, #0'),
        0x3e0a00:('strb','r1, [r0]'),
        0x3e0a16:('cbz',f'r4, #{base+0x3e0a3e:#x}'),
        0x3e0a34:('movs','r1, #0'), 0x3e0a3c:('str','r1, [r0]'),
    },base)
    insns=list(index.values())
    def constant(a,b):return movw_movt_value(insns,base+a,base+b)
    flags=[constant(0x3e0788,0x3e078c),constant(0x3e09f6,0x3e09fc),
           constant(0x3dff14,0x3dff18)]
    states=[constant(0x3e07b0,0x3e07b4),constant(0x3e0a30,0x3e0a36),
            constant(0x3dff06,0x3dff0e)]
    callbacks=[constant(0x3e07fa,0x3e07fe),constant(0x3e086e,0x3e0878)]
    if flags!=[0x1b1e235]*3 or states!=[0x1a6aefc]*3 or callbacks!=[base+0x3e09f0+1]*2:
        raise ValueError('上传、回调和传输检查使用的就绪字段不一致')
    for offset,label in [(0x39d990,b'FW: JPEG IN'),(0x39d99c,b'FW: JPEG OUT')]:
        if cp[offset:offset+len(label)+1]!=label+b'\0':
            raise ValueError('JPEG 地址角色的日志标签不符')
    return {
        'model':'ILCE-7CM2','firmware':'2.01','cp_sha256':TARGETS['cp'],
        'evidence_level':'static-initial-JPEG-fields-and-shared-readiness',
        'main_jpeg_buffers':{
            'builder_file_offset':'0x3859dc','info_query_file_offset':'0xa13bb2',
            'info_reply_copy_bytes':0xd8,'info_address_offset':0x18,'address_bytes':8,
            'input_handle_object_offset':0x5afc,'output_handle_object_offset':0x5b18,
            'input_prefix_address_offsets':[0,8],
            'parameter_input_address_offset':0,'parameter_output_address_offset':0x30,
            'six_u16_object_offset':0x6088,'six_u16_copy_bytes':12,
            'address_role_basis':'initial constructor plus JPEG IN/OUT diagnostic labels'},
        'initial_jpeg_projection':{
            'source_prefix_bytes':0x2c,
            'fields':[{'source_offset':s,'source_bytes':n,'parameter_offset':d,'parameter_bytes':w}
                      for s,n,d,w in JPEG_FIELDS],
            'sum32':{'source_offsets':[0x1c,0x20],'parameter_offset':0x38},
            'initial_zero_word_offsets':list(JPEG_INITIAL_ZERO_OFFSETS),
            'unspecified_word_offsets':[0x4c],
            'later_rewritten_word_offsets':[0x60,0x64],
            'scope':'只记录初始已知字段；不输出完整设备参数或机内载荷'},
        'vfx_first_channel':{
            'builder_file_offset':'0x3dfedc','packet_stack_offset':0x978,
            'frame_basis':'r7 = entry SP - 8; r0 is argument 1',
            'source_word':{'origin':'dereference argument 6, then +8','entry_sp_argument_offset':4,
                           'bytes':4,'packet_offset':0x18},
            'candidate_output_address':{'origin':'argument 10 points to two words',
                                        'entry_sp_argument_offset':0x14,'bytes':8,'packet_offset':0x160,
                                        'role_verified_in_lower_driver':False},
            'u16_fields':{'origin':'argument 7 +2 and +0','entry_sp_argument_offset':8,
                          'packet_offsets':[0x1c,0x168]},
            'scope':'参数来源与宽度已记录；候选输出角色仍需下层核对，不把 32 位源字段拼成 64 位地址'},
        'lut_readiness':{
            'pending_byte_link_va':hex(flags[0]),'state_word_link_va':hex(states[0]),
            'before_upload':'pending byte = 1, state word = 2',
            'callback_file_offset':'0x3e09f0',
            'callback_behavior':'clear pending byte; nonzero result also clears state word',
            'initial_transfer_gate':'state word == 2 and pending byte == 0',
            'shared_fields_statically_connected':True,
            'cross_queue_completion_order_verified':False},
        'baseline_jpeg_api_file_offset':baseline['jpeg_segment']['encode_api_file_offset'],
        'limitations':['缓冲查询返回地址不等于已证明物理/虚拟映射或像素格式',
                       '六个 u16 字段的逐项尺寸语义和实际全尺寸数值未确认',
                       'JPEG 初始参数后续仍有改写，稀疏模型不是最终完整参数',
                       'VFX 输出参数与 MAIN 输入句柄的生产者/缓冲身份仍未连接',
                       '共享就绪字段是静态连接，未证明所有队列时序、缓存/缓冲寿命或色彩条件'],
        'checked_cp_windows':[[hex(a),hex(b)] for a,b in ranges],
        'lut_output_to_main_input_connected':False,'full_resolution_dimensions_verified':False,
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
