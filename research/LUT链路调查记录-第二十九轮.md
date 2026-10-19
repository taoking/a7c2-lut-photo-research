# LUT 开发调整：上游 v2.1 审计与双路线计划

日期：2026-10-19。状态：本轮 N1 审计已完成，未通过/未执行检查已列明。接续[第二十八轮](LUT链路调查记录-第二十八轮.md)。本轮按用户最新要求调整方向，不继续自动延伸固件地址追踪。

## 范围与进度

核验 QAQLeonard v2.1 发布、源码及验证边界，比较原生 Creative Look 拟合与现有 M2/M3 研究，输出可复用模块和独立接入计划。只在电脑下载、审阅和离线验证；不操作 USB、相机，不修改旧安装器锁或放宽程序检查。

- [x] 阅读规则、README、总计划和交接，保留第二十七/二十八轮已有改动。
- [x] 固定 v2.1 发布、提交和审计材料指纹。
- [x] 审阅拟合、色彩模型、部署、设置保护、迁移及恢复边界。
- [x] 输出能力对照、复用清单及 N1–N4 验收条件。
- [x] 运行适用离线验证，记录失败/跳过/未执行范围，更新总计划和短交接。

## 审计结果

完整对照、模块清单、版本迁移/恢复表及色彩验收条件见[v2.1 审计](../docs/UPSTREAM-V2.1-AUDIT.md)，不在轮次日志重复展开。新增 [upstream-looktool.lock.json](upstream-looktool.lock.json) 和 [audit_upstream_looks.py](audit_upstream_looks.py)，只审计公开源码，不替换运行依赖。

通过 GitHub Release/commit/tree API 确认 v2.1 完整提交 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`，下载 331,887 字节源码包并核对完整 SHA-256；26 个所选源码文件与该提交的 Git blob 身份相同。没有下载 DCP 或 152 MB 照片对比附件。旧锁的 46 个来源文件另行逐个核对，再与新包比较；报告保存在忽略目录 `research/output/upstream-v2.1-audit-v1.json`。

结论为优先复用原生拟合路线，N1 审计完成；N2/N3 尚未实现。本地 M2/M3 的控制/缓冲证据不因此升级为照片路径证明。上游单机报告与本机真机验证分别标记；Mac/原厂首次导入/实机恢复/真实多场景精度均未放行。第二十七/二十八轮记录及脚本保留。

## 实际验证

### 本项目回归与审计工具

以下命令在仓库根目录实际运行：

- `.venv/bin/python -B -m unittest discover -s research/tests -v`：125 项通过，退出码 0。
- `.venv/bin/python -B -m unittest discover -s tests -v`：39 项通过，退出码 0。
- `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v`：8 项通过，退出码 0。共 172 项，无相机操作。
- `.venv/bin/python -B -m macfl23 check`：固定源码/资产完整，退出码 0，未连接相机。
- `.venv/bin/python -B -m research.audit_upstream_looks --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/upstream-v2.1-audit-v1.json`：退出码 0，首次保存报告。复跑使用不同输出名。
- `.venv/bin/python -B -`（内联实际 CLI 审核）：stdout/临时报告/保存报告逐字节一致；26 个固定文件、46 个旧来源及 15/24/3/4 差异分类通过。同尺寸损坏 ZIP、篡改旧 `app.py` 均在生成输出前拒绝；拒绝覆盖且旧输出不变，help 通过；源码包、旧运行锁和保存报告 SHA-256 不变，退出码 0。

### 上游测试的实际范围

建立独立环境 `research/materials/upstream-v2.1-audit/env`，不更改现有 `.venv`。Python 3.14.6；NumPy 2.5.4、SciPy 1.18.1、Capstone 5.0.6、pyelftools 0.32、Unicorn 2.1.4。设备 Python 依赖按上游 `src/fl23/requirements.txt` 安装，但没有安装 Zig、打开 USB 或编译本机身安装载荷。所有子进程显式设置 `A7C2_RESEARCH_FIXTURES` 为空，不读取私人素材索引。

实际用 `python3 -` 调度隔离解释器执行：

- 工作目录为上游 `src/looks/tests`，`PYTHONPATH` 指向上游 `src/looks`：`python -B -m unittest test_toolkit test_cli test_six test_settings_scope test_worker test_usbidentity test_usbservice test_device_components.ResourceTests test_device_components.NativeInvocationTests test_device_components.NameReportTests test_device_components.LockTests -v`。发现 57 项：55 通过、2 私人完整来源测试跳过，退出码 0。这是所选测试，不是完整上游套件。
- 工作目录为上游源码根：`python -B -m unittest discover -s src/fl23/tests -v`：8 项通过，退出码 0。
- 同目录：`python -B -m unittest discover -s dev/usb/tests -v`：最终 37 项，28 通过、2 失败、7 Windows 测试跳过，退出码 1。`test_dependency_setup_failure_cannot_start_camera` 和 `test_incomplete_environment_is_preserved` 期待 Windows 启动环境错误，但 Mac 先触发非 Windows 平台拒绝。未修改上游测试、伪造平台或把失败写成通过。
- 首次主机检查另有 3 个缺 USB Python 包的导入错误，按上游依赖补齐后消失；剩余上述 2 个平台断言失败。Keystone 0.9.2 首先因 Python 3.14 缺 `distutils` 导入失败，安装 setuptools 84.0.0 后仍无法加载动态库。汇编相关测试和需要私人完整程序的集成未放行，不宣称本机原生补丁验证通过。

### 文档与发布边界检查

- `.venv/bin/python -B -`（内联公开文件/文档审核）：130 个候选文本文件的所查私人路径、令牌、私钥及二进制检查通过；新脚本 AST、审计锁、50 个 Markdown 的 287 个本地链接/锚点、11 个待提交 Markdown 的空白/换行检查通过。总计划为 16 行四列表格，交接为 35 行，旧计划归档 SHA-256 不变。
- `git diff --check` 与 `git diff --exit-code 5babef40bba986efdd0573380c0ff9f8a027495c -- macfl23 upstream.lock.json requirements.txt a7c2-mac setup.sh tests`：退出码 0。源码包、审计环境和报告的 `git check-ignore -q` 通过，没有将其纳入公开文件。

新审计代码没有设备接入或数学内核变化，真实来源和异常输入通过实际 CLI 验证；不新增镜像静态清单的单元测试。没有修改旧源码/资产校验、原安装器或上游测试，没有操作相机。

## 下一步

下一轮实施 N2：先接入纯离线 `native/color/calibration/references/project` 所需能力和许可，保留现有有界 CUBE/原图保护；建立 ST/桥接契约、原生表往返及参考预测，再增加整体/区域误差和缺样本标志。没有真实样张就明确报告未验证，不把共享模型或合成评分当本机标定。

N3 的独立 Mac 状态迁移、工具链和恢复故障检查后置，N4 更后置；新流程写前需要两份独立介质备份，目录分离不能替代介质证据，备份不保证救砖。目前无需连接相机或准备备份。原 M2–M4 保留至第二十八轮检查点，当前不自动延伸；公开仓库截至第二十六轮，第二十七至二十九轮尚未提交或推送。
