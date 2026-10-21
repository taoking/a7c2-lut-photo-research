# 第五十九轮：私人单槽事务包、冻结输入与独立完整重验

日期：2026-10-21。交付 `lutphoto.slotbundle create/inspect` 及[使用说明](../docs/SINGLE-SLOT-BUNDLE.md)，复用上一轮唯一目标生成器和既有私有Store/Reader，完成C3单槽资料的持久化与独立重验。**包不是相机安装事务；完整设置容器、worker/设备执行、实际材料来源/色彩、独立介质和恢复未证，N3仍部分完成。**

本人原厂Ver.2.00及日常卡副本保留，不要求升级/连接/读取移动盘或准备Docker/惠普电脑。没有实际SDK/共享库、USB/系统相机锁、sudo/磁盘命令、机内模块或私人材料读取。全部正例为实际N2离线候选与自制程序/策略、BK4/UXC，不是实际原厂正例。

## 交付与来源边界

1. slottarget拆出共享冻结输入/纯字节生成接口，旧check_files/CLI仍仅输出原摘要；选择/候选和快照文件入口复用纯字节解析。文件准备先完整身份/描述符再快照、候选和资源；候选表来自同次读取，候选JSON复读必须匹配已检查完整SHA，不以多次读取声称原子捕获。独立包检查不访问原输入或selection内的相对目录。
2. 新包固定150个payload：7原始输入、68原资源、75目标/前向/逆向/设置投影/审阅；另有最终清单和作业锁、空events目录。原文件保留，私有父目录/新作业、0700目录/0600文件、排他保存/逐文件同步读回；全部payload后才在锁内保存规范清单，关闭后独立只读重开。空间/写入/读回/关闭未知均非成功，失败保留现场，不删/修/重用。
3. 独立Reader核对固定清单/角色/source/false标志、每项完整长度/SHA及目录项/元数据；再从包内冻结输入按固定规则重新生成所有目标/逆向，逐文件完整字节比较。清单无任意路径，篡改目标、逆向、设置投影、资源或审阅后只重算哈希仍拒绝。包所有者可重建另一份全有效包，哈希不是签名或原意认证。
4. 包含完整私人程序、快照、名称/资源及逆向字节，绝不公开。设置目标仍只是AP02cf/四CP投影，不序列化为所谓完整BK4；原快照原字节保留也不证明外层真实或可恢复。零程序变更保留零窗口，不凑worker写次数；设置/名称仍可能另有变化。
5. CLI有限摘要无私人路径/身份/材料指纹/值。创建与检查成功0，输入/存储/关闭/输出失败1，参数结构错误2；文件一致不能单独证明原调用关闭/stdout/进程成功。没有worker、重放、续跑、写入或恢复命令，不开放策略/指纹/设备启用参数。

规则继续来自QAQLeonard固定v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90` 及ma1co研究，保留QAQLeonard/ma1co/ajalt署名/许可；归档/固定14成员核验不改，不执行归档Python或原生代码。旧安装器/默认单份备份、旧锁/指纹/偏移/依赖/旧测试和历史计划不改。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_slotbundle.py -v` | 最终22项通过；150 payload/独立-S进程、全部来源路线、重新计算清单哈希后的篡改、角色/链接/部分输出/锁/变化/关闭/输出失败及零程序窗口 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_slottarget.py -v` | 原单槽22项回归通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_importmaterials.py -v` | 原清单22项回归通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_settingsbinding.py -v` | 原设置绑定23项回归通过；上述专项89项，不重复计全量 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究893项通过 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧Mac39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游8项通过；全量940项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产通过，未连接相机 |
| `.venv/bin/python -S -B research/output/custom-round59/audit_targets.py` | 54条AST/元数据观察，14固定上游和8本地源码身份通过，无归档执行/设备导入 |
| `.venv/bin/python -B research/output/custom-round59/exercise_fixed_cli.py` | 四种实际-S CLI拒绝符合预期；固定策略不改，229自制文件字节保留/还原、228项元数据不变，仅自制清单故意重写，临时输入已清理 |
| `.venv/bin/python -B research/output/custom-round59/audit_public.py` | 274个公开文本/112份Markdown/714处本地链接及锚点通过；13项精确发布清单、隐私/密钥排除、受保护路径/锁/历史通过 |
| `git diff --check` | 通过 |

新专项初版20及最终22项均通过；没有删除失败用例、放宽成功条件或改生产规则。共享解析/生成重构后，原目标/清单/设置绑定67项和全量均通过。自制原厂、FL23、standalone两来源及历史布局的包均离线成功；独立-S子进程仍只通过测试内部自制策略核对资料，不构成真实SDK/机身正例。75个原输入的内容/inode/大小/权限/mtime/ctime在创建/独立检查前后不变，不保证atime。

实际固定策略演练使用99,960,744字节全零AP及18,090,880字节全零CP，完整身份拒绝且不打开缺失快照、不创建输出；另有自制包来源不匹配、重写自制包来源声明仍被完整程序门槛拒绝、未知启用参数。四次实际CLI退出1/1/1/2，无私人路径回显或真实材料放行。229文件字节保留/还原，228文件元数据不变；自制清单因故意重写，只验证其最终原字节还原，不声称其mtime/ctime不变。临时输入已清理，未修改生产指纹/清单或状态放行。

## 发布与交接

上一轮 `9bfdc07e2ee1cf9361ba8ecb408c3c88a79e243c` 的CI在第五十八轮结束时尚无记录；本轮复核出现并完成，实际为[39619025357 / success](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39619025357)。不将此前未出现记作失败，也不在此前记录中补称已通过。

总计划只更新N3主表，原本地分析附录/报告保留；PRIVATE在读取内容前排除。本轮只显式提交公开源码/测试/文档，私人包/程序/设置/名称/逆向字节及本地报告均不发布。正常推lut-photo/main，核对远端/本轮CI，结果见最终报告及忽略目录custom-round59/publication-receipt.json。

第六十轮复用已验证包的程序前向/逆向，绑定固定worker元数据并完成离线编译/ABI与报告契约检查，不重写目标生成器/加载器，不执行目标代码。零窗口不生成虚假写任务；完整设置容器和机身事务仍分开列缺口。C2本人首采/实际SDK及材料另行提示，当前2.00保留；C4恢复/独立介质、C5真实ST/摄影及真正3D LUT支线继续后置，备份不保证救砖。见[交接](HANDOFF.md)与[总计划](../plan.md)。
