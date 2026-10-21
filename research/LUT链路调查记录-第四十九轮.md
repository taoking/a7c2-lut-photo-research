# 第四十九轮：Mac 宿主生命周期与固定 MSC 身份独立代码

日期：2026-10-21。按[第四十八轮交接](LUT链路调查记录-第四十八轮.md#交接与发布)，新增[宿主/身份代码](../docs/CAPTURE-MAC-OFFLINE.md)及离线测试。本轮没有枚举 USB、读取移动盘、运行系统相机锁/管理员命令/原生模块或执行相机查询。用户保留原厂 Ver.2.00，既有卡副本不能替代内部程序/设置备份；不要求现在升级。

## 交付与实际范围

1. `capturemsc.py` 明确 TUR、两次 INQUIRY、Sony 型号请求写/读五个事务，替代旧包装中的隐式初始化/重试。完整查询 14 次原始收发，6 写/8 读；明确发送长度、数组响应、共享剩余期限及有界解析。未知不补发，完整错误不发 REQUEST SENSE、clearHalt 或 busy 重试。
2. 序列号摘要来源/编码与旧 `getCameraInfo → core.sha(info.serial.encode())` 一致：对四字节序列号的小写十六进制文本求 SHA-256。初始/返回各新开句柄重新查询，比较同来源身份和物理端口链；不是拿缓存字段与自身比较。型号查询不能识别固件版本，完整 AP/CP 原厂指纹门槛仍须由材料验证。
3. `capturemac.py` 提供尚未被工具实例化的 `_NativeOps` 绑定：固定全局锁、受限 ioreg/diskutil、SDK 清点/新开、当前描述符、驱动/接口管理和原始读写。构造/导入无设备操作；测试注入假系统/SDK，不把 SyntheticDevice.close 当成 PyUSB API。
4. 独立内部宿主阶段要求先全局租约再清点/卸载，唯一目标、稳定完整磁盘拓扑、仅正常卸载、重新匹配设备代次/端口、普通 detach/claim、服务 active/未知拒绝。单一所有者在 OPEN 返回后、日志 ACK 前收养句柄，失败仍释放；关闭先失效视图、只显式尝试一次 SDK dispose。健康普通关闭 release/必要 attach，切换/未知/日志失败不主动重新挂接或补命令，保留主错误。
5. 新 11 成员元数据清单在既有 9 成员认证来源外补充 MSC 初始化/驱动文件；核对完整固定包和每个成员 SHA/Git blob，不导入/执行归档 Python，不公布密钥/原始身份/设备包。QAQLeonard、ma1co、ajalt 署名和完整许可保留，旧锁/指纹/偏移不变。

**尚未完成统一装配。** 这些宿主方法没有执行认证、服务切换、固定材料收取或 stop；演练改变的是假系统枚举阶段。未连接既有 captureraw/pipeline、Store、全局→作业锁顺序的实际协调器及三种检查报告，不生成任何完整采集报告，也没有新增可运行的采集 CLI。

独立宿主预算 65,536 接受字节、共享 120 秒，仅用于两次身份查询和宿主生命周期测试；未来须与认证/材料共享完整预算。MSC 原始读写最长 5 秒/剩余期限，系统命令有输出过程上限和子进程回收。部分 PyUSB 管理 API 没有 timeout 参数，只能返回后查期限；不能宣称已有可中止的原生管理总时限。IORegistry/SDK 同一瞬间身份绑定、显式后端选择也未验证。

CSW tag/residue 一致性、唯一端点和服务 vendor class 是新保守限制，没有真实机身兼容证据；固定上游未检查 tag/residue，不能据此声称成功兼容。SDK dispose 可隐式释放接口，终结行为未验；一次显式调用不是物理释放或零 USB 栈活动证明。版本/电量必填仅阻止调用方遗漏，合成 2.01/75 不代表用户相机读数。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_capturemsc.py' -v` | 13 项通过，独立 MSC 报文/序列号编码、短响应及失败停止 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_capturemac.py' -v` | 45 项通过，假系统/SDK 管理、锁/磁盘/接口/释放/日志/超时故障 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 666 项通过，含新增 58 项 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 原 Mac 39 项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游 8 项通过；合计 713 项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产校验通过，未连接相机 |
| `.venv/bin/python -B research/output/custom-round49/audit_capture_sources.py` | 54 条 AST 观察、44 来源身份；新 11 和既有 9/10/14、N1 的 26/旧 46 成员通过，无设备导入/归档执行 |
| `.venv/bin/python -S -B research/output/custom-round49/exercise_host.py` | 11 固定成员、4 自制序列号编码、6 个独立宿主模拟场景通过；无 USB/原生边界调用或归档执行 |
| `.venv/bin/python -B research/output/custom-round49/audit_public.py` | 公开 AST/JSON/链接、隐私资产、锁/归档/受保护路径与精确清单通过 |
| `git diff --check` | 通过 |

专项覆盖正常返回新查询、改变序列号/端口/枚举地址、多机/已有服务、锁忙、内部盘/父盘不明、稳定/卸载后拓扑变化、仍挂载、部分 detach/claim、描述符变化、管理 None/布尔值区分、日志 INTENT/ACK 故障、超时/短包/未知后零额外协议命令、release/dispose/unlock 错误和主错误保留。系统命令测试用假进程/选择器验证输出超限和超时后终止回收，不实际运行命令或打开系统锁。

最初测试把两次完整查询的写次数误计为 16，独立报文和运行结果均为 12，已更正测试预期；没有放宽实现检查。来源审计最初直接匹配 hashlib 表达式，而旧 Mac 实际调用 core.sha，修正为分别核对调用和固定 core 实现后通过。最终全量回归包含修正后的代码/测试。

六个固定来源/自制材料场景：仅宿主成功、返回身份变化、首次读取未知、claim 失败、OPEN ACK 失败、release 失败。成功只代表模拟宿主阶段；其余分别停止并显式释放已接收对象一次，不补命令。原始身份/报文不写入汇总；证据仅留忽略的 `research/output/custom-round49/`。没有执行上游纯哈希参考或设备模块，本轮不重复前轮材料压力测试。

## 交接与发布

总计划仍四列，本轮只更新 N3；滚动交接/轮次索引另存。已有本地分析附录和报告原样保留、不发布，原分析文件指纹保留；私人目录不读取或发布；不覆盖既有工作目录。旧安装器/默认单份备份/锁/依赖/原测试及历史归档未改。起点 `7449857151bfcae77898c1b25ec1a26267449dc9` 的[第四十八轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39553013333)已确认 completed/success。提交前列出真实测试命令/结果，仅正常推送 lut-photo/main，提交/远端与新 CI 状态以最终报告为准。

第五十轮优先把宿主所有者与既有同服务句柄认证/材料/stop、Store 和检查证据统一装配，保持公共演练精确假对象门槛。明确预算合并、全局→作业锁及发布/关闭顺序、SDK 管理阻塞/后端选择、未知关闭/主错误与日志故障，仍先离线；完成之前不开放采集 CLI。

真实 MSC/CSW/服务端点/回显/排空、完整原厂材料和新鲜同机来源仍待受控验证；事务/bound worker/恢复、双独立介质及 N4 色彩验收后置。进入设备阶段前提示，当前不需相机、Docker 或惠普电脑。若另评估第三方修改升级包，需固定具体仓库/版本和迁移/恢复链，不借此替代原厂 2.01 门槛。真正 3D LUT 支线仍保留第二十八轮未闭合状态。
