#!/usr/bin/env bash
# VOC 部署脚手架：把现场路径集中成一处（VOC_BASE），由本脚本渲染
# systemd 单元与 updater 配置，避免逐个文件改路径。
#
# 用法:
#   deploy/install.sh [BASE]
#   VOC_BASE=/custom/base deploy/install.sh
#
# 环境变量（都有默认值）:
#   VOC_BASE              部署根，默认 $HOME/Project/voc_project
#   VOC_PYTHON            运行 GUI/updater 的 python，默认 $VOC_BASE/.venv/bin/python
#   QT_QPA_PLATFORM       GUI 平台插件，默认 wayland（X11 现场改为 xcb）
#   VOC_SYSTEMD_USER_DIR  用户单元目录，默认 $HOME/.config/systemd/user
#   VOC_AUTOSTART_DIR     自启动目录，默认 $HOME/.config/autostart
#   FOUP_HOST/FOUP_PORT/FOUP_SSH_USER/FOUP_SSH_KEY/FOUP_MOUNT_DEVICE/
#   FOUP_MOUNT_POINT/FOUP_RUN_PATH/FOUP_PL_PATH
#                         updater/config.yaml 的 FOUP 段（默认见下）
#
# 选项:
#   --force-config   已存在 updater/config.yaml 时也覆盖（默认保留现场配置）
#   -h, --help       显示本帮助
#
# 本脚本只做部署脚手架：建目录、渲染并安装单元/自启动项、生成 config.yaml、
# 必要时从仓库复制升级器。它不创建 venv、不安装 Python 依赖、不安装首个
# release、不启动服务；这些会打印在最后的“后续步骤”里。
#
# 幂等：可重复执行；默认不覆盖已有 config.yaml，也不覆盖已有升级器文件。

set -euo pipefail

usage() {
  cat <<'EOF'
VOC 部署脚手架：把现场路径集中成一处（VOC_BASE）后渲染 systemd 单元与 updater 配置。

用法:
  deploy/install.sh [BASE]
  VOC_BASE=/custom/base deploy/install.sh

环境变量:
  VOC_BASE              部署根，默认 $HOME/Project/voc_project
  VOC_PYTHON            运行 GUI/updater 的 python，默认 $VOC_BASE/.venv/bin/python
  QT_QPA_PLATFORM       GUI 平台插件，默认 wayland（X11 现场改为 xcb）
  VOC_SYSTEMD_USER_DIR  用户单元目录，默认 $HOME/.config/systemd/user
  VOC_AUTOSTART_DIR     自启动目录，默认 $HOME/.config/autostart
  FOUP_*                updater/config.yaml 的 FOUP 段（见脚本默认值）
选项:
  --force-config        覆盖已存在的 updater/config.yaml
  -h, --help            显示本帮助
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FORCE_CONFIG=0
POSITIONAL_BASE=""
for arg in "$@"; do
  case "$arg" in
    --force-config) FORCE_CONFIG=1 ;;
    -h|--help) usage; exit 0 ;;
    --*) echo "未知参数: $arg" >&2; usage >&2; exit 2 ;;
    *) POSITIONAL_BASE="$arg" ;;
  esac
done

VOC_BASE="${VOC_BASE:-${POSITIONAL_BASE:-$HOME/Project/voc_project}}"
VOC_PYTHON="${VOC_PYTHON:-$VOC_BASE/.venv/bin/python}"
QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland}"
VOC_SYSTEMD_USER_DIR="${VOC_SYSTEMD_USER_DIR:-$HOME/.config/systemd/user}"
VOC_AUTOSTART_DIR="${VOC_AUTOSTART_DIR:-$HOME/.config/autostart}"

FOUP_HOST="${FOUP_HOST:-192.168.1.50}"
FOUP_PORT="${FOUP_PORT:-65432}"
FOUP_SSH_USER="${FOUP_SSH_USER:-root}"
FOUP_SSH_KEY="${FOUP_SSH_KEY:-$VOC_BASE/updater/id_rsa}"
FOUP_MOUNT_DEVICE="${FOUP_MOUNT_DEVICE:-/dev/mmcblk1p1}"
FOUP_MOUNT_POINT="${FOUP_MOUNT_POINT:-/tmp}"
FOUP_RUN_PATH="${FOUP_RUN_PATH:-/tmp/run}"
FOUP_PL_PATH="${FOUP_PL_PATH:-/tmp/design_1_wrapper.bit.bin}"

