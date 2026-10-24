# LUT 照片开发：当前交接

更新：2026-10-25，第七十一轮实测结果收尾。先读根规则、README、[四列计划](../plan.md)、[本轮记录](LUT链路调查记录-第七十一轮.md)、[枚举诊断](../docs/CAPTURE-INVENTORY-DIAGNOSTICS.md)。N1完成，N2离线完成/真实ST未证，N3部分完成，N4未执行；D1–D3冻结，D4仍无完整采集正例。

## 最新真实事实

本人确认ILCE-7CM2/索尼官方原厂2.01，仅授权采集和检查，禁止更新/修改。第七十一轮单次尝试已由本人运行并报告结束：6事件、ValueError、NEEDS_REVIEW_UNKNOWN、0材料、0已打开句柄/身份查询/认证/传输，服务切换未开始。原CLI退出1、自动文件复核退出1/MATCHED_FAILURE、摘要导出0不是采集成功。

新增宿主诊断绑定通过：inventory_call:1、KEY_VALIDATE、invalid_key_fields:[BUS]、ValueError；errno/backend_error_code均null、record_error_type:null。这证明本次缓存总线字段不满足原精确整数且大于0的门槛，不证明bus的具体值、线材或机身故障。日志未保存原始数值，不断言bus=0。身份诊断为空，程序身份/完整材料仍未证。

第六十九轮6事件/ValueError未记录内部边界，第六十七轮41事件/USBError、13调用/8451字节未记录错误码，独立保留0材料/UNKNOWN，不回填成本次相同原因。旧结果指针分别在custom-round69和custom-round67。本次位置在忽略目录custom-round71/reviewed-capture-location.private.json的output字段；completion-review-20261024.private.json记录已执行结果，准备索引里的未执行标志仅历史状态。所有旧单次命令均已使用，禁止再运行。

本人报告画面正常，最初只确认充电灯熄灭；随后对照官方图明确确认7号存取灯已熄灭。已按官方说明提示Finder有卡图标先正常推出再拔线，无图标可跳过，受阻不强制；尚未确认实际断开，10月25日当前连接不猜测。人工观察不补填拍摄/回放/冷启动、驱动或恢复验收。

## 电脑核对与边界

本轮准备原15项和采集/回执68项通过，实际执行如上失败，不能互相补成功。结果核对只读本人普通用户0600日志/本地SDK源码，不重开管理员原始目录或访问USB；原日志/回执/冻结脚本不修改。程序代码、固定锁、依赖、旧安装器保持原样，PRIVATE/移动盘不读改上传。

本地静态SDK核对：PyUSB的Device.bus来自后端描述符，libusb后端来自libusb_get_bus_number。只读取安装文件，没有导入/加载或调用SDK。下一轮应核对固定版本Darwin编号定义及所有位置/证据校验点；先弄清有效取值域和同端口绑定，不能改成任意值或绕过机型/指纹/未知停止。当前无新采集命令，不重连、不再试。

D4真实程序/74材料及完整退出仍缺，D5事务/恢复、独立介质备份与N4单槽/真实色彩继续后置。真正3D LUT保留[第二十八轮支线缺口](LUT链路调查记录-第二十八轮.md#遗留与交接)。

本轮准备09e3ca4已发布，结果文档提交推送以Git为准，仅lut-photo/main。custom-round71开始时8份快照用于保留README/DELIVERY/plan既有分析及5份未跟踪报告，发布视图逐块排除旧差异，私人日志/脚本/位置/机身材料不发布。历史查[轮次索引](ROUNDS.md)。
