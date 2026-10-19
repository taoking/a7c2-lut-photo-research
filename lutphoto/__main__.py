"""Independent offline CLI. Does not import macfl23, USB or upstream workers."""
import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .cube import load_cube
from .io import write_bytes_new


def parser():
    root = argparse.ArgumentParser(description='LUT 照片离线参考工具；不连接相机')
    root.add_argument('--version', action='version', version=__version__)
    commands = root.add_subparsers(dest='action', required=True)
    inspect = commands.add_parser('inspect', help='检查 3D CUBE 格式，不推断色彩空间')
    inspect.add_argument('lut', type=Path)
    apply = commands.add_parser('apply', help='将编码 sRGB LUT 应用于照片并另存')
    apply.add_argument('--lut', type=Path, required=True)
    apply.add_argument('--input', type=Path, required=True)
    apply.add_argument('--output', type=Path, required=True)
    apply.add_argument('--lut-space', required=True, choices=['srgb'],
                       help='明确声明 LUT 输入及输出均为编码 sRGB；不支持 S-Log3 LUT')
    apply.add_argument('--assume-srgb', action='store_true', help='将未标色彩空间的照片明确按 sRGB 解释')
    fixtures = commands.add_parser('fixtures', help='生成自制恒等/通道交换 LUT 和测试图')
    fixtures.add_argument('--directory', type=Path, required=True, help='尚不存在的新目录')
    fixtures.add_argument('--size', choices=[17, 33], type=int, default=17)
    survey = commands.add_parser('survey', help='只读调查精确匹配原版 2.01 的程序字符串')
    survey.add_argument('--kind', required=True, choices=['ap', 'cp'])
    survey.add_argument('--input', type=Path, required=True)
    survey.add_argument('--output', type=Path, required=True, help='新 JSON 文件；拒绝覆盖')
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.action == 'inspect':
            cube = load_cube(args.lut)
            result = {'size': cube.size, 'rows': len(cube.rows), 'title': cube.title,
                      'domain_min': cube.domain_min, 'domain_max': cube.domain_max,
                      'sha256': cube.sha256, 'color_space': 'not-declared-by-cube-format',
                      'sony_documented_grid_size': cube.size in (17, 33),
                      'camera_compatibility_verified': False}
        elif args.action == 'apply':
            from .images import apply_photo
            result = apply_photo(load_cube(args.lut), args.input, args.output,
                                 lut_space=args.lut_space, assume_srgb=args.assume_srgb)
        elif args.action == 'fixtures':
            from .fixtures import create_fixtures
            result = create_fixtures(args.directory, args.size)
        else:
            from .survey import survey_program
            result = survey_program(args.input, args.kind)
            write_bytes_new(args.output, (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(f'STOPPED: {exc}', file=sys.stderr)
        return 1
    except ImportError as exc:
        print('STOPPED: 缺少研究依赖；执行 python -m pip install -r requirements-lut.txt', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
