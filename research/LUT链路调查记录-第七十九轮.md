# 第七十九轮：新版单次准备及普通认证阶段失败

日期：2026-10-26。基线`39c9b168a2f31189c7e2e490783557e244bb518d`，开工工作区干净。本轮沿用第78轮生产代码，先完成私有准备/离线检查并发布，随后按本人确认执行一次有限验证；在普通认证阶段失败停止，未取得快照，D4仍0真实材料。

## 本轮交付

新的私有操作文件、启动文件、独立回执读取器位于忽略目录`research/output/custom-round79/`，真实路径只保存在`location.private.json`。生成器只复制和调整既有已审流程，使用新随机作业/回执名称，拒绝覆盖已生成准备；未运行旧第77轮生成器或操作文件，旧三份操作文件、失败日志、检查日志和定位文件共6份均保持原字节。

- 单次调用`captureprobe.main`，只取一份RAM快照；没有完整74材料串接、重试、清端点、复位、旧prepare/diagnose或写入。
- 参数固定为本人ILCE-7CM2、官方原厂2.01及`--maintained-power`。无电量输入/确认，也不伪造百分比；这是已有用户声明，不是自动测量。运行前仍需真实连接信息，管理员密码只在本机终端输入。
- 冻结172个源码、依赖声明、锁及新摘要文件的SHA-256；导入项目前、电脑预检查后/设备入口前、摘要子进程前分别核对。文件须是有界单链接普通文件；不接受链接替代或来源变化。
- 延用私有父目录所有者检查、新作业及独立回执排他创建、日志禁止覆盖、实际退出码保留；根权限和真实目录检查留在未来运行时，不用模拟通过冒充现场条件。
- 摘要进程使用`-S -B`，只读指定已有回执，无SDK/USB。采集与摘要退出分别输出，整体失败不会因摘要成功而变为成功。

新摘要schema为`a7c2-service-probe-local-summary/2`，只接受新版probe结果/2。除已有事实/本地收尾/未证标志外，新增供电声明、START控制结果与边界、错误阶段与START失败边界；理由和阶段使用白名单，数值有界，不输出身份、原始字节、路径、材料摘要或任意异常文本。拒绝旧/1、错误类型、矛盾完成/阶段顺序、虚构供电百分比、活动/变化/重复字段回执和链接。

这是回执字段摘要，不是通用probe证据图检查器或硬件证明。`PIPE`始终作为控制结果单列，不改为ACK；只有真实调用内完整认证成功才可形成相应事实。回执中的事实仍需结合原调用、日志和实际材料复核。

## 验证

Python3.14.6，全部使用自制SDK/材料。日志保存在本轮忽略目录。

| 命令 | 实际结果 |
| --- | --- |
| `.venv/bin/python -B research/output/custom-round79/test_preparation.py` | 21项通过，0.716秒 |
| `.venv/bin/python -B -m unittest research.tests.test_captureprobe` | 31项通过，0.988秒 |
| `.venv/bin/python -B -m macfl23 check` | 固定来源和资产通过，无设备访问 |
| `.venv/bin/python -S -B -m lutphoto.captureprobe --help` | 真实参数与供电互斥契约一致，无SDK/USB |
| `/bin/zsh -n research/output/custom-round79/run-reviewed-probe-once.command` | 语法检查通过，已包含在21项准备检查内；没有启动shell操作 |
| `.venv/bin/python -B research/output/custom-round79/check-round.py`、`git diff --check` | 发布范围、文档链接、冻结来源、旧记录和差异检查通过 |

准备测试覆盖普通零返回、限定PIPE后认证成功、PIPE后认证失败、START失败边界、失败退出不被摘要覆盖、摘要失败、导入前/入口前/摘要前来源变化、新目录拒绝重复、无管理员身份即停、禁止电量输入、旧schema与矛盾字段拒绝、活动/重复/链接/变化回执拒绝及隐私白名单。测试中的临时作业及源码改动均由夹具隔离，不运行已用相机脚本、不读取旧快照或程序作测试。

