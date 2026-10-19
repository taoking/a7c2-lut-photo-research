# LUT 照片离线参考工具

这是 LUT 拍照开发的首轮可运行产物：建立色彩参考，并调查原版程序中的入口。机内实时预览、JPEG LUT 直出、持久化及安装尚未实现。当前工具完全在电脑处理，不连接 USB，也不调用现有安装器。

当前主线与验收见[总计划](../plan.md)和[v2.1 审计](../docs/UPSTREAM-V2.1-AUDIT.md)，继续任务先读[当前交接](HANDOFF.md)。[第二十九轮](LUT链路调查记录-第二十九轮.md)已将原生 Creative Look 拟合列为优先路线，[第三十轮](LUT链路调查记录-第三十轮.md)已实现 N2 离线基础，使用方法见[原生拟合与误差报告](../docs/NATIVE-FIT-OFFLINE.md)；[第三十一轮](LUT链路调查记录-第三十一轮.md)已补齐配对标定与冻结场景/分区验收，见[说明](../docs/NATIVE-VALIDATION.md)；真实相机证据留给 N4。以下已有机外工具和 3D LUT 研究入口继续保留。研究支线最后证据见[第二十八轮](LUT链路调查记录-第二十八轮.md)，最初范围见[专项评估](../docs/LUT拍照开发可行性与专利核查.md)。

N3 的独立 Mac 编译探针、合成状态迁移及故障模拟见[第三十二轮](LUT链路调查记录-第三十二轮.md)和[工具说明](../docs/CUSTOM-MAC-OFFLINE.md)。第三十三轮增加[资源/设置离线契约](../docs/CUSTOM-CONTRACTS.md)，使用真实格式的自制夹具验证 68 文件、槽位映射、精确逆向与设置保护。第三十四轮补齐[磁盘日志/独占与中断分类原型](../docs/CUSTOM-JOURNAL.md)，仅使用合成材料；第三十五轮增加[固定来源/worker ABI 核验](../docs/WORKER-CONTRACTS.md)，两份真实 C 源码以合成头编译通过，未加载执行或保留产物；第三十六轮补充[BK4 受限只读解析/设置比较及主机加载链边界](../docs/BK4-OFFLINE.md)，仍只用自制素材验证；第三十七轮增加[完整程序身份与描述符只读入口](../docs/PROGRAM-IDENTITY.md)，第三十八轮接通[描述符与 RAM/保存设置只读绑定](../docs/SETTINGS-BINDING.md)，真实程序/BK4 正例、新鲜同机身来源、资产事务绑定、设备恢复和全局相机锁/USB 仍缺。

## 文档维护与继续任务

- `plan.md` 只保留里程碑表，里程碑状态或证据/缺口变化时才更新。
- [HANDOFF.md](HANDOFF.md) 只保留当前轮次、关键边界、上轮结果和下一步入口；每轮覆盖更新，不累积历史。
- 当轮调查记录单独保存范围、检查项、证据、实际验证命令/结果和遗留问题。结束后保留历史，不再复制进总计划。
- [ROUNDS.md](ROUNDS.md) 汇总轮次索引，[BASELINE.md](BASELINE.md) 保存固定材料/环境；旧计划保存在[归档](../plan-history-through-14.md)。历史验证锚点已转到归档。

继续任务先读根目录规则、README、短总计划、交接和相关当轮记录；其他历史按具体问题读取，不再全量加载旧计划。

## 环境

研究工具需要 **Python 3.12 或更新版本**。这是可选研究工具的要求，原 FL2/FL3 安装器仍按原来的 Python 要求使用。

从仓库根目录执行，已有兼容的 `.venv` 时可直接使用：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lut.txt
.venv/bin/python -B -m lutphoto --help
```

`requirements-lut.txt` 固定 NumPy 2.5.4 与 Pillow 13.0.0。运行相机安装器另按原 README 安装其依赖；本工具不要求运行 setup、sudo 或任何相机命令。

## 先验证自制素材

在一个尚不存在的新目录生成恒等 LUT、红蓝交换 LUT 和色块/渐变图：

```sh
.venv/bin/python -B -m lutphoto fixtures --directory research/output/demo --size 17
.venv/bin/python -B -m lutphoto inspect research/output/demo/identity-17.cube
.venv/bin/python -B -m lutphoto apply \
  --lut research/output/demo/identity-17.cube \
  --input research/output/demo/chart.png \
  --output research/output/demo/identity.png \
  --lut-space srgb
