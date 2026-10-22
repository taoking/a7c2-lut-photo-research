# 第六十五轮：无真机依赖评估、独立预览与摄影准备

2026-10-22。用户要求先继续不需要真机验证的开发，并评估还有哪些可先处理。设备侧D1–D3原收口边界保持；本轮按新指示并行做机外实用入口/摄影准备，不增加设备模拟、假回执、写入许可或进度百分比。本人仍原厂2.00，会自行官方升级2.01后再采集；安排已确认，不假定升级完成。

## 评估与选择

现有nativefit能拟合/渲染，nativevalidate能配对标定/冻结/验收；不重复实现算法和指标。实际缺口是统一入口的build先要求内部AP/CP/设置材料，只有自制demo能整链演示，尚无一个不依赖机身备份的显式项目入口。因此优先补preview和可读超限诊断，再补面向拍摄的工作表。评估与有限清单写入[交付计划](../docs/DELIVERY-PLAN.md#等待真机期间可并行的有限任务)。

| 可先做 | 本轮安排 | 能证明什么 |
| --- | --- | --- |
| 无内部材料的单风格预览 | 已实现offline.preview | 暂定模型下的拟合/图像/整体阈值结果，不是机内等效 |
| 超限/表达边界说明 | 同次实现报告 | 列出留出/本图超限、触限/范围、裁切/参考域计数与缺失分区 |
| 摄影验收准备 | 工作表已提供 | 预先约定来源/域/模型依据、场景分组、阈值/观感；不是实拍或验收完成 |
| 实际候选风格筛选 | 有本人CUBE/参考图后复用preview另存比较 | 不需要新拍或内部备份，但当前未提供材料，不声称真实风格筛选完成 |
| D5静态审阅 | 可先审协议/格式；本轮不自动另开 | 真实部署/写入/读回/恢复仍依赖同机材料及受控验收 |

常见输入域/桥接/ICC的有界中文提示、同图多结果轻量汇总可按实际使用问题继续补充。DCP/自动桥接、GUI、Windows/Docker、多槽管理当前优先级较低，仍在首版后；真正3D LUT关键运行配置/有效像素/MAIN身份时序不能用更多静态追址关闭，保留原研究支线。

## 代码交付

[新预览文档](../docs/COMPUTER-ONLY-PREVIEW.md)给出真实CLI和自制可运行例子。preview只消费项目/模型/CUBE/参考图及可选显式掩码/冻结锁；复用原nativefit.fit/evaluate，不加载归档或真实SDK，不读取程序/设置/68资源，不生成机身包/worker/回执。输入域、模型依据、ST声明仍需明确，不能把普通sRGB或改标签的电影Log LUT认定为Sony ST。

输出candidate/evaluation、中文RESULT.md及preview.private.json，均在仓库外新私人目录。报告包括图、留出/本图误差、逐项超限、灰阶/中性细项、系数触限/范围、裁切及参考域计数、显式分区；缺少或空掩码不记零误差/通过。参考域计数包含重复评估，不等于独立像素数。模型暂定、来源/ST身份未认证、实际机内精度/恢复仍false。

通过项目事先声明的整体离线阈值：CLI退出0 / OFFLINE_PREVIEW_CHECKED；超限：保存图/诊断但退出1 / OFFLINE_PREVIEW_LIMITS_EXCEEDED。错误/输出失败也非成功，保留部分结果，不覆盖或续跑。该单图判断不代替原多场景冻结验收、收敛/触限/分区规则和人工摄影观感。

原build仍经完整源身份/设置/候选门槛，超限表不能被导入，不新增enable/政策覆盖。提取_reference_binding复用项目/模型/桥接、候选与图的核对；同一原始JSON用于元数据与SHA绑定，旧包还要求候选JSON/表字节精确一致。原格式、算法、固定来源、worker/SDK/依赖不改。demo/build相关旧回归通过。

[摄影工作表](../docs/PHOTO-ACCEPTANCE-CHECKLIST.md)是可先填写的Markdown，不是新JSON格式或已通过数据；复用原nativevalidate契约，不把空项、单位响应、场景ID或自制图当物理证据。真实配对/响应/独立场景、机内预览/JPEG/回放/冷启动与恢复仍后置。

## 实际验证

```sh
.venv/bin/python -B -m unittest research.tests.test_preview research.tests.test_offline research.tests.test_nativefit research.tests.test_nativevalidate -v
.venv/bin/python -B -m unittest discover -s research/tests -v
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v
.venv/bin/python -B -m macfl23 check
git diff --check
```

新11项及原offline/拟合/冻结验收共71相关测试通过；研究980、旧Mac39、上游8，共1027回归通过，旧check通过。新测试核对无归档/程序/包调用、原文件字节/时间/权限保持、超限仍诊断且原导入拒绝、ST声明、模型/候选/表变更拒绝、显式分区与缺失区别、无桥接Log拒绝、真实CLI无SDK/编译器、无site帮助/非法开关、输出保护及短stdout不重试。首版测试夹具多上下文换行缺括号，加载失败；修正测试语法后执行最终回归，未改算法/门槛。

实际子进程运行自制暖色项目：退出0，RGB MAE 0.0008537815、Delta E76 P95 0.41902817；自制通道交换/严格阈值项目：退出1并保留4个超限项，已有输出目录再次运行退出1且保留原结果。没有程序/设置包产生。这些全为自制数学材料，不证明真实风格、Sony ST或照片质量。输出与位置记录仅在忽略的custom-round65，不公开私人路径/素材。

公开AST/JSON、Markdown命令/链接/锚点、空白/隐私、固定来源/历史/旧安装器/依赖/旧测试及明确变更清单检查通过。根PRIVATE忽略保护保持，未读内容；原plan本地附录、未跟踪分析报告保留。初始未提交HANDOFF已在忽略目录留存，用户的2.00确认/自行升级安排完整保留并更新本次交接。总计划仍四列16行，只补N2证据，不提升N3/N4完成程度。

上轮D4代码3dd83a6的[CI 39646754013 / success](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39646754013)已核对；它不是本轮代码CI。本轮提交/远端/CI见最终回复与忽略publication-receipt.json，只正常推lut-photo/main。

## 下一步与真机边界

先用明确来源/输入域的CUBE和已有参考图筛选一种风格，按工作表记录拟合问题与正式验收标准；无素材时不自动搜盘或下载。遇到明确软件问题可继续修复，不为轮次增加设备模拟框架。

D4电脑端证据保持，真实SDK通信/退出、同机完整AP/CP/设置/68资源仍缺。相机继续保留2.00，等待本人官方升2.01实际确认；之后取得当时电量/MSC/权限/私人位置/明确只读范围再采集，不调用prepare/diagnose试2.00。D5写入/恢复及两份独立介质内部备份、D6真实ST/一种风格摄影验收继续后置，菜单PRIVATE副本不补内部备份或降级证据。
