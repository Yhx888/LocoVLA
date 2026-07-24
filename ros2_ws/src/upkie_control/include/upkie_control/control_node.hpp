#pragma once

#include <array>
#include <atomic>
#include <chrono>
#include <fstream>
#include <mutex>
#include <string>
#include <vector>

#include "builtin_interfaces/msg/time.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "std_msgs/msg/float64.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"
#include "std_msgs/msg/string.hpp"
#include "std_srvs/srv/trigger.hpp"
#include "upkie_control/safety_state_machine.hpp"

namespace upkie_control {

class ControlNode final : public rclcpp::Node {
 public:
  explicit ControlNode(const rclcpp::NodeOptions& options = rclcpp::NodeOptions());
  ~ControlNode() override;

  std::array<double, 2> GetLastTorques() const;
  SafetyState GetSafetyState() const;

 private:
  void control_tick();
  void WriteTimingJson();

  std::atomic<double> pitch_;
  std::atomic<double> pitch_rate_;
  std::atomic<double> yaw_rate_;
  std::atomic<double> yaw_rate_command_;
  std::atomic<double> last_torque_left_;
  std::atomic<double> last_torque_right_;
  std::atomic<bool> covariance_valid_;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr torque_pub_;
  rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr imu_sub_;
  rclcpp::Subscription<std_msgs::msg::Float64>::SharedPtr yaw_rate_command_sub_;
  rclcpp::TimerBase::SharedPtr timer_;

  bool record_timing_{false};
  std::string record_timing_path_;
  std::vector<std::chrono::steady_clock::time_point> timestamps_;
  std::mutex timing_mutex_;

  bool record_log_{false};
  std::string log_path_;
  int episode_id_{0};
  std::ofstream log_file_;

  std::atomic<SafetyState> safety_state_{SafetyState::BOOT};
  std::atomic<bool> estop_triggered_{false};
  std::atomic<bool> arm_requested_{false};
  std::atomic<bool> reset_requested_{false};
  double pitch_safety_limit_rad_{0.3};
  double yaw_rate_gain_{0.05};
  double yaw_torque_limit_{0.15};
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr safety_state_pub_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr estop_service_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr arm_service_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr reset_service_;

  std::chrono::steady_clock::time_point last_imu_steady_time_;
  std::atomic<bool> nan_detected_{false};
  std::atomic<bool> timestamp_regression_{false};
  std::atomic<bool> imu_ever_received_{false};
  builtin_interfaces::msg::Time last_imu_header_stamp_;
  std::mutex imu_stamp_mutex_;
};

}  // namespace upkie_control
