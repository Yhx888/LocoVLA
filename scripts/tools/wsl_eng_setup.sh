#!/usr/bin/env bash
# 在 WSL2 建立轻量 Python 环境并尝试工程章节 38 的证据生成 + checkpoint 校验。
# 不 pip install 课程包本身（requires-python 限定 3.11，与 WSL 的 3.12 冲突），
# 改用 PYTHONPATH=src 直接加载源码。
set -uo pipefail

ROOT=/mnt/c/HOME/Project/Bipedal-Wheel-robot-learning
cd "$ROOT"

VENV="$ROOT/.venv-wsl"
if [ ! -d "$VENV" ]; then
  echo "== 创建 Linux venv (python3.12) =="
  python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"

echo "== 安装轻量依赖 =="
pip install -q --upgrade pip >/dev/null 2>&1
pip install -q numpy scipy matplotlib pytest 2>&1 | tail -3

export PYTHONPATH="$ROOT/src"
echo "== python & imports =="
python -c "import numpy,scipy,matplotlib,pytest; import upkie_mujoco_course; print('imports OK', __import__('sys').version.split()[0])"

echo "== 生成章节 38 证据（C++ 数值一致性，使用 WSL2 cpp 构建）=="
python scripts/run_engineering_lab.py --chapter 38 --seed 38 --build-dir cpp/build-wsl2 2>&1 | tail -15
echo "LAB38_EXIT=$?"
