"""输入验证器。

提供 IP、端口、文件路径与字符串长度等校验能力，避免将非法输入传递到网络/文件等敏感边界。
"""

from __future__ import annotations

import ipaddress
from pathlib import Path, PurePosixPath
from typing import Any


class ValidationError(ValueError):
    """输入验证失败。"""


def validate_string_length(
    value: Any,
    *,
    min_length: int = 0,
    max_length: int = 1024,
    field: str = "value",
) -> str:
    """验证字符串长度并返回规范化后的字符串。

    Args:
        value: 任意输入，将被转换为字符串（None 视为 ""）
        min_length: 最小长度（含）
        max_length: 最大长度（含）
        field: 字段名，用于错误信息
    """
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    else:
        text = str(value)

    if min_length < 0 or max_length < 0 or max_length < min_length:
        raise ValidationError(f"{field} 长度约束无效")

    if len(text) < min_length:
        raise ValidationError(f"{field} 长度过短")
    if len(text) > max_length:
        raise ValidationError(f"{field} 长度过长")
    return text


def validate_ip(value: Any) -> str:
    """验证 IP 地址（支持 IPv4/IPv6）。"""
    text = validate_string_length(value, min_length=1, max_length=128, field="ip").strip()
    try:
        return str(ipaddress.ip_address(text))
    except ValueError as exc:
        raise ValidationError("无效的 IP 地址") from exc


def validate_port(value: Any) -> int:
    """验证端口号（1-65535）。"""
    if isinstance(value, bool):
        raise ValidationError("无效的端口号")
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("无效的端口号") from exc
    if port < 1 or port > 65535:
        raise ValidationError("端口号超出范围")
    return port


def validate_path_no_traversal(value: Any) -> str:
    """验证路径不包含路径遍历片段（..）。

    该函数不强制要求相对路径，主要用于校验远端路径/用户输入字符串，避免 `../` 逃逸。
    """
    raw = validate_string_length(value, min_length=1, max_length=4096, field="path")
    if "\x00" in raw:
        raise ValidationError("路径包含非法字符")

    normalized = raw.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if any(part == ".." for part in parts):
        raise ValidationError("路径包含非法的上级目录引用")
    return raw


def validate_file_path(
    value: Any,
    *,
    base_dir: Path | None = None,
    must_exist: bool = False,
) -> Path:
    """验证文件路径，防止路径遍历。

    Args:
        value: 路径输入
        base_dir: 限定根目录；提供后 path 必须位于 base_dir 下
        must_exist: 是否要求文件/目录存在
    """
    raw = validate_path_no_traversal(value)
    path = Path(raw).expanduser()

    if base_dir is None:
        candidate = path.resolve(strict=False)
    else:
        base = base_dir.expanduser().resolve(strict=False)
        candidate = (base / path).resolve(strict=False) if not path.is_absolute() else path.resolve(strict=False)
        if candidate != base and base not in candidate.parents:
            raise ValidationError("路径越界")

    if must_exist and not candidate.exists():
        raise ValidationError("路径不存在")
    return candidate

