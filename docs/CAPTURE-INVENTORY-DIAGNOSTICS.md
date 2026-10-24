# USB枚举失败：有限定位与回执兼容

2026-10-24，第七十轮。本人已确认相机断开，本轮仅修改电脑端代码并使用已有自制SDK/材料验证，没有枚举、打开、认证或操作真实相机。第六十九轮真实结果仍为6事件、INVENTORY意图无ACK、ValueError、0材料；**旧记录没有保存具体内部步骤，新代码不能补回其原因，也不能宣称已修复。**

后续[第七十一轮实测](../research/LUT链路调查记录-第七十一轮.md)取得首个新增宿主诊断：inventory_call:1、KEY_VALIDATE、invalid_key_fields:[BUS]、ValueError，两个数值错误码均null，record_error_type:null。仍为6事件/0材料、0已打开句柄/身份/认证；原始bus值未记录，只能确认它未满足原精确整数且大于0的条件，不能据此断言具体值或回填第六十九轮原因。该轮停止设备命令并转入离线核对，没有在当轮修改门槛。

[第七十二轮固定源码审计与修正](CAPTURE-BUS-COMPATIBILITY.md)证明Darwin总线从0编号，现将四处有效域统一为精确整数0–255，0保留原值参与原严格比较；None/布尔/字符串/越界和不明确端口仍拒绝。上述第七十一轮诊断按当时旧规则作为历史失败保留，不重新解释成成功，真实原始值仍未知。本轮回归及新准备均离线通过，本人选择稍后采集。

## 新增记录范围

沿用原两次PID枚举、固定位置字段读取、原_Key校验和单次对象处置。只在原失败路径保存首个有限诊断；不增加枚举、属性读取、端点查询、清除、sense、认证、重试或恢复。未修改机型/指纹、位置范围、唯一机身、协议字节、期限、全局锁或旧安装器。

新调用回执为`a7c2-capture-terminal-receipt/3`，保留身份诊断并增加`host_diagnostics`。成功或没有记录到枚举步骤失败时为空列表；至多一个失败项，字段如下：

| 字段 | 范围与限制 |
| --- | --- |
| inventory_call | 原宿主步骤中第几次INVENTORY调用，精确整数1–2048；不是USB传输次数 |
| failure | `a7c2-host-inventory-failure/1`，operation固定INVENTORY，boundary取下表有限值 |
| invalid_key_fields | 仅在KEY_VALIDATE失败时报告缓存字段中未通过原条件的名称，按PID/BUS/PORTS/ADDRESS固定顺序；不输出值、长度、设备列表或位置 |
| reason_type | 至多64字符的错误类型，不读取异常文本、repr或原因链原文 |
| errno / backend_error_code | 仅带符号32位的精确整数；缺失、读取失败、布尔/浮点/字符串/超范围为null，不转换 |
| record_error_type | 构建诊断失败时failure为null，保存有限错误类型；原正文首错继续传播，不因此重复动作 |

| boundary | 原调用中的失败位置 |
| --- | --- |
| HOST_PRECHECK / HOST_INTENT | 原步骤前置检查或记录INVENTORY意图 |
| NATIVE_RUNTIME | 既有SDK加载/运行上下文；不据此声称已枚举设备 |
| SDK_FIND_NORMAL / SDK_FIND_SERVICE | 既有正常/服务PID枚举或迭代；不保证打开或向相机发过协议命令 |
| INVENTORY_LIMIT | 原16个枚举对象上限拒绝；不放宽或截断接受 |
| KEY_VENDOR_READ / KEY_VENDOR_CHECK | 读取厂商字段或原Sony检查 |
| KEY_PID_READ / KEY_BUS_READ / KEY_PORTS_READ / KEY_ADDRESS_READ | 原位置属性读取；端口项包含原tuple转换，不重新读取属性 |
| KEY_VALIDATE | 原_Key拒绝；只从已缓存值判断哪些字段未通过原条件，原拒绝继续有效 |
| ENUMERATION_DISPOSE | 原枚举对象单次处置或其完成值检查；首错后的原抑制清理不会覆盖首错 |
| HOST_POSTCHECK / HOST_ACK | 原枚举已返回后的检查或日志ACK记录；ACK记录报错可能发生在记录之前或之后 |
| CALLBACK | 未取得更具体内部位置的既有回调边界，例如原假SDK；不能解释为真实SDK动作 |

没有覆盖INVENTORY成功返回后的唯一机身检查、被动等待语义拒绝、MEDIA、OPEN_HANDLE、身份查询、认证或材料读取。对应原逻辑和其他错误保留；空列表不是枚举或相机验证成功。实例状态标记不持有SDK对象或额外读取设备属性。

## 旧记录与只读检查

检查命令未变，仅读取本人已有私人文件，不接触USB：

```sh
.venv/bin/python -S -B -m lutphoto.captureevidence inspect \
  --directory "/path/to/owner-capture/job" \
  --receipt "/path/to/owner-capture/terminal.private.json"
```

管理员所有的文件需要同一所有者上下文；本轮没有读取管理员原作业或改权限。新检查输出为`a7c2-readonly-capture-evidence-inspection/3`。严格只读接受回执/1原字段、/2原字段加身份诊断、/3另加宿主诊断；不升级、补字段或重写旧文件。旧/1、/2的host_diagnostics输出为null，新/3无已记录失败为[]。旧检查器不能读取新回执，不可删字段或修改schema伪装兼容。

有效宿主诊断须与同一作业/检查点绑定，并核对INVENTORY意图/ACK计数及失败边界；首个枚举失败还须与零句柄/身份/认证/传输一致。意图或ACK记录自身报错时，允许原事件已保存或尚未保存两种结果，但不补写事件。缺检查点记录HOST_DIAGNOSTIC_UNBOUND、不输出诊断，保持信息不足/UNKNOWN；矛盾记录HOST_DIAGNOSTIC_DIFFERS并隐藏诊断，仍非成功。

本页只是未来失败的主机位置记录，不认证错误来源或硬件事实。错误数字不自动证明端口/线材/相机故障。NEEDS_REVIEW、原非0退出和所有写入/恢复/续跑未证标志继续保留；正常画面、灯灭或人工断开不能替代材料/退出/恢复验收。

## 本轮验证与下一步

使用[已有自制SDK](../research/tests/native_sdk_fixture.py)和[枚举专项测试](../research/tests/test_captureinventory.py)，验证相同6事件的不同内部失败、缓存字段单次读取、原处置次数、记录前后错误、后续枚举调用绑定、旧回执/1和/2、记录构建失败、缺检查点和伪造诊断拒绝。没有调用真实USB SDK。

第七十一轮已完成[执行结果核对](CAPTURE-TRIAL-REVIEW.md#第七十一轮新单次准备)，仍不等于完整材料、身份或传输通过。第七十二轮修正及[新单次准备](CAPTURE-TRIAL-REVIEW.md#第七十二轮修正后准备)已离线通过，尚未新实测；所有第六十七/六十九/七十一轮旧命令均已使用且冻结过时，禁止再运行。诊断实现见[第七十轮](../research/LUT链路调查记录-第七十轮.md)，当前动作见[交接](../research/HANDOFF.md)。
