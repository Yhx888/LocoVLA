"""MuJoCo 模型加载。

从 URDF 文件加载 Upkie 机器人模型，并补充课程需要的地面、灯光和执行器。
"""

from __future__ import annotations

from typing import Any, Iterable

import mujoco

from upkie_mujoco_course.model.robot_spec import ActuatorSpec, RobotSpec, load_robot_spec


def _add_position_actuator(spec: mujoco.MjSpec, item: ActuatorSpec) -> None:
    """添加位置执行器：ctrl 值直接作为关节目标角度。"""
    actuator = spec.add_actuator(name=item.name)
    actuator.trntype = mujoco.mjtTrn.mjTRN_JOINT
    actuator.target = item.joint
    actuator.set_to_position(item.gain)
    actuator.ctrllimited = True
    actuator.ctrlrange = list(item.ctrlrange)


def _add_torque_actuator(spec: mujoco.MjSpec, item: ActuatorSpec) -> None:
    """添加力矩执行器：ctrl 值直接表示关节力矩。"""
    actuator = spec.add_actuator(name=item.name)
    actuator.trntype = mujoco.mjtTrn.mjTRN_JOINT
    actuator.target = item.joint
    actuator.set_to_motor()
    actuator.gear[0] = item.gain
    actuator.ctrllimited = True
    actuator.ctrlrange = list(item.ctrlrange)


def _setup_light(light: Any, pos: Iterable[float], direction: Iterable[float]) -> None:
    """配置灯光位置、方向和阴影。"""
    light.pos = list(pos)
    light.dir = list(direction)
    if hasattr(light, "directional"):
        light.directional = True
    if hasattr(light, "castshadow"):
        light.castshadow = True


def _apply_visual_style(spec: mujoco.MjSpec) -> None:
    """设置离屏渲染分辨率为 1280x720，用于录像和截图。"""
    if not hasattr(spec, "visual"):
        return
    visual_global = getattr(spec.visual, "global_", None)
    if visual_global is not None:
        if hasattr(visual_global, "offwidth"):
            visual_global.offwidth = 1280
        if hasattr(visual_global, "offheight"):
            visual_global.offheight = 720


def _add_course_camera_and_targets(spec: mujoco.MjSpec, robot_spec: RobotSpec) -> None:
    base = spec.body(robot_spec.base_body)
    if base is None:
        raise ValueError(f"模型中缺少基座 body: {robot_spec.base_body}")
    camera = base.add_camera(name="onboard_camera")
    camera.pos = [0.12, 0.0, -0.05]
    camera.quat = [0.5, 0.5, -0.5, -0.5]
    camera.fovy = 50.0
    for name, position, color in (
        ("red_target", [2.0, 0.0, robot_spec.floor_z + 0.2], [0.9, 0.08, 0.05, 1.0]),
        ("blue_target", [2.0, 1.0, robot_spec.floor_z + 0.2], [0.05, 0.25, 0.9, 1.0]),
        ("green_target", [2.0, -1.0, robot_spec.floor_z + 0.2], [0.05, 0.75, 0.25, 1.0]),
    ):
        target = spec.worldbody.add_geom(name=name)
        target.type = mujoco.mjtGeom.mjGEOM_SPHERE
        target.size = [0.2, 0.0, 0.0]
        target.pos = position
        target.rgba = color
        target.contype = 0
        target.conaffinity = 0
    for name, position in (
        ("obstacle_left", [1.2, 0.65, robot_spec.floor_z + 0.25]),
        ("obstacle_right", [1.2, -0.65, robot_spec.floor_z + 0.25]),
    ):
        obstacle = spec.worldbody.add_geom(name=name)
        obstacle.type = mujoco.mjtGeom.mjGEOM_BOX
        obstacle.size = [0.15, 0.18, 0.25]
        obstacle.pos = position
        obstacle.rgba = [0.32, 0.38, 0.42, 1.0]
        obstacle.contype = 1
        obstacle.conaffinity = 1


