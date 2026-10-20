# 第四十二轮：纯主机采集状态与存储

日期：2026-10-20。实现[纯主机层与自制传输演练](../docs/CAPTURE-HOST-OFFLINE.md)，没有真实采集命令或 USB 读适配器。本轮不连接/枚举 USB、不调用设备命令、sudo 或目标模块，不读取私人机身文件。官方升级/日常备份仍未收到实际完成结果，不能推断已完成。

## 交付与边界

- 新 `lutphoto.capturestore` 以目录句柄、排他创建/私有权限、文件及目录同步、完整读回、稳定 inode/锁与事件链保存材料；接收前检查块/单文件/总预算、期限和预留空间，保留失败原件/部分文件。没有覆盖、旧目录续跑或真实断电恢复。
- 新 `lutphoto.capturehost` 只接受精确的内存 SyntheticTape 类型，C0–C5 演练程序/快照/可选 68 资源、结束复读与健康退出；没有可替换为设备的后端接口。程序仍加载既有固定来源的完整原厂配对，无 CLI 指纹/身份/角色覆盖。
- BK4 仅做已有受限格式和位置对应的指定范围观察；开始/结束的 02cf 与四个 CP 键比较，诊断当前值/无关组沿用既定例外，属性/长度/reset 仍保留。RAM/保存值可不同，不执行 save/reset，不猜芯片角色或外层完整性。
- 每次假协议前先持久化意图，未知/中断/超限后不重试或退出；已知完整响应的内容错误最多尝试一次有记录的健康退出。日志不能持久化时不绕过它继续发命令。退出未知/返回身份变化/主机核验失败均不能完成。
- 完整正例只用测试内部 tiny 程序策略和自制 BK4/UXC；实际 CLI 只生成全尺寸全零 AP，证明固定策略与超限拒绝。模拟成功不证明实际来源、角色、新鲜度、独立介质、全局锁、原生执行、恢复或物理效果，所有对应标志保持 false。

沿用 QAQLeonard v2.1/ma1co 的既有固定策略及解析器/许可，没有导入归档设备代码或新依赖，没有更换旧安装器哈希/偏移/锁/测试/默认单份备份。单次模拟使用作业 flock，旧系统相机锁未打开。

## 实际测试命令与结果

起点提交 `b04a27dbaf97a5a8be0fea00e341c5428fbd24a2`，[第四十一轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39392856371)已 completed/success。本轮实际验证如下：

| 实际命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_capturehost -q` | 新专项 40 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -q` | 研究 384 项通过，包含新专项 |
| `.venv/bin/python -B -m unittest discover -s tests -q` | Mac 39 项通过；终端服务提示来自模拟测试 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q` | 旧上游 8 项通过；合计 431 项 |
| `.venv/bin/python -B -m macfl23 check` | 固定源码/资产检查通过，无设备操作 |
| `.venv/bin/python -S -B -m lutphoto.capturehost rehearse --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --directory /path/to/new-private-demo --case unknown-program` | 自建临时目录实际执行，预期 1/NEEDS_REVIEW；保留 99,960,744 字节全零 AP 后拒绝，模拟健康退出，不读取 CP/快照 |
| 同上命令，使用另一新目录及 `--case oversize` | 预期 1/NEEDS_REVIEW、未知；保留 99,942,400 字节自制部分 AP，拒绝最后超限块，无模拟 stop/重试 |
| `.venv/bin/python -B research/output/custom-round42/audit_public.py` | 待发布文本/AST/JSON/链接、隐私资产、固定锁/历史归档/受保护路径及精确修改清单通过 |
| `git diff --check` | 通过 |

专项涵盖核心/74 文件资源扩展正例、完整配对/截断/未知/已知 FL23 拒绝、超限/总预算/期限、身份/退出变化、RAM/保存差异及保护范围、目录/文件/锁 inode 变化、链接/FIFO/权限/所有者、写满/短写/文件与目录同步故障、意图未持久化时不读取、真实子进程 flock/SIGKILL、已有目录拒绝和无设备/NumPy 导入。专项按实际独立测试 40 项计数，未因引用既有夹具而重复计入旧测试。

实际 CLI 两个目录由本轮临时创建；重跑均以 FileExistsError 拒绝，原 19/12 个文件完整 SHA 不变，固定源码包 SHA 不变。自制全零程序及临时目录已清理，计数/结果只留忽略的 `research/output/custom-round42/cli-checks.json`。没有打开真实程序/BK4/资源正例，也没有编译 C 或运行原生模块。

## 限制、发布与下一轮

主机载荷边界不能代替协议头/累计包、底层 USB 超时、全局锁或相机身份绑定；现有模拟成功报告不是安装许可。失败可能留下部分事件/报告，不只凭一个完成字段判断，不能自动覆盖或恢复；真实断电/介质持久性未证。原厂固定完整程序的成功链、角色和外层容器仍缺实际材料。

保持总计划四列及滚动交接，开始时已有工具分析文档与计划附录原样保留、不纳入本轮发布；仅暂存 N3 行与本轮源码/测试/文档。提交前列出以上命令/结果，只正常推送 lut-photo/main，提交/远端与新 CI 结果以最终报告为准。

下一轮先离线审阅受限 Mac 读适配器：固定路径/快照操作的协议接收器、累计响应预算、会话健康与退出、正常身份前后绑定和旧全局锁接入。不得把模拟 Tape 换成 Session 就宣称接通，也不因已有模拟而运行设备命令；完成可审阅方案和相应测试后，再单独安排获准的真实采集。N3 仍部分完成，N4 实拍/色彩/冷启动与恢复后置，3D LUT 支线保留第二十八轮未闭合状态。当前无需相机、Docker 或惠普电脑。
