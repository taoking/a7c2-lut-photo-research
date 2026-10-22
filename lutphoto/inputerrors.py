"""Fixed hints for offline preview; never display raw exception text there."""
from contextlib import contextmanager


HINTS = {
    'ST_DECLARATION': '缺少明确的ST输入声明；确认模型和图片适用后再提供 --st-input，sRGB标签不能证明Sony ST。',
    'OUTPUT_DIRECTORY': '无法创建输出目录；使用仓库外的全新目录，父目录须已存在、归本人所有且权限0700。保留已有结果，不覆盖或续跑。',
    'PROJECT': '项目无法校验；检查JSON格式、项目schema、base ST、CUBE来源/输入域/输出sRGB，以及事先声明的正数误差阈值。',
    'MODEL': '暂定ST模型无法校验；检查模型文件、schema、坐标模型、依据及有限可逆的3×3响应矩阵。单位矩阵不是实机标定。',
    'CUBE': 'CUBE无法读取或解析；检查文件及UTF-8单一3D表格式、尺寸2–65、数据行数和有限数值，不接受DCP或组合1D/3D表。',
    'LUT_OUTPUT': 'CUBE输出超出0..1编码sRGB范围；先依据原LUT说明制作经审阅的参考转换，不自动裁切HDR/Log输出。',
    'BRIDGE': 'LUT输入域与ST桥接不匹配；非sony-st-srgb输入必须提供有依据且输入/输出域匹配的桥接，不能仅改标签或假设自动转换。',
    'DOMAIN': '采样超出CUBE声明域且当前策略拒绝；核对LUT及桥接的真实适用域，不为通过检查直接改域或改截断策略。',
    'VALIDATION_LOCK': '冻结验收锁无法校验或已变化；核对项目、模型和锁的来源，按正式验收流程重新冻结，不手改锁。',
    'IMAGE': '参考图无法读取或比较；使用不超过400万像素的单帧8位RGB JPEG/PNG，检查色彩声明及文件完整性，必要时另存参考裁图。',
    'IMAGE_SPACE': '照片未明确声明可用sRGB解释；先检查真实色彩空间。仅在确认无标签图片原本就是sRGB时使用 --assume-srgb，不能覆盖其他色彩空间声明。',
    'ICC': '照片ICC无效、过大或无法转换；用可靠色彩管理工具正确另存sRGB参考图，保留原图，不通过删除ICC强行使用。',
    'MASK': '分区掩码无法校验；检查JSON区域名和文件，掩码须为8位灰度单帧PNG、仅含0/255且匹配照片方向修正后的尺寸。',
    'SOURCE_CHANGED': '项目、候选、表、图片或验收锁的绑定不一致；保留本次部分结果，核对输入后使用新目录重新计算，不拼接旧结果。',
    'FIT': '拟合未完成；检查项目、模型、LUT和可选冻结锁。未生成完整预览，不能作为色彩通过或安装许可。',
    'DEPENDENCY': '缺少或无法导入电脑端依赖；检查当前项目Python环境，不需要连接相机或安装机内模块。',
    'INCOMPLETE': '计算、保存或终端输出未完成；检查输入和输出位置的权限/空间，保留部分目录，不覆盖、不自动重试。',
}


class InputProblem(ValueError):
    """A bounded category plus the original message for existing Python callers."""
    def __init__(self, code, message):
        if code not in HINTS:
            raise ValueError('Unknown offline input category')
        super().__init__(message)
        self.code = code


@contextmanager
def input_context(code):
    """Annotate a failed check without changing its acceptance or retrying it."""
    try:
        yield
    except InputProblem:
        raise
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise InputProblem(code, str(error)) from error


def preview_hint(error):
    code = error.code if isinstance(error, InputProblem) else 'DEPENDENCY' if isinstance(error, ImportError) else 'INCOMPLETE'
    # Defensive whitelist: exception fields/messages are never terminal content.
    if code not in HINTS:
        code = 'INCOMPLETE'
    return f'预览已停止 [{code}]：{HINTS[code]} 部分输出如已生成请保留；本次未完成预览。'
