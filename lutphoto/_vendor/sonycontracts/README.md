# 固定上游资源与设置契约

两个 Python 文件及资源文件名清单按原始字节复制自 QAQLeonard [v2.1 固定提交](https://github.com/QAQLeonard/a7c2-fl23-research/tree/7e54d60b458847f1befa6cfd614fbf004b8b0b90/src/looks)。完整路径、长度、SHA-256 见 [PROVENANCE.json](PROVENANCE.json)，保留[完整 MIT 许可](LICENSE.txt)。清单只有 68 个文件名，没有 Sony 资源内容。

接入层只调用资源解码/改名/逆向、设置比较与保存保护。`devicesettings.plan` 需要未随本包分发的 `device_layout` 和真实 AP 描述符，不能使用；不提供替代身份函数或模拟放行。没有 USB、机内执行代码或固件。上层的额外边界检查与合成格式测试见[离线契约说明](../../../docs/CUSTOM-CONTRACTS.md)。
