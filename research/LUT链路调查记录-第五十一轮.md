# 第五十一轮：有界重枚举、取消、阻塞边界与只读预检

日期：2026-10-21。交付[等待/取消与预检](../docs/CAPTURE-CONTROL-PREFLIGHT.md)，按第五十轮交接完善统一流程。没有真实 USB 枚举、SDK/原生模块调用、系统相机锁、管理员命令、相机或移动盘操作。用户保留原厂 Ver.2.00 和日常卡副本，不要求现在升级；卡副本不是内部 AP/CP/BK4 备份或降级证据。

## 交付与实际边界

1. 普通认证/初始关闭后等待服务设备，明确 stop/服务关闭后等待普通设备；每段最多 20 秒/40 观察，约每 0.5 秒一次，同一 1200 秒预算不重置。只可等待空结果或同端口旧 PID，预期设备连续两次稳定才打开。多机/两 PID 共存、不同端口、错误枚举或权限异常立即拒绝；打开时仍重新要求唯一匹配，不重试认证或接管。
2. 本宿主明确完成的等待区间产生 `ObservationTimeout`，不抹去此前已取得的协议/stop 结果；SDK/控制/传输异常仍未知。只认本宿主记录并抛出的实例，故障注入的同名异常不能冒充已确认等待结束。晚于局部期限返回的 SDK 结果不作为准时到达；全程期限在 SDK 内耗尽则保留未确认动作。
3. 精确 Cancellation token 只做合作式检查，没有回调、原因文本、信号/进程终止或自动重跑。入口、宿主调用、MSC/认证/材料收发前后及轮询之间检查。OPEN 返回对象先归所有者，再观察取消；取得模型全局租约后立即取消会尝试释放，不创建作业。已有对象仍仅单次显式 dispose，不主动重挂或补设备命令。
4. owned 格式增加有界等待起止标记，只存阶段/轮询数/结果，检查器核对确认次数与外层位置；旧的不含等待标记格式继续兼容。单纯等待结束不构成设备观察 ACK，因此只读检查仍可为 `NEEDS_REVIEW_UNKNOWN`；报告中的已知 stop 和“协议结果未丢失”不允许恢复/重试。
5. 新 `capturepreflight` 只读检查固定源码、macOS/Python、两项原生依赖元数据、明确新输出名字/父链及当前空间；不创建目录/锁、导入 SDK、安装依赖或改变权限。实际 CLI 仅输出有限私人 JSON；成功为 `OFFLINE_PREFLIGHT_CHECKED`，所有设备/权限/原厂指纹、管理可抢占和实际采集许可仍 false。

只读审阅已安装 PyUSB 1.3.1 的 core/util/libusb1 源码：枚举、open/close、当前配置、claim/release、detach/attach 的后端接口没有 timeout；bulk/control 带 timeout，但 Python 包装还可在传输前查询配置/声明接口。传输超时不能保证整个调用硬时限，合作式取消也不能抢占阻塞 SDK。没有通过杀死未知设备流程、后台重试或放宽校验来掩盖此缺口，真实采集入口继续关闭。

原厂完整程序门槛、读取范围、固定上游/11/9/10/14/N1/旧 FL23 锁、旧安装器/测试/依赖/默认单份备份不改。QAQLeonard/ma1co/ajalt 来源和完整许可保留，不发布密钥/身份/原始应答、固件/资源或私人材料；无原厂完整材料正例、实机重枚举或色彩验收。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_capturecontrol.py' -v` | 新等待/取消 19 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_capturepreflight.py' -v` | 新只读预检 14 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_captureowned.py' -v` | 既有统一装配 37 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_capturemac.py' -v` | 既有宿主 49 项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究 740 项通过，新增 33 项 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧 Mac 39 项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游 8 项通过；合计 787 项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产通过，未连接相机 |
| `.venv/bin/python -B research/output/custom-round51/audit_capture_sources.py` | 69 条 AST 观察/48 来源身份、固定清单通过，新增后端无 timeout/隐式前置调用核对，无 SDK 导入/归档执行 |
| `.venv/bin/python -S -B research/output/custom-round51/exercise_controlled.py` | 八种固定来源/自制材料及实际只读检查 CLI、另一次实际电脑端预检 CLI 通过，无设备调用 |
| `.venv/bin/python -B research/output/custom-round51/audit_public.py` | 公开 AST/JSON/链接、隐私资产、锁/归档/受保护路径和精确清单通过 |
| `git diff --check` | 通过 |

新专项覆盖空/旧 PID/稳定到达、地址变化、多机/错端口立即拒绝、服务/普通等待耗尽、SDK 超时与伪造同名异常、局部期限晚返回/全程期限在调用内耗尽、入口/取得租约/OPEN/轮询/MSC/材料取消、清理主错误保留、token 子类拒绝、等待标记篡改和旧格式兼容。预检覆盖缺/异版本元数据、系统/Python/空间分项、新名字/已有目录/文件/链接/仓库内路径/父链拒绝、不创建目录、隐私有限错误及实际退出码、-S 导入无 SDK。

预检测试最初引用不存在的模块 ROOT 常量，已修正为真实仓库路径，未改变拒绝实现。等待测试最初直接导入 TestCase，导致发现器额外重复运行已有 37 项，改为模块引用；最终新增只计 19+14，全量 740 不重复计数。取消后租约释放失败保留原取消错误，不将关闭失败解释为已确认物理释放。

固定来源演练仍仅用内存密钥和独立标准库 SHA-256 包预期，未执行归档 Python/目标代码。原厂策略下全尺寸全零 AP 99,960,744 字节必须拒绝，不读 CP/快照；八个场景依次为程序拒绝、半包、认证控制不明、材料发送不明、服务 dispose 不明、返回身份变化、服务等待耗尽、普通等待耗尽。实际 -S 检查 CLI 均退出 1，分类未完成及七个未知；等待耗尽可保留协议结果已知，检查器仍不补观察 ACK。

200/144/52/82/146/194/140/233 项输入（含目录）前后内容、inode、权限和 mtime/ctime 不变，不承诺 atime；临时自制目录清理。预检使用另一个明确自制的新输出名字，实际 CLI 退出 0，只报告电脑端检查，不创建目录、不加载 SDK/获得设备许可。汇总只留忽略的 `research/output/custom-round51/`，不记录密钥、挑战、身份或私人路径。

## 交接与发布

总计划只更新 N3，发布部分仍四列；滚动交接/索引单独维护。本地原分析报告/计划附录原样保留、不发布，私人目录不读取/暂存；旧历史归档和受保护路径不改。起点 `0889d85a00c803811d38d7784df271171ef80903` 的[第五十轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39565921459)已核对 completed/success。提交前列出实际测试，只正常推送 lut-photo/main，提交/新 CI 以最终报告为准。

第五十二轮整理可审阅的原生协调候选和首次采集清单：共用已经验证的所有权/等待/取消/持久证据逻辑，明确不可抢占 SDK 的人工停止/现场保留边界，冻结固定只读范围与真实版本/电量/权限门槛。先用假系统审阅差异，不把预检通过当设备就绪，不放宽原厂 2.01 或未知状态，不直接运行设备入口。

进入真机采集前再提示具体范围/配合；当前保留原厂 2.00 卡副本，不需升级/连接相机、读取移动盘、Docker 或惠普电脑。第三方修改升级包另固定仓库/版本及迁移/恢复，不替代现有原厂门槛。实际协议/重枚举/新鲜同机材料、事务/bound worker/恢复、双独立介质及 N4 色彩验收继续独立安排；真正 3D LUT 支线维持第二十八轮未闭合。
