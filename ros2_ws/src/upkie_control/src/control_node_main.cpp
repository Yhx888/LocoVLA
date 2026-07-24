#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "upkie_control/control_node.hpp"

int main(int argc, char** argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<upkie_control::ControlNode>());
  rclcpp::shutdown();
  return 0;
}
