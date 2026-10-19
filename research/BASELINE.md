# 离线研究固定基线

继续任务按 [HANDOFF.md](HANDOFF.md) 选择材料；本页仅在基线变化或核对指纹时读取。所有操作仍受根目录 AGENTS.md 约束。

研究起点提交：`5babef40bba986efdd0573380c0ff9f8a027495c`；固定上游：`dd01c07a2a5df004d709595a43ebafe81bbd8fae`。现有 `.venv` 可用，研究要求 Python ≥3.12，依赖独立见 `requirements-lut.txt` / `requirements-firmware.txt`。不要重新安装相机或覆盖已有工作目录。

官方包 SHA-256：`eb4943e6099754d64deaef5047942e9bfe258f232d0b7bc39fa23b3cd10e1e31`。已有解包材料根目录：

```text
research/materials/official-2.01/firmware.tar_unpacked/0700_part_image/dev/
  nflasha8_unpacked/cpapp-b.bin
  nflasha15_unpacked/lib/appFw.so
```

- CP SHA-256：`f5a477588698ef965748903b8959a39ce4f59ffd4aee4d4234ef1670f56a1428`
- AP SHA-256：`2ea02f7ecbc5bb917316fe8ef4ce5ffd87eb66efaae78ba2ce11420552df539b`
- CP 链接基址从启动指令取得 `0x108000`；研究记录的函数位置均为文件偏移。不要手算 BL 的目标减法，也不要从任意半字开始就认定是代码。
- 材料、解包工具、JSON 和图片在忽略目录中，不上传原始程序或私人备份/日志。工具拒绝已有输出，复跑须用新的文件名。
