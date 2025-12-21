"""认证管理器。

从环境变量 `VOC_AUTH_FILE` 或默认配置文件加载用户凭据，支持 bcrypt/argon2 哈希校验。
同时提供 QML 兼容的 `login(username, password) -> bool` 接口（Qt Slot）。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from voc_app.logging_config import get_logger

from .validator import ValidationError, validate_string_length

logger = get_logger(__name__)


try:
    from PySide6.QtCore import QObject, Slot
except ModuleNotFoundError:  # pragma: no cover
    class QObject:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    def Slot(*args: Any, **kwargs: Any):  # type: ignore[no-redef]
        def decorator(func):
            return func

        return decorator


@dataclass(frozen=True)
class AuthLoadResult:
    users: dict[str, str]
    source: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_auth_paths() -> list[Path]:
    root = _project_root()
    return [
        root / "voc_auth.json",
        root / "config" / "auth.json",
        root / "config" / "voc_auth.json",
    ]


def _load_json_file(path: Path) -> Any:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"读取认证文件失败: {path}") from exc
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"认证文件不是有效 JSON: {path}") from exc


def _parse_users(data: Any) -> dict[str, str]:
    if isinstance(data, Mapping) and "users" in data:
        data = data["users"]

    if isinstance(data, Mapping):
        users: dict[str, str] = {}
        for k, v in data.items():
            username = validate_string_length(k, min_length=1, max_length=128, field="username").strip()
            pwd_hash = validate_string_length(v, min_length=1, max_length=512, field="password_hash").strip()
            users[username] = pwd_hash
        return users

    if isinstance(data, list):
        users = {}
        for item in data:
            if not isinstance(item, Mapping):
                raise ValidationError("users 列表格式无效")
            username = validate_string_length(
                item.get("username") or item.get("user"),
                min_length=1,
                max_length=128,
                field="username",
            ).strip()
            pwd_hash = validate_string_length(
                item.get("password_hash") or item.get("hash"),
                min_length=1,
                max_length=512,
                field="password_hash",
            ).strip()
            users[username] = pwd_hash
        return users

    raise ValidationError("认证文件格式不支持")


def _verify_bcrypt(password: str, password_hash: str) -> bool:
    try:
        import bcrypt  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("缺少 bcrypt 依赖") from exc
    return bool(
        bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    )


def _verify_argon2(password: str, password_hash: str) -> bool:
    try:
        from argon2 import PasswordHasher  # type: ignore
        from argon2.exceptions import VerifyMismatchError, VerificationError  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("缺少 argon2 依赖") from exc

    hasher = PasswordHasher()
    try:
        return bool(hasher.verify(password_hash, password))
    except VerifyMismatchError:
        return False
    except VerificationError as exc:
        raise RuntimeError("argon2 哈希格式无效") from exc


def verify_password(password: str, password_hash: str) -> bool:
    password = validate_string_length(password, min_length=1, max_length=1024, field="password")
    password_hash = validate_string_length(password_hash, min_length=1, max_length=512, field="password_hash")

    if password_hash.startswith("$2"):
        return _verify_bcrypt(password, password_hash)
    if password_hash.startswith("$argon2"):
        return _verify_argon2(password, password_hash)
    raise RuntimeError("不支持的密码哈希格式")


def hash_password(password: str, *, algorithm: str = "bcrypt") -> str:
    """生成密码哈希（用于生成配置文件或测试）。"""
    password = validate_string_length(password, min_length=1, max_length=1024, field="password")
    algo = (algorithm or "").strip().lower()
    if algo == "bcrypt":
        try:
            import bcrypt  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("缺少 bcrypt 依赖") from exc
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    if algo == "argon2":
        try:
            from argon2 import PasswordHasher  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("缺少 argon2 依赖") from exc
        return PasswordHasher().hash(password)

    raise RuntimeError("不支持的哈希算法")


class AuthManager:
    """认证管理器（纯 Python），便于测试与复用。"""

    def __init__(
        self,
        *,
        auth_file: str | Path | None = None,
        env_var: str = "VOC_AUTH_FILE",
    ) -> None:
        self._env_var = env_var
        self._auth_file_override = Path(auth_file).expanduser() if auth_file else None
        self._users: dict[str, str] = {}
        self._source: str = ""
        self.reload()

    @property
    def source(self) -> str:
        return self._source

    def _resolve_auth_file(self) -> Path | None:
        if self._auth_file_override is not None:
            return self._auth_file_override

        env_path = os.environ.get(self._env_var, "").strip()
        if env_path:
            return Path(env_path).expanduser()

        for candidate in _default_auth_paths():
            if candidate.exists():
                return candidate
        return None

    def reload(self) -> None:
        path = self._resolve_auth_file()
        if path is None:
            self._users = {}
            self._source = ""
            logger.warning("未配置认证文件：请设置环境变量 VOC_AUTH_FILE 或提供默认配置文件")
            return

        try:
            data = _load_json_file(path)
            users = _parse_users(data)
        except (OSError, RuntimeError, ValidationError, TypeError, ValueError) as exc:
            logger.error(f"加载认证配置失败: {path}: {exc}", exc_info=True)
            self._users = {}
            self._source = str(path)
            return

        self._users = users
        self._source = str(path)
        logger.info(f"认证配置已加载: {path}，用户数: {len(users)}")

    def authenticate(self, username: Any, password: Any) -> bool:
        try:
            user = validate_string_length(username, min_length=1, max_length=128, field="username").strip()
            pwd = validate_string_length(password, min_length=1, max_length=1024, field="password")
        except ValidationError:
            return False

        stored_hash = self._users.get(user)
        if not stored_hash:
            logger.debug(f"认证失败：用户不存在: {user}")
            return False

        try:
            ok = verify_password(pwd, stored_hash)
        except (RuntimeError, ValidationError) as exc:
            logger.error(f"认证校验失败（配置或依赖问题）: {exc}", exc_info=True)
            return False

        if not ok:
            logger.debug(f"认证失败：密码不匹配: {user}")
        return ok


class AuthenticationManager(QObject):
    """QML 兼容认证管理器。

    QML 通过 `authManager.login(username, password)` 调用，返回 bool，不抛出异常。
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._auth = AuthManager()

    @Slot(str, str, result=bool)
    def login(self, username: str, password: str) -> bool:
        return bool(self._auth.authenticate(username, password))

