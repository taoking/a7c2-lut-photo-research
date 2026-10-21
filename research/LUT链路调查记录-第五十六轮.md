# 第五十六轮：内部原生装配、独立证据与完整调用回执

日期：2026-10-21。交付[内部装配与独立证据](../docs/CAPTURE-EVIDENCE.md)，落实第五十五轮审阅的报告/结束判定缺口；C1内部接线完成，尚余公开设备入口、输出失败/退出码和准入收口。**公开capture仍无条件拒绝，本轮没有设备采集CLI或实际相机操作。**

没有实际SDK/共享库、USB/系统相机锁、sudo/磁盘命令、机内模块或移动盘/私人材料读取。实际信号只发给刚创建的自制子进程。本人原厂Ver.2.00及日常卡副本保留，不要求升级、连接或准备Docker/惠普电脑；卡副本不是内部AP/CP/BK4、恢复或降级证据。

## 实际交付与限制

1. `captureexecution`直接复用NativeOps/Host/_OwnedRun/固定协议/Store。预留私有_capture将来源/电脑/声明版本电量前置、固定NativeOps、共享预算与显式信号/全生命周期接通，不接收任意后端。它不是绕过公开入口取材料的工具。
2. 新检查点保存随机作业号、来源/声明条件、初始/新返回MSC观察、6/74材料、账目/日志；锁内排他写入，checkpoint_only=true，不声称作业/租约/信号已结束。独立事件白名单拒绝旧MODELED/SYNTHETIC记录，不转换模拟报告或批量升级false标志。
3. 回执在Owner/Store/租约/信号还原和最后取消检查之后返回，绑定context及检查点完整SHA/长度；首错误和有界原因链/次要类型保留。报告后取消、Store/租约/信号还原失败均非成功，不在锁外重开作业补写。完整材料不再掩盖调用失败。
4. Store/Reader关闭一个描述符失败仍尝试其余项，材料Sink也先失效、单次尝试，不重试结果不明关闭；初始化主错误保留。Owner记录本地关闭类型，Host保留租约释放确认和真实返回查询观察；单次SDKdispose不等于物理恢复。
5. 新 `captureevidence inspect`只读命令区分材料/终态，核对严格schema/字段/图/计数/实际哈希及回执绑定。程序先于设置、四快照/两守卫的位置重新计算哈希链后仍须正确；原四种模拟格式/分类保留。声明native和自制SDK分别分类，都不是签名、原厂策略重验、真实SDK/机身或恢复/写入许可。

旧FL23安装器/默认单份备份、旧锁/指纹/偏移/依赖/测试及历史计划不改；QAQLeonard/ma1co/ajalt固定来源/署名/许可保留。不发布程序、设置、资源、密钥/身份/私人路径。N3仍部分完成，C2本人材料、C3事务/worker/迁移、C4恢复/独立介质和C5实拍均缺，真正3D LUT支线不升级为已证，不按测试数提高总进度。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_captureexecution research.tests.test_capturesignals -q` | 新24+原信号24，共48项通过；新内部流程含4个真实自制子进程信号场景 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_capturemac.py -v` | Mac宿主49项回归通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究830项通过，无重复发现TestCase |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧Mac39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游8项通过；全量合计877项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产通过，未连接相机 |
| `.venv/bin/python -B research/output/custom-round56/audit_capture_sources.py` | 104条AST观察/53来源身份，固定N1/旧源/宿主11/认证9/加载10/worker14清单通过，无SDK导入/归档执行 |
| `.venv/bin/python -S -B research/output/custom-round56/exercise_execution.py` | 固定来源八种故障、内部装配/实际新检查CLI与终态绑定通过；一未完整/七未知，均预期退出1/MATCHED_FAILURE |
| `.venv/bin/python -B research/output/custom-round56/audit_public.py` | 公开AST/JSON/链接/隐私/密钥排除、受保护路径/锁/历史与精确清单通过 |
| `git diff --check` | 通过 |

专项初版16项通过；增加公开预留接线、畸形输入/错序/检查关闭失败与子进程后46项组合通过。补充显式原因链后47项首次有1个断言失败：原断言只期待SignalScopeError，实际同时保留其OSError原因；更新断言要求两类都保留后47项及初次全量829项通过，没有删用例或放宽成功条件。最后补齐存储空间前置拒绝的context留证，并将材料Sink关闭改为先失效、单次尝试，扩展既有关闭用例；最终专项48项、研究830项通过。

初始回归使用完整模块名组合 `research.tests.test_capturehost research.tests.test_capturemac research.tests.test_captureinspect research.tests.test_capturecandidate`，其中test_capturemac的既有顶层test_capturemsc导入找不到，退出1。改用上表真实discover命令后49项和全量通过，未改既有导入来掩盖错误。最终不把该初始调用计为通过。

四个新子进程场景为配置SIGINT、材料SIGTERM、stop SIGTERM、dispose SIGINT。父进程确认SDK未返回时取消已观察、所有者/租约/ACTIVE_JOB仍在、协议计数不增，再放行假调用；返回后OperationCancelled/NEEDS_REVIEW、未知分类、无新协议、单次dispose、处理器还原，实际设备标志false。加上旧四场景，全量共八个真实自制子进程信号场景，均无实际相机/SDK操作。

固定来源练习仅把密钥读入内存，独立标准库SHA-256构造认证预期，不执行归档/原生代码。99,960,744字节全零AP按原厂策略拒绝，不读CP/设置，无原厂正例。其余覆盖半包、认证控制不明、材料发送不明、服务dispose不明、返回身份变化及两段等待耗尽。198/144/54/82/146/192/140/231项自制输入（含回执）前后内容/inode/权限/mtime/ctime不变，不保证atime；临时输入已清理。信号作用域在这八次练习中无取消并正常还原。

## 发布与交接

起点 `1b2508f03e07dc36736743666f2a1bb2e64ee90e` 的[第五十五轮CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39593144166)已核对success。仅更新总计划N3四列表、滚动交接及独立轮次；原分析报告/本地计划附录保留，PRIVATE在读取内容前排除。仅显式暂存本轮公开文件，计划只暂存主表；正常推lut-photo/main后核对远端/CI，实际结果见最终报告和忽略目录custom-round56/publication-receipt.json。

第五十七轮收口公开首次采集入口、结构化前置拒绝、最终回执输出/真实退出码与stdout失败处理；复用既有内部装配和SDK夹具，不新增平行模拟层或按单个故障拆轮。复核root上下文/输出所有者及实际范围；完成前维持公开设备拒绝。C1完成后才提示本人C2原厂2.01、电量/连接/管理员配合及固定读取临时状态变化，不自动搜盘/prepare/diagnose，也不提前要求当前2.00升级。

C3–C5及双独立介质/恢复/真实色彩仍后置，备份不是救砖保证；真正3D LUT保留原可行性缺口。完整交接见[HANDOFF](HANDOFF.md)，记录格式/实际命令见[证据与回执](../docs/CAPTURE-EVIDENCE.md)。
