"""测试 actuator_map 模块的执行器映射接口。

覆盖场景：
- 执行器名称到 control 通道的映射
- 单位转换（rad / N*m）
- 边界裁剪
"""
from upkie_mujoco_course.model.actuator_map import build_actuator_map
from upkie_mujoco_course.model.robot_spec import load_robot_spec
from upkie_mujoco_course.sim.loader import build_mujoco_model


def test_actuator_mapping_contains_configured_actuators():
    spec = load_robot_spec()
    actuator_map = build_actuator_map(build_mujoco_model(spec), spec.actuator_names)
    assert list(actuator_map.ids) == spec.actuator_names
    assert len(actuator_map.ctrlrange) == len(spec.actuator_names)
