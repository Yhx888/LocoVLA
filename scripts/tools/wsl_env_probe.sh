#!/usr/bin/env bash
# 探查 WSL2 的 Python 环境与课程依赖是否满足 38-47/H01 checkpoint 运行需求。
ROOT=/mnt/c/HOME/Project/Bipedal-Wheel-robot-learning
echo "== python3 =="
which python3 || echo "no python3"
python3 --version 2>&1

echo "== linux venv =="
if [ -d "$ROOT/.venv-wsl" ]; then echo ".venv-wsl exists"; else echo "no .venv-wsl"; fi
ls "$ROOT/.venv/bin" 2>/dev/null | head -3 || echo "no posix .venv/bin (windows venv)"

echo "== package import checks (system python3) =="
python3 - <<'PY'
mods = ["numpy", "scipy", "mujoco", "gymnasium", "torch", "stable_baselines3", "yaml"]
for m in mods:
    try:
        mod = __import__(m)
        print(f"OK  {m} {getattr(mod,'__version__','?')}")
    except Exception as e:
        print(f"MISS {m}: {type(e).__name__}")
try:
    import upkie_mujoco_course
    print("OK  upkie_mujoco_course")
except Exception as e:
    print(f"MISS upkie_mujoco_course: {type(e).__name__} {e}")
PY
