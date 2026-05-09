# 版本更新系统设计

- 日期：2026-05-09
- 项目：VOC_Project
- 范围：Loadport 上位机版本更新、FOUP 下位机 PS/PL 更新、GUI 版本与更新状态显示

## 1. 背景与目标

当前项目是运行在树莓派上的 Loadport 上位机程序，入口为 Python GUI：

```bash
python -m voc_app.gui.app
```

FOUP 下位机运行在另一块 Linux 开发板上，树莓派与 FOUP 开发板通过网线连接。FOUP 侧包含两个更新对象：

- PS 端可执行文件：`run`
- PL 端程序：`design_1_wrapper.bit.bin`

本设计目标是建立一个自动升级机制：当更新压缩包放入指定更新目录后，由 systemd 触发独立 updater 执行更新。当前 GUI 项目不执行替换自身源码、远程 mount、远程 reboot 等升级动作，只暴露版本和更新状态给界面显示。

## 2. 已确认决策

- 升级执行逻辑放在独立 Python updater 中，不放进 `voc_app` 核心 GUI/采集逻辑。
- updater 固定部署在树莓派的稳定目录中，不随业务 release 切换。
- 上位机仍按源码方式运行，不做 wheel 或可执行文件打包。
- 上位机使用 release 目录加 `current` 软链接，不直接剪切覆盖当前源码目录。
- 更新包中的 Loadport 和 FOUP 各自带 manifest。
- FOUP 版本查询使用现有 TCP 长度前缀协议，发送 `get_version`。
- FOUP `get_version` 返回 PS/PL 两个版本。
- FOUP mount、文件传输、sync、reboot 使用 SSH/SCP。
- 检测到更新包后自动执行升级，不等待人工确认。
- UI 标题栏只显示 Loadport 版本和更新状态，不显示 FOUP PS/PL 版本。
- WSL2 仅作为开发与单元测试环境，不执行真实 `systemctl`、`mount`、`reboot`。

## 3. 现场环境观察

通过 SSH 连接真实树莓派 `kasp@192.168.1.233` 做过只读检查，得到以下事实：

- 主机名：`KaspPi`
- 登录用户：`kasp`
- 当前项目路径：`/home/kasp/Project/voc_project/VOC_Project`
- 当前 Python 环境：`/home/kasp/Project/voc_project/.venv/bin/python`
- 当前 GUI 进程命令：

```text
/home/kasp/Project/voc_project/.venv/bin/python /home/kasp/Project/voc_project/VOC_Project/src/voc_app/gui/app.py
```

- 当前 GUI 进程处于用户图形会话 `session-1.scope`，未发现现成的 `voc-gui.service`、`loadport`、`foup` 相关 systemd 单元。
- 用户补充：当前 VOC 自动启动依赖 autostart 目录下的 `.desktop` 文件。

因此本设计建议新增 `systemd --user` 服务管理 GUI，同时保留 autostart 作为图形会话启动入口。关键约束是：不能让 `.desktop` 和 systemd 同时直接启动 Python GUI，否则会产生两个 VOC 进程。推荐做法是把 `.desktop` 的 `Exec` 改为启动 `voc-gui.service`，让 systemd 统一负责 GUI 的 stop/start/status。

## 4. 总体架构

下面的目录结构是**上线部署树**，不是本地 Git checkout 的原始目录；当前代码仓库的开发目录与部署目录可以分离。

```text
/home/kasp/Project/voc_project/
  updater/                         # 固定升级器，不随业务 release 切换
  updates/                         # systemd.path 监听目录
  releases/
    loadport-1.2.2/
    loadport-1.2.3/
  current -> releases/loadport-1.2.3
  state/
    update_status.json             # GUI 读取的简化状态
    update.log                     # updater 写入的详细日志
  .venv/                           # Python 运行环境
```

GUI 服务固定从 `current` 启动：

```bash
cd /home/kasp/Project/voc_project/current
/home/kasp/Project/voc_project/.venv/bin/python -m voc_app.gui.app
```

updater 固定从独立目录启动：

```bash
/home/kasp/Project/voc_project/.venv/bin/python /home/kasp/Project/voc_project/updater/update.py
```

图解：

```text
updates/*.tar.gz
      |
      v
systemd --user voc-updater.path
      |
      v
voc-updater.service
      |
      v
independent updater
      |
      +--> LoadportInstaller: stop GUI -> install release -> switch current -> start GUI
      |
      +--> FoupInstaller: TCP get_version -> SSH mount -> SCP files -> sync -> reboot
      |
      +--> UpdateStateWriter: update_status.json + update.log
```

