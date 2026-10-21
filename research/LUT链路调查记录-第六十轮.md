# 第六十轮：程序worker绑定、离线编译与三模式报告契约

日期：2026-10-21。交付 `lutphoto.programworker review/check-report` 及[使用说明](../docs/PROGRAM-WORKER-OFFLINE.md)，复用私人单槽包独立重建和现有编译/ABI/ELF检查，将完整程序transition绑定到固定上游程序worker元数据。**本轮完成离线编译与报告结构检查，未执行目标代码；N3仍部分完成，真实来源/加载器/机身事务/恢复和色彩未证。**

本人原厂Ver.2.00及日常卡副本保留，不需现在升级、连接相机、读取移动盘或准备Docker/惠普电脑。本轮没有实际SDK/共享库、USB/系统相机锁、sudo/磁盘命令、机内模块或私人材料读取。正例均是实际N2离线候选和自制程序/策略、BK4/UXC，不是真实原厂正例。

## 交付与边界

1. slotbundle抽出内部共享Reader作用域：原inspect摘要/固定150 payload/完整重建语义不变。worker在同一共享锁内获得policy、唯一生成器的完整review和清单SHA，检查及编译完成后再次核对文件变化并关闭；关闭失败不返回成功。没有第二套目标生成器、加载器或模拟传输层。
2. 程序metadata从已检查AP/CP transition及完整目标取得，额外重验正反向。完整源/目标SHA、大小和精确窗口计数绑定；排序对齐上游CP优先、大于1024字节优先、偏移升序。窗口≤4096，头文件预算1MiB。零程序窗口返回NO_PROGRAM_CHANGE/空contract，不加载worker来源或调用编译器，不接受虚假报告；名称/设置可另有变化。
3. 固定v2.1完整归档及14成员核验，与包的commit/归档SHA一致。原C/SHA头原字节写入私有临时目录，用独立翻译单元附加Request/Report全部偏移及Window/整数/元数据数组/窗口数断言。复用Zig0.13.0与现有ELF/LOAD/重定位检查，60秒编译超时，检查后删除头/模块/缓存。默认审阅是标准库路径，编译才需要隔离依赖，没有模块导出或执行入口。
4. check-report每次重验包、重建contract，验证显式240字节报告和模式0/1/2；方向分别是源→零after、源→目标、目标→源，并严格检查状态/phase/计数/大小/完整SHA。请求仅在内存按16字节契约编码/记SHA，不保存/发送。报告可人工构造，正pid/inode不是来源认证；report_structure_verified不表示机内执行或恢复，设备证据始终false。
5. 详细报告含完整材料指纹/contract，仓库外新私有父目录、0600排他写入/同步，不得公开；stdout只给阶段/编译与禁用设备摘要。失败类型有限，无私人路径/编译诊断回显。成功0，材料/编译/依赖/存储/关闭/stdout失败1，结构参数错误2；部分或完整输出保留、不覆盖/修复/续跑，文件存在不证明调用成功。

QAQLeonard固定v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`、ma1co/ajalt署名/许可保留；未执行归档Python。旧安装器、默认单份备份、旧锁/指纹/偏移/依赖/旧测试及历史计划不变。完整BK4设置外层、名称worker绑定和设备部署/事务仍未完成，私人包不是执行授权或独立介质备份。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_programworker.py -v` | 最终18项通过：完整元数据/排序/所有来源路线、锁内编译/变化/关闭、零任务、依赖/失败/超时、三模式方向/计数/状态、私有输出及标准库导入 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_workercontracts.py -v` | 原19项通过，编译器抽取保留旧API/fixture语义 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_slotbundle.py -v` | 原22项通过，共59项专项；不重复计入全量 |
| `.venv/bin/python -B research/output/custom-round60/exercise_compile.py` | 固定原C真实交叉编译4条自制路线，全部ABI/ELF/LOAD通过；零任务不编译；每条非零路线三模式报告结构通过；每包152文件字节/元数据不变，临时输入清理 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究911项通过 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧Mac39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游8项通过；全量958项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产通过，未连接相机 |
| `.venv/bin/python -S -B research/output/custom-round60/audit_targets.py` | 73条AST/元数据观察，14固定上游和10本地源码身份通过，无归档执行/设备导入 |
| `.venv/bin/python -B research/output/custom-round60/audit_public.py` | 精确公开清单、AST/JSON/Markdown链接/锚点、隐私/密钥排除、原附录/报告及受保护路径/锁/历史检查通过 |
| `git diff --check` | 通过 |

初版17项中有1项把任意正inode变化误当成必须拒绝；改为检查非法零值，并明确不认证报告来源，生产校验未放宽。最终增至18项全部通过。第一次编译演练把虚拟环境解释器解析到底层系统解释器，因缺elftools停止；修正演练的解释器路径后复跑四条路线通过，没有安装新依赖或跳过检查。

| 自制路线 | 窗口 | ELF文件字节 | relative relocation | 零填充字节 | LOAD虚拟跨度字节 |
| --- | --- | --- | --- | --- | --- |
| stock | 6 | 24504 | 12 | 79640 | 298248 |
| fl23 | 6 | 24504 | 12 | 79640 | 298248 |
| standalone | 4 | 10344 | 8 | 81512 | 284088 |
| legacy | 2 | 10192 | 4 | 81664 | 283936 |
| zero | 0 | 不编译 | — | — | — |

上述是自制输入的真实编译结果，不能推广为真实程序产物大小或Sony加载能力。文件≤64KiB不代表内存需求≤64KiB。演练使用实际固定14成员与原C，只有自制程序身份策略由测试内部隔离；生产CLI没有策略覆盖。另以实际固定策略运行三个-S拒绝场景：未知自制完整程序、未知启用参数、缺失归档，退出分别1/2/1，无输出或私人路径回显。来源/设备门槛不因测试而放宽。

## 发布与交接

第五十九轮结束时尚未观察到CI；本轮核对 `8e4c54f6e98b8b0e0325cbae535f32440e668513` 的[39624343384 / success](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39624343384)。本轮正常提交/推送lut-photo/main，核对远端及当前CI，最终结果见回复及忽略目录custom-round60/publication-receipt.json；未出现的CI不记通过。

总计划只更新N3主表，保留未发布的原分析附录/报告，不读或发布PRIVATE。只显式提交公开源码/测试/文档，不发布程序、头、模块、设置、逆向、身份或私人报告。下一轮完成名称worker的包绑定/离线编译/四模式报告契约；完整BK4设置和机身事务分别推进。C2本人真实SDK/同机材料、C4恢复/独立介质、C5真实ST/摄影和真正3D LUT支线后置，设备阶段另提示，当前2.00保留。见[交接](HANDOFF.md)和[总计划](../plan.md)。
