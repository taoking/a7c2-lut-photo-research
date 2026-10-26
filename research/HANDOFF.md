# LUT 照片开发：当前交接

更新：2026-10-26，第七十七轮。后续AI先读根AGENTS、README、[四列计划](../plan.md)、本文件和[第77轮记录](LUT链路调查记录-第七十七轮.md)。本文件是接续入口；历史见[轮次索引](ROUNDS.md)。不能只凭“继续”重跑相机命令。

## 当前状态与最新授权

D1–D3离线冻结；R1读包修正、R2有限服务入口和R3单次准备完成。1122项完整离线回归、15项准备测试通过。**R3首次真机失败停止：USB型号已读，NORMAL_START边界PIPE(-9/32)，44事件/0快照。D4真实材料0，旧完整入口仍先查MSC身份。** D5/D6及真正3D LUT支线后置。

本人本轮授权提交推送，随后主动要求继续并明确确认“已连接MSC，仍为官方原厂2.01”。本次授权范围为新有限probe，最多读取一份RAM快照；服务认证会临时改变连接状态，不加载机内模块、不更新/写程序/保存设置。不再次索取已有授权；本次已在终端执行结束，未取得快照。本人随后要求未来脚本不再询问/输入电量，持续高电量/供电作为本人声明；密码仍只在本机终端。该声明不是完整程序指纹或拍摄/恢复证明。

代码已提交推送为`5a8ed7fc2e359e535aeee573c5568a3b03d9a0d6`，远端main已核对，离线[CI 40271099955](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/40271099955)成功。本轮设备结果为NEEDS_REVIEW，CLI退出1、回执摘要退出0；本地owners/job_store/global_lease/signal_handlers均true，协议结果unknown。普通/服务认证、快照解析、停止服务及普通USB重现均未确认；未进行完整采集、更新或保存设置。

本人确认终端结束、画面正常、7号存取灯熄灭，最后回复“仍保持USB连接”。已说明普通USB断开流程，实际断开/正常菜单/冷启动/拍摄未确认。不要再次发相机命令、重采或强制重启。

## 下一动作：离线审阅首次START的状态错误兼容

