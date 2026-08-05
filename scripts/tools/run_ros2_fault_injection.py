#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 43 关：真实 ROS2 端到端故障注入脚本。

在 WSL2 中启动 control_node，用 rclpy 发布 IMU 数据并订阅 /safety_state 和 /wheel_torque，
注入 5 种故障并采集状态转换、力矩门控、检测延迟时间线。

故障清单：
  1. IMU 断流（停止发布 IMU 300ms，触发 communication_lost=True → FAULT）
  2. NaN 注入（发布 IMU 含 NaN quaternion，触发 nan_detected=True → FAULT）
  3. 时间戳回退（发布 IMU header.stamp 比上一条早，触发 timestamp_regression → communication_lost=True → FAULT）
  4. 通信中断（停止发布 IMU 250ms，触发 communication_lost=True → FAULT）
  5. 急停（调用 /estop 服务，触发 estop_triggered=True → FAULT）

用法（必须在 WSL2 中运行）：
  source ~/upkie-ros2-build/install/setup.bash
  python3 /mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/scripts/tools/run_ros2_fault_injection.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

try:
    import rclpy
    from builtin_interfaces.msg import Time
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import (
        QoSDurabilityPolicy,
        QoSHistoryPolicy,
        QoSProfile,
        QoSReliabilityPolicy,
    )
    from sensor_msgs.msg import Imu
    from std_msgs.msg import Float64MultiArray, String
    from std_srvs.srv import Trigger
except ModuleNotFoundError as exc:
    rclpy = None
    ROS_IMPORT_ERROR = exc
    Node = object
else:
    ROS_IMPORT_ERROR = None

# upkie.json 的 default_base_quaternion（wxyz），对应 pitch≈0.142 rad
DEFAULT_QUAT_W = 0.9974656375
DEFAULT_QUAT_X = 0.0
DEFAULT_QUAT_Y = 0.0711498553
DEFAULT_QUAT_Z = 0.0

DEFAULT_OUTPUT_ROOT = str(Path(__file__).resolve().parents[2] / "outputs")
DEFAULT_INSTALL_PREFIX = "~/upkie-ros2-build/install"


def _as_wsl_path(value: str) -> str:
    """同时接受 Windows 盘符路径和 WSL/POSIX 路径。"""
    raw = str(Path(value.strip()).expanduser())
    match = re.match(r"^([A-Za-z]):[\\/](.*)$", raw)
    if match:
        suffix = match.group(2).replace("\\", "/")
        return f"/mnt/{match.group(1).lower()}/{suffix}".rstrip("/")
    return raw.replace("\\", "/").rstrip("/")


def resolve_output_paths(output_root: str) -> dict[str, str]:
    root = _as_wsl_path(output_root)
    return {
        "output_root": root,
        "fault_result": f"{root}/results/engineering_43_ros2_fault_injection.json",
        "timing_log": f"{root}/logs/engineering_40_timing.json",
        "qos_log": f"{root}/logs/engineering_40_qos.json",
        "control_log": f"{root}/logs/engineering_42_log.jsonl",
        "process_log": f"{root}/logs/engineering_43_control_node.log",
    }


def build_control_command(
    paths: dict[str, str],
    *,
    install_prefix: str,
) -> str:
    setup_path = f"{_as_wsl_path(install_prefix)}/setup.bash"
    parameters = [
        "record_timing:=true",
        f"record_timing_path:={paths['timing_log']}",
        "record_log:=true",
        f"log_path:={paths['control_log']}",
    ]
    ros_args = " ".join(f"-p {shlex.quote(value)}" for value in parameters)
    return (
        "source /opt/ros/jazzy/setup.bash && "
        f"source {shlex.quote(setup_path)} && "
        f"exec ros2 run upkie_control control_node --ros-args {ros_args}"
    )


def make_sensor_qos() -> QoSProfile:
    """创建与 control_node SensorDataQoS 等价的 QoS 配置。"""
    return QoSProfile(
        reliability=QoSReliabilityPolicy.BEST_EFFORT,
        durability=QoSDurabilityPolicy.VOLATILE,
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=10,
    )


def make_zero_torque(left: float, right: float) -> bool:
    """判断力矩是否已制动（绝对值 < 1e-6）。"""
    return abs(left) < 1e-6 and abs(right) < 1e-6