这张图回答的是：更新包进入目录后，哪些组件参与升级以及各自边界是什么。GUI 只读取状态文件；真正升级动作都在独立 updater 中。

## 5. 升级包结构

升级包使用 `.tar.gz`，根目录固定包含 `loadport/` 和 `foup/`：

```text
voc-update-1.2.3.tar.gz
  loadport/
    manifest.json
    app/
      pyproject.toml
      src/
      tests/
      docs/
      uv.lock
  foup/
    manifest.json
    ps/
      run
    pl/
      design_1_wrapper.bit.bin
```

`loadport/manifest.json`：

```json
{
  "component": "loadport",
  "version": "1.2.3",
  "entrypoint": "python -m voc_app.gui.app",
  "python": ">=3.11",
  "created_at": "2026-05-09T00:00:00+08:00",
  "sha256": {}
}
```

`foup/manifest.json`：

```json
{
  "component": "foup",
  "ps_version": "2.0.1",
  "pl_version": "2026.05.09",
  "ps_file": "ps/run",
  "pl_file": "pl/design_1_wrapper.bit.bin",
  "remote_mount_device": "/dev/mmcblk1p1",
  "remote_mount_point": "/tmp",
  "sha256": {}
}
```

`sha256` 第一版预留并允许为空。updater 必须先做结构校验；当 manifest 提供哈希值时，必须校验匹配后才执行升级。

## 6. 版本判定

Loadport 当前版本来源：

- 优先读取当前 release 内的 `loadport/manifest.json` 或项目内版本文件。
- 如果当前 release 尚未规范化，允许第一版从配置文件或 `pyproject.toml` 读取，但后续应统一为 release manifest。

FOUP 当前版本来源：

- updater 使用 TCP 长度前缀协议连接 FOUP。
- 发送命令：

```text
get_version
```

- FOUP 返回 JSON：

```json
{"ps_version":"2.0.1","pl_version":"2026.05.09"}
```

判定规则：

- 当前 Loadport 版本不同于 `loadport.version`：升级上位机。
- 当前 FOUP `ps_version` 不同于 `foup.ps_version`：替换 `run`。
- 当前 FOUP `pl_version` 不同于 `foup.pl_version`：替换 `design_1_wrapper.bit.bin`。
- 三者都匹配：记录 `skipped`，不重启 GUI，不重启 FOUP。

## 7. Autostart 与 Systemd 设计

当前现场已经使用 autostart 目录中的 `.desktop` 文件自动启动 VOC。为了兼容现有启动方式并让 updater 可以稳定停启 GUI，本设计采用：

```text
desktop autostart
  -> systemctl --user start voc-gui.service
      -> python -m voc_app.gui.app
```

也就是说，autostart 只负责在用户图形会话起来后触发 systemd 用户服务；真正的 GUI 进程由 `voc-gui.service` 持有。updater 只和 systemd 交互，不直接 kill `.desktop` 启动出的 Python 进程。

禁止同时保留下面两条直接启动路径：

```text
autostart .desktop -> python app.py
systemd --user voc-gui.service -> python -m voc_app.gui.app
```

否则开机后可能出现重复 GUI 进程、端口占用、串口/GPIO 资源冲突和升级时停错进程。

### 7.1 GUI 用户服务

建议新增用户级服务 `voc-gui.service`，路径：

```text
/home/kasp/.config/systemd/user/voc-gui.service
```

示意内容：

```ini
[Unit]
Description=VOC Loadport GUI
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=/home/kasp/Project/voc_project/current
ExecStart=/home/kasp/Project/voc_project/.venv/bin/python -m voc_app.gui.app
Restart=on-failure
RestartSec=3
Environment=QT_QPA_PLATFORM=wayland

[Install]
WantedBy=default.target
```

如果现场图形环境需要 `DISPLAY`、`XDG_RUNTIME_DIR` 或其他 Wayland/X11 变量，应在实际部署前从当前会话补齐。服务化的目标是让 updater 可以稳定执行：

```bash
systemctl --user stop voc-gui.service
systemctl --user start voc-gui.service
systemctl --user is-active voc-gui.service
```

### 7.2 Autostart `.desktop`

保留现有 autostart 机制时，`.desktop` 不再直接运行 Python，而是触发 systemd 用户服务。

示意内容：

```ini
[Desktop Entry]
Type=Application
Name=VOC Loadport GUI
Exec=systemctl --user start voc-gui.service
X-GNOME-Autostart-enabled=true
Terminal=false
```

如果某些桌面环境不能稳定执行 `systemctl --user`，可以退回到只使用 `.desktop` 直接启动 GUI，但 updater 就必须额外实现“查找并停止现有 Python 进程”的逻辑。该退路不作为推荐方案。

