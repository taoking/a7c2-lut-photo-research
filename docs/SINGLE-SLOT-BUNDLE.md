# N3：私人单槽事务包与独立重验

第五十九轮提供 `lutphoto.slotbundle`，复用[单槽目标生成](SINGLE-SLOT-TARGET.md)的唯一内存实现，以及既有私有Store/Reader。创建器保存完整输入、程序/资源目标、前向/逆向和设置投影；独立检查器只从包内固定文件重新生成目标并逐字节比较。**这是离线资料包，不是相机安装事务、恢复工具或设备操作授权。**

本轮正例使用实际N2离线候选和自制程序/策略、BK4/UXC，未读取真实机身或私人材料。原厂2.00和日常卡副本继续保留，不需升级、连接、读取移动盘或准备Docker/惠普电脑。旧安装器、固定指纹/偏移/依赖及默认单份备份不改。QAQLeonard/ma1co来源与许可见[致谢](../ACKNOWLEDGEMENTS.md)。

## 创建与检查

先有本人明确提供的完整材料及[恰好一槽的选择文件](SINGLE-SLOT-TARGET.md#输入与命令)，才使用下面命令；所有路径都是占位示例。固定包仍须完整匹配已审清单。目标父目录须已存在、仓库外、当前用户所有、0700且祖先受信/没有链接；使用规范路径。作业目录必须全新，不自动修改权限或覆盖旧资料。无需sudo、NumPy、SDK或AArch64模块：

```sh
.venv/bin/python -S -B -m lutphoto.slotbundle create \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --ap "/path/to/owner-backup/appFw.so" \
  --cp "/path/to/owner-backup/cpapp-b.bin" \
  --ram "/path/to/owner-backup/ram.bin" \
  --saved "/path/to/owner-backup/saved.bin" \
  --selection "/path/to/owner-materials/selection.json" \
  --resources "/path/to/owner-backup/resources" \
  --ram-roles 0 1 --saved-roles 0 1 \
  --directory "/path/to/private-bundles/slot-001"
```

两组角色是分别声明的AP/CP图像索引，不是默认顺序、机身或芯片角色认证。完整程序/描述符先于快照/候选/资源读取；源状态仍限固定原厂2.01/FL23、精确重建的standalone或历史full7-v4，不通过自填指纹放行2.00或未知文件。候选目录和资源枚举沿用原检查，表字节不在生成后另行替换；候选JSON复读须与已检查版本的完整SHA相同，不能据此声称多文件原子采集。

成功后可在相同所有者上下文独立检查包，不需要原始外部输入位置或选择文件中的相对候选目录：

```sh
.venv/bin/python -S -B -m lutphoto.slotbundle inspect \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "/path/to/private-bundles/slot-001"
```

检查需要同一固定源码包，用于重新派生真实规则；没有任意策略、启用开关、文件路径覆盖、worker、重放/续跑或恢复参数。stdout只给有限阶段/计数，不含私人路径、材料指纹、设置值或名称。0仅表示本次离线操作及输出完成，检查/创建/存储/关闭/输出失败1，参数结构错误2。`CONSISTENT_OFFLINE_BUNDLE`不能当作真实来源、首次采集、部署或恢复通过。

## 实际保存内容

**包内含私人完整程序、原快照、名称/资源、目标与逆向字节，整个目录不得公开或上传聊天。** 它与上一轮只含指纹的摘要不同；含完整来源副本也不是两份独立介质备份。内嵌审阅的 `payloads_exported:false`描述原生成器的摘要契约，包的清单明确另标 `contains_private_payloads:true`，不能只看审阅字段判断目录是否可公开。

| 位置 | 内容 |
| --- | --- |
| `source/` | 原AP/CP、原RAM/保存快照、选择文件、候选JSON与表，共7文件，保留原始字节 |
| `resources/` | 固定68个原UXC |
| `evidence/` | 完整AP/CP目标、68资源目标、程序前向/逆向、设置投影前后/逆向、资源逆向、目标审阅，共75文件 |
| `events/` | 空目录，沿用私有Store布局；没有模拟协议或相机操作日志 |
| `bundle.private.json` | 最后在写锁内保存的规范JSON清单，固定schema/source/角色/false标志与150个payload的长度/完整SHA |
| `session.lock` | 私有作业锁；创建时独占，独立检查时非阻塞共享；使用中拒绝ACTIVE_JOB |

目录0700/文件0600，排他创建、逐文件写入/同步/读回核对；先保存全部150个payload，再保存清单。关闭写入作用域后重新打开为只读，复算固定来源和所有目标/逆向，再逐项比较包内每个文件的完整字节。设置文件明确为作用域投影，不生成完整BK4外层目标；原始快照完整保留，但外层真实性/恢复能力未证。

检查器只读固定白名单，拒绝缺失/额外文件、链接/硬链接、共享或所有者异常、使用中目录、截断/超限、元数据/目录项变化，以及清单的重复键、非规范JSON、额外字段、错误来源/角色/标志。单程序≤128MiB，快照≤32MiB，资源≤1MiB，前向/逆向等JSON≤2MiB，审阅/清单各≤128KiB，总读取≤512MiB；沿用Reader的期限/变化检查，系统调用仍可能阻塞。

仅重新计算文件哈希不能把错误目标、逆向或审阅变成正确内容；检查器会从冻结输入重新调用同一个生成器，核对完整双向程序重建及全部作用域/资源结果。零程序变更保留零窗口，不凑写入次数或生成worker；名称/设置仍可能有独立变化。

## 失败、证据与后续

创建失败保留已存在的空/部分/完整现场，不删除、修复、覆盖或重用；空间不足、写入/读回或关闭未确认均非成功。文件一致也不能证明原创建调用的关闭、stdout或整个进程成功；突然结束不保证留下完整清单。只读检查不会修复或推进任何设备状态，不用captureevidence把本包当成采集证据。

包及哈希不是签名：目录所有者能重新生成另一份完整有效的包。检查证明当前冻结字节与固定规则一致，不证明原用户意图、同机身/新鲜度/原子采集或当前相机仍处于该状态。没有真实程序正例；真实色彩声明不重算，完整设置容器/worker/加载器/设备执行/独立介质/恢复继续未证，不能从包中移植旧安装器放行条件。

第六十轮已增加[程序worker绑定/离线编译与报告检查](PROGRAM-WORKER-OFFLINE.md)，复用本包共享锁内的完整重建与同一生成器，头/模块/缓存仅临时存在，检查后删除；仍不执行目标代码、不连接设备。第六十一轮另完成[名称worker绑定/编译/四模式报告检查](NAME-WORKER-OFFLINE.md)，复用相同Reader作用域内的原始冻结输入与已重建目标；原包格式和inspect摘要保持。第六十二轮另有[设置单元正反向方案/阶段核对](SETTINGS-PLAN-OFFLINE.md)，在同一包上明确程序/名称衔接；本包格式、设置投影与完整原始快照保持原语义，不添加完整BK4外层目标或设备执行器。下一交付为D3统一离线演练/审阅，实际机身事务仍缺。C2本人真实材料另行安排，实采前取得实际版本/电量/连接与系统权限；C3完整设置、C4恢复及C5摄影验收分别列缺口。测试见[第五十九轮](../research/LUT链路调查记录-第五十九轮.md)，继续读[交接](../research/HANDOFF.md)。
