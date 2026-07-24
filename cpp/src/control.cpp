#include "upkie_course/control.hpp"

#include <algorithm>

namespace upkie_course {

double balance_torque(const Eigen::Vector4d& state_error,
                      const BalanceGains& gains) {
  const Eigen::Vector4d gain_vector{
      gains.position, gains.velocity, gains.pitch, gains.pitch_rate};
  return gain_vector.dot(state_error);
}

std::array<double, 2> wheel_torques(double balance,
                                    double yaw,
                                    double limit) {
  const auto clip = [limit](double value) {
    return std::clamp(value, -limit, limit);
  };
  // 右轮关节轴与左轮相反，因此前进公共力矩在执行器坐标中符号相反。
  return {clip(balance - yaw), clip(-balance - yaw)};
}

}  // namespace upkie_course
