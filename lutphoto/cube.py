"""Strict, bounded reader for the 3D-only IRIDAS CUBE subset.

Rows are RGB values, with red varying fastest, then green, then blue.
The format does not establish the input/output color spaces.
"""
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re
import shlex

MAX_BYTES = 8 * 1024 * 1024
MAX_LINE = 4096
MAX_SIZE = 65
MAX_VALUE = 1e6


class CubeError(ValueError):
    pass


@dataclass(frozen=True)
class Cube:
    size: int
    rows: tuple
    domain_min: tuple = (0.0, 0.0, 0.0)
    domain_max: tuple = (1.0, 1.0, 1.0)
    title: str = ''
    sha256: str = ''


def _triple(tokens, line):
    if len(tokens) != 3:
        raise CubeError(f'第 {line} 行：需要三个数值')
    try:
        values = tuple(float(v) for v in tokens)
    except ValueError as exc:
        raise CubeError(f'第 {line} 行：无效数值') from exc
    if not all(math.isfinite(v) and abs(v) <= MAX_VALUE for v in values):
        raise CubeError(f'第 {line} 行：数值须有限且绝对值不超过 {MAX_VALUE:g}')
    return values


def parse_cube(raw):
    if len(raw) > MAX_BYTES:
        raise CubeError('CUBE 文件超过 8 MiB 上限')
    try:
        content = raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise CubeError('CUBE 文件必须为 UTF-8 文本') from exc
    if '\x00' in content:
        raise CubeError('CUBE 文件包含 NUL 字符')
    headers, rows = {}, []
    for number, line in enumerate(content.splitlines(), 1):
        if len(line) > MAX_LINE:
            raise CubeError(f'第 {number} 行：超过 {MAX_LINE} 字符上限')
        try:
            fields = shlex.split(line, comments=True, posix=True)
        except ValueError as exc:
            raise CubeError(f'第 {number} 行：引号不完整') from exc
        if not fields:
            continue
        key = fields[0]
        if key in {'TITLE', 'LUT_3D_SIZE', 'DOMAIN_MIN', 'DOMAIN_MAX'}:
            if rows:
                raise CubeError(f'第 {number} 行：数据开始后不能出现头部字段')
            if key in headers:
                raise CubeError(f'第 {number} 行：重复字段 {key}')
            if key == 'TITLE':
                if len(fields) != 2:
                    raise CubeError(f'第 {number} 行：TITLE 需要一个字符串')
                value = fields[1]
            elif key == 'LUT_3D_SIZE':
                if len(fields) != 2 or not re.fullmatch(r'[0-9]+', fields[1]):
                    raise CubeError(f'第 {number} 行：LUT_3D_SIZE 需要整数')
                value = int(fields[1])
                if not 2 <= value <= MAX_SIZE:
                    raise CubeError(f'LUT 尺寸须在 2–{MAX_SIZE} 之间')
            else:
                value = _triple(fields[1:], number)
            headers[key] = value
        elif key.startswith('LUT_') or key[0].isalpha():
            raise CubeError(f'第 {number} 行：不支持字段 {key}；首版只接受单一 3D LUT')
        else:
            if 'LUT_3D_SIZE' not in headers:
                raise CubeError(f'第 {number} 行：数据前缺少 LUT_3D_SIZE')
            if len(rows) >= headers['LUT_3D_SIZE'] ** 3:
                raise CubeError(f'第 {number} 行：LUT 数据行过多')
            rows.append(_triple(fields, number))
    if 'LUT_3D_SIZE' not in headers:
        raise CubeError('缺少 LUT_3D_SIZE')
    size = headers['LUT_3D_SIZE']
    if len(rows) != size ** 3:
        raise CubeError(f'LUT 数据不完整：需要 {size ** 3} 行，实际 {len(rows)} 行')
    low = headers.get('DOMAIN_MIN', (0.0, 0.0, 0.0))
    high = headers.get('DOMAIN_MAX', (1.0, 1.0, 1.0))
    if any(a >= b for a, b in zip(low, high)):
        raise CubeError('DOMAIN_MAX 的每个通道必须大于 DOMAIN_MIN')
    return Cube(size, tuple(rows), low, high, headers.get('TITLE', ''),
                hashlib.sha256(raw).hexdigest())


def load_cube(path):
    with Path(path).open('rb') as stream:
        return parse_cube(stream.read(MAX_BYTES + 1))


def evaluate(cube, rgb):
    """Trilinear float64 evaluation; input is clamped to DOMAIN, output is not.

    No gamma or gamut conversion is implicit. Callers must establish the
    color-space contract. Work on bounded chunks when evaluating photographs.
    """
    import numpy as np
    data = np.asarray(rgb, dtype=np.float64)
    if data.ndim < 1 or data.shape[-1] != 3 or not np.isfinite(data).all():
        raise CubeError('输入必须是最后一维为 RGB 三通道的有限数值数组')
    low, high = np.asarray(cube.domain_min), np.asarray(cube.domain_max)
    position = (np.clip(data, low, high) - low) / (high - low) * (cube.size - 1)
    lower = np.floor(position).astype(np.intp)
    upper = np.minimum(lower + 1, cube.size - 1)
    weight = position - lower
    table = np.asarray(cube.rows, dtype=np.float64)
    out = np.zeros_like(data)
    for b in (0, 1):
        for g in (0, 1):
            for r in (0, 1):
                indices = np.where((r, g, b), upper, lower)
                index = indices[..., 0] + cube.size * (indices[..., 1] + cube.size * indices[..., 2])
                weights = np.where((r, g, b), weight, 1 - weight).prod(axis=-1)
                out += table[index] * weights[..., None]
    return out
