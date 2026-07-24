"""测试硬件遥测数据帧（HardwareTelemetryFrame）。

覆盖场景：
- 遥测帧字段序列化 / 反序列化
- 字段类型与单位约束
- 与硬件审计模块的对接
"""
import json

import pytest

from upkie_mujoco_course.hardware.telemetry import HardwareTelemetryFrame
from upkie_mujoco_course.hardware.telemetry import load_telemetry_jsonl
from upkie_mujoco_course.hardware.telemetry import write_telemetry_jsonl


def _frame(sequence: int, timestamp: float) -> HardwareTelemetryFrame:
    return HardwareTelemetryFrame(
        sequence=sequence,
        timestamp=timestamp,
        mode="armed",
        proprioception=[0.1, 0.0, -0.1],
        action=[0.0, 0.0, 0.0, 0.0, 0.2, -0.2],
        wheel_torque_nm=[0.2, -0.2],
        motor_current_a=[0.8, 0.9],
        battery_voltage_v=12.1,
        emergency_stop=False,
        fault_code=None,
        metadata={"source": "hardware_in_loop"},
    )


def test_hardware_telemetry_jsonl_round_trip_uses_shared_fields(tmp_path):
    path = write_telemetry_jsonl(tmp_path / "telemetry.jsonl", [_frame(1, 0.01), _frame(2, 0.02)])
    restored = load_telemetry_jsonl(path)
    raw = json.loads(path.read_text(encoding="utf-8").splitlines()[0])

    assert raw["schema_version"] == "1.0"
    assert {"timestamp", "proprioception", "action", "metadata"} <= set(raw)
    assert restored[1].sequence == 2
    assert restored[1].wheel_torque_nm == [0.2, -0.2]


def test_hardware_telemetry_rejects_non_monotonic_time(tmp_path):
    with pytest.raises(ValueError, match="时间戳必须严格递增"):
        write_telemetry_jsonl(tmp_path / "telemetry.jsonl", [_frame(1, 0.02), _frame(2, 0.01)])
