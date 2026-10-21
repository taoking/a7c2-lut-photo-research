# N3：单槽完整程序目标与离线逆向

第五十八轮提供 `lutphoto.slottarget`，复用[完整程序身份](PROGRAM-IDENTITY.md)、[描述符/快照绑定](SETTINGS-BINDING.md)、[N2候选与名称资源检查](IMPORT-MATERIALS.md)。规则来自QAQLeonard固定v2.1的device_layout/six/devicesettings及ma1co BK4研究，见[致谢与许可](../ACKNOWLEDGEMENTS.md)。没有导入/执行归档Python、连接USB、生成/加载worker或操作相机。

本轮正例仅用实际N2离线工具生成的候选，以及自制程序/策略、BK4和UXC夹具。**已完成完整程序目标的内存生成与逐字节前向/逆向验证；真实材料兼容性、完整设置事务和机身恢复仍未验证。** 当前本人原厂2.00及日常卡副本保留，不要求升级、连接或读取移动盘。

## 输入与命令

输入与材料清单命令相同，但选择文件必须恰好一个槽；没有另一个 `--slots` 参数。复用既有选择格式，例如：

```json
{
  "schema": "a7c2-import-material-selection/1",
  "slots": {
    "1": {"candidate": "candidates/own-look", "name": "My Look"}
  }
}
```

候选目录相对选择文件，不允许绝对路径、逃逸或链接。重新读取并核对candidate.json与1215字节表，目标生成直接复用这次观察的表字节；候选的拟合/色彩声明仅作既有格式检查，不重新拟合或验证实际精度。

只有本人明确提供现有材料路径后才运行下面命令；占位路径不能当作现有备份。输出父目录须已存在、归当前用户且0700，路径祖先受信且没有符号链接，使用规范路径；输出文件须全新、位于仓库外，排他发布0600。无需sudo、NumPy、AArch64共享库、Docker或Windows：

```sh
.venv/bin/python -S -B -m lutphoto.slottarget \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --ap "/path/to/owner-backup/appFw.so" \
  --cp "/path/to/owner-backup/cpapp-b.bin" \
  --ram "/path/to/owner-backup/ram.bin" \
  --saved "/path/to/owner-backup/saved.bin" \
  --selection "/path/to/owner-materials/selection.json" \
  --resources "/path/to/owner-backup/resources" \
  --ram-roles 0 1 --saved-roles 0 1 \
  --output "/path/to/private-targets/slot-1.private.json"
```

两组角色分别是AP/CP图像索引的显式断言，不是默认顺序或角色证明。完整AP/CP身份与描述符先于快照/候选/资源读取；程序只接受固定原厂2.01/FL23配对、完整重建的standalone及历史full7-v4，不能用任意指纹、策略文件或参数放行2.00/未知内容。资源必须恰好固定68文件，原有2860/2866布局规则保留。

成功退出0只表示这次本地目标审阅完成；输入/来源/内容/输出失败1，结构参数错误2。错误只输出有限类型，不回显私人参数、名称或路径。没有相机执行、重试、续跑、写入或恢复命令；现有输入和输出不覆盖。

## 实际生成和验证范围

| 部分 | 完成条件 | 限制 |
| --- | --- | --- |
| 原厂/FL23首次程序目标 | CP逐项核对固定bootstrap旧字节，得到完整SHA匹配的canonical零表runtime，再替换所选表/FNV；AP还原完整来源并验证SHA，按原mask与所选位的并集重建 | 五个未选表参照canonical零表，不能称保留原厂程序里不存在的自定义表；不是首次安装实测 |
| standalone更新 | 完整AP重建来源、保留既有mask并启用所选槽；CP仅替换一表及对应FNV | 五表及各自FNV逐字节不变，代码仍需完整归一化身份；不是任意可变区 |
| 历史full7-v4更新 | AP完整保留，CP按独立历史代码身份替换所选表/FNV | 标签顺序仍用历史映射，不迁移到standalone，不接入退休布局 |
| 程序前向/逆向 | 固定大小、非重叠窗口、每窗口≤4096字节且最多4096个；完整源SHA和每窗旧字节都匹配；实际应用前向/逆向后分别与完整目标/原输入逐字节相等，再识别完整目标及所选描述符 | 内存验证；报告不导出窗口、模板、程序或可执行事务 |
| 所选设置 | 从本次AP描述符派生九字段：基底0、八调整取本次RAM的ST引用；对RAM/保存分别生成投影目标并逆向比较全部投影字段 | 仅AP02cf与四个保护CP作用域；保留未选值、属性、reset/分配布局及各自诊断当前值，不生成完整BK4外层或设置写计划 |
| 名称资源 | 同次读取的68个UXC生成目标并逆向逐字节等于原输入，未选名称保留；2860扩展缺失标签时用ST | standalone/历史顺序由程序身份派生；原始记录保留不等于已验证相机资源来源或界面刷新 |

程序差异分组沿用上游首次导入的间隔16/窗口4096规则；窗口外变化会因完整重建比较而拒绝。逆向必须从精确目标开始，不能应用于后来变化的文件。零变更可有零窗口，仍检查完整双向身份，不据此生成机内写任务。

## 私人摘要与后续

报告schema为 `a7c2-offline-single-slot-target/1`，含固定来源、选择/候选/表/名称摘要、完整程序前后/还原SHA、窗口数量、设置作用域指纹和68资源前后/还原SHA。`target_review_sha256`绑定本次材料与结果；哈希不是签名、匿名化或当前机身认证。完整摘要留在本人私人位置，不上传公开仓库或聊天。

`complete_program_transition_verified`、`scoped_settings_transition_verified`仅表示本次内存契约通过。`complete_settings_transition_verified`、真实来源/新鲜度/芯片角色、独立备份、worker/加载器/机内执行、实际色彩、部署与恢复仍未证。目标和逆向字节只在内存，`payloads_exported:false`、写计划/设备标志保持false，不修改旧安装器、指纹、偏移或依赖。

下一交付是复用这些结果形成可独立重验的私人单槽事务包，绑定完整输入/目标/逆向，继续只用自制材料；不再写另一套生成器。C2真实SDK/本人材料另行安排，实采前提示真实版本/电量/连接与系统权限；C3完整设置/worker、C4恢复与独立介质、C5摄影验收分别保留缺口。测试及固定来源实跑见[第五十八轮](../research/LUT链路调查记录-第五十八轮.md)，继续任务读[交接](../research/HANDOFF.md)。
