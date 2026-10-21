# 第五十四轮：进程信号、合作式取消及现场保留

日期：2026-10-21。依据第五十三轮交接完成[信号作用域与离线验证](../docs/CAPTURE-SIGNALS-OFFLINE.md)。真实信号只发给新建自制测试子进程；固定来源演练进程另核对安装/还原。没有实际SDK/共享库、USB/系统相机锁、sudo/磁盘命令、原生模块或移动盘操作。保留用户原厂Ver.2.00和日常卡副本，不要求现在升级/连接；卡副本不是内部程序/BK4备份或降级证据。

## 交付与边界

1. 新SignalCancellation显式作用域只接收精确Cancellation，主线程在任何采集租约/作业前进入。仅接受SIGINT默认中断/SIG_DFL和SIGTERM默认处置；自定义/忽略/未知处理器、嵌套/重用、工作线程或已取消token拒绝。安装后读回，进入正文前再次查取消；导入/构造无安装，既有入口不自动启用，没有新设备命令/公共后端参数。
2. 处理器只赋值token布尔标志，不调用Event.set/cancel/同步原语、不抛异常、写日志、释放资源、执行SDK或终止进程，不保存信号帧。原线程Event取消保留，既有请求检查同时识别两种请求；重复信号不升级强制动作。
3. 安装部分失败逆序核对还原，处理安装抛错前后状态；遇到外部处理器不覆盖/调用，继续处理其余自有处理器。还原读回不符/失败明确SignalScopeError、restoration_confirmed=false，主错误保留并以异常链记录还原问题，不反复尝试。
4. 四个真实自制子进程场景：配置查询SIGINT、材料发送SIGTERM、stop控制SIGTERM、dispose内SIGINT。父进程确认请求已观察但模拟SDK未返回、所有者/租约/ACTIVE_JOB仍在、协议计数不增后，才通过输入管道允许假调用返回。dispose视图提前失效不等于物理释放，仍保留所有者记录。
5. 返回后均OperationCancelled/NEEDS_REVIEW、检查器NEEDS_REVIEW_UNKNOWN，stop ACK/返回身份不伪造，SDK对象仅一次显式释放尝试，无新增协议动作，所有实际设备标志false且处理器还原。不新增报告格式、硬时限、强杀、USB复位或恢复/续跑许可。

真实SDK可能延迟Python信号处理，标志即使已记录也不能抢占底层调用；安装两处理器并非原子，作用域外仍是原进程规则。测试失败清理只能终止本测试的自制子进程，不进入采集实现。真实入口继续关闭，现场规则及设备证据尚待最终审阅/实测。

旧FL23安装器、默认单份备份、锁/指纹/偏移、旧测试/依赖/历史计划及固定上游不改。QAQLeonard/ma1co/ajalt署名/许可保留，不发布程序/设置/资源、密钥/身份/私人路径。N3仍部分完成，事务/worker/恢复、双独立介质及N4实拍未完成，真正3D LUT支线不推进为已证。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_capturesignals.py' -v` | 新24项通过：20作用域/失败/导入，4真实自制子进程信号 |
| `.venv/bin/python -B -m unittest research.tests.test_capturecontrol research.tests.test_capturenative -q` | 既有控制19+原生组合21，合计40项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究804项通过，新增24，无重复发现TestCase |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧Mac39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游8项通过；全量合计851项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产通过，未连接相机 |
| `.venv/bin/python -B research/output/custom-round54/audit_capture_sources.py` | 86条AST观察/51来源身份及N1/旧源/11/9/10/14固定清单通过，无SDK导入/归档执行 |
| `.venv/bin/python -S -B research/output/custom-round54/exercise_controlled.py` | 固定来源八种自制故障/实际检查CLI通过；作用域无取消请求并正常还原；另核对6/74源码审阅及电脑预检 |
| `.venv/bin/python -B research/output/custom-round54/audit_public.py` | 公开AST/JSON/链接、隐私/密钥排除、受保护路径/锁/历史和精确清单通过 |
| `git diff --check` | 通过 |

新测试涵盖默认处置保存、仅布尔标志/不调用Event.set、token/线程/嵌套/重用/自定义或忽略处理器拒绝、第一/第二安装前后失败与状态变化、还原失败/读回不符/主错误保留、外部新处理器保护、工作线程退出拒绝及-S导入无副作用。四个子进程有握手/总时间/输出上限，只向自己刚创建的子进程发信号，不操作其他进程或设备。专项初次17项、扩展22项通过；补充安装未生效和安装期间取消两用例时复现2项失败，增加安装读回及进入前token检查后24项与全量804项通过，未放宽协议或设备门槛。

固定来源练习仍只读密钥到内存，独立标准库SHA-256生成认证预期，不执行归档Python/原生代码。99,960,744字节全零AP按原厂策略拒绝，不读CP/设置，无原厂材料正例。八场景为程序拒绝、半包、认证控制不明、材料发送不明、服务dispose不明、返回身份变化、服务/普通等待耗尽；实际检查CLI一未完成/七未知，均退出1。

197/143/53/81/145/191/139/230项自制输入（含目录）前后内容、inode、权限和mtime/ctime不变，不承诺atime；临时目录清理。作用域安装/还原不添加材料日志字段，6/74源码审阅仍NATIVE_CANDIDATE_BLOCKED/live=false，电脑预检不建目标。汇总只留忽略的 `research/output/custom-round54/`，不发布私人材料/路径/日志/密钥。

## 发布与下一轮交接

起点 `b0a2e18e0c72240583b870e59c951233b5e20dca` 的[第五十三轮CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39585790352)已核对completed/success。总计划只更新N3四列表，滚动交接/轮次独立维护；原本地分析/计划附录保留不发布，PRIVATE不读/暂存。提交前列出实际测试，只正常推lut-photo/main；本轮提交/新CI以最终报告为准。

第五十五轮集中做首次采集候选最终审阅：核对来源/只读范围、程序先于设置、信号安装时机、未知/还原失败/退出码及保留说明，整理实际执行前的缺口和本人配合项，不继续叠加同类模拟层。真实采集仍需另提示并取得真实版本/电量/连接等信息；现阶段保留2.00和卡副本，不需升级/相机/移动盘/Docker/惠普电脑。

SDK/权限/全局锁/CSW/端点/回显/排空/重枚举及新鲜同机材料继续独立验收；N3事务/worker/恢复、双独立介质和N4色彩未完成。真正3D LUT支线维持第二十八轮动态配置、有效像素传输、MAIN身份/时序未闭合。
