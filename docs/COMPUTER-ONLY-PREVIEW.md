# 不需要机身备份的原生表预览

第六十五轮增加`lutphoto.offline preview`。在相机仍为2.00、尚无内部AP/CP/BK4/68资源时，也能用**显式项目、CUBE、暂定模型和参考图**查看原LUT与原生表模型的差异。本入口只做电脑端计算，不要求上游固件归档，不创建机身包或写入许可。算法、输入域/桥接和1,215字节编码继续复用[原有N2工具](NATIVE-FIT-OFFLINE.md)。

## 使用已有项目

输出父目录须已存在、位于仓库外且归本人所有、权限0700；输出目录必须全新。示例路径需替换为实际路径：

```sh
.venv/bin/python -B -m lutphoto.offline preview \
  --project "/private/tmp/A7C2-private/style/project.json" \
  --input "/private/tmp/A7C2-private/style/reference.png" --st-input \
  --directory "/private/tmp/A7C2-private/preview-001"
```

可选`--masks`、`--assume-srgb`及`--validation-lock`沿用原格式。单图最多400万像素；需要缩小时另存参考图，原图不覆盖。输入只接受受支持的8位RGB JPEG/PNG和明确色彩解释。

`--st-input`只表示使用者声明参考适合该暂定ST模型，不能从sRGB标签推断Sony ST；普通JPEG不能据此成为真实标定。电影Log LUT需要有依据的ST→目标输入桥接，不能只改标签；DCP/自动桥接不在此入口范围。没有真实模型时可用自制图/暂定响应考察软件和表达能力，结果不预测机内效果。不同固件的真实材料不能混成同一已验证模型。

## 没有项目时先看自制例子

下面创建仓库外私人临时目录，使用公开自制恒等CUBE/图/单位响应模型，输出位置由程序打印；全是软件示例，不是Sony ST标定：

```sh
.venv/bin/python -B - <<'PY'
from pathlib import Path
import tempfile
from lutphoto.nativefit import fixtures
from lutphoto.offline import preview
root = Path(tempfile.mkdtemp(prefix='a7c2-preview-')).resolve()
fixtures(root / 'input')
result = preview(root / 'preview', project=root / 'input/project.json',
                 photo=root / 'input/chart.png', st_input=True)
print(root / 'preview/RESULT.md')
print(result['phase'])
PY
```

准备自己的CUBE时，按[项目契约](NATIVE-FIT-OFFLINE.md#项目与模型契约)填写真实输入域、输出sRGB、素材来源和模型依据，事先声明阈值。不会自动下载LUT或拿其他机型/单位矩阵冒充本人标定。

## 输出和通过含义

| 输出 | 内容 |
| --- | --- |
| `RESULT.md` | 两张图、整体误差、系数触限/范围、裁切计数、超限原因及显式分区表 |
| `candidate/` | 原N2的`candidate.json`和`correction.table`，不是固件或可直接安装文件 |
| `evaluation/` | 带sRGB配置的`reference.png`/`prediction.png`与`comparison.json` |
| `preview.private.json` | 来源/候选/图片绑定、留出与本图误差、灰阶/中性信息、失败项、完整拟合及未证边界 |

先看图，再看误差：原LUT参考与原生预测接近，只表示**当前暂定模型能否近似该CUBE**。系数触限表示当前表接近编码约束，预测裁切表示当前模型越出0..1；两者都不能直接定位Sony ISP故障。参考域截断按重复评估行累计，不当作独立像素数。缺少或空分区掩码明确不可用，不生成零误差或肤色通过结论。

拟合留出与本图分别核对项目事先声明的RGB MAE和Delta E76 P95，列出每个超限项，不平均掩盖失败。单图入口没有新增摄影标准；收敛、触限、剪裁比例、分区样本数/阈值和多场景正式判断继续使用[冻结验收](NATIVE-VALIDATION.md)。

CLI退出0 / OFFLINE_PREVIEW_CHECKED表示本次计算、报告保存/终端输出完成且上述整体离线阈值通过；退出1 / OFFLINE_PREVIEW_LIMITS_EXCEEDED表示图和诊断已保存但阈值未通过。其他输入/计算/保存错误也退出1、保留部分目录，不伪造完整结果；参数错误退出2。已有目录/不安全父链拒绝，不覆盖、不续跑。终端写失败不重新执行，完整报告文件不单独证明进程成功。

超限候选仍会被原`build`候选门槛拒绝；preview不接受归档、AP/CP、设备版本、启用或续跑开关，也不创建假程序/设置/回执。原demo/build行为和生产固定来源/阈值保护保留，参见[完整离线流程](OFFLINE-WORKFLOW.md)。报告保存在私人目录，不上传本人素材、路径或设置。

## 输入失败时怎么处理

第六十六轮增加固定错误编号和中文提示；预览失败时终端不打印异常原文、私人路径、LUT标题、ICC内容或未校验的JSON字段。提示标明失败环节，不代表已经精确识别底层原因；文件权限、空间或计算错误仍可能需要在本机检查。输入错误退出1，参数错误退出2；不自动修正色彩解释、放宽阈值或重试。

| 编号 | 核对与处理 |
| --- | --- |
| `PROJECT` / `MODEL` | 核对项目及模型文件/schema、ST依据、有限可逆3×3响应和事先声明的正数阈值；不拿单位矩阵当实机标定 |
| `CUBE` / `LUT_OUTPUT` | 检查UTF-8单一3D表、尺寸2–65、完整行数与有限数值；参考输出须为0..1编码sRGB，不自动裁切HDR/Log |
| `BRIDGE` / `DOMAIN` | 核对真实输入域、ST→LUT桥接依据与域策略；不能通过改标签、改域或改截断策略凑通过 |
| `IMAGE` | 使用单帧8位RGB JPEG/PNG、最多400万像素；检查完整性，另存裁图以保留原照片 |
| `IMAGE_SPACE` / `ICC` | 确认真实色彩空间并正确转换；仅对确认原本为sRGB的无标签图使用`--assume-srgb`，不覆盖冲突声明或删除ICC强用 |
| `MASK` | 使用现有区域名；8位灰度单帧PNG，仅0/255且匹配方向修正后的照片尺寸 |
| `VALIDATION_LOCK` / `SOURCE_CHANGED` | 核对冻结锁和输入绑定；不手改锁或拼接新旧结果，修正后用全新目录重算 |
| `OUTPUT_DIRECTORY` | 使用仓库外全新输出，父目录已存在、归本人所有且0700；已有结果保留、不覆盖 |
| `FIT` / `DEPENDENCY` / `INCOMPLETE` | 检查项目、Python依赖、文件权限与空间；未完成预览，保留部分结果，不自动重复执行 |

缺少`--st-input`等必需参数时显示`INVALID_ARGUMENTS`及帮助入口。Python调用者缺少ST声明会收到`ST_DECLARATION`；已归类输入异常继承`ValueError`并保留原消息供本机调试，因此不要将Python异常原文直接上传。中文提示仅供电脑端预览排错，不表示获得机内导入或恢复许可。

下一步可以先用两三个具有明确来源/输入域的CUBE和同一组已有参考图筛选一种风格；复用此入口另存各次结果即可，暂不新建批量管理框架。真实标定/机内比较按[摄影验收工作表](PHOTO-ACCEPTANCE-CHECKLIST.md)准备，实际采集仍按[D4条件](D4-HOST-READINESS.md)另行安排。
