# 常用命令
- 运行 GUI（无显示环境可用 offscreen）：`QT_QPA_PLATFORM=offscreen python3 -m voc_app.gui.app`
- 运行 Loadport CLI/E84 演示：`QT_QPA_PLATFORM=offscreen python3 -m voc_app.loadport.main`
- 单元测试（仅串口模块）：`python3 -m unittest tests/test_serial_device.py`
- 查看项目结构/架构：`sed -n '1,200p' docs/STRUCTURE.md` / `docs/ARCHITECTURE.md`
- 若需手动下载文件（协议测试）：使用 `QmlSocketClientBridge` 绑定后调用 `connectSocket(host, port)` + `getFileAsync(<remote>, <dest>)`。