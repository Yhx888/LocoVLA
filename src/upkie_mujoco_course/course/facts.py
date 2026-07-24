"""课程事实漂移检查。"""

from __future__ import annotations

import re
import numpy as np

from upkie_mujoco_course.course.manifest import load_course_manifest
from upkie_mujoco_course.model.robot_spec import load_robot_spec
from upkie_mujoco_course.sim.loader import build_mujoco_model
from upkie_mujoco_course.utils.config import load_json_config
from upkie_mujoco_course.utils.paths import project_root


def check_course_facts() -> list[str]:
    root = project_root()
    errors: list[str] = []
    manifest = load_course_manifest()
    if len(manifest["chapters"]) != 58:
        errors.append("课程清单必须包含 58 个唯一关卡")

    robot_config = load_json_config("configs/robot/upkie.json")
    if robot_config.get("schema_version") != "2.0":
        errors.append("机器人物理配置必须声明 schema_version=2.0")
    if robot_config.get("state_dimensions") != {"nq": 13, "nv": 12, "nu": 6}:
        errors.append("机器人物理配置的状态维度契约漂移")
    wheel_semantics = robot_config.get("actuator_semantics", {}).get("wheel", {})
    if wheel_semantics.get("command") != "torque" or wheel_semantics.get("unit") != "N*m":
        errors.append("轮端动作必须声明为 N*m 力矩语义")

    spec = load_robot_spec()
    model = build_mujoco_model(spec)
    if (model.nq, model.nv, model.nu) != (13, 12, 6):
        errors.append(f"模型维度漂移: {(model.nq, model.nv, model.nu)}")
    if len(spec.torque_actuators) != 2 or any(item.ctrlrange != (-1.0, 1.0) for item in spec.torque_actuators):
        errors.append("轮端必须是两个 ±1 N·m 力矩执行器")
    if not np.isclose(np.linalg.norm(spec.default_base_quaternion), 1.0, atol=1e-6):
        errors.append("初始基座四元数不是单位四元数")

    for chapter in manifest["chapters"]:
        tutorial = root / chapter["tutorial"]
        if not tutorial.is_file():
            errors.append(f"缺少教程: {chapter['tutorial']}")
        for command in chapter["commands"]:
            match = re.match(r"python\s+(scripts/\S+\.py)", command)
            if match and not (root / match.group(1)).is_file():
                errors.append(f"命令入口不存在: {match.group(1)}")

    public_contracts = [
        root / "src" / "upkie_mujoco_course" / "course" / "results.py",
        root / "src" / "upkie_mujoco_course" / "vla" / "contracts.py",
        root / "src" / "upkie_mujoco_course" / "hardware" / "telemetry.py",
    ]
    for path in public_contracts:
        if not path.is_file():
            errors.append(f"缺少公开契约: {path.relative_to(root)}")

    canonical_files = [root / "README.md", root / "docs" / "SYLLABUS.md", root / "docs" / "guides" / "tutorial-writing-spec.md"]
    # P-MISS-013：将 CLAUDE.md 和 AGENTS.md 纳入事实漂移扫描
    canonical_files.extend([root / "CLAUDE.md", root / "AGENTS.md"])
    canonical_files.extend(root.glob("tutorials/v2/*/README.md"))
    forbidden = ("nq=6", "nv=6", "轮端速度执行器", "速度伺服轮端")
    for path in canonical_files:
        if not path.is_file():
            errors.append(f"缺少事实扫描文件: {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden:
            if phrase in text:
                errors.append(f"{path.relative_to(root)} 含旧事实: {phrase}")

    # P-MISS-013：校验 CLAUDE.md / AGENTS.md 中 nq/nv/nu 数值与 configs/robot/upkie.json 一致
    expected_dims = robot_config.get("state_dimensions", {})
    if expected_dims:
        dim_pattern = re.compile(r"nq\s*=\s*(\d+)\s*,\s*nv\s*=\s*(\d+)\s*,\s*nu\s*=\s*(\d+)")
        for fname in ("CLAUDE.md", "AGENTS.md"):
            fpath = root / fname
            if not fpath.is_file():
                continue
            ftext = fpath.read_text(encoding="utf-8")
            for match in dim_pattern.finditer(ftext):
                found_dims = {
                    "nq": int(match.group(1)),
                    "nv": int(match.group(2)),
                    "nu": int(match.group(3)),
                }
                if found_dims != expected_dims:
                    errors.append(
                        f"{fname} 状态维度漂移: 文档 {found_dims} 与 upkie.json {expected_dims} 不一致"
                    )
    return errors
