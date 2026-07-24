#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <memory>
#include <mutex>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "std_msgs/msg/float64.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"
#include "std_msgs/msg/string.hpp"
#include "std_srvs/srv/trigger.hpp"

#include "upkie_control/control_math.hpp"
#include "upkie_control/control_node.hpp"
#include "upkie_control/log_contract.hpp"
#include "upkie_control/safety_state_machine.hpp"

// 第 42 关：git 短 hash 由 CMake 注入；未注入时兜底为 "unknown"
#ifndef GIT_COMMIT_HASH
#define GIT_COMMIT_HASH "unknown"
#endif

// 第 43 关：从 upkie_control 命名空间引入安全状态机类型与函数
// 避免在 control_tick 中重复书写 upkie_control:: 前缀
using upkie_control::SafetyState;
using upkie_control::SafetyInput;
using upkie_control::transition;
using upkie_control::is_armed;
using upkie_control::is_fault;
using upkie_control::state_name;

// 第 40 关证据采集：控制节点
// 在原 PD 控制节点基础上新增 --record-timing 参数：
//   - 启用时记录每次 control_tick 的 steady_clock 时间戳
//   - 节点析构（rclcpp::shutdown 触发）时将时间戳写入 JSON 文件
//   - 文件路径由参数 record_timing_path 指定，默认输出到
//     /mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/outputs/logs/engineering_40_timing.json
// 该记录功能仅在显式启用时生效，不影响正常运行性能（关闭时零开销）。
//
// 第 42 关扩展：统一日志记录（--record-log）
//   - 启用时每个 tick 构造 LogEntry 并序列化为 JSON lines 写入 .jsonl 文件
//   - 记录 9 字段：时间戳/运行编号/git hash/俯仰角/角速度/限幅前后力矩/安全标志/周期耗时
//   - 安全标志：0=正常, 1=协方差无效(pitch==0 且协方差无效), 2=力矩饱和(|raw|>1.0)
upkie_control::ControlNode::ControlNode(const rclcpp::NodeOptions& options)
      : Node("upkie_control", options),
        pitch_(0.0),
        pitch_rate_(0.0),
        yaw_rate_(0.0),
        yaw_rate_command_(0.0) {
    // 声明参数：是否记录周期时间戳（默认关闭）
    declare_parameter<bool>("record_timing", false);
    declare_parameter<std::string>(
        "record_timing_path",
        "/mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/outputs/logs/"
        "engineering_40_timing.json");
    record_timing_ = get_parameter("record_timing").as_bool();
    record_timing_path_ = get_parameter("record_timing_path").as_string();

    // 第 42 关：统一日志参数
    declare_parameter<bool>("record_log", false);
    declare_parameter<std::string>(
        "log_path",
        "/mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/outputs/logs/"
        "engineering_42_log.jsonl");
    declare_parameter<int>("episode_id", 0);
    record_log_ = get_parameter("record_log").as_bool();
    log_path_ = get_parameter("log_path").as_string();
    episode_id_ = get_parameter("episode_id").as_int();

    // 同时声明最后一个 wheel_torque 输出，便于故障注入时核对实际行为
    last_torque_left_ = 0.0;
    last_torque_right_ = 0.0;
    covariance_valid_.store(false);

    // 第 43 关：安全状态机参数
    // --pitch-safety-limit：俯仰角安全阈值（rad），超过即触发 FAULT
    declare_parameter<double>("pitch_safety_limit", 0.3);
    pitch_safety_limit_rad_ = get_parameter("pitch_safety_limit").as_double();
    declare_parameter<double>("yaw_rate_gain", 0.05);
    declare_parameter<double>("yaw_torque_limit", 0.15);
    yaw_rate_gain_ = get_parameter("yaw_rate_gain").as_double();
    yaw_torque_limit_ = get_parameter("yaw_torque_limit").as_double();
    RCLCPP_INFO(get_logger(), "安全状态机已启用：pitch_safety_limit=%.3f rad",
                pitch_safety_limit_rad_);

    torque_pub_ = create_publisher<std_msgs::msg::Float64MultiArray>("wheel_torque", 10);
    // 第 43 关：发布当前安全状态（BOOT/SELF_CHECK/DISARMED/ARMED/FAULT）
    safety_state_pub_ =
        create_publisher<std_msgs::msg::String>("safety_state", 10);
    imu_sub_ = create_subscription<sensor_msgs::msg::Imu>(
        "imu", rclcpp::SensorDataQoS(),
        [this](const sensor_msgs::msg::Imu& msg) {
          // 第 43 关：NaN 检测——任一关键字段含 NaN 即置位
          if (std::isnan(msg.orientation.w) || std::isnan(msg.orientation.x) ||
              std::isnan(msg.orientation.y) || std::isnan(msg.orientation.z) ||
              std::isnan(msg.angular_velocity.y) ||
              std::isnan(msg.angular_velocity.z)) {
            nan_detected_.store(true);
            RCLCPP_WARN(get_logger(), "IMU 数据含 NaN，状态机将进入 FAULT");
            return;  // 不更新 pitch 等状态，避免 NaN 传播
          }

          // 第 43 关：时间戳回退检测
          if (imu_ever_received_.load()) {
            std::lock_guard<std::mutex> lock(imu_stamp_mutex_);
            // 比较 header.stamp（sec + nanosec）
            const auto new_ns = static_cast<int64_t>(msg.header.stamp.sec) * 1000000000LL
                              + static_cast<int64_t>(msg.header.stamp.nanosec);
            const auto old_ns = static_cast<int64_t>(last_imu_header_stamp_.sec) * 1000000000LL
                              + static_cast<int64_t>(last_imu_header_stamp_.nanosec);
            if (new_ns < old_ns) {
              timestamp_regression_.store(true);
              RCLCPP_WARN(get_logger(),
                      "IMU 时间戳回退：%lld ns -> %lld ns，状态机将进入 FAULT",
                      static_cast<long long>(old_ns),
                      static_cast<long long>(new_ns));
            }
            last_imu_header_stamp_ = msg.header.stamp;
          } else {
            std::lock_guard<std::mutex> lock(imu_stamp_mutex_);
            last_imu_header_stamp_ = msg.header.stamp;
            imu_ever_received_.store(true);
          }

          // 更新 last_imu_steady_time_（用于超时检测）
          last_imu_steady_time_ = std::chrono::steady_clock::now();

          // 原有姿态解算逻辑
          if (upkie_control::orientation_covariance_valid(
                  msg.orientation_covariance[0])) {
            pitch_.store(upkie_control::quaternion_to_pitch(
                msg.orientation.w, msg.orientation.x,
                msg.orientation.y, msg.orientation.z));
            covariance_valid_.store(true);
          } else {
            pitch_.store(0.0);
            covariance_valid_.store(false);
          }
          pitch_rate_.store(msg.angular_velocity.y);
          yaw_rate_.store(msg.angular_velocity.z);
        });
    yaw_rate_command_sub_ = create_subscription<std_msgs::msg::Float64>(
        "yaw_rate_command", 10,
        [this](const std_msgs::msg::Float64& msg) {
          if (!std::isfinite(msg.data)) {
            nan_detected_.store(true);
            return;
          }
          yaw_rate_command_.store(msg.data);
        });

    // 第 43 关：/estop 服务（急停触发，触发后只有 /reset 可清除）
    estop_service_ = create_service<std_srvs::srv::Trigger>(
        "estop",
        [this](const std::shared_ptr<rmw_request_id_t>,
               const std::shared_ptr<std_srvs::srv::Trigger::Request>,
               const std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
          estop_triggered_.store(true);
          RCLCPP_WARN(get_logger(), "ESTOP 触发，状态机将进入 FAULT");
          response->success = true;
        });
    // 第 43 关：/arm 服务（操作者显式请求 arm，进入 ARMED 后自动重置）
    arm_service_ = create_service<std_srvs::srv::Trigger>(
        "arm",
        [this](const std::shared_ptr<rmw_request_id_t>,
               const std::shared_ptr<std_srvs::srv::Trigger::Request>,
               const std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
          arm_requested_.store(true);
          RCLCPP_INFO(get_logger(), "ARM 请求已收到");
          response->success = true;
        });
    // 第 43 关：/reset 服务（FAULT → BOOT 人工复位，同时清除 estop_triggered_）
    reset_service_ = create_service<std_srvs::srv::Trigger>(
        "reset",
        [this](const std::shared_ptr<rmw_request_id_t>,
               const std::shared_ptr<std_srvs::srv::Trigger::Request>,
               const std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
          reset_requested_.store(true);
          estop_triggered_.store(false);
          // 清除故障检测标志，使状态机可以从 BOOT 重新开始
          nan_detected_.store(false);
          timestamp_regression_.store(false);
          RCLCPP_INFO(get_logger(), "RESET 请求已收到，状态机将从 BOOT 重启");
          response->success = true;
        });

    timer_ = create_wall_timer(std::chrono::milliseconds(10),
                               std::bind(&ControlNode::control_tick, this));

    if (record_timing_) {
      RCLCPP_INFO(get_logger(),
                  "周期时间戳记录已启用，输出路径: %s",
                  record_timing_path_.c_str());
    }
    if (record_log_) {
      // 日志文件以追加模式打开，便于多次运行拼接
      log_file_.open(log_path_, std::ios::app);
      if (!log_file_.is_open()) {
        RCLCPP_ERROR(get_logger(), "无法打开日志文件: %s",
                     log_path_.c_str());
      } else {
        RCLCPP_INFO(get_logger(),
                    "统一日志记录已启用，输出路径: %s (episode_id=%d)",
                    log_path_.c_str(), episode_id_);
      }
    }
  }

