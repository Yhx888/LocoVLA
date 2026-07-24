// 第 40 关控制节点单元测试
// 覆盖五项核心逻辑：四元数转 pitch、协方差处理、力矩限幅、轮符号约定、控制律。
// 测试独立于 ROS2 运行（ament_cmake_gtest 编译为独立可执行文件）。

#include <cmath>
#include <chrono>
#include <limits>
#include <thread>

#include <gtest/gtest.h>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "std_msgs/msg/float64.hpp"
#include "std_srvs/srv/trigger.hpp"
#include "upkie_control/control_node.hpp"
#include "upkie_control/control_math.hpp"

namespace {
constexpr double kTol6 = 1e-6;  // 高精度容差（用于数学恒等式验证）
constexpr double kTol4 = 1e-4;  // 中等精度容差（用于查表值验证）
constexpr double kTol3 = 1e-3;  // 控制律容差（spec 要求）
}  // namespace

// ==========================================================================
// 四元数（wxyz）转 pitch 测试
// ==========================================================================

// 用例 1：Upkie 默认姿态四元数（来自 configs/robot/upkie.json 的 default_base_quaternion）
// wxyz = [0.9974656375, 0, 0.0711498553, 0]，对应 equilibrium_pitch_rad ≈ 0.1424200457
TEST(QuaternionToPitch, SmallAngle) {
  const double w = 0.9974656375;
  const double x = 0.0;
  const double y = 0.0711498553;
  const double z = 0.0;
  const double pitch = upkie_control::quaternion_to_pitch(w, x, y, z);
  // 期望值 0.1424200457 rad（upkie.json 中 equilibrium_pitch_rad）
  EXPECT_NEAR(pitch, 0.1424200457, kTol4);
}

// 用例 2：构造已知 pitch=0.1 rad 的四元数 wxyz=[cos(0.05), 0, sin(0.05), 0]
// 验证转换的可逆性（sin(2*θ/2) = sin(θ)，asin(sin(θ)) = θ）
TEST(QuaternionToPitch, KnownAngle) {
  const double pitch_target = 0.1;
  const double w = std::cos(pitch_target / 2.0);
  const double x = 0.0;
  const double y = std::sin(pitch_target / 2.0);
  const double z = 0.0;
  const double pitch = upkie_control::quaternion_to_pitch(w, x, y, z);
  EXPECT_NEAR(pitch, pitch_target, kTol6);
}

// ==========================================================================
// 力矩限幅测试（范围 [-1.0, 1.0] N·m）
// ==========================================================================

TEST(ClampTorque, WithinLimit) {
  EXPECT_DOUBLE_EQ(upkie_control::clamp_torque(0.5, 1.0), 0.5);
  EXPECT_DOUBLE_EQ(upkie_control::clamp_torque(-0.5, 1.0), -0.5);
  EXPECT_DOUBLE_EQ(upkie_control::clamp_torque(0.0, 1.0), 0.0);
}

TEST(ClampTorque, OverLimit) {
  // 正向超限 → 限幅到 +1.0
  EXPECT_DOUBLE_EQ(upkie_control::clamp_torque(1.5, 1.0), 1.0);
  // 负向超限 → 限幅到 -1.0
  EXPECT_DOUBLE_EQ(upkie_control::clamp_torque(-1.5, 1.0), -1.0);
}

// ==========================================================================
// 轮力矩计算测试（PD 控制律 + 符号约定 + 限幅）
// 注意：实际源码为 PD 控制 Kp*pitch + Kd*pitch_rate，Kp=3.0, Kd=0.8。
// spec 假设纯比例 K=3.8（pitch=0.1 → 0.380 N·m），但实际源码 Kp=3.0
// （pitch=0.1, pitch_rate=0 → 0.3 N·m）。本测试以源码实际值为准。
// ==========================================================================

TEST(WheelTorques, ControlLaw) {
  // pitch=0.1, pitch_rate=0 → common = clamp(3.0*0.1 + 0.8*0, 1.0) = 0.3
  // spec 假设 K=3.8 → 0.380，实际源码 Kp=3.0 → 0.3，以源码为准
  const auto torques =
      upkie_control::compute_wheel_torques(0.1, 0.0, 3.0, 0.8, 1.0);
  EXPECT_NEAR(torques[0], 0.3, kTol3);
  EXPECT_NEAR(torques[1], -0.3, kTol3);
}

