# 第三十五轮：固定来源策略、真实 worker 源码与报告 ABI

日期：2026-10-19。继续 N3，转向固定源码和 ABI，不继续泛化合成事务。仅离线源码/构建检查；不读私人程序/备份，不操作 USB、相机或目标模块。

## 本轮检查项

- [x] 额外固定 14 个来源/元数据文件，核对旧运行锁及来源配对策略。
- [x] 建立原厂/FL23/历史六槽/standalone 与设置描述符的只读策略清单。
- [x] 两种请求/报告 ABI 的严格解析、拒绝测试和 C 编译期布局断言。
- [x] 用合成元数据编译真实上游 C 源码，只检查 ELF，不加载执行或保留产物。
- [x] 完整回归、实际 CLI、公开审查及文档交接；审核后提交推送，结果见最终报告。

## 来源、交付与边界

新增 `lutphoto.workercontracts` 和[独立来源清单](upstream-worker.lock.json)，实现与命令见[说明](../docs/WORKER-CONTRACTS.md)。完整包仍为 `8c6c30448219f4e865e8005d2ffa789248e984d73b0f9342035f7065a1a232f7`，提交仍为 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`。14 成员含布局/设置/构建/报告、runtime/资源名元数据、旧 core、两份 C/共享 SHA 头、设备依赖及 LICENSE；与既有审计重叠项逐项一致。固定包内各成员与本地对应副本原字节一致，旧 26/46 来源审计再次通过，原安装器锁未改。

源码只作 AST 字面量提取和元数据检查，不执行归档 Python；仅使用第三十三轮已审 vendored 纯资源函数生成自己的名称夹具。报告列原厂/FL23 完整 AP/CP 对，与旧 core 的 ORIGINAL/FINAL 一致；历史六槽与 standalone 的代码归一化策略、表头/FNV/原生解码、64 AP 模板和 1–63 mask 的完整重建要求分开记录，不输出补丁/模板字节。

设置描述符只记录已审源码规则：表基址、属性起点/步长、行格式、基底/调整类型、九字段/槽、保护 CP 和诊断字段；没有读取真实行或建立键计划。真实 AP 识别和 `devicesettings.plan` 仍未接入，不用模拟身份放行。

请求 16 字节；程序报告 240 字节，名称报告 136 字节，严格核对模式、状态/清理/euid、PID、完整指纹、大小、inode 和计数。相对上游接入收紧 PID、固定 68 资源、恢复计数相关性及规范值；没有改上游。结构正确的合成报告可以通过，因此不称为实际 native 执行，主机完整读回和物理验证始终 false。

两份上游 C 原字节存于临时目录，独立 translation unit 包含源码并添加 LP64/小端、Request/Report 大小及全部字段偏移断言；自制合成头替代私人清单，但不调用真实规划器，不构建可安装候选。Zig 0.13.0 隔离环境沿用第三十二轮，主环境/运行依赖不改；Keystone、外部 Windows 断言未解决，也不影响这两个不需 Keystone 的编译检查。

## 测试命令与结果

最终实际执行并退出 0：

```sh
.venv/bin/python -B -m unittest research.tests.test_workercontracts -q
.venv/bin/python -B -m unittest discover -s research/tests -q
.venv/bin/python -B -m unittest discover -s tests -q
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q
.venv/bin/python -B -m macfl23 check
.venv/bin/python -B -m research.audit_upstream_looks \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --output research/output/custom-round35/upstream-source-audit.json
.venv/bin/python -S -B -m lutphoto.workercontracts \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --output research/output/custom-round35/source-catalog.json
research/materials/n3-host/env/bin/python -B -m lutphoto.workercontracts \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --compile-workers --output research/output/custom-round35/workers-verified.json
```

新增专项 **19 项**，完整研究 **254 项**、Mac **39 项**、旧固定上游 **8 项**，合计 **301 项通过**。覆盖全部请求/报告模式、各错误字段/完整哈希与方向/截断、无效契约、AST 不执行、来源对/模板/窗口漂移、包/成员完整性与重复成员、ELF 加载范围负例、编译失败/超时、既有输出保护和不导入 USB/NumPy/macfl23/PMCA/looktool。旧测试的 USB 提示来自模拟，未打开设备。CI 默认不下载此可选源码包或安装 Zig，只运行独立夹具测试；实际两份 C 编译为本地另行验证，不能冒称已在 CI 构建。

最终 `workers-verified.json`：

| 编译结果 | 程序 | 名称 |
| --- | --- | --- |
| 文件字节 | 8,184 | 21,376 |
| 文件 SHA-256 | `90651855eeddc612af7a5704f03bf82dca12155bc90ca884a7a16a0c6c82de0e` | `5367e5b0f67ded589d21d964bcc4ebbc96f085bc94160e60552ac567dd3267fc` |
| 原 C SHA-256 | `0e3cbd92feaa813a304b87f948fc9d6e578486691b6e6dd070fc853f544966c7` | `92b99b5145628d824ce4be21b4d1f2e76ed723aa55c5cd750fabf816a08ba351` |
| relative relocation / LOAD 段 | 4 / 4 | 68 / 4 |
| 零填充字节 / 总虚拟跨度 | 79,576 / 281,928 | 608,240 / 824,832 |

两者均小端 AArch64 ET_DYN、有 DT_INIT、无依赖/未定义动态符号，ABI 静态断言、相对重定位类型/符号、LOAD 范围、初始化入口、重定位写点与 addend 范围通过。文件≤64 KiB 并不能证明只需≤64 KiB 内存；Sony 的映射/BSS 清零/权限/生命周期仍须独立审阅，`camera_loader_abi_verified` 固定 false。源/header/assertion/输出 SHA 均在忽略报告，目标文件随私有临时目录删除，从未加载执行。

实际 CLI 另验证已有报告拒绝并原字节保留，损坏包拒绝且不生成报告，原源码包完整 SHA 不变，标准库 source-catalog 与编译报告中的政策内容一致。过程早期编译亦通过；最终报告采用长度一致的 256 字节自制 AP 元数据，明确标为合成头，未把早期报告作为机身来源绑定证据。

公开审核覆盖 AST/JSON、本地链接及锚点、个人路径/疑似密钥/NUL、禁止资产和显式改动清单、空白、旧计划归档/运行锁 SHA 及保护路径。源码包、头/ELF、原始构建日志和全部输出报告不提交。沿用授权仅推送 `lut-photo/main`，不推 origin；提交前列出测试命令及结果，提交/远端/CI 以最终报告和 Git 历史核对。

## 遗留与交接

N3 部分完成。下一轮优先核对固定服务/Jiritsu 加载链对 LOAD/BSS/重定位/生命周期的契约，并审阅 BK4 解析接口、同机身来源关联和原厂/FL23 完整资产清单；仅源审阅/离线格式层，不自行搜索或读取私人备份。缺已审资产时拒绝真实身份/描述符规划，不将合成头构建转称可用安装模块。

真实来源/描述符接入、机身绑定 worker、全局相机锁/USB、设备事务/恢复、双独立物理介质备份及 N4 冷启动/真实色彩仍缺；进入相机实测前提示。目前 Mac 足够，不需要用户准备 Docker、惠普电脑或相机。真正 3D LUT 支线仍保持第二十八轮未闭合状态。
