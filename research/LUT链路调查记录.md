# LUT 链路调查：首轮开发记录

日期：2026-10-18。原安装器基线 `5babef40bba986efdd0573380c0ff9f8a027495c`。本轮新增离线参考与分析工具，没有连接 USB，没有运行相机诊断、安装、恢复或修改程序/参数。

## 本轮已经完成

1. 实现独立 `lutphoto` CLI：严格 3D CUBE 解析、float64 三线性插值、sRGB 8 位照片处理、自制诊断素材和只读程序线索扫描。
2. 下载、解包 Sony 官方 2.01 更新包，确认 AP/CP 完整指纹与固定上游原版一致。
3. 找到并验证 AP `SetLutData` 导入的 PLT、GOT 和一处静态直接调用；提供可重跑脚本。
4. 在 CP 中找到分别涉及监看、用户 3D LUT 写入、内部记录输出和 CAP 模式的字符串线索。尚未证明这些路径共同构成静态照片用户 LUT 处理链。

## 分析材料与来源

原始文件来自 [Sony 官方 ILCE-7CM2 2.01 下载页面](https://www.sony.com/electronics/support/software/00301105)，其公开版本为 2.01，标示大小 1,139,929,560 字节。2026-10-18 实际下载大小一致，SHA-256 为：

```text
eb4943e6099754d64deaef5047942e9bfe258f232d0b7bc39fa23b3cd10e1e31
```

官网日本页面给出的完整下载地址包含查询参数；删去参数的地址本轮返回 404，按页面完整地址下载成功。该结果不证明此地址永久可用。无需用户提供私人备份即可复现本轮调查。

解包使用外部 [ma1co/fwtool.py PR #52](https://github.com/ma1co/fwtool.py/pull/52)，固定提交 `3955d7890fc38daf942bb52827599bfe35de4a14`，未修改工具源码；其代码和许可证保留在本地忽略目录，不复制进本项目。实际命令：

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python research/materials/fwtool/fwtool.py unpack \
  -f research/materials/BODYDATA.DAT -o research/materials/official-2.01
```

解包返回版本 2.01、model `0x20030014`、`CXD90057_k8`。工具在本机 Python 3.14.6 提示了已有正则字符串的 SyntaxWarning，但退出码为 0；没有修改其表达式或抑制校验。

| 程序 | 文件大小 | SHA-256 |
| --- | --- | --- |
| `appFw.so` | 99,960,744 B | `2ea02f7ecbc5bb917316fe8ef4ce5ffd87eb66efaae78ba2ce11420552df539b` |
| `cpapp-b.bin` | 18,090,880 B | `f5a477588698ef965748903b8959a39ce4f59ffd4aee4d4234ef1670f56a1428` |

AP 为 AArch64 ELF；CP 仍需按其实际映像布局定位，不能套用 AP 的地址关系。文件只用于本地研究，不随报告分发。

## 已确认的静态入口

以下均针对上述原版，不适用于其他版本或已安装的 FL2/FL3 候选。

| 观察 | 位置/证据 | 可以得出的结论 |
| --- | --- | --- |
| CUBE 解析相关常量 | AP 文件偏移 `0x4bfa1f0`、`0x4bfa204` 为 `LUT_3D_SIZE`、`LUT_3D_INPUT_RANGE` | 存在相应格式线索；尚未定位其全部引用与调用 |
| MPR 接口导入 | 动态符号 `_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE`，即 `mpr::SetLutData` | AP 引用了该接口，不能仅凭名字判断是像素处理还是媒体/元数据 |
| 真实 PLT/GOT | PLT VA `0x165ff70`，GOT VA `0x5bc27c0` | 桩的 ADRP/LDR/ADD/BR 计算与 `.rela.plt` 条目吻合 |
| 直接调用 | AP VA 和文件偏移均为 `0x3561018` | `.text` 中发现一处直接 BL 到上述桩；没有排除间接或其他形式调用 |
| 接口定义 | 同包 `libmpr.so` 导出 `SetLutData`（VA `0xd6044`，164 B）及 `ExecuteSetLutData`（VA `0xd5e60`，484 B） | 可从该库继续追踪异步封装和数据流；未证明此库完成图像 LUT |

`.text` 内本轮 VA 与文件偏移相等，**该等式不是整个 ELF 的通用规则**。工具按节映射分别记录两者。报告中的偏移只用于研究，不能当成写入地址。

CP 中还发现下列字符串：

| 文件偏移 | 标记 | 证据等级 |
| --- | --- | --- |
| `0xab2a0` | `SendVEF_PathSetLut` | 字符串线索 |
| `0x1352c8` | `init_cc_3DLUT` | 字符串线索 |
| `0x135ba4` / `0x135bcc` | `LutMode Change MOV/MON` / `LutMode Change CAP` | 字符串线索；CAP 的实际使用条件待确认 |
| `0x324f1c` | `CamCore 3D-Lut table Write Start` | 字符串线索 |
| `0x446380` / `0x446658` | `ddl_VfxSetMlutUser3D` / `ddl_VfxSetMlutUser3DArtGen` | 字符串线索；不证明完整分辨率 JPEG 会调用 |

已用 Capstone 对 AP PLT 及调用窗口做人工反汇编复核。**尚未完成** AP CUBE 模型到 CP 参数的对应、CP 字符串交叉引用、完整照片图像缓冲和硬件 LUT 配置的追踪，不能把 `CAP` 字样解释成已确认可解锁。

## 参考工具的实际验证

使用自制恒等 LUT 处理 6000 × 5500 的 RGB 合成 PNG，共 3300 万像素。在本机 Python 3.14.6、NumPy 2.5.4、Pillow 13.0.0 上：

- 包含照片读取、ICC 转换、LUT 计算及 PNG 保存，单次测得 5.885 秒；素材生成和之后的像素比较不计时。
- 输出和原图的 RGB 像素完全一致，裁剪通道值为 0。
- 该结果仅证明这次电脑参考流程；没有测量内存峰值，不代表相机处理速度，也不是多次统计基准。

测试与命令：

| 命令 | 本轮结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 27 项专项测试通过 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 39 项原安装器离线测试通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 8 项通过 |
| `.venv/bin/python -B -m macfl23 check` | 固定上游源码和资产校验通过，未连接相机 |
| `.venv/bin/python -m pip check` | 退出码 0，无依赖冲突 |
| `lutphoto fixtures/inspect/apply` | 自制素材的 CLI 流程已实际运行，恒等与红蓝交换像素预期由测试核对 |
| `lutphoto survey`、`research.trace_ap` | 对上述原版实际运行通过；JSON 留在本地忽略目录 |

测试不访问 USB。原安装器源码、上游锁定资产及写入检查没有改动。新增文件、文档与忽略规则的最终检查记录在 [plan.md](../plan.md)。

## 下一步的具体研究门槛

1. 沿 AP CUBE 常量的引用确认读取/转换函数，说明输入范围、采样次序及内部 LUT 数据格式；不能把机外 IRIDAS 子集当成机内格式的完整说明。
2. 追踪 CP 的 `SendVEF_PathSetLut`、`DevLutSetter` 与 `CAP` 模式分支，建立真实调用关系，区分监看、视频、照片和元数据用途。
3. 确认用户 LUT 表地址/长度如何抵达图像处理器，完整分辨率 JPEG 是否能使用，以及输入伽马/色域的前置条件。
4. 只有前三项有充分证据后，设计独立实验候选与恢复路径，才进入专门测试设备上的阶段 C。本轮没有生成或安装任何机内 LUT 补丁。