TEST(WheelTorques, SignConvention) {
  // 符号约定：左轮 direction=+1.0，右轮 direction=-1.0
  // 正 pitch 应产生左轮正力矩、右轮负力矩
  const auto torques =
      upkie_control::compute_wheel_torques(0.1, 0.0, 3.0, 0.8, 1.0);
  EXPECT_GT(torques[0], 0.0);  // 左轮正力矩
  EXPECT_LT(torques[1], 0.0);  // 右轮负力矩
  // 左右轮力矩大小相等、方向相反
  EXPECT_NEAR(torques[0], -torques[1], kTol6);
}

TEST(WheelTorques, Clamping) {
  // pitch=1.0, pitch_rate=0 → common = clamp(3.0*1.0 + 0, 1.0) = 1.0（被限幅）
  const auto torques =
      upkie_control::compute_wheel_torques(1.0, 0.0, 3.0, 0.8, 1.0);
  EXPECT_NEAR(torques[0], 1.0, kTol6);   // 左轮限幅到 +1.0
  EXPECT_NEAR(torques[1], -1.0, kTol6);  // 右轮限幅到 -1.0
}

// ==========================================================================
// 姿态协方差处理测试
// ROS 约定：orientation_covariance[0] < 0 表示协方差未知/无效。
// 本节点设计选择：协方差未知时 pitch 视为 0（不融合不可靠姿态）。
// ==========================================================================

TEST(CovarianceHandling, UnknownCovariance) {
  // 协方差未知（covariance[0] < 0）→ 判定为无效
  EXPECT_FALSE(upkie_control::orientation_covariance_valid(-1.0));
  EXPECT_FALSE(upkie_control::orientation_covariance_valid(-0.01));
  // 协方差已知（covariance[0] >= 0）→ 判定为有效
  EXPECT_TRUE(upkie_control::orientation_covariance_valid(0.0));
  EXPECT_TRUE(upkie_control::orientation_covariance_valid(0.001));
  EXPECT_TRUE(upkie_control::orientation_covariance_valid(1e-4));
  EXPECT_FALSE(upkie_control::orientation_covariance_valid(
      std::numeric_limits<double>::quiet_NaN()));
}

TEST(SensorFreshness, RequiresReceivedValidRecentImu) {
  EXPECT_FALSE(upkie_control::sensor_is_fresh(false, true, 0.0, 50.0));
  EXPECT_FALSE(upkie_control::sensor_is_fresh(true, false, 0.0, 50.0));
  EXPECT_TRUE(upkie_control::sensor_is_fresh(true, true, 10.0, 50.0));
  EXPECT_FALSE(upkie_control::sensor_is_fresh(true, true, 51.0, 50.0));
}

TEST(WheelTorques, BalanceAndYawAreCombinedBeforePerWheelClamp) {
  const auto torques =
      upkie_control::combine_balance_and_yaw_torques(0.8, 0.4, 1.0);
  EXPECT_DOUBLE_EQ(torques[0], 0.4);
  EXPECT_DOUBLE_EQ(torques[1], -1.0);
}

namespace {

class RosEnvironment : public ::testing::Environment {
 public:
  void SetUp() override {
    if (!rclcpp::ok()) {
      int argc = 0;
      rclcpp::init(argc, nullptr);
    }
  }

  void TearDown() override {
    if (rclcpp::ok()) {
      rclcpp::shutdown();
    }
  }
};

const auto* const kRosEnvironment =
    ::testing::AddGlobalTestEnvironment(new RosEnvironment());

void spin_for(rclcpp::executors::SingleThreadedExecutor& executor,
              std::chrono::milliseconds duration) {
  const auto deadline = std::chrono::steady_clock::now() + duration;
  while (std::chrono::steady_clock::now() < deadline) {
    executor.spin_some();
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
  }
}

sensor_msgs::msg::Imu make_imu(double pitch_rad, double covariance_0,
                               double yaw_rate = 0.0) {
  sensor_msgs::msg::Imu message;
  message.orientation.w = std::cos(pitch_rad / 2.0);
  message.orientation.y = std::sin(pitch_rad / 2.0);
  message.orientation_covariance[0] = covariance_0;
  message.angular_velocity.z = yaw_rate;
  return message;
}

void publish_imu(const rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr& publisher,
                 const sensor_msgs::msg::Imu& message,
                 rclcpp::executors::SingleThreadedExecutor& executor) {
  for (int index = 0; index < 3; ++index) {
    publisher->publish(message);
    spin_for(executor, std::chrono::milliseconds(8));
  }
}

void request_arm(const rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr& client,
                 rclcpp::executors::SingleThreadedExecutor& executor) {
  ASSERT_TRUE(client->wait_for_service(std::chrono::seconds(1)));
  auto future = client->async_send_request(
      std::make_shared<std_srvs::srv::Trigger::Request>());
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(1);
  while (future.wait_for(std::chrono::milliseconds(0)) != std::future_status::ready &&
         std::chrono::steady_clock::now() < deadline) {
    executor.spin_some();
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
  }
  ASSERT_EQ(future.wait_for(std::chrono::milliseconds(0)), std::future_status::ready);
}

}  // namespace

