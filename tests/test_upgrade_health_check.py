"""启动确认竞态：新版"起来后立刻退出"被记成升级成功。

真实 Ubuntu 主机部署测试发现：投放一个启动即 `sys.exit(0)` 的 release，
安装器 `start` 后立即检查 `is-active`，此时进程尚未退出 → 确认通过、切到新版本、
状态写 `succeeded`；几十毫秒后进程退出，服务实际是 inactive。

修复口径：`_confirm_running` 必须在启动后等一个稳定窗口，再复查
`is-active` 与 MainPID 是否保持不变，避免把已经死掉/正在重启的进程当成成功。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.commands import FakeCommandRunner  # noqa: E402
from voc_updater.loadport import LoadportInstaller  # noqa: E402


def _make_app(path: Path, marker: str) -> None:
    app = path / "src" / "voc_app" / "gui"
    app.mkdir(parents=True)
    (app / "app.py").write_text(marker, encoding="utf-8")


def _seed_old_release(tmp_path: Path) -> Path:
    old = tmp_path / "releases" / "loadport-1.0.0"
    _make_app(old, "old")
    (tmp_path / "current").symlink_to(old, target_is_directory=True)
    return old


def _installer(tmp_path: Path, runner) -> LoadportInstaller:
    return LoadportInstaller(
        releases_dir=tmp_path / "releases",
        current_link=tmp_path / "current",
        gui_service="voc-gui.service",
        systemctl_scope="user",
        runner=runner,
        # 测试不真的等待，只验证"稳定窗口后再复查"的逻辑
        settle_seconds=0,
    )


class ScriptedIsActiveRunner(FakeCommandRunner):
    """按脚本依次返回 is-active 的返回码，用完后回落到真实服务状态。"""

    def __init__(self, script: list[int]) -> None:
        super().__init__()
        self.is_active_script = list(script)

    def run(self, args, timeout: int = 60):
        if self._service_action(args) == "is-active" and self.is_active_script:
            self.commands.append(list(args))
            return self._result(args, self.is_active_script.pop(0))
        return super().run(args, timeout)


class PidChangingRunner(FakeCommandRunner):
    """每次查询 MainPID 都返回不同的值，模拟稳定窗口内服务发生了重启。"""

    def __init__(self) -> None:
        super().__init__()
        self._next_pid = 5000

    def run(self, args, timeout: int = 60):
        if self._service_action(args) == "show":
            self.commands.append(list(args))
            self._next_pid += 1
            return self._result(args, 0, stdout=str(self._next_pid))
        return super().run(args, timeout)


def test_install_rolls_back_when_service_dies_after_start(tmp_path: Path) -> None:
    """0.3.0 场景：启动确认时还 active，稳定窗口后已经退出。"""
    old = _seed_old_release(tmp_path)
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")
    # 第 1 次 is-active 是停止确认（inactive）；第 2 次启动确认仍 active；
    # 第 3 次（稳定窗口后）已经退出 → inactive。
    runner = ScriptedIsActiveRunner([3, 0, 3])

    with pytest.raises(RuntimeError, match="roll"):
        _installer(tmp_path, runner).install(version="1.2.3", app_dir=new_app)

    assert (tmp_path / "current").resolve() == old.resolve(), "必须回滚到旧版本"
    assert runner.commands.count(
        ["systemctl", "--user", "is-active", "voc-gui.service"]
    ) >= 3, "启动确认必须在稳定窗口后复查 is-active"


def test_install_rolls_back_when_service_restarts_in_settle_window(
    tmp_path: Path,
) -> None:
    old = _seed_old_release(tmp_path)
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")
    runner = PidChangingRunner()

    with pytest.raises(RuntimeError, match="roll"):
        _installer(tmp_path, runner).install(version="1.2.3", app_dir=new_app)

    assert (tmp_path / "current").resolve() == old.resolve()


def test_healthy_service_passes_settle_check(tmp_path: Path) -> None:
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")
    runner = FakeCommandRunner()

    target = _installer(tmp_path, runner).install(version="1.2.3", app_dir=new_app)

    assert (tmp_path / "current").resolve() == target.resolve()
    is_active_calls = [
        call
        for call in runner.commands
        if call == ["systemctl", "--user", "is-active", "voc-gui.service"]
    ]
    assert len(is_active_calls) >= 3, "健康路径也应做稳定窗口复查"
