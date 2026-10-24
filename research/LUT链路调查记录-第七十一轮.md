# 第七十一轮：回执/3的新单次只读尝试审阅与准备

2026-10-24。延续第七十轮，先在相机断开时审阅原完整读取入口、有限枚举/身份诊断与旧失败边界，准备全新一次性命令和输出，不枚举或操作真实USB。本轮准备完成后，本人明确确认“已连接MSC，仍为官方原厂2.01”；实际电量与管理员认证仍须终端现场取得，准备时未执行设备分支；随后实际失败结果见文末。授权仍仅采集/检查，不更新或修改相机。

## 有限交付

复用第六十九轮准备主流程，仅替换全新作业/回执/日志位置、当前166文件摘要及回执/3检查；AST确认除此schema检查外main结构一致，原独立-S文件读取器字节未改，其检查输出/3已自然带有限host_diagnostics。原入口仍只调用一次capturecamera capture --resources：普通身份失败即停，通过后继续完整AP/CP、首末RAM/保存设置及68资源，共74材料、默认一份。没有仅枚举后退出的新模式，也没有增设传输层或后端。

源码导入前、终端输入实际电量后、文件检查子进程前均校验冻结；源码变化拒绝后续相应动作。新私有父目录/目录/回执按原描述符/所有者/0700规则，不chmod/chown已有目录；普通用户结果日志0600/noclobber，已存在即拒绝第二次动作。入口返回后原独立-S子进程只检查新文件并输出有限诊断/计数/至多48事件名，三退出码分别保存，原失败不被成功导出覆盖。

相机认证/选读会改变临时状态；不上传/删除文件、不加载模块、不写程序或保存设置、不WBI，不调用旧prepare/install/verify/restore/diagnose，不清端点/sense/复位/重试。不改固定机型/指纹、位置/唯一、协议/期限/字节/锁或未知即停。第六十七轮41事件/USBError及第六十九轮6事件/ValueError均保留0材料/UNKNOWN，原因未知；本次准备不能补回旧步骤或证明已修复。

具体命令/启动器/读取器及新输出位置仅存忽略目录custom-round71/reviewed-capture-location.private.json；第六十九轮旧命令已使用且源码冻结过时，禁止再运行。本人过去正常画面/灯灭/已断开只是人工观察，当前重新连接声明也不代替完整程序/材料/退出或恢复验收。

## 实际离线检查

```sh
.venv/bin/python -B research/output/custom-round71/test_reviewed_operator.py -v
.venv/bin/python -B -m unittest research.tests.test_captureinventory research.tests.test_captureexecution research.tests.test_capturecamera -v
/bin/zsh -n research/output/custom-round71/run-reviewed-capture.command
.venv/bin/python -B -m macfl23 check
git diff --check
```

本地15项退出0（1.377秒），原枚举/装配/公开入口68项退出0（4.619秒）；shell语法、固定来源check退出0。15项只使用已有自制SDK/74份自制材料、普通用户私人临时文件和真实-S文件检查子进程。覆盖完整读取一次成功/已有作业再用拒绝、身份13调用/8451字节USBError的原诊断、6事件SDK枚举和缓存BUS拒绝的不同新诊断、ACK保存前后故障、零认证、单次对象处置/导出、不泄露位置/异常原文、原非0/检查失败不升级、源码变化/链接/超限/坏父目录拒绝、日志0600/noclobber及普通用户设备前拒绝。原生标签仍是自制SDK经原入口生成，不作为硬件认证。

另执行`.venv/bin/python -B -`：AST核对166文件摘要、main仅更新回执/3检查、原一次调用与ILCE-7CM2/2.01/--resources/实际电量范围、读取器原字节、结果日志不存在及无SDK导入，退出0。规范私人临时目录的原资源预检OFFLINE_PREFLIGHT_CHECKED，预算357,258,024字节、固定依赖元数据/空间满足；管理员标志false，无SDK/相机锁/作业创建；管理员上下文仍由实际运行重新核对。没有访问真实USB或管理员旧作业/PRIVATE/移动盘。

本轮生产代码、公开测试、依赖、固定锁、旧安装器均无修改，故不重复第七十轮1072项全回归，不把旧总数或自制成功计为实机通过。本轮未主动提权，没有向聊天索取密码或代填实际电量。

## 下一动作与交接

已取得本人当前MSC/官方原厂2.01声明；下一动作是在终端只启动本轮完整新命令，由本人现场输入实际电量与管理员认证，不再重复询问已有持久机型/版本事实。若机身状态有变化先说明。实际运行结束后只读新output核对原CLI/文件检查/摘要三退出码、阶段及有限诊断；任意非0/未知/缺结果停止，不再次采集，不补ACK或改变旧回执。若正常阶段重新询问USB方式，仍由本人选MSC。

只有CAPTURE_COMPLETE与完整材料/退出复核通过才推进D4相应证据，D5/N4不自动解锁。当前尚无新设备结果，D4完整程序/74材料及真实退出仍缺，真实ST/单槽/恢复继续后置。