.venv/bin/python -B -m lutphoto apply \
  --lut research/output/demo/swap-rb-17.cube \
  --input research/output/demo/chart.png \
  --output research/output/demo/swap-rb.png \
  --lut-space srgb
```

恒等输出 PNG 应与测试图的 RGB 像素完全一致，红蓝交换输出则交换相应通道。素材来自显式数学映射，没有使用第三方收费 LUT。可以把 `--size` 改为 33；已存在的目录和输出文件都不会被覆盖。

## 处理自己的照片

只在你确认 **LUT 输入及输出均为编码 sRGB** 时使用 `--lut-space srgb`。CUBE 本身通常不能表达完整的色彩空间契约，文件格式检查通过不代表 LUT 适合该照片。

```sh
.venv/bin/python -B -m lutphoto inspect /path/to/look.cube
.venv/bin/python -B -m lutphoto apply \
  --lut /path/to/look.cube \
  --input /path/to/photo.jpg \
  --output /path/to/photo-graded.png \
  --lut-space srgb
```

首版的输入为 RGB 8 位 JPEG/PNG，最大 6400 万像素、128 MiB。有效嵌入 ICC 会先通过 LittleCMS 转换到 sRGB；无 ICC 时接受明确的 sRGB 声明。未标色彩空间的照片会停止，确认它确为 sRGB 后才可加 `--assume-srgb`。该参数不能覆盖明确的其他色彩空间声明，也不能忽略损坏的 ICC。

不支持 S-Log3、HLG、PQ、线性 RGB、RAW、HEIF、16 位 PNG、透明图或多帧文件；不会自动猜测或转换 LUT 所要求的输入空间。S-Log3 转 Rec.709 的 LUT 不能通过把参数填成 `srgb` 来获得正确结果。

输出 `.png` 为无损参考，`.jpg`/`.jpeg` 使用质量 95、无色度降采样重新编码，会产生 JPEG 误差。输出带 sRGB ICC，按 EXIF 方向转正，但不复制 EXIF、GPS、MakerNote 或旧缩略图。原照片不变，目标存在或为符号链接时拒绝写入；中途失败不留下半个目标文件。

成功时输出 JSON，包含所用 LUT 的 SHA-256、插值方式、尺寸和发生输出裁剪的通道值数量；`camera_processing_verified: false` 明确表示没有验证机内处理。文件名中的“效果”或“身份”不用于判定色彩空间。

## 参考实现的格式与数值边界

- 支持单一 IRIDAS 3D CUBE，`TITLE`、`LUT_3D_SIZE`、`DOMAIN_MIN/MAX`、注释和 UTF-8 BOM；不支持 1D、组合 shaper、`LUT_3D_INPUT_RANGE` 或其他扩展。
- 每行 RGB 三值，红坐标变化最快，随后绿、蓝。采样规则与 [OpenColorIO 的 IRIDAS CUBE 格式说明](https://github.com/AcademySoftwareFoundation/OpenColorIO/blob/main/src/OpenColorIO/fileformats/FileFormatIridasCube.cpp)核对；实现为本项目独立编写。
- 文件最大 8 MiB，单行最大 4096 字符，尺寸 2–65，每个数字必须有限且绝对值不超过 1,000,000；精确要求 N³ 行。重复、缺失或数据之后出现头部字段均拒绝。
- NumPy float64 三线性插值，将输入夹到 DOMAIN 内；数值内核保留超出 0–1 的输出，导出 8 位照片时才夹到 0–1 并四舍五入，同时报告裁剪数量。
- 内存中的浮点工作区按 131,072 像素分块。没有宣称复现 Sony、Panasonic 或其他软件的内部插值、色调映射和降噪。
- Sony 手册列出的 17/33 点只是尺寸条件。检查器会说明尺寸是否符合该条件，但始终不宣称已验证相机兼容性。

## 固件只读调查

分析材料保存在忽略目录 `research/materials/`，输出在 `research/output/`。完整固件、解包程序和素材不随代码分发；不要把私人机身备份放进公开资料。

`survey` 只接受完整 SHA-256 匹配已锁定原版 2.01 的 AP/CP 程序。它报告预选字符串的文件偏移，限制单项命中数量，不输出周围原始程序字节。字符串命中不是照片处理链路证明。

```sh
.venv/bin/python -B -m lutphoto survey \
  --kind ap --input /path/to/appFw.so \
  --output research/output/ap-survey.json
