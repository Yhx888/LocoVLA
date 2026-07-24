"""机器人规格配置。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from upkie_mujoco_course.utils.config import load_json_config, require_keys
from upkie_mujoco_course.utils.paths import resolve_project_path


@dataclass(frozen=True)
class ActuatorSpec:
    """执行器配置。"""

    name: str
    joint: str
    kind: str
    gain: float
    ctrlrange: tuple[float, float]


@dataclass(frozen=True)
class RobotSpec:
    """模型可替换边界。"""

    name: str
    description: str
    package_dir: Path
    model_path: Path
    model_format: str
    base_body: str
    floating_base: bool
    root_joint_name: str
    default_base_position: tuple[float, float, float]
    default_base_quaternion: tuple[float, float, float, float]
    equilibrium_pitch_rad: float
    floor_z: float
    timestep: float
    frame_skip: int
    wheel_radius_fallback: float
    wheel_joints: tuple[str, ...]
    wheel_directions: tuple[float, ...]
    leg_joints: tuple[str, ...]
    controlled_joints: tuple[str, ...]
    position_actuators: tuple[ActuatorSpec, ...]
    torque_actuators: tuple[ActuatorSpec, ...]
    sensor_names: tuple[str, ...]
    default_pose: dict[str, dict[str, float]]
    notes: str

    @property
    def actuator_names(self) -> list[str]:
        return [item.name for item in self.position_actuators + self.torque_actuators]


def _parse_position_actuator(raw: dict[str, Any]) -> ActuatorSpec:
    return ActuatorSpec(
        name=str(raw["name"]),
        joint=str(raw["joint"]),
        kind="position",
        gain=float(raw["kp"]),
        ctrlrange=(float(raw["ctrlrange"][0]), float(raw["ctrlrange"][1])),
    )


def _parse_torque_actuator(raw: dict[str, Any]) -> ActuatorSpec:
    return ActuatorSpec(
        name=str(raw["name"]),
        joint=str(raw["joint"]),
        kind="torque",
        gain=float(raw.get("gear", 1.0)),
        ctrlrange=(float(raw["ctrlrange"][0]), float(raw["ctrlrange"][1])),
    )


def load_robot_spec(path: str | Path = "configs/robot/upkie.json") -> RobotSpec:
    """从 JSON 加载机器人规格。"""

    data = load_json_config(path)
    require_keys(
        data,
        [
            "name",
            "package_dir",
            "model_path",
            "model_format",
            "base_body",
            "floating_base",
            "root_joint_name",
            "default_base_position",
            "default_base_quaternion",
            "equilibrium_pitch_rad",
            "floor_z",
            "timestep",
            "frame_skip",
            "wheel_joints",
            "wheel_directions",
            "leg_joints",
            "controlled_joints",
            "position_actuators",
            "torque_actuators",
            "default_pose",
        ],
        str(path),
    )
    model_format = str(data["model_format"]).lower()
    if model_format not in {"urdf", "mjcf"}:
        raise ValueError(f"不支持的模型格式: {model_format}")
    return RobotSpec(
        name=str(data["name"]),
        description=str(data.get("description", "")),
        package_dir=resolve_project_path(data["package_dir"]),
        model_path=resolve_project_path(data["model_path"]),
        model_format=model_format,
        base_body=str(data["base_body"]),
        floating_base=bool(data["floating_base"]),
        root_joint_name=str(data["root_joint_name"]),
        default_base_position=tuple(float(value) for value in data["default_base_position"]),
        default_base_quaternion=tuple(float(value) for value in data["default_base_quaternion"]),
        equilibrium_pitch_rad=float(data["equilibrium_pitch_rad"]),
        floor_z=float(data["floor_z"]),
        timestep=float(data["timestep"]),
        frame_skip=int(data["frame_skip"]),
        wheel_radius_fallback=float(data.get("wheel_radius_fallback", 0.06)),
        wheel_joints=tuple(str(item) for item in data["wheel_joints"]),
        wheel_directions=tuple(float(item) for item in data["wheel_directions"]),
        leg_joints=tuple(str(item) for item in data["leg_joints"]),
        controlled_joints=tuple(str(item) for item in data["controlled_joints"]),
        position_actuators=tuple(_parse_position_actuator(item) for item in data["position_actuators"]),
        torque_actuators=tuple(_parse_torque_actuator(item) for item in data["torque_actuators"]),
        sensor_names=tuple(str(item) for item in data.get("sensor_names", [])),
        default_pose={
            str(pose_name): {str(joint): float(value) for joint, value in pose.items()}
            for pose_name, pose in data["default_pose"].items()
        },
        notes=str(data.get("notes", "")),
    )
