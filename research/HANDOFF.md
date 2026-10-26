# LUT 照片开发：当前交接

更新：2026-10-26，第七十八轮。先读根AGENTS、README、[四列计划](../plan.md)、本文件及[第78轮记录](LUT链路调查记录-第七十八轮.md)。历史见[轮次索引](ROUNDS.md)。本轮只有离线开发，没有新USB或管理员操作。

## 当前状态

D1–D3离线冻结；R1/R2及R3有限入口已实现。第78轮普通侧首次START限定PIPE兼容、持续供电声明及结果`/2`离线完成；完整回归1136项通过。**新代码尚未实测，尚无本项目采集正例，D4仍0真实材料。** 完整入口仍先查MSC身份；D5/D6及真正3D LUT支线后置。

第77轮实际失败：USB型号已读，NORMAL_START边界USBError(-9/32)，44事件/0快照，普通/服务认证未完成、协议结果UNKNOWN；本地句柄/作业/租约/信号收尾确认。本人当时确认终端结束、画面正常、7号存取灯灭，最后“仍保持USB连接”；没有之后的断开/菜单/冷启动/拍摄确认。本轮没有再发设备命令，不把旧现场状态当作当前自动测量。

本人已要求后续脚本不确认/输入电量，并承诺持续高电量和USB供电。此偏好已实现为有限入口的`--maintained-power`，后续准备直接使用该既有约定，不再询问电量、不填98/100等虚构百分比。它是用户声明，回执百分比null、自动测量false。密码仍只在本机终端输入；没有免密sudo或SIP修改。

## 下一动作：准备新的/2单次验证

1. 阅读[有限入口说明](../docs/CAPTURE-SERVICE-PROBE.md)和本轮实现/测试。停止继续扩展通用模拟框架；下一成果是一份可审阅的新单次操作准备。
2. 新建本轮之后的独立私有准备、仓库外新作业和外部回执；冻结当前源码、依赖声明和新摘要读取器。旧第77轮schema为/1，其操作文件与读者全部保留，不能改摘要后复用，不能改旧schema追认。
3. 一次调用`captureprobe.main`，传`--maintained-power`，没有电量输入/确认；不得串接完整采集、重试、复位/清端点、救援或旧prepare/diagnose。沿用私有所有者/新目录及回执排他创建/结果日志noclobber、导入前与摘要子进程前来源核对，管理员密码仅在终端。
4. 配套`/2`摘要需区分START控制结果、完整普通认证、服务认证、快照、停止确认及普通USB重现；特别保留`normal_start.boundary`和错误`start_boundary`。摘要成功不能覆盖采集失败，未知即停；不把摘要称为图检查器或硬件证明。先用自制成功/失败记录验证，不读取私人材料作测试。
5. 准备通过后再安排一次设备验证。既有只读范围有效，但旧失败作业不能重跑；相机连接/MSC/固件变化仍要依据实际反馈，不能因旧“仍连接”自动开始。本轮没有新设备脚本，不提供旧脚本执行指令。
6. 若成功，先审阅服务优先接入完整采集及其供电声明，再安排R4全材料/有界复读；仍要求完整程序指纹。若限定候选在同阶段再失败且无新证据，则转Windows原生只读对照评估或后置Mac，不连续试错。

## 关键实现与判定

