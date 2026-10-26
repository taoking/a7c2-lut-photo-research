# LUT 照片开发：当前交接

更新：2026-10-26，第七十九轮实测后。先读根AGENTS、README、[四列计划](../plan.md)、本文件及[第79轮记录](LUT链路调查记录-第七十九轮.md)。历史见[轮次索引](ROUNDS.md)，限定START实现见[第78轮](LUT链路调查记录-第七十八轮.md)。

## 当前状态

**第79轮新准备已执行一次并失败停止，不是待运行。相机已由本人普通断开，拍摄画面/菜单正常。** START暂定PIPE后，普通认证NORMAL_VERIFY遇到USBError（backend -1、errno5）；认证未完成、0快照、协议UNKNOWN。D1–D3离线冻结，D4仍0真实材料，R3未通过，不能接完整74材料或写入。

本人先确认“已连接 MSC，仍为官方原厂 2.01”，实际终端运行结束后报告7号存取灯灭、屏幕进入连接方式选择页；没有再次选择连接，按普通USB流程拔线后回复“已断开，拍摄画面或菜单正常”。这些是用户观察，不改写协议退出、返回身份或恢复标志；冷启动、新拍和回放未验证。

既有电量偏好持续有效：后续脚本不确认/输入电量，使用持续高电量和USB供电的用户声明`--maintained-power`；百分比null、自动测量false。密码只在本机终端输入，不猜数字、不改免密sudo/SIP。当前没有新设备尝试安排。

## 实测结果与证据边界

- 原日志为NEEDS_REVIEW，`PROBE_CLI_EXIT_CODE=1`、`RECEIPT_SUMMARY_EXIT_CODE=0`，CLI报告回执已保存；摘要读取成功不覆盖采集失败。
- `reported_normal_start`：`control_status=PIPE`、`boundary=COMPLETE`、policy=`normal-start-pipe-32-v1`。这是限定错误及后置检查完成，不是ACK，不证明相机接受START。
- 错误为NORMAL_VERIFY、USBError、backend_error_code=-1、errno=5、start_boundary=null。普通/服务认证、快照解析、停止尝试/确认和普通USB重现全false；device_attempted及protocol_outcome_unknown为true。
- 本地owners/job_store/global_lease/signal_handlers全部确认。失败后仅读取已有结果日志及源码，未补发STOP、重试、复位或再次连接。
- `_RawAuth.authenticate`包含3轮挑战/证明及最终响应；`_OwnedPort._io`又含前后描述符检查。当前结果无逐次I/O边界，不能判定第几轮、读/写或描述符访问失败，也不能推断密钥错误、服务模式已进入或重枚举已发生。
- 第77轮旧NORMAL_START处PIPE(-9/32)、44事件/0快照仍保持；第79轮是新的失败阶段，不追认旧结果成功。

## 下一动作：离线核对普通侧认证传输

1. 保持相机断开；不要运行第79轮operator、command或生成器，不再运行带未派发断言的准备测试。第67/69/71/77/79轮已用命令禁止重跑，第72轮暂停。
2. 先比对固定上游与当前代码的普通侧接口/端点选择、认证报文长度/字节、传输方式、START后切换时序。只读源码和已保存的日志，不执行第三方相机工具，不导入新的固件资产或放宽哈希。
3. 分清现有证据能定位什么，不能仅凭通用USBError(-1/5)作根因判断。如需要新增诊断，先限定不含原始认证内容/身份的最小字段（轮次、方向、前置/SDK/后置边界及长度），说明它将回答什么，再审阅是否值得新的受控验证；不能为补日志立即重采。
4. 没有可复核差异或清晰诊断价值时，转原生Windows只读对照的环境/驱动可行性评估或后置Mac，不能继续扩大异常容忍、写更多通用模拟层或连续试错。后续真机仍需新准备及当时实际连接信息，不反复确认电量。
5. R3真正通过后再审阅完整采集服务优先接入和显式供电声明，安排R4材料/有界复读，仍要求完整程序指纹。D5/D6和真正3D LUT支线后置；当前授权仅采集/检查，不包括安装、更新或保存设置。

## 私人记录定位

`research/output/custom-round79/location.private.json`列出已用3文件、结果log和仓库外作业/回执路径，现为`device_attempt_executed=true`、`dispatch_state=ENDED_NEEDS_REVIEW`、`disconnect_confirmed=true`。`probe-result.private.log`保留原stdout，`device-outcome.private.json`保存从该日志读取的CLI/摘要及用户收尾反馈；不上传。

3操作文件与172冻结来源保持原字节，旧第77轮3操作文件、结果log、详情检查log及location共6份也保持。不要改冻结值后重用；需要核对当前失败状态使用本轮`check-outcome.py`思路，而非旧准备检查。原管理员回执没有在失败后重新打开，现有结论来自运行时读取器及结果日志；没有完整证据图重验或本项目内部备份正例。

## 验证与发布

- 派发前核对172冻结、3文件、旧6文件及新日志不存在，启动文件`zsh -n`通过。现场声明后只派发一次，管理员认证由本人终端处理。
- 准备阶段：`test_preparation.py`21项、`research.tests.test_captureprobe`31项通过；来源/资产、CLI帮助及文档检查通过，仅自制SDK/材料。生产代码沿用`39c9b168a2f31189c7e2e490783557e244bb518d`；第78轮1136回归是此前证据。
- 准备文档提交`4c3486faf650afcbf5c244b81cbe8204d03c7cae`已推送，其[CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/40279218604)success。它不证明设备成功。
- 实测后：`.venv/bin/python -B research/output/custom-round79/check-outcome.py`及`git diff --check`核对结果/退出码、冻结文件、用户收尾记录、公开文档链接和修改范围；生产代码、公开测试、依赖、锁未改，不重跑无关回归。

按既有授权将本次状态补充提交推送`lut-photo/main`，不推origin；仅公开状态文档。实际追加提交以Git及最终回执为准。每轮维护本交接、轮次记录和四列计划，明确区分软件分支走到、认证成功、服务退出、用户画面正常和照片验收。
