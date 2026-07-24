"""传感器读取工具。"""

from __future__ import annotations

import numpy as np

from upkie_mujoco_course.model.sensor_map import SensorMap


def read_sensors(data, sensor_map: SensorMap) -> dict[str, np.ndarray]:
    """按名称读取传感器数据。"""

    values: dict[str, np.ndarray] = {}
    for name, address in sensor_map.addresses.items():
        dim = sensor_map.dims[name]
        values[name] = data.sensordata[address : address + dim].copy()
    return values

