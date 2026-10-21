# 原厂 2.01：首次内部材料采集

第五十七轮提供独立公开入口 `lutphoto.capturecamera`，复用[既有内部装配、检查点与回执](CAPTURE-EVIDENCE.md)。**代码与离线验收已具备，实际SDK/本项目首次真机采集尚未验证。** 本轮只用自制SDK/系统和材料，没有操作相机、移动盘或机内模块。

当前本人机身保留原厂Ver.2.00，日常卡副本不是内部AP/CP/BK4或降级证据。继续离线开发不要求现在升级或连接；下面设备命令只用于之后明确选择并满足条件的采集，不能用2.01参数冒充仍为2.00的机身。旧 `prepare`/`diagnose` 不作为取材料入口。

## 范围与必须确认的信息

- 仅本人 Sony **ILCE-7CM2、原厂2.01**；明确提供菜单版本、机型和刚读取的实际电量（至少50%）。参数只是本人声明；普通MSC会重新查询型号/协议身份，完整AP/CP必须分别匹配固定长度与完整SHA，才能读取设置。FL2/FL3、Custom或修改升级包不属于本入口源状态。
- 本机macOS、Python3.12+、固定PyUSB/libusb-package依赖、管理员上下文和明确数据线/MSC连接。权限由本人在系统或终端认证，不通过聊天收集密码，不改SIP或自动提权。实际环境/协议/重枚举表现仍需首采独立记录。
- 仓库外**已存在的私有父目录**，以及尚不存在的作业目录和独立回执文件。运行上下文须拥有输出路径及其受信祖先；回执父目录0700、文件排他创建0600，不能与作业同名、大小写/规范化别名或位于作业内部。sudo下使用管理员所有的明确路径，不自动chown/chmod用户目录来放行。
- 服务认证、选择读取路径会改变临时会话状态；此操作不是完全无设备操作。本入口不上传/删除文件、不加载机内模块、不写程序/保存设置、不WBI，也没有恢复或续跑功能。

默认保存6个核心材料：完整AP/CP、初始RAM/保存设置、结束RAM/保存设置。显式 `--resources` 才增加固定68个UXC（合计74个材料）。程序与所选资源完整复读、四快照作用域比较和首末守卫均须满足；单服务对象完成认证/读取/健康退出，返回普通设备后新开第三句柄重查同源身份。角色/外层、原子性、新鲜度、独立介质、原生执行或恢复不自动视为已证。

## 命令与输出

先完成[电脑端只读预检](CAPTURE-CONTROL-PREFLIGHT.md#只读预检命令)及设备范围确认。预检不会连接相机，不能替代版本/电量/权限或完整程序核验。固定归档必须已在本地且完整匹配审计；入口不自动下载固件或升级相机。

下面父目录仅为通用示例，须预先在管理员上下文准备为私有目录；不要为复制示例就自动创建目录或操作设备。将 `ACTUAL_PERCENT` 换为本人刚读出的整数电量，保留新作业和新回执名称：

```sh
sudo .venv/bin/python -u -B -m lutphoto.capturecamera capture \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --directory "/private/var/root/A7C2-capture/session-001" \
  --receipt "/private/var/root/A7C2-capture/session-001-terminal.private.json" \
  --model ILCE-7CM2 --firmware 2.01 --battery-percent ACTUAL_PERCENT
```

可加 `--resources`，没有后端、版本覆盖、启用开关、任意机内路径或强制重试参数。命令先验证声明/来源/本地环境与新输出，再排他预留回执文件，之后才构造NativeOps。已有作业、回执、链接、共享/所有者异常或无法同步回执，均在进入设备流程前拒绝；原文件保留。

最终回执保存到 `--receipt`，不依赖shell重定向，不在锁外重新写作业目录。设备/作业/租约/信号收尾后才写回执，完整写入、同步、读回/条目核对并单次关闭；持有回执独占锁期间检查器拒绝 `ACTIVE_RECEIPT`。空文件可能只是预留，部分文件不修复/覆盖。

stdout仅输出schema `a7c2-camera-capture-cli-result/1`的简短JSON，不包含路径、身份、作业号、材料指纹或密钥。查看真实退出码与结果，不能只看某条中间日志或完整JSON文件：

| 退出/阶段 | 含义 |
| --- | --- |
| 0 / `CAPTURE_COMPLETE` | 内部采集契约及回执保存/关闭、简短结果输出均完成；不等于已验证后续导入/恢复 |
| 1 / `REFUSED_BEFORE_DEVICE` | 声明、来源、环境/输出前置拒绝，没有进入原生设备流程 |
| 1 / `NEEDS_REVIEW` | 内部流程未完整或未知，失败回执已保存（`receipt_saved:true`），保留全部现场 |
| 1 / `CAPTURE_OR_DELIVERY_UNCONFIRMED` | 原生入口调用或回执传递不明，不能按成功处理；保留空/部分/完整文件，不重新执行 |
| 1 / `OUTPUT_UNCONFIRMED` | stdout写入/刷新失败，尽力在stderr给有限结果；不重跑设备。回执可能已保存，整个CLI仍非成功 |
| 2 / `INVALID_ARGUMENTS` | 参数结构/类型错误；不读取来源或启动设备 |

代码不会因回执/终端失败重新采集。stdout/stderr都不可写时仍返回非成功；解释器/进程突然结束不保证留下结果。回执描述内部结束时点，不能单独证明最终文件传递、终端输出或整个进程正常退出；不能把文件一致性检查的0当作原调用退出码。

## 采集后只读复核与异常现场

在相同所有者上下文（管理员输出用sudo）核对已有记录：

```sh
sudo .venv/bin/python -S -B -m lutphoto.captureevidence inspect \
  --directory "/private/var/root/A7C2-capture/session-001" \
  --receipt "/private/var/root/A7C2-capture/session-001-terminal.private.json"
```

该命令不接触相机、不需要归档，分别检查材料与终态。记录可以重写，哈希链不是签名；`CONSISTENT_CAPTURE_RECORDS`不重验程序策略/BK4/UXC，也不证明角色/恢复或允许写入。私人记录及程序/设置/资源不上传仓库或聊天；独立介质复制/核验另行处理，备份不保证救回无法启动的机身。

SDK管理可能阻塞，Ctrl-C/SIGTERM仅合作式请求取消；未返回时继续保留所有者、作业、回执和锁，不并行启动其他工具、强杀、复位或自动重试。返回后停止新增协议，单次尝试本地释放；不凭PID或dispose补成功。`needs_review`、通信中断或任何未知均保留目录/连接现场，后续结合已确认动作人工判断，不据本页授权拔线、取电池或恢复。完整边界见[信号说明](CAPTURE-SIGNALS-OFFLINE.md)及[首次采集审阅](CAPTURE-READINESS-REVIEW.md)。

`capturecandidate review`继续只是源码审阅，候选模块的旧capture拒绝不变，不能修改review JSON当执行许可。当前C1代码/离线完成，C2本人真材料仍缺；C3单槽目标/逆向事务可先离线推进，写入/worker/恢复及真实色彩继续后置。实采前会单独提示并取得真实信息；目前不要求升级、相机或Docker/惠普电脑。验证命令/发布见[第五十七轮](../research/LUT链路调查记录-第五十七轮.md)，固定来源与署名见[致谢](../ACKNOWLEDGEMENTS.md)。
