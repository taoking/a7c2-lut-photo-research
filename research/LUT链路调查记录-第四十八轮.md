# 第四十八轮：受限原始接口与同句柄生命周期离线适配

日期：2026-10-21。交付 [captureraw](../docs/CAPTURE-RAW-OFFLINE.md)，在精确模拟设备上实现受限原始收发、同服务句柄顺序及单一关闭所有权，接入既有协调器。没有相机/USB 枚举、设备命令、sudo、系统相机锁、真实 PyUSB 调用、原生模块或私人材料读取，没有读取移动盘。用户继续保留原厂 2.00 及卡副本，不要求升级。

## 本轮交付与边界

- 固定来源没有端点数值锁；新增从明确描述符绑定唯一 bulk IN/OUT、接口 0/备用设置 0，在每次收发前后检测变化。普通 MSC 使用既有 8/6/0x50，服务采用未实机验证的 vendor class 限制；自制端点地址和额外拒绝条件均不伪装成机身事实。
- 直接保留原始 write/OUT 控制结果，必须精确完整 int；读取只接受 bytes/精确 array('B')，先检查长度再转换，不接受任意可转换对象。固定包、分块/排空、发送/接收异常、共享期限和单次最长 5 秒继续有界；没有使用旧吞异常/丢长度包装。
- 新入口的认证、固定材料请求/响应和 stop 共用同一个模拟服务对象；旧三个演练与独立认证入口保留。内部提取认证阶段和协调生命周期，不放宽公共认证接口，也不开放真实设备/子类/回调/策略或已有目录续跑。
- 两个本地端口有单一所有者，借用视图无析构关闭。关闭前先失效视图，仅尝试一次；未知后只释放本地资源，不 reset/cleanup/stop。另一句柄仍会尝试释放，主错误类型不被关闭错误覆盖。关闭或记录不明阻止完整发布，之前已知 stop 结果保留。
- 沿用 pipeline 私人格式，增加模型绑定与两角色关闭记录；检查器验证唯一性及位置，没有新增真实完成许可。普通返回仍为假观察，真实源/认证/协议/新鲜度/系统锁/恢复/写入/续跑全部 false。

源码核对固定 QAQLeonard v2.1/ma1co/ajalt 及 9/10/14 成员、N1 的 26/旧 46 成员；另外只读已安装 PyUSB 1.3.1 的 core.py/util.py 返回类型语义，不导入或复制其源码。共 43 条观察、40 来源身份通过。SyntheticDevice.close 仅为模拟本地释放契约，不是声称真实 PyUSB Device.close 已实现；真实 dispose_resources、MSC 接管、全局锁和新鲜正常身份查询仍缺。

## 实际测试命令与结果

起点 `3eeb418133e25531be5439da7173568012e1ac43`，[第四十七轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39549516747)已 completed/success。

| 实际命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_captureraw -q` | 新专项 36 项通过 |
| `.venv/bin/python -B -m unittest research.tests.test_captureauth research.tests.test_capturepipeline research.tests.test_captureinspect -q` | 既有相关 110 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -q` | 研究 608 项通过，含新专项 |
| `.venv/bin/python -B -m unittest discover -s tests -q` | Mac 39 项通过，服务提示来自模拟 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q` | 旧上游 8 项通过；合计 655 项 |
| `.venv/bin/python -B -m macfl23 check` | 固定源码/资产通过，无设备操作 |
| `.venv/bin/python -S -B research/output/custom-round48/audit_capture_sources.py` | 43 条源码观察/40 来源身份和既有固定清单通过，无归档执行/设备导入 |
| `.venv/bin/python -S -B research/output/custom-round48/exercise_raw.py` | 13 个纯哈希长度及 5 个固定来源同模拟句柄/真实只读 CLI 场景通过，无设备 I/O |
| `.venv/bin/python -B research/output/custom-round48/audit_public.py` | 公开文本/AST/JSON/本地链接、隐私资产、锁/归档/受保护路径与精确发布清单通过 |
| `git diff --check` | 通过 |

专项覆盖同服务模拟对象的完整认证/6或74材料/一次退出、独立包预期、非默认端点、异常/变化描述符、显式长度与数组形状、短发送/短头、超时/中断/认证状态失败、共享期限在调用前及返回后耗尽、日志/关闭/关闭记录失败、借用视图先失效、已有目录不接收句柄、错误优先级、版本/外部后端拒绝、重新计算链后的缺失/重复/错序关闭记录及 -S 无 USB/密码包/NumPy 导入。

首次提取公共生命周期漏传 resources，旧相关回归和新专项在 C0 失败；修正为显式传递选项后通过。修复脚本一度误改生成器表达式而导入失败，已修正；没有通过放宽指纹、阈值或真实标志消除失败。最终完整回归包含修正后的新旧流程。

固定归档演练使用内存中的固定密钥与自制挑战，独立参考仅执行固定且审阅过的三个纯主机哈希函数，不执行归档设备或目标代码。全尺寸全零 AP 99,960,744 字节被固定原厂门槛拒绝，不读 CP/快照；半包、认证控制无计数、材料发送无计数、服务关闭未确认分别保持未知，无盲目 stop。五个场景均只尝试关闭各自两个本地模拟句柄一次，关闭未确认不等于已证释放；实际 -S 检查 CLI 均预期退出 1，分类为未完成/未知/未知/未知/未知。

95/88/15/26/91 项输入（含目录）前后内容、inode、模式和 mtime/ctime 不变，atime 不承诺不变。密钥、挑战、应答、机身身份及个人路径不输出，临时自制材料清理，汇总仅留忽略的 `research/output/custom-round48/`。完整正例仅为测试内部 tiny 策略，不构成真实原厂材料或相机采集证据。

## 交接与发布

总计划仅 N3 一行更新、仍四列；滚动交接和轮次索引更新。已有工具分析及计划附录原样保留、不纳入发布。旧安装器/指纹/偏移/锁/测试/依赖/默认单份备份及历史归档未改，只暂存本轮源码/测试/文档和 N3 行。提交前列出实际测试命令和结果，只正常推 lut-photo/main，提交/远端及新 CI 状态以最终报告为准。

下一轮面向 Mac 宿主预检、MSC 接管/接口声明与释放、系统锁及同来源新鲜正常查询的代码适配和离线测试；先以假系统/PyUSB 对象覆盖已有服务身份、端口变化、权限/忙碌、部分接管/释放失败和未知停止，不直接运行设备入口。真实响应/回显/排空、材料角色/容器/同机新鲜来源、完整事务/bound worker/恢复和双独立介质继续独立验收。

相机保留原厂 2.00，当前卡副本不是内部开发备份，不读取移动盘或运行 prepare/diagnose。若另评估第三方修改升级包，先固定具体仓库/版本、迁移/恢复链；当前不替换原厂 2.01 固定门槛。N3 部分完成、N4 实测后置，进入前提示，目前不需相机、Docker 或惠普电脑。真正 3D LUT 支线保留第二十八轮未闭合状态。
