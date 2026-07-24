#include "upkie_course/control.hpp"

#include <iomanip>
#include <iostream>

int main() {
  std::cout << std::setprecision(17);
  double position = 0.0;
  double velocity = 0.0;
  double pitch = 0.0;
  double pitch_rate = 0.0;
  double yaw = 0.0;
  double limit = 0.0;

  while (std::cin >> position >> velocity >> pitch >> pitch_rate >> yaw >> limit) {
    const Eigen::Vector4d state_error{position, velocity, pitch, pitch_rate};
    const double balance = upkie_course::balance_torque(state_error);
    const auto wheels = upkie_course::wheel_torques(balance, yaw, limit);
    std::cout << balance << ' ' << wheels[0] << ' ' << wheels[1] << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
