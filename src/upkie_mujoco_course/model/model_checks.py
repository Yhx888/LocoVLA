"""模型审计与报告。"""

from __future__ import annotations

import csv
from pathlib import Path

import mujoco

from upkie_mujoco_course.model.actuator_map import build_actuator_map
from upkie_mujoco_course.model.frame_map import build_frame_map
from upkie_mujoco_course.model.joint_map import build_joint_map
from upkie_mujoco_course.model.robot_spec import RobotSpec
from upkie_mujoco_course.model.sensor_map import build_sensor_map
from upkie_mujoco_course.utils.paths import ensure_output_dir


def audit_model(model: mujoco.MjModel, spec: RobotSpec) -> dict[str, object]:
    """返回模型审计摘要。"""

    return {
        "name": spec.name,
        "nq": int(model.nq),
        "nv": int(model.nv),
        "nu": int(model.nu),
        "nbody": int(model.nbody),
        "ngeom": int(model.ngeom),
        "njnt": int(model.njnt),
        "nsensor": int(model.nsensor),
        "joint_map": build_joint_map(model, spec.controlled_joints),
        "actuator_map": build_actuator_map(model, spec.actuator_names),
        "sensor_map": build_sensor_map(model, spec.sensor_names),
        "frame_map": build_frame_map(model),
    }


def write_model_audit(model: mujoco.MjModel, spec: RobotSpec, output_dir: Path | None = None) -> Path:
    """写出 Markdown 与 CSV 审计报告。"""

    output_dir = output_dir or ensure_output_dir("model_audit")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = audit_model(model, spec)
    joint_map = summary["joint_map"]
    actuator_map = summary["actuator_map"]

    report = output_dir / f"{spec.name}_model_report.md"
    report.write_text(
        "\n".join(
            [
                f"# {spec.name} 模型审计报告",
                "",
                f"- nq: {model.nq}",
                f"- nv: {model.nv}",
                f"- nu: {model.nu}",
                f"- bodies: {model.nbody}",
                f"- geoms: {model.ngeom}",
                f"- joints: {model.njnt}",
                f"- sensors: {model.nsensor}",
                "",
                "## 关键关节",
                *[
                    f"- {name}: qpos={joint_map.qposadr[name]}, qvel={joint_map.dofadr[name]}"
                    for name in spec.controlled_joints
                ],
                "",
                "## 执行器",
                *[
                    f"- {name}: id={actuator_map.ids[name]}, ctrlrange={actuator_map.ctrlrange[name]}"
                    for name in spec.actuator_names
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )

    with (output_dir / f"{spec.name}_joint_table.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["name", "id", "qposadr", "dofadr", "range"])
        for name in spec.controlled_joints:
            writer.writerow([name, joint_map.ids[name], joint_map.qposadr[name], joint_map.dofadr[name], joint_map.ranges[name]])

    with (output_dir / f"{spec.name}_actuator_table.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["name", "id", "ctrl_low", "ctrl_high"])
        for name in spec.actuator_names:
            low, high = actuator_map.ctrlrange[name]
            writer.writerow([name, actuator_map.ids[name], low, high])
    return report

