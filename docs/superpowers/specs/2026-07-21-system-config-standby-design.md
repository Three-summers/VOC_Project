# 系统配置化待机媒体设计

**日期：** 2026-07-21  
**状态：** 已获设计批准，等待文档审阅

## 目标

移除 GUI 中的“配置 → 待机动画”页面，将待机媒体目录和无操作秒数改由统一的系统配置文件提供，并在应用运行时自动重新加载待机设置。

## 配置文件

将 `src/voc_app/logging_config.json` 更名为 `src/voc_app/system_config.json`。文件按功能分区：

```json
{
  "logging": {
    "levels": {
      "voc_app": "INFO",
      "voc_app.gui": "WARNING",
      "voc_app.gui.foup_acquisition": "DEBUG",
      "voc_app.loadport": "INFO"
    },
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  },
  "standby": {
    "media_directory": "/home/say/code/python/VOC_Project/standby_res",
    "idle_timeout_seconds": 60
  }
}
```

`logging_config.py` 从 `logging` 分区读取日志设置，保持现有的启动时日志初始化行为。`standby` 分区是待机控制器唯一可写入以外的配置来源；GUI 不再修改或持久化待机设置。

## 运行时重载

`StandbyMediaController` 通过 `QFileSystemWatcher` 监听 `system_config.json` 及其父目录。父目录监听确保以临时文件替换方式保存配置时也能重新添加文件监听。

文件发生变化时，控制器：

1. 读取 JSON 的 `standby` 分区。
2. 校验 `media_directory` 是字符串，`idle_timeout_seconds` 是正整数。
3. 用新目录和超时更新 QML 属性，重新扫描直接媒体文件并发出变更信号，使无操作计时器重启。

若文件暂时不存在、JSON 无效或待机分区不合法，保留上一份有效的目录和秒数，显示可读错误状态，并继续监听后续修改。配置恢复有效后自动清除错误并应用新值。

## GUI 清理

删除以下仅用于 GUI 配置的内容：

- `ConfigStandbyPage.qml`
- `Config_standbyCommands.qml`
- 配置子导航中的 `standby` 条目
- `ConfigView.qml` 中的 `standby` 路由

主窗口的待机播放层、全局输入退出以及媒体循环行为保留不变。待机控制器继续通过 QML 上下文对象公开，但只读消费系统配置。

## 测试

- 验证 `system_config.json` 的日志与待机分区均被正确读取。
- 验证启动时从待机分区得到目录和秒数。
- 验证文件修改后控制器自动应用新目录/秒数并重新扫描。
- 验证无效热更新不覆盖上一份有效设置。
- 验证不存在待机设置页面、路由与命令组件，且 QML 组件测试不再引用它们。

## 非目标

- 不在本次改动中使日志级别/格式热重载；日志设置继续在应用启动时加载。
- 不提供待机设置的 GUI 编辑能力。
- 不改变图片、视频、静音、顺序循环或任意输入退出的既有待机行为。
