# N3：Mac 工具链与事务模拟

第三十二轮交付 N3 的基础层：独立编译能力探针，以及完整指纹/精确逆向的合成迁移与故障模拟。第三十三轮补充[真实格式的资源/解码设置离线契约](CUSTOM-CONTRACTS.md)，使用自制格式夹具。**当前没有真实 Custom 固件适配器或设备执行入口。** 模拟通过不证明原厂、FL23 或已有 Custom 机身可以迁移或恢复。

## 主机工具链

上游固定 v2.1 的 `nativebuild.py` 需要 AArch64 Linux 共享 ELF，不是 Mac Mach-O 库。其 `src/looks/requirements-device.txt` 固定 Zig 0.13.0；已从审计包核对原文件，SHA-256 为 `0ec257cdee531d1ddfb4886fcb6dcb7c686ad34b20398d25cf5367716bcd1d60`，不替换旧运行锁或主环境依赖。实现依据见[固定上游编译器入口](https://github.com/QAQLeonard/a7c2-fl23-research/blob/7e54d60b458847f1befa6cfd614fbf004b8b0b90/src/looks/looktool/nativebuild.py)。

可选依赖放在独立的忽略目录；安装依赖会从 Python 包索引下载主机工具。以下在仓库根目录执行，输出文件须尚不存在：

```sh
.venv/bin/python -m venv research/materials/n3-host/env
research/materials/n3-host/env/bin/python -m pip install -r requirements-custom-host.txt
mkdir -p research/output/custom-demo
research/materials/n3-host/env/bin/python -B -m lutphoto.customhost \
  --compiler zig --compile-probe \
  --output research/output/custom-demo/zig-host.json
.venv/bin/python -B -m lutphoto.customhost \
  --compiler clang --compile-probe \
  --output research/output/custom-demo/clang-host.json
```

Zig 只接受已审计的 `ziglang==0.13.0`。Clang 来自本机 PATH；不安装或升级系统编译器。检查仅编译自制、中性的 `_init` 函数到临时文件，随后删除；不加载/执行输出，不编译实际安装模块，也不读取相机程序。ELF 检查需要 pyelftools；Clang 单独使用时可按 `requirements-firmware.txt` 准备该依赖。

- Zig 检查 AArch64/64 位小端 `ET_DYN`、`DT_INIT`、无外部库/未定义动态符号及允许的相对重定位，文件上限 64 KiB。
- Clang 只检查 AArch64 `ET_REL` 对象，不能据此说 ELF 链接或真实安装模块已经通过。
- 编译失败/超时、工具缺失或仅做版本检查都不会报告编译成功。退出 0 表示报告已生成，须另看 `probe.passed`；实际模块构建和相机安装标志始终为 false。
- 报告只保留编译器版本首行和诊断 SHA，不公开完整命令、临时路径或原始 stderr；实际宿主版本自动读取，不套用旧实机记录的系统版本。

本轮在 macOS 27.0.1 / arm64 上，Apple Clang 21.0.0 对象探针和 Zig 0.13.0 共享库探针都通过。Zig 输出 1,720 字节，含 `DT_INIT`，没有外部库或动态未定义符号；目标代码未执行。Keystone 动态库及 N1 的外部 Windows 平台测试问题仍未解决，不能改写成上游全部测试通过。

## Docker 和 Windows 11 可以做什么

可以将它们作为构建主机；“生成 AArch64 Linux 共享库”和“执行相机模块”是两个阶段：

| 环境 | 可承担的工作 | 本仓库验证状态 |
| --- | --- | --- |
| 当前 Mac + Zig | 交叉编译、ELF 检查和离线测试 | 中性探针已通过 |
| Windows 11 Intel/AMD 64 位电脑 | 安装匹配的 64 位 Python/Zig，交叉编译 Linux AArch64；不必先装 Docker | 有对应 Zig 包，用户的惠普电脑未实测 |
| Docker Linux 容器 | 固定构建依赖，执行交叉编译和离线测试；需要时可另做通用 ARM64 仿真 | 本轮没有容器构建/运行记录 |
| A7C II 机身 | 在实际 Sony 系统/服务中加载并执行相机模块 | 本地 Custom 功能尚未进入实测 |

Zig 0.13.0 提供 [Windows x86-64 Python wheel](https://pypi.org/project/ziglang/0.13.0/#files)。如果惠普电脑是 Intel/AMD 64 位 Windows 11，可作为后续编译验证备选；品牌本身不决定兼容性，CPU 架构、系统和 Python 位数须届时确认。此仓库的旧 macOS USB 接管层不能直接当 Windows 驱动层；上游 Windows 设备流程也不能代替本项目的 Mac 验收。

[Docker 官方文档](https://docs.docker.com/build/building/multi-platform/)区分交叉编译、原生多节点和 QEMU 仿真。构建时可用宿主架构的 Linux 容器运行交叉编译器，目标仍设为 `aarch64-linux-gnu`，不必为编译先仿真 ARM64；若执行通用 ARM64 测试程序，才另行考虑 ARM64 容器/仿真。Windows 上使用 Docker Linux 容器还需满足 [Docker Desktop 的系统及 WSL 2/虚拟化要求](https://docs.docker.com/desktop/setup/install/windows-install/)，本轮不要求安装或改变这些配置。

从已审阅的上游代码可知，相机 worker 访问机身特定程序、请求文件和系统状态。普通 Linux/ARM64 容器没有这些 Sony 环境；Windows 本身也不直接加载 Linux ELF。因此不能用 Docker/Windows 运行相机模块来替代机内验证，也不能根据一般 ARM64 仿真结果宣称相机安装通过。当前只编译/解析中性探针，不加载相机模块。

**目前不缺另一台电脑，不需要用户准备 Docker、连接惠普电脑或连接相机。** 后续若确实需要 Windows 对照验证，会先说明所需 CPU/系统/Python 信息与具体动作；真机阶段再提示连接、实际电量、独立介质备份及拍摄协助。没有实际需要时不提前收集设备身份、私人备份或远程访问凭据。

## 合成事务

```sh
.venv/bin/python -B -m lutphoto.custommigration fixtures \
  --directory research/output/custom-demo/cases
.venv/bin/python -B -m lutphoto.custommigration plan \
  --capsule research/output/custom-demo/cases/S0.json \
  --output research/output/custom-demo/S0-plan.json
.venv/bin/python -B -m lutphoto.custommigration simulate \
  --capsule research/output/custom-demo/cases/S0.json \
  --output research/output/custom-demo/S0-install.json
.venv/bin/python -B -m lutphoto.custommigration simulate \
  --capsule research/output/custom-demo/cases/S0.json --direction restore \
  --output research/output/custom-demo/S0-restore.json
```

S0/S1/S2/S3 分别是“原厂、FL23、历史六槽、已知部分槽”的**合成标签**，不是本机真实识别结果。每个组件只有 128 字节并带固定合成标记；字段为 AP/CP/NAMES/SETTINGS_RAM/SETTINGS_SAVED。八字节占位表、十二字节 ASCII 名称与玩具设置均不同于真实 1,215 字节原生表、68 个 UXC 资源和 Sony 备份单元。不得将 N2 候选、相机程序或备份塞进这个入口。

规划器要求完整合成 AP/CP 对命中内置来源清单，不能只改 `source_state` 或混用两个来源。来源清单只包含生成器的四个固定起点；不会自动接受上一次生成目标作为新的已审来源。读取上限 128 KiB，组件大小、模型/版本、占位槽与名称范围均有校验。来源身份策略是合成测试策略，不是实际 `device_layout` 的移植。

每个计划固定五个组件的完整来源/目标 SHA，推导不重叠窗口，在内存重建正向目标及精确反向原图；保护未选槽、无关名称、设置及保留字节。出现未选设置 RAM/保存态差异即拒绝，避免模拟组保存时把无关修改持久化。恢复必须回到当前事务的完整来源，不能混用原厂或其他机身的备份。

两个模拟备份需数据完整相同、合成机身 token 一致、存储 token 不同。token 只能发现明显重复，**不是实际介质独立性证据**，报告固定 `independent_media_verified: false`。没有读取磁盘信息或备份真实机身，也不改变旧 FL23 默认单份备份。

## 故障与停止边界

```sh
.venv/bin/python -B -m lutphoto.custommigration simulate \
  --capsule research/output/custom-demo/cases/S0.json \
  --fault CP:after-write \
  --output research/output/custom-demo/S0-unknown.json
```

该故障示例生成报告并退出 **2**，是测试预期的模拟停止。正常模拟/规划退出 0；无效输入、来源不符、已有输出或其他错误退出 1。输出均排他创建，输入不修改。

故障格式为 `COMPONENT:stage`；组件为上述五个逻辑名，阶段包括 `before-intent/after-intent/partial-write/after-write/readback-corrupt`。不允许给未变化组件注入写入故障。

引擎在完整预检查后，逐组件检查预期进度、记录写入意图、修改内存和完整读回；发生停止即进入 `NEEDS_REVIEW`。除了明确在意图前停止的情况，报告结果未知；即使最终内容恰好等于目标，也不自动重放或恢复。同一模拟对象一旦开始就不能再次执行，已完成对象也不例外。来源/目标/未知分类仅用于观察，不是继续操作授权。

日志是内存中的事件顺序，**不是断电后可恢复的持久化设备日志**。每次 CLI 都是新合成实验；`--direction restore` 从计算出的完整合成目标开始，不接收上轮未知现场，不能用它修复真实或模拟中的部分写入。正常终态只叫 `SIMULATED_TARGET_VERIFIED/SIMULATED_SOURCE_RESTORED`，没有冷启动或物理通过标志。模拟执行顺序也不是已审核的真实设备写入顺序。

## 真实 Mac 集成还缺什么

N3 保持部分完成，下一轮继续电脑端：

1. 资源/设置保护源、68 文件名及合成格式契约已单独固定并离线验证；真实布局/表检查、AP 描述符绑定和完整 BK4 解析仍缺，没有审阅资产就拒绝实际规划。
2. 核对实际 worker 编译契约、报告 ABI、运行权限/重定位及逐事务来源/目标/逆向；中性编译探针不能代替真实模块验证。Keystone 与其相关指令测试另行处理。
3. 设计持久化意图、结果恢复和单会话锁，再审 Mac USB 生命周期的接入；当前不得调用设备。
4. 为新 Custom 流程取得两份实际独立存储介质及完整备份核对证据；原厂首次安装、Mac 写入和物理恢复继续未验证。

本工具没有 install/prepare/restore 相机命令。真实测试仍在 N4，进入前提示；当前无需连接相机。固定上游审计及已有证据边界见[v2.1 审计](UPSTREAM-V2.1-AUDIT.md)。
