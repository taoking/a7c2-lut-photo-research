# N3 / D2：设置单元方案与程序、名称衔接

第六十二轮提供 `lutphoto.settingsplan review/check`，从已独立重建的私人单槽包生成九个设置单元的原值、ST目标、逆向及操作前提，并核对显式提供的RAM/保存快照。**D2在离线范围完成，实际SDK属性读写/保存、机身事务、完整容器与恢复仍未验证。** 本模块没有设备接口或执行器。

依据QAQLeonard固定v2.1的devicesettings/devicejob流程和ma1co BK4解析；复用[单槽生成器](SINGLE-SLOT-TARGET.md)、[程序worker](PROGRAM-WORKER-OFFLINE.md)、[名称worker](NAME-WORKER-OFFLINE.md)和既有私有输出。来源/许可见[致谢](../ACKNOWLEDGEMENTS.md)。本轮正例全部自制，未加载真实SDK、读取私人材料或操作相机；当前原厂2.00及日常卡副本保留。

## 实际消费格式

上游按所选属性逐项独立读取、必要时写入并立即读回，再按需调用save_settings，最后重新取得RAM/保存快照比较；流程不把改写后的完整BK4容器写回。因此本轮生成属性单元方案，保持现有BK4解析器只读，不新增容器编码器。

方案核心 `fields` 与上游格式一致：`slot/key/before_ram/before_saved/after`。键由本次完整源AP的描述符派生，不由命令行填写；目标值取同一包唯一生成器的已验证结果，源RAM/保存值必须一致。另保存原attr、当前长度、容量和reset数据作为前提。

每个方向的 `units` 说明独立读前值、是否真正需要写、写后读回以及目标值。只有存在需写入的字段或保存态尚非目标时才要求保存；零设置变化不凑写入或保存次数，但仍要求核对。保存前必须检查未选外观设置的未保存差异，不能为了导入风格顺带持久化其他配方。未知或部分状态停止，不提供resume。

主机内将九项变化应用到完整解码AP/CP记录映射，再逆向比较所有记录、attr/reset/容量；这证明模型中的精确逆向，不生成或认证原始BK4外层目标。原始包/快照不改，外层和芯片角色仍未证，不能据此称整份备份可写回或恢复。

## 生成私人方案

下面路径均为占位示例。已有包必须通过原固定完整程序/150 payload及目标逆向重建；输出是包外、仓库外的新文件，已有父目录归当前用户、0700、规范无链接且祖先受信。标准库可运行，无需SDK、编译器或相机：

```sh
.venv/bin/python -S -B -m lutphoto.settingsplan review \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "/path/to/private-bundles/slot-001" \
  --output "/path/to/private-reports/settings-plan.private.json"
```

方案绑定包清单/review/contract SHA、完整程序源/目标与两类worker contract/header摘要。包含真实设置值、reset及材料指纹，标记private_report，0600排他保存/同步，绝不公开。`unit_actions_exported:true`表示确实输出了私人属性方案，`settings_write_plan_enabled:false`表示没有设备执行能力；不是可交给旧安装器的文件。

## 核对已有快照

显式提供两个本地快照及各自AP/CP图像索引，角色是调用者断言，不自动猜测。命令只读文件，不采集设备：

```sh
.venv/bin/python -S -B -m lutphoto.settingsplan check \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "/path/to/private-bundles/slot-001" \
  --stage target \
  --ram "/path/to/private-observations/settings-ram.bin" \
  --saved "/path/to/private-observations/settings-saved.bin" \
  --ram-roles 0 1 --saved-roles 0 1 \
  --output "/path/to/private-reports/settings-checked.private.json"
```

| stage | 预期状态 |
| --- | --- |
| source | 各自匹配包内原RAM/保存设置 |
| target | 所选九项匹配同一ST目标，其他已审字段保留 |
| restored | 匹配各自原值；结构通过不证明实际执行过还原 |

每次重验包、重建方案后核对快照。严格范围是AP02cf和四个保护CP单元，字段集合/值/attr/reset/容量均须符合预期。已知诊断字段02cf0b6e允许当前值变化，布局/reset仍严格；不放宽其他字段。部分目标、未知值、遗漏/新增作用域字段或角色错误均拒绝。

其他AP运行组及非保护CP记录只统计解码差异，不作为已验证保留范围；即使计数为0也不认证真实机身行为。`provided_snapshot_scope_checked_offline:true`不证明同机身、新鲜度、真实属性独立读回或保存。`independent_property_readback_verified`、`settings_save_verified`、`actual_program_and_name_stage_verified`、`actual_observation_origin_verified`、`complete_settings_transition_verified`、`other_runtime_groups_preservation_verified`、`outer_wrapper_verified`和`restore_verified`均false。

## 顺序和停止条件

组合方案在同一Reader锁内核对程序/名称的完整源/目标AP、槽位及contract，给出下列前提顺序，**不是执行脚本或可自动重放的状态机**：

| 阶段 | 计划要求 |
| --- | --- |
| 预检查 | 源程序/资源/设置复核；有程序任务才有program模式0；名称模式0核对源AP |
| 正向 | 名称模式1在源AP下完成并独立读回68资源；有程序变化才执行program模式1及完整目标读回；目标程序状态下处理设置；重载准备另行审阅、冷启动/runtime/资源/设置与照片确认后，名称模式3才按目标AP清理 |
| 逆向 | 精确目标程序/资源先复核；目标程序状态下还原设置；有程序任务才有program模式2及完整源读回；名称模式2须处于源AP并完整读回原资源；重载/冷启动另验 |
| 未知结果 | 停止、保留证据，不自动重试、还原、重放、重启或清理 |

程序零窗口省略其0/1/2任务，保留完整程序复核与名称工作。设置零变化省略实际写入/保存，保留独立读取和快照核对。名称报告缺资源哈希/job ID，不能用其成功计数替代独立68资源读回。实际SDK、临时模块加载、保存影响及重载/WBI行为留D4/D5，组合顺序不是设备许可。

## 结果与后续

stdout只显示阶段、正向需写单元数和设备禁用标志；错误只给有限类型。成功0；材料/快照/来源/关闭/存储/输出失败1；结构参数错误2。失败保留部分/完整私人输出，不覆盖/修复/续跑；文件存在不证明调用或stdout成功。原包与观察文件只读，工作目录中的历史材料保持。

[第六十二轮](../research/LUT链路调查记录-第六十二轮.md)记录21项新测试、六种自制来源的三个快照阶段及独立-S正例。下一交付D3统一离线入口、整条演练与整体审阅；完成后按[收口条件](DELIVERY-PLAN.md#离线开发收口条件)冻结版本，遇真实材料依赖就在检查点等待，不继续增加模拟轮次。D4–D6另行提示，当前不需连接或升级。见[交接](../research/HANDOFF.md)。
