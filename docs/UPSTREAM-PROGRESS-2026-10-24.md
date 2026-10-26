# 上游与相关项目进展：2026-10-24

查询日期：2026-10-24（北京时间）。本轮读取15个公开仓库的默认分支、提交、Release及相关文档，并单独核对直接上游的develop、PR和Issue。版本、分支与作者反馈分别记录；不按提交数量或测试数量推算完成百分比。本轮没有操作相机、下载运行安装包、读取私人诊断附件或更换本项目固定依赖。

## 主要结论

1. **直接上游最新正式版为3.0.3，开发分支另有重要修复，尚未发布。** 正式版修复USB接收、基础外观同步、声音和受限安装续接；develop增加EVF/S35色表刷新、元数据读取安全、混合槽位续接及离线缓存身份检查。
2. **恢复安全仍没有形成A7C II独立重装保障。** 新出现无法开机的用户报告，原因和成功恢复未在公开讨论中确认；现有“恢复原厂功能”仍需可用的相机服务/执行链。
3. **其他机型的进展值得复用，但能力要逐项迁移。** A6700发布0.2.0；A7R V发布4.28候选及实拍标定工具；A7CR有Mac研究工具；ZV-E10有模拟启动和底层恢复研究，但公开代码与恢复声明存在证据差异。
4. 本项目继续保留原厂2.01、完整程序身份及未知即停规则。上游进展不自动推进本项目D4/D5或授权新的设备操作。

## 1. 直接上游：正式发布与开发分支

