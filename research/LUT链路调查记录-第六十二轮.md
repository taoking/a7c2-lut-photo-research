# 第六十二轮：设置单元正反向、快照阶段核对与程序/名称衔接

日期：2026-10-22。完成[交付计划](../docs/DELIVERY-PLAN.md)的D2离线范围，新增 `lutphoto.settingsplan review/check` 和[使用说明](../docs/SETTINGS-PLAN-OFFLINE.md)。生成九个描述符派生的属性单元正反向方案、原记录前提和保存规则，核对显式提供的RAM/保存快照，并绑定程序/名称前后AP及顺序要求。**D1/D2离线完成，D3统一演练仍待完成；真实属性读写/保存、SDK/机身事务、外层容器和恢复未验证，N3仍部分完成。**

本人原厂2.00及日常卡副本保留，不需升级、连接、读移动盘或准备Docker/Windows。本轮未加载真实SDK或其共享库、未使用USB/系统相机锁、sudo/磁盘命令、机内模块或私人机身材料。只用实际N2离线候选、自制程序/策略、BK4/UXC；未重新编译未改动的C源码，也未执行任何目标代码。

## 可运行交付与已关闭缺口

1. 核对固定上游devicesettings.plan/devicejob._settings：实际流程独立读取属性、必要时写入/立即读回，按需save_settings，再获取RAM/保存快照比较，不写回整个BK4。因此复用原BK4只读解析，不创建不必要的外层编码器；原包/投影/完整原快照格式不变。
2. 在同一包Reader锁内重建唯一目标、派生九字段描述符，核心fields沿用slot/key/before_ram/before_saved/after格式。值来自本次冻结源及原生成器目标，不接受外部键/目标/策略；另绑定attr/长度/容量/reset。将九项变化应用到完整解码记录映射，再逆向比较全部记录和元数据，scope目标须精确等于原生成器输出，不建立第二套目标算法。
3. 正反向各列独立读前值、真正需写单元、写后读回、保存与双快照要求。保存前保留未选外观配方的未保存差异检查；原RAM/保存的所选字段必须一致，不生成会丢失其中一个值的逆向。零设置变化无实际写入/保存，程序零窗口无虚假program任务，但资源和完整程序复核仍保留；不支持未知/部分状态续跑。
4. 组合要求复用两类worker metadata与完整源/目标程序，核对名称源/目标AP和槽位。正向先名称1/68资源读回，再程序1/完整读回，再目标程序下设置；照片/重载验证后名称3按目标AP清理。逆向先目标程序下还原设置，再程序2、源AP下名称2和完整资源读回。这里只给前提顺序，没有执行器、设备触发、重试、自动还原或WBI操作。
5. check每次重验包/方案后核对source/target/restored显式阶段。AP02cf与四保护CP范围内字段集合/值/attr/reset/容量严格；诊断02cf0b6e只允许当前值变化。其他运行组只统计解码差异、不认证保留；两个合法图像不认证容器/角色/同机身/新鲜度。restored字节可等于从未写入的source，不能证明恢复执行过。
6. 私人0600方案确实导出属性原/目标值与前提，unit_actions_exported为true；设备写入能力及complete_settings_transition_verified、实际保存/独立读回/程序名称阶段/观察来源/恢复证据均false。默认标准库运行，复用既有私有输出；stdout仅阶段/需写数量/禁用设备。成功0，材料/阶段/保存/关闭/stdout失败1，参数结构错误2；失败保留现场，不覆盖、修复或续跑。

QAQLeonard固定v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`、ma1co/ajalt署名/许可保留；原vendored设置模块原字节不变。14成员/完整归档核验不改，同归档覆盖的devicejob仅作静态审阅。旧安装器、锁/指纹/偏移/依赖/旧测试及默认单份备份保持原样。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_settingsplan.py -v` | 最终21项通过：六槽描述符/ST、全部来源方向/顺序、零写入/保存、完整解码逆向、三阶段、部分/未知值、未选/ST/四CP、attr/reset/容量、诊断与排除组、角色/损坏/链接、锁/关闭、私有输出及标准库入口 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_settingsbinding.py -v` | 原23项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_slottarget.py -v` | 原22项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_slotbundle.py -v` | 原22项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_programworker.py -v` | 原18项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_nameworker.py -v` | 原19项通过；上述专项125项，不重复计入全量 |
| `.venv/bin/python -B research/output/custom-round62/exercise_units.py` | 六种自制来源各生成方案、核对source/target/restored，共18组快照阶段；每包152文件字节/元数据不变，观察文件字节不变，临时输入已清理 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究951项通过 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧Mac39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游8项通过；全量998项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产通过，未连接相机 |
| `.venv/bin/python -S -B research/output/custom-round62/audit_sources.py` | 25源码观察、14固定成员、6本地源码身份与vendored原字节通过；协调源码由完整归档SHA覆盖，无归档执行/设备导入 |
| `.venv/bin/python -B research/output/custom-round62/audit_public.py` | 公开清单、AST/JSON/本地链接/锚点、隐私/密钥排除、原附录/报告及受保护路径/锁/历史通过 |
| `git diff --check` | 通过 |

初版19项出现1个测试夹具错误：7字节测试值超过其声明6字节容量，构造阶段停止。修正为同长度变化后复跑，并加入六槽及损坏/链接用例，最终21项通过；生产校验未放宽、未删除失败用例。最后补充私人输出标识后，专项和全量均按最终源码复跑通过。

演练包括stock、fl23、stock-lut、fl23-lut、legacy、zero-program；最后一种只有程序零变化，设置仍需9项，不能将程序无变化误当全部无变化。专项另有程序和设置同时零变化用例，确认没有虚假program/属性写入/保存。154文件内容/元数据不变的专项覆盖包内152文件及两个观察快照，未保证atime。

独立 `-S` 子进程实际运行review并与父进程结果相等，没有NumPy/编译器/SDK依赖，但身份策略仍由测试内部自制数据隔离，不构成真实原厂正例。另以实际固定生产策略运行未知自制程序、未知启用参数、缺失归档三种-S拒绝，退出1/2/1，无输出或私人路径回显；生产没有策略/plan覆盖或resume参数。

## 发布与下一交付

第六十一轮 `32a80b3e2c4ed7ee39824c40e14d01d9a7804ca4` 的[CI 39635414304 / success](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39635414304)已复核。本轮只显式提交公开源码/测试/文档，正常推lut-photo/main并核对远端/当前CI；结果见最终回复及忽略目录custom-round62/publication-receipt.json，未完成CI不记通过。原本地分析附录/报告保留，PRIVATE在内容读取前排除；私人属性方案、包、快照、材料指纹及详细观察报告不公开。

下一交付D3：统一离线入口，串通CUBE拟合/参考图/误差、私人包和程序/名称/设置检查、逆向/阶段验证，交付一次完整可运行演练与整体审阅，区分自制演示和生产固定策略。复用当前生成器和Reader内接口，不另建模拟传输/回执/状态框架，不编造未实现命令。完成后冻结离线版本；真实SDK/同机材料缺口在D4检查点一次说明所需配合，不继续延长模拟轮次。当前2.00保留，实际采集/写入/恢复和D6摄影另行安排。见[交接](HANDOFF.md)及[交付计划](../docs/DELIVERY-PLAN.md)。
