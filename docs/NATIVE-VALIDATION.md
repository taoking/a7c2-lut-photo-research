# 配对标定与冻结场景验收

N2 现在具备完整的电脑端流程：有界配对补丁构建暂定 ST 逆向模型，拟合前冻结项目、图片、掩码和阈值，再用绑定该冻结清单的候选做多场景比较。它测量的是**模型预测相对 CUBE 参考的误差**，没有测量机内 JPEG；场景身份仍由使用者声明，实际相机精度始终标记未验证。

继续使用 `requirements-lut.txt` 的 NumPy/Pillow。原样复用 QAQLeonard 固定 v2.1 的第三个纯模块 `calibration.py`；[来源与哈希](../lutphoto/_vendor/sonylooks/PROVENANCE.json)、[许可](../lutphoto/_vendor/sonylooks/LICENSE.txt)保留，不增加设备或 SciPy 依赖。基本拟合与单照片格式先读[原生表工具](NATIVE-FIT-OFFLINE.md)。

## 合成完整流程

以下从仓库根目录执行，目录/输出文件必须尚不存在，冻结输出文件的父目录须已存在。所有素材自制，不需连接相机：

```sh
.venv/bin/python -B -m lutphoto.nativevalidate fixtures \
  --directory research/output/validation-demo
.venv/bin/python -B -m lutphoto.nativevalidate calibrate \
  --patches research/output/validation-demo/patches.json \
  --directory research/output/validation-demo/calibrated
.venv/bin/python -B -m lutphoto.nativevalidate freeze \
  --project research/output/validation-demo/validation-project.json \
  --manifest research/output/validation-demo/scenes.json \
  --output research/output/validation-demo/validation.lock.json
.venv/bin/python -B -m lutphoto.nativefit fit \
  --project research/output/validation-demo/validation-project.json \
  --validation-lock research/output/validation-demo/validation.lock.json \
  --directory research/output/validation-demo/fitted
.venv/bin/python -B -m lutphoto.nativevalidate benchmark \
  --project research/output/validation-demo/validation-project.json \
  --candidate research/output/validation-demo/fitted/candidate.json \
  --validation-lock research/output/validation-demo/validation.lock.json \
  --directory research/output/validation-demo/benchmark
```

输出分别为 `model.json/calibration.json`、冻结清单、候选表/报告，以及 `benchmark.json` 和各场景的参考/预测 PNG。退出 0 只表示计算完成；必须检查 `acceptance.passed` 和缺口。合成标签、单位响应和两张人造图表不能证明真实肤色、独立场景或 Sony ST 准确度。

## 配对数据契约

输入采用 `a7c2-offline-patch-set/1`，JSON 上限 128 KiB。示意结构如下；单条示例不能运行，实际需 64–512 条，每个声明场景至少 32 条，训练/留出各至少 32 条：

```json
{
  "schema": "a7c2-offline-patch-set/1",
  "material_kind": "synthetic",
  "st_space": "sony-st-srgb",
  "reference_space": "linear-prophoto-d50",
  "evidence": "说明对齐、曝光、白平衡、RAW 显影和颜色空间依据",
  "response_evidence": "说明单独测量响应矩阵的依据",
  "response_scene_ids": ["response-scene"],
  "response_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
  "max_holdout_linear_prophoto_mae": 0.02,
  "patches": [
    {"id": "p1", "scene": "train-scene", "split": "train",
     "st_rgb": [0.5, 0.5, 0.5], "linear_prophoto": [0.214, 0.214, 0.214]}
  ]
}
```

`material_kind` 允许 `synthetic` 或 `camera-paired-declared`，后者仅为声明。RGB 必须有限且归一化到 0..1；所有 ID 限 1–64 个 ASCII 字母/数字/连字符/下划线，场景/响应 ID 列表有界，补丁 ID 不能重复。相同场景不能跨训练/留出，完全相同的一对观测也不能跨分割；训练颜色变化需三维满秩，灰阶样本不能独自确定颜色矩阵。这些检查不能识别改名的同一实景或裁片。

标定复用上游的 65 节点单调曲线、受限 3×3 混色与固定 12 次更新。只有训练补丁参与参数构建；留出补丁计算线性 ProPhoto RGB MAE/P95/最大通道误差，按留出场景分别报告，并要求每个留出场景满足事先 MAE 阈值。此处是**线性 ProPhoto 误差**，不能与后续编码 sRGB/Delta E76 阈值混用。

