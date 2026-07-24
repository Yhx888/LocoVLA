"""测试 sensor_map 模块的传感器映射接口。"""

import numpy as np

from upkie_mujoco_course.model.robot_spec import load_robot_spec
from upkie_mujoco_course.model.sensor_map import build_sensor_map
from upkie_mujoco_course.sim.loader import build_mujoco_model
from upkie_mujoco_course.sim.runner import SimulationRunner
from upkie_mujoco_course.sim.sensors import read_sensors


def test_upkie_model_exposes_native_imu_and_wheel_encoders():
    spec = load_robot_spec()
    sensor_map = build_sensor_map(build_mujoco_model(spec), spec.sensor_names)
    assert set(sensor_map.ids) == {
        "imu_accelerometer",
        "imu_gyroscope",
        "imu_orientation",
        "left_wheel_position",
        "left_wheel_velocity",
        "right_wheel_position",
        "right_wheel_velocity",
    }
    assert sensor_map.dims["imu_accelerometer"] == 3
    assert sensor_map.dims["imu_gyroscope"] == 3
    assert sensor_map.dims["imu_orientation"] == 4
    assert all(sensor_map.dims[name] == 1 for name in spec.sensor_names[3:])


def test_sensor_reader_returns_finite_mujoco_sensordata_samples():
    runner = SimulationRunner()
    runner.reset("stand")
    runner.step(np.zeros(runner.model.nu))
    readings = read_sensors(runner.data, runner.sensor_map)

    assert set(readings) == set(runner.spec.sensor_names)
    assert all(np.isfinite(value).all() for value in readings.values())
    assert np.linalg.norm(readings["imu_accelerometer"]) > 1.0
    runner.close()
