#pragma once
#include <array>
#include <cstdint>
#include <string>

namespace upkie_control {

// 第 42 关统一日志条目（9 字段）
// 用于控制节点每个 tick 的结构化记录，输出为 JSON lines（.jsonl）。
struct LogEntry {
  uint64_t timestamp_ns;          // 单调时钟纳秒
  uint32_t episode_id;            // 运行编号
  std::string git_commit;         // 短 hash
  double pitch_rad;               // 俯仰角
  double pitch_rate_rad_s;        // 俯仰角速度
  double raw_torque_common_nm;    // 限幅前公共力矩
  double clamped_torque_common_nm;  // 限幅后公共力矩
  uint8_t safety_flag;            // 0=正常, 1=协方差无效, 2=力矩饱和, 3=FAULT 状态
  double loop_cycle_ms;           // 本周期耗时
};

// 将 LogEntry 序列化为 JSON lines 字符串（不含换行符）
std::string serialize_log_entry(const LogEntry& entry);

// 校验 JSON 字符串是否含全部 9 个必需字段
bool validate_log_entry(const std::string& json_line);

// 校验时间戳序列是否单调递增（允许相等返回 false）
bool check_monotonic(uint64_t prev_ns, uint64_t curr_ns);

// 必需字段列表（用于校验）
constexpr std::array<const char*, 9> REQUIRED_LOG_FIELDS = {
    "timestamp_ns",      "episode_id",           "git_commit",
    "pitch_rad",         "pitch_rate_rad_s",     "raw_torque_common_nm",
    "clamped_torque_common_nm", "safety_flag",   "loop_cycle_ms"};

}  // namespace upkie_control
