# 第六十九轮：下一次受控只读验证的离线审阅与准备

2026-10-23准备，10月24日续记执行结果。延续第六十八轮交接，前述准备阶段先审阅既有capturecamera完整固定读取及新诊断，不连接/枚举相机，不执行原生接口、卸载、认证或采集，不读取管理员原始作业；10月24日的新采集失败结果见文末。第六十七轮UNKNOWN/0材料与第六十八轮本人反馈正常均保留，原USBError原因仍未知。

## 本轮有限交付

- 复核同一固定入口的来源/宿主、范围、独立输出、诊断/终态及停止条件，不新增传输层/设备模式/超时或重试。
- 为一次新作业准备冻结源码、现时电量、原私有父目录检查、单次调用、自动电脑端复核和有界摘要；本轮不执行设备分支。
- 验证设备前拒绝、文件权限/不覆盖、原CLI故障和摘要退出码，明确模拟范围与实际待办。
- 更新四列总计划、短交接及本轮证据，保留既有未提交分析和所有私人记录。

电脑端审阅/本地准备完成，结果如下；不把准备完成记作已解决USBError或允许无条件重采。


## 审阅结论与具体准备

复核既有_OwnedRun.body：normal-before身份通过即创建原认证流程，再由同一所有者进入服务/材料读取。因此下一次仍是原capturecamera --resources的一次新作业，正常身份失败即停，通过后继续此前已授权的74材料固定读取；并非仅查看电脑登记或只做一次型号检查。没有新增设备模式/后端/模拟层或放宽期限/源码/指纹。完整结论见[单次验证审阅](../docs/CAPTURE-TRIAL-REVIEW.md)。

为本次本地受控尝试生成独立启动器/读取器和一次性shell，具体路径仅保存忽略目录的位置索引。冻结165个当前Python/JSON/依赖声明文件（包含原资源文件清单）及读取器，项目导入前、现场输入电量后及启动摘要子进程前均核对。只按原描述符规则新建/核验专用0700父目录，不chmod/chown已有条目，拒绝链接/共享目录；新作业与独立回执全新，日志为普通用户0600/noclobber。代码冻结仅检测本地源码变化，不是外部签名或SDK/硬件认证。

启动器只调用原capturecamera.main一次，固定原厂2.01/ILCE-7CM2及--resources，实际电量即时输入50–100，不复用98%。原调用返回后，独立-S子进程复用原captureevidence/Reader做一次完整材料/回执检查，另只读检查点/事件，输出有限新诊断、计数和最多48事件摘要；没有身份、作业号、指纹、原始值或路径。原采集、电脑检查和摘要退出码分别保存，原非0不能被成功摘要掩盖；原采集0但检查失败时外层仍非0。来源/输出/信号/未知即停规则不变，不调用任何恢复/重试/清端点/sense或旧机内诊断。

本轮未运行该命令的管理员/真实设备分支，没有重新连接、枚举、卸载、打开接口、认证或相机命令，没有读取管理员旧作业/PRIVATE/移动盘。默认单份；不创建额外备份副本。

## 实际测试与检查

```sh
.venv/bin/python -B research/output/custom-round69/test_reviewed_operator.py -v
.venv/bin/python -B -m unittest research.tests.test_capturediagnostics research.tests.test_captureexecution research.tests.test_capturecamera -v
/bin/zsh -n research/output/custom-round69/run-reviewed-capture.command
.venv/bin/python -B -m macfl23 check
git diff --check
```

本地12项退出0（1.081秒），原诊断/装配/公开入口59项退出0（4.272秒），shell语法和固定check退出0。12项只使用已有自制SDK/系统/74份自制材料、临时私人文件和真实-S文件读取子进程；没有真实USB SDK导入。覆盖成功调用/74材料独立复核、相同13调用/8451字节USBError的有界新诊断且0认证、两种退出码不被覆盖、已有作业重复拒绝、源码变化/符号/硬链接/大小/目录拒绝、电量拒绝、新私有父目录及坏目录不改权限、日志0600/拒绝覆盖、文件检查拒绝不导出未经核对内容。成功native标签仍是原公开入口在假SDK下生成，不视为硬件认证。