来源：[3.0.3发布](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.3)、[固定正式版更新日志](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/docs/zh-CN/changelog.md)、[固定开发版更新日志](https://github.com/QAQLeonard/a7c2-fl23-research/blob/e8edf50be2859ce16ffe212fbfb6e86bc2937280/docs/zh-CN/changelog.md)。

| 对象 | 查询结果 | 能说明什么 |
| --- | --- | --- |
| 最新正式Release | v3.0.3，10月23日；Windows x64 ZIP、macOS arm64 DMG及外观资源 | 已发布下载，不等于全部功能及故障恢复均验收 |
| main | `782785641ca9f8b984940c7274b48706219e0da4` | 与本轮核对的3.0.3代码基线一致 |
| develop | `e8edf50be2859ce16ffe212fbfb6e86bc2937280`，10月24日 | 比上述main多24个提交，含合并历史；不能读成24项已实机功能 |
| Mac验证 | 正式版README仍写实机USB未验证；开发版PR #25另有一台Mac适配机身的局部对照 | 局部修复实测不能代替正式DMG全流程验证 |

### 3.0.3已发布的变化

- **基础外观同步：** 修复保存设置是ST、运行状态仍是BW等旧基础外观的问题。更新日志记录一台机身第4槽的复现和恢复；不能外推所有槽位、所有原始状态。
- **USB接收：** 按Senser包头长度收包，处理空包和特定CP参数请求的收尾；记录过一台Windows机身72项只读读取成功。仅对满足条件的只读错误执行退出处理，不能作为任意未知写入的通用恢复。
- **安装续接：** 程序和名称已写完且读回证据完整时，可新建事务续做设置。没有完整证据的部分安装仍不能据此放行。
- **声音：** 调整电子/机械快门触发；部分声音操作按当前状态规划；实际保存路径移除在部分Mac上崩溃的Unicorn/JIT调用。
- **恢复记录：** 原厂恢复完成写入后停用旧声音任务占用。它恢复项目涉及的区域与设置，不能等同全芯片重刷或BootROM救砖。

以上为上游发布和日志声明，本轮没有运行这些流程。声音、竖屏、Mac完整流程及长期稳定性的验证边界仍见其[验证表](https://github.com/QAQLeonard/a7c2-fl23-research/blob/782785641ca9f8b984940c7274b48706219e0da4/README.zh-CN.md#验证状态)。

### develop已合入、正式包未包含的变化

| 变化 | 进展和证据 | 对本项目的意义 |
| --- | --- | --- |
| EVF横线、S35视频条带与切槽刷新 | PR #25恢复原生上传条件，随后第三版修复提交确认；作者记录一台机身高刷新EVF、切槽、拍照/回放及S35观察正常 | 必须把“色表内容正确”和“提交时序正确”分开验收；不是仅验证静态字节 |
| ExifTool文件名参数注入 | PR #26已合并；拒绝含CR/LF/NUL路径、使用绝对路径；有真实ExifTool与合成文件回归 | 这是电脑端安全修复：原本的元数据读取可能被特殊文件名变成写文件操作 |
| 混合导入与ST恢复续接 | PR #27已合并；从已保存请求重建完整名称计划，保留完整读回与未知停止 | 可借鉴完整事务目标清单，不能只记录实际导入的槽位 |
| 离线拟合缓存失效 | PR #35已合并；校准/桥接文件增加内容摘要，同路径替换不复用旧结果 | 与本项目模型身份和输入可追溯性直接相关 |
| 原厂恢复重新规划 | 根据当前机身读取内容生成新请求，清理范围受限；执行入口占用、preload启用或文件仍变化时停止 | 可研究，但减少旧任务门槛改变了准入规则，须独立审查；当前只有离线证据 |
| PR #9历史整合 | 部分电脑端修复此前选择性移植，随后纳入原提交历史；未将旧方案整体覆盖当前实现 | 不能仅凭PR被合并，就断言旧分支全部行为都已进入桌面版 |

来源：[PR #25](https://github.com/QAQLeonard/a7c2-fl23-research/pull/25)、[#26](https://github.com/QAQLeonard/a7c2-fl23-research/pull/26)、[#27](https://github.com/QAQLeonard/a7c2-fl23-research/pull/27)、[#35](https://github.com/QAQLeonard/a7c2-fl23-research/pull/35)、[#9](https://github.com/QAQLeonard/a7c2-fl23-research/pull/9)；最新EVF反馈见[Issue #13](https://github.com/QAQLeonard/a7c2-fl23-research/issues/13)。第一版曾出现消除横线但预览停留的回归，不能混用不同候选的验收结论。第三版仍未覆盖所有机身、格式和帧率。

## 2. 会影响安全判断的新反馈

| 公开记录 | 已知事实 | 尚未证明 |
| --- | --- | --- |
| [QAQ #31：无法开机](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31) | 用户称按流程修改、第二次取电池后无法启动，灯2-3-5循环，USB为054c:0d68；作者收集证据 | 未公开确认根因、准确受影响范围或成功恢复；不能据此认定HID就是可用救砖入口 |
| [QAQ #28：部分安装后冲突](https://github.com/QAQLeonard/a7c2-fl23-research/issues/28) | 作者确认竖屏准备可能先完成，后续FL23遇到代码冲突；总任务FAILED不代表此前变更已自动撤销 | 尚未确认该机身适用的恢复方案，作者要求先分析证据 |
| [QAQ #34：快速切换假死](https://github.com/QAQLeonard/a7c2-fl23-research/issues/34) | 用户报告快速切换自定义外观时EVF/屏幕假死，作者回应仍有问题 | 不能用横线修复的有限反馈宣称快速切换与全部模式已稳定 |
| [QAQ #32：改对比度后近黑画面](https://github.com/QAQLeonard/a7c2-fl23-research/issues/32) | 作者在回复中称离线复现自定义曲线包装器可能提前读取空项，提出回退指针候选 | 不是已完成真机验收，也未证明它解释该报告全部症状 |
| [MDHan #14：新版安装设置阶段停止](https://github.com/MDHan/a7c2-fl23-macos/issues/14) | 0.2.3用户报告writing_settings停止，机身仍可拍摄，旧专项diagnose/finish不支持该新版配置 | 最新版本仍未覆盖所有中断恢复路径；不能套用旧版收尾规则 |

这是用户反馈和维护者公开答复，不是本轮复现实验。没有下载帖子中的私人诊断包。无法开机记录没有足够公开证据说明由供电中断引起；在用户给定的持续供电前提下，仍要独立检查程序兼容、色表/设置状态、启动加载、临时执行清理和恢复入口。

## 3. 直接相关仓库的当前进度

以下日期为提交或Release日期，按北京时间归属；未将仓库pushed_at混作功能发布时间。

| 项目 | 最新状态 | 内容及边界 |
| --- | --- | --- |
| [MDHan/a7c2-fl23-macos](https://github.com/MDHan/a7c2-fl23-macos/tree/41950d3eab53e0b801f315af07505a2d0d3f76af) | main `41950d3`，10月21日；工具0.2.3，无GitHub Release | 新增受限服务入口超时重试、证据审查后的收尾；有用户安装重试成功反馈，恢复和所有配置并未全面验收 |
| [YuuLuo/a7c2-camera-tools](https://github.com/YuuLuo/a7c2-camera-tools/tree/f124d87c26110a82db54775bfa64a0843ff21410) | `f124d87`，10月19日；未变，无Release | FL23/声音与修改DAT路线，作者称近十台兼容测试；涉及p1临时门控、原始p1恢复和BK4，不是独立救砖 |
| [YuuLuo/a7c2-service-preload](https://github.com/YuuLuo/a7c2-service-preload/tree/1619f938663a36d41e72302a8cfee89a0f6acd1a) | `1619f93`，10月15日；无新提交/Release | 服务认证、Jiritsu与临时root执行研究；要求正常服务入口，不永久关闭固件签名检查 |
| [lzh2016zzz/a7cr-fl23-research](https://github.com/lzh2016zzz/a7cr-fl23-research/tree/43ba74441c8f10459ade41e84a379ad8005e6ef4) | `43ba744`，10月16日；文档研究，无Release | A7CR 2.01 FL23路由、参数、元数据及WBI；最新局部更改的重启/新照片验收仍列为待做 |
| [injectiver/a7cr-creative-look-tools](https://github.com/injectiver/a7cr-creative-look-tools/tree/48f3cb6cb02a1ad1da29f12d7ca97bdad1cb310f) | `48f3cb6`，10月21日；0.1.0-research，无Release | 一台A7CR+Apple Silicon Mac；原生FL23有实拍，自定义六槽完成写入/读回但完整冷启动与六槽验收未完成；公开CLI无通用install |

MDHan验证来源：[固定验证文档](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/docs/VALIDATION.md)。它的新版变化没有自动进入本仓库继承的旧实现。YuuLuo分析仍见[既有专项报告](A7C2-CAMERA-TOOLS-ANALYSIS.md)；其“之后能走官方2.01更新”的说明是特定设计/作者声明，不构成本机必然可恢复的证明。

## 4. 其他机型、独立恢复与模拟环境

| 项目 | 最新状态 | 与本任务的关系 |
| --- | --- | --- |
| [DavidBuchanan314/ILCE-7M4-RE](https://github.com/DavidBuchanan314/ILCE-7M4-RE/tree/2328d18ce640e6c8cd9341efcf0043ce9042a135) | `2328d18`，10月7日；仍为v0.0.1，较前次调查无新提交 | A7 IV BootROM串行启动、RAM Fastboot和eMMC读写的基础；不是A7C II现成移植 |
| [Erlla/sony-a7m4-custom-firmware](https://github.com/Erlla/sony-a7m4-custom-firmware/tree/0332a1fa94175f17ef8b9287fa42317c95648791) | `0332a1f`，10月23日；无Release | 整理七项独立方法，包含声音/画幅/FL23及SD恢复；恢复仍要求已进入Fastboot、精确更新器匹配，公开适配未完成新的整套实机刷写 |
| [xyzhangxin/sony-a6700-powerful](https://github.com/xyzhangxin/sony-a6700-powerful/releases/tag/v0.2.0) | v0.2.0，10月23日；源码`d5bb948` | Mac应用修复USB上下文、设备释放/重连，开放FTP、关机快门帘、灵活曝光、电子快门声；完整备份恢复尚未提供 |
| [Hearts-Ace/sony-a7r5-custom-firmware](https://github.com/Hearts-Ace/sony-a7r5-custom-firmware/releases/tag/v4.28) | v4.28，10月24日，**prerelease**；源码`8b563d4` | 自定义滤镜、5×9×9网格、独立实拍反推/色彩工具和九款富士风格；4.28菜单、冷启动及照片颜色待验收 |
| [cokeenet/zve10-qemu](https://github.com/cokeenet/zve10-qemu/tree/ad503db6c851d44d1087e80e9ea177bff645f62c) | `ad503db`，10月24日；无Release | ZV-E10 ARMv7/CXD90045模拟启动和UI移植研究；报告过底层单字节救援；不是A7C II的ARM64虚拟机 |
| [dino2048/zv-e10-toolkit](https://github.com/dino2048/zv-e10-toolkit/tree/b86ca0a73ed461cd2da09830a84d089735e27123) | `b86ca0a`，10月23日；无Release | 公开备份、BootROM读取、Pico/RAM Fastboot及eMMC读取；公开版本明确无eMMC写回/恢复入口 |

### A6700：应用可测试，完整恢复仍未闭合

0.2.0并非只升级Pico备份工具，重点是普通USB功能应用的连接与操作引导。安装包限A6700 2.00、Apple Silicon/macOS 13+；作者报告145项无设备检查和继续扩大机身测试。位移多帧因稳定性问题撤回，动态增强防抖禁用，FL2/FL3仍离线验证中。[开发计划](https://github.com/xyzhangxin/sony-a6700-powerful/blob/d5bb9485dfe7cc4bf13a4ead3a7437c2f40240a9/开发计划与进展.md)明确完整备份/恢复和官方固件救砖尚未完成验证。该文档页首日期早于0.2发布，应与Release及README一起读。

### A7R V：与色彩研究相关，但不能靠版本号判断成熟度

4.28回退到4.25菜单基线，保留自动导入、BIN v4和已有网格生命周期，没有合入4.26/4.27全部调整。发布了R5GridCalibrator、R5ColorLab及实拍v2模型。模型只覆盖42/256颜色，留出RMSE为3.696；跨条件精度尚未验收。签名、CRC、完整解密检查与“可冷启动、拍摄正常、颜色正确”是不同验收。公开源码还缺部分构建输入，并非干净克隆即可重建整包。[固定说明](https://github.com/Hearts-Ace/sony-a7r5-custom-firmware/blob/8b563d46f800679abd3f215950cb541fc81da2a6/README.md)

### ZV-E10：模拟与救援声明需交叉核对

[模拟仓库](https://github.com/cokeenet/zve10-qemu/blob/ad503db6c851d44d1087e80e9ea177bff645f62c/README.md)报告已启动内核、加载平台模块并运行部分机身应用，但显示和输入链未完整打通；10月24日最新提交仍在定位新菜单应用的数据访问崩溃。模拟环境存在兼容补丁、替代接口及硬件缺口，不能把能运行部分应用解释为原版整机功能、更新或恢复已验证。

[救援记录](https://github.com/cokeenet/zve10-qemu/blob/ad503db6c851d44d1087e80e9ea177bff645f62c/docs/FASTBOOT_EMMC.md)称通过BootROM/RAM通道修改preload目录项的一字节后恢复UI。但其指向的公开toolkit在本轮固定提交中，[Fastboot说明](https://github.com/dino2048/zv-e10-toolkit/blob/b86ca0a73ed461cd2da09830a84d089735e27123/fastboot/README.md)明确为只读、flash/erase返回失败；公开docs目录只有硬件、USB成功和eMMC读取记录，没有被引用的write-success/fix-record等文件。

因此本轮结论是：**有作者描述的局部真机救援案例，公开读取实现可查；尚未取得与该救援声明对应的完整公开写入实现和验证资料。** 不能称为已独立复现的可交付救砖工具，更不能照搬到A7C II。其他旧研究页面有与新进展不一致的判断，本轮优先记录固定代码/最新状态及尚未解释的差异。

## 5. 机外色彩与基础工具

| 项目 | 最新状态 | 可以参考的内容 |
| --- | --- | --- |
| [751K/sony-a7m5-looks](https://github.com/751K/sony-a7m5-looks/tree/042e2c31a9d75803f2af2f3aaa5ede5e6030e448) | 正式v1.2.1，10月21日；最新文档提交10月24日 | A7 V十二种外观转Capture One、ACR/Lightroom、DxO配置；只在电脑处理。ST/FL2/FL3有Edit对照，其余九种未逐一对照，不是A7C II标定 |
| [ma1co/Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE/tree/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0) | 主分支最新提交2022-08-18；正式v0.18 | 基础USB/Senser协议仍被复用。其旧updater-shell明确不支持CXD90045/57签名固件，不能据此获得A7C II通用重装入口 |
| [ma1co/fwtool.py](https://github.com/ma1co/fwtool.py/tree/cdba742b73eed5981480c326aeb30033aabf0223) | 主分支最新提交2022-09-14；正式v1.2 | [CXD90057支持PR #52](https://github.com/ma1co/fwtool.py/pull/52)仍开放、未合并，head为`3955d7890fc38daf942bb52827599bfe35de4a14`；离线解包能力不等于签名/启动/恢复能力 |

另一个直接相关的新信息是[上游标定来源答复 #30](https://github.com/QAQLeonard/a7c2-fl23-research/issues/30)：维护者称模型来自自制768色块屏幕及参数扰动，完整协议为八轮、64组RAW+JPEG；NPZ含处理样本和插值生成数据，原始照片、完整逐帧索引及全套重建脚本尚未公开。该答复是作者说明，不是本轮复现；它支持继续把现有模型视为限定条件近似，不能作为A6700/A7CR/A7C II跨场景精度保证。

## 6. 对本项目的建议顺序

1. **先复核可离线吸收的修复。** 输入内容摘要、特殊文件名安全、完整槽位目标、失败诊断和原始证据保持；逐项比较本地实现，已有等价机制则不重复迁移。
2. **独立审阅USB及恢复状态变化。** 上游Senser读取、fresh restore、声音遗留清理与本地身份查询是不同阶段；不能把上游序号错误修复直接认作本地早期USBError的根因或修复。
3. **功能验证增加运行时与切换场景。** 六槽切换、EVF高刷新、S35各格式、基础外观与对比度等参数、声音和冷启动应单独验收。文件读回正确不覆盖这些运行故障。
4. **救援继续作为独立路线。** A7C II专用BootROM入口、同机备份覆盖、受限写回、启动恢复与官方更新接受性仍需逐项建立；持续供电不自动提供这条路径。
5. 整理期间，工作区交接更新至`19b8345`：第六十九轮新采集在枚举边界停止，6事件、0材料、NEEDS_REVIEW_UNKNOWN；完整材料和正常退出仍未验收。本轮只读取该交接，没有执行那次设备操作；不把其他任务或上游的成果计作本轮测试，也不据此重采。

## 7. 查询与验证边界

- GitHub连接器读取公开GET接口：仓库、默认分支提交、Release、main/develop、compare、PR、Issue及评论、固定提交文件；网页搜索用于发现额外项目，不用搜索缓存替代最新分支。
- 本轮核实main与develop不同；PR合并状态不等同已发布。Release列表为空仅表示没有GitHub Release对象，不能说没有源码/工具交付。
- 本轮没有找到可核验的A7C II独立恢复完整公开闭环；搜索无结果不是不存在的证明。被引用的ChambersXDU/sony-a7c2-research公开读取返回404，不能据此判断删除、改名或私有，也未计入已核验15个仓库。
- PR #33单独API读取返回404，仅看到列表标题/状态，未据此宣称其代码已合并或发布。文档及Issue中的建议属于来源内容，本轮没有执行。
- 本轮只新增此报告并维护[计划](../plan.md)，保留其他已有变更；不提交、不推送。文档检查的实际命令与结果记录在计划本轮条目，未重跑与文档无关的运行测试。

研究与实现归各项目作者及其引用上游；本报告只链接、概括并标明证据范围，没有复制固件、个体数据或第三方实现进入运行代码。
