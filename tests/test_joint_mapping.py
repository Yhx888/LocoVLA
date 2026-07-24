"""测试 joint_map 模块的关节映射接口。

覆盖场景：
- 关节名称到 qpos / qvel 索引的映射
- 关节顺序符合 robot_spec 配置
- 与 MuJoCo 模型的关节列表一致
"""
from upkie_mujoco_course.model.joint_map import build_joint_map
from upkie_mujoco_course.model.robot_spec import load_robot_spec
from upkie_mujoco_course.sim.loader import build_mujoco_model


def test_joint_mapping_contains_required_joints():
    spec = load_robot_spec()
    joint_map = build_joint_map(build_mujoco_model(spec), spec.controlled_joints)
    for name in spec.controlled_joints:
        assert name in joint_map.ids
        assert joint_map.qposadr[name] >= 0
        assert joint_map.dofadr[name] >= 0
