#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 40 关证据采集：测试 IMU 发布节点。

按 100 Hz 向 /imu 话题发布 sensor_msgs/Imu 消息，
默认使用 upkie.json 中 default_base_quaternion [0.9974656375, 0, 0.0711498553, 0]
（对应 pitch≈0.142 rad），用于驱动 upkie_control 控制节点产生 wheel_torque 输出。

支持故障注入模式（--fault 参数），用于第 40 关 Task 8 故障证据采集：
  - normal                : 正常四元数（|q|=1，对应 pitch≈0.142 rad）
  - unnormalized_quaternion : 未归一化四元数（|q|>1，asin 输入越界）
  - torque_saturation     : 大 pitch 角（pitch≈π/2，控制律输出被 clamp 到 ±1.0）
  - zero_covariance       : orientation_covariance[0] = -1（无效协方差，pitch 视为 0）
  - large_pitch           : 构造 pitch=1.0 rad 的四元数（控制律输出 3.0 N·m，被限幅）

用法（在 WSL2 中，已 source install/setup.bash）：
  python3 /mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/scripts/tools/publish_test_imu.py \
      --duration 10 --fault normal
"""

import argparse
import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy, QoSReliabilityPolicy
from sensor_msgs.msg import Imu


# upkie.json 的 default_base_quaternion（wxyz），对应 pitch≈0.142 rad
DEFAULT_QUAT_W = 0.9974656375
DEFAULT_QUAT_X = 0.0
DEFAULT_QUAT_Y = 0.0711498553
DEFAULT_QUAT_Z = 0.0


def build_quaternion(fault: str):
    """根据故障类型返回 (w, x, y, z) 四元数和协方差[0]。"""
    if fault == "normal":
        # 正常四元数，pitch≈0.142 rad
        return (DEFAULT_QUAT_W, DEFAULT_QUAT_X, DEFAULT_QUAT_Y, DEFAULT_QUAT_Z, 0.01)
    if fault == "unnormalized_quaternion":
        # 未归一化四元数：|q| = sqrt(1.5^2 + 0.1^2) ≈ 1.503
        # sine = 2*(w*y - z*x) = 2*1.5*0.1 = 0.3
        # 但因为是未归一化，实际计算出的 pitch 会偏离真实角度
        # 这里用 [1.5, 0, 0.1, 0]，|q|≈1.503，sine=0.3，asin(0.3)≈0.305 rad
        # 真实角度应为 2*atan2(0.1, 1.5)≈0.133 rad，差异明显
        return (1.5, 0.0, 0.1, 0.0, 0.01)
    if fault == "torque_saturation":
        # 大 pitch 角（接近 π/2），控制律输出 3*1.57=4.7 N·m，被 clamp 到 1.0
        # pitch=π/2 → w=cos(π/4)≈0.7071, y=sin(π/4)≈0.7071
        return (math.cos(math.pi / 4), 0.0, math.sin(math.pi / 4), 0.0, 0.01)
    if fault == "large_pitch":
        # pitch=1.0 rad → w=cos(0.5)≈0.8776, y=sin(0.5)≈0.4794
        # 控制律输出 3.0*1.0 = 3.0 N·m，被 clamp 到 1.0
        return (math.cos(0.5), 0.0, math.sin(0.5), 0.0, 0.01)
    if fault == "zero_covariance":
        # 协方差[0] = -1（无效），控制节点会把 pitch 视为 0
        return (DEFAULT_QUAT_W, DEFAULT_QUAT_X, DEFAULT_QUAT_Y, DEFAULT_QUAT_Z, -1.0)
    raise ValueError(f"未知故障类型: {fault}")


class ImuPublisher(Node):
    """以指定频率发布 sensor_msgs/Imu 消息。"""

    def __init__(self, rate_hz: float, fault: str, duration_sec: float):
        super().__init__("test_imu_publisher")
        # 发布端使用 SensorDataQoS 等价的 QoS 配置（best_effort + volatile + keep_last 5）
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5,
        )
        self.pub_ = self.create_publisher(Imu, "imu", qos)
        self.rate_hz_ = rate_hz
        self.duration_sec_ = duration_sec
        self.fault_ = fault
        self.w_, self.x_, self.y_, self.z_, self.cov0_ = build_quaternion(fault)
        # 计算预期 pitch（用于日志）
        sine = 2.0 * (self.w_ * self.y_ - self.z_ * self.x_)
        sine_clamped = max(-1.0, min(1.0, sine))
        self.expected_pitch_ = math.asin(sine_clamped)
        period_sec = 1.0 / rate_hz
        self.timer_ = self.create_timer(period_sec, self._tick)
        self.start_time_ = self.get_clock().now()
        self.msg_count_ = 0
        self.get_logger().info(
            f"IMU 发布节点启动: rate={rate_hz}Hz, fault={fault}, "
            f"duration={duration_sec}s, quat=({self.w_},{self.x_},{self.y_},{self.z_}), "
            f"cov0={self.cov0_}, expected_pitch={self.expected_pitch_:.4f} rad"
        )

    def _tick(self):
        elapsed = (self.get_clock().now() - self.start_time_).nanoseconds / 1e9
        if elapsed >= self.duration_sec_:
            self.get_logger().info(
                f"达到目标时长 {self.duration_sec_}s，已发布 {self.msg_count_} 条消息，退出"
            )
            raise SystemExit(0)
        msg = Imu()
        # header
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "imu_link"
        # orientation（wxyz 顺序，ROS 中 geometry_msgs/Quaternion 字段为 x,y,z,w）
        msg.orientation.w = self.w_
        msg.orientation.x = self.x_
        msg.orientation.y = self.y_
        msg.orientation.z = self.z_
        # orientation_covariance 是 9 元素数组，[0] 表示 x 方向姿态协方差
        cov = [0.0] * 9
        cov[0] = self.cov0_
        msg.orientation_covariance = cov
        # angular_velocity（绕 Y 轴角速度，对应 pitch_rate=0）
        msg.angular_velocity.x = 0.0
        msg.angular_velocity.y = 0.0
        msg.angular_velocity.z = 0.0
        # linear_acceleration（重力 g）
        msg.linear_acceleration.x = 0.0
        msg.linear_acceleration.y = 0.0
        msg.linear_acceleration.z = 9.81
        self.pub_.publish(msg)
        self.msg_count_ += 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="测试 IMU 发布节点（第 40 关证据采集）")
    parser.add_argument("--rate", type=float, default=100.0,
                        help="发布频率 Hz（默认 100）")
    parser.add_argument("--duration", type=float, default=10.0,
                        help="持续时长秒（默认 10）")
    parser.add_argument("--fault", type=str, default="normal",
                        choices=["normal", "unnormalized_quaternion",
                                 "torque_saturation", "large_pitch",
                                 "zero_covariance"],
                        help="故障注入类型（默认 normal）")
    args = parser.parse_args(argv)

    rclpy.init(args=sys.argv[:1])  # 不消费 ROS 自己的参数
    node = ImuPublisher(args.rate, args.fault, args.duration)
    try:
        rclpy.spin(node)
    except SystemExit:
        node.get_logger().info("IMU 发布节点正常退出")
    except KeyboardInterrupt:
        node.get_logger().info("收到 Ctrl+C，IMU 发布节点退出")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
