# N3：合成事务的持久化与独占原型

第三十四轮增加 `lutphoto.customjournal`：把第三十二轮的五个 128 字节合成组件搬到磁盘，验证意图/结果顺序、进程独占和中断后的只读分类。**没有相机适配器、USB、续写、恢复现场或安装入口。** 磁盘实验通过不代表真实设备事务、断电恢复或完整备份通过。

本工具只用 Python 标准库和本仓库两个离线模块，不需要 Zig、NumPy 或机身程序；目前仅在 Mac/POSIX 验证，使用 `fcntl.flock`，不是 Windows 实现。当前无需 Docker、惠普电脑或相机协助。

## 运行示例

在仓库根目录执行；目录必须新建，父目录须存在：

```sh
mkdir -p research/output/journal-demo
.venv/bin/python -B -m lutphoto.custommigration fixtures \
  --directory research/output/journal-demo/cases
.venv/bin/python -B -m lutphoto.customjournal simulate \
  --capsule research/output/journal-demo/cases/S0.json \
  --directory research/output/journal-demo/install \
  --lock-directory research/output/journal-demo/locks
.venv/bin/python -B -m lutphoto.customjournal inspect \
  --directory research/output/journal-demo/install \
  --lock-directory research/output/journal-demo/locks
.venv/bin/python -B -m lutphoto.customjournal simulate \
  --capsule research/output/journal-demo/cases/S0.json --direction restore \
  --directory research/output/journal-demo/restore \
  --lock-directory research/output/journal-demo/locks
```

`restore` 是从重新计算的完整合成目标开始的新实验，不能消费已中断目录。任何已有目录都拒绝再次 simulate，无论它是否完成、仍为来源字节或已经是目标字节。没有 resume/repair/force 命令。

```sh
.venv/bin/python -B -m lutphoto.customjournal simulate \
  --capsule research/output/journal-demo/cases/S0.json \
  --directory research/output/journal-demo/unknown \
  --lock-directory research/output/journal-demo/locks --fault NAMES:after-write
.venv/bin/python -B -m lutphoto.customjournal inspect \
  --directory research/output/journal-demo/unknown \
  --lock-directory research/output/journal-demo/locks
```

上述两个中断示例预期退出 **2**、状态 NEEDS_REVIEW；第二条只读分类，不继续变更。正常完整实验/检查退出 0；输入错误、锁占用、已有实验目录、权限或 I/O 异常退出 1。现场证据损坏时 inspect 仍输出 NEEDS_REVIEW 并退出 2，`journal_valid` 为 false。结果只写标准输出，错误只给异常类型，不回显路径/设置；重定向报告须自行选择新路径，避免覆盖既有证据。

## 落盘顺序与文件契约

新实验目录和事件目录权限 0700，文件 0600，检查当前用户所有权、普通文件、单硬链接、禁止叶节点符号链接及组/其他用户权限。输入必须是第三十二轮的精确合成胶囊，不接受真实程序、Sony 备份或额外私有字段。

| 文件 | 作用 |
| --- | --- |
| `capsule.json` | 完整合成来源及两个模拟备份；不是物理备份 |
| `contracts.json` | 第三十三轮自制资源/解码设置的独立回归结果；没有把占位缓冲绑定到真实布局 |
| `manifest.json` | 事务 ID、方向、胶囊/计划/格式结果完整 SHA、起终哈希及本地锁 inode 绑定 |
| `current.json` | 五个合成组件的可变磁盘现场；只在新模拟运行期间替换 |
| `events/00000000.json` 等 | 排他创建、规范 JSON、连续编号和 SHA 链的不可覆盖事件 |

启动时重新校验完整合成 AP/CP 来源、双模拟备份、正向/精确逆向和第三十三轮格式契约。先持久化 PREPARED；每个变化组件执行：全现场读回 → INTENT 持久化 → 再次核对现场 → 替换合成现场并同步 → 完整读回 → VERIFIED 持久化；最后再次完整读回并持久化 COMPLETE。模拟顺序沿用第三十二轮，**不是已审核的真实设备操作顺序**。