另实际执行`.venv/bin/python -B -`：以规范化后的本人临时目录作新名字，原资源预检OFFLINE_PREFLIGHT_CHECKED、预算357,258,024字节、依赖元数据/空间满足；普通用户管理员标志false，没有SDK/USB、作业/全局相机锁或目录创建。原实际运行仍须在管理员上下文重新检查。AST确认一次capturecamera.main、固定--resources/ILCE-7CM2/2.01/实际电量参数、没有重试/恢复/额外副本API，三份本地Python语法通过。当前源冻结实际核对通过。

单独以真实普通用户-S子进程启动准备脚本，退出1/OPERATOR_REFUSED_BEFORE_ENTRY=PermissionError，stdout只有限标志，stderr无异常原文；这是预期设备前拒绝，不是真实采集失败或管理员路径通过。没有主动提权或输入/索取密码。

第一次本地测试误把资源清单路径写成较短路径，另一项0750坏目录被测试进程umask077实际创建为0700，导致两项断言失败；原父目录规则没有漏检。更正实际资源路径、显式设置自制坏目录0750并还原测试进程umask后12项通过。首次unittest还自动收集了导入的21项CameraTests，32项中上述2项失败；最终明确仅运行本地12项。首次临时目录预检因系统符号路径var触发原_parent拒绝，改为临时目录的规范物理路径后通过；没有放宽路径规则。上述过程均无设备动作，不将首次失败写成通过。

## 实际待办与交接

旧失败/回执/目录不改，原USB原因未确定，仍0内部材料。本人随后明确回复“暂保持断开，稍后进行”，因此真机阶段后置，保留准备，等待本人主动开始，不发起采集或安排自动执行。届时先复核冻结源码及实际连接/MSC，再提供完整单次命令，终端现场认证/输入实际电量；没有授权更新/写程序/保存设置。正常身份通过后会继续原完整范围，遇非0/未知/缺结果立即停，不重跑旧脚本或第二次试验。新结果另续记本轮并更新交接，不能把这份准备当成D4完成。

本轮生产Python、测试、依赖、固定锁和旧安装器无改动，故只跑上述相关检查，不重复第六十八轮1056项全回归；该旧总数不算本轮验证。总计划只维护四列，详细准备/状态留本轮与交接。公开范围仅脱敏审阅/状态文档，排除README/DELIVERY各4行、plan原有82行附录和4份未跟踪旧分析；本地脚本、测试、位置/日志均忽略不发布。实际Git提交/远端结果另核对，仅lut-photo/main，不推origin、不强推。

最终审阅另补源变化发生在原采集返回之后的边界：启动文件读取子进程之前再次校验冻结源码，变化则不执行可能已改变的读取器，原采集即使0也保持外层非0；没有重采。该项新增自制故障测试后最终本地12项退出0（1.081秒），替代此前本地11项结果；原59项及生产代码未变。准备文件SHA仅保存在私人索引，真实结果日志尚未创建，当前未执行设备分支。

最终文档/公开范围检查退出0：9个脱敏文档、172个本地链接目标及格式/围栏/个人路径通过；README/DELIVERY原有各4行、plan原有82行完整排除，4份旧专项报告哈希不变。git diff --exit-code核对运行代码/公开测试/旧安装器/依赖/固定锁无差异；git diff --check通过。本地准备/测试/位置/日志均保持忽略，真实结果日志尚未创建；按本人最新选择保持断开、稍后进行，未给出旧作业的续跑或重试指令。

## 10月24日：本人主动开始后的启动前复核

本人主动要求“开始只读采集”，随后确认“已连接MSC，仍为官方原厂2.01”。此前暂缓已由本人结束；实际电量及管理员认证仍由本人在终端现场完成，没有沿用旧电量或索取密码。采集范围和未知即停边界不变，原USB错误尚未证实修复。

本次仅执行电脑文件检查：`.venv/bin/python -B -`内联核对165个冻结源码/声明文件及4份本地准备文件的摘要、普通文件/单链接/大小条件、新结果日志不存在及无SDK导入，退出0；`/bin/zsh -n research/output/custom-round69/run-reviewed-capture.command`退出0；`.venv/bin/python -B -m macfl23 check`退出0。没有修改运行代码、锁或准备脚本，没有枚举/接管USB或开始采集；准备向本人提供既有完整单次命令，等待终端实际结果。既有未提交专项分析和私人材料保持原样。