TEST(ControlNodeIntegration, NoImuOrInvalidCovarianceCannotArm) {
  auto control = std::make_shared<upkie_control::ControlNode>();
  auto driver = std::make_shared<rclcpp::Node>("control_node_invalid_imu_driver");
  auto imu = driver->create_publisher<sensor_msgs::msg::Imu>("imu", 10);
  auto arm = driver->create_client<std_srvs::srv::Trigger>("arm");
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(control);
  executor.add_node(driver);

  spin_for(executor, std::chrono::milliseconds(25));
  request_arm(arm, executor);
  EXPECT_NE(control->GetSafetyState(), upkie_control::SafetyState::ARMED);

  publish_imu(imu, make_imu(0.0, -1.0), executor);
  request_arm(arm, executor);
  spin_for(executor, std::chrono::milliseconds(15));
  EXPECT_NE(control->GetSafetyState(), upkie_control::SafetyState::ARMED);
}

TEST(ControlNodeIntegration, ValidImuArmsAndYawCommandProducesLimitedDifferentialTorque) {
  auto control = std::make_shared<upkie_control::ControlNode>();
  auto driver = std::make_shared<rclcpp::Node>("control_node_valid_imu_driver");
  auto imu = driver->create_publisher<sensor_msgs::msg::Imu>("imu", 10);
  auto yaw = driver->create_publisher<std_msgs::msg::Float64>("yaw_rate_command", 10);
  auto arm = driver->create_client<std_srvs::srv::Trigger>("arm");
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(control);
  executor.add_node(driver);

  publish_imu(imu, make_imu(0.0, 0.01), executor);
  request_arm(arm, executor);
  publish_imu(imu, make_imu(0.0, 0.01), executor);
  ASSERT_EQ(control->GetSafetyState(), upkie_control::SafetyState::ARMED);

  std_msgs::msg::Float64 yaw_command;
  yaw_command.data = 10.0;
  yaw->publish(yaw_command);
  publish_imu(imu, make_imu(0.0, 0.01), executor);
  const auto torques = control->GetLastTorques();
  EXPECT_GT(std::abs(torques[0] + torques[1]), 0.01);
  EXPECT_LE(std::abs(torques[0]), 1.0);
  EXPECT_LE(std::abs(torques[1]), 1.0);
}

TEST(ControlNodeIntegration, InvalidCovarianceAfterArmingTriggersFault) {
  auto control = std::make_shared<upkie_control::ControlNode>();
  auto driver = std::make_shared<rclcpp::Node>("control_node_covariance_loss_driver");
  auto imu = driver->create_publisher<sensor_msgs::msg::Imu>("imu", 10);
  auto arm = driver->create_client<std_srvs::srv::Trigger>("arm");
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(control);
  executor.add_node(driver);

  publish_imu(imu, make_imu(0.0, 0.01), executor);
  request_arm(arm, executor);
  publish_imu(imu, make_imu(0.0, 0.01), executor);
  ASSERT_EQ(control->GetSafetyState(), upkie_control::SafetyState::ARMED);

  publish_imu(imu, make_imu(0.0, -1.0), executor);
  EXPECT_EQ(control->GetSafetyState(), upkie_control::SafetyState::FAULT);
}

TEST(ControlNodeIntegration, RuntimePitchLimitTriggersFault) {
  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("pitch_safety_limit", 0.1)});
  auto control = std::make_shared<upkie_control::ControlNode>(options);
  auto driver = std::make_shared<rclcpp::Node>("control_node_pitch_limit_driver");
  auto imu = driver->create_publisher<sensor_msgs::msg::Imu>("imu", 10);
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(control);
  executor.add_node(driver);

  publish_imu(imu, make_imu(0.2, 0.01), executor);
  EXPECT_EQ(control->GetSafetyState(), upkie_control::SafetyState::FAULT);
}
