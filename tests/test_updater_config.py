import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.config import load_config
from voc_updater.state import UpdateStateWriter


def test_load_config_reads_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
paths:
  base_dir: /opt/voc
  updates_dir: /opt/voc/updates
  work_dir: /opt/voc/work
  releases_dir: /opt/voc/releases
  current_link: /opt/voc/current
  state_file: /opt/voc/state/update_status.json
  log_file: /opt/voc/state/update.log
services:
  gui_service: voc-gui.service
  systemctl_scope: user
python:
  executable: /opt/voc/.venv/bin/python
foup:
  host: 192.168.1.50
  port: 65432
  ssh_user: root
  ssh_key: /opt/voc/updater/id_rsa
  remote_mount_device: /dev/mmcblk1p1
  remote_mount_point: /tmp
  remote_run_path: /tmp/run
  remote_pl_path: /tmp/design_1_wrapper.bit.bin
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert str(config.paths.base_dir) == "/opt/voc"
    assert config.services.gui_service == "voc-gui.service"
    assert config.services.systemctl_scope == "user"
    assert config.foup.port == 65432
    assert str(config.foup.remote_run_path) == "/tmp/run"


def test_state_writer_writes_compact_status_and_log(tmp_path: Path) -> None:
    state_file = tmp_path / "state" / "update_status.json"
    log_file = tmp_path / "state" / "update.log"
    writer = UpdateStateWriter(state_file=state_file, log_file=log_file)

    writer.write_status("1.2.3", "running", "Installing")
    writer.log("message one")

    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data == {
        "loadport_version": "1.2.3",
        "update_state": "running",
        "update_message": "Installing",
    }
    assert "message one" in log_file.read_text(encoding="utf-8")
