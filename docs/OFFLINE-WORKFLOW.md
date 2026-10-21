# D3：统一离线入口

第六十三轮完成D1–D3的离线收口。`lutphoto.offline`把CUBE拟合、参考图/预测/误差、私人单槽包、程序/名称元数据、设置单元方案及逆向核对放到同一流程。**不连接USB、不加载SDK或机内模块、不写相机，也不是安装器。** N3仍部分完成，真实采集、机身事务和摄影验收分别留D4–D6，见[交付计划](DELIVERY-PLAN.md)。

## 先运行全部自制的演示

使用现有Python环境及[离线依赖](NATIVE-FIT-OFFLINE.md)。输出父目录须已存在、归当前用户所有且权限0700，位于仓库外；作业目录必须全新。下面可以直接运行，创建私人临时父目录；程序会打印该路径，演示后自行保留或整理，不能将目录上传仓库。

```sh
.venv/bin/python -B - <<'PY'
from pathlib import Path
import tempfile
from lutphoto.offline import demo
parent = Path(tempfile.mkdtemp(prefix='a7c2-offline-')).resolve()
directory = parent / 'demo'
result = demo(directory)
print(directory / 'RESULT.md')
print(result['phase'], 'synthetic_only:', result['synthetic_only'])
PY
```

若已有符合条件的私人父目录，可直接使用CLI（示例路径需替换）：

```sh
.venv/bin/python -B -m lutphoto.offline demo \
  --directory "/private/tmp/A7C2-private/demo-001"
```

演示不需要上游归档或相机材料。输入是自制RGB图、仿射暖色CUBE和单位响应模型；微小误差只表示这套数学模型与原LUT的接近程度，不能作为Sony ST、胶片风格或摄影质量证明。生成的微型AP/CP、BK4包裹和68份UXC也全是自制数据，不能放进相机。演示策略固定在内部，归档哈希全零，生产Reader会拒绝；没有外部程序输入、策略/身份覆盖或启用开关。演示包不能转为本人材料包继续使用。

## 阅读本次结果

| 文件/目录 | 内容 |
| --- | --- |
| `RESULT.md` | 中文结果、误差、作用范围和下一阶段缺口 |
| `input/` | 仅演示创建；自制模型/图/CUBE，实际演示项目是`demo-project.json` |
| `candidate/` | 原生表`correction.table`（1,215字节）及`candidate.json` |
| `evaluation/` | 原LUT的`reference.png`、原生预测`prediction.png`及`comparison.json` |
| `bundle/` | 固定150份私人输入/目标/逆向材料、清单与锁；保持既有包格式 |
| `observations/` | 仅演示创建；自制source/target/restored的RAM/保存快照，6份离线重验 |
| `result.private.json` | 同一Reader绑定的拟合来源、两类worker契约、九属性正反向方案/顺序、逆向结果及未证标志 |

参考图带sRGB配置；ST身份为显式声明，不从sRGB标签推断。不提供分区掩码时，肤色/灰阶/绿植/天空/高光/阴影/饱和色显示缺少数据；有掩码也只报告误差，统一入口不额外认证每区质量。真正独立场景验收继续使用[冻结验收工具](NATIVE-VALIDATION.md)。

程序/名称只生成供审阅的内存元数据，不编译/保留头或模块、不构造假原生回执。D1/既有程序编译证据另见[名称](NAME-WORKER-OFFLINE.md)/[程序](PROGRAM-WORKER-OFFLINE.md)文档。设置方案含私人属性值，复用原生成器的目标；全解码映射的虚拟逆向精确，BK4外层继续只读，不生成原厂完整目标。实际独立属性读回/保存、资源全读回、所有运行组保留、重载/冷启动及恢复均未证。

## 本人材料：固定来源构建

以下只在D4取得同机材料后使用，**当前没有本人的真实正例**。不从聊天/未知目录自动寻找程序、资源或备份；显式传入项目、ST输入、完整AP/CP、RAM/保存快照、明确角色和固定68资源目录。来源策略仍由固定v2.1归档加载，完整长度/指纹/描述符/设置不匹配时，在拟合及输出目录创建前拒绝；候选表和资源随后继续使用原有完整检查。

