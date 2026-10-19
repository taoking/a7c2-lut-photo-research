"""sRGB 8-bit reference photo processing. Camera processing is not emulated."""
import io
from pathlib import Path
import warnings

from .cube import evaluate
from .io import write_new

MAX_PIXELS = 64_000_000
MAX_IMAGE_BYTES = 128 * 1024 * 1024
CHUNK_PIXELS = 131072


def srgb_profile():
    from PIL import ImageCms
    return ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()


def read_srgb(path, assume_srgb=False):
    from PIL import Image, ImageCms, ImageOps
    if Path(path).stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError('输入照片超过 128 MiB 上限')
    with Path(path).open('rb') as stream:
        header = stream.read(29)
    # Pillow decodes 16-bit RGB PNG to RGB8, so inspect the original bit depth.
    if header.startswith(b'\x89PNG\r\n\x1a\n') and (len(header) < 29 or header[24] != 8):
        raise ValueError('首版不接受 16 位或其他非 8 位 PNG，避免隐式降低精度')
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        try:
            opened = Image.open(path)
        except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            raise ValueError('照片声明的像素数量超出安全上限') from exc
        with opened as image:
            if image.format not in {'JPEG', 'PNG'} or image.mode != 'RGB':
                raise ValueError('首版只接受 RGB 8 位 JPEG/PNG，不支持 RAW、HEIF、灰度或透明图')
            if 'transparency' in image.info:
                raise ValueError('首版不接受含透明色的 PNG')
            if image.width * image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
                raise ValueError('只接受不超过 6400 万像素的单帧照片')
            profile = image.info.get('icc_profile')
            # ColorSpace=1 is the EXIF declaration of sRGB.
            exif = image.getexif()
            color_space = exif.get(0xA001)
            if color_space is None and 0x8769 in exif:
                color_space = exif.get_ifd(0x8769).get(0xA001)
            declared_srgb = color_space == 1 or 'srgb' in image.info
            if not profile and color_space not in (None, 1):
                raise ValueError('照片明确声明其他色彩空间，需有效 ICC 或先正确转换；不能用 --assume-srgb 覆盖')
            if not profile and not declared_srgb and not assume_srgb:
                raise ValueError('照片未声明 sRGB；确认其为 sRGB 后显式使用 --assume-srgb')
            image.load()
            result = ImageOps.exif_transpose(image)
            if profile:
                if len(profile) > 4 * 1024 * 1024:
                    raise ValueError('ICC 配置超过 4 MiB 上限')
                try:
                    source = ImageCms.ImageCmsProfile(io.BytesIO(profile))
                    result = ImageCms.profileToProfile(
                        result, source, ImageCms.createProfile('sRGB'), outputMode='RGB',
                        renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC)
                except (ImageCms.PyCMSError, OSError, ValueError) as exc:
                    raise ValueError('ICC 色彩转换失败，未应用 LUT') from exc
                interpretation = 'icc-converted-to-srgb'
            else:
                interpretation = 'declared-srgb' if declared_srgb else 'assumed-srgb'
            return result.copy(), interpretation


def apply_photo(cube, source, destination, *, lut_space, assume_srgb=False):
    import numpy as np
    from PIL import Image
    if lut_space != 'srgb':
        raise ValueError('首版仅支持输入/输出均为编码 sRGB 的 LUT')
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('输出不能覆盖原照片')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('输出已存在，拒绝覆盖')
    suffix = destination.suffix.lower()
    if suffix not in {'.png', '.jpg', '.jpeg'}:
        raise ValueError('输出扩展名须为 .png、.jpg 或 .jpeg')
    image, interpretation = read_srgb(source, assume_srgb)
    # One byte per channel for output; float working storage is chunk bounded.
    data = np.asarray(image).reshape(-1, 3)
    output = np.empty_like(data)
    clipped = 0
    for start in range(0, len(data), CHUNK_PIXELS):
        values = evaluate(cube, data[start:start + CHUNK_PIXELS] / 255.0)
        clipped += int(np.count_nonzero((values < 0) | (values > 1)))
        output[start:start + CHUNK_PIXELS] = np.floor(np.clip(values, 0, 1) * 255 + 0.5).astype(np.uint8)
    rendered = Image.fromarray(output.reshape(image.height, image.width, 3))
    options = {'icc_profile': srgb_profile()}
    fmt = 'PNG' if suffix == '.png' else 'JPEG'
    if fmt == 'JPEG':
        options.update(quality=95, subsampling=0)
    # EXIF, GPS, thumbnails and MakerNotes are intentionally not copied.
    write_new(destination, lambda stream: rendered.save(stream, format=fmt, **options))
    return {'width': image.width, 'height': image.height, 'format': fmt,
            'input_interpretation': interpretation, 'lut_space': lut_space,
            'interpolation': 'trilinear-float64', 'lut_sha256': cube.sha256,
            'clipped_channel_values': clipped, 'camera_processing_verified': False}
