# macOS USB总线0：有效域修正与验证边界

2026-10-25，第七十二轮。仅电脑端静态审阅、代码修正和自制SDK/材料测试，不枚举或操作真实相机。第七十一轮实际记录仍为KEY_VALIDATE/BUS、6事件/0材料；原始总线值未记录，不能倒推当时必为0，也不能声称真机采集已经修复。

## 固定来源证明的问题

固定libusb 1.0.30的[Darwin实现](https://github.com/libusb/libusb/blob/v1.0.30/libusb/os/darwin_usb.c#L1374-L1376)明确注明总线从0编号，并以location ID高字节设置bus_number。[API](https://libusb.sourceforge.io/api-1.0/group__libusb__dev.html)返回uint8_t；该值有效域是0–255，不能把合法的总线0解释成未找到设备。

PyUSB 1.3.1的[libusb后端](https://github.com/pyusb/pyusb/blob/v1.3.1/usb/backend/libusb1.py)从libusb_get_bus_number取得bus，随后[Device构造](https://github.com/pyusb/pyusb/blob/v1.3.1/usb/core.py)将描述符字段转为整数。本机两个已安装Python源文件与上述固定标签下载字节完全一致；本轮没有导入SDK或加载库来取得设备值。libusb-package仍固定1.0.30.0，未更换依赖；静态上游源码不认证安装二进制或当次设备数据。

原项目把bus限定为大于0的整数，属于电脑端平台假设错误。只改第一处枚举会让总线0随后在认证位置或回执观察校验处失败，因此同时修正四处：

| 位置 | 当前规则与作用 |
| --- | --- |
| capturemac._Key | 总线须为精确整数0–255；相比旧规则增加255上界，0原样保存 |
| capturesession._location | 认证与返回身份共享位置校验使用同一有效域 |
| captureevidence._observation | 既有检查器接受同一原始编号，仍核对其余观察字段 |
| capturediagnostics.rejected_key_fields | 与当前原始字段规则一致，负数/缺失/非整数仍报告BUS |

没有把0改成1、替换或伪造机身身份、增加后端选择或使用默认位置。0参与原来的总线号和完整端口路径严格比较：0→1、端口变化、重复设备仍拒绝；没有把0设为通配符。None、布尔、浮点、字符串、负数和大于255都拒绝。端口仍须明确且非0，型号/序列协议身份、PID/地址、唯一机身、同次重枚举、新返回身份、完整程序指纹等原检查不变。

## 验证和兼容

新增[总线回归](../research/tests/test_capturebus.py)：自制总线0的完整74材料/三所有者流程、原始0写入并读回检查点、与总线1相同的SDK动作序列/计数、服务/返回总线变化、端口变化、重复设备、未知值拒绝及旧BUS失败回执不被升级或改写。仅使用已有假SDK/材料，没有另建传输层或设备模式。

旧诊断回执没有原始bus，其BUS拒绝仍按历史事实读取，保持UNKNOWN/失败，不能用新取值域重写成成功。回执/检查输出仍为/3，严格接受旧/1、/2，字段和CLI不变。第六十七/六十九/七十一轮已使用的脚本保持原字节，当前源码冻结已过时，禁止再运行。

1080项回归与16项[新单次准备](CAPTURE-TRIAL-REVIEW.md#第七十二轮修正后准备)通过，167份源码/依赖文件已冻结；本人选择保持现状、稍后采集，当前不执行。本轮尚无新实机结果；第六十七轮的身份查询USBError也没有被本次修正解决或排除。只有未来全新受控作业完成材料和退出核验才推进D4，写入/恢复/真实色彩不自动解锁。测试命令和实际结果见[第七十二轮](../research/LUT链路调查记录-第七十二轮.md)，当前动作见[交接](../research/HANDOFF.md)。
