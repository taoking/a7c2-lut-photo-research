# N3：主机加载链边界与 BK4 只读检查

第三十六轮增加 `lutphoto.bk4` 和 `research.audit_backup_loader`。前者读取显式指定的本地快照，验证受限 BK4 格式，并把范围内记录接到原有设置比较；后者核对固定主机调用链的来源。**本轮只运行自制格式夹具，没有读取私人备份、连接相机、导入设备模块或执行目标代码。** 没有备份写回、自动恢复或相机命令。

BK4 格式依据 [ma1co/Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE) 的解析器，经 QAQLeonard [固定提交](https://github.com/QAQLeonard/a7c2-fl23-research/tree/7e54d60b458847f1befa6cfd614fbf004b8b0b90)包核对；完整[ma1co MIT 许可](Sony-PMCA-RE-MIT.txt)保留。新解析器只读，未引入上游 setter 或 USB 包。[独立 10 成员清单](../research/upstream-backup-loader.lock.json)固定 host session/transport、身份接口、core、PMCA parser/util/protocol 及许可，不修改旧运行锁或此前 worker 清单。

## 使用自制夹具

仓库根目录执行，只需 Python 标准库，无须相机、Zig、Docker 或其他电脑。输出和夹具目录必须新建，父目录须存在：

```sh
mkdir -p research/output/bk4-demo
.venv/bin/python -B -m lutphoto.bk4 fixtures \
  --directory research/output/bk4-demo/case
.venv/bin/python -B -m lutphoto.bk4 inspect \
  --input research/output/bk4-demo/case/ram-before.bin \
  --output research/output/bk4-demo/inspect.json
.venv/bin/python -B -m lutphoto.bk4 compare \
  --directory research/output/bk4-demo/case \
  --output research/output/bk4-demo/comparison.json
.venv/bin/python -B -m research.audit_backup_loader \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --output research/output/bk4-demo/source-audit.json
```

`fixtures` 生成四份自制快照和 case.json，包含固定/变长/大值、reset、未分配属性和两份 BK4 图像；不是机身备份。`inspect` 只接受命令中明确给出的本地文件，没有搜索或设备读取。`compare` 只读该目录中固定的 `ram-before.bin/saved-before.bin/ram-after.bin/saved-after.bin` 及 case.json，不接受配置文件路径跳转。

成功退出 0；校验失败、布局不支持、角色断言不符、符号链接/非普通输入、已有输出等退出 1，不生成成功报告。输出排他创建，不改输入；错误只给类型，不回显路径/数据。可用 `-S` 禁用 site packages。原始 BK4 和报告包含或关联私人设置，报告标为 `private_report`，不上传；报告只列完整输入 SHA、大小/数量及状态，不回显属性数据、header cookie/id1/版本/区域。

## 格式范围与额外拒绝条件

| 范围 | 实现 |
| --- | --- |
| Header/表 | 256 字节头，revision BK4；子系统及属性表均为 packed `<HI`，属性保存完整 16 位 attr；表区不得穿过数据起点 |
| 校验和 | 对声明图像范围求加法和，排除偏移 `0x20:0x24` 的 checksum 自身；不把它当密码学认证 |
| 属性指针 | `0xffffffff` 为未分配；高 8 位为固定长度，低 24 位为相对图像偏移；高位 0 读 `<HH` size/max，255 读 `<H` 大值长度 |
| 属性数据 | size≤max，值/分配区/长度前缀及 `attr & 0x74` 的 reset 当前值均须在声明图像内；reset 不得从下个块借字节 |
| 资源上限 | 快照≤32 MiB，单图像≤16 MiB，子系统≤65536、属性表行≤65536；候选标记≤64，声明候选总扫描工作≤64 MiB |
| 重叠 | 拒绝子系统表行别名、属性存储重叠、重叠的有效 BK4 图像和第三个有效图像；先检查存储范围，再复制数据，防止别名放大内存 |

这是保守格式子集，尚未用真实备份验证兼容性。上游通用 parser 还支持 BK2，本工具当前只接受目标流程使用的 BK4；高属性位在解析层完整保留，投影到旧 8 位设置契约时明确拒绝，绝不截断。实际格式如存在合法别名或超出限制，当前也会拒绝，不据此修改限制来操作设备。

双块读取沿用候选标记思路，但严格校验图像范围、表和数据。无效标记可出现在载荷中；外层前缀/填充/尾部保持不解释。**找到两个有效块只表示两个结构有效图像，不证明整个外层容器完整、芯片归属或机身来源。** `outer_wrapper_verified` 与 `container_complete_backup_verified` 始终 false；不要把这个工具当完整备份验收或恢复编码器。`fixture_image` 仅生成自制夹具，不保留原头/容器，不能用作原备份重建。

## 四态比较与未验证角色

case.json 只含 `schema: a7c2-bk4-comparison/1`、`roles` 和 `expected`。夹具的 roles 为 `{"AP":0,"CP":1}`；必须显式给出互异整数 0/1，拒绝 bool、猜测或自动重排。顺序仅是调用方断言；缺少 AP 02cf 或四个保护 CP 单元会拒绝，满足这些字段也不证明芯片归属。

投影只包括 AP 02cf 和四个保护 CP 单元，交给[原有设置契约](CUSTOM-CONTRACTS.md)检查目标、未选项、RAM/保存态和诊断字段。本层另外检查该范围四态的 attr、最大分配长度、当前长度和 reset 数据全部保留；即使普通值一致，也不能悄悄改变 reset/布局。其他运行组不比较，未把完整快照改写为设置计划。

`raw_backup_parsed` 在本层为 true，嵌套的旧设置契约仍为 false，因为它只收到解码记录。角色、同机身关联、真实程序身份、描述符写入计划和物理验证全部 false。BK4 的 id1 在 PMCA 接口中是开关字段，不是序列号；checksum/相似字段/完整文件 SHA 都不能单独证明同机身，配置也不接受用户填写序列号 token 来伪造认证。未来需由经过验证的捕获流程在快照之外绑定实际正常 USB 身份和程序来源。

## 主机加载链能证明什么

固定 host 代码显示：选路径命令 15、写入 16、主机临时数据≤65536 字节；先暂存/读回 worker，请求存在时也读回，然后记录意图，把写入 `libJit.so` 作为触发步骤，读取/解析结果，再按内容匹配清理已知临时文件。触发和主结果读取/解码位于 mark_unknown 异常保护内；附加结果和 cleanup 位于该段保护之外，外层 Job 安装等路径另有 NEEDS_REVIEW 处理。未来 Mac 接入必须覆盖这些不同阶段，不能把一段 except 当成所有会话异常的统一处理。本轮只审阅，不改上游会话行为。

这条 host 链没有展示 Sony 端如何映射 LOAD、分配/清零 BSS、施加权限、应用重定位及保持模块生命周期。既有文档中的 NOR/CP 启动加载证据属于另一条路径，不能补齐 Jiritsu 插件加载证明。第三十五轮的文件/ABI 检查和本轮上传流程审阅都不能将 `camera_loader_abi_verified` 改为 true；这一缺口保留至受控 N4，不继续凭主机文件名推断加载器实现。

下一轮推进“用户显式指定本地文件”的纯只读 AP/CP 身份与描述符适配入口，先列清完整来源/正例材料要求；不自行找或读取私人文件，缺真实材料时只报告拒绝/格式测试的范围。全局相机锁/USB、机身绑定 worker、设备恢复、独立介质备份及真实色彩仍未完成。目前无需连接相机，进入实测前提示；进度见[总计划](../plan.md)与[交接](../research/HANDOFF.md)。
