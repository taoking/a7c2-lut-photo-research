# N3：描述符与 RAM/保存快照的只读绑定

第三十八轮增加 `lutphoto.settingsbinding`：通过[完整 AP/CP 内容身份](PROGRAM-IDENTITY.md)后，按程序描述符派生所选槽的九字段及八个共享 ST 引用，再检查显式提供的两份[BK4 快照](BK4-OFFLINE.md)。固定来源、署名和 MIT 许可沿用此前清单，不导入上游设备模块或归档 Python；旧 FL23 锁/安装器、默认单份备份不变。

**本轮正例仅使用自制程序与 BK4 数据。** 实际 CLI 只验证固定包核验、未知输入/已有输出等拒绝；没有读取真实程序/备份、运行目标模块或操作相机，真实兼容性与同机身来源仍未验证。检查不会生成 after 快照、设置写计划、worker 或恢复操作。

## 命令与必要输入

只需 Python 标准库；可用 `-S` 禁用 site packages。先按[材料说明](PROGRAM-IDENTITY.md#先查材料再显式检查)准备固定包及本人明确提供的完整 AP/CP 路径。RAM 与保存快照也须由本人明确提供既有本地路径；没有输入时不自动查找私人目录或运行相机 prepare/diagnose。

```sh
mkdir -p research/output/binding-demo
.venv/bin/python -S -B -m lutphoto.settingsbinding \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --ap "/path/to/owner-backup/appFw.so" \
  --cp "/path/to/owner-backup/cpapp-b.bin" \
  --ram "/path/to/owner-backup/ram.bin" \
  --saved "/path/to/owner-backup/saved.bin" \
  --slots 1 2 \
  --ram-roles 0 1 --saved-roles 0 1 \
  --output research/output/binding-demo/summary.json
```

所有 `/path/to/owner-backup` 均为通用占位路径；输出须尚不存在。角色参数的两项分别为 AP/CP 图像索引，须显式提供互异 0/1。示例 0/1 只展示格式，与自制夹具一致，不是相机默认顺序；两个快照可分别断言不同顺序。满足所需字段也不证明角色，此工具不会猜测/重排或从 checksum/id1 推断机身。

`--slots` 为互异整数 1–6。没有 `expected`、自定义策略/指纹、机身认证 token 或输出写入数据的参数。完整身份或描述符不符时不打开快照。输入只读，拒绝链接/非普通文件、坏 checksum、越界、布局不支持和已有输出；快照上限 32 MiB、格式/资源限制继承 BK4 层，投影后每芯片最多 4096 个记录。成功 0，检查失败 1，参数格式错误 2；错误不回显私人路径/数据。

## 实际比较范围

| 检查 | 条件 |
| --- | --- |
| 描述符来源 | 固定包完整来源核验 → 完整 AP/CP 内容识别 → AP 行身份/范围/组/类型/布局/独占检查，均通过后才读 BK4 |
| 所选槽 | 每槽基底 1 字节、八项调整各 4 字节，两快照中都存在；拒绝 `attr & 3`；RAM/保存的当前值和属性一致 |
| ST 引用 | 八个引用来自程序行，两快照中存在且为 4 字节；引用只读，允许原属性只读位，不把它们当写目标 |
| 未保存设置 | AP 02cf 除诊断值外全部键/属性/当前值双向相等，包括未选槽、ST 引用与仅在保存态出现的键；任何差异拒绝 |
| CP 保护 | 四个固定 CP 单元必须存在，RAM/保存当前值、属性均相等 |
| reset/布局 | 整个投影范围（含诊断字段和保护 CP）的键集、attr、max_size、当前长度及 reset 数据都相等，高 attr 位拒绝投影，绝不截断 |
| 诊断及其他组 | 02cf0b6e 的易变当前值不比较，布局/reset 仍核对；其他运行组不比较、不写入，不能称全快照保留 |

检查仅计算当前所选字段与 ST 是否相等的数量：基底与单字节 0 比较，调整与对应 ST 引用值比较。现有 recipe 尚未等于 ST 可以通过本地结构检查，报告会如实给计数；不据此声称已导入或允许写入，也不生成目标值字典/假想 after 状态。之后导入仍需独立的新鲜来源、事务和写后验证。

## 报告和未闭合证据

`local_program_content_verified` 与 `provided_snapshot_structure_and_values_checked` 只说明读取的本地内容满足所列规则。报告只包含完整 SHA、图像/字段数量、所选槽和状态，不输出属性键/值、ST 目标、程序字节或写计划；含来源指纹，标记 `private_report`，不得上传公开仓库。

以下始终 false：快照新鲜度、同一捕获来源、实际机身身份/芯片角色、完整外层备份容器、Sony 加载器/机内执行、物理验证、live 描述符及设置写计划。两个相同文件、合法时间戳/相似字段/完整内容哈希都不能补齐这些证明；本命令不收取自填 token 来认证。嵌套 `descriptors.setting_values_verified` 保留行层的 false；本层的内容检查标志不认证当前机身设置。文件离线检查不等于安装预检查已通过。

专项测试覆盖自制正例、描述符键重映射、缺字段/长度/属性/别名、未保存项、四个 CP 单元、诊断值例外、reset/分配布局、显式角色和私人输出保护，另有实际 `-S` CLI 拒绝检查。真实完整程序及 BK4 正例仍缺，必要材料见[来源说明](PROGRAM-IDENTITY.md)，真正需要时一次请求本人路径和捕获记录，不自动访问既有备份。

N3 仍部分完成。后续需将本地表/槽位/名称资产与输入指纹及完整来源/目标/逆向事务绑定，并在真实输入正例充分前保持设备入口关闭。USB/全局相机锁、设备恢复、独立介质及 N4 冷启动/真实色彩后置，进入实测前提示；当前无需连接相机、Docker 或惠普电脑。见[总计划](../plan.md)与[交接](../research/HANDOFF.md)。
