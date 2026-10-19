# 第三十七轮：完整程序身份与描述符只读入口

日期：2026-10-19。继续 N3，仅固定源码与自制程序夹具；不搜索/读取私人程序、备份或照片，不接触 USB，不编译或执行目标模块。

## 本轮检查项

- [x] 固定来源策略接入：完整配对、standalone 全文件重建与历史六槽分流。
- [x] 六表 header/FNV/有符号 7 位范围检查，拒绝混合来源与额外改动。
- [x] 身份通过后只读九字段描述符，保持机身/设置/写入门禁关闭。
- [x] 自制正负例、实际 CLI、完整离线回归，提交前审查公开内容。
- [x] 更新四列总计划与滚动交接，审核后仅提交推送研究仓库；结果以 Git/远端及 CI 为准。

## 交付与固定来源

新增 `lutphoto.programidentity` 和[使用/材料说明](../docs/PROGRAM-IDENTITY.md)。只复用[第三十五轮的 14 成员清单](upstream-worker.lock.json)核验归档、元数据和规则，不增加可覆盖的来源文件或命令行指纹参数。来源仍 QAQLeonard v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`，包 SHA-256 `8c6c30448219f4e865e8005d2ffa789248e984d73b0f9342035f7065a1a232f7`。保留作者/MIT，归档 Python 不导入或执行；完整 AP 模板/恢复窗口仅在内存读取，不公开复制，不写目标程序。

原厂/FL23 完整 AP/CP 必须为相同 kind 的固定大小/SHA 配对。standalone 先虚拟还原窗口，对整个 AP 哈希；再按非零 1–63 mask 核对全部恢复窗口重建结果，包含未选标签。窗口外已由完整还原 SHA 覆盖，等价于完整重建比较；流式哈希避免复制约 100 MB 程序。历史六槽固定 AP 与独立归一化 CP 身份单独识别，退休/未知/混合方案不放行。

CP 归一化只虚拟清零 `[0x8008,0x9c9a)`，不修改魔数/版本或其他代码；六张 1215 字节表逐张核对 header、FNV-1a 和 signed 7 位范围。可变表仍绑定本次完整 CP SHA；本入口没有前向/逆向事务、worker 或任何设备操作。

## 描述符与只读边界

完整 AP/CP 内容身份通过后才读取 AP 中描述符。所选每槽九字段，加八个共享 ST 引用，最多 54+8 行；检查边界、属性身份、02cf 组、基底/调整类型和布局，并对 ST 引用增加同样调整检查。禁止诊断字段、所选键重复、ST 引用重复和两者别名。只输出槽位/行计数，不输出键、原始行或设置值；没有调用上游 `devicesettings.plan`。

新增 `requirements` 只核验包并报告所需材料，不找或打开程序文件。`inspect` 只读用户明确给出的 AP/CP 路径，固定大小、普通文件、no-follow、读取前后元数据/长度核对，拒绝已有输出，源文件原字节保留。输出含完整来源 SHA，均标为私人报告，不上传。

`local_program_content_verified` 仅指本地内容符合固定规则。机身/芯片关联、同一捕获来源、当前实际程序/设置、机内加载/执行、描述符写计划、物理验证仍 false；文件行通过不是 live descriptor/RAM/保存值证据。没有真实程序正例，真实兼容性仍未证。未来材料需用户提供本人完整 AP（99,960,744 字节）/CP（18,090,880 字节）的明确本地路径及同一捕获来源记录，不自动搜索私人备份，也不为本入口运行相机 prepare/diagnose。

## 测试命令与结果

| 实际命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_programidentity -q` | 新专项 23 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -q` | 研究 299 项通过，含新专项 |
| `.venv/bin/python -B -m unittest discover -s tests -q` | Mac 39 项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q` | 旧上游 8 项通过；完整合计 346 项 |
| `.venv/bin/python -B -m macfl23 check` | 旧固定源码/资产核验通过，无设备操作 |
| `.venv/bin/python -B -m research.audit_upstream_looks --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round37/upstream-source-audit.json` | 包、26 源及旧 46 成员通过 |
| `.venv/bin/python -S -B -m lutphoto.workercontracts --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round37/worker-source-policy.json` | 14 成员/来源策略通过，未编译 C |
| `.venv/bin/python -S -B -m lutphoto.programidentity requirements --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round37/material-requirements.json` | 实际 CLI 成功；无程序输入读取 |

专项用两个 16 KiB 自制 AP、8 KiB 自制 CP，独立 bytearray 全量参考重建覆盖两种来源各 63 masks；覆盖零 mask/未知模板、恢复窗口外改动、未选标签变化、CP 范围外改动、六表校验和/全部 256 byte 值与既有 native decode 对照、描述符身份/键别名、读取变化和输出保护。测试小策略只在内部夹具注入，CLI 不支持。

实际 `-S -B -m lutphoto.programidentity` CLI 另以固定大小的自制全零 AP/CP 验证完整身份拒绝（退出 1、无报告），完整输入 SHA 不变；临时文件随目录删除。requirements 已有输出、源路径作输出、坏归档均拒绝。原归档 SHA 保留；`-S` 无 USB/NumPy/相机或归档模块导入。实际 CLI 没有真实内容正例；不能把 patched 单测成功当真实 CLI 已识别机身。报告在忽略的 `research/output/custom-round37/`，不含公开分发的程序或派生目标。

提交前公开检查文本/AST/JSON、Markdown 链接、私人路径/二进制、旧锁/归档/受保护路径和精确文件清单；CI 运行完整离线测试，没有可选私有包或相机。推送后结果以最终 Git/CI 为准。

## 遗留与交接

N3 部分完成。下一轮连接纯只读“身份/描述符→新鲜 RAM/保存设置”的范围、长度、属性与 ST 引用检查，明确角色/来源仍未认证，不产写计划或 worker。真实程序正例/完整事务来源、目标/逆向及资产绑定仍缺；材料需求已列清，在后续真正需要时只请求必要本地路径。BK4 真实兼容/机身关联、全局相机锁/USB、设备恢复及双独立介质仍缺，Sony 加载行为与真实 ST/色彩留 N4，进入前提示；当前无需相机、Docker 或惠普电脑协助。

前轮 `310e9036d1c8f47bcc00db00cd62016a61adcbfc`，[CI 已通过](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39277337677)。本轮仅正常推送 `lut-photo/main`，不推 origin；旧安装器及默认单份备份不变。M2–M4 不自动推进，[总计划](../plan.md)保持四列，[交接](HANDOFF.md)滚动覆盖，历史轮次不改。
