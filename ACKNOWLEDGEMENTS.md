# 致谢与贡献边界

## macOS 适配来源：MDHan/a7c2-fl23-macos

本研究仓库继承 [MDHan/a7c2-fl23-macos](https://github.com/MDHan/a7c2-fl23-macos) 的 macOS 适配、测试、文档及提交历史，研究起点为提交 `5babef40bba986efdd0573380c0ff9f8a027495c`。原有版权和 MIT 声明保留；新增机外 LUT 工具与只读研究不改变原作者的贡献归属，也不扩大已有实机验证范围。

## 主要上游：QAQLeonard/a7c2-fl23-research

本项目直接依赖 [QAQLeonard/a7c2-fl23-research](https://github.com/QAQLeonard/a7c2-fl23-research)，固定提交 [`dd01c07a2a5df004d709595a43ebafe81bbd8fae`](https://github.com/QAQLeonard/a7c2-fl23-research/tree/dd01c07a2a5df004d709595a43ebafe81bbd8fae)。感谢原作者公开研究结果、源代码和验证边界。

上游贡献包括：A7C II 2.01 的补丁位置与前后完整哈希、FL2/FL3 色彩数据和映射、原生安装/恢复模块、机内诊断、WBI 处理、运行状态读取、参数保留验证，以及原安装器。**这些研究与实现不属于本项目新成果。**

Mac 适配层通过 Python 继承与会话替换调用固定上游实现，不修改下载的上游文件。新增部分包括：macOS 存储枚举与接口接管、句柄所有权、异常中断处理、备份落盘与核验、CLI 阶段限制、连接返回状态以及测试/文档。`workflow.py` 的准备流程改编自上游 `app.py`，相应原作者 MIT 声明随仓库保留。

## Sony-PMCA-RE

USB 服务协议来自 [ma1co/Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE)，上游固定提交 `a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0`。其 MIT 许可见 [docs/Sony-PMCA-RE-MIT.txt](docs/Sony-PMCA-RE-MIT.txt)。本项目不宣称独立实现该协议。

## 上游研究参考

按照原项目 NOTICE 保留来源：

- [lzh2016zzz/a7cr-fl23-research](https://github.com/lzh2016zzz/a7cr-fl23-research/tree/43ba74441c8f10459ade41e84a379ad8005e6ef4)：A7CR FL2/FL3 的移植、参数、标签与 WBI 研究参考。本项目没有直接套用 A7CR 偏移。
- [YuuLuo/a7c2-service-preload](https://github.com/YuuLuo/a7c2-service-preload/tree/1619f938663a36d41e72302a8cfee89a0f6acd1a)：A7C II 服务模式研究参考，原文档许可为 CC BY-SA 4.0。本仓库仅链接说明来源，未复制该项目文档。
- [ma1co/fwtool.py PR #52](https://github.com/ma1co/fwtool.py/pull/52)，上游注明的固定提交为 `3955d7890fc38daf942bb52827599bfe35de4a14`：官方固件离线解包分析参考。本项目运行时不调用或附带该工具。
- Sony A7C II 2.01 和 Alpha 1 II 4.00 是上游程序/色彩研究的数据来源。Sony 商标与固件资料权利仍归权利人所有。

本项目与上述作者及 Sony 无官方合作或背书关系。
