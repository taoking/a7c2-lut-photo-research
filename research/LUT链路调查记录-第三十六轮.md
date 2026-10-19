# 第三十六轮：主机加载链边界与只读 BK4 解析

日期：2026-10-19。继续 N3，只审固定源与自制格式夹具；不读私人程序/备份，不调用 USB、相机、诊断或 sudo，不构建/加载目标模块。

## 本轮检查项

- [x] 核验 10 个来源/许可成员，厘清主机链可证范围和机身关联缺口。
- [x] 受限 BK4 图像/双块解析、重叠/越界/校验和与资源上限检查。
- [x] 显式未验证角色投影、设置比较及 reset/布局保留，禁止自动规划/写入。
- [x] 自制格式夹具、负例、实际 CLI 与完整离线回归。
- [x] 更新四列计划和滚动交接；公开审查后仅提交推送 `lut-photo/main`，结果以 Git/远端和 CI 为准。

## 固定来源与主机链结论

新增[10 成员清单](upstream-backup-loader.lock.json)及 `research.audit_backup_loader`，固定 QAQLeonard v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`。工具包 331,887 字节，SHA-256 `8c6c30448219f4e865e8005d2ffa789248e984d73b0f9342035f7065a1a232f7`。清单覆盖 session、身份、服务、transport/core、PMCA parser/util/protocol 及两份许可，逐成员核对大小、SHA-256、Git blob 和本地提取原字节；只做 AST 语法检查，不导入归档 Python。保留 QAQLeonard 和 ma1co 署名及[完整 MIT 许可](../docs/Sony-PMCA-RE-MIT.txt)。旧 26 源、46 个固定上游成员及 14 worker 成员再次核验；旧运行锁、偏移和机型检查不变。

主机链能证明暂存≤65536 字节、路径命令 15/上传 16、暂存读回、可选请求读回、写 `libJit.so` 触发、主结果解码和按预期内容清理。触发/主结果的异常会标记会话 unknown；extras 和 cleanup 位于该段保护之外，外层 Job 安装等路径另有 NEEDS_REVIEW，未来接入须逐阶段覆盖。本轮未修改上游行为。

已审 host 链没有提供 Sony 端 ELF LOAD/BSS/权限/重定位/生命周期实现。NOR/CP 启动加载证据属于其他路径，不能替代 Jiritsu 插件加载证明；第三十五轮编译/ABI 元数据也不能证明设备行为。`camera_loader_abi_verified` 继续 false，缺口转交受控 N4，不继续从主机文件名推断。

BK4 两块的先后、checksum 和相似字段不能证明芯片归属或同机身。PMCA 的 id1 是开关字段，不是序列号；正常 USB 序列号哈希绑定发生在 BK4 之外，不能混用或自填 token 代替来源证明。

## 只读格式与设置比较

新增 `lutphoto.bk4`，仅用标准库读取命令明确给出的本地文件。支持 256 字节 BK4 头、packed `<HI` 表、固定/变长/大值、未分配指针、完整 16 位 attr 和 reset 当前值。检查 checksum、表/数据/分配区边界、行别名和存储重叠；先验证独占范围，再复制，防止别名放大内存。

快照≤32 MiB，单图像≤16 MiB，子系统/属性表行各≤65536，候选≤64、声明扫描工作≤64 MiB。必须恰好两个有效且不重叠的图像；无效标记可在载荷中，嵌套有效图像/第三块均拒绝。外层前缀/填充/尾部不解释，不验证完整备份容器。此为保守子集：未用真实备份验证，合法别名或超限格式也会拒绝，不能宣称可恢复。

`compare` 只读四个固定文件及 case.json；要求显式 AP/CP 互异索引 0/1，仍只是调用方断言。投影 AP 02cf 和四个保护 CP 单元至[既有设置契约](../docs/CUSTOM-CONTRACTS.md)，另检查四态 attr、max_size、当前长度和 reset 数据保留。高 attr 位不截断，投影直接拒绝；其他运行组不比较，不生成描述符或写计划。

报告不输出属性值/header 身份字段，但含输入完整 SHA，标记为私人报告，不上传。本层 `raw_backup_parsed:true` 只表示结构解析，嵌套设置契约该字段仍 false；角色、机身、真实程序身份、完整容器、描述符和物理验证始终 false。CLI 输出排他创建，拒绝链接/非普通输入和已有输出，不改源文件。详细范围及命令见[BK4 说明](../docs/BK4-OFFLINE.md)。

## 测试命令与结果

| 实际命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_bk4 -q` | 新专项 22 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -q` | 研究 276 项通过，含新专项 |
| `.venv/bin/python -B -m unittest discover -s tests -q` | Mac 39 项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q` | 旧上游 8 项通过；完整合计 323 项 |
| `.venv/bin/python -B -m macfl23 check` | 旧固定源码/资产核验通过，无设备操作 |
| `.venv/bin/python -B -m research.audit_backup_loader --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round36/loader-source-audit.json` | 新 10 成员通过，无归档导入或设备操作 |
| `.venv/bin/python -B -m research.audit_upstream_looks --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round36/upstream-source-audit.json` | 固定包、26 源及旧 46 成员通过 |
| `.venv/bin/python -S -B -m lutphoto.workercontracts --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round36/worker-source-policy.json` | 默认 14 成员/策略仍通过 |

使用 `-S -B -m lutphoto.bk4` 实际执行 `fixtures`、四次 `inspect`、一次 `compare`，均退出 0。四次已有 inspect 输出重跑均退出 1 且内容未变；损坏 checksum 输入拒绝、未生成报告，五个源文件全字节 SHA 保持。报告留在忽略的 `research/output/custom-round36/`。独立手工 packed 289 字节格式正例不依赖生产 HEADER/夹具生成器；负例覆盖越界/别名/重叠/reset/角色、配置伪身份、布局改变、输出和链接保护；`-S` 验证不导入 USB/设备包。未重编译 C，未加载执行模块，未打开真实程序/备份/照片。

公开审查检查所有公开文本、AST/JSON、Markdown 链接、私人路径/二进制、固定哈希、旧归档和受保护安装器路径及精确改动清单。CI 自动运行离线测试；不会下载本轮可选包或访问相机，CI 结果以推送后检查为准。

## 遗留与交接

N3 部分完成。下一轮为“显式指定本地文件”的纯只读 AP/CP 完整身份与描述符入口，先列清来源和真实正例材料；不自动搜索私人文件、不用合成身份放行计划，缺真实材料时明确限制。真实 worker 仍需完整事务来源/目标/逆向绑定；全局相机锁/USB、设备恢复和双独立介质备份未完成。Sony 加载行为及真实 ST/色彩留 N4，进入前提示，目前无需相机、Docker 或惠普电脑协助。

前轮提交 `a427c46d65d954973916017c3f4ebd3676c0f044`，[CI 已通过](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39274607218)。本轮审核后仅正常推送 `lut-photo/main`，不推 origin；旧 FL23 默认单份备份规则不变。真实 3D LUT 支线仍冻结于[第二十八轮](LUT链路调查记录-第二十八轮.md#遗留与交接)。[总计划](../plan.md)保持四列，[交接](HANDOFF.md)滚动覆盖，历史轮次不改。
