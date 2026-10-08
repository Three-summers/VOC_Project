from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    def run(self, args: list[str], timeout: int = 60) -> CommandResult:
        completed = subprocess.run(
            args,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return CommandResult(
            args=args,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def upload(
        self,
        local_path: Path,
        remote_path: str,
        options: list[str] | None = None,
    ) -> CommandResult:
        """SCP 上传。``options`` 用于复用 ssh 的密钥与非交互参数（R26）。"""
        args = ["scp"]
        if options:
            args.extend(options)
        args.extend([str(local_path), remote_path])
        return self.run(args, timeout=300)


class FakeCommandRunner(CommandRunner):
    """测试替身，同时维护一个最小的 systemd 服务状态。

    ``stop`` 把服务置为 inactive 并更换 MainPID，``start`` 置为 active，
    ``is-active`` 返回 0/3，``show -p MainPID --value`` 返回当前 PID。
    这样安装器"确认服务真的停止/真的重启"的逻辑可以被真实驱动；如果所有
    命令都无条件返回 0，就会掩盖 R27 那类"旧进程仍在运行却记成功"的问题。
    """

    _SERVICE_ACTIONS = ("stop", "start", "is-active", "show", "restart")

    def __init__(
        self,
        fail_on: list[list[str]] | None = None,
        service_active: bool = True,
    ) -> None:
        self.commands: list[list[str]] = []
        self.uploads: list[tuple[Path, str]] = []
        self.upload_commands: list[list[str]] = []
        self.fail_on = fail_on or []
        self.upload_fail = False
        self.service_active = bool(service_active)
        self.main_pid = 1000

    @staticmethod
    def _result(args: list[str], returncode: int, stdout: str = "") -> CommandResult:
        return CommandResult(
            args=list(args), returncode=returncode, stdout=stdout, stderr=""
        )

    @classmethod
    def _service_action(cls, args: list[str]) -> str | None:
        if not args or args[0] != "systemctl":
            return None
        for action in cls._SERVICE_ACTIONS:
            if action in args:
                return action
        return None

    def run(self, args: list[str], timeout: int = 60) -> CommandResult:
        self.commands.append(list(args))
        forced_failure = args in self.fail_on
        action = self._service_action(args)
        if action is not None:
            if forced_failure:
                return self._result(args, 1)
            if action == "stop":
                self.service_active = False
                self.main_pid += 1
            elif action in ("start", "restart"):
                self.service_active = True
            elif action == "is-active":
                return self._result(args, 0 if self.service_active else 3)
            elif action == "show":
                pid = str(self.main_pid) if self.service_active else "0"
                return self._result(args, 0, stdout=pid)
            return self._result(args, 0)
        returncode = 1 if forced_failure else 0
        return self._result(args, returncode)

    def upload(
        self,
        local_path: Path,
        remote_path: str,
        options: list[str] | None = None,
    ) -> CommandResult:
        self.uploads.append((Path(local_path), remote_path))
        args = ["scp"]
        if options:
            args.extend(list(options))
        args.extend([str(local_path), remote_path])
        self.upload_commands.append(list(args))
        returncode = 1 if (self.upload_fail or args in self.fail_on) else 0
        return self._result(args, returncode)


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copytree(source, destination)
