# 第三十轮：N2 原生色表离线拟合接入

日期：2026-10-19。范围：电脑端 CUBE→原生修正表、模型/桥接契约、参考预测及误差验证。沿用[第二十九轮审计](LUT链路调查记录-第二十九轮.md)的固定来源，不操作 USB 或相机。

## 本轮检查项

- [x] 仅接入已审计的纯 NumPy 算法，保留来源、许可与完整哈希。
- [x] 输入域、模型来源、桥接及输出保护独立校验。
- [x] 合成拟合、参考预测和可量化误差，保持实机精度未验证。
- [x] 运行离线测试与实际 CLI，核对保护路径及公开文档。
- [x] 更新四列总计划和滚动交接，记录下一步。

## 交付与来源

新增 `lutphoto.nativefit` 独立 CLI 与 `native_metrics` 比较模块；使用方法、项目格式、模型要求及完整限制见[说明](../docs/NATIVE-FIT-OFFLINE.md)。依赖仍只有原研究工具的 NumPy/Pillow，不增加 SciPy、Keystone、设备或网络依赖。

QAQLeonard 上游 v2.1 的 `native.py`、`color.py` 两个纯 NumPy 模块原样置于 `lutphoto/_vendor/sonylooks/`。固定提交 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`，长度分别为 5,631 / 2,021 字节；SHA-256、来源和完整 MIT 许可见[清单](../lutphoto/_vendor/sonylooks/PROVENANCE.json)。专项测试同时核对这两个文件和许可的原始字节。

新增接入层明确以下边界：

- 单 CUBE 离线项目，强制 ST 基底、模型证据、输入/输出域、素材出处和事先阈值；非 ST 需要独立桥接的域及依据。CUBE 沿用已有严格有界解析，最终输出节点必须为 0..1 编码 sRGB。
- 校验响应矩阵条件数及模型假设；域外采样默认拒绝，只有显式选择后才截断并计数。合成单位矩阵仅验证软件，不附带或宣称真实 Sony 标定。
- 生成原生形状的 1,215 字节表和候选报告；保留项目/模型/参考/桥接/表哈希与种子。比较时重新核对来源，不覆盖输入/旧输出；生成文件去掉源照片私人元数据。没有安装/恢复/固件执行接口。
- 同样 ST 输入上计算 CUBE 参考与原生预测，输出 RGB、D65 Lab Delta E76、灰阶、系数范围/触限、收敛及剪裁。照片接受显式区域掩码，缺失/空区域报告不可用；大区域最多 65,536 个固定种子无放回样本，统计口径明确。

## 测试命令与结果

本轮实际运行，均在仓库根目录，退出码 0：

```sh
.venv/bin/python -B -m unittest research.tests.test_nativefit -v
.venv/bin/python -B -m unittest discover -s research/tests -v
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v
.venv/bin/python -B -m macfl23 check
```

专项 23 项通过；完整研究 148 项（包含上述 23 项），Mac 39 项，旧固定上游 8 项，**合计 195 项通过**。最后补充透明掩码拒绝和读取指纹一致性后，以 `unittest discover -s research/tests -q` 复核完整研究套件。旧固定上游完整性检查通过，未连接相机。本轮未重新运行 N1 的外部上游测试，不将之前的平台断言失败或 Keystone 限制写成已解决。

验证包括独立可计算的平面顺序/有符号边界、常量修正、亮度轴线性插值、可表达变换恢复、黑白/红色 Lab 预期，以及来源漂移、输出已有/符号链接、磁盘写失败清理、模型条件数、域/桥接不匹配、缺失 ST、照片/掩码限制、未提供区域和真实 CLI。新模块导入后未出现 `macfl23/usb/pmca`。

实际 CLI 保存于被忽略的 `research/output/native-round30/`，包括 stdout/stderr 与候选报告；以下命令均已运行，前三类成功退出 0：

```sh
.venv/bin/python -B -m lutphoto.nativefit fixtures \
  --directory research/output/native-round30/fixtures
.venv/bin/python -B -m lutphoto.nativefit fit \
  --project research/output/native-round30/fixtures/project.json \
  --directory research/output/native-round30/identity
.venv/bin/python -B -m lutphoto.nativefit evaluate \
  --project research/output/native-round30/fixtures/project.json \
  --candidate research/output/native-round30/identity/candidate.json \
  --input research/output/native-round30/fixtures/gray-reference.png \
  --directory research/output/native-round30/gray-evaluation --st-input \
  --masks research/output/native-round30/fixtures/masks.json
.venv/bin/python -B -m lutphoto.nativefit fit \
  --project research/output/native-round30/fixtures/swap-project.json \
  --directory research/output/native-round30/swap
```

灰阶图是本轮另行自制的 64×64 sRGB 渐变，掩码为完整灰阶、各 1/4 高光/阴影、空饱和区域。swap 项目仅将来源改为自制红蓝交换 CUBE。它们均不是相机样张；重跑请准备新目录，不能覆盖本轮输出。

| 自制案例 | RGB MAE | Delta E76 P95 | 其他结果 |
| --- | --- | --- | --- |
| 恒等 CUBE，4,096 留出样本 | 2.9833e-17 | 6.2350e-14 | 全零表、无系数触限、合成阈值通过 |
| 恒等灰阶照片，4,096 像素 | 2.8262e-17 | 约数值零 | 灰阶 4,096 样本，空饱和/缺失肤色不可用 |
| 红蓝交换，4,096 留出样本 | 0.09009984 | 83.32001 | 415 系数触限、收敛、预设阈值未通过 |

恒等拟合 stdout 与保存的 `candidate.json` 字节相同。输出已存在、缺失 `--st-input`、项目字节变化三种实际 CLI 均退出 1，原有输出保留且未创建失败比较目录。退出 0 只表示计算成功，红蓝交换正是计算完成但阈值失败的例子。

## 公开检查与保护

候选公开文件均为文本；AST、Markdown 本地链接/锚点、个人路径/疑似密钥、NUL、忽略输出未进入候选清单和 `git diff --check` 已核对。`macfl23/`、原 `tests/`、`requirements.txt`、启动器、`setup.sh` 和 `upstream.lock.json` 相对研究起点无变更；运行锁与旧计划归档完整 SHA-256 均保持原值。

未提交或推送。本地第二十七至三十轮改动保留，公开仓库仍截至第二十六轮；不分发素材、虚拟环境、原始相机程序、DCP 或照片。

## 遗留与交接

N2 标记为部分完成：输入契约、CUBE 拟合和参考比较已可运行；配对 ST/参考补丁的有界标定构建、训练/留出身份、多场景冻结清单和分区阈值仍待补。下一轮先完成这些电脑端能力，以合成材料验证，不索取或自动搜索私人照片/备份；真实 ST 响应、多光源/多场景色彩和 JPEG/预览一致性留给 N4。

随后才进入 N3 独立 Mac 事务/迁移/恢复模拟；不会把此表接入旧 FL23 安装器或放宽其哈希。DCP 暂为后续扩展，真正 3D LUT 的 M2–M4 继续保持第二十八轮的未闭合研究状态。相机实测后置，进入前提示，当前无需连接相机。滚动入口见[HANDOFF](HANDOFF.md)。
