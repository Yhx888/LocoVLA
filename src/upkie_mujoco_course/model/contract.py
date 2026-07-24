"""机器人模型 v2 替换契约审计。"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import mujoco
import numpy as np

from upkie_mujoco_course.course.results import write_experiment_result
from upkie_mujoco_course.model.robot_spec import RobotSpec, load_robot_spec
from upkie_mujoco_course.sim.loader import build_mujoco_model
from upkie_mujoco_course.utils.config import load_json_config
from upkie_mujoco_course.utils.paths import project_root


REQUIRED_SENSOR_FIELDS = {
    "base_position",
    "base_quaternion",
    "base_linear_velocity",
    "base_angular_velocity",
    "joint_position",
    "joint_velocity",
}


def _model_names(model: mujoco.MjModel, object_type: mujoco.mjtObj, count: int) -> list[str]:
    return [mujoco.mj_id2name(model, object_type, index) or "" for index in range(count)]


def audit_robot_contract(
    model: mujoco.MjModel,
    spec: RobotSpec,
    raw_config: dict[str, Any],
) -> dict[str, Any]:
    """逐项检查模型、解析后规格与原始配置是否表达同一套物理语义。"""

    joint_names = _model_names(model, mujoco.mjtObj.mjOBJ_JOINT, model.njnt)
    actuator_names = _model_names(model, mujoco.mjtObj.mjOBJ_ACTUATOR, model.nu)
    free_joint_names = [
        joint_names[index]
        for index in range(model.njnt)
        if int(model.jnt_type[index]) == int(mujoco.mjtJoint.mjJNT_FREE)
    ]

    state_dimensions = raw_config.get("state_dimensions", {})
    profile = str(raw_config.get("profile", "generic"))
    controlled_joints = [str(name) for name in raw_config.get("controlled_joints", [])]
    semantics = raw_config.get("actuator_semantics", {})
    wheel_semantics = semantics.get("wheel", {})
    wheel_limit = [float(value) for value in wheel_semantics.get("limit", [])]
    wheel_directions = [float(value) for value in raw_config.get("wheel_directions", [])]
    quaternion = np.asarray(raw_config.get("default_base_quaternion", []), dtype=float)
    sensor_fields = {
        str(field.get("name", ""))
        for field in raw_config.get("sensor_contract", {}).get("fields", [])
        if isinstance(field, dict)
    }

    torque_ranges: list[list[float]] = []
    for actuator in spec.torque_actuators:
        actuator_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator.name)
        if actuator_id >= 0:
            torque_ranges.append(model.actuator_ctrlrange[actuator_id].astype(float).tolist())

    configured_actuators = list(spec.position_actuators + spec.torque_actuators)
    configured_by_joint = {item.joint: item for item in configured_actuators}
    actuator_target_joints: dict[str, str] = {}
    actuator_joint_mapping = True
    actuator_types = True
    actuator_gears = True
    actuator_ctrlranges = True
    actuator_array_order = actuator_names == spec.actuator_names
    for actuator_id, item in enumerate(configured_actuators):
        if actuator_id >= model.nu:
            actuator_joint_mapping = False
            actuator_types = False
            actuator_gears = False
            actuator_ctrlranges = False
            continue
        actuator_array_order &= actuator_names[actuator_id] == item.name
        target_joint_id = int(model.actuator_trnid[actuator_id, 0])
        target_joint = (
            mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, target_joint_id)
            or ""
        )
        actuator_target_joints[item.name] = target_joint
        actuator_joint_mapping &= (
            int(model.actuator_trntype[actuator_id])
            == int(mujoco.mjtTrn.mjTRN_JOINT)
            and target_joint == item.joint
        )
        common_type_ok = (
            int(model.actuator_dyntype[actuator_id])
            == int(mujoco.mjtDyn.mjDYN_NONE)
            and int(model.actuator_gaintype[actuator_id])
            == int(mujoco.mjtGain.mjGAIN_FIXED)
        )
        if item.kind == "position":
            type_ok = (
                common_type_ok
                and int(model.actuator_biastype[actuator_id])
                == int(mujoco.mjtBias.mjBIAS_AFFINE)
                and np.isclose(model.actuator_gainprm[actuator_id, 0], item.gain)
                and np.isclose(model.actuator_biasprm[actuator_id, 1], -item.gain)
            )
            expected_gear = 1.0
        else:
            type_ok = (
                common_type_ok
                and int(model.actuator_biastype[actuator_id])
                == int(mujoco.mjtBias.mjBIAS_NONE)
                and np.isclose(model.actuator_gainprm[actuator_id, 0], 1.0)
            )
            expected_gear = item.gain
        actuator_types &= bool(type_ok)
        actuator_gears &= bool(
            np.isclose(model.actuator_gear[actuator_id, 0], expected_gear)
        )
        actuator_ctrlranges &= bool(
            model.actuator_ctrllimited[actuator_id]
            and np.allclose(model.actuator_ctrlrange[actuator_id], item.ctrlrange)
        )

    controlled_joint_actuators = [
        configured_by_joint[joint].name
        for joint in controlled_joints
        if joint in configured_by_joint
    ]
    actuator_controlled_joint_order = (
        controlled_joints == list(spec.controlled_joints)
        and len(controlled_joint_actuators) == len(controlled_joints)
        and all(
            actuator_target_joints.get(actuator_name) == joint
            for joint, actuator_name in zip(
                controlled_joints,
                controlled_joint_actuators,
            )
        )
    )
    raw_actuators = list(raw_config.get("position_actuators", [])) + list(
        raw_config.get("torque_actuators", [])
    )
    raw_actuator_names = [str(item.get("name", "")) for item in raw_actuators]
    raw_actuator_declarations = len(raw_actuators) == len(configured_actuators)
    position_count = len(raw_config.get("position_actuators", []))
    for index, (raw_actuator, actuator) in enumerate(
        zip(raw_actuators, configured_actuators)
    ):
        gain_key = "kp" if index < position_count else "gear"
        raw_range = raw_actuator.get("ctrlrange", [])
        raw_actuator_declarations &= bool(
            str(raw_actuator.get("name", "")) == actuator.name
            and str(raw_actuator.get("joint", "")) == actuator.joint
            and np.isclose(float(raw_actuator.get(gain_key, float("nan"))), actuator.gain)
            and len(raw_range) == 2
            and np.allclose(raw_range, actuator.ctrlrange)
        )
    configured_joint_names = [item.joint for item in configured_actuators]
    is_upkie_v2 = profile == "upkie_v2"
    upkie_profile = (
        not is_upkie_v2
        or (
            len(controlled_joints) == 6
            and len(spec.position_actuators) == 4
            and len(spec.torque_actuators) == 2
            and len(wheel_directions) == 2
        )
    )

    checks = {
        "schema_version_v2": raw_config.get("schema_version") == "2.0",
        "state_dimensions": (
            int(state_dimensions.get("nq", -1)) == model.nq
            and int(state_dimensions.get("nv", -1)) == model.nv
            and int(state_dimensions.get("nu", -1)) == model.nu
        ),
        "floating_base": (
            bool(raw_config.get("floating_base")) == spec.floating_base
            and bool(free_joint_names) == spec.floating_base
        ),
        "root_joint": (
            free_joint_names == [str(raw_config.get("root_joint_name", ""))]
            if spec.floating_base
            else not free_joint_names
        ),
        "controlled_joint_mapping": (
            controlled_joints == list(spec.controlled_joints)
            and len(controlled_joints) == len(set(controlled_joints))
            and set(controlled_joints) <= set(joint_names)
            and set(configured_joint_names) == set(controlled_joints)
        ),
        "actuator_count": (
            model.nu == len(configured_actuators)
            and len(configured_actuators) == len(raw_actuators)
            and spec.actuator_names == raw_actuator_names
            and set(spec.actuator_names) == set(actuator_names)
        ),
        "raw_actuator_declarations": bool(raw_actuator_declarations),
        "upkie_profile": bool(upkie_profile),
        "actuator_array_order": bool(actuator_array_order),
        "actuator_joint_mapping": bool(actuator_joint_mapping),
        "actuator_controlled_joint_order": bool(actuator_controlled_joint_order),
        "actuator_types": bool(actuator_types),
        "actuator_gears": bool(actuator_gears),
        "actuator_ctrlranges": bool(actuator_ctrlranges),
        "wheel_torque_semantics": (
            not is_upkie_v2
            or (
                wheel_semantics.get("command") == "torque"
                and wheel_semantics.get("unit") == "N*m"
            )
        ),
        "wheel_torque_limit": (
            not is_upkie_v2
            or (
                len(wheel_limit) == 2
                and len(torque_ranges) == len(spec.torque_actuators)
                and all(np.allclose(ctrlrange, wheel_limit) for ctrlrange in torque_ranges)
            )
        ),
        "opposite_wheel_directions": (
            not is_upkie_v2
            or (
                len(wheel_directions) == 2
                and wheel_directions[0] * wheel_directions[1] < 0.0
            )
        ),
        "normalized_base_quaternion": (
            quaternion.shape == (4,) and abs(float(np.linalg.norm(quaternion)) - 1.0) <= 1e-6
        ),
        "sensor_contract_fields": REQUIRED_SENSOR_FIELDS <= sensor_fields,
        "positive_timestep": (
            float(raw_config.get("timestep", 0.0)) > 0.0
            and float(model.opt.timestep) > 0.0
            and int(raw_config.get("frame_skip", 0)) > 0
        ),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    torque_limit_nm = max((abs(value) for value in wheel_limit), default=0.0)
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "metrics": {
            "nq": float(model.nq),
            "nv": float(model.nv),
            "nu": float(model.nu),
            "free_joint_count": float(len(free_joint_names)),
            "controlled_joint_count": float(len(controlled_joints)),
            "wheel_torque_limit_nm": float(torque_limit_nm),
            "contract_check_ratio": float(sum(checks.values()) / len(checks)),
            "failed_check_count": float(len(failed_checks)),
        },
        "details": {
            "joint_names": joint_names,
            "actuator_names": actuator_names,
            "actuator_target_joints": actuator_target_joints,
            "controlled_joint_actuators": controlled_joint_actuators,
            "free_joint_names": free_joint_names,
            "wheel_ctrlranges_nm": torque_ranges,
            "sensor_fields": sorted(sensor_fields),
            "failed_checks": failed_checks,
        },
    }


def _resolve_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    return root if root.is_absolute() else project_root() / root


def _write_contract_plot(checks: dict[str, bool], path: Path) -> None:
    labels = list(checks)
    values = [1.0 if checks[label] else 0.0 for label in labels]
    colors = ["#17745a" if value else "#d36b27" for value in values]
    figure, axis = plt.subplots(figsize=(9.2, 5.8))
    axis.barh(labels, values, color=colors)
    axis.set(xlim=(0.0, 1.0), xlabel="pass (1) / fail (0)", title="Chapter 11: robot replacement contract")
    axis.grid(axis="x", alpha=0.2)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def run_model_contract_lab(
    *,
    output_root: str | Path = "outputs",
    inject_fault: str | None = None,
    source_root: str | Path | None = None,
) -> Path:
    """运行关卡 11 审计，并保存结果、日志、图表和作品集证据。"""

    raw_config = deepcopy(load_json_config("configs/robot/upkie.json"))
    if inject_fault == "wheel_semantics":
        raw_config["actuator_semantics"]["wheel"].update(
            {"command": "velocity", "unit": "rad/s"}
        )
    elif inject_fault == "wheel_direction":
        raw_config["wheel_directions"] = [1.0, 1.0]
    elif inject_fault is not None:
        raise ValueError(f"不支持的故障类型: {inject_fault}")

    spec = load_robot_spec()
    model = build_mujoco_model(spec)
    audit = audit_robot_contract(model, spec, raw_config)
    root = _resolve_output_root(output_root)
    suffix = f"_{inject_fault}" if inject_fault else ""
    result_path = root / "results" / f"model_contract_11{suffix}.json"
    log_path = root / "logs" / f"model_contract_11{suffix}.json"
    plot_path = root / "plots" / f"model_contract_11{suffix}.png"
    _write_contract_plot(audit["checks"], plot_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        json.dumps(
            {"chapter_id": "11", "inject_fault": inject_fault, "audit": audit},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    written_result = write_experiment_result(
        result_path,
        chapter_id="11",
        seed=0,
        config={
            "schema_version": raw_config.get("schema_version"),
            "robot": raw_config.get("name"),
            "model_path": raw_config.get("model_path"),
            "inject_fault": inject_fault,
        },
        metrics=audit["metrics"],
        pass_conditions={
            "contract_check_ratio": {"operator": "==", "value": 1.0},
            "failed_check_count": {"operator": "==", "value": 0.0},
        },
        plots=[str(plot_path)],
        logs=[str(log_path)],
        root=source_root,
    )
    result = json.loads(written_result.read_text(encoding="utf-8"))
    portfolio_name = f"fault_{inject_fault}.json" if inject_fault else "evidence.json"
    portfolio_path = root / "portfolio" / "11" / portfolio_name
    portfolio_path.parent.mkdir(parents=True, exist_ok=True)
    portfolio_path.write_text(
        json.dumps(
            {
                "chapter_id": "11",
                "passed": result["passed"],
                "result_path": str(written_result),
                "plots": result["plots"],
                "logs": result["logs"],
                "metrics": result["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return written_result
