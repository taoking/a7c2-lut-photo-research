# 第四十三轮：固定请求与有界协议接收

日期：2026-10-20。交付[被动协议模型](../docs/CAPTURE-PROTOCOL-OFFLINE.md)，不打开 USB、不接收驱动回调、不提供相机命令。本轮未枚举/操作设备、sudo、运行原生模块或读取私人机身文件。官方升级/日常备份仍未收到实际完成结果，不能记为已完成。

## 交付与源码依据

新增 `lutphoto.captureprotocol.OfflineChannel`，只生成固定 HASP、RAM/保存快照、AP/CP 与可选 68 资源的请求字节，默认 7/扩展 143 项。Jiritsu 只允许固定选择 15/读取 17，禁止任意路径、16/18 和 setter；读取须有匹配的成功选择，没有自动重试。原厂精确长度来自原有固定完整程序策略，没有 SHA/身份/角色覆盖。

被动接收保留独立 USB read 结果边界：12 字节头、最多 1 MiB/段、32 KiB 载荷及必要的独立排空读取。头声明/累计响应/段数、全程载荷与线路开销均有前置上限；请求/状态字/头/排空计入线路预算，共享 Sink 的总期限，最多 512 请求和 65,536 读取结果。没有默认 BytesIO 累积完整程序；状态字仅缓存 4 字节。

已完成响应的状态/长度/主机同步错误停止新读取，可在预算允许时消费一次本地健康退出许可；半包/序号/超限/中断/未完成排空/载荷写失败变为未知，不再给读取或退出许可。完成后收到额外非请求结果同样变未知并清除当前结果。许可本身不发 stop，也不证明身份/认证或 C5；真实退出还需持久化意图与正常身份复核。

QAQLeonard v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`、ma1co Sony-PMCA-RE 署名/许可及既有来源清单保留。实际归档 10/14 成员、N1 的 26/旧 46 成员通过，20 条源码 AST 观察覆盖 27 个来源身份；没有导入归档/USB Python 或运行目标代码，没有新依赖。旧安装器、固定锁/偏移、测试及默认单份备份不变。

## 协议风险与验收边界

上游只检查响应序号。本层额外要求 pFunc 回显和三个零字段，属于**未获机身证据的保守实验限制**，可能拒绝合法响应。没有凭空增加 size 必须逐段递减的断言，而用独立累计边界限制续段。

上游额外排空读取允许零长度/任意内容；即使结果形似下一段头，离线模型也不能凭内容判定真实 USB 边界。因此 `physical_protocol_verified`、`response_profile_verified` 与设备操作标志均 false，不能宣布可接通相机。单测明确覆盖这个缺口，而非伪造协议保证。

本层不验证 AP/CP 完整 SHA、BK4/UXC 内容、型号、原子快照或 C0–C5 顺序，尚未与上一轮 Tape/存储流程装配成真实适配器。HASP 88 字节与一次模型成功不构成机身认证、完整备份、写入许可或恢复证据。

## 实际测试命令与结果

起点 `5f2d3707f774bdf0547b9ddcc83b519513306eae` 的[第四十二轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39395807881)已 completed/success。

| 实际命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_captureprotocol -q` | 新专项 41 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -q` | 研究 425 项通过，包含新专项 |
| `.venv/bin/python -B -m unittest discover -s tests -q` | Mac 39 项通过，服务提示来自模拟 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q` | 旧上游 8 项通过；合计 472 项 |
| `.venv/bin/python -B -m macfl23 check` | 固定源码/资产通过，无设备操作 |
| `.venv/bin/python -S -B research/output/custom-round43/audit_capture_sources.py` | 20 条源码观察/27 来源身份与固定清单通过，不执行归档 Python |
| `.venv/bin/python -S -B research/output/custom-round43/exercise_protocol.py` | 实际固定归档的 143 请求、99,960,744 字节原厂 AP 长度通过；自制 88 字节 HASP 与空 AP 已知拒绝/一次本地许可通过，包 SHA 不变，无设备导入 |
| `.venv/bin/python -B research/output/custom-round43/audit_public.py` | 公开文本/AST/JSON/链接、隐私资产、固定锁/归档/受保护路径和精确发布清单通过 |
| `git diff --check` | 通过 |

专项使用独立黄金编码、自制字节、tiny 测试策略、真实私人临时目录和 hash Sink；涵盖固定请求/选择、整段/碎片/状态字、线路/载荷/期限预算、半包/恶意声明/累计续段、错序/额外结果、写满/中断/同步失败及一次许可。没有真实固件、备份或资源成功材料；临时自制文件自动清理，源码观察/练习/公开审计报告仅留忽略的 `research/output/custom-round43/`。单测无需归档下载，独立 -S 子进程导入确认无 USB/旧 Session/NumPy。

## 交接与发布

总计划仍四列，仅更新 N3 一行；滚动交接、轮次索引及对应说明已维护。开始时已有工具分析报告和计划附录保持原样，不纳入本轮发布；仅暂存本轮源码/测试/文档及 N3 行。提交前列出实际命令与结果，只正常推送 lut-photo/main，提交/远端及新 CI 结果以最终报告为准。

下一轮离线装配受限会话协调：固定请求与持久化意图/ACK、正常身份前后同源观测、物理端口、系统锁获取顺序、认证/退出及既有临时状态守卫。先用假事件/假锁/假认证测试，不连接 USB、不打开真实系统锁、不引入设备 CLI。协议真实轮廓/排空、旧目录只读检查及中断分类、真实材料角色/新鲜度、完整事务/bound worker/恢复与独立介质仍需后续验收。

N3 部分完成，N4 实拍/真实色彩/冷启动与恢复后置，进入前提示；真正 3D LUT 支线保留第二十八轮未闭合状态。当前无需相机、Docker 或惠普电脑，勿用 prepare/diagnose 取材料。
