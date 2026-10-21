# 公开仓库与发布边界

公开仓库：[taoking/a7c2-lut-photo-research](https://github.com/taoking/a7c2-lut-photo-research)。已完成首次源码推送及远端文件核对，详情见[第二十六轮记录](../research/LUT链路调查记录-第二十六轮.md#公开发布)。

本仓库发布机外 LUT 参考工具、原生拟合/配对标定/冻结场景验收、只读调查脚本、合成测试、研究记录，以及继承的 macOS 适配源码。**机内照片 LUT 尚未实现，没有照片 LUT 安装包或可用补丁。** 研究测试与相机安装工具的历史实机验证分别记录，不互相替代。

保留 [MDHan、QAQLeonard 及其他上游署名](../ACKNOWLEDGEMENTS.md)、[许可证](../LICENSE)、[来源说明](../NOTICE.md)与固定上游锁文件。研究路径不修改原安装器的固定哈希、偏移、机型/版本或安全门槛。

公开树仅纳入审核过的源码、文本说明和公开验证摘要。`research/materials/`、`research/output/`、`.upstream/`、`.venv/`、根`PRIVATE/`菜单设置副本、原始固件、设备备份、设置、个人日志和生成报告不随发布上传；发布前同时核对候选文件和将推送的历史，文档使用通用路径。

复核入口：

```sh
.venv/bin/python -B -m unittest discover -s research/tests -v
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s .upstream/a7c2_fl23_preview/tests -v
.venv/bin/python -B -m macfl23 check
git diff --check
```

上述测试全部离线。研究指令断言的原版材料由使用者自行准备，公开 CI 不包含官方程序或私人备份。相机实测继续后置，进入前提示；公开推送不代表机内功能验收。

第三十一轮的统一发布范围为第二十七至三十一轮已审核的源码/文档，目标为 `lut-photo/main`；不会推送到来源仓库 `origin`。验证命令和限制见[本轮记录](../research/LUT链路调查记录-第三十一轮.md)，提交及推送结果以 Git 提交记录、远端 `main` 和本轮任务最终报告为准。
