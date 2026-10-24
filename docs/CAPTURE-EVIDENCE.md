# 内部采集检查点与调用回执

第五十六轮交付[内部装配](../lutphoto/captureexecution.py)和[独立检查器](../lutphoto/captureevidence.py)，复用NativeOps/Host、所有权核心、固定协议、Store与只读图检查。第五十七轮交付[公开首次采集入口](CAPTURE-FIRST-USE.md)的自制SDK离线验收；[第六十七轮](../research/LUT链路调查记录-第六十七轮.md)实际打开接口后，身份查询发生USBError，0材料，尚无完整首采正例。当前暂停设备命令，保留NEEDS_REVIEW_UNKNOWN；候选模块的旧capture仍拒绝，源码review不能授权或启用设备操作。

10月24日[第六十九轮新尝试](../research/LUT链路调查记录-第六十九轮.md)在INVENTORY意图后无ACK，ValueError/6事件/0材料，身份与认证尚未开始；回执`/2`由管理员上下文自动文件检查得NEEDS_REVIEW_UNKNOWN/MATCHED_FAILURE，identity_diagnostics为空。原采集/检查退出1，摘要导出0不代表成功；旧第六十七轮记录不改，下一步先离线补枚举定位。

随后[第七十一轮新作业](../research/LUT链路调查记录-第七十一轮.md)的回执/3由自动文件检查得到host_diagnostics:KEY_VALIDATE/BUS，仍NEEDS_REVIEW_UNKNOWN/MATCHED_FAILURE、6事件/0材料、0身份/认证。该次新增定位有效绑定，原始总线值未保存，不能补写旧第六十七/六十九轮原因，也不提高材料、物理协议、原生执行或恢复未证标志。当前停止设备命令，先离线核对字段来源与取值域。

## 两份记录的边界

| 记录 | 生成时点与内容 | 不能证明 |
| --- | --- | --- |
| `native-checkpoint.private.json` | 三句柄关闭后、作业锁/全局租约内排他写入；schema `a7c2-native-capture-checkpoint/1`，绑定随机作业号、声明版本/电量/资源范围、来源、初始/返回MSC观察、材料/流量/日志 | `MATERIALS_OBSERVED`只到材料观察截止点，作业关闭、租约释放、信号还原仍未完成 |
| 调用回执 | 全部收尾尝试和信号还原后，最后检查取消；当前schema `a7c2-capture-terminal-receipt/3`增加有限宿主枚举诊断，保留`/2`身份诊断及同一context/检查点绑定、作用域结果、主/次错误类型；旧`/1`与`/2`严格只读接受 | 不是签名，不能保证进程突然死亡或stdout失败时留下完整记录；缺回执不推断成功 |

内部函数返回回执对象，不在作业锁外重开目录补写/覆盖。公开入口要求独立的全新私有回执文件，在NativeOps构造前排他预留并持有锁，内部收尾之后再写入/同步/读回/关闭；stdout只给简短结果。文件或stdout失败均非成功；已有完整回执也不能单独证明整个CLI正常退出，见[首次采集说明](CAPTURE-FIRST-USE.md)。身份摘要/材料指纹和作业关联都须私有保存，哈希不等于匿名化。

类型分为 `native` 和 `self-made-sdk`，后者成功只能为 `EXERCISE_COMPLETE`。公开入口的原生装配固定选择native，没有公共后端/版本覆盖参数。记录声明native也不是硬件认证；目录所有者可以重写一致记录。本轮无真实SDK或原厂程序/BK4/资源正例。

## 前置与结束判定

1. 来源/新输出/依赖、声明原厂2.01及整数电量50–100在NativeOps构造之前检查；实际完整AP/CP仍在读取后匹配。声明版本/电量不是自动测量，输出父目录所有者须匹配运行上下文，不自动提权/改所有者或设置免密sudo。
2. 信号早于全局租约/作业，晚于所有收尾；SDK未返回时保留对象/作业/锁，不能抢占、强杀、复位或超时解锁。协议未知或取消不发新命令、不补ACK/stop。健康已知且未取消的内容拒绝，仍只允许一次已有固定退出。
3. 保留正文首个失败，随后记录本地所有者、Store、租约、处理器的次要失败及有界显式原因链，仅类型、最多64条，无异常原文/私人路径。Store、Reader及材料Sink均先失效、单次关闭，不重试结果不明的关闭；前两者一项失败后仍尝试其余描述符。
4. 只有材料/复读/守卫/新返回身份、三个关闭确认、检查点持久化、全部作用域关闭及最后取消检查均通过，才允许完整成功。报告后取消、作业/租约/还原失败均为 `NEEDS_REVIEW`，纯 `exit_code` 检查返回1。关闭确认不是物理恢复证明。

服务认证/选读取路径会改变临时会话状态，未来采集仍是设备操作。范围不上传/删除、不加载机内模块、不写程序/保存设置、不WBI；未知保留现场，本页不授权拔线、取电池、重启、恢复或续跑。

