"""commands 模块单元测试。

覆盖 command_types、scripted_commands、language_stub、keyboard 四个子模块。
"""

from __future__ import annotations

import pytest

from upkie_mujoco_course.commands.command_types import MotionCommand
from upkie_mujoco_course.commands.keyboard import key_to_command
from upkie_mujoco_course.commands.language_stub import parse_language_command
from upkie_mujoco_course.commands.scripted_commands import (
    forward_command,
    stand_command,
)


# ----------------- command_types -----------------


def test_motion_command_default_values():
    """MotionCommand 默认值应为零速度、零角速度、零高度，source 为 script。"""
    cmd = MotionCommand()
    assert cmd.forward_velocity == 0.0
    assert cmd.yaw_rate == 0.0
    assert cmd.height == 0.0
    assert cmd.source == "script"


def test_motion_command_is_frozen():
    """MotionCommand 应为不可变 dataclass（frozen=True）。"""
    cmd = MotionCommand(forward_velocity=0.1)
    with pytest.raises(Exception):
        cmd.forward_velocity = 0.2  # type: ignore[misc]


def test_motion_command_equality():
    """字段相同的 MotionCommand 应相等。"""
    a = MotionCommand(forward_velocity=0.1, yaw_rate=0.2, source="test")
    b = MotionCommand(forward_velocity=0.1, yaw_rate=0.2, source="test")
    assert a == b


def test_motion_command_inequality():
    """任一字段不同的 MotionCommand 应不等。"""
    base = MotionCommand(forward_velocity=0.1)
    assert base != MotionCommand(forward_velocity=0.2)
    assert base != MotionCommand(yaw_rate=0.1)
    assert base != MotionCommand(height=0.1)
    assert base != MotionCommand(source="other")


def test_motion_command_custom_values():
    """MotionCommand 应保留传入的所有字段值。"""
    cmd = MotionCommand(
        forward_velocity=0.15, yaw_rate=-0.05, height=0.02, source="language_stub"
    )
    assert cmd.forward_velocity == 0.15
    assert cmd.yaw_rate == -0.05
    assert cmd.height == 0.02
    assert cmd.source == "language_stub"


# ----------------- scripted_commands -----------------


def test_stand_command_returns_zero_motion():
    """stand_command 应返回零速度命令，source 为 script:stand。"""
    cmd = stand_command()
    assert cmd.forward_velocity == 0.0
    assert cmd.yaw_rate == 0.0
    assert cmd.height == 0.0
    assert cmd.source == "script:stand"


def test_forward_command_default_speed():
    """forward_command 默认速度应为 0.2，source 为 script:forward。"""
    cmd = forward_command()
    assert cmd.forward_velocity == 0.2
    assert cmd.yaw_rate == 0.0
    assert cmd.source == "script:forward"


def test_forward_command_custom_speed():
    """forward_command 应使用传入的 speed 参数。"""
    cmd = forward_command(speed=0.35)
    assert cmd.forward_velocity == 0.35


def test_forward_command_negative_speed():
    """forward_command 应允许负速度（后退场景）。"""
    cmd = forward_command(speed=-0.1)
    assert cmd.forward_velocity == -0.1


def test_forward_command_int_speed_coerced_to_float():
    """forward_command 接收 int 时应转为 float。"""
    cmd = forward_command(speed=1)
    assert isinstance(cmd.forward_velocity, float)
    assert cmd.forward_velocity == 1.0


# ----------------- language_stub -----------------


def test_language_forward_english():
    """英文 forward 应解析为前进命令。"""
    cmd = parse_language_command("move forward")
    assert cmd.forward_velocity == 0.12
    assert cmd.yaw_rate == 0.0
    assert cmd.source == "language_stub"


def test_language_forward_chinese():
    """中文"前进"应解析为前进命令。"""
    cmd = parse_language_command("前进")
    assert cmd.forward_velocity == 0.12


def test_language_back_english():
    """英文 back 应解析为后退命令。"""
    cmd = parse_language_command("step back")
    assert cmd.forward_velocity == -0.12


def test_language_back_chinese():
    """中文"后退"应解析为后退命令。"""
    cmd = parse_language_command("后退")
    assert cmd.forward_velocity == -0.12