`response_matrix` 是另行提供的 ISP 响应，**不是从这些 ST/RAW 配对中估计出来的**；模型记录来源和响应场景。构建结果与上游 `a7c2-look-calibration/1` 兼容，保留完整补丁文件 SHA、分割/场景身份、阈值和 `full_camera_characterization: false`。不附带真实相机模型，不复制其他机型的 RAW 矩阵；当前 CUBE 拟合只消费模型的响应部分，逆 ST 曲线保留给后续桥接/DCP 工作。

## 场景、区域与阈值

清单为 `a7c2-offline-scene-set/1`。完整可运行模板由 `fixtures` 生成，字段如下：

- `material_kind` 为 `synthetic` 或 `camera-st-declared`，以及非空 `evidence`。
- `required_scene_ids` 列出需要验收的全部场景；可缺部分实际图片，但报告会列出缺失并判定未通过。
- `excluded_scene_ids` 必须包含模型记录的所有训练、留出和响应场景；验收场景 ID 不得与之重合。
- `scenes` 提供 1–16 张图片，每条包含唯一 `id`、`input`、可选 `masks`、强制 `st_input: true` 和可选布尔 `assume_srgb`。图片/掩码限制沿用单照片工具；禁止相同图片字节冒充不同场景。
- `thresholds.overall` 以及 `thresholds.regions` 中全部七类区域，每条必须声明 `min_samples`、`max_rgb_mae`、`max_delta_e76_p95`。区域名为 `skin/gray/green/sky/highlights/shadows/saturated`，掩码格式沿用单照片工具。
- `thresholds.max_bounded_coefficients` 为 0–1,215 的整数；`thresholds.max_native_clip_fraction` 为 0–1 的有限数值，约束完整图像预测被截断的通道比例。

每张图的整体误差及剪裁比例必须通过。每类区域至少在一张图出现，并且**所有出现该区域的场景**都需满足该区域的样本数和误差阈值；不要求每张图片都含全部七类区域。未提供/空掩码为 `unavailable`，非空但采样不足为 `insufficient_samples`，误差超限为 `failed_threshold`。一个好场景不能通过平均值掩盖另一个失败场景，P95 不进行跨图片平均或假装合并。

完整验收还要求：无缺失必需场景、模型配对留出验收已通过、候选拟合收敛、触限数符合声明。只有响应矩阵的旧模型仍可做对比，但缺少配对留出证据时不会通过整体验收。区域最多采样 65,536 个像素，种子与候选一致；报告保留每张图的样本数和采样口径。

## 冻结和变更规则

`freeze` 只核对并记录输入，不计算色彩验收结果；固定项目/模型/参考/桥接哈希、完整清单字节、场景照片、掩码清单和每张掩码的哈希及阈值。冻结文件记录相对于自身的场景清单路径，不包含照片字节。

`fit --validation-lock` 在拟合前及发布候选前再次核对冻结内容，把冻结文件 SHA 写入候选。`benchmark` 要求候选事先绑定该冻结文件；先拟合的旧候选不能事后获得“预先冻结”的标志。更改阈值/来源/模型/任何场景文件后，需要新输出文件重新冻结并显式重新拟合，不改旧候选。发布前再次核对所有输入，并校对实际渲染报告中的照片/掩码/候选哈希。

这是一份复现与防误用契约，不是数字签名或可信时间戳，不能证明人工没有事后调整阈值、改写报告或重用同一实景。场景 ID 不足以证明物理独立，软件也不自动识别拍摄光源、白平衡或肤色。真实验收阈值应在独立样张揭盲前由使用者确定；示例阈值只用于软件验证。

失败不会覆盖已有输出。多场景预测先在临时目录计算，全部输入检查完成后才发布最终目录；异常会清理临时结果。模型、冻结清单、样张和报告应保存在忽略的研究输出或仓库外，公开仓库只保留源码和自制测试生成器。

## 后续

N2 的离线能力现已具备，真实 ST 响应、真实配对样张、跨光源/跨场景质量和预览/JPEG/回放一致性仍留给 N4。下一步为 N3 独立 Mac 工具链、精确来源迁移及失败/恢复模拟；当前不需要连接相机，进入实测前提示。DCP 及自动桥接构建为后续扩展，真正 3D LUT 研究支线仍未闭合。