## 10月24日：新作业实际失败与收尾

本人执行已给出的单次命令后回复“已结束”。本地0600结果日志包含准备检查通过、CLI简报及管理员上下文自动文件检查/摘要；本次核对只读取该已有普通用户日志，不重新读取管理员原始目录或发送相机命令。结果如下：

| 项目 | 实际记录 |
| --- | --- |
| 原CLI | NEEDS_REVIEW / ValueError / receipt_saved:true，CAPTURE_CLI_EXIT_CODE=1 |
| 自动文件检查 | NEEDS_REVIEW_UNKNOWN，terminal_evidence:MATCHED_FAILURE，OFFLINE_INSPECTION_EXIT_CODE=1 |
| 摘要导出 | export_complete:true，EXISTING_RECORD_EXPORT_EXIT_CODE=0；只证明摘要成功 |
| 事件 | 6条：CAPTURE_CONTEXT、CAPTURE_LOCKS_HELD、OWNER_FLOW_BOUND、INTENT normal-before、HOST_INTENT INVENTORY、NEEDS_REVIEW；无INVENTORY ACK |
| 流程 | C0/blocked/outcome_unknown；0已打开/关闭句柄、0身份查询/调用/字节、0认证调用/字节、0材料/材料通道请求/传输；authentication_phase:NOT_STARTED，transition_started:false |
| 收尾 | owners:NOT_ACQUIRED，global_lease/job_store/signal_handlers:CONFIRMED；不据此声称相机恢复通过 |
| 身份诊断 | 空列表，查询尚未开始；没有取得真实新身份IO诊断或原USB错误原因 |

源码核对显示HOST_INTENT后由同一步执行原_NativeOps.inventory、后置检查和HOST_ACK记录；因此能定位到枚举边界，不能单凭6事件/ValueError确定SDK枚举、_Key位置字段拒绝、枚举对象处置或ACK记录中的具体失败点。未出现后续MEDIA/UNMOUNT/OPEN_HANDLE/DETACH_KERNEL/CLAIM_INTERFACE/身份/认证事件。跟踪句柄计数不包括枚举内部SDK对象，不能据0句柄声称整个尝试完全未接触USB。第六十七轮41事件/USBError与本次6事件/ValueError分开保存，不互相补齐。

本人随后确认“画面正常，存取灯已熄灭”。已提示按普通USB断开：有卡图标先正常推出、再拔线，无图标可拔线；推出受阻则停，不强制。尚未收到实际断开确认，不补填拍摄/回放/冷启动/恢复验收。没有重跑采集、补ACK、清端点、sense、复位、认证、旧prepare/verify/diagnose或写入。

`.venv/bin/python -B -`本地内联核对退出0：原结果日志为本人所有的0600单链接普通文件，长度/元数据前后一致；两个报告、三退出码、6事件及所有零计数一致。独立保存本地completion-review-20261024.private.json（0600），记录原日志摘要及已执行/失败/未确认断开事实，不修改原回执、日志、准备索引或冻结脚本。该新结果优先于准备索引中历史device_attempt_executed:false。

N3/D4仍未完成，内部备份仍0材料。下一步只针对本次已发现缺口补有界枚举定位与自制SDK验证，不放宽位置/唯一机身/程序指纹，不增加设备调用或重试；离线修正和审阅完成前不发起另一轮采集。总计划和交接按此更新，D5/N4写入及真实色彩继续后置。

本次结果文档检查：`.venv/bin/python -B -`内联公开范围/链接检查退出0，10份脱敏文档、183个受跟踪本地链接、格式/围栏/个人路径检查通过；README/DELIVERY原有各4行、plan原有82行完整排除，4份未跟踪专项报告摘要不变。首次检查用默认Git文本列表时，中文路径被Git引号编码而误报缺失；改用`git ls-files -z`核对后通过，未改链接目标或放宽发布范围。`git diff --check`退出0；`git diff --exit-code -- lutphoto macfl23 tests research/tests upstream.lock.json requirements.txt a7c2-mac setup.sh`退出0。生产代码未改，不重复前轮离线全回归；真实运行如上为失败，不能以文档检查通过代替。发布仅含脱敏状态文档，原作业/回执/日志/位置/脚本不上传，提交推送结果另以Git核对。