.venv/bin/python -B -m lutphoto survey \
  --kind cp --input /path/to/cpapp-b.bin \
  --output research/output/cp-survey.json
```

进一步追踪 AP 的 `SetLutData` 导入，额外安装只读分析依赖：

```sh
.venv/bin/python -m pip install -r requirements-firmware.txt
.venv/bin/python -B -m research.trace_ap \
  --ap /path/to/appFw.so \
  --output research/output/ap-direct-calls.json
```

脚本检查真实 PLT 指令与重定位目标一致后，枚举 `.text` 中指向该桩的直接 `BL`。它不包含间接调用、尾调用或完整跨进程调用图，也不产生可写补丁。Capstone 用于本轮人工反汇编复核，脚本的 PLT/分支验证使用指令编码，ELF 解析使用 pyelftools。

第二轮增加 AP CUBE 解析器和 CP 控制链的只读定位：

```sh
.venv/bin/python -B -m research.trace_cube_ap \
  --ap /path/to/appFw.so \
  --output research/output/ap-cube-parser.json
.venv/bin/python -B -m research.trace_cp \
  --cp /path/to/cpapp-b.bin \
  --output research/output/cp-control-flow.json
```

两者只接受完整指纹匹配的原版程序。输出选定指令和函数范围的验证结果、地址引用及推导限制，不输出原始代码，不生成载荷或补丁。`trace_cp` 区分已确认函数边界中的 ADR 引用与全文件扫描的 BL 候选；后者可能命中数据或指令后半字，不是完整调用图。`trace_cube_ap` 记录中间转换分支，不能将它们当作最终硬件数据格式。所有 JSON 都保留 `photo_pipeline_located: false`。

第三轮同时核对 AP 转换/传输区间与 CP 的用户 LUT 消费长度：

```sh
.venv/bin/python -B -m research.trace_lut_handoff \
  --ap /path/to/appFw.so \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-handoff.json
```

该工具报告普通分支的 48,000 字节索引排布、扩展区间的 48,000 字节表及 124 字节寄存器数据，保留 4 字节未解释尾部。索引模型只计算源行与补零，不生成机内表。AP/CP 的完整 IPC 分发、照片管线及色彩条件尚未确认，`ap_to_cp_runtime_verified` 仍为 `false`。相机实测全部后置，具体项目与进入条件见[第三轮后续清单](LUT链路调查记录-第三轮.md#5-后续离线工作与真机后置清单)，目前无需连接相机。

第四轮进一步核对间接分发和快照字段复制：

```sh
.venv/bin/python -B -m research.trace_lut_dispatch \
  --ap /path/to/appFw.so \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-dispatch.json
```

该工具分别报告前端 `0x0166` 和内部 `0x4155` 分发表、各自的状态，以及 96 字节复制到 VFX 参数的字段映射。两套分发域之间的转换、快照来源及完整 JPEG 路径仍未确认，报告明确列出未连接的部分；不把布局一致当作运行验证。详见[第四轮记录](LUT链路调查记录-第四轮.md)。

第五轮确认内部状态的初始快照来源，并定位另一条 VEF 请求的接收类：

```sh
.venv/bin/python -B -m research.trace_lut_snapshot \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-snapshot.json
```

该工具核对初始复制、上下文绑定、两次复制后的字段位置及匹配的 VEF 接收类，仍不声明完整队列路由、运行刷新和 JPEG 已验证。状态读取/导出标识经指令操作数计算为 `0x00030160`，已更正旧文档中的手工换算错误。两条控制路径汇合于下层接口，不预设前端编号必须换算为内部编号。详见[第五轮记录](LUT链路调查记录-第五轮.md)。

第六轮核对构造之外的快照复制、回调描述符提交和 LUT 未就绪分支：

```sh
.venv/bin/python -B -m research.trace_lut_refresh \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-refresh.json
```

该工具确认同一内部状态到参数根的另一处复制及 `VD_Pre` 回调的潜在控制流路径，并验证另一个排队回调调用 LUT 分发器。路径搜索不求解条件，不能据此确定每帧刷新、照片模式或完整 JPEG 处理；未就绪时还可清零四个开关字后继续。详见[第六轮记录](LUT链路调查记录-第六轮.md)，目前仍无需连接相机。

第七轮继续核对描述符消费者、任务对象及独立的主图 JPEG 调用段：

```sh
.venv/bin/python -B -m research.trace_lut_schedule \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-schedule.json
```

该工具连接回调链表、包装函数与 LUT 分发器，并区分 `VD_Pre`、`VD_CO` 的两个队列；不能据代码位置推断运行先后。另确认 `SCN/THM/MAIN` 共用编码准备函数并调用 JPEG API，但 LUT/VFX 输出与 `MAIN` 输入缓冲、完整尺寸仍未对应。详见[第七轮记录](LUT链路调查记录-第七轮.md)，相机实测继续后置。

第八轮核对主图参数来源、初始字段映射及共享 LUT 就绪字段：

```sh
.venv/bin/python -B -m research.trace_pixel_parameters \
  --cp /path/to/cpapp-b.bin \
  --output research/output/pixel-parameters.json
