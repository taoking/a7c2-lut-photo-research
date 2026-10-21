# LUT 照片开发：当前交接

更新：2026-10-21，第五十四轮显式信号/合作式取消及现场保留离线完成。先读根规则、README、[里程碑](../plan.md)、[信号边界](../docs/CAPTURE-SIGNALS-OFFLINE.md)、[首次采集清单](../docs/CAPTURE-NATIVE-CANDIDATE.md)及[本轮](LUT链路调查记录-第五十四轮.md)；历史查[索引](ROUNDS.md)。

## 当前状态与边界

N1完成；N2离线拟合/标定/冻结验收具备，真实ST/色彩未证；N3部分完成。既有NativeOps/Host/候选/Store已经假SDK组合验证，本轮补齐显式进程信号到合作式取消。**真实采集仍关闭**，不自动安装信号处理器，没有任意后端/实际设备命令。SDK/全局锁/权限/协议/重枚举及同机材料、事务/worker/恢复仍缺，N4后置，进入前提示。

用户原厂Ver.2.00，BACKUP-GUIDE保存日常卡副本，暂不升级。移动盘曾连接，本轮未读/核验；卡副本不是AP/CP/BK4或可降级证据。离线不要求升级，第三方修改升级包需固定版本/迁移/恢复另审，不替代原厂2.01完整程序门槛。

本轮无实际SDK/共享库/USB/系统相机锁、sudo/磁盘命令/原生模块或私人材料读取，不搜盘、不用prepare/diagnose取材料。只向新建自制测试子进程发送真实SIGINT/SIGTERM；固定材料演练也显式安装/还原但不发信号。旧安装器/锁/指纹/偏移/测试/依赖/默认单份备份不改，新Custom双独立介质及恢复未证。原分析报告/计划附录及PRIVATE保留不发布，不读私人目录；QAQLeonard/ma1co/ajalt署名/许可保留。

## 本轮结果与证据

- 新SignalCancellation为显式单次主线程作用域，仅精确Cancellation和默认SIGINT/SIGTERM；自定义/忽略/未知、嵌套/重用/工作线程/已取消token拒绝。安装后读回、进入正文前查取消；导入/构造无安装，既有入口默认不变，实际capture仍无条件拒绝。
- 处理器只赋布尔标志，无Event.set/cancel/同步原语、异常/日志/SDK/关闭/进程终止；不保留帧。旧Event线程取消继续有效，既有检查点识别两类请求；无重复信号升级或硬时限承诺。
- 部分安装失败逆序还原；外部新处理器不覆盖，其他自有处理器仍处理。还原读回失败SignalScopeError、restoration_confirmed=false，主异常/还原原因链保留，单次尝试、不假装成功。
- 四个实际信号/自制SDK子进程：配置SIGINT、材料SIGTERM、stop SIGTERM、dispose SIGINT。父进程先确认取消已观察、SDK未返回、所有者/租约/ACTIVE_JOB仍在、协议计数不增，再放行假调用；返回后均OperationCancelled/NEEDS_REVIEW，检查器未知，stop ACK/返回身份不伪造，单次dispose、处理器还原、设备标志false。
- 新24项（20作用域+4子进程）和控制/原生40回归通过；研究804+Mac39+上游8=851、旧check通过。86条AST观察/51来源身份及固定清单通过；八种固定来源自制故障进入信号作用域但不取消、正常还原，实际检查CLI一未完成/七未知。197/143/53/81/145/191/139/230输入内容/元数据不变并清理，6/74源码审阅/电脑预检仍live=false；无归档执行/原厂材料正例。
- 公开AST/JSON/链接/隐私/密钥排除/锁/历史/受保护路径及精确清单通过，汇总仅忽略目录custom-round54。起点b0a2e18e0c72240583b870e59c951233b5e20dca的[第五十三轮CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39585790352)completed/success；本轮提交/CI见最终报告及publication-receipt.json，只推lut-photo/main。

## 下一轮（第五十五轮）：首次采集候选最终审阅

1. 核对第五十四轮提交/CI；集中复核固定来源/只读范围、原厂程序先于设置、同服务认证/材料/stop及两次新MSC、所有权/锁/发布顺序，不新增同类模拟层。
2. 核对信号安装必须先于租约/作业，默认处理器/失败还原边界、未知/关闭失败/退出码和现场保留说明；scope字段/源码预检/模拟成功都不是执行许可。
3. 收口实际执行前缺口与本人配合清单，真实SDK/权限/全局锁、CSW/端点/回显/排空、重枚举和新鲜同机材料独立验收；不以更多模拟延后明确方向决策。
4. 实际采集前另提示范围并取得真实版本/电量/连接；当前保留2.00和卡副本，不读移动盘，不需升级/相机/Docker/惠普电脑。事务/worker/恢复、双独立介质及N4色彩后置。

## 支线与复核入口

M2–M4维持[第二十八轮](LUT链路调查记录-第二十八轮.md#遗留与交接)未闭合：动态配置、有效像素传输、MAIN身份/时序仍缺，不自动逐轮追踪，原生拟合/适配/信号验证不能补齐。

[采集设计](../docs/CAPTURE-DESIGN.md)、[材料清单](../docs/IMPORT-MATERIALS.md)、[控制预检](../docs/CAPTURE-CONTROL-PREFLIGHT.md)、[原生离线组合](../docs/CAPTURE-NATIVE-OFFLINE.md)及[只读检查](../docs/CAPTURE-INSPECTION.md)仍有效。总计划发布部分仅四列，每轮独立、交接滚动覆盖，[历史归档](../plan-history-through-14.md)不改；实际命令见[本轮](LUT链路调查记录-第五十四轮.md#实际测试命令与结果)。
