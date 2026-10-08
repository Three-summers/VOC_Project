#!/usr/bin/env bash
# 在真实 Ubuntu 主机上验证升级相关修复（R13/R14/R27/R29/R30）。
# 只依赖 python3 与 systemd --user，不需要 PySide6。
#
# 前提（由调用方完成）：
#   $BASE/updater/voc_updater/    = 仓库 tools/updater/voc_updater
#   $BASE/updater/host_driver.py  = 本目录 host_driver.py
#
# 注意：脚本会重建 $BASE 下的 releases/work/updates/state 目录，请使用专用
# 验证目录（默认 $HOME/Project/voc_project），不要指向真实部署目录。
set -euo pipefail

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ -S "$XDG_RUNTIME_DIR/bus" ]; then
  export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
fi
BASE="${VOC_VERIFY_BASE:-$HOME/Project/voc_project}"
STATE="$BASE/state"
UNIT="$HOME/.config/systemd/user/voc-gui.service"

mkdir -p "$BASE"
# 保留已上传的 updater/，只重建验证使用的目录
rm -rf "$BASE/releases" "$BASE/work" "$BASE/updates" "$STATE" "$BASE/run_stub"
mkdir -p "$BASE/releases" "$BASE/work" "$BASE/updates" "$STATE" "$BASE/run_stub"

write_app() {
  local dst="$1" ver="$2"
  mkdir -p "$dst/src/voc_app/gui"
  : > "$dst/src/voc_app/__init__.py"
  : > "$dst/src/voc_app/gui/__init__.py"
  cat > "$dst/src/voc_app/gui/app.py" <<PYEOF
import os

import time

import voc_app

marker = os.path.join(os.environ.get("VOC_STATE_DIR", r"$STATE"), "run-$ver.txt")
with open(marker, "w", encoding="utf-8") as handle:
    handle.write(voc_app.__file__ + "\n" + str(os.getpid()) + "\n")
time.sleep(3600)
PYEOF
}

make_release() {
  local ver="$1"
  local rel="$BASE/releases/loadport-$ver"
  rm -rf "$rel"
  mkdir -p "$rel/loadport"
  write_app "$rel" "$ver"
  printf '{"component": "loadport", "version": "%s"}\n' "$ver" \
    > "$rel/loadport/manifest.json"
}

build_package() {
  local ver="$1"
  local pkg="$BASE/work/pkg-$ver"
  rm -rf "$pkg"
  mkdir -p "$pkg/loadport" "$pkg/foup/ps" "$pkg/foup/pl"
  write_app "$pkg/loadport/app" "$ver"
  printf '{"component": "loadport", "version": "%s"}\n' "$ver" \
    > "$pkg/loadport/manifest.json"
  printf 'run' > "$pkg/foup/ps/run"
  printf 'bit' > "$pkg/foup/pl/design_1_wrapper.bit.bin"
  printf '{"component": "foup", "ps_version": "9.9.9", "pl_version": "9.9.9", "ps_file": "ps/run", "pl_file": "pl/design_1_wrapper.bit.bin"}\n' \
    > "$pkg/foup/manifest.json"
  tar -C "$pkg" -czf "$BASE/updates/voc-update-$ver.tar.gz" .
}

write_unit() {
  local workdir="$1"
  cat > "$UNIT" <<EOF
[Unit]
Description=VOC Loadport GUI (upgrade verification)
After=default.target

[Service]
Type=simple
WorkingDirectory=$workdir
Environment=PYTHONPATH=$BASE/current/src
Environment=VOC_STATE_DIR=$STATE
ExecStart=/usr/bin/python3 -m voc_app.gui.app
Restart=no
TimeoutStopSec=5

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
}

make_release 1.0.0
ln -sfn "$BASE/releases/loadport-1.0.0" "$BASE/current"
mkdir -p "$HOME/.config/systemd/user"
write_unit "$BASE/current"
systemctl --user stop voc-gui.service >/dev/null 2>&1 || true
systemctl --user start voc-gui.service
sleep 1.5

PID=$(systemctl --user show -p MainPID --value voc-gui.service)
echo "== baseline 1.0.0 =="
echo "is-active: $(systemctl --user is-active voc-gui.service)"
echo "MainPID:   $PID"
echo "proc cwd:  $(readlink -f "/proc/$PID/cwd")"
echo "module:    $(head -n1 "$STATE/run-1.0.0.txt")"

echo
echo "== R13: PYTHONPATH 决定实际加载的 release =="
( cd /tmp && PYTHONPATH="$BASE/current/src" /usr/bin/python3 -c 'import voc_app; print(voc_app.__file__)' )

echo
echo "== 升级到 2.0.0（真实 systemctl + 事务确认）=="
build_package 2.0.0
OLD_PID=$PID
/usr/bin/python3 "$BASE/updater/host_driver.py" "$BASE" 2.0.0 success
NEW_PID=$(systemctl --user show -p MainPID --value voc-gui.service)
echo "current -> $(readlink -f "$BASE/current")"
echo "is-active: $(systemctl --user is-active voc-gui.service)"
echo "MainPID:   $OLD_PID -> $NEW_PID"
echo "proc cwd:  $(readlink -f "/proc/$NEW_PID/cwd")"
echo "module:    $(head -n1 "$STATE/run-2.0.0.txt")"
echo "state:     $(cat "$STATE/update_status.json")"

echo
echo "== R14+R13: 进程 cwd 不属于目标 release 时必须回滚 =="
# 让服务的工作目录不再是 current：启动进程的 cwd 与目标 release 不一致，
# 安装器的事务确认必须发现并回滚到 2.0.0（而不是把 3.0.0 记成成功）。
write_unit "$BASE/run_stub"
build_package 3.0.0
/usr/bin/python3 "$BASE/updater/host_driver.py" "$BASE" 3.0.0 failure
echo "current -> $(readlink -f "$BASE/current")"
echo "is-active: $(systemctl --user is-active voc-gui.service)"
echo "module:    $(head -n1 "$STATE/run-2.0.0.txt")"
echo "state:     $(cat "$STATE/update_status.json")"

echo
echo "== 恢复正确 unit 并确认 2.0.0 仍可正常启动 =="
write_unit "$BASE/current"
systemctl --user stop voc-gui.service >/dev/null 2>&1 || true
systemctl --user start voc-gui.service
sleep 1
PID=$(systemctl --user show -p MainPID --value voc-gui.service)
echo "is-active: $(systemctl --user is-active voc-gui.service)"
echo "proc cwd:  $(readlink -f "/proc/$PID/cwd")"

systemctl --user stop voc-gui.service >/dev/null 2>&1 || true
echo "HOST-VERIFY-DONE"
