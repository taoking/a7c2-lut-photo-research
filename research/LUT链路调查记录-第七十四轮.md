# 第七十四轮：R1 Senser文件/快照读包兼容修正

2026-10-25；基线`d94a462`，承接[第73轮评估](LUT链路调查记录-第七十三轮.md)。本轮只在电脑端修改既有解析器、运行自制测试及维护文档，没有枚举USB、管理员认证、服务命令、材料读取或相机更新。R1离线完成，R2身份入口待审；D4真实材料仍为0。

## 交付与边界

[captureprotocol](../lutphoto/captureprotocol.py)取消每个512字节对齐块后的主动排空，改为按头中声明长度接收文件/快照。已有`OfflineChannel`类名和被动结果字段保留；该类同时服务合成流程与原生采集装配，本轮修正文档中“仅离线、不得接设备”的过时描述。解析器自身没有USB能力，实际设备行为仍由外层所有者记录。

| 已发现问题 | 本轮结果 |
| --- | --- |
| 对齐数据已收齐，但没有额外尾空包时仍继续读取 | 声明数据收齐后结束，不安排额外读取；512字节和32KiB边界均有测试 |
| 对齐块之后的非空续块被当成排空内容丢弃 | 所有声明内非空内容进入载荷，32768+137字节及形似包头的续块摘要逐字节一致 |
| 包头前的空传输被当作错误 | 在当前包头/数据阶段消费空传输，等待后续非空内容；跨请求留下的尾空包也由下一次正常读取处理 |

空传输计入读取次数，不能刷新全程期限；请求/头/状态/载荷继续计入线路字节上限。移除已不需要的排空字节余量，没有扩大任何材料上限。非空短头仍拒绝，包头不跨传输拼接；序号、pFunc及零字段限制保持，后两者的真实响应轮廓仍未验证。未放宽型号、固件、机身、同端口或完整程序指纹。

未收齐声明内容、超时、错序、短写和中断仍令通道未知，不补发、不重放、不自动退出。完整响应后才进行状态、精确长度和落盘检查；本地健康退出许可仍不等于真实服务已退出。没有新增直接CP单元命令、端点清理、sense、自动重认证或上游救援流程。

合成会话的逐响应生成器改为仅在后续还有数据/头时提供可选空传输。新[顺序队列测试](tests/test_captureframing.py)将尾空包保留到下一请求，经过既有`_Port.exchange`执行读写顺序，避免按解析器种类分队列或切换请求时丢掉尾包。下层只有自制对象，没有导入USB SDK；整个认证/材料流程另由已有组合回归覆盖。

## 固定上游依据

参考QAQLeonard/a7c2-fl23-research正式3.0.3，提交`782785641ca9f8b984940c7274b48706219e0da4`。本轮复用第73轮已核验的本地公开源码副本，没有再次执行下载源码或更换运行依赖。

| 固定公开文件 | SHA-256 |
| --- | --- |
| [src/camera_runtime/transport.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/src/camera_runtime/transport.py) | `52f2c34f4b5c5d2361a7a5869320fec3711b753299a74fd814a87129d1a9d10a` |
| [dev/desktop/test_senser_end_packet.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/dev/desktop/test_senser_end_packet.py) | `967e48ad5c03dc20305560facc37e88329474099160f85bf081109dfe8c2409d` |

仅参考文件/快照的按长度读取与空传输行为，在本项目既有有界状态机上实现；上游直接CP读后的特殊结束包处理不在此次白名单范围。QAQLeonard与ma1co的贡献及MIT许可见[致谢](../ACKNOWLEDGEMENTS.md)。既有v2.1材料策略、旧FL23安装器与所有固定锁均保持原样，不能把新读包规则说成旧归档已经具备。

## 实际验证

测试使用现有Python 3.14.6。输出保存在本地忽略目录`research/output/custom-round74/`，没有上传任何私人记录。

| 命令 | 实际结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_captureframing`（修改生产代码前） | 退出1；13项中1通过、3失败、9错误，确认新增边界测试会揭示旧行为；此失败是预期的修复前记录 |
| `.venv/bin/python -B -m unittest research.tests.test_captureframing research.tests.test_captureprotocol research.tests.test_capturesession research.tests.test_capturepipeline research.tests.test_captureraw` | 退出0；162项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 退出0；1045项通过，包含上述专项，不重复相加 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 退出0；39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 退出0；8项通过；是既有固定旧上游测试，不是3.0.3实测 |
| `.venv/bin/python -B -m macfl23 check` | 退出0；固定源码与资产完整，无设备访问 |
| `.venv/bin/python -B research/output/custom-round74/check-legacy-receipts.py` | 退出0；用基线旧解析器/会话生成3类自制回执，再由当前检查器核对：完整、未知中断、完整内容拒绝分类保持，文件摘要不变、续跑均未放行，USB SDK未加载 |
| `.venv/bin/python -B research/output/custom-round74/check-round.py` | 退出0；10份文档、227个本地链接/锚点及格式/个人路径检查通过；22个外部引用仅计数，17份固定公开源码摘要/长度/Git blob重新核对；6份既有报告和共享文档原修改块保持 |
| `git diff --check` | 退出0；变更范围已审阅，身份/认证/所有者/回执检查器、旧固定锁和依赖均未改 |

完整离线回归共1092项。新顺序队列覆盖三个原始反例、尾空包跨请求、载荷碎片、1MiB续段、期限/读取次数边界、短写/缺内容/错序后不重放；原有声明上限、状态字、程序精确长度、失败保存与只读证据检查继续通过。本轮不将测试数或上游Windows报告计为Mac实机通过。

## 交接与下一步

R1离线修正完成，下一轮R2优先审阅上游“USB型号→服务快照序列号”的身份入口。必须保留唯一设备/物理端口、BK4完整解析、四字节序列号旧编码、已有备份绑定、完整程序指纹和失败退出约束；不能仅删除MSC查询或把USB产品字符串当唯一机身身份。

当前MSC身份查询未修改。第67轮USBError发生在材料读取之前，根因仍未知；本轮修复不证明它已经解决。第69/71轮失败保持原记录；第72轮旧准备暂不执行，源码已变化，后续需要重新冻结与准备，不改写旧脚本中的预期摘要。

R2完成后，还须实现并审阅小范围只读入口，之后由本人主动开始R3受控验证；目前CLI没有独立小样本模式。原“两轮电脑工作加一次小范围真机”的决策预算已完成第一轮；同阶段重复失败而无新证据时，按[交付计划](../docs/DELIVERY-PLAN.md)转Windows只读对照评估或后置Mac适配。相机现场条件后续再确认，本轮无需用户接线或提供材料。

总计划、交付计划、README、当前交接与协议说明已同步。开始时11项已有本地改动已快照并保留；第73轮报告及5份独立分析不改写。本轮代码和文档保存在本地，未提交或推送。
