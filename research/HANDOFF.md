# LUT 照片开发：当前交接

更新：2026-10-26，第七十九轮。先读根AGENTS、README、[四列计划](../plan.md)、本文件及[第79轮记录](LUT链路调查记录-第七十九轮.md)。历史见[轮次索引](ROUNDS.md)，生产代码边界见[第78轮](LUT链路调查记录-第七十八轮.md)。

## 当前状态

D1–D3离线冻结；R1/R2及R3有限入口已实现。第79轮新版单次准备及/2摘要已完成，冻结172个文件，21项准备检查和31项probe专项通过。**未派发设备命令，新版尚未实测，D4仍0真实材料。** 不继续扩展通用模拟框架；下一动作是根据现场信息执行这份新准备。

生产代码基线`39c9b168a2f31189c7e2e490783557e244bb518d`；第78轮1136项回归及[CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/40277028386)通过。本轮未改生产代码/公开测试/依赖/固定锁，不把以前全套测试记为本轮执行。有限入口详见[使用范围与契约](../docs/CAPTURE-SERVICE-PROBE.md)。

第77轮实际失败保留：普通USB型号已读，NORMAL_START处USBError(-9/32)，44事件/0快照、认证未完成、结果UNKNOWN；本地四项收尾确认。本人当时确认终端结束、画面正常、7号存取灯灭，最后“仍保持USB连接”；此后没有断开/菜单/冷启动/拍摄确认，不能当作当前自动观测。

本人已要求后续脚本不确认/输入电量，并承诺持续高电量和USB供电。新准备直接使用`--maintained-power`，不再询问电量、不填98/100等虚构数字。它是用户声明，回执百分比null、自动测量false。密码仍仅在本机终端输入，没有免密sudo或SIP修改。

## 下一动作：当前现场信息后单次验证

已向本人询问当前是否直连Mac、MSC、仍为官方原厂2.01；截至本次交接尚无新反馈。若后续收到回复，以实际消息更新此段，不重复已回答的条件。若暂不连接，则保留准备并后置设备任务。

1. 私有定位文件：`research/output/custom-round79/location.private.json`。其中`device_attempt_executed=false`，列出新的operator、reader、command、log、仓库外随机作业/回执路径及3文件SHA-256。本轮没有创建真实采集作业，实际父目录/新路径/管理员上下文在未来运行时校验。
2. 核对这3份文件及operator内172项`EXPECTED`，核对日志尚不存在。按需重新运行本轮离线准备检查；不要运行生成器覆盖/重建。若源码变化，停止并审阅差异，不能直接更新哈希放行。
3. 只有实际连接信息满足时，在本人终端启动该command一次，管理员密码仅在终端。它单次调用`captureprobe.main`并用`--maintained-power`；只验证服务入口/一份RAM快照，不自动接完整74材料、写入、重试、复位、清端点、旧prepare/diagnose。
4. 派发时立即记录实际派发状态，保留结果日志；`PROBE_CLI_EXIT_CODE`和`RECEIPT_SUMMARY_EXIT_CODE`分别判断。摘要是字段读取，退出0不能把采集失败升级。结果不明即停，不能重跑脚本或强制重启。
5. 核对START控制结果/边界、普通认证、服务认证、快照解析、停止确认、同端口普通USB重现及本地4项收尾。新摘要保留失败阶段/有界错误码；旧`last_host_operation`不是精准失败位置，CONTROL也不证明USB内部故障根因。
6. 结束后一次核实实际画面与7号存取灯（不是充电灯），安排普通USB收尾并记录是否回到菜单；不从正常画面或电量假定服务退出已证。
7. R3成功后审阅完整采集的服务优先接入及显式供电声明，再安排R4全材料/有界复读，仍保留完整程序指纹。若同阶段再失败且无新证据，则评估原生Windows只读对照或后置Mac，不连续试错。D5/D6与真正3D LUT支线后置。

## 新准备及结果边界

- 新三文件位于`research/output/custom-round79/`，不上传；生成器拒绝已有目标。启动器日志noclobber，私有目录/作业/回执排他检查保留。源码在导入前、电脑预检查后/入口前、摘要子进程前核验。
- 新reader只接受`a7c2-service-probe-result/2`，输出`a7c2-service-probe-local-summary/2`；供电、START状态/边界、认证/快照/退出与本地收尾分列，失败阶段/错误码白名单输出，拒绝矛盾完成和类型。字段摘要不是证据图检查或硬件证明，不输出身份/材料哈希/路径/原始字节。
- 第78轮限定兼容仍只有普通侧第一次START、实际SDK USBError精确整数-9/32，随后必须完整认证；PIPE没有伪ACK。服务START/STOP、其他错误、取消/期限/日志失败仍停止。
- 旧完整采集/安装器及其版本、百分比、完整程序指纹契约不变；接入完整入口时需要显式迁移持续供电声明，不能填假数字绕过旧接口。

## 本轮验证与私人记录

本轮日志在`research/output/custom-round79/`：

- `.venv/bin/python -B research/output/custom-round79/test_preparation.py`：21项通过，0.716秒，仅自制SDK/材料，含真实隔离摘要子进程与非管理员拒绝。
- `.venv/bin/python -B -m unittest research.tests.test_captureprobe`：31项通过，0.988秒。
- `.venv/bin/python -B -m macfl23 check`及`.venv/bin/python -S -B -m lutphoto.captureprobe --help`：通过，无USB；启动文件`zsh -n`通过。
- `.venv/bin/python -B research/output/custom-round79/check-round.py`及`git diff --check`：公开范围/链接、172冻结来源、新准备未使用及6份旧私人文件不变检查通过。

第77轮原定位文件和失败结果仍在`research/output/custom-round77/`。其3操作文件、原结果log、既有详情检查log及location共6份保持；第67/69/71/77轮已用命令禁止重跑，第72轮暂停。不要运行旧生成器/冻结测试去更新现场。

本轮按已有授权推送到`lut-photo/main`，不推origin；仅公开文档，私有脚本/材料/日志不上传。本轮提交/远端/CI以Git和最终回执为准。每轮更新本交接、轮次记录和四列计划，明确区分准备完成、实际派发、设备返回与照片验收。
