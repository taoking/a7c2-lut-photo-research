# 第三十九轮：原生表/名称资源与只读输入清单

日期：2026-10-20。继续 N3，固定源码和自制程序、BK4、N2 候选及 UXC；不打开私人程序/备份/照片，不接触 USB 或执行目标模块。

## 本轮检查项

- [x] 复核第三十八轮 CI 与固定来源。
- [x] 槽位/N2 候选/表/名称的严格选择格式与指纹核验。
- [x] 标签布局由已识别程序导出，连接 68 资源内存改名/保留/完整逆向。
- [x] 私人输入清单绑定与部署/来源证明边界，实际 CLI/自制正负例及完整离线回归。
- [x] 维护四列计划与滚动交接，公开审查后提交推送；Git/远端与 CI 结果以最终报告为准。

## 交付与来源

新增 `lutphoto.importmaterials` 和[使用说明](../docs/IMPORT-MATERIALS.md)。只接受严格选择文件（1–6 规范槽键、相对候选目录、1–63 UTF-8 字节名称），由选择槽位调用上一轮完整 AP/CP/描述符/BK4 检查，不接受导出的旧报告作凭证。程序身份通过后由实际识别结果导出 standalone/legacy-six 标签顺序，没有 `--layout` 或自填程序指纹覆盖入口。

来源沿用 QAQLeonard v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`，[14 成员清单](upstream-worker.lock.json)与旧 26/46 成员重新核验，完整包 SHA-256 `8c6c30448219f4e865e8005d2ffa789248e984d73b0f9342035f7065a1a232f7`。保留 ma1co BK4/许可与既有 N2/资源来源，不导入归档 Python、设备 planner，不改变旧运行锁/程序指纹/偏移或 Mac 安装器。

## 材料检查与清单含义

候选目录逐层拒绝绝对/上溯/链接路径，恰好两个固定文件。核对 N2 schema/version/提交、机外候选标志、表固定描述符、1215 字节/完整 SHA/signed −64…63，以及三项来源 SHA 语法。要求已有合成 RGB MAE/Delta E76 P95 声明与正有限阈值及 passed:true 一致；不读取元数据中的项目/CUBE/模型路径，不重算标定/桥接/拟合/照片或冻结验收，可选锁 SHA 也只是声明。

JSON 单次读取的同一批字节用于解析和指纹；提取既有严格解码器供复用，并补拒绝 `1e999` 溢出浮点，保留大小/深度/节点/重复键等约束。相同候选目录在多槽选择中复用一次读取结果，避免同次清单重复观察不同版本。

68 资源沿用完整格式/数量/保留/内存逆向契约，legacy-six 只接受 2866，standalone 接受一致的 2860/2866；后者不是已证明同一捕获或安装阶段。报告记录全部来源/内存目标/还原 SHA，无资源 payload。源程序/快照、完整选择文件、每槽候选/表/名称及明确角色断言和资源结果共同形成规范指纹清单。

`materials_sha256` 仅绑定本次读取内容，不是签名、来源认证或后续写入许可。私人报告不含路径、名称、设置键/值或程序/表字节；仍含完整指纹，不上传。新鲜同机身来源、资源实际来源、独立介质、完整 AP/CP 及设置事务/逆向、机身 worker/部署/物理/色彩全部未验证；资源数学逆向不能替代程序逆向或设备恢复。本轮没有真实材料正例、相机/USB/sudo/诊断、C 构建或目标执行。

## 测试命令与结果

| 实际命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_importmaterials -q` | 新专项 22 项通过；使用实际 N2 fit 生成的未修改候选文件与 tiny 程序/BK4/UXC 夹具 |
| `.venv/bin/python -B -m unittest discover -s research/tests -q` | 研究 344 项通过，含新专项 |
| `.venv/bin/python -B -m unittest discover -s tests -q` | Mac 39 项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q` | 旧上游 8 项通过，完整合计 391 项 |
| `.venv/bin/python -B -m macfl23 check` | 旧固定源码/资产检查通过，无设备操作 |
| `.venv/bin/python -B -m lutphoto.nativefit fixtures --directory research/output/custom-round39/demo` | 实际 CLI 生成自制 CUBE/模型/图表，无私人照片 |
| `.venv/bin/python -B -m lutphoto.nativefit fit --project research/output/custom-round39/demo/project.json --directory research/output/custom-round39/n2-candidate` | 实际 CLI 输出两文件候选，新标准库读取器通过；没有重算或证明相机精度 |
| `.venv/bin/python -S -B -m lutphoto.workercontracts --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round39/worker-source-policy.json` | 14 成员/来源策略通过，未编译 C |
| `.venv/bin/python -B -m research.audit_upstream_looks --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round39/upstream-source-audit.json` | 包、26 源与旧 46 成员通过 |

专项覆盖实际 N2 输出消费、选择/名字/路径/链接、坏长度/SHA/值域、声明阈值/非有限与超大整数、候选私有路径不跟随、同候选复用、程序派生 legacy 首两标签互换、全部资源精确逆向、资源遗漏/混合/损坏、指纹复现、私人输出和无设备/NumPy 导入。完整联合正例只在内部测试注入 tiny 程序来源策略，没有替换身份判断器或在 CLI 暴露放宽参数；不把这种正例称为真实机身验证。

实际 `-S -B -m lutphoto.importmaterials` CLI 以全尺寸自制全零 AP/CP、两份自制 BK4、N2 CLI 候选及 68 自制 UXC 验证未知程序拒绝（1，无报告）。九次源文件/归档作输出和坏归档拒绝；75 个自制源文件及固定归档完整 SHA 不变，临时程序/快照/资源删除。N2 生成物及报告仅留忽略的 `research/output/custom-round39/`；真实材料的完整 CLI 正例未测。

公开检查覆盖文本/AST/JSON、Markdown 链接、私人路径/二进制、旧锁/归档/受保护路径和精确文件清单。总计划继续四列、交接滚动覆盖，历史轮次不改。

## 下一轮真实正例检查点

起点提交 `d73ec3a1b33bf1d0b377b5d8554fb7de56164f32` 已推送，[第三十八轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39284863413)本轮复核 completed/success。本轮审核后仅正常推送 `lut-photo/main`，不推 origin，新 CI 以最终报告为准。

下一轮优先本人已有材料的纯只读正例：一次说明需要现有工作/备份目录本地路径、捕获来源和当前原厂/FL23 状态，以及可选的既有 68 资源目录。材料尚缺时保留此检查点，不自行搜盘，不为补齐资产启动 prepare/diagnose，不继续用合成正例宣称真实身份或恢复已通过。若只有完整程序/快照，先验证身份与设置绑定，资源缺口单列；真实材料、路径和报告不得公开提交。

N3 仍缺新鲜同机身来源、完整来源/目标/逆向事务、worker、USB/全局锁、设备恢复与独立介质；Sony 加载器及真实 ST/色彩/冷启动留受控 N4，进入前提示。当前不需要相机、Docker 或惠普电脑协助。M2–M4 支线继续保留，不自动推进。
