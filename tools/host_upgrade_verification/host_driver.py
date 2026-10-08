"""真实主机升级验证驱动：用真实 systemctl 跑 LoadportInstaller 事务。

用法：host_driver.py <base> <version> <success|failure>

FOUP 版本用桩（与包内版本一致）以避免在没有 FOUP 的主机上触发固件升级；
Loadport 安装器、包解析器和状态写入都使用真实实现。
"""

from __future__ import annotations

import json
import pathlib
import sys

base = pathlib.Path(sys.argv[1]).resolve()
version = sys.argv[2]
expect = sys.argv[3]
sys.path.insert(0, str(base / "updater"))

from voc_updater.commands import CommandRunner  # noqa: E402
from voc_updater.foup_version import FoupVersion  # noqa: E402
from voc_updater.loadport import LoadportInstaller  # noqa: E402
from voc_updater.orchestrator import UpdateOrchestrator  # noqa: E402
from voc_updater.package import UpdatePackageReader  # noqa: E402


class StubFoupClient:
    def get_version(self) -> FoupVersion:
        return FoupVersion(ps_version="9.9.9", pl_version="9.9.9")


class NoFoupInstaller:
    def upgrade(self, **_kwargs) -> None:
        raise AssertionError("FOUP upgrade must not run in this verification")


def current_loadport_version() -> str:
    manifest = base / "current" / "loadport" / "manifest.json"
    return json.loads(manifest.read_text(encoding="utf-8"))["version"]


orchestrator = UpdateOrchestrator(
    reader=UpdatePackageReader(base / "work"),
    current_loadport_version=current_loadport_version,
    foup_client=StubFoupClient(),
    loadport_installer=LoadportInstaller(
        releases_dir=base / "releases",
        current_link=base / "current",
        gui_service="voc-gui.service",
        systemctl_scope="user",
        runner=CommandRunner(),
    ),
    foup_installer=NoFoupInstaller(),
    state_file=base / "state" / "update_status.json",
    log_file=base / "state" / "update.log",
)

package = base / "updates" / f"voc-update-{version}.tar.gz"

if expect == "success":
    orchestrator.run(package)
    print(f"upgrade-ok {version}")
else:
    try:
        orchestrator.run(package)
    except Exception as exc:  # noqa: BLE001
        print(f"expected-failure {version}: {exc}")
    else:
        raise SystemExit("ERROR: upgrade unexpectedly succeeded")
