"""Offline index/span models for the observed LUT branches, without payloads.

These helpers model addresses and counts only. They neither reproduce the IPSX
converter nor establish a color-space contract or camera compatibility.
"""
from itertools import product


def legacy_source_rows(size):
    """Map 8000 output locations to red-fast CUBE rows, or None for padding.

    The observed flag-zero converter samples a 17-point lattice. A 33-point
    input uses its even coordinates; it is not interpolated. Each parity bank
    has room for 10**3 samples, with blue varying fastest inside the bank.
    This is one channel's index map, not a binary encoder.
    """
    if type(size) is not int or size not in (17, 33):
        raise ValueError('此排布模型只支持 17/33 点输入')
    step = (size - 1) // 16
    rows = []
    for pr, pg, pb in product(range(2), repeat=3):
        for r, g, b in product(range(pr, 20, 2), range(pg, 20, 2), range(pb, 20, 2)):
            rows.append(None if max(r, g, b) > 16 else step * (r + size*g + size*size*b))
    return rows


def layout_summary(size):
    rows = legacy_source_rows(size)
    counts = [sum(x is not None for x in rows[n:n+1000]) for n in range(0, 8000, 1000)]
    return {
        'input_grid_size': size, 'sampled_grid_size': 17,
        'input_coordinate_step': (size-1)//16,
        'valid_samples_per_bank': counts, 'padding_samples_per_channel': rows.count(None),
        'samples_per_channel': len(rows), 'channel_order': ['R', 'G', 'B'],
        'channel_plane_bytes': len(rows)*2, 'total_table_bytes': len(rows)*2*3,
        'scope': 'flag-zero 的索引/补零模型；不生成量化值、机内载荷或补丁',
    }


def split_summary(total, table_offset, table_size, register_offset, register_size):
    """Check observed non-overlapping byte spans using unbounded integers.

    No firmware data is read. Byte counts are reported separately from any
    undocumented alignment/tail bytes, rather than calling all 128 bytes regs.
    """
    values = (total, table_offset, table_size, register_offset, register_size)
    if any(type(x) is not int or not 0 <= x <= 0xffffffff for x in values):
        raise ValueError('长度/偏移须为 uint32 整数')
    a, b = (table_offset, table_offset+table_size), (register_offset, register_offset+register_size)
    if min(table_size, register_size) == 0 or max(a[1], b[1]) > total:
        raise ValueError('数据区间为空或越界')
    if max(a[0], b[0]) < min(a[1], b[1]):
        raise ValueError('数据区间重叠')
    return {'reported_output_bytes': total,
            'table': {'offset': a[0], 'bytes': table_size},
            'registers': {'offset': b[0], 'bytes': register_size},
            'unassigned_bytes': total-table_size-register_size}
