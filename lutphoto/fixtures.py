"""Original diagnostic assets, generated from explicit mathematical mappings."""
from pathlib import Path

from .io import write_bytes_new, write_new


def cube_bytes(size=17, mapping='identity'):
    if size not in (2, 17, 33, 65) or mapping not in ('identity', 'swap-rb'):
        raise ValueError('不支持的自制 LUT 尺寸或映射')
    lines = [f'TITLE "lutphoto {mapping} encoded sRGB"', f'LUT_3D_SIZE {size}',
             'DOMAIN_MIN 0 0 0', 'DOMAIN_MAX 1 1 1']
    for b in range(size):
        for g in range(size):
            for r in range(size):
                values = (r, g, b) if mapping == 'identity' else (b, g, r)
                lines.append(' '.join(f'{v / (size - 1):.12g}' for v in values))
    return ('\n'.join(lines) + '\n').encode('ascii')


def create_fixtures(directory, size=17):
    import numpy as np
    from PIL import Image
    from .images import srgb_profile
    raw = {f'{kind}-{size}.cube': cube_bytes(size, kind) for kind in ('identity', 'swap-rb')}
    # Gray ramp, independent RGB ramps, and RGB cross-channel gradients.
    x = np.arange(256, dtype=np.uint8)
    chart = np.zeros((256, 768, 3), dtype=np.uint8)
    chart[:, :256] = x[None, :, None]
    for channel in range(3):
        chart[channel * 64:(channel + 1) * 64, 256:512, channel] = x
    chart[:, 512:, 0] = x
    chart[:, 512:, 1] = x[:, None]
    chart[:, 512:, 2] = 128
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=False)
    for name, data in raw.items():
        write_bytes_new(target / name, data)
    image = Image.fromarray(chart)
    write_new(target / 'chart.png', lambda stream: image.save(stream, format='PNG', icc_profile=srgb_profile()))
    return {'files_created': [*raw, 'chart.png'], 'lut_space': 'srgb',
            'origin': 'original-mathematical-diagnostics', 'camera_processing_verified': False}
