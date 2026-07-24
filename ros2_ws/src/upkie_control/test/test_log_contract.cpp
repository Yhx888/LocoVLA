// 第 42 关统一日志契约单元测试
// 覆盖：序列化含 9 字段、字段缺失校验、单调时间戳、安全标志取值、力矩记录精度。
// 测试独立于 ROS2 运行（ament_cmake_gtest 编译为独立可执行文件）。

#include <sstream>

#include <gtest/gtest.h>

#include "upkie_control/log_contract.hpp"

// ==========================================================================
// 序列化：9 个必需字段必须全部出现
// ==========================================================================
TEST(LogContractSerialize, ContainsAllNineFields) {
  upkie_control::LogEntry entry{1234567890, 0, "abc1234", 0.1, 0.0, 0.3, 0.3, 0, 10.0};
  std::string json = upkie_control::serialize_log_entry(entry);
  // 检查 9 个字段都存在
  EXPECT_NE(json.find("timestamp_ns"), std::string::npos);
  EXPECT_NE(json.find("episode_id"), std::string::npos);
  EXPECT_NE(json.find("git_commit"), std::string::npos);
  EXPECT_NE(json.find("pitch_rad"), std::string::npos);
  EXPECT_NE(json.find("pitch_rate_rad_s"), std::string::npos);
  EXPECT_NE(json.find("raw_torque_common_nm"), std::string::npos);
  EXPECT_NE(json.find("clamped_torque_common_nm"), std::string::npos);
  EXPECT_NE(json.find("safety_flag"), std::string::npos);
  EXPECT_NE(json.find("loop_cycle_ms"), std::string::npos);
}

// ==========================================================================
// 字段校验：缺失字段返回 false，完整返回 true
// ==========================================================================
TEST(LogContractValidate, MissingFieldReturnsFalse) {
  std::string incomplete = R"({"timestamp_ns":123,"episode_id":0})";
  EXPECT_FALSE(upkie_control::validate_log_entry(incomplete));
}

TEST(LogContractValidate, CompleteReturnsTrue) {
  upkie_control::LogEntry entry{1234567890, 0, "abc1234", 0.1, 0.0, 0.3, 0.3, 0, 10.0};
  std::string json = upkie_control::serialize_log_entry(entry);
  EXPECT_TRUE(upkie_control::validate_log_entry(json));
}

// ==========================================================================
// 单调时间戳：递增返回 true，递减/相等返回 false
// ==========================================================================
TEST(LogContractMonotonic, IncreasingReturnsTrue) {
  EXPECT_TRUE(upkie_control::check_monotonic(1000, 2000));
}

TEST(LogContractMonotonic, DecreasingReturnsFalse) {
  EXPECT_FALSE(upkie_control::check_monotonic(2000, 1000));
}

TEST(LogContractMonotonic, EqualReturnsFalse) {
  EXPECT_FALSE(upkie_control::check_monotonic(1000, 1000));
}

// ==========================================================================
// 安全标志取值：0=正常, 1=协方差无效, 2=力矩饱和
// ==========================================================================
TEST(LogContractSafetyFlag, NormalValue) {
  upkie_control::LogEntry entry{1234567890, 0, "abc1234", 0.1, 0.0, 0.3, 0.3, 0, 10.0};
  std::string json = upkie_control::serialize_log_entry(entry);
  EXPECT_NE(json.find("\"safety_flag\":0"), std::string::npos);
}

TEST(LogContractSafetyFlag, CovarianceInvalidValue) {
  upkie_control::LogEntry entry{1234567890, 0, "abc1234", 0.0, 0.0, 0.0, 0.0, 1, 10.0};
  std::string json = upkie_control::serialize_log_entry(entry);
  EXPECT_NE(json.find("\"safety_flag\":1"), std::string::npos);
}

TEST(LogContractSafetyFlag, TorqueSaturatedValue) {
  upkie_control::LogEntry entry{1234567890, 0, "abc1234", 0.5, 0.0, 1.5, 1.0, 2, 10.0};
  std::string json = upkie_control::serialize_log_entry(entry);
  EXPECT_NE(json.find("\"safety_flag\":2"), std::string::npos);
}

// ==========================================================================
// 力矩记录精度：raw 与 clamped 以 %.6f 格式记录
// ==========================================================================
TEST(LogContractTorque, RawAndClampedRecorded) {
  upkie_control::LogEntry entry{1234567890, 0, "abc1234", 0.5, 0.0, 1.5, 1.0, 2, 10.0};
  std::string json = upkie_control::serialize_log_entry(entry);
  EXPECT_NE(json.find("\"raw_torque_common_nm\":1.500000"), std::string::npos);
  EXPECT_NE(json.find("\"clamped_torque_common_nm\":1.000000"), std::string::npos);
}
