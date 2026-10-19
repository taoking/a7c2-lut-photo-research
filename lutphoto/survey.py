"""Read-only string leads from exact original 2.01 programs; never patch bytes."""
import hashlib
import mmap
import os
from pathlib import Path
import re

TARGETS = {
    'ap': '2ea02f7ecbc5bb917316fe8ef4ce5ffd87eb66efaae78ba2ce11420552df539b',
    'cp': 'f5a477588698ef965748903b8959a39ce4f59ffd4aee4d4234ef1670f56a1428',
}
TERMS = (b'.cube', b'LUT_3D_SIZE', b'PPLUT', b'UserLut', b'UserLUT', b'S-Log3', b'LUT')


def string_leads(data, limit=32):
    result = []
    for term in TERMS:
        for encoding in ('ascii', 'utf-16-le'):
            needle = term if encoding == 'ascii' else term.decode('ascii').encode(encoding)
            offsets = []
            truncated = False
            for match in re.finditer(re.escape(needle), data):
                if len(offsets) == limit:
                    truncated = True
                    break
                offsets.append(hex(match.start()))
            if offsets:
                result.append({'term': term.decode('ascii'), 'encoding': encoding,
                               'file_offsets': offsets, 'more_hits': truncated})
    return result


def survey_program(path, kind):
    if kind not in TARGETS:
        raise ValueError('程序类型须为 ap 或 cp')
    path = Path(path)
    with path.open('rb') as stream:
        size = os.fstat(stream.fileno()).st_size
        if not 0 < size <= 512 * 1024 * 1024:
            raise ValueError('程序大小必须在 1 字节至 512 MiB 之间')
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != TARGETS[kind]:
            raise ValueError('不匹配锁定的原版 2.01 完整程序指纹；不分析未知或已修改程序')
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            leads = string_leads(data)
    return {'kind': kind, 'model': 'ILCE-7CM2', 'firmware': '2.01', 'bytes': size,
            'sha256': digest, 'evidence_level': 'string-leads-only', 'leads': leads,
            'photo_pipeline_located': False, 'camera_commands_sent': False,
            'note': '偏移是离线文件偏移；字符串命中不证明静态照片调用关系或可用补丁位置。'}
