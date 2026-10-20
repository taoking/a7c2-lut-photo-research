# 第四十四轮：会话协调的离线装配

日期：2026-10-20。新增[离线会话协调](../docs/CAPTURE-SESSION-OFFLINE.md)，将固定请求、主机存储与自制身份/认证流程装配。没有设备 CLI、USB、真实系统相机锁或真实认证；本轮未枚举/操作相机、sudo、运行目标模块或读取私人机身文件。官方升级/日常备份仍未收到实际完成结果，不推断已完成。

## 交付与边界

- 新 `lutphoto.capturesession.rehearse` 只接受精确的 SyntheticPeer 和固定归档，不接受真实后端、锁回调或策略覆盖。模型先取得假全局锁再取得真实私人作业 flock，退出/材料核验/报告发布完才释放；旧 `/var/run` 锁路径仅为常量，从未打开。
- 普通身份与返回身份均要求同一种 `sony-get-camera-info` 观测、Sony/ILCE-7CM2、唯一普通身份/无服务身份及完整总线/物理端口；两段假认证之间要求唯一同端口服务身份。没有 busy/no-media 补认、已有服务重认证或 PID 返回即成功的分支。
- 每个假认证/身份查询和固定 select/read/HASP/快照独立持久化 INTENT/ACK；未知认证/半包/超限/中断/载荷写错误停止。完整响应后内容/格式/复读/同步拒绝最多一次有日志的健康退出；stop ACK 先更新内存再写日志，不因 ACK 同步失败重复退出。本地主机关闭也不重复尝试。
- 原厂 AP 完整长度/SHA 先通过才读 CP；完整配对通过后采 RAM/保存快照、可选 68 资源，再程序/资源复读及结束范围观察。全部原件排他保存、同步读回；BK4 仍不推断芯片角色、外层容器或原子时刻。
- 协议模型新增显式守卫模式，从固定 13 个临时名与 preload 导出 14 路径，共增加 28 个固定 select/read。只在守卫 read 接受完整 missing 状态且无额外载荷；存在包括空文件都停止。每项载荷最多 4096 字节、只 hash、不保存/清理；首末均检查，不证明观察间没有变化或路径清单穷尽。
- 逐请求日志的完整资源流程超过 512 事件，Store 增加显式最多 2048 的容量，默认仍为 512、每项仍 16 KiB，并计入空间预检。原 SyntheticTape 入口、旧安装器/锁/哈希/偏移/测试/依赖/默认单份备份不改。

## 源码发现及后续限制

固定来源仍是 QAQLeonard v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90` 与 ma1co Sony-PMCA-RE，保留署名/许可。26 条 AST 观察覆盖 27 个来源身份，10/14、N1 的 26/旧 46 成员重新核验；没有执行归档 Python 或目标代码。

固定 PMCA 的 `SonySenserAuthDevice.start/stop` 会捕获 `GenericUsbException` 后返回，旧 Mac `_close` 等待普通 PID 而不重新查询同源身份。本轮新模型补上假身份前后复核，但**没有解决真实控制传输异常被吞掉的问题**；不能把旧方法返回 None 映射为新模型的成功 True。后续设备适配必须独立审阅错误传播、认证响应、剩余期限与句柄生命周期，保留旧安装器原行为。

pFunc 回显/零字段仍为保守实验限制，排空结果内容不能证明真实 USB 边界；系统锁/MSC 接管/认证/正常返回、真实完整程序成功材料均未证。报告所有真实来源/机身/协议/锁/角色/容器/新鲜度/独立介质/原生运行/恢复/写入许可标志为 false；模拟完成不能作为安装依据。默认假版本、电量和身份是自制夹具，不是用户相机观测。

## 实际测试命令与结果

起点 `5698d5846657e44e254564dcee0b61e6e8505382`，[第四十三轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39398500563)已 completed/success。

| 实际命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_capturesession -q` | 新专项 37 项通过 |
| `.venv/bin/python -B -m unittest research.tests.test_capturesession research.tests.test_captureprotocol research.tests.test_capturehost -q` | 相关 118 项通过，包含新专项，不重复计入总量 |
| `.venv/bin/python -B -m unittest discover -s research/tests -q` | 研究 462 项通过 |
| `.venv/bin/python -B -m unittest discover -s tests -q` | Mac 39 项通过，服务提示来自模拟 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q` | 旧上游 8 项通过；合计 509 项 |
| `.venv/bin/python -B -m macfl23 check` | 固定源码/资产通过，无设备操作 |
| `.venv/bin/python -S -B research/output/custom-round44/audit_capture_sources.py` | 26 条 AST 观察/27 来源身份和固定清单通过，无归档代码/设备导入 |
| `.venv/bin/python -S -B research/output/custom-round44/exercise_session.py` | 实际固定归档 14 守卫/171 扩展请求通过；全尺寸自制全零 AP 99,960,744 字节预期拒绝，仅一次假 stop，不读 CP/快照；重跑拒绝且原 86 文件 SHA 不变，包 SHA 不变 |
| `.venv/bin/python -B research/output/custom-round44/audit_public.py` | 公开文本/AST/JSON/本地链接、隐私资产、固定锁/归档/受保护路径及精确发布清单通过 |
| `git diff --check` | 通过 |

新专项含完整 6/74 项材料、逐动作意图先落盘、锁顺序与发布范围、原厂指纹门槛、同源身份/总线/端口/唯一性、两段认证中断、空/非空/超限守卫及 preload、结束变化、状态 missing 的严格范围、发送前日志与 stop ACK 失败、磁盘/同步/中断、一次退出/本地关闭、旧目录拒绝、容量边界及 -S 无 USB/Session/NumPy 导入。正例只在测试内注入自制 tiny 策略，没有真实机身材料正例。

实际固定归档练习执行 31 个请求/83 条日志，未放宽固定原厂指纹。自制全零程序与临时目录已清理，观察/练习/公开审计报告仅留忽略的 `research/output/custom-round44/`；没有上传材料、身份或私人路径。

## 交接与发布

总计划仅更新 N3 一行，仍为四列；滚动交接及轮次索引更新。开始时已有工具分析报告与计划附录原样保留、不纳入本轮发布；只暂存本轮源码/测试/文档与 N3 行。提交前列出实际命令/结果，只正常推送 lut-photo/main，提交、远端和新 CI 结果以最终报告为准。

下一轮先做旧演练目录的只读检查与中断分类：目录/文件/日志链、未完成 INTENT、报告及材料一致性，输出有限私人证据，不重建/续跑/清理或将模拟状态升级为真实验证。仍仅使用自制临时材料；本人明确授权已有路径后才读私人材料，不搜盘。

真实认证异常传播、MSC/USB/全局锁与句柄适配独立后续开发；真实协议轮廓/排空、机身材料角色/外层容器/新鲜来源、完整事务/bound worker/恢复、独立介质仍缺。N3 部分完成，N4 实拍/色彩/冷启动与恢复后置，真正 3D LUT 支线保留第二十八轮未闭合状态。当前无需相机、Docker 或惠普电脑，进入实测前提示，勿用 prepare/diagnose 取材料。
