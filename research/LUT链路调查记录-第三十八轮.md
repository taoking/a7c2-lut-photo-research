# 第三十八轮：描述符与 RAM/保存设置只读绑定

日期：2026-10-20。继续 N3，仅固定来源和自制程序/BK4 夹具；不读取私人程序、备份、照片，不接触 USB，不编译/执行目标模块。

## 本轮检查项

- [x] 复核上一轮 CI，保留待完成结果，不把排队视为通过。
- [x] 复用完整 AP/CP 身份，按真实描述符规则派生九字段及八个 ST 引用。
- [x] 只读绑定显式 RAM/保存快照，检查长度/属性/未保存项/保护范围/reset 布局。
- [x] 自制正负例、实际 CLI 拒绝、完整离线回归，提交前审查公开内容。
- [x] 维护四列计划/滚动交接，审核后提交推送研究仓库，结果以 Git/远端与 CI 为准。

## 交付与来源

新增 `lutphoto.settingsbinding` 和[使用说明](../docs/SETTINGS-BINDING.md)。在第三十七轮内容身份入口中抽出不可变 `_Bindings/_Field`，行校验与原报告行为不变；只有完整 AP/CP 配对及描述符通过后，才能打开用户显式提供的 RAM/保存 BK4。所选每槽九字段及八个 ST 引用均派生自已识别 AP 行，没有用户手填 `expected`、自填指纹/策略或机身 token 的入口。

沿用[14 成员固定来源](upstream-worker.lock.json)，仍为 QAQLeonard v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`，完整包 SHA-256 `8c6c30448219f4e865e8005d2ffa789248e984d73b0f9342035f7065a1a232f7`；另保留 ma1co BK4 格式署名/MIT 和既有纯比较函数来源。本轮不执行归档 Python，不调用 vendored `devicesettings.plan`，不修改旧运行锁/指纹/偏移或原安装器。

## 检查范围与证据边界

所选基底 1 字节、调整 4 字节，两快照均须存在且不带 `attr & 3`，RAM/保存值和属性一致；ST 引用均为 4 字节，只读属性允许，因为引用不是写目标。AP 02cf 除诊断值外全部键/值/属性双向比较，包含未选槽、ST 和保存态独有键；四个 CP 保护单元必须存在且相等。

投影范围全部记录另核对键集、attr、max_size、当前长度和 reset 数据；02cf0b6e 当前易变值例外，布局/reset 仍保留，其他运行组不比较。快照角色分别显式断言 AP/CP 索引，不猜顺序。受限格式/32 MiB/只读普通文件/no-follow 等规则复用 BK4，解码投影每芯片≤4096 条。

只统计当前所选字段与 ST 的匹配数量（基底比 0，调整比引用），不生成目标字典、after 快照或写计划。原 recipe 尚未等于 ST 可以通过本地结构检查，不能据此说已导入或设备预检查已通过。

`local_program_content_verified` 与 `provided_snapshot_structure_and_values_checked` 只针对提供的本地内容。新鲜度、同一捕获来源、真实机身/角色、外层完整备份、加载器/机内执行、物理、live 描述符和写计划均 false。两个相同文件也不证明新鲜；嵌套行层 `setting_values_verified` 保持 false。报告含完整输入 SHA，标私人，仅输出数量/槽位/状态，无属性键/值、程序字节或写目标。

本轮只用自制程序与 BK4 正例，没有真实完整程序或备份兼容正例；没有访问 USB、相机、sudo/诊断、私人照片，没有编译 C 或加载目标。真实材料后续须本人明确提供必要本地路径及捕获来源，不能自动搜索已有工作目录或运行相机 prepare 来补齐。

## 测试命令与结果

| 实际命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_settingsbinding research.tests.test_programidentity -q` | 新绑定 23 + 原身份 23，共 46 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -q` | 研究 322 项通过，含新专项 |
| `.venv/bin/python -B -m unittest discover -s tests -q` | Mac 39 项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q` | 旧上游 8 项通过，完整合计 369 项 |
| `.venv/bin/python -B -m macfl23 check` | 旧固定源码/资产检查通过，无设备操作 |
| `.venv/bin/python -S -B -m lutphoto.workercontracts --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round38/worker-source-policy.json` | 14 成员/来源策略通过，未编译 C |
| `.venv/bin/python -B -m research.audit_upstream_looks --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round38/upstream-source-audit.json` | 包、26 源与旧 46 成员通过 |

专项使用第三十七轮 tiny 程序夹具和本轮自制 BK4，正例未模拟身份判断器，仅替换内部测试来源策略；CLI 没有这种参数。覆盖六槽 54+8 字段、描述符键重映射、缺项/长度/保护属性/键别名、未保存项、四个保护 CP、诊断值例外、reset/max 布局、显式分开角色、同文件不能证明新鲜、私人输出与源保护。只读 ST 引用属性与所选写保护位分开验证。

实际 `-S -B -m lutphoto.settingsbinding` CLI 以自制全尺寸全零 AP/CP 与两份自制 BK4 验证未知程序拒绝（退出 1，无报告）；替换为不存在快照路径仍先报身份 ValueError。四个源文件及固定归档作输出共五次拒绝，坏归档拒绝，四输入完整 SHA 及归档 SHA 不变，临时文件删除。真实 CLI 没有程序/快照正例；patched 测试成功不称为真实 CLI 已识别机身。报告在忽略的 `research/output/custom-round38/`，不公开上传。

公开审查覆盖文本/AST/JSON、Markdown 链接、私人路径/二进制、旧锁/归档/受保护路径及精确文件清单。总计划继续四列，交接滚动覆盖；本次吸收上一条“记录下一轮”保存的交接，第三十八轮由待开始转为本轮完成范围。

## CI 与后续交接

起点为已推送的 `22947393c924f0c0c970aa9b257e8e31c39b1f38`；[第三十七轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39281032240)本轮开始时查询仍 queued，提交前复核已 completed/success。CI 排队未用来放宽任何校验；本地完整测试已执行。本轮审核后仅正常推送 `lut-photo/main`，不推 origin，推送及新 CI 状态以最终报告为准。

N3 仍部分完成。下一轮连接 N2 原生表/槽位/名称资产与当前只读输入指纹，建立本地材料清单和保留/逆向检查需求，不将哈希清单当机身来源认证；在真实程序/BK4 正例、完整事务来源/目标/逆向充分前不启用 worker。若真需要私人材料，一次说明本人本地 AP/CP、RAM/保存快照及捕获记录需求，不自动访问。USB/全局相机锁、设备恢复、独立介质及 Sony 加载行为/真实 ST 色彩仍缺；N4 实测前提示，目前无需相机、Docker 或惠普电脑协助。M2–M4 继续保留，不自动推进。
