// 第 43 关：安全状态机纯函数单元测试
// 覆盖 transition 的全部状态转换路径、故障触发条件、复位逻辑，
// 以及 is_armed / is_fault 谓词。
// 注意：SafetyInput 最后一个字段是运行时俯仰安全阈值。
#include <gtest/gtest.h>
#include "upkie_control/safety_state_machine.hpp"
#include <cmath>

using upkie_control::SafetyState;
using upkie_control::SafetyInput;
using upkie_control::transition;
using upkie_control::is_armed;
using upkie_control::is_fault;

TEST(SafetyStateMachine, BootToSelfCheck) {
  // current_state=BOOT, pitch=0, sensor_fresh=true, estop_released=true
  // arm=false, reset=false, nan=false, comm_lost=false
  SafetyInput input{SafetyState::BOOT, 0.0, true, true, false, false, false, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::SELF_CHECK);
}

TEST(SafetyStateMachine, SelfCheckToDisarmed) {
  SafetyInput input{SafetyState::SELF_CHECK, 0.0, true, true, false, false, false, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::DISARMED);
}

TEST(SafetyStateMachine, SelfCheckStaysIfSensorStale) {
  // sensor_fresh=false → 自检未通过，保持 SELF_CHECK
  SafetyInput input{SafetyState::SELF_CHECK, 0.0, false, true, false, false, false, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::SELF_CHECK);
}

TEST(SafetyStateMachine, DisarmedToArmed) {
  // arm_requested=true 且条件满足 → ARMED
  SafetyInput input{SafetyState::DISARMED, 0.0, true, true, true, false, false, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::ARMED);
}

TEST(SafetyStateMachine, DisarmedStaysWithoutArmRequest) {
  // 缺少显式 arm 请求 → 保持 DISARMED
  SafetyInput input{SafetyState::DISARMED, 0.0, true, true, false, false, false, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::DISARMED);
}

TEST(SafetyStateMachine, PitchOverLimitToFault) {
  // |pitch|=0.5 > 0.3 → FAULT
  SafetyInput input{SafetyState::ARMED, 0.5, true, true, false, false, false, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::FAULT);
}

TEST(SafetyStateMachine, NanToFault) {
  // nan_detected=true → FAULT
  SafetyInput input{SafetyState::ARMED, 0.0, true, true, false, false, true, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::FAULT);
}

TEST(SafetyStateMachine, CommunicationLostToFault) {
  // communication_lost=true → FAULT
  SafetyInput input{SafetyState::ARMED, 0.0, true, true, false, false, false, true, 0.3};
  EXPECT_EQ(transition(input), SafetyState::FAULT);
}

TEST(SafetyStateMachine, ArmedStaleSensorToFault) {
  SafetyInput input{SafetyState::ARMED, 0.0, false, true, false, false, false, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::FAULT);
}

TEST(SafetyStateMachine, EstopToFault) {
  // estop_released=false → FAULT
  SafetyInput input{SafetyState::ARMED, 0.0, true, false, false, false, false, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::FAULT);
}

TEST(SafetyStateMachine, FaultDoesNotAutoRecover) {
  // 无 reset 请求 → 保持 FAULT
  SafetyInput input{SafetyState::FAULT, 0.0, true, true, false, false, false, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::FAULT);
}

TEST(SafetyStateMachine, FaultResetToBoot) {
  // 显式 reset_requested=true → BOOT（人工复位）
  SafetyInput input{SafetyState::FAULT, 0.0, true, true, false, true, false, false, 0.3};
  EXPECT_EQ(transition(input), SafetyState::BOOT);
}

TEST(SafetyStateMachine, IsArmedReturnsTrueOnlyForArmed) {
  EXPECT_FALSE(is_armed(SafetyState::BOOT));
  EXPECT_FALSE(is_armed(SafetyState::SELF_CHECK));
  EXPECT_FALSE(is_armed(SafetyState::DISARMED));
  EXPECT_TRUE(is_armed(SafetyState::ARMED));
  EXPECT_FALSE(is_armed(SafetyState::FAULT));
}

TEST(SafetyStateMachine, IsFaultReturnsTrueOnlyForFault) {
  EXPECT_FALSE(is_fault(SafetyState::BOOT));
  EXPECT_FALSE(is_fault(SafetyState::ARMED));
  EXPECT_TRUE(is_fault(SafetyState::FAULT));
}

TEST(SafetyStateMachine, UsesRuntimePitchSafetyLimit) {
  SafetyInput strict{SafetyState::ARMED, 0.2, true, true, false, false, false, false, 0.1};
  SafetyInput relaxed{SafetyState::ARMED, 0.2, true, true, false, false, false, false, 0.25};
  EXPECT_EQ(transition(strict), SafetyState::FAULT);
  EXPECT_EQ(transition(relaxed), SafetyState::ARMED);
}
