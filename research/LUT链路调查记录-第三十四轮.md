# 第三十四轮：持久化日志、进程独占与中断只读分类

日期：2026-10-19。继续 N3 的电脑端原型，不访问 USB、私人程序/备份、机内模块或相机。仅使用自制合成材料，旧安装器与固定锁不改。

## 本轮检查项

- [x] 核对旧全局锁与上游工作目录锁、日志持久化边界。
- [x] 合成事务的完整来源/目标绑定、不可覆盖日志、持久化顺序与只读分类。
- [x] 跨进程互斥、进程中断、日志/现场损坏及落盘故障测试。
- [x] 真实 CLI、完整离线回归与公开文件审核。
- [x] 更新四列总计划、当轮记录和滚动交接；审核后提交推送研究仓库，结果见最终报告。

## 来源审阅与交付

再次核验 v2.1 固定包 SHA `8c6c30448219f4e865e8005d2ffa789248e984d73b0f9342035f7065a1a232f7`，26 个审阅成员及本地副本（含 devicejob/devicelock）、旧基线 46 个成员身份全部通过。没有更新旧运行锁、原安装器或上游源码。

旧 Mac 安装器用 `/var/run/a7c2-fl23-macos.lock` 的全局 flock，固定上游 Custom 的 serialized 装饰器使用每个工作目录的锁。两者不同，不能直接认为互斥。原型使用显式同一临时锁目录/固定 inode，非阻塞跨进程独占、从不删锁；没有打开系统锁，没有接入 USB。未来设备流程必须先接入旧工具兼容的全局锁，并覆盖完整会话。

新增 `lutphoto.customjournal`，只依赖标准库和现有合成迁移/格式层。命令、文件结构、阶段与限制见[使用说明](../docs/CUSTOM-JOURNAL.md)。五个组件仍是 128 字节占位材料；资源/解码设置契约只作独立前置回归，不冒充真实布局绑定。

事件为 PREPARED→逐组件 INTENT/VERIFIED→COMPLETE；每个事件先同步临时文件，再排他发布、同步目录、删除临时链接并再次同步目录，全部返回后才变更合成现场。现场文件原子替换并同步，每步/结束前完整读回；清单固定胶囊、计划、起终 SHA、格式结果和锁 inode。日志连续编号、规范 JSON、前一完整 SHA 及事务身份逐步检查，不覆盖既有事件。

任何落盘/读回异常都停止，保留临时文件及原现场；进程中断不尝试补事件。inspect 只读校验和分类，缺少完成记录、pending 意图或任何证据/现场差异都不能通过。即使全目标吻合也不会自动重放、续写或恢复。simulate 对任何已有目录均拒绝，restore 只从重新计算的完整合成目标启动新实验。

链式 SHA 不是签名或外部可信锚，不能抵抗本地写权限者完整伪造/回滚；真实性标志固定 false。fsync/进程 SIGKILL 也不等于真实掉电或设备持久性验证，物理/全局相机锁/设备操作/介质独立和自动恢复标志均为 false。

## 测试命令与结果

实际执行，最终均退出 0：

```sh
.venv/bin/python -B -m unittest research.tests.test_customjournal -q
.venv/bin/python -B -m unittest discover -s research/tests -q
.venv/bin/python -B -m unittest discover -s tests -q
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -q
.venv/bin/python -B -m macfl23 check
.venv/bin/python -B -m research.audit_upstream_looks \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --output research/output/custom-round34/upstream-source-audit.json
```

新增专项 **22 项**，完整研究 **235 项**、Mac **39 项**、旧固定上游 **8 项**，合计 **282 项通过**。旧测试 USB 提示来自模拟，未打开设备。本轮没有新增运行依赖、实际 worker 编译或目标代码执行。

| 专项覆盖 | 实际结果 |
| --- | --- |
| 4 来源 × 2 方向 | 完整落盘/重新检查通过 |
| 11 组件阶段 + 3 最终阶段 × 2 方向 | 28 组合全部 NEEDS_REVIEW，拒绝重放；不是另计 28 项 unittest |
| 5 组件 × 2 方向，写后缺结果 | 10 组合，完整目标仍保留 pending 意图和未知结果 |
| 真实子进程 SIGKILL，意图后/写后 | 两次内核释放锁，重新检查为 source/target 观察，但均 NEEDS_REVIEW，不续写 |
| 文件/目录 fsync 失败 | 意图失败时现场不变；现场替换后同步失败保留 pending，不重新操作 |
| 跨进程共享临时锁 | 其他任务和检查都非阻塞拒绝；旧算法等价 flock 调用同 inode 时也拒绝，并非系统锁实测 |
| 断链、缺失/额外/临时记录、错误顺序/事务/哈希、非规范 JSON | 全部拒绝为完整结果 |
| 损坏/回退现场、清单/胶囊/契约变化、权限/符号链接/硬链接/FIFO | 只读停止，无修复或覆盖 |
| 意图后/完成前现场被改变 | 新鲜完整读回发现差异，拒绝覆盖或记录完成 |

实际 CLI 位于忽略的 `research/output/custom-round34/`，使用说明中同样参数：8 组完整 simulate/inspect 退出 0，8 次已有目录重跑退出 1，3 组中断 simulate/inspect 退出 2（临时意图、写后缺结果、缺最终完成）。检查前后证据内容和来源胶囊完整 SHA 不变；全部以 `-S` 不加载 site packages 运行，专项确认无 USB/NumPy/macfl23/PMCA 导入。输出仅摘要，不含宿主 inode、路径或胶囊数据。

公开审核检查全部文本的 AST/JSON/本地链接与锚点、NUL/个人路径/疑似密钥、禁止资产、显式改动清单及空白，固定旧归档/运行锁 SHA 及原安装器保护路径不变。环境、磁盘实验、原始日志与报告不提交。沿用授权仅提交推送 `lut-photo/main`，不推 origin；提交前列出测试命令和结果，提交/远端/CI 由最终报告及 Git 历史核对。

## 遗留与交接

本轮离线持久化/锁原型已具备，不再无期限扩展合成模拟。下一轮转向固定上游真实 device_layout/six 与 descriptor 来源/表资产边界、nativebuild/worker 报告 ABI，先做不读取私人程序的源审阅/构建可行性检查；没有完整已审资产就拒绝真实规划，不修改哈希或启用模拟身份。

完整 BK4/同机身来源证明、真实 worker 构建及加载边界、实际全局锁/USB、设备恢复、独立介质和 N4 物理/色彩验收仍缺。未知事务没有自动续写/恢复入口。N3 部分完成，N4 进入前提示，目前无需连接相机、准备 Docker 或惠普电脑。真正 3D LUT 支线仍停在第二十八轮未闭合状态。
