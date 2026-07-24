#include "upkie_control/log_contract.hpp"

#include <cstdio>
#include <string>

namespace upkie_control {

// 将 LogEntry 序列化为紧凑 JSON 字符串（键值对冒号后无空格）。
// double 统一用 %.6f，保证可解析、可对比；整数类型做跨平台安全转换。
std::string serialize_log_entry(const LogEntry& entry) {
  char buf[512];
  const int n = std::snprintf(
      buf, sizeof(buf),
      "{\"timestamp_ns\":%llu,\"episode_id\":%u,\"git_commit\":\"%s\","
      "\"pitch_rad\":%.6f,\"pitch_rate_rad_s\":%.6f,"
      "\"raw_torque_common_nm\":%.6f,\"clamped_torque_common_nm\":%.6f,"
      "\"safety_flag\":%u,\"loop_cycle_ms\":%.6f}",
      static_cast<unsigned long long>(entry.timestamp_ns),
      static_cast<unsigned int>(entry.episode_id), entry.git_commit.c_str(),
      entry.pitch_rad, entry.pitch_rate_rad_s, entry.raw_torque_common_nm,
      entry.clamped_torque_common_nm,
      static_cast<unsigned int>(entry.safety_flag), entry.loop_cycle_ms);
  return std::string(buf, n > 0 ? static_cast<size_t>(n) : 0);
}

// 校验 JSON 字符串是否含全部 9 个必需字段（简单子串查找）。
bool validate_log_entry(const std::string& json_line) {
  for (const char* field : REQUIRED_LOG_FIELDS) {
    if (json_line.find(field) == std::string::npos) {
      return false;
    }
  }
  return true;
}

// 时间戳严格单调递增校验（相等返回 false）。
bool check_monotonic(uint64_t prev_ns, uint64_t curr_ns) {
  return curr_ns > prev_ns;
}

}  // namespace upkie_control
