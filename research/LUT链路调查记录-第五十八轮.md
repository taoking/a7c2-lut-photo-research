# 第五十八轮：单槽完整程序目标、设置投影及资源逆向离线验证

日期：2026-10-21。交付独立 `lutphoto.slottarget` 和[使用说明](../docs/SINGLE-SLOT-TARGET.md)，复用既有完整身份/描述符、BK4投影、N2候选和68资源检查。完成C3中的单槽完整程序目标及精确双向重建、ST设置投影/名称资源目标与逆向；只生成内存目标和私人摘要。**N3仍部分完成，真实材料兼容性、完整设置/持久化事务、worker/部署和恢复尚未验证。**

本人原厂Ver.2.00及日常卡副本保留。没有实际SDK/共享库、USB/系统相机锁、sudo/磁盘命令、机内模块、相机/移动盘/私人材料读取；本轮无需升级、连接或准备Docker/惠普电脑。卡副本不是内部AP/CP/BK4、恢复或降级证据。

## 交付与来源

1. 读取恰好一个槽的既有selection，固定来源→完整AP/CP配对/重建身份→描述符→RAM/保存投影→N2候选→目标/资源。候选检查拆为私有_content返回同次观察的表，原_candidate接口/清单不变；资源检查拆为同次目标/逆向及固定文件枚举，旧资源摘要接口不变。没有新传输、模拟协调器或策略/指纹覆盖参数。
2. 原厂/FL23首次导入核对固定CP bootstrap旧字节并匹配完整canonical零表runtime SHA，再替换所选1215字节表/FNV。AP完整恢复并匹配原来源SHA，再按既有mask与所选位的并集重建。standalone更新保留另外五表及FNV；历史full7-v4保留整个AP和历史标签顺序，独立代码身份不混用。
3. 固定长度、非重叠/有界窗口组成内存前向和逆向；应用前检查完整源SHA与逐窗口旧字节，应用后检查完整目标SHA，实际重建结果分别逐字节等于完整目标/输入。目标再次经过完整身份与所选描述符一致检查，不忽略窗口外改动。首次CP差异分组沿用上游间隔16/窗口4096规则，零变更允许零窗口。
4. 设置由本次描述符派生九字段：基底0、八调整取本次RAM ST引用，对两快照分别构造投影目标并逆向比较所有投影字段。未选当前值、属性/reset/分配、各自诊断当前值与四保护CP保留；不生成完整BK4外层或保存设置事务，不称其他运行组已验证。
5. 同次读取的68 UXC生成目标、保留未选名称并逐字节逆向；2860新增标签的未选名称初始化ST，历史/连续标签映射由程序身份派生。摘要绑定选择/候选/表/名称及程序/投影/资源前后/还原SHA，只含计数/指纹，不导出程序、窗口、设置值、名称/资源、逆向payload或worker。

QAQLeonard固定v2.1 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`、ma1co及既有许可/署名保留；完整归档/14成员继续逐字节核验，不导入/执行归档Python或原生代码。固定元数据包括64个唯一AP模板、每来源9个AP还原区和原厂59/FL23 10个CP bootstrap区。仅来源规则审计，不是实际程序资产或机身证明。

## 实际测试命令与结果

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_slottarget.py -v` | 最终22项通过；覆盖两来源×六单槽、既有mask并集、历史布局、完整前向/逆向、窗口外/重叠/旧字节拒绝、设置/名称/输出/私密性 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_customcontracts.py -v` | 原资源/设置契约23项回归通过 |
| `.venv/bin/python -B -m unittest discover -s research/tests -p test_importmaterials.py -v` | 原材料清单22项回归通过；上述专项共67，不重复计入全量 |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 研究871项通过 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 旧Mac39项通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 旧上游8项通过；全量共918项 |
| `.venv/bin/python -B -m macfl23 check` | 固定旧源码/资产通过，未连接相机 |
| `.venv/bin/python -S -B research/output/custom-round58/audit_targets.py` | 35条AST/元数据观察、14固定上游及5本地源码身份通过；无归档执行/设备导入 |
| `.venv/bin/python -S -B research/output/custom-round58/exercise_fixed_cli.py` | 四种实际-S CLI拒绝符合预期，固定策略不改、五个自制输入内容/元数据不变并清理，无原厂正例 |
| `.venv/bin/python -B research/output/custom-round58/audit_public.py` | 270个公开文本/110份Markdown/701处本地链接及锚点通过；14项精确发布清单、隐私/密钥排除、受保护路径/锁/历史通过 |
| `git diff --check` | 通过 |

初次新专项20项中19通过、1失败：成功CLI用例的自制临时目录包含macOS的/var别名，按既有_NOFOLLOW祖先规则被NotADirectoryError拒绝。单独确认自身临时路径的规范地址可通过后，只将测试输出改用自制目录的规范路径，生产拒绝规则不改；补充显式链接父目录/输出失败和同固定runtime身份测试后，22项全部通过。固定来源CLI坏包测试也使用规范输出路径，避免被更早的父目录拒绝遮盖。

正例复用实际N2工具生成的离线候选，程序/BK4/UXC和CP bootstrap元数据均为自制小夹具，内部补充非零/边界系数验证，未放行真实策略。真实-S CLI使用固定包、99,960,744字节全零AP和18,090,880字节全零CP，在完整身份门槛拒绝，快照/候选/资源路径不存在仍未被读取；另验证坏包、已有输出和未知策略参数拒绝。退出依次1/1/1/2，无私人路径回显/新报告，五个自制输入的内容/inode/大小/权限/mtime/ctime不变，不保证atime，临时输入已清理。

完整程序目标、程序逆向和设置投影通过不证明整个设置容器/机身事务。候选元数据的拟合/阈值声明未重算；实际色彩、来源/角色/新鲜度、独立介质、加载器/worker和恢复标志仍false。摘要不是签名或写入许可，输入后来改变须重新检查，不对变化后的材料套用旧逆向。

## 发布与下一交付

起点 `5684e2a0db9e5bb8ac34b5b304f87e34e0a849fe` 的[第五十七轮CI](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39604173092)已核对success。旧安装器/默认单份备份、锁/指纹/偏移/依赖/旧测试及历史计划不改。总计划仅更新N3主表，原本地分析附录/报告保留，PRIVATE在读取内容前排除；只显式发布本轮文件，正常推lut-photo/main并核对远端/CI，实际收据留忽略目录custom-round58/publication-receipt.json及最终报告。

第五十九轮复用本轮内存结果形成私人单槽事务包，绑定完整输入/目标/逆向并能在独立读取时重验，先以自制材料交付持久化与篡改/来源变化拒绝；不重新写生成器或再加一层模拟。完整设置容器/worker接入仍须独立证据。C2真实SDK/本人首采另行提示，当前2.00保留，不自动搜盘或运行prepare/diagnose。C4恢复/独立介质、C5真实ST/摄影及真正3D LUT可行性缺口后置，备份不保证救砖。详见[交接](HANDOFF.md)与[总计划](../plan.md)。
