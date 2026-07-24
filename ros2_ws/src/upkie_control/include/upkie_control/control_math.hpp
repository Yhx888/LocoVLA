#ifndef UPKIE_CONTROL_CONTROL_MATH_HPP_
#define UPKIE_CONTROL_CONTROL_MATH_HPP_

#include <array>

namespace upkie_control {

// 四元数（wxyz 顺序）转 pitch（rad），仅取绕 Y 轴的旋转分量。
// 数学推导：对于绕 Y 轴的纯旋转四元数 [cos(θ/2), 0, sin(θ/2), 0]，
//   sine = 2*(w*y - z*x) = 2*cos(θ/2)*sin(θ/2) = sin(θ)，
//   pitch = asin(clamp(sine, -1, 1)) = θ（小角度范围内恒等）。
// 该函数不依赖 ROS，可独立单元测试。
double quaternion_to_pitch(double w, double x, double y, double z);

// 检查 IMU 姿态协方差是否有效。
// ROS 约定：orientation_covariance[0] < 0 表示协方差未知/无效。
// 本节点设计选择：协方差未知时 pitch 视为 0（入门节点不融合不可靠姿态）。
bool orientation_covariance_valid(double covariance_0);

// 传感器必须已经收到、协方差有效且未超过超时阈值，才可视为新鲜。
bool sensor_is_fresh(bool imu_received, bool covariance_valid,
                     double elapsed_ms, double timeout_ms);

// 力矩限幅：将 tau 限制到 [-limit, +limit]。
double clamp_torque(double tau, double limit);

// 计算左右轮力矩（PD 控制律 + 限幅 + 符号约定）。
// 符号约定：左轮 direction = +1.0，右轮 direction = -1.0。
// common = clamp(Kp*pitch + Kd*pitch_rate, limit)
// 返回值：[common, -common]（左轮、右轮）。
std::array<double, 2> compute_wheel_torques(double pitch, double pitch_rate,
                                             double Kp, double Kd, double limit);

// 在物理轮力矩层组合平衡公共量与偏航差动量，再分别限幅并转换为执行器符号。
std::array<double, 2> combine_balance_and_yaw_torques(
    double balance_common, double yaw_torque, double limit);

}  // namespace upkie_control

#endif  // UPKIE_CONTROL_CONTROL_MATH_HPP_
