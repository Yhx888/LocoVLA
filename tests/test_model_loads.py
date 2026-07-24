"""测试 MuJoCo 模型加载。

覆盖场景：
- MJCF 模型能成功加载
- 关节数 / 速度数 / 执行器数符合 robot_spec
- 根部自由基座与默认位姿正确
"""
import mujoco
import numpy as np

from upkie_mujoco_course.model.robot_spec import load_robot_spec
from upkie_mujoco_course.sim.loader import build_mujoco_model
from upkie_mujoco_course.sim.runner import SimulationRunner


def test_upkie_model_loads_with_actuators():
    spec = load_robot_spec()
    model = build_mujoco_model(spec)
    assert model.nq == 13
    assert model.nv == 12
    assert model.nu == 6
    free_joints = [
        joint_id
        for joint_id in range(model.njnt)
        if int(model.jnt_type[joint_id]) == int(mujoco.mjtJoint.mjJNT_FREE)
    ]
    assert len(free_joints) == 1
    assert mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, free_joints[0]) == spec.root_joint_name


def test_wheel_actuators_are_torque_motors():
    spec = load_robot_spec()
    model = build_mujoco_model(spec)
    for actuator in spec.torque_actuators:
        actuator_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator.name)
        assert int(model.actuator_biastype[actuator_id]) == int(mujoco.mjtBias.mjBIAS_NONE)


def test_onboard_camera_renders_visible_red_target():
    model = build_mujoco_model(load_robot_spec())
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    camera_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "onboard_camera")
    assert camera_id >= 0
    renderer = mujoco.Renderer(model, height=120, width=160)
    renderer.update_scene(data, camera="onboard_camera")
    frame = renderer.render()
    renderer.close()
    red_pixels = (frame[..., 0] > frame[..., 1] + 40) & (frame[..., 0] > frame[..., 2] + 40)
    assert int(np.count_nonzero(red_pixels)) > 10


def test_course_scene_contains_colliding_obstacles():
    model = build_mujoco_model(load_robot_spec())
    obstacle_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "obstacle_left")
    assert obstacle_id >= 0
    assert int(model.geom_contype[obstacle_id]) != 0
    assert int(model.geom_conaffinity[obstacle_id]) != 0


def test_standing_pose_projects_center_of_mass_over_wheel_axis():
    runner = SimulationRunner()
    runner.reset("stand")
    base_id = runner.frame_map.body_ids[runner.spec.base_body]
    wheel_x = np.mean(
        [runner.data.xpos[int(runner.model.jnt_bodyid[runner.joint_map.ids[name]]), 0] for name in runner.spec.wheel_joints]
    )
    assert abs(float(runner.data.subtree_com[base_id, 0]) - float(wheel_x)) < 0.01
    assert abs(float(runner.posture_state()["pitch_error"])) < 1e-6
    runner.close()