## 身份查询失败的诊断限制

`identity_raw_calls`计数在调用所有者回调之前增加；该回调还会复查描述符，然后才调用SDK读写。因此计数不能单独证明相应bulk传输已经开始。第六十七轮的13次调用/8451已接受字节，可用自制47字节INQUIRY复现为型号数据接收失败，也可复现为接收前描述符复查失败；两种情况均保持UNKNOWN、0认证/材料，不发送后续CSW、认证、清除端点或重试。

第六十七轮旧回执只保留错误类型，没有errno/backend_error_code或每次SDK动作的独立轨迹，不能回溯判定当次属于超时或端点错误。第六十八轮新增[有界诊断](CAPTURE-DIAGNOSTICS.md)，仅为未来失败记录固定边界/有限数字码，未进行新实采或补写旧记录。`wire_bytes:0`只描述材料通道，不代表身份查询没有USB通信；本地`owners:CONFIRMED`/HANDLE_CLOSE_CONFIRMED表示SDK处置完成，也不证明内核驱动重新附着、磁盘挂载或机身功能恢复；本页不增加重试许可。

## 已有记录的只读检查

输入须在仓库外，目录0700、文件0600且所属当前运行者，回执也须满足私人普通文件要求。不接受链接、硬链接、特殊/共享文件、持有作业锁的目录或持有回执独占锁的文件（ACTIVE_RECEIPT）。占位路径替换为本人明确提供的位置：

```sh
.venv/bin/python -S -B -m lutphoto.captureevidence inspect \
  --directory "/path/to/owner-capture/job" \
  --receipt "/path/to/owner-capture/terminal.private.json"
```

省略 `--receipt` 可以仅查材料，即使材料一致也返回 `NEEDS_REVIEW_TERMINAL_MISSING`/退出1。命令不启动采集，不搜索、修复、创建或写入，无需归档、SDK、相机或共享库。输出仅有限状态/计数/问题码，不复制身份、作业号、材料指纹或路径。

| 结果 | 含义 | 退出码 |
| --- | --- | --- |
| `CONSISTENT_CAPTURE_RECORDS` / `CONSISTENT_EXERCISE_RECORDS` | 相应声明类型的材料与完整回执结构/绑定一致；不等于实机认证或写入许可 | 0 |
| `NEEDS_REVIEW_TERMINAL_MISSING` / `NEEDS_REVIEW_TERMINAL_FAILURE` | 材料可一致，但缺回执或收尾失败 | 1 |
| `NEEDS_REVIEW_INCOMPLETE` / `NEEDS_REVIEW_UNKNOWN` | 材料未完整或有未确认动作/结果 | 1 |
| `EVIDENCE_INCONSISTENT` / `REFUSED` | 结构/哈希/语义矛盾，或输入不安全、使用中、不可读、超限、检查关闭未确认 | 1 |

`material_evidence` 与 `terminal_evidence` 分别给出结果，不互补成功。严格检查完整字段/类型、作业/检查点绑定、6/74材料、流量、程序先于设置、四个快照/两次守卫位置、三所有者、两段被动等待和新MSC顺序；重新计算哈希链也不能掩盖这些语义错序。当前检查输出版本`/3`保留identity_diagnostics，另加[宿主枚举诊断](CAPTURE-INVENTORY-DIAGNOSTICS.md)。身份诊断在旧`/1`或未提供回执时为null，无已记录IO失败为[]；宿主诊断在旧`/1`、`/2`时为null。有效诊断还须与查询流量或枚举意图/ACK一致；矛盾或拒绝时隐藏，缺检查点分别标记IDENTITY_DIAGNOSTIC_UNBOUND/HOST_DIAGNOSTIC_UNBOUND并保留不足/未知。仍非成功，原四种模拟格式不被改名接受，原检查器不交叉升级。

读取边界沿用[既有检查器](CAPTURE-INSPECTION.md)：最多2048事件，单项/总量/期限受限，材料最多512MiB、检查点及外部回执各128KiB，读取前后核对身份/权限/元数据和目录项，atime不作不变保证；文件系统调用仍可能阻塞。不重验来源归档、程序策略或BK4/UXC格式；角色、外层、原子性、新鲜度、独立介质、原生执行、恢复、写入和续跑全部未证。

新增24项专项和四个实际自制子进程信号场景通过，命令/故障练习见[第五十六轮](../research/LUT链路调查记录-第五十六轮.md)。第五十七轮完成公开入口与传递/退出码离线收口；第六十七轮本人确认官方原厂2.01并授权只读采集，最新实际尝试尚未通过身份查询/认证。完整CSW/回显/排空/重枚举、同机材料及正常退出仍需独立验收，不能凭失败调用中的部分通信视为通过。卡副本不是内部备份；当前不要求读取移动盘或准备Docker/惠普电脑。见[交接](../research/HANDOFF.md)和[QAQLeonard/ma1co/ajalt致谢/许可](../ACKNOWLEDGEMENTS.md)。
