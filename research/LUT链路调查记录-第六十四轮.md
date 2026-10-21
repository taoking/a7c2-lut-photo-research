# 第六十四轮：D4真实电脑端核验与菜单设置发布保护

2026-10-22。用户指示继续D4开发，并说明PRIVATE目录拷贝自相机保存设置。本轮完成D4电脑端真实检查，保留D1–D3离线冻结；**D4尚未完成，真实内部首采未执行。** 没有枚举、打开、认证相机或读移动盘，没有sudo、相机锁、系统磁盘命令、机内模块、固件/设置写入或恢复。

## 本轮实际进度

1. 复核D3提交 `4873fda4d053d8a8d71b8a9630fa209166cc5cb2` 的[CI 39644666229](https://github.com/taoking/a7c2-lut-photo-research/actions/runs/39644666229)，结果completed/success。它属于D3，不能替代当前提交的CI或相机验收。
2. 当前真实Mac为macOS27.0.1/arm64，Python3.14.6/64位；依赖PyUSB1.3.1及libusb-package1.0.30.0匹配。实际运行原capturepreflight，固定归档及带68资源的357,258,024字节容量预算通过，未创建目标作业。管理员上下文为false，权限不作成功推断。
3. 独立子进程真实导入现装usb.core/util/libusb1和libusb_package，检查实际签名、随包库选择及加载；Mach-O arm64库162,832字节，静态版本查询返回1.0.30.12037，13个后续需要的导出符号可解析。只调用libusb_get_version；未构造后端或设备、调用get_backend/libusb_init/枚举/open/claim/传输。PyUSB后端全局对象在前后保持None。
4. 根.gitignore新增`/PRIVATE/`，避免菜单设置被普通git add纳入；没有搬移、覆盖或读取PRIVATE内容，没有受跟踪PRIVATE文件。来源仅记录为用户声明的菜单设置副本，不认证文件格式、机型、版本或可恢复性；它不能作为内部AP/CP/BK4/68UXC、降级或独立介质证据。
5. capturemac原说明仍称“无公开入口/没有已交付调用方”，与现有captureexecution/capturecamera事实不符，本轮仅修正模块/类docstring。去除docstring后的运行AST完全一致；没有改运行流程、固定来源、原安装器、安全门槛或依赖。

版本结构及静态查询语义核对[libusb v1.0.30头文件](https://github.com/libusb/libusb/blob/v1.0.30/libusb/libusb.h)和[core实现](https://github.com/libusb/libusb/blob/v1.0.30/libusb/core.c)。仅按公开ABI调用版本函数，不复制/分发库或头文件；库加载/版本/符号不证明真实SDK管理、USB权限、接口/重枚举、服务协议或退出成功。旧capturepreflight仍不导入SDK，不能将独立主机检查混称该命令新增能力。

## 实际检查与测试

```sh
sw_vers
uname -m
.venv/bin/python -B -m lutphoto.capturepreflight --archive research/materials/upstream-v2.1-audit/a7c2-tools-2.1.zip --directory "/path/to/owner-parent/capture-new" --resources
.venv/bin/python -B research/output/custom-round64/probe_host_sdk.py
.venv/bin/python -B -m unittest discover -s research/tests -p 'test_capturemac.py' -v
.venv/bin/python -B -m unittest research.tests.test_capturecamera research.tests.test_capturepreflight -v
git check-ignore -v PRIVATE/ PRIVATE/example.dat PRIVATE/settings/example.dat
git ls-files -- PRIVATE
git diff --check
```

上述输出路径已匿名化。主机预检退出0；专用电脑端SDK检查脚本退出0，仅为本机忽略目录中的证据脚本，不是新增已发布CLI或设备执行器。49宿主测试及19公开入口/14预检测试，共82项通过；不接触真实USB。另以-S导入capturemac通过，未导入SDK；运行AST、忽略规则/无私人受跟踪文件和公开文档/隐私检查通过。

最初将capturemac以包模块名和另外两个模块一起执行，34项中的1项加载失败：旧测试使用顶层`test_capturemsc`导入，包模块模式未提供该搜索位置；其余33项通过。随后按已有发现模式执行capturemac49项，另两个模块33项，均退出0；未改测试、伪造模块或调整生产实现来掩盖错误。原失败日志保留。不因docstring/忽略变更重跑无关全套；最近全套1016项属于D3及对应CI，不称本轮重新执行。

忽略目录custom-round64保留初始工作树、host-preflight.json、host-sdk.json、scope-audit.json、实际测试日志和公开/发布核验。SDK源/库身份只在该本机记录；没有机身程序、设置、身份或私人路径进入公开摘要。原plan本地分析附录逐字保持，未跟踪分析报告哈希保持；PRIVATE先排除且未读内容。旧历史、锁、安装器、依赖/旧测试不变，总计划发布部分仍为四列16行。

## 交接

[D4条件文档](../docs/D4-HOST-READINESS.md)、[交付计划](../docs/DELIVERY-PLAN.md)、[四列总计划](../plan.md)、README、[首次采集说明](../docs/CAPTURE-FIRST-USE.md)、[发布边界](../docs/PUBLISHING.md)、致谢及[短交接](HANDOFF.md)同步实际范围。D4状态为电脑端核验通过、真实首采待条件；N3仍部分完成、N4未执行，不以检查数提高进度。

已询问本人当前菜单版本及升级安排；未有新确认时沿用最近原厂2.00记录。继续开发不是当前相机服务操作授权。若保留2.00，在此等待，不运行2.01入口或prepare/diagnose；若选择官方升级，先核对官方条件并等待实际完成，不自动升级或假定降级可用。

真正实采前一次取得实际机型/原厂版本、刚查看的电量至少50%、MSC数据线连接、本人私人位置和明确只读范围。使用现有capturecamera显式--resources，共6核心+68UXC=74材料，默认一份及独立回执；认证/选读改变临时状态，不加载模块、不写程序/保存设置、不WBI。真实SDK/通信/退出、同机材料与完整身份在此阶段分别验证；未知停止保留、不重试。管理员认证只在系统/终端，不索取密码。

后续D5真实事务/恢复审阅及两份独立介质内部备份满足后才另行单槽写入，D6再做真实ST/一种风格摄影验收。当前电脑条件无新增安装需求，不要求Docker/Windows；真实版本/电量/连接、系统权限和本人采集配合仍是缺口。没有这些条件时不继续增加自制模拟轮次。