- [captureprobe](../lutphoto/captureprobe.py)：`_ProbePort.normal_start`只捕获实际SDK控制调用的精确USBError、整数backend -9及errno32，仅普通侧首次START。描述符前后检查在捕获范围之外；缺失errno/其他类型或码、服务START、STOP、读写异常仍拒绝。
- PIPE只是暂定：`normal_start.control_status=PIPE`及`NORMAL_START_PIPE`事件，没有`ACK/NORMAL_START`。仅三轮挑战/证明及最终认证通过才确认普通认证并结束暂定状态。没有重置unknown或再次START；取消、期限、日志失败仍停止。
- `normal_start.boundary`为PRECHECK/CONTROL/POSTCHECK/COMPLETE；`control_status`为NOT_ATTEMPTED/UNKNOWN/ACK/PIPE。错误项`start_boundary`仅在NORMAL_START填写。CONTROL定位到SDK调用，不证明USB内部状态阶段；旧`last_host_operation`不是精准错误位置。
- `_Power`记录百分比模式或持续供电模式，互斥；当前私有结果及stdout为`a7c2-service-probe-result/2`、`a7c2-service-probe-cli-result/2`。新增`declared.power`、`normal_start`和错误边界，旧/1私有读取器不适用新版。
- [captureexecution](../lutphoto/captureexecution.py)仅抽取来源/环境装配，[capturemac](../lutphoto/capturemac.py)仅抽取宿主字段初始化；完整采集原版本/电量门槛、认证、完整回执/3、检查器不改。未来接完整入口时显式迁移供电声明，不能偷偷填电量绕过旧契约。

固定YuuLuo源码是协议行为参考，头部目标为1.02，不是本项目2.01实测证据；本轮处理比该源码更窄。其GPL-3.0-only声明和贡献见致谢，本轮未导入或复制其源码/注释/模块。已有PMCA认证/许可及固定锁保留。

## 验证和证据位置

Python3.14.6，仅自制SDK/数据。本轮日志在忽略目录`research/output/custom-round78/`。

- `.venv/bin/python -B -m unittest research.tests.test_captureprobe research.tests.test_capturecamera research.tests.test_captureauth research.tests.test_captureexecution`：119项通过。
- `.venv/bin/python -B -m unittest discover -s research/tests -p test_capturemac.py -v`：51项通过。最初模块路径调用因其既有同目录导入失败，改用discover后通过，没有修改该模块。
- `.venv/bin/python -B -m unittest discover -s research/tests -v`：1089项通过，82.815秒。
- `.venv/bin/python -B -m unittest discover -s tests -v`：39项通过；`.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v`：8项通过；全套1136项。
- `.venv/bin/python -B -m macfl23 check`：来源/资产通过；`custom-round74/check-legacy-receipts.py`：3类自制旧记录不变。
- `.venv/bin/python -S -B -m lutphoto.captureprobe --help`：互斥参数正确、无SDK/USB。
- `.venv/bin/python -B research/output/custom-round78/check-round.py`及`git diff --check`：检查通过：16个公开文件、10份文档/243个本地链接、17份固定来源及6份第77轮私人文件未改；旧冻结清单有6个代码/测试路径变化，不能复用旧准备。

新增14项probe测试，总31项，涵盖精确错误对、成功不伪ACK、7次认证回复分别拒绝、前后描述符/读写/服务/STOP异常、取消/期限/日志失败、二次START和供电声明。没有把这些测试称为实机成功，也没有重跑旧设备脚本。

## 私人记录及发布

第77轮定位文件`research/output/custom-round77/location.private.json`记录真实失败；`probe-result.private.log`有CLI退出1、摘要退出0，`existing-details-terminal.private.log`有仅回执字段检查。`device_attempt_executed=true`，原三操作文件和结果字节均保持。第67/69/71/77轮禁止重跑；第72轮暂停。不要再运行旧生成器或旧冻结测试来“更新”现场。

本轮开工HEAD为`c0fbd5f352d5bad14b9686add7877c48996d6a72`，工作区干净；上一轮代码`5a8ed7f`的CI通过不代表本轮CI/真机。按已有授权发布到`lut-photo/main`（taoking/a7c2-lut-photo-research），不推origin；本轮提交/远端与CI状态以Git及最终回执为准。私人脚本/材料/日志不上传。

每轮结束更新本文件、轮次记录和四列计划，区分代码完成、新准备完成、实际派发与设备验收。当前下一轮是“准备/2单次验证”，不能把上一轮已用准备当作待运行。