# 渲染用的键值对：@KEY@ -> value。只在这里维护占位符。
RENDER_PAIRS=(
  "VOC_BASE=$VOC_BASE"
  "VOC_PYTHON=$VOC_PYTHON"
  "QT_QPA_PLATFORM=$QT_QPA_PLATFORM"
  "FOUP_HOST=$FOUP_HOST"
  "FOUP_PORT=$FOUP_PORT"
  "FOUP_SSH_USER=$FOUP_SSH_USER"
  "FOUP_SSH_KEY=$FOUP_SSH_KEY"
  "FOUP_MOUNT_DEVICE=$FOUP_MOUNT_DEVICE"
  "FOUP_MOUNT_POINT=$FOUP_MOUNT_POINT"
  "FOUP_RUN_PATH=$FOUP_RUN_PATH"
  "FOUP_PL_PATH=$FOUP_PL_PATH"
)

render() {
  # render <template> <target>；用 python3 做纯文本替换，避免 sed 转义问题。
  python3 - "$1" "$2" "${RENDER_PAIRS[@]}" <<'PY'
import re
import sys

template, target = sys.argv[1], sys.argv[2]
text = open(template, encoding="utf-8").read()
keys = []
for pair in sys.argv[3:]:
    key, _, value = pair.partition("=")
    keys.append(key)
    text = text.replace(f"@{key}@", value)
leftover = [key for key in keys if f"@{key}@" in text]
unknown = sorted(set(re.findall(r"@[A-Z_]+@", text)))
if leftover or unknown:
    raise SystemExit(f"模板 {template} 仍有未替换的占位符: {leftover + unknown}")
with open(target, "w", encoding="utf-8") as handle:
    handle.write(text)
PY
}

echo "== VOC 部署脚手架 =="
echo "部署根:       $VOC_BASE"
echo "python:       $VOC_PYTHON"
echo "systemd 单元: $VOC_SYSTEMD_USER_DIR"
echo

mkdir -p \
  "$VOC_BASE/updater" "$VOC_BASE/updates" "$VOC_BASE/releases" \
  "$VOC_BASE/state" "$VOC_BASE/work" \
  "$VOC_SYSTEMD_USER_DIR" "$VOC_AUTOSTART_DIR"
echo "已创建部署目录: $VOC_BASE/{updater,updates,releases,state,work}"

for template in "$SCRIPT_DIR"/systemd/user/*.in; do
  target="$VOC_SYSTEMD_USER_DIR/$(basename "${template%.in}")"
  render "$template" "$target"
  echo "已渲染单元: $target"
done

cp "$SCRIPT_DIR/autostart/voc-gui.desktop" "$VOC_AUTOSTART_DIR/voc-gui.desktop"
echo "已安装自启动项: $VOC_AUTOSTART_DIR/voc-gui.desktop"

CONFIG_PATH="$VOC_BASE/updater/config.yaml"
if [ -e "$CONFIG_PATH" ] && [ "$FORCE_CONFIG" -ne 1 ]; then
  echo "已存在，保留现场配置: $CONFIG_PATH（需覆盖请加 --force-config）"
else
  render "$SCRIPT_DIR/updater/config.yaml.example" "$CONFIG_PATH"
  echo "已生成配置: $CONFIG_PATH"
fi

if [ -d "$REPO_ROOT/tools/updater/voc_updater" ]; then
  if [ ! -f "$VOC_BASE/updater/update.py" ]; then
    cp "$REPO_ROOT/tools/updater/update.py" "$VOC_BASE/updater/update.py"
    echo "已复制: $VOC_BASE/updater/update.py"
  fi
  if [ ! -d "$VOC_BASE/updater/voc_updater" ]; then
    cp -r "$REPO_ROOT/tools/updater/voc_updater" "$VOC_BASE/updater/voc_updater"
    echo "已复制: $VOC_BASE/updater/voc_updater"
  fi
fi

if command -v systemctl >/dev/null 2>&1; then
  if systemctl --user daemon-reload 2>/dev/null; then
    echo "已执行: systemctl --user daemon-reload"
  else
    echo "提示: systemctl --user 当前不可用，请登录图形会话后执行 daemon-reload"
  fi
fi

cat <<EOF

后续步骤（脚本不代做）：
  1) 建 venv 并装依赖（树莓派再加 RPi.GPIO）:
       python3 -m venv "$VOC_BASE/.venv"
       "$VOC_BASE/.venv/bin/pip" install PySide6 numpy pyserial PyYAML RPi.GPIO
  2) 放入首个 release（或直接把升级包放进 updates/ 由升级器安装）:
       ln -sfn "$VOC_BASE/releases/loadport-<version>" "$VOC_BASE/current"
  3) 启用并启动:
       systemctl --user enable --now voc-updater.path
       systemctl --user start voc-gui.service
       systemctl --user is-active voc-gui.service
EOF
