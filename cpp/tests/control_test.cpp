#include "upkie_course/control.hpp"

#include <cassert>
#include <cmath>

int main() {
  const Eigen::Vector4d error{0.1, 0.2, -0.05, 0.4};
  const double torque = upkie_course::balance_torque(error);
  assert(std::abs(torque - 0.53) < 1e-12);

  const auto wheels = upkie_course::wheel_torques(0.8, 0.4, 1.0);
  assert(std::abs(wheels[0] - 0.4) < 1e-12);
  assert(std::abs(wheels[1] + 1.0) < 1e-12);
  return 0;
}
