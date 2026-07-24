#!/usr/bin/env bash
# 探查 WSL2 可用的 Python 打包工具，判断能否在不使用 sudo 的情况下建立可运行环境。
for t in pip pip3 pipx virtualenv conda mamba python3.11 python3.12 uv; do
  printf '%-12s ' "$t"
  command -v "$t" || echo MISSING
done
echo "--- ensurepip ---"
python3 -m ensurepip --version 2>&1 | head -1
echo "--- pip module ---"
python3 -m pip --version 2>&1 | head -1
echo "--- dpkg venv/pip ---"
dpkg -l python3-venv python3.12-venv python3-pip 2>/dev/null | grep -E 'venv|pip' || echo 'none'
echo "--- site-packages numpy path ---"
python3 -c "import numpy,sys; print(numpy.__file__); print(sys.prefix)"