```sh
.venv/bin/python -B -m lutphoto.offline build \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --project "/private/tmp/A7C2-private/style/project.json" \
  --input "/private/tmp/A7C2-private/style/st-reference.png" --st-input \
  --ap "/private/tmp/A7C2-private/source/appFw.so" \
  --cp "/private/tmp/A7C2-private/source/cpapp-b.bin" \
  --ram "/private/tmp/A7C2-private/source/ram.bin" \
  --saved "/private/tmp/A7C2-private/source/saved.bin" \
  --resources "/private/tmp/A7C2-private/source/resources" \
  --ram-roles 0 1 --saved-roles 0 1 \
  --slot 1 --name "My Look" \
  --directory "/private/tmp/A7C2-private/style-review-001"
```

`--assume-srgb`仅用于明确解释无配置图像；不代替`--st-input`。`--masks`使用原[掩码格式](NATIVE-FIT-OFFLINE.md)，`--validation-lock`复用原冻结清单检查，不新增验收机制。角色0/1只作例子，AP/CP索引需要真实来源核对。首版只选一个槽/一个风格，第一真实来源限定原厂2.01；已有生产策略中的FL23/standalone/历史来源保护保留，不因此扩首次设备范围。

拟合留出和输入图对比须满足项目事先声明的整体阈值；失败保留已生成文件，不生成完整成功结果。构建后重新打开包，重建全部目标/逆向，并在同一Reader内绑定三份契约、候选表、显式项目/模型/桥接及输入图片；独立关闭检查完成后才保存最终结果。生产路径不接受演示策略，也不根据清单选择策略。来源哈希、同机来源/新鲜度、独立存储、实际执行和摄影验收分别记录，完整指纹通过仍不等于其他项通过。

stdout只输出schema、phase、synthetic_only和device_operations_enabled；私人名称/路径/设置/指纹在私人文件。退出0表示本次离线流程及结果保存/终端输出完成；退出1表示停止，保留所有部分结果；退出2表示参数错误。已有目录、链接、共享输出父目录和仓库内输出拒绝。不覆盖、不修复、不续跑，终端失败也不重新执行；完整JSON文件不能单独证明整个CLI成功结束。

## 离线冻结与D4配合

D1–D3至此冻结；后续只处理明确缺陷或本人真实材料问题，不继续添加模拟传输/回执或自制轮次。下一步是D4真实只读首采，不是直接安装。

目前继续保留原厂Ver.2.00。进入D4前，一次说明并等待本人完成以下配合：

1. 明确是否选择索尼官方2.01升级；尚未决定时保留2.00，不运行2.01采集，不用修改升级包、prepare或diagnose取材料。升级按[备份/升级指南](BACKUP-GUIDE.md)另行安排，不由本入口触发；不能假定可降级。
2. 真正准备采集时，提供菜单中的机型/版本及刚查看的实际电量（至少50%），按提示用数据线直连Mac并选MSC。明确只读首采范围包含68份UXC；服务认证/选读会改变临时状态，但不加载模块、写程序或保存设置。管理员认证只在系统/终端完成。
3. 指定仓库外本人私人输出位置，先核对电脑端环境/权限/固定来源，再按[首次采集说明](CAPTURE-FIRST-USE.md)安排受控采集。真实SDK、通信/退出表现与同机材料在D4分别记录；异常保留现场、不重跑。

本轮无需现在升级、连接相机、读取移动盘或准备Docker/Windows。现有卡副本不算内部AP/CP/BK4备份。D5真实事务/恢复审阅及两份独立介质完整内部备份后，才另行安排单槽持久化写入；采集默认仍只生成一份，备份不能保证救回无法启动的相机。D6再做真实ST标定、一种风格与独立场景的摄影验收。

实现和审阅证据见[第六十三轮](../research/LUT链路调查记录-第六十三轮.md)，固定来源/许可见[致谢](../ACKNOWLEDGEMENTS.md)。