upkie_control::ControlNode::~ControlNode() {
    if (record_timing_) {
      WriteTimingJson();
    }
    // 析构时关闭日志文件（ofstream 析构也会关闭，显式 close 更明确）
    if (log_file_.is_open()) {
      log_file_.close();
    }
  }

  // 查询最后一个力矩输出（供外部诊断工具读取，本节点不使用）
std::array<double, 2> upkie_control::ControlNode::GetLastTorques() const {
    return {last_torque_left_.load(), last_torque_right_.load()};
}

upkie_control::SafetyState upkie_control::ControlNode::GetSafetyState() const {
  return safety_state_.load();
}

void upkie_control::ControlNode::control_tick() {
    const auto tick_start = std::chrono::steady_clock::now();
    if (record_timing_) {
      std::lock_guard<std::mutex> lock(timing_mutex_);
      timestamps_.push_back(tick_start);
    }

    // PD 控制律：Kp=3.0, Kd=0.8；力矩限幅 ±1.0 N·m
    // 轮符号约定：左轮 +1.0，右轮 -1.0
    const double pitch = pitch_.load();
    const double pitch_rate = pitch_rate_.load();
    // 限幅前公共力矩（用于日志记录与安全标志判定）
    const double raw_torque_common = 3.0 * pitch + 0.8 * pitch_rate;
    // PD 限幅后公共力矩（未考虑安全状态机门控）
    const double clamped_torque_common =
        upkie_control::clamp_torque(raw_torque_common, 1.0);
    const double yaw_torque = upkie_control::clamp_torque(
        yaw_rate_gain_ * (yaw_rate_command_.load() - yaw_rate_.load()),
        yaw_torque_limit_);
    const auto commanded_torques =
        upkie_control::combine_balance_and_yaw_torques(
            clamped_torque_common, yaw_torque, 1.0);

    // 第 43 关：推进安全状态机
    // SafetyInput 字段：current_state, pitch, sensor_fresh, estop_released,
    //                  arm_requested, reset_requested, nan_detected, communication_lost
    // 第 43 关：接入真实传感器健康检测（IMU 超时/NaN/通信中断）
    const bool estop_released = !estop_triggered_.load();

    // 第 43 关：真实传感器超时检测
    // 超时阈值 50ms（100Hz 标称 10ms，5 倍周期为超时边界）
    // 未收到过 IMU 时不报超时（避免启动阶段误报）
    const auto now = std::chrono::steady_clock::now();
    const bool imu_received = imu_ever_received_.load();
    double elapsed_ms = 0.0;
    // 第 43 关：时间戳回退同样视为通信失联（数据链路异常或重放）
    // 该标志由 IMU 回调检测 header.stamp 倒退时置位，需 /reset 清除
    bool communication_lost = timestamp_regression_.load();
    if (imu_received) {
      elapsed_ms = std::chrono::duration<double, std::milli>(
                       now - last_imu_steady_time_).count();
      // 传感器超时：IMU 断流超过 50ms
      if (elapsed_ms > 200.0) {
        communication_lost = true;
      }
    }
    const bool sensor_fresh = upkie_control::sensor_is_fresh(
        imu_received, covariance_valid_.load(), elapsed_ms, 50.0);

    // 第 43 关：/reset 服务清除 NaN 和时间戳回退标志
    // reset_requested_ 已在状态机中处理 BOOT 转换，这里同步清除故障标志
    if (reset_requested_.load() && safety_state_.load() == SafetyState::FAULT) {
      nan_detected_.store(false);
      timestamp_regression_.store(false);
    }

    const SafetyInput safety_input{
        safety_state_.load(),
        pitch,
        sensor_fresh,
        estop_released,
        arm_requested_.load(),
        reset_requested_.load(),
        nan_detected_.load(),
        communication_lost,
        pitch_safety_limit_rad_,
    };
    const SafetyState next_state = transition(safety_input);
    safety_state_.store(next_state);

    // 进入 ARMED 后自动重置 arm_requested_，避免持续 arm
    if (next_state == SafetyState::ARMED) {
      arm_requested_.store(false);
    }
    // 离开 FAULT（已转 BOOT）后清除 reset_requested_，避免持续 reset
    if (next_state == SafetyState::BOOT && reset_requested_.load()) {
      reset_requested_.store(false);
    }

    // 第 43 关：发布 /safety_state 话题（每个 tick 一次）
    std_msgs::msg::String state_msg;
    state_msg.data = state_name(safety_state_.load());
    safety_state_pub_->publish(state_msg);

    // 第 43 关：非 ARMED 状态输出零力矩（覆盖 PD 输出）
    // clamped_torque_common 仍按 PD 计算保留，用于日志审计；
    // 实际下发的 final_torque_common 受安全状态机门控。
    const bool armed = is_armed(safety_state_.load());
    const double final_torque_common = armed ? clamped_torque_common : 0.0;
    const double final_torque_left = armed ? commanded_torques[0] : 0.0;
    const double final_torque_right = armed ? commanded_torques[1] : 0.0;

    std_msgs::msg::Float64MultiArray message;
    message.data = {final_torque_left, final_torque_right};
    torque_pub_->publish(message);
    last_torque_left_.store(final_torque_left);
    last_torque_right_.store(final_torque_right);

    // 第 42 关：统一日志记录（仅启用且文件可用时写入，零开销保证）
    if (record_log_ && log_file_.is_open()) {
      // 安全标志优先级（高→低）：
      //   3=FAULT（状态机进入故障，第 43 关新增）
      //   2=力矩饱和（|raw|>1.0）
      //   1=协方差无效（pitch==0 且协方差无效）
      //   0=正常
      uint8_t safety_flag = 0;
      if (pitch == 0.0 && !covariance_valid_.load()) {
        safety_flag = 1;
      }
      if (std::abs(raw_torque_common) > 1.0) {
        safety_flag = 2;
      }
      // 第 43 关：FAULT 状态优先级最高
      if (is_fault(safety_state_.load())) {
        safety_flag = 3;
      }
      // 本次 tick 处理耗时（steady_clock 单调时钟）
      const auto tick_end = std::chrono::steady_clock::now();
      const double loop_cycle_ms =
          std::chrono::duration<double, std::milli>(tick_end - tick_start)
              .count();

      upkie_control::LogEntry entry;
      entry.timestamp_ns = static_cast<uint64_t>(
          std::chrono::duration_cast<std::chrono::nanoseconds>(
              tick_start.time_since_epoch())
              .count());
      entry.episode_id = static_cast<uint32_t>(episode_id_);
      entry.git_commit = GIT_COMMIT_HASH;
      entry.pitch_rad = pitch;
      entry.pitch_rate_rad_s = pitch_rate;
      entry.raw_torque_common_nm = raw_torque_common;
      entry.clamped_torque_common_nm = clamped_torque_common;
      entry.safety_flag = safety_flag;
      entry.loop_cycle_ms = loop_cycle_ms;
      log_file_ << upkie_control::serialize_log_entry(entry) << "\n";
    }
  }

  // 将时间戳数组写入 JSON 文件
  // 字段：periods_ms（相邻 tick 差，单位 ms）、statistics、raw_offset_ms