```

该工具记录两个缓冲查询结果到 JPEG 输入/输出地址的初始映射、六个 u16 的扩展与重复，以及未知字和后续覆盖字段；稀疏模型不输出完整设备参数。另核对 LUT 上传置位、回调清除和 VFX 启动检查共用的就绪字段。VFX 候选输出与主图输入、尺寸和像素格式仍未连接。详见[第八轮记录](LUT链路调查记录-第八轮.md)，目前无需连接相机。

第九轮核对主图角色槽的生产/转移，以及另一条捕获 VFX 请求中的候选地址字段：

```sh
.venv/bin/python -B -m research.trace_capture_buffers \
  --cp /path/to/cpapp-b.bin \
  --output research/output/capture-buffers.json
```

该工具记录 `+0x5afc` 的角色槽、赋值生产者、源槽失效，以及 `Stage_Dev_Vfx` 对同一偏移的查询和条件式参数构造。构造位置换算后与上一轮 VFX 候选双字的字段偏移相同；中间调用、实例身份、用户 LUT 的接入和下层输出角色仍未证实。有界 TBB 表独立解析，表/填充不当作指令，选择值不命名为相机模式。详见[第九轮记录](LUT链路调查记录-第九轮.md)。所有工具仍只读原版材料，报告和已有目标均不覆盖。

第十轮核对前置调用的显式配置指针路径和捕获模块初始选择：

```sh
.venv/bin/python -B -m research.trace_capture_effects \
  --cp /path/to/cpapp-b.bin \
  --output research/output/capture-effects.json
```

该工具在已核对调用标志 `0x2b` 下，排除三个受 `0x40` 位控制的显式配置指针位置；同时记录其他标志下的潜在准备写入，并连接捕获模块的选择、存槽和初始通道值。路径函数新增可选的调用者分支决策和分离代码块支持；默认仍保留两条条件边，遇到空隙不会虚构顺序执行边。决策不是自动条件求解，不能据此宣称全部调用/别名/异步副作用已排除或运行时参数已验证。详见[第十轮记录](LUT链路调查记录-第十轮.md)。

第十一轮核对 VFX 候选双字到下层传输描述项，以及传输/用户 LUT 共用的逻辑路由：

```sh
.venv/bin/python -B -m research.trace_vfx_consumers \
  --cp /path/to/cpapp-b.bin \
  --output research/output/vfx-consumers.json
```

该工具记录两种描述结构的字段换算、7 项循环中第 3 项的双字读取、带进位的地址加法和后续编码，另核对共用句柄解析器的通道掩码/逻辑路由映射。四张内联 TBB 表及填充均从代码窗口排除。数值模型只处理合成地址字，不生成设备参数。共用解析器不证明同一句柄、最终硬件通道或 LUT 使能；详见[第十一轮记录](LUT链路调查记录-第十一轮.md)。

第十二轮核对模式字段到寄存器位、条件式地址清零及捕获模块句柄生产：

```sh
.venv/bin/python -B -m research.trace_vfx_registers \
  --cp /path/to/cpapp-b.bin \
  --output research/output/vfx-registers.json
