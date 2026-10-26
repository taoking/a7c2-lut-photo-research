# 第七十七轮：有限服务验证单次准备与公开发布

日期：2026-10-26。基线`d94a4628171aeacbebfc707f98bc1d8d2cb34a09`。本轮承接第76轮，完成R3的电脑端操作准备，不扩展协议或完整采集入口。本人授权提交推送，准备完成期间主动报告已连接并确认MSC/官方原厂2.01；现场电量和管理员认证留在终端。本记录当前尚无本轮设备结果。

## 交付

新操作只调用一次`lutphoto.captureprobe`，读取一份RAM快照。沿用受信来源、私有父目录/所有权、新作业与回执排他创建、一次性日志拒绝覆盖。源码冻结172个文件，含新probe/identity、现有运行依赖、测试、声明和专用读取器；项目导入前、现场电量输入后、预检后、摘要子进程前重复核验，变化即停止相应后续动作。

新私有摘要读取器通过独立-S进程只读新回执，检查私有普通文件/不跟随链接/共享非阻塞锁/有界JSON、严格布尔字段与明显矛盾。仅输出固定结果和白名单错误类别/数字码，不输出身份、位置、私人路径、原始材料或材料摘要。它的作用域明确为`receipt-fields-only`，不是完整证据图或硬件验证。采集、摘要退出码分别保存，非0不被后续成功覆盖。

三个操作文件和新路径在忽略目录`research/output/custom-round77/location.private.json`登记。没有复制任何私人材料到公开树，没有修改旧第72轮操作摘要或覆盖旧作业。当前代码不变；实机步骤只用新准备，接续顺序见[HANDOFF](HANDOFF.md)。源码冻结是本地防漂移检查，不是签名或SDK二进制认证。

## 实际检查

| 命令/检查 | 结果 |
| --- | --- |
| `.venv/bin/python -B -m unittest discover -s research/tests -v` | 1075通过，83.706秒 |
| `.venv/bin/python -B -m unittest discover -s tests -v` | 39通过 |
| `.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v` | 8通过，完整回归合计1122 |
| `.venv/bin/python -B research/output/custom-round77/test_preparation.py` | 15通过，0.426秒 |
| `.venv/bin/python -B -m macfl23 check` | 固定来源/资产通过，无设备访问 |
| `.venv/bin/python -B research/output/custom-round74/check-legacy-receipts.py` | 3类自制旧记录分类和字节保持，无SDK |
| `.venv/bin/python -S -B -m lutphoto.captureprobe --help` | 实际CLI参数通过，无SDK/USB |
| 普通用户临时私有目录预检，无resources | 通过，285954856字节保守预算；未创建作业、管理员标志false |
| `.venv/bin/python -B research/output/custom-round77/check-publication.py`、`git diff --check` | 提交前核对公开范围、链接、私人信息、冻结/来源及已有文件保留 |

准备测试覆盖实际probe在自制SDK上只取一份快照、未知失败不停止服务、不继续读取、成功摘要不能覆盖失败、摘要失败不能转为成功、输入期间/执行后源码变化、链接/超限源码、旧目录保留、真实非管理员拒绝、锁住/重复JSON回执拒绝、摘要隐私及一次调用。初次测试对清单中包含capturecamera文件名误判，改为AST调用名称检查后通过；未改生产代码来迁就断言。

## 发布范围与未完成项

本轮获明确授权，将第73–76轮读包修正、快照身份、独立有限入口及测试/记录，与此前五份公开专项分析和本轮准备摘要一并审阅发布。开工34项既有文件已快照；保留各报告原资料日期，不把发布当作重新联网核验。目标`lut-photo/main`，不推origin；私人脚本/位置/日志、原件、固件、设置和身份不提交。提交及远端结果以Git记录和本轮最终回执为准。

本轮尚未验证机内效果、完整备份、返回序列、恢复、冷启动或拍摄。D4仍0真实材料。本人已确认连接，下一步按交接完成新单次有限验证；成功后先审阅完整采集接入再安排R4，失败保留记录、未知即停，不解除历史UNKNOWN或重跑旧74材料入口。同阶段无新证据时转Windows原生只读对照评估或后置Mac。
