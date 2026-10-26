# 第七十八轮：首次START限定兼容与持续供电声明

日期：2026-10-26。基线`c0fbd5f352d5bad14b9686add7877c48996d6a72`，开工工作区干净。本轮只做源码核对、代码、离线测试和文档；没有管理员认证、USB枚举或相机命令，没有生成或运行新设备脚本。第77轮失败与原操作文件保留，D4仍0真实材料。

## 证据与决定

第77轮已经读取USB型号，在NORMAL_START调用边界遇到USBError(-9/32)，44事件/0快照，协议结果未知。该边界包含描述符检查和控制调用，旧回执无法定位到USB内部阶段，不能把“状态阶段STALL”当作已证实根因。

重新核对第73轮固定17文件摘要，并查看[YuuLuo固定研究脚本](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/macos/mac_service_readonly/sony-service-research/service_probe.py)：START出现后端-9且errno32/None时继续认证，其他错误抛出。该文件头部目标固件为1.02；本项目仍只接受2.01，不能把作者现场描述作为本项目2.01验证。固定v2.1 PMCA的start/stop更广泛吞掉GenericUsbException，也不直接迁移。

本轮把可复核的错误码现象作为行为参考，在现有借用端口内编写更窄的候选：只允许普通侧首次START、实际SDK控制调用返回精确USBError类型、精确整数-9和32。没有导入或复制相关项目源码/注释/模块；其GPL-3.0-only声明及研究贡献在[致谢](../ACKNOWLEDGEMENTS.md)保留，不当作MIT代码来源。现有PMCA认证/协议代码及许可不变。

## 实现

[有限入口](../lutphoto/captureprobe.py)新增私有`_ProbePort.normal_start`：

- 一次普通START，固定请求和空载荷，最长5秒且受整段120秒预算约束。
- 描述符/就绪检查在控制异常捕获之外；前置、SDK调用、后置检查分别留边界。只有SDK控制调用的精确错误对可以形成暂定PIPE。
- 暂定PIPE不是成功ACK，日志为`NORMAL_START_PIPE`且不产生`ACK/NORMAL_START`。之后三轮挑战/证明及最终响应全部通过，才确认普通认证并结束暂定状态；不重置任何unknown标志。
- 错误类型/子类不符、缺失errno、浮点码、其他错误码、读写错误、取消、超时和日志失败均停止。服务START及STOP仍严格拒绝错误，禁止第二次START，没有清端点/复位/重试/救援或74材料串接。

持续供电声明通过冻结的`_Power`值进入`--maintained-power`/API，替代后续脚本电量输入；记录`mode=maintained-high-battery-usb`、`battery_percent=null`、`automatically_measured=false`。保留显式百分比模式且两者互斥，不接受空声明或真假值冒充数值。供电不是自动电量测量，也不放宽机型、版本、固定来源和后续完整程序指纹。

为复用现有流程，[captureexecution](../lutphoto/captureexecution.py)只抽取来源/环境装配，[capturemac](../lutphoto/capturemac.py)只抽取宿主生命周期字段初始化。旧完整入口及Host构造的版本/百分比校验仍在原入口，旧认证、完整结果/3、检查器、安装器和固定锁不改。测试夹具对应改为在共用来源装配处绑定自制请求，没有替换生产认证或传输方法。

私有结果和stdout分别升级为`a7c2-service-probe-result/2`与`a7c2-service-probe-cli-result/2`，新增`declared.power`、`normal_start`及错误项`start_boundary`。`normal_start`的控制结果和边界分别记录，不把成功后置检查当作控制ACK。旧第77轮`/1`记录及读取器原样保留，不可改名追认。新版仍不兼容完整`captureevidence inspect`，没有新增通用probe图检查器。

## 实际验证

Python3.14.6，测试全部使用自制数据/SDK，无相机访问。

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_captureprobe research.tests.test_capturecamera research.tests.test_captureauth research.tests.test_captureexecution` | 119项通过，5.980秒 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_capturemac.py -v` | 51项通过，0.110秒 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 1089项通过，82.815秒 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 8项通过；全套1136项 |
| `.venv/bin/python -B -m macfl23 check` | 固定来源/资产通过 |
| `.venv/bin/python -B research/output/custom-round74/check-legacy-receipts.py` | 3类自制旧记录分类和字节保持 |
| `.venv/bin/python -S -B -m lutphoto.captureprobe --help` | 实际互斥参数正确，不加载SDK/USB |
| `.venv/bin/python -B research/output/custom-round78/check-round.py`、`git diff --check` | 通过：16个公开文件、10份文档/243个本地链接、17固定来源、6份旧私人文件未变，旧完整入口校验及生命周期AST保持 |

probe专项从17增加到31项，覆盖暂定PIPE后完整认证成功且无伪ACK、7个认证响应分别拒绝、认证读写错误、描述符前后错误、服务START/STOP错误、取消/超时/日志失败、非精确错误、二次START、严格零长度返回、供电声明/CLI无输入与旧入口门槛保持。

最初用模块路径运行`test_capturemac`时，其既有同目录导入缺少搜索路径而导入失败；改为该目录的unittest discover后51项通过，未改生产或测试导入去掩盖问题。其余相关测试及最终完整回归如上，不把失败调用记为通过，也不重复相加专项测试为总测试数。

## 交接与发布边界

下一步准备全新的`/2`单次操作、私有作业/回执和摘要读取器，使用`--maintained-power`且不再询问电量。先审阅输出/退出码及源码冻结，不能改旧冻结值、旧回执或重跑第77轮。设备阶段需要实际连接信息；本轮没有要求重连，也没有利用上一轮“仍连接”启动相机。

完整服务入场、快照、停止和USB返回仍缺本项目正例；这项候选可能仍失败，特别是服务侧START保持严格规则。同阶段没有新证据时转Windows原生只读对照评估或后置Mac，不无限扩大模拟框架。R3通过后再审阅完整采集接入，D5/D6和真正3D LUT支线继续后置。

本轮按已有授权提交推送到`lut-photo/main`，不推继承origin。仅公开源码/测试/说明；本轮日志、来源快照与第77轮私人脚本/记录不上传。实际提交和远端状态以Git记录及最终回执为准。接续入口：[HANDOFF](HANDOFF.md)。
