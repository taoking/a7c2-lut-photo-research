# 第六十六轮：机外预览输入错误的中文诊断

2026-10-22。继续无需真机的有限任务：补齐第六十五轮预留的CUBE/域/桥接/ICC等输入错误提示。相机仍按本人已确认的原厂2.00记录，待自行官方升级2.01后另行安排首采。本轮没有USB/SDK/设备操作，没有读PRIVATE或移动盘，没有增加设备执行器。

## 交付与实现范围

原preview只给异常类型，难以判断应检查哪类输入。新增[inputerrors](../lutphoto/inputerrors.py)的固定类别/中文建议，以及[使用文档](../docs/COMPUTER-ONLY-PREVIEW.md#输入失败时怎么处理)。项目/模型、CUBE格式/输出范围、ST桥接/域、图片格式/色彩声明/ICC、分区掩码、冻结锁、来源绑定、输出目录、缺依赖与未完成等分别提示；未知错误只给有限兜底，不声称定位到精确根因。

在原校验处补InputProblem（ValueError子类），阶段上下文只归类失败；终端不使用异常原文、输入路径、LUT标题、ICC或未校验的JSON字段。原消息保留供本机Python调用者调试，异常链仍可能含私人信息，不应直接公开。未为失败新建报告/回执格式；部分目录保持，不覆盖、不续跑或自动重试。

参数错误仍退出2；预览输入/保存/输出错误退出1。原阈值超限仍输出参考图和诊断、退出1，正常通过退出0。没有静默转换Log、删除ICC、忽略冲突色彩声明、放宽域/模型/候选/来源或阈值检查。旧demo/build维持原错误摘要和参数行为；不改变N2计算/输出schema或生产来源规则。

独立AST检查将新增诊断导入/上下文移除、InputProblem还原为原ValueError，并排除有意变化的offline.main呈现：原nativefit、images及offline其余函数的语法树与6da8b41一致。由此确认原计算、接受谓词、调用顺序、格式没有随提示改动；这不证明实际Sony ISP模型或相机恢复。

## 测试命令与实际结果

```sh
.venv/bin/python -B -m unittest research.tests.test_preview_diagnostics research.tests.test_preview research.tests.test_offline research.tests.test_nativefit research.tests.test_nativevalidate -v
.venv/bin/python -B -m unittest discover -s research/tests -v
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v
.venv/bin/python -B -m macfl23 check
.venv/bin/python -B -m unittest research.tests.test_preview.PreviewTests.test_help_is_standard_library_only_and_no_program_or_enable_flags_exist research.tests.test_preview.PreviewTests.test_ST_declaration_is_required_before_any_input_or_output research.tests.test_offline.OfflineTests.test_cli_help_is_standard_library_only_and_override_errors_are_private -v
git diff --check
```

相关79项通过，其中新增8项；完整研究988、Mac39、上游8合计1035项通过，固定源码/资产check通过。最后仅将中文非法参数提示限定preview、保留demo/build原提示后，额外复测上述3项帮助/参数测试通过；没有重复计入1035项。

新增测试用实际自制错误文件核对缺失/重复键项目、奇异模型、错误CUBE/HDR输出、缺失/不可读桥接、域拒绝、无标签/冲突色彩/无效ICC/透明图片、无效掩码、缺失参考图、错误冻结锁及已有目录；均失败且不生成完整预览。另测来源变化、未知/导入错误只给固定提示、不重试、旧原文保留在Python异常中而不进入预览终端。原有测试继续覆盖完整绑定/数学结果、超限不能导入、输入不变与无设备调用等。

实际子进程CLI另跑自制有效项目0、已有目录1、无ST桥接1、非法参数2；stdout/stderr不含临时私人根路径，未产生机身包。素材/输出/日志仅在私人临时位置及忽略的custom-round66，全部自制，不是本人风格筛选、Sony ST标定或照片质量验收。

公开审查核对AST/JSON、Markdown目标/锚点、格式/命令、个人路径/密钥表示、固定锁/历史/旧安装器和明确变更清单。总计划只更新N2证据，四列表16行保持；原本地plan附录、README/DELIVERY评估入口及4份未跟踪分析逐字保留，不纳入本轮提交。PRIVATE忽略保护保持，不读内容；不改变依赖或上游署名许可。

上轮6da8b41的[CI 39750290705 / success](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39750290705)已实际核对；最初两次网络失败不能视为CI失败，后续重查确认completed/success。本轮提交/推送/CI以最终回复及忽略publication-receipt.json为准，只正常推lut-photo/main。

## 交接与剩余条件

N1完成；N2离线完成但真实ST与相机精度未证；N3部分完成、N4未执行；D4仍缺实际通信/退出和同机74材料。中文提示不增加上述完成比例。没有本人CUBE/参考图时不自动搜盘或新增批处理框架；后续可用明确来源的实际素材筛选一种风格，按既有摄影工作表准备独立验收。

既有回滚/持续供电评估保留。D5固定协议、持久化证据及恢复后验证可继续针对具体缺口审阅，实际部署/保存/独立读回/执行器仍需D4及另行受控验证；不以更多模拟层替代。D5写入前明确合法源状态、可操作恢复步骤、实际预算及独立介质内部备份；持续供电也不能保证所有异常可恢复。D6真实ST/单风格摄影后置，进入相机阶段前提示。本人自行升级安排和PRIVATE菜单设置的边界见[当前交接](HANDOFF.md)。
