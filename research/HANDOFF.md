# LUT 照片开发：当前交接

更新：2026-10-19，第三十六轮主机加载链边界/BK4 只读解析与四态比较完成。先读根目录规则、README、[里程碑表](../plan.md)、[BK4 说明](../docs/BK4-OFFLINE.md)及[本轮记录](LUT链路调查记录-第三十六轮.md)，历史按需查[轮次索引](ROUNDS.md)。

## 当前主线与边界

N1 完成；N2 离线拟合/标定/冻结验收具备，真实 ST/色彩未证；N3 部分完成。已有格式、日志/进程锁、来源/ABI 和 BK4 格式/设置比较，没有真实 AP/CP 身份/描述符 planner、机身绑定 worker、设备恢复或 USB 入口。N4 相机/色彩后置，进入前提示，目前无需连接相机。

不调用 USB、安装器设备命令、诊断、sudo，不搜索或读私人程序/备份/照片。旧 FL23 哈希、运行锁、原测试不改；目标模块从未加载执行。新 Custom 双独立介质备份仍无实证且不保证恢复；旧流程默认单份备份不变。

## 本轮固定结果

- 新[10 成员清单](upstream-backup-loader.lock.json)与 `research.audit_backup_loader` 固定 host session/身份/transport/core、PMCA parser/util/protocol 及许可；来源仍 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`，与包/本地提取逐字节核对，不导入归档 Python。旧 26 源/46 成员/14 worker 再次通过，保留 QAQLeonard/ma1co 署名与许可。
- 主机暂存≤65536、命令 15/16、读回/触发/解码/按内容清理有源码依据。触发和主结果有 mark_unknown 保护；extras/cleanup 在该段之外，外层 Job 另有 NEEDS_REVIEW，未来须覆盖各阶段。本轮不改上游。
- host 链不提供 Sony ELF LOAD/BSS/权限/重定位/生命周期实现，NOR/CP 启动加载证据不能替代插件链。`camera_loader_abi_verified:false` 保留至受控 N4；不继续凭主机名或第三十五轮文件 ABI 推断设备行为。
- `lutphoto.bk4` 标准库只读 BK4 头/表/固定、变长、大值和 reset；校验和/数据区/表行别名/存储重叠/候选数与资源上限失败即拒绝。自制夹具外有独立 packed 正例，尚无真实备份兼容证据。
- 必须两个有效不重叠块；外层容器未解析，角色是调用方显式断言。AP 02cf/四个 CP 保护单元接入原设置比较，另保留四态 attr/max/当前长度/reset；高属性位拒绝投影。id1 是开关，checksum/顺序/自填 token 均不证明同机身，所有角色/来源/完整备份/描述符/物理标志 false。
- 新专项 22；完整研究 276、Mac 39、旧上游 8，合计 323 项通过，旧 check 通过。真实 CLI 四次 inspect/一次 compare、四次已有输出与坏 checksum 拒绝通过，五个自制源文件不变。私人报告仅留忽略的 `research/output/custom-round36/`；本轮未重编译 C、未读真实资产、未导入设备模块。
- 上轮提交 `a427c46d65d954973916017c3f4ebd3676c0f044` 及 CI 通过；本轮审核后仅提交 `lut-photo/main`，结果以 Git/远端及最终报告核对，不推 origin。主环境/依赖未改，Keystone/外部 Windows 断言仍未解决。

## 下一轮：真实只读身份/描述符入口

1. 在固定完整 AP/CP 配对、历史六槽/standalone 归一化和完整重建/mask 策略上，实现用户显式指定本地路径的纯只读身份入口；不扫描私人目录，不把局部字节或模板相似视为完整身份。
2. 将程序身份与描述符九字段/槽/保护范围适配连接，缺来源、身份或已审资产就拒绝；合成正例仅证明格式/拒绝规则，真实写计划和 worker 不得启用。先明确所需完整来源及正例材料，再解释后续需用户提供的具体本地路径/协助。
3. BK4 真实兼容/芯片角色/同机身证据仍缺；未来需经过验证的捕获流程在快照之外绑定正常 USB 身份与程序来源，不能从两个 BK4 块或自填哈希跳过。Sony 加载行为缺口留给受控 N4。
4. 全局相机锁/USB、逐机事务来源/目标/逆向绑定、设备恢复、独立介质及 N4 冷启动/真实色彩仍缺；进入设备阶段前提示。当前 Mac 足够，不需要 Docker、惠普电脑或相机协助；真需要时一次说明具体事项。

## 3D LUT 研究支线

M2–M4 保留[第二十八轮](LUT链路调查记录-第二十八轮.md#遗留与交接)未闭合状态，不自动延伸；动态配置、有效传输、MAIN 身份/时序未证，原生拟合和离线核验不能补齐。

## 复核入口

命令/边界见[BK4 说明](../docs/BK4-OFFLINE.md)，实际结果见[第三十六轮](LUT链路调查记录-第三十六轮.md#测试命令与结果)；此前[worker](../docs/WORKER-CONTRACTS.md)、[日志/进程锁](../docs/CUSTOM-JOURNAL.md)、[资源/设置](../docs/CUSTOM-CONTRACTS.md)和[Mac 环境](../docs/CUSTOM-MAC-OFFLINE.md)继续有效。总计划四列、每轮独立、交接滚动覆盖，旧[归档](../plan-history-through-14.md)不变。
