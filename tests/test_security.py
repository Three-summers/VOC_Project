"""测试 security 模块"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.security.auth import (
    AuthManager,
    AuthenticationManager,
    hash_password,
    verify_password,
)
from voc_app.security.validator import (
    ValidationError,
    validate_file_path,
    validate_ip,
    validate_path_no_traversal,
    validate_port,
    validate_string_length,
)


class TestValidator(unittest.TestCase):
    """输入验证器测试"""

    def test_validate_string_length_basic(self) -> None:
        self.assertEqual(validate_string_length("abc", min_length=1, max_length=3), "abc")

    def test_validate_string_length_none(self) -> None:
        self.assertEqual(validate_string_length(None, min_length=0, max_length=1), "")

    def test_validate_string_length_too_short(self) -> None:
        with self.assertRaises(ValidationError):
            validate_string_length("", min_length=1, max_length=10)

    def test_validate_string_length_too_long(self) -> None:
        with self.assertRaises(ValidationError):
            validate_string_length("abcd", min_length=0, max_length=3)

    def test_validate_string_length_invalid_constraints(self) -> None:
        with self.assertRaises(ValidationError):
            validate_string_length("a", min_length=2, max_length=1)

    def test_validate_ip_ipv4(self) -> None:
        self.assertEqual(validate_ip("127.0.0.1"), "127.0.0.1")

    def test_validate_ip_ipv6(self) -> None:
        self.assertEqual(validate_ip("::1"), "::1")

    def test_validate_ip_invalid(self) -> None:
        for value in ("", "999.1.1.1", "not-an-ip"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_ip(value)

    def test_validate_port_valid(self) -> None:
        self.assertEqual(validate_port(1), 1)
        self.assertEqual(validate_port("65535"), 65535)

    def test_validate_port_invalid(self) -> None:
        for value in (0, 65536, "abc", None, True):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_port(value)

    def test_validate_path_no_traversal_accepts_normal_paths(self) -> None:
        for value in ("Log", "/custom/path", "a/b/c", r"a\\b\\c"):
            with self.subTest(value=value):
                self.assertEqual(validate_path_no_traversal(value), value)

    def test_validate_path_no_traversal_rejects_traversal(self) -> None:
        for value in ("../etc", "a/../b", "..", r"a\\..\\b", "a/.."):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_path_no_traversal(value)

    def test_validate_path_no_traversal_rejects_nul(self) -> None:
        with self.assertRaises(ValidationError):
            validate_path_no_traversal("a\x00b")

    def test_validate_file_path_base_dir_ok(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            p = validate_file_path("a/b.txt", base_dir=base_dir, must_exist=False)
            self.assertTrue(str(p).startswith(str(base_dir.resolve())))

    def test_validate_file_path_base_dir_escape(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            with self.assertRaises(ValidationError):
                validate_file_path("../x", base_dir=base_dir)

    def test_validate_file_path_must_exist(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            target = base_dir / "exists.txt"
            target.write_text("ok", encoding="utf-8")
            self.assertEqual(
                validate_file_path("exists.txt", base_dir=base_dir, must_exist=True),
                target.resolve(),
            )
            with self.assertRaises(ValidationError):
                validate_file_path("missing.txt", base_dir=base_dir, must_exist=True)


class TestAuthManager(unittest.TestCase):
    """认证管理器测试"""

    def _write_auth_file(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_authenticate_success_and_failure_bcrypt_and_argon2(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = Path(tmpdir) / "auth.json"
            data = {
                "users": {
                    "admin": hash_password("s3cret", algorithm="bcrypt"),
                    "user": hash_password("p@ss", algorithm="argon2"),
                }
            }
            self._write_auth_file(auth_path, data)

            mgr = AuthManager(auth_file=auth_path)
            self.assertTrue(mgr.authenticate("admin", "s3cret"))
            self.assertFalse(mgr.authenticate("admin", "wrong"))
            self.assertTrue(mgr.authenticate("user", "p@ss"))
            self.assertFalse(mgr.authenticate("user", "wrong"))

    def test_authenticate_unknown_user(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = Path(tmpdir) / "auth.json"
            self._write_auth_file(
                auth_path, {"users": {"admin": hash_password("x", algorithm="bcrypt")}}
            )
            mgr = AuthManager(auth_file=auth_path)
            self.assertFalse(mgr.authenticate("missing", "x"))

    def test_authenticate_invalid_hash_format(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = Path(tmpdir) / "auth.json"
            self._write_auth_file(auth_path, {"users": {"admin": "plain-text"}})
            mgr = AuthManager(auth_file=auth_path)
            self.assertFalse(mgr.authenticate("admin", "anything"))

    def test_auth_file_list_schema(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = Path(tmpdir) / "auth.json"
            self._write_auth_file(
                auth_path,
                {
                    "users": [
                        {
                            "username": "admin",
                            "password_hash": hash_password("s3cret", algorithm="bcrypt"),
                        }
                    ]
                },
            )
            mgr = AuthManager(auth_file=auth_path)
            self.assertTrue(mgr.authenticate("admin", "s3cret"))

    def test_env_var_voc_auth_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = Path(tmpdir) / "auth.json"
            self._write_auth_file(
                auth_path, {"users": {"admin": hash_password("s3cret", algorithm="bcrypt")}}
            )
            with patch.dict(os.environ, {"VOC_AUTH_FILE": str(auth_path)}, clear=False):
                mgr = AuthManager()
                self.assertTrue(mgr.authenticate("admin", "s3cret"))

    def test_reload_invalid_json_does_not_crash(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = Path(tmpdir) / "auth.json"
            auth_path.write_text("{invalid json", encoding="utf-8")
            mgr = AuthManager(auth_file=auth_path)
            self.assertFalse(mgr.authenticate("admin", "x"))

    def test_reload_missing_file_does_not_crash(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing.json"
            mgr = AuthManager(auth_file=missing_path)
            self.assertFalse(mgr.authenticate("admin", "x"))

    def test_reload_invalid_users_schema_does_not_crash(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = Path(tmpdir) / "auth.json"
            self._write_auth_file(auth_path, {"users": ["not-a-dict"]})
            mgr = AuthManager(auth_file=auth_path)
            self.assertFalse(mgr.authenticate("admin", "x"))

            auth_path.write_text("123", encoding="utf-8")
            mgr = AuthManager(auth_file=auth_path)
            self.assertFalse(mgr.authenticate("admin", "x"))

    def test_authenticate_validation_error_returns_false(self) -> None:
        mgr = AuthManager()
        self.assertFalse(mgr.authenticate("", ""))
        self.assertFalse(mgr.authenticate(None, None))

    def test_default_auth_paths_are_used_when_present(self) -> None:
        import tempfile
        from unittest.mock import patch as mock_patch

        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = Path(tmpdir) / "auth.json"
            self._write_auth_file(
                auth_path, {"users": {"admin": hash_password("s3cret", algorithm="bcrypt")}}
            )
            with mock_patch(
                "voc_app.security.auth._default_auth_paths", return_value=[auth_path]
            ), patch.dict(os.environ, {"VOC_AUTH_FILE": ""}, clear=False):
                mgr = AuthManager()
                self.assertTrue(mgr.authenticate("admin", "s3cret"))

    def test_source_property(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = Path(tmpdir) / "auth.json"
            self._write_auth_file(
                auth_path, {"users": {"admin": hash_password("x", algorithm="bcrypt")}}
            )
            mgr = AuthManager(auth_file=auth_path)
            self.assertEqual(mgr.source, str(auth_path))

    def test_verify_password_invalid_argon2_hash(self) -> None:
        with self.assertRaises(RuntimeError):
            verify_password("password", "$argon2id$invalid")

    def test_hash_password_invalid_algorithm(self) -> None:
        with self.assertRaises(RuntimeError):
            hash_password("password", algorithm="md5")

    def test_qml_compatible_authentication_manager_login(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            auth_path = Path(tmpdir) / "auth.json"
            self._write_auth_file(
                auth_path, {"users": {"admin": hash_password("s3cret", algorithm="bcrypt")}}
            )
            qml_mgr = AuthenticationManager()
            qml_mgr._auth = AuthManager(auth_file=auth_path)  # type: ignore[attr-defined]
            self.assertTrue(qml_mgr.login("admin", "s3cret"))
            self.assertFalse(qml_mgr.login("admin", "wrong"))

    def test_no_hardcoded_password_in_app_py(self) -> None:
        app_py = ROOT_DIR / "src" / "voc_app" / "gui" / "app.py"
        content = app_py.read_text(encoding="utf-8")
        self.assertNotIn('"123456"', content)
        self.assertNotIn("'123456'", content)


if __name__ == "__main__":
    unittest.main()
