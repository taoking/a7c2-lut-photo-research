# 原生色表离线拟合与参考比较

本工具完成 N2 的第一步：将显式声明输入域的 CUBE 拟合为 5×9×9×3、1,215 字节的原生形状修正表，并在电脑比较原 CUBE 参考和模型预测。它没有设备接口；输出表不是固件、安装包或可直接交给旧安装器的文件。真实 Sony ST 标定和多场景相机精度尚未验证。

拟合、表编码和坐标预测直接复用 QAQLeonard 上游 v2.1 的两个纯 NumPy 模块，固定提交 `7e54d60b458847f1befa6cfd614fbf004b8b0b90`；[来源、完整哈希](../lutphoto/_vendor/sonylooks/PROVENANCE.json)及[MIT 许可](../lutphoto/_vendor/sonylooks/LICENSE.txt)随源码保留。没有引入设备模块或固件资产，旧 FL23 运行锁保持不变。

## 用合成素材跑通

使用研究环境，依赖与原机外工具相同，仅需要 `requirements-lut.txt`。以下输出目录必须尚不存在；命令在仓库根目录执行：

```sh
.venv/bin/python -B -m lutphoto.nativefit --help
.venv/bin/python -B -m lutphoto.nativefit fixtures \
  --directory research/output/native-demo
.venv/bin/python -B -m lutphoto.nativefit fit \
  --project research/output/native-demo/project.json \
  --directory research/output/native-identity
.venv/bin/python -B -m lutphoto.nativefit evaluate \
  --project research/output/native-demo/project.json \
  --candidate research/output/native-identity/candidate.json \
  --input research/output/native-demo/chart.png \
  --directory research/output/native-identity-images \
  --st-input
```

`fixtures` 中的响应矩阵为单位矩阵，图表也由程序生成；`--st-input` 在这个例子中只是演示输入契约，**不是图表来自 Sony ST 的证据**。该模型只能测试软件，不能预测你的相机。

`fit` 输出 `correction.table` 和 `candidate.json`。后者包含来源/模型/桥接 SHA-256、固定上游提交、种子、训练/选择/留出样本数、收敛、系数触限、合成误差和事先声明的阈值结果。`evaluate` 输出 `reference.png`、`prediction.png` 和 `comparison.json`；原照片及已存在的输出目录不会覆盖，PNG 带 sRGB ICC，去除原 EXIF 等私人元数据。

## 项目与模型契约

这是本仓库独立的离线格式，不是上游槽位安装项目；目前每个项目处理一个 CUBE，不接受 DCP 或相机程序：

```json
{
  "schema": "a7c2-offline-native-project/1",
  "base": "ST",
  "calibration": "model.json",
  "seed": 201,
  "training_samples": 12000,
  "source": {
    "type": "cube",
    "path": "my-look.cube",
    "input_space": "sony-st-srgb",
    "output_space": "srgb",
    "domain_policy": "reject",
    "attribution": "填写自己的素材来源、授权或自制说明"
  },
  "thresholds": {
    "max_rgb_mae": 0.005,
    "max_delta_e76_p95": 2.0
  }
}
```

相对路径按项目文件所在目录解析；模型接受上游 `a7c2-look-calibration/1` 的响应部分：

```json
{
  "schema": "a7c2-look-calibration/1",
  "coordinate_model": "bt601-limited-provisional",
  "response_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
  "full_camera_characterization": false,
  "evidence": "此单位矩阵仅为语法演示，未经相机标定"
}
```

响应矩阵必须为有限、可逆且条件数不大于 30 的 3×3 矩阵。坐标模型仍采用上游的 BT.601 limited-range 假设，矩阵作用为 `output = clip(ST + interpolated_coefficients / 256 @ response_matrix, 0, 1)`。这既不证明 Sony 的真实像素坐标，也不把 ICC/sRGB 照片自动解释成 ST。本 CLI 只消费响应部分，不自动使用额外 RAW 字段；[配对标定工具](NATIVE-VALIDATION.md)可构建暂定逆 ST 曲线，但没有附带真实机身标定。

输入 `sony-st-srgb` 表示 CUBE 的设计者明确以 Sony ST 成像后的编码 RGB 作为输入。普通 sRGB、Log、线性 RGB 或电影 LUT 不能仅改标签来适配。其他输入必须提供桥接，字段加在 `source` 中：

```json
{
  "input_space": "my-explicit-log-domain",
  "bridge": {
    "path": "st-to-my-log.cube",
    "input_space": "sony-st-srgb",
    "output_space": "my-explicit-log-domain",
    "evidence": "填写桥接的构建方式、测量依据和适用范围"
  }
}
```

