import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.commands import FakeCommandRunner
from voc_updater.foup import FoupInstaller


def test_foup_installer_updates_only_changed_ps_file(tmp_path: Path) -> None:
    run_file = tmp_path / "run"
    pl_file = tmp_path / "design_1_wrapper.bit.bin"
    run_file.write_bytes(b"run")
    pl_file.write_bytes(b"pl")
    runner = FakeCommandRunner()

    installer = FoupInstaller(
        host="192.168.1.50",
        ssh_user="root",
        ssh_key=tmp_path / "id_rsa",
        mount_device="/dev/mmcblk1p1",
        mount_point="/tmp",
        remote_run_path="/tmp/run",
        remote_pl_path="/tmp/design_1_wrapper.bit.bin",
        runner=runner,
    )

    installer.upgrade(
        ps_changed=True,
        pl_changed=False,
        local_run_file=run_file,
        local_pl_file=pl_file,
    )

    assert runner.commands == [
        [
            "ssh",
            "-i",
            str(tmp_path / "id_rsa"),
            "root@192.168.1.50",
            "mount /dev/mmcblk1p1 /tmp",
        ],
        ["ssh", "-i", str(tmp_path / "id_rsa"), "root@192.168.1.50", "sync"],
        ["ssh", "-i", str(tmp_path / "id_rsa"), "root@192.168.1.50", "reboot"],
    ]
    assert runner.uploads == [(run_file, "root@192.168.1.50:/tmp/run")]


def test_foup_installer_skips_when_no_files_changed(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    installer = FoupInstaller(
        host="192.168.1.50",
        ssh_user="root",
        ssh_key=tmp_path / "id_rsa",
        mount_device="/dev/mmcblk1p1",
        mount_point="/tmp",
        remote_run_path="/tmp/run",
        remote_pl_path="/tmp/design_1_wrapper.bit.bin",
        runner=runner,
    )

    installer.upgrade(
        ps_changed=False,
        pl_changed=False,
        local_run_file=tmp_path / "run",
        local_pl_file=tmp_path / "design_1_wrapper.bit.bin",
    )

    assert runner.commands == []
    assert runner.uploads == []
