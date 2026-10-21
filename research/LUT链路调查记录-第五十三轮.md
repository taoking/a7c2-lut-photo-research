# 第五十三轮：现有Mac适配方法的假SDK组合验证

日期：2026-10-21。完成[假SDK组合验证](../docs/CAPTURE-NATIVE-OFFLINE.md)，按第五十二轮交接执行现有NativeOps/Host/候选/Store，而非增加平行协调器。本轮不导入实际SDK/共享库、不操作USB、系统相机锁、管理员认证、系统磁盘命令、原生模块或移动盘。用户保留原厂Ver.2.00和日常卡副本，不要求现在升级/连接；卡副本不是内部程序/BK4备份或降级证据。

## 交付及实际范围

1. 研究目录新增自制SDK对象/系统夹具。NativeOps枚举、选择、当前配置/端点、驱动/声明/释放、控制/收发及命令/锁规则均执行既有方法；仅runtime、该模块os/fcntl/sys引用及命令执行点替换为假接口。实际临时作业/锁/日志/回读仍由Store处理，系统全局租约是假。未增加公共后端参数/设备入口，不代表真实权限/后端加载已验。
2. 每次枚举产生新对象；库存对象不执行配置/协议，原生open重新选择唯一对象。选中对象先归所有者，再模拟当前配置触发惰性打开。初始/服务/返回三个对象分开，同服务对象完成认证/材料/stop，返回身份重新MSC查询。自制6/74材料和计数与已有候选一致，owned四种证据/物理false边界不变。
3. 先复现异常枚举重复引用同对象导致两次释放，再修正仅清理按对象身份去重；重复观察仍保留并拒绝，不折叠成唯一相机。枚举中途失败仍清理已收纳对象，不重试已失败的释放。
4. 先复现取得锁失败后close异常覆盖原错误，再修正继续抛主异常，以异常链保留close错误；仅尝试一次关闭，不创建作业/启动设备流程，也不宣称关闭已确认。
5. 覆盖配置/claim/日志/释放失败、身份/认证/材料/stop未知、单次健康退出、返回身份变化、等待耗尽及关闭/发布顺序。假SDK在调用内收到取消/期限耗尽时保留所有者/活动作业/租约，返回后停止；不构成管理调用可抢占或真实信号已验。

旧安装器、默认单份备份、锁/程序指纹/偏移、原测试/依赖和历史计划不改；固定来源及QAQLeonard/ma1co/ajalt署名/许可保留。真实SDK/协议/系统锁/重枚举/新鲜同机材料、恢复/事务和实拍未完成，N3仍部分完成；不开放设备采集，不扩大到2.00或第三方修改升级包。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -p 'test_capturenative.py' -v` | 新组合专项21项通过 |
| `.venv/bin/python -B -m unittest research.tests.test_captureowned research.tests.test_capturecontrol research.tests.test_capturecandidate -q` | 既有装配/等待/候选75项通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究780项通过，新增21，无重复发现TestCase |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧Mac39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游8项通过；全量合计827项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产通过，未连接相机 |
| `.venv/bin/python -B research/output/custom-round53/audit_capture_sources.py` | 80条AST观察/50来源身份及N1/旧源/11/9/10/14固定清单通过；不导入SDK或执行归档代码 |
| `.venv/bin/python -S -B research/output/custom-round53/exercise_controlled.py` | 八种固定来源自制材料经现有NativeOps/假SDK及实际检查CLI通过；另核对6/74源码审阅和电脑预检 |
| `.venv/bin/python -B research/output/custom-round53/audit_public.py` | 公开AST/JSON/链接、隐私/密钥排除、受保护路径/锁/历史及精确发布清单通过 |
| `git diff --check` | 通过 |

初始三项中重复释放和锁错误两项失败，修正后通过；扩展夹具端点断言时误将返回普通MSC对象视为具有认证对象，造成7项失败，已补齐自制MSC端点声明，未修改产品轮廓/放宽检查。最后加强主异常/close原因链核对并重跑全量780项通过。AST审计重复输出按不覆盖规则保留早期快照，再生成最终来源摘要。

21项还覆盖新枚举对象/别名/变化、dispose未确认/中途枚举失败的主错误、OPEN确认日志失败时未打开对象的归属、假SDK隐式release与显式release区分，以及真实-S检查CLI只读/隐私和无SDK导入。所有原始收发仍经过固定端点/超时/计数检查。

固定来源练习使用内存密钥/独立标准库SHA-256认证预期；不执行归档Python/原生代码。99,960,744字节全零AP按原厂策略拒绝，不读CP/设置，无原厂材料正例。八场景仍为程序拒绝、半包、认证控制不明、材料发送不明、服务dispose不明、返回身份变化、服务/普通等待耗尽；实际检查CLI退出1，一未完成/七未知。

197/143/53/81/145/191/139/230项自制输入（含目录）前后内容、inode、权限和mtime/ctime不变，不承诺atime；临时目录清理。每个假SDK对象仅一次显式dispose尝试，不能推断物理释放。6/74源码审阅仍NATIVE_CANDIDATE_BLOCKED、live=false，电脑预检不建目标。汇总仅忽略的 `research/output/custom-round53/`，不发布原始材料/日志/密钥/路径。

## 发布与下一轮

起点 `28351fa26de9ca90335273b87c462795d55fd7b4` 的[第五十二轮CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39580415336)已核对completed/success。总计划只更新N3四列表，滚动交接和本轮记录独立；本地原分析/计划附录保留、不发布，PRIVATE不读/暂存。提交前列出测试结果，只正常推lut-photo/main；本轮提交/新CI以最终报告为准。

第五十四轮处理进程信号到合作式取消的边界，用受控子进程和假阻塞验证调用中作业/所有权/锁保留、返回后停止新协议及处理器还原；不强杀或复位实际USB流程。完成后集中复核首次采集候选，不继续增加同类模拟层。当前保留原厂2.00卡副本，无需相机、升级、移动盘、Docker或惠普电脑；真机采集前另提示范围和所需配合。

N3事务/worker/恢复、双独立介质和N4色彩仍独立验收；真正3D LUT支线维持第二十八轮的动态配置、有效传输、MAIN身份/时序缺口。
