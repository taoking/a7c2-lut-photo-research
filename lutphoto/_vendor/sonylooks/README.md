# 固定上游离线算法

`native.py`、`color.py`、`calibration.py` 按原始字节复制自 QAQLeonard 的 [a7c2-fl23-research v2.1](https://github.com/QAQLeonard/a7c2-fl23-research/tree/7e54d60b458847f1befa6cfd614fbf004b8b0b90/src/looks/looktool)。未修改算法；路径、提交、长度、SHA-256 和作者记录在 [PROVENANCE.json](PROVENANCE.json)，[完整 MIT 许可](LICENSE.txt)保留。固件资料的权利边界另见根目录 [NOTICE.md](../../../NOTICE.md)。

这里只分发三个纯 NumPy 源文件；没有设备模块、相机资源、真实标定、照片或 DCP。坐标及像素响应仍是近似模型。接入层及验证说明见 [N2 文档](../../../docs/NATIVE-FIT-OFFLINE.md)。

配对标定接入及分割/场景验收说明见[N2 冻结验证](../../../docs/NATIVE-VALIDATION.md)。
