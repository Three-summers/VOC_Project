# 真实主机升级验证

用于在没有 PySide6 / 没有 FOUP 的 Ubuntu 主机上，用**真实 systemd --user**
验证升级器的事务行为。验证结果见
[`docs/reviews/evidence/2026-09-29/host-upgrade-verification.txt`](../../docs/reviews/evidence/2026-09-29/host-upgrade-verification.txt)。

覆盖项：

| 编号 | 验证点 |
| --- | --- |
| R13 | 服务 `WorkingDirectory=current` + `PYTHONPATH=current/src`，导入的 `voc_app` 来自当前 release；安装器校验 MainPID 的 `/proc/<pid>/cwd` 属于目标 release |
| R14 | 确认阶段失败（进程 cwd 不属于目标 release）时回滚到旧版本 |
| R27 | 用真实 `systemctl` 停止/启动，并确认 MainPID 变化（服务确实重启） |
| R29 | 回滚后状态文件记录实际运行版本，目标版本单独放在 `loadport_target_version` |
| R30 | 失败的升级尝试写入 `update_state=failed`，不会停留在 running |

## 复现步骤

在一台可 `systemctl --user` 的 Ubuntu 主机上（验证会重建 `$BASE` 下的
releases/work/updates/state，务必用专用目录）：

```bash
BASE="${VOC_VERIFY_BASE:-$HOME/Project/voc_project}"
mkdir -p "$BASE/updater"
scp -r tools/updater/voc_updater "$HOST:$BASE/updater/"
scp tools/host_upgrade_verification/host_driver.py "$HOST:$BASE/updater/"
ssh "$HOST" 'bash -s' < tools/host_upgrade_verification/run_host_verification.sh
```

脚本使用桩 FOUP 客户端（版本与包内一致），因此不会触发固件升级；Loadport
安装器、包解析器和状态写入均为真实实现。
