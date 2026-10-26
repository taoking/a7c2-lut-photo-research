# 第七十七轮：有限服务验证单次准备与公开发布

日期：2026-10-26。基线`d94a4628171aeacbebfc707f98bc1d8d2cb34a09`。本轮承接第76轮，完成R3的电脑端操作准备，不扩展协议或完整采集入口。本人授权提交推送，准备完成期间主动报告已连接并确认MSC/官方原厂2.01；现场电量和管理员认证留在终端。随后已执行一次；结果见下文，失败停止。

## 交付

新操作只调用一次`lutphoto.captureprobe`，范围限定最多一份RAM快照（本次实测未取得）。沿用受信来源、私有父目录/所有权、新作业与回执排他创建、一次性日志拒绝覆盖。源码冻结172个文件，含新probe/identity、现有运行依赖、测试、声明和专用读取器；项目导入前、现场电量输入后、预检后、摘要子进程前重复核验，变化即停止相应后续动作。

新私有摘要读取器通过独立-S进程只读新回执，检查私有普通文件/不跟随链接/共享非阻塞锁/有界JSON、严格布尔字段与明显矛盾。仅输出固定结果和白名单错误类别/数字码，不输出身份、位置、私人路径、原始材料或材料摘要。它的作用域明确为`receipt-fields-only`，不是完整证据图或硬件验证。采集、摘要退出码分别保存，非0不被后续成功覆盖。

三个操作文件和新路径在忽略目录`research/output/custom-round77/location.private.json`登记。没有复制任何私人材料到公开树，没有修改旧第72轮操作摘要或覆盖旧作业。当前代码不变；实机步骤只用新准备，接续顺序见[HANDOFF](HANDOFF.md)。源码冻结是本地防漂移检查，不是签名或SDK二进制认证。

## 实际检查

| 命令/检查 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 1075通过，83.706秒 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 39通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 8通过，完整回归合计1122 |
| `.venv/bin/python -B research/output/custom-round77/test_preparation.py` | 15通过，0.426秒 |
| `.venv/bin/python -B -m macfl23 check` | 固定来源/资产通过，无设备访问 |
| `.venv/bin/python -B research/output/custom-round74/check-legacy-receipts.py` | 3类自制旧记录分类和字节保持，无SDK |
| `.venv/bin/python -S -B -m lutphoto.captureprobe --help` | 实际CLI参数通过，无SDK/USB |
| 普通用户临时私有目录预检，无resources | 通过，285954856字节保守预算；未创建作业、管理员标志false |
| `.venv/bin/python -B research/output/custom-round77/check-publication.py`、`git diff --check` | 提交前核对公开范围、链接、私人信息、冻结/来源及已有文件保留 |

准备测试覆盖实际probe在自制SDK上只取一份快照、未知失败不停止服务、不继续读取、成功摘要不能覆盖失败、摘要失败不能转为成功、输入期间/执行后源码变化、链接/超限源码、旧目录保留、真实非管理员拒绝、锁住/重复JSON回执拒绝、摘要隐私及一次调用。初次测试对清单中包含capturecamera文件名误判，改为AST调用名称检查后通过；未改生产代码来迁就断言。

## 发布范围与未完成项

本轮获明确授权，将第73–76轮读包修正、快照身份、独立有限入口及测试/记录，与此前五份公开专项分析和本轮准备摘要一并审阅发布。开工34项既有文件已快照；保留各报告原资料日期，不把发布当作重新联网核验。目标`lut-photo/main`，不推origin；私人脚本/位置/日志、原件、固件、设置和身份不提交。提交及远端结果以Git记录和本轮最终回执为准。

本轮尚未验证机内效果、完整备份、返回序列、恢复、冷启动或拍摄。D4仍0真实材料。新单次有限验证现已失败停止；成功条件仍未满足，先审阅新START边界证据，不解除历史UNKNOWN或重跑旧74材料入口。同阶段无新证据时转Windows原生只读对照评估或后置Mac。

