# N3：固定来源规则与 worker ABI

第三十五轮提供 `lutphoto.workercontracts`：从已固定的 v2.1 包读取源码，审计来源规则、请求/报告格式，并可在隔离环境中编译上游两份真实 C 源码。**编译头只含自制合成元数据，产物不绑定机身、不保留、不加载或执行。** 此模块没有 AP/CP 文件识别入口、设置写入计划、USB 或安装命令；第三十七轮另增[程序身份只读入口](PROGRAM-IDENTITY.md)，真实程序正例仍未验证。

独立的[来源清单](../research/upstream-worker.lock.json)记录 14 个成员的原路径、长度、SHA-256/Git blob SHA-1，以及完整源码包 SHA；包含布局/设置/构建/报告 Python、runtime/文件名元数据、旧 core、两份 C、SHA 头、设备依赖和 LICENSE。清单与既有 v2.1 审计交叉核对，不改旧安装器锁，不复制固件内容或真实备份。来源仍为 QAQLeonard 的[固定提交](https://github.com/QAQLeonard/a7c2-fl23-research/tree/7e54d60b458847f1befa6cfd614fbf004b8b0b90)，代码/固件资料权利见[致谢](../ACKNOWLEDGEMENTS.md)与[NOTICE](../NOTICE.md)。

## 使用

固定包已按[N1 审计](UPSTREAM-V2.1-AUDIT.md)准备后，在仓库根目录运行；输出必须尚不存在：

```sh
mkdir -p research/output/worker-demo
.venv/bin/python -B -m lutphoto.workercontracts \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --output research/output/worker-demo/source-policy.json
research/materials/n3-host/env/bin/python -B -m lutphoto.workercontracts \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --compile-workers --output research/output/worker-demo/compiled-abi.json
```

第一条只需标准库，`-S` 无 site packages 也可运行；它不编译。第二条使用已准备的隔离环境与 `requirements-custom-host.txt` 中 Zig 0.13.0/pyelftools 0.32，准备方法见[工具链说明](CUSTOM-MAC-OFFLINE.md#主机工具链)。不安装到主环境，不需要 Keystone、NumPy、另一台电脑或相机。当前 Mac 已通过两份 C 的合成头编译，Windows/Docker 未实测，也暂不需要用户协助。

成功退出 0；固定包/来源不符、编译器缺失、编译失败/超时、ELF/ABI 不符、已有输出等退出 1，不生成成功报告，不回显私人路径或原始编译 stderr。程序只读取包内固定成员，在私有临时目录写入已校验的 C/头文件，结束删除；没有归档路径提取或归档 Python 导入/执行。只复用第三十三轮已审的纯资源函数来生成自己的名称夹具。

## 来源规则：元数据审计，不是机身识别

| 来源 | 固定上游的识别要求 |
| --- | --- |
| 原厂 / FL23 首次导入 | 完整 AP 与 CP 必须命中相同种类的固定配对；清单核对 runtime 元数据与旧 core 的 ORIGINAL/FINAL 完全一致 |
| 新版 standalone | 从候选 AP 还原固定窗口后完整 SHA 命中已知来源，并按 1–63 槽位 mask 重建整个 AP 精确比较；CP 非表代码身份及表校验仍须通过 |
| 历史六槽 full7-v4 | 固定 AP 完整身份；CP 归一化代码 SHA、六表头、每表 FNV 及原生表解码检查；不能冒充 standalone |
| 未知、混合或退休方案 | 不在已审来源内，不构建真实规划，不通过修改哈希或状态放行 |

CP 代码身份归一化只清零文件 `[0x8008, 0x9c9a)` 的 24 字节校验和与 6×1215 字节表；魔数/版本仍在代码 SHA 范围内。归一化不能替代每次事务完整来源/目标 SHA 和精确逆向。报告只列完整指纹、大小、窗口数量和范围，不输出补丁字节、AP 模板或可应用窗口。读取固定元数据并不证明本机机身属于该来源，也不证明首次导入已实测。

描述符规则按固定 `devicesettings.plan` 人工审阅记录：`0x57c6710 + (attribute-0x14ea)*32`，每行 `<8I`；槽选择器 `slot+9`，一项基底加八项调整。基底 row type 3 / value layout `0x10000`，调整 type 0 / `0x40000`，调整属性起点 `0x1520`、步长 18；行属性身份和 AP 02cf 组必须正确。保护 CP/诊断字段及保存限制见[设置契约](CUSTOM-CONTRACTS.md)。**本轮没有读取真实行、建立设置键或绑定真实原生表资产，write_plan_enabled 始终 false。**

## 请求、报告与拒绝条件

| 类型 | 大小与模式 | 本地检查 |
| --- | --- | --- |
| 请求 | 16 字节，`<8sII` | 程序 A7INS001 / 名称 A7NAM001；合法整数 mode；reserved=0；拒绝 bool |
| 程序报告 | 240 字节，模式 0/1/2 | A7IRP001、版本 1、phase 9；状态/回滚/重挂载/只读/清理/euid 全 0；PID/两 inode 正数，大小/窗口计数/完整双向哈希符合契约；mode 0 的目标哈希全零 |
| 名称报告 | 136 字节，模式 0/1/2/3 | A7NMR001、固定 68 文件、成功状态、PID、reserved、预期 AP 哈希和各阶段计数；mode 3 核对命名后 AP，其他模式核对原 AP |

相对上游 Python 接入进一步收紧 PID、名称 count 必须 68、恢复 staged≤restored 且 restored+removed≤68、规范小写 SHA 和整数类型边界；未修改上游源码。错误/截断/多字节/哈希方向不符一律拒绝。C 本身的失败回滚与上层自动重放是不同机制：报告不完整仍停止，不从目标哈希猜测可以续写。

本地 API `request/validate_program/validate_names` 只打包或校验字节。正确合成包也可通过结构检查，因此 `report_structure_verified` 不等于实际机内执行证据；`native_execution_verified`、完整主机读回、物理/真实身份等标志全部为 false。名称报告也不能替代 68 个资源的完整主机读回、设置保留或界面/照片验证。

## 真实 C 源码编译，合成元数据

只将固定 `installer.c` 和 `names.c` 原字节放入临时目录，通过独立 translation unit 包含它们并添加 `_Static_assert`，不改原 C。断言 LP64/小端、请求大小/偏移，以及报告大小和全部字段偏移。程序头使用两份 256 字节自制内容的两处占位变更；名称头使用自制 UXC 和 68 文件名、合成 AP 哈希，不是身份识别的替代结果，没有调用真实设置 planner。

编译目标/关键 flags 沿用固定 nativebuild：`aarch64-linux-gnu`、PIC/共享库、无标准库/外部符号、`-Bsymbolic` 和 noexecstack 等；单模块超时 60 秒。每份输出文件必须≤64 KiB，并检查 AArch64 小端 ET_DYN、DT_INIT、无 DT_NEEDED/动态未定义符号，仅允许无符号的 AArch64 relative relocation。另核对 LOAD 文件/内存边界与不重叠、总虚拟跨度≤8 MiB、`_init` 在可执行文件区、重定位写点和 relative addend 在相应加载范围。

实际结果（合成头）：

| worker | 文件字节 | relative relocation | 零填充字节 | LOAD 总虚拟跨度 |
| --- | --- | --- | --- | --- |
| 程序 | 8,184 | 4 | 79,576 | 281,928 |
| 名称 | 21,376 | 68 | 608,240 | 824,832 |

**文件≤64 KiB 不等于加载只需≤64 KiB 内存。** 这些 ELF 检查只约束文件声明，未证明 Sony 实际加载器怎样分配、清零 BSS、重定位、设权限和维护生命周期。`camera_loader_abi_verified` 与 `firmware_bound_worker_verified` 均固定 false。产物 SHA/源与断言 SHA 留在忽略的本地报告，不提供模块下载或相机加载命令。

N3 仍部分完成。第三十六轮已增加[BK4 只读解析/设置比较及主机加载链边界审阅](BK4-OFFLINE.md)，Sony 加载行为与同机身关联仍未证明；第三十七轮已有[完整程序身份/描述符只读入口及材料清单](PROGRAM-IDENTITY.md)，第三十八轮已有[描述符/快照只读绑定](SETTINGS-BINDING.md)，第三十九轮已有[表/名称资源材料清单](IMPORT-MATERIALS.md)，真实程序/BK4/资源正例、新鲜同机身来源和完整事务仍缺，不自行搜索私人备份，不在缺资产时模拟身份。实际全局相机锁/USB、设备恢复、双独立介质备份与 N4 物理/色彩验收继续后置，进入前提示。进度见[总计划](../plan.md)、[交接](../research/HANDOFF.md)。

第六十轮另增[程序worker绑定/离线编译与报告检查](PROGRAM-WORKER-OFFLINE.md)：复用私人单槽包完整重建和此处编译/ABI/ELF检查，固定C不改，新增Window/元数据断言。新入口不再只使用此模块的微型ABI fixture，但本轮所有正例仍是自制程序/策略，真实材料、Sony加载及执行未证；原本模块的CLI与fixture语义保留。
