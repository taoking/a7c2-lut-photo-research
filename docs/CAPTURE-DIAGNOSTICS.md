# 身份查询失败：有界诊断与旧回执兼容

第六十八轮在[既有固定身份查询](../lutphoto/capturemsc.py)、[所有者回调](../lutphoto/capturemac.py)和[私人调用回执](CAPTURE-EVIDENCE.md)中记录首个IO/回调失败；不增加查询、端点清除、重试、认证或机内诊断动作。仅通过自制SDK验证，尚未取得真实新诊断正例。第六十七轮实机失败的步骤/错误码仍缺失，不能事后找回或补写。

10月24日[第六十九轮新作业](../research/LUT链路调查记录-第六十九轮.md)在INVENTORY意图无ACK的边界发生ValueError，身份查询尚未开始，因此新回执identity_diagnostics为空；6事件/0材料并未验证本页身份IO诊断。该边界具体原因未记录，下一步先离线补有限枚举定位，不重采。

## 记录在哪里

新回执为`a7c2-capture-terminal-receipt/2`，增加`identity_diagnostics`，最多一个失败项；成功时为空列表。作业检查点仍为原来的`a7c2-native-capture-checkpoint/1`，事件词汇与哈希链不改，不新增作业文件或第二份备份。回执仍经原入口的私人文件排他预留、写入/同步/完整读回、关闭流程传递。

只读检查命令不变：

```sh
.venv/bin/python -S -B -m lutphoto.captureevidence inspect \
  --directory "/path/to/owner-capture/job" \
  --receipt "/path/to/owner-capture/terminal.private.json"
```

管理员所有的记录仍需相同所有者上下文，不绕过权限；这里仅说明既有入口，本轮未重新读取管理员目录。检查器输出版本为`a7c2-readonly-capture-evidence-inspection/2`，只在回执/绑定/诊断与流量一致时返回有界诊断。矛盾或拒绝时不输出该诊断；缺少检查点时记录IDENTITY_DIAGNOSTIC_UNBOUND、不输出诊断，保留信息不足/未知，不把证据缺失判为矛盾。分类和非0退出仍保留。

新检查器严格接受旧回执`/1`的原字段，`identity_diagnostics:null`表示没有可用的新诊断；不会改写旧回执/目录。旧回执夹带新字段、新回执缺字段或未知版本均拒绝。旧检查器不识别新回执，需更新电脑端工具，不能删字段/改版本伪装成旧记录。

## 能定位到哪里

每项包括`owner`（normal-initial或normal-return）、`failure`及`record_error_type`。failure为`a7c2-msc-identity-failure/1`：

| 字段 | 范围与解释 |
| --- | --- |
| transaction / part | 固定5个事务，CBW/DATA/CSW；不接受任意命令 |
| call_number / direction / requested_bytes | 固定14个回调槽、read/write及允许长度，彼此交叉检查；第三事务INQUIRY为32–255字节 |
| callback_attempted | 是否进入所有者回调；即使为true，也不保证实际bulk传输已开始 |
| boundary | 下表允许的失败边界；只描述主机调用位置 |
| returned_bytes | 仅在已返回且可安全计量时记录0–8192整数；否则null，不从异常猜测部分传输量 |
| accepted_bytes | 本次查询已通过校验/预算的累计字节，不是USB线上实际流量；返回但未接受的字节不计入 |
| reason_type | 至多64字符的错误类型；不输出异常文本、repr、路径或原因链原文 |
| errno / backend_error_code | 仅精确整数、带符号32位范围；缺失、属性读取异常、布尔/浮点/字符串或超范围均为null，不转换或猜测 |

| boundary | 含义 |
| --- | --- |
| QUERY_PRECHECK | 预算/期限检查；尚未尝试该回调 |
| OWNER_PRECHECK | 所有者状态/期限检查；尚未进入对应SDK读写 |
| DESCRIPTOR_QUERY | SDK描述符复查报错 |
| DESCRIPTOR_CHECK | 返回描述符不符合既有固定要求 |
| SDK_BULK_READ / SDK_BULK_WRITE | 错误从既有SDK read/write方法返回；不能证明请求已到达相机 |
| OWNER_POSTCHECK | SDK方法已返回，所有者后置检查失败 |
| RESULT_VALIDATION / ACCOUNTING | 原返回值长度/类型校验，或接受字节的预算检查失败 |
| CALLBACK | 无更具体绑定时的回调边界，例如纯查询层的自制测试；不据此声称SDK已调用 |

本次功能只覆盖身份查询的IO与回调边界；CSW内容解释、型号解码、主机卸载、服务认证、材料读取或持久化写入并非新增诊断范围。新回执空列表不等于查询成功。数字码不自动映射为线材/相机故障，也不授予清端点、sense或重试许可。

## 失败与隐私边界

首个记录只构建一次，后续异常不覆盖、不补采。诊断构建失败时，failure为null、record_error_type记录有限类型，原USB/其他失败继续是正文首错。回执传递或stdout失败时，已知首错仍作为reason_type，传递错误列在secondary_error_types；阶段仍为CAPTURE_OR_DELIVERY_UNCONFIRMED或OUTPUT_UNCONFIRMED、退出1，不因此复用/覆盖作业。

所有者处置、关闭确认及正常屏幕依然不证明驱动重新附着、磁盘挂载或相机恢复；已有UNKNOWN不因诊断增加而变为成功。新诊断未提供恢复或续跑功能，不调用旧安装器的`diagnose`。原始回执、材料、身份及私人日志不公开。

相关离线测试为[元数据边界](../research/tests/test_capturediagnostics.py)、[原装配与回执](../research/tests/test_captureexecution.py)及[传递/输出故障](../research/tests/test_capturecamera.py)。命令、真实结果与剩余任务见[第六十八轮](../research/LUT链路调查记录-第六十八轮.md)、[交接](../research/HANDOFF.md)。
