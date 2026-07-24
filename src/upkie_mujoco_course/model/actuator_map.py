"""执行器名称映射。"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco


@dataclass(frozen=True)
class ActuatorMap:
    ids: dict[str, int]
    ctrlrange: dict[str, tuple[float, float]]


def build_actuator_map(model: mujoco.MjModel, actuator_names: list[str] | tuple[str, ...]) -> ActuatorMap:
    ids: dict[str, int] = {}
    ctrlrange: dict[str, tuple[float, float]] = {}
    for name in actuator_names:
        actuator_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
        if actuator_id < 0:
            raise ValueError(f"模型中缺少执行器: {name}")
        ids[name] = int(actuator_id)
        ctrlrange[name] = (float(model.actuator_ctrlrange[actuator_id, 0]), float(model.actuator_ctrlrange[actuator_id, 1]))
    return ActuatorMap(ids=ids, ctrlrange=ctrlrange)

