# 有限服务身份读取：只读一份快照

第78轮完成普通侧首次START的限定PIPE兼容、供电声明和结果`/2`，仅离线验证，尚未执行新版本真机。第77轮旧版本在NORMAL_START边界遇到PIPE(-9/32)、44事件/0快照；该失败保持原样，不能倒推已认证成功。第67/69/71/77轮已用命令禁止重跑，第72轮准备停用。最新接续见[HANDOFF](../research/HANDOFF.md)。

## 范围与供电声明

入口仅接受本人ILCE-7CM2、声明索尼官方原厂2.01；管理员认证在本机完成。按本人持续保持高电量及USB供电的约定，后续准备使用`--maintained-power`，不再询问或输入电量。它记录为`declared.power.mode=maintained-high-battery-usb`、`battery_percent=null`、`automatically_measured=false`，不是设备测量或虚构百分比。

API也可显式传入`maintained_power=True`并省略`battery_percent`。原`--battery-percent`仍支持50–100整数，二者互斥且必须选择一种，省略、真假值冒充整数、混用均在设备前拒绝。旧完整采集及安装器当前契约不变；后续接完整采集时再接入明确供电声明，不能为复用旧入口硬填电量。

本入口不读取AP/CP，因此`program_fingerprints_verified`始终false，不能凭版本或供电声明导入LUT或开启写入。完整采集的固定完整程序指纹门槛保留。

执行顺序：

1. 设备访问前核对固定归档/密钥、宿主环境、新私有作业及独立回执。
2. 取得全局排他锁，确认唯一设备与稳定磁盘，正常卸载并接管接口。
3. 有时限地读取标准USB型号；型号不是唯一机身身份，不发送旧MSC型号/序列查询。
4. 普通侧首次START后完成全部认证，关闭句柄，在同一物理端口等待服务设备，再完成服务侧START及认证。
5. 只读取一份RAM设置快照，解析两份BK4图像，从第一份四字节属性取得身份摘要。原快照属于私人资料。
6. 健康状态下最多发送一次停止服务、关闭服务句柄，被动确认普通USB在原端口稳定重现；没有第三句柄、重新认证或返回序列查询。
7. 关闭作业、释放租约、恢复信号处理，保存独立回执并输出简短结果。

不读取完整程序、保存态快照或68份资源，不加载机内模块、写程序、保存设置或处理WBI。服务认证改变临时连接状态。全程120秒合作式期限、协议调用最多5秒、单段等待20秒；SDK/文件系统管理可能阻塞，取消不强杀。

## 首次START的有限兼容

仅普通设备的第一个START，且**错误来自实际SDK控制调用，类型恰为SDK USBError、backend_error_code精确整数-9、errno精确整数32**时，记录暂定PIPE并继续原认证。普通侧控制请求只发送一次，没有重试、清端点、复位或重置unknown标志。errno缺失、浮点码、其他异常/子类、其他错误码均拒绝。

这不是成功ACK：回执`normal_start.control_status=PIPE`，日志写`NORMAL_START_PIPE`，没有`ACK/NORMAL_START`。只有随后三轮挑战/证明以及最终认证响应均通过，才确认`normal_authenticated`并解除该暂定状态；失败、超时、取消、日志失败仍停止，未完成认证的PIPE保持结果未知。

描述符/就绪检查在控制异常捕获范围之外。服务侧START、STOP和认证读写均沿用严格失败停止规则。完整响应内容拒绝且会话健康时，仍允许原有的一次停止；任何结果都不会自动串接全材料采集。

诊断将`normal_start.boundary`分为PRECHECK、CONTROL、POSTCHECK、COMPLETE，另以NOT_ATTEMPTED、UNKNOWN、ACK、PIPE记录控制结果。失败项的`start_boundary`只在NORMAL_START阶段填写；`last_host_operation`仍只是最近记录的宿主操作。CONTROL也只是SDK调用边界，不证明USB内部状态阶段或故障根因。

来源与局限见[第78轮](../research/LUT链路调查记录-第七十八轮.md)。相关固定研究脚本的START处理只作为行为参考，不把其作者测试视为本项目2.01真机证据。

## CLI与结果版本

查看帮助不加载SDK或访问USB：

```sh
.venv/bin/python -S -B -m lutphoto.captureprobe --help
```

以下为真实参数说明，实际运行前仍需新建并审阅一次性准备。父目录须存在、属于运行者且为私有目录；作业和外部回执须全新：

```sh
sudo .venv/bin/python -u -B -m lutphoto.captureprobe \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory /path/to/private/probe-002 \
  --receipt /path/to/private/probe-002-terminal.private.json \
  --model ILCE-7CM2 --firmware 2.01 --maintained-power
```

没有`--resources`、后端替换、强制、重试或续跑选项。默认最多一份快照，不是完整内部备份。标准USB型号和服务快照身份不能独立证明物理图像角色、新鲜度或返回机身身份。

| 输出 | 意义 |
| --- | --- |
| 0 / `PROBE_COMPLETE` | 快照身份已解析、停止确认、同端口普通USB重现及本地交付完成；仅此有限范围 |
| 1 / `NEEDS_REVIEW` | 读取、认证、停止、返回或本地收尾不完整；保留记录，不重跑 |
| 1 / `REFUSED_BEFORE_DEVICE` | 声明、来源、环境或输出前置拒绝 |
| 1 / `PROBE_OR_DELIVERY_UNCONFIRMED` | 运行或回执保存/关闭未确认，可能有空或部分回执 |
| 1 / `OUTPUT_UNCONFIRMED` | 终端输出不完整，已有回执不代表CLI成功 |
| 2 / `INVALID_ARGUMENTS` | 参数不匹配，没有进入来源/设备处理 |

新私有回执schema为`a7c2-service-probe-result/2`，stdout为`a7c2-service-probe-cli-result/2`。变化是`declared.power`、`normal_start`及失败项`start_boundary`；stdout仍不输出身份、路径或材料摘要。`normal_identity_rechecked`、`program_fingerprints_verified`、`complete_backup`、恢复/写入/续跑标志保持false。

旧第77轮`/1`回执及私有读取器保持原字节；不能改schema追认兼容成功。准备下一次操作时必须配套新的`/2`摘要读取器和源码冻结。旧`captureevidence inspect`继续拒绝probe结果，当前没有通用probe证据图检查器。回执或摘要不是签名/硬件证明，仍需按范围核对原调用、日志和快照。

R3通过后先审阅完整采集的服务优先接入，再安排R4全材料和有界复读。完整备份、LUT导入/恢复和真实JPEG颜色仍在D4–D6验收。
