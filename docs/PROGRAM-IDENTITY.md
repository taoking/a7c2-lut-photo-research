# N3：完整程序身份与描述符只读检查

第三十七轮增加 `lutphoto.programidentity`。它从[固定 14 成员清单](../research/upstream-worker.lock.json)核验的 v2.1 包读取来源规则，以命令显式提供的本地 AP/CP 文件作完整内容识别，再读取所选槽的描述符。规则来自 QAQLeonard 的 `device_layout.py`、`six.py`、`devicesettings.py` 和 runtime 元数据，保留[署名及许可](../ACKNOWLEDGEMENTS.md)。不导入归档 Python，不修改旧安装器或运行锁，没有设备命令、备份写回、目标程序输出或写计划。

**本轮只用自制程序夹具验证正例，真实 CLI 只验证材料查询及未知输入拒绝；没有读取真实程序、备份或照片。** 实际机身程序正例和描述符兼容性未验证。测试内部的小策略不开放为 CLI 参数，不能通过自填指纹、任意策略文件或模拟身份放行输入。

## 先查材料，再显式检查

固定包按[N1 说明](UPSTREAM-V2.1-AUDIT.md)准备后，只需 Python 标准库。父目录须存在，输出必须尚不存在；可加 `-S` 禁用 site packages：

```sh
mkdir -p research/output/program-demo
.venv/bin/python -S -B -m lutphoto.programidentity requirements \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --output research/output/program-demo/materials.json
```

此命令只核验固定包和来源/ABI 元数据，不打开任何程序文件、搜索目录或连接相机。后续真实只读正例需要：

| 材料 | 要求与缺口 |
| --- | --- |
| 完整程序 | 用户明确提供本地 `appFw.so`（99,960,744 字节）及 `cpapp-b.bin`（18,090,880 字节）路径；来自本人授权、同一捕获来源的 ILCE-7CM2 2.01 完整程序，不能提供片段、改名后的其他版本或混用备份 |
| 来源记录 | 保留原目录和捕获记录，不覆盖原备份；文件大小/内容匹配也不能证明同机身、捕获时序、当前磁盘状态或备份介质独立 |
| 固定规则 | 包必须命中清单中的完整 SHA/成员哈希；只接受原厂/FL23、可完整重建的 standalone 或历史 full7-v4，退休/未知方案拒绝 |
| 后续设置接入 | 将来需显式提供新鲜 RAM/保存快照及可信角色/来源证明；本命令没有读取 BK4，也没有验证设置值或绑定 N2 表资产 |

已有文件且明确路径后才运行下面命令；示例 `/path/to/owner-backup` 须替换为本人提供的路径。没有材料时停留在查询/夹具测试，不为验证此入口自动运行相机 prepare/diagnose：

```sh
.venv/bin/python -S -B -m lutphoto.programidentity inspect \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --ap "/path/to/owner-backup/appFw.so" \
  --cp "/path/to/owner-backup/cpapp-b.bin" \
  --slots 1 2 \
  --output research/output/program-demo/identity.json
```

`--slots` 取互异整数 1–6；检查可包含尚未启用的槽，报告的 `mask` 是当前 AP 的启用位，不是本次写入请求。成功 0，输入/身份/描述符/来源不符、读取期间变化或已有输出等失败 1；错误只输出类型，不回显私人路径/字节。输入必须是固定大小的普通文件，拒绝符号链接及非普通文件，读取前限制大小，读取后核对长度与文件元数据。所有输出排他创建，源文件原字节保留。

## 完整身份规则

| 路线 | 检查 |
| --- | --- |
| 原厂 / FL23 首次导入 | 完整 AP 与 CP 的大小及 SHA 必须命中相同 kind 的固定配对；不能把原厂 AP 配 FL23 CP 或已改 CP |
| standalone | 固定窗口还原后，对整个 AP 计算 SHA 并匹配来源；识别非零 1–63 mask，再逐字节核对全部还原窗口的目标结果，包含未选槽原标签。窗口之外已由完整还原 SHA 覆盖，等价于整个 AP 重建比较；不分配/输出目标 AP，没有忽略范围 |
| 历史 full7-v4 | 完整 AP 固定 SHA；CP 归一化代码 SHA 与 standalone 分开，不能混淆两个适配器 |
| 已导入 CP | 仅将 `[0x8008,0x9c9a)` 的六个 checksum 与 6×1215 字节表在虚拟哈希流中清零；完整其余代码、长度、魔数/版本仍固定。每张表再检查 FNV-1a 及所有 signed int8 值在 −64…63，等价于现有 native decode 的范围条件 |

可变表被允许不代表忽略其身份：报告仍记录本次完整 CP SHA。此读取器不生成来源/目标事务、不执行逆向、不提供任何可应用窗口或固件模板。完整事务/目标/逆向绑定仍须独立实现和验证。

## 描述符和证据边界

只有完整 AP/CP 身份通过才读 AP 文件中的行。地址公式和九字段策略见[worker 说明](WORKER-CONTRACTS.md)：每槽一个基底加八个调整，另外核对八个共享 ST 调整引用行。检查行边界、属性身份、AP 02cf 组、类型/布局；额外对 ST 引用也检查调整类型/布局，拒绝诊断字段、所选键重复、ST 引用重复及二者别名。六槽共 54 个所选字段与 8 个共享引用；报告仅给槽位/计数，不输出键、行或设置值。

`local_program_content_verified:true` 只说明显式读取的本地文件符合固定内容规则。`actual_source_identity_verified`、机身/芯片关联、真实捕获来源、加载器、机内执行、当前设置和物理验证均为 false；`live_descriptors_verified` 与 `write_plan_enabled` 也为 false。不能把文件描述符正确称为相机 RAM/保存值已验证，不能据此启动 installer/worker。

报告含完整输入 SHA，标为 `private_report`；程序、报告、身份和捕获记录不上传公开仓库。来源 metadata 和自制单元测试留在仓库，原始程序与本地报告保持忽略。

本轮新增 23 项测试，覆盖两种来源各 63 masks 的独立完整重建、六表/256 字节值范围、混合/未知布局、额外改动、描述符身份/别名、读取变化、文件保护及无设备导入。真实正例材料仍缺；当前不需要相机、Docker 或惠普电脑协助，后续需要文件时只请求必要的本地路径。第三十八轮已接通[描述符→RAM/保存快照的只读绑定](SETTINGS-BINDING.md)，不证明捕获新鲜度或同机身来源；第三十九轮已有[表/名称资源材料清单](IMPORT-MATERIALS.md)，完整事务和真实材料来源仍缺；真实写入/恢复、USB/全局锁、独立介质及 N4 色彩/冷启动继续后置，进入前提示。见[总计划](../plan.md)和[交接](../research/HANDOFF.md)。

第五十八轮另有独立[单槽目标/逆向检查](SINGLE-SLOT-TARGET.md)，复用本读取器，在内存重建完整程序并验证精确前向/逆向，连接所选设置投影及68资源；本读取器原报告/只读接口不变。正例仍是自制材料，完整设置/持久化事务、真实来源、worker/部署和恢复没有因此完成。
