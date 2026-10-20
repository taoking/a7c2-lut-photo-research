# 第四十一轮：独立内部采集流程离线审阅

日期：2026-10-20。交付[采集设计](../docs/CAPTURE-DESIGN.md)，没有新增产品代码、采集 CLI 或 USB 适配器。本轮不连接/枚举 USB，不调用相机安装器设备命令、sudo、临时模块或任何相机操作，也不读取私人材料。原厂官方升级和日常备份仍未收到实际完成结果，不把意愿记为完成。

## 审阅结果与设计决策

1. 固定 transport 的文件读取为 Jiritsu 15/17，PMCA 内存/保存快照为 `(0x603,5)` 配 1/0；它们不要求先运行 runtime/probe。首版拟仅开放固定服务读取，禁止上传/删除模块、写程序/设置、WBI、重载和 preload；进入服务及查询仍为设备操作，实际 Sony 端行为尚未验证。
2. 现有 Mac 正常身份查询没有消费固件版本；2.01 菜单只是先决信息，完整原厂配对在程序读完后验证，已知 2.00 必须进入服务前停止。首版只针对原厂 2.01，不把离线识别的其他来源状态扩大为采集支持范围。
3. 上游 `_capture` 在完整程序识别后先执行 runtime，再读取快照/资源，最后才写主机备份；旧 prepare 还包含候选/预检查。新设计先排他保存原件，不调用这两个高层流程来采集。
4. Bounded 限时及 Senser 1 MiB 分包不等于整个响应有界。新实现须在接收累计前限制数据，按固定材料计算协议开销/累计预算并保留全程期限；主机排他文件/目录同步与读取未知分别处理。
5. BK4 扫描顺序、相似字段、重复 SHA 和一次会话不证明 AP/CP 角色、完整外层容器或原子时刻；旧 CP 直接读仅两个键，N3 保护范围四个。保留原件与私人观测来源，不自动填写角色或把材料清单变成写入资格。
6. C0–C5 区分主机/版本预检查、全局锁/普通身份、服务认证、程序身份、材料/结束复读和健康退出/普通身份复核；异常不自动清理或重试。系统锁须与旧工具相同，不能用上游用户锁或原型锁替代；本轮未打开这些锁。

完整材料范围、输出权限/完整性、核心/可选 68 资源、重复读取及失败矩阵见[设计](../docs/CAPTURE-DESIGN.md)。额外内部副本未来在电脑端复制核验，独立介质另证；旧默认单份备份、完整程序指纹、偏移、依赖和安装器均未修改。保留 QAQLeonard v2.1/ma1co 固定来源和许可，没有引入其他加载/改装路线。

## 实际核查命令与结果

起点 `ee9ba6db548b3e9be04356bc9788fa6fda5c60a4`，[第四十轮 CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39375969996)已 completed/success。源码包仍为 `8c6c30448219f4e865e8005d2ffa789248e984d73b0f9342035f7065a1a232f7`，固定提交 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`。

| 实际命令（仓库根目录） | 结果 |
| --- | --- |
| `.venv/bin/python -S -B -m research.audit_backup_loader --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round41/backup-loader.json` | 10 成员来源/主机加载边界核验通过；未导入归档代码 |
| `.venv/bin/python -S -B -m lutphoto.workercontracts --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round41/worker-source-policy.json` | 14 成员固定来源/ABI 通过，未编译或执行 C |
| `.venv/bin/python -S -B -m lutphoto.programidentity requirements --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round41/program-requirements.json` | 固定材料/程序策略查询通过，没有打开真实程序或快照 |
| `.venv/bin/python -S -B -m research.audit_upstream_looks --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --output research/output/custom-round41/upstream-source-audit.json` | 完整包、26 源及旧 46 成员通过；标准输出留同目录 |
| `.venv/bin/python -S -B research/output/custom-round41/audit_capture_sources.py` | 14 项 AST 源码观察通过，记录 27 个来源身份；无 USB/transport/core/设备模块导入 |
| `.venv/bin/python -B research/output/custom-round41/audit_public.py` | 本轮待发布文本/本地链接、隐私/资产、固定锁/历史及受保护路径、精确修改清单通过；既有未提交分析及计划附录保留且不纳入发布 |
| `git diff --check` | 通过 |

静态观察脚本定位固定读取/快照参数、runtime/备份的源码顺序、响应接收方式、健康退出顺序与两/四个 CP 键的差别；它不是完整控制流形式证明或设备测试。脚本/报告只留忽略目录，不新增正式测试计数。仅文档变更，未重跑此前 391 项软件测试；旧安装器和来源锁保持原样。

## 发布与交接

开始时工作区已有相机工具专项分析文档及 plan.md 附录。本轮原样保留，只暂存总计划中的 N3 行和本轮文档，不发布既有专项分析或其附录。提交前逐项列出上述核查结果，仅正常推送 lut-photo/main；提交、远端和新 CI 状态以最终报告为准。

下一轮先做纯主机采集状态/存储层与假传输演练；不启用真实 USB、不打开系统相机锁、不添加可运行设备命令。测试覆盖持久化/并发/链接/超限/中断/复读变化及未知退出，不把合成结果当作来源或恢复证明。随后再实现受限 Mac 读适配器并独立审阅，完成可审阅方案后才具体安排获准设备采集。

N3 仍部分完成，真实程序/BK4/资源正例、角色/外层容器、捕获新鲜度、完整事务、bound worker、全局锁/USB、恢复及独立介质仍缺。N4 的真实 ST/色彩/预览/JPEG/回放/冷启动后置；3D LUT 支线保留第二十八轮未闭合状态。当前无需连接相机、Docker 或惠普电脑。
