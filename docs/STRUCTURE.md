# 项目目录结构

```
VOC_Project/
├── docs/                  # 文档与结构说明
├── src/
│   └── voc_app/
│       ├── gui/
│       │   ├── app.py            # GUI 入口 (python3 -m voc_app.gui.app)
│       │   ├── alarm_store.py
│       │   ├── csv_model.py
│       │   ├── file_tree_browser.py
│       │   ├── qml/              # QML 视图
│       │   ├── resources/        # GUI 静态资源
│       │   ├── Log/              # GUI 生成的日志目录
│       │   ├── qml_socket_client_bridge.py
│       │   └── socket_client.py
│       └── loadport/
│           ├── main.py          # E84 控制器 CLI 入口 (python3 -m voc_app.loadport.main)
│           ├── E84Passive.py
│           ├── e84_thread.py
│           ├── GPIOController.py
│           └── serial_device.py
├── tests/
│   └── test_serial_device.py
└── verification.md
```

## 运行方式
- GUI: `QT_QPA_PLATFORM=offscreen python3 -m voc_app.gui.app`
- Loadport CLI: `QT_QPA_PLATFORM=offscreen python3 -m voc_app.loadport.main`
- 单元测试: `python3 -m unittest tests/test_serial_device.py`
