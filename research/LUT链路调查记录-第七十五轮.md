# 第七十五轮：R2服务身份审阅与四快照核对

2026-10-25；基线`d94a462`，承接[第74轮](LUT链路调查记录-第七十四轮.md)。本轮交付了服务快照身份解析、旧摘要编码兼容，以及现有完整采集中的四份快照身份核对。**R2部分完成，服务优先入口尚未接通，旧MSC查询故障未定因。** 没有枚举USB、认证、读取相机或执行更新；D4真实材料仍0。

## 已交付

[captureidentity](../lutphoto/captureidentity.py)是纯电脑端解析器，不含USB、会话或CLI能力。调用既有`bk4.parse_snapshot`完整校验恰好两份有效图像，固定取第一份的`0x00e70003`属性，要求四字节。摘要输入为保留前导零的小写十六进制ASCII文本，与旧`getCameraInfo`相同；不是原始字节、整数或大写文本。返回独立的`sony-service-bk4-00e70003`来源标记，不伪称MSC查询。

显式比较函数接受旧上游的型号/摘要二字段绑定或带已知来源的三字段绑定；严格拒绝错误型号、非法摘要、未知来源和额外字段，不改写原绑定，也不搜索/自动认领旧备份。第一份图像选择来自上游的位置约定，不独立证明AP/CP物理角色、数据来源或新鲜度；第二份存在同名属性时仍固定取第一份，第一份缺失时不回退搜索。

[captureexecution](../lutphoto/captureexecution.py)在每份快照原有接收、落盘、完整解析及作用域检查后，从同一已核验本地文件解析身份，与本次初始MSC观察比较。覆盖初始/结束RAM与保存态四个位置，未增加设备请求。身份缺失或不匹配停止继续读取；在协议已完整响应且会话健康的条件下，仍只执行原有的一次退出和新MSC身份查询。未知协议结果保持未知，不进行退出补发。

型号、同端口/唯一设备、固定完整AP/CP指纹、资源复读、保存态比较及首末守卫均保持。检查点/1、回执/3与原独立检查器未改；`SNAPSHOT_FORMAT_CHECKED`没有新增身份认证含义，检查器不重新解析BK4，也不因新代码追认旧回执具备新增身份检查。旧初始/返回MSC来源和顺序仍然必须真实满足。

## 上游对照与未接通原因

审阅QAQLeonard固定3.0.3提交`782785641ca9f8b984940c7274b48706219e0da4`。本轮复用第73轮公开源码副本，并获取同一提交的`core.py`补齐解析依据；没有执行这些文件，也没有重新宣称它是查询时最新版本。

| 环节 | 固定上游3.0.3 | 本项目及本轮决定 |
| --- | --- | --- |
| 入场型号 | USB产品字符串检查，再进入服务 | 当前仍为MSC协议查询；型号字符串不能替代唯一身份，服务优先入口待接入 |
| 唯一身份 | 服务认证后读取RAM快照，`backup_records(snapshot)[0]`取四字节属性 | 纯解析和旧摘要兼容完成；已用于完整采集四快照核对，未替换入场流程 |
| 解析证据 | `backup_records`按扫描顺序收集有效BK4；`service_identity`测试模拟该函数 | 本项目实际解析自制双图像，检查长度/校验/数量；两者都不是本人真机角色证据 |
| 设备位置 | 按PID选择唯一对象 | 保留本项目唯一对象、总线/物理端口及新句柄位置检查 |
| Mac退出 | `Session.__exit__`等待普通USB出现 | 本项目需新句柄再次查询并匹配MSC身份；不能把仅重现写成身份已核对 |
| 失败处理 | 包含冷却、服务进入重试与独立只读救援路线 | 本轮不迁移；未知即停，保留单次健康退出与原总期限 |
| 程序策略 | `core.patch_program`以被修改窗口为守卫，不要求完整固件来源白名单 | 不迁移该策略，继续固定原厂2.01完整AP/CP长度与SHA |

现有认证流程要求入场时已取得真实MSC身份；现有检查器要求两次MSC查询、完整程序先于四快照及完整6/74材料顺序。因此不能只替换一个函数，或将服务观察标成MSC、用占位摘要通过旧契约。下一步限定为有限服务优先入口及独立结果：明确身份来源、尚未检查的程序/材料，以及实际退出证据；不是重新建设通用会话框架。当前没有可运行的小样本CLI，完整入口仍会先碰到旧MSC查询。