```

该工具连接传输行的模式字节到控制位 1–2，以及初始选择值 9 在相关打开分支和占用检查成功时到路由 4 的句柄发布。格式值 3/4 会将初始地址寄存器清零，后续有效地址/传输仍待追踪；LUT 提交来自另一个上下文字段，实际句柄身份尚未连接。三张 TBB 表、两张 u32 表分别复核。数值模型只投影选定指令，不生成设备参数。详见[第十二轮记录](LUT链路调查记录-第十二轮.md)；目前无需连接相机。

第十三轮追踪 LUT 上下文输出指针、任务记录/服务令牌和捕获释放边界：

```sh
.venv/bin/python -B -m research.trace_lut_handles \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-handles.json
```

该工具核对上下文 `+0x13b4` 输出指针的三层传递、任务记录 `+0xc` 写回，以及一条服务返回字段的生产路径；请求值和实际任务编号分开。另核对模式 1 打开、真正的释放虚表项 `+0x10`、引用计数和注册表类型字清除；失败不能被当作整体事务回滚。72 项 TBH 表和七项 TBB 表与代码分离，并检查全部表目标。另一地址更新入口的端口不同，不能补齐捕获像素链。详见[第十三轮记录](LUT链路调查记录-第十三轮.md)；实际句柄身份、照片使能和 MAIN 关系仍未证实。

第十四轮连接请求/类别选择到直接原生 VFX 句柄生产：

```sh
.venv/bin/python -B -m research.trace_lut_selection \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-selection.json
```

该工具核对请求 `0x10` 在类别 1–7 选中的实际任务，以及共同的直接 VFX 打开分支，连接上下文输出到原生发布器。它区分第十三轮通用服务分支，并记录该路径与捕获模块打开的发布标志差异。共用句柄域仍不证明运行时同一句柄或照片使能；类别的拍摄语义、有效像素和 MAIN 关系仍待查。复用已有有界表解析，实际 CLI 检查全部十类；详见[第十四轮记录](LUT链路调查记录-第十四轮.md)。

第十五轮追踪类别配置复制和 User3D 公共提交：

```sh
.venv/bin/python -B -m research.trace_lut_context \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-context.json
```

该工具将类别字段连到条件式配置块复制，并定位 User3D 六字配置到 ID `0x2ae085a` 的 56 字节公共提交描述。运行类别、硬件消费、句柄位 31 语义和 MAIN 像素关系仍未确认；详见[第十五轮记录](LUT链路调查记录-第十五轮.md)。本轮完成的文档拆分使继续任务只需读取短里程碑表、当前交接和相关轮次，旧计划不再累积新日志。

第十六轮连接 User3D 同 ID 接收与种类 2 配置消费：

```sh
.venv/bin/python -B -m research.trace_lut_receiver \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-receiver.json
```

该工具核对六项分发表、六字配置到三个寄存器写入描述的打包、七个逻辑上下文的目标基址构造，以及异步提交/完成回调。寄存器位语义、运行接收和硬件执行尚未验证，也未补齐照片像素链；详见[第十六轮记录](LUT链路调查记录-第十六轮.md)。

第十七轮连接 User3D 提交后的路由通道控制：

```sh
.venv/bin/python -B -m research.trace_lut_gate \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-gate.json
```

该工具核对七路到四通道范围、软件缓存控制字第 28 位的置位/清零构造及捕获端口所在的静态 MMIO 块，并区分配置 RAM 镜像。位的功能名、缓存一致性、实际使能和配置完成先后仍未确认；详见[第十七轮记录](LUT链路调查记录-第十七轮.md)。

第十八轮追控制缓存的多种写入方式和原生准备分支：

```sh
.venv/bin/python -B -m research.trace_lut_control \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-control.json
```

该工具区分释放时软件缓存清零、条件式固定初值和整字重建，连接缓存字段回填及原生准备的三条潜在清零路径。固定初值本身也置第 28 位，不能由缓存位推断 User3D 运行或硬件使能；详见[第十八轮记录](LUT链路调查记录-第十八轮.md)。

第十九轮连接准备后参数、句柄比较与完成回调：

```sh
.venv/bin/python -B -m research.trace_lut_completion \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-completion.json
```

该工具核对六组描述的初始模板和寄存器偏移、完整句柄比较及回调可见状态存储。回调清忙不能替代照片整帧完成，配置块相同偏移也不能连接捕获像素；详见[第十九轮记录](LUT链路调查记录-第十九轮.md)。

第二十轮核对原生前置条件和后续标量配置：

```sh
.venv/bin/python -B -m research.trace_lut_update \
  --cp /path/to/cpapp-b.bin \
  --output research/output/lut-update.json