void upkie_control::ControlNode::WriteTimingJson() {
    std::lock_guard<std::mutex> lock(timing_mutex_);
    if (timestamps_.size() < 2) {
      std::ofstream ofs(record_timing_path_);
      ofs << "{\"error\": \"samples < 2\", \"count\": "
          << timestamps_.size() << "}";
      return;
    }
    // 计算每个 tick 相对第一个 tick 的偏移（ms）
    std::vector<double> offset_ms;
    offset_ms.reserve(timestamps_.size());
    const auto t0 = timestamps_.front();
    for (const auto& t : timestamps_) {
      const double ms = std::chrono::duration<double, std::milli>(t - t0).count();
      offset_ms.push_back(ms);
    }
    // 计算相邻周期（ms）
    std::vector<double> periods_ms;
    periods_ms.reserve(timestamps_.size() - 1);
    for (size_t i = 1; i < timestamps_.size(); ++i) {
      const double ms = std::chrono::duration<double, std::milli>(
                            timestamps_[i] - timestamps_[i - 1])
                            .count();
      periods_ms.push_back(ms);
    }
    // 统计信息
    double sum = 0.0;
    double mn = periods_ms.front();
    double mx = periods_ms.front();
    for (const double p : periods_ms) {
      sum += p;
      if (p < mn) mn = p;
      if (p > mx) mx = p;
    }
    const double mean = sum / periods_ms.size();
    // P50 / P99
    std::vector<double> sorted = periods_ms;
    std::sort(sorted.begin(), sorted.end());
    const double p50 = sorted[sorted.size() / 2];
    const double p99 = sorted[static_cast<size_t>(
        std::min<double>(0.99 * (sorted.size() - 1), sorted.size() - 1))];
    // deadline miss：周期 > 12ms（100Hz 标称 10ms，允许 20% 抖动）
    int miss_count = 0;
    const double deadline_ms = 12.0;
    for (const double p : periods_ms) {
      if (p > deadline_ms) ++miss_count;
    }

    std::ofstream ofs(record_timing_path_);
    if (!ofs.is_open()) {
      RCLCPP_ERROR(get_logger(), "无法写入时间戳文件: %s",
                   record_timing_path_.c_str());
      return;
    }
    ofs << "{\n";
    ofs << "  \"topic\": \"/wheel_torque\",\n";
    ofs << "  \"timer_period_ms_target\": 10.0,\n";
    ofs << "  \"sample_count\": " << timestamps_.size() << ",\n";
    ofs << "  \"period_count\": " << periods_ms.size() << ",\n";
    ofs << "  \"deadline_ms\": " << deadline_ms << ",\n";
    ofs << "  \"statistics\": {\n";
    ofs << "    \"mean_period_ms\": " << mean << ",\n";
    ofs << "    \"min_period_ms\": " << mn << ",\n";
    ofs << "    \"max_period_ms\": " << mx << ",\n";
    ofs << "    \"p50_period_ms\": " << p50 << ",\n";
    ofs << "    \"p99_period_ms\": " << p99 << ",\n";
    ofs << "    \"deadline_miss_count\": " << miss_count << ",\n";
    ofs << "    \"deadline_miss_rate\": "
        << static_cast<double>(miss_count) / periods_ms.size() << "\n";
    ofs << "  },\n";
    ofs << "  \"offsets_ms\": [";
    for (size_t i = 0; i < offset_ms.size(); ++i) {
      if (i) ofs << ", ";
      ofs << offset_ms[i];
    }
    ofs << "],\n";
    ofs << "  \"periods_ms\": [";
    for (size_t i = 0; i < periods_ms.size(); ++i) {
      if (i) ofs << ", ";
      ofs << periods_ms[i];
    }
    ofs << "]\n";
    ofs << "}\n";
    RCLCPP_INFO(get_logger(),
                "时间戳已写入 %s（samples=%zu, mean=%.3fms, p99=%.3fms, miss=%d）",
                record_timing_path_.c_str(), timestamps_.size(), mean, p99,
                miss_count);
  }
