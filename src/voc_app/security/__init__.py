"""VOC 安全模块。

包含认证与输入验证等基础能力，用于集中修复硬编码密码、缺乏校验等问题。
"""

from .auth import AuthManager, AuthenticationManager
from .validator import (
    ValidationError,
    validate_file_path,
    validate_ip,
    validate_path_no_traversal,
    validate_port,
    validate_string_length,
)

__all__ = [
    "AuthManager",
    "AuthenticationManager",
    "ValidationError",
    "validate_file_path",
    "validate_ip",
    "validate_path_no_traversal",
    "validate_port",
    "validate_string_length",
]

