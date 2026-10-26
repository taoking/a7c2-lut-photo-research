# LUT 照片开发：当前交接

更新：2026-10-26，第七十七轮。后续AI先读根AGENTS、README、[四列计划](../plan.md)、本文件和[第77轮记录](LUT链路调查记录-第七十七轮.md)。本文件是接续入口；历史见[轮次索引](ROUNDS.md)。不能只凭“继续”重跑相机命令。

## 当前状态与最新授权

D1–D3离线冻结；R1读包修正、R2有限服务入口和R3单次准备完成。1122项完整离线回归、15项准备测试通过。**本项目仍无真机成功；D4真实材料0，旧完整入口仍先查MSC身份。** D5/D6及真正3D LUT支线后置。

本人本轮授权提交推送，随后主动要求继续并明确确认“已连接MSC，仍为官方原厂2.01”。这次可进入新有限probe；只读一份RAM快照，服务认证会临时改变连接状态，不加载机内模块、不更新/写程序/保存设置。不再次索取已有授权；实际电量仍须现场输入，密码仅在本机终端。该声明不是完整程序指纹或拍摄/恢复证明。

此交接写入时准备与离线检查完成，尚未启动管理员/设备分支。**后续进程必须先查看下述本地定位文件和新结果是否存在；如果已经派发或有任何结果，先核对，不再启动。** 文件不存在也不能独立证明未尝试；须结合当前会话及定位记录判断。旧第67/69/71轮禁止重跑，第72轮继续暂停。

## 本地准备位置与执行顺序

忽略目录`research/output/custom-round77/location.private.json`保存新操作文件、摘要读取器、一次性.command、结果日志、仓库外作业/独立回执的位置，以及3个操作文件摘要。新文件名：`probe-reviewed-once.py`、`read-probe-receipt.py`、`run-reviewed-probe-once.command`。不要运行`build-preparation.py`重新生成路径；它只是本轮生成过程。不存在这些私人文件时不能照抄公开示例直接开始，应重新准备并审阅。

1. 先看定位记录的派发/执行信息和结果日志是否存在。核对3个文件摘要，再只导入操作模块调用`verify_reviewed_source()`，不要调用`main()`作检查。172文件冻结含新probe/identity和依赖；变化即重新审阅，不改旧摘要放行。
2. 当前本人已确认MSC/官方原厂2.01。没有后续断开或版本变更信息时不重复确认；若隔轮且实际状态不明再核对。启动一次性.command，在本机终端完成管理员认证和即时整数电量50–100。不要在代理后台输入密码，也不要填上次电量。
3. 一次性操作只调用一次`captureprobe.main`，没有74材料串接、重试、复位、清端点/sense、WBI或旧prepare/diagnose。新作业/回执排他创建，日志0600/noclobber；执行后不能再运行，即使入口前拒绝也先核对原因。
4. 返回后核对原CLI摘要、`PROBE_CLI_EXIT_CODE`、`RECEIPT_SUMMARY_EXIT_CODE`和外层结果。摘要子进程只读新回执，成功不覆盖原调用失败。若日志缺失/中断/未结束，保持现场，不自动重采或强杀。
5. 成功或失败均分别核对认证、快照身份、停止服务、普通USB重现、本地关闭与错误。需要正常USB断开时确认本人当前画面和7号存取灯；不凭充电灯判断，不强制重启/取电池。本人报告正常菜单、冷启动/拍摄应各自记录，不能从USB返回推断。

正常流程全程120秒合作式预算，协议调用最长5秒，单段等待20秒；SDK/文件系统管理仍可能阻塞。未知/取消/日志失败不发新命令；完整响应内容拒绝才允许健康单次停止。

## 结果边界及后续路线

私有回执schema为`a7c2-service-probe-result/1`，stdout为`a7c2-service-probe-cli-result/1`。0/PROBE_COMPLETE只表示一次快照身份、健康停止、同端口普通USB重现及本地交付完成。`normal_identity_rechecked`、`program_fingerprints_verified`、`complete_backup`、恢复/写入/续跑始终false；没有第三句柄或返回序列复查。

专用摘要为`a7c2-service-probe-local-summary/1`，`scope=receipt-fields-only`、`graph_checked=false`、`hardware_verified=false`。只核对私有普通文件边界、严格布尔字段和明显矛盾，不独立验证事件图、快照绑定或硬件事实。没有新增通用probe图检查器。原快照、身份摘要、位置和日志都是私人资料，不能公开。旧`captureevidence inspect`有意拒绝新schema，不改schema消除拒绝。

R3成功后先审阅将服务优先入场接入完整采集的必要改动，再安排R4全材料及有界复读；不能直接运行仍采用MSC入场的74材料命令。完整程序指纹门槛没有豁免。若同阶段再次失败且无新证据，按[交付计划](../docs/DELIVERY-PLAN.md)评估原生Windows 11只读对照或后置Mac，不继续堆模拟轮次/反复重连。

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

## 历史现场、发布与交接

第71轮KEY_VALIDATE/BUS、6事件、0身份/认证/材料、UNKNOWN，未记录原bus值。第69轮枚举ValueError缺内部边界，第67轮身份USBError只有13调用/8451接受字节；不回填原因。第72轮167冻结有8个路径已改变且不含新入口，操作文件仍原字节保留，不再可用。

开工HEAD为`d94a4628171aeacbebfc707f98bc1d8d2cb34a09`；34项既有修改/新文件已快照在本轮忽略目录initial。本轮没有修改公开运行代码，只准备私人操作/测试并更新文档。提交范围包含保留的第73–76轮源码/测试/记录、此前五份公开专项分析及本轮交接；固定锁、安装器、依赖、完整程序策略不改。

本人已授权发布到`lut-photo/main`（taoking/a7c2-lut-photo-research），不能推继承的origin。提交及远端结果以本轮最终回执、Git日志与远端main一致性为准；私人材料不进入Git。每轮结束更新本文件、轮次记录和四列计划，区分代码完成、操作准备、已派发与真机验收；实际执行一旦发生必须更新本段状态和定位记录，不能沿用“未启动”。