固定来源与摘要如下，QAQLeonard/ma1co署名和MIT边界见[致谢](../ACKNOWLEDGEMENTS.md)：

| 文件 | SHA-256 |
| --- | --- |
| [src/camera_runtime/transport.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/src/camera_runtime/transport.py) | `52f2c34f4b5c5d2361a7a5869320fec3711b753299a74fd814a87129d1a9d10a` |
| [src/camera_runtime/core.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/src/camera_runtime/core.py) | `0492a4f066f53dbd679838ed0e65e5e143750239e43c6cac783c10dbfe5ae412` |
| [dev/usb/tests/test_service_identity.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/dev/usb/tests/test_service_identity.py) | `d54495a622eabe1bc49ac2654153c1ea5c2a8c5f2dbb763b3d4a76e47d1bb0c0` |

## 实际验证

现有Python 3.14.6；全部使用自制材料/对象，日志保存在忽略目录`research/output/custom-round75/`。新增11项解析/绑定测试和2项完整装配测试；后者遍历四个快照位置验证错误机身停止及既有退出，并验证属性缺失停止。修改共同装配测试材料，使其包含与自制MSC查询一致的序列属性；未修改真实材料或用模拟解析替代生产解析。

| 命令 | 实际结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_captureidentity research.tests.test_captureexecution research.tests.test_capturecamera research.tests.test_captureowned` | 退出0；102项通过。首次运行暴露新增测试辅助函数将`None`替成默认样本的问题，修正为直接调用被测函数后通过；没有据失败修改生产边界 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 退出0；1058项通过，包含上述专项，不重复相加 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 退出0；39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 退出0；8项通过，是既有固定旧上游测试 |
| `.venv/bin/python -B -m macfl23 check` | 退出0；固定源码与资产完整，无设备访问 |
| `.venv/bin/python -B research/output/custom-round74/check-legacy-receipts.py` | 退出0；复用已有脚本，用基线旧解析器/会话生成完整、未知中断、已知内容拒绝三类自制回执，当前检查器保持分类/字节/不续跑边界，未加载USB SDK |
| `.venv/bin/python -B research/output/custom-round75/check-round.py` | 退出0；文档链接/锚点/格式、固定来源摘要、既有改动保留、旧操作文件及新变更范围检查通过；不检查远程链接实时可达性 |
| `git diff --check` | 退出0；旧固定锁、依赖、MSC/宿主/认证/所有者/独立证据检查器均未改 |

合计1105项离线回归。解析测试包括前导零/零与全FF值的编码兼容、错误机身、型号、属性长度/位置、双图像数量与校验失败、只读输入、严格字段及无USB导入。这些合成值仅验证编码，不表示真实序列号有效性已获物理认证。既有备份兼容是显式摘要算法比较，没有读取本人内部备份正例；上游测试没有在本轮运行，不能计为本机实测。

## 交接与范围

原定“两轮电脑工作加一次小范围真机”的前两轮已用完，但服务优先入口仍未交付，保留这一偏差。下一步只补上述有限入口、退出判定与独立结果；不能通过增加测试数量或泛化封装宣称完成。如果仍不能满足已有约束，或之后同阶段失败而无新证据，按[交付计划](../docs/DELIVERY-PLAN.md)评估原生Windows只读对照或后置Mac。当前无需连接相机或准备Docker/Windows。

真实证据仍为第67轮MSC身份USBError、第69轮枚举ValueError、第71轮KEY_VALIDATE/BUS；没有新机身材料，旧错误根因不回填。第72轮准备继续暂停，167文件冻结已有7个既有路径变化，新增身份模块还不在旧清单内；四个操作文件/定位记录不改，不能更新旧摘要后运行。第67/69/71轮禁止重跑保持。

本轮开始时21项既有修改已在忽略目录快照；第73/74轮代码与报告、五份独立分析保留，共享文档只更新本轮状态。总计划保持四列，交接与轮次记录分离；首次采集说明纠正旧准备“等待开始”的过时措辞。未读取私人备份、调整宿主权限、提交或推送。
