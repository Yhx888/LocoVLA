#include "upkie_course/control.hpp"

#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
#include <thread>

#ifdef _WIN32
#include <windows.h>
#include <mmsystem.h>
#endif

int main(int argc, char** argv) {
  int ticks = 6000;
  int period_ms = 10;
  int inject_block_ms = 0;
  for (int index = 1; index < argc; ++index) {
    const std::string argument = argv[index];
    if (index + 1 >= argc) {
      return 2;
    }
    const int value = std::stoi(argv[++index]);
    if (argument == "--ticks") {
      ticks = value;
    } else if (argument == "--period-ms") {
      period_ms = value;
    } else if (argument == "--inject-block-ms") {
      inject_block_ms = value;
    } else {
      return 2;
    }
  }
  if (ticks <= 1 || period_ms <= 0 || inject_block_ms < 0) {
    return 2;
  }

  using Clock = std::chrono::steady_clock;
  const auto period = std::chrono::milliseconds(period_ms);
#ifdef _WIN32
  timeBeginPeriod(1);
#endif
  const auto origin = Clock::now();
  auto deadline = origin;
  auto previous_start = origin;
  std::cout << "tick,start_ns,period_ns,compute_ns,deadline_miss,balance_nm,left_nm,right_nm\n";
  std::cout << std::setprecision(17);
  for (int tick = 0; tick < ticks; ++tick) {
    deadline += period;
    const auto start = Clock::now();
    const Eigen::Vector4d state{
        0.05 * std::sin(0.1 * tick),
        0.02 * std::cos(0.1 * tick),
        0.08 * std::sin(0.07 * tick),
        0.03 * std::cos(0.07 * tick)};
    const double balance = upkie_course::balance_torque(state);
    const auto wheels = upkie_course::wheel_torques(balance, 0.0, 1.0);
    if (inject_block_ms > 0 && tick > 0 && tick % 100 == 0) {
      std::this_thread::sleep_for(std::chrono::milliseconds(inject_block_ms));
    }
    const auto completed = Clock::now();
    const auto period_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(start - previous_start).count();
    const auto compute_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(completed - start).count();
    const int missed = completed > deadline ? 1 : 0;
    std::cout << tick << ','
              << std::chrono::duration_cast<std::chrono::nanoseconds>(start - origin).count() << ','
              << period_ns << ',' << compute_ns << ',' << missed << ','
              << balance << ',' << wheels[0] << ',' << wheels[1] << '\n';
    previous_start = start;
    std::this_thread::sleep_until(deadline);
  }
#ifdef _WIN32
  timeEndPeriod(1);
#endif
  return 0;
}
