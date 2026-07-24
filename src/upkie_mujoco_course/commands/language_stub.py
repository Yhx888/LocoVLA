"""语言命令 stub。

本文件是 stub 实现，仅用于教学演示，不接入真实语音或 LLM 解析。
完整解析逻辑见 vla/language.py 的 parse_task_instruction()。
"""

from __future__ import annotations

from .command_types import MotionCommand


def parse_language_command(text: str) -> MotionCommand:
    """把简单语言命令解析为 MotionCommand。

    支持的命令关键词（中英文）：
    - 前进 / forward：forward_velocity=0.12
    - 后退 / back：forward_velocity=-0.12
    - 左转 / turn left：yaw_rate=0.3
    - 右转 / turn right：yaw_rate=-0.3
    - 停止 / stop：forward_velocity=0.0, yaw_rate=0.0
    """
    normalized = text.strip().lower()
    if "forward" in normalized or "前进" in normalized:
        return MotionCommand(forward_velocity=0.12, source="language_stub")
    if "back" in normalized or "后退" in normalized:
        return MotionCommand(forward_velocity=-0.12, source="language_stub")
    if "turn left" in normalized or "左转" in normalized:
        return MotionCommand(yaw_rate=0.3, source="language_stub")
    if "turn right" in normalized or "右转" in normalized:
        return MotionCommand(yaw_rate=-0.3, source="language_stub")
    if "stop" in normalized or "停止" in normalized or "停车" in normalized:
        return MotionCommand(forward_velocity=0.0, yaw_rate=0.0, source="language_stub")
    return MotionCommand(source="language_stub")
