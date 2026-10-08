from __future__ import annotations

from pathlib import Path

from .commands import CommandRunner


class FoupInstaller:
    def __init__(
        self,
        host: str,
        ssh_user: str,
        ssh_key: str | Path,
        mount_device: str,
        mount_point: str | Path,
        remote_run_path: str | Path,
        remote_pl_path: str | Path,
        runner: CommandRunner,
    ) -> None:
        self.host = host
        self.ssh_user = ssh_user
        self.ssh_key = Path(ssh_key)
        self.mount_device = mount_device
        self.mount_point = Path(mount_point)
        self.remote_run_path = Path(remote_run_path)
        self.remote_pl_path = Path(remote_pl_path)
        self.runner = runner

    def upgrade(
        self,
        ps_changed: bool,
        pl_changed: bool,
        local_run_file: str | Path,
        local_pl_file: str | Path,
    ) -> None:
        if not ps_changed and not pl_changed:
            return
        self._run_remote(f"mount {self.mount_device} {self.mount_point}")
        if ps_changed:
            self._upload(Path(local_run_file), self.remote_run_path)
        if pl_changed:
            self._upload(Path(local_pl_file), self.remote_pl_path)
        self._run_remote("sync")
        self._run_remote("reboot")

    def _remote(self) -> str:
        return f"{self.ssh_user}@{self.host}"

    def _ssh_auth_options(self) -> list[str]:
        """ssh 与 scp 共用的认证/非交互参数（R26）。

        只给 ssh 加 ``-i``、scp 不加时，配置了非默认密钥且 SSH agent 没有
        等效身份的环境里，挂载能成功但上传会认证失败或等待交互输入。
        """
        return [
            "-i",
            str(self.ssh_key),
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
        ]

    def _run_remote(self, command: str) -> None:
        args = ["ssh", *self._ssh_auth_options(), self._remote(), command]
        result = self.runner.run(args, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"remote command failed: {command}")

    def _upload(self, local_path: Path, remote_path: Path) -> None:
        result = self.runner.upload(
            local_path,
            f"{self._remote()}:{remote_path}",
            options=self._ssh_auth_options(),
        )
        if result.returncode != 0:
            raise RuntimeError(f"upload failed: {local_path} -> {remote_path}")
