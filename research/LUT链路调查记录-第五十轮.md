# 第五十轮：宿主、身份、认证和材料流的统一离线装配

日期：2026-10-21。交付[统一所有权演练](../docs/CAPTURE-OWNED-OFFLINE.md)，按第四十九轮交接连接宿主/MSC、受限认证/材料、Store 和检查器。仍不操作相机/移动盘，不执行真实 USB、系统相机锁、管理员命令或原生模块。用户保留原厂 2.00 及日常卡副本，不要求现在升级；卡副本不是内部 AP/CP/BK4 或可降级证据。

## 本轮交付与边界

- 新 `captureowned.rehearse` 只接收精确未用的 SyntheticSystem，不能用 NativeOps、外部 Session、子类、回调或策略代替。完整固定来源先于任何模拟宿主动作校验；旧公开演练类型门槛不变，无采集 CLI。
- 依次打开初始普通、服务、返回普通三个假句柄。普通初始和返回都执行 MSC 原始查询，认证/固定材料/stop 共用同一服务所有者/端点；不再使用 peer 提供的缓存普通身份。服务/普通“到达”只是受限假系统阶段变化，没有真实切换证明。
- 全局模型租约先于新 Store/真实作业 flock；打开结果在 ACK 前接收。关闭先失效借用视图，dispose 单次显式尝试且独立持久记录；日志失效仍释放本地对象，不借此补协议动作。健康完整响应后的内容拒绝最多一次退出，未知/释放不明不补 stop/认证/查询或重挂。
- 一个 1200 秒 Budget 覆盖宿主、MSC、认证和材料；固定材料上限另加 32 KiB 认证及 64 KiB 身份余量。身份字节包含 CBW/CSW/数据，认证 14,448 字节/31 视图调用不变；材料载荷/线路分别保留，三类相加为总量。两个完整身份查询共 28 次调用，不重置期限。
- 增加第四种 owned 报告/只读检查：三角色唯一关闭、宿主操作顺序及其位于外层材料确认序列的位置、两次身份查询、共享计数、真实/写入标志 false。宿主同名动作的未确认记录分别保留，后续 ACK 不消除旧未知。原三格式不放宽，混入宿主证据不能冒充完整。
- 内部 NativeOps 明确缓存 libusb-package 后端解析结果，每次枚举显式传入后端；缺失即停止，仅用假模块/SDK 验证。没有导入实际 SDK、调用动态库或接通真实入口。部分管理 API 没有 timeout，仍只在返回后检查期限，不能保证中止阻塞；延迟重枚举尚未实现。

完整报告在三个所有者均关闭后、模型全局/真实作业锁内发布，再关闭 Store/作业锁，最后释放模型全局租约。Store 关闭/解锁失败会抛错，即使已经留下完整报告也不能把整个调用视为成功；检查器只检查目录一致性，不证明此类后续操作。主错误和清理错误保留类型，原始异常、身份、路径、报文不进报告。

保留 QAQLeonard/ma1co/ajalt 来源和完整许可；11/9/10/14 与旧 N1/FL23 锁不改，不发布密钥/固件/资源或私人材料。新报告真实源、认证、协议、新鲜观察、系统锁、恢复、写入和续跑标志全部 false。完整正例仅自动测试中的 tiny 自制程序策略，原厂真实材料正例仍缺。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_captureowned.py' -v` | 新统一专项 37 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_capturemac.py' -v` | 49 项通过，新增后端/原始控制/释放日志 4 项 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_captureraw.py' -q` | 既有受限接口 36 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_captureinspect.py' -v` | 既有只读检查 40 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究 707 项通过，包含新增 41 项 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧 Mac 39 项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游 8 项通过；合计 754 项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产通过，未连接相机 |
| `.venv/bin/python -B research/output/custom-round50/audit_capture_sources.py` | 57 条 AST 观察、45 来源身份，新 11/既有 9/10/14、N1 的 26/旧 46 成员通过，无设备导入或归档执行 |
| `.venv/bin/python -S -B research/output/custom-round50/exercise_owned.py` | 6 个实际固定来源/自制材料统一流程和真实只读 CLI 场景通过，临时输入保留校验后清理 |
| `.venv/bin/python -B research/output/custom-round50/audit_public.py` | 公开 AST/JSON/链接、隐私资产、锁/归档/受保护路径与精确发布清单通过 |
| `git diff --check` | 通过 |

专项覆盖 6/74 材料、同服务对象、第三个返回句柄和原始查询、共享对象/期限/计数、全局→作业锁和发布/关闭顺序、实际 inspect 对活跃作业拒绝、版本/外部类型/已用对象拒绝、已有目录不接收设备、端口/序列号变化、锁忙、MSC/认证/材料/stop 未知、OPEN/释放 INTENT/ACK 故障、持续日志不可用、已知 stop 与释放失败分离、清理主错误优先及 Store/解锁错误传播。

检查篡改另覆盖缺确认、重复/错角色关闭、宿主顺序、身份计数、真实标志、把新证据换成旧报告及 -S 无 USB 导入。实际只读 CLI 的自制完整格式通过，不改变内容/inode/权限/mtime/ctime；不承诺 atime。

首次生成检查器字段时插入位置误落在 FALSE_COMMON 名称中，导入检查发现后已修正。篡改测试还发现同名宿主动作可能覆盖旧待确认记录，已改成分别保存并检查阶段位置，最终全量回归通过，没有放宽来源、指纹、长度或真实标志来消除失败。

实际固定归档演练仅 AST/元数据/内存密钥校验，SHA-256 包预期独立由标准库计算，没有执行归档 Python 或目标模块。全尺寸全零 AP 99,960,744 字节必须被原厂策略拒绝，不读 CP/快照；其余场景是半包、认证控制不明、材料发送不明、服务 dispose 不明和返回身份变化。六种真实 -S 检查 CLI 均预期退出 1，分类依次未完成/未知/未知/未知/未知/未知；已接收句柄均只显式尝试一次 dispose，不明返回不能算明确关闭。

192/140/52/78/142/186 项输入（含目录）前后内容、inode、模式及写/状态时间不变；临时自制材料清理。汇总只留忽略的 `research/output/custom-round50/`，不公开真实密钥、挑战、应答、身份和私人路径。本轮没有真实完整原厂材料或实机兼容证据。

## 交接与发布

总计划仍四列，本轮只更新 N3；滚动交接/索引独立维护。已有本地分析报告/计划附录保持原字节、不发布；私人目录不读取或暂存。旧安装器、指纹、偏移、锁、原测试、依赖、默认单份备份和历史归档不改。起点 `1d161948cb25c91b0bf7776f1ec5151d6166a2f1` 的[第四十九轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39558401208)completed/success；提交前列出实际测试，只正常推送 lut-photo/main，提交/新 CI 以最终报告为准。

第五十一轮聚焦原生管理阻塞/中断边界、受限延迟重枚举及入口前只读预检，继续离线故障验证；不得直接杀死/重试未知服务流程来假装获得时限保证。决定真实入口前必须明确环境/权限、来源与版本门槛、取消后现场保留及同一所有者释放策略。

真实 MSC/CSW/服务端点/回显/排空、原厂完整材料和新鲜同机来源仍需受控验证，进入前提示；当前不需要升级 2.01、连接相机、Docker、惠普电脑或读取移动盘。第三方修改升级包须单独固定仓库/版本并审阅迁移/恢复，不借其替代原厂门槛。事务/bound worker/恢复、双独立介质、N4 色彩验收后置；真正 3D LUT 支线维持第二十八轮未闭合状态。