这段是附加字段示例，不是独立项目。桥接必须与目标输入域同名且说明依据；直接 ST 输入禁止再指定桥接。工具验证声明一致性，不能凭声明证明桥接物理正确。桥接输出按目标 CUBE 自己的 DOMAIN 解释，不强行缩放到 0..1；最终参考表的全部输出节点必须在 0..1 编码 sRGB 内，HDR/Log 输出需先另行建立明确的归一化参考。

`domain_policy: reject` 遇到任意采样超出桥接/目标 CUBE 的 DOMAIN 即停止。选择 `clip-and-report` 才会执行边界截断并累计超域行数；不会静默截断。计数包含训练、选择、重复留出及灰阶/分区计算，须结合 `reference_rows_evaluated` 阅读，不能当作唯一像素数。

## 照片与显式区域

照片比较只支持现有工具允许的 8 位 RGB JPEG/PNG，沿用 ICC 转换、EXIF 方向、来源/精度检查。`--st-input` 表示使用者确认这是适合该 ST 模型的参考；sRGB 元数据只证明编码空间，不能证明 ST。仅当确实知道未标记文件为 sRGB 时使用 `--assume-srgb`。独立照片比较当前上限 400 万像素，可另存参考裁片后处理，不会修改原图。

区域可选，工具不自动猜肤色或光照。创建相对于**已应用 EXIF 方向的图像**、同尺寸的 8 位灰度 PNG 掩码，只允许 0 和 255；用 `--masks /path/to/masks.json` 指定：

```json
{
  "schema": "a7c2-offline-region-masks/1",
  "regions": {
    "skin": "skin.png",
    "gray": "gray.png",
    "green": "green.png",
    "sky": "sky.png",
    "highlights": "highlights.png",
    "shadows": "shadows.png",
    "saturated": "saturated.png"
  }
}
```

允许只提供部分区域；缺少区域或空掩码报告 `available: false`，不伪造零误差。掩码路径按清单所在目录解析，报告记录每张掩码的 SHA-256。区域可以重叠。

## 如何读误差和阈值

- RGB MAE、P95 和最大通道误差使用归一化编码 sRGB；色差是本工具明确采用 D65 白点的 Lab 欧氏距离 **Delta E76**，不是 Delta E2000、ICC PCS D50 或相机测量。
- Lab 计算从 sRGB 解码到线性 RGB，再以固定 7 位小数矩阵转 XYZ，白点为 `[0.95047, 1, 1.08883]`。转移函数和 Lab 分段结构可参考 [W3C sRGB 说明](https://www.w3.org/Graphics/Color/srgb)及[颜色转换公式](https://www.w3.org/TR/2026/CRD-css-color-4-20261007/#color-conversion-code)；本实现明确保留 D65，不套用 CSS Lab 所需的 D50 适应。
- `fit` 沿用上游固定分割：随机训练数加 2,048 个灰阶训练样本，2,048 个选平滑强度样本，4,096 个留出样本。额外重算同一留出集以增加色差报告，不参与模型选择；513 点灰阶单独报告参考误差和预测/参考的 Lab 色度。
- 照片及各区域最多取 65,536 个固定种子的无放回样本；不足则全取。报告总像素数、实际样本数和采样方式，P95/最大值是**样本统计**。指标在保存 PNG 的 8 位量化之前计算。完整图像的预测越界通道计数另行精确累计，原生输出按模型截断。
- 示例阈值仅用于合成演示，不是通用摄影质量标准。必须先设置项目阈值再拟合；更改项目、模型、参考、桥接或表字节后，旧候选会被拒绝，需显式重新拟合。软件哈希用于复现和误用保护，不是签名或相机授权机制。
- `acceptance.passed` 只判断整体 RGB MAE / Delta E76 P95 是否满足已声明阈值。还需人工查看收敛、触限、剪裁和区域误差；分区没有单独通过阈值。触限或强非线性 LUT 可能无法拟合。退出码 0 表示计算成功，**不表示阈值通过**。

JSON 上限 128 KiB、训练随机样本 512–50,000、种子 0–2³²−1；CUBE 沿用原工具的 8 MiB/尺寸上限及严格解析。读取和渲染均在电脑完成，无 USB、安装、恢复或固件执行入口。

## 本轮与下一步边界

本轮使用合成恒等、可表达修正和红蓝交换验证数值与保护机制，没有使用真实照片或声称新 ST 标定。第三十一轮已提供[配对标定/冻结场景与分区验收](NATIVE-VALIDATION.md)，N2 离线工具链具备；真实响应和独立场景质量仍未验证。DCP 是后续扩展。下一步为 N3 独立 Mac 迁移设计，N4 相机验证后置，进入前提示。

第三十九轮可将本工具的 `candidate.json`/`correction.table` 接入[私人导入材料清单](IMPORT-MATERIALS.md)，只核验核心格式、完整表指纹及声明误差/阈值一致性；不会重算模型或把拟合通过当机内色彩验证。原生表仍不是固件或可直接交给旧安装器的文件。
