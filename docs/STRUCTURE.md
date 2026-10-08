# 项目目录结构

> 更新日期：2026-09-28

```
VOC_Project/
├── pyproject.toml            # 依赖、pytest 配置（testpaths/pythonpath）
├── conftest.py               # 测试隔离：强制 offscreen Qt + 临时数据目录
├── docs/                     # 文档（架构、结构、变更、验证）
│   └── superpowers/          # 设计与实施计划（specs / plans）
├── deploy/                   # systemd --user 单元与 autostart 模板
├── examples/                 # 手工联调脚本（模拟服务端、串口交互示例）
├── src/
│   └── voc_app/
│       ├── app_paths.py      # 系统配置定位、数据目录解析、旧状态迁移
│       ├── logging_config.py # 统一日志配置
│       ├── version_info.py   # Loadport 版本读取（manifest → pyproject）
│       ├── system_config.json# 包内默认配置（首次运行复制为数据目录中的用户配置）
│       ├── gui/
│       │   ├── app.py             # GUI 入口（python -m voc_app.gui.app）
│       │   ├── foup_acquisition.py# FOUP 采集控制器（TCP 协议、通道分发）
│       │   ├── socket_client.py   # 长度前缀协议客户端与通信抽象
│       │   ├── channel_config.py  # 前缀预设与通道配置持久化
│       │   ├── csv_model.py       # 图表系列模型与 CSV 文件管理
│       │   ├── spectrum_model.py  # 频谱数据模型与模拟器
│       │   ├── chart_options.py   # 图表显示策略（报警颜色同步、Y 轴范围）
│       │   ├── standby_media.py   # 待机媒体控制器（读系统配置）
│       │   ├── status_gpio.py     # 状态灯/蜂鸣器启动初始化
│       │   ├── update_status.py   # 升级状态轮询
│       │   ├── alarm_store.py     # 报警模型
│       │   ├── file_tree_browser.py # 文件预览控制器
│       │   ├── qml_socket_client_bridge.py # QML 侧 TCP 命令桥
│       │   ├── performance_config.py # 运行环境检测与 Qt 性能设置
│       │   ├── qml/               # QML 界面（main/views/components/commands）
│       │   ├── resources/         # GUI 静态图片资源
│       │   └── channel_config.json# 旧版通道配置（首次启动迁移到数据目录）
│       └── loadport/
│           ├── main.py          # E84 控制器 CLI 入口（需要 RPi.GPIO）
│           ├── e84_passive.py   # E84 被动状态机与采集联动信号
│           ├── e84_thread.py    # E84 控制器的 QThread 封装与信号中继
│           ├── gpio_controller.py # RPi.GPIO 输入输出抽象
│           ├── ascii_serial.py  # STM32 ASCII 串口客户端
│           └── serial_device.py # 通用串口设备兼容层
├── tools/updater/            # 独立升级器（部署在 release 之外）
│   ├── update.py
│   └── voc_updater/          # 配置、包校验、Loadport/FOUP 安装、状态写入
├── tools/host_upgrade_verification/  # 真实 Ubuntu 主机升级事务验证脚本
├── tests/                    # 单元测试（pytest 收集范围之一）
└── verification.md           # 历次验证记录（git 忽略，本地保留）
```

## 配置与运行期数据

运行期可变状态不再写在源码 release 目录里，避免升级切换 `current` 软链后丢失现场设置。

| 内容 | 位置 | 说明 |
| --- | --- | --- |
| 系统配置 | `<数据目录>/system_config.json` | 首次启动由 `src/voc_app/system_config.json` 复制生成，可现场编辑 |
| 通道配置 | `<数据目录>/channel_config.json` | 首次启动从旧的 `gui/channel_config.json` 迁移 |
| 采集日志 | `<数据目录>/Log` | 下载的 CSV，同时作为 DataLog/FileView 根目录 |

数据目录优先级：环境变量 `VOC_DATA_DIR` > 配置项 `paths.data_directory` > 用户数据目录
（`$XDG_DATA_HOME/voc`，缺省 `~/.local/share/voc`）。

配置文件的查找优先级：`VOC_SYSTEM_CONFIG` > `<数据目录>/system_config.json` > 包内默认值；
用户配置与包内默认值按分区递归合并，因此新增默认项不会覆盖现场设置。

## 运行方式

- GUI：`python -m voc_app.gui.app`（无显示环境加 `QT_QPA_PLATFORM=offscreen`）
- Loadport CLI：`python -m voc_app.loadport.main`（需要树莓派 `RPi.GPIO`，非树莓派会导入失败）
- 单元测试：`pytest`（`pyproject.toml` 已限定收集范围，`conftest.py` 负责 Qt 平台与数据目录隔离）
- 模拟服务端联调：`python examples/test_server.py`（`TEST_SERVER_*` 环境变量可配置类型与频谱推送）
