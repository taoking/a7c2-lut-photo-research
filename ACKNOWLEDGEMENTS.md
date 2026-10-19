# 致谢与贡献边界

## macOS 适配来源：MDHan/a7c2-fl23-macos

本研究仓库继承 [MDHan/a7c2-fl23-macos](https://github.com/MDHan/a7c2-fl23-macos) 的 macOS 适配、测试、文档及提交历史，研究起点为提交 `5babef40bba986efdd0573380c0ff9f8a027495c`。原有版权和 MIT 声明保留；新增机外 LUT 工具与只读研究不改变原作者的贡献归属，也不扩大已有实机验证范围。

## 主要上游：QAQLeonard/a7c2-fl23-research

本项目直接依赖 [QAQLeonard/a7c2-fl23-research](https://github.com/QAQLeonard/a7c2-fl23-research)，固定提交 [`dd01c07a2a5df004d709595a43ebafe81bbd8fae`](https://github.com/QAQLeonard/a7c2-fl23-research/tree/dd01c07a2a5df004d709595a43ebafe81bbd8fae)。感谢原作者公开研究结果、源代码和验证边界。 原安装器继续使用该固定版本；新增原生拟合方向另行审计 [v2.1 提交 7e54d60b…](https://github.com/QAQLeonard/a7c2-fl23-research/tree/7e54d60b458847f1befa6cfd614fbf004b8b0b90)，上游 looktool 算法、原生表研究和设备流程均归原作者，见[审计与复用边界](docs/UPSTREAM-V2.1-AUDIT.md)。

N2 离线工具原样接入该 v2.1 的 `native.py`、`color.py` 与 `calibration.py`，表编码/预测、平滑约束拟合、基础颜色函数及配对逆 ST 标定归上游作者；本仓库新增有界输入接入、来源保护、照片/掩码比较及误差报告。三个源文件、完整哈希和 MIT 许可见[固定算法目录](lutphoto/_vendor/sonylooks/README.md)。没有接入上游设备模块或固件资产。

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

第三十二轮 N3 编译探针与合成事务参考上游固定 v2.1 的 `nativebuild.py`、`device_layout.py`、`devicejob.py` 及资源/设置保护边界；使用其要求的 Zig 0.13.0 进行中性代码验证，没有复制或运行设备执行模块、固件资产或私人事务清单。真实机内布局及保护研究继续归原作者，本项目合成模型不替代这些验证。

第三十三轮在独立的 `lutphoto/_vendor/sonycontracts` 原字节保留上游 `resources.py`、`devicesettings.py` 与 68 个资源文件名清单，来源哈希、路径及完整 MIT 许可见[来源记录](lutphoto/_vendor/sonycontracts/README.md)。只使用资源内存改名/逆向和设置比较保护；没有 Sony UXC 内容、真实 AP 识别/描述符适配器或 USB 执行。新增的边界检查、合成格式夹具与命令行见[N3 离线契约](docs/CUSTOM-CONTRACTS.md)。

第三十四轮对照固定上游 `devicejob.py`、`devicelock.py` 及继承的 Mac 全局锁审阅持久化/独占边界，新增独立的合成磁盘日志与只读分类原型；没有复制或运行上游设备执行模块，没有将临时目录的进程锁称为真实相机锁已接通。

第三十五轮通过[独立 14 成员清单](research/upstream-worker.lock.json)固定上游布局、设置、构建、报告与 C 来源；只在临时目录原字节包含上游 C，以自制头编译并附加 ABI 静态断言，完整包许可也纳入固定清单，不分发生成模块或固件衍生资产。源码、保护策略及报告设计归原作者；新增审计入口、严格字节校验和 ELF 范围检查见[说明](docs/WORKER-CONTRACTS.md)。

第三十六轮的新只读 BK4 解析器依据 ma1co/Sony-PMCA-RE 的格式设计，经 QAQLeonard 固定包核对，未引入 setter 或 USB 模块。保留[ma1co 完整 MIT 许可](docs/Sony-PMCA-RE-MIT.txt)及[10 成员来源清单](research/upstream-backup-loader.lock.json)；额外边界限制、reset/布局比较、显式未验证角色及加载链审阅见[BK4 说明](docs/BK4-OFFLINE.md)。

第三十七轮的[完整程序身份/描述符只读实现](docs/PROGRAM-IDENTITY.md)依据同一固定包内 QAQLeonard 的 `device_layout/six/devicesettings` 和 runtime 规则，不导入归档 Python，不公开 AP 模板、补丁窗口或程序资产。自制夹具验证和虚拟流式重建/额外别名限制由本仓库补充；原始设计和来源身份研究归原作者。

第三十八轮[描述符/快照只读绑定](docs/SETTINGS-BINDING.md)沿用 QAQLeonard 的描述符/设置保存保护设计与 ma1co BK4 格式来源，复用此前固定和保留许可的纯比较函数。新增只读连接、reset/分配布局与负例不改变原作者归属；未引入上游设备 planner 或执行模块。
