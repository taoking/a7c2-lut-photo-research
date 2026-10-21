# N3：原生表、名称资源与只读输入清单

第三十九轮提供 `lutphoto.importmaterials`：将 N2 候选、所选槽/名称、68 个 UXC 资源与[程序/描述符/快照只读检查](SETTINGS-BINDING.md)纳入同一份私人清单。它重新读取输入文件，不接受旧报告作为身份凭证。规则及许可沿用 QAQLeonard/ma1co 的[固定来源与致谢](../ACKNOWLEDGEMENTS.md)，旧 FL23 锁/安装器和依赖不变。

**本轮只用自制材料：N2 候选由实际 `nativefit` 生成，完整程序/BK4/UXC 正例为夹具，真实 CLI 只验证拒绝。** 没有读取私人材料、执行目标模块或操作相机。此工具不输出固件/设置目标或 worker，资源改名/撤销仅在内存验证；N3 仍部分完成。

## 准备选择文件

N2 的 `fit` 输出可直接作为候选目录，固定为 `candidate.json` 与 `correction.table` 两个普通文件，不允许缺失、额外文件或链接。候选路径相对选择文件所在目录，逐层拒绝 `..`、绝对路径和链接。例如：

```json
{
  "schema": "a7c2-import-material-selection/1",
  "slots": {
    "1": {"candidate": "candidates/own-look", "name": "My Look"},
    "6": {"candidate": "candidates/own-look", "name": "My Look 6"}
  }
}
```

选择文件只接受这两个顶层字段；槽位须为字符串 `1`–`6`，非空，不接受重复键或多余字段。名称限 1–63 个 UTF-8 字节，拒绝 C0/DEL/C1 控制字符；同一候选可用于多个槽，一次读取结果供这些槽复用。选择文件及名称原文不进入报告，只记录完整选择文件 SHA 和名称 UTF-8 SHA。清单仍是私人材料，哈希不是匿名化。

## 只读命令

只需 Python 标准库，不导入 NumPy 或设备包；N2 拟合本身仍使用原研究依赖。所有路径须由本人明确提供；示例为占位路径。报告放在独立输出目录，必须尚不存在：

```sh
mkdir -p research/output/material-demo
.venv/bin/python -S -B -m lutphoto.importmaterials \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --ap "/path/to/owner-backup/appFw.so" \
  --cp "/path/to/owner-backup/cpapp-b.bin" \
  --ram "/path/to/owner-backup/ram.bin" \
  --saved "/path/to/owner-backup/saved.bin" \
  --selection "/path/to/owner-materials/selection.json" \
  --resources "/path/to/owner-backup/resources" \
  --ram-roles 0 1 --saved-roles 0 1 \
  --output research/output/material-demo/manifest.json
```

两个角色参数各为 AP/CP 索引的显式断言，示例 0/1 不是相机默认值，也不证明角色。所选槽完全来自选择文件；没有额外 `--slots`、布局覆盖、程序指纹或设备放行参数。先通过完整程序/描述符/快照检查，再打开候选及资源。成功 0，检查失败 1，参数错误 2；错误只输出类型，输出排他创建，源文件保持原字节。

## 核对内容

| 材料 | 检查与范围 |
| --- | --- |
| N2 候选核心格式 | schema/version/固定上游提交、三项来源 SHA 语法，以及仍为机外候选的标志；JSON≤128 KiB，拒绝重复键、过深结构、非有限数，包含溢出指数 `1e999` |
| 原生表 | 固定文件名/布局、恰好 1215 字节、完整 SHA、每个 signed int8 系数在 −64…63；不沿候选中的其他路径读取项目/CUBE/模型 |
| 声明阈值 | 要求 `acceptance.passed:true` 且声明的 RGB MAE/Delta E76 P95 与正有限阈值一致；只核对已有声明，未重算拟合、模型、桥接或照片误差 |
| 冻结验收 | 可选 `validation_lock_sha256` 只检查规范 SHA 语法并由候选完整 SHA 绑定，未读取/重验冻结清单或独立场景 |
| 名称资源 | 恰好固定的 68 文件、每项格式/大小/链接等规则继承[资源契约](CUSTOM-CONTRACTS.md)，改名与完整逐字节逆向在内存检查，不输出资源或逆向 payload |
| 标签顺序 | 从本次已识别程序导出：full7-v4 用历史六槽顺序，stock/FL23/standalone 用连续顺序，调用方不能覆盖；前者只接受 2866 项，后者按既有契约接受一致的 2860 或 2866 项 |

候选完整 SHA 绑定其全部元数据，但内容一致不证明这些声明真实。`project_model_or_fit_revalidated`、`validation_lock_revalidated` 和真实色彩标志保持 false。资源格式/逆向通过也不证明这些资源与 AP/CP 来自同一捕获或同一安装阶段，不作为原厂/Custom 资源的完整指纹白名单。

## 清单含义与下一步

`materials_sha256` 将本次程序/快照检查结果、完整选择文件 SHA、逐槽候选/表/名称 SHA、明确角色断言、68 文件的来源/内存目标/还原 SHA 和程序派生布局一起规范序列化后求 SHA。报告不输出私人路径、名称、设置键/值、表/程序字节或写计划；完整报告必须留在私人/忽略目录，不能上传公开仓库。

这是本次读入内容的指纹清单，不是签名、机身认证、后续写入许可或完整事务。文件之后改变须重新读取；新鲜度、同机身捕获、独立备份、完整 AP/CP 与设置前向/逆向事务、worker/部署均未验证。68 个资源的数学逆向不能替代程序逆向或设备恢复。

真实材料只读正例检查点仍未完成。有**现有**工作/备份目录时，由本人提供本地路径及捕获来源/当前状态；若已有68资源目录再验证完整清单，否则先验证AP/CP与RAM/保存快照，并记录资源缺口。没有备份或仍为Ver.2.00时，先看[日常备份与官方升级分流](BACKUP-GUIDE.md)：卡文件/菜单设置不满足这里的输入契约，官方升至2.01也不自动产生内部开发材料。第五十七轮已交付独立[首次内部采集入口](CAPTURE-FIRST-USE.md)，但仅用自制SDK/材料离线验收，实际SDK/同机身材料仍待验证；本人2.00现在继续保留。已有[旧演练目录检查](CAPTURE-INSPECTION.md)与[独立检查点/回执检查](CAPTURE-EVIDENCE.md)均不重验本材料契约或提供续跑许可。自制演练输出不能代替真实材料，角色、同源性和捕获原子性不自动推断。

不自动搜盘，也不为补齐文件运行相机 prepare/diagnose。相机实测、USB/全局锁、恢复、独立介质和真实色彩继续后置，进入前提示；当前无需连接相机或准备 Docker/惠普电脑。见[总计划](../plan.md)及[交接](../research/HANDOFF.md)。

第五十八轮新增独立[单槽目标/逆向检查](SINGLE-SLOT-TARGET.md)：选择文件恰好一个槽时，复用候选/完整程序/快照/资源检查并直接使用同次观察的表字节，在内存生成完整程序目标、设置投影及名称资源，验证精确逆向，仅导出私人摘要。原清单接口/格式及false标志不变；它的哈希不能代替新检查，新的成功也不证明实际材料来源、完整设置事务、部署或恢复。
