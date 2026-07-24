#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 40 关证据采集：监听 /wheel_torque 输出。

订阅 /wheel_torque（std_msgs/Float64MultiArray）并记录每条消息的
时间戳和力矩值，用于故障注入证据采集。

用法（在 WSL2 中，已 source install/setup.bash）：
  python3 /mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/scripts/tools/record_wheel_torque.py \
      --duration 10 --output /mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/outputs/logs/eng_40_torque.json
"""

import argparse
import json
import sys
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy, QoSReliabilityPolicy
from std_msgs.msg import Float64MultiArray


class TorqueRecorder(Node):
    """记录 /wheel_torque 消息。"""

    def __init__(self, duration_sec: float, output_path: str):
        super().__init__("torque_recorder")
        # 订阅端使用 SensorDataQoS 等价配置以匹配控制节点发布端
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.sub_ = self.create_subscription(
            Float64MultiArray, "wheel_torque", self._on_msg, qos)
        self.duration_sec_ = duration_sec
        self.output_path_ = output_path
        self.start_time_ = self.get_clock().now()
        self.records_ = []
        self.get_logger().info(
            f"力矩记录节点启动: duration={duration_sec}s, output={output_path}")

    def _on_msg(self, msg: Float64MultiArray):
        elapsed = (self.get_clock().now() - self.start_time_).nanoseconds / 1e9
        if elapsed >= self.duration_sec_:
            self._flush_and_exit()
            return
        if len(msg.data) >= 2:
            self.records_.append({
                "t_sec": round(elapsed, 6),
                "left": msg.data[0],
                "right": msg.data[1],
            })

    def _flush_and_exit(self):
        # 计算统计信息
        if self.records_:
            left_vals = [r["left"] for r in self.records_]
            right_vals = [r["right"] for r in self.records_]
            stats = {
                "count": len(self.records_),
                "left_min": min(left_vals),
                "left_max": max(left_vals),
                "left_last": left_vals[-1],
                "right_min": min(right_vals),
                "right_max": max(right_vals),
                "right_last": right_vals[-1],
            }
        else:
            stats = {"count": 0}

        output = {
            "topic": "/wheel_torque",
            "duration_sec": self.duration_sec_,
            "statistics": stats,
            "records": self.records_,
        }
        Path(self.output_path_).parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path_, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        self.get_logger().info(
            f"已记录 {len(self.records_)} 条消息，写入 {self.output_path_}")
        raise SystemExit(0)

    def flush_on_shutdown(self):
        """Ctrl+C 时也写入。"""
        if self.records_:
            self._flush_and_exit()


def main(argv=None):
    parser = argparse.ArgumentParser(description="记录 /wheel_torque 消息")
    parser.add_argument("--duration", type=float, default=10.0,
                        help="持续时长秒（默认 10）")
    parser.add_argument("--output", type=str, required=True,
                        help="输出 JSON 文件路径")
    args = parser.parse_args(argv)

    rclpy.init(args=sys.argv[:1])
    node = TorqueRecorder(args.duration, args.output)
    try:
        rclpy.spin(node)
    except SystemExit:
        node.get_logger().info("力矩记录节点正常退出")
    except KeyboardInterrupt:
        node.get_logger().info("收到 Ctrl+C，写入已记录数据后退出")
        node.flush_on_shutdown()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
