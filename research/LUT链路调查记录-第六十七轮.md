# 第六十七轮：真实只读首采与失败核对

本轮始于2026-10-22，最新状态见文末2026-10-23的USBError记录；前面的准备/待执行表述是历史，不能作为当前重试指令。

2026-10-22。本人报告升级且连接，明确“可以进行采集和检查，但是不要进行更新或修改”；一次补充确认机型ILCE-7CM2、索尼官方原厂2.01（未用修改升级包）、当前电量98%及MSC。该声明替代此前等待2.00升级的状态，仍不能替代协议身份和完整AP/CP指纹。

## 当前完成与待办

- 已阅读根规则、README/总计划/交接、安装与验证边界、capturecamera/首次采集/电脑端条件与核心装配源码。
- 固定源码/资产check通过；带68资源的离线来源/依赖/新名字/空间预检通过，预算357,258,024字节，不创建作业或保留空间。
- macfl23 usb-status成功，macOS登记确认唯一054c:0e8a及对应两组USB磁盘；不读存储卡文件，不卸载、接管或发相机协议命令。
- sudo -n检查提示需要密码；已准备完整单次命令，等待本人终端认证。未进行真实服务认证、内部读取或机内改动，尚无备份材料/SDK通信及退出正例。
- 既有未提交README/DELIVERY/plan安全分析与4份未跟踪专项报告已在忽略目录保存起始快照；PRIVATE未读取或修改。本次只维护计划/交接及操作记录，不改运行代码、依赖、指纹或锁。

只读范围为既有capturecamera --resources的完整程序、首末RAM/保存设置及68份UXC，共74材料，默认一份。服务认证和选读切换临时会话状态；不加载模块、不上传/删除机内文件、不写程序/保存设置、不WBI，也不调用旧prepare/verify/diagnose或任何安装/恢复入口。

忽略目录custom-round67准备一个本地启动脚本，只调用现有capturecamera.main一次，完成后使用captureevidence.main只读检查已有主机记录。没有新传输/后端/强制参数或设备重试。脚本经AST解析和逐项范围审阅，尚未执行设备分支；新作业及独立回执位于仓库外管理员私人目录，实际路径只保存在私人位置。

## 实际检查命令与结果

```sh
.venv/bin/python -B -m macfl23 check
.venv/bin/python -B -m lutphoto.capturecamera capture --help
.venv/bin/python -B -m lutphoto.capturepreflight --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --directory "/path/to/existing-owned-parent/new-job" --resources
.venv/bin/python -B -m macfl23 usb-status
sudo -n /usr/bin/true
```

前四项退出0；预检实际使用仓库外、父目录已存在且本人拥有的新名字，只记录检查结果，不创建目录或设备。帮助不启动设备。sudo检查退出1并提示需要密码，没有设备操作，也没有自动审批拒绝。运行代码未改，不重跑无关1035项回归，不把前轮结果当本轮真机验证。

## 交接

本人在本任务终端运行已准备的完整命令并自行输入管理员密码后，再核对原CLI退出码、阶段、回执与captureevidence一致性。不得因无输出、超时或未知而重跑设备；不强杀、复位、拔线或自行取电池。声明时点若已明显过期，先重新取得实际电量。

N3仍部分完成，D4待真实采集/退出/材料重验；N4、D5写入/恢复、D6真实Sony ST及摄影验收均未执行。此授权不推进持久化写入，默认一份内部材料不等于独立介质容灾或救砖保障。后续结果追加本记录并更新[当前交接](HANDOFF.md)及[总计划](../plan.md)，原始程序/设置/资源/身份/私人日志不上GitHub或聊天。

## 首次命令失败后的核查与修正

本人贴出原终端结果：REFUSED_BEFORE_DEVICE、ValueError、camera_session_may_have_started:false、receipt_saved:false、CAPTURE_CLI_EXIT_CODE=1，并明确未创建作业。原命令没有进入原生设备流程。与本任务终端未同步，后续sudo -n只读检查现有记录亦因需要密码而拒绝，未连接或重跑相机；没有自动审批拒绝。

