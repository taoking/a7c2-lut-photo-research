# N3：纯主机采集存储与自制传输演练

第四十二轮提供 `lutphoto.capturestore` 和 `lutphoto.capturehost`。**它们只支持内存中的 SyntheticTape，没有真实采集/备份命令或 USB 适配器。** 设计依据见[内部采集设计](CAPTURE-DESIGN.md)，程序策略及 BK4/UXC 格式沿用已保留 QAQLeonard/ma1co 署名和许可的现有模块。旧安装器、锁、指纹、依赖和默认单份备份不变。

## 实现范围

| 层 | 已实现内容 |
| --- | --- |
| 私人存储 | 仓库外新目录，逐层拒绝链接/异常所有者及不可信可写父目录；以目录句柄定位固定文件夹，排他创建，目录 0700/文件 0600 |
| 完整性/持久化 | 每项写入、文件 fsync、完整 SHA/长度读回、目录 fsync；最后重新核对全部已记录材料/事件。失败留下原件或部分文件，不覆盖、不续写 |
| 作业互斥 | 私人 session.lock 的真实非阻塞 flock；检查锁/目录 inode、单链接文件和权限。进程终止后锁释放，原锁文件保留；未打开旧系统相机锁 |
| 有界接收 | 每块最多 64 KiB，块/单文件/全程载荷上限在写入前检查；精确程序长度；文件与哈希接收器共用 1200 秒载荷预算，不按新 read 重置 |
| 状态与日志 | C0–C5 模拟顺序；每次假读取前持久化 INTENT，返回后记录 ACK，事件带序号/前项 SHA；最多 512 项，每项 16 KiB，报告最多 128 KiB |
| 材料顺序 | 两份原厂完整程序逐项保存并严格匹配；初始 RAM/保存快照、可选 68 资源；完整程序/资源复读、结束快照，最后模拟服务退出和普通身份复核 |
| 格式检查 | BK4 仍只检查两个结构有效块，不猜角色；观察开始/结束的 02cf 和四个 CP 键，诊断当前值/无关组有既定边界，属性/长度/reset 仍保留。RAM 与保存值可以不同，不执行 save/reset |

空间检查按请求材料的最大保存量及有界元数据计算，在任何假传输前执行；它不保证后续写入成功，实际写满仍停止。载荷时间检查发生在调用前、每块和接收结束；不能替代未来 USB 调用的超时，也不能抢占正在阻塞的文件系统调用。

初始程序/快照放在 `source/`，结束快照放在 `evidence/`，可选资源放在 `resources/`，日志在 `events/`。报告为 `capture-report.private.json`；它含指纹和逻辑文件名，不含绝对路径、身份值、设置键值或原始数据，仍应保留在私人位置。

## CLI：只演练固定策略拒绝

使用现有 Python 3.12+ 研究环境，只需标准库，支持 POSIX 文件/锁。先按[固定来源说明](UPSTREAM-V2.1-AUDIT.md)准备源码包。不需要相机、sudo、Docker 或 AArch64 Linux 共享库。

以下命令**不会备份相机**。它生成约 100 MB 的全零 AP 数据，验证固定原厂策略的拒绝；不会读取照片、用户备份或其他输入程序。父目录须存在且归本人所有，演练目录必须尚不存在，并位于仓库之外。例如首次运行：

```sh
mkdir -m 700 "$HOME/Pictures/A7C2-capture-demo"
.venv/bin/python -S -B -m lutphoto.capturehost rehearse \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "$HOME/Pictures/A7C2-capture-demo/unknown-program" \
  --case unknown-program
```

预期退出 **1**，JSON 为 `NEEDS_REVIEW`：全零程序不匹配，保留演练原件，模拟一次健康退出，不读取 CP/快照。已有父目录就不要再次创建；已有演练目录不能重跑覆盖。

另一种拒绝演练使用新的目录：

```sh
.venv/bin/python -S -B -m lutphoto.capturehost rehearse \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "$HOME/Pictures/A7C2-capture-demo/oversize" \
  --case oversize
```

预期退出 **1**，`simulated_outcome_unknown:true`：超限块在写入前拒绝，保留此前部分数据，不再发送模拟退出或重试。`accepted_payload_bytes` 只统计通过接收边界的载荷，不包含被拒绝块、协议头或元数据。两种演练都不生成固件候选；没有 `--policy`、身份、角色或指纹覆盖参数。

## 成功与失败的证据边界

完整正例只在自动测试中注入自制 tiny 程序策略，执行相同存储/核验流程；真实固定程序的完整正例未测。正例报告仅为 `SIMULATED_HOST_CAPTURE_COMPLETE`，`simulation_only:true`；真实机身身份、芯片角色、外层备份、快照新鲜度、原子捕获、独立介质、系统相机锁、原生执行、恢复和物理验证均 false。

接收超限/中断/半包视为未知，停止所有后续假协议动作；响应完整之后的内容/主机核验失败，最多尝试一次已记录的健康退出。退出未知、返回身份变化、未能持久化意图/结果均不能完成。日志无法继续写入时不绕过日志发送退出命令；留下现场待审阅，不自动重建目录或清理失败证据。

失败发布可能留下部分事件/报告，不能只看到某个 JSON 的完成字段就视为成功，更不能拿它当写入许可；要结合本次实际返回、完整日志和全部材料。本轮没有旧目录检查/恢复/续跑入口，也未验证真实断电或文件系统故障后的介质持久性。子进程 SIGKILL 测试证明的是本机进程终止时锁与文件的观察结果。

下一步审阅真实读适配器的协议接收上限、会话健康/退出、普通身份前后绑定及旧全局相机锁接入；模拟后端不是可替换为 USB Session 的插件接口。真实采集、USB、原生执行及恢复仍须独立开发和验证，进入前提示。进度见[总计划](../plan.md)、[交接](../research/HANDOFF.md)及[本轮记录](../research/LUT链路调查记录-第四十二轮.md)。
