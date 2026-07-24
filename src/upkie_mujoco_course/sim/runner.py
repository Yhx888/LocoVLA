"""MuJoCo 仿真 runner。"""

from __future__ import annotations

import time

import mujoco
import mujoco.viewer
import numpy as np

from upkie_mujoco_course.model.actuator_map import build_actuator_map
from upkie_mujoco_course.model.frame_map import build_frame_map
from upkie_mujoco_course.model.joint_map import build_joint_map
from upkie_mujoco_course.model.robot_spec import RobotSpec, load_robot_spec
from upkie_mujoco_course.model.sensor_map import build_sensor_map
from upkie_mujoco_course.sim.contacts import wheel_ground_state
from upkie_mujoco_course.sim.loader import build_mujoco_model


class SimulationRunner:
    """统一管理 MjModel、MjData 和模型映射。"""

    def __init__(self, spec: RobotSpec | None = None):
        self.spec = spec or load_robot_spec()
        self.model = build_mujoco_model(self.spec)
        self.data = mujoco.MjData(self.model)
        self.joint_map = build_joint_map(self.model, self.spec.controlled_joints)
        self.actuator_map = build_actuator_map(self.model, self.spec.actuator_names)
        self.sensor_map = build_sensor_map(self.model, self.spec.sensor_names)
        self.frame_map = build_frame_map(self.model)
        self.actuator_ids = self.actuator_map.ids
        self.ctrl_low = self.model.actuator_ctrlrange[:, 0].copy()
        self.ctrl_high = self.model.actuator_ctrlrange[:, 1].copy()
        self.default_qpos = self.data.qpos.copy()
        self.default_qvel = self.data.qvel.copy()
        self.root_joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, self.spec.root_joint_name)
        self.left_wheel_radius = self._estimate_wheel_radius(self.spec.wheel_joints[0])
        self.right_wheel_radius = self._estimate_wheel_radius(self.spec.wheel_joints[1])
        self._viewer = None
        self.last_reset_pose = "stand"

    @property
    def time(self) -> float:
        return float(self.data.time)

    def _estimate_wheel_radius(self, joint_name: str) -> float:
        joint_id = self.joint_map.ids[joint_name]
        body_id = int(self.model.jnt_bodyid[joint_id])
        radii = [
            float(self.model.geom_size[geom_id, 0])
            for geom_id in range(self.model.ngeom)
            if int(self.model.geom_bodyid[geom_id]) == body_id
            and int(self.model.geom_type[geom_id]) == int(mujoco.mjtGeom.mjGEOM_CYLINDER)
        ]
        return max(radii) if radii else self.spec.wheel_radius_fallback

    def reset(self, initial_pose: str = "stand") -> np.ndarray:
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = self.default_qpos
        self.data.qvel[:] = self.default_qvel
        if self.model.nu > 0:
            self.data.ctrl[:] = 0.0
        pose = self.spec.default_pose.get(initial_pose)
        if pose is None:
            raise ValueError(f"未知初始姿态: {initial_pose}")
        self.last_reset_pose = initial_pose
        for joint_name, target in pose.items():
            self.data.qpos[self.joint_map.qposadr[joint_name]] = float(target)
        if self.root_joint_id >= 0:
            qpos_adr = int(self.model.jnt_qposadr[self.root_joint_id])
            self.data.qpos[qpos_adr : qpos_adr + 3] = self.spec.default_base_position
            self.data.qpos[qpos_adr + 3 : qpos_adr + 7] = self.spec.default_base_quaternion
        mujoco.mj_forward(self.model, self.data)
        return self.observation()

    def open_viewer(self) -> None:
        """打开 MuJoCo 可视化窗口。关闭后可再次调用重新打开。"""
        if self._viewer is None:
            self._viewer = mujoco.viewer.launch_passive(self.model, self.data)

    def step(self, action: np.ndarray) -> np.ndarray:
        action = np.asarray(action, dtype=float).reshape(-1)
        if action.shape != (self.model.nu,):
            raise ValueError(f"动作维度错误：需要 {self.model.nu}，收到 {action.shape[0]}")
        self.data.ctrl[:] = np.clip(action, self.ctrl_low, self.ctrl_high)
        for _ in range(self.spec.frame_skip):
            mujoco.mj_step(self.model, self.data)
        if self._viewer is not None and self._viewer.is_running():
            self._viewer.sync()
            time.sleep(self.model.opt.timestep * self.spec.frame_skip)
        return self.observation()

    def observation(self) -> np.ndarray:
        return np.concatenate([self.data.qpos.copy(), self.data.qvel.copy()]).astype(np.float64)

    def posture_state(self) -> dict[str, float | bool]:
        pitch, pitch_rate, forward_velocity, yaw_rate = self._floating_base_state()
        base_position = self._base_position()
        contacts = wheel_ground_state(self)
        return {
            "time": self.time,
            "x_position": float(base_position[0]),
            "base_height": float(base_position[2]),
            "pitch": pitch,
            "pitch_error": pitch - self.spec.equilibrium_pitch_rad,
            "pitch_rate": pitch_rate,
            "forward_velocity": forward_velocity,
            "yaw_rate": yaw_rate,
            **contacts,
        }

    def _base_position(self) -> np.ndarray:
        body_ids = self.frame_map.body_ids
        base_id = body_ids.get(self.spec.base_body, 0)
        return self.data.xpos[int(base_id)].copy()

    def _floating_base_state(self) -> tuple[float, float, float, float]:
        for joint_id in range(self.model.njnt):
            if int(self.model.jnt_type[joint_id]) != int(mujoco.mjtJoint.mjJNT_FREE):
                continue
            qpos_adr = int(self.model.jnt_qposadr[joint_id])
            qvel_adr = int(self.model.jnt_dofadr[joint_id])
            qw, qx, qy, qz = [float(value) for value in self.data.qpos[qpos_adr + 3 : qpos_adr + 7]]
            sin_pitch = 2.0 * (qw * qy - qz * qx)
            pitch = float(np.arcsin(np.clip(sin_pitch, -1.0, 1.0)))
            return (
                pitch,
                float(self.data.qvel[qvel_adr + 4]),
                float(self.data.qvel[qvel_adr]),
                float(self.data.qvel[qvel_adr + 5]),
            )
        left = float(self.data.qvel[self.joint_map.dofadr[self.spec.wheel_joints[0]]])
        right = float(self.data.qvel[self.joint_map.dofadr[self.spec.wheel_joints[1]]])
        radius = 0.5 * (self.left_wheel_radius + self.right_wheel_radius)
        return 0.0, 0.0, float(radius * 0.5 * (left + right)), 0.0

    def close(self) -> None:
        if self._viewer is not None:
            self._viewer.close()
            self._viewer = None
