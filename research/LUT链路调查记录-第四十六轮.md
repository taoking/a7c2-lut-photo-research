# 第四十六轮：认证报文与退出错误传播的离线适配

日期：2026-10-20。交付 [captureauth](../docs/CAPTURE-AUTH-OFFLINE.md)，在精确的假驱动上验证原始传输结果、两段认证、同端口转换和一次退出。独立于现有材料协调器，没有真实采集入口。没有相机/USB 枚举、设备命令、sudo、系统相机锁、原生模块或私人机身材料读取。官方升级/日常备份仍未收到完成结果，不推断。

## 本轮交付与证据

- 新增独立 9 成员认证来源锁，固定同一 v2.1 包及 SHA，核对各成员长度/SHA/Git blob。只 AST 解析固定密钥布局，密钥/挑战/原始应答不写入仓库或报告。保留 QAQLeonard、ma1co、ajalt/python-sha1 来源及现有 MIT 许可。
- 审阅确认：PMCA start/stop 吞 GenericUsbException；GenericUsbDriver 与 libusb 两层还丢弃发送/控制返回长度。独立模型要求控制请求明确 int 0、发送明确 int 516、响应一次不可变 bytes 516，不能用旧方法的 None/无异常代替确认，也不改旧安装器。
- 固定大端认证包、三轮挑战/应答及结束状态；普通 PID 只取挑战前四字节，服务 PID 使用全挑战加对应轮密钥。复现源码 SHA-1 的低五位字节长度字段，支持 SHA-256、混合轮次及非零 salt。
- 同一个 120 秒/32 KiB 默认预算贯穿两段认证和退出，单调用最多 5 秒并消耗剩余期限；长度有效的完整双阶段为 14,448 认证字节、31 次假调用。计数不是未知短包的实际线路总量，也不含 USB 请求头或材料流量。
- start、整段认证、stop、正常返回核对均先持久化 INTENT 再动作、返回后 ACK。意图失败零发送且冻结；未知后不重认证、stop 或清理；完整返回后 ACK 失败保留已知阶段但禁止重发。退出许可在日志成功后、调用前仅消费一次。
- 严格同端口/唯一服务转换和同来源普通身份匹配。`STOP_CONTROL_RETURNED` 只代表主机假控制返回，`SIMULATED_AUTH_COMPLETE` 只代表自制认证流程；正常观察是调用方提供的假事实，没有重新查询设备或证明新鲜度。所有真实认证、协议/机身、系统锁、恢复/续跑/写入标志 false。

实际固定归档的源码核对通过 38 条 AST 观察、33 个来源身份，包含 9/10/14 成员及 N1 的 26/旧 46 成员。生产模块不执行归档 Python；本轮独立对照**执行了三个固定、审阅过的纯主机哈希函数**，只提供 struct、len、range，核对 13 种自制长度和完整报文的独立预期。未执行归档设备模块或目标代码，未导入 USB/旧 Session，也不把主机哈希执行称为“零归档代码执行”。

## 实际测试命令与结果

起点 `3a77192af336a06b172ce00959d2acac746cfffe`，[第四十五轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39413612040)已 completed/success。

| 实际命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_captureauth -q` | 新专项 34 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -q` | 研究 536 项通过，含新专项 |
| `.venv/bin/python -B -m unittest discover -s tests -q` | Mac 39 项通过；提示来自模拟 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q` | 旧上游 8 项通过；合计 583 项 |
| `.venv/bin/python -B -m macfl23 check` | 固定源码/资产通过，无设备操作 |
| `.venv/bin/python -S -B research/output/custom-round46/audit_capture_sources.py` | 38 条源码观察/33 来源身份、既有固定清单通过；该脚本只读/AST，不执行归档代码 |
| `.venv/bin/python -S -B research/output/custom-round46/exercise_auth.py` | 执行固定纯主机哈希参考；13 个长度及 8 个实际固定来源假驱动场景通过，无设备 I/O |
| `.venv/bin/python -B research/output/custom-round46/audit_public.py` | 公开文本/AST/JSON/本地链接、隐私资产、锁/归档/受保护路径与精确发布清单通过 |
| `git diff --check` | 通过 |

专项覆盖自制密钥/挑战的独立报文预期、两种哈希与混合轮次、非零 salt、短/过长/可变响应、None/布尔/短发送、异常/超时/中断、非法状态和端序、同端口/来源拒绝、共享期限/剩余额度、INTENT/ACK 各阶段失败、stop 不重发、调用顺序/策略覆盖拒绝及 -S 无 USB/额外密码包/NumPy 导入。测试不依赖未发布归档。

固定归档场景为 SHA-1、SHA-256、混合轮次三个完整自制流程，以及控制无计数、短发送、短响应、第二段超时、stop 超时五个拒绝流程；完整流程比对所有 14 个发送包，未知后所有后续动作零发送。仅汇总场景/计数/状态及公开来源身份，未输出密钥/挑战/应答。私人自制临时目录已清理，报告仅留忽略的 `research/output/custom-round46/`。

首次专项有三个测试循环错误地在独立故障案例间共用累计预算；测试改为每个独立流程各自建预算，单流程仍共享，不放宽限制。源码观察脚本首次用了错误的 libusb 类名，改为实际 UsbBackend 后通过；未修改固定源或生产逻辑来消除该检查失败。

## 遗留与交接

本模块尚未接入 capturesession 或材料协议，旧假认证保持原状。独立认证摘要/日志不是完整采集证据，旧 captureinspect 不能据此判完整。下一轮在自制流程中装配原始认证与固定材料读取，统一预算、日志/阶段及单次退出，并让检查器识别新增格式；不把 SyntheticPeer/Driver 直接换成真实 Session。

再后续独立实现/审阅受限 USB 接口、MSC 接管/重挂、真实全局锁、句柄生命周期；真实响应/回显/排空与正常身份新鲜查询须另验。材料角色/外层容器/新鲜同机来源、完整事务/bound worker/恢复和独立介质仍缺；N3 只部分完成，N4 真机/色彩后置，进入前提示，目前不需相机、Docker 或惠普电脑。

总计划只更新 N3 一行、仍四列，交接滚动覆盖、轮次单独记录。已有工具分析及计划附录保持原样且不纳入发布；只暂存本轮源码/测试/文档与 N3 行。旧安装器/锁/指纹/偏移/测试/依赖/默认单份备份及历史归档未改；只正常推 lut-photo/main，提交/远端与新 CI 状态以最终报告为准。真正 3D LUT 支线仍保留第二十八轮未闭合状态。
