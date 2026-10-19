# N3：资源与设置的离线契约

第三十三轮将固定上游 v2.1 的 UXC 资源和设置保护函数接入 `lutphoto.customcontracts`。**只校验电脑上的文件，改名与撤销只发生在内存。** 不产生可写入机身的资源、固件补丁或设置计划；没有 USB、机内模块或安装入口。格式夹具通过不代表真实机身状态已识别。

上游两个 Python 文件和 68 文件名清单按原始字节保留，提交为 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`；[来源固定](../lutphoto/_vendor/sonycontracts/PROVENANCE.json)包含长度、SHA-256、原路径及完整包哈希，[许可与边界](../lutphoto/_vendor/sonycontracts/README.md)单独记录。该包与 N2 的纯色彩算法包分开。没有复制任何 Sony UXC 内容、程序、备份或照片；夹具均由本项目生成。

## 运行合成格式示例

仓库根目录执行，输出路径必须尚不存在；只需 Python 标准库，不需要 NumPy、Zig、Docker、另一台电脑或相机：

```sh
mkdir -p research/output/contracts-demo
.venv/bin/python -B -m lutphoto.customcontracts fixtures \
  --directory research/output/contracts-demo/cases
.venv/bin/python -B -m lutphoto.customcontracts resources \
  --directory research/output/contracts-demo/cases/stock \
  --layout standalone --names research/output/contracts-demo/cases/names.json \
  --output research/output/contracts-demo/stock-report.json
.venv/bin/python -B -m lutphoto.customcontracts resources \
  --directory research/output/contracts-demo/cases/imported \
  --layout legacy-six --names research/output/contracts-demo/cases/names.json \
  --output research/output/contracts-demo/legacy-report.json
.venv/bin/python -B -m lutphoto.customcontracts settings \
  --capsule research/output/contracts-demo/cases/settings.json \
  --output research/output/contracts-demo/settings-report.json
```

`fixtures` 排他创建目录，产生 stock/imported 两套各 68 个自制 UXC-v7 文件、名称 JSON 和解码设置 JSON；它们不是相机提取物。所有输入保持原字节，报告排他创建，已有文件或符号链接不会被覆盖。成功退出 0，拒绝退出 1；错误输出只给异常类型，不回显原路径、名称或设置。文件链接读取保护目前只在 Mac 验证，Windows 运行本入口尚未验证。

## 资源契约

文件夹必须恰好包含固定清单的 68 个名称，不允许遗漏、额外项、符号链接、非普通文件或混合的索引布局。每文件限 1 MiB。接受 group 5、2860 或 2866 项的 UXC-v7，检查头、描述符、对齐、索引/记录身份、UTF-8、终止符、非重叠记录；2866 布局要求六个名称 ID 都存在。

`names.json` 为 `{"2": "Demo Look"}` 形式；槽位只可为字符串 `1` 至 `6`，非空。新名称限 1–63 个 UTF-8 字节，不接受 C0/C1 控制字符；比原上游进一步拒绝 DEL/C1。名称只是资源内容，不用作文件路径。

| 显式布局 | 槽 1、2 对应名称 ID | 适用范围 |
| --- | --- | --- |
| `standalone` | `0200ab2c`、`0200ab2d` | 新版的连续顺序；2860 原始索引或 2866 扩展索引 |
| `legacy-six` | `0200ab2d`、`0200ab2c` | 上游历史六槽顺序；只接受 2866 |

这个参数是调用方的布局断言，**不是 AP 身份识别结果**；同一个 UXC 无法证明机身程序采用哪种顺序。工具不猜测或自动选择映射。2860 扩展至 2866 时，未选的新标签按上游初始化为 ST，其他原记录保留；2866 只替换选中名称。完整原字节保留在内存目标中，并执行上游 inverse，要求恢复结果与完整原文件逐字节相等。报告记录来源/目标/恢复 SHA 和字节数，不输出改名后的资源、名称文本或逆向写入计划。

完整哈希此处只绑定所读文件和本次内存计算，不是已验证 Sony 原厂/FL23/Custom 版本的白名单，也不能证明同一机身来源。

## 解码设置契约

输入是明确的 `a7c2-decoded-settings-contract/1` JSON，不接受原始 BK4、相机程序或旧模拟器的占位缓冲。顶层严格包含 `schema`、`ram_before`、`saved_before`、`ram_after`、`saved_after` 和 `expected`。每个状态为 `AP`、`CP` 字典，键是八位小写十六进制；记录仅含 0–255 整数 `attr` 和小写偶数长度十六进制 `data`。`expected` 指定预期 AP 字段及目标 hex，**尚未绑定真实描述符或自定义槽**。

限制为 JSON 2 MiB、嵌套深度 32、10 万节点、每芯片每状态 4096 记录、每值 65535 字节；拒绝重复 JSON 键、非有限数字、非法 UTF-8/hex、额外顶层字段。选择 1–54 字段，只允许 `02cf` AP 组内已存在、长度不变的一字节基底/四字节调整值；额外拒绝 `attr & 3` 的字段。该属性位约束是接入层的保守限制，不代替真实描述符检查。

- 所选字段在 RAM/保存态开始时必须一致，RAM/保存态结束时都须精确命中预期，属性不得改变。
- 未选 `02cf` 字段的数据、属性、键集合必须保留；保存前两种状态也必须一致，不能把无关未保存设置一起持久化。
- `02cf0b6e` 只作诊断，不能作为目标；其值允许变化，但存在性、长度、属性必须一致。
- 四个 CP 单元 `02a40000/02a40001/02a40002/02a4000d` 必须存在，四份状态之间的数据与属性必须相同。
- 其他 AP 运行组及 CP 单元不在此比较范围，也不能作为目标。输入可能只是解码片段，**这里没有执行完整备份，也没有证明备份完整性、机身关联或介质独立性**。

接入调用上游 compare、protected_equal 和保存保护，提供只处理该限定范围的严格比较器，不引入旧 core/USB 或宽泛计数器豁免。报告只给范围和计数，不回显设置数据。`actual_source_identity_verified`、`descriptor_write_plan_verified`、`raw_backup_parsed`、`camera_backup_performed`、`physical_validation_verified` 均为 false。

上游 `devicesettings.plan` 会先调用真实 AP 识别再读取描述符；依赖模块没有随此契约包引入，因此该入口不可用。没有模拟识别函数、放宽哈希或用手填 `expected` 代替设备写入计划。

## 剩余工作

N3 仍为部分完成：真实 `device_layout/six` 来源、描述符与表资产绑定、真实 BK4 兼容/角色与来源证明、机身绑定 worker 和 Mac USB/全局锁尚待接入；第三十五轮已完成[固定来源规则及真实 C 的合成头构建/报告 ABI](WORKER-CONTRACTS.md)，Sony 加载边界仍未验证。第三十四轮已增加[合成持久化日志及进程锁原型](CUSTOM-JOURNAL.md)，不能替代设备事务或恢复。[总计划](../plan.md)和[交接](../research/HANDOFF.md)记录下一轮顺序；旧 FL23 安装器、运行锁、默认单份备份不变。

新 Custom 流程的两份独立物理介质完整备份尚无实证，Docker/惠普电脑也没有实测需求。真机写入、恢复、冷启动和真实色彩仍在 N4，进入前提示；当前无需连接相机。

第三十六轮新增[BK4 原始格式只读桥接](BK4-OFFLINE.md)，可将显式提供的四份快照投影到本契约，并额外保留 reset/分配布局；仅用自制夹具验证，不证明芯片归属或同机身，也没有启用设置 planner。