1. 不重跑第77轮或任何旧准备。先读[本轮失败与固定来源](LUT链路调查记录-第七十七轮.md#实测结果与后续决策)，核对原始回执阶段与控制路径。USB型号成功及NORMAL_START阶段已由仅文件读取器确认；`last_host_operation=USB_PRODUCT_STRING`是最近已记录宿主操作，不是此次错误的精准定位。NORMAL_START仍含描述符前后检查及控制调用，现有回执没有底层逐调用追踪，不能把状态阶段假说写成已证实根因。
2. 本地固定YuuLuo源码在首次START的PIPE(-9、errno32/None)后继续认证；固定v2.1 PMCA更广泛吞掉start/stop异常。本项目当前任何异常都会污染认证/端口后停止。只审阅“首次START、明确错误码、随后完整认证才建立成功”的有限候选，不复制宽泛吞异常、STOP容忍、重试/复位/救援；失败、中断及异常阶段仍停止。
3. 如实现候选，先厘清各层unknown标志、诊断阶段和回执区别，用独立自制响应验证允许条件及其他错误仍拒绝；同时明确CLI/回执不把START异常当成功ACK。审阅及离线验证完成后才新建准备，禁止修改旧冻结值后复用。本轮只有源码比较和一次自制失败复现，尚未实现该兼容。
4. 后续脚本不再要求电量确认或百分比输入。将本人“持续维持高电量、USB连接中电量不下降”保留为用户供电声明，不能宣称自动读到了电量。当前CLI/宿主仍要求整数百分比，下一份准备必须先显式表达该声明并测试相关入口/回执，不能硬填98/100或修改旧材料。不得因旧脚本含电量提示再反复向本人询问。
5. 下一次设备验证需新的明确问题、审阅过的准备及实际连接；不因“仍连接”自动开始。若限定候选仍在同阶段失败且无新证据，再评估Windows原生只读对照或后置Mac。R3未通过前不接完整采集。

## 私人记录定位及只读复核

忽略目录`research/output/custom-round77/location.private.json`登记操作/读取器/.command摘要、仓库外作业/回执和本地结果日志。当前`device_attempt_executed=true`，有失败摘要和文件检查状态；三个已用操作文件保持原字节。`build-preparation.py`只是历史生成过程，不再运行。第67/69/71/77轮已用命令禁止重跑，第72轮准备暂停。

`probe-result.private.log`保留原CLI及`PROBE_CLI_EXIT_CODE=1`、`RECEIPT_SUMMARY_EXIT_CODE=0`；`existing-details-terminal.private.log`保留仅回执字段检查：USB型号存在、NORMAL_START、44事件、无服务身份/快照。普通代理进程无法读取管理员原件；一次sudo非交互文件检查因需要密码退出，随后只读文件终端成功。两者不访问USB。不要重复打开相机操作命令解决文件权限。

`probe-reviewed-once.py`、`read-probe-receipt.py`、`run-reviewed-probe-once.command`的172冻结仍可只读核对；文件存在/摘要正确不代表可以重跑。正常流程120秒合作式预算、单次协议5秒、单段等待20秒，管理调用可能阻塞；本次没有强杀或额外设备命令。

## 结果边界及后续路线

私有回执schema为`a7c2-service-probe-result/1`，stdout为`a7c2-service-probe-cli-result/1`。0/PROBE_COMPLETE只表示一次快照身份、健康停止、同端口普通USB重现及本地交付完成。`normal_identity_rechecked`、`program_fingerprints_verified`、`complete_backup`、恢复/写入/续跑始终false；没有第三句柄或返回序列复查。

专用摘要为`a7c2-service-probe-local-summary/1`，`scope=receipt-fields-only`、`graph_checked=false`、`hardware_verified=false`。只核对私有普通文件边界、严格布尔字段和明显矛盾，不独立验证事件图、快照绑定或硬件事实。没有新增通用probe图检查器。原快照、身份摘要、位置和日志都是私人资料，不能公开。旧`captureevidence inspect`有意拒绝新schema，不改schema消除拒绝。

R3成功后先审阅将服务优先入场接入完整采集的必要改动，再安排R4全材料及有界复读；不能直接运行仍采用MSC入场的74材料命令。完整程序指纹门槛没有豁免。本轮产生具体START候选，下一步按上文有限审阅；若后续同阶段再次失败且无新证据，按[交付计划](../docs/DELIVERY-PLAN.md)评估原生Windows 11只读对照或后置Mac，不继续堆模拟轮次/反复重连。

实现：[captureprobe](../lutphoto/captureprobe.py)、[captureidentity](../lutphoto/captureidentity.py)；专项测试[17项](tests/test_captureprobe.py)。完整采集与证据契约仍在[captureexecution](../lutphoto/captureexecution.py)/[captureevidence](../lutphoto/captureevidence.py)。操作说明见[有限入口](../docs/CAPTURE-SERVICE-PROBE.md)、[新旧准备](../docs/CAPTURE-TRIAL-REVIEW.md)。

## 本轮实际离线验证

Python3.14.6，自制数据/SDK；命令及日志均在本机执行：

- `.venv/bin/python -B -m unittest discover -s research/tests -v`：1075项通过，83.706秒。
- `.venv/bin/python -B -m unittest discover -s tests -v`：39项通过。
- `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v`：8项通过；完整回归共1122项。
- `.venv/bin/python -B research/output/custom-round77/test_preparation.py`：15项通过，含真实-S文件读取子进程、单快照自制成功/未知失败、退出码、源码漂移、链接/超限、旧目录、锁、摘要隐私及单次控制流。初次测试误把清单中的capturecamera文件名判作调用，改为AST名称检查后全15项通过；不是生产问题。
- `.venv/bin/python -B -m macfl23 check`：固定来源/资产通过。
- `.venv/bin/python -B research/output/custom-round74/check-legacy-receipts.py`：3类自制旧回执分类/字节不变。
- `.venv/bin/python -S -B -m lutphoto.captureprobe --help`：参数匹配；无SDK/USB。
- 普通用户临时私有目录`capturepreflight.inspect(...,resources=False)`：通过，285954856字节保守预算，管理员标志false、未加载SDK、未创建作业。
- `.venv/bin/python -B research/output/custom-round77/check-publication.py`：公开范围、链接、隐私、172冻结、旧文件与来源保留检查；详细结果在本轮忽略目录。`git diff --check`检查通过后才提交。

本次设备失败后的补充验证：`.venv/bin/python -B research/output/custom-round77/reproduce-start-stall.py`的1个自制START故障场景通过；`.venv/bin/python -B research/output/custom-round77/check-outcome.py`检查8份更新文档、187个本地链接、已用脚本及172来源未变、失败摘要与供电偏好一致，`git diff --check`通过。补充只改文档，未重复全套或再次操作设备。

## 历史现场、发布与交接

第71轮KEY_VALIDATE/BUS、6事件、0身份/认证/材料、UNKNOWN，未记录原bus值。第69轮枚举ValueError缺内部边界，第67轮身份USBError只有13调用/8451接受字节；不回填原因。第72轮167冻结有8个路径已改变且不含新入口，操作文件仍原字节保留，不再可用。

开工HEAD为`d94a4628171aeacbebfc707f98bc1d8d2cb34a09`；34项既有修改/新文件已快照在本轮忽略目录initial。本轮没有修改公开运行代码；完成私人操作准备/测试后，执行一次有限验证并只读复核失败回执。提交范围包含保留的第73–76轮源码/测试/记录、此前五份公开专项分析及本轮交接；固定锁、安装器、依赖、完整程序策略不改。

已按本人授权将上述公开代码推送到`lut-photo/main`（taoking/a7c2-lut-photo-research）；未推继承的origin。提交及远端结果以本轮最终回执、Git日志与远端main一致性为准；私人材料不进入Git。每轮结束更新本文件、轮次记录和四列计划，区分代码完成、操作准备、已派发与真机验收；本次实际执行及失败已更新，不能沿用此前“待开始/未启动”状态。