```

该工具连接原始状态/参数比较、两项缓存去重及标量算术到选定配置字段。忙字节非零也可进入更新，不能称为完成回调后的串行处理；标量配置也不能补齐有效像素地址。详见[第二十轮记录](LUT链路调查记录-第二十轮.md)，下一轮转回 M3 的格式 3/4 像素传输与 MAIN 关系。

第二十一轮回到格式 3/4 的传输字段和 MAIN 查询边界：

```sh
.venv/bin/python -B -m research.trace_transfer_fields \
  --cp /path/to/cpapp-b.bin \
  --output research/output/transfer-fields.json
```

该工具核对八个后续字段、四项掩码表，以及捕获/MAIN 共用槽位查询的回复复制边界；其中 `0x2a` 是操作值、`0x55` 是回显标识，历史 JSON 的 command 字段名按此更正理解。算术/零值字段不能自动补齐有效像素地址，同偏移槽位也不证明两次回复或缓冲身份相同；详见[第二十一轮记录](LUT链路调查记录-第二十一轮.md)，其中按 P1–P4 列出关键断点和后置观测假设。

第二十二轮连接查询注册、操作分发和单元记录地址生产：

```sh
.venv/bin/python -B -m research.trace_buffer_query \
  --cp /path/to/cpapp-b.bin \
  --output research/output/buffer-query.json
```

该工具核对注册域 `0x61003c`、操作 `0x2a` 的有界表项，以及单元描述中的基址加偏移到回复地址对的连接。它更正 `0x55` 为请求字段的回显标识，并记录回复复制长度上界；描述的分配/释放/复用、运行送达和照片像素仍未验证。详见[第二十二轮记录](LUT链路调查记录-第二十二轮.md)。

第二十三轮核对单元槽位复用与选定描述的构造/归还：

```sh
.venv/bin/python -B -m research.trace_buffer_lifetime \
  --cp /path/to/cpapp-b.bin \
  --output research/output/buffer-lifetime.json
```

该工具核对槽位队列、代号 1–31 的循环、一条父子描述构造及条件式释放边。相同槽位或地址不能证明同一帧身份，描述归还非零后仍有通向槽位归还/清状态的潜在路径，不能据此宣称完整回滚。完整生命周期与照片像素仍未验证；详见[第二十三轮记录](LUT链路调查记录-第二十三轮.md)。

第二十四轮连接角色 9 的分配回复与捕获/MAIN 阶段工作字段：

```sh
.venv/bin/python -B -m research.trace_capture_work \
  --cp /path/to/cpapp-b.bin \
  --output research/output/capture-work.json
```

该工具区分分配操作 `0x20` 与查询操作 `0x2a`，核对两条分配后端、回复 `+0xc` 到角色 9 工作槽、两个阶段分发表及构造器的工作指针存储。后续构造可显式传入工作指针，不能默认捕获与 MAIN 属于同次拍摄；实际实例、槽位转移与照片像素链仍未验证。详见[第二十四轮记录](LUT链路调查记录-第二十四轮.md)。

第二十五轮核对捕获到 MAIN 的条件式阶段切换与工作配置选表：

```sh
.venv/bin/python -B -m research.trace_capture_stages \
  --cp /path/to/cpapp-b.bin \
  --output research/output/capture-stages.json
```

该工具连接组 11–15 的后续回调、原阶段参数传递、工作配置到处理描述的工厂表，以及返回值到步骤推进的关系。MAIN 所查分发表中步骤 0 为前一步入口、步骤 1 才进入主图构造；队列复制和原指针传递不证明运行完成、角色 9 保持不变或 LUT 已进入照片。详见[第二十五轮记录](LUT链路调查记录-第二十五轮.md)。

第二十六轮核对工作配置来源与 MAIN 前置缓冲：

```sh
.venv/bin/python -B -m research.trace_capture_config \
  --cp /path/to/cpapp-b.bin \
  --output research/output/capture-config.json
