"""升级事务化 / 服务确认 / 认证参数回归（R13 / R14 / R26 / R27）。

R13：systemd 切换 current 后可能仍运行原有代码 —— 需要能验证实际运行进程
     属于目标 release；部署模板必须让 current/src 真正进入模块搜索路径。
R14：启动超时等异常不触发回滚 —— 停止/切换/启动/确认必须是一个事务。
R26：FOUP 的 SCP 上传没有使用配置的 SSH 密钥 —— ssh 与 scp 共用认证参数。
R27：忽略停止服务失败，把旧进程误记为升级成功 —— 必须确认服务真的停了。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.commands import FakeCommandRunner
from voc_updater.foup import FoupInstaller
from voc_updater.loadport import LoadportInstaller


def _make_app(path: Path, marker: str) -> None:
    app = path / "src" / "voc_app" / "gui"
    app.mkdir(parents=True)
    (app / "app.py").write_text(marker, encoding="utf-8")


def _installer(tmp_path: Path, runner=None) -> LoadportInstaller:
    return LoadportInstaller(
        releases_dir=tmp_path / "releases",
        current_link=tmp_path / "current",
        gui_service="voc-gui.service",
        systemctl_scope="user",
        runner=runner or FakeCommandRunner(),
        # 稳定窗口在单元测试里不真的等待
        settle_seconds=0,
    )


def _seed_old_release(tmp_path: Path) -> Path:
    releases = tmp_path / "releases"
    old = releases / "loadport-1.0.0"
    _make_app(old, "old")
    (tmp_path / "current").symlink_to(old, target_is_directory=True)
    return old


class _StartTimeoutRunner(FakeCommandRunner):
    """第一次 start 抛 TimeoutExpired，回滚时的 start 正常。"""

    def __init__(self) -> None:
        super().__init__()
        self.start_calls = 0

    def run(self, args, timeout: int = 60):
        if args[:1] == ["systemctl"] and "start" in args:
            self.start_calls += 1
            self.commands.append(list(args))
            if self.start_calls == 1:
                raise subprocess.TimeoutExpired(args, timeout)
            from voc_updater.commands import CommandResult

            self.service_active = True
            return CommandResult(args=list(args), returncode=0, stdout="", stderr="")
        return super().run(args, timeout)


# ------------------------------------------------------------------ R27


def test_install_aborts_when_stop_fails_and_service_still_active(tmp_path: Path) -> None:
    old = _seed_old_release(tmp_path)
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")
    runner = FakeCommandRunner(
        fail_on=[["systemctl", "--user", "stop", "voc-gui.service"]]
    )

    with pytest.raises(RuntimeError, match="stop"):
        _installer(tmp_path, runner).install(version="1.2.3", app_dir=new_app)

    assert (tmp_path / "current").resolve() == old.resolve(), (
        "停止失败且服务仍在运行时不能切换 current"
    )


def test_install_aborts_when_service_still_active_after_stop(tmp_path: Path) -> None:
    old = _seed_old_release(tmp_path)
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")

    class LyingStopRunner(FakeCommandRunner):
        def run(self, args, timeout: int = 60):
            result = super().run(args, timeout)
            if args[:1] == ["systemctl"] and "stop" in args:
                # 假装 stop 返回 0，但服务其实还活着
                self.service_active = True
            return result

    with pytest.raises(RuntimeError, match="stop"):
        _installer(tmp_path, LyingStopRunner()).install(
            version="1.2.3", app_dir=new_app
        )

    assert (tmp_path / "current").resolve() == old.resolve()


# ------------------------------------------------------------------ R14


def test_install_rolls_back_when_start_raises_timeout(tmp_path: Path) -> None:
    old = _seed_old_release(tmp_path)
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")
    runner = _StartTimeoutRunner()

    with pytest.raises(RuntimeError) as excinfo:
        _installer(tmp_path, runner).install(version="1.2.3", app_dir=new_app)

    assert "roll" in str(excinfo.value).lower()
    assert (tmp_path / "current").resolve() == old.resolve(), "必须回滚到旧版本"


def test_install_rolls_back_when_confirm_fails(tmp_path: Path) -> None:
    old = _seed_old_release(tmp_path)
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")
    runner = FakeCommandRunner(
        fail_on=[["systemctl", "--user", "is-active", "voc-gui.service"]]
    )

    with pytest.raises(RuntimeError):
        _installer(tmp_path, runner).install(version="1.2.3", app_dir=new_app)

    assert (tmp_path / "current").resolve() == old.resolve()


# ------------------------------------------------------------------ R13


def test_verify_process_release_detects_wrong_release(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    target = tmp_path / "releases" / "loadport-9.9.9"
    target.mkdir(parents=True)

    with pytest.raises(RuntimeError, match="running process"):
        installer._verify_process_release(str(os.getpid()), target)

    # 进程 cwd 等于目标时通过
    installer._verify_process_release(str(os.getpid()), Path.cwd().resolve())


def test_verify_process_release_skips_when_pid_unknown(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    installer._verify_process_release("", tmp_path / "whatever")


def test_install_confirms_current_link_points_to_target(tmp_path: Path) -> None:
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")

    target = _installer(tmp_path).install(version="1.2.3", app_dir=new_app)

    assert (tmp_path / "current").resolve() == target.resolve()


# ------------------------------------------------------------------ R26


def _foup_installer(tmp_path: Path, runner) -> FoupInstaller:
    return FoupInstaller(
        host="192.168.1.50",
        ssh_user="root",
        ssh_key=tmp_path / "id_rsa",
        mount_device="/dev/mmcblk1p1",
        mount_point="/tmp",
        remote_run_path="/tmp/run",
        remote_pl_path="/tmp/design_1_wrapper.bit.bin",
        runner=runner,
    )


def test_scp_upload_uses_configured_ssh_key_and_batch_mode(tmp_path: Path) -> None:
    run_file = tmp_path / "run"
    run_file.write_bytes(b"run")
    runner = FakeCommandRunner()

    _foup_installer(tmp_path, runner).upgrade(
        ps_changed=True,
        pl_changed=False,
        local_run_file=run_file,
        local_pl_file=tmp_path / "design_1_wrapper.bit.bin",
    )

    assert len(runner.upload_commands) == 1
    upload_args = runner.upload_commands[0]
    assert upload_args[0] == "scp"
    assert "-i" in upload_args
    assert str(tmp_path / "id_rsa") in upload_args
    assert "BatchMode=yes" in upload_args


def test_ssh_and_scp_share_authentication_options(tmp_path: Path) -> None:
    run_file = tmp_path / "run"
    run_file.write_bytes(b"run")
    runner = FakeCommandRunner()

    _foup_installer(tmp_path, runner).upgrade(
        ps_changed=True,
        pl_changed=False,
        local_run_file=run_file,
        local_pl_file=tmp_path / "design_1_wrapper.bit.bin",
    )

    ssh_args = runner.commands[0]
    assert "-i" in ssh_args
    assert "BatchMode=yes" in ssh_args


def test_upload_failure_still_raises(tmp_path: Path) -> None:
    run_file = tmp_path / "run"
    run_file.write_bytes(b"run")
    runner = FakeCommandRunner()
    runner.upload_fail = True

    with pytest.raises(RuntimeError, match="upload failed"):
        _foup_installer(tmp_path, runner).upgrade(
            ps_changed=True,
            pl_changed=False,
            local_run_file=run_file,
            local_pl_file=tmp_path / "design_1_wrapper.bit.bin",
        )
