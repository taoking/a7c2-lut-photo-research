# 第六十八轮：身份查询失败的有界诊断

2026-10-23。延续第六十七轮的离线诊断任务；相机最新已知仍为NEEDS_REVIEW_UNKNOWN、0材料。本轮不运行相机/USB命令，不执行任何采集启动器，不更新或修改机身，不读取/改写管理员原始记录。第六十七轮已发布ba5029e，原始证据保持。

## 本轮范围与验收

- 开发固定身份查询IO阶段/描述符复查/SDK读写/返回校验及有界数字错误码，不记录异常文本、身份、路径、报文或密钥。
- 新私人回执明确版本；严格只读兼容旧回执，不回写旧作业，诊断不能增加成功或续跑许可。
- 使用自制SDK验证步骤区分、错误属性、记录失败、回执传递、未知停止及隐私；完成相关离线回归。
- 维护四列总计划、短交接及本轮证据；保留已有未提交分析，不发布私人资料。

诊断实现与离线验证完成，结果如下；没有真实新诊断或材料正例，不将新增功能视为原USBError已解决。


## 实现与兼容

新增capturediagnostics纯元数据模块，固定5事务/14个IO槽，不导入SDK或执行I/O。Query在既有调用前、回调失败、返回值检查/预算接受失败处记首次边界；Owner对既有描述符复查、SDK read/write和后置检查细分。单次记录、失败后不重试，不更改原始报文、协议/时间/字节预算、身份与指纹门槛。

只保存固定字段、允许的边界、精确整数长度/计数和有限错误类型；errno/backend_error_code只接收带符号32位精确整数，缺失/异常属性、布尔/浮点/字符串或超限为null。不调用str/repr、不读原因链原文、不保存身份/路径/报文/密钥。returned_bytes未知不补0，accepted_bytes仍是单次查询已通过校验的累计量，不推断线上部分传输。

新私人终态回执schema为a7c2-capture-terminal-receipt/2，最多一个identity_diagnostics失败项。检查点/1、作业文件、事件图与公共采集CLI参数不变，无额外材料副本。检查器输出/2，只读兼容旧终态/1的原字段，旧记录不修改/升级；旧版夹带新字段、新版缺字段或未知版本拒绝。诊断与角色/调用/接受字节不一致时EVIDENCE_INCONSISTENT，不输出该诊断、不改变非0。

构建记录出错时只保留record_error_type，failure为null，不再尝试记录；底层原错误仍首位。回执传递或stdout失败时，已知正文首错继续是reason_type，传递错误列secondary_error_types，阶段仍为传递/输出未确认、退出1。新诊断不覆盖CSW语义解码、型号解码、主机卸载、服务认证、材料或持久化写入；空列表不等于查询成功。细则见[诊断说明](../docs/CAPTURE-DIAGNOSTICS.md)。

## 真实现场收尾与边界

本人本轮先确认存取灯已熄灭，后来说明仍在USB模式、询问是否需要断开检查。以旧进程已结束、认证/程序写入未开始的记录及当前灯灭为依据，读取索尼ILCE-7CM2[官方普通断开说明](https://helpguide.sony.net/ilc/2360/v1/zh-cn/contents/0903_disconnect_pc.html)，指导Finder有卡图标时正常推出、推出受阻则停下不强制、灯保持熄灭后断开USB，无需关机或取电池。该页面说明Mac正常推出、无图标时可跳过及灯亮不可拔线；本轮没有执行主机弹出或设备命令。

本人随后反馈“相机一切正常”，记录为收到上述指导后的人工反馈，不补填冷启动/拍摄/回放/完整程序/服务退出或恢复验收，也不因此放行重采。第六十七轮原UNKNOWN/0材料保持；没有新相机命令、管理员认证、内部数据或真实新诊断。正常断开指导不是机内恢复、强制重启或追加安装许可。

## 实际测试命令与结果

```sh
.venv/bin/python -B -m unittest research.tests.test_capturediagnostics research.tests.test_captureexecution research.tests.test_capturecamera -v
.venv/bin/python -B -m unittest discover -s research/tests -v
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v
.venv/bin/python -B -m macfl23 check
.venv/bin/python -S -B -m lutphoto.captureevidence inspect --help
git diff --check
```

最终专项58项退出0；完整研究1008项（81.184秒）、旧Mac39项、上游8项均退出0，合计1055项；固定check和-S帮助退出0。新增13项测试，另外加强第六十七轮两种同计数故障的边界断言。自制故障覆盖数字码/异常属性、固定槽交叉验证、前置与返回校验/预算边界、记录构建失败、初始/返回查询、旧回执完整/未知兼容、篡改拒绝、回执部分写入和stdout失败保留首错。全部离线，不操作真实USB或执行机内模块。

过程中的首次模块列表命令包含旧test_capturemac的包导入，其内部裸模块导入导致加载错误，62项运行但退出1；改用discover后538项中出现两处新增测试自身问题：patch替换为函数却断言call_count，以及把固定private_report字段误当异常文本泄漏。修正为带签名Mock计数和具体自制秘密标记检查后，上列58项和完整1008项均通过。没有更改运行保护来消除测试失败，不把早期失败命令记作通过。

## 后续交接与发布

本轮不为取得错误码再跑设备，不复用旧作业/启动器，不上传原始回执/材料或私人位置。下一步先审阅后续受控只读方案及停止条件，需要设备阶段再取得实际版本/电量/连接/管理员认证；当前不准备新的相机命令。D4仍未完成，N4/D5/D6不前移。

维护总计划四列、交接独立文档和轮次索引。发布范围仅本轮代码、自制测试和脱敏说明；README/DELIVERY既有各4行、plan既有82行和4份未跟踪分析报告保留，不纳入提交。原固定锁、旧安装器/依赖与PRIVATE保持。实际Git提交/远端结果另核对，目标仅lut-photo/main，不推origin、不强推。


### 最终审阅补充与通过结果

审阅新增“身份失败后检查点写入失败”的组合故障，发现缺少检查点只表示诊断无法绑定，不能据此新造证据矛盾。检查器现标记IDENTITY_DIAGNOSTIC_UNBOUND、诊断输出null，保留原UNKNOWN/MATCHED_FAILURE和正文USBError；新增一项自制测试验证0认证、不追加读取。该改动后重新执行上列专项与完整研究命令，最终59项/1009项均退出0，完整研究用时80.979秒。旧Mac39和上游8不受该变更影响且已通过，最终合计1056项，比上轮增加14项；此前58/1008项为补充改动前结果，不替代最终结果。

额外实际检查：`.venv/bin/python -B -`的AST对照退出0，固定协议常量、Query.run、去除纯元数据part关键字后的事务白名单/顺序、整个NativeOps及Owner.close与本轮基线完全一致；旧安装器、依赖及固定锁无差异。`.venv/bin/python -S -B -`的新模块/前端导入检查退出0，未导入USB SDK。公开候选19个文件、181个本地链接及格式/AST/个人路径检查通过，README/DELIVERY/plan原有插入块排除、4份原报告哈希不变；git diff --check退出0。未执行任何相机命令，没有真实新诊断、内部备份或首采正例。