```

所查 23 行静态配置中，捕获索引 2 所在行的 MAIN 原值为 0，不能把此前两个不同条件的入口拼成同次拍摄链；动态行与其他捕获路径仍未证。MAIN 步骤 0 所查直接写槽也与角色 9 输入槽分开。详见[第二十六轮记录](LUT链路调查记录-第二十六轮.md)，公开仓库范围见[发布说明](../docs/PUBLISHING.md)。

第二十七轮核对同一静态配置下的其他捕获入口：

```sh
.venv/bin/python -B -m research.trace_capture_paths \
  --cp /path/to/cpapp-b.bin \
  --output research/output/capture-paths.json
```

所查静态行 1–5、12 包含捕获索引 5 和 MAIN 原值 3/1 的条件候选；捕获包装入口连接到 `0x382834`，仍不证明运行采用该配置或完成同次拍摄。新入口使用 `0x7f/0xff`，不能套用旧 `0x2b` 对辅助分支的排除结论；捕获后还可条件式替换角色 9，MAIN 同槽查询不保证最初缓冲身份。动态行生产、有效像素及照片使能仍未证，详见[第二十七轮记录](LUT链路调查记录-第二十七轮.md)。

第二十八轮核对新捕获辅助调用和替换句柄来源：

```sh
.venv/bin/python -B -m research.trace_capture_exchange \
  --cp /path/to/cpapp-b.bin \
  --output research/output/capture-exchange.json
```

配置指针已接到驱动虚表 `+0x28` 的间接调用边界，完整副作用仍未证。伴随对象可从全局复用，其 `+0x5308` 对应第 8 槽；角色 9 操作值 2 已连到请求 `0x23` 及条件式归还，但调用者清槽不保证底层归还成功。机内照片 LUT、完整缓冲身份及有效传输仍未验证，详见[第二十八轮记录](LUT链路调查记录-第二十八轮.md)。

第二十九轮增加固定上游源码包与旧基线的离线审计：

```sh
.venv/bin/python -B -m research.audit_upstream_looks \
  --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip \
  --output research/output/upstream-v2.1-audit-rerun.json
```

独立研究锁仅固定审计来源，不改旧安装器依赖。能力对照、复用清单、迁移/恢复及色彩验收条件见[v2.1 审计](../docs/UPSTREAM-V2.1-AUDIT.md)；该轮完成时 N2 转换/误差工具尚未接入；目前的独立离线实现与边界见[第三十轮工具说明](../docs/NATIVE-FIT-OFFLINE.md)。

## 测试

完整研究测试还需要 `requirements-firmware.txt` 中的 Capstone/pyelftools；普通照片处理只需要 `requirements-lut.txt`。

```sh
.venv/bin/python -m pip install -r requirements-lut.txt -r requirements-firmware.txt
.venv/bin/python -B -m unittest discover -s research/tests -v
```

测试包含独立的多线性函数数学预期、不同网格与通道顺序、异常 CUBE、输入色彩约束、精度/透明图拒绝、原图和已存在文件保护、EXIF 方向处理、CLI 完整流程，以及 AArch64 正/负分支和 PLT 校验。素材只在临时目录生成，不接触 USB。原安装器测试仍可按原命令单独运行。

3300 万像素合成图验证及各轮工具/测试见[轮次索引](ROUNDS.md)。当前研究测试共 322 项，第三十轮新增 23 项拟合/预测测试，第三十一轮新增 19 项标定/冻结验收测试，第三十二轮新增 23 项工具链/合成事务测试（含 200 组合故障矩阵），第三十三轮新增 23 项资源/设置格式契约测试，第三十四轮新增 22 项日志/跨进程锁/中断测试，第三十五轮新增 19 项来源/报告 ABI/加载范围测试，第三十六轮新增 22 项 BK4/角色断言/设置保留测试，第三十七轮新增 23 项完整程序身份/描述符只读测试，第三十八轮新增 23 项描述符/快照绑定与保护测试；第十三轮增加 TBH 数值/边界测试，第十四轮复用该模型并增加完整原版 CLI 的类别选择和原生发布断言。测试通过不代替机内验证，更不证明机内照片 LUT 可用；后续按交接中的具体入口继续。
