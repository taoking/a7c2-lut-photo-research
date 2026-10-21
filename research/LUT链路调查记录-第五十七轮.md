# 第五十七轮：公开首次采集入口、私有回执传递与退出码

日期：2026-10-21。交付独立[首次内部采集命令](../docs/CAPTURE-FIRST-USE.md)，完成C1的公开入口、前置拒绝、回执保存/退出码与离线准入收口。复用同一内部NativeOps/Host/所有权核心/固定协议/Store，没有新增模拟层。**代码和离线交付完成；实际SDK、首次真机采集及本人同机材料仍未验证，N3仍部分完成。**

本人保留原厂Ver.2.00及日常卡副本，当前不需升级、连接或准备Docker/惠普电脑；卡副本不是内部AP/CP/BK4、恢复或降级证据。本轮没有实际SDK/共享库、USB/系统相机锁、sudo/磁盘命令、机内模块或移动盘/私人材料读取。真实信号只发送给刚创建的自制测试子进程。

## 交付与准入边界

1. 新 `lutphoto.capturecamera capture` 明确要求model、firmware、实际battery-percent、新作业目录和独立私有receipt，可选固定68资源。声明精确机型/原厂2.01/整数电量50–100先检查，再核对固定来源/本地环境/新路径；之后排他预留回执，最后构造NativeOps。没有任意后端、版本覆盖、启用开关、机内路径或强制续跑参数。旧capturecandidate.capture仍无条件拒绝，review JSON不能变成执行许可。
2. 从captureexecution提取唯一_prepare/_run边界，既有私有_capture仍委托同一装配；来源/环境检查不会因预留回执重复。权限与输出所有者匹配运行者；管理员上下文须使用已存在的受信私有父目录，不自动chown/chmod来放行用户路径。
3. 回执在设备流程前排他创建0600，父目录0700，拒绝现有文件、链接、同名/规范化别名及作业内部位置；同步预留文件/目录并保持独占锁。内部收尾后验证native终态，完整写入/同步、读回SHA/长度、核对条目与所有者、单次关闭；一项关闭失败仍尝试其余描述符。检查器先取非阻塞共享锁，持有写锁时拒绝ACTIVE_RECEIPT。
4. 文件/关闭失败保留空、部分或完整现场，不删除、重开作业补写或重新采集。保留首错误及有限原因链/次要类型，CLI不输出原始异常/路径。stdout只含有限阶段、回执保存/可能已开始及错误类型；拒绝/未知/传递/输出失败退出1，结构参数错误退出2。
5. 退出0须内部完整、回执保存/关闭及stdout完整写入/刷新均确认。完整核心回执也不能单独证明最终传递/终端输出或整个进程成功；只读检查的一致性0不是原调用退出码。突然死亡或stdout/stderr都不可写时不保证留下结果，不新增原子性承诺。

固定完整AP/CP策略、协议/请求范围、单服务所有者和新返回MSC查询保持不变。服务认证/选读取路径会改变临时状态；新入口不上传/删除、不加载机内模块、不写程序/保存设置、不WBI，无恢复/续跑。真实响应轮廓与同机材料须由C2独立验收，声明参数不是自动测量或绕过检查的依据。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest research.tests.test_capturecamera research.tests.test_captureexecution research.tests.test_capturesignals -q` | 新19+内部24+原信号24，共67项通过；公开API另含4个真实自制子进程信号场景 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究849项通过 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧Mac39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游8项通过；全量合计896项，不重复加入专项数 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产检查通过，未连接相机 |
| `.venv/bin/python -B research/output/custom-round57/audit_capture_sources.py` | 115条AST观察/54来源身份，固定N1/旧源/宿主11/认证9/加载10/worker14清单通过，无SDK导入/归档执行 |
| `.venv/bin/python -S -B research/output/custom-round57/exercise_public.py` | 固定来源八故障、实际公开CLI及独立-S检查CLI通过；都预期退出1，一未完整/七未知，终态MATCHED_FAILURE |
| `.venv/bin/python -B research/output/custom-round57/audit_public.py` | 266个公开文本/108份Markdown/685处本地链接及锚点通过；21项精确发布清单、隐私/密钥排除、锁/历史/受保护路径通过 |
| `git diff --check` | 通过 |

专项初版41项通过；补充公开API子进程和初始化收尾失败原因后，最终67项与全量均通过，本轮没有失败用例被删除或放宽成功条件。公开API测试的完整材料成功来自既有自制程序/策略夹具，仅为装配测试；它不符合真实原厂完整指纹，不能作为C2正例。拒绝测试涵盖声明/来源/环境/管理员、已有输出/权限/别名、部分回执与关闭失败、stdout短写/刷新失败；真实-S进程以2.00声明拒绝和自制断管输出验证非成功，均未构造实际SDK。

四个公开API信号场景为配置SIGINT、材料SIGTERM、stop SIGTERM、dispose SIGINT。父进程先确认取消已观察、假调用未返回、所有者/租约/ACTIVE_JOB/ACTIVE_RECEIPT仍在及协议计数不增，再放行假SDK。返回后不追加协议、单次dispose、处理器还原及失败回执一致；加上旧候选/内部装配，全量12个真实自制子进程场景，均非机身证据。

固定来源八故障演练没有修改固定原厂策略；环境/管理员元数据和NativeOps底层SDK/系统均为既有夹具。密钥仅读入内存，独立标准库SHA-256构造认证预期，不执行归档或原生代码。99,960,744字节全零AP在读取CP/设置前拒绝；其余覆盖半包、认证控制不明、材料发送不明、服务dispose不明、返回身份变化和两段等待耗尽。八次都保存失败回执，公开CLI与独立检查CLI都返回1。198/144/54/82/146/192/140/231项自制输入（含回执）前后内容/inode/权限/mtime/ctime不变，不保证atime；临时输入已清理。检查点/日志/回执/简短stdout中未出现密钥、包/挑战原文或路径。

## 发布与交接

起点 `63b6cea35ef4a021272169e3164a7aa327666e07` 的[第五十六轮CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39598638026)已核对success。旧FL23安装器、默认单份备份、旧锁/指纹/偏移/依赖/测试及历史计划不改；QAQLeonard/ma1co/ajalt固定来源、署名与许可保留，不发布程序/设置/资源、密钥、身份或私人路径。

总计划只更新N3四列表，独立轮次记录与滚动交接同步。原分析报告/本地计划附录保留；PRIVATE在读取内容前排除。只显式暂存本轮公开文件，计划仅暂存主表；正常推lut-photo/main后核对远端/CI，实际发布结果见最终报告及忽略目录custom-round57/publication-receipt.json。

第五十八轮推进C3单槽完整目标生成、未选区域保留和逐字节逆向离线核对，复用既有候选/材料与固定上游，不新增平行模拟层。C2实际首采单独后置，进入前另提示范围并取得真实版本/电量/连接/管理员配合；当前2.00先保留。C3部署/worker、C4恢复/独立介质、C5真实ST/摄影及真正3D LUT可行性缺口未闭合，备份不保证救砖。见[HANDOFF](HANDOFF.md)与[总计划](../plan.md)。
