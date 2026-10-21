# N3 / D1：名称worker离线绑定与编译

第六十一轮提供 `lutphoto.nameworker review/check-report`。它在同一私人单槽包的共享Reader锁内，复用完整重建的68个资源目标/逆向及原始冻结输入，绑定固定上游名称worker元数据，并可临时交叉编译原C。**D1离线完成不代表资源部署、机内执行、设置事务或恢复完成；没有模块导出、加载或相机操作入口。**

规则来自QAQLeonard固定v2.1，保留ma1co/ajalt研究署名与许可，见[致谢](../ACKNOWLEDGEMENTS.md)、[14成员来源/ABI](WORKER-CONTRACTS.md)。全部正例为自制程序/策略、BK4/UXC与实际N2离线候选；固定C真实编译，目标代码未执行，未使用真实机身材料。当前原厂2.00和日常卡副本保留，不需升级、连接或读取移动盘。

## 使用已有私人包

先有[已验证私人包](SINGLE-SLOT-BUNDLE.md)。下列均为占位路径；输出必须是包外、仓库外的新文件，父目录已存在、归当前用户、0700、规范无链接且祖先受信。不搜索材料、不更改旧包或自动修改权限。

默认审阅只需标准库，核验固定归档及包完整来源，绑定元数据，不编译：

```sh
.venv/bin/python -S -B -m lutphoto.nameworker review \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "/path/to/private-bundles/slot-001" \
  --output "/path/to/private-reports/names-review.private.json"
```

实际编译复用现有Zig0.13.0/pyelftools0.32隔离环境，不加 `-S`；无需Docker/Windows或新依赖：

```sh
research/materials/n3-host/env/bin/python -B -m lutphoto.nameworker review \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "/path/to/private-bundles/slot-001" \
  --compile-names \
  --output "/path/to/private-reports/names-compiled.private.json"
```

原C/SHA头原字节参与编译，独立翻译单元附加Request/Report全部偏移、80字节Asset及字段偏移、68项数组、6×64名称、68×6旧指针与完整AP元数据断言。复用[程序worker](PROGRAM-WORKER-OFFLINE.md)的来源检查、编译器/60秒超时、ELF/LOAD/初始化/重定位检查，以及私有排他报告保存。头、模块、缓存只在临时目录存在，结束删除；不导入或执行归档Python。

## 实际绑定

| 部分 | 依据和边界 |
| --- | --- |
| 资源与布局 | 固定文件顺序、68个完整原/目标长度与SHA，完整逆向重建；标签顺序从已识别程序派生，保留standalone和历史六槽顺序差异 |
| 名称和指针 | 选择文件中的单槽/UTF-8名称与已检查review匹配；六个64字节C缓冲区用数值编码，旧指针来自原资源；2860布局缺标签用65535，扩展时未选名称为ST，2866布局保留未选项 |
| 原生缓冲限制 | 固定C的assetbuf为524288字节；原资源至少5740字节，原/目标都不超过512KiB。离线资源格式允许的范围更宽，不代表该C能处理，超限在编译前拒绝 |
| AP方向 | plain为包的完整源AP，named为完整目标AP；额外核对完整前向/逆向。两者可相同，不能自行替换为当前机身状态 |
| 备份命名 | 固定 `/usr/share/app/.a7c2-lut-` 命名空间加16位小写十六进制ID；离线ID由包清单/review绑定派生、可复现，不接受命令行覆盖，也不是实际设备事务ID或执行许可 |
| 所有者 | 保留上游固定uid57285/gid1000，不放宽；实际文件所有者未验证，不能仅凭这份元数据进入设备流程 |

程序零窗口仍可能需要名称工作；本入口照常绑定和编译68资源，不根据程序无变更跳过。整个过程沿用同一Reader、150 payload重建和关闭/变化检查；读回内容或关闭不确定时不返回成功。

## 四模式报告检查

显式提供本地136字节报告及预期模式，只检查文件字节：

```sh
.venv/bin/python -S -B -m lutphoto.nameworker check-report \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "/path/to/private-bundles/slot-001" \
  --report "/path/to/private-reports/names-report.bin" \
  --mode 1 \
  --output "/path/to/private-reports/names-report-checked.private.json"
```

| 模式 | 报告预期AP | 成功计数条件 |
| --- | --- | --- |
| 0，预检查 | 完整源AP | staged/linked/committed/restored/removed全部0 |
| 1，暂存及替换 | 完整源AP | staged/linked/committed各68，restored/removed为0 |
| 2，名称逆向 | 完整源AP | linked/committed为0，staged≤restored，restored+removed≤68；允许没有资源需要还原 |
| 3，清理备份 | 完整目标AP | staged/linked/committed/restored为0，removed为0–68 |

每次重验包并重建contract，再调用既有 `validate_names`，严格检查magic/版本/模式/phase9、固定68文件、全部成功状态、正PID、reserved0与AP完整SHA。请求仅在内存按A7NAM001/mode/reserved0编码并记SHA，不保存或发送。

**固定报告不含资源哈希或作业编号。** 同一个AP、不同名称/资源包可对应完全相同的报告字节。头/contract绑定具体包，但 `report_structure_verified:true`只表示字节符合上述AP/计数契约；`report_contains_resource_hashes_or_job_id`、`report_authenticates_bundle`、`native_report_origin_authenticated`、`resource_full_readback_verified`及机内/恢复证据均false。不能用计数代替68资源完整读回、调用来源证据或真实界面验证。

模式0/1/2依赖源AP、模式3依赖目标AP；名称/程序/设置的执行顺序必须在D2及后续设备集成中明确。本轮没有执行顺序调度、触发器、重试/续跑或设备恢复入口，报告通过不授权这些操作。

## 输出、失败与下一步

详细报告含材料指纹、资源contract和离线ID，0600新文件私有保存/同步，不能公开；不导出资源、头、模块或请求字节。stdout仅阶段、是否编译和设备禁用摘要。成功0；材料/依赖/编译/报告/关闭/保存/stdout失败1；参数结构错误2。失败保留部分/完整现场，不覆盖、修复或续跑；文件存在不证明调用及输出成功。

[第六十一轮](../research/LUT链路调查记录-第六十一轮.md)记录19项新测试、七组自制材料实际固定C编译及四模式报告检查。下一交付为D2完整设置处理和程序/名称衔接，再做D3统一离线演练/审阅；到真实SDK/同机材料缺口按[收口条件](DELIVERY-PLAN.md#离线开发收口条件)停在检查点，D4–D6另行安排。见[当前交接](../research/HANDOFF.md)。
