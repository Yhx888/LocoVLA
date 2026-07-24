"""测试控制器输出接口。

覆盖场景：
- PD / LQR 控制器输出形状与数值范围
- 动作滤波器（低通、增量限制）行为
- LQR 平衡控制器接口契约
"""
import numpy as np

from upkie_mujoco_course.controllers.action_filter import LowPassActionFilter, limit_action_delta
from upkie_mujoco_course.controllers.lqr import LQRController
from upkie_mujoco_course.controllers.lqr import LQRBalanceController
from upkie_mujoco_course.controllers.pd import PDController
from upkie_mujoco_course.controllers.saturation import clip_action
from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.controllers.residual import ResidualController
from upkie_mujoco_course.sim.runner import SimulationRunner


def test_controller_outputs_are_finite_and_saturated():
    runner = SimulationRunner()
    obs = runner.reset("crouch")
    controller = WheelBalancerController()
    action = controller.compute_action(runner, runner.time)
    assert action.shape == (runner.model.nu,)
    assert np.isfinite(action).all()
    assert np.all(action <= runner.ctrl_high + 1e-9)
    assert np.all(action >= runner.ctrl_low - 1e-9)

    pd = PDController(kp=2.0, kd=0.5, limit=3.0)
    pd_action = pd.compute(np.array([1.0, -1.0]), np.zeros(2), np.zeros(2), np.zeros(2))
    assert pd_action.shape == (2,)
    assert np.isfinite(pd_action).all()

    lqr = LQRController(gain=np.ones((1, 4)))
    assert lqr.compute(np.ones(4)).shape == (1,)

    clipped = clip_action(np.array([-10.0, 10.0]), np.array([-1.0, -2.0]), np.array([1.0, 2.0]))
    assert np.allclose(clipped, [-1.0, 2.0])

    filt = LowPassActionFilter(alpha=0.5, size=2)
    assert np.allclose(filt.filter(np.ones(2)), [0.5, 0.5])
    assert np.allclose(limit_action_delta(np.array([1.0]), np.array([0.0]), 0.2), [0.2])
    assert obs.shape[0] == runner.model.nq + runner.model.nv
    runner.close()


def test_wheel_balancer_keeps_floating_robot_upright_for_five_seconds():
    runner = SimulationRunner()
    runner.reset("stand")
    controller = WheelBalancerController(standup_duration=0.2)
    max_pitch = 0.0
    while runner.time < 5.0:
        runner.step(controller.compute_action(runner, runner.time))
        state = runner.posture_state()
        max_pitch = max(max_pitch, abs(float(state["pitch"])))
        assert float(state["base_height"]) > -0.35
    runner.close()
    assert max_pitch < 0.5


def test_lqr_balancer_keeps_floating_robot_upright_for_five_seconds():
    runner = SimulationRunner()
    runner.reset("stand")
    controller = LQRBalanceController()
    max_pitch = 0.0
    while runner.time < 5.0:
        runner.step(controller.compute_action(runner))
        max_pitch = max(max_pitch, abs(float(runner.posture_state()["pitch"])))
    runner.close()
    assert max_pitch < 0.5


def test_residual_controller_scales_and_clips_action():
    controller = ResidualController(scale=0.5, low=np.array([-1.0, -1.0]), high=np.array([1.0, 1.0]))
    action = controller.compute(np.array([0.8, -0.8]), np.array([1.0, -1.0]))
    assert np.allclose(action, [1.0, -1.0])


def test_velocity_target_changes_wheel_torque_direction():
    runner = SimulationRunner()
    runner.reset("stand")
    stopped = WheelBalancerController(target_velocity=0.0, torque_filter_alpha=1.0)
    moving = WheelBalancerController(target_velocity=0.4, torque_filter_alpha=1.0)
    stopped_action = stopped.compute_action(runner, runner.time)
    moving_action = moving.compute_action(runner, runner.time)
    left_motor = runner.actuator_ids["left_wheel_motor"]
    assert moving_action[left_motor] < stopped_action[left_motor]
    runner.close()


def test_wheel_balancer_consumes_optional_estimated_state():
    runner = SimulationRunner()
    runner.reset("stand")
    controller = WheelBalancerController(torque_filter_alpha=1.0)
    action = controller.compute_action(
        runner,
        runner.time,
        estimated_state={
            "pitch_error": 0.05,
            "pitch_rate": -0.1,
            "forward_velocity": 0.0,
            "x_position": 1.25,
        },
    )

    assert controller.last_debug.pitch == 0.05
    assert controller.last_debug.pitch_rate == -0.1
    assert controller.target_position == 1.25
    assert action[runner.actuator_ids["left_wheel_motor"]] != 0.0
    runner.close()


def test_velocity_controller_tracks_reference_for_thirty_seconds():
    runner = SimulationRunner()
    runner.reset("stand")
    controller = WheelBalancerController(target_velocity=0.1)
    max_pitch_error = 0.0
    while runner.time < 30.0:
        runner.step(controller.compute_action(runner, runner.time))
        state = runner.posture_state()
        max_pitch_error = max(max_pitch_error, abs(float(state["pitch_error"])))
    state = runner.posture_state()
    assert state["both_wheels_contact"] is True
    assert max_pitch_error < 0.2
    assert abs(float(state["x_position"]) - controller.target_position) < 0.1
    assert abs(float(state["forward_velocity"]) - 0.1) < 0.15
    runner.close()
