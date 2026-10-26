# A7C II 硬件平台与独立恢复入口调查

日期：2026-10-22。目标是判断能否建立类似服务器外部启动盘的恢复能力。本轮只检索官方资料、读取公开研究源码和检查官方开源内核归档；没有访问USB、运行机内程序、读取私人材料或更换本项目固定依赖。

## 结论

**A7C II 的公开内核证据指向ARM64、CXD90057主处理器平台和四个Cortex-A35核心。已有同平台相机通过BootROM加载RAM恢复环境的公开研究，值得沿此方向继续核验；尚未找到并验证A7C II自身独立恢复与写回后正常启动的完整证据。**

不能把“都是ARM／BIONZ XR”视为同一块板，也不能把“可读备份”“正常系统中恢复原厂功能”“底层重刷”视为同一能力。现阶段不建议为运行A7C II固件购买通用ARM开发板；如确需硬件验证，能正常启动、通信且版本与研究匹配的同型号测试机身更有代表性。RP2040是辅助启动器，不是相机替身。

## 1. 硬件平台：这次取得的直接证据

索尼官方为[ILCE-7CM2 Ver.2.01](https://oss.sony.net/Products/Linux/DI/ILCE-7CM2_Ver201.html)发布了Linux源码。阅读[下载说明](https://oss.sony.net/Products/Linux/notice.html)后，仅下载其中公开内核，不下载或读取机身固件备份。

归档地址：[linux-kernel.tar.gz](https://prodgpl.blob.core.windows.net/download/DI/20251111_ILCE-7CM2_Ver.2.01/linux-kernel.tar.gz)。大小109,975,591字节；本轮SHA-256为`99a6f717659a87a60fd92475edcfe734f73617874650c6aa1d28ca71e2140d3d`。实算MD5与服务端Content-MD5一致，仅用于核对下载完整性，不当作安全签名。

| 归档内文件与行号 | 内容 | 可以据此说什么 |
| --- | --- | --- |
| linux-kernel/.config:5,31,359,535 | ARM64=y、SMP=y、ARCH_CXD900XX=y、NR_CPUS=4 | 发布配置使用64位ARM、多核CXD平台，最大CPU数为4 |
| arch/arm64/boot/dts/cxd/cxd90057_set.dts:32,36–37 | 引入cxd90057.dtsi；model/compatible指向CXD90057 | 官方机型源码的主处理器平台指向CXD90057 |
| arch/arm64/boot/dts/cxd/cxd90057.dtsi:91–125 | cpu@0至cpu@3均为arm,cortex-a35 / arm,armv8 | 平台设备树描述四个Cortex-A35核心 |
| linux-kernel/Makefile:1–3 | 4、9、337 | 本次公开源码版本为Linux 4.9.337；不冒充读取了实机运行内核 |

索尼[发布资料](https://sony.mediaroom.com/2023-08-29-Sony-Electronics-Releases-Two-New-Alpha-7C-Series-Cameras)确认BIONZ XR和AI处理单元。[OpenMemories研究](https://github.com/ma1co/OpenMemories-Docs/blob/master/hardware.rst)将CXD90057称为Mira，并说明同代BIONZ平台还有实时处理等部分。相机不是单个普通Linux进程或只含一颗ARM CPU的开发板。

**证据边界：**源码中的平台名不是可购买主板型号；本轮未确认用户机身PCB料号、板修订、芯片封装后缀、熔丝配置或实际启动参数。也不能直接把A7 IV上的CXD90058协处理器识别当成已独立确认A7C II的全部芯片清单。相同Cortex内核无法保证引脚、存储布局、外设、启动认证和固件兼容。

## 2. 已找到的恢复路线

| 项目／路径 | 已公开的能力和证据 | 对A7C II的意义与限制 |
| --- | --- | --- |
| DavidBuchanan314 / ILCE-7M4-RE | A7 IV的BootROM串行入口；RAM中的裸机Fastboot；eMMC读写与分区加密处理源码 | 真正接近独立恢复入口；原作者范围是A7 IV，不能直接运行到A7C II |
| xyzhangxin / sony-a6700-powerful | A6700 2.00从USB-C相关线路触发RAM引导，进入只读Fastboot；作者记录读取用户区分区表覆盖范围及两个引导区各前4MiB | 支持该思路能被移植到另一机型；明确尚未验证完整恢复，不是A7C II教程 |
| Erlla / sony-a7m4-custom-firmware 方法0 | 已进入Fastboot后准备受限SD更新入口；报告历史同机恢复日志及正常取景 | 可参考“底层入口→官方更新器”架构；仅A7 IV及一份精确修改版更新器，不支持随意套用原厂或A7C II |
| QAQLeonard / a7c2-fl23-research 3.0.2 | A7C II服务模式内恢复项目涉及的原厂2.01区域，重启后核对；作者报告一台Windows机身通过 | 可改善正常撤销和有限中断恢复；仍依赖服务接口与机内执行，不是BootROM救砖 |
| YuuLuo / a7c2-service-preload | A7C II 2.01正常MSC→服务认证→机内临时代码执行 | 当前修改工具的重要入口；依赖运行系统，不证明主系统损坏后仍能使用 |

### 2.1 最接近服务器重装能力：A7 IV的BootROM路线

核对提交：`2328d18ce640e6c8cd9341efcf0043ce9042a135`。

- [项目说明](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/2328d18ce640e6c8cd9341efcf0043ce9042a135/README.md)：通过早期串行启动入口把恢复程序载入RAM，再通过USB访问eMMC。正常相机Linux／应用不是这条路径的执行环境。
- [BootROM说明](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/2328d18ce640e6c8cd9341efcf0043ce9042a135/bootrom/README.md)：区分Mira主处理器与Cetus协处理器的不同启动入口。
- [Fastboot实现](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/2328d18ce640e6c8cd9341efcf0043ce9042a135/payloads/fastboot/src/fastboot.c)：有实际分区写入逻辑；逻辑分区AES-XTS与原始引导区处理不同。`nflasha`范围按分区表最大末端计算，不自动等于物理eMMC全容量。
- [机型限制讨论](https://github.com/DavidBuchanan314/ILCE-7M4-RE/issues/2)明确原作者没有A6700，仓库针对A7 IV。[USB-C讨论](https://github.com/DavidBuchanan314/ILCE-7M4-RE/issues/3)仍涉及连接与引脚识别，不能把Multi接口接线原样复制。

这里的Fastboot是研究者写的临时程序，不是已证实Sony向普通用户开放了Android式Fastboot。源码可写入也不等于任意损坏均有成功恢复记录。数据加密、固件包签名与启动阶段认证是不同问题；A7 IV某层的研究结果不能推广成A7C II所有层都没有签名检查。

### 2.2 A6700：已经有跨机型移植，但仅证明读取路线

核对提交：`ac1cd0db5d0210292be1cee292d15034a222ae64`。

[操作手册](https://github.com/xyzhangxin/sony-a6700-powerful/blob/ac1cd0db5d0210292be1cee292d15034a222ae64/操作手册.md)说明不要求正常菜单或MSC，使用Pico注入RAM只读程序。作者记录读取1,864,368,128字节的用户区分区表覆盖范围和两个引导区各前4MiB，同时明确未确认全物理容量、完整恢复未验证。

[构建器](https://github.com/xyzhangxin/sony-a6700-powerful/blob/ac1cd0db5d0210292be1cee292d15034a222ae64/源码/脚本/构建相机引导.py)调整USB线路选择，限定只读命令，并检查产物不含存储写入等符号。这是具体的板级适配工作；并非改一个产品名就能通用。[开发计划](https://github.com/xyzhangxin/sony-a6700-powerful/blob/ac1cd0db5d0210292be1cee292d15034a222ae64/开发计划与进展.md)仍将完整备份／恢复和官方固件救砖列为未完成验证。

### 2.3 A7 IV的SD恢复：有历史案例，但限制非常具体

核对提交：`7149216db1ebcd0ed4928d968616884ad404d232`。

[方法说明](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/7149216db1ebcd0ed4928d968616884ad404d232/methods/00-sd-recovery/README.md)要求已经进入Fastboot，核对更新器、保存六个分区，写入受限恢复标志，再让现有机内更新器处理卡内包。当前[配置](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/7149216db1ebcd0ed4928d968616884ad404d232/a7m4/profiles/sd-recovery.json)只有一份此前验证的修改版更新器。

[验证记录](https://github.com/Erlla/sony-a7m4-custom-firmware/blob/7149216db1ebcd0ed4928d968616884ad404d232/methods/00-sd-recovery/validation.md)区分历史单机成功与公开适配版离线测试；主机成功只表示触发更新，仍需机内完成证据。六分区备份不是全机备份；更新器、SD链或其他启动阶段损坏仍可能无法恢复。本报告不提供修改版本字段或更新门控的操作，不改变本项目禁止绕过检查的规则。

### 2.4 A7C II最新“恢复原厂功能”的实际含义

搜索索引仍显示2.2-preview.1；本轮直接读取GitHub确认main已到3.0.2，提交`042f000c57f967bf0fd3fd4faecccc3a0c398400`（2026-10-22）。此前本项目的固定v2.1审计不涵盖该版本。

[README验证表](https://github.com/QAQLeonard/a7c2-fl23-research/blob/042f000c57f967bf0fd3fd4faecccc3a0c398400/README.zh-CN.md#验证状态)报告作者一台Windows+A7C II完成原厂功能恢复、读回和重启核对；macOS实机USB仍未验证。这是作者声明，本轮没有取得第二方或本项目实机复现。

源码核对结果：

- [direct.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/042f000c57f967bf0fd3fd4faecccc3a0c398400/src/looks/looktool/direct.py#L55)内置原厂区域覆盖指定程序片段，恢复选定色彩／槽位设置，保留范围外数据；不是刷入整份Sony官方DAT或整芯片复原。
- 同文件的`verify_direct`检查RAM和保存设置、重启标识、运行区域及只读挂载，是有价值的恢复后核验。
- [devicesession.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/042f000c57f967bf0fd3fd4faecccc3a0c398400/src/looks/looktool/devicesession.py)仍使用MSC或已记录身份的存续服务会话；后者不等于独立于系统的启动入口。
- [checkpointjob.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/042f000c57f967bf0fd3fd4faecccc3a0c398400/src/looks/looktool/checkpointjob.py)及新区域恢复采用的准入规则与本项目固定完整指纹规则不同。不能未经单独审查直接升级依赖、取消哈希门槛或将“无需旧备份”推广为不需要保留本机原始材料。

## 3. 买什么硬件才有测试价值

| 候选 | 能覆盖的工作 | 不能替代的工作 |
| --- | --- | --- |
| 通用ARM64开发板／ARM服务器 | 与硬件无关的算法、部分工具和接口模拟 | Sony整机启动、专有驱动、协处理器、持久化与真实恢复 |
| RP2040 Pico及经过核验的接口辅助电路 | 作为早期启动波形／RAM程序发送器 | 不能装上A7C II固件充当相机；A7C II接线和载荷尚未验证 |
| 同为BIONZ XR的其他型号 | 研究共用协议、对照BootROM／驱动 | 不能证明A7C II的引脚、存储、更新器或补丁兼容 |
| A7C II裸主板 | 在配套供电、控制和外设条件已清楚时研究主板 | 不是开箱即用开发板，缺少组件会混入新的启动故障 |
| 能正常启动的同型号测试机身 | 建立基线，验证进入恢复环境、退出、受限写回与冷启动 | 仍需逐机版本／身份核验，不允许不同机身互刷个体数据 |

这是基于依赖关系的工程判断。本轮没有找到可直接运行A7C II固件的零售CXD90057通用开发板，也未核定替换主板料号。若预算用于保障主力机，优先考虑同型号测试机身；无法开机且原因未知的故障机不适合建立第一条恢复基线。采购前应先明确独立入口的机型适配需求，本轮没有下单或制作接线。

## 4. 如何逐步建立恢复官方版本的保障

1. **先定义恢复范围。** 撤销本项目所有修改、重装官方2.01、更新到另一官方版本是三种验收。恢复设置菜单不还原程序；正常启动也不证明官方更新会接受包。
2. **先做离线兼容审查。** 以官方CXD90057源码及上述固定研究为依据，核对A7C II的启动入口、USB切换、内存／存储与协处理器依赖。源码同族只产生候选，不放行设备操作。
3. **在测试机身验证独立只读入口。** 从全新启动进入RAM环境，读取并重复核对机身身份／布局／指定内容，再确认退出后正常启动。不修改主系统来“证明救砖”，也不把RAM执行称为无设备操作。
4. **形成同机、覆盖明确的恢复材料。** 区分原始加密扇区、解密逻辑分区、引导区、协处理器存储、校准／身份／设置；记录已覆盖与未覆盖范围。当前AP/CP文件备份不自动升级为全机备份。
5. **再在测试机身验证受限写回与重启。** 写入能力需要独立实机证据；能读、能列分区、电脑报告成功都不能替代写后读回与冷启动。正常写回成功后，才评估具体故障的恢复覆盖。
6. **单独验证官方更新兼容。** 针对确切来源、目标和原有更新器完成真实更新／重刷验收；保留签名、机型和版本规则，不靠伪造身份或放宽白名单。没有验证的同版本重刷、降级与未来版本继续列为未知。

在持续供电的既定前提下，最值得优先研究的是第2–3步：让恢复工具尽可能独立于被修改的相机应用。若在A7C II证明了该入口并完成写回闭环，可以显著降低主系统损坏的恢复风险；目前仍不能承诺任意故障都可自行修复或必然不需要维修。

## 5. 本轮检查与边界

- 官方内核归档下载完成；核对长度、MD5及SHA-256；只用标准库读取归档成员，没有执行／编译源码。
- 逐项读取上述固定提交的公开文档、恢复入口与关键源码，区分作者声明、源码能力和本轮观察。没有运行任何第三方设备脚本或相机命令。
- GitHub跨仓库`7CM2 + fastboot` issue检索本轮返回0项；公开搜索也未找到可核对的A7C II专用BootROM恢复闭环。这不是不存在该能力的证明。
- 本轮新增调查报告并维护计划；文档检查见[plan.md](../plan.md)。旧[持续供电方案](POWERED-UPDATE-SAFETY.md)与[全项目回滚评估](ROLLBACK-SAFETY-REVIEW.md)的本地实现状态不变，新增研究不提升D4/D5或真机验证状态。

保留David Buchanan、ma1co、QAQLeonard、YuuLuo、xyzhangxin、Erlla及各上游的研究归属。本轮只引用与分析，不复制第三方实现进入运行代码或重新发布原厂固件材料。
