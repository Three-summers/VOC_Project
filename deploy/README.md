# 部署脚手架

现场路径**只填一次**：`deploy/install.sh` 的 `VOC_BASE`。所有 systemd 单元与
updater 配置都是模板，占位符由脚本统一渲染，不需要逐个文件改路径。

## 目录

```text
deploy/
├── install.sh                       # 渲染并安装单元/配置；路径的唯一入口是 VOC_BASE
├── systemd/user/
│   ├── voc-gui.service.in           # 含 @VOC_BASE@ / @VOC_PYTHON@ / @QT_QPA_PLATFORM@
│   ├── voc-updater.service.in
│   └── voc-updater.path.in
├── autostart/voc-gui.desktop        # 只触发 systemctl --user start voc-gui.service
└── updater/config.yaml.example      # 升级器配置模板，供 install.sh 渲染或手工替换
```

## 用法

```bash
# 方式一：位置参数
deploy/install.sh /home/kasp/Project/voc_project

# 方式二：环境变量（可同时改 python、平台插件、FOUP 参数）
VOC_BASE=/opt/voc QT_QPA_PLATFORM=xcb deploy/install.sh
```

脚本会：

1. 建目录 `$VOC_BASE/{updater,updates,releases,state,work}`；
2. 把 `systemd/user/*.in` 渲染到 `~/.config/systemd/user/`（可用 `VOC_SYSTEMD_USER_DIR` 改）；
3. 安装 autostart 到 `~/.config/autostart/`（可用 `VOC_AUTOSTART_DIR` 改）；
4. 用 `updater/config.yaml.example` 生成 `$VOC_BASE/updater/config.yaml`（已存在则保留，`--force-config` 覆盖）；
5. 若 `$VOC_BASE/updater` 里没有升级器，从仓库 `tools/updater/` 复制 `update.py` 与 `voc_updater/`；
6. `systemctl --user daemon-reload`（可用时）。

脚本**不做**：建 venv、装 Python 依赖、安装首个 release、启动服务；它会把这些打印成
“后续步骤”。

## 可配置项

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VOC_BASE` | `$HOME/Project/voc_project` | 部署根；其余路径都从它派生 |
| `VOC_PYTHON` | `$VOC_BASE/.venv/bin/python` | 运行 GUI 与升级器的解释器 |
| `QT_QPA_PLATFORM` | `wayland` | X11 现场改为 `xcb` |
| `VOC_SYSTEMD_USER_DIR` | `$HOME/.config/systemd/user` | 用户单元目录 |
| `VOC_AUTOSTART_DIR` | `$HOME/.config/autostart` | 自启动目录 |
| `FOUP_HOST` / `FOUP_PORT` / `FOUP_SSH_USER` / `FOUP_SSH_KEY` | `192.168.1.50` / `65432` / `root` / `$VOC_BASE/updater/id_rsa` | FOUP 连接 |
| `FOUP_MOUNT_DEVICE` / `FOUP_MOUNT_POINT` / `FOUP_RUN_PATH` / `FOUP_PL_PATH` | `/dev/mmcblk1p1` / `/tmp` / `/tmp/run` / `/tmp/design_1_wrapper.bit.bin` | FOUP 固件替换目标 |

## 单元模板里的占位符

改动部署布局时只需要同步 `install.sh` 的 `RENDER_PAIRS` 与模板；`install.sh` 会拒绝
渲染仍有未替换占位符的模板。

```text
@VOC_BASE@        部署根
@VOC_PYTHON@      python 解释器
@QT_QPA_PLATFORM@ GUI 平台插件
@FOUP_*@          config.yaml 的 FOUP 段
```