def _add_state_estimation_sensors(spec: mujoco.MjSpec, robot_spec: RobotSpec) -> None:
    """添加由 MuJoCo 直接计算的基座 IMU 与轮关节编码器。"""

    base = spec.body(robot_spec.base_body)
    if base is None:
        raise ValueError(f"模型中缺少基座 body: {robot_spec.base_body}")
    base.add_site(name="imu_site", size=[0.005])
    spec.add_sensor(
        name="imu_accelerometer",
        type=mujoco.mjtSensor.mjSENS_ACCELEROMETER,
        objtype=mujoco.mjtObj.mjOBJ_SITE,
        objname="imu_site",
    )
    spec.add_sensor(
        name="imu_gyroscope",
        type=mujoco.mjtSensor.mjSENS_GYRO,
        objtype=mujoco.mjtObj.mjOBJ_SITE,
        objname="imu_site",
    )
    spec.add_sensor(
        name="imu_orientation",
        type=mujoco.mjtSensor.mjSENS_FRAMEQUAT,
        objtype=mujoco.mjtObj.mjOBJ_SITE,
        objname="imu_site",
    )
    for side, joint_name in zip(("left", "right"), robot_spec.wheel_joints, strict=True):
        spec.add_sensor(
            name=f"{side}_wheel_position",
            type=mujoco.mjtSensor.mjSENS_JOINTPOS,
            objtype=mujoco.mjtObj.mjOBJ_JOINT,
            objname=joint_name,
        )
        spec.add_sensor(
            name=f"{side}_wheel_velocity",
            type=mujoco.mjtSensor.mjSENS_JOINTVEL,
            objtype=mujoco.mjtObj.mjOBJ_JOINT,
            objname=joint_name,
        )


def build_mujoco_model(robot_spec: RobotSpec | None = None) -> mujoco.MjModel:
    """读取 Upkie URDF，并补充课程需要的地面与执行器。

    构建流程：
    1. 加载 URDF 文件
    2. 配置仿真参数（时间步、积分器）
    3. 添加灯光和地面
    4. 添加执行器（位置/力矩）
    5. 编译为 MjModel
    """
    robot_spec = robot_spec or load_robot_spec()
    if not robot_spec.model_path.exists():
        raise FileNotFoundError(f"未找到模型: {robot_spec.model_path}")
    spec = mujoco.MjSpec.from_file(str(robot_spec.model_path))
    if robot_spec.floating_base:
        base = spec.body(robot_spec.base_body)
        if base is None:
            raise ValueError(f"模型中缺少基座 body: {robot_spec.base_body}")
        root_joint = base.add_freejoint()
        root_joint.name = robot_spec.root_joint_name
    spec.option.timestep = float(robot_spec.timestep)
    # RK4 积分器比默认欧拉积分更精确，适合机器人仿真（误差更小，能量守恒更好）
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_RK4
    if hasattr(spec, "compiler") and hasattr(spec.compiler, "discardvisual"):
        spec.compiler.discardvisual = 0
    _apply_visual_style(spec)
    _add_course_camera_and_targets(spec, robot_spec)
    _add_state_estimation_sensors(spec, robot_spec)
    # 灯光：从右上方照射，产生自然阴影
    _setup_light(spec.worldbody.add_light(name="key_light"), [3.0, -2.0, 4.0], [-0.5, 0.3, -1.0])
    # 地面：30x30 平面，摩擦三元组 [滑动摩擦, 扭转摩擦, 滚动摩擦]
    floor = spec.worldbody.add_geom(name="floor")
    floor.type = mujoco.mjtGeom.mjGEOM_PLANE
    floor.size = [30.0, 30.0, 0.1]  # 0.1 是半厚度（MuJoCo 要求）
    floor.pos = [0.0, 0.0, float(robot_spec.floor_z)]
    floor.friction = [1.2, 0.05, 0.01]  # 高滑动摩擦防止轮子打滑
    floor.contype = 1
    floor.conaffinity = 1
    floor.rgba = [0.18, 0.22, 0.28, 1.0]  # 深蓝灰色地面
    for item in robot_spec.position_actuators:
        _add_position_actuator(spec, item)
    for item in robot_spec.torque_actuators:
        _add_torque_actuator(spec, item)
    return spec.compile()
