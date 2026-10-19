[返回简明安装教程](../README.md)

# 技术说明与完整操作参考

**基于 [QAQLeonard/a7c2-fl23-research](https://github.com/QAQLeonard/a7c2-fl23-research) 的 macOS 实验适配层。** FL2/FL3 补丁定位、色彩数据、机内工作模块和原始安装器来自上游；本项目负责 Mac 的 USB 接管、备份流程、状态处理和使用文档。感谢原作者开放研究成果。

固定上游提交：`dd01c07a2a5df004d709595a43ebafe81bbd8fae`，预览包 `0.1.0`。具体来源和授权见 [ACKNOWLEDGEMENTS.md](../ACKNOWLEDGEMENTS.md)、[NOTICE.md](../NOTICE.md)。

> 这是会修改相机程序和设置的实验工具，有无法正常开机的风险，备份不保证能救砖。仅支持 **Sony ILCE-7CM2（A7C II）、原版 2.01**，还必须通过完整 AP/CP 指纹检查。不要用于 A7CR、其他固件或已改过的机身。

## 验证范围

此前的机身专用 Mac 脚本在 **MacBook Air M4 + 一台 A7C II 2.01** 上完成了备份、安装、完整断电、程序/参数/六处运行区域验证，使用者确认 ST、FL2、FL3 拍摄和回放正常。

**本仓库的 `verify` 流程已于 2026-10-18 在上述机身实测通过**：使用提交 `b2fc5ed`，完整程序、保存参数、6处运行区域及返回 MSC 全部核验通过。本次复用前身脚本的机身工作目录，没有重新安装。

通用版的 `prepare`（含默认单份备份）、`install`、`restore` 尚未实机测试，也未验证第二台机身。详见 [验证记录与限制](VALIDATION.md) 和 [脱敏实测摘要](hardware-validation.json)。

## Mac 改进

- 从 IORegistry 确认相机的存储子设备，再调用普通 `diskutil unmountDisk`；不硬编码磁盘编号、不强制卸载、不格式化、不关闭 SIP。
- 等待磁盘识别稳定，避免服务模式返回时 USB 已出现、存储卷仍未列举完成。
- 用 libusb 临时释放目标接口的宿主驱动；验证机身身份并绑定物理 USB 端口。
- 两次服务认证，明确管理接口/句柄生命周期；USB 超时或中断后停止发送后续命令。
- 默认逐文件保存一份备份并校验，包含当前/已保存设置；生成候选后核对反向补丁能精确还原原文件。
- 区分未知结果与“主体完成、服务退出已确认、普通 USB 返回超时”；后者独立标记，仍不自动重试写入。
- 工作目录必须位于仓库之外；私有权限、并发锁、防止误覆盖及固定上游源码/资产哈希检查。

## 准备环境

需要 macOS、Python **3.10+**、可传数据的 USB 线、充足电量。只测试过前述 Apple Silicon 环境；其他 Mac 不视为已验证。

```sh
git clone https://github.com/taoking/a7c2-lut-photo-research.git
cd a7c2-lut-photo-research
./setup.sh
./a7c2-mac check
```

`setup.sh` 不用 sudo，不连接相机。它创建 `.venv`，安装固定依赖，再下载固定提交的上游 ZIP，核验 ZIP 和每个文件。下载内容放在被 Git 忽略的 `.upstream/`，本仓库不附带 Sony 完整固件或个人机身数据。

若系统 `python3` 低于 3.10，先准备符合版本要求的 Python，并使 `python3` 指向它。不要用系统 Python 3.9 硬跑。不要以 root 克隆仓库或安装依赖。

## 操作顺序

相机开机后用数据线直连 Mac。在「选择连接模式」界面，选择 **第 2 项：影像传输（MSC）**。

| 屏幕选项 | 本工具是否使用 |
| --- | --- |
| 1. 实时流式传输（USB流式传输） | 否 |
| **2. 影像传输（MSC）** | **选这一项** |
| 3. 影像传输（MTP） | 否 |
| 4. 遥控拍摄（电脑遥控） | 否 |

MSC 即文档中的 Mass Storage／大量存储。服务模式退出后再次出现这个界面，也选择第2项。先关闭正在浏览相机存储卡的窗口或应用。Mac 接电，写入期间保持 USB 和相机供电。

### 1. 查看 USB，尚不接管接口

```sh
./a7c2-mac usb-status
```

只读取 macOS 的 USB/磁盘信息，不进入服务模式、不发相机协议命令。Windows 文档中的 Zadig/libusbK 不用于 Mac。

### 2. 一份备份与机内预检查

工作目录必须**尚不存在**，父目录必须存在。默认只保存一份备份，位于工作目录的 `original/` 中；每台机身使用自己的工作目录。备份写入后仍会读回、核对哈希，不因只有一份而跳过检查。

```sh
sudo ./a7c2-mac prepare \
  --workspace "$HOME/Pictures/A7C2-work"
```

此步骤会进入服务模式、读取程序与设置、生成候选，并上传/运行/清理上游临时诊断模块。**不会写入固件程序或保存拍摄设置**，但不是完全无设备操作的“离线检查”。只有全部备份与预检查通过，才进入 `prepared`。

### 3. 明确安装

把下方 `ACTUAL_PERCENT` 替换为**相机屏幕显示的实际电量整数**，范围 50–100。50% 是上游操作门槛，不是安全保证。不要复制虚构电量。

```sh
sudo ./a7c2-mac install \
  --workspace "$HOME/Pictures/A7C2-work" \
  --battery-percent ACTUAL_PERCENT
```

这一步会实际修改程序、保存目标设置并处理旧开机快照。保持连接，不关机、不重复执行。若退出服务模式时屏幕询问连接方式，选择第2项「影像传输（MSC）」；工具最多等待 60 秒。

### 4. 完整断电与验证

在 `installed_pending_cold_start` 后：拔 USB，正常关机，等存取灯熄灭，取出电池约 10 秒，再装回开机。**写入未知、`needs_review` 或仍有读写时不可照此操作。** 若为 `installed_pending_cold_start_usb_unconfirmed`，先阅读下方故障表，确认屏幕无错误、存取灯熄灭；该状态表示主体已验证，但正常 USB 返回未确认。

查看 FL2/FL3 菜单；分别使用相机内建重设，再用 ST、FL2、FL3 各拍新照片并回放。重新连 Mac、选择第2项「影像传输（MSC）」：

```sh
sudo ./a7c2-mac verify \
  --workspace "$HOME/Pictures/A7C2-work" \
  --cold-start-confirmed
```

`--cold-start-confirmed` 表示你已实际完成上述断电步骤，不会替你操作相机。验证会读取完整程序、参数及六处运行区域，上传临时诊断模块，不重新安装。成功为 `verified_after_cold_start`。实际颜色、其他拍摄模式及长期稳定性仍需人工验证。

### 查看状态

```sh
./a7c2-mac status --workspace "$HOME/Pictures/A7C2-work"
```

## 本次遇到的错误怎么处理

| 现象 | 判断与处理 |
| --- | --- |
| `Access denied`，sudo 也无效 | macOS 存储驱动可能占用接口。本项目只在确认相机磁盘已卸载后临时接管接口；不建议关闭 SIP 或卸载系统驱动。 |
| `Camera volumes did not all unmount` | USB 捕获前停止。不要绕过检查或强制卸载。保存日志，检查是否仍有应用访问相机或磁盘识别未稳定。 |
| `prepared_usb_unconfirmed` | 备份和机内预检查已完成，但普通 USB 返回超时。未写入固件；先使相机回到影像传输（MSC），再明确调用 `install`。 |
| `installed_pending_cold_start_usb_unconfirmed` | 只在安装主体、读回、参数保存、WBI 和服务退出均已完成时出现。不要重跑安装；确认相机无错误且不在读写，再正常关机冷启动并验证。 |
| `verified_after_cold_start_usb_unconfirmed` | 程序/参数/运行区域核对通过，但最终普通 USB 连接未确认。检查相机的连接选择和菜单状态；不重新安装。 |
| `needs_review`、超时、断线、未知结果 | 保留工作目录与相机现状；不能仅凭最后一句报错决定重跑或取电池。本项目不提供通用“强制续写”。 |

普通 USB 返回超时专门使用退出码 `2`，不伪装成完整成功；其他错误为 `1`，完全成功为 `0`。详见 [状态与失败处理](STATE-MACHINE.md)。

## 安装停在 writing_settings 的专项诊断

针对 `needs_review / failed_action=install / failed_during=writing_settings`，见 [实验性专项诊断](INTERRUPTED-INSTALL.md)。新增 `diagnose` 尚未真机验证，会进入服务模式并运行临时模块，不自动续写或恢复；请先阅读风险与适用条件。

## 恢复原版

仅支持已知完整候选和本机身有效备份，不支持任意损坏映像救砖。先在相机选择 **ST**，正常关机、等灯灭、取电池约10秒再开机，接回影像传输（MSC）：

```sh
sudo ./a7c2-mac restore \
  --workspace "$HOME/Pictures/A7C2-work" \
  --battery-percent ACTUAL_PERCENT \
  --st-selected --cold-start-confirmed
```

恢复使用上游的完整候选检查、原始程序和四项目标设置，不覆盖整份机身设置。完成后仍需冷启动和实际检查。`verify` 目前核验 FL2/FL3 安装结果，**不用于恢复原版后的核验**。本仓库恢复路径仅做离线流程测试，未实际执行恢复。

## 隐私、测试与贡献

不要公开机身备份、原始程序、参数、序列号或整个工作目录。截图裁掉用户名、个人路径和身份信息。提交问题时先提供错误阶段、脱敏文本与 Mac/固件版本；不要直接上传日志目录。

```sh
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v
```

测试使用模拟 USB 和合成数据，不连接相机。CI 不执行真实安装。上游引用和原生模块保持固定版本；升级须重新核验，不会自动跟随 `main`。

## 致谢

再次感谢 **[QAQLeonard](https://github.com/QAQLeonard/a7c2-fl23-research)** 的 A7C II 移植与工具、**[ma1co / Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE)** 的协议实现，以及上游注明的 A7CR 和 A7C II 服务模式研究者。详细分工、固定提交及许可见 [ACKNOWLEDGEMENTS.md](../ACKNOWLEDGEMENTS.md)。
