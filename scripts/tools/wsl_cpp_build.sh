#!/usr/bin/env bash
# 在 WSL2 中构建 C++ 控制库并运行 CTest，导出正式日志。
set -euo pipefail

ROOT=/mnt/c/HOME/Project/Bipedal-Wheel-robot-learning
LOG="$ROOT/outputs/logs/cpp_ctest_20260723_wsl2.log"
mkdir -p "$ROOT/outputs/logs"
cd "$ROOT/cpp"

{
  echo "== CONFIGURE =="
  cmake -B build-wsl2 -DCMAKE_BUILD_TYPE=Release
  echo "== BUILD =="
  cmake --build build-wsl2 -j
  echo "== CTEST =="
  ctest --test-dir build-wsl2 --output-on-failure
} 2>&1 | tee "$LOG"

echo "CTEST_EXIT=${PIPESTATUS[0]}" | tee -a "$LOG"