## 实测结果与后续决策

本人确认MSC/官方原厂2.01后，在终端完成一次新probe。CLI为NEEDS_REVIEW、退出1；专用摘要退出0不覆盖失败。USB标准型号读取成功，首次`NORMAL_START`边界返回USBError、errno32、backend_error_code=-9，44条事件、0快照/0服务身份、普通/服务认证未完成；协议结果unknown。没有补发停止/重试/进入完整采集。本地句柄、作业、全局租约及信号处理收尾均确认。

随后只检查已有电脑回执，未再访问USB。独立非交互sudo文件读取因需要密码未执行，之后由本机终端完成仅文件读取。本人确认原终端结束、画面正常、7号存取灯熄灭；最后仍保持USB连接，实际断开、正常菜单、冷启动及拍摄没有新证据。

`last_host_operation=USB_PRODUCT_STRING`是最近已记录的宿主操作，不能据此说型号读取失败；实际错误stage是NORMAL_START。该调用边界包含描述符检查及控制传输，当前回执没有底层逐调用追踪，所以“START状态阶段STALL”是有依据的兼容候选，尚非已证实根因或已认证成功。原第67/69/71轮故障也不能据此倒推。

本地PyUSB1.3.1常量将-9映射为LIBUSB_ERROR_PIPE/errno EPIPE。重新核对已固定来源：

- [YuuLuo固定service_probe.py](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/macos/mac_service_readonly/sony-service-research/service_probe.py)在START捕获backend_error_code=-9且errno为32/None时继续认证；其他错误抛出，下一步仍须完整认证。文件SHA与第73轮清单一致；未运行该程序，没有将其作者现场描述当成本机证据。
- 本项目固定v2.1归档中的`SonySenserAuthDevice.start/stop`会广泛捕获GenericUsbException；本轮重新通过9文件来源核验后只读查看。不能直接复制这种宽泛行为，尤其不能把未知STOP当成功。
- 当前`captureauth._RawAuth`和借用端口遇到任意异常即标记unknown；因此即使审阅后允许特定START状态，也必须同步处理认证/端口边界及结果表达，不能只在外层catch后继续。

本轮没有修改该策略或解除unknown。新增私有自制复现`reproduce-start-stall.py`通过：首次START注入USBError(-9/32)，得到相同失败阶段/型号已读/无快照、一次控制、不重试/不停止服务；这是模拟路径检查，不证明实际USB内部阶段。

下一步仅离线审阅“首次START明确错误码→完整认证才确认”的有限候选、其他错误拒绝、取消/日志/STOP边界及诊断记录；审阅通过后才新建准备。本轮出现了具体新证据，因此先完成这项审阅，再按是否仍缺进展决定Windows原生对照；不安排同环境重复尝试。

本人最新要求后续脚本不确认/输入电量，并承诺持续高电量与连接供电。该偏好写入HANDOFF；现有已用脚本保持原字节。下一份准备须将供电声明显式接入入口/回执并离线验证，不以虚构百分比填充现有CLI，不能将用户声明写作自动电量测量。

失败结果补充的实际检查：`.venv/bin/python -B research/output/custom-round77/check-outcome.py`通过，8份文档/187个本地链接、原操作文件和172来源未变、已有回执摘要及最新供电偏好一致；`git diff --check`通过。补充仅文档，未重跑全套离线测试或设备调用。

## 发布结果

37个公开文件已按授权提交推送为`5a8ed7fc2e359e535aeee573c5568a3b03d9a0d6`，远端main与本地一致，提交文件字节与审阅清单一致。该代码的[GitHub离线CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/40271099955)已完成success。此后仅更新本轮失败结果、后续计划和供电偏好，文档补充提交同样不含私人脚本、原件或日志；最终文档提交以Git记录和任务最终回执为准。
