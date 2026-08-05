"""测试模型契约（model.contract）审计。

覆盖场景：
- audit_robot_contract 检查 nq / nv / nu 一致性
- 执行器单位与范围符合 robot_spec
- 传感器契约（sensor_contract）字段完整
"""
from copy import deepcopy
from dataclasses import replace
import json

import mujoco

from upkie_mujoco_course.model.contract import audit_robot_contract
from upkie_mujoco_course.model.contract import run_model_contract_lab
from upkie_mujoco_course.model.robot_spec import load_robot_spec
from upkie_mujoco_course.model.robot_spec import ActuatorSpec
from upkie_mujoco_course.sim.loader import build_mujoco_model
from upkie_mujoco_course.utils.config import load_json_config


def _audit(config=None):
    spec = load_robot_spec()
    model = build_mujoco_model(spec)
    return audit_robot_contract(
        model,
        spec,
        load_json_config("configs/robot/upkie.json") if config is None else config,
    )


def test_current_upkie_satisfies_robot_replacement_contract():
    report = _audit()
    assert report["passed"] is True
    assert all(report["checks"].values())
    assert report["metrics"]["nq"] == 13.0
    assert report["metrics"]["wheel_torque_limit_nm"] == 1.0


def test_robot_contract_rejects_wheel_actuator_connected_to_hip_joint():
    spec = load_robot_spec()
    model = build_mujoco_model(spec)
    wheel_actuator_id = mujoco.mj_name2id(
        model,
        mujoco.mjtObj.mjOBJ_ACTUATOR,
        "left_wheel_motor",
    )
    hip_joint_id = mujoco.mj_name2id(
        model,
        mujoco.mjtObj.mjOBJ_JOINT,
        "left_hip",
    )
    model.actuator_trnid[wheel_actuator_id, 0] = hip_joint_id

    report = audit_robot_contract(
        model,
        spec,
        load_json_config("configs/robot/upkie.json"),
    )

    assert report["passed"] is False
    assert report["checks"]["actuator_joint_mapping"] is False


def test_robot_contract_rejects_actuator_array_order_mismatch():
    spec = load_robot_spec()
    swapped = replace(
        spec,
        position_actuators=(
            spec.position_actuators[1],
            spec.position_actuators[0],
            *spec.position_actuators[2:],
        ),
    )
    report = audit_robot_contract(
        build_mujoco_model(spec),
        swapped,
        load_json_config("configs/robot/upkie.json"),
    )

    assert report["passed"] is False
    assert report["checks"]["actuator_array_order"] is False


def test_robot_contract_rejects_wrong_actuator_gear_and_type():
    spec = load_robot_spec()
    model = build_mujoco_model(spec)
    wheel_id = mujoco.mj_name2id(
        model,
        mujoco.mjtObj.mjOBJ_ACTUATOR,
        "left_wheel_motor",
    )
    model.actuator_gear[wheel_id, 0] = 2.0
    model.actuator_biastype[wheel_id] = int(mujoco.mjtBias.mjBIAS_AFFINE)

    report = audit_robot_contract(
        model,
        spec,
        load_json_config("configs/robot/upkie.json"),
    )

    assert report["passed"] is False
    assert report["checks"]["actuator_gears"] is False
    assert report["checks"]["actuator_types"] is False


def test_robot_contract_rejects_raw_actuator_declaration_mismatch():
    spec = load_robot_spec()
    raw = deepcopy(load_json_config("configs/robot/upkie.json"))
    raw["torque_actuators"][0]["gear"] = 3.0

    report = audit_robot_contract(build_mujoco_model(spec), spec, raw)

    assert report["passed"] is False
    assert report["checks"]["raw_actuator_declarations"] is False


