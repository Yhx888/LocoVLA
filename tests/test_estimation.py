"""测试状态估计模块（estimation_20 ~ estimation_23）。

覆盖场景：
- 互补滤波器（ComplementaryPitchEstimator）姿态估计
- 线性卡尔曼滤波器（LinearKalmanFilter）状态估计
- 扩展卡尔曼滤波器（ExtendedKalmanFilter）非线性估计
"""
import numpy as np

from upkie_mujoco_course.estimation.complementary import ComplementaryPitchEstimator
from upkie_mujoco_course.estimation.ekf import ExtendedKalmanFilter
from upkie_mujoco_course.estimation.kalman import LinearKalmanFilter
from upkie_mujoco_course.estimation.ukf import UnscentedKalmanFilter
from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.sim.runner import SimulationRunner
from upkie_mujoco_course.sim.sensors import read_sensors


def test_complementary_filter_converges_to_accelerometer_angle():
    estimator = ComplementaryPitchEstimator(alpha=0.98, dt=0.01)
    estimates = [estimator.update(gyro_rate=0.0, accelerometer_pitch=0.2) for _ in range(500)]
    assert np.isclose(estimates[-1], 0.2, atol=0.01)


def test_complementary_filter_reset_clears_state():
    estimator = ComplementaryPitchEstimator(alpha=0.9, dt=0.01)
    estimator.update(gyro_rate=1.0, accelerometer_pitch=0.2)
    estimator.reset(-0.1)
    assert estimator.pitch == -0.1


def test_linear_kalman_filter_converges_on_noisy_constant_state():
    estimator = LinearKalmanFilter(
        state=np.array([0.0]),
        covariance=np.array([[1.0]]),
        transition=np.array([[1.0]]),
        observation=np.array([[1.0]]),
        process_noise=np.array([[1e-4]]),
        measurement_noise=np.array([[0.04]]),
    )
    measurements = [0.9, 1.1, 0.95, 1.05, 1.0] * 20
    for measurement in measurements:
        estimator.predict()
        estimator.update(np.array([measurement]))

    assert np.isclose(estimator.state[0], 1.0, atol=0.03)
    assert estimator.covariance[0, 0] < 0.04


def test_extended_kalman_filter_handles_nonlinear_measurement():
    estimator = ExtendedKalmanFilter(
        state=np.array([1.0]),
        covariance=np.array([[1.0]]),
        process_noise=np.array([[1e-4]]),
        measurement_noise=np.array([[0.01]]),
    )

    for _ in range(12):
        estimator.predict(
            transition=lambda state: state,
            transition_jacobian=lambda state: np.array([[1.0]]),
        )
        estimator.update(
            np.array([4.0]),
            measurement=lambda state: np.array([state[0] ** 2]),
            measurement_jacobian=lambda state: np.array([[2.0 * state[0]]]),
        )

    assert np.isclose(estimator.state[0], 2.0, atol=0.02)
    assert estimator.covariance[0, 0] < 0.01


def test_unscented_kalman_filter_handles_nonlinear_measurement():
    estimator = UnscentedKalmanFilter(
        state=np.array([1.0]),
        covariance=np.array([[1.0]]),
        process_noise=np.array([[1e-4]]),
        measurement_noise=np.array([[0.01]]),
    )

    for _ in range(12):
        estimator.predict(transition=lambda state: state)
        estimator.update(
            np.array([4.0]),
            measurement=lambda state: np.array([state[0] ** 2]),
        )

    assert np.isclose(estimator.state[0], 2.0, atol=0.03)
    assert estimator.covariance[0, 0] < 0.02


def test_chapter_19_complementary_filter_collects_from_standing_closed_loop():
    runner = SimulationRunner()
    runner.reset("stand")
    controller = WheelBalancerController(standup_duration=0.2)
    dt = runner.model.opt.timestep * runner.spec.frame_skip
    estimator = ComplementaryPitchEstimator(alpha=0.98, dt=dt)
    estimator.reset(runner.spec.equilibrium_pitch_rad)
    rng = np.random.default_rng(19)
    estimates = []
    truth = []
    try:
        for _ in range(1000):
            runner.step(controller.compute_action(runner, runner.time))
            state = runner.posture_state()
            assert state["base_height"] > -0.35
            assert abs(state["pitch"]) < 0.5
            readings = read_sensors(runner.data, runner.sensor_map)
            acceleration = readings["imu_accelerometer"]
            accelerometer_pitch = np.arctan2(
                -acceleration[0],
                np.hypot(acceleration[1], acceleration[2]),
            ) + rng.normal(0.0, 0.05)
            gyro_rate = readings["imu_gyroscope"][1] + 0.001 + rng.normal(0.0, 0.001)
            estimates.append(estimator.update(gyro_rate, accelerometer_pitch))
            truth.append(state["pitch"])
    finally:
        runner.close()

    error = np.asarray(estimates) - np.asarray(truth)
    assert len(estimates) == 1000
    assert np.sqrt(np.mean(error**2)) < 0.2
