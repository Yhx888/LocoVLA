"""关节名称映射。"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco


@dataclass(frozen=True)
class JointMap:
    ids: dict[str, int]
    qposadr: dict[str, int]
    dofadr: dict[str, int]
    ranges: dict[str, tuple[float, float] | None]


def require_object_id(model: mujoco.MjModel, obj_type: mujoco.mjtObj, name: str) -> int:
    """按名称获取 MuJoCo 对象 ID，缺失时快速失败。"""

    obj_id = mujoco.mj_name2id(model, obj_type, name)
    if obj_id < 0:
        raise ValueError(f"模型中缺少对象: {name}")
    return int(obj_id)


def build_joint_map(model: mujoco.MjModel, joint_names: tuple[str, ...] | list[str]) -> JointMap:
    ids = {name: require_object_id(model, mujoco.mjtObj.mjOBJ_JOINT, name) for name in joint_names}
    qposadr = {name: int(model.jnt_qposadr[joint_id]) for name, joint_id in ids.items()}
    dofadr = {name: int(model.jnt_dofadr[joint_id]) for name, joint_id in ids.items()}
    ranges: dict[str, tuple[float, float] | None] = {}
    for name, joint_id in ids.items():
        if bool(model.jnt_limited[joint_id]):
            ranges[name] = (float(model.jnt_range[joint_id, 0]), float(model.jnt_range[joint_id, 1]))
        else:
            ranges[name] = None
    return JointMap(ids=ids, qposadr=qposadr, dofadr=dofadr, ranges=ranges)