class FaultInjectorNode(Node):
    """真实 ROS2 故障注入节点。

    发布 /imu（100Hz），订阅 /safety_state 和 /wheel_torque，
    按时序注入 5 种故障并采集状态转换与力矩门控时间线。
    """

    def __init__(self) -> None:
        super().__init__("fault_injector")
        sensor_qos = make_sensor_qos()

        # IMU 发布器
        self.imu_pub_ = self.create_publisher(Imu, "imu", sensor_qos)
        # 订阅 /safety_state 和 /wheel_torque
        self.safety_sub_ = self.create_subscription(
            String, "safety_state", self._on_safety_state, 10
        )
        self.torque_sub_ = self.create_subscription(
            Float64MultiArray, "wheel_torque", self._on_torque, sensor_qos
        )
        # 服务客户端
        self.arm_client_ = self.create_client(Trigger, "arm")
        self.estop_client_ = self.create_client(Trigger, "estop")
        self.reset_client_ = self.create_client(Trigger, "reset")

        # 数据记录
        self.state_records_: list[dict] = []
        self.torque_records_: list[dict] = []
        self.imu_published_count_ = 0
        self.current_state_ = "BOOT"
        self.current_torque_ = (0.0, 0.0)

        # 用 time.monotonic() 测量时间，与 control_node steady_clock 一致
        self.start_monotonic_ = time.monotonic()

        # IMU 发布控制
        self.imu_publishing_ = True
        self.imu_fault_mode_ = "normal"  # normal / nan / timestamp_regression
        # 100Hz IMU 发布定时器
        self.timer_ = self.create_timer(0.01, self._publish_imu)

        # 故障测量变量
        self.fault_name_: str | None = None
        self.fault_injection_time_: float | None = None
        self.fault_detected_time_: float | None = None
        self.brake_time_: float | None = None
        self.torque_before_: float | None = None
        self.start_state_: str | None = None

        # 锁（保护记录数据与状态）
        self.lock_ = threading.Lock()

        self.get_logger().info("故障注入节点已启动")

    def _elapsed_s(self) -> float:
        """返回自节点启动以来的秒数（monotonic 时钟）。"""
        return time.monotonic() - self.start_monotonic_

    def _on_safety_state(self, msg: String) -> None:
        t = self._elapsed_s()
        with self.lock_:
            self.current_state_ = msg.data
            self.state_records_.append({"t_s": round(t, 6), "state": msg.data})
            # 检测故障
            if (
                self.fault_name_ is not None
                and msg.data == "FAULT"
                and self.fault_detected_time_ is None
            ):
                self.fault_detected_time_ = t
                self.get_logger().info(
                    f"[{self.fault_name_}] 故障检测时间: t={t:.4f}s"
                )

    def _on_torque(self, msg: Float64MultiArray) -> None:
        t = self._elapsed_s()
        if len(msg.data) >= 2:
            left, right = float(msg.data[0]), float(msg.data[1])
        else:
            left, right = 0.0, 0.0
        with self.lock_:
            self.current_torque_ = (left, right)
            self.torque_records_.append(
                {
                    "t_s": round(t, 6),
                    "torque_left": left,
                    "torque_right": right,
                }
            )
            # 检测制动（力矩从非零变为零）
            if (
                self.fault_name_ is not None
                and self.fault_detected_time_ is not None
                and self.brake_time_ is None
                and make_zero_torque(left, right)
            ):
                self.brake_time_ = t
                self.get_logger().info(
                    f"[{self.fault_name_}] 制动时间: t={t:.4f}s"
                )

    def _publish_imu(self) -> None:
        """100Hz 定时器回调：按当前故障模式发布 IMU 消息。"""
        if not self.imu_publishing_:
            return
        msg = Imu()
        msg.header.frame_id = "imu_link"
        # 协方差（默认有效）
        cov = [0.0] * 9
        cov[0] = 0.01
        msg.orientation_covariance = cov
        # 角速度（绕 Y 轴，pitch_rate=0）
        msg.angular_velocity.x = 0.0
        msg.angular_velocity.y = 0.0
        msg.angular_velocity.z = 0.0
        # 线性加速度（重力 g）
        msg.linear_acceleration.x = 0.0
        msg.linear_acceleration.y = 0.0
        msg.linear_acceleration.z = 9.81

        now_stamp = self.get_clock().now().to_msg()
        now_ns = int(now_stamp.sec) * 1_000_000_000 + int(now_stamp.nanosec)

        if self.imu_fault_mode_ == "nan":
            # NaN 注入：四元数含 NaN
            msg.orientation.w = float("nan")
            msg.orientation.x = 0.0
            msg.orientation.y = 0.0
            msg.orientation.z = 0.0
            # 时间戳正常
            msg.header.stamp = now_stamp
        elif self.imu_fault_mode_ == "timestamp_regression":
            # 时间戳回退：header.stamp 比当前 ROS 时间早 5 秒
            # 第一条这样的消息会触发回退（new_ns < old_ns，因为上次正常消息的 stamp 是 now）
            regressed_ns = max(0, now_ns - 5_000_000_000)
            regressed_stamp = Time()
            regressed_stamp.sec = int(regressed_ns // 1_000_000_000)
            regressed_stamp.nanosec = int(regressed_ns % 1_000_000_000)
            msg.header.stamp = regressed_stamp
            # 正常四元数
            msg.orientation.w = DEFAULT_QUAT_W
            msg.orientation.x = DEFAULT_QUAT_X
            msg.orientation.y = DEFAULT_QUAT_Y
            msg.orientation.z = DEFAULT_QUAT_Z
        else:
            # 正常 IMU
            msg.header.stamp = now_stamp
            msg.orientation.w = DEFAULT_QUAT_W
            msg.orientation.x = DEFAULT_QUAT_X
            msg.orientation.y = DEFAULT_QUAT_Y
            msg.orientation.z = DEFAULT_QUAT_Z

        self.imu_pub_.publish(msg)
        self.imu_published_count_ += 1

    def qos_observation(self) -> dict:
        """返回 DDS 端点发现和实际消息收发计数。"""
        return {
            "imu_subscription_count": int(self.imu_pub_.get_subscription_count()),
            "safety_publisher_count": int(self.safety_sub_.get_publisher_count()),
            "torque_publisher_count": int(self.torque_sub_.get_publisher_count()),
            "imu_published_count": int(self.imu_published_count_),
            "safety_received_count": len(self.state_records_),
            "torque_received_count": len(self.torque_records_),
        }

    def call_service(self, client: Trigger.Client, name: str, timeout_sec: float = 2.0) -> bool:
        """同步调用 /arm /estop /reset 服务。"""
        if not client.wait_for_service(timeout_sec=timeout_sec):
            self.get_logger().error(f"服务 {name} 不可用")
            return False
        req = Trigger.Request()
        future = client.call_async(req)
        start = time.monotonic()
        while time.monotonic() - start < timeout_sec:
            if future.done():
                result = future.result()
                return bool(result.success)
            time.sleep(0.005)
        self.get_logger().error(f"服务 {name} 调用超时")
        return False

    def get_current_state(self) -> str:
        with self.lock_:
            return self.current_state_

    def get_current_torque(self) -> tuple[float, float]:
        with self.lock_:
            return self.current_torque_

    def wait_for_state(self, target_state: str, timeout_sec: float = 2.0) -> bool:
        """等待状态机进入指定状态。"""
        start = time.monotonic()
        while time.monotonic() - start < timeout_sec:
            if self.get_current_state() == target_state:
                return True
            time.sleep(0.01)
        return False

    def start_fault_measurement(self, fault_name: str, start_state: str) -> None:
        """开始一次故障测量。"""
        with self.lock_:
            self.fault_name_ = fault_name
            self.fault_injection_time_ = self._elapsed_s()
            self.fault_detected_time_ = None
            self.brake_time_ = None
            self.torque_before_ = self.current_torque_[0]
            self.start_state_ = start_state

    def finish_fault_measurement(self, description: str) -> dict:
        """完成一次故障测量，返回结果字典。"""
        with self.lock_:
            det_t = self.fault_detected_time_
            brake_t = self.brake_time_
            t_fault = self.fault_injection_time_
            torque_before = self.torque_before_
            torque_after = self.current_torque_[0]
            start_state = self.start_state_
            final_state = self.current_state_
            name = self.fault_name_
            # 重置
            self.fault_name_ = None
            self.fault_injection_time_ = None
            self.fault_detected_time_ = None
            self.brake_time_ = None
            self.torque_before_ = None
            self.start_state_ = None

        if det_t is None:
            det_lat = None
            self.get_logger().error(f"[{name}] 故障未被检测！")
        else:
            det_lat = (det_t - t_fault) * 1000.0

        if brake_t is None or det_t is None:
            brake_lat = None
        else:
            brake_lat = (brake_t - det_t) * 1000.0

        safe = final_state == "FAULT"

        return {
            "fault_name": name,
            "description": description,
            "fault_injection_time_s": round(t_fault, 6),
            "fault_detected_time_s": round(det_t, 6) if det_t else None,
            "brake_time_s": round(brake_t, 6) if brake_t else None,
            "detection_latency_ms": round(det_lat, 3) if det_lat is not None else None,
            "brake_latency_ms": round(brake_lat, 3) if brake_lat is not None else None,
            "start_state": start_state,
            "final_state": final_state,
            "safe": safe,
            "torque_before": round(torque_before, 6),
            "torque_after": round(torque_after, 6),
        }


def _wait_fault_detected(node: FaultInjectorNode, timeout_sec: float = 1.5) -> bool:
    """等待状态机进入 FAULT，返回是否成功检测。"""
    start = time.monotonic()
    while time.monotonic() - start < timeout_sec:
        if node.get_current_state() == "FAULT":
            return True
        time.sleep(0.005)
    return False


def _recover_to_armed(node: FaultInjectorNode, fault_idx: int) -> None:
    """故障恢复：先发布正常 IMU，再 /reset，等待 DISARMED，重新 /arm。

    重要：必须先开始发布正常 IMU，让 control_node 收到至少几条正常消息，
    更新 last_imu_steady_time_ 使 sensor_fresh=true 且 communication_lost=false。
    否则 /reset 后状态机仍会被 communication_lost 拉回 FAULT。
    """
    # 1) 先开始发布正常 IMU，让传感器链路恢复新鲜
    node.imu_publishing_ = True
    node.imu_fault_mode_ = "normal"
    # 等 0.3 秒让 control_node 收到足够多正常 IMU（≈30 条）
    time.sleep(0.3)
    # 2) 调用 /reset，清除 nan_detected_/timestamp_regression_/estop_triggered_，
    #    并触发 FAULT → BOOT（reset 优先级最高）
    print(f"[INFO] 故障 {fault_idx + 1} 恢复：调用 /reset ...")
    if not node.call_service(node.reset_client_, "reset"):
        raise RuntimeError("/reset 服务调用失败")
    # 3) 等待状态机推进：FAULT → BOOT → SELF_CHECK → DISARMED
    time.sleep(0.8)
    # 4) 显式等待 DISARMED（sensor_fresh 已为 true，SELF_CHECK 会推进）
    if not node.wait_for_state("DISARMED", timeout_sec=2.0):
        cur = node.get_current_state()
        time.sleep(0.5)
        cur = node.get_current_state()
        if cur != "DISARMED":
            raise RuntimeError(
                f"故障 {fault_idx + 1} 恢复后未进入 DISARMED，当前状态: {cur}"
            )
    # 5) 调用 /arm → ARMED
    print("[INFO] 重新调用 /arm ...")
    if not node.call_service(node.arm_client_, "arm"):
        raise RuntimeError("/arm 服务调用失败")
    if not node.wait_for_state("ARMED", timeout_sec=2.0):
        cur = node.get_current_state()
        raise RuntimeError(
            f"故障 {fault_idx + 1} 恢复后未进入 ARMED，当前状态: {cur}"
        )
    # 6) 稳态 0.5 秒，确认输出非零力矩
    time.sleep(0.5)


def run_injection(paths: dict[str, str], install_prefix: str) -> int:
    """主流程：启动 control_node，注入 5 种故障，输出 JSON。"""
    for name in ("fault_result", "timing_log", "qos_log", "control_log", "process_log"):
        Path(paths[name]).parent.mkdir(parents=True, exist_ok=True)

    rclpy.init()
    node = FaultInjectorNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    # 启动 control_node 子进程（独立进程组，便于终止）
    # 重要：stdout 必须重定向到文件，不能用 PIPE（不读取会阻塞子进程）
    control_log_path = paths["process_log"]
    control_cmd = [
        "bash",
        "-c",
        build_control_command(paths, install_prefix=install_prefix),
    ]
    print("[INFO] 启动 control_node 子进程 ...")
    control_log_file = open(control_log_path, "w")
    control_proc = subprocess.Popen(
        control_cmd,
        stdout=control_log_file,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,
    )

    # 启动 executor 后台线程
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    faults: list[dict] = []
    try:
        # 1) 等待 discovery（让 control_node 启动并发现本节点）
        print("[INFO] 等待 control_node 启动（2.5 秒）...")
        time.sleep(2.5)

        # 2) 发布正常 IMU 1 秒，让状态机 BOOT → SELF_CHECK → DISARMED
        print("[INFO] 发布正常 IMU 1 秒，让状态机进入 DISARMED ...")
        node.imu_publishing_ = True
        node.imu_fault_mode_ = "normal"
        time.sleep(1.0)
        print(f"[INFO] 当前状态: {node.get_current_state()}")

        # 3) 调用 /arm 服务
        print("[INFO] 调用 /arm 服务 ...")
        if not node.call_service(node.arm_client_, "arm"):
            raise RuntimeError("/arm 服务调用失败")
        if not node.wait_for_state("ARMED", timeout_sec=2.0):
            raise RuntimeError(
                f"未进入 ARMED，当前状态: {node.get_current_state()}"
            )
        print("[OK] 已进入 ARMED")

        # 4) 稳态 1 秒，确认 ARMED 输出非零力矩
        print("[INFO] 等待 1 秒稳态 ...")
        time.sleep(1.0)
        left, right = node.get_current_torque()
        print(f"[INFO] 稳态力矩: left={left:.4f}, right={right:.4f}")

        # ==================== 故障 1：IMU 断流 300ms ====================
        print("\n[FAULT 1] IMU 断流 300ms（触发 communication_lost）")
        node.start_fault_measurement("imu_dropout", "ARMED")
        node.imu_publishing_ = False  # 停止发布 IMU
        _wait_fault_detected(node, timeout_sec=1.5)
        time.sleep(0.3)  # 让制动完成
        result = node.finish_fault_measurement(
            "IMU 断流 300ms，触发 communication_lost=True → FAULT"
        )
        faults.append(result)
        print(
            f"  -> 检测延迟: {result['detection_latency_ms']} ms, "
            f"制动延迟: {result['brake_latency_ms']} ms, safe={result['safe']}"
        )
        _recover_to_armed(node, 0)

        # ==================== 故障 2：NaN 注入 ====================
        print("\n[FAULT 2] NaN 注入（触发 nan_detected）")
        node.start_fault_measurement("nan_injection", "ARMED")
        node.imu_fault_mode_ = "nan"  # 切换到 NaN 模式
        _wait_fault_detected(node, timeout_sec=1.5)
        time.sleep(0.3)
        result = node.finish_fault_measurement(
            "IMU 数据含 NaN quaternion，触发 nan_detected=True → FAULT"
        )
        faults.append(result)
        print(
            f"  -> 检测延迟: {result['detection_latency_ms']} ms, "
            f"制动延迟: {result['brake_latency_ms']} ms, safe={result['safe']}"
        )
        _recover_to_armed(node, 1)

        # ==================== 故障 3：时间戳回退 ====================
        print("\n[FAULT 3] 时间戳回退（触发 timestamp_regression → communication_lost）")
        node.start_fault_measurement("timestamp_regression", "ARMED")
        node.imu_fault_mode_ = "timestamp_regression"
        _wait_fault_detected(node, timeout_sec=1.5)
        time.sleep(0.3)
        result = node.finish_fault_measurement(
            "IMU header.stamp 倒退 5 秒，触发 timestamp_regression → communication_lost → FAULT"
        )
        faults.append(result)
        print(
            f"  -> 检测延迟: {result['detection_latency_ms']} ms, "
            f"制动延迟: {result['brake_latency_ms']} ms, safe={result['safe']}"
        )
        _recover_to_armed(node, 2)

        # ==================== 故障 4：通信中断 250ms ====================
        print("\n[FAULT 4] 通信中断 250ms（触发 communication_lost）")
        node.start_fault_measurement("communication_lost", "ARMED")
        node.imu_publishing_ = False  # 停止发布 IMU
        _wait_fault_detected(node, timeout_sec=1.5)
        time.sleep(0.3)
        result = node.finish_fault_measurement(
            "IMU 断流 250ms，触发 communication_lost=True → FAULT"
        )
        faults.append(result)
        print(
            f"  -> 检测延迟: {result['detection_latency_ms']} ms, "
            f"制动延迟: {result['brake_latency_ms']} ms, safe={result['safe']}"
        )
        _recover_to_armed(node, 3)

        # ==================== 故障 5：急停 ====================
        print("\n[FAULT 5] 急停（调用 /estop 服务）")
        node.start_fault_measurement("estop", "ARMED")
        if not node.call_service(node.estop_client_, "estop"):
            raise RuntimeError("/estop 服务调用失败")
        _wait_fault_detected(node, timeout_sec=1.5)
        time.sleep(0.3)
        result = node.finish_fault_measurement(
            "调用 /estop 服务，触发 estop_triggered=True → FAULT"
        )
        faults.append(result)
        print(
            f"  -> 检测延迟: {result['detection_latency_ms']} ms, "
            f"制动延迟: {result['brake_latency_ms']} ms, safe={result['safe']}"
        )

        # ==================== 汇总 ====================
        detected_count = sum(1 for f in faults if f["safe"])
        all_safe = all(f["safe"] for f in faults)
        det_lats = [
            f["detection_latency_ms"]
            for f in faults
            if f["detection_latency_ms"] is not None
        ]
        brake_lats = [
            f["brake_latency_ms"]
            for f in faults
            if f["brake_latency_ms"] is not None
        ]

        summary = {
            "fault_count": len(faults),
            "detected_count": detected_count,
            "all_faults_safe": all_safe,
            "mean_detection_latency_ms": (
                round(sum(det_lats) / len(det_lats), 3) if det_lats else None
            ),
            "mean_brake_latency_ms": (
                round(sum(brake_lats) / len(brake_lats), 3) if brake_lats else None
            ),
        }

        output = {
            "scenario": "real_ros2_fault_injection",
            "ros2_distro": "jazzy",
            "control_rate_hz": 100,
            "faults": faults,
            "state_timeline": node.state_records_,
            "torque_timeline": node.torque_records_,
            "summary": summary,
        }

        observed = node.qos_observation()
        compatible = all(value > 0 for value in observed.values())
        qos_evidence = {
            "compatible": compatible,
            "source": "rclpy DDS endpoint discovery and actual callback counters",
            "observed": observed,
        }
        Path(paths["qos_log"]).write_text(
            json.dumps(qos_evidence, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        out_path = Path(paths["fault_result"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n[OK] 结果已写入: {out_path}")
        print(f"[SUMMARY] {summary}")
        return 0 if all_safe and compatible else 1

    finally:
        # 终止 control_node 子进程
        print("[INFO] 终止 control_node 子进程 ...")
        try:
            os.killpg(os.getpgid(control_proc.pid), signal.SIGTERM)
            control_proc.wait(timeout=2.0)
        except Exception:
            try:
                os.killpg(os.getpgid(control_proc.pid), signal.SIGKILL)
            except Exception:
                pass
        # 关闭日志文件
        try:
            control_log_file.close()
        except Exception:
            pass
        # 打印 control_node 日志（便于调试）
        try:
            with open(control_log_path) as f:
                log_content = f.read()
            print("\n=== control_node 日志（最后 30 行）===")
            log_lines = log_content.strip().split("\n")
            for line in log_lines[-30:]:
                print(line)
        except Exception:
            pass
        # 关闭 executor
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description="运行真实 ROS2 故障注入与证据采集")
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="fresh 输出根目录，接受 WSL 路径或 Windows 盘符路径",
    )
    parser.add_argument(
        "--install-prefix",
        default=DEFAULT_INSTALL_PREFIX,
        help="已完成 colcon build 的 ROS2 install prefix",
    )
    args = parser.parse_args()
    if ROS_IMPORT_ERROR is not None:
        print(
            f"[FAIL] 当前环境缺少 ROS2 Python 依赖: {ROS_IMPORT_ERROR}",
            file=sys.stderr,
        )
        return 2
    paths = resolve_output_paths(args.output_root)
    return run_injection(paths, _as_wsl_path(args.install_prefix))


if __name__ == "__main__":
    sys.exit(main())