每个事件先在唯一临时文件中写入并 flush/fsync，再用排他硬链接发布、同步父目录、删除临时链接并再次同步目录。只有全部返回后才允许模拟变更。现场 JSON 用临时文件 fsync→原子 replace→目录 fsync；这只是合成单文件替换，不代表相机的多文件事务有原子性。失败保留 `.pending-*`、已有日志和现场，不尝试清理、补日志或重新执行。

每个 JSON 上限 128 KiB；必须符合规范序列化，拒绝重复键、非有限值、非规范字节及结构不符。事件最多 12 个，校验完整前缀协议、编号、前一 SHA、事务身份和每步全组件哈希。额外/缺失文件、断链、未完成发布、输入/清单/格式结果变化均进入待检查。

## 独占范围

所有原型任务必须显式使用**同一个** `--lock-directory`，非阻塞锁住其中固定 `session.lock`。检查与 simulate 使用同一独占锁，检查不创建缺失锁/目录；锁占用就停止，不等待重试。锁文件永不主动删除，进程退出/被终止后由内核释放锁，避免删文件使不同进程锁住不同 inode。清单绑定原锁 inode，更换锁目录不能冒充原实验。

旧 Mac 安装器使用 `/var/run/a7c2-fl23-macos.lock` 的全局 flock，上游 Custom 的装饰器使用工作目录锁；不同路径不能互斥。本轮没有打开系统锁，也没有修改旧安装器。实际跨进程测试只证明同一临时 inode 的 flock 互斥，包括旧算法等价的锁调用；**真实全局相机锁接入仍缺**。未来任何 USB 接入必须先持有旧工具兼容的全局锁并保持整个会话的所有权，不能只加新工作目录锁。不同显式目录、非合作进程及其他相机软件不受本原型锁保护。

## 分类与验证边界

inspect 在锁内重新推导来源、目标及期望日志协议，校验磁盘数据，不修改日志、现场、目录内容或权限，不创建检查报告文件。逐组件只分 source/target/unchanged/unknown；target 指本实验方向的目标，restore 时含义相反。pending INTENT、日志/现场不符或缺少 COMPLETE 都是 NEEDS_REVIEW。即使完整目标已吻合、所有 VERIFIED 都在，缺少最终 COMPLETE 也不自动补齐。

SHA 链不是认证签名，没有外部可信尾锚，不能抵抗拥有本地写权限者完整重写/回滚所有证据。`journal_authenticity_verified` 固定 false。fsync 与 SIGKILL 测试也不是实际掉电或存储控制器持久性测试，`power_loss_verified` 固定 false。没有根据文件内容自动执行任何下一步。

报告中的 `global_camera_lock_acquired`、`camera_operations_enabled`、`actual_source_identity_verified`、`independent_media_verified`、`physical_validation_verified`、自动重试/恢复均为 false。仅有合成终态 SIMULATED_TARGET_VERIFIED / SIMULATED_SOURCE_RESTORED；不代表相机安装成功。

故障 `COMPONENT:stage` 的组件只能是实际变化的 AP/CP/NAMES/SETTINGS_RAM/SETTINGS_SAVED；阶段为 `before-intent`、`intent-temporary`、`intent-published`、`after-intent`、`state-temporary`、`state-published`、`partial-write`、`after-write`、`verified-temporary`、`verified-published`、`after-verified`。最终阶段使用 `TRANSACTION:before-complete/complete-temporary/complete-published`。临时/发布阶段中断可能使证据本身不完整；不把这类报告判为合法结果。

第三十五轮完成[来源策略与真实 C 的合成头编译/ABI 核验](WORKER-CONTRACTS.md)，第三十六轮增加[BK4 只读格式/四态比较并厘清主机加载链边界](BK4-OFFLINE.md)。第三十七轮已有[程序身份/描述符只读入口](PROGRAM-IDENTITY.md)，第三十八轮已有[描述符/快照只读绑定](SETTINGS-BINDING.md)，真实程序/BK4 正例、资产/事务绑定、备份兼容性、新鲜角色/机身来源证明、真实 Mac USB/全局锁、独立介质及物理恢复仍缺；Sony 加载行为留给受控 N4。N3 保持部分完成，N4 相机实测后置、进入前提示。当前进度见[总计划](../plan.md)与[交接](../research/HANDOFF.md)。
