#include "upkie_control/safety_state_machine.hpp"

namespace upkie_control {

// 安全状态机纯函数：根据当前状态和输入决定下一个状态
// 优先级（自顶向下）：
//   1. FAULT 显式 reset → BOOT（人工复位）
//   2. 任何故障条件 → FAULT（NaN / 通信失联 / 俯仰超限 / 急停触发）
//   3. 状态机正常推进（BOOT→SELF_CHECK→DISARMED→ARMED）
SafetyState transition(const SafetyInput& input) {
  // 1. FAULT 复位：仅显式 reset 请求才能离开 FAULT
  if (input.reset_requested && input.current_state == SafetyState::FAULT) {
    return SafetyState::BOOT;
  }

  // 2. 任何状态下的故障触发条件（按任务规则统一优先级）
  if (input.nan_detected || input.communication_lost ||
      !std::isfinite(input.pitch_safety_limit_rad) ||
      input.pitch_safety_limit_rad <= 0.0) {
    return SafetyState::FAULT;
  }
  if (std::abs(input.pitch_rad) > input.pitch_safety_limit_rad) {
    return SafetyState::FAULT;
  }
  if (!input.estop_released) {
    return SafetyState::FAULT;
  }
  if (input.current_state == SafetyState::ARMED && !input.sensor_fresh) {
    return SafetyState::FAULT;
  }

  // 3. 正常状态推进
  switch (input.current_state) {
    case SafetyState::BOOT:
      // 启动后立即进入自检
      return SafetyState::SELF_CHECK;
    case SafetyState::SELF_CHECK:
      // 传感器新鲜即视为自检通过
      return input.sensor_fresh ? SafetyState::DISARMED
                                : SafetyState::SELF_CHECK;
    case SafetyState::DISARMED:
      // 显式 arm 请求且条件满足才进入 ARMED
      return (input.arm_requested && is_safe_to_arm(input))
                 ? SafetyState::ARMED
                 : SafetyState::DISARMED;
    case SafetyState::ARMED:
      // 故障条件已在上文统一拦截，这里保持 ARMED
      return SafetyState::ARMED;
    case SafetyState::FAULT:
      // 仅 reset 才能离开，已在第 1 步处理；此处保持故障
      return SafetyState::FAULT;
    // P-CODE-017 修复：添加 default 分支，安全失败（未知状态 → FAULT）
    default:
      return SafetyState::FAULT;
  }
}

// 判断当前是否满足 arm 条件
// 条件：传感器新鲜 + 俯仰在安全范围内 + 急停释放
bool is_safe_to_arm(const SafetyInput& input) {
  return input.sensor_fresh &&
         std::abs(input.pitch_rad) < input.pitch_safety_limit_rad &&
         input.estop_released;
}

// 是否允许输出力矩（仅 ARMED 状态允许）
bool is_armed(SafetyState state) {
  return state == SafetyState::ARMED;
}

// 是否处于故障状态
bool is_fault(SafetyState state) {
  return state == SafetyState::FAULT;
}

// 状态名称字符串（用于日志和 /safety_state 话题）
const char* state_name(SafetyState state) {
  switch (state) {
    case SafetyState::BOOT:
      return "BOOT";
    case SafetyState::SELF_CHECK:
      return "SELF_CHECK";
    case SafetyState::DISARMED:
      return "DISARMED";
    case SafetyState::ARMED:
      return "ARMED";
    case SafetyState::FAULT:
      return "FAULT";
    // P-CODE-017 修复：添加 default 分支
    default:
      return "UNKNOWN";
  }
}

}  // namespace upkie_control
