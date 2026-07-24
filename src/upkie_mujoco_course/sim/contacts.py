"""接触读取工具。"""

from __future__ import annotations

from typing import Any

import mujoco


def read_contact_pairs(model: mujoco.MjModel, data: mujoco.MjData) -> list[tuple[str, str]]:
    """读取当前接触对名称。"""

    pairs: list[tuple[str, str]] = []
    for idx in range(data.ncon):
        contact = data.contact[idx]
        geom1 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(contact.geom1)) or str(contact.geom1)
        geom2 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(contact.geom2)) or str(contact.geom2)
        pairs.append((str(geom1), str(geom2)))
    return pairs


def wheel_ground_state(runner: Any) -> dict[str, Any]:
    """判断左右轮是否接近地面。"""

    left_name, right_name = runner.spec.wheel_joints
    left_body = int(runner.model.jnt_bodyid[runner.joint_map.ids[left_name]])
    right_body = int(runner.model.jnt_bodyid[runner.joint_map.ids[right_name]])
    floor_id = runner.frame_map.geom_ids.get("floor", -1)
    left_contact = False
    right_contact = False
    for idx in range(runner.data.ncon):
        contact = runner.data.contact[idx]
        geom1 = int(contact.geom1)
        geom2 = int(contact.geom2)
        if floor_id not in (geom1, geom2):
            continue
        other = geom2 if geom1 == floor_id else geom1
        body = int(runner.model.geom_bodyid[other])
        if body == left_body:
            left_contact = True
        if body == right_body:
            right_contact = True
    left_height = float(runner.data.xpos[left_body, 2] - runner.spec.floor_z)
    right_height = float(runner.data.xpos[right_body, 2] - runner.spec.floor_z)
    left_grounded = left_contact or left_height <= runner.left_wheel_radius + 0.01
    right_grounded = right_contact or right_height <= runner.right_wheel_radius + 0.01
    return {
        "left_contact": bool(left_grounded),
        "right_contact": bool(right_grounded),
        "both_wheels_contact": bool(left_grounded and right_grounded),
        "left_wheel_axis_height": left_height,
        "right_wheel_axis_height": right_height,
    }