只读stat确认系统管理员主目录为0750。原启动准备直接将作业/回执放在该目录下，遗漏了[首次采集要求](../docs/CAPTURE-FIRST-USE.md#范围与必须确认的信息)中的专用0700父目录；_Receipt在预留文件之前执行_private检查，因此该布局必定拒绝。源检查或SDK未因此获得放行，不把宿主准备错误记为相机通信失败。该遗漏已向本人说明；原命令/路径保留，不覆盖或重跑。

忽略目录另备修正脚本及全新路径：复用现有_parent/_private/_same，以描述符新建/验证管理员专用0700子目录；不修改系统目录或已有目录权限/所有者，拒绝链接和不合格条目。正式调用前重新取得本人实际电量并运行电脑预检；随后只调用既有capturecamera.main一次、captureevidence.main只读核对文件。没有后端/版本覆盖、机内模块、写入、恢复或未知重试。

为免再次要求本人转贴结果，终端命令用umask077/noclobber将原CLI简短输出/退出码和文件检查结果保存到本人可读的全新0600私人日志；原始程序/设置/资源/回执仍在管理员私人目录。日志不覆盖，位置仅记在忽略目录。日志存在或某项检查为0均不能单独代表整个采集成功。

实际离线验证：`.venv/bin/python -B -`的文件系统复现4项通过，分别证明0750父目录预留前拒绝、新0700子目录接受且原权限不变、已有不合格目录不变、链接拒绝；没有SDK/USB导入或相机操作。`.venv/bin/python -B -m unittest research.tests.test_capturecamera -v`：19项自制SDK测试通过。`/bin/zsh -n`检查修正命令通过；另以自制printf在临时目录验证真实shell的0600新日志及二次运行拒绝覆盖，通过。运行代码、依赖、源锁和指纹未改，不重复无关全套回归。

当前仍待本人执行修正后的完整命令并读取真实结果，不能记作备份或D4成功。允许此次修正后的首次设备尝试以明确设备前拒绝为依据，不适用于未知或已进入设备流程的失败；后者仍停止并保留现场。后续电量在终端重新取得，不复用首次98%声明。

## 实际尝试：NEEDS_REVIEW_UNKNOWN与主机输出上限修正

2026-10-23本人报告修正后的命令已结束。读取本人0600结果日志确认：原capturecamera退出1，NEEDS_REVIEW/ValueError，camera_session_may_have_started:true、receipt_saved:true；captureevidence退出1，NEEDS_REVIEW_UNKNOWN/MATCHED_FAILURE，8条日志、0份材料。失败回执保存与本次失败匹配，但不是采集或退出成功。没有完整内部备份；从此停止设备命令，不重采、不认证、不运行机内诊断、不复位或自行取电池。

sudo -n检查仍要求本人终端认证，不能直接读取管理员私人目录。本任务终端没有输出，因此另备仅检查既有主机文件的命令：使用原Reader/receipt检查并导出固定事件名/操作名、阶段、计数及清理结果，不输出身份、路径、上下文或原始程序。该命令不构造NativeOps、不导入USB SDK或触碰设备，不是旧diagnose；待本人执行并读取新0600结果。所有原始失败作业、回执、脚本和日志均保留。

独立的被动主机复现已确认一个问题：同一固定ioreg查询在原8MiB上限触发Host command output exceeded bound；在明确32MiB上限的测量中返回19,340,104字节。没有保存完整系统登记内容，没有导入SDK或发送相机协议。本次8条实际事件尚未取得，故这只是与早期ValueError相容的可复现电脑问题，不能独自证明原调用具体失败点，更不能把NEEDS_REVIEW_UNKNOWN改成成功或自动解锁设备重试。

[capturemac](../lutphoto/capturemac.py)只为固定ioreg命令设置32MiB限额；其他主机命令仍使用原8MiB，白名单/非强制卸载/20秒期限/原生所有权、设备身份、协议和固件指纹不改。测试SDK夹具仅补接已有limit参数，仍检查其他命令的原限额。两个新增测试核对专用限额不能扩展到其他命令，以及真实自制子进程9MiB/32MiB通过、32MiB+1拒绝、原8MiB+1仍拒绝。没有增加设备重试、恢复或后端覆盖。

修正后只运行media中的ioreg/diskutil元数据查询：唯一普通MSC目标与两组相机磁盘检查通过，_runtime被断言不得调用且没有USB SDK导入。该查询没有卸载磁盘、打开接口或执行相机协议；普通登记存在也不证明机身功能或恢复。主机修正通过不代替本次事故日志与真实首采。

实际最终验证命令：

```sh
.venv/bin/python -B -m unittest discover -s research/tests -p test_capturemac.py -v
.venv/bin/python -B -m unittest research.tests.test_capturecamera research.tests.test_captureexecution -v
.venv/bin/python -B -m unittest discover -s research/tests -v
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v
.venv/bin/python -B -m macfl23 check
git diff --check
```

主机51项、相机入口/装配43项专项通过；研究990、旧Mac39、上游8合计1037项回归通过，固定源码/资产check通过。第一次专项命令误列不存在的test_captureevidence模块，43项实际测试通过但加载错误使该命令退出1；更正为上列有效模块后退出0，不将首次失败写成通过。原读取/设置/资源/worker、旧安装器、依赖与固定锁未改。当前未重新运行设备流程，真实成功、完整程序身份/材料及正常退出仍未证。

## 已有日志核对完成与下一次单独读取

本人已在其终端完成仅检查既有主机文件的命令，读取新0600结果，取得全部8条原事件：CAPTURE_CONTEXT、CAPTURE_LOCKS_HELD、OWNER_FLOW_BOUND、INTENT normal-before、HOST_INTENT INVENTORY、HOST_ACK INVENTORY、HOST_INTENT MEDIA、NEEDS_REVIEW。没有UNMOUNT、OPEN_HANDLE或后续认证事件。检查仍为NEEDS_REVIEW_UNKNOWN/MATCHED_FAILURE，未篡改原事件或补ACK。

原检查点计数：handles_opened/closed、identity_queries/raw_calls/bytes、authentication_raw_calls/bytes、wire_bytes、payload_bytes、requests、total_bytes均0；authentication_phase=NOT_STARTED、transition_started=false、stage=C0。原回执的global_lease/job_store/signal_handlers均CONFIRMED，owners=NOT_ACQUIRED。由此确认本次停于主机MEDIA查询，在磁盘卸载/接口打开/身份查询/服务认证/内部读取之前；没有需补做的服务退出，也未执行固件更新或程序/设置写入。真实SDK初始库存有ACK，不等于相机协议通信或D4通过。

同环境主机登记超原上限已独立复现，修正后被动MEDIA检查通过；原事件没有异常原文或瞬时登记原文，不声称保留了该次完整系统输出。原失败与当前主机复现吻合，允许在同一已授权只读范围内准备全新作业；不会将旧NEEDS_REVIEW_UNKNOWN转成成功，不允许续跑旧作业或重放旧命令。该判断仅适用于上述明确0协议及资源释放的本次证据，不作未知失败的普遍重试规则。

另备全新单次入口，仍先本人终端认证、即时实际电量、私人父目录及原电脑/身份/程序检查，然后只调用原capturecamera.main一次、原captureevidence文件核对。自动启一个独立-S子进程读取该次现有主机文件，保存固定阶段/计数及最多48条事件摘要，不带身份/路径/原始程序，避免下一次错误还需单独认证导出；它不导入USB SDK或新增相机操作。原采集退出码非0时，检查或导出成功不能把最终退出改为0。

旧脚本、作业、回执及各次结果保留；新作业/回执/日志全新，shell继续umask077/noclobber，现有日志拒绝覆盖。新入口/读文件子进程已在-S普通用户上下文验证导入和设备前拒绝，AST确认仅一次采集调用、原私人父目录函数不变、无修改/恢复API，zsh语法通过。运行代码自1037项通过后没有新变化，未重复全套测试。新入口尚未执行，D4仍未完成；下一次真实结果续记本轮。


## 最新实际调用：身份查询USBError，停止设备命令

2026-10-23本人报告命令已结束，之后确认相机仍显示正常连接；没有取得明确的存取灯状态。本人观察接线后电量不下降，记录为本人观察，不推断所有阶段持续供电、实际电量或恢复保证。本次及下文离线分析没有再次向相机发送命令。

读取现有本人可读0600日志及自动脱敏导出：原CLI退出1，NEEDS_REVIEW/USBError、camera_session_may_have_started:true、receipt_saved:true；文件检查退出1，NEEDS_REVIEW_UNKNOWN/MATCHED_FAILURE、41事件、0材料。EXISTING_RECORD_EXPORT_EXIT_CODE=0仅说明已有主机文件导出完成，不能覆盖前两项失败。所有原始作业/回执/检查点/日志保留。

与此前8事件失败不同，最新真实日志有两个UNMOUNT及OPEN_HANDLE、DESCRIPTOR、KERNEL_ACTIVE、DETACH_KERNEL、CLAIM_INTERFACE的ACK；第36项为NORMAL_IDENTITY_QUERY意图，无成功ACK，随后DISPOSE_RESOURCES意图/ACK、HANDLE_CLOSE_CONFIRMED和NEEDS_REVIEW。计数identity_queries=1、identity_raw_calls=13、identity_bytes=8451；认证调用/字节均0、NOT_STARTED，transition_started=false，材料请求/字节均0。尚未触发服务认证、内部程序/设置/资源读取或更新/持久化写入；完整程序指纹未取得。材料通道wire_bytes:0不表示身份查询没有真实USB通信。

回执global_lease/job_store/owners/signal_handlers均CONFIRMED，仅描述本地处置；未知分支不会显式RELEASE_INTERFACE/ATTACH_KERNEL。SDK处置可能隐式释放接口，不能由此推断内核重新附着、磁盘重新挂载或完整机身可用性。屏幕正常是本人观察，不能补成上述软件/设备验收。当前不重采、认证、清端点、REQUEST SENSE、复位、运行机内模块或安排拔线/重启/取电池，不准备新的设备命令。

### 固定源码对照与计数不能证明的内容

以原v2.1审计锁核验完整归档和成员，静态读取QAQLeonard所固定的ma1co MSC/Sony代码，不导入或执行归档源码。AST断言Sony外部命令拼装、GetModelInfo=(1,1)、16字节头、8192字节发送/接收默认值和序列号十六进制编码，与当前capturemsc一致；未发现这些报文参数的差异。对照仅涉及身份查询，不能推广为所有设备协议已正确/实测通过。

来源：固定提交7e54d60b458847f1befa6cfd614fbf004b8b0b90的[型号查询和头封装](https://github.com/QAQLeonard/a7c2-fl23-research/blob/7e54d60b458847f1befa6cfd614fbf004b8b0b90/src/fl23/vendor/pmca/usb/sony.py#L271)、[MSC收发](https://github.com/QAQLeonard/a7c2-fl23-research/blob/7e54d60b458847f1befa6cfd614fbf004b8b0b90/src/fl23/vendor/pmca/usb/driver/generic/__init__.py#L103)及[USBError转换](https://github.com/QAQLeonard/a7c2-fl23-research/blob/7e54d60b458847f1befa6cfd614fbf004b8b0b90/src/fl23/vendor/pmca/usb/driver/generic/libusb.py#L77)。上游统一转换USBError后会清端点并继续读CSW，还可能sense/busy重试；当前有意在未知时停止，不据此复制恢复动作。

自制47字节INQUIRY时，在第13个回调尝试（第五事务的型号数据接收阶段）注入错误，得到8451已接受字节：5×31字节CBW + 4×13字节CSW + 5/47字节INQUIRY + 8192字节请求。失败的接收本身没有贡献接受字节，后续CSW/认证未执行。另一个自制SDK复现，在同一回调内的描述符复查就抛出USBError，实际bulk read少一次，检查点仍为13/8451。因此现有计数只能定位到尝试阶段，不能确定真实USBError来自描述符复查还是数据接收，更不能证明失败传输实际收到了0字节。

真实回执只有body/USBError，没有errno/backend_error_code或原异常；原对象已不存在，不能从现有日志恢复错误码，不能断言超时、stall、线材、权限或相机故障。离线复现使用的错误码与文本全为自制，不是实机错误码。本轮未找到足以放行重采的修复。

### 新增离线回归及下一步

[test_capturemsc](tests/test_capturemsc.py)增加3项：32/36/47/255字节INQUIRY；14个调用逐个注入错误后不继续/不重放；13调用/8451字节的型号接收错误。[test_captureexecution](tests/test_captureexecution.py)增加2项：上述接收错误贯穿原SDK装配/回执/独立检查器后仍为UNKNOWN、0认证/材料，仅SDK处置；描述符前置错误得到相同计数，证明不能过度定位。

实际命令`.venv/bin/python -B -m unittest research.tests.test_capturemsc research.tests.test_captureexecution -v`：退出0，42项通过，全部使用自制SDK/主机/材料，不初始化USB或执行相机命令。固定归档/成员核验与上述AST断言退出0，输出无身份/原始数据，未导入USB SDK。完整回归与最终文档检查结果随后追加。

下一步先开发并审阅有界、无身份/报文的失败步骤与errno/backend码记录，区分描述符复查、实际bulk调用、返回校验；诊断写入失败不得掩盖首错，旧记录严格兼容，UNKNOWN/非0/禁止重试不变。该诊断功能尚未实现，不补写旧作业或要求再跑一次取得错误码。先离线验证全部边界，再评估未知现场的结束及后续设备安排。N3/D4仍未完成，N4/D5/D6不前移。


### 最新最终回归与发布范围

```sh
.venv/bin/python -B -m unittest research.tests.test_capturemsc research.tests.test_captureexecution -v
.venv/bin/python -B -m unittest discover -s research/tests -v
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v
.venv/bin/python -B -m macfl23 check
git diff --check
```

专项42项退出0；最新完整研究995项（80.593秒）、旧Mac39项、上游8项均退出0，合计1042项；固定源码/资产check退出0。比本轮上一阶段1037项增加5项故障回归。所有测试均离线，不执行真实USB/相机命令；离线通过没有修复/补证本次实机失败，也不解锁重采。

README、交付计划、D4电脑记录及首次采集/证据说明同步当前官方2.01、身份查询失败和UNKNOWN暂停，历史轮次证据不冒充最新状态。总计划维持四列；交接独立记录最新路径索引、事实、诊断缺口及下一动作。公开候选只含本轮源码/自制回归/脱敏说明，排除README/DELIVERY原有安全调查插入段、plan原有本地附录及4份未跟踪专项分析；这些既有内容保留在工作区。原始作业、回执、材料、个人路径和日志仍私有，不进入提交。实际提交/推送以Git记录为准，仅使用lut-photo/main，不推origin、不强推。

最终公开范围检查：14个候选文件、171个本地链接目标、Markdown格式/围栏、Python AST及个人路径检查通过；测试夹具中既有OWN-FAKE为固定自制路径。README/DELIVERY原有各4行、plan原有82行不入候选且工作区保留，4份专项分析逐字节不变；旧安装器/依赖/固定锁无差异。git diff --check退出0。未检查真实机身功能/挂载恢复或重新发起采集。
