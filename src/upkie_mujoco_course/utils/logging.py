"""日志工具。"""

from __future__ import annotations


def format_key_values(values: dict[str, object]) -> str:
    """把诊断字段格式化为一行日志。"""

    return " | ".join(f"{key}={value}" for key, value in values.items())

