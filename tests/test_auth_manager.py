"""登录状态与命令面板门控测试。

业务规则：未登录时右侧命令面板整体不可点击（disabled），登录成功后恢复。
状态由 Python 侧 AuthenticationManager 统一持有，QML 只读它，
避免 TitlePanel 的局部状态与命令面板门控各自为政。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.app import AuthenticationManager

QML_ROOT = ROOT_DIR / "src" / "voc_app" / "gui" / "qml"


class AuthenticationManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = AuthenticationManager()
        self.changes: list[bool] = []
        self.manager.authenticationChanged.connect(
            lambda: self.changes.append(self.manager.isAuthenticated)
        )

    def test_starts_unauthenticated(self) -> None:
        self.assertFalse(self.manager.isAuthenticated)
        self.assertEqual(self.manager.currentUser, "")

    def test_login_success_sets_authenticated(self) -> None:
        self.assertTrue(self.manager.login("admin", "123456"))
        self.assertTrue(self.manager.isAuthenticated)
        self.assertEqual(self.manager.currentUser, "admin")
        self.assertEqual(self.changes, [True])

    def test_login_failure_keeps_unauthenticated(self) -> None:
        self.assertFalse(self.manager.login("admin", "wrong"))
        self.assertFalse(self.manager.isAuthenticated)
        self.assertEqual(self.changes, [])

    def test_logout_clears_state(self) -> None:
        self.manager.login("user", "user")
        self.manager.logout()
        self.assertFalse(self.manager.isAuthenticated)
        self.assertEqual(self.manager.currentUser, "")
        self.assertEqual(self.changes, [True, False])

    def test_logout_without_login_does_not_emit(self) -> None:
        self.manager.logout()
        self.assertEqual(self.changes, [])


class CommandPanelGateSourceTests(unittest.TestCase):
    """命令面板必须整体按登录状态门控，且给出提示"""

    def _read(self, relative: str) -> str:
        return (QML_ROOT / relative).read_text(encoding="utf-8")

    def test_command_panel_binds_auth_state(self) -> None:
        text = self._read("CommandPanel.qml")
        self.assertIn("authManager.isAuthenticated", text)
        self.assertIn("enabled:", text)

    def test_command_panel_shows_login_hint(self) -> None:
        text = self._read("CommandPanel.qml")
        self.assertIn("请先登录", text)

    def test_title_panel_uses_auth_manager_state(self) -> None:
        text = self._read("TitlePanel.qml")
        self.assertIn("authManager.isAuthenticated", text)
        self.assertIn("authManager.logout()", text)


if __name__ == "__main__":
    unittest.main()
