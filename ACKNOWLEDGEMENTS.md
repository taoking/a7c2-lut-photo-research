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

第三十九轮[材料清单](docs/IMPORT-MATERIALS.md)连接本仓库 N2 候选、QAQLeonard 的程序/标签布局和既有 68 资源内存改名/逆向规则；继续保留 ma1co 设置格式来源与完整许可。新增相对目录/单次 JSON 读取指纹及声明一致性校验不改变上游归属，不分发资源目标、固件或设备事务。

第四十六轮[认证错误传播离线适配](docs/CAPTURE-AUTH-OFFLINE.md)依据同一 QAQLeonard 固定包内 ma1co 的认证报文及兼容哈希行为；原 crypto.py 注明 [ajalt/python-sha1](https://github.com/ajalt/python-sha1)，这里一并保留来源，ma1co 完整 MIT 许可保持不变。[9 成员清单](research/upstream-auth.lock.json)仅记录来源指纹，不分发认证密钥、挑战或原始应答。新增严格原始长度/异常传播、总期限及一次退出只经过假驱动验证，未接入真实 USB 或改变旧安装器。

第四十七轮[统一离线协调器](docs/CAPTURE-PIPELINE-OFFLINE.md)复用上述 QAQLeonard/ma1co/ajalt 来源的认证、固定材料与协议规则；新增共享预算、分别计数、失败冻结及第三种只读证据格式，不改变原协议及保护研究的贡献归属。只用假驱动/自制材料，无真实 USB 接入或新固件资产。

第四十八轮[受限原始接口](docs/CAPTURE-RAW-OFFLINE.md)继续依据固定 QAQLeonard/ma1co/ajalt 的认证、读取与生命周期规则，新增同模拟句柄收发、明确结果类型/期限和单一关闭所有者。只读核对已安装 PyUSB 1.3.1 的原始计数/数组语义，未复制其源码或更换依赖；没有真实 USB、固件或机身资产。

第四十九轮[Mac 宿主与 MSC 身份代码](docs/CAPTURE-MAC-OFFLINE.md)依据 QAQLeonard 固定 v2.1 内 ma1co 的 MSC/Sony 查询与继承的 Mac 接管设计；[11 成员清单](research/upstream-host.lock.json)补充 MSC 初始化和驱动来源，既有锁/许可不改。新增严格长度、CSW 轮廓、同来源序列号摘要与所有权代码只经假系统验证；只读审阅 PyUSB 1.3.1 管理/释放语义，无真实调用、依赖更换或设备资产。

第五十轮[统一所有权离线装配](docs/CAPTURE-OWNED-OFFLINE.md)连接上述 QAQLeonard/ma1co/ajalt 来源的 MSC、认证和材料协议与 Mac 生命周期设计。新增共享预算、借用视图、释放持久证据及第四种只读报告；libusb-package/PyUSB 后端选择仅以假模块验证，未复制其代码或更换依赖。固定来源/真实密钥仅在内存核对，自制材料不构成实机或原厂正例。

第五十一轮[等待/取消与只读预检](docs/CAPTURE-CONTROL-PREFLIGHT.md)延续 QAQLeonard/ma1co/ajalt 固定来源，补充同端口观察、合作式取消及电脑端条件检查。只读审阅已安装 PyUSB 1.3.1 后端管理/传输签名，未复制源码、导入实际 SDK 或更换依赖；严格状态和日志边界不构成原生硬超时或实机验证。

第五十二轮[原生协调候选](docs/CAPTURE-NATIVE-CANDIDATE.md)继续使用 QAQLeonard/ma1co/ajalt 的固定来源、现有认证/读取/所有权实现和完整许可。新增代码由本项目编写；NativeOps 形状的假能力及被动枚举演练不构成实际 SDK、协议或机身验证。只输出来源/请求摘要，不分发认证材料、原厂程序或个人数据。

第五十三轮[假SDK组合验证](docs/CAPTURE-NATIVE-OFFLINE.md)沿用QAQLeonard/ma1co/ajalt固定来源和既有许可。新增自制SDK/系统夹具及所有权测试由本项目编写，不复制或执行USB运行库/归档代码，不分发密钥、机身数据或原厂程序；不构成真实SDK/相机验证。

第五十四轮[信号取消与现场保留](docs/CAPTURE-SIGNALS-OFFLINE.md)由本项目编写，沿用QAQLeonard/ma1co/ajalt既有协议来源和许可；使用Python标准库及自制子进程验证，不复制/执行归档或USB运行库，不发布认证材料或机身数据，不构成实际SDK/相机验证。

第五十六轮[内部采集装配与独立证据](docs/CAPTURE-EVIDENCE.md)由本项目编写，继续复用QAQLeonard/ma1co/ajalt固定来源及既有许可；未复制或执行归档/USB运行库，不分发密钥、程序或机身材料。新增图检查/收尾回执及自制子进程验证不构成实际SDK或相机验收。
