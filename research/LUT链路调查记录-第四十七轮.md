# 第四十七轮：原始认证与固定材料流的离线装配

日期：2026-10-21。交付 [capturepipeline](../docs/CAPTURE-PIPELINE-OFFLINE.md)，统一认证/材料的离线顺序、预算、日志及一次退出，检查器新增第三种演练格式。本轮没有相机/USB 枚举、设备命令、sudo、系统相机锁、原生模块或私人机身文件读取，没有读取移动盘。

用户确认仍为原厂 Ver.2.00，按 BACKUP-GUIDE 保存的是相机卡副本；尚未升级 2.01，选择暂时保留版本。本轮只记录该说明，未核验备份内容、路径、完整性或内部恢复能力。卡副本不是 AP/CP/BK4 开发备份，不据此放行 2.00 或推断可以降级；离线开发不需要现在升级。若以后采用第三方修改升级包路线，须固定具体来源/版本和迁移/恢复链另审，不与当前原厂 2.01 服务流程混用。

## 本轮交付

- 精确全新 SyntheticPeer 和两个 SyntheticDriver 接入单一协调器，旧演练入口保留；原会话抽取空间预检/固定材料方法复用，程序指纹、资源/设置保护、守卫和复读规则不放宽。材料仍由独立假 peer 供帧，未证明真实共用接口、端点或句柄。
- 原始普通/服务认证按固定报文执行，去除新流程内重复的 True 假认证与假 stop。身份/端口仍是自制观察；正常返回查询的 INTENT 先于查询本身，不仅先于结果比较。
- 同一 Budget 对象、1200 秒总期限覆盖两段认证/材料/退出，单次认证最长 5 秒且取剩余时间；独立认证的默认 120 秒不改。总额度为原材料上限加 32 KiB，单材料/请求/帧/材料线路上限不改。
- 认证计数独立保存，材料不会增加 accepted_auth_bytes；accepted_payload_bytes 保留材料/88 字节查询语义，accepted_total_bytes 为两者之和，材料协议 accepted_wire_bytes 单独保留。固定完整认证为 14,448 字节、31 次假调用，不表示未知短包的实际线路流量。
- 新流程的任一日志失败冻结后续动作；认证/读取未知或中断不重试/stop/清理。完整内容拒绝且仍健康时可一次退出。退出成功的已知事实保留，即使后续正常查询失败或确认丢失，也不重复发送、不发布完整成功。
- 新私人报告/检查格式校验原始认证标记的位置、计数、阶段/冻结状态、全部材料/确认顺序及加总。独立认证摘要不能充当完整采集；缺 ACK 仍保留未确认意图，真实认证/观察新鲜度、机身/协议/系统锁、恢复/写入/续跑全部 false。

生产不执行归档模块；来源仍固定 QAQLeonard v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90` 及 ma1co/ajalt，既有 9/10/14 成员锁、N1 的 26/旧 46 成员通过。38 条固定源码观察、35 来源身份核对通过，旧安装器/锁/指纹/偏移/测试/依赖/默认单份备份和旧归档未改。

## 实际测试命令与结果

起点 `8399d7ebbb18f50d09093468afcd76220d361123`，[第四十六轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39418500186)已 completed/success。

| 实际命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_captureauth research.tests.test_capturesession research.tests.test_captureinspect -q` | 装配重构后的既有相关 111 项通过 |
| `.venv/bin/python -B -m unittest research.tests.test_capturepipeline -q` | 新专项 36 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -q` | 研究 572 项通过，含新专项 |
| `.venv/bin/python -B -m unittest discover -s tests -q` | Mac 39 项通过，服务提示来自模拟 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q` | 旧上游 8 项通过；合计 619 项 |
| `.venv/bin/python -B -m macfl23 check` | 固定源码/资产通过，无设备操作 |
| `.venv/bin/python -S -B research/output/custom-round47/audit_capture_sources.py` | 38 条源码观察/35 来源身份及固定清单通过，无归档代码执行或设备导入 |
| `.venv/bin/python -S -B research/output/custom-round47/exercise_pipeline.py` | 13 个纯哈希长度及 3 个固定来源完整装配/真实只读 CLI 场景通过；无设备 I/O |
| `.venv/bin/python -B research/output/custom-round47/audit_public.py` | 公开文本/AST/JSON/本地链接、隐私资产、锁/归档/受保护路径与精确发布清单通过 |
| `git diff --check` | 通过 |

专项包含核心 6/资源 74 项材料、独立认证包预期与混合哈希轮次、逐动作意图顺序、同源身份/端口、原厂拒绝、临时状态/坏快照、复读变化、半包/中断、认证/材料/退出/返回日志失败、共享对象/期限/剩余额度、一次退出、已有目录/外部后端/2.00 拒绝、重新计算链后的认证标记/计数/物理声明矛盾及只读/无设备导入。

首轮新专项 30 项中有 5 项失败，定位为检查器未给新格式计入 88 字节响应，以及后续返回失败时覆盖此前已知退出结果；补齐新格式载荷计算并保留已知状态后通过，未放宽阈值或升级真实标志。再补充 6 项边界测试，最终 36 项与完整回归通过。

固定归档演练使用实际固定密钥只留内存、自制挑战和纯主机参考哈希作独立预期；仅执行固定且审阅过的三个主机哈希函数，未执行归档设备或目标代码。自制完整长度全零 AP 99,960,744 字节预期被固定原厂策略拒绝，只退出一次，不读取 CP/快照；半包与认证控制无计数均未知后停止。实际 -S 检查 CLI 全部预期退出 1，分类分别未完成/未知/未知，92/85/12 项输入的内容、inode、模式和 mtime/ctime 不变（含目录项），atime 不作承诺。密钥/挑战/应答/身份/个人路径不输出，临时自制材料清理，汇总仅留忽略的 `research/output/custom-round47/`。

## 交接与发布

总计划只更新 N3 一行，仍四列；交接滚动覆盖、历史轮次单独记录。已有工具分析与计划附录原样保留，不发布；只暂存本轮文件及 N3 行。提交前列出实际测试命令和结果，只正常推 lut-photo/main，提交/远端/新 CI 状态以最终报告为准。

下一轮受限原始 USB 接口和句柄生命周期的实现/离线审阅：固定端点、原始控制/收发结果、超时和关闭所有权，以假设备对象测试，不枚举 USB、不打开系统锁、不提供真实设备 CLI。再后续才接入真实 MSC/全局锁、同句柄材料读取和新鲜身份查询；真实响应回显/零字段/排空、角色/容器/同机来源、完整事务/bound worker/恢复与双独立介质仍缺。N3 部分完成，N4 实测后置，进入前提示。

保留 2.00 及现有卡副本，不自动升级或读取移动盘；当前无需相机、Docker 或惠普电脑。真正 3D LUT 支线仍保留第二十八轮未闭合状态。
