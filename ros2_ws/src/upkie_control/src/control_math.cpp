#include "upkie_control/control_math.hpp"

#include <algorithm>
#include <cmath>

namespace upkie_control {

double quaternion_to_pitch(double w, double x, double y, double z) {
  // 取绕 Y 轴旋转的分量：sine = 2*(w*y - z*x)
  const double sine = 2.0 * (w * y - z * x);
  // asin 定义域为 [-1, 1]，浮点误差可能略微越界，需 clamp
  return std::asin(std::clamp(sine, -1.0, 1.0));
}

bool orientation_covariance_valid(double covariance_0) {
  // ROS 约定：covariance[0] < 0 表示协方差未知
  return std::isfinite(covariance_0) && covariance_0 >= 0.0;
}

bool sensor_is_fresh(bool imu_received, bool covariance_valid,
                     double elapsed_ms, double timeout_ms) {
  return imu_received && covariance_valid && std::isfinite(elapsed_ms) &&
         timeout_ms > 0.0 && elapsed_ms <= timeout_ms;
}

double clamp_torque(double tau, double limit) {
  return std::clamp(tau, -limit, limit);
}

std::array<double, 2> compute_wheel_torques(double pitch, double pitch_rate,
                                            double Kp, double Kd, double limit) {
  // PD 控制律：common = clamp(Kp*pitch + Kd*pitch_rate, limit)
  // 轮符号约定：左轮 +1.0，右轮 -1.0
  const double common = clamp_torque(Kp * pitch + Kd * pitch_rate, limit);
  return {common, -common};
}

std::array<double, 2> combine_balance_and_yaw_torques(
    double balance_common, double yaw_torque, double limit) {
  const double left_physical = balance_common - yaw_torque;
  const double right_physical = balance_common + yaw_torque;
  return {
      clamp_torque(left_physical, limit),
      -clamp_torque(right_physical, limit),
  };
}

}  // namespace upkie_control