生产代码、现有公开测试、依赖与固定锁均未修改，因此没有重复执行无关全套回归。第78轮1136项及其[CI通过](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/40277028386)是此前证据，不计成本轮测试或真机成功。

## 单次实测与普通断开收尾

本人明确回复“已连接 MSC，仍为官方原厂 2.01”后，重新核对172冻结来源、3操作文件及6份旧记录，确认新日志不存在。按既有范围在本机终端派发一次新命令，使用`--maintained-power`，未要求电量输入。本人随后回复终端已结束。

原结果日志及运行时摘要显示：

| 项目 | 实际结果 |
| --- | --- |
| CLI/回执摘要 | NEEDS_REVIEW；probe退出1、摘要退出0，回执保存已报告 |
| 普通侧首次START | control_status=PIPE，boundary=COMPLETE；没有成功ACK，表示限定控制错误及后置检查已记录 |
| 失败位置 | NORMAL_VERIFY，USBError，backend_error_code=-1、errno=5；start_boundary=null |
| 认证与材料 | 普通/服务认证均false，snapshot_validated=false，尚无快照 |
| 协议退出 | protocol_outcome_unknown=true；停止服务未尝试/未确认，normal_usb_reappeared=false |
| 本地收尾 | owners、job_store、global_lease、signal_handlers均true |
| 供电记录 | maintained-high-battery-usb、battery_percent=null、automatically_measured=false |

失败后只读取已有本地结果日志和源码，没有再次给相机发命令、停止/复位/重试或开始完整采集。没有为获取更细字段再请求管理员读取，也没有修改旧记录。新的3操作文件及172冻结保持。

本人确认存取灯熄灭，屏幕已切换到连接方式选择页；未要求再次选择连接。按普通USB流程收尾后，本人确认“已断开，拍摄画面或菜单正常”。这记录为使用者观察，与协议退出/身份重验分别保留；没有冷启动、新拍或回放验证，不将其记为完整恢复验收。

## 结论与下一动作

限定START路径已经实际走到认证调用，但认证仍未完成。现有结果只能定位NORMAL_VERIFY；源码中该阶段包含每次读写前后的描述符检查与三轮认证/最终响应，没有逐次认证I/O诊断，因此不能确定第几轮、读/写或描述符访问失败，更不能从-1/5或连接选择画面推定密钥错误、进入服务模式或正常重枚举。

下一轮只做离线核对：比较固定上游普通侧认证的接口/端点、报文长度/字节、传输方式和切换时序，先利用已有日志/源码确认可观测范围。若需要更细诊断，先提出最小字段和明确的问题，再审阅是否值得一次新验证；不得仅加日志就马上重采，不继续扩大错误容忍。若无可复核差异，评估原生Windows只读对照的环境/驱动条件或后置Mac；不连续在同环境试错。

R3仍未通过，不能接完整74材料采集；完整内部备份、单槽导入、恢复和真实色彩验收继续后置。第79轮已用脚本、生成器和准备测试均为历史，不可重跑或更新冻结值；下一进程从[HANDOFF](HANDOFF.md)开始。

## 发布与检查

准备文档提交`4c3486faf650afcbf5c244b81cbe8204d03c7cae`已推送并核对远端，其[CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/40279218604)完成success；CI不证明设备成功。本次追加实际失败、用户收尾和后续动作，生产代码/测试/依赖/锁仍未改。

追加检查：`.venv/bin/python -B research/output/custom-round79/check-outcome.py`及`git diff --check`通过，核对实际结果日志、CLI与摘要退出、未改的3操作文件/172来源/6旧文件、文档链接和公开范围；没有在真机之后重跑带“未派发”断言的准备测试，也没有重复无关全套回归。公开仅状态文档，不上传私人脚本、真实路径、材料或日志；按已有授权推送`lut-photo/main`，具体追加提交以Git及最终回执为准。