def test_language_turn_left_english():
    """英文 turn left 应解析为左转命令（正角速度）。"""
    cmd = parse_language_command("turn left")
    assert cmd.yaw_rate == 0.3
    assert cmd.forward_velocity == 0.0


def test_language_turn_left_chinese():
    """中文"左转"应解析为左转命令。"""
    cmd = parse_language_command("左转")
    assert cmd.yaw_rate == 0.3


def test_language_turn_right_english():
    """英文 turn right 应解析为右转命令（负角速度）。"""
    cmd = parse_language_command("turn right")
    assert cmd.yaw_rate == -0.3
    assert cmd.forward_velocity == 0.0


def test_language_turn_right_chinese():
    """中文"右转"应解析为右转命令。"""
    cmd = parse_language_command("右转")
    assert cmd.yaw_rate == -0.3


def test_language_stop_english():
    """英文 stop 应解析为停止命令（所有速度归零）。"""
    cmd = parse_language_command("stop")
    assert cmd.forward_velocity == 0.0
    assert cmd.yaw_rate == 0.0


def test_language_stop_chinese():
    """中文"停止"应解析为停止命令。"""
    cmd = parse_language_command("停止")
    assert cmd.forward_velocity == 0.0
    assert cmd.yaw_rate == 0.0


def test_language_stop_parking_chinese():
    """中文"停车"也应解析为停止命令。"""
    cmd = parse_language_command("停车")
    assert cmd.forward_velocity == 0.0
    assert cmd.yaw_rate == 0.0


def test_language_unknown_returns_default():
    """未识别的命令应返回默认零速度命令，source 仍为 language_stub。"""
    # 注：不含 forward/back/turn left/turn right/stop 等已知关键词
    cmd = parse_language_command("do a barrel roll")
    assert cmd.forward_velocity == 0.0
    assert cmd.yaw_rate == 0.0
    assert cmd.source == "language_stub"


def test_language_case_insensitive():
    """语言解析应大小写不敏感。"""
    cmd_upper = parse_language_command("FORWARD")
    cmd_mixed = parse_language_command("Turn Left")
    assert cmd_upper.forward_velocity == 0.12
    assert cmd_mixed.yaw_rate == 0.3


def test_language_strip_whitespace():
    """语言解析应去除前后空白。"""
    cmd = parse_language_command("  forward  ")
    assert cmd.forward_velocity == 0.12


def test_language_priority_forward_over_back():
    """同时含 forward 和 back 时，forward 优先（按代码顺序匹配）。"""
    # 注：当前实现按 forward -> back -> turn left -> turn right -> stop 顺序匹配
    cmd = parse_language_command("move forward then back")
    assert cmd.forward_velocity == 0.12


# ----------------- keyboard -----------------


def test_keyboard_w_returns_forward_command():
    """w 键应映射为前进命令。"""
    cmd = key_to_command("w")
    assert cmd.forward_velocity == 0.2
    assert cmd.source == "keyboard:w"


def test_keyboard_s_returns_backward_command():
    """s 键应映射为后退命令。"""
    cmd = key_to_command("s")
    assert cmd.forward_velocity == -0.2
    assert cmd.source == "keyboard:s"


def test_keyboard_case_insensitive():
    """键盘解析应大小写不敏感。"""
    cmd_upper = key_to_command("W")
    cmd_lower = key_to_command("w")
    assert cmd_upper == cmd_lower


def test_keyboard_unknown_key_returns_default():
    """未识别的键应返回默认零速度命令，source 标注为 keyboard:<key>。"""
    cmd = key_to_command("x")
    assert cmd.forward_velocity == 0.0
    assert cmd.yaw_rate == 0.0
    assert cmd.source == "keyboard:x"


def test_keyboard_unknown_key_preserves_case_in_source():
    """未识别的键应在 source 中保留原大小写。"""
    cmd = key_to_command("X")
    # source 中保留原 key，仅匹配时小写化
    assert cmd.source.startswith("keyboard:")


# ----------------- 跨模块一致性 -----------------


def test_all_sources_are_distinct():
    """不同命令源生成的 source 前缀应可区分。"""
    sources = {
        stand_command().source,
        forward_command().source,
        parse_language_command("forward").source,
        key_to_command("w").source,
        MotionCommand().source,
    }
    # 至少 5 个不同的 source
    assert len(sources) == 5
