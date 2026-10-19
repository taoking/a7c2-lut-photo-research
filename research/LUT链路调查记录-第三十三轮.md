# 第三十三轮：UXC 资源与解码设置离线格式契约

日期：2026-10-19。继续 N3，按交接接入纯资源/设置保护层；不读取私人程序、备份或照片，不访问 USB、运行机内模块、编译真实 worker 或操作相机。沿用测试/公开审核后提交研究仓库的流程。

## 本轮检查项

- [x] 核验固定 v2.1 包、来源文件和资源文件名元数据。
- [x] 独立保留上游原字节、署名及许可，只接入纯资源/设置函数。
- [x] 自制 UXC 格式夹具、68 文件检查、显式槽位映射及精确逆向。
- [x] 解码设置的保存保护、CP 保留、诊断字段及严格输入边界。
- [x] 专项/完整回归、真实 CLI、公开审查、总计划和滚动交接。

## 来源与实现

固定包 SHA 仍为 `8c6c30448219f4e865e8005d2ffa789248e984d73b0f9342035f7065a1a232f7`，提交 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`。核对包内 26 个已固定文件、本地对应副本及旧基线 46 成员；没有改旧运行锁。资源清单元数据另外从完整已核验包取出，与本地副本逐字节一致，不冒称它原已在 26 文件清单中。

独立 `lutphoto/_vendor/sonycontracts` 的完整来源、许可见[来源记录](../lutphoto/_vendor/sonycontracts/README.md)。复制文件未修改：

| 文件 | 字节数 | SHA-256 |
| --- | --- | --- |
| `resources.py` | 4044 | `5a49691c8dc6875f5a55104601a981f78d28492999e5128f0fd7ab3bf61f03d1` |
| `devicesettings.py` | 3993 | `47e0f76db65366b8fb7059319410c665951239a76e2d892dfda83daa6c4247b5` |
| `resource-files.json` | 2395 | `dd7a5fa20a1da6d5015781610754215543a53fbf04e3fc7aa41d52ce11712d61` |

`lutphoto.customcontracts` 只用标准库，额外限制尺寸、规范 JSON/hex、嵌套/节点数、资源重叠和名称控制字符。命令与格式见[离线契约说明](../docs/CUSTOM-CONTRACTS.md)。UXC 来源只检查格式，不识别真实 AP/CP。历史六槽和新版槽 1/2 名称 ID 顺序不同，要求显式布局；2860 扩展后未选新标签为 ST，2866 保留未选原名；内存改名后必须逐字节恢复完整原资源。

设置输入是解码记录四态，不是原始 BK4。所选字段 RAM/保存态须已一致且结束时符合预期；未选 02cf 字段、键集、属性和四个保护 CP 单元精确保留。诊断 `02cf0b6e` 值可变，但长度/属性/存在性不变；其他运行组不比较且不能当目标。严格比较器没有旧运行计数器豁免，也没有进行备份。

上游 `devicesettings.plan` 依赖未引入的真实 AP 识别/描述符模块，入口不可用；测试明确验证没有通过模拟身份使其可用。手填 expected 只用于比较，不是设备写入规划或槽位绑定。报告不输出原资源文本、设置值或写入数据，所有真实身份/设备/物理验证标志为 false。

## 测试命令与结果

以下最终检查实际执行且退出 0：

```sh
.venv/bin/python -B -m unittest research.tests.test_customcontracts -q
.venv/bin/python -B -m unittest discover -s research/tests -q
.venv/bin/python -B -m unittest discover -s tests -q
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q
.venv/bin/python -B -m macfl23 check
.venv/bin/python -B -m research.audit_upstream_looks \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --output research/output/custom-round33/upstream-source-audit.json
```

专项 **23 项**，包含多状态/四保护 CP 单元/数据属性存在性组合；完整研究 **213 项**、Mac **39 项**、旧固定上游 **8 项**，合计 **260 项通过**。旧测试的 USB 提示来自模拟，未打开设备。首次专项的许可证署名断言和重叠负例构造有误，已修正测试；同时发现 Python 3.14 的 JSON 深层解析不一定触发递归错误，加入显式深度 32/节点数上限后通过。没有将初次失败当作通过。

实际 CLI 使用文档相同参数，输出留在忽略的 `research/output/custom-round33/`：

| 检查 | 结果 |
| --- | --- |
| `fixtures --directory …/cases` | 两套各 68 个自制格式文件及两个 JSON，退出 0 |
| `resources` stock/standalone、imported/standalone、imported/legacy-six | 三组各 68 文件及完整逆向通过，退出 0 |
| `settings --capsule …/settings.json` | 解码设置比较/保存保护通过，退出 0 |
| 三个已存在的资源报告 | 均拒绝，退出 1，未覆盖 |
| 所有输入的运行前后完整 SHA | 138 个文件原字节不变 |
| 资源/设置 CLI 的 `-S` 环境 | 不加载 site packages；专项还确认不导入 NumPy/USB/macfl23/PMCA/device_layout |
| 上游源码审计 | 包、26 个审阅成员和旧 46 成员身份通过 |

公开检查覆盖 UTF-8/AST/JSON、本地链接及锚点、隐私/资产路径、显式改动清单、空白、来源文件哈希与旧计划归档/运行锁完整 SHA。原安装器、原测试、启动器和运行依赖相对研究基线仍无差异。生成资源/报告、环境和原始日志均不提交。

沿用授权只提交推送 `lut-photo/main`，不推 origin；提交前列出实际测试命令和结果，提交/远端/CI 结果在最终报告给出并由 Git 历史复核。

## 遗留与交接

N3 仍部分完成。本轮解决纯资源/解码设置的格式与保留契约，未解决真实来源身份、描述符绑定、完整 BK4 解析/备份证明、真实 worker 构建/ABI、持久化意图/恢复日志、共享单会话锁和 Mac USB 生命周期。

下一轮先做持久化意图/结果、共享锁和中断后只读分类的离线原型，复用合成来源和本轮格式契约设计故障负例；不把现有合成顺序当成真实设备顺序，不重放未知结果。随后再审真实布局/worker 来源与 ABI，在完整资产审阅前拒绝真实规划。Docker/Windows 备用环境仍无实际需要，Keystone/外部 Windows 断言未解决。

N4 相机写入/恢复、冷启动及真实色彩继续后置，进入前提示。目前无需连接相机或提供惠普电脑；新 Custom 的两份独立物理介质完整备份证据仍缺。真正 3D LUT 支线保持第二十八轮未闭合状态，不自动恢复地址追踪。
