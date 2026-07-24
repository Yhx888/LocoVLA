#pragma once
#include <cmath>
#include <cstdint>

namespace upkie_control {

// 安全状态机五状态
enum class SafetyState : uint8_t {
  BOOT = 0,        // 上电启动
  SELF_CHECK = 1,  // 自检中
  DISARMED = 2,    // 已解锁但未 armed（待命）
  ARMED = 3,       // 已 armed（可输出力矩）
  FAULT = 4,       // 故障（输出零力矩，需人工复位）
};

// 状态转换输入
struct SafetyInput {
  SafetyState current_state;
  double pitch_rad;              // 当前俯仰角
  bool sensor_fresh;             // 传感器是否新鲜（未超时）
  bool estop_released;           // 急停是否释放
  bool arm_requested;            // 操作者是否显式请求 arm
  bool reset_requested;          // 操作者是否显式请求 reset（FAULT→BOOT）
  bool nan_detected;             // 是否检测到 NaN
  bool communication_lost;       // 通信是否失联
  double pitch_safety_limit_rad; // 当前运行时俯仰安全阈值
};

// 状态转换纯函数
// 规则：
// - BOOT → SELF_CHECK：自动（启动后立即进入自检）
// - SELF_CHECK → DISARMED：自检通过（传感器新鲜、无 NaN、通信正常）
// - DISARMED → ARMED：传感器新鲜 + |pitch|<0.3 + 急停释放 + 显式 arm 请求
// - 任何状态 → FAULT：NaN 检测、通信失联、|pitch|>0.3、急停触发
// - FAULT → BOOT：仅显式 reset 请求（不自动恢复）
// - FAULT 状态输出零力矩
SafetyState transition(const SafetyInput& input);

// 判断是否可以 arm
bool is_safe_to_arm(const SafetyInput& input);

// 判断当前状态是否允许输出力矩
bool is_armed(SafetyState state);

// 判断当前状态是否为故障
bool is_fault(SafetyState state);

// 状态名称（用于日志和话题发布）
const char* state_name(SafetyState state);

// 默认安全俯仰角阈值（rad）
constexpr double PITCH_SAFETY_LIMIT_RAD = 0.3;

}  // namespace upkie_control
