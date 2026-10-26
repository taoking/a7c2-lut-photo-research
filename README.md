# A7C II LUT 照片研究与 macOS 工具

本仓库提供机外 LUT 参考工具、[原生 Creative Look 离线拟合与预测](docs/NATIVE-FIT-OFFLINE.md)和只读固件研究。**本仓库尚未集成机内自定义外观导入，任意 3D LUT 照片直出也未实现。** 近期主线调整见[v2.1 审计与接入计划](docs/UPSTREAM-V2.1-AUDIT.md)。 从[研究说明](research/README.md)、[总计划](plan.md)和[当前交接](research/HANDOFF.md)开始查看。公开内容与发布边界见[发布说明](docs/PUBLISHING.md)。

仓库继承 [MDHan/a7c2-fl23-macos](https://github.com/MDHan/a7c2-fl23-macos) 的 macOS FL2/FL3 适配代码与历史；下方保留其安装说明和验证来源，不能将这些证据视为新 LUT 功能的实机验证。

本项目直接基于 **[QAQLeonard/a7c2-fl23-research](https://github.com/QAQLeonard/a7c2-fl23-research)**（QAQLeonard／小红书「QAQLeonard（读研版）」）进行 Mac 适配。感谢原作者开放 A7C II 的补丁研究、机内工具和验证记录。

## 按用途选择入口

- **只有CUBE/参考图、还没内部备份：** 用[纯机外preview](docs/COMPUTER-ONLY-PREVIEW.md)拟合/看图/看超限原因，无需归档或机身材料；真实机内色彩尚未验证。
- **现在先运行完整离线演示：** [统一入口与结果说明](docs/OFFLINE-WORKFLOW.md)，串通CUBE拟合、参考图/误差、私人包与程序/名称/设置逆向检查；默认材料全自制，无需相机。
- **跟进开发：** [后续交付计划](docs/DELIVERY-PLAN.md)按离线演练、真实只读采集、单槽与摄影验收推进；[当前交接](research/HANDOFF.md)列下一动作。D1–D3离线冻结，D4仍0材料。[第七十七轮](research/LUT链路调查记录-第七十七轮.md)完成[有限服务入口](docs/CAPTURE-SERVICE-PROBE.md)的单次准备与172文件冻结，1122项离线回归及15项准备测试通过；本人已确认MSC/官方原厂2.01，待现场运行受控小范围验证。本入口只读一份快照，旧完整入口仍保留MSC检查，第72轮准备继续暂停。
- **获取内部材料：** 另读[首次采集说明](docs/CAPTURE-FIRST-USE.md)，仅支持固定原厂2.01/完整程序身份；本人已确认官方2.01，最新失败保留UNKNOWN，不能重跑示例试错。
- **安装旧FL2/FL3：** 使用[旧安装指南](docs/AI-INSTALL.md)及下方教程；它有独立的适用条件、操作范围和验证边界，新LUT尚未提供机内安装入口。

## 原项目与贡献来源

把直接上游及其引用的研究、工具一并列在这里，方便追溯：

| 仓库 | 贡献与本项目的关系 |
| --- | --- |
| [QAQLeonard/a7c2-fl23-research](https://github.com/QAQLeonard/a7c2-fl23-research) | 本项目直接使用的 A7C II 2.01 移植与安装工具：补丁定位、色彩映射、机内安装/恢复、诊断与验证实现。 |
| [lzh2016zzz/a7cr-fl23-research](https://github.com/lzh2016zzz/a7cr-fl23-research) | 上游引用的 A7CR FL2/FL3 移植、参数、标签与 WBI 研究；A7C II 由上游另行定位实现，不能直接套用 A7CR 偏移。 |
| [YuuLuo/a7c2-service-preload](https://github.com/YuuLuo/a7c2-service-preload) | 上游引用的 A7C II 2.01 服务认证与机内执行链研究。 |
| [ma1co/Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE) | 上游使用的 USB/Senser 通信、机身备份操作和解析实现。 |
| [ma1co/fwtool.py](https://github.com/ma1co/fwtool.py/pull/52) | 上游引用的官方固件离线解包分析工具，具体为 PR #52；本项目运行时不依赖它。 |

我们的新增工作是 macOS USB 接管、流程与错误处理、备份核验及简明/AI安装教程。上述移植研究与基础工具的贡献归各原作者；固定提交、许可和完整致谢见 [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)。

> **相机安装工具：这是实验性相机改装，有无法正常开机的风险，备份不保证能救砖。** 继承的 Mac 适配工具已有固定提交的 `verify` 实机记录；其通用版首次备份、安装和恢复仍未实机测试。[查看验证来源与范围](docs/VALIDATION.md)

回滚与后续更新的完整评估见[全项目实现与回滚安全评估](docs/ROLLBACK-SAFETY-REVIEW.md)：区分离线逆向、正常撤销、中断恢复和无法启动时的救援，并列出后续实现与写入验收门槛。[持续供电更新方案](docs/POWERED-UPDATE-SAFETY.md)进一步限定首版的阶段恢复、时间预算和每轮可用性验收。当前不能承诺断电可恢复或未来官方更新兼容。

[硬件平台与独立恢复入口调查](docs/HARDWARE-RECOVERY-RESEARCH.md)已从索尼公开内核核对ARM64／CXD90057平台，并梳理同系列相机的BootROM／RAM恢复研究和最新上游原厂功能恢复边界；A7C II独立入口与写回闭环仍未实机验证。

> **已知安装中断问题：** [Issue #2](https://github.com/MDHan/a7c2-fl23-macos/issues/2) 报告在 `writing_settings` 因 `0x02770015` 变化停止。此时程序可能已经写入，但收尾未完成，不能直接重装。专项 `diagnose` 仅经过离线测试、尚未真机验证；它会进入服务模式并运行临时模块，仍存在设备操作风险。请先阅读 [适用条件、风险和诊断方法](docs/INTERRUPTED-INSTALL.md)，再自行决定是否运行。

## LUT 照片开发进度

主线是上游v2.1的原生Creative Look拟合。N1[固定源码审计](docs/UPSTREAM-V2.1-AUDIT.md)完成；N2[拟合/预测](docs/NATIVE-FIT-OFFLINE.md)和[配对标定/冻结验收](docs/NATIVE-VALIDATION.md)离线工具已具备，真实ST与相机精度仍待N4。N3已有完整程序/描述符、设置/资源及来源检查；[公开首次内部采集入口](docs/CAPTURE-FIRST-USE.md)已接通固定读取、独占/信号收尾和独立回执，**只用自制SDK/材料完成离线验证，尚无本项目首次真机采集正例**。另有[单槽目标/逆向验证](docs/SINGLE-SLOT-TARGET.md)及[私人事务包/独立重验](docs/SINGLE-SLOT-BUNDLE.md)，连接N2表、设置投影和68名称资源，包内含完整私人输入/目标/逆向；新增[程序worker绑定/离线编译与报告检查](docs/PROGRAM-WORKER-OFFLINE.md)，固定C仅在临时目录编译并删除，未执行；第六十一轮另完成[名称worker绑定/编译/四模式报告检查](docs/NAME-WORKER-OFFLINE.md)，D1离线完成；第六十二轮完成[设置单元正反向方案/快照阶段核对](docs/SETTINGS-PLAN-OFFLINE.md)，D2离线完成；第六十三轮完成[统一离线入口/演练/整体审阅](docs/OFFLINE-WORKFLOW.md)，D3离线完成，冻结D1–D3版本；第六十四轮[D4电脑端核验](docs/D4-HOST-READINESS.md)已确认真实SDK导入/动态库加载；实际SDK通信/退出、同机材料、属性保存和机身事务/写入/恢复仍未证。

首次采集只支持本人ILCE-7CM2原厂2.01及固定完整AP/CP指纹，要求实际版本/电量、管理员权限和新私人输出；服务认证/选读路径会改变临时状态，不加载模块或写程序/保存设置。材料检查点、内部终态、回执传递及CLI退出分开判断，见[证据/回执](docs/CAPTURE-EVIDENCE.md)。候选review仍是无设备操作的源码审阅，不能改JSON当采集许可。本人已确认官方2.01；[第六十九轮](research/LUT链路调查记录-第六十九轮.md)新作业在枚举边界失败，身份/认证未开始、0材料，尚无内部备份；当前仅做已有日志/源码分析与离线故障验证，不据正常画面或本地清理结果放行重采。

任意3D LUT的M2–M4保留研究支线，动态配置、有效传输、MAIN身份/时序未闭合，不视为通向完整JPEG的证明。旧FL2/FL3锁/安装器保持原样。总状态见[四列里程碑](plan.md)，交付顺序与收口条件见[后续计划](docs/DELIVERY-PLAN.md)，下一动作读[当前交接](research/HANDOFF.md)，历史证据查[轮次索引](research/ROUNDS.md)。

## 先确认设备和版本

尚未做过备份，或当前是原厂 Ver.2.00，先看[日常备份与官方升级说明](docs/BACKUP-GUIDE.md)：先保存照片/菜单设置，决定更新时使用索尼官方 Ver.2.01；卡文件副本不能代替内部开发备份。内部开发材料另用[首次采集入口](docs/CAPTURE-FIRST-USE.md)，它只支持原厂2.01且尚未真机验证；不要用下文 `prepare` 给不支持的版本试采集。升级成功仍需完整程序指纹检查。

| 需要什么 | 要求 |
| --- | --- |
| 相机 | **索尼 A7C II / A7C2，型号 ILCE-7CM2**；不适用于 A7CR 或其他型号 |
| 相机固件 | **原版 2.01**；工具还会核对完整程序指纹，不能只看菜单版本号 |
| 电脑 | **Mac**；实测为 **MacBook Air M4 / arm64**，其他芯片未验证 |
| 系统 | 实测 **macOS 27.2**；尚未确定最低兼容版本，不要求为此升级到这个版本 |
| Python | **3.10 或更新版本**；实测 **3.12.14**。运行 `python3 --version` 检查；未安装或版本过低时，先安装符合要求的 Python |
| 连接线 | **能传数据的 USB 线**，相机直连 Mac；纯充电线不行 |
| 电池与存储卡 | 相机实际电量 **至少 50%**；准备可正常拍摄的存储卡，用于安装后试拍 |
| 其他 | Mac 接电、首次下载需要网络；Mac 管理员密码由你在系统/终端中输入 |

已经装过 FL2/FL3 的相机，**不要从头再安装**。保留已有工作目录，先按下文“怎么查看目前做到哪一步？”检查状态，再根据所处阶段完成冷启动和验证。

## 方式一：让 Codex / Claude 帮你操作

使用**能访问本机文件和终端**的 Codex、Claude Code 或其他本地 AI 工具。普通网页聊天不能直接操作你的 USB 相机。

把下面整段复制给它：

```text
请帮我使用这个项目，在我的 Mac 上给 Sony A7C II 安装 FL2/FL3：
https://github.com/taoking/a7c2-lut-photo-research

先阅读 README.md、AGENTS.md 和 docs/AI-INSTALL.md，检查设备、固件、
Python 和已有安装状态；不满足支持条件就停止并说明。
我了解这是实验性改装，授权你完成环境准备、单份备份、预检查、安装和验证。
能自动完成的请直接执行，不要每一步都询问。
需要我连接相机、选择 MSC、提供实际电量、输入管理员密码或取电池时，
一次告诉我具体操作，等我完成再继续，不要猜测或代填。
如果已经安装过，保留已有工作目录，只验证，不重复安装。
遇到报错先检查阶段和日志，不强制重试，不修改校验或伪造成功状态。
完成后告诉我验证结果和备份位置，不要上传我的机身数据。
```

**你需要亲手做的事很少：连接相机并选 MSC、输入实际电量和管理员密码、按提示取电池重启、试拍。** AI 不能替你拔电池，也不应索取你的密码。详细流程见 [AI 安装指南](docs/AI-INSTALL.md)。

## 方式二：自己按步骤操作

下面命令在 Mac 的「终端」运行。默认只保存**一份原始备份**。每一步成功后，再进行下一步。

下面的输出示例根据当前仓库与固定版本上游代码整理，用于对照提示，**不是通用版全流程已经实测通过的记录**。终端中文提示统一使用简体；磁盘编号、下载日志和个人路径会因电脑而异。

只复制标为 `sh` 的命令框，不要把输出示例或终端里的用户名、`%`、`$` 提示符一起复制。后续命令都在下载的 `a7c2-fl23-macos` 目录中执行。

### 1. 下载工具

先输入 `python3 --version`，确认至少是 3.10。然后复制：

```sh
git clone https://github.com/taoking/a7c2-lut-photo-research.git
cd a7c2-lut-photo-research
./setup.sh
```

首次运行会显示依赖下载、安装日志。正常结束前会看到：

```text
固定版本上游下载与全部文件哈希核验通过；未连接相机。
套件源码和资产完整；未连接相机。
```

这表示电脑端工具准备完成，还没有检查或操作相机。**这一步不加 sudo。** 如果没有成功结束，先按提示处理：

- 系统提示安装命令行开发者工具：完成安装后，再执行下载命令。
- 提示找不到 `python3` 或 Python 版本过低：先安装 Python 3.10 或更新版本，重新打开终端，确认 `python3 --version` 符合要求。
- 依赖或上游文件下载失败：先检查网络；若已经进入项目目录，可重新运行 `./setup.sh`。此步骤不操作相机；哈希核验失败时不要跳过校验。
- 提示 `a7c2-fl23-macos` 文件夹已存在：先检查是否为此前下载的项目；确认后进入该目录继续，不要直接删除重来。

### 2. 连接相机，选第 2 项

相机开机，用数据线直连 Mac。出现四个选项时：

| 选项 | 怎么选 |
| --- | --- |
| 1 实时流式传输（USB流式传输） | 不选 |
| **2 影像传输（MSC）** | **选这个 ✅** |
| 3 影像传输（MTP） | 不选 |
| 4 遥控拍摄（电脑遥控） | 不选 |

后面再次出现这个界面，仍选 **第 2 项**。关闭正在浏览相机存储卡的窗口，然后运行：

```sh
./a7c2-mac usb-status
```

正常时会输出类似下面的 JSON（示意一组磁盘，实际可能有多组）：

```json
{
  "target": "054c:0e8a",
  "media": {
    "disk4": {"parent": "disk4", "whole": true, "mounted": false},
    "disk4s1": {"parent": "disk4", "whole": false, "mounted": true}
  },
  "camera_commands_sent": false
}
```

看这三点即可：

- `target` 是 `054c:0e8a`，表示识别到预期的 MSC USB 设备。
- `media` 中有相机磁盘；`disk4` 只是例子，**不需要与你的编号一致**。如果是空的 `{}`，先排查，暂不继续。
- `camera_commands_sent: false` 是正常结果，表示这一步只读取电脑上的设备信息，没有给相机发送命令。

这里出现 `mounted: true` 并不代表失败，后续工具会自动卸载核实过的相机磁盘。此步通过也不等于接口接管、固件版本或备份已通过；这些还要在下一步检查。

### 3. 备份并检查

```sh
sudo ./a7c2-mac prepare --workspace "$HOME/Pictures/A7C2-work"
```

出现 `Password:` 时输入 Mac 管理员密码，终端**不会显示字符，也不会显示星号**，输完按回车即可；如果近期已认证，也可能不再询问。

正常流程中的关键提示如下（磁盘卸载行数按实际设备而定）：

```text
正常卸载已核实的相机磁盘：disk4
读取并备份完整程序：cpapp-b.bin
读取并备份完整程序：appFw.so
备份及候选已核验。开始机内诊断（上传临时模块，不写固件或保存设置）。
服务模式已退出，等待普通 USB 连接；若相机询问连接模式，请选第2项「影像传输（MSC）」。
RESULT: prepared
备份和机内预检查完成；尚未写入固件或保存拍摄设置。
```

读完整程序和机内检查时可能一段时间没有新文字，工具没有连续百分比进度条；不要仅凭暂时没输出就按 `Ctrl+C`。相机再次询问连接模式时，及时选 **第 2 项 MSC**，保持 USB 连接。

**只有看到 `RESULT: prepared`，且命令正常结束，才按下面步骤安装。** 仅看到“备份及候选已核验”还不够，后面仍有机内预检查。

备份在「图片 → A7C2-work → original」。此步会运行临时诊断模块，尚未写入固件。若提示目录已存在，**不要删除旧目录或覆盖备份**。先用下文的 `status` 命令查看该目录状态；若状态文件缺失或无法读取，保留目录，按故障说明排查，不继续安装。

### 4. 安装

复制下面整段，按提示输入**相机屏幕显示的实际电量数字**（50–100）：

```sh
(
  printf '相机当前实际电量（50–100，只输入数字）：'
  read -r A7C2_BATTERY
  sudo ./a7c2-mac install --workspace "$HOME/Pictures/A7C2-work" --battery-percent "$A7C2_BATTERY"
)
```

开始后保持连接，不拔线、不关机、不同时运行其他相机操作。正常流程会依次出现这些关键提示（摘录，中间省略其他提示）：

```text
正在写入固定窗口；请勿拔线或关机。
完整读回 cpapp-b.bin
完整读回 appFw.so
程序及保存设置已验证，正在处理旧开机快照。
服务模式已退出，等待普通 USB 连接；若相机询问连接模式，请选第2项「影像传输（MSC）」。
RESULT: installed_pending_cold_start
```

- “正在写入固定窗口”：已进入程序写入阶段，继续等待。
- “完整读回”：正在读取并校验安装后的程序；**看到这行不等于该文件已校验完成，更不等于整个安装完成**。
- “正在处理旧开机快照”：仍在处理安装后的启动状态，继续等待。
- “等待普通 USB 连接”：若相机弹出四选一界面，再选 **第 2 项 MSC**；这是正常流程的一部分。
- `RESULT: installed_pending_cold_start`：安装及本轮核验完成，命令结束后才进行下一步取电池重启。这里的 `pending` 表示还需要冷启动，并非安装失败。

没有出现上述最终结果，或结果带 `_usb_unconfirmed` 后缀时，先看下方故障说明，不要自行重复安装。

### 5. 取电池重启，检查菜单并试拍

**只有上一步完成后**才按这个顺序操作：

1. 拔 USB，正常关机，等存取灯熄灭。
2. 取出电池约 **10 秒**，装回开机。
3. 查看 FL2/FL3 是否出现，分别使用相机内建重设；用 ST、FL2、FL3 各拍一张新照片并回放。

**完成以上步骤，FL2/FL3 菜单正常显示，ST、FL2、FL3 均能正常拍摄和回放，就完成了基本使用检查，可以结束操作。无需为了日常使用再次连接 Mac。** 保留整个 `A7C2-work` 文件夹。

### 可选：重新连接 Mac，做一次电脑端复核

**下面这一步不是必做项，是额外的保险验证。** 想进一步检查冷启动后的程序文件、参数和运行状态，可以重新连接 Mac，选 **第 2 项「影像传输（MSC）」**，运行：

```sh
sudo ./a7c2-mac verify --workspace "$HOME/Pictures/A7C2-work" --cold-start-confirmed
```

正常流程中的关键提示如下：

```text
正常卸载已核实的相机磁盘：disk4
完整读回 cpapp-b.bin
完整读回 appFw.so
服务模式已退出，等待普通 USB 连接；若相机询问连接模式，请选第2项「影像传输（MSC）」。
磁盘程序与保存参数符合预期；菜单、照片及回放仍需实际检查。
RESULT: verified_after_cold_start
```

最后的 `RESULT: verified_after_cold_start` 表示这次额外的电脑端复核通过。菜单和试拍检查只能确认基本使用正常，不能替代这项程序、参数及运行区域核验；选择跳过时，不代表电脑端已核验通过。此命令会进入服务模式并运行临时诊断模块，但不会重新安装补丁。

### 怎么查看目前做到哪一步？

在没有其他相机命令运行时，可以执行：

```sh
./a7c2-mac status --workspace "$HOME/Pictures/A7C2-work"
```

此命令只读取电脑上的状态文件，不需要 sudo，也不连接相机。以输出中的 `phase` 为主要依据：

| `phase` | 含义 |
| --- | --- |
| `prepared` | 备份与预检查完成，可以进入安装步骤 |
| `installed_pending_cold_start` | 安装完成；需手动冷启动并试拍。若跳过可选的电脑复核，即使已完成试拍，此记录也不会自动更新 |
| `verified_after_cold_start` | 冷启动后的电脑端核验完成，仍需人工试拍 |
| 带 `_usb_unconfirmed` 后缀 | 操作主体已核验，但普通 USB 返回未确认，按下面说明处理 |
| `needs_review` 或其他中间阶段 | 不能当作完成；保留现场，先检查日志 |

如果还有 `failed_during` 或 `last_error`，可能是此前失败留下的记录，需要结合当前 `phase` 和最新日志判断。`status` 仅展示已有记录，不会重新核验相机；工作目录尚未创建时也不能用它判断安装结果。

## 报错了怎么办？

出现 `STOPPED`、未知报错或 `needs_review` 时，**先停，不重复安装、不手改状态、不直接取电池**。保留工作目录和终端输出，先按下表对照处理。无法确定原因时，可在 [GitHub Issues](https://github.com/taoking/a7c2-lut-photo-research/issues) 提供相机固件版本、Mac/系统版本、执行的命令及脱敏后的报错文字；不要上传整个工作目录。下面几项是我们实际遇到过、或当前工具会明确区分的情况：

| 看到什么 | 怎么理解、怎么处理 |
| --- | --- |
| `Password:` 后输入没有显示 | 正常的密码输入方式，输完按回车；不是卡住 |
| `sudo: a password is required` | 当前命令未获得管理员授权。若尚未开始相机操作，在本机终端按教程使用 `sudo` 执行并输入密码；已经开始操作则先检查阶段，不直接重跑。密码仅在本机输入 |
| `Access denied` / `insufficient permissions`，即使加了 sudo | 我们此前遇到过 macOS 存储驱动占用接口。当前工具会尝试卸载已核实的相机磁盘并临时接管；若仍报错，停止排查，不关闭 SIP、不强制卸载系统驱动 |
| `Camera volumes did not all unmount` | 当前这次 USB 接管前，磁盘未全部卸载。检查是否有 Finder 或其他应用占用；不要绕过检查，也不能据此推断此前所有步骤都没有写入 |
| `完整读回 appFw.so` 后相机询问连接模式 | 选择第 2 项 MSC，继续等最终 `RESULT`；不要拔线或重新运行安装 |
| `RESULT: prepared_usb_unconfirmed` | 备份和预检查完成，但普通 USB 返回未确认；尚未写入固件。先确认相机回到 MSC，再按故障文档继续 |
| `RESULT: installed_pending_cold_start_usb_unconfirmed` | 当前工具已核验安装主体完成，仅普通 USB 返回未确认。不要重跑安装；确认相机无错误、存取灯熄灭后，按故障文档冷启动并验证 |
| `RESULT: verified_after_cold_start_usb_unconfirmed` | 程序、参数和运行区域核验完成，普通 USB 返回未确认。检查连接选择与相机状态，不重新安装 |
| 其他 `STOPPED`、读回不符、断线或超时 | 不能套用上面的“仅 USB 返回未确认”处理。保留现场和日志，先判断实际阶段 |

我们早期脚本曾显示 `STOPPED: normal USB return: Expected USB identity did not appear: 0e8a`。**这条旧报错本身不代表安装成功**；当时是核对写入证据、完成冷启动与后续验证后才确认成功。不要复制旧脚本的续接参数，也不要把任意超时都当作正常。

当前工具完全成功的退出码为 `0`，明确的普通 USB 返回未确认为 `2`，以 `STOPPED` 报告的错误为 `1`。命令参数写错也可能返回 `2`，因此不能只看退出码，必须结合 `RESULT` 或错误文字判断。详细处理见 [故障说明](docs/ADVANCED.md#本次遇到的错误怎么处理) 和 [阶段说明](docs/STATE-MACHINE.md)。

恢复原版、完整命令与技术说明放在 [进阶文档](docs/ADVANCED.md)。请勿公开机身备份、原始程序、私人日志或密码。
