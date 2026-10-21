# 第六十一轮：名称worker离线绑定、原C编译与四模式报告边界

日期：2026-10-22。完成[交付计划](../docs/DELIVERY-PLAN.md)的D1，提供 `lutphoto.nameworker review/check-report` 及[使用说明](../docs/NAME-WORKER-OFFLINE.md)。复用同一私人包/目标生成器和既有编译、来源、报告及私人输出接口，没有新增模拟传输层。**D1只在离线范围完成；N3仍部分完成，D2设置、D3统一演练以及D4–D6真实材料/设备/摄影均未完成。**

本人原厂2.00、日常卡副本保留，不升级/连接或读取移动盘，不准备Docker/Windows。本轮未加载实际SDK或其共享库，未使用USB/系统相机锁、sudo/磁盘命令或私人机身材料，未执行目标代码。正例均为自制程序/策略、BK4/UXC与实际N2离线候选；原厂首次采集/导入、Mac真实加载/执行和恢复仍未证。

## 可运行交付与证据边界

1. slotbundle内部共享作用域提供已冻结输入与完整重建review；旧程序worker和inspect继续通过原三项接口访问同一Reader，包格式/150 payload/固定清单和摘要不变。名称绑定在同一共享锁内，消费后再检查元数据变化并关闭，关闭或变化未知不返回成功；不再次打开原外部输入。
2. 名称metadata绑定68文件顺序/完整原目标大小/SHA、原指针/计数、从程序身份派生的标签顺序、单槽选择/UTF-8名称、精确源/目标AP及双向重建。2860扩展/2866保留和历史顺序复用原生成器；固定C资源缓冲512KiB、最小源5740字节在编译前检查，不把宽泛的离线格式上限当C能力。
3. 备份前缀维持上游固定命名空间/16位小写十六进制规则；离线ID由包/review绑定派生，不接受用户覆盖，不是设备授权或实际新事务ID。原uid57285/gid1000保留，真实文件所有者未证。程序零窗口仍单独绑定/编译名称任务，不能以程序无变更跳过资源处理。
4. 固定完整归档与14成员、包commit/SHA一致；原names.c和SHA头原字节，独立翻译单元增加80字节Asset/字段偏移、68项元数据数组、6×64名称/68×6旧指针、完整AP数组断言，沿用Request/Report偏移、60秒Zig编译、ELF/LOAD/DT_INIT/重定位检查。头/模块/缓存临时检查后删除，不执行归档Python或目标模块。
5. check-report每次重验包并重建contract，复用136字节/四模式校验；模式0/1/2核对源AP，模式3核对目标AP，状态/phase9/68项计数/PID/reserved严格检查。请求仅内存编码/记SHA，无设备发送。报告不含资源哈希或job ID，同一AP不同名称包的报告可完全相同；新增测试明确结构可通过而report_authenticates_bundle、native_report_origin_authenticated、resource_full_readback_verified仍false，不能代替68资源完整读回或来源证据。
6. 默认标准库审阅，可选compile-names使用现有隔离环境；私人0600新报告包含完整材料指纹，不公开。stdout只阶段/编译/设备禁用摘要。成功0，材料/编译/依赖/报告/关闭/存储/输出失败1，结构参数错误2；失败保留现场，不覆盖、修复或续跑，没有模块导出/加载/安装/恢复入口。

QAQLeonard固定v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`、ma1co/ajalt署名/许可继续保留。旧安装器/锁/指纹/偏移/依赖/旧测试及默认单份备份不变。本轮额外静态核对同一完整归档覆盖的devicejob协调源码，确认名称构建传入源AP和程序目标AP；没有执行它或改变14成员锁。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_nameworker.py -v` | 最终19项通过；初版18项也通过，增加原生报告无法认证具体资源包的边界用例，无失败用例删除或校验放宽 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_programworker.py -v` | 原18项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_slotbundle.py -v` | 原22项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_workercontracts.py -v` | 原19项通过；专项共78项，不重复计入全量 |
| `.venv/bin/python -B research/output/custom-round61/exercise_compile.py` | 七组自制输入用实际固定names.c编译/ABI/ELF/LOAD通过，各四模式报告结构通过；每包152文件字节/元数据不变，临时输入已清理 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究930项通过 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧Mac39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游8项通过；全量977项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产通过，未连接相机 |
| `.venv/bin/python -S -B research/output/custom-round61/audit_sources.py` | 25条源码观察、14固定成员及5本地源码身份通过；额外协调源码由同一完整归档SHA覆盖，无归档执行/设备导入 |
| `.venv/bin/python -B research/output/custom-round61/audit_public.py` | 精确公开清单、AST/JSON/Markdown链接/锚点、隐私/密钥排除、原附录/报告与受保护路径/锁/历史检查通过 |
| `git diff --check` | 通过 |

新测试覆盖两种资源计数×六槽与独立C追加规则字节预期、UTF-8/引号/反斜线、所有程序来源及标签顺序、程序零窗口、锁/变化/关闭、原生缓冲限制、四模式方向/状态/计数/长度、私有输出/缺编译器/超时及标准库导入。原报告契约中合法的恢复零操作和清理零备份也保留，不以计数推测真的恢复过机身。

| 自制路线 | ELF文件字节 | relative relocation | 零填充字节 | LOAD虚拟跨度字节 |
| --- | --- | --- | --- | --- |
| stock / 2860 | 21936 | 68 | 611776 | 825392 |
| stock / 2866、fl23、stock-lut、fl23-lut | 21360 | 68 | 608256 | 824816 |
| legacy、zero-program | 21304 | 68 | 608312 | 824760 |

这是自制元数据的真实编译结果；文件≤64KiB不代表加载内存≤64KiB，更不证明Sony加载器兼容。七组演练的身份策略在测试内部隔离，来源和原C真实固定；生产入口没有策略/指纹覆盖。另用实际固定策略运行三个-S拒绝场景：未知自制程序、未知启用参数、缺失归档，退出1/2/1，无输出或私人路径回显。没有真实程序正例或实际SDK/机身验证。

## 交接与发布

计划调整提交 `65dc558f1984781b3a0df08e17b5a0322a966cf3` 的[CI 39631995240 / success](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39631995240)本轮已复核。本轮显式提交公开源码/测试/文档并正常推lut-photo/main，核对远端和当前CI；最终结果见回复及忽略目录custom-round61/publication-receipt.json，未完成的CI不记通过。原本地分析附录/报告保留，PRIVATE在内容读取前排除，不公开私人包、程序、资源、头/模块或详细报告。

下一交付D2：从固定devicesettings.plan及devicejob._settings确认实际逐属性读取/写入/保存/完整快照比较的消费格式，明确所选字段正反向、保存对未保存数据的影响、四保护CP与无关设置、程序/名称AP方向和失败停止条件。先完成可运行离线完整方案及衔接，不为自制投影重写一个并非流程所需的BK4编码器；真实外层兼容性/SDK留D4。D3统一离线入口/演练/整体审阅后收口；遇到必须依赖真实材料的缺口就停在检查点，不增加模拟轮次。当前2.00保留，D4设备操作另提示，D5恢复/独立介质及D6摄影仍未证。见[交接](HANDOFF.md)和[交付计划](../docs/DELIVERY-PLAN.md)。
