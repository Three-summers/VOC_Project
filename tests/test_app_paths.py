"""测试 app_paths：系统配置定位、数据目录解析、状态迁移。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app import app_paths


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """每个用例都从干净的环境与缓存开始。"""
    monkeypatch.delenv(app_paths.DATA_DIR_ENV, raising=False)
    monkeypatch.delenv(app_paths.CONFIG_PATH_ENV, raising=False)
    app_paths.reset_cache()
    yield
    app_paths.reset_cache()


def _write_config(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_bundled_config_declares_expected_sections() -> None:
    """包内默认配置必须包含数据目录与硬件默认值分区"""
    config = json.loads(
        app_paths.BUNDLED_CONFIG_PATH.read_text(encoding="utf-8")
    )
    for section in ("logging", "paths", "standby", "acquisition", "loadport", "update"):
        assert section in config, section
    assert "data_directory" in config["paths"]
    assert "host" in config["acquisition"]
    assert "lock_serial_port" in config["loadport"]


def test_default_data_directory_uses_xdg(monkeypatch, tmp_path: Path) -> None:
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    assert app_paths.default_data_directory() == (xdg / "voc").resolve()


def test_data_directory_prefers_env(monkeypatch, tmp_path: Path) -> None:
    env_dir = tmp_path / "env-data"
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(env_dir))
    assert app_paths.get_data_directory() == env_dir.resolve()


def test_data_directory_from_config(monkeypatch, tmp_path: Path) -> None:
    """未设置 VOC_DATA_DIR 时，数据目录取自配置的 paths.data_directory"""
    data_dir = tmp_path / "elsewhere"
    config_path = _write_config(
        tmp_path / "custom.json", {"paths": {"data_directory": str(data_dir)}}
    )
    monkeypatch.setenv(app_paths.CONFIG_PATH_ENV, str(config_path))

    assert app_paths.get_system_config_path() == config_path.resolve()
    assert app_paths.get_data_directory() == data_dir.resolve()
    assert app_paths.get_log_directory() == data_dir.resolve() / "Log"


def test_data_directory_env_beats_config(monkeypatch, tmp_path: Path) -> None:
    """VOC_DATA_DIR 优先级高于配置项"""
    data_dir = tmp_path / "elsewhere"
    config_path = _write_config(
        tmp_path / "custom.json", {"paths": {"data_directory": str(data_dir)}}
    )
    env_dir = tmp_path / "env-data"
    monkeypatch.setenv(app_paths.CONFIG_PATH_ENV, str(config_path))
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(env_dir))

    assert app_paths.get_data_directory() == env_dir.resolve()


def test_system_config_path_env_wins(monkeypatch, tmp_path: Path) -> None:
    explicit = _write_config(tmp_path / "custom.json", {"paths": {}})
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(tmp_path / "bootstrap"))
    monkeypatch.setenv(app_paths.CONFIG_PATH_ENV, str(explicit))
    assert app_paths.get_system_config_path() == explicit.resolve()


def test_missing_user_config_falls_back_to_bundled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(tmp_path / "empty"))
    assert app_paths.get_system_config_path() == app_paths.BUNDLED_CONFIG_PATH


def test_user_config_overrides_and_merges_with_bundled(monkeypatch, tmp_path: Path) -> None:
    bootstrap = tmp_path / "bootstrap"
    _write_config(
        bootstrap / app_paths.CONFIG_FILE_NAME,
        {"standby": {"idle_timeout_seconds": 5}},
    )
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(bootstrap))

    config = app_paths.load_config()
    # 用户值覆盖
    assert config["standby"]["idle_timeout_seconds"] == 5
    # 未覆盖的键保留包内默认值
    assert config["standby"]["media_directory"] == json.loads(
        app_paths.BUNDLED_CONFIG_PATH.read_text(encoding="utf-8")
    )["standby"]["media_directory"]
    assert "logging" in config
    assert app_paths.get_value("acquisition", "port", 0) == 65432


def test_load_config_is_cached_until_reset(monkeypatch, tmp_path: Path) -> None:
    bootstrap = tmp_path / "bootstrap"
    config_path = _write_config(
        bootstrap / app_paths.CONFIG_FILE_NAME,
        {"standby": {"idle_timeout_seconds": 7}},
    )
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(bootstrap))
    assert app_paths.load_config()["standby"]["idle_timeout_seconds"] == 7

    _write_config(config_path, {"standby": {"idle_timeout_seconds": 11}})
    assert app_paths.load_config()["standby"]["idle_timeout_seconds"] == 7
    app_paths.reset_cache()
    assert app_paths.load_config()["standby"]["idle_timeout_seconds"] == 11


def test_ensure_user_config_seeds_once(monkeypatch, tmp_path: Path) -> None:
    bootstrap = tmp_path / "bootstrap"
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(bootstrap))

    created = app_paths.ensure_user_config()
    assert created == bootstrap / app_paths.CONFIG_FILE_NAME
    assert created.exists()
    # 内容与包内默认配置一致
    assert json.loads(created.read_text(encoding="utf-8")) == json.loads(
        app_paths.BUNDLED_CONFIG_PATH.read_text(encoding="utf-8")
    )
    # 第二次不再生成
    assert app_paths.ensure_user_config() is None


def test_ensure_user_config_skipped_when_explicit(monkeypatch, tmp_path: Path) -> None:
    bootstrap = tmp_path / "bootstrap"
    explicit = _write_config(tmp_path / "custom.json", {"paths": {}})
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(bootstrap))
    monkeypatch.setenv(app_paths.CONFIG_PATH_ENV, str(explicit))

    assert app_paths.ensure_user_config() is None
    assert not (bootstrap / app_paths.CONFIG_FILE_NAME).exists()


def test_migrate_legacy_channel_config(monkeypatch, tmp_path: Path) -> None:
    bootstrap = tmp_path / "bootstrap"
    legacy = _write_config(tmp_path / "legacy_channel_config.json", {"VOC": {}})
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(bootstrap))
    monkeypatch.setattr(app_paths, "LEGACY_CHANNEL_CONFIG_PATH", legacy)

    target = bootstrap / app_paths.CHANNEL_CONFIG_FILE_NAME
    assert app_paths.migrate_legacy_channel_config() == target
    assert json.loads(target.read_text(encoding="utf-8")) == {"VOC": {}}
    # 目标已存在时不再覆盖
    target.write_text('{"VOC": {"_meta": {}}}', encoding="utf-8")
    assert app_paths.migrate_legacy_channel_config() is None
    assert "VOC" in json.loads(target.read_text(encoding="utf-8"))


def test_prepare_runtime_paths_creates_directories(monkeypatch, tmp_path: Path) -> None:
    bootstrap = tmp_path / "bootstrap"
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(bootstrap))
    monkeypatch.setattr(
        app_paths, "LEGACY_CHANNEL_CONFIG_PATH", tmp_path / "missing.json"
    )

    data_dir = app_paths.prepare_runtime_paths()
    assert data_dir == bootstrap.resolve()
    assert app_paths.get_log_directory().is_dir()
    assert (bootstrap / app_paths.CONFIG_FILE_NAME).exists()
