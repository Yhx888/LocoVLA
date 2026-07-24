"""JSON 配置加载工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import resolve_project_path


class ConfigError(ValueError):
    """配置文件字段不完整或格式错误。"""


def load_json_config(path: str | Path) -> dict[str, Any]:
    """读取项目内 JSON 配置。"""

    config_path = resolve_project_path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"找不到配置文件: {config_path}")
    with config_path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ConfigError(f"配置文件必须是 JSON object: {config_path}")
    return data


def require_keys(data: dict[str, Any], keys: list[str], source: str) -> None:
    """检查配置必需字段。"""

    missing = [key for key in keys if key not in data]
    if missing:
        raise ConfigError(f"{source} 缺少字段: {', '.join(missing)}")