### 7.3 Updater 用户服务

建议新增：

```text
/home/kasp/.config/systemd/user/voc-updater.path
/home/kasp/.config/systemd/user/voc-updater.service
```

`voc-updater.path`：

```ini
[Unit]
Description=Watch VOC update packages

[Path]
PathExistsGlob=/home/kasp/Project/voc_project/updates/*.tar.gz

[Install]
WantedBy=default.target
```

`voc-updater.service`：

```ini
[Unit]
Description=Run VOC updater

[Service]
Type=oneshot
WorkingDirectory=/home/kasp/Project/voc_project/updater
ExecStart=/home/kasp/Project/voc_project/.venv/bin/python /home/kasp/Project/voc_project/updater/update.py --config /home/kasp/Project/voc_project/updater/config.yaml
```

updater 每次只处理一个包。处理成功后移动到 `updates/processed/`，处理失败后移动到 `updates/failed/`，避免坏包反复触发。

## 8. Updater 配置

配置文件：

```text
/home/kasp/Project/voc_project/updater/config.yaml
```

建议内容：

```yaml
paths:
  base_dir: /home/kasp/Project/voc_project
  updates_dir: /home/kasp/Project/voc_project/updates
  work_dir: /home/kasp/Project/voc_project/work
  releases_dir: /home/kasp/Project/voc_project/releases
  current_link: /home/kasp/Project/voc_project/current
  state_file: /home/kasp/Project/voc_project/state/update_status.json
  log_file: /home/kasp/Project/voc_project/state/update.log

services:
  gui_service: voc-gui.service
  systemctl_scope: user

python:
  executable: /home/kasp/Project/voc_project/.venv/bin/python

foup:
  host: 192.168.1.50
  port: 65432
  ssh_user: root
  ssh_key: /home/kasp/Project/voc_project/updater/id_rsa
  remote_mount_device: /dev/mmcblk1p1
  remote_mount_point: /tmp
  remote_run_path: /tmp/run
  remote_pl_path: /tmp/design_1_wrapper.bit.bin
```

FOUP 的真实 IP、SSH 用户和密钥路径以后按现场网络配置修正。设计上 updater 不依赖 WSL2 开发机的 SSH 配置。

## 9. Loadport 升级流程

```text
validate package
  -> compare loadport version
  -> stop voc-gui.service
  -> copy loadport/app to releases/loadport-<version>
  -> switch current symlink atomically
  -> start voc-gui.service
  -> check service active
```

详细步骤：

1. 解压升级包到 `work/<package-id>/`。
2. 校验 `loadport/manifest.json` 和 `loadport/app/src/voc_app/gui/app.py` 存在。
3. 读取目标版本，计算 release 目录 `releases/loadport-<version>/`。
4. 如果版本相同，跳过 Loadport 升级。
5. 如果版本不同，记录旧 `current` 指向。
6. 停止 `voc-gui.service`。
7. 安装新 release 到临时目录，再原子 rename 到目标 release 目录。
8. 原子切换 `current` 软链接。
9. 启动 `voc-gui.service`。
10. 检查服务是否 active。
11. 如果启动失败，切回旧 release 并重启服务，状态写 `rollback`。

保留策略：

- 默认保留最近 3 个 release。
- 不删除 `current` 指向的 release。
- 不删除刚回滚使用的旧 release。

## 10. FOUP 升级流程

```text
TCP get_version
  -> compare ps/pl version
  -> ssh mount /dev/mmcblk1p1 /tmp
  -> scp selected files
  -> ssh sync
  -> ssh reboot
```

详细规则：

- PS 版本不同：上传 `run` 到 `/tmp/run`。
- PL 版本不同：上传 `design_1_wrapper.bit.bin` 到 `/tmp/design_1_wrapper.bit.bin`。
- 两者都不同：两个文件都上传。
- 两者都相同：跳过 FOUP 升级。

失败处理：

- `get_version` 失败：FOUP 升级失败，记录日志。已完成的 Loadport 升级不强制回滚。
- `mount` 失败：不上传文件，不 reboot。
- `scp` 失败：停止后续 FOUP 步骤，不 reboot。
- `sync` 失败：停止并记录失败，不主动 reboot。
- `reboot` 失败：记录失败，标记需要人工检查。

## 11. 状态文件与 UI 显示

GUI 只读取简化状态文件：

```text
/home/kasp/Project/voc_project/state/update_status.json
```

格式：

```json
{
  "loadport_version": "1.2.3",
  "update_state": "succeeded",
  "update_message": "Update completed"
}
```

`update_state` 枚举：

```text
idle
running
succeeded
failed
skipped
rollback
```

标题栏显示：

