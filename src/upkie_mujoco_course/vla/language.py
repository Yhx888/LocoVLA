"""把课程范围内的自然语言任务解析为结构化命令。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskInstruction:
    verb: str
    target_color: str
    stop_at_target: bool
    emergency_stop: bool
    source_text: str


def parse_task_instruction(text: str) -> TaskInstruction:
    normalized = text.strip().lower()
    color_aliases = {
        "red": ("red", "红", "红色"),
        "blue": ("blue", "蓝", "蓝色"),
        "green": ("green", "绿", "绿色"),
    }
    target_color = next(
        (color for color, aliases in color_aliases.items() if any(alias in normalized for alias in aliases)),
        "unknown",
    )
    navigate = any(word in normalized for word in ("前往", "驶向", "到", "navigate", "go to", "approach"))
    stop = any(word in normalized for word in ("停车", "停下", "停止", "stop"))
    emergency_stop = bool(stop and not navigate and target_color == "unknown")
    return TaskInstruction(
        verb="navigate" if navigate else ("stop" if emergency_stop else "unknown"),
        target_color=target_color,
        stop_at_target=bool(stop and navigate),
        emergency_stop=emergency_stop,
        source_text=text,
    )
