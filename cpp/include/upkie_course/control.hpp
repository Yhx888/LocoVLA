#pragma once

#include <Eigen/Core>
#include <array>

namespace upkie_course {

struct BalanceGains {
  double position = 2.0;
  double velocity = 0.8;
  double pitch = 3.0;
  double pitch_rate = 0.8;
};

double balance_torque(const Eigen::Vector4d& state_error,
                      const BalanceGains& gains = {});

std::array<double, 2> wheel_torques(double balance,
                                    double yaw,
                                    double limit = 1.0);

}  // namespace upkie_course
