"""传感器名称映射。"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco


@dataclass(frozen=True)
class SensorMap:
    ids: dict[str, int]
    addresses: dict[str, int]
    dims: dict[str, int]


def build_sensor_map(model: mujoco.MjModel, sensor_names: tuple[str, ...] | list[str]) -> SensorMap:
    ids: dict[str, int] = {}
    addresses: dict[str, int] = {}
    dims: dict[str, int] = {}
    for name in sensor_names:
        sensor_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, name)
        if sensor_id < 0:
            raise ValueError(f"模型中缺少传感器: {name}")
        ids[name] = int(sensor_id)
        addresses[name] = int(model.sensor_adr[sensor_id])
        dims[name] = int(model.sensor_dim[sensor_id])
    return SensorMap(ids=ids, addresses=addresses, dims=dims)

