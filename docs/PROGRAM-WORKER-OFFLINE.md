# N3：程序 worker 绑定与离线编译

第六十轮提供 `lutphoto.programworker review/check-report`，消费已独立重建的[私人单槽包](SINGLE-SLOT-BUNDLE.md)，将完整程序前向/逆向绑定到固定 v2.1 程序 worker 元数据。可选交叉编译在临时目录完成，检查后删除头文件、模块和缓存。**没有模块导出、加载、安装或恢复入口，编译及报告结构通过不能证明机内执行。**

正例仅为真实N2离线候选与自制程序/策略、BK4/UXC；固定上游C原字节参与真实编译，但没有真实原厂程序正例。本人原厂2.00及日常卡副本继续保留，现在不需升级、连接相机或读取移动盘。QAQLeonard/ma1co/ajalt来源、固定提交与许可见[致谢](../ACKNOWLEDGEMENTS.md)和[14成员审计](WORKER-CONTRACTS.md)。

## 使用现有私人包

下面路径均为占位示例。已有包必须通过固定完整来源、150个payload及全部目标/逆向重建检查。输出父目录必须已存在，仓库外、当前用户所有、0700、规范无链接且祖先受信；报告必须是包外的新文件，不覆盖旧文件。不自动搜索材料或修改权限。

标准库审阅无需NumPy、SDK或编译器，仍会核对固定源码归档：

```sh
.venv/bin/python -S -B -m lutphoto.programworker review \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "/path/to/private-bundles/slot-001" \
  --output "/path/to/private-reports/program-review.private.json"
```

实际编译复用既有隔离环境：`ziglang==0.13.0`、`pyelftools==0.32`，不要加 `-S`，也不要把虚拟环境解释器解析为其底层系统解释器。没有这些依赖时停止，不降级编译器或跳过ELF检查；现有Mac环境已能完成本轮任务，不需要Docker或Windows电脑。

```sh
research/materials/n3-host/env/bin/python -B -m lutphoto.programworker review \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "/path/to/private-bundles/slot-001" \
  --compile-program \
  --output "/path/to/private-reports/program-compiled.private.json"
```

审阅及编译期间保持包的共享锁和文件变化检查，结束及关闭检查后才返回结果。源文件始终只读。零程序变更返回 `NO_PROGRAM_CHANGE`、空contract且不调用编译器；设置或名称仍可另有变化。

## 元数据与编译检查

- 从唯一单槽生成器已经验证的AP/CP transition取得窗口，再验证完整正反向。保留完整源/目标SHA与大小，不接受手填指纹、补丁路径、源状态或启用开关。支持范围仍是固定2.01/FL23、完整重建的standalone和历史布局，不能放行2.00。
- 对齐上游 `nativebuild.program_header`：CP先于AP，每个芯片内大于1024字节的窗口优先，再按偏移排序；窗口携带确切before/after，完整文件元数据按AP、CP顺序。最多4096窗口；另设1MiB头文件预算，超限拒绝。
- 固定14成员及完整归档核验，构建来源必须与包的commit/归档SHA相同。不导入或执行归档Python，原C与SHA头不改，另一个翻译单元包含原C及静态断言。
- 断言AArch64 LP64/小端、16字节Request、240字节Report及所有字段偏移、32字节Window及其字段偏移、整数宽度、完整文件元数据数组和窗口数。复用既有固定Zig参数及60秒编译超时。
- ELF文件≤64KiB，AArch64/ET_DYN、DT_INIT、无外部库/未解析符号、只允许无符号引用的AArch64 relative relocation；同时检查LOAD范围、可执行初始化地址、可写重定位目的和加载范围内addend。文件小于64KiB不代表加载内存也小于64KiB，实际Sony加载/清零/权限/生命周期尚未验证。

私人报告绑定包清单SHA、target review SHA、头文件/contract SHA、完整源/目标contract和实际编译摘要；**这些指纹与身份同样不得公开**。不导出头、窗口字节、请求文件或模块。`compiled_offline:true`只表示本次编译与ELF/ABI检查成功，`firmware_bound_worker_verified`、`native_execution_verified`、`camera_loader_abi_verified`等设备证据始终false。

## 检查已有报告字节

显式提供本地240字节报告和预期模式；命令只读文件，不请求相机运行worker：

```sh
.venv/bin/python -S -B -m lutphoto.programworker check-report \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "/path/to/private-bundles/slot-001" \
  --report "/path/to/private-reports/program-report.bin" \
  --mode 1 \
  --output "/path/to/private-reports/program-report-checked.private.json"
```

| 模式 | 报告before hash | 报告after hash | writes |
| --- | --- | --- | --- |
| 0，预检查 | 包的完整源 | 全零64字节 | 0 |
| 1，应用 | 包的完整源 | 包的完整目标 | 精确窗口数 |
| 2，逆向 | 包的完整目标 | 包的完整源 | 精确窗口数 |

每次重新检查包并重建contract，再用既有 `validate_program` 校验格式/模式/phase9、全部成功状态、正pid/inode、精确大小/计数/完整哈希方向。零程序变更不接受报告。16字节请求只在内存中按固定magic/mode/reserved0编码并记SHA，不保存或发送。

`report_structure_verified:true`只证明输入字节符合此contract，**报告可被人工构造，pid/inode正数不认证其来源**；`native_report_origin_authenticated:false`。模式2结构通过不表示恢复成功，更不是重跑、逆向写入或设备操作授权。

## 失败和后续

stdout只有阶段、是否离线编译和设备禁用标志；详细报告私有0600排他保存/同步，异常只输出错误类型。成功0；材料、依赖、编译、报告、关闭或输出失败1；参数结构错误2。失败可能保留部分/完整报告，不删除、修复、覆盖或续跑；报告文件存在不证明stdout及调用成功。

本轮18项新测试、四条自制路线实际编译与三模式报告检查见[第六十轮](../research/LUT链路调查记录-第六十轮.md)。名称worker绑定、完整BK4设置容器和机身事务/恢复仍未完成。下一步先完成名称worker的离线绑定/编译，继续复用同一包；真实SDK与同机材料、独立介质和N4摄影验收后置，进入设备阶段前另提示。见[交接](../research/HANDOFF.md)与[总计划](../plan.md)。
