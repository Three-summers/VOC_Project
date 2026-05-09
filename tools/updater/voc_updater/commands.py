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

    def upload(self, local_path: Path, remote_path: str) -> CommandResult:
        args = ["scp", str(local_path), remote_path]
        return self.run(args, timeout=300)


class FakeCommandRunner(CommandRunner):
    def __init__(self, fail_on: list[list[str]] | None = None) -> None:
        self.commands: list[list[str]] = []
        self.uploads: list[tuple[Path, str]] = []
        self.fail_on = fail_on or []

    def run(self, args: list[str], timeout: int = 60) -> CommandResult:
        self.commands.append(list(args))
        returncode = 1 if args in self.fail_on else 0
        return CommandResult(args=list(args), returncode=returncode, stdout="", stderr="")

    def upload(self, local_path: Path, remote_path: str) -> CommandResult:
        self.uploads.append((Path(local_path), remote_path))
        args = ["upload", str(local_path), remote_path]
        returncode = 1 if args in self.fail_on else 0
        return CommandResult(args=args, returncode=returncode, stdout="", stderr="")


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copytree(source, destination)
