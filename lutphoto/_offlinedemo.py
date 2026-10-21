"""Closed mathematical demonstration, never an identity policy for user files.

All tiny program/BK4/UXC bytes are generated here; no archive, device, test-suite
imports, external program inputs or policy switch. QAQLeonard/ma1co layout
semantics are acknowledged in ACKNOWLEDGEMENTS.md. Not camera firmware.
"""
import struct

from . import slotbundle as b, settingsplan as settings
from .capturestore import encoded


def create_input(directory):
    from . import nativefit as nf
    from .io import write_bytes_new
    nf.fixtures(directory)
    lines = ['TITLE "Self-generated mild warm diagnostic"', 'LUT_3D_SIZE 17',
             'DOMAIN_MIN 0 0 0', 'DOMAIN_MAX 1 1 1']
    for blue in range(17):
        for green in range(17):
            for red in range(17):
                rgb = (red / 16 * .98 + .01, green / 16 * .98 + .005, blue / 16 * .98)
                lines.append(' '.join(format(v, '.12g') for v in rgb))
    write_bytes_new(directory / 'warm-17.cube', ('\n'.join(lines) + '\n').encode())
    project, _ = nf.read_json(directory / 'project.json')
    project['source'].update(path='warm-17.cube', attribution='Self-generated affine RGB diagnostic; not a photographic style or Sony ST model')
    write_bytes_new(directory / 'demo-project.json', nf.json_bytes(project))


def materials(candidate, table):
    p, bk4 = b.p, settings.bk4
    ap = bytearray([17]) * 16384

    def row(attribute, key, base=False):
        struct.pack_into('<8I', ap, 4096 + (attribute - 0x14ea) * 32,
                         3 if base else 0, key, 0x10000 if base else 0x40000, 0, 0, 0, attribute, 0)

    props = {}
    for i in range(8):
        row(0x1520 + i * 18, 0x02cf0300 + i)
        props[0x02cf0300 + i] = bk4.Property(2, struct.pack('<I', i + 10), None, 4)
    for slot in range(1, 7):
        row(0x14ea + slot + 9, 0x02cf0100 + slot, True)
        props[0x02cf0100 + slot] = bk4.Property(0, b'\x01', None, 1)
        for i in range(8):
            row(0x1520 + i * 18 + slot + 9, 0x02cf0200 + i * 8 + slot)
            props[0x02cf0200 + i * 8 + slot] = bk4.Property(0, struct.pack('<I', i + 10 + slot), None, 4)
    props[0x02cf0b6e] = bk4.Property(64, bytes(4), bytes(4), 4)
    props[0x02770015] = bk4.Property(0, b'X', None, 1)
    cp_props = {key: bk4.Property(2, b'DEMO', None, 4) for key in b.c.devicesettings.PROTECTED}
    ap = bytes(ap); cp = bytes([17]) * 8192
    zero = bytearray([51]) * 8192
    struct.pack_into('<8I', zero, 256, 0x364c3741, 0x10006, *([p._fnv(bytes(1215))] * 6))
    zero[288:7578] = bytes(7290); zero = bytes(zero)
    restore = tuple(p._Window(at, ap[at:at + size]) for at, size in
                    ((128, 132), (16, 4), (32, 12), *((512 + i * 8, 4) for i in range(6))))
    # Zero archive hash deliberately prevents production bundle-reader acceptance.
    # The native candidate still records the actual algorithm's upstream commit.
    from .nativefit import UPSTREAM
    policy = p._Policy((p._Source('stock', len(ap), p.w.sha(ap), len(cp), p.w.sha(cp), restore),),
                       tuple(bytes([i]) * 132 for i in range(64)), b'TITL', b'MAP!' * 3,
                       'ff' * 32, 'ff' * 32, p.w.sha(zero[:264] + bytes(7314) + zero[7578:]),
                       UPSTREAM, '00' * 32, hook_at=128, title_at=16, map_at=32,
                       labels_at=512, label_stride=8, descriptors_at=4096, table_at=256)
    runtime = {'cp_zero_tables_sha256': p.w.sha(zero), 'cp_sources': [{'kind': 'stock', 'windows': [
        {'offset': at, 'before': cp[at:at + 4096].hex(), 'after': zero[at:at + 4096].hex()}
        for at in (0, 4096)]}]}
    selection = encoded({'schema': b.m.SELECTION, 'slots': {'1': {'candidate': 'candidate', 'name': 'Synthetic Demo'}}})
    snapshot = encode_snapshot({'AP': props, 'CP': cp_props})
    inputs = b.t._Inputs(ap, cp, snapshot, snapshot, selection, candidate, table,
                         {n: b.c.synthetic_resource(False) for n in b.c.RESOURCE_FILES},
                         {'AP': 0, 'CP': 1}, {'AP': 0, 'CP': 1})
    return policy, runtime, inputs


def encode_snapshot(full):
    """Selfmade wrapper only; this does not encode an original Sony BK4."""
    return b'SYNTHETIC D3 ONLY' + b''.join(settings.bk4.fixture_image(full[chip]) for chip in ('AP', 'CP'))