```text
Loadport v1.2.3 | Update: succeeded
```

详细过程不展示在 UI 上，写入：

```text
/home/kasp/Project/voc_project/state/update.log
```

当前项目需要新增的能力很小：

- 一个 Loadport 版本读取对象或函数。
- 一个 `UpdateStatusController`，定时读取 `update_status.json`。
- `TitlePanel.qml` 增加版本和更新状态显示。

## 12. Updater 模块划分

建议独立 updater 内部拆为：

- `UpdatePackageReader`
  - 解包、读 manifest、校验文件结构和 SHA256。
- `VersionResolver`
  - 读取当前 Loadport 版本。
  - 通过 TCP `get_version` 读取 FOUP PS/PL 版本。
- `LoadportInstaller`
  - 停/启 GUI 服务。
  - 安装 release。
  - 切换 `current`。
  - 回滚。
- `FoupInstaller`
  - SSH mount。
  - SCP 上传。
  - sync。
  - reboot。
- `UpdateStateWriter`
  - 写 `update_status.json`。
  - 写 `update.log`。

这些模块通过显式配置和返回值协作，不直接依赖 GUI 进程内部对象。

## 13. WSL2 开发与验证策略

WSL2 中只执行无危险动作的验证：

- 升级包结构校验。
- manifest 解析。
- 版本比较。
- `current` 软链接切换与回滚。
- 状态文件写入。
- TCP `get_version` 解析。
- SSH/SCP 层用 mock。
- systemd 调用用 mock。

WSL2 中不执行：

- 真实 `systemctl --user stop/start`。
- 真实 `mount /dev/mmcblk1p1 /tmp`。
- 真实 `reboot`。
- 对真实 FOUP 开发板写文件。

树莓派 `kasp@192.168.1.233` 可以用于部署前验证：

- 创建目录结构。
- 配置 `systemd --user` 服务。
- 验证 GUI 可以由 `voc-gui.service` 启停。
- 验证 updater 能发现测试包。
- 使用 dry-run 模式验证升级计划。

## 14. 第一阶段交付范围

第一阶段建议交付：

- 当前项目：
  - Loadport 版本读取。
  - 更新状态读取。
  - 标题栏显示 `Loadport vX | Update: state`。
  - 对应单元测试或 QML 文本检查。
- 独立 updater：
  - 配置读取。
  - 包结构和 manifest 校验。
  - 版本比较。
  - Loadport release 安装和回滚。
  - FOUP `get_version` TCP 查询。
  - SSH/SCP 执行层接口和 mock 测试。
  - 状态文件和日志写入。
- systemd：
  - `voc-gui.service`
  - autostart `.desktop` 改为触发 `voc-gui.service`
  - `voc-updater.path`
  - `voc-updater.service`

不在第一阶段做：

- UI 手动确认升级。
- UI 展示 FOUP PS/PL 版本。
- 增量补丁升级。
- 多 FOUP 设备批量升级。
- 网络断点续传。

## 15. 主要风险与应对

- GUI 当前由 autostart `.desktop` 在用户图形会话中启动，环境变量可能依赖当前桌面会话。
  - 应对：保留 `.desktop` 作为图形会话入口，但改为触发 `systemctl --user start voc-gui.service`，再在真实树莓派上验证 `systemd --user` 启停。
- `.desktop` 和 systemd 如果同时直接启动 Python，会产生重复 GUI 进程。
  - 应对：迁移时必须先确认 `.desktop` 的 `Exec` 不再直接运行 Python。
- updater 切换的是正在运行程序的源码目录。
  - 应对：不覆盖 `current` 目录，使用 release 目录和软链接切换。
- FOUP 文件替换后 reboot 失败或版本查询失败。
  - 应对：详细日志记录，FOUP 失败不强制回滚 Loadport。
- 现场权限不足导致 mount/scp/reboot 失败。
  - 应对：FOUP SSH 用户和 sudo/root 策略在配置中显式声明，部署前 dry-run 检查。
- 坏包反复触发。
  - 应对：失败包移动到 `updates/failed/`。

## 16. 待实现前置条件

- 确认树莓派上的最终 base 目录，当前建议沿用 `/home/kasp/Project/voc_project`。
- 将当前 autostart `.desktop` 直启 GUI 的方式改为触发 `systemd --user` 服务。
- 确认 FOUP 开发板真实 IP、SSH 用户、认证方式。
- 确认 FOUP TCP 服务实现 `get_version` 并返回约定 JSON。
- 确认 FOUP 上 `/dev/mmcblk1p1` 可挂载到 `/tmp`，且目标文件名固定为 `run` 和 `design_1_wrapper.bit.bin`。
