"""仿真、台架与实机共享的硬件遥测契约。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class HardwareTelemetryFrame:
    sequence: int
    timestamp: float
    mode: str
    proprioception: list[float]
    action: list[float]
    wheel_torque_nm: list[float]
    motor_current_a: list[float]
    battery_voltage_v: float
    emergency_stop: bool
    fault_code: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        _validate_frame(self)
        data = asdict(self)
        return {"schema_version": "1.0", **data}


def _finite(values: Iterable[float]) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def _validate_frame(frame: HardwareTelemetryFrame) -> None:
    if frame.sequence < 0:
        raise ValueError("序号不能为负数")
    if not math.isfinite(frame.timestamp) or frame.timestamp < 0.0:
        raise ValueError("时间戳必须是非负有限值")
    if not frame.mode:
        raise ValueError("运行模式不能为空")
    if len(frame.action) != 6:
        raise ValueError("动作必须对应 6 个执行器")
    if len(frame.wheel_torque_nm) != 2 or len(frame.motor_current_a) != 2:
        raise ValueError("轮端力矩和电流必须各包含左右轮两个值")
    numeric = [
        *frame.proprioception,
        *frame.action,
        *frame.wheel_torque_nm,
        *frame.motor_current_a,
        frame.battery_voltage_v,
    ]
    if not _finite(numeric):
        raise ValueError("遥测数值必须是有限值")
    if frame.battery_voltage_v <= 0.0:
        raise ValueError("电池电压必须为正数")


def write_telemetry_jsonl(
    path: str | Path,
    frames: Iterable[HardwareTelemetryFrame],
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    previous_sequence = -1
    previous_timestamp = -1.0
    for frame in frames:
        if frame.sequence <= previous_sequence:
            raise ValueError("序号必须严格递增")
        if frame.timestamp <= previous_timestamp:
            raise ValueError("时间戳必须严格递增")
        lines.append(json.dumps(frame.to_dict(), ensure_ascii=False, separators=(",", ":")))
        previous_sequence = frame.sequence
        previous_timestamp = frame.timestamp
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output


def load_telemetry_jsonl(path: str | Path) -> list[HardwareTelemetryFrame]:
    frames: list[HardwareTelemetryFrame] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        if data.pop("schema_version", None) != "1.0":
            raise ValueError(f"第 {line_number} 行的遥测版本不受支持")
        frame = HardwareTelemetryFrame(**data)
        _validate_frame(frame)
        if frames and frame.sequence <= frames[-1].sequence:
            raise ValueError("序号必须严格递增")
        if frames and frame.timestamp <= frames[-1].timestamp:
            raise ValueError("时间戳必须严格递增")
        frames.append(frame)
    return frames