def test_robot_contract_accepts_different_valid_topology():
    xml = """
    <mujoco>
      <option timestep="0.005"/>
        <worldbody>
          <body name="base">
            <freejoint name="root"/>
            <geom type="sphere" size="0.1"/>
            <body><joint name="leg" type="hinge"/><geom type="sphere" size="0.05"/></body>
            <body><joint name="drive" type="hinge"/><geom type="sphere" size="0.05"/></body>
          </body>
      </worldbody>
      <actuator>
        <position name="leg_servo" joint="leg" kp="10" ctrllimited="true" ctrlrange="-1 1"/>
        <motor name="drive_motor" joint="drive" gear="2" ctrllimited="true" ctrlrange="-2 2"/>
      </actuator>
    </mujoco>
    """
    model = mujoco.MjModel.from_xml_string(xml)
    base = load_robot_spec()
    spec = replace(
        base,
        controlled_joints=("leg", "drive"),
        leg_joints=("leg",),
        wheel_joints=("drive",),
        wheel_directions=(1.0,),
        position_actuators=(ActuatorSpec("leg_servo", "leg", "position", 10.0, (-1.0, 1.0)),),
        torque_actuators=(ActuatorSpec("drive_motor", "drive", "torque", 2.0, (-2.0, 2.0)),),
    )
    raw = deepcopy(load_json_config("configs/robot/upkie.json"))
    raw.update(
        {
            "profile": "generic",
            "controlled_joints": ["leg", "drive"],
            "leg_joints": ["leg"],
            "wheel_joints": ["drive"],
            "wheel_directions": [1.0],
            "position_actuators": [
                {"name": "leg_servo", "joint": "leg", "kp": 10.0, "ctrlrange": [-1.0, 1.0]}
            ],
            "torque_actuators": [
                {"name": "drive_motor", "joint": "drive", "gear": 2.0, "ctrlrange": [-2.0, 2.0]}
            ],
            "state_dimensions": {"nq": model.nq, "nv": model.nv, "nu": model.nu},
            "timestep": 0.005,
            "frame_skip": 1,
            "actuator_semantics": {
                "leg": {"command": "position", "unit": "rad"},
                "wheel": {"command": "torque", "unit": "N*m", "limit": [-2.0, 2.0]},
            },
        }
    )

    report = audit_robot_contract(model, spec, raw)

    assert report["passed"] is True, report["details"]["failed_checks"]


def test_robot_contract_rejects_velocity_semantics_for_wheel_torque():
    config = deepcopy(load_json_config("configs/robot/upkie.json"))
    config["actuator_semantics"]["wheel"]["command"] = "velocity"
    config["actuator_semantics"]["wheel"]["unit"] = "rad/s"
    report = _audit(config)

    assert report["passed"] is False
    assert report["checks"]["wheel_torque_semantics"] is False


def test_robot_contract_rejects_equal_wheel_directions():
    config = deepcopy(load_json_config("configs/robot/upkie.json"))
    config["wheel_directions"] = [1.0, 1.0]
    report = _audit(config)

    assert report["passed"] is False
    assert report["checks"]["opposite_wheel_directions"] is False


def test_model_contract_lab_writes_result_log_plot_and_portfolio(tmp_path):
    result_path = run_model_contract_lab(output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["chapter_id"] == "11"
    assert result["passed"] is True
    assert (tmp_path / result["plots"][0]).is_file()
    assert (tmp_path / result["logs"][0]).is_file()
    assert (tmp_path / "portfolio" / "11" / "evidence.json").is_file()


def test_model_contract_lab_exposes_injected_wheel_semantics_fault(tmp_path):
    result_path = run_model_contract_lab(
        output_root=tmp_path,
        inject_fault="wheel_semantics",
        source_root=tmp_path,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / result["logs"][0]).read_text(encoding="utf-8"))

    assert result["passed"] is False
    assert log["audit"]["checks"]["wheel_torque_semantics"] is False
    assert not (tmp_path / "portfolio" / "11" / "evidence.json").exists()
    assert (tmp_path / "portfolio" / "11" / "fault_wheel_semantics.json").is_file()