开始前在忽略目录custom-round71保存8份既有改动快照，README/DELIVERY/plan的原分析及5份未跟踪报告均保留、不纳入本轮。plan原上游调查段包含勾选和正文更新，发布视图按快照逐块精确撤回已有差异，工作文件不回退。公开仅本轮脱敏审阅/状态文档，所有本地脚本/测试/位置/日志不发布；提交推送另核对，仅lut-photo/main。

最终`.venv/bin/python -B -`文档/公开范围检查退出0：9份脱敏文档、175个本地链接目标、格式/围栏/个人路径通过；已有增补/更新逐块精确排除，5份未跟踪报告摘要不变，四份本地准备文件摘要仍匹配，真实结果日志不存在。`git diff --check`退出0；`git diff --exit-code -- lutphoto macfl23 research/tests tests upstream.lock.json requirements.txt a7c2-mac setup.sh`退出0，研究固定锁逐份无变化。本人连接事实已到，仍等待其终端实际启动，不将准备或连接确认写成采集通过。

## 实际执行结果：KEY_VALIDATE/BUS拒绝

本人在终端执行本轮新命令后报告已结束。原CLI NEEDS_REVIEW/ValueError/receipt_saved:true，CAPTURE_CLI_EXIT_CODE=1；管理员上下文自动文件检查为NEEDS_REVIEW_UNKNOWN/MATCHED_FAILURE、OFFLINE_INSPECTION_EXIT_CODE=1；EXISTING_RECORD_EXPORT_EXIT_CODE=0且export_complete:true，只表示摘要成功。6事件仍为CAPTURE_CONTEXT、CAPTURE_LOCKS_HELD、OWNER_FLOW_BOUND、INTENT normal-before、HOST_INTENT INVENTORY、NEEDS_REVIEW，没有INVENTORY ACK或后续接口/身份/认证事件。

首次取得新增宿主诊断：inventory_call:1，failure为KEY_VALIDATE、invalid_key_fields:[BUS]、ValueError，errno/backend_error_code均null，record_error_type:null；identity_diagnostics为空。检查点C0/blocked/outcome_unknown，所有流量/身份/认证/材料和已打开/关闭句柄计数为0，认证NOT_STARTED、transition_started:false；收尾owners:NOT_ACQUIRED，job_store/global_lease/signal_handlers:CONFIRMED。枚举内部SDK对象不计入跟踪句柄，不能把0句柄解释为整个尝试没有接触USB。

本次可证明缓存总线字段未满足原精确整数且大于0的条件；原始bus值未保存，不能断言为0/None/负数或认定机身/线材故障。PID/PORTS/ADDRESS没有被记录为拒绝字段。第六十九轮没有该诊断，第六十七轮失败点不同，不据本次回填两次旧原因。所有原UNKNOWN、0材料和写入/恢复未证边界保留。

结果核对只读取本人所有的0600单链接普通日志，长度/元数据前后一致；原日志摘要、两报告/三退出码、6事件/零计数和新诊断一致，`.venv/bin/python -B -`内联核对退出0。另存本地0600 completion-review-20261024.private.json，不修改原日志/回执/冻结脚本/准备索引；准备时device_attempt_executed:false不再表示最新结果。没有重新采集、认证、卸载/打开接口、清端点/sense、复位或写入，也没有重开管理员原作业/PRIVATE/移动盘。

本人报告画面正常，但起初只认识充电灯。核对[官方说明书第42页侧面图](https://helpguide.sony.net/ilc/2360/v1/zh-cn/print.pdf#page=42)，2号充电灯与7号存取灯分开；本人随后明确确认7号灯已熄灭。已按[官方USB断开说明](https://helpguide.sony.net/ilc/2360/v1/zh-cn/contents/0903_disconnect_pc.html)提示普通推出/拔线、受阻不强制。尚未收到实际断开确认，10月25日当前连接不猜测，不补填拍摄/冷启动/恢复通过。

只读本地安装的PyUSB 1.3.1源码，Device.bus来自后端描述符；libusb后端将libusb_get_bus_number的uint8_t结果写入描述符。此为静态来源核对，没有导入/调用USB SDK，也未采集原始bus。下一轮先审计固定libusb/Darwin总线编号语义及全部位置/证据校验点，再决定兼容修正；不以未知数值为理由放宽原检查，也不直接再试相机。

D4仍无完整材料/退出正例，本次新增定位不等于修复。所有第六十七/六十九/七十一轮命令已使用，禁止再运行；下一步仅电脑端工作。

10月25日结果文档检查：`.venv/bin/python -B -`核对10份脱敏文档、184个本地链接及格式/围栏/个人路径通过；已有分析逐块排除、5份未跟踪报告及原日志/四份准备文件摘要不变。`git diff --check`退出0；`git diff --exit-code -- lutphoto macfl23 research/tests tests upstream.lock.json requirements.txt a7c2-mac setup.sh`退出0。本段仅收尾结果文档，没有新增代码或设备操作，不重复运行无关离线回归。
