# 第六十三轮：D3统一离线入口与收口

2026-10-22。用户指示“好的 开始d3”。本轮完成[交付计划](../docs/DELIVERY-PLAN.md)D3，D1–D3离线冻结；N3仍部分完成、N4未执行。没有连接相机、SDK/USB操作、移动盘读取、临时机内模块或持久化写入；本人相机仍原厂2.00，不自动升级。

## 交付

新增[统一入口](../docs/OFFLINE-WORKFLOW.md) `lutphoto.offline demo/build`。demo是自制微暖仿射CUBE、RGB图、单位响应模型以及微型AP/CP、BK4包裹、68资源；不读取外部程序/归档，不把演示称为Sony ST标定或摄影风格。策略仅内部固定生成，全零归档标记；生产读取/构建均拒绝该材料，不开放策略/固件/身份覆盖或启用开关。

build显式接收真实项目/ST图、AP/CP、RAM/保存设置/角色、固定68资源及一个槽/名称。生产固定来源、完整程序与设置门槛在拟合/输出创建前执行，来源策略不来自清单；保留现有全部来源保护，首版真实采集仍只限定原厂2.01，不扩设备范围。

统一流程调用原nativefit.fit/evaluate、slotbundle.create/Reader、programworker/nameworker metadata和settingsplan._build；使用同一目标生成器，不复制变换算法。输出候选表、sRGB参考/预测图、误差、150材料私人包、中文RESULT.md和含私人属性方案的result.private.json。拟合留出/本图须满足事先声明的整体阈值；没有分区材料就显示不可用，不宣称分区摄影质量通过。

slotbundle仅抽出内部_freeze/_read_frozen/_regenerate供闭合演示复用，原150文件清单、格式、CLI和固定来源入口不变。锁内完整读回、源/目标/逆向重建，消费前/后与关闭检查保留。两类worker及设置方向哈希与同一包绑定；项目/模型/桥接/图片和候选文件再核对。演示另外写出并重验source/target/restored的6份自制快照；生产不会伪造目标/恢复快照或执行报告。

此次不改C/ABI/加载器、不重新编译、不构造新模拟传输或回执框架。D1/既有程序交叉编译证据见原记录，不当作本轮编译或执行证据。完整BK4仍只读；单位方案、保存规则和名称→程序→设置、逆向设置→程序→名称及未知停止顺序沿用D2，不提供设备执行器。

## 实际CLI演练

执行 `.venv/bin/python -B -m lutphoto.offline demo --directory <仓库外新私人目录>`，真实子进程退出0；150材料包、6程序窗口、9设置单元、3快照阶段、非零1,215字节表通过。参考PNG像素确实与输入不同，不能仅靠文件元数据变化认定色彩变换。

| 自制数学材料 | RGB MAE | Delta E76 P95 | 样本 |
| --- | --- | --- | --- |
| 随机留出 | 0.0007210048 | 0.34293487 | 4,096 |
| 自制图 | 0.0008537815 | 0.41902817 | 196,608像素中固定种子抽65,536 |

输入与校准都是自制；这只是本次模型拟合误差，不是Sony ISP/真实JPEG/肤色验收或其他LUT的精度保证。默认阈值是示例，正式摄影验收另设。

使用真实固定v2.1归档运行生产build并提供上述微型演示程序，退出1且未创建输出；真实生产slotbundle.inspect也退出1；重用已有演示目录退出1且保留原结果。原生报告、执行/读回/恢复及同机来源标志保持false。结果与程序只在仓库外私人目录，忽略的custom-round63/exercise.json记录统计，demo-location.private.json只保存本机位置，不公开。

## 一次整体审阅

逐项沿调用路径检查输入声明与阈值、固定来源/整程序身份、冻结清单与锁、候选/渲染绑定、三契约/设置顺序、精确逆向与作用域、失败/输出/公开边界。

开发中修正三点：

1. 合并结果不只并列几份报告：最终Reader内重新绑定显式项目/模型/桥接、图片及冻结候选。替换候选、改变模型/图片均停止；非零表演示避免只验证恒等表。
2. 补充缺少拟合依赖时的有界错误，help/参数错误仍仅标准库；不把用户路径放入终端异常，短stdout不成功、不重复流程。
3. 拆分Reader后补回重建结束、消费开始前的文件复核；新增测试证明重建期间变更会在消费体执行前拒绝。消费后/关闭失败同样不能发布完整结果。

相关回归已通过。仍有明确设备依赖，不能由源码审阅关闭：实际SDK/权限与通信退出、同机来源/新鲜度/角色/容器、所有68资源真实读回、模块部署/触发、逐属性独立读写与保存、其他运行组保留、重载/冷启动、实际恢复以及真实ST/独立照片验收。原生名称报告不含资源哈希/job ID的限制沿用D1；整包一致性和顺序列表不能替代这些证明。

## 测试与检查

以下均为离线；源码修正后执行最终回归。没有更换环境/依赖或修改原安装器锁。

```sh
.venv/bin/python -B -m unittest research.tests.test_offline research.tests.test_slotbundle research.tests.test_programworker research.tests.test_nameworker research.tests.test_settingsplan -v
.venv/bin/python -B -m unittest discover -s research/tests -v
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v
.venv/bin/python -B -m macfl23 check
git diff --check
```

新18项加包22/程序18/名称19/设置21，共98相关测试通过；研究969、旧Mac39、上游8，共1016通过；旧check显示源码和资产完整、未连接相机。新测试包含实际CLI/无SDK导入、真实拟合与原生成器的自制正例、原材料字节/时间/权限保持、演示隔离、非法来源提前拒绝、阈值失败、项目/图片/候选绑定、重算哈希后的目标篡改、消费前/最终关闭失败、已有/链接/共享/仓库输出拒绝、依赖/输出错误。正例的任意策略替换仅在测试内部，生产CLI不提供该能力。

整合源码16项观察及14固定归档成员检查通过；固定提交 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`、归档SHA `8c6c30448219f4e865e8005d2ffa789248e984d73b0f9342035f7065a1a232f7` 保持。静态检查不能代替机身执行。公开AST/JSON、Markdown命令/链接/锚点、空白/隐私、旧历史/锁/安装器/依赖/旧测试不变及明确变更清单检查通过。原本地plan附录/未跟踪分析报告逐字/哈希保持，PRIVATE先排除且未读内容；发布总计划仅原四列16行。

第六十二轮提交2a957bf的[CI 39641235560](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39641235560)已复核completed/success；当前提交/远端与CI以最终回复及忽略的publication-receipt.json为准，不能把前轮CI作为本轮通过证据。只正常提交推送lut-photo/main。

## 收口与交接

[四列总计划](../plan.md)、[交付计划](../docs/DELIVERY-PLAN.md)、README、[短交接](HANDOFF.md)和[轮次索引](ROUNDS.md)已更新。D1–D3冻结，不再添加模拟研究轮次；下一步D4真实只读首采准备，缺陷或真实材料问题才继续离线修复。

[一次配合说明](../docs/OFFLINE-WORKFLOW.md#离线冻结与d4配合)明确：先保留2.00，另行决定是否官方升级2.01/采集范围；实际进入时再取得菜单机型/版本、真实电量至少50%、MSC数据线连接、本人私人位置和系统认证。只读范围需含68UXC，服务认证/选读改变临时状态；不用2.00试2.01入口、不用prepare/diagnose取材料。卡副本不是内部备份；D5前另核验独立介质副本及恢复步骤，D6才做一种风格摄影验收。本轮无需用户现在连接/升级或准备Docker/Windows。
